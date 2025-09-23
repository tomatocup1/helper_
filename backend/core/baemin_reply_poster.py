#!/usr/bin/env python3
"""
배달의민족 답글 자동 등록 시스템
- AI 생성 답글을 배민 리뷰에 자동 등록
- 배치 처리로 동일 매장 리뷰 효율적 처리
- 답글 상태 추적 및 에러 처리
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from supabase import create_client, Client
from dotenv import load_dotenv

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from utils.popup_handler import PopupHandler

class BaeminReplyPoster:
    def __init__(self, headless=False, timeout=30000):
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.context = None
        self.page = None
        
        # 금지어 목록 (배민에서 차단하는 경쟁업체 키워드)
        self.forbidden_words = [
            '요기요', '요기요', 'yogiyo', 'YOGIYO',
            '쿠팡이츠', '쿠팡잇츠', '쿠팡 이츠', 'coupangeats', 'COUPANGEATS',
            '배달요', '딜리버리히어로', '위메프오', '위메프 오',
            '배달통', '배민라이더스', '띵동',  # 경쟁 서비스들
            '네이버', 'naver', 'NAVER',  # 네이버도 경쟁사로 분류될 수 있음
        ]
        
        # Supabase 클라이언트 초기화
        load_dotenv()
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            raise ValueError("Supabase 환경변수가 설정되지 않았습니다.")
        
        self.supabase: Client = create_client(supabase_url, supabase_service_key)
    
    async def post_replies_batch(self, username: str, password: str, 
                                 platform_store_id: str, user_id: str,
                                 max_replies: int = 10) -> Dict:
        """동일 매장의 여러 리뷰에 답글 배치 등록"""
        try:
            print(f"[BAEMIN] 배민 답글 배치 등록 시작: {platform_store_id}")
            
            # 1. 답글 등록이 필요한 리뷰들 조회
            reviews_to_reply = await self._get_pending_reviews(platform_store_id, user_id, max_replies)
            
            if not reviews_to_reply:
                print("[BAEMIN] 답글 등록할 리뷰가 없습니다.")
                return {
                    'success': True,
                    'total': 0,
                    'success_count': 0,
                    'failed_count': 0,
                    'message': 'No reviews to reply'
                }
            
            print(f"[BAEMIN] {len(reviews_to_reply)}개 리뷰에 답글 등록 예정")
            
            # 2. 브라우저 초기화 및 로그인
            await self._initialize_browser()
            
            # 3. 로그인 수행
            login_success = await self._login(self.page, username, password)
            if not login_success:
                await self._cleanup_browser()
                return {
                    'success': False,
                    'error': '로그인 실패',
                    'total': len(reviews_to_reply),
                    'success_count': 0,
                    'failed_count': len(reviews_to_reply)
                }
            
            # 4. 리뷰 페이지로 이동
            review_url = f"https://self.baemin.com/shops/{platform_store_id}/reviews"
            print(f"[BAEMIN] 리뷰 페이지로 이동: {review_url}")
            
            try:
                await self.page.goto(review_url, wait_until='domcontentloaded', timeout=15000)
            except Exception as e:
                print(f"[BAEMIN] 페이지 로드 타임아웃 (무시하고 진행): {str(e)}")
            
            await self.page.wait_for_timeout(3000)
            
            # 팝업 닫기 시도 (새로운 범용 핸들러 사용)
            await PopupHandler.handle_baemin_popup(self.page)

            # 4.5. 날짜 필터 선택 (최근 30일로 설정)
            await self._set_date_filter(self.page, 30)

            # 5. 미답변 탭 클릭 (답글 등록할 리뷰만 표시)
            try:
                # 여러 가능한 미답변 탭 선택자 시도
                unanswered_tab_selectors = [
                    'button:has-text("미답변")',
                    '#no-comment',
                    'button[role="tab"]:has-text("미답변")',
                    'button[aria-controls*="noComment"]'
                ]
                
                unanswered_tab = None
                for selector in unanswered_tab_selectors:
                    unanswered_tab = await self.page.query_selector(selector)
                    if unanswered_tab:
                        print(f"[BAEMIN] 미답변 탭 발견: {selector}")
                        break
                
                if unanswered_tab:
                    await unanswered_tab.click()
                    await self.page.wait_for_timeout(2000)
                    print("[BAEMIN] 미답변 탭 클릭 완료")
                else:
                    print("[BAEMIN] 미답변 탭을 찾을 수 없음 (전체 리뷰에서 진행)")
                    
            except Exception as e:
                print(f"[BAEMIN] 미답변 탭 클릭 중 오류: {str(e)}")
            
            # 6. 각 리뷰에 답글 등록
            success_count = 0
            failed_count = 0
            results = []
            total = len(reviews_to_reply)

            # 먼저 현재 페이지에서 찾을 수 있는 리뷰들을 확인
            print(f"[BAEMIN] 📋 현재 페이지 로드된 리뷰 확인 중...")
            available_on_page = await self._get_available_reviews_on_page(self.page)
            print(f"[BAEMIN] 📋 현재 페이지에서 {len(available_on_page)}개 리뷰 발견")

            # 처리할 리뷰들을 우선순위에 따라 정렬 (현재 페이지에 있는 것을 먼저)
            reviews_on_page = []
            reviews_need_scroll = []

            for review in reviews_to_reply:
                if review['baemin_review_id'] in available_on_page:
                    reviews_on_page.append(review)
                else:
                    reviews_need_scroll.append(review)

            print(f"[BAEMIN] 📋 우선 처리 (현재 페이지): {len(reviews_on_page)}개")
            print(f"[BAEMIN] 📋 스크롤 필요: {len(reviews_need_scroll)}개")

            # 현재 페이지 리뷰들 먼저 처리
            all_reviews_ordered = reviews_on_page + reviews_need_scroll

            for idx, review in enumerate(all_reviews_ordered, 1):
                try:
                    print(f"\n{'='*60}")
                    print(f"[BAEMIN] 📊 진행률: {idx}/{total} ({idx*100//total}%)")
                    print(f"[BAEMIN] 🎯 리뷰 {review['baemin_review_id']} 처리 시작")
                    print(f"[BAEMIN] 👤 작성자: {review.get('reviewer_name', 'Unknown')}")
                    print(f"{'='*60}")

                    # 답글 등록
                    result = await self._post_single_reply(
                        self.page,
                        review['baemin_review_id'],
                        review['reply_text'],
                        review  # review 객체 전달
                    )

                    if result['success']:
                        success_count += 1
                        # DB 상태 업데이트
                        await self._update_reply_status(
                            review['id'],
                            'sent',
                            review['reply_text']
                        )
                        print(f"[BAEMIN] ✅ [{idx}/{total}] 리뷰 {review['baemin_review_id']} 답글 등록 성공")
                    else:
                        failed_count += 1
                        # 금지어 실패인 경우 특별 처리
                        if 'Forbidden word' in result.get('error', '') or 'forbidden' in result.get('error', '').lower():
                            print(f"[BAEMIN] ⚠️ [{idx}/{total}] 리뷰 {review['baemin_review_id']} 금지어로 인한 실패")
                            # failure_reason은 이미 _post_single_reply에서 DB에 저장됨
                        elif 'not found' in result.get('error', '').lower():
                            print(f"[BAEMIN] ❌ [{idx}/{total}] 리뷰 {review['baemin_review_id']} 리뷰를 찾을 수 없음")
                        else:
                            print(f"[BAEMIN] ❌ [{idx}/{total}] 리뷰 {review['baemin_review_id']} 답글 등록 실패: {result.get('error')}")

                    results.append(result)

                    # 현재까지 진행 상황 요약
                    print(f"\n[BAEMIN] 📈 현재까지: 성공 {success_count}개 / 실패 {failed_count}개")

                    # 마지막 리뷰가 아니면 다음 답글 등록 전 대기
                    if idx < total:
                        print(f"[BAEMIN] ⏳ 다음 리뷰 처리 전 2초 대기...")
                        await self.page.wait_for_timeout(2000)
                    
                except Exception as e:
                    print(f"[BAEMIN] 리뷰 {review['baemin_review_id']} 처리 중 오류: {str(e)}")
                    failed_count += 1
                    results.append({
                        'success': False,
                        'review_id': review['baemin_review_id'],
                        'error': str(e)
                    })
            
            # 6. 브라우저 정리
            await self._cleanup_browser()
            
            print(f"\n[BAEMIN] 배치 처리 완료: 성공 {success_count}개, 실패 {failed_count}개")
            
            return {
                'success': True,
                'total': len(reviews_to_reply),
                'success_count': success_count,
                'failed_count': failed_count,
                'results': results
            }
            
        except Exception as e:
            print(f"[BAEMIN] 배치 처리 중 오류: {str(e)}")
            await self._cleanup_browser()
            return {
                'success': False,
                'error': str(e),
                'total': 0,
                'success_count': 0,
                'failed_count': 0
            }
    
    async def _initialize_browser(self):
        """브라우저 초기화"""
        try:
            self.playwright = await async_playwright().start()
            
            try:
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    channel='chrome',
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--start-maximized'
                    ]
                )
            except Exception as e:
                print(f"Chrome 채널 실패, Chromium으로 대체: {e}")
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.page = await self.context.new_page()
            
            # 자동화 감지 방지
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
            """)
            
        except Exception as e:
            print(f"[BAEMIN] 브라우저 초기화 실패: {str(e)}")
            raise
    
    async def _cleanup_browser(self):
        """브라우저 정리"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    async def _login(self, page: Page, username: str, password: str) -> bool:
        """배민 로그인"""
        try:
            print("[BAEMIN] 로그인 페이지로 이동 중...")
            await page.goto("https://biz-member.baemin.com/login", timeout=30000)
            await page.wait_for_timeout(2000)
            
            print("[BAEMIN] 로그인 정보 입력 중...")
            await page.fill('input[data-testid="id"]', username)
            await page.wait_for_timeout(500)
            
            await page.fill('input[data-testid="password"]', password)
            await page.wait_for_timeout(500)
            
            print("[BAEMIN] 로그인 버튼 클릭...")
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(3000)
            
            # 로그인 성공 확인
            current_url = page.url
            print(f"[BAEMIN] 로그인 후 URL: {current_url}")
            
            if 'login' not in current_url:
                print("[BAEMIN] [OK] 로그인 성공")
                return True
            else:
                print("[BAEMIN] [ERROR] 로그인 실패")
                return False
                
        except Exception as e:
            print(f"[BAEMIN] 로그인 중 오류: {str(e)}")
            return False
    
    async def _get_pending_reviews(self, platform_store_id: str, user_id: str, limit: int) -> List[Dict]:
        """답글 등록이 필요한 리뷰 조회"""
        try:
            from datetime import datetime
            
            # platform_stores 테이블에서 UUID 조회
            store_result = self.supabase.table('platform_stores').select('id').eq(
                'platform_store_id', platform_store_id
            ).eq('platform', 'baemin').eq('user_id', user_id).single().execute()
            
            if not store_result.data:
                print(f"[BAEMIN] 매장을 찾을 수 없습니다: {platform_store_id}")
                return []
            
            platform_store_uuid = store_result.data['id']
            
            # 현재 시각
            current_time = datetime.now()
            print(f"[BAEMIN] 현재 시각: {current_time.isoformat()}")
            
            # AI 답글이 생성되었지만 아직 등록되지 않은 리뷰 조회
            # schedulable_reply_date 필드도 포함
            reviews_result = self.supabase.table('reviews_baemin').select(
                'id, baemin_review_id, reviewer_name, review_text, reply_text, reply_status, schedulable_reply_date'
            ).eq(
                'platform_store_id', platform_store_uuid
            ).eq(
                'reply_status', 'draft'  # AI 답글 생성됨
            ).neq(
                'reply_text', None  # 답글 텍스트 있음
            ).limit(100).execute()  # 모든 리뷰 조회 (최대 100개)
            
            if not reviews_result.data:
                print("[BAEMIN] 답글 등록 대기 중인 리뷰가 없습니다.")
                return []
            
            # schedulable_reply_date 체크하여 필터링
            eligible_reviews = []
            skipped_reviews = []
            
            for review in reviews_result.data:
                schedulable_date = review.get('schedulable_reply_date')
                
                # schedulable_reply_date가 없으면 즉시 처리 가능
                if not schedulable_date:
                    eligible_reviews.append(review)
                    continue
                
                # 문자열을 datetime 객체로 변환
                try:
                    if isinstance(schedulable_date, str):
                        # ISO 형식 또는 다양한 형식 처리
                        if 'T' in schedulable_date:
                            schedulable_datetime = datetime.fromisoformat(schedulable_date.replace('Z', '+00:00'))
                            # timezone-aware 날짜를 naive로 변환 (한국 시간 기준)
                            if schedulable_datetime.tzinfo is not None:
                                # UTC+9 (한국 시간)로 변환 후 naive로 만들기
                                from datetime import timezone, timedelta
                                kst = timezone(timedelta(hours=9))
                                schedulable_datetime = schedulable_datetime.astimezone(kst).replace(tzinfo=None)
                        else:
                            schedulable_datetime = datetime.strptime(schedulable_date, '%Y-%m-%d %H:%M:%S')
                    else:
                        schedulable_datetime = schedulable_date
                    
                    # 현재 시각과 비교 (둘 다 naive datetime)
                    if current_time >= schedulable_datetime:
                        eligible_reviews.append(review)
                        print(f"[BAEMIN] ✅ 리뷰 {review['baemin_review_id']}: 답글 게시 가능 (예정: {schedulable_date})")
                    else:
                        time_diff = schedulable_datetime - current_time
                        hours_remaining = time_diff.total_seconds() / 3600
                        skipped_reviews.append(review)
                        print(f"[BAEMIN] [WAITING] 리뷰 {review['baemin_review_id']}: 아직 대기 중 (예정: {schedulable_date}, {hours_remaining:.1f}시간 남음)")
                        
                except Exception as e:
                    print(f"[BAEMIN] [WARNING] 리뷰 {review['baemin_review_id']}: 날짜 파싱 오류 ({schedulable_date}) - 즉시 처리")
                    eligible_reviews.append(review)
            
            # 결과 요약 출력
            if skipped_reviews:
                print(f"[BAEMIN] [INFO] 총 {len(reviews_result.data)}개 중:")
                print(f"  - 처리 가능: {len(eligible_reviews)}개")
                print(f"  - 대기 중: {len(skipped_reviews)}개")
            
            # limit 적용 (0이면 제한 없음)
            if limit > 0:
                eligible_reviews = eligible_reviews[:limit]
            
            if eligible_reviews:
                print(f"[BAEMIN] {len(eligible_reviews)}개의 답글 등록 가능한 리뷰 발견")
            else:
                print("[BAEMIN] 현재 답글 등록 가능한 리뷰가 없습니다 (모두 대기 중)")
            
            # 최종 요약 로그
            if skipped_reviews:
                print(f"[BAEMIN] [INFO] schedulable_reply_date 필터링 결과:")
                print(f"    - 전체 조회: {len(reviews_result.data)}개")
                print(f"    - 즉시 처리: {len(eligible_reviews)}개")
                print(f"    - 예약 대기: {len(skipped_reviews)}개")
            
            return eligible_reviews
            
        except Exception as e:
            print(f"[BAEMIN] 리뷰 조회 중 오류: {str(e)}")
            return []
    
    def check_forbidden_words(self, text: str) -> List[str]:
        """텍스트에서 금지어 검출"""
        found_words = []
        text_lower = text.lower()
        for word in self.forbidden_words:
            if word.lower() in text_lower:
                found_words.append(word)
        return found_words
    
    def filter_forbidden_words(self, text: str) -> str:
        """[DEPRECATED] 금지어를 대체 문자로 변경 - 더 이상 사용하지 않음
        
        사용자 요청에 따라 자동 치환 대신 실패 처리 후 
        다음 답글 생성 시 AI가 개선된 답글을 작성하도록 변경됨
        """
        filtered_text = text
        replacements = {
            '요기요': '타 플랫폼',
            'yogiyo': '타 플랫폼',
            '쿠팡이츠': '타 배달앱',
            'coupangeats': '타 배달앱',
            '쿠팡잇츠': '타 배달앱',
            '쿠팡 이츠': '타 배달앱',
            '배달요': '타 서비스',
            '네이버': '타 플랫폼',
            'naver': '타 플랫폼',
        }
        
        for forbidden, replacement in replacements.items():
            # 대소문자 구분 없이 치환
            import re
            pattern = re.compile(re.escape(forbidden), re.IGNORECASE)
            filtered_text = pattern.sub(replacement, filtered_text)
        
        return filtered_text
    
    async def _post_single_reply(self, page: Page, baemin_review_id: str, reply_text: str, review: Dict = None) -> Dict:
        """개별 리뷰에 답글 등록"""
        try:
            print(f"\n{'='*60}")
            print(f"[BAEMIN] 🎯 리뷰 ID: {baemin_review_id} 처리 시작")
            print(f"[BAEMIN] 📝 답글 내용: '{reply_text[:100]}{'...' if len(reply_text) > 100 else ''}'")
            
            # 사전 체크 제거 - 배민이 직접 검증하도록 함
            print(f"{'='*60}")
            
            # 1. 해당 리뷰 찾기
            print(f"[BAEMIN] 🔍 1단계: 리뷰 {baemin_review_id} 요소 검색 시작...")
            review_element = None

            # 먼저 현재 보이는 화면에서 검색
            review_number_spans = await page.query_selector_all(f'span:has-text("리뷰번호 {baemin_review_id}")')

            if review_number_spans:
                # 리뷰 컨테이너 찾기
                for span in review_number_spans:
                    # 상위 컨테이너로 이동
                    container = await span.evaluate_handle('''(element) => {
                        let parent = element;
                        while (parent && parent.parentElement) {
                            parent = parent.parentElement;
                            // 적절한 컨테이너 크기 확인 (리뷰 전체를 포함하는 요소)
                            if (parent.offsetHeight > 100) {
                                return parent;
                            }
                        }
                        return null;
                    }''')

                    if container:
                        review_element = container
                        break

            # 현재 화면에서 못 찾으면 스크롤하며 검색
            if not review_element:
                print(f"[BAEMIN]    🔄 스크롤 검색 시작...")
                review_element = await self._find_review_with_scroll(page, baemin_review_id)

                if not review_element:
                    # 더 강력한 스크롤 검색 시도 (페이지 새로고침 없이)
                    print(f"[BAEMIN]    🔄 확장된 스크롤 검색 시도...")
                    review_element = await self._find_review_with_scroll(page, baemin_review_id, max_scrolls=50)

                    if not review_element:
                        # 페이지 전체를 처음부터 다시 스크롤
                        print(f"[BAEMIN]    🔄 전체 페이지 재스크롤...")
                        await self._scroll_to_top(page)
                        await page.wait_for_timeout(1000)
                        review_element = await self._find_review_with_scroll(page, baemin_review_id, max_scrolls=100)

                        if not review_element:
                            print(f"[BAEMIN]    ❌ 스크롤 검색으로 리뷰를 찾을 수 없음")
                            return {
                                'success': False,
                                'review_id': baemin_review_id,
                                'error': 'Review not found with extensive scroll search'
                            }
            
            if not review_element:
                return {
                    'success': False,
                    'review_id': baemin_review_id,
                    'error': 'Review container not found'
                }
            
            
            # 2. 특정 리뷰 컨테이너 내에서 답글 작성 버튼 찾기 ⭐ 핵심 수정
            print(f"[BAEMIN] 🔘 2단계: 리뷰 {baemin_review_id} 전용 답글 버튼 검색...")
            reply_button = None
            
            # 먼저 해당 리뷰 컨테이너 내에서 답글 버튼 찾기
            selectors = [
                'button:has-text("사장님 댓글 등록하기")',
                'span:has-text("사장님 댓글 등록하기")',
                '[class*="Button"]:has-text("사장님 댓글 등록하기")',
                'button:has-text("답글")',
                'span:has-text("답글")',
                '*:has-text("사장님 댓글 등록하기")'
            ]
            
            # 🔥 핵심 변경: review_element 내에서만 검색
            for selector in selectors:
                try:
                    reply_button = await review_element.query_selector(selector)
                    if reply_button:
                        # 요소가 실제로 클릭 가능한지 확인
                        is_clickable = await reply_button.evaluate('''(element) => {
                            const rect = element.getBoundingClientRect();
                            const style = getComputedStyle(element);
                            
                            return rect.width > 0 && 
                                   rect.height > 0 && 
                                   style.visibility !== 'hidden' && 
                                   style.display !== 'none' &&
                                   !element.disabled;
                        }''')
                        
                        if is_clickable:
                            print(f"[BAEMIN]    ✅ 리뷰 {baemin_review_id} 전용 답글 버튼 발견! (선택자: {selector})")
                            break
                        else:
                            print(f"[BAEMIN] 버튼 발견했지만 클릭 불가능 - 선택자: {selector}")
                            reply_button = None
                except Exception as e:
                    print(f"[BAEMIN] 리뷰 컨테이너에서 선택자 시도 중 오류 - {selector}: {str(e)}")
                    continue
            
            # 리뷰 컨테이너에서 못찾으면 페이지 전체에서 시도 (백업)
            if not reply_button:
                print(f"[BAEMIN] 리뷰 컨테이너에서 못찾음. 페이지 전체에서 백업 검색...")
                for selector in selectors:
                    try:
                        all_buttons = await page.query_selector_all(selector)
                        for button in all_buttons:
                            # 해당 버튼이 현재 리뷰와 관련있는지 확인
                            is_related = await button.evaluate(f'''(element) => {{
                                // 버튼 주변에 리뷰 ID가 있는지 확인
                                let parent = element;
                                for (let i = 0; i < 10; i++) {{
                                    if (parent.textContent && parent.textContent.includes('{baemin_review_id}')) {{
                                        return true;
                                    }}
                                    parent = parent.parentElement;
                                    if (!parent) break;
                                }}
                                return false;
                            }}''')
                            
                            if is_related:
                                reply_button = button
                                print(f"[BAEMIN] 리뷰 {baemin_review_id}와 관련된 답글 버튼 발견!")
                                break
                        
                        if reply_button:
                            break
                    except Exception as e:
                        continue
            
            # 리뷰 컨테이너 내에서 JavaScript로 강화된 검색
            if not reply_button:
                print(f"[BAEMIN] 리뷰 {baemin_review_id} 컨테이너 내에서 JavaScript 강화 검색 시작...")
                
                click_result = await review_element.evaluate(f'''(container) => {{
                    console.log('리뷰 {baemin_review_id} 컨테이너에서 답글 버튼 검색 중...');
                    
                    // 모든 하위 요소 검색
                    const allElements = container.querySelectorAll('*');
                    
                    for (let element of allElements) {{
                        const text = element.textContent || element.innerText || '';
                        
                        // "사장님 댓글 등록하기" 텍스트를 포함하는 요소 찾기
                        if (text.includes('사장님 댓글 등록하기') || 
                            text.includes('댓글 등록하기') ||
                            text.includes('답글 작성') ||
                            text.includes('답글')) {{
                            
                            console.log('리뷰 {baemin_review_id} - 답글 관련 텍스트 발견:', element.tagName, element.className, text.substring(0, 30));
                            
                            // 해당 요소 또는 상위 클릭 가능한 요소 찾기
                            let clickableElement = element;
                            while (clickableElement) {{
                                const styles = getComputedStyle(clickableElement);
                                const hasClickEvents = clickableElement.onclick || 
                                                     styles.cursor === 'pointer' ||
                                                     clickableElement.tagName === 'BUTTON' ||
                                                     clickableElement.getAttribute('role') === 'button' ||
                                                     clickableElement.className.includes('Button');
                                
                                if (hasClickEvents) {{
                                    console.log('리뷰 {baemin_review_id} - 클릭 가능한 요소 발견:', clickableElement.tagName, clickableElement.className);
                                    
                                    // 직접 클릭 시도
                                    try {{
                                        clickableElement.click();
                                        return {{ success: true, clicked: true, reviewId: '{baemin_review_id}' }};
                                    }} catch (e) {{
                                        console.log('리뷰 {baemin_review_id} - 클릭 실패:', e.message);
                                        return {{ success: true, clicked: false, error: e.message, reviewId: '{baemin_review_id}' }};
                                    }}
                                }}
                                
                                clickableElement = clickableElement.parentElement;
                            }}
                            
                            // 클릭 가능한 상위 요소가 없으면 원래 요소 클릭 시도
                            try {{
                                element.click();
                                return {{ success: true, clicked: true, reviewId: '{baemin_review_id}' }};
                            }} catch (e) {{
                                console.log('리뷰 {baemin_review_id} - 직접 클릭 실패:', e.message);
                                continue;
                            }}
                        }}
                    }}
                    
                    return {{ success: false, message: '리뷰 {baemin_review_id} 컨테이너에서 답글 버튼을 찾을 수 없음' }};
                }}''')
                
                if click_result and click_result.get('success'):
                    if click_result.get('clicked'):
                        print(f"[BAEMIN] 리뷰 {baemin_review_id} JavaScript 답글 버튼 클릭 성공!")
                        await page.wait_for_timeout(2000)  # 모달 로딩 대기
                        reply_button = "clicked_by_js"
                    else:
                        print(f"[BAEMIN] 리뷰 {baemin_review_id} JavaScript 클릭 실패: {click_result.get('error', 'Unknown error')}")
                        reply_button = None
                else:
                    print(f"[BAEMIN] 리뷰 {baemin_review_id} 컨테이너에서 답글 버튼을 찾을 수 없음")
                    
                    # 디버깅: 리뷰 컨테이너의 HTML 구조 출력
                    container_html = await review_element.inner_html()
                    print(f"[BAEMIN] 디버깅: 리뷰 컨테이너 HTML 구조 (처음 1000자):")
                    print(container_html[:1000])
                    
                    # 컨테이너 내 모든 텍스트가 있는 요소들 출력
                    text_elements = await review_element.evaluate('''(container) => {
                        const elements = [];
                        const allElements = container.querySelectorAll('*');
                        
                        for (let element of allElements) {
                            const text = (element.textContent || '').trim();
                            if (text && (text.includes('댓글') || text.includes('답글') || text.includes('등록'))) {
                                elements.push({
                                    tag: element.tagName,
                                    className: element.className,
                                    text: text.substring(0, 100),
                                    hasClick: !!(element.onclick || element.getAttribute('onclick'))
                                });
                            }
                        }
                        
                        return elements;
                    }''')
                    
                    print("[BAEMIN] 컨테이너 내 '댓글', '답글', '등록' 관련 요소들:")
                    for elem in text_elements[:5]:  # 처음 5개만
                        print(f"  - {elem['tag']}.{elem['className']}: '{elem['text']}' (onclick: {elem['hasClick']})")
                    
                    # 추가 디버깅: 페이지의 모든 버튼과 클릭 가능한 요소들 확인
                    print("\n[BAEMIN] 페이지의 모든 클릭 가능한 요소들 확인:")
                    all_clickable = await page.evaluate('''() => {
                        const clickableElements = [];
                        
                        // 버튼 요소들
                        document.querySelectorAll('button, [role="button"], [class*="Button"], [class*="button"], span[onclick], div[onclick]').forEach(el => {
                            const text = (el.textContent || '').trim();
                            if (text && text.length < 100) {
                                clickableElements.push({
                                    tag: el.tagName,
                                    className: el.className || '',
                                    text: text
                                });
                            }
                        });
                        
                        return clickableElements;
                    }''')
                    
                    # 댓글, 답글, 등록 관련 키워드가 있는 버튼들 찾기
                    reply_related = [elem for elem in all_clickable if any(keyword in elem['text'] for keyword in ['댓글', '답글', '등록', '사장님', '작성'])]
                    
                    if reply_related:
                        print("답글 관련 버튼들:")
                        for elem in reply_related[:10]:  # 최대 10개
                            print(f"  - {elem['tag']}.{elem['className']}: '{elem['text']}'")
                    else:
                        print("답글 관련 버튼을 찾을 수 없음. 전체 버튼 목록 (처음 20개):")
                        for elem in all_clickable[:20]:
                            print(f"  - {elem['tag']}.{elem['className']}: '{elem['text']}'")
                    
                    # 현재 페이지 URL 확인
                    current_url = page.url
                    print(f"\n[BAEMIN] 현재 페이지 URL: {current_url}")
                    
                    # 페이지 제목 확인
                    title = await page.title()
                    print(f"[BAEMIN] 페이지 제목: {title}")
            
            # 버튼이 없으면 이미 답글이 있는지 확인
            if not reply_button:
                # 이미 답글이 있는지 확인
                existing_reply = await review_element.query_selector('div:has-text("사장님")')
                if existing_reply:
                    print(f"[BAEMIN] 리뷰 {baemin_review_id}에 이미 답글이 있습니다.")
                    return {
                        'success': False,
                        'review_id': baemin_review_id,
                        'error': 'Reply already exists'
                    }
                
                # 답글 버튼을 찾을 수 없음
                return {
                    'success': False,
                    'review_id': baemin_review_id,
                    'error': 'Reply button not found'
                }
            
            # 3. 답글 작성 버튼 클릭
            print(f"[BAEMIN] 🚀 3단계: 답글 버튼 클릭...")
            if reply_button != "clicked_by_js":
                await reply_button.click()
                print("[BAEMIN]    ✓ 답글 버튼 클릭 완료")
                print("[BAEMIN]    ⏳ 모달 로딩 대기 중...")
                # 모달이 완전히 로딩될 때까지 충분히 대기 (3초→5초)
                await page.wait_for_timeout(5000)
                print("[BAEMIN]    ✅ 모달 로딩 대기 완료")
            else:
                print("[BAEMIN]    ✓ JavaScript로 이미 클릭했으므로 Playwright 클릭 건너뜀")
                await page.wait_for_timeout(3000)  # 2초→3초로 증가
            
            # 4. 리뷰 카드 내에서 텍스트 입력 필드 찾기 ✨ 핵심 개선
            print(f"[BAEMIN] 📝 4단계: 텍스트 입력 필드 검색...")
            textarea = None

            # 모달 로딩 추가 대기 (안정화)
            await page.wait_for_timeout(2000)  # 추가 2초 대기
            
            # 🎯 리뷰 카드 내에서만 textarea 검색 (핵심 개선!)
            textarea_selectors = [
                'textarea[rows="3"]',  # 가장 정확한 선택자
                'textarea[class*="TextArea"]',
                'textarea[placeholder=""]',  # 빈 placeholder
                'textarea.TextArea_b_pnsa_12i8sxif', 
                'textarea',
                'div[contenteditable="true"]'
            ]
            
            # 리뷰 컨테이너 내에서 먼저 검색
            print(f"[BAEMIN]    🔍 리뷰 {baemin_review_id} 컨테이너 내에서 textarea 검색...")
            for selector in textarea_selectors:
                try:
                    textarea = await review_element.query_selector(selector)
                    if textarea:
                        # textarea가 실제로 보이는지 확인
                        is_visible = await textarea.is_visible()
                        if is_visible:
                            print(f"[BAEMIN]    ✅ 리뷰 컨테이너 내에서 textarea 발견: {selector}")
                            break
                        else:
                            print(f"[BAEMIN]    ⚠️ textarea 발견했지만 숨겨져 있음: {selector}")
                            textarea = None
                except Exception as e:
                    print(f"[BAEMIN]    선택자 {selector} 시도 중 오류: {str(e)}")
                    continue
            
            # 리뷰 컨테이너에서 못 찾으면 페이지 전체에서 백업 검색
            if not textarea:
                print(f"[BAEMIN]    🔍 페이지 전체에서 백업 검색...")
                for selector in textarea_selectors:
                    try:
                        textarea = await page.query_selector(selector)
                        if textarea:
                            is_visible = await textarea.is_visible()
                            if is_visible:
                                print(f"[BAEMIN]    ✅ 페이지에서 textarea 발견: {selector}")
                                break
                            else:
                                textarea = None
                    except Exception as e:
                        continue
            
            if not textarea:
                print(f"[BAEMIN]    ❌ textarea를 찾을 수 없음")
                return {
                    'success': False,
                    'review_id': baemin_review_id,
                    'error': 'Reply textarea not found'
                }
            
            # 5. 답글 텍스트 입력
            print(f"[BAEMIN] ✍️ 5단계: 답글 텍스트 입력 ('{reply_text[:50]}...')")
            
            # ✨ 간단하고 확실한 키보드 입력 방식 (성공한 다른 코드 방식 적용)
            input_success = False
            
            try:
                print("[BAEMIN]    📝 간단한 키보드 입력 방식 사용")
                
                # 1단계: textarea 클릭하여 포커스
                await textarea.click()
                await page.wait_for_timeout(500)  # 0.5초 대기
                print("[BAEMIN]    ✓ textarea 포커스 완료")
                
                # 2단계: 기존 텍스트 전체 선택
                await textarea.press('Control+a')
                await page.wait_for_timeout(200)  # 0.2초 대기
                print("[BAEMIN]    ✓ 전체 텍스트 선택 완료")
                
                # 3단계: 기존 텍스트 삭제
                await textarea.press('Delete')
                await page.wait_for_timeout(500)  # 0.5초 대기
                print("[BAEMIN]    ✓ 기존 텍스트 삭제 완료")
                
                # 4단계: 새 텍스트 입력 (천천히)
                await textarea.type(reply_text, delay=50)  # 50ms 딜레이
                await page.wait_for_timeout(1000)  # 1초 대기
                print(f"[BAEMIN]    ✓ 새 텍스트 입력 완료: {len(reply_text)}자")
                
                input_success = True
                
            except Exception as e:
                print(f"[BAEMIN]    ❌ 키보드 입력 실패: {str(e)}")
            
            # 백업 방법: Playwright fill (키보드 입력 실패 시)
            if not input_success:
                try:
                    print("[BAEMIN]    🔄 백업 방법: Playwright fill 시도")
                    
                    # textarea 클릭 후 fill
                    await textarea.click()
                    await page.wait_for_timeout(300)
                    
                    # 완전 리셋 후 새 텍스트 입력
                    await textarea.fill('')  # 기존 텍스트 지우기
                    await page.wait_for_timeout(500)
                    await textarea.fill(reply_text)  # 새 텍스트 입력
                    await page.wait_for_timeout(500)
                    
                    print("[BAEMIN]    ✓ Playwright fill 완료")
                    input_success = True
                    
                except Exception as e:
                    print(f"[BAEMIN]    ❌ Playwright fill 실패: {str(e)}")
            
            # ✨ 간소화된 텍스트 입력 검증
            if input_success:
                print("[BAEMIN]    🔍 텍스트 입력 검증...")
                try:
                    actual_value = await textarea.input_value()
                    
                    if actual_value and actual_value.strip():
                        print(f"[BAEMIN]    ✅ 텍스트 입력 검증 성공! ({len(actual_value.strip())}자 입력됨)")
                        print(f"[BAEMIN]    📝 입력된 내용: '{actual_value[:100]}{'...' if len(actual_value) > 100 else ''}'")
                    else:
                        print("[BAEMIN]    ❌ 빈 텍스트 감지 - 등록 중단")
                        return {
                            'success': False,
                            'review_id': baemin_review_id,
                            'error': 'Empty text detected - preventing submission'
                        }
                except Exception as e:
                    print(f"[BAEMIN]    ⚠️ 검증 중 오류 (계속 진행): {str(e)}")
            else:
                print("[BAEMIN]    ❌ 모든 텍스트 입력 방법 실패")
                return {
                    'success': False,
                    'review_id': baemin_review_id,
                    'error': 'Text input failed - preventing empty reply submission'
                }
            
            await page.wait_for_timeout(1000)
            
            # 6. 등록 버튼 찾기 및 클릭 - 최적화된 버전
            print(f"[BAEMIN] 🔘 6단계: 등록 버튼 검색...")

            # 가장 자주 작동하는 선택자들만 먼저 시도 (빠른 검색)
            primary_selectors = [
                'button:has(span span p:has-text("등록"))',  # 가장 많이 성공한 패턴
                'button[data-disabled="false"][data-loading="false"]:has-text("등록")',
                'button:has-text("등록")'
            ]

            submit_button = None

            # 1차: 빠른 검색 (timeout 짧게)
            for selector in primary_selectors:
                try:
                    submit_button = await page.wait_for_selector(selector, timeout=1000, state='visible')
                    if submit_button:
                        # 버튼이 활성화되어 있는지 확인
                        is_disabled = await submit_button.get_attribute('disabled')
                        if not is_disabled:
                            print(f"[BAEMIN]    ✅ 등록 버튼 빠르게 발견!")
                            break
                        else:
                            submit_button = None
                except:
                    continue

            # 1차에서 못 찾으면 2차 상세 검색
            if not submit_button:
                print(f"[BAEMIN]    🔄 상세 검색 모드...")

                # 추가 선택자들 (백업용)
                backup_selectors = [
                    'button.Button_b_pnsa_1w1nucha[data-disabled="false"]:has-text("등록")',
                    'button[data-atelier-component="Button"]:has(p:has-text("등록"))',
                    'button[type="button"]:has(p:has-text("등록"))',
                    'div[role="dialog"] button:has-text("등록")'
                ]

                for selector in backup_selectors:
                    try:
                        submit_button = await page.wait_for_selector(selector, timeout=1500, state='visible')
                        if submit_button:
                            is_disabled = await submit_button.get_attribute('disabled')
                            if not is_disabled:
                                print(f"[BAEMIN]    ✅ 등록 버튼 발견 (백업 검색)")
                                break
                            else:
                                submit_button = None
                    except:
                        continue
            
            if not submit_button:
                print(f"[BAEMIN]    ❌ 등록 버튼을 찾을 수 없음")
                
                # 디버깅: 페이지의 모든 등록 관련 버튼 출력
                print(f"[BAEMIN]    🔍 디버깅: 페이지의 모든 등록 관련 버튼 확인...")
                page_buttons = await page.evaluate('''() => {
                    const buttons = [];
                    document.querySelectorAll('button, [role="button"], [class*="Button"]').forEach(btn => {
                        const text = (btn.textContent || '').trim();
                        if (text && (text.includes('등록') || text.includes('저장') || text.includes('완료') || text.includes('확인'))) {
                            buttons.push({
                                tag: btn.tagName,
                                className: btn.className || '',
                                text: text,
                                visible: btn.offsetWidth > 0 && btn.offsetHeight > 0,
                                disabled: btn.disabled
                            });
                        }
                    });
                    return buttons;
                }''')
                
                print(f"[BAEMIN]    등록 관련 버튼 {len(page_buttons)}개 발견:")
                for btn in page_buttons[:8]:  # 최대 8개만
                    status = "활성" if not btn['disabled'] and btn['visible'] else "비활성/숨김"
                    print(f"[BAEMIN]      - {btn['text']} ({status})")
                
                return {
                    'success': False,
                    'review_id': baemin_review_id,
                    'error': 'Submit button not found'
                }
            
            # 7. 등록 버튼 클릭
            print(f"[BAEMIN] 🚀 7단계: 등록 버튼 클릭...")
            await submit_button.click()
            print(f"[BAEMIN]    ✓ 등록 버튼 클릭 완료")
            
            # 등록 완료 대기 (금지어 팝업 체크를 위해 짧게)
            print(f"[BAEMIN]    ⏳ 등록 처리 대기 중...")
            await page.wait_for_timeout(1500)  # 1.5초 대기
            
            # 7-1. 금지어 팝업 체크
            print(f"[BAEMIN] 🔍 금지어 팝업 확인 중...")
            forbidden_popup = await page.query_selector('div[role="alertdialog"]')
            
            if forbidden_popup:
                print(f"[BAEMIN] ⚠️ 금지어 팝업 감지!")
                
                # 배민 팝업 메시지 정확히 추출
                popup_message = "배민 금지어 팝업 감지"  # 기본값
                detected_forbidden_word = None
                
                try:
                    # 팝업에서 정확한 메시지 추출
                    popup_text = await forbidden_popup.text_content()
                    if popup_text:
                        print(f"[BAEMIN] 📝 배민 팝업 전체 내용: {popup_text.strip()}")
                        
                        # 배민 팝업 메시지 패턴: "'요기요' 키워드는 입력하실 수 없습니다. 다른 문구로 변경해 주세요."
                        import re
                        
                        # 패턴 1: '단어' 키워드는 입력하실 수 없습니다
                        pattern1 = r"'([^']+)'\s*키워드는\s*입력하실\s*수\s*없습니다"
                        match = re.search(pattern1, popup_text)
                        
                        if match:
                            detected_forbidden_word = match.group(1)
                            # 배민의 정확한 메시지를 그대로 저장
                            full_message = popup_text.strip()
                            popup_message = f"배민 금지어 알림: {full_message[:150]}"
                            print(f"[BAEMIN] 🚨 배민이 금지한 단어: '{detected_forbidden_word}'")
                            print(f"[BAEMIN] 📄 배민 메시지: {full_message}")
                        else:
                            # 패턴을 못 찾으면 전체 메시지 저장
                            popup_message = f"배민 금지어 팝업: {popup_text.strip()[:150]}"
                            print(f"[BAEMIN] ⚠️ 알 수 없는 팝업 형식, 전체 메시지 저장")
                    
                except Exception as e:
                    print(f"[BAEMIN] 팝업 메시지 추출 실패: {str(e)}")
                    popup_message = f"팝업 메시지 추출 오류: {str(e)}"
                
                # 확인 버튼 클릭
                try:
                    print(f"[BAEMIN] 🔘 팝업 확인 버튼 찾는 중...")
                    
                    # 여러 가능한 확인 버튼 선택자
                    confirm_selectors = [
                        'div[role="alertdialog"] button:has-text("확인")',
                        'button:has-text("확인")',
                        'div.Dialog_b_dvcv_3pnjmu4 button:has-text("확인")',
                        'button[data-atelier-component="Button"]:has-text("확인")',
                        'button.Button_b_dvcv_1w1nucha:has-text("확인")'
                    ]
                    
                    confirm_button = None
                    for selector in confirm_selectors:
                        confirm_button = await forbidden_popup.query_selector(selector)
                        if not confirm_button:
                            confirm_button = await page.query_selector(selector)
                        if confirm_button:
                            print(f"[BAEMIN] ✅ 확인 버튼 발견: {selector}")
                            break
                    
                    if confirm_button:
                        await confirm_button.click()
                        print(f"[BAEMIN] ✓ 확인 버튼 클릭 완료")
                        await page.wait_for_timeout(1000)
                    else:
                        print(f"[BAEMIN] ⚠️ 확인 버튼을 찾을 수 없음 - ESC 키로 닫기 시도")
                        await page.keyboard.press('Escape')
                        await page.wait_for_timeout(1000)
                    
                except Exception as e:
                    print(f"[BAEMIN] 확인 버튼 클릭 실패: {str(e)}")
                
                # DB에 배민의 정확한 팝업 메시지 저장
                if review:
                    await self._update_reply_status(
                        review['id'],
                        'failed',
                        failure_reason=popup_message
                    )
                    print(f"[BAEMIN] 💾 DB 저장 완료: failure_reason = '{popup_message[:100]}...'")
                
                    # 추가로 원본 답글과 함께 상세 로그
                    if detected_forbidden_word:
                        print(f"[BAEMIN] 📊 상세 정보:")
                        print(f"    - 원본 답글: {reply_text[:50]}...")
                        print(f"    - 금지 단어: '{detected_forbidden_word}'")
                        print(f"    - 다음 AI 생성 시 이 정보를 참고하여 답글 재작성 예정")
                
                print(f"\n{'='*60}")
                print(f"[BAEMIN] ❌ 리뷰 {baemin_review_id} 배민 금지어로 인한 답글 등록 실패")
                print(f"[BAEMIN] 📝 배민 메시지: {popup_message}")
                print(f"[BAEMIN] 🔄 main.py 다음 실행 시 이 정보를 바탕으로 새 답글 생성됩니다")
                print(f"{'='*60}\n")
                
                return {
                    'success': False,
                    'review_id': baemin_review_id,
                    'error': f'Baemin forbidden word popup: {popup_message}',
                    'detected_word': detected_forbidden_word
                }
            
            # 금지어 팝업이 없으면 성공 대기
            print(f"[BAEMIN]    ✅ 금지어 팝업 없음 - 정상 처리")
            await page.wait_for_timeout(1500)  # 추가 1.5초 대기 (총 3초)
            print(f"[BAEMIN]    ✅ 등록 완료 대기 완료")
            
            # 8. 성공 확인
            print(f"[BAEMIN] ✅ 8단계: 답글 등록 성공 여부 확인...")
            # 답글이 등록되었는지 확인
            success_indicators = [
                '답글이 등록되었습니다',
                '댓글이 등록되었습니다',
                '등록되었습니다',
                '사장님'  # 답글 영역에 사장님 표시가 나타남
            ]
            
            success = False
            for indicator in success_indicators:
                if await page.query_selector(f'*:has-text("{indicator}")'):
                    success = True
                    break
            
            # 답글 영역이 나타났는지 확인
            if not success:
                reply_section = await review_element.query_selector('div:has-text("사장님")')
                if reply_section:
                    success = True
            
            if success:
                print(f"\n{'='*60}")
                print(f"[BAEMIN] 🎉 리뷰 {baemin_review_id} 답글 등록 성공!")
                print(f"[BAEMIN] 📝 등록된 답글: '{reply_text[:100]}{'...' if len(reply_text) > 100 else ''}'")
                print(f"{'='*60}\n")
                return {
                    'success': True,
                    'review_id': baemin_review_id,
                    'reply_text': reply_text,
                    'posted_at': datetime.now().isoformat()
                }
            else:
                print(f"\n{'='*60}")
                print(f"[BAEMIN] ❌ 리뷰 {baemin_review_id} 답글 등록 검증 실패")
                print(f"{'='*60}\n")
                return {
                    'success': False,
                    'review_id': baemin_review_id,
                    'error': 'Reply posting verification failed'
                }
            
        except Exception as e:
            print(f"[BAEMIN] 답글 등록 중 오류: {str(e)}")
            return {
                'success': False,
                'review_id': baemin_review_id,
                'error': str(e)
            }
    
    async def _update_reply_status(self, review_id: str, status: str, reply_text: str = None, failure_reason: str = None):
        """리뷰 답글 상태 업데이트"""
        try:
            update_data = {
                'reply_status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if status == 'sent':
                update_data['reply_posted_at'] = datetime.now().isoformat()
            
            # 실패 상태일 때 failure_reason 저장
            if status == 'failed' and failure_reason:
                update_data['failure_reason'] = failure_reason
            
            self.supabase.table('reviews_baemin').update(
                update_data
            ).eq('id', review_id).execute()
            
            print(f"[BAEMIN] 리뷰 {review_id} 상태 업데이트: {status}")
            if failure_reason:
                print(f"[BAEMIN] 실패 사유 저장: {failure_reason}")
            
        except Exception as e:
            print(f"[BAEMIN] 상태 업데이트 실패: {str(e)}")


    async def _set_date_filter(self, page, days: int = 30):
        """날짜 필터 설정 (크롤러와 동일한 로직)"""
        try:
            print(f"[BAEMIN] 📅 날짜 필터 선택 시도: 최근 {days}일")

            # 1. 먼저 날짜 드롭박스 클릭 (현재 날짜 표시 영역)
            date_dropdown = await page.query_selector("div.ReviewFilter-module__NZW0")
            if date_dropdown:
                await date_dropdown.click()
                await page.wait_for_timeout(1000)
                print("[BAEMIN] ✅ 날짜 드롭박스 열기 성공")
            else:
                print("[BAEMIN] ⚠️ 날짜 드롭박스를 찾을 수 없음")
                return False

            # 2. 라디오 버튼 선택
            if days >= 30:
                # 최근 30일 선택
                radio_30 = await page.query_selector('input[type="radio"][value="최근 30일"]')
                if radio_30:
                    await radio_30.click()
                    print("[BAEMIN] ✅ 최근 30일 선택")
                else:
                    print("[BAEMIN] ⚠️ 최근 30일 라디오 버튼을 찾을 수 없음")
                    return False
            else:
                # 최근 7일 선택
                radio_7 = await page.query_selector('input[type="radio"][value="최근 7일"]')
                if radio_7:
                    await radio_7.click()
                    print("[BAEMIN] ✅ 최근 7일 선택")
                else:
                    print("[BAEMIN] ⚠️ 최근 7일 라디오 버튼을 찾을 수 없음")
                    return False

            await page.wait_for_timeout(500)

            # 3. 적용 버튼 클릭 (중요!)
            apply_button = await page.query_selector('button[type="button"]:has-text("적용")')
            if apply_button:
                await apply_button.click()
                print("[BAEMIN] ✅ 적용 버튼 클릭")
                await page.wait_for_timeout(2000)
            else:
                print("[BAEMIN] ⚠️ 적용 버튼을 찾을 수 없음")
                return False

            print(f"[BAEMIN] ✅ 날짜 필터 적용 완료")
            return True

        except Exception as e:
            print(f"[BAEMIN] ⚠️ 날짜 필터 선택 실패: {str(e)}")
            return False

    async def _get_review_scroll_container(self, page):
        """리뷰 리스트의 실제 스크롤 컨테이너를 자동 감지"""
        try:
            container_handle = await page.evaluate_handle('''() => {
                // 리뷰 아이템을 기준점으로 찾기
                const reviewSelectors = [
                    '.ReviewContent-module__Ksg4',
                    '[data-atelier-component="Container"]',
                    'span',
                    'article', 'section'
                ];

                let reviewElement = null;
                for (const selector of reviewSelectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        reviewElement = elements[0];
                        break;
                    }
                }

                if (!reviewElement) {
                    // 텍스트로 리뷰 요소 찾기
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        if (el.textContent && el.textContent.includes('리뷰번호')) {
                            reviewElement = el;
                            break;
                        }
                    }
                }

                if (!reviewElement) {
                    console.log('리뷰 요소를 찾을 수 없음');
                    return null;
                }

                // 리뷰 요소의 상위로 올라가면서 스크롤 가능한 컨테이너 찾기
                let current = reviewElement;
                let scrollContainer = null;

                while (current && current !== document.body) {
                    const style = getComputedStyle(current);
                    const overflow = style.overflow || style.overflowY;

                    if ((overflow === 'auto' || overflow === 'scroll') &&
                        current.scrollHeight > current.clientHeight) {
                        // 스크롤 가능한 컨테이너 발견
                        console.log('스크롤 컨테이너 발견:', {
                            tag: current.tagName,
                            className: current.className,
                            scrollHeight: current.scrollHeight,
                            clientHeight: current.clientHeight
                        });
                        scrollContainer = current;
                        break;
                    }
                    current = current.parentElement;
                }

                // 못찾았으면 디폴트로 window 사용
                if (!scrollContainer) {
                    console.log('스크롤 컨테이너를 찾을 수 없음, window 사용');
                    return window;
                }

                return scrollContainer;
            }''');

            return container_handle;
        except Exception as e:
            print(f"[BAEMIN] 스크롤 컨테이너 감지 오류: {str(e)}")
            return None

    async def _scroll_container_to(self, container_handle, position, behavior='smooth'):
        """컨테이너를 특정 위치로 스크롤"""
        try:
            await container_handle.evaluate('''(container, options) => {
                if (container === window) {
                    window.scrollTo({
                        top: options.position,
                        behavior: options.behavior
                    });
                } else {
                    container.scrollTo({
                        top: options.position,
                        behavior: options.behavior
                    });
                }
            }''', {'position': position, 'behavior': behavior})
        except Exception as e:
            print(f"[BAEMIN] 스크롤 오류: {str(e)}")

    async def _get_container_scroll_info(self, container_handle):
        """컨테이너의 스크롤 정보 가져오기"""
        try:
            info = await container_handle.evaluate('''(container) => {
                if (container === window) {
                    return {
                        scrollTop: window.pageYOffset || document.documentElement.scrollTop,
                        scrollHeight: document.documentElement.scrollHeight,
                        clientHeight: window.innerHeight
                    };
                } else {
                    return {
                        scrollTop: container.scrollTop,
                        scrollHeight: container.scrollHeight,
                        clientHeight: container.clientHeight
                    };
                }
            }''')
            return info
        except Exception as e:
            print(f"[BAEMIN] 스크롤 정보 오류: {str(e)}")
            return {'scrollTop': 0, 'scrollHeight': 0, 'clientHeight': 0}

    async def _get_available_reviews_on_page(self, page):
        """현재 페이지에 로드된 모든 리뷰 ID들을 수집"""
        try:
            available_reviews = await page.evaluate('''() => {
                const spans = document.querySelectorAll('span');
                const reviewIds = [];

                for (const span of spans) {
                    const text = span.textContent || '';
                    if (text.includes('리뷰번호')) {
                        // "리뷰번호 12345" 형태에서 숫자 부분 추출
                        const match = text.match(/리뷰번호\\s+(\\d+)/);
                        if (match) {
                            reviewIds.push(match[1]);
                        }
                    }
                }

                return [...new Set(reviewIds)]; // 중복 제거
            }''')

            return available_reviews
        except Exception as e:
            print(f"[BAEMIN] 현재 페이지 리뷰 수집 오류: {str(e)}")
            return []

    async def _scroll_to_top(self, page):
        """페이지 맨 위로 스크롤"""
        try:
            # 스크롤 컨테이너 감지
            container_handle = await self._get_review_scroll_container(page)
            if container_handle:
                await self._scroll_container_to(container_handle, 0, 'smooth')
                print("[BAEMIN] 페이지 맨 위로 스크롤 완료")
            else:
                # 윈도우 스크롤
                await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
                print("[BAEMIN] 윈도우 맨 위로 스크롤 완료")
        except Exception as e:
            print(f"[BAEMIN] 맨 위로 스크롤 오류: {str(e)}")

    async def _find_review_with_scroll(self, page, baemin_review_id, max_scrolls=30):
        """스크롤하면서 특정 리뷰 ID를 찾는 함수"""
        try:
            print(f"\n[BAEMIN] 🔄 스크롤 검색 시작: 리뷰 {baemin_review_id}")

            # 스크롤 컨테이너 찾기
            container_handle = await self._get_review_scroll_container(page)
            if not container_handle:
                print("[BAEMIN] ⚠️ 스크롤 컨테이너를 찾을 수 없음")
                return None

            # 현재 위치에서 시작 (더 이상 맨 위로 이동하지 않음)
            # await self._scroll_container_to(container_handle, 0, 'auto')
            await page.wait_for_timeout(500)

            found_review_element = None
            scroll_count = 0
            last_scroll_height = 0
            no_change_count = 0

            while scroll_count < max_scrolls:
                scroll_count += 1

                # 현재 페이지에서 리뷰 검색
                print(f"[BAEMIN] 🔍 스크롤 {scroll_count}/{max_scrolls} - 리뷰 {baemin_review_id} 검색 중...")

                # 더 정확한 리뷰 검색 로직
                review_search_result = await page.evaluate('''(reviewId) => {
                    console.log(`[SCROLL SEARCH] 리뷰 ID ${reviewId} 검색 중...`);

                    // 1단계: span 요소에서 정확한 텍스트 매칭
                    const spans = document.querySelectorAll('span');
                    let foundSpan = null;

                    for (const span of spans) {
                        const text = span.textContent || '';
                        if (text === '리뷰번호 ' + reviewId || text.includes('리뷰번호 ' + reviewId)) {
                            console.log(`[SCROLL SEARCH] 리뷰번호 스팬 발견: "${text}"`);
                            foundSpan = span;
                            break;
                        }
                    }

                    if (!foundSpan) {
                        console.log(`[SCROLL SEARCH] 리뷰번호 스팬을 찾을 수 없음`);

                        // 디버깅: 현재 페이지의 모든 리뷰번호 출력
                        const allReviewNumbers = [];
                        for (const span of spans) {
                            const text = span.textContent || '';
                            if (text.includes('리뷰번호')) {
                                allReviewNumbers.push(text.trim());
                            }
                        }
                        console.log(`[SCROLL SEARCH] 현재 페이지의 리뷰번호들:`, allReviewNumbers);
                        return { found: false, currentReviews: allReviewNumbers };
                    }

                    // 2단계: 리뷰 컨테이너 찾기
                    let container = foundSpan;
                    while (container && container.parentElement) {
                        container = container.parentElement;
                        if (container.offsetHeight > 100) {
                            console.log(`[SCROLL SEARCH] 리뷰 컨테이너 발견`);
                            // 뷰포트로 스크롤
                            container.scrollIntoView({
                                behavior: 'smooth',
                                block: 'center'
                            });
                            return { found: true, reviewId: reviewId };
                        }
                    }

                    console.log(`[SCROLL SEARCH] 리뷰 컨테이너를 찾을 수 없음`);
                    return { found: false, reviewId: reviewId };
                }''', baemin_review_id)

                if review_search_result.get('found'):
                    print(f"[BAEMIN] ✅ 리뷰 {baemin_review_id} 발견! 뷰포트에 위치시킴")
                    await page.wait_for_timeout(1500)  # 스크롤 안정화 대기

                    # 리뷰 요소 가져오기
                    review_spans = await page.query_selector_all(f'span:has-text("리뷰번호 {baemin_review_id}")')
                    if review_spans:
                        # 컨테이너 찾기
                        for span in review_spans:
                            container = await span.evaluate_handle('''(element) => {
                                let parent = element;
                                while (parent && parent.parentElement) {
                                    parent = parent.parentElement;
                                    if (parent.offsetHeight > 100) {
                                        return parent;
                                    }
                                }
                                return null;
                            }''')

                            if container:
                                found_review_element = container
                                break

                    if found_review_element:
                        return found_review_element

                # 스크롤 정보 가져오기
                scroll_info = await self._get_container_scroll_info(container_handle)
                current_height = scroll_info['scrollHeight']

                # 더 이상 스크롤할 곳이 없는지 확인
                if current_height == last_scroll_height:
                    no_change_count += 1
                    if no_change_count >= 3:
                        print(f"[BAEMIN] ⚠️ 더 이상 스크롤할 콘텐츠가 없음")
                        break
                else:
                    no_change_count = 0
                    last_scroll_height = current_height

                # 다음 위치로 스크롤 (더 작은 단위로)
                new_position = scroll_info['scrollTop'] + scroll_info['clientHeight'] * 0.5
                await self._scroll_container_to(container_handle, new_position)
                await page.wait_for_timeout(800)  # DOM 업데이트 대기 (더 빠르게)

            print(f"[BAEMIN] ❌ 리뷰 {baemin_review_id}를 찾을 수 없음 (스크롤 {scroll_count}회 시도)")
            return None

        except Exception as e:
            print(f"[BAEMIN] 스크롤 검색 중 오류: {str(e)}")
            return None


async def main():
    parser = argparse.ArgumentParser(description='배달의민족 답글 자동 등록')
    parser.add_argument('--username', required=True, help='배민 사업자 아이디')
    parser.add_argument('--password', required=True, help='배민 사업자 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID (platform_store_id)')
    parser.add_argument('--user-id', required=True, help='사용자 ID (UUID)')
    parser.add_argument('--max-replies', type=int, default=10, help='최대 답글 등록 수')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드')
    parser.add_argument('--timeout', type=int, default=30000, help='타임아웃 (ms)')
    
    args = parser.parse_args()
    
    poster = BaeminReplyPoster(
        headless=args.headless,
        timeout=args.timeout
    )
    
    result = await poster.post_replies_batch(
        args.username,
        args.password,
        args.store_id,
        args.user_id,
        args.max_replies
    )
    
    # 결과 출력 (JSON 형태)
    print(f"REPLY_RESULT:{json.dumps(result, ensure_ascii=False)}")
    
    return result['success']


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)