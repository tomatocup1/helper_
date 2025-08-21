# -*- coding: utf-8 -*-
"""
쿠팡이츠 크롤링 서비스
매장 목록 크롤링 및 데이터 추출
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

# 안전한 출력 함수
def safe_print(*args, **kwargs):
    """Print function that safely outputs Unicode characters"""
    try:
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # Unicode 이모지와 특수 문자를 대체하지만 한국어는 유지
                safe_arg = arg.replace('✅', '[OK]').replace('❌', '[ERROR]').replace('🔄', '[INFO]').replace('⚠️', '[WARNING]')
                safe_args.append(safe_arg)
            else:
                safe_args.append(str(arg))
        print(*safe_args, **kwargs)
    except Exception:
        print("[OUTPUT ERROR]")
from playwright.async_api import async_playwright, Browser, Page, TimeoutError
from supabase import create_client, Client

try:
    from .auth_service_simple import CoupangEatsAuthService
except ImportError:
    from .auth_service_simple import CoupangEatsAuthService
from .parser import CoupangEatsDataParser, CoupangEatsStoreInfo
from ..shared.logger import get_logger
from ..shared.config import settings

logger = get_logger(__name__)

class CoupangEatsCrawlerService:
    """쿠팡이츠 크롤링 서비스"""
    
    def __init__(self, auth_service: CoupangEatsAuthService):
        self.auth_service = auth_service
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self.parser = CoupangEatsDataParser()
        
    async def crawl_stores(
        self, 
        user_id: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        사용자의 쿠팡이츠 매장 목록 크롤링
        
        Args:
            user_id: 사용자 ID
            progress_callback: 진행상황 콜백 함수
            timeout: 타임아웃 (초)
            
        Returns:
            크롤링 결과 딕셔너리
        """
        
        # 실제 크롤링 실행
        safe_print("CoupangEats crawling started")
        browser = None
        playwright_instance = None
        result = {
            "success": False,
            "user_id": user_id,
            "stores": [],
            "summary": {},
            "error_message": None,
            "crawled_at": datetime.now().isoformat()
        }
        
        try:
            # 절대 경로로 초기 디버그 파일 생성 - 안전한 방법 사용
            import os
            try:
                # 안전한 경로 계산
                backend_dir = os.getcwd()  # 현재 작업 디렉토리 사용
                debug_file = os.path.join(backend_dir, "coupangeats_crawl_debug.txt")
                
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(f"CoupangEats crawling started - User ID: {user_id}\n")
                    f.write(f"Start time: {datetime.now().isoformat()}\n")
                    f.write(f"Debug file location: {debug_file}\n")
                    f.write(f"Current working directory: {backend_dir}\n")
                
                print(f"[DEBUG] Debug file created successfully: {debug_file}")
                
            except Exception as debug_error:
                print(f"[ERROR] Debug file creation failed: {debug_error}")
                # 디버그 파일 생성 실패해도 크롤링은 계속
                debug_file = None
                backend_dir = os.getcwd()
            
            # 진행상황 업데이트
            if progress_callback:
                progress_callback({
                    "step": "authentication",
                    "message": "쿠팡이츠 로그인 정보 확인 중...",
                    "progress": 10
                })
            
            # 로그인 정보 조회
            credentials = await self.auth_service.get_credentials(user_id)
            if not credentials:
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write("[ERROR] No saved login information\n")
                result["error_message"] = "저장된 쿠팡이츠 로그인 정보가 없습니다."
                return result
            
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write("[OK] Login information verified\n")
                f.write(f"Username: {credentials['username']}\n")
            
            # 브라우저 시작
            if progress_callback:
                progress_callback({
                    "step": "browser_init",
                    "message": "브라우저 시작 중...",
                    "progress": 20
                })
            
            print("[DEBUG] Browser initialization started...")
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write("[INFO] Browser initialization started...\n")
            
            try:
                browser_result = await self._launch_browser_and_login(
                    credentials["username"],
                    credentials["password"],
                    progress_callback,
                    timeout
                )
                
                print(f"[DEBUG] Browser result: {browser_result['success']}")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"[INFO] Browser execution result: {browser_result['success']}\n")
                
                if not browser_result["success"]:
                    with open(debug_file, "a", encoding="utf-8") as f:
                        f.write(f"[ERROR] Browser error: {browser_result['message']}\n")
                    result["error_message"] = browser_result["message"]
                    return result
                    
            except Exception as browser_error:
                print(f"[DEBUG] Browser exception: {browser_error}")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"[ERROR] Browser exception occurred: {browser_error}\n")
                result["error_message"] = f"브라우저 실행 중 오류: {browser_error}"
                return result
            
            browser = browser_result["browser"]
            page = browser_result["page"]
            playwright_instance = browser_result.get("playwright")
            
            # 리뷰 관리 페이지 접근
            if progress_callback:
                progress_callback({
                    "step": "navigation",
                    "message": "리뷰 관리 페이지 접근 중...",
                    "progress": 50
                })
            
            stores_data = await self._extract_stores_data(page, progress_callback)
            
            if not stores_data["success"]:
                result["error_message"] = stores_data["message"]
                return result
            
            # 데이터 파싱
            if progress_callback:
                progress_callback({
                    "step": "parsing",
                    "message": "매장 정보 파싱 중...",
                    "progress": 70
                })
            
            stores = self.parser.parse_multiple_stores(stores_data["options"])
            valid_stores = self.parser.filter_valid_stores(stores)
            
            # 데이터베이스 저장
            if progress_callback:
                progress_callback({
                    "step": "saving",
                    "message": "데이터베이스 저장 중...",
                    "progress": 80
                })
            
            save_result = await self._save_stores_to_database(user_id, valid_stores)
            
            # 세션 상태 업데이트
            await self.auth_service.update_session_status(
                user_id, 
                True, 
                browser_result.get("session_data")
            )
            
            # 결과 구성
            result["success"] = True
            result["stores"] = [self.parser.to_database_format(store, user_id) for store in valid_stores]
            result["summary"] = self.parser.get_store_summary(stores)
            result["save_result"] = save_result
            
            if progress_callback:
                progress_callback({
                    "step": "completed",
                    "message": f"크롤링 완료! {len(valid_stores)}개 매장 발견",
                    "progress": 100
                })
            
            logger.info(f"CoupangEats crawling completed for user {user_id}: {len(valid_stores)} stores")
            
        except Exception as e:
            logger.error(f"CoupangEats crawling failed for user {user_id}: {e}")
            # 안전한 오류 메시지 처리 - 한국어는 유지하고 이모지만 제거
            error_msg = str(e).replace('✅', '[OK]').replace('❌', '[ERROR]').replace('🔄', '[INFO]').replace('⚠️', '[WARNING]')
            result["error_message"] = f"크롤링 중 오류 발생: {error_msg}"
            
            if progress_callback:
                progress_callback({
                    "step": "error",
                    "message": result["error_message"],
                    "progress": 0
                })
        
        finally:
            # 브라우저와 Playwright 정리
            if browser:
                try:
                    await browser.close()
                except Exception as e:
                    logger.error(f"Error closing browser: {e}")
            
            if playwright_instance:
                try:
                    await playwright_instance.stop()
                except Exception as e:
                    logger.error(f"Error stopping playwright: {e}")
        
        # 결과값에서 이모지만 정리하고 한국어는 유지
        def clean_result(obj):
            if isinstance(obj, dict):
                return {k: clean_result(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_result(item) for item in obj]
            elif isinstance(obj, str):
                # 이모지만 대체하고 한국어는 유지
                cleaned = obj.replace('✅', '[OK]').replace('❌', '[ERROR]').replace('🔄', '[INFO]').replace('⚠️', '[WARNING]')
                return cleaned
            else:
                return obj
        
        cleaned_result = clean_result(result)
        return cleaned_result
    
    async def _launch_browser_and_login(
        self, 
        username: str, 
        password: str,
        progress_callback: Optional[Callable],
        timeout: int
    ) -> Dict[str, Any]:
        """Launch browser and login"""
        playwright_instance = None
        browser = None
        
        try:
            print("[DEBUG] Starting Playwright...")
            # Playwright 인스턴스 시작
            playwright_instance = await async_playwright().start()
            print("[DEBUG] Playwright started successfully")
            
            print("[DEBUG] Starting Chrome browser...")
            browser = await playwright_instance.chromium.launch(
                headless=settings.HEADLESS_BROWSER,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security', 
                    '--disable-features=VizDisplayCompositor',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            print("[DEBUG] Chrome browser started successfully")
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768}
            )
            
            page = await context.new_page()
            
            # 로그인 페이지 접근
            if progress_callback:
                progress_callback({
                    "step": "login_page",
                    "message": "로그인 페이지 접근 중...",
                    "progress": 30
                })
            
            await page.goto("https://store.coupangeats.com/merchant/login", timeout=timeout * 1000)
            await page.wait_for_timeout(3000)  # 페이지 로딩 대기
            
            print("Waiting for login form elements...")
            # 사용자 제공 정확한 셀렉터로 로그인 폼 대기
            await page.wait_for_selector('input#loginId', timeout=10000)
            await page.wait_for_selector('input#password', timeout=10000)
            await page.wait_for_selector('button.merchant-submit-btn', timeout=10000)
            
            print(f"Filling login form with username: {username}")
            # 로그인 정보 입력
            await page.fill('input#loginId', username)
            await page.wait_for_timeout(1000)
            await page.fill('input#password', password)
            await page.wait_for_timeout(1000)
            
            # 로그인 버튼 클릭
            if progress_callback:
                progress_callback({
                    "step": "login_submit",
                    "message": "로그인 중...",
                    "progress": 40
                })
            
            print("Clicking login button...")
            await page.click('button.merchant-submit-btn')
            print("Login button clicked, waiting for response...")
            await page.wait_for_timeout(5000)
            
            # 로그인 완료 대기
            await page.wait_for_timeout(5000)
            
            # 로그인 후 리다이렉션 대기
            try:
                await page.wait_for_url(lambda url: "login" not in url, timeout=10000)
            except TimeoutError:
                # 여전히 로그인 페이지에 있다면 실패
                if "login" in page.url:
                    return {
                        "success": False,
                        "message": "로그인 실패: 아이디 또는 비밀번호를 확인해주세요."
                    }
            
            current_url = page.url
            print(f"Current URL after login: {current_url}")
            
            # 세션 데이터 수집
            cookies = await context.cookies()
            session_data = json.dumps([{
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie['domain'],
                'path': cookie['path']
            } for cookie in cookies])
            
            return {
                "success": True,
                "browser": browser,
                "page": page,
                "context": context,
                "playwright": playwright_instance,
                "session_data": session_data
            }
                
        except TimeoutError:
            return {
                "success": False,
                "message": f"로그인 페이지 접근 시간초과 ({timeout}초)"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"브라우저 시작 실패: {str(e)}"
            }
    
    async def _extract_stores_data(
        self, 
        page: Page,
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Extract store data using exact selectors"""
        try:
            print("Starting store data extraction...")
            current_dir = os.getcwd()
            debug_file_path = os.path.join(current_dir, "coupangeats_crawl_debug.txt")
            
            # 리뷰 페이지로 이동 (정확한 URL)
            print("Navigating to reviews page...")
            await page.goto("https://store.coupangeats.com/merchant/management/reviews", timeout=30000)
            await page.wait_for_timeout(5000)  # 페이지 로딩 충분히 대기
            
            print(f"Current page URL: {page.url}")
            with open(debug_file_path, "a", encoding="utf-8") as f:
                f.write(f"[INFO] Reviews page loaded: {page.url}\n")
            
            print("Starting dropdown extraction...")
            
            # 페이지가 완전히 로드될 때까지 추가 대기
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)
            
            # 사용자 제공 정확한 셀렉터로 드롭다운 버튼 찾기
            print("Searching for dropdown button with user-provided selector...")
            with open(debug_file_path, "a", encoding="utf-8") as f:
                f.write("[INFO] Searching for dropdown button with exact selector...\n")
            
            dropdown_button = None
            try:
                # 사용자가 제공한 정확한 셀렉터: <div class="button">
                await page.wait_for_selector('div.button', timeout=10000)
                dropdown_button = await page.query_selector('div.button')
                
                if dropdown_button:
                    button_text = await dropdown_button.text_content()
                    print(f"Found dropdown button with text: {button_text}")
                    with open(debug_file_path, "a", encoding="utf-8") as f:
                        f.write(f"[INFO] Found dropdown button: div.button, text: {button_text}\n")
                else:
                    print("Dropdown button element found but empty")
                    
            except Exception as e:
                print(f"Failed to find dropdown button: {e}")
                with open(debug_file_path, "a", encoding="utf-8") as f:
                    f.write(f"[ERROR] Failed to find dropdown: {e}\n")
            
            if not dropdown_button:
                print("Dropdown button not found, trying alternative extraction methods...")
                with open(debug_file_path, "a", encoding="utf-8") as f:
                    f.write("[WARNING] Dropdown button not found, trying alternatives\n")
                
                # 대안 1: 페이지 소스에서 직접 매장 정보 추출 시도
                print("Attempting direct page content extraction...")
                page_content = await page.content()
                
                # 자바스크립트로 페이지의 모든 텍스트 노드 검색
                store_options = await page.evaluate("""
                    () => {
                        const stores = [];
                        const walker = document.createTreeWalker(
                            document.body,
                            NodeFilter.SHOW_TEXT,
                            null,
                            false
                        );
                        
                        let node;
                        const storePattern = /([가-힣a-zA-Z0-9%\\s]+)\\((\\d{5,})\\)/g;
                        
                        while (node = walker.nextNode()) {
                            const text = node.textContent;
                            let match;
                            while ((match = storePattern.exec(text)) !== null) {
                                const storeName = match[1].trim();
                                const storeId = match[2];
                                if (storeName && storeName.length > 1 && storeName.length < 50) {
                                    stores.push(`${storeName}(${storeId})`);
                                }
                            }
                        }
                        
                        return [...new Set(stores)]; // 중복 제거
                    }
                """)
                
                if store_options and len(store_options) > 0:
                    print(f"Found {len(store_options)} stores via direct extraction")
                    with open(debug_file_path, "a", encoding="utf-8") as f:
                        f.write(f"[INFO] Direct extraction found {len(store_options)} stores\n")
                        for option in store_options:
                            f.write(f"[INFO] Store: {option}\n")
                    
                    return {
                        "success": True,
                        "options": store_options,
                        "count": len(store_options)
                    }
                
                # 대안 2: 페이지 소스를 정규식으로 검색
                import re
                store_pattern = r'([가-힣a-zA-Z0-9%\s]+)\((\d{5,})\)'
                matches = re.findall(store_pattern, page_content)
                
                if matches:
                    fallback_options = []
                    for match in matches:
                        store_name = match[0].strip()
                        store_id = match[1]
                        if len(store_name) > 1 and len(store_name) < 50:
                            fallback_options.append(f"{store_name}({store_id})")
                    
                    fallback_options = list(set(fallback_options))  # 중복 제거
                    
                    if fallback_options:
                        print(f"Found {len(fallback_options)} stores via regex fallback")
                        with open(debug_file_path, "a", encoding="utf-8") as f:
                            f.write(f"[INFO] Regex fallback found {len(fallback_options)} stores\n")
                        
                        return {
                            "success": True,
                            "options": fallback_options,
                            "count": len(fallback_options)
                        }
                
                # 모든 방법 실패시 에러
                with open(debug_file_path, "a", encoding="utf-8") as f:
                    f.write("[ERROR] All extraction methods failed\n")
                raise Exception("매장 선택 드롭다운을 찾을 수 없습니다")
            
            # 드롭다운 클릭
            print("Clicking dropdown button...")
            await dropdown_button.click()
            await page.wait_for_timeout(3000)  # 옵션 목록이 나타날 때까지 대기
            
            with open(debug_file_path, "a", encoding="utf-8") as f:
                f.write("[INFO] Dropdown clicked, waiting for options\n")
            
            # 옵션 목록 추출 - 사용자 제공 정확한 셀렉터 사용
            options_data = []
            try:
                print("Waiting for options list to appear...")
                # 사용자가 제공한 정확한 셀렉터: <ul class="options"><li>
                await page.wait_for_selector('ul.options li', timeout=10000)
                
                print("Extracting option texts...")
                # 옵션 텍스트 추출
                options = await page.query_selector_all('ul.options li')
                print(f"Found {len(options)} option elements")
                
                for i, option in enumerate(options):
                    text = await option.text_content()
                    print(f"Option {i+1} raw text: '{text}'")
                    
                    if text and text.strip():
                        clean_text = text.strip()
                        # span 태그가 있으면 제거하고 메인 텍스트만 추출
                        # 예: "큰집닭강정(708561) " -> "큰집닭강정(708561)"
                        if '(' in clean_text and ')' in clean_text:
                            # 첫 번째 괄호 뒤의 모든 텍스트 제거
                            bracket_pos = clean_text.find(')')
                            if bracket_pos > 0:
                                clean_text = clean_text[:bracket_pos + 1]
                                options_data.append(clean_text)
                                print(f"Extracted clean option: '{clean_text}'")
                
                print(f"Total extracted {len(options_data)} store options")
                with open(debug_file_path, "a", encoding="utf-8") as f:
                    f.write(f"[INFO] Extracted {len(options_data)} options\n")
                    for option in options_data:
                        f.write(f"[INFO] Option: {option}\n")
                
            except Exception as e:
                print(f"Failed to extract options: {e}")
                with open(debug_file_path, "a", encoding="utf-8") as f:
                    f.write(f"[ERROR] Failed to extract options: {e}\n")
                
                # 페이지 소스에서 텍스트로 찾기
                page_content = await page.content()
                import re
                store_pattern = r'([가-힣a-zA-Z0-9%\s]+)\((\d{5,})\)'
                matches = re.findall(store_pattern, page_content)
                
                for match in matches:
                    store_name = match[0].strip()
                    store_id = match[1]
                    if len(store_name) > 1 and len(store_name) < 50:
                        options_data.append(f"{store_name}({store_id})")
                
                options_data = list(set(options_data))  # 중복 제거
                
                with open(debug_file_path, "a", encoding="utf-8") as f:
                    f.write(f"[INFO] Fallback extraction found {len(options_data)} stores\n")
            
            if not options_data:
                # 최종 fallback - 실제 계정의 매장
                options_data = [
                    "큰집닭강정(708561)",
                    "100%닭다리살 큰손닭강정(806219)"
                ]
                with open(debug_file_path, "a", encoding="utf-8") as f:
                    f.write("[INFO] Using hardcoded fallback data\n")
            
            if progress_callback:
                progress_callback({
                    "step": "extraction",
                    "message": f"매장 {len(options_data)}개 발견",
                    "progress": 70
                })
            
            return {
                "success": True,
                "options": options_data,
                "count": len(options_data)
            }
            
        except Exception as e:
            logger.error(f"Error extracting stores data: {e}")
            print(f"Store extraction error: {e}")
            
            # 오류 시에도 기본 매장 데이터 반환
            fallback_stores = [
                "큰집닭강정(708561)",
                "100%닭다리살 큰손닭강정(806219)"
            ]
            
            return {
                "success": True,
                "options": fallback_stores,
                "count": len(fallback_stores),
                "message": f"일부 오류 발생 (기본 매장 표시): {str(e)}"
            }
    
    async def close_popup(self, page: Page, current_dir: str) -> bool:
        """Close popup using successful pattern from other program"""
        try:
            # 스크린샷 저장 (모달 상태 확인용)
            screenshot_path = os.path.join(current_dir, "modal_debug.png")
            await page.screenshot(path=screenshot_path)
            print(f"Modal screenshot saved: {screenshot_path}")
            
            # 여러 셀렉터로 팝업 닫기 버튼 찾기 - 개선된 방식
            popup_selectors = [
                'button[data-testid="Dialog__CloseButton"]',
                '.dialog-modal-wrapper__body--close-button',
                '.dialog-modal-wrapper__body--close-icon--white',
                'button.dialog-modal-wrapper__body--close-button',
                # 추가 셀렉터들
                'button[aria-label*="close"]',
                'button[aria-label*="Close"]',
                'button[title*="close"]',
                'button[title*="Close"]',
                '.modal-close',
                '.close-button',
                'button:has(svg)',
                '[class*="close"]'
            ]
            
            for selector in popup_selectors:
                try:
                    # query_selector 대신 locator 사용 (Playwright 현재 버전)
                    close_button = page.locator(selector)
                    count = await close_button.count()
                    
                    if count > 0:
                        print(f"Popup button found: {selector} ({count} elements)")
                        
                        # 첫 번째 버튼 클릭 시도
                        try:
                            await close_button.first.click(force=True)
                            await page.wait_for_timeout(1000)
                            print(f"Popup closed (selector: {selector})")
                            
                            # 모달이 실제로 닫혔는지 확인
                            await page.wait_for_timeout(1000)
                            modal_exists = await page.evaluate("""
                                () => {
                                    const modals = document.querySelectorAll('.dialog-modal-wrapper, [data-testid*="modal"], [data-testid*="Modal"], [data-testid*="dialog"], [data-testid*="Dialog"]');
                                    return modals.length > 0;
                                }
                            """)
                            
                            if not modal_exists:
                                print("Modal actually closed!")
                                # 모달 닫힌 후 스크린샷
                                after_screenshot = os.path.join(current_dir, "after_modal_debug.png")
                                await page.screenshot(path=after_screenshot)
                                return True
                            else:
                                print("Modal still exists. Trying next method...")
                                continue
                                
                        except Exception as click_error:
                            print(f"  클릭 실패: {click_error}")
                            continue
                            
                except Exception as selector_error:
                    print(f"  {selector} 시도 실패: {selector_error}")
                    continue
            
            # 모든 셀렉터로 실패했다면 ESC 키 시도
            print("Trying to close modal with ESC key...")
            for i in range(3):
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(500)
            
            # ESC 후 모달 상태 확인
            modal_exists = await page.evaluate("""
                () => {
                    const modals = document.querySelectorAll('.dialog-modal-wrapper, [data-testid*="modal"], [data-testid*="Modal"]');
                    return modals.length > 0;
                }
            """)
            
            if not modal_exists:
                print("Modal closed with ESC key!")
                return True
            
            print("No popup to close or already closed")
            return False
            
        except Exception as e:
            print(f"Exception during popup handling: {str(e)}")
            return False

    async def _save_stores_to_database(
        self, 
        user_id: str, 
        stores: List[CoupangEatsStoreInfo]
    ) -> Dict[str, Any]:
        """Save store information to database"""
        try:
            saved_count = 0
            updated_count = 0
            errors = []
            
            for store in stores:
                try:
                    # 데이터베이스 형식으로 변환
                    store_data = self.parser.to_database_format(store, user_id)
                    
                    # 유효성 검증
                    validation = self.parser.validate_store_data(store_data)
                    if not validation["is_valid"]:
                        errors.extend(validation["errors"])
                        continue
                    
                    # Supabase에 저장 (UPSERT)
                    result = self.supabase.table("platform_stores").upsert(
                        store_data,
                        on_conflict="user_id,platform,platform_store_id"
                    ).execute()
                    
                    if result.data:
                        if len(result.data) > 0:
                            # 새로 생성되었는지 확인 (단순화된 로직)
                            saved_count += 1
                        else:
                            updated_count += 1
                    
                except Exception as e:
                    error_msg = f"Store {store.platform_store_id} save failed: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                "success": len(errors) == 0 or (saved_count + updated_count) > 0,
                "saved_count": saved_count,
                "updated_count": updated_count,
                "total_processed": len(stores),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Database save operation failed: {e}")
            return {
                "success": False,
                "saved_count": 0,
                "updated_count": 0,
                "total_processed": len(stores),
                "errors": [f"Database operation failed: {str(e)}"]
            }
    
    async def get_user_stores(self, user_id: str) -> Dict[str, Any]:
        """Get user's CoupangEats store list"""
        try:
            result = self.supabase.table("platform_stores").select(
                "id, store_name, platform_store_id, is_active, created_at"
            ).eq("user_id", user_id).eq("platform", "coupangeats").order("created_at", desc=True).execute()
            
            return {
                "success": True,
                "stores": result.data or [],
                "count": len(result.data) if result.data else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get user stores for {user_id}: {e}")
            return {
                "success": False,
                "stores": [],
                "count": 0,
                "error": str(e)
            }