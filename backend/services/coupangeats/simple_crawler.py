# -*- coding: utf-8 -*-
"""
쿠팡이츠 크롤러 - 타임아웃 문제 해결 버전
"""

import asyncio
import random
import time
import sys
import os
from typing import Dict, List, Tuple
from playwright.async_api import async_playwright
from datetime import datetime

# 프로젝트 루트 경로를 시스템 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..', '..')
sys.path.append(project_root)

try:
    import pyperclip  # 클립보드 제어용
except ImportError:
    pyperclip = None
    print("Warning: pyperclip not installed. Using fallback typing method.")

# 프록시 및 User-Agent 로테이터 임포트
try:
    from free_proxy_manager import FreeProxyManager
    from user_agent_rotator import UserAgentRotator
except ImportError as e:
    print(f"Warning: Proxy/UA modules not found: {e}")
    FreeProxyManager = None
    UserAgentRotator = None

class CoupangEatsCrawler:
    """쿠팡이츠 크롤러 - Enhanced with Proxy + User-Agent Rotation"""
    
    def __init__(self):
        self.login_url = "https://store.coupangeats.com/merchant/login"
        self.reviews_url = "https://store.coupangeats.com/merchant/management/reviews"
        self.browser = None
        self.playwright = None
        
        # 프록시 및 User-Agent 관리자 초기화 (프록시 비활성화)
        self.proxy_manager = None  # 안정성을 위해 프록시 비활성화
        self.ua_rotator = UserAgentRotator() if UserAgentRotator else None
        self.current_proxy = None
        self.current_user_agent = None
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        
    async def initialize(self):
        """브라우저 초기화 - Enhanced with Proxy + User-Agent"""
        self.playwright = await async_playwright().start()
        
        # 프록시 비활성화, User-Agent만 설정
        self.current_proxy = None
        print("[쿠팡이츠] 직접 연결 사용 (프록시 비활성화)")

        if self.ua_rotator:
            self.current_user_agent = self.ua_rotator.get_smart_user_agent()
            print(f"[쿠팡이츠] User-Agent: {self.current_user_agent[:60]}...")
        else:
            self.current_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # 랜덤 해상도 선택
        resolutions = [
            (1920, 1080),
            (1366, 768), 
            (1536, 864),
            (1440, 900)
        ]
        width, height = random.choice(resolutions)
        
        # 브라우저 실행 옵션 구성
        launch_args = [
            # 핵심 스텔스 설정
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-http2',  # HTTP/2 프로토콜 오류 방지
            '--force-http-1',   # HTTP/1.1 강제 사용
            
            # 봇 탐지 우회 설정
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-infobars',
            '--disable-background-networking',
            '--disable-extensions',
            
            # 실제 브라우저처럼 보이게 하는 설정
            f'--user-agent={self.current_user_agent}',
            f'--window-size={width},{height}',
            '--start-maximized',
            
            # 추가 보안 우회
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
        ]
        
        # 직접 연결 설정 (프록시 없음)
        launch_options = {
            'headless': False,  # 강제로 헤드리스 비활성화
            'args': launch_args
        }
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        print(f"[쿠팡이츠] 브라우저 시작 ({width}x{height}) - 직접 연결")
            
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
            
            # 동적 해상도 설정
            resolutions = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900)]
            viewport_width, viewport_height = random.choice(resolutions)
            
            # 브라우저 컨텍스트 생성 (Enhanced 스텔스 모드)
            context = await self.browser.new_context(
                viewport={'width': viewport_width, 'height': viewport_height},
                user_agent=self.current_user_agent,
                ignore_https_errors=True,
                # 추가 브라우저 속성 설정
                locale="ko-KR",
                timezone_id="Asia/Seoul",
                geolocation={"latitude": 37.5665, "longitude": 126.9780},  # 서울
                permissions=["geolocation"]
            )
            print(f"[쿠팡이츠] 컨텍스트 생성 완료 ({viewport_width}x{viewport_height})")
            
            page = await context.new_page()
            
            # navigator.webdriver 속성 숨기기 및 기타 스텔스 설정
            await page.add_init_script("""
                // navigator.webdriver 제거
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // chrome 객체 추가 (실제 크롬처럼 보이게)
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                };
                
                // permissions 객체 추가
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
                
                // plugins 길이 설정 (헤드리스에서 0개로 나오는 것 방지)
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // languages 설정
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                });
            """)
            
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
            
            # 2. 로그인 (5회 시도)
            login_success = False
            max_attempts = 5
            
            for attempt in range(max_attempts):
                print(f"[쿠팡이츠] 로그인 시도 {attempt + 1}/{max_attempts}")
                
                try:
                    login_success = await self._login_with_stealth_monitored(page, username, password)
                    
                    if login_success:
                        print(f"[쿠팡이츠] 로그인 성공! (시도 {attempt + 1})")
                        # User-Agent 성공 기록
                        if self.ua_rotator and self.current_user_agent:
                            self.ua_rotator.mark_success(self.current_user_agent)
                            print("[쿠팡이츠] User-Agent 성공으로 기록됨")
                        break
                    else:
                        print(f"[쿠팡이츠] 로그인 실패 - 시도 {attempt + 1}")
                        if attempt < max_attempts - 1:
                            print("[쿠팡이츠] 3초 후 재시도...")
                            await page.wait_for_timeout(3000)
                            
                except Exception as e:
                    print(f"[쿠팡이츠] 로그인 시도 {attempt + 1} 중 오류: {e}")
                    if attempt < max_attempts - 1:
                        print("[쿠팡이츠] 3초 후 재시도...")
                        await page.wait_for_timeout(3000)
            
            if not login_success:
                print(f"[쿠팡이츠] 모든 로그인 시도 실패 ({max_attempts}회)")
                # User-Agent 실패 기록
                if self.ua_rotator and self.current_user_agent:
                    self.ua_rotator.mark_failure(self.current_user_agent)
                    print("[쿠팡이츠] User-Agent 실패로 기록됨")
                await self.cleanup()
                return False, [], f"로그인 실패: {max_attempts}회 시도 후 실패. 계정 정보를 확인하거나 사이트 접속을 확인해주세요"
            
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

            # 프로모션 모달 팝업 닫기 (있는 경우) - 강화된 버전
            try:
                print("[쿠팡이츠] 프로모션 모달 확인 중...")

                # 여러 모달 선택자들 시도
                modal_selectors = [
                    '.modal__contents',
                    '.modal',
                    '[role="dialog"]',
                    '.dialog',
                    '.popup',
                    'div[class*="modal"]',
                    'div[class*="dialog"]',
                    'div[class*="popup"]'
                ]

                modal_found = False
                found_selector = None
                for selector in modal_selectors:
                    modal_element = await page.query_selector(selector)
                    if modal_element:
                        print(f"[쿠팡이츠] 모달 발견 (선택자: {selector})")
                        modal_found = True
                        found_selector = selector
                        break

                if modal_found:
                    # 1. 먼저 ESC 키 여러 번 시도
                    print("[쿠팡이츠] ESC 키로 모달 닫기 시도...")
                    for i in range(3):
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(800)

                    # 2. 여전히 모달이 있다면 닫기 버튼 클릭 시도
                    modal_still_exists = False
                    for selector in modal_selectors:
                        if await page.query_selector(selector):
                            modal_still_exists = True
                            break

                    if modal_still_exists:
                        print("[쿠팡이츠] ESC로 안닫힘 - 닫기 버튼 클릭 시도...")

                        # 닫기 버튼 선택자들
                        close_selectors = [
                            'button[data-testid="Dialog__CloseButton"]',
                            'button[aria-label*="닫기"]',
                            'button[aria-label*="close"]',
                            'button[aria-label*="Close"]',
                            'button.close',
                            '.close-button',
                            'button[data-dismiss="modal"]',
                            '.modal__header button',
                            '.modal-header button',
                            '.modal .close',
                            '.dialog .close',
                            'button[title*="닫기"]',
                            'button[title*="close"]'
                        ]

                        close_clicked = False
                        for close_selector in close_selectors:
                            try:
                                close_button = await page.query_selector(close_selector)
                                if close_button:
                                    print(f"[쿠팡이츠] 닫기 버튼 클릭: {close_selector}")
                                    await close_button.click()
                                    await page.wait_for_timeout(1500)
                                    close_clicked = True
                                    break
                            except Exception as click_error:
                                print(f"[쿠팡이츠] 버튼 클릭 실패: {click_error}")
                                continue

                        # 3. 여전히 안되면 모달 배경이나 빈 공간 클릭
                        if not close_clicked:
                            print("[쿠팡이츠] 닫기 버튼 없음 - 다양한 빈 공간 클릭 시도...")

                            # 여러 빈 공간 위치 시도 (모달 외부)
                            empty_click_positions = [
                                (10, 10),      # 좌상단
                                (50, 50),      # 좌상단2
                                (10, 300),     # 좌중간
                                (10, 500),     # 좌하단
                                (1000, 10),    # 우상단
                                (1000, 300),   # 우중간
                                (500, 10),     # 상단 중앙
                                (500, 600),    # 하단 중앙
                                (200, 200),    # 중앙 좌측
                                (800, 200)     # 중앙 우측
                            ]

                            for x, y in empty_click_positions:
                                try:
                                    print(f"[쿠팡이츠] 빈 공간 클릭 시도: ({x}, {y})")
                                    await page.mouse.click(x, y)
                                    await page.wait_for_timeout(800)

                                    # 클릭 후 모달이 닫혔는지 확인
                                    modal_check = False
                                    for selector in modal_selectors:
                                        if await page.query_selector(selector):
                                            modal_check = True
                                            break

                                    if not modal_check:
                                        print(f"[쿠팡이츠] 빈 공간 클릭으로 모달 닫기 성공: ({x}, {y})")
                                        break
                                except Exception as click_error:
                                    print(f"[쿠팡이츠] 빈 공간 클릭 실패: {click_error}")
                                    continue

                            # 여전히 모달이 있다면 페이지 이동 트릭 시도
                            modal_still_there = False
                            for selector in modal_selectors:
                                if await page.query_selector(selector):
                                    modal_still_there = True
                                    break

                            if modal_still_there:
                                print("[쿠팡이츠] 페이지 이동 트릭으로 모달 닫기 시도...")
                                try:
                                    # 현재 URL 저장
                                    current_url = page.url
                                    print(f"[쿠팡이츠] 현재 URL: {current_url}")

                                    # 잠깐 다른 페이지로 이동했다가 바로 돌아오기
                                    # 쿠팡이츠 관리 페이지 내에서 안전한 페이지
                                    temp_url = "https://store.coupangeats.com/merchant/management"

                                    print(f"[쿠팡이츠] 임시 페이지로 이동: {temp_url}")
                                    await page.goto(temp_url)
                                    await page.wait_for_timeout(1000)

                                    print(f"[쿠팡이츠] 원래 페이지로 복귀: {current_url}")
                                    await page.goto(current_url)
                                    await page.wait_for_timeout(2000)

                                    print("[쿠팡이츠] 페이지 이동 트릭 완료 - 모달 확인...")

                                except Exception as nav_error:
                                    print(f"[쿠팡이츠] 페이지 이동 트릭 실패: {nav_error}")

                            # 키보드 시도
                            await page.keyboard.press("Enter")
                            await page.wait_for_timeout(500)
                            await page.keyboard.press("Space")
                            await page.wait_for_timeout(500)

                    # 4. 최종 확인
                    final_modal_exists = False
                    for selector in modal_selectors:
                        if await page.query_selector(selector):
                            final_modal_exists = True
                            break

                    if not final_modal_exists:
                        print("[쿠팡이츠] 모달 닫기 성공")
                    else:
                        print("[쿠팡이츠] 모달이 여전히 있음 - 강제로 계속 진행")
                        # 마지막 시도로 Tab 키와 Enter
                        await page.keyboard.press("Tab")
                        await page.wait_for_timeout(300)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(500)
                else:
                    print("[쿠팡이츠] 프로모션 모달 없음")

            except Exception as e:
                print(f"[쿠팡이츠] 모달 처리 중 오류 (무시): {e}")
            
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
    
    async def _enhanced_clipboard_login(self, page, username: str, password: str) -> bool:
        """coupang_review_crawler.py와 동일한 클립보드 로그인"""
        try:
            print("[쿠팡이츠] 클립보드 로그인 시작...")
            
            # ID 입력 - pyperclip 사용 (coupang_review_crawler.py와 동일)
            if pyperclip:
                try:
                    # ID 입력 - 랜덤 클릭 with 15% margin
                    print("[쿠팡이츠] ID 필드 랜덤 클릭...")
                    id_element = await page.query_selector('#loginId')
                    if id_element:
                        box = await id_element.bounding_box()
                        if box:
                            margin_x = box['width'] * 0.15
                            margin_y = box['height'] * 0.15
                            click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                            click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                            await page.mouse.click(click_x, click_y)
                            print(f"[쿠팡이츠] ID 필드 랜덤 클릭 완료: ({click_x:.1f}, {click_y:.1f})")
                        else:
                            await page.click('#loginId')
                    else:
                        await page.click('#loginId')
                    
                    await page.wait_for_timeout(random.randint(800, 1200))  # ~1초 대기
                    await page.keyboard.press('Control+A')
                    pyperclip.copy(username)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press('Control+V')
                    print("[쿠팡이츠] ID 입력 완료")
                    
                    # PW 입력 - 랜덤 클릭 with 15% margin
                    print("[쿠팡이츠] PW 필드 랜덤 클릭...")
                    pw_element = await page.query_selector('#password')
                    if pw_element:
                        box = await pw_element.bounding_box()
                        if box:
                            margin_x = box['width'] * 0.15
                            margin_y = box['height'] * 0.15
                            click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                            click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                            await page.mouse.click(click_x, click_y)
                            print(f"[쿠팡이츠] PW 필드 랜덤 클릭 완료: ({click_x:.1f}, {click_y:.1f})")
                        else:
                            await page.click('#password')
                    else:
                        await page.click('#password')
                    
                    await page.wait_for_timeout(random.randint(800, 1200))  # ~1초 대기
                    await page.keyboard.press('Control+A')
                    pyperclip.copy(password)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press('Control+V')
                    print("[쿠팡이츠] PW 입력 완료")
                    
                except Exception as clipboard_error:
                    print(f"[쿠팡이츠] 클립보드 방식 실패, JavaScript 직접 입력으로 전환: {clipboard_error}")
                    await self._javascript_input_fallback(page, username, password)
            else:
                print("[쿠팡이츠] pyperclip 없음 - JavaScript 직접 입력 방식 사용...")
                await self._javascript_input_fallback(page, username, password)
            
            print("[쿠팡이츠] 로그인 입력 완료")
            return True
            
        except Exception as e:
            print(f"[쿠팡이츠] 로그인 입력 오류: {e}")
            return False
    
    async def _javascript_input_fallback(self, page, username: str, password: str):
        """클립보드 실패시 JavaScript를 통한 직접 입력 폴백 (완전한 이벤트 발생)"""
        try:
            # ID 입력 (모든 이벤트 발생) - 랜덤 클릭 with 15% margin
            print("[쿠팡이츠] ID 필드 랜덤 클릭 (JavaScript 폴백)...")
            id_element = await page.query_selector('#loginId')
            if id_element:
                box = await id_element.bounding_box()
                if box:
                    margin_x = box['width'] * 0.15
                    margin_y = box['height'] * 0.15
                    click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                    click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                    await page.mouse.click(click_x, click_y)
                    print(f"[쿠팡이츠] ID 필드 랜덤 클릭 완료: ({click_x:.1f}, {click_y:.1f})")
                else:
                    await page.click('#loginId')
            else:
                await page.click('#loginId')
            await page.wait_for_timeout(random.randint(800, 1200))  # ~1초 대기
            
            # 기존 값 지우기
            await page.evaluate('document.querySelector("#loginId").value = ""')
            
            # 한 글자씩 입력하며 모든 이벤트 발생
            for i in range(len(username)):
                partial_text = username[:i+1]
                await page.evaluate(f'''
                    const input = document.querySelector("#loginId");
                    input.focus();
                    input.value = "{partial_text}";
                    
                    // 모든 관련 이벤트 발생
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
                ''')
                await page.wait_for_timeout(50)
            
            # 최종 blur 이벤트
            await page.evaluate('''
                const input = document.querySelector("#loginId");
                input.dispatchEvent(new Event('blur', { bubbles: true }));
            ''')
            
            # Tab키로 이동
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(200)
            
            # 비밀번호 입력 (모든 이벤트 발생)
            await page.evaluate('document.querySelector("#password").value = ""')
            
            for i in range(len(password)):
                partial_text = password[:i+1]
                await page.evaluate(f'''
                    const input = document.querySelector("#password");
                    input.focus();
                    input.value = "{partial_text}";
                    
                    // 모든 관련 이벤트 발생
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
                ''')
                await page.wait_for_timeout(50)
            
            # 최종 blur 이벤트와 폼 검증 강제 실행
            await page.evaluate('''
                const input = document.querySelector("#password");
                input.dispatchEvent(new Event('blur', { bubbles: true }));
                
                // 폼 검증 강제 실행
                const form = document.querySelector('form');
                if (form && form.checkValidity) {
                    form.checkValidity();
                }
            ''')
            
            print("[쿠팡이츠] JavaScript 폴백 입력 완료 (모든 이벤트 발생)")
            
            # 추가로 잠시 대기하여 버튼 상태 변경 확인
            await page.wait_for_timeout(500)
            
        except Exception as e:
            print(f"[쿠팡이츠] JavaScript 입력 실패: {e}")
    
    async def _enhanced_random_button_click(self, page, selector: str) -> bool:
        """간단한 랜덤 버튼 클릭"""
        try:
            button = await page.query_selector(selector)
            if not button:
                print(f"[쿠팡이츠] 버튼을 찾을 수 없음: {selector}")
                return False
            
            # 버튼의 bounding box 가져오기
            box = await button.bounding_box()
            if box:
                # 버튼 내부의 랜덤 위치 계산
                margin_x = box['width'] * 0.15
                margin_y = box['height'] * 0.15
                
                click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                
                await page.mouse.click(click_x, click_y)
                print(f"[쿠팡이츠] 랜덤 위치 클릭: ({click_x:.1f}, {click_y:.1f})")
            else:
                await button.click()
                print("[쿠팡이츠] 일반 클릭 완료")
            
            return True
            
        except Exception as e:
            print(f"[쿠팡이츠] 버튼 클릭 오류: {e}")
            return False
    
    async def _quick_login_detection(self, page) -> bool:
        """로그인 결과 8초 빠른 감지 (API 응답 대기 시간 연장)"""
        try:
            print("[쿠팡이츠] 로그인 결과 대기 중 (8초 API 응답 대기)...")
            
            # 8초동안 반복 확인 (API 응답 대기 시간 연장)
            for i in range(8):  # 1초씩 8번 확인
                await page.wait_for_timeout(1000)
                current_url = page.url
                
                # URL 변경으로 로그인 성공 판단
                if "/merchant/login" not in current_url:
                    print(f"[쿠팡이츠] 로그인 성공! URL: {current_url} (대기 시간: {i+1}초)")
                    return True
                
                # 에러 메시지 확인
                error_element = await page.query_selector('.error, .alert, [class*="error"]')
                if error_element:
                    error_text = await error_element.inner_text()
                    if error_text and error_text.strip():
                        print(f"[쿠팡이츠] 로그인 에러: {error_text}")
                        return False
            
            print("[쿠팡이츠] 로그인 실패 (8초 내 응답 없음)")
            return False
                
        except Exception as e:
            print(f"[쿠팡이츠] 로그인 감지 오류: {e}")
            return False
    
    async def _login_with_stealth_monitored(self, page, username: str, password: str) -> bool:
        """coupang_review_crawler.py와 동일한 로그인 로직"""
        try:
            print("스텔스 모드 로그인 시작...")
            
            # 로그인 페이지로 이동
            print("[Monitor] 로그인 페이지로 이동 중...")
            await page.goto("https://store.coupangeats.com/merchant/login", wait_until='domcontentloaded', timeout=30000)
            
            # DOM 안정화 대기
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            # 페이지 상태 검증
            current_url = page.url
            print(f"[Monitor] 현재 URL: {current_url}")
            
            # 성공 지표 체크 (이미 로그인된 상태인지)
            if "/merchant/login" not in current_url:
                print("이미 로그인된 상태")
                return True
            
            # 로그인 필드 확인
            print("[Monitor] 로그인 필드 찾는 중...")
            await page.wait_for_selector('#loginId', timeout=10000)
            await page.wait_for_selector('#password', timeout=10000)
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
            
            # 간단한 대기 시간
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            # 자격 증명 입력 (클립보드 방식 우선 사용)
            print("[Monitor] 자격 증명 입력 시작...")
            
            # 간단한 클립보드 로그인 (복잡한 마우스 이동 제거)
            if pyperclip:
                try:
                    print("[Monitor] 클립보드 로그인 시작...")
                    
                    # ID 입력 - 랜덤 클릭 with 15% margin
                    print("[Monitor] ID 필드 랜덤 클릭...")
                    id_element = await page.query_selector('#loginId')
                    if id_element:
                        box = await id_element.bounding_box()
                        if box:
                            margin_x = box['width'] * 0.15
                            margin_y = box['height'] * 0.15
                            click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                            click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                            await page.mouse.click(click_x, click_y)
                            print(f"[Monitor] ID 필드 랜덤 클릭 완료: ({click_x:.1f}, {click_y:.1f})")
                        else:
                            await page.click('#loginId')
                    else:
                        await page.click('#loginId')
                    
                    await page.wait_for_timeout(random.randint(800, 1200))  # ~1초 대기
                    await page.keyboard.press('Control+A')
                    pyperclip.copy(username)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press('Control+V')
                    print("[Monitor] ID 입력 완료")
                    
                    # PW 입력 - 랜덤 클릭 with 15% margin  
                    print("[Monitor] PW 필드 랜덤 클릭...")
                    pw_element = await page.query_selector('#password')
                    if pw_element:
                        box = await pw_element.bounding_box()
                        if box:
                            margin_x = box['width'] * 0.15
                            margin_y = box['height'] * 0.15
                            click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                            click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                            await page.mouse.click(click_x, click_y)
                            print(f"[Monitor] PW 필드 랜덤 클릭 완료: ({click_x:.1f}, {click_y:.1f})")
                        else:
                            await page.click('#password')
                    else:
                        await page.click('#password')
                        
                    await page.wait_for_timeout(random.randint(800, 1200))  # ~1초 대기
                    await page.keyboard.press('Control+A')
                    pyperclip.copy(password)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press('Control+V')
                    print("[Monitor] PW 입력 완료")
                    
                except Exception as clipboard_error:
                    print(f"[Monitor] 클립보드 방식 실패, JavaScript 직접 입력으로 전환: {clipboard_error}")
                    await self._javascript_input_fallback(page, username, password)
            else:
                print("[Monitor] pyperclip 없음 - JavaScript를 통한 직접 입력 방식 사용...")
                await self._javascript_input_fallback(page, username, password)
            
            # 간단한 마우스 이동 후 로그인 버튼 클릭
            print("[Monitor] 로그인 버튼 클릭...")
            await page.wait_for_timeout(500)  # 잠시 대기
            
            # 버튼 랜덤 클릭
            box = await submit_button.bounding_box()
            if box:
                margin_x = box['width'] * 0.15
                margin_y = box['height'] * 0.15
                click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                
                await page.mouse.click(click_x, click_y)
                print(f"[Monitor] 랜덤 위치 클릭: ({click_x:.1f}, {click_y:.1f})")
            else:
                await submit_button.click()
                print("[Monitor] 일반 클릭 완료")
            
            print("[Monitor] 로그인 버튼 클릭 완료 - 응답 대기 시작")
            
            # 1단계: 빠른 실패 감지 (3초 이내)
            print("[Monitor] 빠른 실패 감지 중 (3초)...")
            quick_fail_detected = False
            
            for i in range(3):  # 3초간 1초씩 체크
                await page.wait_for_timeout(1000)
                current_url = page.url
                
                # URL이 변경되었으면 성공 가능성이 있음
                if "/merchant/login" not in current_url:
                    print(f"[Monitor] URL 변경 감지! 성공 가능성 있음: {current_url}")
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
                            print(f"[Monitor] 빠른 실패 감지 - 에러 메시지: {error_text}")
                            quick_fail_detected = True
                            break
                
                if quick_fail_detected:
                    break
                    
                print(f"[Monitor] 빠른 감지 {i+1}/3 - 아직 로그인 페이지")
            
            # 3초 후에도 로그인 페이지에 있고 에러가 없으면 빠른 실패
            if not quick_fail_detected and "/merchant/login" in page.url:
                print("[Monitor] ⚡ 빠른 실패 감지 - 3초 내 변화 없음, 즉시 재시도")
                return False
            
            if quick_fail_detected:
                print("[Monitor] ⚡ 빠른 실패 감지 - 에러 메시지 발견, 즉시 재시도")
                return False
            
            # 2단계: 정상적인 URL 변경 대기
            try:
                print("[Monitor] 정상 URL 변경 대기 중...")
                await page.wait_for_url(lambda url: "/merchant/login" not in url, timeout=12000)  # 나머지 12초
                print("[Monitor] URL 변경됨")
            except:
                print("[Monitor] URL 변경 타임아웃 - 수동 확인 진행")
            
            # 로그인 성공 확인
            return await self._verify_login_success_simple(page)
            
        except Exception as e:
            print(f"[Monitor] 스텔스 로그인 오류: {e}")
            return False
    
    async def _verify_login_success_simple(self, page) -> bool:
        """로그인 성공 확인 (간단 버전)"""
        try:
            # URL 확인
            current_url = page.url
            if "/merchant/login" not in current_url:
                print(f"[Monitor] URL 변경으로 로그인 성공 확인: {current_url}")
                return True
            
            # 로그인 폼이 없으면 성공
            login_form = await page.query_selector('#loginId')
            if not login_form:
                print("[Monitor] 로그인 폼 사라짐으로 성공 확인")
                return True
            
            return False
            
        except Exception as e:
            print(f"[Monitor] 로그인 확인 중 오류: {e}")
            return False


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



if __name__ == "__main__":
    asyncio.run(test_crawler())