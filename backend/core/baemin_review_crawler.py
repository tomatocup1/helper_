#!/usr/bin/env python3
"""
배달의민족 리뷰 크롤링 엔진
- 배달의민족 리뷰 페이지 자동 수집
- 별점, 텍스트, 주문메뉴, 배송평가 통합 추출
- SVG 별점 구조 분석을 통한 정확한 평점 추출
"""

import os
import sys
import json
import asyncio
import argparse
import hashlib
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from supabase import create_client, Client
from dotenv import load_dotenv

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from baemin_star_rating_extractor import BaeminStarRatingExtractor
from utils.popup_handler import PopupHandler

def safe_console_print(message):
    """콘솔 출력용 안전한 함수 - 이모지나 특수문자 제거"""
    try:
        # 이모지 및 cp949에서 지원하지 않는 문자 제거
        import re
        clean_message = re.sub(r'[^\u0000-\uFFFF]', '?', str(message))
        clean_message = re.sub(r'[\U00010000-\U0010FFFF]', '?', clean_message)
        print(clean_message)
    except UnicodeEncodeError:
        # 최후 수단: ASCII 안전 문자만 남기기
        ascii_safe = ''.join(c if ord(c) < 128 else '?' for c in str(message))
        print(ascii_safe)

def log_only(logger, level, message):
    """로그 파일에만 기록하는 함수 - 모든 문자 안전"""
    logger.log(level, message)

