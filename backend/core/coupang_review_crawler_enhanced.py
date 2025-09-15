#!/usr/bin/env python3
"""
쿠팡잇츠 리뷰 크롤러 - Enhanced Version
- 클립보드 붙여넣기로 ID/PW 입력 (더 자연스러움)
- 로그인 버튼 랜덤 위치 클릭
- 강화된 자동화 감지 우회
"""

import asyncio
import argparse
import json
import os
import sys
import re
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import hashlib
try:
    import pyperclip  # 클립보드 제어용
except ImportError:
    pyperclip = None
    print("Warning: pyperclip not installed. Using fallback typing method.")

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from backend.services.shared.logger import get_logger
from backend.services.shared.config import settings
from backend.core.coupang_star_rating_extractor import CoupangStarRatingExtractor

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

class EnhancedCoupangReviewCrawler:
    """강화된 쿠팡잇츠 리뷰 크롤러"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.star_extractor = CoupangStarRatingExtractor()
        self.success_count = 0
        self.failure_count = 0
        
    async def create_stealth_browser(self, playwright) -> Browser:
        """스텔스 모드 브라우저 생성"""
        # 랜덤 화면 크기
        width = 1920 - random.randint(0, 200)
        height = 1080 - random.randint(0, 100)
        
        browser = await playwright.chromium.launch(
                headless=False,  # 개발 중에는 False, 운영에서는 True
                args=[
                    f'--window-size={width},{height}',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--password-store=basic',
                    '--use-mock-keychain',
                    '--force-color-profile=srgb',
                    f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{120 + random.randint(0, 5)}.0.0.0 Safari/537.36'
                ]
            )
        
        return browser
    
    async def create_stealth_context(self, browser: Browser) -> BrowserContext:
        """스텔스 브라우저 컨텍스트 생성"""
        # 랜덤 뷰포트
        viewport_width = 1920 - random.randint(0, 200)
        viewport_height = 1080 - random.randint(0, 100)
        
        context = await browser.new_context(
            viewport={'width': viewport_width, 'height': viewport_height},
            user_agent=f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{120 + random.randint(0, 5)}.0.0.0 Safari/537.36',
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            permissions=['geolocation', 'notifications'],
            ignore_https_errors=True,
            java_script_enabled=True
        )
        
        # 쿠키 추가 (선택적)
        await context.add_cookies([
            {
                'name': '_ga',
                'value': f'GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time())}',
                'domain': '.coupangeats.com',
                'path': '/'
            }
        ])
        
        return context
    
    async def inject_stealth_scripts(self, page: Page):
        """고급 스텔스 스크립트 주입"""
        await page.add_init_script("""
            // 완전한 webdriver 속성 제거
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            delete navigator.__proto__.webdriver;
            
            // Chrome 객체 완벽 모킹
            window.chrome = {
                runtime: {
                    PlatformOs: {
                        MAC: 'mac',
                        WIN: 'win',
                        ANDROID: 'android',
                        CROS: 'cros',
                        LINUX: 'linux',
                        OPENBSD: 'openbsd'
                    },
                    PlatformArch: {
                        ARM: 'arm',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64',
                        MIPS: 'mips',
                        MIPS64: 'mips64'
                    },
                    PlatformNaclArch: {
                        ARM: 'arm',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64',
                        MIPS: 'mips',
                        MIPS64: 'mips64'
                    },
                    RequestUpdateCheckStatus: {
                        THROTTLED: 'throttled',
                        NO_UPDATE: 'no_update',
                        UPDATE_AVAILABLE: 'update_available'
                    },
                    OnInstalledReason: {
                        INSTALL: 'install',
                        UPDATE: 'update',
                        CHROME_UPDATE: 'chrome_update',
                        SHARED_MODULE_UPDATE: 'shared_module_update'
                    },
                    OnRestartRequiredReason: {
                        APP_UPDATE: 'app_update',
                        OS_UPDATE: 'os_update',
                        PERIODIC: 'periodic'
                    }
                },
                app: {
                    isInstalled: false,
                    runningState: () => 'running'
                },
                csi: () => {},
                loadTimes: () => {}
            };
            
            // Plugin 배열 모킹
            Object.defineProperty(navigator, 'plugins', {
                get: function() {
                    return [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: Plugin},
                            description: "",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        },
                        {
                            0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: Plugin},
                            1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable", enabledPlugin: Plugin},
                            description: "",
                            filename: "internal-nacl-plugin",
                            length: 2,
                            name: "Native Client"
                        }
                    ];
                }
            });
            
            // Languages 설정
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });
            
            // Platform 설정
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            
            // Hardware concurrency (CPU 코어)
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // Device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // Permissions 모킹
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // WebGL Vendor 설정
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
            
            // Canvas fingerprinting 방지
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {
                const context = this.getContext('2d');
                if (context) {
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = imageData.data[i] ^ (Math.random() * 2);
                        imageData.data[i + 1] = imageData.data[i + 1] ^ (Math.random() * 2);
                        imageData.data[i + 2] = imageData.data[i + 2] ^ (Math.random() * 2);
                    }
                    context.putImageData(imageData, 0, 0);
                }
                return originalToDataURL.apply(this, arguments);
            };
            
            // Battery API 모킹
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 0.89
                });
            }
        """)
    
    async def human_like_mouse_movement(self, page: Page):
        """인간같은 마우스 움직임 시뮬레이션"""
        viewport = page.viewport_size
        if not viewport:
            return
            
        # 베지어 곡선을 이용한 자연스러운 마우스 경로
        for _ in range(random.randint(2, 4)):
            start_x = random.randint(100, viewport['width'] - 100)
            start_y = random.randint(100, viewport['height'] - 100)
            end_x = random.randint(100, viewport['width'] - 100)
            end_y = random.randint(100, viewport['height'] - 100)
            
            # 중간 지점들 생성
            control_points = []
            for i in range(random.randint(3, 6)):
                control_points.append({
                    'x': start_x + (end_x - start_x) * i / 5 + random.randint(-50, 50),
                    'y': start_y + (end_y - start_y) * i / 5 + random.randint(-50, 50)
                })
            
            # 부드러운 마우스 이동
            for point in control_points:
                await page.mouse.move(point['x'], point['y'], steps=random.randint(5, 10))
                await page.wait_for_timeout(random.randint(50, 150))
        
        # 랜덤 스크롤
        scroll_amount = random.choice([-100, -50, 0, 50, 100])
        await page.mouse.wheel(0, scroll_amount)
        await page.wait_for_timeout(random.randint(300, 700))
    
    async def clipboard_paste_login(self, page: Page, username: str, password: str):
        """클립보드를 이용한 자연스러운 로그인 (또는 대체 방법)"""
        
        if pyperclip:
            # pyperclip이 설치된 경우 클립보드 사용
            logger.info("클립보드 붙여넣기 방식으로 로그인 시작...")
            
            # 1. ID 필드에 포커스 후 클립보드 붙여넣기
            await page.click('#loginId')
            await page.wait_for_timeout(random.randint(300, 600))
            
            # 필드 전체 선택 (Ctrl+A)
            await page.keyboard.press('Control+A')
            await page.wait_for_timeout(random.randint(100, 300))
            
            # 클립보드에 ID 복사
            pyperclip.copy(username)
            await page.wait_for_timeout(random.randint(200, 400))
            
            # 붙여넣기 (Ctrl+V)
            await page.keyboard.press('Control+V')
            await page.wait_for_timeout(random.randint(500, 1000))
            
            # 2. Tab키로 다음 필드로 이동 (더 자연스러움)
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(random.randint(300, 600))
            
            # 비밀번호 필드 전체 선택
            await page.keyboard.press('Control+A')
            await page.wait_for_timeout(random.randint(100, 300))
            
            # 클립보드에 비밀번호 복사
            pyperclip.copy(password)
            await page.wait_for_timeout(random.randint(200, 400))
            
            # 붙여넣기
            await page.keyboard.press('Control+V')
            await page.wait_for_timeout(random.randint(500, 1000))
            
            logger.info("클립보드 붙여넣기 완료")
        else:
            # pyperclip이 없는 경우 JavaScript evaluate 사용
            logger.info("JavaScript를 통한 직접 입력 방식으로 로그인...")
            
            # ID 필드 클릭 및 입력
            await page.click('#loginId')
            await page.wait_for_timeout(random.randint(300, 600))
            
            # JavaScript로 직접 값 설정 (더 자연스럽게 보이도록)
            await page.evaluate(f'document.querySelector("#loginId").value = ""')
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
            
            logger.info("입력 완료")
    
    async def random_button_click(self, page: Page, selector: str):
        """버튼의 랜덤 위치 클릭"""
        button = await page.query_selector(selector)
        if not button:
            logger.error(f"버튼을 찾을 수 없음: {selector}")
            return False
        
        # 버튼의 bounding box 가져오기
        box = await button.bounding_box()
        if not box:
            logger.error("버튼 위치를 가져올 수 없음")
            return False
        
        # 버튼 내부의 랜덤 위치 계산
        # 가장자리를 피하고 중심부 70% 영역 내에서 클릭
        margin_x = box['width'] * 0.15
        margin_y = box['height'] * 0.15
        
        click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
        click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
        
        logger.info(f"버튼 랜덤 클릭 위치: ({click_x:.1f}, {click_y:.1f})")
        
        # 마우스를 클릭 위치로 이동 (자연스럽게)
        await page.mouse.move(click_x, click_y, steps=random.randint(10, 20))
        await page.wait_for_timeout(random.randint(100, 300))
        
        # 클릭
        await page.mouse.down()
        await page.wait_for_timeout(random.randint(50, 150))
        await page.mouse.up()
        
        return True
    
    async def enhanced_login(self, page: Page, username: str, password: str, max_attempts: int = 3) -> bool:
        """강화된 로그인 프로세스"""
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"로그인 시도 {attempt}/{max_attempts}")
                
                # 스텔스 스크립트 주입
                await self.inject_stealth_scripts(page)
                
                # 로그인 페이지로 이동
                await page.goto("https://store.coupangeats.com/merchant/login", 
                               wait_until='domcontentloaded', 
                               timeout=30000)
                
                # 페이지 로드 대기
                await page.wait_for_timeout(random.randint(2000, 4000))
                
                # 이미 로그인되어 있는지 확인
                current_url = page.url
                if "/merchant/login" not in current_url:
                    logger.info("이미 로그인된 상태")
                    return True
                
                # 인간같은 마우스 움직임
                await self.human_like_mouse_movement(page)
                
                # 로그인 필드 확인
                try:
                    await page.wait_for_selector('#loginId', timeout=5000)
                    await page.wait_for_selector('#password', timeout=5000)
                    await page.wait_for_selector('button[type="submit"]', timeout=5000)
                except PlaywrightTimeoutError:
                    logger.error("로그인 폼을 찾을 수 없음")
                    continue
                
                # 클립보드 붙여넣기로 로그인 정보 입력
                await self.clipboard_paste_login(page, username, password)
                
                # 잠시 대기 (사람이 확인하는 것처럼)
                await page.wait_for_timeout(random.randint(1000, 2000))
                
                # 로그인 버튼 랜덤 위치 클릭
                success = await self.random_button_click(page, 'button[type="submit"]')
                if not success:
                    logger.error("로그인 버튼 클릭 실패")
                    continue
                
                # 로그인 결과 대기
                logger.info("로그인 응답 대기 중...")
                
                # URL 변경 대기 (최대 20초)
                for i in range(20):
                    await page.wait_for_timeout(1000)
                    current_url = page.url
                    
                    if "/merchant/login" not in current_url:
                        logger.info(f"로그인 성공! URL: {current_url}")
                        self.success_count += 1
                        return True
                    
                    # 에러 메시지 확인
                    error_element = await page.query_selector('.error, .alert, [class*="error"]')
                    if error_element:
                        error_text = await error_element.inner_text()
                        if error_text and error_text.strip():
                            logger.error(f"로그인 에러: {error_text}")
                            break
                
                logger.warning(f"로그인 시도 {attempt} 실패")
                
                # 재시도 전 대기
                if attempt < max_attempts:
                    wait_time = random.randint(5000, 10000)
                    logger.info(f"{wait_time/1000:.1f}초 후 재시도...")
                    await page.wait_for_timeout(wait_time)
                    
                    # 페이지 새로고침
                    await page.reload(wait_until='domcontentloaded')
                    
            except Exception as e:
                logger.error(f"로그인 중 오류 발생: {e}")
                if attempt < max_attempts:
                    await page.wait_for_timeout(random.randint(5000, 10000))
        
        self.failure_count += 1
        return False
    
    async def crawl_reviews(self, username: str, password: str, store_id: str, days: int = 7, max_pages: int = 10):
        """리뷰 크롤링 메인 함수"""
        playwright = None
        browser = None
        try:
            # Playwright 인스턴스 생성
            playwright = await async_playwright().start()
            
            # 스텔스 브라우저 생성
            browser = await self.create_stealth_browser(playwright)
            context = await self.create_stealth_context(browser)
            page = await context.new_page()
            
            # 강화된 로그인
            login_success = await self.enhanced_login(page, username, password)
            
            if not login_success:
                logger.error("로그인 실패 - 크롤링 중단")
                return []
            
            logger.info("로그인 성공 - 리뷰 크롤링 시작")
            
            # 리뷰 페이지로 이동
            reviews_url = f"https://store.coupangeats.com/merchant/management/reviews/{store_id}"
            await page.goto(reviews_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            # 리뷰 수집 로직 (기존 코드 활용)
            reviews = []
            current_page = 1
            
            while current_page <= max_pages:
                logger.info(f"페이지 {current_page} 크롤링 중...")
                
                # 리뷰 요소 대기
                try:
                    await page.wait_for_selector('.review-item, [class*="review"]', timeout=10000)
                except:
                    logger.warning("리뷰 요소를 찾을 수 없음")
                    break
                
                # 페이지의 모든 리뷰 수집
                page_reviews = await self.extract_reviews_from_page(page)
                reviews.extend(page_reviews)
                
                # 다음 페이지로 이동
                next_button = await page.query_selector('button[aria-label="Next page"], .pagination-next')
                if next_button and current_page < max_pages:
                    await next_button.click()
                    await page.wait_for_timeout(random.randint(2000, 4000))
                    current_page += 1
                else:
                    break
            
            logger.info(f"총 {len(reviews)}개 리뷰 수집 완료")
            return reviews
            
        except Exception as e:
            logger.error(f"크롤링 중 오류: {e}")
            return []
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
    
    async def extract_reviews_from_page(self, page: Page) -> List[Dict[str, Any]]:
        """페이지에서 리뷰 추출"""
        reviews = []
        
        # 리뷰 요소들 찾기
        review_elements = await page.query_selector_all('.review-item, [class*="review-card"], [class*="review-content"]')
        
        for element in review_elements:
            try:
                review_data = {}
                
                # 고객 이름
                name_elem = await element.query_selector('[class*="customer-name"], [class*="user-name"]')
                if name_elem:
                    review_data['customer_name'] = await name_elem.inner_text()
                
                # 리뷰 내용
                content_elem = await element.query_selector('[class*="review-text"], [class*="review-content"]')
                if content_elem:
                    review_data['content'] = await content_elem.inner_text()
                
                # 별점 (SVG 또는 이미지로 되어 있을 수 있음)
                rating_elem = await element.query_selector('[class*="rating"], [class*="star"]')
                if rating_elem:
                    # CoupangStarRatingExtractor 사용
                    html_content = await element.inner_html()
                    rating = self.star_extractor.extract_star_rating(html_content)
                    review_data['rating'] = rating
                
                # 날짜
                date_elem = await element.query_selector('[class*="date"], [class*="time"]')
                if date_elem:
                    review_data['date'] = await date_elem.inner_text()
                
                # 메뉴 정보
                menu_elem = await element.query_selector('[class*="menu"], [class*="product"]')
                if menu_elem:
                    review_data['menu_items'] = await menu_elem.inner_text()
                
                if review_data:
                    reviews.append(review_data)
                    
            except Exception as e:
                logger.error(f"리뷰 추출 중 오류: {e}")
                continue
        
        return reviews

async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='쿠팡잇츠 리뷰 크롤러 (Enhanced)')
    parser.add_argument('--username', required=True, help='쿠팡잇츠 사용자명')
    parser.add_argument('--password', required=True, help='쿠팡잇츠 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID')
    parser.add_argument('--days', type=int, default=7, help='수집할 일수')
    parser.add_argument('--max-pages', type=int, default=5, help='최대 페이지 수')
    
    args = parser.parse_args()
    
    # 크롤러 실행
    crawler = EnhancedCoupangReviewCrawler()
    reviews = await crawler.crawl_reviews(
        username=args.username,
        password=args.password,
        store_id=args.store_id,
        days=args.days,
        max_pages=args.max_pages
    )
    
    # 결과 출력
    print(f"\n크롤링 완료!")
    print(f"성공: {crawler.success_count}회")
    print(f"실패: {crawler.failure_count}회")
    print(f"수집된 리뷰: {len(reviews)}개")
    
    # 리뷰 샘플 출력
    if reviews:
        print("\n리뷰 샘플:")
        for i, review in enumerate(reviews[:3], 1):
            print(f"\n리뷰 {i}:")
            print(f"  고객: {review.get('customer_name', 'Unknown')}")
            print(f"  평점: {review.get('rating', 'N/A')}")
            print(f"  내용: {review.get('content', '')[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())