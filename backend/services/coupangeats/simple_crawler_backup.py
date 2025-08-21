# -*- coding: utf-8 -*-
"""
쿠팡이츠 간단 크롤러 - 새로 만든 버전
복잡한 기능 제거하고 핵심 기능만 구현
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any

from playwright.async_api import async_playwright, Browser, Page
import logging

logger = logging.getLogger(__name__)

class SimpleCoupangEatsCrawler:
    """간단한 쿠팡이츠 크롤러"""
    
    def __init__(self):
        self.browser = None
        self.playwright = None
    
    async def crawl_stores(self, username: str, password: str) -> Dict[str, Any]:
        """매장 목록 크롤링 - 가장 단순한 방식"""
        result = {
            "success": False,
            "stores": [],
            "error_message": None,
            "crawled_at": datetime.now().isoformat()
        }
        
        try:
            print(f"=== 쿠팡이츠 크롤링 시작 ===")
            print(f"계정: {username}")
            
            # 1. 브라우저 시작 - API용 격리된 환경
            print("브라우저 시작...")
            self.playwright = await async_playwright().start()
            
            # CoupangEats 우회를 위한 최강 설정 - 브라우저 자동화 완전 숨김
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # 사용자가 직접 볼 수 있도록
                channel="chrome",  # 실제 Chrome 브라우저 사용
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-infobars',
                    '--no-default-browser-check',
                    '--disable-features=TranslateUI',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--allow-running-insecure-content',
                    '--ignore-certificate-errors',
                    '--ignore-ssl-errors',
                    '--start-maximized',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ],
                # 실제 사용자 프로필 사용 시도
                executable_path=None  # 시스템 Chrome 사용
            )
            
            # 더 현실적인 브라우저 컨텍스트 설정 (새로운 User-Agent와 환경)
            import random
            
            # 다양한 User-Agent 중 랜덤 선택
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15'
            ]
            
            selected_user_agent = random.choice(user_agents)
            print(f"사용할 User-Agent: {selected_user_agent}")
            
            # 화면 해상도도 랜덤하게 변경
            viewports = [
                {'width': 1920, 'height': 1080},
                {'width': 1366, 'height': 768},
                {'width': 1440, 'height': 900},
                {'width': 1536, 'height': 864}
            ]
            selected_viewport = random.choice(viewports)
            
            context = await self.browser.new_context(
                viewport=selected_viewport,
                user_agent=selected_user_agent,
                locale='ko-KR',
                timezone_id='Asia/Seoul',
                extra_http_headers={
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            page = await context.new_page()
            
            # 쿠키 및 로컬 스토리지 완전 클리어 (안전하게)
            await page.goto("about:blank")
            await context.clear_cookies()
            try:
                await page.evaluate("""
                    try {
                        if (typeof localStorage !== 'undefined') {
                            localStorage.clear();
                        }
                    } catch(e) {
                        console.log('localStorage clear failed:', e);
                    }
                    try {
                        if (typeof sessionStorage !== 'undefined') {
                            sessionStorage.clear();
                        }
                    } catch(e) {
                        console.log('sessionStorage clear failed:', e);
                    }
                    try {
                        if ('indexedDB' in window && indexedDB.deleteDatabase) {
                            indexedDB.deleteDatabase('coupangeats');
                        }
                    } catch(e) {
                        console.log('indexedDB clear failed:', e);
                    }
                """)
            except Exception as e:
                print(f"스토리지 클리어 실패 (무시): {e}")
            print("쿠키 및 스토리지 완전 클리어 완료")
            
            # 자동화 감지 방지 (강화된 버전) - CoupangEats 특화
            await page.add_init_script("""
                // webdriver 속성 제거
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Chrome 객체 설정 (더 현실적으로)
                window.chrome = {
                    runtime: {
                        onConnect: {},
                        onMessage: {},
                        sendMessage: function() {},
                        connect: function() { return { postMessage: function() {}, onMessage: {} }; }
                    },
                    app: {
                        isInstalled: false,
                        getDetails: function() { return { name: 'Chrome', version: '121.0.0.0' }; }
                    },
                    webstore: {
                        onInstallStageChanged: {},
                        onDownloadProgress: {},
                    },
                };
                
                // 플러그인 정보 현실적으로 설정
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Chromium PDF Viewer'},
                        {name: 'Native Client', filename: 'internal-nacl-plugin', description: 'Native Client'},
                        {name: 'Microsoft Edge PDF Plugin', filename: 'edge-pdf-plugin', description: 'PDF Plugin for Edge'}
                    ],
                });
                
                // 언어 설정
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                });
                
                // 권한 설정 (더 안전하게)
                if (navigator.permissions && navigator.permissions.query) {
                    const originalQuery = navigator.permissions.query;
                    navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission || 'default' }) :
                            originalQuery(parameters)
                    );
                }
                
                // 배터리 API 제거 (자동화 감지에 사용됨)
                if ('getBattery' in navigator) {
                    delete navigator.getBattery;
                }
                
                // WebGL 정보 현실적으로 설정 (더 안전하게)
                try {
                    if (typeof WebGLRenderingContext !== 'undefined') {
                        const getParameter = WebGLRenderingContext.prototype.getParameter;
                        WebGLRenderingContext.prototype.getParameter = function(parameter) {
                            if (parameter === 37445) {
                                return 'Intel Inc.';
                            }
                            if (parameter === 37446) {
                                return 'Intel(R) UHD Graphics 620';
                            }
                            return getParameter.call(this, parameter);
                        };
                    }
                } catch (e) {
                    // WebGL 설정 실패는 무시
                }
                
                // Playwright 특유의 속성들 제거
                delete window._playwright;
                delete window.__playwright;
                
                // 마우스/키보드 이벤트 정상화
                ['click', 'mousedown', 'mouseup', 'mousemove', 'keydown', 'keyup'].forEach(eventType => {
                    const original = window.addEventListener;
                    window.addEventListener = function(type, listener, options) {
                        if (type === eventType) {
                            const wrappedListener = function(event) {
                                // isTrusted 속성을 true로 설정
                                Object.defineProperty(event, 'isTrusted', { get: () => true });
                                return listener.call(this, event);
                            };
                            return original.call(this, type, wrappedListener, options);
                        }
                        return original.call(this, type, listener, options);
                    };
                });
            """)
            
            # 페이지 에러 핸들링 (CoupangEats 특화)
            def handle_page_error(error):
                error_msg = str(error)
                # CoupangEats의 알려진 오류들은 무시 (정상 동작에 영향 없음)
                if "Cannot read properties of undefined" in error_msg:
                    print(f"알려진 오류 무시: {error_msg}")
                elif "createContext" in error_msg:
                    print(f"React 컨텍스트 오류 무시: {error_msg}")
                else:
                    print(f"Page error: {error}")
            
            def handle_request_failed(request):
                # Analytics나 광고 관련 요청 실패는 무시
                url = request.url
                ignored_domains = [
                    "analytics.google.com",
                    "mpc-prod-1-",
                    "bc.ad.daum.net",
                    "assets.coupangcdn.com"
                ]
                if any(domain in url for domain in ignored_domains):
                    print(f"무시된 요청 실패: {url}")
                else:
                    print(f"Request failed: {url}")
            
            page.on("pageerror", handle_page_error)
            page.on("requestfailed", handle_request_failed)
            
            # 2. 로그인 - 대화형 모드 (사용자가 직접 로그인)
            print("로그인 중...")
            print("=" * 60)
            print("🔥 CoupangEats 자동화 방지로 인해 수동 로그인이 필요합니다!")
            print("브라우저 창에서 직접 로그인해주세요:")
            print(f"계정: {username}")
            print(f"비밀번호: {password}")
            print("로그인 완료 후 아무 키나 눌러주세요...")
            print("=" * 60)
            
            # 로그인 페이지로 이동
            await page.goto("https://store.coupangeats.com/merchant/login", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # 사용자 입력 대기 (30초마다 URL 확인)
            login_success = False
            for i in range(10):  # 최대 5분 대기 (30초 * 10)
                await page.wait_for_timeout(30000)  # 30초 대기
                current_url = page.url
                print(f"현재 URL 확인 ({i+1}/10): {current_url}")
                
                # 로그인 성공 확인
                if "login" not in current_url or any(indicator in current_url for indicator in ["dashboard", "management", "merchant", "store", "admin", "home"]):
                    print("✅ 로그인 성공이 감지되었습니다!")
                    login_success = True
                    break
                elif i == 9:
                    print("⏰ 대기 시간이 초과되었습니다. 로그인을 확인해주세요.")
                else:
                    print("⏳ 로그인 대기 중... (브라우저에서 로그인을 완료해주세요)")
            
            if not login_success:
                result["error_message"] = "로그인 시간 초과 또는 실패"
                return result
            
            print("로그인 성공! 매장 정보를 추출합니다...")
            
            # 3. 매장 목록 추출
            print("매장 목록 추출 중...")
            
            # 현재 URL에서 매장 ID 추출 (이미 로그인된 매장)
            current_url = page.url
            print(f"현재 접속된 URL: {current_url}")
            
            # URL에서 매장 ID 추출
            if '/home/' in current_url:
                import re
                match = re.search(r'/home/(\d+)', current_url)
                if match:
                    store_id = match.group(1)
                    print(f"URL에서 매장 ID 발견: {store_id}")
                    
                    # 매장 이름 추출을 위해 드롭다운 시도, 실패하면 기본값 사용
                    stores = await self._extract_stores(page)
                    
                    # 드롭다운에서 추출 실패시 URL의 매장 ID로 기본 매장 생성
                    if not stores:
                        print("드롭다운 추출 실패, URL 기반으로 매장 정보 생성")
                        stores = [{
                            "store_name": f"매장 {store_id}",
                            "platform_store_id": store_id,
                            "platform": "coupangeats"
                        }]
                else:
                    stores = await self._extract_stores(page)
            else:
                stores = await self._extract_stores(page)
            
            # 크롤링 완료 - 브라우저 확인 시간 단축
            print("크롤링 완료. 브라우저를 10초간 열어둡니다...")
            print("매장 정보를 확인해보세요!")
            await page.wait_for_timeout(10000)
            
            result["success"] = True
            result["stores"] = stores
            print(f"크롤링 완료! {len(stores)}개 매장 발견")
            
        except Exception as e:
            print(f"크롤링 오류: {e}")
            result["error_message"] = str(e)
        
        finally:
            await self._cleanup()
        
        return result
    
    async def _setup_modal_handler(self, page: Page):
        """모달 자동 닫기 핸들러 설정"""
        try:
            # 페이지 로드 후 모달 확인 및 닫기
            await page.evaluate("""
                // 모달 자동 닫기 함수 정의
                function closeAnyModal() {
                    // 다양한 모달 닫기 버튼 셀렉터들
                    const closeSelectors = [
                        '.dialog-modal-wrapper__body--close-button',
                        'button[class*="close"]', 
                        'button[class*="modal-close"]',
                        '.modal-close',
                        '.close-button',
                        '[data-dismiss="modal"]',
                        'button[aria-label="Close"]',
                        'button[title="Close"]',
                        '.close',
                        '.btn-close'
                    ];
                    
                    // 텍스트 기반 닫기 버튼들
                    const textCloseButtons = Array.from(document.querySelectorAll('button')).filter(btn => {
                        const text = btn.textContent.trim();
                        return text === '닫기' || text === '확인' || text === 'X' || text === '×' || text === '✕';
                    });
                    
                    // 셀렉터 기반 닫기 버튼 찾기
                    for (let selector of closeSelectors) {
                        try {
                            const closeBtn = document.querySelector(selector);
                            if (closeBtn && closeBtn.offsetParent !== null) {
                                console.log('모달 닫기 버튼 발견:', selector);
                                closeBtn.click();
                                return true;
                            }
                        } catch (e) {
                            console.log('셀렉터 시도 실패:', selector, e);
                        }
                    }
                    
                    // 텍스트 기반 닫기 버튼 찾기
                    for (let btn of textCloseButtons) {
                        try {
                            if (btn.offsetParent !== null) {
                                console.log('텍스트 기반 닫기 버튼 발견:', btn.textContent);
                                btn.click();
                                return true;
                            }
                        } catch (e) {
                            console.log('텍스트 버튼 클릭 실패:', e);
                        }
                    }
                    
                    // Speak Up 모달 전용: iframe 내부 확인
                    try {
                        const iframes = document.querySelectorAll('iframe');
                        for (let iframe of iframes) {
                            try {
                                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                const closeBtn = iframeDoc.querySelector('button, .close, [role="button"]');
                                if (closeBtn) {
                                    console.log('iframe 내부 닫기 버튼 발견');
                                    closeBtn.click();
                                    return true;
                                }
                            } catch (e) {
                                // Cross-origin iframe은 접근 불가
                            }
                        }
                    } catch (e) {
                        console.log('iframe 확인 실패:', e);
                    }
                    
                    return false;
                }
                
                // 페이지 로드 시 모달 닫기 시도
                setTimeout(closeAnyModal, 1000);
                
                // 주기적으로 모달 확인 (5초마다)
                setInterval(closeAnyModal, 5000);
            """)
            print("모달 자동 닫기 핸들러 설정 완료")
        except Exception as e:
            print(f"모달 핸들러 설정 실패: {e}")
    
    async def _close_modal(self, page: Page) -> bool:
        """수동으로 모달 닫기"""
        try:
            print("모달 닫기 시도 중...")
            
            # 다양한 모달 닫기 셀렉터 시도
            modal_selectors = [
                '.dialog-modal-wrapper__body--close-button',
                'button[class*="close"]', 
                'button[class*="modal-close"]',
                '.modal-close',
                '.close-button',
                '[data-dismiss="modal"]',
                'button:has-text("닫기")',
                'button:has-text("확인")',
                'button:has-text("X")',
                '.btn-close',
                # Speak Up 모달 관련 셀렉터
                'button[aria-label="Close"]',
                'button[title="Close"]',
                '.close',
                '[role="button"]:has-text("×")',
                '[role="button"]:has-text("✕")',
                # 일반적인 모달 배경 클릭
                '.modal-backdrop',
                '.overlay'
            ]
            
            for selector in modal_selectors:
                try:
                    # 모달 버튼이 보이는지 확인 (최대 2초 대기)
                    close_btn = await page.wait_for_selector(selector, state='visible', timeout=2000)
                    if close_btn:
                        print(f"모달 닫기 버튼 발견: {selector}")
                        await close_btn.click()
                        await page.wait_for_timeout(1000)  # 모달 닫히기 대기
                        print("모달 닫기 성공")
                        return True
                except:
                    continue
            
            # JavaScript로 강제 모달 닫기 시도
            try:
                result = await page.evaluate("""
                    (function() {
                        // 모든 모달 관련 요소 찾아서 닫기
                        const modals = document.querySelectorAll('[class*="modal"], [class*="dialog"], [class*="popup"]');
                        let closed = false;
                        
                        modals.forEach(modal => {
                            if (modal.style.display !== 'none') {
                                // 모달 내부의 닫기 버튼 찾기
                                const closeBtn = modal.querySelector('button, [role="button"], .close, .btn-close');
                                if (closeBtn) {
                                    closeBtn.click();
                                    closed = true;
                                } else {
                                    // 모달 자체 숨기기
                                    modal.style.display = 'none';
                                    closed = true;
                                }
                            }
                        });
                        
                        return closed;
                    })()
                """)
                
                if result:
                    print("JavaScript로 모달 닫기 성공")
                    return True
                    
            except Exception as e:
                print(f"JavaScript 모달 닫기 실패: {e}")
            
            print("닫을 모달을 찾지 못함")
            return False
            
        except Exception as e:
            print(f"모달 닫기 오류: {e}")
            return False
    
    async def _login(self, page: Page, username: str, password: str) -> bool:
        """로그인 처리"""
        try:
            # 로그인 페이지 이동 (단계적으로)
            print("로그인 페이지로 이동 중...")
            
            # 1단계: 메인 페이지 먼저 방문 (자연스러운 접근)
            await page.goto("https://store.coupangeats.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            # 2단계: 로그인 페이지로 이동
            await page.goto("https://store.coupangeats.com/merchant/login", wait_until="domcontentloaded")
            
            # 페이지 완전 로딩 대기 - 더 긴 시간
            import random
            wait_time = random.randint(5000, 8000)
            print(f"페이지 로딩 대기: {wait_time}ms")
            await page.wait_for_timeout(wait_time)
            
            # JavaScript가 로드되었는지 확인
            try:
                js_ready = await page.evaluate("() => typeof window.React !== 'undefined' || document.readyState === 'complete'")
                print(f"JavaScript 로딩 상태: {js_ready}")
            except:
                print("JavaScript 상태 확인 실패")
            
            # 페이지 스크롤해서 자연스러운 사용자 행동 시뮬레이션
            await page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight / 4);
                setTimeout(() => window.scrollTo(0, 0), 500);
            """)
            await page.wait_for_timeout(1000)
            
            print("현재 URL:", page.url)
            
            # 로그인 폼 요소 대기
            try:
                await page.wait_for_selector('#loginId', state='visible', timeout=10000)
                print("로그인 폼 발견됨")
            except:
                print("로그인 폼을 찾을 수 없음")
                # 페이지 스크린샷 저장
                await page.screenshot(path="login_page_error.png")
                return False
            
            # 로그인 폼 입력 - 더욱 자연스럽게
            print("계정 정보 입력 중...")
            
            # 마우스 움직임 시뮬레이션
            await page.mouse.move(500, 300)
            await page.wait_for_timeout(random.randint(200, 500))
            
            # 아이디 필드 클릭 및 입력
            await page.click('#loginId')
            await page.wait_for_timeout(random.randint(300, 700))
            await page.keyboard.press('Control+a')
            await page.wait_for_timeout(random.randint(100, 300))
            
            # 한 글자씩 자연스럽게 타이핑
            for char in username:
                await page.keyboard.type(char)
                await page.wait_for_timeout(random.randint(80, 150))
            
            await page.wait_for_timeout(random.randint(500, 1000))
            
            # 비밀번호 필드 클릭 및 입력
            await page.click('#password')
            await page.wait_for_timeout(random.randint(300, 700))
            await page.keyboard.press('Control+a')
            await page.wait_for_timeout(random.randint(100, 300))
            
            # 비밀번호도 한 글자씩 자연스럽게 타이핑
            for char in password:
                await page.keyboard.type(char)
                await page.wait_for_timeout(random.randint(80, 150))
            
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            # 로그인 버튼 클릭 - 여러 셀렉터 시도
            print("로그인 버튼 찾는 중...")
            
            login_selectors = [
                'button[type="submit"].merchant-submit-btn',  # 원래 작동하던 셀렉터
                'button[type="submit"]',  # 기본 submit 버튼
                'button.merchant-submit-btn',  # 클래스만
                'button:has-text("로그인")',  # 텍스트 기반
                'form button[type="submit"]',  # 폼 안의 submit 버튼
                'input[type="submit"]'  # input 타입
            ]
            
            login_clicked = False
            for selector in login_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        print(f"로그인 버튼 발견: {selector}")
                        await button.click()
                        login_clicked = True
                        break
                except Exception as e:
                    print(f"셀렉터 {selector} 시도 실패: {e}")
                    continue
            
            if not login_clicked:
                print("로그인 버튼을 찾을 수 없음. JavaScript로 강제 클릭 시도...")
                try:
                    await page.evaluate("""
                        const buttons = document.querySelectorAll('button');
                        for (let button of buttons) {
                            if (button.textContent.includes('로그인') || button.type === 'submit') {
                                button.click();
                                console.log('JavaScript로 로그인 버튼 클릭');
                                break;
                            }
                        }
                    """)
                    login_clicked = True
                except Exception as e:
                    print(f"JavaScript 클릭도 실패: {e}")
            
            if login_clicked:
                print("로그인 버튼 클릭 완료")
            else:
                # 최후의 수단으로 Enter 키 사용
                print("Enter 키로 폼 제출 시도...")
                await page.focus('#password')
                await page.wait_for_timeout(500)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(500)
            
            # 로그인 처리를 기다림 - 더 긴 대기시간과 URL 변화 감지
            print("로그인 처리 대기 중...")
            await page.wait_for_timeout(5000)
            
            # 로그인 후 상태 확인
            current_url = page.url
            print(f"로그인 후 현재 URL: {current_url}")
            
            # 에러 메시지 확인 (더 포괄적으로)
            print("로그인 후 상태 확인 중...")
            login_error_msg = None
            try:
                # 다양한 에러 메시지 셀렉터 확인
                error_selectors = [
                    '.error', '.alert', '[class*="error"]', '[class*="alert"]',
                    '.message', '[class*="message"]', '.notification',
                    '.warning', '[class*="warning"]', '.danger',
                    '[role="alert"]', '.invalid-feedback', '.field-error'
                ]
                
                for selector in error_selectors:
                    error_elements = await page.query_selector_all(selector)
                    for error_elem in error_elements:
                        error_text = await error_elem.text_content()
                        if error_text and error_text.strip():
                            # JavaScript 오류는 무시하고 실제 로그인 관련 메시지만 처리
                            if "Cannot read properties of undefined" not in error_text:
                                print(f"⚠️ 로그인 메시지 ({selector}): {error_text.strip()}")
                                if not login_error_msg:
                                    login_error_msg = error_text.strip()
                            else:
                                print(f"JavaScript 오류 무시: {error_text.strip()}")
            except Exception as e:
                print(f"에러 메시지 확인 실패: {e}")
            
            # 추가 인증 요구사항 확인 (OTP, 캡차, 보안 질문 등)
            try:
                # 캡차 확인
                captcha_elements = await page.query_selector_all('[class*="captcha"], [id*="captcha"], img[src*="captcha"]')
                if captcha_elements:
                    print("🔒 캡차가 필요합니다")
                    await page.screenshot(path="captcha_detected.png")
                
                # OTP/SMS 인증 확인
                otp_elements = await page.query_selector_all('[class*="otp"], [class*="sms"], [class*="verification"], [placeholder*="인증"], [placeholder*="OTP"]')
                if otp_elements:
                    print("📱 OTP/SMS 인증이 필요합니다")
                    
                # 보안 질문 확인
                security_elements = await page.query_selector_all('[class*="security"], [class*="question"]')
                if security_elements:
                    print("🔐 보안 질문이 필요합니다")
                    
                # 추가 비밀번호 필드 확인
                additional_pw = await page.query_selector_all('input[type="password"]:not(#password)')
                if additional_pw:
                    print("🔑 추가 비밀번호 입력이 필요합니다")
                    
            except Exception as e:
                print(f"추가 인증 확인 실패: {e}")
            
            # 계정 상태 확인
            try:
                page_content = await page.content()
                if '계정이 잠금' in page_content or '로그인 제한' in page_content:
                    print("🚫 계정이 잠겨있거나 로그인이 제한됨")
                elif '잘못된 아이디' in page_content or '잘못된 비밀번호' in page_content:
                    print("❌ 잘못된 로그인 정보")
                elif '이용약관' in page_content or '약관 동의' in page_content:
                    print("📋 약관 동의가 필요함")
            except:
                pass
            
            # 성공 확인을 위해 더 오래 기다림
            try:
                # 로그인 응답을 기다림 (API 응답 대기)
                print("로그인 API 응답 대기 중...")
                
                # 네트워크 응답을 기다려본다 (최대 10초)
                try:
                    await page.wait_for_response(
                        lambda response: "login" in response.url and response.status == 200, 
                        timeout=10000
                    )
                    print("로그인 API 응답 수신됨")
                except:
                    print("로그인 API 응답 대기 시간 초과")
                
                # 추가 대기 후 URL 확인
                await page.wait_for_timeout(3000)
                
                # 페이지 이동을 기다림 (최대 15초)
                await page.wait_for_url(lambda url: "login" not in url, timeout=15000)
                print("로그인 성공! 페이지가 이동되었습니다.")
                
                # 로그인 성공 후 모달이 나타날 시간을 기다림
                await page.wait_for_timeout(3000)
                
                # 모달 닫기 시도 (로그인 성공 후에만)
                await self._close_modal(page)
                
                success = True
            except Exception as e:
                # URL 변화가 없으면 추가로 대기
                print("URL 변화 없음, 추가 확인 중...")
                await page.wait_for_timeout(7000)
                
                final_url = page.url
                print(f"최종 URL: {final_url}")
                
                # 다양한 성공 지표 확인
                success_indicators = [
                    "dashboard", "management", "merchant", "store", "admin"
                ]
                
                success = any(indicator in final_url for indicator in success_indicators) and "login" not in final_url
                
                if success:
                    print("로그인 성공!")
                    # 성공 시에도 페이지 확인용 대기
                    print("로그인 성공 확인을 위해 10초 대기...")
                    await page.wait_for_timeout(10000)
                else:
                    print("로그인 실패")
                    # 실패 시 스크린샷 저장
                    await page.screenshot(path="login_failed_detailed.png")
                    # 페이지 소스도 저장
                    page_content = await page.content()
                    with open("login_failed_detailed.html", "w", encoding="utf-8") as f:
                        f.write(page_content)
                    
                    # 실패 시에도 브라우저를 잠시 열어둠
                    print("로그인 실패 상태를 확인하기 위해 20초 대기합니다...")
                    print("브라우저에서 어떤 상태인지 확인해보세요!")
                    await page.wait_for_timeout(20000)
                
            return success
            
        except Exception as e:
            print(f"로그인 오류: {e}")
            try:
                await page.screenshot(path="login_exception.png")
            except:
                pass
            return False
    
    async def _extract_stores(self, page: Page) -> List[Dict[str, Any]]:
        """매장 목록 추출"""
        stores = []
        
        try:
            # 리뷰 페이지로 이동
            print("리뷰 관리 페이지로 이동 중...")
            await page.goto("https://store.coupangeats.com/merchant/management/reviews", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            # 리뷰 페이지 로드 후 모달 닫기 시도
            await self._close_modal(page)
            
            print(f"현재 페이지 URL: {page.url}")
            
            # 페이지 스크린샷 저장
            await page.screenshot(path="reviews_page.png")
            
            # 드롭다운 찾기 및 클릭
            print("매장 선택 드롭다운 찾는 중...")
            try:
                # 여러 가지 셀렉터로 시도
                dropdown_selectors = [
                    'div.button',
                    'button.button',
                    '[class*="dropdown"]',
                    '[class*="select"]',
                    'div[role="button"]'
                ]
                
                dropdown = None
                for selector in dropdown_selectors:
                    try:
                        dropdown = await page.wait_for_selector(selector, timeout=5000)
                        print(f"드롭다운 발견: {selector}")
                        break
                    except:
                        continue
                
                if not dropdown:
                    print("드롭다운을 찾을 수 없음")
                    # 페이지 내용 저장
                    page_content = await page.content()
                    with open("reviews_page.html", "w", encoding="utf-8") as f:
                        f.write(page_content)
                    return []
                
                print("드롭다운 클릭...")
                await dropdown.click()
                await page.wait_for_timeout(3000)
                
                # 클릭 후 스크린샷
                await page.screenshot(path="dropdown_opened.png")
                
            except Exception as e:
                print(f"드롭다운 클릭 오류: {e}")
                return []
            
            # 매장 옵션 추출
            print("매장 옵션 추출 중...")
            try:
                # 여러 가지 옵션 셀렉터로 시도
                option_selectors = [
                    'ul.options li',
                    'li[role="option"]',
                    'div[role="option"]',
                    '[class*="option"]',
                    'ul li',
                    'select option'
                ]
                
                options = []
                for selector in option_selectors:
                    try:
                        options = await page.query_selector_all(selector)
                        if options:
                            print(f"옵션 발견: {selector}, 개수: {len(options)}")
                            break
                    except:
                        continue
                
                if not options:
                    print("매장 옵션을 찾을 수 없음")
                    return []
                
                print(f"총 {len(options)}개 옵션 발견")
                
                for i, option in enumerate(options):
                    try:
                        text = await option.text_content()
                        print(f"옵션 {i+1}: {text}")
                        
                        if text and '(' in text and ')' in text:
                            # "매장명(ID)" 형태에서 파싱
                            text = text.strip()
                            paren_pos = text.find('(')
                            if paren_pos > 0:
                                store_name = text[:paren_pos].strip()
                                store_id_part = text[paren_pos+1:]
                                close_paren = store_id_part.find(')')
                                if close_paren > 0:
                                    store_id = store_id_part[:close_paren].strip()
                                    
                                    stores.append({
                                        "store_name": store_name,
                                        "platform_store_id": store_id,
                                        "platform": "coupangeats"
                                    })
                                    print(f"매장 추가됨: {store_name} (ID: {store_id})")
                    except Exception as e:
                        print(f"옵션 {i+1} 처리 오류: {e}")
                
            except Exception as e:
                print(f"매장 옵션 추출 오류: {e}")
        
        except Exception as e:
            print(f"매장 추출 오류: {e}")
        
        print(f"최종 발견된 매장 수: {len(stores)}")
        return stores
    
    async def _cleanup(self):
        """리소스 정리"""
        try:
            if self.browser:
                # 모든 컨텍스트와 페이지 먼저 정리
                for context in self.browser.contexts:
                    await context.close()
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"정리 중 오류 (무시): {e}")
            
        # 브라우저 관련 리소스만 정리 (임시 디렉토리 정리 제거)


# 테스트용 함수
async def test_crawl():
    """크롤러 테스트"""
    crawler = SimpleCoupangEatsCrawler()
    
    # 실제 계정 정보 사용
    username = "hong7704002646"
    password = "bin986200#"
    
    result = await crawler.crawl_stores(username, password)
    
    print("\n=== 크롤링 결과 ===")
    print(f"성공 여부: {result['success']}")
    if result.get('error_message'):
        print(f"오류: {result['error_message']}")
    
    print(f"매장 수: {len(result['stores'])}")
    for i, store in enumerate(result['stores'], 1):
        print(f"{i}. {store['store_name']} (ID: {store['platform_store_id']})")


if __name__ == "__main__":
    asyncio.run(test_crawl())