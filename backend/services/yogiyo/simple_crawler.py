"""
요기요 매장 크롤러 - 비동기 방식
"""
import asyncio
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser

class YogiyoCrawler:
    def __init__(self):
        self.login_url = "https://ceo.yogiyo.co.kr/login/"
        self.reviews_url = "https://ceo.yogiyo.co.kr/reviews"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        
    async def initialize(self):
        """브라우저 초기화"""
        playwright = await async_playwright().start()
        try:
            # Chrome 채널 시도
            self.browser = await playwright.chromium.launch(
                headless=False,
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
            print(f"[요기요] Chrome 채널 실패, Chromium으로 대체: {e}")
            # Chromium 대체
            self.browser = await playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--start-maximized'
                ]
            )
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        self.page = await context.new_page()
        
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
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({state: 'granted'})
                })
            });
        """)
        
    async def cleanup(self):
        """브라우저 정리"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
            
    async def login(self, username: str, password: str) -> bool:
        """요기요 로그인"""
        try:
            print(f"[요기요] 로그인 시도: {username}")
            
            # 로그인 페이지로 이동
            await self.page.goto(self.login_url, wait_until='domcontentloaded')  # networkidle -> domcontentloaded로 변경
            await asyncio.sleep(1)  # 2초 -> 1초로 단축

            # ID 입력
            await self.page.fill('input[name="username"]', username)
            await asyncio.sleep(0.2)  # 0.5초 -> 0.2초로 단축

            # 비밀번호 입력
            await self.page.fill('input[name="password"]', password)
            await asyncio.sleep(0.2)  # 0.5초 -> 0.2초로 단축
            
            # 로그인 버튼 클릭 - 빠른 실행
            print("[요기요] 로그인 버튼 클릭 시도...")
            button_clicked = False

            # 방법 1: submit 타입 버튼 (가장 빠른 셀렉터)
            try:
                await self.page.click('button[type="submit"]', timeout=2000)
                print("[요기요] 로그인 버튼 클릭 성공 (방법 1: submit 버튼)")
                button_clicked = True
            except:
                pass

            # 방법 2: 구체적인 클래스 (필요한 경우만)
            if not button_clicked:
                try:
                    await self.page.click('button.sc-bczRLJ.claiZC.sc-eCYdqJ.hsiXYt[type="submit"]', timeout=2000)
                    print("[요기요] 로그인 버튼 클릭 성공 (방법 2: 구체적 클래스)")
                    button_clicked = True
                except:
                    pass

            # 방법 3: 텍스트 기반 (최후 수단)
            if not button_clicked:
                try:
                    await self.page.click('button:has-text("로그인")', timeout=2000)
                    print("[요기요] 로그인 버튼 클릭 성공 (방법 3: 텍스트)")
                    button_clicked = True
                except:
                    pass

            if not button_clicked:
                raise Exception("로그인 버튼을 찾을 수 없습니다")

            # 로그인 완료 대기 (페이지 이동 감지)
            try:
                # URL 변경을 기다리거나 특정 요소 대기
                await self.page.wait_for_function(
                    "window.location.href.indexOf('login') === -1",
                    timeout=5000
                )
                print("[요기요] 로그인 성공 - 페이지 이동 감지")
            except:
                # URL 변경이 없어도 짧게 대기
                await asyncio.sleep(2)  # 3초 -> 2초로 단축
            
            # 로그인 성공 확인
            current_url = self.page.url
            if 'login' not in current_url:
                print(f"[요기요] 로그인 성공")
                return True
            else:
                print(f"[요기요] 로그인 실패")
                return False
                
        except Exception as e:
            print(f"[요기요] 로그인 오류: {e}")
            return False
            
    async def get_stores(self) -> List[Dict]:
        """매장 목록 가져오기"""
        try:
            print("[요기요] 매장 목록 가져오기 시작")
            
            # 리뷰 페이지로 이동 (더 관대한 설정)
            print("[요기요] 리뷰 페이지로 이동 중...")
            try:
                await self.page.goto(self.reviews_url, wait_until='domcontentloaded', timeout=60000)
                print("[요기요] 리뷰 페이지 로드 완료")
            except Exception as e:
                print(f"[요기요] 리뷰 페이지 로드 에러 (무시): {e}")
            
            await asyncio.sleep(5)
            
            # 드롭다운 버튼 클릭 (사용자 제공 셀렉터 사용)
            print("[요기요] 드롭다운 버튼 찾는 중...")
            try:
                # 먼저 드롭다운 전체 영역을 클릭
                dropdown_area = await self.page.wait_for_selector(
                    'div.StoreSelector__SelectedStore-sc-1rowjsb-13', 
                    timeout=10000
                )
                await dropdown_area.click()
                print("[요기요] 드롭다운 영역 클릭")
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"[요기요] 드롭다운 영역 클릭 실패, 버튼 직접 클릭 시도: {e}")
                # 백업: 드롭다운 버튼 직접 클릭
                try:
                    dropdown_button = await self.page.wait_for_selector(
                        'button.StoreSelector__DropdownButton-sc-1rowjsb-11', 
                        timeout=10000
                    )
                    await dropdown_button.click()
                    print("[요기요] 드롭다운 버튼 직접 클릭")
                    await asyncio.sleep(2)
                except Exception as e2:
                    print(f"[요기요] 드롭다운 버튼 직접 클릭도 실패: {e2}")
            
            # 매장 목록 대기
            print("[요기요] 매장 목록 대기 중...")
            await self.page.wait_for_selector(
                'ul.List__VendorList-sc-2ocjy3-8', 
                timeout=15000
            )
            print("[요기요] 매장 목록 발견")
            await asyncio.sleep(2)
            
            # 매장 정보 추출 (모든 매장을 포괄하는 셀렉터 사용)
            print("[요기요] 매장 정보 추출 중...")
            stores = await self.page.evaluate("""
                () => {
                    // 더 포괄적인 셀렉터 사용 (특정 클래스에 의존하지 않음)
                    const storeElements = document.querySelectorAll('li.List__Vendor-sc-2ocjy3-7');
                    const stores = [];
                    
                    console.log('[요기요] 매장 요소 개수:', storeElements.length);
                    
                    storeElements.forEach((element, index) => {
                        console.log('[요기요] 매장 요소', index + 1, '처리 중...');
                        console.log('  - 클래스:', element.className);
                        
                        // 매장명 - 여러 가능한 클래스 시도
                        const nameElement = element.querySelector('p.List__VendorName-sc-2ocjy3-3.hmbZyh') ||
                                           element.querySelector('p.List__VendorName-sc-2ocjy3-3.iXdZqX') ||
                                           element.querySelector('p.List__VendorName-sc-2ocjy3-3');
                        
                        // 매장 ID - 일관된 클래스 사용
                        const idElement = element.querySelector('span.List__VendorID-sc-2ocjy3-1.eStxxc') ||
                                         element.querySelector('span.List__VendorID-sc-2ocjy3-1');
                        
                        // 상태 - 일관된 클래스 사용  
                        const statusElement = element.querySelector('p.List__StoreStatus-sc-2ocjy3-0.fWsvNu') ||
                                             element.querySelector('p.List__StoreStatus-sc-2ocjy3-0');
                        
                        if (nameElement && idElement) {
                            const storeName = nameElement.textContent.trim();
                            const storeIdText = idElement.textContent.trim();
                            const storeId = storeIdText.replace('ID.', '').trim();
                            const status = statusElement ? statusElement.textContent.trim() : '';
                            
                            console.log('[요기요] 매장 발견:', storeName, 'ID:', storeId, 'Status:', status);
                            
                            stores.push({
                                store_name: storeName,
                                platform_store_id: storeId,
                                platform: 'yogiyo',
                                status: status
                            });
                        } else {
                            console.log('[요기요] 매장', index + 1, '정보 추출 실패');
                            console.log('  - nameElement:', nameElement ? '있음' : '없음');
                            console.log('  - idElement:', idElement ? '있음' : '없음');
                            
                            // 디버깅: 실제 HTML 구조 확인
                            const allPElements = element.querySelectorAll('p');
                            const allSpanElements = element.querySelectorAll('span');
                            console.log('  - p 요소 개수:', allPElements.length);
                            console.log('  - span 요소 개수:', allSpanElements.length);
                            
                            allPElements.forEach((p, idx) => {
                                console.log('    p[' + idx + ']:' + p.className + ' = ' + p.textContent.trim());
                            });
                            
                            allSpanElements.forEach((span, idx) => {
                                console.log('    span[' + idx + ']:' + span.className + ' = ' + span.textContent.trim());
                            });
                        }
                    });
                    
                    console.log('[요기요] 총', stores.length, '개 매장 추출 완료');
                    return stores;
                }
            """)
            
            print(f"[요기요] {len(stores)}개 매장 발견")
            for store in stores:
                print(f"  - {store['store_name']} (ID: {store['platform_store_id']})")
                
            return stores
            
        except Exception as e:
            print(f"[요기요] 매장 목록 가져오기 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
            
    async def crawl_stores(self, username: str, password: str) -> Tuple[bool, List[Dict], str]:
        """메인 크롤링 함수"""
        try:
            # 로그인
            login_success = await self.login(username, password)
            if not login_success:
                return False, [], "로그인 실패"
                
            # 매장 목록 가져오기
            stores = await self.get_stores()
            
            if not stores:
                return True, [], "등록된 매장이 없습니다"
                
            return True, stores, f"{len(stores)}개 매장을 찾았습니다"
            
        except Exception as e:
            print(f"[요기요] 크롤링 오류: {e}")
            import traceback
            traceback.print_exc()
            return False, [], str(e)


# 테스트용 함수
async def test_crawler():
    """테스트 함수"""
    async with YogiyoCrawler() as crawler:
        success, stores, message = await crawler.crawl_stores(
            username="test_user",
            password="test_password"
        )
        print(f"성공: {success}")
        print(f"메시지: {message}")
        print(f"매장 수: {len(stores)}")
        for store in stores:
            print(f"  - {store}")


if __name__ == "__main__":
    asyncio.run(test_crawler())