"""
네이버 답글 등록 자동화 모듈
Supabase에서 승인된 AI 답글을 가져와 네이버에 자동으로 등록합니다.
"""

import os
import sys
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from pathlib import Path

# Windows 환경 UTF-8 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from playwright.async_api import async_playwright, Page, Browser
from supabase import create_client, Client
from dotenv import load_dotenv

# NaverAutoLogin 클래스 임포트
sys.path.append(os.path.dirname(__file__))
from naver_login_auto import NaverAutoLogin

# 환경 변수 로드 (backend 폴더의 .env 파일)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/naver_reply_poster.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ReplyTask:
    """답글 작업 데이터 클래스"""
    review_id: str
    naver_review_id: str
    store_id: str
    platform_store_code: str
    platform_id: str  # 네이버 로그인 ID
    platform_password: str  # 네이버 로그인 비밀번호
    reviewer_name: str
    review_text: str
    rating: int
    ai_generated_reply: str
    approved_at: str
    # 답글 규칙 정보
    reply_style: str = 'friendly'
    custom_instructions: str = None
    branding_keywords: list = None
    auto_approve_positive: bool = True
    
    def __repr__(self):
        return f"ReplyTask(store={self.platform_store_code}, reviewer={self.reviewer_name})"


class NaverReplyPoster:
    """네이버 답글 자동 등록 클래스"""
    
    def __init__(self):
        """초기화"""
        # Supabase 클라이언트 설정
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경변수를 설정해주세요.")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # 브라우저 프로필 경로
        self.browser_data_dir = Path("logs/browser_profiles/naver")
        self.browser_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 통계
        self.stats = {
            "total_fetched": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
    
    def _get_browser_profile_path(self, platform_id: str) -> str:
        """계정별 브라우저 프로필 경로 생성"""
        account_hash = hashlib.md5(platform_id.encode()).hexdigest()[:10]
        profile_path = self.browser_data_dir / f"profile_{account_hash}"
        profile_path.mkdir(parents=True, exist_ok=True)
        return str(profile_path)
    
    def _apply_branding_keywords(self, reply_text: str, branding_keywords: list) -> str:
        """브랜딩 키워드를 답글에 적용"""
        if not branding_keywords or not reply_text:
            return reply_text
        
        # 브랜딩 키워드를 자연스럽게 추가
        branded_reply = reply_text
        
        # 키워드를 문장 끝에 추가 (예: "감사합니다! #맛집 #친절")
        keywords_text = " ".join([f"#{keyword.strip()}" for keyword in branding_keywords if keyword.strip()])
        
        if keywords_text:
            # 답글 끝에 해시태그 형태로 추가
            if not branded_reply.endswith(('.', '!', '?')):
                branded_reply += "."
            branded_reply += f" {keywords_text}"
            
            logger.debug(f"브랜딩 키워드 적용: {keywords_text}")
        
        return branded_reply
    
    async def fetch_pending_replies(self, limit: int = 10) -> List[ReplyTask]:
        """
        Supabase에서 등록 대기 중인 답글 가져오기
        
        조건:
        1. reply_status = 'approved' (승인됨) 또는 미답변이지만 AI 답글이 생성됨
        2. ai_generated_reply가 존재
        3. reply_sent_at이 NULL (아직 전송 안됨)
        4. platform_stores에서 계정 정보와 답글 규칙 가져오기
        """
        try:
            # reviews_naver에서 미답변이지만 AI 답글이 있는 리뷰 조회
            # 1단계: AI 답글이 있고 아직 전송하지 않은 리뷰 조회
            reviews_response = self.supabase.table('reviews_naver').select(
                "id, naver_review_id, platform_store_id, "
                "reviewer_name, review_text, rating, ai_generated_reply, "
                "approved_at, reply_status"
            ).is_(
                'reply_sent_at', 'null'
            ).not_.is_(
                'ai_generated_reply', 'null'
            ).limit(limit).execute()
            
            logger.info(f"🔍 조회된 리뷰 수: {len(reviews_response.data)}개")
            
            tasks = []
            for review in reviews_response.data:
                # platform_stores에서 해당 매장의 계정 정보 조회
                # reviews_naver.platform_store_id는 실제로 platform_stores.id를 참조
                store_response = self.supabase.table('platform_stores').select(
                    "platform_id, platform_pw, reply_style, custom_instructions, "
                    "branding_keywords, auto_approve_positive, platform_store_id"
                ).eq('id', review['platform_store_id']).eq(
                    'platform', 'naver'
                ).eq('is_active', True).execute()
                
                if not store_response.data:
                    logger.warning(f"매장 {review['platform_store_id']}의 계정 정보를 찾을 수 없습니다.")
                    continue
                
                store_info = store_response.data[0]
                
                if not store_info.get('platform_id') or not store_info.get('platform_pw'):
                    logger.warning(f"매장 {review['platform_store_id']}의 로그인 정보가 없습니다.")
                    continue
                
                # 브랜딩 키워드 파싱
                branding_keywords = store_info.get('branding_keywords', [])
                if isinstance(branding_keywords, str):
                    branding_keywords = json.loads(branding_keywords) if branding_keywords else []
                
                task = ReplyTask(
                    review_id=review['id'],
                    naver_review_id=review['naver_review_id'],
                    store_id=review['platform_store_id'],  # platform_stores.id
                    platform_store_code=store_info['platform_store_id'],  # 실제 네이버 매장 ID
                    platform_id=store_info['platform_id'],
                    platform_password=store_info['platform_pw'],
                    reviewer_name=review['reviewer_name'],
                    review_text=review['review_text'],
                    rating=review['rating'] or 3,
                    ai_generated_reply=review['ai_generated_reply'],
                    approved_at=review.get('approved_at'),
                    reply_style=store_info.get('reply_style', 'friendly'),
                    custom_instructions=store_info.get('custom_instructions'),
                    branding_keywords=branding_keywords,
                    auto_approve_positive=store_info.get('auto_approve_positive', True)
                )
                tasks.append(task)
            
            self.stats["total_fetched"] = len(tasks)
            logger.info(f"📋 {len(tasks)}개의 등록 대기 답글을 가져왔습니다.")
            
            # 통계 정보 출력
            if tasks:
                logger.info("📊 작업 요약:")
                for task in tasks[:3]:  # 처음 3개만 표시
                    logger.info(f"  - {task.reviewer_name} ({task.rating}⭐) → {task.ai_generated_reply[:30]}...")
                if len(tasks) > 3:
                    logger.info(f"  ... 외 {len(tasks) - 3}개")
            
            return tasks
            
        except Exception as e:
            logger.error(f"답글 가져오기 실패: {e}")
            return []
    
    async def login_with_naver_auto_login(self, platform_id: str, platform_password: str) -> dict:
        """NaverAutoLogin 시스템을 사용한 고급 로그인"""
        try:
            logger.info(f"🔑 NaverAutoLogin으로 로그인 시작: {platform_id}")
            
            # NaverAutoLogin 인스턴스 생성 (크롤러와 동일한 설정)
            auto_login = NaverAutoLogin(
                headless=False,  # 디버깅을 위해 헤드리스 모드 비활성화
                timeout=60000,   # 충분한 타임아웃 설정
                force_fresh_login=False  # 기존 세션 활용
            )
            
            logger.info("로그인 시도 중...")
            
            # 브라우저 세션을 유지하면서 로그인 (크롤러와 동일한 방식)
            result = await auto_login.login(
                platform_id=platform_id,
                platform_password=platform_password,
                keep_browser_open=True
            )
            
            logger.info(f"로그인 결과: {result}")
            
            if result['success']:
                logger.info(f"✅ NaverAutoLogin 로그인 성공: {platform_id}")
                
                # 브라우저와 페이지 객체 확인
                browser = result.get('browser')
                page = result.get('page')
                
                if browser and page:
                    logger.info(f"✅ 브라우저 세션 유지됨 - 현재 URL: {page.url}")
                    
                    # 스마트플레이스 완전 로그인 검증
                    try:
                        logger.info("🔐 스마트플레이스 완전 로그인 검증 시작")
                        
                        # 1. 스마트플레이스 메인 페이지로 이동
                        await page.goto("https://new.smartplace.naver.com", wait_until="networkidle", timeout=30000)
                        await asyncio.sleep(5)  # 충분한 로딩 시간
                        
                        current_url = page.url
                        logger.info(f"스마트플레이스 접근 후 URL: {current_url}")
                        
                        # 2. 로그인 페이지로 리디렉션되었는지 확인
                        if "nid.naver.com" in current_url:
                            logger.warning("⚠️ 스마트플레이스 접근 시 로그인 페이지로 리디렉션됨")
                            return {
                                'success': False,
                                'error': '스마트플레이스 접근 권한 없음 - 로그인 미완료',
                                'browser': browser,
                                'page': page,
                                'playwright': result.get('playwright')
                            }
                        
                        # 3. 로그인 요구 요소 확인
                        login_required_elements = await page.query_selector_all("a[href*='nid.naver.com'], button:has-text('로그인'), .login")
                        if login_required_elements:
                            logger.warning(f"⚠️ 페이지에 로그인 요구 요소 {len(login_required_elements)}개 발견")
                            return {
                                'success': False,
                                'error': '스마트플레이스 로그인 미완료',
                                'browser': browser,
                                'page': page,
                                'playwright': result.get('playwright')
                            }
                        
                        # 4. 로그인된 사용자 요소 확인
                        user_elements = await page.query_selector_all("a[href*='/my/'], .user, [data-test*='user'], .profile")
                        logger.info(f"💡 사용자 관련 요소: {len(user_elements)}개 발견")
                        
                        # 5. 페이지 텍스트에서 로그인 상태 확인
                        try:
                            page_text = await page.text_content("body")
                            if any(keyword in page_text for keyword in ["로그아웃", "내 정보", "마이페이지", "내 업체"]):
                                logger.info("✅ 페이지 텍스트에서 로그인 상태 확인됨")
                            else:
                                logger.info("💡 페이지 텍스트에서 명확한 로그인 표시 없음")
                        except:
                            pass
                        
                        logger.info("✅ 스마트플레이스 로그인 검증 완료")
                        
                    except Exception as test_error:
                        logger.error(f"스마트플레이스 로그인 검증 실패: {test_error}")
                        return {
                            'success': False,
                            'error': f'스마트플레이스 검증 오류: {test_error}',
                            'browser': browser,
                            'page': page,
                            'playwright': result.get('playwright')
                        }
                
                return result
            else:
                error_msg = result.get('error', '알 수 없는 오류')
                logger.error(f"❌ NaverAutoLogin 로그인 실패: {platform_id}")
                logger.error(f"   오류 상세: {error_msg}")
                
                # 2차 인증이 필요한 경우
                if result.get('requires_2fa'):
                    logger.error("   💡 2차 인증이 필요합니다. 네이버 계정 설정을 확인하세요.")
                
                return result
                
        except Exception as e:
            logger.error(f"NaverAutoLogin 로그인 중 예외 발생: {e}")
            import traceback
            logger.error(f"스택 트레이스: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'browser': None,
                'page': None
            }
    
    async def post_reply(self, page: Page, task: ReplyTask) -> bool:
        """
        네이버 리뷰에 답글 등록
        
        1. 리뷰 페이지로 이동
        2. 해당 리뷰 찾기
        3. 답글 쓰기 버튼 클릭
        4. 답글 내용 입력
        5. 등록 버튼 클릭
        """
        try:
            # 비즈니스 관리자 모드로 리뷰 관리 페이지 접근
            business_review_url = f"https://new.smartplace.naver.com/bizes/place/{task.platform_store_code}/reviews"
            logger.info(f"📍 비즈니스 리뷰 관리 페이지로 이동: {business_review_url}")
            
            await page.goto(business_review_url, wait_until="networkidle")
            await asyncio.sleep(3)
            
            # 관리자 모드인지 확인
            current_url = page.url
            if "bizes" not in current_url:
                logger.warning("⚠️ 비즈니스 관리자 모드가 아닌 것 같습니다.")
                # 대안: 직접 비즈니스 센터로 이동
                business_center_url = f"https://new.smartplace.naver.com/bizes/place/{task.platform_store_code}"
                logger.info(f"📍 비즈니스 센터로 이동: {business_center_url}")
                await page.goto(business_center_url, wait_until="networkidle")
                await asyncio.sleep(2)
                
                # 리뷰 탭 클릭
                try:
                    review_tab = await page.query_selector("a[href*='/reviews'], button:has-text('리뷰'), [data-area-code*='review']")
                    if review_tab:
                        await review_tab.click()
                        await asyncio.sleep(3)
                        logger.info("✅ 리뷰 탭 클릭 완료")
                    else:
                        logger.warning("⚠️ 리뷰 탭을 찾을 수 없습니다.")
                except Exception as e:
                    logger.warning(f"리뷰 탭 클릭 실패: {e}")
                    
                # 최종 URL로 직접 이동
                await page.goto(business_review_url, wait_until="networkidle")
                await asyncio.sleep(3)
            
            # 로그인이 필요한지 확인
            current_url = page.url
            if "nid.naver.com" in current_url or "login" in current_url.lower():
                logger.warning("⚠️ 리뷰 페이지 접근 시 로그인이 필요합니다. 다시 로그인을 시도합니다.")
                
                # 네이버 메인 페이지를 거쳐서 스마트플레이스로 이동
                await page.goto("https://www.naver.com", wait_until="networkidle")
                await asyncio.sleep(2)
                
                # 스마트플레이스 링크 클릭 또는 직접 이동
                await page.goto("https://new.smartplace.naver.com", wait_until="networkidle")
                await asyncio.sleep(2)
                
                # 다시 리뷰 페이지 시도
                await page.goto(review_url, wait_until="networkidle")
                await asyncio.sleep(3)
            
            logger.info(f"📄 현재 페이지: {page.url}")
            
            # 날짜 필터를 "7일"로 설정
            try:
                logger.info("📅 날짜 필터를 '7일'로 설정 중...")
                
                # 날짜 드롭박스 클릭
                date_filter = await page.query_selector("button[data-area-code='rv.calendarfilter']")
                if date_filter:
                    await date_filter.click()
                    await asyncio.sleep(1)
                    
                    # "7일" 옵션 클릭 (여러 가능한 선택자 시도)
                    week_option_selectors = [
                        "[data-area-code='rv.calendarweek']",
                        "a[data-area-code='rv.calendarweek']",
                        "text=7일",
                        "a:has-text('7일')",
                        "li:has-text('7일')"
                    ]
                    
                    for selector in week_option_selectors:
                        try:
                            week_option = await page.query_selector(selector)
                            if week_option:
                                await week_option.click()
                                logger.info("✅ 날짜 필터를 '7일'로 설정 완료")
                                await asyncio.sleep(3)  # 리뷰 다시 로딩 대기
                                break
                        except:
                            continue
                else:
                    logger.info("💡 날짜 필터 버튼을 찾을 수 없음 - 기본 상태로 진행")
                    
            except Exception as e:
                logger.warning(f"날짜 필터 설정 실패: {e}")
            
            # 페이지 구조 확인 (디버깅용)
            logger.info("🔍 페이지 구조 분석 중...")
            
            # "결제 정보 상세 보기" 링크에서 리뷰 ID 추출
            payment_links = await page.query_selector_all("a[href*='/my/review/']")
            
            found_review_ids = []
            logger.info(f"📋 발견된 결제 정보 링크 수: {len(payment_links)}")
            
            for link in payment_links:
                href = await link.get_attribute("href")
                if href and "/my/review/" in href:
                    # URL에서 리뷰 ID 추출: /my/review/REVIEW_ID/paymentInfo
                    import re
                    match = re.search(r'/my/review/([a-f0-9]{24})', href)
                    if match:
                        review_id = match.group(1)
                        found_review_ids.append(review_id)
                        logger.info(f"📝 추출된 리뷰 ID: {review_id}")
            
            # 추가로 리뷰 구조 확인 (백업용)
            review_containers = await page.query_selector_all("li.pui__X35jYm")
            logger.info(f"📋 발견된 리뷰 컨테이너 수: {len(review_containers)}")
            
            # 중복 제거
            found_review_ids = list(set(found_review_ids))
            
            logger.info(f"🔍 발견된 리뷰 관련 ID들: {found_review_ids}")
            logger.info(f"🎯 찾고 있는 리뷰 ID: {task.naver_review_id}")
            
            # 페이지 제목과 URL 확인
            page_title = await page.title()
            logger.info(f"📄 페이지 제목: {page_title}")
            
            # 로그인이 필요한지 다시 확인
            login_required = await page.query_selector("text=로그인")
            if login_required:
                logger.warning("⚠️ 아직 로그인이 필요한 상태입니다")
                return False
            
            # 리뷰 찾기 (naver_review_id로 매칭)
            matched_review_id = None
            
            # 정확한 매칭 먼저 시도
            if task.naver_review_id in found_review_ids:
                matched_review_id = task.naver_review_id
                logger.info(f"✅ 정확한 리뷰 ID 매칭: {matched_review_id}")
            else:
                # 부분 매칭 시도
                for found_id in found_review_ids:
                    if task.naver_review_id in found_id or found_id in task.naver_review_id:
                        matched_review_id = found_id
                        logger.info(f"🔄 부분 매칭된 리뷰 ID: {found_id}")
                        break
            
            if not matched_review_id:
                logger.warning(f"❌ 리뷰를 찾을 수 없음: {task.naver_review_id}")
                logger.info("💡 가능한 원인: 1) 리뷰가 다른 페이지에 있음, 2) 리뷰가 삭제됨, 3) ID 형식이 다름")
                return False
            
            # 매칭된 리뷰 ID로 해당 링크 찾기
            target_link = await page.query_selector(f"a[href*='/my/review/{matched_review_id}']")
            if not target_link:
                logger.warning(f"❌ 매칭된 리뷰 링크를 찾을 수 없음: {matched_review_id}")
                return False
            
            # 리뷰 컨테이너 찾기 (링크의 상위 요소들 중 리뷰 컨테이너)
            review_element = await target_link.evaluate_handle("""
                element => {
                    let current = element;
                    while (current && current.parentElement) {
                        current = current.parentElement;
                        if (current.classList && current.classList.contains('pui__X35jYm')) {
                            return current;
                        }
                    }
                    return null;
                }
            """)
            
            if not review_element:
                logger.warning(f"❌ 리뷰 컨테이너를 찾을 수 없음: {matched_review_id}")
                return False
            
            # 리뷰로 스크롤
            await review_element.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            
            # 제공된 HTML 구조 기반 정확한 답글 쓰기 버튼 선택자
            reply_button_selectors = [
                "button[data-area-code='rv.replywrite']",                    # 정확한 데이터 속성
                "button.Review_btn__Lu4nI.Review_btn_write__pFgSj",         # 정확한 클래스 조합
                "button[data-area-code='rv.replywrite']:has-text('답글 쓰기')", # 데이터 속성 + 텍스트
                "button:has-text('답글 쓰기')",                              # 텍스트 기반
                ".Review_btn_write__pFgSj",                                 # 답글 쓰기 전용 클래스
                "button.Review_btn__Lu4nI:has-text('답글')",                # 기본 버튼 클래스 + 텍스트
                "button:has(.fn.fn-write2)",                                # 아이콘 기반 선택
                "div.Review_btn_group__mDkTf button[data-area-code='rv.replywrite']" # 그룹 내 버튼
            ]
            
            reply_button = None
            for selector in reply_button_selectors:
                try:
                    reply_button = await review_element.query_selector(selector)
                    if reply_button:
                        logger.info(f"✅ 답글 버튼 발견: {selector}")
                        break
                except:
                    continue
            
            if not reply_button:
                # 제공된 HTML 구조 기반 기존 답글 확인
                existing_reply_selectors = [
                    "a[data-pui-click-code='rv.replyedit']",           # 정확한 답글 수정 링크
                    "a.pui__4Gicix[data-pui-click-code='rv.replyedit']", # 정확한 클래스 조합
                    "a:has-text('수정')",                              # 수정 텍스트 기반
                    "[data-pui-click-code='rv.replyedit']",           # 데이터 속성 기반
                    "button[data-area-code='rv.replyeditedit']",       # 답글 수정 버튼 (수정 모드)
                    ".pui__xtsQN-[data-pui-click-code='rv.replyfold']" # 답글 내용 표시 영역
                ]
                
                existing_reply = None
                for selector in existing_reply_selectors:
                    try:
                        existing_reply = await review_element.query_selector(selector)
                        if existing_reply:
                            logger.info(f"ℹ️ 기존 답글 발견: {selector}")
                            break
                    except:
                        continue
                
                if existing_reply:
                    logger.info(f"ℹ️ 이미 답글이 존재합니다: {task.reviewer_name}")
                    self.stats["skipped"] += 1
                    return False
                else:
                    # 디버깅: 리뷰 요소의 내부 구조 확인
                    try:
                        review_html = await review_element.inner_html()
                        logger.info(f"🔍 리뷰 요소 내부 HTML (처음 500자): {review_html[:500]}...")
                        
                        # 모든 버튼과 링크 확인
                        all_buttons = await review_element.query_selector_all("button, a")
                        logger.info(f"🔍 리뷰 내 버튼/링크 수: {len(all_buttons)}개")
                        
                        for i, btn in enumerate(all_buttons[:5]):  # 처음 5개만
                            btn_text = await btn.text_content()
                            btn_class = await btn.get_attribute("class")
                            btn_onclick = await btn.get_attribute("onclick")
                            btn_href = await btn.get_attribute("href")
                            logger.info(f"  버튼 {i}: text='{btn_text}', class='{btn_class}', onclick='{btn_onclick}', href='{btn_href}'")
                            
                    except Exception as debug_e:
                        logger.error(f"디버깅 중 오류: {debug_e}")
                    
                    # 페이지 전체에서 답글 버튼 검색 (마지막 시도)
                    logger.info("🔍 페이지 전체에서 답글 버튼 재검색...")
                    page_reply_buttons = await page.query_selector_all("button, a")
                    reply_found = False
                    
                    for btn in page_reply_buttons:
                        try:
                            btn_text = await btn.text_content()
                            btn_class = await btn.get_attribute("class")
                            btn_data_area = await btn.get_attribute("data-area-code")
                            
                            # 필터 버튼 제외하고 실제 답글 쓰기 버튼만 찾기
                            if btn_data_area == "rv.replywrite" or \
                               (btn_class and "Review_btn_write__pFgSj" in btn_class) or \
                               (btn_text and btn_text.strip() == "답글 쓰기"):
                                
                                # 필터 버튼은 제외 (rv.replyfilter)
                                if btn_data_area and "filter" in btn_data_area:
                                    continue
                                    
                                logger.info(f"💡 발견된 답글 쓰기 버튼: text='{btn_text}', class='{btn_class}', data-area='{btn_data_area}'")
                                
                                # 해당 리뷰와 연관된 버튼인지 확인
                                btn_parent = await btn.evaluate_handle("element => element.closest('.pui__X35jYm')")
                                if btn_parent:
                                    # 해당 리뷰 컨테이너에 속한 버튼 찾음
                                    reply_button = btn
                                    reply_found = True
                                    logger.info(f"✅ 답글 쓰기 버튼 발견 (페이지 검색): {btn_text}")
                                    break
                        except:
                            continue
                    
                    if not reply_found:
                        logger.error(f"답글 버튼을 찾을 수 없음: {task.reviewer_name}")
                        return False
            
            # 답글 쓰기 버튼 클릭
            await reply_button.click()
            await asyncio.sleep(1)
            
            # 제공된 HTML 구조 기반 정확한 답글 입력 필드 찾기
            textarea_selectors = [
                "#replyWrite",                              # 정확한 ID
                "textarea[id='replyWrite']",                # ID 속성 기반
                "textarea[placeholder*='리뷰 작성자와']",     # placeholder 기반
                ".Review_textarea_box__gTAoe textarea",     # 컨테이너 내 textarea
                "div.Review_textarea_box__gTAoe #replyWrite" # 정확한 경로
            ]
            
            reply_textarea = None
            for selector in textarea_selectors:
                try:
                    reply_textarea = await page.wait_for_selector(selector, timeout=3000)
                    if reply_textarea:
                        logger.info(f"✅ 답글 입력 필드 발견: {selector}")
                        break
                except:
                    continue
                    
            if not reply_textarea:
                logger.error("답글 입력 필드를 찾을 수 없습니다.")
                return False
            
            # 브랜딩 키워드가 있으면 답글에 적용
            final_reply = self._apply_branding_keywords(task.ai_generated_reply, task.branding_keywords)
            
            # 답글 내용 입력
            await reply_textarea.fill(final_reply)
            await asyncio.sleep(0.5)
            
            logger.info(f"📝 답글 내용: {final_reply[:50]}{'...' if len(final_reply) > 50 else ''}")
            
            # 제공된 HTML 구조 기반 정확한 답글 등록 버튼 찾기
            submit_selectors = [
                "button[data-area-code='rv.replydone']",                    # 정확한 데이터 속성
                "button.Review_btn__Lu4nI.Review_btn_enter__az8i7",         # 정확한 클래스 조합
                "button[data-area-code='rv.replydone']:has-text('등록')",    # 데이터 속성 + 텍스트
                "button:has-text('등록')",                                  # 텍스트 기반
                ".Review_btn_enter__az8i7",                                 # 등록 전용 클래스
                "button.Review_btn__Lu4nI:has-text('등록')"                 # 기본 버튼 클래스 + 텍스트
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await page.query_selector(selector)
                    if submit_button:
                        logger.info(f"✅ 답글 등록 버튼 발견: {selector}")
                        break
                except:
                    continue
                    
            if not submit_button:
                logger.error("답글 등록 버튼을 찾을 수 없습니다.")
                return False
            
            await submit_button.click()
            await asyncio.sleep(2)
            
            # 등록 성공 확인 (여러 방법으로 검증)
            await asyncio.sleep(3)  # 페이지 업데이트 대기
            
            # 제공된 HTML 구조 기반 답글 등록 성공 확인
            # 1. 답글 수정 버튼이 나타났는지 확인 (review_element 내에서)
            reply_edit_selectors = [
                "a[data-pui-click-code='rv.replyedit']",           # 정확한 수정 링크
                "a.pui__4Gicix[data-pui-click-code='rv.replyedit']", # 정확한 클래스 조합
                "a:has-text('수정')",                              # 수정 텍스트
                "[data-pui-click-code='rv.replyedit']"             # 데이터 속성 기반
            ]
            
            posted_reply = None
            for selector in reply_edit_selectors:
                try:
                    posted_reply = await review_element.query_selector(selector)
                    if posted_reply:
                        break
                except:
                    continue
            
            # 2. 답글 텍스트가 화면에 표시되는지 확인 (review_element 내에서)
            reply_text_selectors = [
                ".pui__xtsQN-[data-pui-click-code='rv.replyfold']", # 답글 내용 영역
                "a[data-pui-click-code='rv.replyfold']",            # 답글 내용 링크
                ".reply_text",                                      # 일반적인 답글 텍스트
                ".review_reply"                                     # 답글 영역
            ]
            
            reply_displayed = None
            for selector in reply_text_selectors:
                try:
                    reply_displayed = await review_element.query_selector(selector)
                    if reply_displayed:
                        break
                except:
                    continue
            
            if posted_reply or reply_displayed:
                logger.info(f"✅ 답글 등록 성공: {task.reviewer_name}")
                
                # Supabase 업데이트
                await self.update_reply_status(task.review_id, success=True)
                self.stats["success"] += 1
                return True
            else:
                # 에러 메시지 확인
                error_element = await page.query_selector(".error_message, .alert, .notification")
                error_msg = "알 수 없는 오류"
                if error_element:
                    error_msg = await error_element.text_content() or error_msg
                
                logger.error(f"❌ 답글 등록 실패: {task.reviewer_name} - {error_msg}")
                await self.update_reply_status(task.review_id, success=False, error_message=error_msg)
                self.stats["failed"] += 1
                return False
                
        except Exception as e:
            logger.error(f"답글 등록 중 오류: {e}")
            self.stats["errors"].append(str(e))
            self.stats["failed"] += 1
            return False
    
    async def find_review_by_id(self, page, target_review_id: str):
        """리뷰 ID로 리뷰 엘리먼트 찾기 (사용자 제공 HTML 구조 기반)"""
        try:
            logger.info(f"🔍 리뷰 ID로 리뷰 찾기: {target_review_id}")
            
            # 결제 정보 링크에서 리뷰 ID 추출 (사용자 제공 HTML 기준)
            payment_link_selectors = [
                "a[href*='/my/review/'][data-pui-click-code='rv.paymentinfo']",  # 정확한 선택자 (최우선)
                "a[data-pui-click-code='rv.paymentinfo']",                      # 데이터 속성만
                "a[href*='/my/review/']",                                        # 기존 href 패턴
                "a.pui__oQ0qP9[href*='/my/review/']",                           # 클래스 + href
                "a:has-text('결제 정보 상세 보기')"                                 # 텍스트 기반
            ]
            
            found_matches = []
            
            for selector in payment_link_selectors:
                try:
                    payment_links = await page.query_selector_all(selector)
                    logger.info(f"📋 선택자 '{selector}'로 발견된 링크 수: {len(payment_links)}")
                    
                    for link in payment_links:
                        href = await link.get_attribute("href")
                        if href and "/my/review/" in href:
                            # URL에서 리뷰 ID 추출: /my/review/REVIEW_ID/paymentInfo
                            import re
                            match = re.search(r'/my/review/([a-f0-9]{24})', href)
                            if match:
                                review_id = match.group(1)
                                logger.info(f"📝 추출된 리뷰 ID: {review_id}")
                                
                                # 정확한 매칭 확인 (24자리 hex ID)
                                if review_id == target_review_id:
                                    logger.info(f"✅ 매칭된 리뷰 ID: {review_id}")
                                    
                                    # 해당 리뷰 컨테이너 찾기
                                    review_container = await link.evaluate_handle("""
                                        element => {
                                            let current = element;
                                            while (current && current.parentElement) {
                                                current = current.parentElement;
                                                // 리뷰 컨테이너 클래스들 확인
                                                if (current.classList && (
                                                    current.classList.contains('pui__X35jYm') ||
                                                    current.classList.contains('Review_pui_review__zhZdn') ||
                                                    current.tagName === 'LI'
                                                )) {
                                                    return current;
                                                }
                                            }
                                            return null;
                                        }
                                    """)
                                    
                                    if review_container:
                                        logger.info(f"🎯 리뷰 컨테이너 발견: {target_review_id}")
                                        return review_container
                                    
                                found_matches.append({
                                    'id': review_id,
                                    'link': link,
                                    'href': href
                                })
                    
                    # 정확한 매칭을 찾았으면 다른 선택자는 시도하지 않음
                    if found_matches:
                        break
                        
                except Exception as e:
                    logger.warning(f"선택자 '{selector}' 처리 중 오류: {e}")
                    continue
            
            # 정확한 매칭을 못 찾은 경우 추가 디버깅 정보 제공
            if found_matches:
                logger.info(f"🔄 발견된 네이버 리뷰 ID들: {[m['id'] for m in found_matches]}")
                logger.info(f"🎯 찾고 있는 리뷰 ID: {target_review_id}")
                
                # 가능한 매칭 시도 (길이나 패턴 확인)
                for match_info in found_matches:
                    # 24자리 hex 패턴이 맞는지 확인
                    if len(target_review_id) == 24 and len(match_info['id']) == 24:
                        # 일부 유사성 확인 (앞 8자리 또는 뒤 8자리)
                        if (target_review_id[:8] == match_info['id'][:8] or 
                            target_review_id[-8:] == match_info['id'][-8:]):
                            logger.info(f"🔄 패턴 유사성 발견: {match_info['id']}")
                            
                            # 해당 리뷰 컨테이너 찾기
                            review_container = await match_info['link'].evaluate_handle("""
                                element => {
                                    let current = element;
                                    while (current && current.parentElement) {
                                        current = current.parentElement;
                                        if (current.classList && (
                                            current.classList.contains('pui__X35jYm') ||
                                            current.classList.contains('Review_pui_review__zhZdn') ||
                                            current.tagName === 'LI'
                                        )) {
                                            return current;
                                        }
                                    }
                                    return null;
                                }
                            """)
                            
                            if review_container:
                                logger.info(f"⚠️ 패턴 유사성으로 매칭된 리뷰 컨테이너 사용")
                                return review_container
            
            logger.warning(f"❌ 리뷰 ID '{target_review_id}'에 해당하는 리뷰를 찾을 수 없음")
            
            # 디버깅: 페이지의 모든 리뷰 컨테이너 확인
            all_containers = await page.query_selector_all("li.pui__X35jYm, li.Review_pui_review__zhZdn")
            logger.info(f"📋 페이지의 총 리뷰 컨테이너 수: {len(all_containers)}")
            
            return None
            
        except Exception as e:
            logger.error(f"리뷰 찾기 중 오류: {e}")
            return None
    
    async def expand_review_content(self, review_element):
        """리뷰의 "더보기" 버튼을 클릭하여 전체 내용 표시"""
        try:
            # 더보기 버튼 선택자 (사용자 제공 HTML 기준)
            expand_button_selectors = [
                "a.pui__wFzIYl[aria-expanded='false'][data-pui-click-code='text']",  # 정확한 선택자
                "a.pui__wFzIYl:has-text('더보기')",                                  # 클래스 + 텍스트
                "a[data-pui-click-code='text']:has-text('더보기')",                  # 데이터 속성 + 텍스트
                "a:has-text('더보기')",                                               # 텍스트만
                "button:has-text('더보기')"                                          # 버튼 타입
            ]
            
            for selector in expand_button_selectors:
                try:
                    expand_button = await review_element.query_selector(selector)
                    if expand_button:
                        # 버튼이 실제로 보이는지 확인
                        is_visible = await expand_button.is_visible()
                        if is_visible:
                            logger.info(f"📖 '더보기' 버튼 클릭: {selector}")
                            await expand_button.click()
                            await asyncio.sleep(1)  # 내용 로딩 대기
                            return True
                except:
                    continue
            
            return False  # 더보기 버튼이 없음 (전체 내용이 이미 표시됨)
            
        except Exception as e:
            logger.warning(f"리뷰 내용 확장 중 오류: {e}")
            return False
    
    async def analyze_review_content(self, review_element):
        """리뷰 내용 분석 (텍스트, 사진, 키워드 등)"""
        try:
            content_info = {
                'has_text': False,
                'has_photos': False,
                'has_keywords': False,
                'has_receipt': False,
                'text_content': '',
                'photo_count': 0,
                'keyword_count': 0
            }
            
            # 먼저 더보기 버튼 클릭 시도
            await self.expand_review_content(review_element)
            
            # 텍스트 리뷰 확인 (다양한 상황 처리)
            text_selectors = [
                "div.pui__vn15t2 a.pui__xtsQN-",                          # 정확한 텍스트 선택자 (사용자 제공)
                "a.pui__xtsQN-[data-pui-click-code='text']",             # 데이터 속성 기반 (사용자 제공)
                "a[role='button'][data-pui-click-code='text']",          # role + 데이터 속성 (사용자 제공) 
                "a[role='button'].pui__xtsQN-",                          # role + 클래스 기반
                ".pui__vn15t2 a",                                         # 컨테이너 내 링크
                ".pui__vn15t2",                                           # 텍스트 컨테이너 직접
                "div:has(.pui__xtsQN-)"                                   # 텍스트 포함 div
            ]
            
            for selector in text_selectors:
                try:
                    text_element = await review_element.query_selector(selector)
                    if text_element:
                        text_content = await text_element.text_content()
                        if text_content and len(text_content.strip()) > 5:  # 짧은 텍스트도 허용
                            content_info['has_text'] = True
                            content_info['text_content'] = text_content.strip()
                            break
                except:
                    continue
            
            # 사진 확인 (사용자 제공 HTML 구조 반영)
            photo_selectors = [
                "div.Review_img_slide__H3Xlr img.Review_img__n9UPw",      # 정확한 사진 선택자 (사용자 제공)
                "div.Review_img_box__iZRS7 img",                          # 개별 사진 박스 (사용자 제공)
                "div.Review_img_slide__H3Xlr img",                        # 사진 슬라이드 컨테이너
                "img.Review_img__n9UPw",                                   # 리뷰 이미지 클래스 (사용자 제공)
                "img[alt='리뷰이미지']",                                     # alt 속성 기반 (사용자 제공)
                "div.Review_img_slide__H3Xlr",                            # 사진 컨테이너만 확인
                ".Review_img_box__iZRS7"                                  # 사진 박스 컨테이너
            ]
            
            for selector in photo_selectors:
                try:
                    if selector.endswith('img'):  # 이미지 태그를 직접 찾는 경우
                        photos = await review_element.query_selector_all(selector)
                        if photos:
                            content_info['has_photos'] = True
                            content_info['photo_count'] = len(photos)
                            break
                    else:  # 컨테이너를 찾는 경우
                        photo_container = await review_element.query_selector(selector)
                        if photo_container:
                            # 컨테이너 내에서 실제 이미지 찾기
                            inner_photos = await photo_container.query_selector_all("img")
                            if inner_photos:
                                content_info['has_photos'] = True
                                content_info['photo_count'] = len(inner_photos)
                                break
                except:
                    continue
            
            # 추천 키워드 확인 (사용자 제공 HTML 구조 반영)
            keyword_selectors = [
                "div.pui__HLNvmI span.pui__jhpEyP",                      # 정확한 키워드 컨테이너 (사용자 제공)
                "span.pui__jhpEyP",                                      # 개별 키워드 (사용자 제공)
                "div.pui__HLNvmI span:has(img)",                        # 이모지가 있는 키워드
                "span:has-text('음식이 맛있어요')",                        # 특정 키워드 예시
                "span:has-text('고기 질이 좋아요')",                       # 사용자 제공 예시
                "span:has-text('특별한 메뉴가 있어요')",                   # 사용자 제공 예시
                "span:has-text('단체모임 하기 좋아요')",                   # 사용자 제공 예시
                "span:has-text('친절해요')",                             # 사용자 제공 예시
                "[class*='keyword']",                                    # 키워드 관련 클래스
                "div.pui__HLNvmI"                                        # 키워드 컨테이너 전체
            ]
            
            # 키워드 더보기 버튼 먼저 클릭 시도 (사용자 제공 정보)
            try:
                more_keywords_button = await review_element.query_selector("a.pui__jhpEyP.pui__ggzZJ8[data-pui-click-code='rv.keywordmore']")
                if not more_keywords_button:
                    more_keywords_button = await review_element.query_selector("a:has-text('+')")
                
                if more_keywords_button and await more_keywords_button.is_visible():
                    await more_keywords_button.click()
                    await asyncio.sleep(1)  # 키워드 로딩 대기
            except:
                pass
            
            for selector in keyword_selectors:
                try:
                    if selector == "div.pui__HLNvmI":  # 컨테이너 전체 확인
                        keyword_container = await review_element.query_selector(selector)
                        if keyword_container:
                            keywords = await keyword_container.query_selector_all("span.pui__jhpEyP")
                    else:
                        keywords = await review_element.query_selector_all(selector)
                    
                    visible_keywords = []
                    if keywords:
                        for keyword in keywords:
                            try:
                                if await keyword.is_visible():
                                    keyword_text = await keyword.text_content()
                                    if keyword_text and not keyword_text.startswith('+') and len(keyword_text.strip()) > 2:
                                        visible_keywords.append(keyword_text.strip())
                            except:
                                continue
                    
                    if visible_keywords:
                        content_info['has_keywords'] = True
                        content_info['keyword_count'] = len(visible_keywords)
                        break
                except:
                    continue
            
            # 영수증 첨부 확인 (사용자 제공 HTML 구조 반영)
            receipt_selectors = [
                "span.pui__m7nkds.pui__lHDwSH:has-text('영수증')",        # 정확한 영수증 표시 (사용자 제공)
                "span.pui__m7nkds:has-text('영수증')",                   # 클래스 기반
                "span:has-text('영수증')",                                # 영수증 텍스트 (사용자 제공)
                "a.pui__oQ0qP9[data-pui-click-code='rv.paymentinfo']",  # 정확한 결제 정보 링크 (사용자 제공)
                "[data-pui-click-code='rv.paymentinfo']",               # 데이터 속성 기반
                "a:has-text('결제 정보 상세 보기')"                        # 링크 텍스트 기반
            ]
            
            for selector in receipt_selectors:
                try:
                    receipt_element = await review_element.query_selector(selector)
                    if receipt_element:
                        content_info['has_receipt'] = True
                        break
                except:
                    continue
            
            # 로깅
            content_types = []
            if content_info['has_text']:
                content_types.append(f"텍스트({len(content_info['text_content'])}자)")
            if content_info['has_photos']:
                content_types.append(f"사진({content_info['photo_count']}장)")
            if content_info['has_keywords']:
                content_types.append(f"키워드({content_info['keyword_count']}개)")
            if content_info['has_receipt']:
                content_types.append("영수증")
                
            if content_types:
                logger.info(f"📝 리뷰 내용 분석: {', '.join(content_types)}")
            else:
                logger.warning("❓ 리뷰 내용을 분석할 수 없음")
            
            return content_info
            
        except Exception as e:
            logger.error(f"리뷰 내용 분석 중 오류: {e}")
            return None
    
    async def setup_date_filter(self, page):
        """7일 날짜 필터 설정"""
        try:
            logger.info("📅 날짜 필터를 7일로 설정 중...")
            
            # 날짜 필터 드롭박스 클릭
            filter_button_selectors = [
                "button[data-area-code='rv.calendarfilter']",
                "button.ButtonSelector_btn_select__BcLKR",
                "button:has-text('전체')",
                ".ButtonSelector_btn_select__BcLKR"
            ]
            
            filter_button = None
            for selector in filter_button_selectors:
                try:
                    filter_button = await page.wait_for_selector(selector, timeout=5000)
                    if filter_button:
                        logger.info(f"✅ 날짜 필터 버튼 발견: {selector}")
                        break
                except:
                    continue
            
            if not filter_button:
                logger.warning("❌ 날짜 필터 버튼을 찾을 수 없음 - 기본 필터 사용")
                return False
            
            # 드롭박스 클릭
            await filter_button.click()
            logger.info("날짜 필터 드롭박스 열림")
            await asyncio.sleep(1)
            
            # 7일 옵션 선택
            week_option_selectors = [
                "a[data-area-code='rv.calendarweek']",
                "a.ButtonSelector_btn__Tu3Nm:has-text('7일')",
                "li a:has-text('7일')",
                "a:has-text('7일')"
            ]
            
            week_option = None
            for selector in week_option_selectors:
                try:
                    week_option = await page.wait_for_selector(selector, timeout=5000)
                    if week_option:
                        logger.info(f"✅ 7일 옵션 발견: {selector}")
                        break
                except:
                    continue
            
            if not week_option:
                logger.warning("❌ 7일 옵션을 찾을 수 없음")
                return False
            
            # 7일 옵션 클릭
            await week_option.click()
            logger.info("✅ 날짜 필터가 7일로 설정됨")
            await asyncio.sleep(2)  # 필터 적용 대기
            
            return True
            
        except Exception as e:
            logger.error(f"날짜 필터 설정 중 오류: {e}")
            return False
    
    async def post_reply_optimized(self, page, task: ReplyTask, refresh_page: bool = True) -> bool:
        """최적화된 답글 등록 (페이지 새로고침 최소화)"""
        try:
            logger.info(f"답글 등록 시작: {task.reviewer_name}")
            
            # 페이지 새로고침이 필요한 경우에만
            if refresh_page:
                review_url = f"https://new.smartplace.naver.com/bizes/place/{task.platform_store_code}/reviews"
                logger.info(f"📍 페이지 이동: {review_url}")
                await page.goto(review_url, wait_until="networkidle", timeout=30000)
                await self.setup_date_filter(page)
            
            # 리뷰 찾기 및 내용 분석 (네이버 리뷰 ID 사용)
            review_element = await self.find_review_by_id(page, task.naver_review_id)
            if not review_element:
                logger.warning(f"❌ 리뷰를 찾을 수 없습니다: {task.reviewer_name}")
                await self.update_reply_status(task.review_id, success=False, error_message="리뷰를 찾을 수 없음")
                self.stats["failed"] += 1
                return False
            
            # 리뷰 내용 분석 (다양한 형태 처리)
            content_info = await self.analyze_review_content(review_element)
            if content_info:
                logger.info(f"📋 {task.reviewer_name} 리뷰 분석 완료")
            else:
                logger.warning(f"⚠️ {task.reviewer_name} 리뷰 내용 분석 실패 - 계속 진행")
            
            # 답글 버튼 찾기 및 클릭 (사용자 제공 HTML 기준)
            reply_button_selectors = [
                "button[data-area-code='rv.replywrite']",                    # 정확한 데이터 속성 (최우선)
                "button.Review_btn__Lu4nI.Review_btn_write__pFgSj",          # 정확한 클래스 조합
                "div.Review_btn_group__mDkTf button[data-area-code='rv.replywrite']", # 그룹 내 버튼
                "button.Review_btn_write__pFgSj",                            # 답글 쓰기 버튼 클래스
                "button:has(.fn.fn-write2)",                                 # 아이콘 기반
                "button:has-text('답글 쓰기')"                                 # 텍스트 기반
            ]
            
            reply_button = None
            for selector in reply_button_selectors:
                try:
                    reply_button = await review_element.query_selector(selector)
                    if reply_button:
                        logger.info(f"✅ 답글 버튼 발견: {selector}")
                        break
                except:
                    continue
            
            if not reply_button:
                # 기존 답글이 있는지 확인 (사용자 제공 HTML 기준)
                existing_reply_selectors = [
                    "a[data-pui-click-code='rv.replyedit']",                     # 정확한 답글 수정 링크 (최우선)
                    "a.pui__4Gicix[data-pui-click-code='rv.replyedit']",       # 정확한 클래스 + 데이터 속성
                    "a:has-text('수정')",                                        # 수정 텍스트 기반
                    "[data-pui-click-code='rv.replyedit']",                     # 데이터 속성만
                    "button[data-area-code='rv.replyeditedit']",                # 답글 수정 버튼 (수정 모드)
                    ".pui__xtsQN-[data-pui-click-code='rv.replyfold']"         # 답글 내용 표시 영역
                ]
                
                for selector in existing_reply_selectors:
                    try:
                        existing_reply = await review_element.query_selector(selector)
                        if existing_reply:
                            logger.info(f"ℹ️ 이미 답글이 존재합니다: {task.reviewer_name}")
                            self.stats["skipped"] += 1
                            return False
                    except:
                        continue
                
                logger.warning(f"❌ 답글 버튼을 찾을 수 없습니다: {task.reviewer_name}")
                await self.update_reply_status(task.review_id, success=False, error_message="답글 버튼을 찾을 수 없음")
                self.stats["failed"] += 1
                return False
            
            # 답글 버튼 클릭
            await reply_button.click()
            logger.info("답글 작성 폼 열림")
            await asyncio.sleep(2)
            
            # 답글 입력 필드 찾기 (사용자 제공 HTML 기준)
            reply_input_selectors = [
                "textarea#replyWrite",                                       # 정확한 ID (최우선)
                "textarea[id='replyWrite']",                                 # ID 속성 기반
                "div.Review_textarea_box__gTAoe textarea",                   # 컨테이너 내 textarea
                "textarea[placeholder*='리뷰 작성자와 리뷰를 보는']",              # placeholder 기반
                "textarea[placeholder*='욕설, 비방']",                        # placeholder 일부
                "textarea[data-area-code='rv.replycontent']",               # 기존 데이터 속성
                "textarea[name='content']"                                   # name 속성
            ]
            
            reply_input = None
            for selector in reply_input_selectors:
                try:
                    reply_input = await page.wait_for_selector(selector, timeout=5000)
                    if reply_input:
                        logger.info(f"✅ 답글 입력 필드 발견: {selector}")
                        break
                except:
                    continue
            
            if not reply_input:
                logger.warning(f"❌ 답글 입력 필드를 찾을 수 없습니다: {task.reviewer_name}")
                await self.update_reply_status(task.review_id, success=False, error_message="답글 입력 필드를 찾을 수 없음")
                self.stats["failed"] += 1
                return False
            
            # 브랜딩 키워드가 있으면 답글에 적용
            final_reply = self._apply_branding_keywords(task.ai_generated_reply, task.branding_keywords)
            
            # 답글 내용 입력
            await reply_input.fill("")
            await reply_input.fill(final_reply)
            logger.info(f"답글 내용 입력 완료: {final_reply[:50]}...")
            await asyncio.sleep(1)
            
            # 등록 버튼 찾기 및 클릭 (사용자 제공 HTML 기준)
            submit_selectors = [
                "button[data-area-code='rv.replydone']",                     # 정확한 데이터 속성 (최우선)
                "button.Review_btn__Lu4nI.Review_btn_enter__az8i7",          # 정확한 클래스 조합
                "button.Review_btn_enter__az8i7",                            # 등록 버튼 클래스
                "button:has-text('등록')",                                     # 텍스트 기반
                "button[data-area-code='rv.replyregist']",                   # 기존 데이터 속성
                "button[type='submit']"                                      # submit 타입
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await page.wait_for_selector(selector, timeout=5000)
                    if submit_button:
                        logger.info(f"✅ 등록 버튼 발견: {selector}")
                        break
                except:
                    continue
            
            if not submit_button:
                logger.warning(f"❌ 등록 버튼을 찾을 수 없습니다: {task.reviewer_name}")
                await self.update_reply_status(task.review_id, success=False, error_message="등록 버튼을 찾을 수 없음")
                self.stats["failed"] += 1
                return False
            
            # 등록 버튼 클릭
            await submit_button.click()
            logger.info("답글 등록 버튼 클릭")
            await asyncio.sleep(3)
            
            # 성공 확인 (새로고침 없이)
            success_selectors = [
                ".success_message",
                ".alert-success",
                "div:has-text('등록되었습니다')",
                "div:has-text('답글이 등록')"
            ]
            
            registration_success = False
            for selector in success_selectors:
                try:
                    success_element = await page.wait_for_selector(selector, timeout=3000)
                    if success_element:
                        logger.info(f"✅ 등록 성공 메시지 확인: {selector}")
                        registration_success = True
                        break
                except:
                    continue
            
            # 성공 메시지가 없어도 오류 메시지가 없으면 성공으로 간주
            if not registration_success:
                error_selectors = [
                    ".error_message",
                    ".alert-error",
                    "div:has-text('오류')",
                    "div:has-text('실패')"
                ]
                
                has_error = False
                for selector in error_selectors:
                    try:
                        error_element = await page.wait_for_selector(selector, timeout=2000)
                        if error_element:
                            error_text = await error_element.text_content()
                            logger.error(f"❌ 등록 오류: {error_text}")
                            await self.update_reply_status(task.review_id, success=False, error_message=error_text)
                            self.stats["failed"] += 1
                            return False
                    except:
                        continue
                
                # 오류 메시지도 없으면 성공으로 간주
                registration_success = True
            
            if registration_success:
                logger.info(f"✅ 답글 등록 완료: {task.reviewer_name}")
                await self.update_reply_status(task.review_id, success=True)
                self.stats["success"] += 1
                return True
            else:
                logger.error(f"❌ 답글 등록 상태를 확인할 수 없음: {task.reviewer_name}")
                await self.update_reply_status(task.review_id, success=False, error_message="등록 상태 확인 불가")
                self.stats["failed"] += 1
                return False
                
        except Exception as e:
            logger.error(f"답글 등록 중 오류: {e}")
            self.stats["errors"].append(str(e))
            self.stats["failed"] += 1
            return False
    
    async def update_reply_status(self, review_id: str, success: bool, error_message: str = None):
        """Supabase에 답글 전송 상태 업데이트"""
        try:
            current_time = datetime.now().isoformat()
            
            if success:
                update_data = {
                    'reply_sent_at': current_time,
                    'reply_status': 'sent',  # approved가 아닌 sent로 변경
                    'updated_at': current_time
                }
                logger.info(f"✅ DB 업데이트: 리뷰 {review_id} 답글 등록 완료 (status: sent)")
            else:
                # 실패 시 retry_count 증가
                # 먼저 현재 retry_count 조회
                current_review = self.supabase.table('reviews_naver').select('retry_count').eq('id', review_id).execute()
                current_retry_count = current_review.data[0]['retry_count'] if current_review.data else 0
                
                update_data = {
                    'reply_status': 'failed',
                    'reply_failed_at': current_time,  # 실패 시간 기록
                    'failure_reason': error_message or '알 수 없는 오류',  # 실패 이유 저장
                    'retry_count': current_retry_count + 1,  # 재시도 횟수 증가
                    'updated_at': current_time
                }
                logger.warning(f"❌ DB 업데이트: 리뷰 {review_id} 답글 등록 실패 - {error_message or '알 수 없는 오류'}")
            
            result = self.supabase.table('reviews_naver').update(
                update_data
            ).eq('id', review_id).execute()
            
            if result.data:
                status_text = "sent" if success else "failed"
                logger.info(f"✅ DB 업데이트 성공: {review_id} - reply_status를 '{status_text}'로 변경")
            else:
                logger.error(f"DB 업데이트 실패: 응답 데이터 없음 - {review_id}")
            
        except Exception as e:
            logger.error(f"상태 업데이트 실패: {e}")
            self.stats["errors"].append(f"DB 업데이트 실패: {str(e)}")
    
    async def process_replies(self, limit: int = 10, dry_run: bool = False):
        """
        답글 등록 프로세스 실행
        
        Args:
            limit: 처리할 최대 답글 수
            dry_run: True면 실제 등록하지 않고 시뮬레이션만
        """
        # 대기 중인 답글 가져오기
        tasks = await self.fetch_pending_replies(limit)
        
        if not tasks:
            logger.info("처리할 답글이 없습니다.")
            return
        
        if dry_run:
            logger.info("🔍 DRY RUN 모드 - 실제 등록하지 않습니다.")
            for task in tasks:
                logger.info(f"  - {task.reviewer_name}: {task.ai_generated_reply[:50]}...")
            return
        
        # 계정별로 그룹화
        tasks_by_account: Dict[str, List[ReplyTask]] = {}
        for task in tasks:
            if task.platform_id not in tasks_by_account:
                tasks_by_account[task.platform_id] = []
            tasks_by_account[task.platform_id].append(task)
        
        # 각 계정별로 처리
        for platform_id, account_tasks in tasks_by_account.items():
            logger.info(f"\n🔄 계정 처리 시작: {platform_id} ({len(account_tasks)}개 답글)")
            
            first_task = account_tasks[0]
            
            # NaverAutoLogin을 사용한 고급 로그인
            login_result = await self.login_with_naver_auto_login(
                first_task.platform_id, 
                first_task.platform_password
            )
            
            if not login_result['success']:
                logger.error(f"로그인 실패로 계정 {platform_id}의 작업을 건너뜁니다.")
                logger.error(f"오류: {login_result.get('error', '알 수 없는 오류')}")
                continue
            
            # 로그인된 브라우저와 페이지 가져오기
            browser = login_result.get('browser')
            page = login_result.get('page')
            
            if not browser or not page:
                logger.error(f"브라우저 세션을 가져올 수 없습니다: {platform_id}")
                continue
            
            try:
                logger.info(f"✅ 로그인된 브라우저 세션 확보 - 답글 등록 시작")
                
                # 스토어별로 그룹화하여 연속 처리
                tasks_by_store = {}
                for task in account_tasks:
                    if task.platform_store_code not in tasks_by_store:
                        tasks_by_store[task.platform_store_code] = []
                    tasks_by_store[task.platform_store_code].append(task)
                
                # 각 스토어별로 연속 처리
                for store_code, store_tasks in tasks_by_store.items():
                    logger.info(f"\n🏪 스토어 {store_code} 처리 시작 ({len(store_tasks)}개 답글)")
                    
                    # 첫 번째 답글로 페이지 접근
                    first_task = store_tasks[0]
                    review_url = f"https://new.smartplace.naver.com/bizes/place/{store_code}/reviews"
                    
                    logger.info(f"📍 페이지 이동: {review_url}")
                    await page.goto(review_url, wait_until="networkidle", timeout=30000)
                    await self.setup_date_filter(page)
                    
                    # 동일 페이지에서 연속 답글 처리
                    for i, task in enumerate(store_tasks):
                        logger.info(f"\n📝 [{i+1}/{len(store_tasks)}] 답글 처리: {task.reviewer_name}")
                        
                        # 페이지 새로고침 없이 답글 처리
                        success = await self.post_reply_optimized(page, task, refresh_page=False)
                        
                        # 마지막 답글이 아니면 짧은 딜레이만
                        if i < len(store_tasks) - 1:
                            await asyncio.sleep(2)
                        else:
                            await asyncio.sleep(3)  # 스토어 간 전환 시 조금 더 대기
                
            except Exception as e:
                logger.error(f"답글 처리 중 오류: {e}")
            finally:
                # 브라우저 정리
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass
                
                # Playwright 정리
                playwright = login_result.get('playwright')
                if playwright:
                    try:
                        await playwright.stop()
                    except:
                        pass
        
        # 통계 출력
        self.print_stats()
    
    def print_stats(self):
        """처리 통계 출력"""
        logger.info("\n" + "="*50)
        logger.info("📊 처리 결과 통계")
        logger.info("="*50)
        logger.info(f"총 가져온 답글: {self.stats['total_fetched']}개")
        logger.info(f"✅ 성공: {self.stats['success']}개")
        logger.info(f"❌ 실패: {self.stats['failed']}개")
        logger.info(f"⏭️ 건너뜀: {self.stats['skipped']}개")
        
        if self.stats['errors']:
            logger.info(f"\n오류 목록:")
            for error in self.stats['errors'][:5]:  # 최대 5개만 표시
                logger.info(f"  - {error}")
        
        logger.info("="*50)


async def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='네이버 답글 자동 등록')
    parser.add_argument('--limit', type=int, default=10, help='처리할 최대 답글 수')
    parser.add_argument('--dry-run', action='store_true', help='실제 등록하지 않고 시뮬레이션')
    
    args = parser.parse_args()
    
    try:
        poster = NaverReplyPoster()
        await poster.process_replies(limit=args.limit, dry_run=args.dry_run)
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())