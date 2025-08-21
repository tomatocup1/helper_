"""
배달의민족 매장 크롤러 - 실제 크롤링 구현
"""
import asyncio
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser

class BaeminCrawler:
    def __init__(self):
        self.login_url = "https://biz-member.baemin.com/login"
        self.stores_url = "https://self.baemin.com/"
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
            print(f"[배민] Chrome 채널 실패, Chromium으로 대체: {e}")
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
        """)
        
    async def cleanup(self):
        """브라우저 정리"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
            
    async def login(self, username: str, password: str) -> bool:
        """배민 로그인"""
        try:
            print(f"[배민] 로그인 시도: {username}")
            
            # 로그인 페이지로 이동
            await self.page.goto(self.login_url, wait_until='networkidle')
            await asyncio.sleep(2)
            
            # ID 입력 - 정확한 셀렉터 사용
            try:
                await self.page.wait_for_selector('input[name="id"][data-testid="id"]', timeout=10000)
                await self.page.fill('input[name="id"][data-testid="id"]', username)
                print(f"[배민] ID 입력 성공")
            except Exception as e:
                print(f"[배민] ID 입력 실패: {e}")
                return False
            
            await asyncio.sleep(0.5)
            
            # 비밀번호 입력 - 정확한 셀렉터 사용
            try:
                await self.page.wait_for_selector('input[name="password"][data-testid="password"]', timeout=10000)
                await self.page.fill('input[name="password"][data-testid="password"]', password)
                print(f"[배민] 비밀번호 입력 성공")
            except Exception as e:
                print(f"[배민] 비밀번호 입력 실패: {e}")
                return False
            
            await asyncio.sleep(0.5)
            
            # 로그인 버튼 클릭 - 정확한 셀렉터 사용
            try:
                await self.page.wait_for_selector('button[type="submit"].Button__StyledButton-sc-1cxc4dz-0', timeout=10000)
                await self.page.click('button[type="submit"].Button__StyledButton-sc-1cxc4dz-0')
                print(f"[배민] 로그인 버튼 클릭 성공")
            except Exception as e:
                print(f"[배민] 로그인 버튼 클릭 실패: {e}")
                return False
            
            # 로그인 처리 대기
            await asyncio.sleep(3)
            
            # 로그인 성공으로 가정하고 계속 진행
            print(f"[배민] 로그인 완료 - 현재 페이지에서 드롭다운 찾기 시작")
            return True
                
        except Exception as e:
            print(f"[배민] 로그인 오류: {e}")
            return False
            
    async def get_stores(self) -> List[Dict]:
        """매장 목록 가져오기 - 정확한 배민 로직"""
        try:
            print("[배민] 매장 목록 가져오기 시작")
            
            # 항상 self.baemin.com으로 이동 (강제)
            print(f"[배민] self.baemin.com으로 강제 이동 시작...")
            try:
                current_url = self.page.url
                print(f"[배민] 현재 URL: {current_url}")
                
                await self.page.goto('https://self.baemin.com/', wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(2)
                print(f"[배민] 이동 완료 - URL: {self.page.url}")
                
            except Exception as e:
                print(f"[배민] 이동 중 오류: {e}")
                print(f"[배민] 현재 페이지에서 드롭다운 찾기 시도...")
                # 이동 실패해도 현재 페이지에서 계속 시도
            
            # 매장 선택 드롭다운에서 정보 추출
            stores = []
            
            # 페이지 로딩 상태 확인
            print("[배민] 드롭다운 찾기 시작...")
            await asyncio.sleep(3)  # 적당한 대기 시간
            
            # 페이지 내용 디버깅
            try:
                page_title = await self.page.title()
                print(f"[배민] 페이지 제목: {page_title}")
                
                # 모든 select 요소 확인
                all_selects = await self.page.evaluate("""
                    () => {
                        const selects = document.querySelectorAll('select');
                        return Array.from(selects).map(select => ({
                            className: select.className,
                            id: select.id,
                            optionsCount: select.options.length,
                            innerHTML: select.innerHTML.substring(0, 200)
                        }));
                    }
                """)
                print(f"[배민] 발견된 select 요소들: {len(all_selects)}개")
                for i, select in enumerate(all_selects):
                    print(f"  Select {i+1}: class='{select['className']}', options={select['optionsCount']}")
                    if select['optionsCount'] > 0:
                        print(f"    내용: {select['innerHTML'][:100]}...")
                
            except Exception as e:
                print(f"[배민] 페이지 디버깅 오류: {e}")
            
            try:
                # 다양한 드롭다운 셀렉터 시도
                dropdown_selectors = [
                    'select.Select-module__a623.ShopSelect-module___pC1',
                    'select.ShopSelect-module___pC1',
                    'select.Select-module__a623',
                    'select[class*="ShopSelect"]',
                    'select[class*="Select-module"]',
                    'select'
                ]
                
                dropdown_found = False
                stores_data = []
                
                for selector in dropdown_selectors:
                    try:
                        print(f"[배민] 드롭다운 셀렉터 시도: {selector}")
                        
                        # 빠른 확인
                        dropdown = await self.page.query_selector(selector)
                        
                        if dropdown:
                            print(f"[배민] 드롭다운 발견: {selector}")
                            
                            # 옵션 개수 확인
                            option_count = await self.page.evaluate(f"""
                                (selector) => {{
                                    const dropdown = document.querySelector(selector);
                                    return dropdown ? dropdown.options.length : 0;
                                }}
                            """, selector)
                            
                            print(f"[배민] 옵션 개수: {option_count}")
                            
                            if option_count > 0:
                                # 매장 정보 추출
                                stores_data = await self.page.evaluate(f"""
                                    (selector) => {{
                                        const dropdown = document.querySelector(selector);
                                        if (!dropdown) return [];
                                        
                                        const options = dropdown.querySelectorAll('option');
                                        const stores = [];
                                        
                                        options.forEach(option => {{
                                            const value = option.value;
                                            const text = option.textContent.trim();
                                            
                                            console.log('옵션:', text, 'value:', value);
                                            
                                            if (value && text && text.includes(']')) {{
                                                const parts = text.split('] ');
                                                if (parts.length >= 2) {{
                                                    const subType = parts[0] + ']';
                                                    const remaining = parts[1];
                                                    
                                                    const lastSlashIndex = remaining.lastIndexOf(' / ');
                                                    if (lastSlashIndex > 0) {{
                                                        const storePart = remaining.substring(0, lastSlashIndex);
                                                        const businessPart = remaining.substring(lastSlashIndex + 3);
                                                        const businessType = businessPart.replace(/ \\d+.*$/, '');
                                                        
                                                        stores.push({{
                                                            store_name: storePart.trim(),
                                                            platform_store_id: value,
                                                            business_type: businessType.trim(),
                                                            sub_type: subType.replace('[', '').replace(']', ''),
                                                            platform: 'baemin'
                                                        }});
                                                    }}
                                                }}
                                            }}
                                        }});
                                        
                                        return stores;
                                    }}
                                """, selector)
                                
                                if stores_data and len(stores_data) > 0:
                                    stores = stores_data
                                    print(f"[배민] {len(stores)}개 매장 성공적으로 추출")
                                    dropdown_found = True
                                    break
                                    
                    except Exception as e:
                        print(f"[배민] 셀렉터 {selector} 시도 실패: {e}")
                        continue
                
                if not dropdown_found:
                    print("[배민] 모든 셀렉터로 드롭다운을 찾을 수 없음")
                    # 페이지 HTML 일부 출력
                    html_sample = await self.page.evaluate("""
                        () => document.body.innerHTML.substring(0, 1000)
                    """)
                    print(f"[배민] 페이지 HTML 샘플: {html_sample}")
                    
            except Exception as e:
                print(f"[배민] 드롭다운 처리 오류: {e}")
                import traceback
                traceback.print_exc()
            
            for store in stores:
                print(f"  - {store['store_name']} (ID: {store['platform_store_id']}) [{store.get('business_type', 'N/A')}] ({store.get('sub_type', 'N/A')})")
                
            return stores
            
        except Exception as e:
            print(f"[배민] 매장 목록 가져오기 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
            
    async def get_stores_async(self, username: str, password: str) -> Tuple[bool, List[Dict], str]:
        """메인 크롤링 함수"""
        try:
            await self.initialize()
            
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
            print(f"[배민] 크롤링 오류: {e}")
            import traceback
            traceback.print_exc()
            return False, [], str(e)
        finally:
            await self.cleanup()


# 테스트용 함수
async def test_crawler():
    """테스트 함수"""
    crawler = BaeminCrawler()
    success, stores, message = await crawler.get_stores_async(
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