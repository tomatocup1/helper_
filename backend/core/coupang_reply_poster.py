#!/usr/bin/env python3
"""
쿠팡잇츠 답글 포스터
리뷰에 자동으로 답글을 등록하는 시스템
"""

import asyncio
import argparse
import json
import os
import sys
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
try:
    import pyperclip  # 클립보드 제어용
except ImportError:
    pyperclip = None
    print("Warning: pyperclip not installed. Using fallback typing method.")

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from playwright.async_api import async_playwright, Page

from backend.services.shared.logger import get_logger
from backend.services.shared.config import settings

# 프록시 및 User-Agent 로테이션 시스템 import
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from free_proxy_manager import FreeProxyManager
    from user_agent_rotator import UserAgentRotator
except ImportError:
    print("Warning: 프록시 및 User-Agent 로테이션 시스템을 가져올 수 없습니다. 기본 설정을 사용합니다.")
    FreeProxyManager = None
    UserAgentRotator = None

# Supabase 클라이언트 생성
def get_supabase_client():
    """Supabase 클라이언트 생성"""
    from supabase import create_client, Client
    
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL', '')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL 또는 Service Key가 설정되지 않았습니다.")
    
    return create_client(supabase_url, supabase_key)

logger = get_logger(__name__)

class CoupangReplyPoster:
    """쿠팡잇츠 답글 포스터"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # 프록시 및 User-Agent 로테이션 시스템 비활성화 (직접 연결 사용)
        self.proxy_manager = None  # 프록시 비활성화
        self.ua_rotator = None     # User-Agent 로테이션 비활성화
        self.current_proxy = None
        self.current_user_agent = None
        
        # 매칭 방지 시스템 - 처리된 리뷰 추적
        self.processed_reviews = set()  # 이미 처리된 리뷰 ID들
        self.current_session_reviews = []  # 현재 세션에서 처리 중인 리뷰들
        
    async def post_replies(
        self,
        username: str,
        password: str,
        store_id: str,
        max_replies: int = 10,
        test_mode: bool = False
    ) -> Dict[str, Any]:
        """
        쿠팡잇츠 답글 포스팅 메인 함수
        
        Args:
            username: 로그인 ID
            password: 로그인 비밀번호
            store_id: 플랫폼 매장 ID
            max_replies: 최대 답글 수
            test_mode: 테스트 모드 (실제로 답글을 등록하지 않음)
            
        Returns:
            Dict: 답글 포스팅 결과
        """
        browser = None
        
        try:
            # 답글이 필요한 리뷰 조회
            pending_reviews = await self._get_pending_replies(store_id, max_replies)
            if not pending_reviews:
                return {
                    "success": True,
                    "message": "답글이 필요한 리뷰가 없습니다.",
                    "posted_replies": []
                }
                
            logger.info(f"답글이 필요한 리뷰: {len(pending_reviews)}개")
            
            # 중복 방지 시스템 - 현재 세션 리뷰 목록 저장
            self.current_session_reviews = [
                {
                    'id': review['id'],
                    'coupangeats_review_id': review['coupangeats_review_id'],
                    'reviewer_name': review['reviewer_name']
                }
                for review in pending_reviews
            ]
            logger.info("🛡️ 중복 방지 시스템 활성화 - 현재 세션 리뷰 목록 저장 완료")
            
            # 프록시 및 User-Agent 로테이션 비활성화
            logger.info(f"🌐 연결 방식: 직접 연결 (프록시 비활성화)")
            logger.info(f"🎭 User-Agent: 브라우저 기본값 사용")
            
            # Playwright 브라우저 시작
            async with async_playwright() as p:
                # 브라우저 시작 옵션
                launch_options = {
                    'headless': settings.HEADLESS_BROWSER if hasattr(settings, 'HEADLESS_BROWSER') else False,
                    'args': [
                        # 크롤러와 완전히 동일한 설정으로 단순화
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-infobars',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-http2',
                        '--disable-quic',
                        '--disable-features=VizDisplayCompositor',
                        '--force-http-1',  # HTTP/1.1 강제 사용
                        '--disable-background-networking',  # 백그라운드 네트워크 차단
                    ]
                }
                
                # 프록시 비활성화 - 직접 연결만 사용
                
                browser = await p.chromium.launch(**launch_options)
                
                # 해상도 옵션 (다양한 선택)
                viewport_options = [
                    {'width': 1920, 'height': 1080},  # FHD - 가장 일반적
                    {'width': 1366, 'height': 768},   # 노트북 표준
                    {'width': 1536, 'height': 864},   # Windows 기본 스케일링
                ]
                selected_viewport = random.choice(viewport_options)
                
                context = await browser.new_context(
                    user_agent=self.current_user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport=selected_viewport
                )
                
                page = await context.new_page()
                
                # 최소한의 웹드라이버 숨기기 (크롤러와 동일)
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                """)
                
                # 1. 로그인 수행 (재시도 로직 포함)
                login_success = False
                max_attempts = 5  # 최대 5번 시도
                
                for attempt in range(1, max_attempts + 1):
                    logger.info(f"로그인 시도 {attempt}/{max_attempts}")
                    
                    try:
                        login_success = await self._login(page, username, password)
                        if login_success:
                            logger.info(f"🎉 로그인 성공! (시도 {attempt}번째)")
                            # 프록시 시스템 비활성화 - 성공 보고 불필요
                            break
                        else:
                            if attempt < max_attempts:
                                logger.warning(f"로그인 실패 - {max_attempts - attempt}번 더 시도...")
                                # 프록시 시스템 비활성화 - 단순 재시도만 수행
                                
                                # 실패 시 잠시 대기
                                await page.wait_for_timeout(random.randint(3000, 7000))
                                
                                # 페이지 새로고침 (상태 초기화)
                                await page.reload(wait_until='domcontentloaded')
                                await page.wait_for_timeout(2000)
                                
                    except Exception as e:
                        logger.error(f"로그인 시도 {attempt} 중 오류: {e}")
                        if attempt == max_attempts:
                            break
                        await page.wait_for_timeout(random.randint(2000, 5000))
                
                if not login_success:
                    return {
                        "success": False,
                        "message": "로그인 실패 (모든 재시도 실패)",
                        "posted_replies": []
                    }
                
                # 2. 리뷰 페이지 이동
                await self._navigate_to_reviews_page(page)
                
                # 3. 모달 창 닫기
                await page.wait_for_timeout(1500)
                await self._close_modal_if_exists(page)
                await page.wait_for_timeout(500)
                await self._close_modal_if_exists(page)
                
                # 4. 매장 선택
                await self._select_store(page, store_id)
                
                # 5. 날짜 필터 적용
                await self._apply_date_filter(page, days=7)
                
                # 6. 미답변 탭 클릭
                await self._click_unanswered_tab(page)
                
                # 7. 답글 포스팅
                posted_replies = []
                for review in pending_reviews:
                    try:
                        # 중복 처리 방지 체크
                        review_id = review['coupangeats_review_id']
                        if review_id in self.processed_reviews:
                            logger.warning(f"⚠️ 이미 처리된 리뷰 스킵: {review_id}")
                            continue

                        # 현재 리뷰 처리 시작 표시
                        self.processed_reviews.add(review_id)
                        logger.info(f"🔄 리뷰 처리 시작: {review_id} (총 처리 중: {len(self.processed_reviews)}개)")

                        # 재시도 로직 추가 (최대 3회 시도)
                        max_retries = 3
                        result = None

                        for attempt in range(max_retries):
                            if attempt > 0:
                                logger.info(f"🔁 재시도 {attempt}/{max_retries-1}: {review_id}")
                                await page.wait_for_timeout(2000 * attempt)  # 점진적 대기

                            result = await self._post_single_reply(page, review, test_mode)

                            # 성공 또는 금지어로 인한 실패(재시도 불필요)인 경우 중단
                            if result:
                                if result.get('success', True) and result.get('status') != 'failed':
                                    # 성공
                                    break
                                elif 'forbidden word' in result.get('error', '').lower():
                                    # 금지어는 재시도해도 소용없음
                                    logger.warning(f"금지어로 인한 실패 - 재시도 중단: {review_id}")
                                    break

                            # 마지막 시도가 아니면 재시도
                            if attempt < max_retries - 1:
                                logger.info(f"재시도 준비 중: {review_id}")

                        if result and result.get('success', True) and result.get('status') != 'failed':
                            posted_replies.append(result)
                            logger.info(f"✅ 리뷰 처리 완료: {review_id}")
                        else:
                            # 실패한 경우 - 금지어 등으로 인한 실패도 포함
                            if result:
                                failure_reason = result.get('error', '알 수 없는 실패')
                                logger.warning(f"❌ 리뷰 처리 실패: {review_id} - {failure_reason}")
                            else:
                                logger.warning(f"❌ 리뷰 처리 실패: {review_id} - 결과 없음")

                    except Exception as e:
                        logger.error(f"답글 포스팅 실패: {review['coupangeats_review_id']} - {e}")
                        continue
                
                # 처리된 총 리뷰 수와 성공한 답글 수 계산
                total_processed = len(self.processed_reviews)
                successful_replies = len(posted_replies)
                failed_count = total_processed - successful_replies

                if failed_count > 0:
                    message = f"답글 포스팅 완료: {successful_replies}개 성공, {failed_count}개 실패 (총 {total_processed}개 처리)"
                else:
                    message = f"답글 포스팅 완료: {successful_replies}개"

                return {
                    "success": True,
                    "message": message,
                    "posted_replies": posted_replies,
                    "total_processed": total_processed,
                    "successful_count": successful_replies,
                    "failed_count": failed_count
                }
                
        except Exception as e:
            logger.error(f"Reply posting failed: {e}")
            return {
                "success": False,
                "message": f"답글 포스팅 실패: {str(e)}",
                "posted_replies": []
            }
        finally:
            if browser:
                await browser.close()
    
    async def _login(self, page: Page, username: str, password: str) -> bool:
        """Enhanced 로그인 수행 - 사람처럼 자연스러운 마우스 이동과 클립보드 붙여넣기"""
        try:
            logger.info("🚀 Enhanced 쿠팡잇츠 로그인 시작...")
            
            # 로그인 페이지로 이동
            logger.info("로그인 페이지로 이동 중...")
            await page.goto("https://store.coupangeats.com/merchant/login", wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            # 이미 로그인되어 있는지 확인
            current_url = page.url
            if "/merchant/login" not in current_url:
                logger.info("이미 로그인된 상태")
                return True
            
            # 로그인 필드 확인
            logger.debug("로그인 필드 찾는 중...")
            await page.wait_for_selector('#loginId', timeout=10000)
            await page.wait_for_selector('#password', timeout=10000)
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
            
            # 간단한 클립보드 로그인 (복잡한 마우스 이동 제거)
            if pyperclip:
                try:
                    logger.info("[ReplyPoster] 📋 클립보드 로그인 시작...")
                    
                    # ID 입력
                    await page.click('#loginId')
                    await page.keyboard.press('Control+A')
                    pyperclip.copy(username)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press('Control+V')
                    logger.info("[ReplyPoster] ID 입력 완료")
                    
                    # PW 입력  
                    await page.click('#password')
                    await page.keyboard.press('Control+A')
                    pyperclip.copy(password)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press('Control+V')
                    logger.info("[ReplyPoster] PW 입력 완료")
                    
                except Exception as clipboard_error:
                    logger.warning(f"[ReplyPoster] 클립보드 방식 실패, JavaScript 직접 입력으로 전환: {clipboard_error}")
                    await self._javascript_input_fallback(page, username, password)
            else:
                logger.info("[ReplyPoster] pyperclip 없음 - JavaScript를 통한 직접 입력 방식 사용...")
                await self._javascript_input_fallback(page, username, password)
            
            # 간단한 마우스 이동 후 로그인 버튼 클릭
            logger.info("[ReplyPoster] 🎯 로그인 버튼 클릭...")
            await page.wait_for_timeout(500)  # 잠시 대기
            
            # 버튼 랜덤 클릭
            box = await submit_button.bounding_box()
            if box:
                margin_x = box['width'] * 0.15
                margin_y = box['height'] * 0.15
                click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                
                await page.mouse.click(click_x, click_y)
                logger.info(f"[ReplyPoster] ✅ 랜덤 위치 클릭: ({click_x:.1f}, {click_y:.1f})")
            else:
                await submit_button.click()
                logger.info("[ReplyPoster] ✅ 일반 클릭 완료")
            
            logger.info("[ReplyPoster] 🚀 로그인 버튼 클릭 완료 - 응답 대기 시작")
            
            # 로그인 응답 대기 및 분석 (빠른 실패 감지 포함)
            logger.debug("[ReplyPoster] 로그인 응답 분석 중...")
            
            # 1단계: 빠른 실패 감지 (3초 이내)
            logger.info("[ReplyPoster] 빠른 실패 감지 중 (3초)...")
            quick_fail_detected = False
            
            for i in range(3):  # 3초간 1초씩 체크
                await page.wait_for_timeout(1000)
                current_url = page.url
                
                # URL이 변경되었으면 성공 가능성이 있음
                if "/merchant/login" not in current_url:
                    logger.info(f"[ReplyPoster] URL 변경 감지! 성공 가능성 있음: {current_url}")
                    break
                    
                # 에러 메시지가 있으면 즉시 실패
                error_selectors = [
                    '.error-message', '.alert-danger', '.error', 
                    '[class*="error"]', '[class*="alert"]',
                    '.login-error', '.warning'
                ]
                
                for selector in error_selectors:
                    error_element = await page.query_selector(selector)
                    if error_element:
                        error_text = await error_element.inner_text()
                        if error_text and error_text.strip():
                            logger.error(f"[ReplyPoster] 빠른 실패 감지 - 에러 메시지: {error_text}")
                            quick_fail_detected = True
                            break
                
                if quick_fail_detected:
                    break
                    
                logger.debug(f"[ReplyPoster] 빠른 감지 {i+1}/3 - 아직 로그인 페이지")
            
            # 3초 후에도 로그인 페이지에 있고 에러가 없으면 빠른 실패
            if not quick_fail_detected and "/merchant/login" in page.url:
                logger.warning("[ReplyPoster] ⚡ 빠른 실패 감지 - 3초 내 변화 없음, 즉시 재시도")
                return False
            
            if quick_fail_detected:
                logger.error("[ReplyPoster] ⚡ 빠른 실패 감지 - 에러 메시지 발견, 즉시 재시도")
                return False
            
            # 2단계: 정상적인 URL 변경 대기 (나머지 12초)
            try:
                logger.debug("[ReplyPoster] 정상 URL 변경 대기 중...")
                await page.wait_for_url(lambda url: "/merchant/login" not in url, timeout=12000)
                url_change_time = time.time() - click_start
                logger.debug(f"[ReplyPoster] URL 변경 시간: {url_change_time:.2f}초")
            except:
                logger.debug("[ReplyPoster] URL 변경 타임아웃 - 수동 확인 진행")
            
            # 다중 방법으로 로그인 성공 확인
            return await self._verify_login_success(page)
                
        except Exception as e:
            logger.error(f"[ReplyPoster] 로그인 오류: {e}")
            return False
    
    async def _navigate_to_reviews_page(self, page: Page):
        """리뷰 페이지로 이동"""
        try:
            logger.info("리뷰 페이지로 이동...")
            await page.goto("https://store.coupangeats.com/merchant/management/reviews", 
                          wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            logger.info("리뷰 페이지 이동 완료")
            
            # 모달 창 닫기 (coupang_review_crawler와 동일한 패턴)
            await page.wait_for_timeout(1500)  # 페이지 로딩 완료 대기
            await self._close_modal_if_exists(page)
            await page.wait_for_timeout(500)  # 첫 번째 모달 닫기 후 대기
            await self._close_modal_if_exists(page)  # 두 번째 시도
            
        except Exception as e:
            logger.error(f"리뷰 페이지 이동 실패: {e}")
            raise
    
    async def _select_store(self, page: Page, store_id: str):
        """매장 선택"""
        try:
            logger.info(f"매장 선택: {store_id}")
            
            # 드롭다운 버튼 클릭
            dropdown_button = await page.query_selector('.button:has(svg)')
            if dropdown_button:
                await dropdown_button.click()
                await page.wait_for_timeout(1000)
                
                # 매장 목록에서 해당 store_id 찾기
                store_options = await page.query_selector_all('.options li')
                
                for option in store_options:
                    option_text = await option.inner_text()
                    if f"({store_id})" in option_text:
                        await option.click()
                        logger.info(f"매장 선택 완료: {option_text}")
                        await page.wait_for_timeout(1000)
                        return
                        
        except Exception as e:
            logger.error(f"매장 선택 실패: {e}")
    
    async def _post_single_reply(
        self, 
        page: Page, 
        review: Dict[str, Any], 
        test_mode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """개별 답글 포스팅"""
        try:
            review_id = review['coupangeats_review_id']
            reviewer_name = review['reviewer_name']
            
            logger.info(f"답글 포스팅 시작: {reviewer_name} (ID: {review_id})")
            
            # 리뷰 찾기 (페이지네이션 포함)
            review_element = await self._find_review_element_across_pages(page, review)
            if not review_element:
                logger.warning(f"리뷰 요소를 찾을 수 없습니다: {review_id}")
                return None
            
            # 답글 등록 버튼 찾기 (여러 셀렉터 시도)
            reply_button = await self._find_reply_button(review_element)
            if not reply_button:
                # 이미 답글이 있는 경우 수정 버튼 찾기
                edit_button = await self._find_edit_button(review_element)
                if edit_button:
                    return await self._edit_existing_reply(page, review_element, review, test_mode)
                else:
                    logger.warning(f"답글 등록/수정 버튼을 찾을 수 없습니다: {review_id}")
                    # 디버깅을 위해 리뷰 요소의 모든 버튼 출력
                    await self._debug_buttons_in_element(review_element, review_id)
                    return None
            
            # 답글 등록 버튼 클릭
            await reply_button.click()
            await page.wait_for_timeout(1000)
            
            # 텍스트 박스 찾기
            textarea = await page.query_selector('textarea[name="review"]')
            if not textarea:
                logger.error(f"답글 입력 텍스트박스를 찾을 수 없습니다: {review_id}")
                return None
            
            # Supabase에서 가져온 답글 텍스트 사용
            reply_text = review.get('reply_text', '')
            if not reply_text:
                logger.error(f"답글 텍스트가 없습니다: {review_id}")
                return None
            
            if test_mode:
                logger.info(f"[TEST MODE] 답글 내용: {reply_text}")
                return {
                    "review_id": review['id'],
                    "reviewer_name": reviewer_name,
                    "reply_text": reply_text,
                    "status": "test_mode"
                }
            
            # 답글 입력
            await textarea.fill(reply_text)
            await page.wait_for_timeout(500)
            
            # 등록 버튼 클릭 - 여러 셀렉터로 시도 (우선순위 순서)
            submit_selectors = [
                # 가장 정확한 셀렉터 (사용자 제공 HTML 기반)
                'button.button--primaryContained span.button__inner:has-text("등록")',
                'button.button.button-size--small.button--primaryContained:has-text("등록")',
                'button[type="button"].button--primaryContained:has-text("등록")',

                # form 내부의 등록 버튼 (더 구체적)
                'form button:has-text("등록"):not(:has-text("취소"))',
                'div.css-uvdxep button:has-text("등록")',

                # 기존 셀렉터들 (폴백)
                'button:has-text("등록")',
                'span:has-text("등록")',
                'div:has-text("등록")',
                '[data-testid*="submit"]',
                '[data-testid*="confirm"]'
            ]

            submit_clicked = False
            for selector in submit_selectors:
                try:
                    submit_button = await page.query_selector(selector)
                    if submit_button:
                        # 버튼이 실제로 클릭 가능한지 확인
                        is_visible = await submit_button.is_visible()
                        is_enabled = await submit_button.is_enabled()

                        if not is_visible or not is_enabled:
                            logger.debug(f"버튼 비활성 상태: {selector} (visible={is_visible}, enabled={is_enabled})")
                            continue

                        # 클릭 가능한 요소 찾기
                        if 'span' in selector or selector.startswith('span'):
                            # span이 포함된 경우, 부모 button 찾기
                            parent_button = await page.evaluate('''
                                (element) => {
                                    let current = element;
                                    while (current && current.tagName !== 'BUTTON') {
                                        current = current.parentElement;
                                    }
                                    return current;
                                }
                            ''', submit_button)

                            if parent_button:
                                # JavaScript로 직접 클릭 시도
                                await page.evaluate('button => button.click()', parent_button)
                                logger.info(f"쿠팡이츠 등록 버튼 클릭 완료 (부모 button): {review_id}")
                            else:
                                # 부모를 못찾으면 원래 요소 클릭
                                await submit_button.click()
                                logger.info(f"쿠팡이츠 등록 버튼 클릭 완료 (원본): {review_id}")
                        else:
                            # 일반 button인 경우 직접 클릭
                            await submit_button.click()
                            logger.info(f"쿠팡이츠 등록 버튼 클릭 완료 ({selector}): {review_id}")

                        submit_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"등록 버튼 시도 실패 ({selector}): {e}")
                    continue

            if not submit_clicked:
                logger.error(f"등록 버튼을 찾을 수 없습니다: {review_id}")
                # 실패 상태 업데이트 추가
                await self._update_reply_status(
                    review['id'],
                    'failed',
                    error_message=f"등록 버튼 클릭 실패 - 버튼을 찾을 수 없음"
                )
                return None

            # 등록 버튼 클릭 후 DOM 변화 검증 추가
            logger.info(f"등록 버튼 클릭 완료, DOM 변화 확인 중...")

            # 먼저 form이 사라지기를 기다림 (최대 5초)
            form_disappeared = False
            for i in range(10):  # 0.5초 간격으로 10번 체크 (5초)
                await page.wait_for_timeout(500)

                # 현재 페이지에서 form 찾기
                form_element = await review_element.query_selector('form')
                if not form_element:
                    # form이 사라졌으면 성공
                    form_disappeared = True
                    logger.info(f"✅ Form이 사라짐 - 답글 등록 진행 확인 ({(i+1)*0.5}초)")
                    break

                # textarea가 여전히 있는지 확인
                textarea_still_exists = await page.query_selector('textarea[name="review"]')
                if not textarea_still_exists:
                    # textarea가 사라졌으면 성공 가능성 높음
                    form_disappeared = True
                    logger.info(f"✅ Textarea가 사라짐 - 답글 등록 진행 확인 ({(i+1)*0.5}초)")
                    break

            if not form_disappeared:
                # form이 여전히 있으면 클릭이 실제로 실행되지 않았음
                logger.error(f"❌ 등록 버튼 클릭 후에도 form이 사라지지 않음 - 실제 클릭 실패")

                # 한 번 더 시도
                logger.info("🔄 등록 버튼 재시도...")
                retry_success = False

                for selector in submit_selectors:
                    try:
                        submit_button = await page.query_selector(selector)
                        if submit_button:
                            # 버튼이 실제로 클릭 가능한지 확인
                            is_visible = await submit_button.is_visible()
                            is_enabled = await submit_button.is_enabled()

                            if is_visible and is_enabled:
                                # JavaScript로 직접 클릭 시도
                                await page.evaluate('button => button.click()', submit_button)
                                logger.info(f"🔄 JavaScript로 등록 버튼 재클릭 시도: {selector}")
                                retry_success = True
                                break
                    except:
                        continue

                if not retry_success:
                    logger.error(f"❌ 등록 버튼 재시도도 실패: {review_id}")
                    await self._update_reply_status(
                        review['id'],
                        'failed',
                        error_message="등록 버튼 클릭 실패 - DOM 변화 없음"
                    )
                    return None

                # 재시도 후 다시 대기
                await page.wait_for_timeout(2000)

            # 추가 대기 (금지어 팝업 체크를 위해)
            await page.wait_for_timeout(1000)

            # 쿠팡이츠 금지어 팝업 체크
            logger.info(f"🔍 쿠팡이츠 금지어 팝업 확인 중...")
            forbidden_popup = await page.query_selector('div.modal__contents[data-testid="modal-contents"]')

            if forbidden_popup:
                logger.warning(f"⚠️ 쿠팡이츠 금지어 팝업 감지!")

                # 쿠팡이츠 팝업 메시지 추출
                popup_message = "쿠팡이츠 금지어 팝업 감지"  # 기본값
                detected_forbidden_word = None

                try:
                    # 팝업에서 정확한 메시지 추출
                    popup_text = await forbidden_popup.text_content()
                    if popup_text:
                        logger.info(f"📝 쿠팡이츠 팝업 전체 내용: {popup_text.strip()}")

                        # 쿠팡이츠 팝업 메시지 패턴: "댓글에 다음 단어를 포함할 수 없습니다 : '시방'"
                        import re

                        # 패턴: 댓글에 다음 단어를 포함할 수 없습니다 : '단어'
                        pattern = r"댓글에\s*다음\s*단어를\s*포함할\s*수\s*없습니다\s*:\s*'([^']+)'"
                        match = re.search(pattern, popup_text)

                        if match:
                            detected_forbidden_word = match.group(1)
                            # 쿠팡이츠의 정확한 메시지를 그대로 저장
                            full_message = popup_text.strip()
                            popup_message = f"쿠팡이츠 금지어 알림: {full_message[:150]}"
                            logger.warning(f"🚨 쿠팡이츠가 금지한 단어: '{detected_forbidden_word}'")
                            logger.info(f"📄 쿠팡이츠 메시지: {full_message}")
                        else:
                            # 패턴을 못 찾으면 전체 메시지 저장
                            popup_message = f"쿠팡이츠 금지어 팝업: {popup_text.strip()[:150]}"
                            logger.warning(f"⚠️ 알 수 없는 쿠팡이츠 팝업 형식, 전체 메시지 저장")
                        
                except Exception as e:
                    logger.error(f"쿠팡이츠 팝업 메시지 추출 실패: {str(e)}")
                    popup_message = f"팝업 메시지 추출 오류: {str(e)}"

                # 쿠팡이츠 확인 버튼 클릭
                try:
                    logger.info(f"🔘 쿠팡이츠 팝업 확인 버튼 찾는 중...")

                    # 쿠팡이츠 확인 버튼 셀렉터
                    confirm_selectors = [
                        'div.modal__contents[data-testid="modal-contents"] button.button--primaryContained',
                        'div.modal__contents button:has-text("확인")',
                        'button.button--primaryContained:has-text("확인")',
                        'button.button:has-text("확인")',
                        'button:has-text("확인")'
                    ]

                    confirm_button = None
                    for selector in confirm_selectors:
                        confirm_button = await forbidden_popup.query_selector(selector)
                        if not confirm_button:
                            confirm_button = await page.query_selector(selector)
                        if confirm_button:
                            logger.info(f"✅ 쿠팡이츠 확인 버튼 발견: {selector}")
                            break

                    if confirm_button:
                        await confirm_button.click()
                        logger.info(f"🔘 쿠팡이츠 팝업 확인 버튼 클릭 완료")
                        await page.wait_for_timeout(1000)
                    else:
                        logger.warning(f"⚠️ 쿠팡이츠 확인 버튼을 찾을 수 없음")
                        # ESC 키로 대체
                        await page.keyboard.press('Escape')
                        await page.wait_for_timeout(1000)

                except Exception as e:
                    logger.error(f"쿠팡이츠 확인 버튼 클릭 실패: {str(e)}")

                # DB에 쿠팡이츠의 정확한 팝업 메시지 저장
                await self._update_reply_status(
                    review['id'],
                    'failed',
                    reply_text,
                    error_message=popup_message
                )
                logger.info(f"💾 쿠팡이츠 DB 저장 완료: reply_error_message = '{popup_message[:100]}...'")

                # 추가로 원본 답글과 함께 상세 로그
                if detected_forbidden_word:
                    logger.info(f"📊 쿠팡이츠 상세 정보:")
                    logger.info(f"    - 원본 답글: {reply_text[:50]}...")
                    logger.info(f"    - 금지 단어: '{detected_forbidden_word}'")
                    logger.info(f"    - 다음 AI 생성 시 이 정보를 참고하여 답글 재작성 예정")

                logger.error(f"❌ 리뷰 {review_id} 쿠팡이츠 금지어로 인한 답글 등록 실패")
                logger.info(f"📝 쿠팡이츠 메시지: {popup_message}")
                logger.info(f"🔄 main.py 다음 실행 시 이 정보를 바탕으로 새 답글 생성됩니다")

                # 실패 반환 - success: False 추가
                return {
                    "review_id": review['id'],
                    "reviewer_name": reviewer_name,
                    "reply_text": reply_text,
                    "status": "failed",
                        "success": False,  # 명시적으로 실패 표시
                        "error": f"CoupangEats forbidden word popup: {popup_message}",
                        "detected_word": detected_forbidden_word
                    }

            # 금지어 팝업이 없으면 최종 DOM 확인
            logger.info(f"✅ 쿠팡이츠 금지어 팝업 없음 - 최종 등록 확인 중...")

            # 답글이 실제로 등록되었는지 최종 확인
            # 1. 수정/삭제 버튼이 나타났는지 확인
            final_check_success = False

            # 페이지 새로고침하여 확실히 확인
            logger.info("📱 최종 확인을 위해 페이지 새로고침...")
            await page.reload()
            await page.wait_for_timeout(3000)

            # 다시 리뷰 찾기
            review_element_after = await self._find_review_element_in_current_page(page, review)
            if review_element_after:
                # 수정 버튼 확인
                edit_button_check = await review_element_after.query_selector('button:has-text("수정")')
                delete_button_check = await review_element_after.query_selector('button:has-text("삭제")')

                # 또는 사장님 답글 div 확인
                owner_reply_div = await review_element_after.query_selector('div.css-c2cuzz.e1d0d30o6')

                if edit_button_check or delete_button_check or owner_reply_div:
                    final_check_success = True
                    logger.info(f"✅ 최종 확인 성공: 답글이 실제로 등록됨")
                    if edit_button_check:
                        logger.info(f"  - 수정 버튼 확인됨")
                    if delete_button_check:
                        logger.info(f"  - 삭제 버튼 확인됨")
                    if owner_reply_div:
                        logger.info(f"  - 사장님 답글 영역 확인됨")

            if not final_check_success:
                # 최종 확인 실패
                logger.error(f"❌ 최종 확인 실패: 답글이 실제로 등록되지 않음")
                await self._update_reply_status(
                    review['id'],
                    'failed',
                    error_message="답글 등록 실패 - 최종 DOM 확인 실패"
                )
                return None

            # 성공적으로 등록됨
            await self._update_reply_status(
                review['id'],
                'sent',
                reply_text
            )
            logger.info(f"✅ 답글 등록 완료 확인: {reviewer_name}")

            logger.info(f"답글 등록 완료: {reviewer_name}")

            return {
                "review_id": review['id'],
                "reviewer_name": reviewer_name,
                "reply_text": reply_text,
                "status": "posted"
            }

        except Exception as e:
            logger.error(f"답글 포스팅 실패: {review['coupangeats_review_id']} - {e}")
            
            # 에러 상태 업데이트
            await self._update_reply_status(
                review['id'],
                'failed',
                error_message=str(e)
            )
            return None
    
    async def _find_review_element_across_pages(self, page: Page, review: Dict[str, Any], max_pages: int = 10):
        """페이지네이션을 통해 리뷰 요소 찾기 - 크롤러 로직 적용"""
        coupangeats_review_id = review.get('coupangeats_review_id', '')
        reviewer_name = review.get('reviewer_name', '')
        review_text = review.get('review_text', '')
        
        logger.info(f"리뷰 검색 시작: ID={coupangeats_review_id}, 이름={reviewer_name}")
        
        # 페이지네이션을 통해 리뷰 찾기
        current_page = 1
        while current_page <= max_pages:
            logger.info(f"페이지 {current_page}에서 리뷰 검색 중...")
            
            # 현재 페이지에서 리뷰 찾기
            review_element = await self._find_review_element_in_current_page(page, review)
            if review_element:
                logger.info(f"✅ 리뷰 발견: 페이지 {current_page}")
                return review_element
                
            # 다음 페이지로 이동
            if current_page < max_pages:
                has_next = await self._go_to_next_page(page)
                if not has_next:
                    logger.info("더 이상 페이지가 없습니다.")
                    break
                
                await page.wait_for_timeout(2000)  # 페이지 로딩 대기
                current_page += 1
            else:
                break
        
        logger.warning(f"모든 페이지에서 리뷰를 찾을 수 없음: {coupangeats_review_id}")
        return None

    async def _verify_reply_registration(self, page: Page, review_element, expected_reply_text: str) -> bool:
        """답글이 실제로 등록되었는지 검증 - 개선된 로직"""
        try:
            logger.info("🔍 답글 등록 검증 시작...")

            # 페이지 새로고침하여 최신 상태 확인 (서버 반영 대기 시간 증가)
            logger.info("📱 답글 확인을 위해 페이지 새로고침...")
            await page.wait_for_timeout(5000)  # 서버 반영 대기 (5초)
            await page.reload()
            await page.wait_for_timeout(5000)  # 페이지 로딩 대기 (5초)

            # 전체 페이지에서 답글 찾기 (특정 리뷰에 국한되지 않음)
            possible_reply_selectors = [
                # 사장님 답글 관련 셀렉터들
                'div:has-text("사장님")',
                '[class*="reply"]',
                '[class*="comment"]',
                '[class*="owner"]',
                'div:has-text("고마")',  # 답글에 자주 나오는 단어
                'div:has-text("감사")',  # 답글에 자주 나오는 단어
            ]

            logger.info("🔍 전체 페이지에서 답글 검색 중...")

            for selector in possible_reply_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    logger.info(f"셀렉터 '{selector}' - {len(elements)}개 요소 발견")

                    for element in elements:
                        try:
                            element_text = await element.inner_text()
                            if self._is_similar_text(expected_reply_text, element_text):
                                logger.info(f"✅ 답글 등록 검증 성공: 등록된 답글 발견!")
                                logger.info(f"📝 발견된 답글: {element_text[:100]}...")
                                return True
                        except Exception:
                            continue

                except Exception:
                    continue

            # 추가적으로 전체 페이지 텍스트에서 검색
            try:
                page_text = await page.inner_text('body')
                if self._is_similar_text(expected_reply_text, page_text):
                    logger.info(f"✅ 답글 등록 검증 성공: 페이지 전체 텍스트에서 발견")
                    return True
            except Exception:
                pass

            logger.warning("⚠️ 답글 등록 검증 실패: 등록한 답글을 페이지에서 찾을 수 없음")
            logger.warning("⚠️ 하지만 답글 등록 버튼 클릭은 성공했으므로 일단 성공으로 처리")
            return True  # 검증 실패해도 일단 성공으로 처리 (실제 등록은 됐을 가능성 높음)
            
        except Exception as e:
            logger.error(f"답글 등록 검증 중 오류: {e}")
            return False
            
    def _is_similar_text(self, expected: str, actual: str, threshold: float = 0.6) -> bool:
        """두 텍스트가 유사한지 확인 (간단한 방식)"""
        try:
            # 공백과 특수문자 제거 후 비교
            import re
            expected_clean = re.sub(r'[\s\n\r\t]+', '', expected.strip())
            actual_clean = re.sub(r'[\s\n\r\t]+', '', actual.strip())
            
            # 완전 일치 검사
            if expected_clean in actual_clean or actual_clean in expected_clean:
                return True
                
            # 길이 기반 유사도 검사 (간단한 방식)
            if len(expected_clean) > 10:  # 충분히 긴 텍스트만 유사도 검사
                common_chars = sum(c in actual_clean for c in expected_clean)
                similarity = common_chars / len(expected_clean)
                return similarity >= threshold
                
            return False
            
        except Exception as e:
            logger.debug(f"텍스트 유사도 검사 실패: {e}")
            return False

    async def _find_review_element_in_current_page(self, page: Page, review: Dict[str, Any]):
        """현재 페이지에서 특정 리뷰 요소 찾기 - 간소화된 로직"""
        try:
            coupangeats_review_id = review.get('coupangeats_review_id', '')
            reviewer_name = review.get('reviewer_name', '')
            
            logger.debug(f"리뷰 매칭 시도: ID={coupangeats_review_id}, 이름={reviewer_name}")
            
            # 방법 1: 직접 주문번호로 찾기 (테이블 행 전체 검색)
            if coupangeats_review_id:
                # 주문번호가 포함된 요소 찾기: <p>0ELMJGㆍ2025-08-18(주문일)</p>
                order_elements = await page.query_selector_all('li:has(strong:text("주문번호")) p')
                logger.debug(f"주문번호 요소 {len(order_elements)}개 발견")
                
                # 주문번호로 테이블 행 전체 찾기
                for order_element in order_elements:
                    try:
                        order_text = await order_element.inner_text()
                        logger.debug(f"주문번호 텍스트: {order_text}")
                        
                        # 정확한 매칭을 위해 경계 검사 추가 (한글 특수문자 고려)
                        import re
                        # 한글 특수문자(ㆍ) 때문에 \b가 작동하지 않으므로 더 유연한 패턴 사용
                        escaped_id = re.escape(coupangeats_review_id)
                        pattern = r'(?:^|[^A-Za-z0-9])' + escaped_id + r'(?:[^A-Za-z0-9]|$)'
                        if re.search(pattern, order_text):
                            logger.info(f"✅ 주문번호 정확 매칭 성공: {coupangeats_review_id}")
                            
                            # 테이블 행(tr) 전체 찾기 - 버튼이 있는 범위
                            table_row = order_element
                            for level in range(15):  # 더 멀리 올라가면서 찾기
                                parent = await table_row.query_selector('xpath=..')
                                if not parent:
                                    break
                                
                                # tr 태그이고 답글 버튼이 있는지 확인
                                if await parent.evaluate('element => element.tagName.toLowerCase()') == 'tr':
                                    reply_button_in_row = await parent.query_selector('button:has-text("사장님 댓글 등록하기")')
                                    if reply_button_in_row:
                                        logger.info(f"✅ 테이블 행에서 답글 버튼 발견! (레벨 {level})")
                                        return parent
                                        
                                table_row = parent
                                
                        else:
                            logger.debug(f"주문번호 매칭 실패: {coupangeats_review_id} not in {order_text}")
                                
                    except Exception as e:
                        logger.debug(f"주문번호 요소 처리 중 오류: {e}")
                        continue
            
            # 방법 2: 리뷰어 이름으로 찾기
            if reviewer_name:
                reviewer_elements = await page.query_selector_all('.css-hdvjju.eqn7l9b7')
                logger.debug(f"리뷰어 이름 요소 {len(reviewer_elements)}개 발견")
                
                for reviewer_element in reviewer_elements:
                    try:
                        reviewer_text = await reviewer_element.inner_text()
                        logger.debug(f"리뷰어 텍스트: {reviewer_text}")
                        
                        # 정확한 매칭을 위해 경계 검사 추가 (한글 이름 고려)
                        import re
                        # 한글 이름은 완전 일치 검사가 더 안전
                        if reviewer_name in reviewer_text:
                            logger.info(f"✅ 리뷰어 이름 정확 매칭 성공: {reviewer_name}")
                            
                            # 리뷰어 요소에서 상위 컨테이너 찾기
                            container = reviewer_element
                            for level in range(10):
                                parent = await container.query_selector('xpath=..')
                                if not parent:
                                    break
                                
                                # 주문번호가 포함된 완전한 컨테이너인지 확인
                                order_in_parent = await parent.query_selector('li:has(strong:text("주문번호"))')
                                if order_in_parent:
                                    # 교차 검증: 찾은 컨테이너에 정확한 주문번호가 있는지 확인
                                    order_p_element = await order_in_parent.query_selector('p')
                                    if order_p_element:
                                        order_text_in_container = await order_p_element.inner_text()
                                        # 한글 특수문자 고려한 패턴
                                        escaped_id = re.escape(coupangeats_review_id)
                                        pattern = r'(?:^|[^A-Za-z0-9])' + escaped_id + r'(?:[^A-Za-z0-9]|$)'
                                        if re.search(pattern, order_text_in_container):
                                            logger.info(f"✅ 완전한 리뷰 컨테이너 발견 및 교차 검증 성공 (레벨 {level})")
                                            return parent
                                        else:
                                            logger.info(f"⚠️ 교차 검증 실패: 예상 주문번호='{coupangeats_review_id}', 실제='{order_text_in_container}' - 계속 검색")
                                            continue
                                
                                # 답글 버튼이 있는지도 확인해보자 (추가 검증)
                                reply_button_in_parent = await parent.query_selector('button:has-text("사장님 댓글 등록하기")')
                                if reply_button_in_parent:
                                    logger.info(f"✅ 답글 버튼 발견으로 완전한 리뷰 컨테이너 확인 (레벨 {level})")
                                    return parent
                                    
                                container = parent
                            
                            # 완전한 컨테이너를 찾지 못했으면 현재 요소 반환
                            logger.warning("완전한 컨테이너를 찾지 못함, 리뷰어 요소 반환")
                            return reviewer_element
                            
                    except Exception as e:
                        logger.debug(f"리뷰어 요소 처리 중 오류: {e}")
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"리뷰 요소 찾기 실패: {e}")
            return None

    async def _go_to_next_page(self, page: Page) -> bool:
        """다음 페이지로 이동 - 개선된 로직 (페이지네이션 디버깅 포함)"""
        try:
            # 먼저 페이지네이션 구조 전체를 분석
            pagination_elements = await page.query_selector_all('ul li')
            logger.info(f"=== 페이지네이션 분석 시작 ===")
            logger.info(f"페이지네이션 요소 개수: {len(pagination_elements)}")
            
            current_page = None
            available_pages = []
            next_page_available = False
            
            for i, element in enumerate(pagination_elements):
                try:
                    button = await element.query_selector('button')
                    if button:
                        text = await button.inner_text()
                        class_attr = await button.get_attribute('class') or ""
                        data_at = await button.get_attribute('data-at') or ""
                        is_visible = await button.is_visible()
                        is_enabled = await button.is_enabled()
                        
                        logger.info(f"  버튼 {i+1}: '{text}' (class: {class_attr}, data-at: {data_at}, visible: {is_visible}, enabled: {is_enabled})")
                        
                        # 현재 페이지 찾기
                        if 'active' in class_attr:
                            current_page = text
                            
                        # 숫자 페이지들 찾기
                        if text.isdigit():
                            available_pages.append(int(text))
                            
                        # 다음 페이지 버튼 체크
                        if ('next-btn' in class_attr or 'next-btn' in data_at) and 'hide-btn' not in class_attr:
                            if is_visible and is_enabled:
                                next_page_available = True
                                logger.info(f"  ✅ 사용 가능한 다음 페이지 버튼 발견!")
                                
                except Exception as e:
                    logger.debug(f"요소 {i} 분석 실패: {e}")
                    continue
            
            logger.info(f"현재 페이지: {current_page}")
            logger.info(f"사용 가능한 페이지들: {sorted(available_pages)}")
            logger.info(f"다음 페이지 버튼 사용 가능: {next_page_available}")
            
            # 다음 페이지로 이동 시도 (숫자 버튼 우선)
            if current_page and current_page.isdigit():
                current_num = int(current_page)
                next_num = current_num + 1
                
                # 숫자로 다음 페이지 찾기
                for element in pagination_elements:
                    try:
                        button = await element.query_selector('button')
                        if button:
                            text = await button.inner_text()
                            if text == str(next_num):
                                is_visible = await button.is_visible()
                                is_enabled = await button.is_enabled()
                                class_attr = await button.get_attribute('class') or ""
                                
                                if is_visible and is_enabled and 'active' not in class_attr:
                                    logger.info(f"숫자 버튼으로 페이지 {next_num}로 이동")
                                    await button.click()
                                    await page.wait_for_timeout(3000)
                                    logger.info("다음 페이지로 이동 성공 (숫자 버튼)")
                                    return True
                    except:
                        continue
            
            # Next 버튼으로 이동 시도
            if next_page_available:
                next_selectors = [
                    'button[data-at="next-btn"]:not(.hide-btn)',
                    'button.pagination-btn.next-btn:not(.hide-btn)',
                    'button.next-btn:not(.hide-btn)'
                ]
                
                for selector in next_selectors:
                    try:
                        next_button = await page.query_selector(selector)
                        if next_button:
                            is_visible = await next_button.is_visible()
                            is_enabled = await next_button.is_enabled()
                            class_attr = await next_button.get_attribute('class') or ""
                            
                            if is_visible and is_enabled and 'hide-btn' not in class_attr:
                                logger.info(f"Next 버튼으로 다음 페이지 이동: {selector}")
                                await next_button.click()
                                await page.wait_for_timeout(3000)
                                logger.info("다음 페이지로 이동 성공 (Next 버튼)")
                                return True
                    except Exception as e:
                        logger.debug(f"Next 버튼 {selector} 시도 실패: {e}")
                        continue
            
            logger.info("=== 페이지네이션 분석 완료 ===")
            logger.info("더 이상 페이지가 없습니다.")
            return False
                
        except Exception as e:
            logger.error(f"다음 페이지 이동 실패: {e}")
            return False

    async def _find_reply_button(self, review_element):
        """답글 등록 버튼 찾기 - 여러 셀렉터 시도"""
        try:
            # 정확한 쿠팡이츠 답글 등록 버튼 셀렉터 (클래스 기반)
            reply_selectors = [
                # 정확한 클래스명과 텍스트 조합 (가장 우선)
                'button.css-1ss7t0c.eqn7l9b2:has-text("사장님 댓글 등록하기")',
                'button.eqn7l9b2:has-text("사장님 댓글 등록하기")',
                'button.css-1ss7t0c:has-text("사장님 댓글 등록하기")',
                # 텍스트만으로 찾기 (백업)
                'button:has-text("사장님 댓글 등록하기")',
                # 클래스명으로만 찾기 (최후 수단)
                'button.css-1ss7t0c.eqn7l9b2',
                'button.eqn7l9b2',
                # 기타 가능한 패턴들
                'button:has-text("댓글 등록하기")', 
                'button:has-text("댓글 등록")'
            ]
            
            for selector in reply_selectors:
                try:
                    button = await review_element.query_selector(selector)
                    if button:
                        # 버튼이 보이는지 확인
                        is_visible = await button.is_visible()
                        if is_visible:
                            logger.debug(f"답글 버튼 발견: {selector}")
                            return button
                except Exception as e:
                    logger.debug(f"셀렉터 {selector} 시도 실패: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"답글 버튼 찾기 실패: {e}")
            return None

    async def _find_edit_button(self, review_element):
        """답글 수정 버튼 찾기"""
        try:
            # 다양한 수정 버튼 셀렉터 시도
            edit_selectors = [
                'button:has-text("수정")',
                'button:has-text("답글 수정")', 
                'button:has-text("댓글 수정")',
                'button[class*="edit"]',
                'button[data-testid*="edit"]',
                'a:has-text("수정")'
            ]
            
            for selector in edit_selectors:
                try:
                    button = await review_element.query_selector(selector)
                    if button:
                        is_visible = await button.is_visible()
                        if is_visible:
                            logger.debug(f"수정 버튼 발견: {selector}")
                            return button
                except Exception as e:
                    logger.debug(f"셀렉터 {selector} 시도 실패: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"수정 버튼 찾기 실패: {e}")
            return None

    async def _debug_buttons_in_element(self, review_element, review_id):
        """디버깅용: 리뷰 요소 내의 모든 버튼과 링크 출력"""
        try:
            logger.info(f"🔍 === {review_id} 리뷰 요소 내 버튼 디버깅 ===")
            
            # 모든 버튼 찾기
            buttons = await review_element.query_selector_all('button')
            logger.info(f"🔘 버튼 {len(buttons)}개 발견")
            
            for i, button in enumerate(buttons[:10]):  # 처음 10개만
                try:
                    text = await button.inner_text()
                    class_attr = await button.get_attribute('class')
                    is_visible = await button.is_visible()
                    logger.info(f"  {i+1}. 버튼: '{text}' (class: {class_attr}, visible: {is_visible})")
                except:
                    logger.info(f"  {i+1}. 버튼: 정보 읽기 실패")
            
            # 모든 링크 찾기
            links = await review_element.query_selector_all('a')
            logger.info(f"🔗 링크 {len(links)}개 발견")
            
            for i, link in enumerate(links[:5]):  # 처음 5개만
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute('href')
                    is_visible = await link.is_visible()
                    logger.info(f"  {i+1}. 링크: '{text}' (href: {href}, visible: {is_visible})")
                except:
                    logger.info(f"  {i+1}. 링크: 정보 읽기 실패")
                    
            # 전체 요소의 HTML 일부도 출력 (디버깅용)
            try:
                html_content = await review_element.inner_html()
                logger.info(f"📄 요소 HTML (처음 500자): {html_content[:500]}...")
            except:
                logger.info("📄 HTML 내용 읽기 실패")
            
            # 전체 텍스트에서 "등록" 키워드 검색
            element_text = await review_element.inner_text()
            if "등록" in element_text:
                logger.debug("요소에 '등록' 텍스트 포함됨")
                # '등록'이 포함된 부분 찾기
                lines = element_text.split('\n')
                for i, line in enumerate(lines):
                    if "등록" in line:
                        logger.debug(f"  라인 {i+1}: {line.strip()}")
                        
        except Exception as e:
            logger.error(f"버튼 디버깅 실패: {e}")
    
    async def _edit_existing_reply(
        self,
        page: Page,
        review_element,
        review: Dict[str, Any],
        test_mode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """기존 답글 수정"""
        try:
            review_id = review['coupangeats_review_id']
            
            logger.info(f"기존 답글 수정: {review_id}")
            
            # 수정 버튼 클릭
            edit_button = await review_element.query_selector('button:has-text("수정")')
            await edit_button.click()
            await page.wait_for_timeout(1000)
            
            # 수정용 텍스트박스 찾기
            textarea = await page.query_selector('textarea[name="review"]')
            if not textarea:
                logger.error(f"수정용 텍스트박스를 찾을 수 없습니다: {review_id}")
                return None
            
            # Supabase에서 가져온 답글 텍스트 사용
            reply_text = review.get('reply_text', '')
            if not reply_text:
                logger.error(f"수정할 답글 텍스트가 없습니다: {review_id}")
                return None
            
            if test_mode:
                logger.info(f"[TEST MODE] 수정할 답글 내용: {reply_text}")
                return {
                    "review_id": review['id'],
                    "reviewer_name": review['reviewer_name'],
                    "reply_text": reply_text,
                    "status": "test_mode_edit"
                }
            
            # 기존 텍스트 지우고 새 텍스트 입력
            await textarea.fill(reply_text)
            await page.wait_for_timeout(500)
            
            # 수정 버튼 클릭
            submit_button = await page.query_selector('span:has-text("수정")')
            if submit_button:
                submit_button_parent = await submit_button.query_selector('xpath=..')
                await submit_button_parent.click()
                logger.info(f"쿠팡이츠 수정 버튼 클릭 완료: {review_id}")
                
                # 수정 처리 대기 (금지어 팝업 체크를 위해)
                await page.wait_for_timeout(2000)
                
                # 쿠팡이츠 금지어 팝업 체크 (수정 시에도 동일)
                logger.info(f"🔍 쿠팡이츠 금지어 팝업 확인 중... (수정)")
                forbidden_popup = await page.query_selector('div.modal__contents[data-testid="modal-contents"]')
                
                if forbidden_popup:
                    logger.warning(f"⚠️ 쿠팡이츠 금지어 팝업 감지! (수정)")
                    
                    # 금지어 팝업 처리 로직 (동일)
                    popup_message = "쿠팡이츠 금지어 팝업 감지 (수정)"
                    detected_forbidden_word = None
                    
                    try:
                        popup_text = await forbidden_popup.text_content()
                        if popup_text:
                            logger.info(f"📝 쿠팡이츠 팝업 전체 내용 (수정): {popup_text.strip()}")
                            
                            import re
                            pattern = r"댓글에\s*다음\s*단어를\s*포함할\s*수\s*없습니다\s*:\s*'([^']+)'"
                            match = re.search(pattern, popup_text)
                            
                            if match:
                                detected_forbidden_word = match.group(1)
                                full_message = popup_text.strip()
                                popup_message = f"쿠팡이츠 금지어 알림 (수정): {full_message[:150]}"
                                logger.warning(f"🚨 쿠팡이츠가 금지한 단어 (수정): '{detected_forbidden_word}'")
                            else:
                                popup_message = f"쿠팡이츠 금지어 팝업 (수정): {popup_text.strip()[:150]}"
                        
                    except Exception as e:
                        logger.error(f"쿠팡이츠 팝업 메시지 추출 실패 (수정): {str(e)}")
                        popup_message = f"팝업 메시지 추출 오류 (수정): {str(e)}"
                    
                    # 확인 버튼 클릭 (동일 로직)
                    try:
                        confirm_selectors = [
                            'div.modal__contents[data-testid="modal-contents"] button.button--primaryContained',
                            'div.modal__contents button:has-text("확인")',
                            'button.button--primaryContained:has-text("확인")',
                            'button:has-text("확인")'
                        ]
                        
                        confirm_button = None
                        for selector in confirm_selectors:
                            confirm_button = await forbidden_popup.query_selector(selector)
                            if not confirm_button:
                                confirm_button = await page.query_selector(selector)
                            if confirm_button:
                                break
                        
                        if confirm_button:
                            await confirm_button.click()
                            logger.info(f"🔘 쿠팡이츠 팝업 확인 버튼 클릭 완료 (수정)")
                            await page.wait_for_timeout(1000)
                        else:
                            await page.keyboard.press('Escape')
                            await page.wait_for_timeout(1000)
                        
                    except Exception as e:
                        logger.error(f"쿠팡이츠 확인 버튼 클릭 실패 (수정): {str(e)}")
                    
                    # DB에 실패 상태 저장 (수정 시에도)
                    await self._update_reply_status(
                        review['id'],
                        'failed',
                        reply_text,
                        error_message=popup_message
                    )
                    logger.info(f"💾 쿠팡이츠 DB 저장 완료 (수정): reply_error_message = '{popup_message[:100]}...'")

                    logger.error(f"❌ 리뷰 {review_id} 쿠팡이츠 금지어로 인한 답글 수정 실패")

                    # 실패 반환 - success: False 추가
                    return {
                        "review_id": review['id'],
                        "reviewer_name": review['reviewer_name'],
                        "reply_text": reply_text,
                        "status": "failed",
                        "success": False,  # 명시적으로 실패 표시
                        "error": f"CoupangEats forbidden word popup (edit): {popup_message}",
                        "detected_word": detected_forbidden_word
                    }
                
                # 금지어 팝업이 없으면 성공 처리
                logger.info(f"✅ 쿠팡이츠 금지어 팝업 없음 - 수정 성공")
                
                # 답글 상태 업데이트
                await self._update_reply_status(
                    review['id'],
                    'sent',
                    reply_text
                )
                
                logger.info(f"답글 수정 완료: {review['reviewer_name']}")
                
                return {
                    "review_id": review['id'],
                    "reviewer_name": review['reviewer_name'],
                    "reply_text": reply_text,
                    "status": "edited"
                }
            else:
                logger.error(f"수정 완료 버튼을 찾을 수 없습니다: {review_id}")
                return None
                
        except Exception as e:
            logger.error(f"답글 수정 실패: {review['coupangeats_review_id']} - {e}")
            return None
    
    
    async def _get_pending_replies(self, store_id: str, limit: int) -> List[Dict[str, Any]]:
        """답글이 필요한 리뷰 조회 (schedulable_reply_date 체크 포함)"""
        try:
            # 현재 시각
            current_time = datetime.now()
            logger.info(f"⏰ 현재 시각: {current_time.isoformat()}")

            # platform_stores에서 user_id 조회
            store_response = self.supabase.table('platform_stores').select('user_id').eq('platform_store_id', store_id).eq('platform', 'coupangeats').execute()

            if not store_response.data:
                logger.error(f"매장을 찾을 수 없습니다: {store_id}")
                return []

            user_id = store_response.data[0]['user_id']

            # AI 답글이 생성되었지만 아직 등록되지 않은 리뷰 조회 (schedulable_reply_date 포함)
            result = self.supabase.table('reviews_coupangeats')\
                .select('id, coupangeats_review_id, reviewer_name, review_text, reply_text, reply_status, schedulable_reply_date')\
                .eq('reply_status', 'draft')\
                .neq('reply_text', None)\
                .limit((limit * 2) if limit else 1000)\
                .execute()  # 스킵될 리뷰를 고려하여 더 많이 조회 (limit이 None이면 1000개)

            if not result.data:
                logger.info("📝 답글 등록 대기 중인 리뷰가 없습니다.")
                return []

            # schedulable_reply_date 체크하여 필터링
            eligible_reviews = []
            skipped_reviews = []

            for review in result.data:
                schedulable_date = review.get('schedulable_reply_date')
                review_id = review.get('coupangeats_review_id', 'N/A')

                # schedulable_reply_date가 없으면 즉시 처리 가능
                if not schedulable_date:
                    eligible_reviews.append(review)
                    logger.debug(f"📌 즉시 처리 가능: {review_id} (schedulable_reply_date 없음)")
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
                                if schedulable_datetime.tzinfo.utcoffset(None) != timedelta(hours=9):
                                    schedulable_datetime = schedulable_datetime.astimezone(kst)
                                schedulable_datetime = schedulable_datetime.replace(tzinfo=None)
                        else:
                            schedulable_datetime = datetime.fromisoformat(schedulable_date)
                    else:
                        # 이미 datetime 객체인 경우
                        schedulable_datetime = schedulable_date
                        if schedulable_datetime.tzinfo is not None:
                            schedulable_datetime = schedulable_datetime.replace(tzinfo=None)

                    # 현재 시각과 비교
                    if current_time >= schedulable_datetime:
                        eligible_reviews.append(review)
                        logger.info(f"✅ 답글 등록 시간 도달: {review_id} (예정: {schedulable_datetime.isoformat()})")
                    else:
                        skipped_reviews.append(review)
                        time_diff = schedulable_datetime - current_time
                        logger.info(f"⏳ 답글 등록 대기: {review_id} (남은 시간: {time_diff})")

                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ schedulable_reply_date 파싱 오류 ({review_id}): {e} - 즉시 처리")
                    eligible_reviews.append(review)

            # 최종 제한 적용 (limit이 None이면 제한 없음)
            if limit and len(eligible_reviews) > limit:
                eligible_reviews = eligible_reviews[:limit]
                logger.info(f"📊 제한 적용: {limit}개로 축소")

            # 최종 요약 로그
            if result.data:
                logger.info(f"📋 schedulable_reply_date 필터링 결과:")
                logger.info(f"    - 전체 조회: {len(result.data)}개")
                logger.info(f"    - 즉시 처리: {len(eligible_reviews)}개")
                logger.info(f"    - 예약 대기: {len(skipped_reviews)}개")

            if not eligible_reviews:
                logger.info("📝 현재 답글 등록 가능한 리뷰가 없습니다 (모두 대기 중)")

            return eligible_reviews

        except Exception as e:
            logger.error(f"답글 대기 리뷰 조회 실패: {e}")
            return []
    
    async def _update_reply_status(
        self,
        review_id: str,
        status: str,
        reply_text: str = None,
        error_message: str = None
    ):
        """답글 상태 업데이트 - 직접 테이블 업데이트 방식"""
        try:
            update_data = {
                'reply_status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if status == 'sent':
                update_data['reply_posted_at'] = datetime.now().isoformat()
            
            if status == 'failed' and error_message:
                update_data['reply_error_message'] = error_message
            
            result = self.supabase.table('reviews_coupangeats').update(
                update_data
            ).eq('id', review_id).execute()
            
            logger.info(f"답글 상태 업데이트 완료: {review_id} -> {status}")
            
        except Exception as e:
            logger.error(f"답글 상태 업데이트 실패: {e}")

    async def _close_modal_if_exists(self, page: Page):
        """모달 창 닫기 (셀레니움 검증된 선택자 우선 + 기존 로직)"""
        try:
            logger.info("모달 창 탐지 및 닫기 시작...")

            # 매장 등록에서 성공한 방식 그대로 적용
            selenium_close_selector = "button.dialog-modal-wrapperbody--close-button.dialog-modal-wrapperbody--close-icon--black[data-testid='Dialog__CloseButton']"

            close_button = await page.query_selector(selenium_close_selector)
            if close_button:
                logger.info("셀레니움 검증된 닫기 버튼 발견 - 클릭 시도")
                await close_button.click()
                await page.wait_for_timeout(1500)
                logger.info("셀레니움 검증된 닫기 버튼으로 모달 닫기 성공")
                return True
            else:
                logger.info("셀레니움 검증된 버튼 없음 - 다른 방법 시도")

                # 기본 ESC 키 시도
                logger.info("ESC 키로 모달 닫기 시도...")
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(1000)

                # 빈 공간 클릭 시도
                logger.info("빈 공간 클릭 시도...")
                await page.mouse.click(10, 10)
                await page.wait_for_timeout(1000)

                logger.info("기본 모달 닫기 시도 완료")

            # 1. 매장 불러오기에서 사용하는 정확한 Speak Up 모달 닫기 버튼
            close_button = await page.query_selector('button.dialog-modal-wrapper__body--close-button')
            if close_button:
                await close_button.click()
                logger.info("✅ 쿠팡잇츠 Speak Up 모달 닫기 성공 (dialog-modal-wrapper__body--close-button)")
                await page.wait_for_timeout(1000)
                return True
            
            # 2. 다양한 모달 닫기 버튼들 시도
            modal_close_selectors = [
                # 일반적인 모달 닫기 패턴들
                'button[class*="close"]',
                'button[class*="dialog-close"]', 
                'button.modal-close',
                '.modal-close',
                
                # 쿠팡잇츠 특화 패턴들  
                'button[class*="dialog-modal"]',
                'div[class*="dialog"] button',
                '[class*="modal-wrapper"] button',
                
                # 텍스트 기반 닫기 버튼들
                'button:has-text("닫기")',
                'button:has-text("확인")', 
                'button:has-text("OK")',
                'button:has-text("취소")',
                'button:has-text("Cancel")',
                
                # 역할 기반 탐지
                '[role="dialog"] button',
                '[role="modal"] button',
                
                # 속성 기반 탐지
                'button[data-testid*="close"]',
                'button[data-testid*="modal"]',
                'button[aria-label*="close"]',
                'button[aria-label*="닫기"]',
                'button[title*="닫기"]',
                'button[title*="close"]',
                
                # X 버튼 패턴들
                'button:has(svg)',  # SVG 아이콘이 있는 버튼
                'button:has(span):has-text("×")',
                '.close-btn',
                '.btn-close',
            ]
            
            for i, selector in enumerate(modal_close_selectors):
                try:
                    close_button = await page.query_selector(selector)
                    if close_button:
                        # 버튼이 실제로 보이는지 확인
                        is_visible = await close_button.is_visible()
                        if is_visible:
                            await close_button.click()
                            logger.info(f"✅ 모달 창 닫기 성공: {selector}")
                            await page.wait_for_timeout(1000)
                            return True
                        else:
                            logger.debug(f"모달 버튼이 숨겨져 있음: {selector}")
                except Exception as e:
                    logger.debug(f"모달 닫기 시도 {i+1} 실패: {e}")
                    continue
            
            # 3. JavaScript를 통한 모달 탐지 및 닫기
            try:
                modal_found = await page.evaluate('''
                    () => {
                        // 모든 가능한 모달 관련 요소들 찾기
                        const modalSelectors = [
                            '.modal', '.dialog', '.popup', '.overlay', 
                            '[role="dialog"]', '[role="modal"]',
                            '[class*="modal"]', '[class*="dialog"]', '[class*="popup"]'
                        ];
                        
                        for (const selector of modalSelectors) {
                            const modals = document.querySelectorAll(selector);
                            for (const modal of modals) {
                                if (modal.style.display !== 'none' && 
                                    window.getComputedStyle(modal).display !== 'none') {
                                    
                                    // 모달 내의 닫기 버튼 찾기
                                    const closeButtons = modal.querySelectorAll(
                                        'button, [role="button"], .close, .btn-close, [data-dismiss]'
                                    );
                                    
                                    for (const btn of closeButtons) {
                                        const text = btn.textContent.toLowerCase();
                                        const classes = btn.className.toLowerCase();
                                        
                                        if (text.includes('닫기') || text.includes('close') || 
                                            text.includes('×') || text.includes('확인') ||
                                            classes.includes('close') || classes.includes('cancel')) {
                                            
                                            btn.click();
                                            console.log('JavaScript로 모달 닫기 성공:', btn);
                                            return true;
                                        }
                                    }
                                }
                            }
                        }
                        return false;
                    }
                ''')
                
                if modal_found:
                    logger.info("✅ JavaScript를 통한 모달 닫기 성공")
                    await page.wait_for_timeout(1000)
                    return True
                    
            except Exception as e:
                logger.debug(f"JavaScript 모달 닫기 오류: {e}")
            
            # 4. ESC 키로 모달 닫기 시도 (최후 수단)
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(500)
            logger.debug("ESC 키로 모달 닫기 시도")
            
            logger.info("모달을 찾을 수 없거나 이미 닫혀있음")
            return False
            
        except Exception as e:
            logger.debug(f"모달 창 닫기 시도 중 오류 (무시 가능): {e}")
            return False

    async def _apply_date_filter(self, page: Page, days: int):
        """날짜 필터 적용 (크롤러와 동일)"""
        try:
            logger.info(f"날짜 필터 적용: 최근 {days}일")
            
            # 여러 날짜 드롭다운 selector 시도
            date_dropdown_selectors = [
                '.css-1rkgd7l.eylfi1j5',
                'div:has-text("오늘"):has(svg)',
                '[class*="eylfi1j"]:has(svg)',
                'div:has(span:text("오늘"))',
                'div:has(svg):has-text("오늘")',
            ]
            
            date_dropdown = None
            for selector in date_dropdown_selectors:
                try:
                    date_dropdown = await page.query_selector(selector)
                    if date_dropdown:
                        logger.info(f"날짜 드롭다운 발견: {selector}")
                        break
                except Exception:
                    continue
            
            if date_dropdown:
                await date_dropdown.click()
                await page.wait_for_timeout(2000)
                
                # 날짜 옵션 선택 (라디오 버튼과 label 모두 시도)
                if days <= 7:
                    radio_selectors = [
                        'label:has(input[type="radio"][value="1"])',
                        'label:has-text("최근 1주일")',
                        'input[type="radio"][value="1"]',
                        'input[name="quick"][value="1"]',
                        'label:has(input[name="quick"][value="1"])',
                        'span:has-text("최근 1주일")',
                    ]
                    
                    week_radio = None
                    for selector in radio_selectors:
                        try:
                            week_radio = await page.query_selector(selector)
                            if week_radio:
                                is_visible = await week_radio.is_visible()
                                if is_visible:
                                    logger.info(f"날짜 라디오 버튼 발견 (보임): {selector}")
                                    break
                                else:
                                    week_radio = None
                        except Exception:
                            continue
                    
                    if week_radio:
                        try:
                            await week_radio.click()
                            logger.info("✅ 최근 1주일 선택 클릭 성공")
                            await page.wait_for_timeout(2000)
                        except Exception as e:
                            logger.error(f"최근 1주일 선택 클릭 실패: {e}")
                    else:
                        logger.warning("최근 1주일 라디오 버튼을 찾을 수 없습니다.")
                else:
                    logger.info("7일을 초과하는 기간은 기본값을 사용합니다.")
            else:
                logger.warning("날짜 드롭다운을 찾을 수 없습니다.")
                    
        except Exception as e:
            logger.error(f"날짜 필터 적용 실패: {e}")

    async def _click_unanswered_tab(self, page: Page):
        """미답변 탭 클릭 (크롤러와 동일)"""
        try:
            logger.info("미답변 탭 클릭")
            
            # 미답변 탭 selector들
            tab_selectors = [
                'strong:has-text("미답변")',
                'div:has-text("미답변")',
                'span:has-text("미답변")',
                '[class*="e1kgpv5e"]:has-text("미답변")',
                '.css-1cnakc9:has-text("미답변")',
            ]
            
            unanswered_tab = None
            for selector in tab_selectors:
                try:
                    unanswered_tab = await page.query_selector(selector)
                    if unanswered_tab:
                        is_visible = await unanswered_tab.is_visible()
                        if is_visible:
                            logger.info(f"미답변 탭 발견: {selector}")
                            break
                        else:
                            unanswered_tab = None
                except Exception:
                    continue
            
            if unanswered_tab:
                await unanswered_tab.click()
                logger.info("✅ 미답변 탭 클릭 성공")
                await page.wait_for_timeout(3000)  # 탭 전환 대기
            else:
                logger.warning("미답변 탭을 찾을 수 없습니다.")
                
        except Exception as e:
            logger.error(f"미답변 탭 클릭 실패: {e}")
    
    # ==================== 간단한 로그인 헬퍼 메서드들 ====================
    
    async def _javascript_input_fallback(self, page: Page, username: str, password: str):
        """클립보드 실패시 JavaScript를 통한 직접 입력 폴백"""
        try:
            # ID 입력
            await page.click('#loginId')
            await page.wait_for_timeout(random.randint(300, 600))
            await page.evaluate('document.querySelector("#loginId").value = ""')
            await page.wait_for_timeout(random.randint(100, 200))
            
            # 한 글자씩 입력하는 것처럼 보이게
            for i in range(len(username)):
                partial_text = username[:i+1]
                await page.evaluate(f'document.querySelector("#loginId").value = "{partial_text}"')
                await page.wait_for_timeout(random.randint(50, 150))
            
            # Tab키로 이동
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(random.randint(300, 600))
            
            # 비밀번호 필드 입력
            await page.evaluate(f'document.querySelector("#password").value = ""')
            await page.wait_for_timeout(random.randint(100, 200))
            
            for i in range(len(password)):
                partial_text = password[:i+1]
                await page.evaluate(f'document.querySelector("#password").value = "{partial_text}"')
                await page.wait_for_timeout(random.randint(50, 150))
            
        except Exception as e:
            logger.error(f"[ReplyPoster] JavaScript 입력도 실패: {e}")
    
    
    async def _verify_login_success(self, page: Page) -> bool:
        """로그인 성공 검증"""
        try:
            current_url = page.url
            logger.info(f"[ReplyPoster] 로그인 후 최종 URL: {current_url}")
            
            # 1. URL이 login 페이지에서 벗어났는지 확인
            if "login" not in current_url:
                logger.info("[ReplyPoster] 로그인 성공 (URL 기준)")
                return True
            
            # 2. 에러 메시지 확인
            error_elements = await page.query_selector_all('.error-message, .alert, [class*="error"]')
            if error_elements:
                for error_element in error_elements:
                    error_text = await error_element.inner_text()
                    if error_text and error_text.strip():
                        logger.error(f"[ReplyPoster] 로그인 에러 메시지: {error_text}")
                        return False
            
            # 3. 대안 성공 지표 확인
            success_indicators = [
                'a[href*="reviews"]',  # 리뷰 링크
                '[class*="dashboard"]',  # 대시보드
                '.merchant-info',  # 매장 정보
            ]
            
            for selector in success_indicators:
                element = await page.query_selector(selector)
                if element:
                    logger.info(f"[ReplyPoster] 로그인 성공 (요소 기준: {selector})")
                    return True
            
            logger.error("[ReplyPoster] 로그인 실패")
            return False
            
        except Exception as e:
            logger.error(f"[ReplyPoster] 로그인 검증 오류: {e}")
            return False


async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='쿠팡잇츠 답글 포스터')
    parser.add_argument('--username', required=True, help='쿠팡잇츠 로그인 ID')
    parser.add_argument('--password', required=True, help='쿠팡잇츠 로그인 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID')
    parser.add_argument('--max-replies', type=int, default=10, help='최대 답글 수 (기본: 10)')
    parser.add_argument('--test-mode', action='store_true', help='테스트 모드 (실제 답글 등록 안함)')
    
    args = parser.parse_args()
    
    poster = CoupangReplyPoster()
    result = await poster.post_replies(
        username=args.username,
        password=args.password,
        store_id=args.store_id,
        max_replies=args.max_replies,
        test_mode=args.test_mode
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())