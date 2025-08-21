# -*- coding: utf-8 -*-
"""
쿠팡이츠 크롤링 서비스 - 사용자 스펙 정확히 구현
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

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
    """쿠팡이츠 크롤링 서비스 - 사용자 스펙 정확히 구현"""
    
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
        """사용자의 쿠팡이츠 매장 목록 크롤링"""
        
        result = {
            "success": False,
            "user_id": user_id,
            "stores": [],
            "summary": {},
            "error_message": None,
            "crawled_at": datetime.now().isoformat()
        }
        
        playwright_instance = None
        browser = None
        
        try:
            # 로그인 정보 조회
            credentials = await self.auth_service.get_credentials(user_id)
            if not credentials:
                result["error_message"] = "저장된 쿠팡이츠 로그인 정보가 없습니다."
                return result
            
            print(f"로그인 정보 확인됨: {credentials['username']}")
            
            # 브라우저 시작
            playwright_instance = await async_playwright().start()
            browser = await playwright_instance.chromium.launch(
                headless=settings.HEADLESS_BROWSER,
                args=[
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-http2',  # HTTP/2 비활성화
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1366, "height": 768}
            )
            
            page = await context.new_page()
            
            # JavaScript 오류 무시 설정
            await page.add_init_script("""
                window.addEventListener('error', function(e) {
                    console.log('JavaScript error ignored:', e.message);
                    e.preventDefault();
                    return true;
                });
                
                window.addEventListener('unhandledrejection', function(e) {
                    console.log('Promise rejection ignored:', e.reason);
                    e.preventDefault();
                    return true;
                });
            """)
            
            # 1. 로그인 페이지 접근 (검증된 방식)
            print("로그인 페이지로 이동 중...")
            await page.goto("https://store.coupangeats.com/merchant/login", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # 2. 로그인 폼 입력 (안정적인 방식)
            print("로그인 폼 입력 중...")
            await page.wait_for_selector('#loginId', state='visible', timeout=10000)
            await page.fill('#loginId', credentials['username'])
            await page.wait_for_timeout(500)
            
            await page.fill('#password', credentials['password'])
            await page.wait_for_timeout(500)
            
            print(f"로그인 정보 입력 완료: {credentials['username']}")
            
            # 3. 로그인 버튼 클릭 (type="submit" 추가)
            print("로그인 버튼 클릭 중...")
            await page.click('button[type="submit"].merchant-submit-btn')
            
            # 로그인 완료 대기
            await page.wait_for_timeout(5000)
            
            # 4. 로그인 성공 확인 (간단하고 안정적인 방식)
            print("로그인 성공 확인 중...")
            current_url = page.url
            
            if "login" not in current_url:
                print("로그인 성공 - 페이지 이동 확인됨")
            else:
                print("로그인 실패 - 여전히 로그인 페이지에 있음")
                result["error_message"] = "로그인 실패: 아이디 또는 비밀번호를 확인해주세요."
                return result
            
            print(f"로그인 성공, 현재 URL: {page.url}")
            
            # 5. 리뷰 페이지로 이동
            print("리뷰 페이지로 이동 중...")
            await page.goto("https://store.coupangeats.com/merchant/management/reviews", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            print(f"리뷰 페이지 로드됨: {page.url}")
            
            # 6. 팝업 닫기 (검증된 방식)
            await self._close_popup(page)
            
            # 7. 드롭다운 버튼 찾기: <div class="button">
            print("드롭다운 버튼 찾는 중...")
            await page.wait_for_selector('div.button', timeout=10000)
            dropdown_button = await page.query_selector('div.button')
            
            if not dropdown_button:
                raise Exception("드롭다운 버튼을 찾을 수 없습니다")
            
            button_text = await dropdown_button.text_content()
            print(f"드롭다운 버튼 발견: {button_text}")
            
            # 8. 드롭다운 클릭
            print("드롭다운 클릭 중...")
            await dropdown_button.click()
            await page.wait_for_timeout(3000)
            
            # 9. 옵션 목록 추출: <ul class="options"><li>
            print("옵션 목록 추출 중...")
            await page.wait_for_selector('ul.options li', timeout=10000)
            
            options = await page.query_selector_all('ul.options li')
            print(f"옵션 {len(options)}개 발견")
            
            options_data = []
            for i, option in enumerate(options):
                text = await option.text_content()
                if text and text.strip():
                    clean_text = text.strip()
                    # span 태그 제거하고 매장명(ID) 형태만 추출
                    if '(' in clean_text and ')' in clean_text:
                        bracket_pos = clean_text.find(')')
                        if bracket_pos > 0:
                            clean_text = clean_text[:bracket_pos + 1]
                            options_data.append(clean_text)
                            print(f"추출된 매장: {clean_text}")
            
            print(f"총 {len(options_data)}개 매장 추출 완료")
            
            # 9. 데이터 파싱
            stores = self.parser.parse_multiple_stores(options_data)
            valid_stores = self.parser.filter_valid_stores(stores)
            
            # 10. 데이터베이스 저장
            save_result = await self._save_stores_to_database(user_id, valid_stores)
            
            # 11. 세션 상태 업데이트
            cookies = await context.cookies()
            session_data = json.dumps([{
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie['domain'],
                'path': cookie['path']
            } for cookie in cookies])
            
            await self.auth_service.update_session_status(user_id, True, session_data)
            
            # 12. 결과 구성
            result["success"] = True
            result["stores"] = [self.parser.to_database_format(store, user_id) for store in valid_stores]
            result["summary"] = self.parser.get_store_summary(stores)
            result["save_result"] = save_result
            
            print(f"크롤링 완료! {len(valid_stores)}개 매장 발견")
            
        except Exception as e:
            error_message = str(e)
            print(f"크롤링 오류: {error_message}")
            
            # 브라우저 관련 오류 메시지 개선
            if "Target page, context or browser has been closed" in error_message:
                result["error_message"] = "브라우저 세션이 종료되었습니다. 다시 시도해주세요."
            elif "net::ERR_HTTP2_PROTOCOL_ERROR" in error_message:
                result["error_message"] = "네트워크 프로토콜 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            elif "TimeoutError" in error_message or "timeout" in error_message.lower():
                result["error_message"] = "요청 시간이 초과되었습니다. 네트워크 상태를 확인해주세요."
            else:
                result["error_message"] = f"크롤링 중 오류 발생: {error_message}"
        
        finally:
            # 브라우저 정리 (안전한 방식)
            try:
                if browser:
                    print("브라우저 정리 중...")
                    await browser.close()
                    print("브라우저 정리 완료")
            except Exception as e:
                print(f"브라우저 정리 중 오류 (무시됨): {e}")
            
            try:
                if playwright_instance:
                    print("Playwright 정리 중...")
                    await playwright_instance.stop()
                    print("Playwright 정리 완료")
            except Exception as e:
                print(f"Playwright 정리 중 오류 (무시됨): {e}")
        
        return result
    
    async def _close_popup(self, page: Page) -> bool:
        """팝업/모달 창 닫기 (검증된 방식)"""
        try:
            print("팝업 닫기 시도...")
            
            # 팝업 셀렉터들
            popup_selectors = [
                'button[data-testid="Dialog__CloseButton"]',
                '.dialog-modal-wrapper__body--close-button',
                '.dialog-modal-wrapper__body--close-icon--white',
                'button.dialog-modal-wrapper__body--close-button',
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
                    close_button = page.locator(selector)
                    count = await close_button.count()
                    
                    if count > 0:
                        print(f"팝업 버튼 발견: {selector}")
                        await close_button.first.click(force=True)
                        await page.wait_for_timeout(1000)
                        print("팝업 닫기 성공")
                        return True
                except Exception:
                    continue
            
            # ESC 키로 팝업 닫기
            print("ESC 키로 팝업 닫기 시도...")
            for i in range(3):
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(500)
            
            print("팝업 닫기 완료")
            return True
            
        except Exception as e:
            print(f"팝업 닫기 중 오류: {e}")
            return False
    
    async def _save_stores_to_database(
        self, 
        user_id: str, 
        stores: List[CoupangEatsStoreInfo]
    ) -> Dict[str, Any]:
        """매장 정보를 데이터베이스에 저장"""
        try:
            saved_count = 0
            errors = []
            
            for store in stores:
                try:
                    store_data = self.parser.to_database_format(store, user_id)
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
                        saved_count += 1
                    
                except Exception as e:
                    error_msg = f"Store {store.platform_store_id} save failed: {str(e)}"
                    errors.append(error_msg)
            
            return {
                "success": len(errors) == 0 or saved_count > 0,
                "saved_count": saved_count,
                "total_processed": len(stores),
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "saved_count": 0,
                "total_processed": len(stores),
                "errors": [f"Database operation failed: {str(e)}"]
            }
    
    async def get_user_stores(self, user_id: str) -> Dict[str, Any]:
        """사용자의 쿠팡이츠 매장 목록 조회"""
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
            return {
                "success": False,
                "stores": [],
                "count": 0,
                "error": str(e)
            }