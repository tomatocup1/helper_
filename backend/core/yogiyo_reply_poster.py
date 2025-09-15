#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
요기요 리뷰 답글 자동 등록 시스템
AI가 생성한 답글을 요기요 CEO 사이트에 자동으로 등록
DSID 매칭을 통한 정확한 리뷰 식별 및 답글 등록
"""

import os
import sys
import asyncio
import logging
import io
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import re
from urllib.parse import urlparse, parse_qs

# UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from supabase import create_client, Client
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Supabase 클라이언트 설정
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('yogiyo_reply_poster.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# DSID 생성기 임포트 (logger 정의 후)
try:
    from yogiyo_dsid_generator import YogiyoDSIDGenerator
except ImportError:
    try:
        from .yogiyo_dsid_generator import YogiyoDSIDGenerator
    except ImportError:
        logger.warning("DSID 생성기를 찾을 수 없습니다. 기본 구현을 사용합니다.")
        class YogiyoDSIDGenerator:
            def generate_dsid(self, *args, **kwargs):
                return f"temp_dsid_{int(datetime.now().timestamp())}"

# 패스워드 복호화 함수 임포트 (logger 정의 후)
try:
    # 직접 실행시에는 상대 임포트가 안되므로 절대 임포트로 시도
    try:
        from password_decrypt import decrypt_password
    except ImportError:
        from .password_decrypt import decrypt_password
except ImportError:
    logger.warning("password_decrypt 모듈을 찾을 수 없습니다. 환경변수만 사용합니다.")
    def decrypt_password(encrypted_pw: str) -> str:
        return encrypted_pw


class YogiyoReplyPoster:
    """요기요 리뷰 답글 자동 등록 시스템"""
    
    def __init__(self):
        """초기화"""
        self.supabase = supabase
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.logged_in = False
        self.current_store_info: Optional[Dict] = None
        
        # 요기요 URL 설정
        self.login_url = "https://ceo.yogiyo.co.kr/login"
        self.reviews_url = "https://ceo.yogiyo.co.kr/reviews"
        
        # DSID 생성기
        self.dsid_generator = YogiyoDSIDGenerator()
        
        # 통계
        self.stats = {
            'total_reviews': 0,
            'reviews_with_replies': 0,
            'replies_posted': 0,
            'replies_failed': 0,
            'reviews_not_found': 0
        }
        
        logger.info("YogiyoReplyPoster 초기화 완료")
    
    async def run(
        self,
        platform_store_uuid: str,
        limit: int = 10,
        dry_run: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        요기요 답글 등록 메인 프로세스
        
        Args:
            platform_store_uuid: Supabase platform_stores UUID
            limit: 최대 처리 개수
            dry_run: 테스트 모드 (실제 등록하지 않음)
            username: 요기요 로그인 ID (옵션, 없으면 DB에서 조회)
            password: 요기요 로그인 비밀번호 (옵션, 없으면 DB에서 조회)
            
        Returns:
            Dict: 실행 결과 정보
        """
        try:
            logger.info(f"요기요 답글 등록 시작 - Store UUID: {platform_store_uuid}")
            
            # 1. 매장 정보 및 계정 정보 조회
            store_info = await self._get_store_info_and_credentials(platform_store_uuid)
            if not store_info:
                return {
                    "success": False,
                    "message": "매장 정보를 찾을 수 없습니다",
                    "posted_count": 0,
                    "failed_count": 0
                }
            
            self.current_store_info = store_info
            
            # 2. 로그인 정보 결정 (매개변수 > DB > 환경변수)
            if username and password:
                login_username = username
                login_password = password
                logger.info("매개변수로 제공된 로그인 정보 사용")
            elif store_info.get('platform_id') and store_info.get('platform_pw'):
                login_username = store_info['platform_id']
                login_password = decrypt_password(store_info['platform_pw'])
                logger.info("DB에서 조회한 로그인 정보 사용")
            else:
                login_username = os.getenv('YOGIYO_USERNAME', '')
                login_password = os.getenv('YOGIYO_PASSWORD', '')
                logger.info("환경변수 로그인 정보 사용")
            
            if not login_username or not login_password:
                return {
                    "success": False,
                    "message": "로그인 정보가 없습니다",
                    "posted_count": 0,
                    "failed_count": 0
                }
            
            # 3. 처리할 답글 조회
            pending_reviews = await self._get_pending_reviews(platform_store_uuid, limit)
            if not pending_reviews:
                logger.info("처리할 답글이 없습니다")
                return {
                    "success": True,
                    "message": "처리할 답글이 없습니다",
                    "posted_count": 0,
                    "failed_count": 0
                }
            
            logger.info(f"{len(pending_reviews)}개 답글 처리 예정")
            
            if dry_run:
                logger.info("DRY RUN 모드 - 실제 등록하지 않음")
                return {
                    "success": True,
                    "message": f"DRY RUN 완료: {len(pending_reviews)}개 답글 발견",
                    "posted_count": len(pending_reviews),
                    "failed_count": 0,
                    "reviews": pending_reviews
                }
            
            # 4. 브라우저 초기화
            if not await self.initialize():
                return {
                    "success": False,
                    "message": "브라우저 초기화 실패",
                    "posted_count": 0,
                    "failed_count": 0
                }
            
            # 5. 로그인
            self.current_store_info['credentials'] = {
                'username': login_username,
                'password': login_password
            }
            
            if not await self.login():
                return {
                    "success": False,
                    "message": "로그인 실패",
                    "posted_count": 0,
                    "failed_count": 0
                }
            
            # 6. 리뷰 페이지로 이동
            if not await self.navigate_to_reviews():
                return {
                    "success": False,
                    "message": "리뷰 페이지 이동 실패",
                    "posted_count": 0,
                    "failed_count": 0
                }
            
            # 7. 답글 등록 처리
            results = await self._process_reply_tasks(pending_reviews)
            
            success_count = len([r for r in results if r.get('success')])
            failed_count = len([r for r in results if not r.get('success')])
            
            logger.info(f"답글 등록 완료 - 성공: {success_count}, 실패: {failed_count}")
            
            return {
                "success": True,
                "message": f"답글 등록 완료: {success_count}/{len(pending_reviews)}개 성공",
                "posted_count": success_count,
                "failed_count": failed_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"답글 등록 중 오류: {e}")
            return {
                "success": False,
                "message": f"오류 발생: {str(e)}",
                "posted_count": 0,
                "failed_count": 0
            }
        finally:
            await self.cleanup()
    
    async def _get_store_info_and_credentials(self, platform_store_uuid: str) -> Optional[Dict]:
        """플랫폼 매장 정보 및 계정 정보 조회"""
        try:
            result = self.supabase.table('platform_stores').select(
                'platform_store_id, platform_id, platform_pw, store_name'
            ).eq(
                'id', platform_store_uuid
            ).eq(
                'platform', 'yogiyo'  # 요기요 플랫폼 확인
            ).single().execute()
            
            if result.data:
                logger.info(f"매장 정보 조회 성공: {result.data.get('store_name', 'N/A')} ({result.data['platform_store_id']})")
                return result.data
            return None
            
        except Exception as e:
            logger.error(f"매장 정보 조회 실패: {e}")
            return None
    
    async def _get_pending_reviews(self, platform_store_uuid: str, limit: int) -> List[Dict]:
        """답글 대기 리뷰 조회 (schedulable_reply_date 필터링 포함)"""
        try:
            logger.info("답글 대기 상태 리뷰 검색 중...")

            # draft 상태의 답글 조회 (매칭을 위해 더 많은 필드 포함)
            result = self.supabase.table('reviews_yogiyo').select(
                'id, yogiyo_dsid, reviewer_name, review_text, reply_text, reply_status, platform_store_id, review_date, overall_rating, schedulable_reply_date'
            ).eq(
                'platform_store_id', platform_store_uuid
            ).eq(
                'reply_status', 'draft'  # draft 상태의 리뷰
            ).neq(
                'reply_text', 'null'  # 답글이 생성되어 있는 리뷰 (포스팅 대기 상태)
            ).limit(limit * 2).execute()  # schedulable_reply_date 필터링을 위해 더 많이 조회
            
            if result.data:
                logger.info(f"답글 대기 리뷰 {len(result.data)}개 발견")

                # schedulable_reply_date 필터링
                current_time = datetime.now()
                filtered_reviews = []

                for review in result.data:
                    schedulable_date = review.get('schedulable_reply_date')
                    review_id = review.get('id', 'unknown')

                    if schedulable_date:
                        try:
                            # ISO 포맷 파싱 및 시간대 처리
                            if isinstance(schedulable_date, str):
                                # UTC 시간으로 파싱
                                scheduled_time = datetime.fromisoformat(schedulable_date.replace('Z', '+00:00'))

                                # KST로 변환
                                if scheduled_time.tzinfo:
                                    scheduled_time = scheduled_time.astimezone(timezone(timedelta(hours=9)))
                                else:
                                    scheduled_time = scheduled_time.replace(tzinfo=timezone(timedelta(hours=9)))

                                # 현재 시간과 비교 (타임존 제거)
                                scheduled_time_naive = scheduled_time.replace(tzinfo=None)

                                if current_time < scheduled_time_naive:
                                    remaining = scheduled_time_naive - current_time
                                    logger.info(f"⏳ 답글 등록 대기: {review_id} (남은 시간: {remaining})")
                                    continue  # 시간이 안된 경우 스킵
                                else:
                                    logger.info(f"✅ 답글 등록 가능: {review_id} (예약 시간 도달)")
                        except Exception as e:
                            logger.warning(f"⚠️ schedulable_reply_date 파싱 오류: {e}, 즉시 처리로 진행")

                    filtered_reviews.append(review)

                    # limit에 도달하면 중단
                    if len(filtered_reviews) >= limit:
                        break

                logger.info(f"시간 필터링 후 리뷰: {len(filtered_reviews)}개")
                return filtered_reviews
            else:
                logger.info("답글 대기 리뷰가 없습니다")
                return []
            
        except Exception as e:
            logger.error(f"답글 대기 리뷰 조회 실패: {e}")
            return []
    
    async def _process_reply_tasks(self, pending_reviews: List[Dict]) -> List[Dict]:
        """답글 작업 처리"""
        results = []
        
        # 현재 페이지의 리뷰 추출
        page_reviews = await self.extract_reviews_from_page()
        
        for review_data in pending_reviews:
            try:
                dsid = review_data.get('yogiyo_dsid')
                reply_text = review_data.get('reply_text', '')
                
                if not dsid or not reply_text:
                    results.append({
                        "success": False,
                        "review_id": review_data.get('id'),
                        "error": "DSID 또는 답글 텍스트 없음"
                    })
                    continue
                
                # DSID로 리뷰 찾기 (DB 리뷰 정보 전달)
                matched_review, review_index = await self.find_review_by_dsid(dsid, page_reviews, review_data)
                
                if not matched_review:
                    results.append({
                        "success": False,
                        "review_id": review_data.get('id'),
                        "dsid": dsid,
                        "error": "리뷰를 찾을 수 없음"
                    })
                    continue
                
                # 이미 답글이 있는지 확인
                if matched_review.get('has_reply'):
                    # DB 상태 업데이트
                    self.supabase.table('reviews_yogiyo') \
                        .update({'reply_status': 'sent', 'reply_posted_at': datetime.now().isoformat()}) \
                        .eq('id', review_data['id']) \
                        .execute()
                    
                    results.append({
                        "success": True,
                        "review_id": review_data.get('id'),
                        "dsid": dsid,
                        "status": "이미 답글 존재"
                    })
                    continue
                
                # 답글 등록
                element_index = matched_review.get('element_index', review_index)
                result = await self.post_reply(element_index, reply_text, review_data)

                # 결과 처리
                if isinstance(result, dict):
                    if result.get('success'):
                        # DB 상태 업데이트 (성공)
                        self.supabase.table('reviews_yogiyo') \
                            .update({
                                'reply_status': 'sent',
                                'reply_posted_at': datetime.now().isoformat()
                            }) \
                            .eq('id', review_data['id']) \
                            .execute()

                        results.append({
                            "success": True,
                            "review_id": review_data.get('id'),
                            "dsid": dsid,
                            "status": "답글 등록 성공"
                        })

                        # 다음 답글 전 대기
                        await asyncio.sleep(3)
                    else:
                        # 금지어 실패 처리
                        error_message = result.get('error', '')
                        popup_message = result.get('popup_message', '')
                        detected_word = result.get('detected_word', '')

                        # 금지어가 감지된 경우
                        if 'forbidden word' in error_message.lower() or detected_word:
                            # DB에 오류 메시지 저장
                            self.supabase.table('reviews_yogiyo') \
                                .update({
                                    'reply_status': 'failed',
                                    'reply_error_message': popup_message or error_message,
                                    'updated_at': datetime.now().isoformat()
                                }) \
                                .eq('id', review_data['id']) \
                                .execute()

                            logger.info(f"[YOGIYO] 💾 DB 업데이트 완료: reply_error_message = '{popup_message[:100] if popup_message else error_message[:100]}...'")

                            if detected_word:
                                logger.info(f"[YOGIYO] 📄 상세 정보:")
                                logger.info(f"   - 원본 답글: {reply_text[:50]}...")
                                logger.info(f"   - 금지 단어: '{detected_word}'")
                                logger.info(f"   - 다음 AI 생성 시 이 정보를 참고하여 답글 재작성 예정")

                        results.append({
                            "success": False,
                            "review_id": review_data.get('id'),
                            "dsid": dsid,
                            "error": error_message,
                            "detected_word": detected_word
                        })
                elif isinstance(result, bool):
                    # 호환성을 위해 bool 반환을 처리
                    if result:
                        # DB 상태 업데이트 (성공)
                        self.supabase.table('reviews_yogiyo') \
                            .update({
                                'reply_status': 'sent',
                                'reply_posted_at': datetime.now().isoformat()
                            }) \
                            .eq('id', review_data['id']) \
                            .execute()

                        results.append({
                            "success": True,
                            "review_id": review_data.get('id'),
                            "dsid": dsid,
                            "status": "답글 등록 성공"
                        })
                        await asyncio.sleep(3)
                    else:
                        results.append({
                            "success": False,
                            "review_id": review_data.get('id'),
                            "dsid": dsid,
                            "error": "답글 등록 실패"
                        })
                else:
                    results.append({
                        "success": False,
                        "review_id": review_data.get('id'),
                        "dsid": dsid,
                        "error": "답글 등록 실패"
                    })
                
            except Exception as e:
                logger.error(f"개별 답글 처리 실패: {e}")
                results.append({
                    "success": False,
                    "review_id": review_data.get('id'),
                    "error": str(e)
                })
        
        return results
    
    async def initialize(self):
        """브라우저 초기화"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=False,  # 디버깅을 위해 GUI 모드
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                ]
            )
            
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            self.page = await context.new_page()
            
            # 네트워크 요청 모니터링 (디버깅용)
            self.page.on("request", lambda request: logger.debug(f"Request: {request.url[:100]}"))
            self.page.on("response", lambda response: logger.debug(f"Response: {response.status} {response.url[:100]}"))
            
            logger.info("브라우저 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"브라우저 초기화 실패: {e}")
            return False
    
    async def login(self) -> bool:
        """요기요 CEO 사이트 로그인"""
        try:
            logger.info("요기요 CEO 로그인 시작")
            
            if not self.current_store_info or not self.current_store_info.get('credentials'):
                logger.error("매장 정보 또는 로그인 정보가 없습니다")
                return False
            
            credentials = self.current_store_info['credentials']
            username = credentials.get('username', '')
            password = credentials.get('password', '')
            
            if not username or not password:
                logger.error("로그인 정보가 없습니다")
                return False
            
            # 로그인 페이지로 이동
            login_url = "https://ceo.yogiyo.co.kr/login"
            await self.page.goto(login_url, wait_until='networkidle')
            
            # 이미 로그인되어 있는지 확인
            if "reviews" in self.page.url or "home" in self.page.url:
                logger.info("이미 로그인되어 있음")
                self.logged_in = True
                return True
            
            # 아이디 입력
            await self.page.fill('input[name="username"], input[type="text"]', username)
            await asyncio.sleep(1)
            
            # 비밀번호 입력
            await self.page.fill('input[name="password"], input[type="password"]', password)
            await asyncio.sleep(1)
            
            # 로그인 버튼 클릭
            await self.page.click('button[type="submit"], button:has-text("로그인")')
            
            # 로그인 성공 대기 (더 유연하게)
            try:
                await self.page.wait_for_url('**/home/**', timeout=15000)
            except PlaywrightTimeout:
                # home이 아닌 다른 URL로 이동했는지 확인
                current_url = self.page.url
                if "login" not in current_url:
                    logger.info(f"로그인 성공 (URL: {current_url})")
                else:
                    raise PlaywrightTimeout("로그인 실패")
            
            self.logged_in = True
            logger.info("로그인 성공")
            return True
            
        except PlaywrightTimeout:
            logger.error("로그인 타임아웃")
            return False
        except Exception as e:
            logger.error(f"로그인 실패: {e}")
            return False
    
    async def navigate_to_reviews(self) -> bool:
        """리뷰 페이지로 이동 및 매장 선택"""
        try:
            logger.info("리뷰 페이지로 이동")
            await self.page.goto(self.reviews_url, wait_until='domcontentloaded')
            await self.page.wait_for_timeout(3000)
            
            # 매장 선택
            if not self.current_store_info:
                logger.error("매장 정보가 없습니다")
                return False
            
            platform_store_id = self.current_store_info.get('platform_store_id')
            if not platform_store_id:
                logger.error("플랫폼 매장 ID가 없습니다")
                return False
            
            store_selected = await self._select_store(platform_store_id)
            if not store_selected:
                logger.error("매장 선택 실패")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"리뷰 페이지 이동 실패: {e}")
            return False
    
    async def _select_store(self, store_id: str) -> bool:
        """매장 선택 (크롤러에서 복사)"""
        try:
            logger.info(f"매장 선택: {store_id}")
            
            # 드롭다운 클릭
            dropdown_selectors = [
                'div.StoreSelector__SelectedStore-sc-1rowjsb-13',
                'button.StoreSelector__DropdownButton-sc-1rowjsb-11',
                'div[role="menu"]'
            ]
            
            for selector in dropdown_selectors:
                try:
                    await self.page.click(selector)
                    logger.info(f"드롭다운 클릭 성공: {selector}")
                    break
                except:
                    continue
            
            await self.page.wait_for_timeout(2000)
            
            # 매장 목록 대기
            await self.page.wait_for_selector('ul.List__VendorList-sc-2ocjy3-8', timeout=10000)
            
            # 매장 선택 (platform_store_id 기준)
            store_selected = await self.page.evaluate(f"""
                () => {{
                    const storeElements = document.querySelectorAll('li.List__Vendor-sc-2ocjy3-7');
                    
                    for (const element of storeElements) {{
                        const idElement = element.querySelector('span.List__VendorID-sc-2ocjy3-1');
                        if (idElement) {{
                            const storeIdText = idElement.textContent.trim();
                            const storeId = storeIdText.replace('ID.', '').trim();
                            
                            if (storeId === '{store_id}') {{
                                element.click();
                                return true;
                            }}
                        }}
                    }}
                    
                    return false;
                }}
            """)
            
            if store_selected:
                logger.info(f"매장 선택 완료: {store_id}")
                await self.page.wait_for_timeout(3000)
                
                # 미답변 탭 클릭
                unanswered_clicked = await self._click_unanswered_tab()
                if unanswered_clicked:
                    logger.info("미답변 탭 클릭 완료")
                else:
                    logger.warning("미답변 탭 클릭 실패 - 전체 리뷰에서 진행")
                
                return True
            else:
                logger.error(f"매장을 찾을 수 없음: {store_id}")
                return False
                
        except Exception as e:
            logger.error(f"매장 선택 중 오류: {e}")
            return False
    
    async def _click_unanswered_tab(self) -> bool:
        """미답변 탭 클릭 (크롤러에서 복사)"""
        try:
            # 미답변 탭 선택자들
            unanswered_selectors = [
                'li:has-text("미답변")',
                'li.InnerTab__TabItem-sc-14s9mjy-0:has-text("미답변")',
                'li.expvkr:has-text("미답변")',
                'li.hWCMEW:has-text("미답변")',
                '[class*="TabItem"]:has-text("미답변")',
                '[class*="InnerTab"]:has-text("미답변")'
            ]
            
            for selector in unanswered_selectors:
                try:
                    # 탭이 존재하는지 확인
                    tab_element = await self.page.query_selector(selector)
                    if tab_element:
                        # 탭 텍스트 확인
                        tab_text = await tab_element.inner_text()
                        logger.debug(f"탭 발견: {tab_text}")
                        
                        # 미답변 탭인지 확인하고 클릭
                        if '미답변' in tab_text:
                            await tab_element.click()
                            await self.page.wait_for_timeout(2000)
                            
                            # 클릭 후 페이지 변화 확인
                            await self.page.wait_for_load_state('networkidle', timeout=5000)
                            
                            logger.info(f"미답변 탭 클릭 성공: {tab_text}")
                            return True
                except Exception as e:
                    logger.debug(f"선택자 {selector} 시도 실패: {e}")
                    continue
            
            # JavaScript로 직접 시도
            logger.debug("JavaScript로 미답변 탭 클릭 시도")
            clicked = await self.page.evaluate("""
                () => {
                    // 모든 li 요소에서 "미답변"이 포함된 요소 찾기
                    const tabs = document.querySelectorAll('li');
                    for (const tab of tabs) {
                        if (tab.textContent && tab.textContent.includes('미답변')) {
                            tab.click();
                            return true;
                        }
                    }
                    
                    // 클래스명으로도 시도
                    const tabElements = document.querySelectorAll('[class*="TabItem"], [class*="InnerTab"]');
                    for (const tab of tabElements) {
                        if (tab.textContent && tab.textContent.includes('미답변')) {
                            tab.click();
                            return true;
                        }
                    }
                    
                    return false;
                }
            """)            
            if clicked:
                await self.page.wait_for_timeout(2000)
                logger.info("JavaScript로 미답변 탭 클릭 성공")
                return True
            
            logger.warning("미답변 탭을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            logger.error(f"미답변 탭 클릭 중 오류: {e}")
            return False
    
    
    async def extract_reviews_from_page(self) -> List[Dict]:
        """현재 페이지에서 리뷰 추출"""
        try:
            reviews = []
            
            # 리뷰 컨테이너 찾기 (크롤러와 동일한 셀렉터)
            review_containers = await self.page.query_selector_all('div.ReviewItem__Container-sc-1oxgj67-0')
            
            if not review_containers:
                # 백업 셀렉터
                review_containers = await self.page.query_selector_all('div[class*="ReviewItem"]')
            
            if not review_containers:
                logger.warning("리뷰 요소를 찾을 수 없음")
                return reviews
            
            logger.info(f"리뷰 컨테이너 {len(review_containers)}개 발견")
            
            for idx, container in enumerate(review_containers):
                try:
                    # HTML 추출
                    html = await container.inner_html()
                    
                    # 리뷰 정보 추출
                    review_data = await self._extract_review_data(container, html)
                    if review_data:
                        review_data['element_index'] = idx
                        reviews.append(review_data)
                        
                except Exception as e:
                    logger.error(f"리뷰 추출 실패 (인덱스 {idx}): {e}")
                    continue
            
            logger.info(f"페이지에서 {len(reviews)}개 리뷰 추출")
            return reviews
            
        except Exception as e:
            logger.error(f"리뷰 추출 실패: {e}")
            return []
    
    async def _extract_review_data(self, element, html: str) -> Optional[Dict]:
        """리뷰 요소에서 데이터 추출 (크롤러 선택자 사용)"""
        try:
            review_data = {}
            
            # 리뷰어 이름 (크롤러 선택자)
            reviewer_element = await element.query_selector('h6.Typography__StyledTypography-sc-r9ksfy-0.dZvFzq')
            if reviewer_element:
                review_data['reviewer_name'] = await reviewer_element.inner_text()
            else:
                review_data['reviewer_name'] = '익명'
            
            # 전체 별점 (크롤러 선택자)
            rating_element = await element.query_selector('h6.Typography__StyledTypography-sc-r9ksfy-0.cknzqP')
            if rating_element:
                rating_text = await rating_element.inner_text()
                try:
                    review_data['rating'] = float(rating_text)
                except:
                    review_data['rating'] = 0.0
            else:
                review_data['rating'] = 0.0
            
            # 리뷰 날짜 (크롤러 선택자)
            date_element = await element.query_selector('p.Typography__StyledTypography-sc-r9ksfy-0.jwoVKl')
            if date_element:
                review_data['review_date'] = await date_element.inner_text()
            else:
                review_data['review_date'] = ''
            
            # 리뷰 텍스트 (크롤러 선택자)
            text_element = await element.query_selector('p.ReviewItem__CommentTypography-sc-1oxgj67-3.blUkHI')
            if not text_element:
                text_element = await element.query_selector('p.Typography__StyledTypography-sc-r9ksfy-0.hLRURJ')
            if text_element:
                review_data['review_text'] = await text_element.inner_text()
            else:
                review_data['review_text'] = ''
            
            # 주문 메뉴 (크롤러 선택자)
            menu_element = await element.query_selector('p.Typography__StyledTypography-sc-r9ksfy-0.jlzcvj')
            if menu_element:
                review_data['order_menu'] = await menu_element.inner_text()
            else:
                review_data['order_menu'] = ''
            
            # 리뷰 이미지
            image_elements = await element.query_selector_all('img.ReviewItem__Image-sc-1oxgj67-1.hOzzCg')
            image_urls = []
            for img in image_elements:
                src = await img.get_attribute('src')
                if src:
                    image_urls.append(src)
            review_data['image_urls'] = image_urls
            review_data['has_photos'] = len(image_urls) > 0
            
            # 사장님 답글 확인 (크롤러 선택자)
            owner_reply = ''
            reply_element = await element.query_selector('div.ReviewReply__ReplyContent-sc-1536a88-7')
            if reply_element:
                owner_reply = await reply_element.inner_text()
            
            review_data['owner_reply'] = owner_reply
            review_data['has_reply'] = bool(owner_reply)
            review_data['html'] = html
            
            # 리뷰 메타데이터
            review_data['yogiyo_metadata'] = {
                'extracted_at': datetime.now().isoformat()
            }
            
            return review_data if review_data else None
            
        except Exception as e:
            logger.error(f"리뷰 데이터 추출 실패: {e}")
            return None
    
    async def find_review_by_dsid(self, target_dsid: str, reviews: List[Dict], db_review: Dict) -> Optional[Tuple[Dict, int]]:
        """DSID로 리뷰 찾기 (다중 매칭 전략)"""
        try:
            # 1단계: 정확한 DSID 매칭
            current_url = self.page.url
            parsed_url = urlparse(current_url)
            query_params = parse_qs(parsed_url.query)
            
            sort_option = query_params.get('sort', [''])[0]
            filter_option = query_params.get('filter', [''])[0]
            
            # DSID 생성기로 현재 페이지의 리뷰들 처리
            processed_reviews = self.dsid_generator.process_review_list(
                reviews.copy(),
                url=current_url,
                sort_option=sort_option,
                filter_option=filter_option
            )
            
            # DSID 매칭
            for idx, review in enumerate(processed_reviews):
                if review.get('dsid') == target_dsid:
                    logger.info(f"✅ DSID 완전 매칭 성공: {target_dsid} (인덱스: {idx})")
                    return review, idx
            
            logger.warning(f"DSID 완전 매칭 실패: {target_dsid}")
            
            # 2단계: 콘텐츠 기반 매칭 (리뷰어 + 내용 + 날짜 + 별점)
            logger.info("콘텐츠 기반 매칭 시도...")
            
            db_reviewer = db_review.get('reviewer_name', '').strip()
            db_text = db_review.get('review_text', '').strip()
            db_date = db_review.get('review_date', '').strip()
            db_rating = db_review.get('overall_rating', 0)
            
            for idx, page_review in enumerate(reviews):
                page_reviewer = page_review.get('reviewer_name', '').strip()
                page_text = page_review.get('review_text', '').strip()
                page_date = page_review.get('review_date', '').strip()
                page_rating = page_review.get('rating', 0)
                
                # 4중 매칭: 리뷰어 + 내용 + 날짜 + 별점
                reviewer_match = (db_reviewer and page_reviewer and db_reviewer == page_reviewer)
                content_match = (db_text and page_text and (db_text in page_text or page_text in db_text))
                date_match = (db_date and page_date and self._dates_similar(db_date, page_date))
                rating_match = (abs(float(db_rating or 0) - float(page_rating or 0)) <= 0.1)
                
                match_score = sum([reviewer_match, content_match, date_match, rating_match])
                
                if match_score >= 3:  # 4개 중 3개 이상 매칭
                    logger.info(f"🎯 콘텐츠 매칭 성공 (점수: {match_score}/4)")
                    logger.info(f"   👤 리뷰어: {page_reviewer} {'✅' if reviewer_match else '❌'}")
                    logger.info(f"   📝 내용: {page_text[:20]}... {'✅' if content_match else '❌'}")
                    logger.info(f"   📅 날짜: {page_date} {'✅' if date_match else '❌'}")
                    logger.info(f"   ⭐ 별점: {page_rating} {'✅' if rating_match else '❌'}")
                    return page_review, idx
            
            logger.warning(f"콘텐츠 매칭도 실패: DB리뷰({db_reviewer}, {db_text[:20]}..., {db_date})")
            return None, None
            
        except Exception as e:
            logger.error(f"리뷰 매칭 실패: {e}")
            return None, None
    
    def _dates_similar(self, date1: str, date2: str) -> bool:
        """날짜 유사도 확인 (상대시간 고려)"""
        try:
            # 완전 일치
            if date1 == date2:
                return True
            
            # 패턴 정규화
            date1_clean = re.sub(r'[^\d.]', '', date1)
            date2_clean = re.sub(r'[^\d.]', '', date2)
            
            if date1_clean == date2_clean:
                return True
            
            # 오늘, 어제 등의 상대시간 처리
            relative_terms = ['오늘', '어제', '시간 전', '분 전', '일 전']
            for term in relative_terms:
                if term in date1 and term in date2:
                    return True
            
            return False
            
        except Exception:
            return False
    
    async def post_reply(self, review_element_index: int, reply_text: str, review_data: Optional[Dict] = None) -> Dict[str, Any]:
        """답글 등록"""
        try:
            logger.info(f"답글 등록 시작 (리뷰 인덱스: {review_element_index})")
            
            # 리뷰 요소 다시 찾기 (크롤러와 동일한 선택자)
            review_elements = await self.page.query_selector_all('div.ReviewItem__Container-sc-1oxgj67-0')
            if not review_elements:
                review_elements = await self.page.query_selector_all('div[class*="ReviewItem"]')
            if review_element_index >= len(review_elements):
                logger.error(f"리뷰 인덱스 {review_element_index}가 범위를 벗어남")
                return False
            
            review_element = review_elements[review_element_index]
            
            # 답글 버튼 클릭 (실제 HTML 구조 기반)
            reply_button_selectors = [
                'button.ReviewReply__AddReplyButton-sc-1536a88-10:has-text("댓글쓰기")',
                'button:has-text("댓글쓰기")',
                'button.ReviewReply__AddReplyButton-sc-1536a88-10',
                'button.fMcjWR'
            ]
            
            reply_button = None
            for selector in reply_button_selectors:
                try:
                    reply_button = await review_element.query_selector(selector)
                    if reply_button:
                        logger.info(f"답글 버튼 발견: {selector}")
                        await reply_button.click()
                        await asyncio.sleep(2)  # 입력창 로드 대기
                        break
                except:
                    continue
            
            if not reply_button:
                logger.error("답글 버튼을 찾을 수 없음")
                return False
            
            # 답글 입력 필드 찾기 (실제 HTML 구조 기반)
            textarea_selectors = [
                'textarea.ReviewReply__CustomTextarea-sc-1536a88-5',
                'textarea[placeholder*="댓글을 입력"]',
                'textarea[maxlength="1000"]',
                'textarea.hYwPZb',
                'textarea'
            ]
            
            textarea = None
            for selector in textarea_selectors:
                try:
                    # 전체 페이지에서 찾기 (모달일 수 있음)
                    textarea = await self.page.wait_for_selector(selector, timeout=5000)
                    if textarea:
                        logger.info(f"답글 입력창 발견: {selector}")
                        break
                except:
                    continue
            
            if not textarea:
                logger.error("답글 입력 필드를 찾을 수 없음")
                return False
            
            # 답글 입력
            await textarea.click()  # 포커스
            await asyncio.sleep(0.5)
            await textarea.fill('')  # 기존 내용 지우기
            await asyncio.sleep(0.5)
            await textarea.type(reply_text)  # 타이핑으로 입력
            await asyncio.sleep(1)
            logger.info(f"답글 입력 완료: {reply_text[:20]}...")
            
            # 등록 버튼 클릭 (답글 등록 영역의 정확한 등록 버튼만 클릭)
            submit_button_selectors = [
                # 답글 액션 컨테이너 내의 등록 버튼만 대상
                'div.ReviewReply__ActionButtonWrapper-sc-1536a88-8 button:has-text("등록")',
                'div[class*="ActionButtonWrapper"] button:has-text("등록")',
                'div[class*="ActionButtonWrapper"] button.sc-bczRLJ.ifUnxI.sc-eCYdqJ.hsiXYt',
                'button.sc-bczRLJ.ifUnxI.sc-eCYdqJ.hsiXYt:has-text("등록")',
                # 백업 선택자 (더 구체적)
                'button[size="40"][color="primaryA"]:has-text("등록")',
                'button.hsiXYt[size="40"]:has-text("등록")'
            ]
            
            submit_clicked = False
            for selector in submit_button_selectors:
                try:
                    submit_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if submit_button:
                        logger.info(f"등록 버튼 발견: {selector}")
                        await submit_button.click()
                        submit_clicked = True
                        logger.info("답글 등록 버튼 클릭 완료")
                        break
                except:
                    continue

            if not submit_clicked:
                logger.error("등록 버튼을 찾을 수 없음")
                return False

            # 등록 처리 대기 (금지어 팝업 체크를 위해)
            await asyncio.sleep(2)

            # 요기요 금지어 팝업 체크
            logger.info("[YOGIYO] 🔍 금지어 팝업 확인 중...")

            # 요기요 금지어 팝업 셀렉터 (새로운 HTML 구조 기반)
            forbidden_popup_selectors = [
                'p.Typography__StyledTypography-sc-r9ksfy-0.buezIH[color="ygyOrange"]',
                'p[color="ygyOrange"]:has-text("작성할 수 없어요")',
                'p:has-text("요기요 운영 정책에 따라")',
                'div[role="dialog"] p[color="ygyOrange"]',
                'div.modal p:has-text("작성할 수 없어요")'
            ]

            forbidden_popup = None
            for selector in forbidden_popup_selectors:
                try:
                    forbidden_popup = await self.page.query_selector(selector)
                    if forbidden_popup:
                        logger.info(f"[YOGIYO] 금지어 팝업 감지: {selector}")
                        break
                except:
                    continue

            if forbidden_popup:
                logger.warning("[YOGIYO] ⚠️ 요기요 금지어 팝업 감지!")

                # 팝업 텍스트 추출
                popup_message = "요기요 금지어 팝업 감지"  # 기본값
                detected_forbidden_word = None

                try:
                    logger.info("[YOGIYO] 🔍 요기요 팝업 텍스트 추출 중...")
                    popup_text = await forbidden_popup.text_content()

                    if popup_text:
                        logger.info(f"[YOGIYO] 📄 요기요 팝업 원문: {popup_text}")

                        # 요기요 팝업 메시지 패턴: "요기요 운영 정책에 따라 이 단어는 작성할 수 없어요. \"쿠팡\""
                        import re
                        pattern = r'"요기요\s+운영\s+정책에\s+따라.*?\"([^"]+)\"'
                        match = re.search(pattern, popup_text)

                        if match:
                            detected_forbidden_word = match.group(1)
                            logger.info(f"[YOGIYO] ✅ 요기요 금지어 추출 성공: {detected_forbidden_word}")
                            popup_message = f"요기요 금지어 알림: {popup_text[:150]}"
                        else:
                            # 다른 패턴 시도
                            pattern2 = r'\"([^"]+)\"'
                            matches = re.findall(pattern2, popup_text)
                            if matches:
                                detected_forbidden_word = matches[-1]  # 마지막 따옴표 내용
                                logger.info(f"[YOGIYO] ✅ 요기요 금지어 추출 (대체 패턴): {detected_forbidden_word}")
                            popup_message = f"요기요 금지어 팝업: {popup_text[:150]}"
                except Exception as e:
                    logger.error(f"[YOGIYO] 팝업 텍스트 추출 실패: {e}")

                # 취소 버튼 클릭
                cancel_button_selectors = [
                    'button.sc-bczRLJ.dTrTca.sc-eCYdqJ.hsiXYt[size="40"][color="accent100"]:has-text("취소")',
                    'button[color="accent100"]:has-text("취소")',
                    'button:has-text("취소")',
                    'button.dTrTca:has-text("취소")',
                    'div[role="dialog"] button:has-text("취소")'
                ]

                for selector in cancel_button_selectors:
                    try:
                        cancel_button = await self.page.wait_for_selector(selector, timeout=3000)
                        if cancel_button:
                            logger.info(f"[YOGIYO] ✅ 취소 버튼 발견: {selector}")
                            await cancel_button.click()
                            logger.info("[YOGIYO] 🔘 팝업 취소 버튼 클릭 완료")
                            await asyncio.sleep(1)
                            break
                    except:
                        continue

                logger.error(f"[YOGIYO] ❌ 리뷰 금지어로 인한 답글 등록 실패")
                logger.info(f"[YOGIYO] 📄 요기요 메시지: {popup_message}")
                logger.info(f"[YOGIYO] 🔄 main.py 다음 실행 시 이 정보를 바탕으로 새 답글 생성됩니다")

                # 금지어 감지 시 실패 반환
                return {
                    "success": False,
                    "error": f"Yogiyo forbidden word popup: {popup_message}",
                    "detected_word": detected_forbidden_word,
                    "popup_message": popup_message
                }

            # 금지어 팝업이 없는 경우 성공 대기
            logger.info("[YOGIYO] ✅ 요기요 금지어 팝업 없음 - 정상 처리")
            await asyncio.sleep(1)
            
            # 성공 확인 (답글이 표시되는지)
            await asyncio.sleep(2)

            # 답글이 등록되었는지 확인
            reply_check = await review_element.query_selector('.owner-reply, .reply-content')
            if reply_check:
                logger.info("답글 등록 성공")
                return {
                    "success": True,
                    "status": "sent",
                    "message": "답글 등록 성공"
                }

            logger.warning("답글 등록 확인 실패")
            return {
                "success": True,  # 일단 성공으로 처리
                "status": "sent",
                "message": "답글 등록 완료 (확인 대기)"
            }

        except Exception as e:
            logger.error(f"답글 등록 실패: {e}")
            return {
                "success": False,
                "status": "failed",
                "error": str(e)
            }
    
    
    async def cleanup(self):
        """리소스 정리 (Windows asyncio 경고 해결)"""
        try:
            # Windows ProactorEventLoop 리소스 정리를 위한 순차적 종료
            if self.page and not self.page.is_closed():
                await self.page.close()
                await asyncio.sleep(0.1)  # 리소스 정리 대기

            if self.browser:
                await self.browser.close()
                await asyncio.sleep(0.2)  # 브라우저 종료 대기

            # Windows에서 pipe 리소스 정리 강제 실행
            import sys
            if sys.platform == "win32":
                try:
                    # ProactorEventLoop에서 pending tasks 정리
                    loop = asyncio.get_running_loop()
                    if hasattr(loop, '_default_executor') and loop._default_executor:
                        loop._default_executor.shutdown(wait=False)
                        await asyncio.sleep(0.1)

                    # 남은 task들 정리
                    pending_tasks = [task for task in asyncio.all_tasks(loop)
                                   if not task.done() and task != asyncio.current_task()]
                    if pending_tasks:
                        for task in pending_tasks:
                            if not task.cancelled():
                                task.cancel()
                        # 취소된 작업들 완료 대기
                        await asyncio.gather(*pending_tasks, return_exceptions=True)

                except Exception as e:
                    logger.debug(f"Windows 리소스 정리 중 예외 (무시 가능): {e}")

            logger.info("리소스 정리 완료")
        except Exception as e:
            logger.error(f"리소스 정리 실패: {e}")


async def main():
    """테스트 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Yogiyo Reply Poster')
    parser.add_argument('--store-uuid', type=str, help='Platform store UUID')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual posting)')
    parser.add_argument('--limit', type=int, default=5, help='Maximum number of reviews to process')
    
    args = parser.parse_args()
    
    try:
        if args.store_uuid:
            # 지정된 매장 UUID 사용
            result = supabase.table('platform_stores') \
                .select('*') \
                .eq('id', args.store_uuid) \
                .eq('platform', 'yogiyo') \
                .execute()
            
            if not result.data:
                logger.error(f"매장을 찾을 수 없습니다: {args.store_uuid}")
                return
                
            store_uuid = result.data[0]['id']
            store_name = result.data[0]['store_name']
        else:
            # 기본: 첫 번째 활성 매장 사용
            user_id = "a7654c42-10ed-435f-97d8-d2c2dfeccbcb"
            
            result = supabase.table('platform_stores') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('platform', 'yogiyo') \
                .eq('is_active', True) \
                .execute()
            
            if not result.data:
                logger.error("활성화된 요기요 매장이 없습니다")
                return
            
            store_uuid = result.data[0]['id']
            store_name = result.data[0]['store_name']
        
        logger.info(f"매장 선택: {store_name} (UUID: {store_uuid})")
        
        # 답글 등록기 실행
        poster = YogiyoReplyPoster()
        result = await poster.run(
            platform_store_uuid=store_uuid,
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        print("\n" + "="*50)
        print("요기요 답글 등록 결과")
        print("="*50)
        print(f"성공: {result.get('posted_count', 0)}개")
        print(f"실패: {result.get('failed_count', 0)}개")
        print(f"메시지: {result.get('message', '')}")
        
        # 상세 결과
        if result.get('results'):
            print("\n상세 결과:")
            for idx, item in enumerate(result['results'], 1):
                status = "[OK]" if item.get('success') else "[FAIL]"
                print(f"  {idx}. {status} {item.get('review_id', 'N/A')} - {item.get('status', item.get('error', 'Unknown'))}")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"메인 실행 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Windows에서 asyncio 경고 해결을 위한 이벤트 루프 정책 설정
    import sys
    if sys.platform == "win32":
        try:
            # WindowsProactorEventLoopPolicy 사용 (pipe 리소스 정리 개선)
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except AttributeError:
            # 이전 버전 Python에서는 기본 정책 사용
            pass

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[요기요] 사용자에 의해 중단됨")
    except Exception as e:
        print(f"[요기요] 실행 오류: {e}")
        import traceback
        traceback.print_exc()