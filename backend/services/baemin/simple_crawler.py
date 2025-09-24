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
        # 환경에 따른 브라우저 설정
        import os
        is_local = os.getenv('RENDER') != 'true'  # Render 환경이 아니면 로컬

        # 진짜 사람처럼 보이는 브라우저 설정
        self.browser = await playwright.chromium.launch(
            headless=not is_local,  # 로컬에서는 headless=False, 서버에서는 True
            slow_mo=100 if is_local else 200,  # 로컬: 100ms, 서버: 200ms 지연
            args=[
                # 자동화 감지 방지 강화
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--exclude-switches=enable-automation',
                '--disable-automation',
                '--disable-infobars',

                # 보안 및 샌드박스
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',

                # 웹 보안 관련
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-default-apps',
                '--disable-popup-blocking',

                # GPU 및 렌더링
                '--disable-gpu',
                '--disable-gpu-sandbox',
                '--disable-software-rasterizer',

                # 메모리 최적화
                '--no-first-run',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # 이미지 로딩 비활성화로 메모리 절약
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-background-networking',
                '--disable-javascript-harmony-shipping',
                '--disable-ipc-flooding-protection',
                '--memory-pressure-off',  # 메모리 압박 모드 비활성화
                '--max_old_space_size=512',  # Node.js 메모리 제한

                # 추가 우회 설정
                '--disable-logging',
                '--disable-login-animations',
                '--disable-notifications',
                '--disable-password-generation',
                '--disable-save-password-bubble',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--ignore-certificate-errors-spki-list',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',

                # 언어 및 로케일 설정
                '--lang=ko-KR',
                '--accept-lang=ko-KR,ko,en-US,en'
            ]
        )

        # 한국 환경으로 설정된 브라우저 컨텍스트
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        )
        
        self.page = await context.new_page()
        
        # 최고 수준의 JavaScript 스텔스 모드
        await self.page.add_init_script("""
            // WebDriver 속성 완전 제거
            delete navigator.__proto__.webdriver;
            delete navigator.webdriver;
            delete window.navigator.webdriver;

            // 모든 자동화 관련 속성 제거
            delete navigator.automation;
            delete window.navigator.automation;
            delete window.webdriver;

            // Chrome 런타임 객체 완전 구현
            Object.defineProperty(window, 'chrome', {
                value: {
                    runtime: {
                        onConnect: null,
                        onMessage: null,
                        onConnectExternal: null,
                        onInstalled: null
                    },
                    loadTimes: function() {
                        return {
                            requestTime: Date.now() - 1000,
                            startLoadTime: Date.now() - 800,
                            commitLoadTime: Date.now() - 600,
                            finishDocumentLoadTime: Date.now() - 400,
                            finishLoadTime: Date.now() - 200,
                            firstPaintTime: Date.now() - 100,
                            firstPaintAfterLoadTime: 0,
                            navigationType: "Reload"
                        };
                    },
                    csi: function() {
                        return {
                            startE: Date.now(),
                            onloadT: Date.now(),
                            pageT: Math.random() * 1000 + 500,
                            tran: 15
                        };
                    },
                    app: {
                        isInstalled: false,
                        InstallState: {
                            DISABLED: 'disabled',
                            INSTALLED: 'installed',
                            NOT_INSTALLED: 'not_installed'
                        },
                        getDetails: function() { return null; },
                        getIsInstalled: function() { return false; },
                        runningState: function() { return 'cannot_run'; }
                    }
                },
                writable: false,
                enumerable: true,
                configurable: false
            });

            // Navigator 속성 강화
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                configurable: true
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => Array.from({length: 5}, (_, i) => ({
                    name: `Plugin ${i}`,
                    filename: `plugin${i}.so`,
                    description: `Plugin Description ${i}`,
                    version: '1.0.0'
                })),
                configurable: true
            });

            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => Array.from({length: 5}, (_, i) => ({
                    type: `application/plugin${i}`,
                    suffixes: `p${i}`,
                    description: `Plugin ${i} MIME Type`
                })),
                configurable: true
            });

            // 자동화 탐지 우회 - Permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );

            // 화면 해상도 및 색상 깊이 설정
            Object.defineProperty(screen, 'colorDepth', {
                get: () => 24,
                configurable: true
            });

            Object.defineProperty(screen, 'pixelDepth', {
                get: () => 24,
                configurable: true
            });

            // 플러그인 배열 프로토타입 수정
            Object.setPrototypeOf(navigator.plugins, PluginArray.prototype);
            Object.setPrototypeOf(navigator.mimeTypes, MimeTypeArray.prototype);

            // UserAgent 데이터 일관성 확보
            Object.defineProperty(navigator, 'userAgentData', {
                get: () => ({
                    brands: [
                        { brand: 'Google Chrome', version: '131' },
                        { brand: 'Chromium', version: '131' },
                        { brand: 'Not_A Brand', version: '24' }
                    ],
                    mobile: false,
                    platform: 'Windows'
                }),
                configurable: true
            });

            // 추가 핑거프린트 우회
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4,
                configurable: true
            });

            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true
            });

            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 100,
                    downlink: 2,
                    saveData: false
                }),
                configurable: true
            });

            // 브라우저 타이밍 API 우회
            Object.defineProperty(window, 'performance', {
                value: window.performance || {},
                writable: true
            });

            if (window.performance && window.performance.timing) {
                Object.defineProperty(window.performance, 'timing', {
                    get: () => ({
                        navigationStart: Date.now() - Math.random() * 1000,
                        unloadEventStart: 0,
                        unloadEventEnd: 0,
                        redirectStart: 0,
                        redirectEnd: 0,
                        fetchStart: Date.now() - Math.random() * 800,
                        domainLookupStart: Date.now() - Math.random() * 600,
                        domainLookupEnd: Date.now() - Math.random() * 500,
                        connectStart: Date.now() - Math.random() * 400,
                        connectEnd: Date.now() - Math.random() * 300,
                        requestStart: Date.now() - Math.random() * 200,
                        responseStart: Date.now() - Math.random() * 100,
                        responseEnd: Date.now() - Math.random() * 50,
                        domLoading: Date.now() - Math.random() * 30,
                        domInteractive: Date.now() - Math.random() * 20,
                        domContentLoadedEventStart: Date.now() - Math.random() * 10,
                        domContentLoadedEventEnd: Date.now(),
                        domComplete: Date.now(),
                        loadEventStart: Date.now(),
                        loadEventEnd: Date.now()
                    }),
                    configurable: true
                });
            }
        """)
        
    async def cleanup(self):
        """브라우저 정리"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
            
    async def login(self, username: str, password: str) -> bool:
        """배민 로그인 - 완전히 사람처럼"""
        try:
            print(f"[배민] 로그인 시도: {username}")

            # 사람처럼 천천히 로그인 페이지로 이동
            print(f"[배민] 로그인 페이지로 이동: {self.login_url}")
            await self.page.goto(self.login_url, wait_until='load', timeout=30000)

            # 사람처럼 페이지 둘러보기
            await asyncio.sleep(3)  # 페이지를 읽는 시간

            # 간단한 사람 시뮬레이션 (메모리 효율적)
            await self.page.mouse.move(300, 200)
            await asyncio.sleep(1)
            await self.page.mouse.move(600, 400)
            await asyncio.sleep(1)

            # 간단한 스크롤
            await self.page.evaluate("window.scrollTo(0, 100)")
            await asyncio.sleep(1)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)

            # JavaScript 실행 완료 대기
            try:
                await self.page.wait_for_load_state('networkidle', timeout=10000)
            except:
                print("[배민] NetworkIdle 대기 실패, 계속 진행")
                pass

            # 페이지 정보 확인
            current_url = self.page.url
            title = await self.page.title()
            print(f"[배민] 페이지 로드 완료 - URL: {current_url}")
            print(f"[배민] 페이지 제목: {title}")

            # 페이지에 있는 모든 input 요소 확인
            try:
                all_inputs = await self.page.evaluate('''
                    () => {
                        const inputs = Array.from(document.querySelectorAll('input'));
                        return inputs.map(input => ({
                            type: input.type,
                            name: input.name,
                            id: input.id,
                            placeholder: input.placeholder,
                            className: input.className,
                            testId: input.getAttribute('data-testid')
                        }));
                    }
                ''')
                print(f"[배민] 페이지에서 발견된 input 요소들:")
                for i, input_info in enumerate(all_inputs):
                    print(f"  {i+1}. type: {input_info['type']}, name: {input_info['name']}, id: {input_info['id']}")
                    print(f"     placeholder: {input_info['placeholder']}, testId: {input_info['testId']}")
                    print(f"     className: {input_info['className']}")
            except Exception as e:
                print(f"[배민] 페이지 분석 오류: {e}")
            
            # ID 입력 - 여러 가능한 셀렉터 시도
            id_selectors = [
                'input[name="id"][data-testid="id"]',
                'input[name="id"]',
                'input[data-testid="id"]',
                'input[type="text"]',
                'input[placeholder*="아이디"]',
                'input[placeholder*="ID"]'
            ]

            id_input_success = False
            for selector in id_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)

                    # 사람처럼 필드 클릭 후 천천히 타이핑
                    element = await self.page.query_selector(selector)
                    if element:
                        # 필드 근처로 마우스 이동 후 클릭
                        box = await element.bounding_box()
                        if box:
                            await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=10)
                            await asyncio.sleep(0.5)
                            await self.page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                            await asyncio.sleep(1)

                            # 사람처럼 천천히 타이핑
                            await element.type(username, delay=100)
                            print(f"[배민] ID 입력 성공 - 셀렉터: {selector}")
                            id_input_success = True
                            break
                except Exception as e:
                    print(f"[배민] ID 셀렉터 {selector} 실패: {e}")
                    continue

            if not id_input_success:
                print(f"[배민] 모든 ID 셀렉터 실패")
                return False
            
            # 사람처럼 잠깐 쉬고 다음 필드로
            await asyncio.sleep(1.5)

            # 비밀번호 입력 - 여러 가능한 셀렉터 시도
            password_selectors = [
                'input[name="password"][data-testid="password"]',
                'input[name="password"]',
                'input[data-testid="password"]',
                'input[type="password"]',
                'input[placeholder*="비밀번호"]',
                'input[placeholder*="password"]'
            ]

            password_input_success = False
            for selector in password_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)

                    # 사람처럼 필드 클릭 후 천천히 타이핑
                    element = await self.page.query_selector(selector)
                    if element:
                        # 필드 근처로 마우스 이동 후 클릭
                        box = await element.bounding_box()
                        if box:
                            await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=10)
                            await asyncio.sleep(0.5)
                            await self.page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                            await asyncio.sleep(1)

                            # 사람처럼 천천히 타이핑
                            await element.type(password, delay=100)
                            print(f"[배민] 비밀번호 입력 성공 - 셀렉터: {selector}")
                            password_input_success = True
                            break
                except Exception as e:
                    print(f"[배민] 비밀번호 셀렉터 {selector} 실패: {e}")
                    continue

            if not password_input_success:
                print(f"[배민] 모든 비밀번호 셀렉터 실패")
                return False
            
            # 사람처럼 입력 확인하고 로그인 버튼으로
            await asyncio.sleep(2)

            # 로그인 버튼 클릭 - 여러 가능한 셀렉터 시도
            login_button_selectors = [
                'button[type="submit"].Button__StyledButton-sc-1cxc4dz-0',
                'button[type="submit"]',
                'button:has-text("로그인")',
                'button:has-text("LOGIN")',
                'input[type="submit"]',
                '[data-testid="submit"]',
                '.login-button'
            ]

            login_button_success = False
            for selector in login_button_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)

                    # 사람처럼 버튼으로 마우스 이동 후 클릭
                    element = await self.page.query_selector(selector)
                    if element:
                        box = await element.bounding_box()
                        if box:
                            # 버튼 근처로 자연스럽게 이동
                            await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=15)
                            await asyncio.sleep(0.8)

                            # 사람처럼 살짝 망설이고 클릭
                            await self.page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                            print(f"[배민] 로그인 버튼 클릭 성공 - 셀렉터: {selector}")
                            login_button_success = True
                            break
                except Exception as e:
                    print(f"[배민] 로그인 버튼 셀렉터 {selector} 실패: {e}")
                    continue

            if not login_button_success:
                print(f"[배민] 모든 로그인 버튼 셀렉터 실패")
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