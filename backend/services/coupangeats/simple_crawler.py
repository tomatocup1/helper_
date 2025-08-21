# -*- coding: utf-8 -*-
"""
쿠팡이츠 크롤러 - 타임아웃 문제 해결 버전
"""

import asyncio
from typing import Dict, List, Tuple
from playwright.async_api import async_playwright
from datetime import datetime

class CoupangEatsCrawler:
    """쿠팡이츠 크롤러"""
    
    def __init__(self):
        self.login_url = "https://store.coupangeats.com/merchant/login"
        self.reviews_url = "https://store.coupangeats.com/merchant/management/reviews"
        self.browser = None
        self.playwright = None
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        
    async def initialize(self):
        """브라우저 초기화"""
        self.playwright = await async_playwright().start()
        
        # 브라우저 실행 (더 안정적인 설정)
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        print("[쿠팡이츠] 브라우저 시작")
            
    async def cleanup(self):
        """브라우저 정리"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    async def close_popup(self, page):
        """팝업 닫기"""
        try:
            # Speak Up 모달 닫기 버튼 찾기
            close_button = await page.query_selector('button.dialog-modal-wrapper__body--close-button')
            if close_button:
                await close_button.click()
                print("[쿠팡이츠] 팝업 닫기 성공")
                await page.wait_for_timeout(1000)
        except:
            pass
    
    async def crawl_stores(self, username: str, password: str) -> Tuple[bool, List[Dict], str]:
        """매장 목록 크롤링"""
        try:
            await self.initialize()
            
            # 브라우저 컨텍스트 생성 (더 안정적인 설정)
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True
            )
            
            page = await context.new_page()
            
            # 타임아웃 설정 - 중요!
            page.set_default_navigation_timeout(60000)  # 60초
            page.set_default_timeout(60000)  # 60초
            
            print(f"[쿠팡이츠] 로그인 시작: {username}")
            
            # 1. 로그인 페이지로 이동 - domcontentloaded 사용
            print("[쿠팡이츠] 로그인 페이지 이동")
            try:
                await page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)
                print("[쿠팡이츠] 페이지 로드 완료")
            except Exception as e:
                print(f"[쿠팡이츠] 페이지 로드 에러 (무시): {e}")
                
            await page.wait_for_timeout(3000)
            
            # 2. 로그인 정보 입력
            print("[쿠팡이츠] ID/PW 입력")
            
            login_success = False
            max_attempts = 3
            
            for attempt in range(max_attempts):
                try:
                    print(f"[쿠팡이츠] 로그인 시도 {attempt + 1}/{max_attempts}")
                    
                    # 타임스탬프 미리 정의
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # ID 입력
                    await page.wait_for_selector('#loginId', state='visible', timeout=10000)
                    await page.fill('#loginId', '')  # 클리어
                    await page.wait_for_timeout(200)
                    await page.fill('#loginId', username)  # 입력
                    print("[쿠팡이츠] ID 입력 완료")
                    await page.wait_for_timeout(500)
                    
                    # PW 입력
                    await page.fill('#password', '')  # 클리어
                    await page.wait_for_timeout(200)
                    await page.fill('#password', password)  # 입력
                    print("[쿠팡이츠] PW 입력 완료")
                    await page.wait_for_timeout(500)
                    
                    # 로그인 전 스크린샷
                    await page.screenshot(path=f"coupangeats_before_login_{timestamp}.png")
                    
                    # 로그인 버튼 클릭
                    await page.click('button[type="submit"].merchant-submit-btn')
                    print("[쿠팡이츠] 로그인 버튼 클릭")
                    
                    # 로그인 처리 대기 (시간 증가)
                    await page.wait_for_timeout(8000)
                    
                    # 로그인 성공 확인 (간단한 방법)
                    current_url = page.url
                    print(f"[쿠팡이츠] 로그인 후 현재 URL: {current_url}")
                    
                    if "login" not in current_url:
                        print("[쿠팡이츠] 로그인 성공 확인됨")
                        login_success = True
                        break
                    else:
                        print(f"[쿠팡이츠] 로그인 실패 - 시도 {attempt + 1}")
                        # 실패 시 스크린샷 저장 (브라우저가 살아있을 때만)
                        try:
                            await page.screenshot(path=f"coupangeats_login_failed_{timestamp}_attempt_{attempt + 1}.png")
                        except:
                            print(f"[쿠팡이츠] 스크린샷 저장 실패 - 브라우저가 종료되었을 수 있음")
                        
                        if attempt < max_attempts - 1:
                            print("[쿠팡이츠] 3초 후 재시도...")
                            try:
                                await page.wait_for_timeout(3000)
                            except:
                                print(f"[쿠팡이츠] 브라우저 종료로 인한 재시도 불가")
                                break
                    
                except Exception as e:
                    print(f"[쿠팡이츠] 로그인 시도 {attempt + 1} 중 오류: {e}")
                    # 스크린샷 저장 시도 (실패해도 계속 진행)
                    try:
                        await page.screenshot(path=f"coupangeats_login_error_{timestamp}_attempt_{attempt + 1}.png")
                    except:
                        print(f"[쿠팡이츠] 오류 스크린샷 저장 실패 - 브라우저가 종료되었을 수 있음")
                    
                    # 브라우저 종료 관련 오류면 재시도 중단
                    if "Target page, context or browser has been closed" in str(e) or "closed" in str(e).lower():
                        print("[쿠팡이츠] 브라우저 종료로 인한 오류 - 재시도 중단")
                        break
                        
                    if attempt < max_attempts - 1:
                        try:
                            await page.wait_for_timeout(3000)
                        except:
                            print("[쿠팡이츠] 대기 중 브라우저 종료 - 재시도 중단")
                            break
            
            if not login_success:
                print("[쿠팡이츠] 모든 로그인 시도 실패")
                await self.cleanup()
                return False, [], "로그인 실패: 계정 정보를 확인하거나 사이트 접속을 확인해주세요"
            
            # 로그인 성공 후 추가 처리
            current_url = page.url
            print(f"[쿠팡이츠] 로그인 후 현재 URL: {current_url}")
            
            # 3. 리뷰 페이지로 이동
            print("[쿠팡이츠] 리뷰 페이지로 이동")
            try:
                await page.goto(self.reviews_url, wait_until="domcontentloaded", timeout=60000)
                print("[쿠팡이츠] 리뷰 페이지 로드 완료")
            except Exception as e:
                print(f"[쿠팡이츠] 리뷰 페이지 로드 에러 (무시): {e}")
                
            await page.wait_for_timeout(3000)
            
            # 팝업 닫기
            await self.close_popup(page)
            
            # 4. 매장 드롭다운 클릭
            print("[쿠팡이츠] 매장 드롭다운 찾기")
            stores = []
            
            try:
                # 드롭다운 버튼 찾기 - 사용자가 제공한 정확한 셀렉터
                dropdown_button = await page.query_selector('div.button')
                
                if dropdown_button:
                    await dropdown_button.click()
                    print("[쿠팡이츠] 드롭다운 클릭")
                    await page.wait_for_timeout(2000)
                    
                    # 옵션 목록 대기 - 사용자가 제공한 정확한 셀렉터
                    try:
                        await page.wait_for_selector('ul.options', timeout=5000)
                        print("[쿠팡이츠] 옵션 목록 발견")
                    except:
                        print("[쿠팡이츠] 옵션 목록 대기 실패")
                    
                    # 매장 목록 추출
                    stores = await page.evaluate("""
                        () => {
                            const options = document.querySelectorAll('ul.options li');
                            const stores = [];
                            
                            options.forEach(option => {
                                const text = option.textContent.trim();
                                // "큰집닭강정(708561)" 형식
                                const match = text.match(/^(.+?)\\((\\d+)\\)/);
                                if (match) {
                                    stores.push({
                                        store_name: match[1].trim(),
                                        platform_store_id: match[2],
                                        platform: 'coupangeats'
                                    });
                                }
                            });
                            
                            return stores;
                        }
                    """)
                    
                    if stores and len(stores) > 0:
                        print(f"[쿠팡이츠] {len(stores)}개 매장 발견")
                        for store in stores:
                            print(f"  - {store['store_name']} (ID: {store['platform_store_id']})")
                    else:
                        print("[쿠팡이츠] 매장을 찾을 수 없음")
                else:
                    print("[쿠팡이츠] 드롭다운 버튼을 찾을 수 없음")
                    
                    # 페이지 스크린샷 저장
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    await page.screenshot(path=f"coupangeats_page_{timestamp}.png")
                    
                    # 페이지 텍스트에서 매장 정보 찾기 시도
                    page_content = await page.content()
                    if '(' in page_content and ')' in page_content:
                        print("[쿠팡이츠] 페이지에서 매장 정보 찾기 시도")
                        # JavaScript로 매장 정보 추출
                        stores = await page.evaluate("""
                            () => {
                                const bodyText = document.body.innerText;
                                const regex = /([가-힣a-zA-Z0-9\\s%]+)\\((\\d{6,})\\)/g;
                                const matches = [];
                                let match;
                                
                                while ((match = regex.exec(bodyText)) !== null) {
                                    matches.push({
                                        store_name: match[1].trim(),
                                        platform_store_id: match[2],
                                        platform: 'coupangeats'
                                    });
                                }
                                
                                // 중복 제거
                                const unique = matches.filter((item, index, self) =>
                                    index === self.findIndex((t) => t.platform_store_id === item.platform_store_id)
                                );
                                
                                return unique;
                            }
                        """)
                        
                        if stores and len(stores) > 0:
                            print(f"[쿠팡이츠] 페이지에서 {len(stores)}개 매장 발견")
                            for store in stores:
                                print(f"  - {store['store_name']} (ID: {store['platform_store_id']})")
                    
            except Exception as e:
                print(f"[쿠팡이츠] 드롭다운 처리 중 오류: {e}")
                # 스크린샷 저장
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                await page.screenshot(path=f"coupangeats_error_{timestamp}.png")
            
            # 브라우저를 잠시 열어둠 (디버깅용)
            print("[쿠팡이츠] 10초 후 브라우저 종료...")
            await page.wait_for_timeout(10000)
            
            await self.cleanup()
            
            if stores and len(stores) > 0:
                return True, stores, f"{len(stores)}개 매장을 찾았습니다"
            else:
                return True, [], "등록된 매장이 없습니다"
                
        except Exception as e:
            print(f"[쿠팡이츠] 크롤링 오류: {e}")
            import traceback
            traceback.print_exc()
            await self.cleanup()
            return False, [], f"크롤링 중 오류가 발생했습니다: {str(e)}"


# 테스트용 함수
async def test_crawler():
    """테스트 함수"""
    async with CoupangEatsCrawler() as crawler:
        success, stores, message = await crawler.crawl_stores(
            username="test_user",
            password="test_password"
        )
        print(f"성공: {success}")
        print(f"메시지: {message}")
        print(f"매장 수: {len(stores)}")


    async def _check_login_success(self, page) -> bool:
        """로그인 성공 여부 확인"""
        try:
            current_url = page.url
            print(f"[쿠팡이츠] 로그인 확인 - 현재 URL: {current_url}")
            
            # 1. URL 변화 확인
            if "login" not in current_url:
                print("[쿠팡이츠] URL 변화로 로그인 성공 확인")
                return True
            
            # 2. 페이지 제목 확인
            try:
                title = await page.title()
                if "로그인" not in title and "login" not in title.lower():
                    print(f"[쿠팡이츠] 페이지 제목 변화로 로그인 성공 확인: {title}")
                    return True
            except:
                pass
            
            # 3. 로그인 폼 존재 여부 확인 (로그인 성공시 폼이 사라짐)
            login_form = await page.query_selector('#loginId')
            if not login_form:
                print("[쿠팡이츠] 로그인 폼 사라짐으로 로그인 성공 확인")
                return True
            
            # 4. 대시보드 요소 확인
            dashboard_elements = [
                'nav', '.header', '.sidebar', '.dashboard', '.merchant-header'
            ]
            for selector in dashboard_elements:
                element = await page.query_selector(selector)
                if element:
                    print(f"[쿠팡이츠] 대시보드 요소 발견으로 로그인 성공 확인: {selector}")
                    return True
            
            print("[쿠팡이츠] 로그인 성공 확인 실패")
            return False
            
        except Exception as e:
            print(f"[쿠팡이츠] 로그인 확인 중 오류: {e}")
            return False
    
    async def _get_login_error_message(self, page) -> str:
        """로그인 에러 메시지 추출"""
        try:
            error_selectors = [
                '.error-message',
                '.alert-danger', 
                '.error',
                '[class*="error"]',
                '[class*="alert"]',
                '.validation-message'
            ]
            
            for selector in error_selectors:
                error_element = await page.query_selector(selector)
                if error_element:
                    error_text = await error_element.text_content()
                    if error_text and error_text.strip():
                        return error_text.strip()
            
            return ""
        except:
            return ""


if __name__ == "__main__":
    asyncio.run(test_crawler())