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
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from supabase import create_client, Client
from dotenv import load_dotenv

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from star_rating_extractor import StarRatingExtractor

class BaeminReviewCrawler:
    def __init__(self, headless=True, timeout=30000):
        self.headless = headless
        self.timeout = timeout
        
        # 향상된 별점 추출기 초기화
        self.rating_extractor = StarRatingExtractor()
        
        # Supabase 클라이언트 초기화 (Service Role Key 사용 - RLS 우회)
        load_dotenv()
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            raise ValueError("Supabase 환경변수가 설정되지 않았습니다. NEXT_PUBLIC_SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 확인하세요.")
        
        self.supabase: Client = create_client(supabase_url, supabase_service_key)
    
    async def crawl_reviews(self, username: str, password: str, 
                           platform_store_id: str, user_id: str, days: int = 7) -> Dict:
        """리뷰 크롤링 메인 함수"""
        try:
            print(f"배민 리뷰 크롤링 시작: {platform_store_id}")
            
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
                return await self._process_review_results(reviews, platform_store_id, user_id)
                
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
                print("✅ 배민 로그인 성공")
                return True
            else:
                print("❌ 배민 로그인 실패 - 로그인 페이지에 남아있음")
                return False
                
        except Exception as e:
            print(f"❌ 로그인 중 오류: {str(e)}")
            return False
    
    async def _crawl_review_page(self, page, platform_store_id: str, days: int) -> List[Dict]:
        """배민 리뷰 페이지 크롤링"""
        try:
            # 리뷰 페이지로 직접 이동
            review_url = f"https://self.baemin.com/shops/{platform_store_id}/reviews"
            print(f"리뷰 페이지로 이동: {review_url}")
            
            try:
                # DOM이 로드되면 바로 진행 (networkidle을 기다리지 않음)
                await page.goto(review_url, wait_until='domcontentloaded', timeout=15000)
            except Exception as e:
                # 타임아웃이 발생해도 페이지는 이미 이동했을 가능성이 높으므로 계속 진행
                print(f"⚠️ 페이지 로드 타임아웃 (무시하고 진행): {str(e)}")
            
            await page.wait_for_timeout(3000)
            print("✅ 리뷰 페이지 로드 완료")
            
            # 날짜 필터 선택 (드롭박스 클릭 후 라디오 버튼 선택)
            print(f"날짜 필터 선택 시도: 최근 {days}일")
            try:
                # 1. 먼저 날짜 드롭박스 클릭 (현재 날짜 표시 영역)
                date_dropdown = await page.query_selector("div.ReviewFilter-module__NZW0")
                if date_dropdown:
                    await date_dropdown.click()
                    await page.wait_for_timeout(1000)
                    print("✅ 날짜 드롭박스 열기 성공")
                
                # 2. 라디오 버튼 선택
                if days >= 30:
                    # 최근 30일 선택
                    radio_30 = await page.query_selector('input[type="radio"][value="최근 30일"]')
                    if radio_30:
                        await radio_30.click()
                        print("✅ 최근 30일 선택")
                else:
                    # 최근 7일 선택  
                    radio_7 = await page.query_selector('input[type="radio"][value="최근 7일"]')
                    if radio_7:
                        await radio_7.click()
                        print("✅ 최근 7일 선택")
                
                await page.wait_for_timeout(500)
                
                # 3. 적용 버튼 클릭 (중요!)
                apply_button = await page.query_selector('button[type="button"]:has-text("적용")')
                if apply_button:
                    await apply_button.click()
                    print("✅ 적용 버튼 클릭")
                    await page.wait_for_timeout(2000)
                
                print(f"✅ 날짜 필터 적용 완료")
            except Exception as e:
                print(f"⚠️ 날짜 필터 선택 실패, 기본값(6개월) 사용: {str(e)}")
            
            # 미답변 탭으로 이동 (선택사항)
            try:
                unanswered_tab = await page.query_selector('button#no-comment')
                if unanswered_tab:
                    await unanswered_tab.click()
                    await page.wait_for_timeout(2000)
                    print("✅ 미답변 탭으로 이동")
            except Exception as e:
                print(f"ℹ️ 미답변 탭 이동 스킵 (전체 리뷰 크롤링): {str(e)}")
            
            # 리뷰 수집
            reviews = await self._extract_reviews(page)
            
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
        """리뷰 데이터 추출"""
        reviews = []
        
        try:
            # 리뷰 목록 로드 대기
            await page.wait_for_timeout(3000)
            
            # 페이지 구조 디버깅
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
            
            # 방법 1: 리뷰어 이름을 포함한 요소의 상위 컨테이너 찾기
            try:
                reviewer_span = await page.query_selector('span.Typography_b_pnsa_1bisyd47')
                if reviewer_span:
                    # 상위로 올라가면서 리뷰 컨테이너 찾기
                    parent = await reviewer_span.evaluate_handle('(element) => element.closest("article, section, div[class*=\\"module\\"], li")')
                    if parent:
                        # 같은 레벨의 모든 요소 찾기
                        container_class = await parent.evaluate('(element) => element.className')
                        container_tag = await parent.evaluate('(element) => element.tagName.toLowerCase()')
                        
                        if container_class and container_class.strip():
                            # 클래스명이 있을 때만 클래스 선택자 추가
                            class_name = container_class.split(" ")[0]
                            if class_name:
                                review_selector = f'{container_tag}.{class_name}'
                            else:
                                review_selector = container_tag
                        else:
                            review_selector = container_tag
                        
                        print(f"✅ 리뷰 컨테이너 발견: {review_selector}")
            except Exception as e:
                print(f"리뷰어 기반 검색 실패: {str(e)}")
            
            # 방법 2: 리뷰번호를 포함한 텍스트로 찾기
            if not review_selector:
                try:
                    review_number_elements = await page.query_selector_all('span:has-text("리뷰번호")')
                    if review_number_elements:
                        for elem in review_number_elements:
                            parent = await elem.evaluate_handle('(element) => element.closest("article, section, div, li")')
                            if parent:
                                container_tag = await parent.evaluate('(element) => element.tagName.toLowerCase()')
                                review_selector = container_tag
                                print(f"✅ 리뷰번호 기반 컨테이너 발견: {review_selector}")
                                break
                except Exception as e:
                    print(f"리뷰번호 기반 검색 실패: {str(e)}")
            
            if not review_selector:
                print("⚠️ 리뷰 요소를 찾을 수 없습니다. 기본 선택자 사용")
                review_selector = "article, section, div"
            
            # 리뷰 요소 찾기 - 더 직접적인 방법
            # 리뷰번호를 포함한 모든 요소의 상위 컨테이너를 찾기
            review_elements = []
            try:
                # 방법 1: 리뷰번호로 찾기
                review_number_spans = await page.query_selector_all('span:has-text("리뷰번호")')
                print(f"리뷰번호 요소 {len(review_number_spans)}개 발견")
                
                for span in review_number_spans:
                    # 각 리뷰번호의 상위 컨테이너 찾기
                    container = await span.evaluate_handle('''(element) => {
                        let parent = element;
                        // 적절한 컨테이너를 찾을 때까지 상위로 이동
                        while (parent && parent.parentElement) {
                            parent = parent.parentElement;
                            // 리뷰어 이름과 리뷰 텍스트를 모두 포함하는 컨테이너 찾기
                            const hasReviewer = parent.querySelector('span.Typography_b_pnsa_1bisyd47');
                            const hasReviewText = parent.querySelector('span.Typography_b_pnsa_1bisyd49');
                            if (hasReviewer && hasReviewText) {
                                return parent;
                            }
                        }
                        return null;
                    }''')
                    
                    if container:
                        review_elements.append(container)
                
                print(f"✅ 총 {len(review_elements)}개의 리뷰 컨테이너 발견")
                
            except Exception as e:
                print(f"리뷰번호 기반 컨테이너 검색 중 오류: {str(e)}")
                
                # 폴백: 기존 선택자 사용
                if review_selector:
                    review_elements = await page.query_selector_all(review_selector)
                    print(f"폴백 선택자로 {len(review_elements)}개 요소 발견")
            
            # 모든 리뷰 추출
            for i, review_element in enumerate(review_elements):
                try:
                    print(f"리뷰 {i+1}/{len(review_elements)} 처리 중...")
                    review_data = await self._extract_single_review(review_element)
                    if review_data:
                        reviews.append(review_data)
                        print(f"리뷰 {i+1} 추출 완료")
                except Exception as e:
                    print(f"리뷰 {i+1} 처리 중 오류: {str(e)}")
                    continue
            
            print(f"총 {len(reviews)}개 리뷰 추출 완료")
            return reviews
            
        except Exception as e:
            print(f"리뷰 추출 중 오류: {str(e)}")
            return reviews
    
    async def _load_all_reviews(self, page):
        """페이지 스크롤로 추가 리뷰 로드 (필요시)"""
        try:
            # 간단히 한 번만 스크롤하여 추가 리뷰 로드 시도
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(2000)
            print("페이지 스크롤 완료")
        except Exception as e:
            print(f"스크롤 중 오류: {str(e)}")
    
    async def _extract_single_review(self, review_element) -> Optional[Dict]:
        """개별 리뷰 데이터 추출 (새로운 셀렉터 적용)"""
        try:
            review_data = {}
            
            # 리뷰어 이름 - 더 간단한 방법
            # Typography_b_pnsa_1bisyd47 클래스를 가진 span 찾기
            reviewer_element = await review_element.query_selector("span.Typography_b_pnsa_1bisyd47")
            if reviewer_element:
                review_data['reviewer_name'] = await reviewer_element.text_content()
            
            # 리뷰 날짜
            date_element = await review_element.query_selector("span:has-text('년'):has-text('월'):has-text('일')")
            if date_element:
                date_text = await date_element.text_content()
                review_data['review_date'] = self._parse_date(date_text)
            
            # 리뷰 번호 - 가장 중요한 고유 식별자
            review_id_element = await review_element.query_selector("span:has-text('리뷰번호')")
            if review_id_element:
                id_text = await review_id_element.text_content()
                # "리뷰번호 2025081802062196" 형식에서 숫자만 추출
                import re
                match = re.search(r'리뷰번호\s*(\d+)', id_text)
                if match:
                    review_data['baemin_review_id'] = match.group(1)
                    print(f"  리뷰번호: {review_data['baemin_review_id']}")
            
            # 리뷰 텍스트 - Typography 클래스 기반
            review_text_selectors = [
                "span.Typography_b_pnsa_1bisyd49.Typography_b_pnsa_1bisyd4q.Typography_b_pnsa_1bisyd41u",
                "span[data-atelier-component='Typography']"
            ]
            for selector in review_text_selectors:
                elements = await review_element.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    # 리뷰어 이름, 날짜, 리뷰번호, 메뉴명이 아닌 텍스트만 리뷰로 간주
                    if text and len(text) > 5 and not any(x in text for x in ['년', '월', '일', '리뷰번호', '세트', ')']):
                        if 'reviewer_name' not in review_data or text != review_data.get('reviewer_name'):
                            review_data['review_text'] = text.strip()
                            break
                if 'review_text' in review_data:
                    break
            
            # 주문 메뉴 - Badge 컴포넌트 내부의 메뉴명
            menu_elements = await review_element.query_selector_all("ul.ReviewMenus-module__WRZI span.Badge_b_pnsa_19agxiso")
            order_menu_items = []
            for menu_element in menu_elements:
                menu_text = await menu_element.text_content()
                if menu_text and menu_text.strip():
                    order_menu_items.append(menu_text.strip())
            review_data['order_menu_items'] = order_menu_items
            
            # 배송 평가 - ReviewDelivery 모듈 내부
            delivery_review_element = await review_element.query_selector("div.ReviewDelivery-module__QlG8 span.Badge_b_pnsa_19agxiso")
            if delivery_review_element:
                delivery_text = await delivery_review_element.text_content()
                review_data['delivery_review'] = delivery_text.strip()
            
            # 별점 추출 (향상된 추출기 사용)
            rating = await self.rating_extractor.extract_rating(review_element, 'baemin')
            if rating:
                review_data['rating'] = rating
            
            # 리뷰 ID 생성
            review_data['baemin_review_id'] = await self._generate_review_id(review_element)
            
            # 답글 상태 확인
            reply_info = await self._check_reply_status(review_element)
            review_data.update(reply_info)
            
            return review_data
            
        except Exception as e:
            print(f"개별 리뷰 추출 중 오류: {str(e)}")
            return None
    
    
    async def _check_reply_status(self, review_element) -> Dict:
        """답글 상태 확인"""
        try:
            result = {
                'reply_text': None,
                'reply_status': None
            }
            
            # 답글 작성 버튼 확인 (미답변)
            reply_write_btn = await review_element.query_selector("button.reply-write-btn")
            if reply_write_btn:
                result['reply_status'] = 'draft'
                return result
            
            # 기존 답글 확인 (답변 완료)
            reply_section = await review_element.query_selector("div.reply-section")
            if reply_section:
                result['reply_status'] = 'sent'
                
                # 답글 텍스트 추출
                reply_text_element = await reply_section.query_selector("p.reply-text")
                if reply_text_element:
                    reply_text = await reply_text_element.text_content()
                    if reply_text and reply_text.strip():
                        result['reply_text'] = reply_text.strip()
            
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
                # "리뷰번호 2025081802062196" 형식에서 숫자만 추출
                import re
                match = re.search(r'리뷰번호\s*(\d+)', id_text)
                if match:
                    review_id = match.group(1)
                    print(f"리뷰번호 추출: {review_id}")
                    return review_id
            
            # 리뷰번호를 못 찾은 경우 해시 생성 (폴백)
            print("리뷰번호를 찾을 수 없어 해시 생성")
            reviewer_name = ""
            name_element = await review_element.query_selector("span.Typography_b_pnsa_1bisyd47")
            if name_element:
                reviewer_name = await name_element.text_content()
            
            review_text = ""
            text_element = await review_element.query_selector("span.Typography_b_pnsa_1bisyd49")
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
            return f"baemin_{int(datetime.now().timestamp() * 1000)}"
    
    def _parse_date(self, date_text: str) -> str:
        """날짜 텍스트 파싱"""
        try:
            import re
            # "2025년 8월 18일" 형태를 "2025-08-18" 형태로 변환
            date_match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_text)
            if date_match:
                year, month, day = date_match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            # "2025.08.21" 형태를 "2025-08-21" 형태로 변환
            date_match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', date_text)
            if date_match:
                year, month, day = date_match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            return date_text
            
        except Exception as e:
            print(f"날짜 파싱 중 오류: {str(e)}")
            return date_text
    
    async def _process_review_results(self, reviews: List[Dict], platform_store_id: str, user_id: str) -> Dict:
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
            
            # 기존 리뷰 확인 (중복 방지)
            existing_reviews_result = self.supabase.table('reviews_baemin').select('baemin_review_id').eq('platform_store_id', platform_store_uuid).execute()
            existing_review_ids = {review['baemin_review_id'] for review in existing_reviews_result.data}
            
            print(f"기존 리뷰 수: {len(existing_review_ids)}")
            
            # 새로운 리뷰만 필터링하여 데이터 변환
            new_reviews_data = []
            for review in reviews:
                baemin_review_id = review.get('baemin_review_id', '')
                
                # 이미 존재하는 리뷰인지 확인
                if baemin_review_id in existing_review_ids:
                    print(f"중복 리뷰 건너뛰기: {baemin_review_id}")
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
                    'has_photos': False,  # 현재 구현에서는 사진 미처리
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
                    # 개별 삽입으로 중복 에러 처리
                    insert_result = self.supabase.table('reviews_baemin').insert(review_data).execute()
                    if insert_result.data:
                        successfully_saved += 1
                except Exception as e:
                    error_str = str(e)
                    if '23505' in error_str or 'duplicate' in error_str.lower():
                        print(f"중복 리뷰 건너뛰기: {review_data.get('baemin_review_id')}")
                    else:
                        print(f"리뷰 저장 실패: {error_str[:100]}")
                    continue
            
            print(f"✅ {successfully_saved}개의 새 리뷰 저장 완료")
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