class BaeminReviewCrawler:
    def __init__(self, headless=False, timeout=30000):
        self.headless = headless
        self.timeout = timeout
        
        # 향상된 별점 추출기 초기화
        self.rating_extractor = BaeminStarRatingExtractor()
        
        # Supabase 클라이언트 초기화 (Service Role Key 사용 - RLS 우회)
        load_dotenv()
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            raise ValueError("Supabase 환경변수가 설정되지 않았습니다. NEXT_PUBLIC_SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 확인하세요.")
        
        self.supabase: Client = create_client(supabase_url, supabase_service_key)

        # 로거 설정
        self._setup_logger()

    def _setup_logger(self):
        """로그 파일 설정"""
        # 로그 디렉토리 생성
        log_dir = Path(__file__).parent.parent / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # 로그 파일명 (날짜별)
        today = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f"baemin_crawler_{today}.log"

        # 로거 설정
        self.logger = logging.getLogger('baemin_crawler')
        self.logger.setLevel(logging.INFO)

        # 핸들러가 이미 있으면 제거 (중복 방지)
        if self.logger.handlers:
            self.logger.handlers.clear()

        # 파일 핸들러만 사용 (콘솔 출력은 별도 처리)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 포맷터
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # 파일 핸들러만 추가
        self.logger.addHandler(file_handler)

        # 부모 로거로의 전파 방지 (중복 출력 방지)
        self.logger.propagate = False

        self.logger.info(f"배민 크롤러 로그 시작 - 로그 파일: {log_file}")

    async def _get_unanswered_count(self, page) -> int:
        """미답변 탭에서 '미답변(N)' 숫자를 동적으로 추출하여 목표 개수 설정"""
        try:
            count = await page.evaluate('''() => {
                const elements = Array.from(document.querySelectorAll('span,button,div,a'));
                const el = elements.find(n => /미답변\\s*\\(\\d+\\)/.test(n.textContent || ''));
                if (!el) {
                    console.log('미답변(N) 텍스트를 찾을 수 없음');
                    return 30; // 기본값
                }
                const match = (el.textContent || '').match(/미답변\\s*\\((\\d+)\\)/);
                const result = match ? parseInt(match[1]) : 30;
                console.log('미답변 개수 추출:', result);
                return result;
            }''')
            self.logger.info(f"동적 목표 설정: {count}개 (미답변 탭에서 추출)")
            return count
        except Exception as e:
            self.logger.warning(f"미답변 개수 추출 실패: {e}, 기본값 30 사용")
            return 30

    async def _get_review_scroll_container(self, page):
        """리뷰 리스트의 실제 스크롤 컨테이너를 자동 감지"""
        try:
            container_handle = await page.evaluate_handle('''() => {
                // 1단계: 리뷰 아이템을 기준점으로 찾기
                const reviewSelectors = [
                    '.ReviewContent-module__Ksg4',
                    '[data-atelier-component="Container"]',
                    'span:contains("리뷰번호")',
                    'article', 'section'
                ];

                let firstReview = null;
                for (const selector of reviewSelectors) {
                    firstReview = document.querySelector(selector);
                    if (firstReview) break;
                }

                if (!firstReview) {
                    console.log('리뷰 요소를 찾을 수 없음, body 사용');
                    return document.scrollingElement || document.body;
                }

                // 2단계: 스크롤 가능한 조상 컨테이너 찾기
                function isScrollable(element) {
                    if (!element) return false;
                    const style = getComputedStyle(element);
                    const overflowY = style.overflowY;
                    const hasScroll = element.scrollHeight > element.clientHeight;
                    return (/(auto|scroll)/.test(overflowY) && hasScroll);
                }

                // 3단계: 위로 올라가며 스크롤 컨테이너 탐색
                let current = firstReview;
                let level = 0;
                const maxLevels = 15;

                while (current && current.parentElement && level < maxLevels) {
                    current = current.parentElement;
                    level++;

                    if (isScrollable(current)) {
                        console.log(`스크롤 컨테이너 발견 (레벨 ${level}):`, current.tagName, current.className);
                        return current;
                    }
                }

                // 4단계: 최후 수단 - 기본 스크롤 요소
                console.log('전용 스크롤 컨테이너 없음, 기본 요소 사용');
                return document.scrollingElement || document.body;
            }''')

            self.logger.info("리뷰 스크롤 컨테이너 감지 완료")
            return container_handle

        except Exception as e:
            self.logger.warning(f"스크롤 컨테이너 감지 실패: {e}, body 사용")
            return await page.evaluate_handle('() => document.scrollingElement || document.body')

    async def _get_container_scroll_info(self, container_handle):
        """컨테이너의 스크롤 정보 획득"""
        try:
            info = await container_handle.evaluate('''(container) => {
                return {
                    scrollTop: container.scrollTop,
                    scrollHeight: container.scrollHeight,
                    clientHeight: container.clientHeight,
                    scrollable: container.scrollHeight > container.clientHeight
                };
            }''')
            return info
        except Exception as e:
            self.logger.warning(f"스크롤 정보 획득 실패: {e}")
            return {'scrollTop': 0, 'scrollHeight': 0, 'clientHeight': 0, 'scrollable': False}

    async def _scroll_container_to(self, container_handle, position, behavior='auto'):
        """컨테이너를 지정된 위치로 스크롤"""
        try:
            await container_handle.evaluate('''(container, options) => {
                container.scrollTo({
                    top: options.position,
                    behavior: options.behavior
                });
            }''', {'position': position, 'behavior': behavior})
            return True
        except Exception as e:
            self.logger.warning(f"컨테이너 스크롤 실패: {e}")
            return False

    async def crawl_reviews(self, username: str, password: str,
                           platform_store_id: str, user_id: str, days: int = 7) -> Dict:
        """리뷰 크롤링 메인 함수"""
        try:
            self.logger.info(f"배민 리뷰 크롤링 시작: {platform_store_id}")
            
            # 브라우저 초기화 및 로그인
            playwright = await async_playwright().start()
            
            try:
                browser = await playwright.chromium.launch(
                    headless=self.headless,
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
                print(f"Chrome 채널 실패, Chromium으로 대체: {e}")
                browser = await playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process'
                    ]
                )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # 자동화 감지 방지
            await page.add_init_script("""
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
            
            try:
                # 로그인 수행
                login_success = await self._login(page, username, password)
                if not login_success:
                    return {
                        'success': False,
                        'error': '로그인 실패',
                        'reviews_found': 0,
                        'reviews_new': 0,
                        'reviews_updated': 0
                    }
                
                # 리뷰 크롤링
                reviews = await self._crawl_review_page(page, platform_store_id, days)
                return await self._process_review_results(reviews, platform_store_id, user_id, days)
                
            except Exception as e:
                print(f"크롤링 중 오류: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'reviews_found': 0,
                    'reviews_new': 0,
                    'reviews_updated': 0
                }
            finally:
                try:
                    await browser.close()
                    await playwright.stop()
                except:
                    pass
            
        except Exception as e:
            print(f"크롤링 초기화 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'reviews_found': 0,
                'reviews_new': 0,
                'reviews_updated': 0
            }
    
    async def _login(self, page, username: str, password: str) -> bool:
        """배민 로그인 (매장 불러오기와 동일한 로직)"""
        try:
            print("배민 로그인 페이지로 이동 중...")
            await page.goto("https://biz-member.baemin.com/login", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # 올바른 셀렉터 사용 (매장 불러오기와 동일)
            print("로그인 정보 입력 중...")
            await page.fill('input[data-testid="id"]', username)
            await page.wait_for_timeout(500)
            
            await page.fill('input[data-testid="password"]', password)
            await page.wait_for_timeout(500)
            
            # 로그인 버튼 클릭
            print("로그인 버튼 클릭 중...")
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(3000)
            
            # 로그인 성공 확인
            current_url = page.url
            print(f"로그인 후 URL: {current_url}")
            
            if 'login' not in current_url:
                self.logger.info("배민 로그인 성공")
                return True
            else:
                self.logger.error("배민 로그인 실패 - 로그인 페이지에 남아있음")
                return False
                
        except Exception as e:
            self.logger.error(f"로그인 중 오류: {str(e)}")
            return False
    
    async def _crawl_review_page(self, page, platform_store_id: str, days: int) -> List[Dict]:
        """배민 리뷰 페이지 크롤링"""
        reviews = []  # 리뷰 저장할 리스트 초기화
        processed_review_ids = set()  # 처리된 리뷰 ID 추적

        try:
            # 리뷰 페이지로 직접 이동
            review_url = f"https://self.baemin.com/shops/{platform_store_id}/reviews"
            print(f"리뷰 페이지로 이동: {review_url}")
            
            try:
                # DOM이 로드되면 바로 진행 (networkidle을 기다리지 않음)
                await page.goto(review_url, wait_until='domcontentloaded', timeout=15000)
            except Exception as e:
                # 타임아웃이 발생해도 페이지는 이미 이동했을 가능성이 높으므로 계속 진행
                print(f"[WARNING] 페이지 로드 타임아웃 (무시하고 진행): {str(e)}")
            
            await page.wait_for_timeout(3000)
            self.logger.info("리뷰 페이지 로드 완료")
            
            # 팝업 닫기 시도 (새로운 범용 핸들러 사용)
            await PopupHandler.handle_baemin_popup(page)
            
            # 날짜 필터 선택 (드롭박스 클릭 후 라디오 버튼 선택)
            print(f"날짜 필터 선택 시도: 최근 {days}일")
            try:
                # 1. 먼저 날짜 드롭박스 클릭 (현재 날짜 표시 영역)
                date_dropdown = await page.query_selector("div.ReviewFilter-module__NZW0")
                if date_dropdown:
                    await date_dropdown.click()
                    await page.wait_for_timeout(1000)
                    print("[SUCCESS] 날짜 드롭박스 열기 성공")
                
                # 2. 라디오 버튼 선택
                if days >= 30:
                    # 최근 30일 선택
                    radio_30 = await page.query_selector('input[type="radio"][value="최근 30일"]')
                    if radio_30:
                        await radio_30.click()
                        print("[SUCCESS] 최근 30일 선택")
                else:
                    # 최근 7일 선택  
                    radio_7 = await page.query_selector('input[type="radio"][value="최근 7일"]')
                    if radio_7:
                        await radio_7.click()
                        print("[SUCCESS] 최근 7일 선택")
                
                await page.wait_for_timeout(500)
                
                # 3. 적용 버튼 클릭 (중요!)
                apply_button = await page.query_selector('button[type="button"]:has-text("적용")')
                if apply_button:
                    await apply_button.click()
                    print("[SUCCESS] 적용 버튼 클릭")
                    await page.wait_for_timeout(2000)
                
                print(f"[SUCCESS] 날짜 필터 적용 완료")
            except Exception as e:
                print(f"[WARNING] 날짜 필터 선택 실패, 기본값(6개월) 사용: {str(e)}")
            
            # 미답변 탭으로 이동하여 답변이 필요한 리뷰만 확인
            try:
                print("[SEARCH] 미답변 탭 검색 중...")
                
                # JavaScript로 미답변 탭 찾기 및 클릭
                unanswered_clicked = await page.evaluate('''() => {
                    // 모든 버튼 요소 검색
                    const buttons = Array.from(document.querySelectorAll('button'));
                    
                    for (let button of buttons) {
                        const text = button.textContent || '';
                        const id = button.id || '';
                        const ariaControls = button.getAttribute('aria-controls') || '';
                        
                        // 미답변 탭 조건 확인
                        if (text.includes('미답변') || id.includes('no-comment') || ariaControls.includes('noComment')) {
                            console.log('미답변 탭 발견:', text, 'ID:', id);
                            
                            // 이미 활성화되어 있는지 확인
                            const isActive = button.getAttribute('aria-selected') === 'true';
                            
                            if (!isActive) {
                                try {
                                    button.click();
                                    console.log('미답변 탭 클릭 성공');
                                    return { success: true, text: text, action: 'clicked' };
                                } catch (e) {
                                    console.log('미답변 탭 클릭 실패:', e);
                                    return { success: false, error: e.toString() };
                                }
                            } else {
                                console.log('미답변 탭 이미 활성화됨');
                                return { success: true, text: text, action: 'already_active' };
                            }
                        }
                    }
                    
                    return { success: false, error: '미답변 탭을 찾을 수 없음' };
                }''')
                
                if unanswered_clicked.get('success'):
                    if unanswered_clicked.get('action') == 'clicked':
                        await page.wait_for_timeout(3000)  # 탭 전환 대기
                        print(f"[SUCCESS] 미답변 탭 클릭 성공: {unanswered_clicked.get('text')}")
                    else:
                        print(f"[SUCCESS] 미답변 탭 이미 활성화: {unanswered_clicked.get('text')}")
                else:
                    print(f"[WARNING] 미답변 탭 조작 실패: {unanswered_clicked.get('error')}")
                    print("전체 탭에서 미답변 리뷰만 필터링하여 진행")
                        
            except Exception as e:
                print(f"[INFO] 미답변 탭 처리 중 오류: {str(e)}")
                print("전체 탭에서 미답변 리뷰만 필터링하여 진행")
            
            # 가상 스크롤 처리 - 스크롤하면서 바로 추출
            print("[SCROLL] 가상 스크롤 방식 크롤링 시작...")
            await self._extract_with_virtual_scroll(page, reviews, processed_review_ids)

            print(f"수집된 리뷰 수: {len(reviews)}")
            return reviews
            
        except Exception as e:
            print(f"리뷰 페이지 크롤링 중 오류: {str(e)}")
            return []
    
    async def _select_store(self, page, platform_store_id: str):
        """매장 선택 및 sub_type 추출"""
        try:
            print("매장 선택 및 sub_type 추출 중...")
            
            # 매장 목록에서 해당 매장 찾기 및 클릭
            store_selector = f'[data-store-id="{platform_store_id}"]'
            store_element = await page.wait_for_selector(store_selector, timeout=10000)
            
            if store_element:
                # sub_type 추출 ([음식배달], [포장주문] 등)
                sub_type_element = await store_element.query_selector('.store-type')
                sub_type = ""
                if sub_type_element:
                    sub_type_text = await sub_type_element.text_content()
                    # [음식배달] 형태에서 음식배달만 추출
                    import re
                    match = re.search(r'\[([^\]]+)\]', sub_type_text)
                    if match:
                        sub_type = match.group(1)
                        print(f"sub_type 추출: {sub_type}")
                
                # platform_stores 테이블에 sub_type 업데이트
                if sub_type:
                    await self._update_store_sub_type(platform_store_id, sub_type)
                
                # 매장 클릭
                await store_element.click()
                await asyncio.sleep(2)
            
        except Exception as e:
            print(f"매장 선택 중 오류: {str(e)}")
    
    async def _update_store_sub_type(self, platform_store_id: str, sub_type: str):
        """platform_stores 테이블의 sub_type 업데이트"""
        try:
            result = self.supabase.table('platform_stores').update({
                'sub_type': sub_type
            }).eq('platform_store_id', platform_store_id).eq('platform', 'baemin').execute()
            
            if result.data:
                print(f"sub_type 업데이트 완료: {sub_type}")
            
        except Exception as e:
            print(f"sub_type 업데이트 중 오류: {str(e)}")
    
    async def _extract_reviews(self, page) -> List[Dict]:
        """가상 스크롤 방식 리뷰 데이터 추출 - 스크롤하면서 즉시 추출"""
        reviews = []
        processed_review_ids = set()  # 이미 처리한 리뷰 ID 추적
        
        try:
            # 리뷰 목록 로드 대기
            await page.wait_for_timeout(3000)

            # 가상 스크롤 처리 - 스크롤하면서 바로 추출
            print("[SCROLL] 가상 스크롤 방식 크롤링 시작...")
            await self._extract_with_virtual_scroll(page, reviews, processed_review_ids)

            # 가상 스크롤로 모든 리뷰를 수집했으므로 바로 반환
            print(f"[SUCCESS] 가상 스크롤 완료: 총 {len(reviews)}개 리뷰 수집")
            return reviews

            # === 아래는 기존 로직 (사용하지 않음) ===
            print("페이지 구조 분석 중...")
            
            # 디버그: 현재 페이지의 HTML 일부 출력
            try:
                # 전체 리뷰 섹션 찾기
                main_content = await page.query_selector('main, div[role="main"], div[class*="content"]')
                if main_content:
                    # 리뷰 관련 요소들 찾기
                    all_elements = await main_content.query_selector_all('article, section, div[class*="Review"], div[class*="review"], li')
                    print(f"발견된 잠재적 리뷰 요소 수: {len(all_elements)}")
                    
                    # 첫 몇 개 요소의 클래스명 확인
                    for i, elem in enumerate(all_elements[:5]):
                        class_name = await elem.get_attribute('class')
                        if class_name:
                            print(f"  요소 {i+1} 클래스: {class_name[:100]}...")
            except Exception as e:
                print(f"디버그 중 오류: {str(e)}")
            
            # 리뷰 컨테이너 찾기 - 더 포괄적인 선택자
            print("리뷰 요소 검색 중...")
            
            # Typography 클래스를 포함한 span의 부모 요소 찾기
            # 리뷰어 이름이나 날짜를 포함한 요소의 상위 컨테이너
            review_selector = None
            
            # 방법 1: 리뷰어 이름을 포함한 요소의 상위 컨테이너 찾기 (신구조 모두 지원)
            try:
                reviewer_span = await page.query_selector('span.Typography_b_pnsa_1bisyd47') or \
                                await page.query_selector('span.Typography_b_dvcv_1bisyd47') or \
                                await page.query_selector('span.Typography_b_c9kn_1bisyd47')
                if reviewer_span:
                    # JavaScript로 상위 컨테이너 정보 얻기
                    container_info = await reviewer_span.evaluate('''(element) => {
                        const parent = element.closest("article, section, div[class*='module'], li");
                        if (parent) {
                            return {
                                tagName: parent.tagName.toLowerCase(),
                                className: parent.className
                            };
                        }
                        return null;
                    }''')
                    
                    if container_info:
                        if container_info['className'] and container_info['className'].strip():
                            # 클래스명이 있을 때만 클래스 선택자 추가
                            class_name = container_info['className'].split(" ")[0]
                            if class_name:
                                review_selector = f'{container_info["tagName"]}.{class_name}'
                            else:
                                review_selector = container_info['tagName']
                        else:
                            review_selector = container_info['tagName']
                        
                        print(f"[SUCCESS] 리뷰 컨테이너 발견: {review_selector}")
            except Exception as e:
                print(f"리뷰어 기반 검색 실패: {str(e)}")
            
            # 방법 2: 리뷰번호를 포함한 텍스트로 찾기
            if not review_selector:
                try:
                    review_number_elements = await page.query_selector_all('span:has-text("리뷰번호")')
                    if review_number_elements:
                        for elem in review_number_elements:
                            container_info = await elem.evaluate('''(element) => {
                                const parent = element.closest("article, section, div, li");
                                if (parent) {
                                    return parent.tagName.toLowerCase();
                                }
                                return null;
                            }''')
                            if container_info:
                                review_selector = container_info
                                print(f"[SUCCESS] 리뷰번호 기반 컨테이너 발견: {review_selector}")
                                break
                except Exception as e:
                    print(f"리뷰번호 기반 검색 실패: {str(e)}")
            
            if not review_selector:
                print("[WARNING] 리뷰 요소를 찾을 수 없습니다. 기본 선택자 사용")
                review_selector = "article, section, div"
            
            # 리뷰 요소 찾기 - 간단하고 직접적인 방법
            review_elements = []
            found_review_ids = set()  # 중복 방지를 위한 리뷰 ID 추적
            try:
                # 방법 1: 리뷰번호 span을 포함하는 가장 가까운 적절한 컨테이너 찾기
                review_number_spans = await page.query_selector_all('span:has-text("리뷰번호")')
                print(f"리뷰번호 요소 {len(review_number_spans)}개 발견")
                
                for span in review_number_spans:
                    try:
                        # 더 보수적인 접근: 리뷰번호 span의 직접적인 상위 몇 단계만 확인
                        container = await span.evaluate('''(element) => {
                            // 리뷰번호 span에서 시작해서 적절한 리뷰 컨테이너 찾기
                            let current = element;
                            let maxLevels = 10; // 최대 10레벨까지만 상위로 이동
                            let level = 0;
                            
                            while (current && current.parentElement && level < maxLevels) {
                                current = current.parentElement;
                                level++;
                                
                                // 리뷰 데이터가 포함될 만한 적절한 크기의 컨테이너인지 확인
                                const textLength = current.textContent ? current.textContent.length : 0;
                                const hasMultipleSpans = current.querySelectorAll('span').length >= 3;
                                const hasReviewData = current.textContent.includes('리뷰번호') && 
                                                    (current.textContent.match(/\\d{4}년/) || 
                                                     current.querySelector('span.Typography_b_pnsa_1bisyd47') ||
                                                     current.querySelector('span.Typography_b_dvcv_1bisyd47'));
                                
                                // 조건: 텍스트가 충분히 있고, span 요소가 여러개 있으며, 리뷰 데이터가 포함된 경우
                                if (textLength > 50 && hasMultipleSpans && hasReviewData) {
                                    return {
                                        tagName: current.tagName.toLowerCase(),
                                        className: current.className,
                                        textContent: current.textContent.substring(0, 200), // 디버깅용
                                        level: level
                                    };
                                }
                            }
                            return null;
                        }''')
                        
                        if container:
                            print(f"  리뷰 컨테이너 후보 발견 (레벨 {container['level']}): {container['tagName']} - {container['textContent'][:100]}...")
                            
                            # 컨테이너에서 리뷰번호 추출
                            container_review_id = None
                            try:
                                import re
                                container_text = container['textContent']
                                if container_text and '리뷰번호' in container_text:
                                    match = re.search(r'리뷰번호\s*(\d+)', container_text)
                                    if match:
                                        container_review_id = match.group(1)
                                        print(f"      현재 컨테이너 리뷰번호 추출: {container_review_id}")
                            except:
                                pass
                                
                            # 중복 확인
                            if container_review_id and container_review_id in found_review_ids:
                                print(f"    [WARNING] 중복 리뷰 컨테이너 건너뛰기 (ID: {container_review_id})")
                                continue
                            
                            # 직접 리뷰 ID로 요소 찾기 (클래스 기반 매칭 대신)
                            if container_review_id:
                                try:
                                    # 페이지에서 해당 리뷰 ID를 포함하는 가장 작은 컨테이너 찾기
                                    review_element = await page.evaluate(f'''() => {{
                                        const reviewId = "{container_review_id}";
                                        let bestElement = null;
                                        let smallestLength = Infinity;
                                        
                                        const allElements = document.querySelectorAll('*');
                                        
                                        for (let elem of allElements) {{
                                            if (elem.textContent && elem.textContent.includes('리뷰번호 ' + reviewId)) {{
                                                const textLength = elem.textContent.length;
                                                
                                                // 미답변 탭에서는 더욱 관대한 조건 (크기 제한 완화)
                                                if (textLength > 10000 || textLength < 50) continue;
                                                
                                                // 리뷰 데이터가 있는지 확인 (미답변 탭에서는 매우 관대하게)
                                                const hasReviewData = elem.textContent.match(/\\d{{4}}년/) &&
                                                                     elem.querySelectorAll('span').length >= 2;
                                                
                                                // 정렬 헤더나 대시보드 요소는 제외
                                                const isHeaderElement = elem.textContent.includes('리뷰 정렬') ||
                                                                       elem.textContent.includes('평균 별점') ||
                                                                       elem.textContent.includes('기본 리뷰 정렬') ||
                                                                       elem.textContent.includes('필터') ||
                                                                       elem.textContent.includes('정렬방식');
                                                
                                                // 리뷰 조건: 모든 리뷰 수집 (답글 여부와 관계없이)
                                                const isValidReview = hasReviewData && !isHeaderElement;

                                                if (isValidReview && textLength < smallestLength) {{
                                                    // 다른 리뷰 ID가 포함되어 있는지 확인 (여러 리뷰가 포함된 컨테이너도 허용)
                                                    const reviewIdMatches = elem.textContent.match(/리뷰번호\\s*\\d+/g);
                                                    if (reviewIdMatches && reviewIdMatches.length >= 1) {{
                                                        bestElement = {{
                                                            tagName: elem.tagName.toLowerCase(),
                                                            className: elem.className,
                                                            id: elem.id || '',
                                                            textContent: elem.textContent.substring(0, 300)
                                                        }};
                                                        smallestLength = textLength;
                                                    }}
                                                }}
                                            }}
                                        }}
                                        return bestElement;
                                    }}''')
                                    
                                    if review_element:
                                        print(f"      JavaScript 발견 요소: {review_element['tagName']}.{review_element.get('className', 'no-class')[:50]} (텍스트 길이: {len(review_element['textContent'])})")
                                        print(f"      요소 텍스트 일부: {review_element['textContent'][:100]}...")
                                        
                                        # 찾은 요소 정보로 실제 ElementHandle 가져오기
                                        actual_elem = None
                                        if review_element['id']:
                                            actual_elem = await page.query_selector(f"#{review_element['id']}")
                                            print(f"      ID 선택자로 요소 발견")
                                        elif review_element['className']:
                                            selector = f"{review_element['tagName']}.{review_element['className'].split()[0]}"
                                            elements = await page.query_selector_all(selector)
                                            print(f"      클래스 선택자로 {len(elements)}개 요소 발견")
                                            for i, elem in enumerate(elements):
                                                elem_text = await elem.text_content()
                                                if elem_text and f'리뷰번호 {container_review_id}' in elem_text and len(elem_text) < 2000:
                                                    actual_elem = elem
                                                    print(f"      매칭된 요소: {i+1}번째 (텍스트 길이: {len(elem_text)})")
                                                    break
                                        else:
                                            # 클래스가 없는 경우: 텍스트 내용으로 직접 찾기
                                            print(f"      클래스가 없는 요소 - 텍스트로 직접 매칭")
                                            all_elements = await page.query_selector_all(review_element['tagName'])
                                            print(f"      {review_element['tagName']} 태그 {len(all_elements)}개 발견")
                                            
                                            target_text_part = review_element['textContent'][:100]  # 처음 100자로 매칭
                                            for i, elem in enumerate(all_elements):
                                                try:
                                                    elem_text = await elem.text_content()
                                                    if elem_text and f'리뷰번호 {container_review_id}' in elem_text:
                                                        # 텍스트 내용이 일치하는지 확인 (처음 100자)
                                                        if elem_text.startswith(target_text_part[:50]):  # 더 확실한 매칭을 위해 50자
                                                            actual_elem = elem
                                                            print(f"      텍스트 매칭 성공: {i+1}번째 요소 (길이: {len(elem_text)})")
                                                            break
                                                except:
                                                    continue
                                        
                                        if actual_elem:
                                            # 추가하기 전에 실제 내용 확인
                                            test_text = await actual_elem.text_content()
                                            print(f"      실제 ElementHandle 텍스트 길이: {len(test_text) if test_text else 0}")
                                            if test_text and len(test_text) > 50:
                                                print(f"      실제 ElementHandle 텍스트 일부: {test_text[:100]}")
                                            
                                            review_elements.append(actual_elem)
                                            found_review_ids.add(container_review_id)
                                            print(f"    [SUCCESS] 새로운 리뷰 컨테이너 추가 (ID: {container_review_id})")
                                        else:
                                            print(f"    [WARNING] 리뷰 요소를 ElementHandle로 변환 실패 (ID: {container_review_id})")
                                    else:
                                        print(f"    [WARNING] 리뷰 ID로 요소 찾기 실패 (ID: {container_review_id})")

                                except Exception as e:
                                    error_msg = str(e)
                                    if "collected" in error_msg:
                                        print(f"    [INFO] 객체 참조 문제로 건너뛰기 (ID: {container_review_id})")
                                        # 메모리 정리를 위해 잠시 대기
                                        await page.wait_for_timeout(100)
                                    else:
                                        print(f"    [ERROR] 리뷰 요소 찾기 중 오류 (ID: {container_review_id}): {error_msg}")
                                    continue

                    except Exception as e:
                        error_msg = str(e)
                        if "collected" in error_msg:
                            print(f"    [INFO] 객체 참조 문제로 컨테이너 건너뛰기")
                            continue
                        else:
                            print(f"리뷰 컨테이너 찾기 중 오류: {error_msg}")
                            continue
                
                print(f"[SUCCESS] 총 {len(review_elements)}개의 리뷰 컨테이너 발견")
                
            except Exception as e:
                print(f"리뷰 컨테이너 검색 중 오류: {str(e)}")

            # 폴백: 간단하고 직접적인 방법으로 다시 시도
            if len(review_elements) < 5:  # 리뷰가 너무 적게 발견된 경우
                try:
                    print("[FALLBACK] 간단한 방법으로 더 많은 리뷰 검색 중...")

                    # 방법 1: 리뷰번호 텍스트가 포함된 가장 가까운 컨테이너 직접 찾기
                    additional_elements = await page.evaluate('''() => {
                        const elements = [];
                        const reviewNumbers = document.querySelectorAll('*');

                        for (let elem of reviewNumbers) {
                            if (elem.textContent && elem.textContent.includes('리뷰번호') && elem.textContent.match(/\\d{4}년/)) {
                                // 적절한 크기의 리뷰 컨테이너인지 확인
                                const textLength = elem.textContent.length;
                                if (textLength > 100 && textLength < 3000) {
                                    // 이미 찾은 리뷰 ID와 중복되는지 확인
                                    const reviewIdMatch = elem.textContent.match(/리뷰번호\\s*(\\d+)/);
                                    if (reviewIdMatch) {
                                        elements.push({
                                            reviewId: reviewIdMatch[1],
                                            textContent: elem.textContent.substring(0, 200),
                                            tagName: elem.tagName.toLowerCase(),
                                            className: elem.className || ''
                                        });
                                    }
                                }
                            }
                        }

                        return elements;
                    }''')

                    print(f"추가 검색으로 {len(additional_elements)}개 리뷰 후보 발견")

                    # 찾은 요소들을 실제 ElementHandle로 변환 (정확한 선택자 사용)
                    for elem_info in additional_elements:
                        review_id = elem_info['reviewId']
                        if review_id not in found_review_ids:
                            try:
                                # 더 정확한 선택자 사용 - div 태그만, 리뷰번호 포함
                                selectors = [
                                    f"div:has-text('리뷰번호 {review_id}')",  # div만 찾기
                                    f"article:has-text('리뷰번호 {review_id}')",  # article 태그
                                    f"section:has-text('리뷰번호 {review_id}')",  # section 태그
                                ]

                                found_element = None
                                for selector in selectors:
                                    try:
                                        actual_elements = await page.query_selector_all(selector)

                                        # 가장 적절한 크기의 요소 찾기
                                        best_element = None
                                        best_length = 0

                                        for actual_elem in actual_elements:
                                            try:
                                                elem_text = await actual_elem.text_content()
                                                if elem_text and f'리뷰번호 {review_id}' in elem_text:
                                                    text_length = len(elem_text)
                                                    # 100자 이상 3000자 이하이고, 현재까지 찾은 것 중 가장 짧은 요소 선택
                                                    if 100 < text_length < 3000:
                                                        if best_element is None or text_length < best_length:
                                                            best_element = actual_elem
                                                            best_length = text_length
                                            except:
                                                continue

                                        if best_element:
                                            found_element = best_element
                                            break
                                    except:
                                        continue

                                if found_element:
                                    review_elements.append(found_element)
                                    found_review_ids.add(review_id)
                                    print(f"    [FALLBACK] 추가 리뷰 발견: {review_id} (크기: {best_length}자)")

                            except Exception as e:
                                print(f"    [ERROR] 리뷰 {review_id} 처리 중 오류: {str(e)}")
                                continue

                    print(f"폴백 방법으로 총 {len(review_elements)}개 리뷰 컨테이너 확보")

                except Exception as fallback_error:
                    print(f"폴백 방법도 실패: {str(fallback_error)}")
            
            # 모든 리뷰 추출 (ElementHandle 가비지 컬렉션 방지)
            for i, review_element in enumerate(review_elements):
                try:
                    print(f"리뷰 {i+1}/{len(review_elements)} 처리 중...")

                    # ElementHandle이 가비지 컬렉션되지 않도록 즉시 처리
                    review_data = None

                    # 먼저 ElementHandle이 유효한지 확인
                    try:
                        # 간단한 작업으로 ElementHandle 유효성 테스트
                        tag_name = await review_element.evaluate('element => element.tagName')
                        if not tag_name:
                            print(f"  [WARNING] 리뷰 {i+1} ElementHandle 무효화됨")
                            continue
                    except Exception as e:
                        if "collected" in str(e).lower():
                            print(f"  [WARNING] 리뷰 {i+1} 이미 가비지 컬렉션됨")
                            continue
                        else:
                            print(f"  [ERROR] ElementHandle 검증 실패: {e}")
                            continue

                    # 디버깅: HTML 내용 확인 (선택적)
                    if i < 3:  # 처음 3개만 디버깅
                        try:
                            html_content = await review_element.inner_html()
                            print(f"=== 리뷰 {i+1} HTML 내용 (처음 500자) ===")
                            print(html_content[:500] + "..." if len(html_content) > 500 else html_content)
                            print("=== HTML 내용 끝 ===")
                        except Exception as e:
                            print(f"HTML 내용 확인 실패: {e}")

                    # 리뷰 데이터 추출
                    review_data = await self._extract_single_review(review_element)

                    # ID가 없는 리뷰는 건너뛰기
                    if review_data and review_data.get('baemin_review_id'):
                        reviews.append(review_data)
                        print(f"리뷰 {i+1} 추출 완료 (ID: {review_data['baemin_review_id']})")
                    elif review_data:
                        print(f"  [WARNING] 리뷰 {i+1} ID 생성 실패 - 건너뛰기")
                    else:
                        print(f"  [WARNING] 리뷰 {i+1} 데이터 추출 실패")

                except Exception as e:
                    error_msg = str(e)
                    if "collected" in error_msg.lower():
                        print(f"리뷰 {i+1} 가비지 컬렉션: ElementHandle 접근 불가")
                    else:
                        print(f"리뷰 {i+1} 처리 중 오류: {error_msg}")
                    continue
            
            print(f"총 {len(reviews)}개 리뷰 추출 완료")
            return reviews
            
        except Exception as e:
            print(f"리뷰 추출 중 오류: {str(e)}")
            return []  # reviews가 정의되지 않았을 때 빈 리스트 반환
    
    async def _extract_with_virtual_scroll(self, page, reviews: List[Dict], processed_ids: set,
                                          target_count: int = None, max_duration_sec: int = 90):
        """스마트 컨테이너 스크롤을 사용한 완전한 리뷰 추출 시스템"""
        import time
        try:
            print("\n" + "="*60)
            print("[START] 배민 리뷰 스마트 수집 시스템 시작")
            print("="*60)

            # 동적 목표 설정: 미답변(N) 숫자를 실제로 추출
            if target_count is None:
                target_count = await self._get_unanswered_count(page)

            print(f"[TARGET] 수집 목표: {target_count}개 리뷰 (미답변 리뷰)")
            print(f"[INFO] 기존 수집: {len(reviews)}개 리뷰")

            # 1단계: 스마트 스크롤 컨테이너 감지
            print("[SEARCH] 리뷰 영역 자동 감지 중...")
            container_handle = await self._get_review_scroll_container(page)
            container_info = await self._get_container_scroll_info(container_handle)

            if not container_info['scrollable']:
                print("[WARNING]  스크롤 불가능한 페이지 - 기본 모드로 전환")
                self.logger.warning("스크롤 불가능한 컨테이너, 기본 추출 모드 사용")
                return await self._extract_visible_reviews(page, processed_ids)

            print(f"[SUCCESS] 리뷰 컨테이너 감지 완료")
            print(f"[CONTAINER] 컨테이너 정보: 전체 높이 {container_info['scrollHeight']}px, 보이는 높이 {container_info['clientHeight']}px")
            print("\n[SMART_SCROLL] 스마트 스크롤링 시작...")

            started = time.time()
            scroll_attempts = 0
            max_scroll_attempts = 100  # 60 → 100으로 증가
            consecutive_no_new = 0
            total_found = 0
            last_container_height = container_info['scrollHeight']

            # 초기 리뷰 추출
            initial_reviews = await self._extract_visible_reviews(page, processed_ids)
            if initial_reviews:
                reviews.extend(initial_reviews)
                total_found = len(reviews)
                print(f"[INFO] 초기 리뷰 {len(initial_reviews)}개 발견 (총 {total_found}개)")

            # 스크롤 루프
            while (scroll_attempts < max_scroll_attempts and
                   total_found < target_count and
                   (time.time() - started) < max_duration_sec):
                scroll_attempts += 1

                # 현재 컨테이너 상태 확인
                container_info = await self._get_container_scroll_info(container_handle)
                current_top = container_info['scrollTop']
                container_height = container_info['scrollHeight']
                client_height = container_info['clientHeight']

                # 진행률 계산
                progress_percent = min((total_found / target_count) * 100, 100) if target_count > 0 else 0
                scroll_progress = min((current_top / max(container_height - client_height, 1)) * 100, 100)

                print(f"\n--- [SCROLL] 스크롤 시도 {scroll_attempts}회 ---")
                print(f"  [TARGET] 수집 진행률: {total_found}/{target_count}개 ({progress_percent:.1f}%)")
                print(f"  [PROGRESS] 스크롤 진행률: {scroll_progress:.1f}% (위치: {current_top}px/{container_height}px)")
                print(f"  [CONTAINER] scrollHeight={container_height}px, clientHeight={client_height}px")

                # 스크롤 단계 계산 (컨테이너 높이의 1/3)
                scroll_step = max(client_height // 3, 200)
                new_position = min(current_top + scroll_step, container_height - client_height)

                print(f"  [SCROLL] 컨테이너 스크롤: {current_top}px → {new_position}px (단계: {scroll_step}px)")

                # 컨테이너 스크롤 실행
                success = await self._scroll_container_to(container_handle, new_position, 'smooth')
                if not success:
                    print("  [ERROR] 컨테이너 스크롤 실패")
                    break

                # 스크롤 후 안정화 대기
                await page.wait_for_timeout(1500)

                # 스크롤 완료 확인
                try:
                    await container_handle.wait_for_function(
                        f"""(container) => {{
                            return Math.abs(container.scrollTop - {new_position}) < 20;
                        }}""",
                        timeout=3000
                    )
                except Exception:
                    # 타임아웃 시 대체 방법으로 확인
                    container_info = await self._get_container_scroll_info(container_handle)
                    print(f"    스크롤 확인: 목표 {new_position}px, 실제 {container_info['scrollTop']}px")
                await page.wait_for_timeout(800)  # 추가 안정화


                # 새로운 리뷰 추출
                current_reviews = await self._extract_visible_reviews(page, processed_ids)
                unique_count = len(set(r['baemin_review_id'] for r in reviews + current_reviews))

                print(f"  [SEARCH] 현재 스크롤에서 {len(current_reviews)}개 리뷰 발견, 총 고유 ID: {unique_count}개")

                if current_reviews:
                    # 정말 새로운 리뷰들만 필터링
                    existing_ids = {r['baemin_review_id'] for r in reviews}
                    new_reviews = [r for r in current_reviews if r['baemin_review_id'] not in existing_ids]

                    if new_reviews:
                        # 새로운 리뷰들을 기존 리스트에 추가
                        reviews.extend(new_reviews)
                        processed_ids.update(r['baemin_review_id'] for r in new_reviews)
                        total_found = len(reviews)
                        consecutive_no_new = 0

                        print(f"  [SUCCESS] 신규 리뷰 {len(new_reviews)}개 발견 (총 {total_found}개/{target_count}개)")

                        # 새로 추가된 리뷰 정보 출력 (안전한 정보만)
                        for new_review in new_reviews[-2:]:  # 최근 2개만 표시
                            review_length = len(new_review.get('review_text', '')) if new_review.get('review_text') else 0
                            rating = new_review.get('star_rating', 0)
                            print(f"    + {new_review['baemin_review_id']}: {new_review.get('reviewer_name', '익명')} - {review_length}글자, 별점{rating}")
                            # 상세 텍스트는 로그 파일에만 기록
                            log_only(self.logger, logging.INFO, f"    리뷰 텍스트: {new_review.get('review_text', '')}")

                        # 목표 달성 시 즉시 종료
                        if total_found >= target_count:
                            print(f"[TARGET] 목표 달성! ({total_found}개/{target_count}개)")
                            break
                    else:
                        consecutive_no_new += 1
                        print(f"  [WARNING] 신규 리뷰 없음 - 모두 기존 리뷰 (연속 {consecutive_no_new}회)")
                else:
                    consecutive_no_new += 1
                    print(f"  [WARNING] 리뷰 추출 실패 - DOM에서 리뷰 없음 (연속 {consecutive_no_new}회)")

                # 컨테이너 끝 감지 - 컨테이너 높이 변화 추적
                container_info = await self._get_container_scroll_info(container_handle)
                new_container_height = container_info['scrollHeight']

                # 컨테이너 끝 도달 확인
                is_at_bottom = (container_info['scrollTop'] + container_info['clientHeight']) >= (new_container_height - 50)
                height_unchanged = new_container_height <= last_container_height + 10

                if height_unchanged and is_at_bottom:
                    print(f"  [BOTTOM] 컨테이너 끝 도달 (높이: {new_container_height}px, 변화없음)")


                    if consecutive_no_new >= 3:
                        print(f"  [FINAL] 컨테이너 끝 + 연속 무수확 {consecutive_no_new}회 → 최종 재스캔 후 종료")
                        break
                else:
                    last_container_height = new_container_height
                    if not height_unchanged:
                        print(f"  [HEIGHT] 컨테이너 높이 증가: {last_container_height} → {new_container_height}px")

                # 안전 종료 조건들 (더 적극적인 스크롤링)
                if consecutive_no_new >= 15:  # 8 → 15로 증가
                    print(f"  [STOP] 연속 무수확 {consecutive_no_new}회 → 조기 종료")
                    break

            # 최종 컨테이너 재스캔으로 누락된 리뷰 보완
            if total_found < target_count:
                print(f"\n[RESCAN] 최종 재스캔 시작 (현재 {total_found}/{target_count}개)")
                await self._perform_final_container_rescan(container_handle, page, reviews, processed_ids, target_count)
                total_found = len(reviews)

            # 종료 통계 계산
            elapsed = time.time() - started
            success_rate = (total_found / target_count * 100) if target_count > 0 else 100
            avg_time_per_review = elapsed / max(total_found, 1)

            # 결과 로깅
            self.logger.info(f"스마트 컨테이너 스크롤 완료!")
            self.logger.info(f"수집 결과: {total_found}개 리뷰 (목표: {target_count}개)")
            self.logger.info(f"스크롤 시도: {scroll_attempts}회")
            self.logger.info(f"소요 시간: {elapsed:.1f}초")

            # 사용자 친화적인 완료 메시지
            print("\n" + "="*60)
            print("[FINISH] 배민 리뷰 수집 완료")
            print("="*60)
            print(f"[SUCCESS] 수집 성공: {total_found}개/{target_count}개 리뷰 ({success_rate:.1f}%)")
            print(f"[TIME]  소요 시간: {elapsed:.1f}초 (평균 {avg_time_per_review:.1f}초/리뷰)")
            print(f"[STATS] 스크롤 횟수: {scroll_attempts}회")

            if total_found >= target_count:
                print("[GOAL_ACHIEVED] 목표 달성! 모든 리뷰를 성공적으로 수집했습니다.")
            elif total_found >= target_count * 0.9:
                print("[SUCCESS] 거의 완료! 90% 이상 수집에 성공했습니다.")
            else:
                print("[NOTE] 일부 리뷰가 누락되었을 수 있습니다. 가상 스크롤링의 한계입니다.")

            print("="*60)

            return reviews

        except Exception as e:
            self.logger.error(f"스마트 컨테이너 스크롤 중 오류: {e}")
            safe_console_print(f"[ERROR] 스크롤 중 오류 발생: {str(e)}")
            return reviews

    async def _perform_final_container_rescan(self, container_handle, page, reviews, processed_ids, target_count):
        """컨테이너 기반 최종 재스캔으로 누락된 리뷰 보완"""
        try:
            print("  [RESCAN] 컨테이너 전체 재스캔 시작...")

            # 컨테이너를 맨 위로 이동
            await self._scroll_container_to(container_handle, 0)
            await page.wait_for_timeout(2000)

            container_info = await self._get_container_scroll_info(container_handle)
            max_height = container_info['scrollHeight']
            client_height = container_info['clientHeight']
            rescan_step = max(client_height // 4, 200)  # 더 세밀한 단계

            print(f"  [SIZE] 컨테이너 높이: {max_height}px, {rescan_step}px 단위로 재스캔")

            missed_reviews = []
            rescan_pos = 0

            while rescan_pos < max_height and len(reviews) < target_count:
                await self._scroll_container_to(container_handle, rescan_pos)
                await page.wait_for_timeout(1200)

                rescan_reviews = await self._extract_visible_reviews(page, processed_ids)
                if rescan_reviews:
                    new_missed = [r for r in rescan_reviews if r['baemin_review_id'] not in processed_ids]
                    if new_missed:
                        missed_reviews.extend(new_missed)
                        processed_ids.update(r['baemin_review_id'] for r in new_missed)
                        print(f"    [SUCCESS] 재스캔 위치 {rescan_pos}px: {len(new_missed)}개 누락 리뷰 발견")
                    else:
                        print(f"    [POS] 재스캔 위치 {rescan_pos}px: DOM {len(rescan_reviews)}개 (모두 기존)")
                else:
                    print(f"    [POS] 재스캔 위치 {rescan_pos}px: DOM에서 리뷰 없음")

                rescan_pos += rescan_step

            if missed_reviews:
                reviews.extend(missed_reviews)
                print(f"  [TARGET] 최종 재스캔으로 {len(missed_reviews)}개 추가 발견! (총 {len(reviews)}개/{target_count}개)")
            else:
                print(f"  [INFO] 재스캔에서 추가 리뷰 없음")

        except Exception as e:
            self.logger.warning(f"최종 재스캔 중 오류: {e}")
            print(f"  [WARNING] 재스캔 중 오류: {str(e)}")

    async def _extract_visible_reviews(self, page, processed_ids: set) -> List[Dict]:
        """현재 DOM에 있는 리뷰만 추출 (가상 스크롤용)"""
        visible_reviews = []

        try:
            print(f"    _extract_visible_reviews 시작 - processed_ids: {len(processed_ids)}개")
            # JavaScript로 현재 보이는 리뷰 요소들 찾기
            print("    JavaScript로 리뷰 요소 검색 중...")
            review_elements_info = await page.evaluate('''() => {
                const reviews = [];
                console.log('[DEBUG] 완전히 개선된 리뷰 요소 검색 시작...');

                // 완전히 새로운 접근: 리뷰 컨테이너의 엄격한 격리
                function findIsolatedReviewContainers() {
                    const containers = [];
                    const processedIds = new Set();

                    // 1단계: 가장 정확한 리뷰 컨테이너 찾기 (ReviewContent 모듈)
                    const reviewContentContainers = document.querySelectorAll('.ReviewContent-module__Ksg4');
                    console.log(`ReviewContent 컨테이너: ${reviewContentContainers.length}개`);

                    for (let container of reviewContentContainers) {
                        const reviewId = extractReviewId(container);
                        if (reviewId && !processedIds.has(reviewId)) {
                            containers.push({
                                element: container,
                                reviewId: reviewId,
                                method: 'ReviewContent',
                                priority: 1
                            });
                            processedIds.add(reviewId);
                        }
                    }

                    // 2단계: 백업 검색 - Container 컴포넌트 (이미 찾은 ID는 제외)
                    if (containers.length < 20) {  // 충분히 찾지 못한 경우만
                        const allContainers = document.querySelectorAll('[data-atelier-component="Container"]');
                        console.log(`전체 Container 요소: ${allContainers.length}개 검색`);

                        for (let container of allContainers) {
                            const reviewId = extractReviewId(container);
                            if (reviewId && !processedIds.has(reviewId)) {
                                // 리뷰번호와 날짜가 모두 있는지 확인
                                const text = container.textContent || '';
                                if (text.match(/\\d{4}년\\s*\\d{1,2}월\\s*\\d{1,2}일/)) {
                                    containers.push({
                                        element: container,
                                        reviewId: reviewId,
                                        method: 'Container',
                                        priority: 2
                                    });
                                    processedIds.add(reviewId);
                                }
                            }
                        }
                    }

                    console.log(`총 ${containers.length}개의 고유 리뷰 컨테이너 발견`);
                    return containers;
                }

                // 리뷰 ID 추출 함수
                function extractReviewId(container) {
                    const text = container.textContent || '';
                    const reviewIdMatch = text.match(/리뷰번호\\s*(\\d+)/);
                    return reviewIdMatch ? reviewIdMatch[1] : null;
                }

                // 각 컨테이너에서 리뷰 정보 추출 (완전 격리)
                function extractReviewFromContainer(containerInfo) {
                    try {
                        const container = containerInfo.element;
                        const reviewId = containerInfo.reviewId;

                        // 날짜 확인
                        const text = container.textContent || '';
                        const dateMatch = text.match(/\\d{4}년\\s*\\d{1,2}월\\s*\\d{1,2}일/);
                        if (!dateMatch) {
                            return null;
                        }

                        // 리뷰어 이름 추출 (더 정확한 방법으로 개선)
                        let reviewerName = null;

                        // 1단계: 특정 리뷰어 이름 클래스로 검색
                        const nameSelectors = [
                            'span.Typography_b_c9kn_1bisyd47',  // 가장 일반적인 이름 클래스
                            'span.Typography_b_pnsa_1bisyd47',
                            'span.Typography_b_dvcv_1bisyd47',
                            'span[class*="Typography_b"][class*="1bisyd47"]'  // 범용 패턴
                        ];

                        for (let selector of nameSelectors) {
                            const nameElements = container.querySelectorAll(selector);
                            for (let nameEl of nameElements) {
                                const nameText = nameEl.textContent ? nameEl.textContent.trim() : '';

                                // 리뷰어 이름 조건 (영문 이름은 더 길 수 있음)
                                if (nameText && nameText.length >= 1 && nameText.length <= 20) {
                                    // 제외할 텍스트들
                                    const excludeTerms = [
                                        '배달', '포장', '리뷰번호', '년', '월', '일',
                                        '좋아요', '보통이에요', '아쉬워요', '별점', '댓글',
                                        '사장님', '주문메뉴', '가게배달', '한집배달'
                                    ];

                                    const hasExcludedTerm = excludeTerms.some(term => nameText.includes(term));
                                    const isOnlyNumbers = /^\\d+$/.test(nameText);
                                    const isOnlySymbols = /^[★☆\\s]+$/.test(nameText);

                                    // 유효한 이름 패턴: 한글, 영문, 자음/모음, 또는 그들의 조합
                                    const hasValidCharacters = /[가-힣a-zA-Zㄱ-ㅎㅏ-ㅣ]/.test(nameText);

                                    // 유효한 리뷰어 이름 조건
                                    if (!hasExcludedTerm && !isOnlyNumbers && !isOnlySymbols && hasValidCharacters) {
                                        reviewerName = nameText;
                                        console.log(`이름 발견 (클래스 선택자): "${nameText}"`);
                                        break;
                                    }
                                }
                            }
                            if (reviewerName) break;
                        }

                        // 2단계: 특정 클래스로 찾지 못한 경우, 포지션 기반 검색
                        if (!reviewerName) {
                            // 리뷰번호 근처에 있는 이름 요소 찾기
                            const reviewIdElement = container.querySelector('span:contains("리뷰번호")') ||
                                                  Array.from(container.querySelectorAll('span')).find(el =>
                                                      el.textContent && el.textContent.includes('리뷰번호'));

                            if (reviewIdElement) {
                                // 리뷰번호 요소의 형제나 부모 요소에서 이름 찾기
                                const parent = reviewIdElement.parentElement;
                                if (parent) {
                                    const siblingSpans = parent.querySelectorAll('span');
                                    for (let span of siblingSpans) {
                                        const text = span.textContent ? span.textContent.trim() : '';
                                        // 영문, 한글, 자음/모음 모두 허용
                                        if (text && text.length >= 1 && text.length <= 20 &&
                                            /[a-zA-Z가-힣ㄱ-ㅎㅏ-ㅣ]/.test(text) &&
                                            !text.includes('리뷰번호') &&
                                            !text.includes('배달') &&
                                            !text.includes('포장') &&
                                            !text.includes('주문') &&
                                            !text.includes('년') &&
                                            !text.includes('월') &&
                                            !text.includes('일')) {
                                            reviewerName = text;
                                            console.log(`형제 요소에서 이름 발견: "${reviewerName}"`);
                                            break;
                                        }
                                    }
                                }
                            }
                        }

                        // 3단계: 마지막 수단 - 전체 텍스트에서 패턴 매칭 (영문, 한글, 특수문자 모두 지원)
                        if (!reviewerName) {
                            // 리뷰번호 앞의 모든 가능한 이름 패턴 찾기
                            // 1. 영문 이름 (Mary, jjangee, tina, baegopa 등)
                            // 2. 한글 이름 (ㄱㅎ, ㅂㄷ, 배달초밥 등)
                            // 3. 혼합 이름
                            const namePatterns = [
                                /([a-zA-Z]{2,20})(?=.*리뷰번호)/,  // 영문 이름
                                /([가-힣]{1,10})(?=.*리뷰번호)/,    // 한글 이름 (1글자도 허용)
                                /([ㄱ-ㅎㅏ-ㅣ]{1,10})(?=.*리뷰번호)/, // 자음/모음만
                                /([a-zA-Z가-힣ㄱ-ㅎㅏ-ㅣ0-9_\\-]{1,20})(?=.*리뷰번호)/ // 혼합
                            ];

                            for (const pattern of namePatterns) {
                                const nameMatch = text.match(pattern);
                                if (nameMatch) {
                                    const candidateName = nameMatch[1];
                                    // 제외 키워드 체크
                                    const excludeKeywords = ['배달', '포장', '주문', '리뷰', '좋아요', '보통', '아쉬워', '별점'];
                                    const isExcluded = excludeKeywords.some(keyword => candidateName.includes(keyword));

                                    if (!isExcluded && candidateName.length >= 1 && candidateName.length <= 20) {
                                        reviewerName = candidateName;
                                        console.log(`이름 패턴 매칭 성공: "${reviewerName}"`);
                                        break;
                                    }
                                }
                            }
                        }

                        // 주문 메뉴 먼저 추출 (리뷰 텍스트와 구분하기 위해)
                        const menuItems = [];
                        const menuElements = container.querySelectorAll('span[class*="Badge"], ul[class*="ReviewMenus"] span');
                        for (let menuEl of menuElements) {
                            const menuText = menuEl.textContent ? menuEl.textContent.trim() : '';
                            if (menuText && !menuText.includes('배달') && !menuText.includes('포장') && menuText.length > 1) {
                                menuItems.push(menuText);
                            }
                        }

                        // 리뷰 텍스트 추출 (메뉴와 완전 분리) - 교차 오염 완전 방지
                        let reviewText = null;

                        // 1단계: 특정 리뷰 텍스트 클래스 우선 검색
                        const specificTextSelectors = [
                            'span.Typography_b_c9kn_1bisyd49.Typography_b_c9kn_1bisyd4q.Typography_b_c9kn_1bisyd41y',
                            'span.Typography_b_pnsa_1bisyd49.Typography_b_pnsa_1bisyd4q.Typography_b_pnsa_1bisyd41y',
                            'span.Typography_b_dvcv_1bisyd49.Typography_b_dvcv_1bisyd4q.Typography_b_dvcv_1bisyd41y',
                            'span[class*="Typography_b"][class*="1bisyd49"][class*="1bisyd4q"]'
                        ];

                        for (let selector of specificTextSelectors) {
                            const specificElements = container.querySelectorAll(selector);
                            for (let el of specificElements) {
                                const content = el.textContent ? el.textContent.trim() : '';
                                if (content && content.length >= 5) {
                                    // 메뉴 아이템이 아닌지 확인
                                    const isMenuContent = menuItems.some(menu => content.includes(menu) || menu.includes(content));

                                    // 메타데이터가 아닌지 확인
                                    const isMetadata = (
                                        content.includes('리뷰번호') ||
                                        content.includes('년') && content.includes('월') ||
                                        content.includes('배달') ||
                                        content.includes('포장') ||
                                        content === reviewerName ||
                                        /^[★☆]+$/.test(content) ||
                                        content.match(/^\\d+$/) ||
                                        content.includes('좋아요') ||
                                        content.includes('보통이에요') ||
                                        content.includes('아쉬워요') ||
                                        content.includes('사장님') ||
                                        content.includes('댓글')
                                    );

                                    if (!isMenuContent && !isMetadata && content.length >= 10) {
                                        reviewText = content;
                                        break;
                                    }
                                }
                            }
                            if (reviewText) break;
                        }

                        // 2단계: 특정 클래스로 찾지 못한 경우, 일반적인 Typography 요소 검색
                        if (!reviewText) {
                            const textElements = container.querySelectorAll('span[class*="Typography"]');
                            const candidates = [];

                            for (let textEl of textElements) {
                                const content = textEl.textContent ? textEl.textContent.trim() : '';
                                if (content && content.length >= 10) {  // 최소 10자 이상만 고려
                                    // 메뉴 아이템인지 확인
                                    const isMenuContent = menuItems.some(menu =>
                                        content.includes(menu) || menu.includes(content) || content === menu
                                    );

                                    // 메타데이터 제외 조건 (더 엄격하게)
                                    const isMetadata = (
                                        content.includes('리뷰번호') ||
                                        content.includes('년') && content.includes('월') ||
                                        content.includes('배달') ||
                                        content.includes('포장') ||
                                        content === reviewerName ||
                                        /^[★☆]+$/.test(content) ||
                                        content.match(/^\\d+$/) ||
                                        content.includes('좋아요') ||
                                        content.includes('보통이에요') ||
                                        content.includes('아쉬워요') ||
                                        content.includes('사장님') ||
                                        content.includes('댓글') ||
                                        content.includes('주문메뉴') ||
                                        content.length > 100  // 너무 긴 텍스트는 여러 리뷰가 섞인 것일 가능성
                                    );

                                    if (!isMenuContent && !isMetadata) {
                                        candidates.push(content);
                                    }
                                }
                            }

                            // 가장 적절한 리뷰 텍스트 선택 (메뉴 제외)
                            if (candidates.length > 0) {
                                // 가장 긴 의미있는 텍스트 선택 (단, 80자 이하로 제한)
                                const filteredCandidates = candidates.filter(c => c.length <= 80);
                                if (filteredCandidates.length > 0) {
                                    reviewText = filteredCandidates.sort((a, b) => b.length - a.length)[0];
                                }
                            }
                        }

                        // 날짜 추출 (컨테이너 내에서만)
                        let reviewDate = null;
                        const fullDateMatch = text.match(/(\\d{4})년\\s*(\\d{1,2})월\\s*(\\d{1,2})일/);
                        if (fullDateMatch) {
                            const year = fullDateMatch[1];
                            const month = fullDateMatch[2].padStart(2, '0');
                            const day = fullDateMatch[3].padStart(2, '0');
                            reviewDate = `${year}-${month}-${day}`;
                        }

                        // 별점 추출 (컨테이너 내에서만)
                        let starRating = 0;
                        const starElements = container.querySelectorAll('span[class*="Star"]');
                        for (let starEl of starElements) {
                            // 여기에 별점 추출 로직 추가 가능
                        }

                        // (메뉴는 이미 위에서 추출됨 - 중복 제거)

                        // 컨테이너의 고유 식별자 생성
                        const rect = container.getBoundingClientRect();
                        const containerId = `review_${reviewId}_${Math.round(rect.top)}`;

                        // 최종 검증: 리뷰 텍스트가 메뉴와 겹치지 않는지 확인
                        if (reviewText && menuItems.length > 0) {
                            const textOverlapsWithMenu = menuItems.some(menu =>
                                reviewText.includes(menu) || menu.includes(reviewText) || reviewText === menu
                            );
                            if (textOverlapsWithMenu) {
                                console.log(`리뷰 ${reviewId}: 텍스트가 메뉴와 겹쳐서 제거 - "${reviewText}"`);
                                reviewText = null;  // 겹치는 경우 텍스트 제거
                            }
                        }

                        return {
                            reviewId: reviewId,
                            containerId: containerId,
                            reviewerName: reviewerName || 'Unknown',
                            reviewText: reviewText || '',  // null인 경우 빈 문자열
                            reviewDate: reviewDate || '',
                            starRating: starRating,
                            menuItems: menuItems,
                            method: containerInfo.method,
                            priority: containerInfo.priority,
                            candidateCount: reviewText ? 1 : 0,  // 실제 텍스트 여부로 설정
                            containerTextLength: text.length,
                            isolationVerified: true,  // 격리 검증 완료
                            hasMenuContamination: false  // 메뉴 오염 없음 확인
                        };

                    } catch (error) {
                        console.error('리뷰 추출 중 오류:', error);
                        return null;
                    }
                }

                // 모든 격리된 컨테이너에서 리뷰 추출
                const containers = findIsolatedReviewContainers();
                for (let containerInfo of containers) {
                    const review = extractReviewFromContainer(containerInfo);
                    if (review) {
                        // 누락된 사용자 이름 목록
                        const missingUserNames = ['jjangee', 'Mary', '배달초밥', 'baegopa', 'ㄱㅎ', 'ㅂㄷ', 'tina'];

                        // 리뷰어 이름이 Unknown인 경우 또는 특정 사용자인 경우 상세 로그
                        if (review.reviewerName === 'Unknown' || missingUserNames.some(name => review.reviewerName === name)) {
                            console.log(`[SPECIAL] 특수 리뷰 발견:`, {
                                reviewId: review.reviewId,
                                reviewerName: review.reviewerName,
                                method: review.method,
                                text: review.reviewText ? review.reviewText.substring(0, 50) : '텍스트 없음'
                            });
                        }

                        console.log(`리뷰 ${review.reviewId}: ${review.reviewerName} - 텍스트: ${review.reviewText ? review.reviewText.substring(0, 30) + '...' : '없음'}`);
                        reviews.push(review);
                    }
                }

                console.log(`[SUCCESS] 총 ${reviews.length}개 고유 리뷰 추출 완료`);
                return reviews;
            }''')

            print(f"  현재 DOM에 {len(review_elements_info)}개 리뷰 발견")

            # JavaScript에서 완전히 추출된 리뷰 정보를 Python 객체로 변환 - 교차 오염 완전 방지
            for review_info in review_elements_info:
                try:
                    if review_info and 'reviewId' in review_info:
                        review_id = review_info['reviewId']

                        # 엄격한 중복 확인
                        if review_id in processed_ids:
                            print(f"  [WARNING] 중복 리뷰 ID 발견, 건너뛰기: {review_id}")
                            continue

                        reviewer_name = review_info.get('reviewerName', 'Unknown')
                        review_text = review_info.get('reviewText', '')  # JavaScript에서 추출된 텍스트 사용
                        review_date = review_info.get('reviewDate', '')
                        star_rating = review_info.get('starRating', 0)
                        menu_items = review_info.get('menuItems', [])

                        # 콘솔에는 안전한 정보만 출력
                        print(f"\n[INFO] 격리된 리뷰 처리: {review_id} ({review_info.get('method', 'Unknown')})")
                        print(f"  리뷰어: {reviewer_name}")
                        print(f"  텍스트 길이: {len(review_text) if review_text else 0}글자")
                        print(f"  날짜: {review_date}")
                        print(f"  별점: {star_rating}")
                        print(f"  메뉴 수: {len(menu_items)}개")

                        # 상세 내용은 로그 파일에만 기록 (UTF-8 안전)
                        log_only(self.logger, logging.INFO, f"  텍스트: {review_text if review_text else '없음 (별점만 리뷰)'}")
                        menu_text = ', '.join(menu_items) if menu_items else '없음'
                        log_only(self.logger, logging.INFO, f"  메뉴: {menu_text}")
                        print(f"  후보 텍스트 수: {review_info.get('candidateCount', 0)}")
                        print(f"  격리 검증: {review_info.get('isolationVerified', False)}")

                        # processed_ids에 추가 (중복 방지)
                        processed_ids.add(review_id)

                        # 새로운 리뷰 데이터 구조 - JavaScript에서 추출된 정보 활용
                        new_review = {
                            'baemin_review_id': review_id,
                            'reviewer_name': reviewer_name,
                            'review_text': review_text,  # JavaScript에서 안전하게 추출된 텍스트
                            'star_rating': star_rating,
                            'order_menu_items': menu_items,
                            'review_date': review_date,
                            'delivery_review': '',  # 별도 처리 필요 시
                            'extraction_method': review_info.get('method', 'Unknown'),
                            'container_id': review_info.get('containerId', ''),
                            'isolation_verified': review_info.get('isolationVerified', False),
                            'candidate_count': review_info.get('candidateCount', 0),
                            'priority': review_info.get('priority', 0)
                        }

                        visible_reviews.append(new_review)
                        print(f"  [SUCCESS] 격리된 리뷰 {review_id} 추가됨 (총 {len(visible_reviews)}개)")

                except Exception as e:
                    # 개별 리뷰 처리 오류는 로그에만 기록하고 계속 진행
                    safe_console_print(f"  [ERROR] 개별 리뷰 처리 중 오류 - 다음 리뷰로 계속 진행")
                    self.logger.error(f"개별 리뷰 처리 중 오류: {str(e)}")
                    continue

        except Exception as e:
            safe_console_print(f"[ERROR] 보이는 리뷰 추출 중 오류 발생")
            self.logger.error(f"보이는 리뷰 추출 중 오류: {str(e)}")
            import traceback
            self.logger.error(f"스택 트레이스: {traceback.format_exc()}")

        return visible_reviews

    async def _load_all_reviews(self, page):
        """무한 스크롤 방식으로 모든 리뷰 로드 (레거시 - 사용하지 않음)"""
        try:
            print("무한 스크롤 시작...")

            previous_height = 0
            scroll_attempts = 0
            max_scroll_attempts = 10  # 최대 스크롤 시도 횟수

            while scroll_attempts < max_scroll_attempts:
                # 현재 페이지 높이 확인
                current_height = await page.evaluate("document.body.scrollHeight")

                if current_height == previous_height:
                    print(f"더 이상 로드할 컨텐츠가 없음 (시도 {scroll_attempts + 1}회)")
                    break

                # 페이지 끝까지 스크롤
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                await page.wait_for_timeout(2000)  # 로딩 대기

                # 리뷰가 추가로 로드되었는지 확인
                new_height = await page.evaluate("document.body.scrollHeight")

                if new_height > current_height:
                    print(f"새로운 리뷰 로드됨: {current_height} → {new_height}")
                    previous_height = new_height
                    scroll_attempts = 0  # 새 컨텐츠가 로드되면 카운터 리셋
                else:
                    scroll_attempts += 1
                    print(f"스크롤 시도 {scroll_attempts}/{max_scroll_attempts}")

                # 스크롤 후 잠시 대기
                await page.wait_for_timeout(1000)

            print("무한 스크롤 완료")

        except Exception as e:
            safe_console_print(f"무한 스크롤 중 오류: {str(e)}")
    
    async def _extract_single_review(self, review_element) -> Optional[Dict]:
        """개별 리뷰 데이터 추출 (새로운 셀렉터 적용)"""
        try:
            # 필수 필드들에 기본값 설정
            review_data = {
                'reviewer_name': '익명',
                'review_text': '',
                'rating': 5,  # 기본값
                'order_menu_items': [],
                'delivery_review': None,
                'baemin_review_id': None
            }
            
            # 리뷰어 이름 추출 (사용자 제공 HTML에 기반한 최신 선택자)
            reviewer_selectors = [
                "span.c_c1xs_13c33de7.Typography_b_c9kn_1bisyd47.Typography_b_c9kn_1bisyd4r.Typography_b_c9kn_1bisyd44j",  # 사용자 제공 최신 구조
                "span.Typography_b_c9kn_1bisyd47",  # c9kn 기본 구조
                "span.Typography_b_pnsa_1bisyd47",  # 기존 구조
                "span.Typography_b_dvcv_1bisyd47",  # 새 구조
                "span[data-atelier-component='Typography'].Typography_b_pnsa_1bisyd47",
                "span[data-atelier-component='Typography'].Typography_b_dvcv_1bisyd47",
                "span[data-atelier-component='Typography'].Typography_b_c9kn_1bisyd47"
            ]
            
            reviewer_name = None
            for selector in reviewer_selectors:
                try:
                    reviewer_element = await review_element.query_selector(selector)
                    if reviewer_element:
                        text = await reviewer_element.text_content()
                        if text and text.strip() and not any(x in text for x in ['년', '월', '일', '리뷰번호', '별점']):
                            reviewer_name = text.strip()
                            print(f"  리뷰어 이름 발견: {reviewer_name} (선택자: {selector})")
                            break
                except Exception as e:
                    continue
            
            if reviewer_name:
                review_data['reviewer_name'] = reviewer_name
            else:
                print("  [WARNING] 리뷰어 이름을 찾을 수 없어 기본값 사용")
            
            # 완전한 날짜 파싱 시스템 (절대시간 + 상대시간 지원)
            review_data['review_date'] = await self._extract_review_date_advanced(review_element)
            
            # 리뷰 번호 - 가장 중요한 고유 식별자
            review_id_element = await review_element.query_selector("span:has-text('리뷰번호')")
            if review_id_element:
                id_text = await review_id_element.text_content()
                # "리뷰번호 2025081802062196" 형식에서 숫자만 추출
                match = re.search(r'리뷰번호\s*(\d+)', id_text)
                if match:
                    review_data['baemin_review_id'] = match.group(1)
                    print(f"  리뷰번호: {review_data['baemin_review_id']}")
            
            # 리뷰 텍스트 추출 - 현재 리뷰 컨테이너 내에서만 검색하여 교차 오염 완전 방지
            review_text = None

            try:
                # 다단계 리뷰 텍스트 추출 - 교차 오염 방지
                print(f"  [TEXT] 리뷰 텍스트 추출 시작 (리뷰어: {reviewer_name})")

                # 1단계: 컨테이너 내 모든 Typography 요소 수집
                all_text_elements = await review_element.query_selector_all("span[class*='Typography']")
                candidate_texts = []

                for element in all_text_elements:
                    text = await element.text_content()
                    if text and text.strip():
                        text = text.strip()

                        # 기본 필터링
                        exclude_keywords = ['리뷰번호', '년', '월', '일', '주문메뉴', '배달리뷰', '사장님 댓글',
                                          '좋아요', '보통이에요', '아쉬워요', '배달', '포장', '가게배달', '한집배달', '알뜰배달']

                        is_excluded = any(keyword in text for keyword in exclude_keywords)
                        is_metadata = (text == reviewer_name or
                                     text.isdigit() or
                                     re.match(r'^[★☆]+$', text) or
                                     re.match(r'^\d{4}년.*', text) or
                                     '(' in text and ')' in text)  # 메뉴명 패턴

                        if (len(text) >= 3 and
                            not is_excluded and
                            not is_metadata):
                            candidate_texts.append(text)

                # 2단계: 가장 유의미한 텍스트 선택
                if candidate_texts:
                    # 길이 기준으로 정렬하여 가장 긴 텍스트 선택 (일반적으로 리뷰 내용)
                    candidate_texts.sort(key=len, reverse=True)
                    review_text = candidate_texts[0]
                    # 콘솔에는 안전한 정보만 출력
                    print(f"  [SUCCESS] 리뷰 텍스트 발견: {len(review_text)}글자 (후보 {len(candidate_texts)}개 중 선택)")
                    # 실제 텍스트는 로그 파일에만 기록
                    log_only(self.logger, logging.INFO, f"  리뷰 텍스트: '{review_text}'")
                else:
                    # 3단계: 특정 선택자로 재시도
                    review_text_selectors = [
                        "span.c_c1xs_13c33de7.Typography_b_c9kn_1bisyd49.Typography_b_c9kn_1bisyd4q.Typography_b_c9kn_1bisyd41y",
                        "span.Typography_b_c9kn_1bisyd49.Typography_b_c9kn_1bisyd4q.Typography_b_c9kn_1bisyd41y",
                        "span.Typography_b_pnsa_1bisyd49.Typography_b_pnsa_1bisyd4q.Typography_b_pnsa_1bisyd41y",
                        "span.Typography_b_dvcv_1bisyd49.Typography_b_dvcv_1bisyd4q.Typography_b_dvcv_1bisyd41y",
                        "span[class*='Typography_b'][class*='1bisyd49']",  # 더 유연한 선택자
                    ]

                    for selector in review_text_selectors:
                        try:
                            text_elements = await review_element.query_selector_all(selector)

                            for text_element in text_elements:
                                text = await text_element.text_content()
                                if text and text.strip():
                                    text = text.strip()

                                    if (len(text) >= 3 and
                                        not any(kw in text for kw in exclude_keywords) and
                                        text != reviewer_name and
                                        not text.isdigit() and
                                        not re.match(r'^[★☆]+$', text)):

                                        review_text = text
                                        print(f"  [SUCCESS] 리뷰 텍스트 발견: '{text}' (선택자: {selector})")
                                        break

                            if review_text:
                                break
                        except Exception as e:
                            continue

                    if not review_text:
                        print("  [INFO] 리뷰 텍스트 없음: 별점만 있는 리뷰")

            except Exception as e:
                print(f"  [ERROR] 리뷰 텍스트 추출 중 오류: {e}")

            # 최종 검증 및 저장
            if review_text:
                # 최종 검증: 다른 리뷰어 이름이 포함되지 않았는지 확인
                if len(review_text) > 100:  # 긴 텍스트는 추가 검증
                    print(f"  [SEARCH] 긴 텍스트 검증: {len(review_text)}글자")

                review_data['review_text'] = review_text
            else:
                review_data['review_text'] = ""
            
            # 주문 메뉴 - Badge 컴포넌트 내부의 메뉴명 (신구조 모두 지원)
            menu_selectors = [
                "ul.ReviewMenus-module__WRZI span.Badge_b_pnsa_19agxiso",
                "ul.ReviewMenus-module__WRZI span.Badge_b_dvcv_19agxiso",
                "ul.ReviewMenus-module__WRZI span.Badge_b_c9kn_19agxiso",  # 새로운 구조 추가
                "span.Badge_b_pnsa_19agxiso",  # 더 일반적인 선택자
                "span.Badge_b_dvcv_19agxiso",
                "span.Badge_b_c9kn_19agxiso",
                "span[class*='Badge']",  # 폴백 선택자
            ]

            order_menu_items = []
            for selector in menu_selectors:
                try:
                    menu_elements = await review_element.query_selector_all(selector)
                    if menu_elements:
                        for menu_element in menu_elements:
                            menu_text = await menu_element.text_content()
                            if menu_text and menu_text.strip():
                                menu_items_text = menu_text.strip()
                                # 인코딩 문제가 있는 문자 제거
                                try:
                                    menu_items_text.encode('cp949')
                                    safe_menu_text = menu_items_text
                                except UnicodeEncodeError:
                                    # 안전한 문자만 남기기
                                    safe_menu_text = ''.join(c for c in menu_items_text if ord(c) < 0x10000 and (c.isalnum() or c in ' .,!?-()[]'))
                                    if not safe_menu_text.strip():
                                        safe_menu_text = "특수문자메뉴"

                                # 이미 추가된 메뉴가 아닌 경우만 추가 (중복 방지)
                                if safe_menu_text not in order_menu_items:
                                    order_menu_items.append(safe_menu_text)
                        if order_menu_items:  # 메뉴를 찾았으면 다른 선택자 시도하지 않음
                            break
                except Exception as e:
                    continue

            review_data['order_menu_items'] = order_menu_items
            if order_menu_items:
                print(f"  주문 메뉴 수: {len(order_menu_items)}개")
                # 메뉴 상세 내용은 로그 파일에만 기록
                menu_display = ', '.join(order_menu_items)
                log_only(self.logger, logging.INFO, f"  주문 메뉴: {menu_display}")
            
            # 배송 평가 - ReviewDelivery 모듈 내부 (신구조 모두 지원)
            delivery_review_element = await review_element.query_selector("div.ReviewDelivery-module__QlG8 span.Badge_b_pnsa_19agxiso")
            if not delivery_review_element:
                delivery_review_element = await review_element.query_selector("div.ReviewDelivery-module__QlG8 span.Badge_b_dvcv_19agxiso")
            if delivery_review_element:
                delivery_text = await delivery_review_element.text_content()
                review_data['delivery_review'] = delivery_text.strip()
            
            # 별점 추출 (향상된 추출기 사용)
            rating = await self.rating_extractor.extract_rating(review_element)
            if rating:
                review_data['rating'] = rating
            else:
                # 별점을 찾지 못한 경우 디버깅 정보 출력
                print(f"  [WARNING] 별점 추출 실패, 기본값 5 사용")

            # 리뷰 이미지 확인 및 추출
            has_images = await self._check_review_has_photos(review_element, review_data)

            # 리뷰 ID 생성
            review_data['baemin_review_id'] = await self._generate_review_id(review_element)

            # 답글 상태 확인
            reply_info = await self._check_reply_status(review_element)
            review_data.update(reply_info)

            return review_data
            
        except Exception as e:
            print(f"개별 리뷰 추출 중 오류: {str(e)}")
            return None
    
    
    async def _check_review_has_photos(self, review_element, review_data: Dict) -> bool:
        """리뷰에 이미지가 있는지 확인 및 이미지 URL 추출"""
        try:
            # 리뷰 이미지 선택자들 (배민의 이미지 구조에 맞춰 설정)
            image_selectors = [
                "img[src*='review']",  # 리뷰 이미지
                "img[class*='review']",
                "img[class*='Review']",
                "div[class*='image'] img",
                "div[class*='photo'] img",
                "div[class*='picture'] img",
                "img[alt*='리뷰']",
                "img[alt*='review']"
            ]

            # 기본적으로 이미지 메타데이터 초기화
            review_data['review_images'] = []
            has_images = False

            for selector in image_selectors:
                try:
                    image_elements = await review_element.query_selector_all(selector)
                    if image_elements:
                        for img_element in image_elements:
                            img_src = await img_element.get_attribute('src')
                            if img_src and img_src.strip():
                                # 상대 경로를 절대 경로로 변환
                                if img_src.startswith('//'):
                                    img_src = 'https:' + img_src
                                elif img_src.startswith('/'):
                                    img_src = 'https://self.baemin.com' + img_src

                                review_data['review_images'].append(img_src)
                                has_images = True

                        if has_images:
                            print(f"  리뷰 이미지 {len(review_data['review_images'])}개 발견")
                            break  # 이미지를 찾았으면 다른 선택자 시도하지 않음

                except Exception as e:
                    continue

            return has_images

        except Exception as e:
            print(f"리뷰 이미지 확인 중 오류: {str(e)}")
            review_data['review_images'] = []
            return False

    async def _check_reply_status(self, review_element) -> Dict:
        """답글 상태 확인"""
        try:
            result = {
                'reply_text': None,
                'reply_status': None
            }
            
            # 답글 작성 버튼 확인 (미답변) - 신구조 모두 지원
            reply_selectors = [
                "button.reply-write-btn",  # 기존 구조
                "button:has-text('사장님 댓글 등록하기')",  # 새로운 구조
                "button.Button_b_dvcv_1w1nucha:has-text('댓글')",
                "button[data-atelier-component='Button']:has-text('댓글')"
            ]
            
            for selector in reply_selectors:
                reply_write_btn = await review_element.query_selector(selector)
                if reply_write_btn:
                    result['reply_status'] = 'draft'
                    return result
            
            # 기존 답글 확인 (답변 완료) - 더 엄격한 선택자 사용
            reply_selectors_completed = [
                "div.reply-section",  # 기존 구조
                "div:has(> p:has-text('사장님'))",  # 사장님 답글이 포함된 div
                "div.Container_c_dogv_1utdzds5:has(p:has-text('사장님'))",  # 새 구조
            ]
            
            for selector in reply_selectors_completed:
                reply_section = await review_element.query_selector(selector)
                if reply_section:
                    # 실제 답글 텍스트가 있는지 확인
                    reply_text_element = await reply_section.query_selector("p")
                    if reply_text_element:
                        reply_text = await reply_text_element.text_content()
                        # "사장님" 텍스트와 실제 답글이 있는지 확인
                        if reply_text and "사장님" in reply_text and len(reply_text.strip()) > 10:
                            result['reply_status'] = 'sent'
                            result['reply_text'] = reply_text.strip()
                            return result
            
            return result
            
        except Exception as e:
            print(f"답글 상태 확인 중 오류: {str(e)}")
            return {'reply_text': None, 'reply_status': None}
    
    async def _generate_review_id(self, review_element) -> str:
        """배민 리뷰 고유 ID 생성 - 실제 리뷰번호 사용"""
        try:
            # 먼저 이미 추출한 리뷰번호가 있는지 확인
            # (이미 _extract_single_review에서 추출했을 가능성)
            
            # 리뷰번호 직접 추출
            review_id_element = await review_element.query_selector("span:has-text('리뷰번호')")
            if review_id_element:
                id_text = await review_id_element.text_content()
                # "리뷰번호 2025092200547953" 형식에서 숫자만 추출 (10자리 이상)
                import re
                match = re.search(r'리뷰번호\s*(\d{10,})', id_text)
                if match:
                    review_id = match.group(1)
                    print(f"리뷰번호 추출: {review_id}")
                    return review_id
            
            # 리뷰번호를 못 찾은 경우 해시 생성 (폴백)
            print("리뷰번호를 찾을 수 없어 해시 생성")
            reviewer_name = ""
            name_element = await review_element.query_selector("span.Typography_b_pnsa_1bisyd47") or \
                          await review_element.query_selector("span.Typography_b_dvcv_1bisyd47") or \
                          await review_element.query_selector("span.Typography_b_c9kn_1bisyd47")
            if name_element:
                reviewer_name = await name_element.text_content()
            
            review_text = ""
            text_element = await review_element.query_selector("span.Typography_b_pnsa_1bisyd49") or \
                          await review_element.query_selector("span.Typography_b_dvcv_1bisyd49") or \
                          await review_element.query_selector("span.Typography_b_dvcv_1bisyd41y")
            if text_element:
                review_text = await text_element.text_content()
            
            date_text = ""
            date_element = await review_element.query_selector("span:has-text('년'):has-text('월'):has-text('일')")
            if date_element:
                date_text = await date_element.text_content()
            
            # 고유 ID 생성
            unique_string = f"{reviewer_name}_{date_text}_{review_text[:50]}"
            review_id = hashlib.md5(unique_string.encode()).hexdigest()[:24]
            print(f"해시 기반 ID 생성: {review_id}")
            
            return review_id
            
        except Exception as e:
            print(f"리뷰 ID 생성 중 오류: {str(e)}")
            # 리뷰번호가 없으면 null 반환 (저장하지 않음)
            return None
    
    def _parse_date(self, date_text: str) -> str:
        """날짜 텍스트 파싱"""
        try:
            if not date_text or not date_text.strip():
                return ""

            import re
            # "2025년 8월 28일" 형태를 "2025-08-28" 형태로 변환
            date_match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_text)
            if date_match:
                year, month, day = date_match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            # "2025.08.21" 형태를 "2025-08-21" 형태로 변환
            date_match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', date_text)
            if date_match:
                year, month, day = date_match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            # 파싱 실패하면 빈 문자열 반환
            return ""

        except Exception as e:
            print(f"날짜 파싱 중 오류: {str(e)}")
            return ""

    async def _extract_review_date_advanced(self, review_element) -> str:
        """완전한 날짜 파싱 시스템 - 절대시간 + 상대시간 지원"""
        try:
            from datetime import datetime, timedelta
            import re

            # JavaScript에서 모든 날짜 관련 텍스트를 찾고 실시간 변환
            date_result = await review_element.evaluate('''(element) => {
                const now = new Date();

                // 모든 텍스트 노드에서 날짜 관련 패턴 찾기
                function findDateTexts(el) {
                    const dateTexts = [];
                    const walker = document.createTreeWalker(
                        el,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );

                    let node;
                    while (node = walker.nextNode()) {
                        const text = node.textContent.trim();
                        if (text) {
                            // 절대시간 패턴
                            if (/\\d{4}년\\s*\\d{1,2}월\\s*\\d{1,2}일/.test(text)) {
                                dateTexts.push({type: 'absolute', text: text});
                            }
                            // 상대시간 패턴
                            else if (/(오늘|어제|그저께|\\d+\\s*(분|시간|일)\\s*전)/.test(text)) {
                                dateTexts.push({type: 'relative', text: text});
                            }
                        }
                    }
                    return dateTexts;
                }

                // 상대시간을 절대시간으로 변환
                function parseRelativeTime(text) {
                    const now = new Date();

                    if (text.includes('오늘')) {
                        return formatDate(now);
                    }
                    else if (text.includes('어제')) {
                        const yesterday = new Date(now);
                        yesterday.setDate(yesterday.getDate() - 1);
                        return formatDate(yesterday);
                    }
                    else if (text.includes('그저께')) {
                        const dayBeforeYesterday = new Date(now);
                        dayBeforeYesterday.setDate(dayBeforeYesterday.getDate() - 2);
                        return formatDate(dayBeforeYesterday);
                    }

                    // "N분 전", "N시간 전", "N일 전" 패턴
                    const match = text.match(/(\\d+)\\s*(분|시간|일)\\s*전/);
                    if (match) {
                        const [, num, unit] = match;
                        const amount = parseInt(num);
                        const date = new Date(now);

                        switch(unit) {
                            case '분':
                                date.setMinutes(date.getMinutes() - amount);
                                break;
                            case '시간':
                                date.setHours(date.getHours() - amount);
                                break;
                            case '일':
                                date.setDate(date.getDate() - amount);
                                break;
                        }
                        return formatDate(date);
                    }

                    return null;
                }

                // 절대시간 파싱
                function parseAbsoluteTime(text) {
                    const match = text.match(/(\\d{4})년\\s*(\\d{1,2})월\\s*(\\d{1,2})일/);
                    if (match) {
                        const [, year, month, day] = match;
                        return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
                    }
                    return null;
                }

                // 날짜 포맷팅
                function formatDate(date) {
                    const year = date.getFullYear();
                    const month = String(date.getMonth() + 1).padStart(2, '0');
                    const day = String(date.getDate()).padStart(2, '0');
                    return `${year}-${month}-${day}`;
                }

                // 날짜 텍스트 찾기 및 변환
                const dateTexts = findDateTexts(element);
                console.log('날짜 후보:', dateTexts);

                // 우선순위: 절대시간 > 상대시간
                for (const dateInfo of dateTexts) {
                    if (dateInfo.type === 'absolute') {
                        const parsed = parseAbsoluteTime(dateInfo.text);
                        if (parsed) {
                            console.log('절대시간 파싱 성공:', dateInfo.text, '->', parsed);
                            return {success: true, date: parsed, type: 'absolute', original: dateInfo.text};
                        }
                    }
                }

                for (const dateInfo of dateTexts) {
                    if (dateInfo.type === 'relative') {
                        const parsed = parseRelativeTime(dateInfo.text);
                        if (parsed) {
                            console.log('상대시간 파싱 성공:', dateInfo.text, '->', parsed);
                            return {success: true, date: parsed, type: 'relative', original: dateInfo.text};
                        }
                    }
                }

                console.log('날짜 파싱 실패');
                return {success: false, date: null, type: null, original: null};
            }''')

            if date_result['success']:
                parsed_date = date_result['date']
                print(f"  [DATE] 날짜 파싱 성공: '{date_result['original']}' ({date_result['type']}) → {parsed_date}")
                return parsed_date
            else:
                # 기본값: 오늘 날짜
                today = datetime.now().strftime('%Y-%m-%d')
                print(f"  [DATE] 날짜 파싱 실패, 기본값 사용: {today}")
                return today

        except Exception as e:
            # 오류 시 기본값
            today = datetime.now().strftime('%Y-%m-%d')
            print(f"  [WARNING] 날짜 파싱 중 오류: {e}, 기본값 사용: {today}")
            return today


    
    
    async def _process_review_results(self, reviews: List[Dict], platform_store_id: str, user_id: str, days: int = 7) -> Dict:
        """리뷰 결과 처리 및 Supabase reviews_baemin 테이블에 저장"""
        try:
            reviews_found = len(reviews)
            reviews_new = 0
            reviews_updated = 0
            
            if reviews_found == 0:
                print("수집된 리뷰가 없습니다.")
                return {
                    'success': True,
                    'reviews_found': 0,
                    'reviews_new': 0,
                    'reviews_updated': 0,
                    'table_used': 'reviews_baemin'
                }
            
            # platform_store_id 조회
            platform_store_result = self.supabase.table('platform_stores').select('id').eq('user_id', user_id).eq('platform_store_id', platform_store_id).eq('platform', 'baemin').single().execute()
            
            if not platform_store_result.data:
                print(f"platform_stores 테이블에서 store_id {platform_store_id}를 찾을 수 없습니다.")
                return {
                    'success': False,
                    'error': f'Store not found in platform_stores: {platform_store_id}',
                    'reviews_found': reviews_found,
                    'reviews_new': 0,
                    'reviews_updated': 0
                }
            
            platform_store_uuid = platform_store_result.data['id']
            print(f"Platform store UUID: {platform_store_uuid}")
            
            # 기존 리뷰 확인 (날짜 범위 기반 중복 방지)
            from datetime import datetime, timedelta

            # 크롤링 기간 내의 기존 리뷰만 확인 (ID + 날짜 조합으로 더 정확한 중복 검사)
            target_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            existing_reviews_result = self.supabase.table('reviews_baemin')\
                .select('baemin_review_id, review_date')\
                .eq('platform_store_id', platform_store_uuid)\
                .gte('review_date', target_date)\
                .execute()

            # ID + 날짜 조합으로 중복 검사 (같은 ID라도 다른 날짜면 다른 리뷰)
            existing_review_keys = {f"{review['baemin_review_id']}_{review['review_date']}" for review in existing_reviews_result.data}

            print(f"기존 리뷰 수 ({target_date} 이후): {len(existing_review_keys)}")
            
            # 새로운 리뷰만 필터링하여 데이터 변환
            new_reviews_data = []
            for review in reviews:
                baemin_review_id = review.get('baemin_review_id', '')
                review_date = review.get('review_date', '')

                # ID + 날짜 조합으로 중복 검사
                review_key = f"{baemin_review_id}_{review_date}"
                if review_key in existing_review_keys:
                    print(f"중복 리뷰 건너뛰기: {baemin_review_id} ({review_date})")
                    continue
                
                # reviews_baemin 테이블 구조에 맞게 데이터 변환
                order_menu_items = review.get('order_menu_items', [])
                order_menu_jsonb = json.dumps(order_menu_items, ensure_ascii=False) if order_menu_items else '[]'
                
                # baemin_metadata 생성
                baemin_metadata = {
                    'delivery_review': review.get('delivery_review', ''),
                    'crawled_at': datetime.now().isoformat()
                }
                
                review_data = {
                    'platform_store_id': platform_store_uuid,
                    'baemin_review_id': baemin_review_id,
                    'baemin_review_url': f"https://self.baemin.com/shops/{platform_store_id}/reviews",
                    'reviewer_name': review.get('reviewer_name', ''),
                    'reviewer_id': '',  # 배민은 reviewer_id가 명확하지 않음
                    'reviewer_level': '',  # 배민은 reviewer_level이 없음
                    'rating': review.get('rating') if review.get('rating') else None,
                    'review_text': review.get('review_text', ''),
                    'review_date': review.get('review_date', ''),
                    'order_menu_items': order_menu_jsonb,
                    'reply_text': review.get('reply_text'),
                    'reply_status': review.get('reply_status', 'draft'),
                    'has_photos': bool(review.get('review_images')) if review.get('review_images') else False,  # 이미지 여부 확인
                    'baemin_metadata': json.dumps(baemin_metadata, ensure_ascii=False),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                new_reviews_data.append(review_data)
            
            reviews_new = len(new_reviews_data)
            
            if reviews_new == 0:
                print("모든 리뷰가 이미 존재합니다. 새로 저장할 리뷰가 없습니다.")
                return {
                    'success': True,
                    'reviews_found': reviews_found,
                    'reviews_new': 0,
                    'reviews_updated': 0,
                    'message': 'All reviews already exist',
                    'table_used': 'reviews_baemin'
                }
            
            # Supabase에 새 리뷰들 개별 삽입 (중복 처리)
            print(f"Supabase에 {reviews_new}개의 새 리뷰 저장 중...")
            
            successfully_saved = 0
            for review_data in new_reviews_data:
                try:
                    # 저장 전 필수 필드 검증 및 보완
                    self._validate_and_fix_review_data(review_data, platform_store_uuid, user_id)
                    
                    # 개별 삽입으로 중복 에러 처리
                    insert_result = self.supabase.table('reviews_baemin').insert(review_data).execute()
                    if insert_result.data:
                        successfully_saved += 1
                        print(f"리뷰 저장 성공: {review_data.get('baemin_review_id')}")
                except Exception as e:
                    error_str = str(e)
                    if '23505' in error_str or 'duplicate' in error_str.lower():
                        print(f"중복 리뷰 건너뛰기: {review_data.get('baemin_review_id')}")
                    else:
                        self.logger.error(f"리뷰 저장 실패: {error_str}")
                        self.logger.error(f"실패한 데이터: {review_data}")
                    continue
            
            self.logger.info(f"{successfully_saved}개의 새 리뷰 저장 완료")
            insert_result = {'data': True}  # 성공 플래그 설정
            
            if successfully_saved > 0 or reviews_new == 0:
                # platform_stores 테이블의 last_crawled_at 업데이트
                try:
                    self.supabase.table('platform_stores').update({
                        'last_crawled_at': datetime.now().isoformat()
                    }).eq('id', platform_store_uuid).execute()
                    print("platform_stores 테이블 업데이트 완료")
                except Exception as update_error:
                    print(f"platform_stores 업데이트 중 오류 (무시): {str(update_error)}")
                
                return {
                    'success': True,
                    'reviews_found': reviews_found,
                    'reviews_new': successfully_saved,
                    'reviews_updated': reviews_updated,
                    'reviews_skipped': reviews_new - successfully_saved,
                    'table_used': 'reviews_baemin',
                    'platform_store_id': platform_store_uuid
                }
            else:
                return {
                    'success': True,
                    'reviews_found': reviews_found,
                    'reviews_new': 0,
                    'reviews_updated': 0,
                    'reviews_skipped': reviews_new,
                    'message': 'All reviews already exist or failed to save',
                    'table_used': 'reviews_baemin'
                }
            
        except Exception as e:
            error_msg = f"Supabase 저장 중 오류: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'reviews_found': reviews_found,
                'reviews_new': 0,
                'reviews_updated': 0
            }

    def _validate_and_fix_review_data(self, review_data: Dict, platform_store_uuid: str, user_id: str):
        """저장 전 리뷰 데이터 검증 및 필수 필드 보완"""
        from datetime import datetime
        
        # 1. 필수 필드 설정
        if not review_data.get('platform_store_id'):
            review_data['platform_store_id'] = platform_store_uuid
        
        # user_id는 reviews_baemin 테이블에 없으므로 제거
        if 'user_id' in review_data:
            del review_data['user_id']
            
        # 2. review_date 검증 및 수정
        review_date = review_data.get('review_date')
        if not review_date or review_date == '' or review_date is None:
            review_data['review_date'] = datetime.now().strftime('%Y-%m-%d')
            print(f"리뷰 날짜 누락으로 기본값 설정: {review_data['review_date']}")
        elif isinstance(review_date, str):
            # 날짜 형식 검증
            try:
                if len(review_date) != 10 or review_date.count('-') != 2:
                    review_data['review_date'] = datetime.now().strftime('%Y-%m-%d')
                    print(f"잘못된 날짜 형식으로 기본값 설정: {review_date} → {review_data['review_date']}")
                else:
                    # YYYY-MM-DD 형식 확인
                    datetime.strptime(review_date, '%Y-%m-%d')
            except (ValueError, TypeError):
                review_data['review_date'] = datetime.now().strftime('%Y-%m-%d')
                print(f"날짜 파싱 오류로 기본값 설정: {review_date} → {review_data['review_date']}")
        
        # 3. 기타 필수 필드 기본값 설정
        if not review_data.get('reviewer_name'):
            review_data['reviewer_name'] = '익명'
            
        if review_data.get('review_text') is None:
            review_data['review_text'] = ''
            
        if not review_data.get('rating') or review_data.get('rating') == 0:
            review_data['rating'] = 5
            
        if not review_data.get('order_menu_items'):
            review_data['order_menu_items'] = []
            
        # 4. baemin_review_id 검증 (고유 식별자)
        if not review_data.get('baemin_review_id'):
            # 해시 기반 ID 생성
            import hashlib
            content = f"{review_data['reviewer_name']}_{review_data['review_text']}_{review_data['review_date']}"
            review_data['baemin_review_id'] = hashlib.md5(content.encode()).hexdigest()[:24]
            print(f"baemin_review_id 누락으로 해시 생성: {review_data['baemin_review_id']}")
        
        # 5. created_at, updated_at 설정
        current_time = datetime.now().isoformat()
        if not review_data.get('created_at'):
            review_data['created_at'] = current_time
        if not review_data.get('updated_at'):
            review_data['updated_at'] = current_time
            
        print(f"데이터 검증 완료: {review_data.get('baemin_review_id')} - {review_data.get('review_date')}")

async def main():
    parser = argparse.ArgumentParser(description='배달의민족 리뷰 크롤링')
    parser.add_argument('--username', required=True, help='배민 사업자 아이디')
    parser.add_argument('--password', required=True, help='배민 사업자 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID (platform_store_id)')
    parser.add_argument('--user-id', required=True, help='사용자 ID (UUID)')
    parser.add_argument('--days', type=int, default=7, help='크롤링 기간 (일)')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드')
    parser.add_argument('--timeout', type=int, default=30000, help='타임아웃 (ms)')
    
    args = parser.parse_args()
    
    crawler = BaeminReviewCrawler(
        headless=args.headless, 
        timeout=args.timeout
    )
    result = await crawler.crawl_reviews(
        args.username, 
        args.password, 
        args.store_id,
        args.user_id, 
        args.days
    )
    
    # 결과 출력 (JSON 형태)
    print(f"CRAWLING_RESULT:{json.dumps(result, ensure_ascii=False)}")
    
    return result['success']

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)