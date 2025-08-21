"""
배달의민족 크롤링 서비스
매장 목록 크롤링 및 데이터 추출
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from playwright.async_api import async_playwright, Browser, Page, TimeoutError
from supabase import create_client, Client

try:
    from .auth_service import BaeminAuthService
except ImportError:
    from .auth_service_simple import BaeminAuthService
from .parser import BaeminDataParser, BaeminStoreInfo
from ..shared.logger import get_logger
from ..shared.config import settings

logger = get_logger(__name__)

class BaeminCrawlerService:
    """배달의민족 크롤링 서비스"""
    
    def __init__(self, auth_service: BaeminAuthService):
        self.auth_service = auth_service
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self.parser = BaeminDataParser()
        
    async def crawl_stores(
        self, 
        user_id: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        사용자의 배민 매장 목록 크롤링
        
        Args:
            user_id: 사용자 ID
            progress_callback: 진행상황 콜백 함수
            timeout: 타임아웃 (초)
            
        Returns:
            크롤링 결과 딕셔너리
        """
        browser = None
        result = {
            "success": False,
            "user_id": user_id,
            "stores": [],
            "summary": {},
            "error_message": None,
            "crawled_at": datetime.now().isoformat()
        }
        
        try:
            # 진행상황 업데이트
            if progress_callback:
                progress_callback({
                    "step": "authentication",
                    "message": "배민 로그인 정보 확인 중...",
                    "progress": 10
                })
            
            # 로그인 정보 조회
            credentials = await self.auth_service.get_credentials(user_id)
            if not credentials:
                result["error_message"] = "저장된 배민 로그인 정보가 없습니다."
                return result
            
            # 브라우저 시작
            if progress_callback:
                progress_callback({
                    "step": "browser_init",
                    "message": "브라우저 시작 중...",
                    "progress": 20
                })
            
            browser_result = await self._launch_browser_and_login(
                credentials["username"],
                credentials["password"],
                progress_callback,
                timeout
            )
            
            if not browser_result["success"]:
                result["error_message"] = browser_result["message"]
                return result
            
            browser = browser_result["browser"]
            page = browser_result["page"]
            
            # 매장 관리 페이지 접근
            if progress_callback:
                progress_callback({
                    "step": "navigation",
                    "message": "매장 관리 페이지 접근 중...",
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
            
            logger.info(f"Baemin crawling completed for user {user_id}: {len(valid_stores)} stores")
            
        except Exception as e:
            logger.error(f"Baemin crawling failed for user {user_id}: {e}")
            result["error_message"] = f"크롤링 중 오류 발생: {str(e)}"
            
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
            
            # Playwright 인스턴스가 있으면 정리
            if 'playwright' in result.get('browser_result', {}):
                try:
                    playwright = result['browser_result']['playwright']
                    await playwright.stop()
                except Exception as e:
                    logger.error(f"Error stopping playwright: {e}")
        
        return result
    
    async def _launch_browser_and_login(
        self, 
        username: str, 
        password: str,
        progress_callback: Optional[Callable],
        timeout: int
    ) -> Dict[str, Any]:
        """브라우저 시작 및 로그인"""
        playwright_instance = None
        browser = None
        
        try:
            # Playwright 인스턴스 시작
            playwright_instance = await async_playwright().start()
            
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
            
            await page.goto("https://biz-member.baemin.com/login", timeout=timeout * 1000)
            await page.wait_for_timeout(2000)  # 페이지 로딩 대기
            
            # 로그인 정보 입력
            await page.fill('input[data-testid="id"]', username)
            await page.wait_for_timeout(500)
            await page.fill('input[data-testid="password"]', password)
            await page.wait_for_timeout(500)
            
            # 로그인 버튼 클릭
            if progress_callback:
                progress_callback({
                    "step": "login_submit",
                    "message": "로그인 중...",
                    "progress": 40
                })
            
            await page.click('button[type="submit"]')
            
            # 로그인 완료 대기 - 더 긴 시간과 URL 변화 감지
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
            print(f"로그인 후 현재 URL: {current_url}")
            
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
        """매장 데이터 추출"""
        try:
            # 매장 관리 페이지로 이동
            print("매장 관리 페이지로 이동 중...")
            await page.goto("https://self.baemin.com/", timeout=30000)
            
            # 페이지 로딩 충분히 대기
            await page.wait_for_timeout(5000)
            print(f"페이지 이동 완료: {page.url}")
            
            if progress_callback:
                progress_callback({
                    "step": "page_navigation",
                    "message": "매장 관리 페이지 로딩 중...",
                    "progress": 50
                })
            
            # 여러 가능한 셀렉터로 드롭박스 찾기
            select_selectors = [
                'select.Select-module__a623.ShopSelect-module___pC1',
                'select[class*="Select-module"]',
                'select[class*="ShopSelect-module"]',
                'select'
            ]
            
            select_found = False
            select_selector = None
            
            for selector in select_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    select_selector = selector
                    select_found = True
                    print(f"드롭박스 찾음: {selector}")
                    break
                except TimeoutError:
                    continue
            
            if not select_found:
                # 페이지 소스 확인을 위한 스크린샷
                await page.screenshot(path='debug_page.png')
                page_content = await page.content()
                print(f"페이지 내용 일부: {page_content[:500]}...")
                
                return {
                    "success": False,
                    "message": "매장 선택 드롭박스를 찾을 수 없습니다. 페이지 구조가 변경되었거나 로그인 세션이 만료되었을 수 있습니다."
                }
            
            if progress_callback:
                progress_callback({
                    "step": "extraction",
                    "message": "매장 목록 추출 중...",
                    "progress": 60
                })
            
            # 옵션 추출
            options_data = await page.evaluate(f'''
                () => {{
                    const select = document.querySelector('{select_selector}');
                    if (!select) return [];
                    
                    const options = Array.from(select.querySelectorAll('option'));
                    return options.map(option => ({{
                        value: option.value,
                        text: option.textContent || option.innerText
                    }})).filter(opt => opt.value && opt.text && opt.value !== '' && opt.value !== 'undefined');
                }}
            ''')
            
            if not options_data:
                return {
                    "success": False,
                    "message": "매장 정보를 찾을 수 없습니다. 등록된 매장이 없거나 권한이 없을 수 있습니다."
                }
            
            print(f"추출된 매장 옵션: {options_data}")
            logger.info(f"Extracted {len(options_data)} store options from baemin")
            
            return {
                "success": True,
                "options": options_data,
                "count": len(options_data)
            }
            
        except Exception as e:
            logger.error(f"Error extracting stores data: {e}")
            return {
                "success": False,
                "message": f"매장 데이터 추출 실패: {str(e)}"
            }
    
    async def _save_stores_to_database(
        self, 
        user_id: str, 
        stores: List[BaeminStoreInfo]
    ) -> Dict[str, Any]:
        """매장 정보를 데이터베이스에 저장"""
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
        """사용자의 배민 매장 목록 조회"""
        try:
            result = self.supabase.table("platform_stores").select(
                "id, store_name, business_type, sub_type, platform_store_id, is_active, created_at"
            ).eq("user_id", user_id).eq("platform", "baemin").order("created_at", desc=True).execute()
            
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