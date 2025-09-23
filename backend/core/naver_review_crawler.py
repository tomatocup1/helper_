#!/usr/bin/env python3
"""
네이버 리뷰 크롤링 엔진
- 네이버 플레이스 리뷰 페이지 자동 수집
- 이미지, 텍스트, 키워드, 평점 통합 추출
- "더보기" 버튼 자동 클릭으로 전체 데이터 수집
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from supabase import create_client, Client
from dotenv import load_dotenv

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from naver_login_auto import NaverAutoLogin

class NaverReviewCrawler:
    def __init__(self, headless=True, timeout=30000, force_fresh_login=False):
        self.headless = headless
        self.timeout = timeout
        self.force_fresh_login = force_fresh_login
        self.login_system = NaverAutoLogin(
            headless=headless, 
            timeout=timeout, 
            force_fresh_login=force_fresh_login
        )
        
        # Supabase 클라이언트 초기화 (Service Role Key 사용 - RLS 우회)
        load_dotenv()
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            raise ValueError("Supabase 환경변수가 설정되지 않았습니다. NEXT_PUBLIC_SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 확인하세요.")
        
        self.supabase: Client = create_client(supabase_url, supabase_service_key)
    
    async def _close_popup_if_exists(self, page) -> bool:
        """리뷰 페이지에서 나타나는 팝업 닫기"""
        try:
            print("팝업 확인 및 닫기 처리 중...")
            
            # 다양한 팝업 닫기 버튼 선택자들
            popup_close_selectors = [
                "i.fn-booking.fn-booking-close1",           # 사용자가 제공한 선택자
                ".fn-booking-close1",                       # 클래스만
                "i[aria-label='닫기']",                     # aria-label 속성
                ".popup_close",                             # 일반적인 팝업 닫기
                ".modal_close",                             # 모달 닫기
                "button[class*='close']",                   # 닫기 버튼
                ".btn_close",                               # 버튼 타입 닫기
                "[data-action='close']",                    # 데이터 액션
                ".layer_close"                              # 레이어 닫기
            ]
            
            for selector in popup_close_selectors:
                try:
                    # 팝업 요소가 있는지 확인 (짧은 타임아웃)
                    close_button = await page.wait_for_selector(selector, timeout=2000)
                    if close_button:
                        # 요소가 실제로 보이는지 확인
                        is_visible = await close_button.is_visible()
                        if is_visible:
                            print(f"팝업 닫기 버튼 발견: {selector}")
                            await close_button.click()
                            await page.wait_for_timeout(1000)  # 팝업 닫힘 대기
                            print("팝업 닫기 완료")
                            return True
                except Exception:
                    # 이 선택자로는 팝업을 찾지 못함, 다음 시도
                    continue
                    
            print("팝업이 없거나 이미 닫혀있음")
            return False
            
        except Exception as e:
            print(f"팝업 처리 중 오류: {str(e)}")
            return False
        
    async def crawl_reviews(self, platform_id: str, platform_password: str, 
                           store_id: str, user_id: str, days: int = 7) -> Dict:
        """리뷰 크롤링 메인 함수"""
        try:
            print(f"Starting review crawling for store: {store_id}")
            
            # 로그인 처리 및 브라우저 세션 유지 (매장 크롤링 비활성화)
            login_result = await self.login_system.login(
                platform_id, 
                platform_password, 
                keep_browser_open=True,
                crawl_stores=False  # 리뷰 크롤러는 매장 크롤링 불필요
            )
            if not login_result['success']:
                return {
                    'success': False,
                    'error': f"로그인 실패: {login_result.get('error', 'Unknown error')}",
                    'reviews_found': 0,
                    'reviews_new': 0,
                    'reviews_updated': 0
                }
            
            print("로그인 성공 - 동일한 브라우저 세션에서 리뷰 페이지 접속 중...")
            
            # 기존 브라우저 세션을 사용하여 리뷰 페이지 크롤링
            browser = login_result['browser']
            playwright = login_result['playwright'] 
            page = login_result['page']
            
            try:
                # 브라우저 연결 상태 확인 (페이지가 유효한지 확인)
                try:
                    current_url = page.url  # 페이지 상태 확인
                    print(f"브라우저 연결 상태 양호 - 현재 URL: {current_url}")
                    print("크롤링 시작")
                    reviews = await self._crawl_review_page_with_session(browser, page, store_id, days)
                    return await self._process_review_results(reviews, store_id, user_id)
                except Exception as connection_error:
                    print(f"브라우저 연결이 끊어짐: {str(connection_error)}")
                    return {
                        'success': False,
                        'error': f'브라우저 연결 오류: {str(connection_error)}',
                        'reviews_found': 0,
                        'reviews_new': 0,
                        'reviews_updated': 0
                    }
            except Exception as e:
                print(f"크롤링 실행 중 오류: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'reviews_found': 0,
                    'reviews_new': 0,
                    'reviews_updated': 0
                }
            finally:
                # 크롤링 완료 후 브라우저 정리
                try:
                    if browser:
                        await browser.close()
                    if playwright:
                        await playwright.stop()
                except Exception as e:
                    print(f"브라우저 정리 중 오류: {str(e)}")
            
        except Exception as e:
            print(f"크롤링 중 오류 발생: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'reviews_found': 0,
                'reviews_new': 0,
                'reviews_updated': 0
            }
    
    async def _crawl_review_page_with_session(self, browser, page, store_id: str, days: int) -> List[Dict]:
        """기존 브라우저 세션을 사용한 리뷰 페이지 크롤링"""
        try:
            # 리뷰 페이지 URL 생성 (지정된 store_id 사용)
            review_url = f"https://new.smartplace.naver.com/bizes/place/{store_id}/reviews"
            print(f"✅ 지정된 매장 ID로 직접 이동: {store_id}")
            print(f"리뷰 페이지 URL: {review_url}")
            
            # 최적화: 직접 리뷰 페이지로 이동 (대기시간 단축)
            await page.goto(review_url, wait_until='domcontentloaded', timeout=self.timeout)
            await page.wait_for_timeout(3000)  # 최적화: 대기시간 단축 (networkidle 대신 3초 고정)
            
            print(f"✅ 리뷰 페이지 접속 완료: {review_url}")
            
            # 팝업 닫기 처리 (리뷰 페이지에서 나타나는 팝업)
            await self._close_popup_if_exists(page)
            
            # 날짜 필터 설정
            await self._set_date_filter(page, days)
            
            # 리뷰 수집
            reviews = await self._extract_reviews(page)
            
            print(f"수집된 리뷰 수: {len(reviews)}")
            return reviews
            
        except Exception as e:
            print(f"리뷰 페이지 크롤링 중 오류: {str(e)}")
            return []
    
    async def _crawl_review_page(self, profile_path: str, store_id: str, days: int) -> List[Dict]:
        """리뷰 페이지 크롤링"""
        browser = None
        playwright = None
        
        try:
            # 브라우저 설정 (로그인 시스템과 동일한 프로필 사용)
            playwright = await async_playwright().start()
            
            # 로그인 시스템과 동일한 브라우저 arguments 사용
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-gpu',
                '--disable-web-security',
                '--no-sandbox',
                '--disable-features=VizDisplayCompositor'
            ]
            
            browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=self.headless,
                args=browser_args,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale='ko-KR',
                timezone_id='Asia/Seoul',
                viewport={'width': 1280, 'height': 720},
                java_script_enabled=True,
                accept_downloads=True,
                ignore_https_errors=True
            )
            
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            # 리뷰 페이지 URL 생성 (지정된 store_id 사용)
            review_url = f"https://new.smartplace.naver.com/bizes/place/{store_id}/reviews"
            print(f"✅ 지정된 매장 ID로 직접 이동: {store_id}")
            print(f"리뷰 페이지 URL: {review_url}")
            
            # 최적화: 직접 리뷰 페이지로 이동 (대기시간 단축)
            await page.goto(review_url, wait_until='domcontentloaded', timeout=self.timeout)
            await page.wait_for_timeout(3000)  # 최적화: 대기시간 단축 (networkidle 대신 3초 고정)
            
            print(f"✅ 리뷰 페이지 접속 완료: {review_url}")
            
            # 날짜 필터 설정
            await self._set_date_filter(page, days)
            
            # 리뷰 수집
            reviews = await self._extract_reviews(page)
            
            print(f"수집된 리뷰 수: {len(reviews)}")
            return reviews
            
        except Exception as e:
            print(f"리뷰 페이지 크롤링 중 오류: {str(e)}")
            return []
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
    
    async def _set_date_filter(self, page, days: int):
        """날짜 필터 설정"""
        try:
            print(f"날짜 필터 설정: 최근 {days}일")
            
            # 날짜 드롭박스 클릭
            date_selector = "button.ButtonSelector_btn_select__BcLKR[data-area-code='rv.calendarfilter']"
            await page.wait_for_selector(date_selector, timeout=self.timeout)
            await page.click(date_selector)
            await page.wait_for_timeout(1000)
            
            # 필터 옵션 선택
            if days <= 7:
                # 7일 선택
                await page.click("a[data-area-code='rv.calendarweek']")
            else:
                # 한달 선택
                await page.click("a[data-area-code='rv.calendarmonth']")
            
            await page.wait_for_timeout(2000)
            print("날짜 필터 설정 완료")
            
        except Exception as e:
            print(f"날짜 필터 설정 중 오류: {str(e)}")
            # 필터 설정 실패해도 계속 진행
    
    async def _extract_reviews(self, page) -> List[Dict]:
        """리뷰 데이터 추출 (무한 스크롤로 모든 리뷰 로드)"""
        reviews = []
        
        try:
            # 리뷰 목록 로드 대기
            await page.wait_for_timeout(3000)
            
            # 리뷰 아이템 선택자 (여러 후보 시도)
            review_selectors = [
                "li.pui__X35jYm.Review_pui_review__zhZdn",  # 기존 선택자
                "li[class*='Review_pui_review']",  # 부분 매칭
                "li[class*='pui_review']",  # 더 포괄적
                ".review-item",  # 일반적인 클래스
                "li[class*='Review']",  # 매우 포괄적
                "li"  # 최후의 수단
            ]

            review_selector = None
            print("리뷰 선택자 확인 중...")

            for selector in review_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    elements = await page.query_selector_all(selector)
                    if elements:
                        review_selector = selector
                        print(f"✅ 리뷰 선택자 발견: {selector} ({len(elements)}개 요소)")
                        break
                except:
                    print(f"❌ 선택자 시도 실패: {selector}")
                    continue

            if not review_selector:
                print("⚠️ 리뷰 선택자를 찾을 수 없음 - 페이지 HTML 확인 필요")
                # 페이지 HTML 일부 출력 (디버깅용)
                page_content = await page.content()
                print(f"페이지 콘텐츠 일부: {page_content[:500]}")
                return []
            
            # 무한 스크롤로 모든 리뷰 로드
            max_scroll_attempts = 30  # 최대 30번까지 스크롤
            no_new_content_count = 0  # 새 콘텐츠가 없는 횟수
            
            for attempt in range(max_scroll_attempts):
                try:
                    # 현재 리뷰 수 확인
                    current_reviews = await page.query_selector_all(review_selector)
                    current_count = len(current_reviews)
                    print(f"스크롤 {attempt + 1}: 현재 로드된 리뷰 수 {current_count}")
                    
                    # 페이지 끝까지 스크롤
                    await page.evaluate("""
                        window.scrollTo(0, document.body.scrollHeight);
                    """)
                    
                    # 스크롤 후 로딩 대기
                    await page.wait_for_timeout(2000)
                    
                    # 새로운 리뷰가 로드되었는지 확인
                    new_reviews = await page.query_selector_all(review_selector)
                    new_count = len(new_reviews)
                    
                    if new_count > current_count:
                        # 새로운 리뷰가 로드됨
                        print(f"새 리뷰 {new_count - current_count}개 로드됨")
                        no_new_content_count = 0
                    else:
                        # 새로운 리뷰가 없음
                        no_new_content_count += 1
                        print(f"새 리뷰 없음 (연속 {no_new_content_count}번)")
                        
                        # 3번 연속 새 콘텐츠가 없으면 종료
                        if no_new_content_count >= 3:
                            print("더 이상 로드할 리뷰가 없음 - 스크롤 완료")
                            break
                    
                    # 추가 로딩 확인을 위한 대기
                    await page.wait_for_timeout(1000)
                    
                except Exception as e:
                    print(f"스크롤 중 오류 (시도 {attempt + 1}): {str(e)}")
                    break
            
            # 최종 리뷰 요소들 가져오기
            final_review_elements = await page.query_selector_all(review_selector)
            final_count = len(final_review_elements)
            print(f"최종 발견된 리뷰 요소 수: {final_count}")
            
            # 모든 리뷰 추출
            for i, review_element in enumerate(final_review_elements):
                try:
                    print(f"리뷰 {i+1}/{final_count} 처리 중...")
                    review_data = await self._extract_single_review(review_element, page)
                    if review_data:
                        reviews.append(review_data)
                        print(f"리뷰 {i+1} 추출 완료")
                except Exception as e:
                    print(f"리뷰 {i+1} 처리 중 오류: {str(e)}")
                    continue
            
            print(f"총 {len(reviews)}개 리뷰 추출 완료")
            
            # 답글 상태별 통계 출력
            self._print_reply_statistics(reviews)
            
            return reviews
            
        except Exception as e:
            print(f"리뷰 추출 중 오류: {str(e)}")
            return reviews
    
    def _print_reply_statistics(self, reviews: List[Dict]) -> None:
        """답글 상태별 통계 출력"""
        try:
            total_reviews = len(reviews)
            if total_reviews == 0:
                return
            
            # 답글 상태별 카운트
            sent_count = 0
            draft_count = 0
            unknown_count = 0
            
            for review in reviews:
                reply_status = review.get('reply_status')
                if reply_status == 'sent':
                    sent_count += 1
                elif reply_status == 'draft':
                    draft_count += 1
                else:
                    unknown_count += 1
            
            # 통계 출력
            print("\n" + "="*50)
            print("📊 답글 상태 통계")
            print("="*50)
            print(f"📝 총 리뷰 수: {total_reviews}개")
            print(f"✅ 답글 완료: {sent_count}개 ({sent_count/total_reviews*100:.1f}%)")
            print(f"⏳ 답글 대기: {draft_count}개 ({draft_count/total_reviews*100:.1f}%)")
            if unknown_count > 0:
                print(f"❓ 상태 불명: {unknown_count}개 ({unknown_count/total_reviews*100:.1f}%)")
            
            # 답글 작성률
            if total_reviews > 0:
                reply_rate = sent_count / total_reviews * 100
                print(f"📈 답글 작성률: {reply_rate:.1f}%")
            
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"답글 통계 출력 중 오류: {str(e)}")

    async def _extract_single_review(self, review_element, page) -> Optional[Dict]:
        """개별 리뷰 데이터 추출"""
        try:
            review_data = {}
            
            # 작성자 정보
            reviewer_info = await self._extract_reviewer_info(review_element)
            review_data.update(reviewer_info)
            
            # 날짜 정보
            date_info = await self._extract_date_info(review_element)
            review_data.update(date_info)
            
            # 리뷰 내용 (더보기 처리 포함)
            review_content = await self._extract_review_content(review_element, page)
            review_data.update(review_content)
            
            # 이미지 정보
            images = await self._extract_review_images(review_element)
            review_data['images'] = images
            
            # 키워드 정보 (더보기 처리 포함)
            keywords = await self._extract_review_keywords(review_element, page)
            review_data['keywords'] = keywords
            
            # 사업자 답글 및 상태 추출 (더보기 처리 포함)
            reply_info = await self._extract_store_reply(review_element, page)
            review_data['reply_text'] = reply_info.get('reply_text')
            review_data['reply_status'] = reply_info.get('reply_status')
            
            # 디버깅을 위한 HTML 구조 출력 (첫 번째 리뷰만)
            if not hasattr(self, '_debug_html_printed'):
                try:
                    html_content = await review_element.inner_html()
                    print(f"=== 첫 번째 리뷰 HTML 구조 디버깅 ===")
                    print(html_content[:2000])  # 처음 2000자만 출력
                    print("=== HTML 구조 디버깅 끝 ===")
                    self._debug_html_printed = True
                except:
                    pass
            
            # 기타 정보
            review_data['has_receipt'] = await self._check_receipt(review_element)
            review_data['review_id'] = await self._generate_review_id(review_element)
            
            return review_data
            
        except Exception as e:
            print(f"개별 리뷰 추출 중 오류: {str(e)}")
            return None
    
    async def _extract_reviewer_info(self, review_element) -> Dict:
        """작성자 정보 추출"""
        try:
            reviewer_info = {}
            
            # 작성자 이름
            name_element = await review_element.query_selector(".pui__NMi-Dp")
            if name_element:
                reviewer_info['reviewer_name'] = await name_element.text_content()
            
            # 작성자 통계 (리뷰 수, 사진 수, 방문 횟수)
            stats_elements = await review_element.query_selector_all(".pui__WN-kAf")
            stats = {}
            for stat_element in stats_elements:
                stat_text = await stat_element.text_content()
                if '리뷰' in stat_text:
                    stats['review_count'] = self._extract_number(stat_text)
                elif '사진' in stat_text:
                    stats['photo_count'] = self._extract_number(stat_text)
                elif '방문' in stat_text:
                    stats['visit_count'] = self._extract_number(stat_text)
            
            reviewer_info['reviewer_stats'] = stats
            
            # 작성자 프로필 URL
            profile_link = await review_element.query_selector("a[data-pui-click-code='profile']")
            if profile_link:
                reviewer_info['reviewer_profile_url'] = await profile_link.get_attribute('href')
            
            return reviewer_info
            
        except Exception as e:
            print(f"작성자 정보 추출 중 오류: {str(e)}")
            return {}
    
    async def _extract_date_info(self, review_element) -> Dict:
        """날짜 정보 추출"""
        try:
            date_info = {}
            
            # 방문일과 작성일 찾기
            date_sections = await review_element.query_selector_all(".pui__4rEbt5")
            for section in date_sections:
                label_element = await section.query_selector(".pui__ewpNGR")
                if label_element:
                    label_text = await label_element.text_content()
                    time_element = await section.query_selector("time")
                    
                    if time_element:
                        date_text = await time_element.text_content()
                        
                        if '방문일' in label_text:
                            date_info['visit_date'] = self._parse_date(date_text)
                        elif '작성일' in label_text:
                            date_info['created_date'] = self._parse_date(date_text)
            
            return date_info
            
        except Exception as e:
            print(f"날짜 정보 추출 중 오류: {str(e)}")
            return {}
    
    async def _extract_review_content(self, review_element, page) -> Dict:
        """리뷰 내용 추출 (더보기 처리 포함)"""
        try:
            content_info = {}

            print("🔍 리뷰 텍스트 추출 시작...")

            # 여러 선택자 시도
            text_selectors = [
                ".pui__vn15t2",  # 기존 선택자
                "[class*='vn15t2']",  # 부분 매칭
                "[class*='review'][class*='text']",  # 포괄적
                "div[class*='text']",  # 더 포괄적
                "a.pui__xtsQN-[data-pui-click-code='text']",  # 직접 텍스트 링크
                "a[class*='xtsQN']",  # 부분 매칭
                "div p", "div span",  # 일반적인 텍스트 요소
            ]

            text_container = None
            found_selector = None

            for selector in text_selectors:
                try:
                    text_container = await review_element.query_selector(selector)
                    if text_container:
                        found_selector = selector
                        print(f"✅ 텍스트 컨테이너 발견: {selector}")
                        break
                except:
                    continue

            if not text_container:
                print("❌ 텍스트 컨테이너를 찾을 수 없음")
                # 리뷰 요소의 전체 텍스트 내용 확인
                full_text = await review_element.text_content()
                print(f"리뷰 요소 전체 텍스트: {full_text[:200]}...")
                return content_info

            # 더보기 버튼 확인 및 클릭
            more_button_selectors = [
                "a.pui__wFzIYl[aria-expanded='false']",  # 기존
                "a[aria-expanded='false']",  # 포괄적
                "button[class*='more']",  # 일반적
                "a[class*='more']"
            ]

            for more_selector in more_button_selectors:
                try:
                    more_button = await text_container.query_selector(more_selector)
                    if more_button:
                        print(f"더보기 버튼 발견: {more_selector} - 클릭 중...")
                        await more_button.click()
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue

            # 텍스트 추출 - 여러 방법 시도
            review_text = ""

            # 1차: 직접 텍스트 링크에서 추출
            text_link_selectors = [
                "a.pui__xtsQN-",  # 기존
                "a[class*='xtsQN']",  # 부분 매칭
                "a[data-pui-click-code='text']",  # 데이터 속성
            ]

            for link_selector in text_link_selectors:
                try:
                    text_element = await text_container.query_selector(link_selector)
                    if text_element:
                        review_text = await text_element.text_content()
                        if review_text and review_text.strip():
                            print(f"✅ 텍스트 추출 성공 (링크): {link_selector}")
                            print(f"   텍스트: {review_text[:100]}...")
                            break
                except:
                    continue

            # 2차: 컨테이너에서 직접 추출
            if not review_text or not review_text.strip():
                try:
                    review_text = await text_container.text_content()
                    if review_text and review_text.strip():
                        print(f"✅ 텍스트 추출 성공 (컨테이너 직접)")
                        print(f"   텍스트: {review_text[:100]}...")
                except:
                    pass

            # 3차: 일반적인 텍스트 요소에서 추출
            if not review_text or not review_text.strip():
                generic_selectors = ["p", "span", "div"]
                for gen_selector in generic_selectors:
                    try:
                        text_elements = await text_container.query_selector_all(gen_selector)
                        for element in text_elements:
                            element_text = await element.text_content()
                            if element_text and len(element_text.strip()) > 10:  # 10자 이상
                                review_text = element_text
                                print(f"✅ 텍스트 추출 성공 (일반): {gen_selector}")
                                print(f"   텍스트: {review_text[:100]}...")
                                break
                        if review_text and review_text.strip():
                            break
                    except:
                        continue

            if review_text and review_text.strip():
                content_info['review_text'] = review_text.strip()
                print(f"✅ 최종 텍스트 저장: {len(review_text)} 글자")
            else:
                print("❌ 리뷰 텍스트 추출 실패")

            # 평점 추출 (별점)
            rating = await self._extract_rating(review_element)
            if rating:
                content_info['rating'] = rating

            return content_info

        except Exception as e:
            print(f"리뷰 내용 추출 중 오류: {str(e)}")
            return {}
    
    async def _extract_review_images(self, review_element) -> List[str]:
        """리뷰 이미지 URL 추출"""
        try:
            images = []
            
            # 이미지 컨테이너 찾기
            image_container = await review_element.query_selector(".Review_img_slide__H3Xlr")
            if not image_container:
                return images
            
            # 모든 이미지 요소 추출
            img_elements = await image_container.query_selector_all("img.Review_img__n9UPw")
            for img_element in img_elements:
                src = await img_element.get_attribute('src')
                if src and src.startswith('http'):
                    images.append(src)
            
            return images
            
        except Exception as e:
            print(f"이미지 추출 중 오류: {str(e)}")
            return []
    
    async def _extract_review_keywords(self, review_element, page) -> List[str]:
        """리뷰 키워드 추출 (더보기 처리 포함)"""
        try:
            keywords = []
            
            # 키워드 컨테이너 찾기
            keyword_container = await review_element.query_selector(".pui__HLNvmI")
            if not keyword_container:
                return keywords
            
            # 더보기 버튼 확인 및 클릭
            more_keywords_button = await keyword_container.query_selector("a.pui__jhpEyP.pui__ggzZJ8[data-pui-click-code='rv.keywordmore']")
            if more_keywords_button:
                print("키워드 더보기 버튼 발견 - 클릭 중...")
                await more_keywords_button.click()
                await page.wait_for_timeout(1000)
            
            # 모든 키워드 추출 (이모지 + 텍스트 구조 처리)
            keyword_elements = await keyword_container.query_selector_all("span.pui__jhpEyP:not(.pui__ggzZJ8)")
            print(f"키워드 요소 개수: {len(keyword_elements)}")

            for i, keyword_element in enumerate(keyword_elements):
                try:
                    # 전체 텍스트 추출 (이모지 alt 텍스트 + 실제 텍스트)
                    keyword_text = await keyword_element.text_content()
                    print(f"키워드 {i+1} 원본 텍스트: '{keyword_text}'")

                    if keyword_text and keyword_text.strip():
                        # 텍스트 정리 (이모지는 이미 text_content()에서 제외됨)
                        clean_keyword = keyword_text.strip()

                        # 더보기 버튼("+숫자개 더보기") 제외
                        if clean_keyword and not clean_keyword.startswith('+') and '더보기' not in clean_keyword:
                            keywords.append(clean_keyword)
                            print(f"✅ 키워드 추가: '{clean_keyword}'")
                        else:
                            print(f"❌ 키워드 제외: '{clean_keyword}'")
                    else:
                        print(f"❌ 빈 키워드 텍스트")

                except Exception as e:
                    print(f"키워드 요소 {i+1} 처리 중 오류: {e}")
                    continue
            
            return keywords
            
        except Exception as e:
            print(f"키워드 추출 중 오류: {str(e)}")
            return []
    
    async def _extract_rating(self, review_element) -> Optional[int]:
        """평점 추출"""
        try:
            # 별점은 보통 다른 위치에 있을 수 있음
            # 이 부분은 실제 HTML 구조에 따라 조정 필요
            return None  # 현재는 별점 정보가 명확하지 않음
            
        except Exception as e:
            print(f"평점 추출 중 오류: {str(e)}")
            return None
    
    async def _extract_store_reply(self, review_element, page) -> Dict[str, Any]:
        """사업자 답글 및 상태 추출 (더보기 처리 포함)"""
        try:
            
            # 결과 초기화
            result = {
                'reply_text': None,
                'reply_status': None
            }
            
            # 1. 먼저 답글 작성 버튼 확인 (미답변 리뷰)
            reply_write_btn = await review_element.query_selector("button[data-area-code='rv.replywrite']")
            if reply_write_btn:
                print("📝 미답변 리뷰 발견 - reply_status: draft")
                result['reply_status'] = 'draft'
                return result
            
            # 2. 답글 수정 버튼 확인 (답변 완료 리뷰)
            reply_edit_btn = await review_element.query_selector("a[data-pui-click-code='rv.replyedit']")
            if reply_edit_btn:
                print("✅ 답변 완료 리뷰 발견 - reply_status: sent")
                result['reply_status'] = 'sent'
                
                # 답글 텍스트 추출
                # 답글 섹션 찾기
                reply_section_selectors = [
                    ".pui__GbW8H7.pui__BDGQvd",  # 답글 섹션 전체
                    ".pui__GbW8H7",  # 답글 섹션 (단일 클래스)
                    "div:has(span.pui__XE54q7)",  # 사업자명 포함한 섹션
                ]
                
                reply_section = None
                for selector in reply_section_selectors:
                    try:
                        reply_section = await review_element.query_selector(selector)
                        if reply_section:
                            print(f"답글 섹션 발견 (선택자: {selector})")
                            break
                    except:
                        continue
                
                if reply_section:
                    # 답글 텍스트 컨테이너 찾기
                    reply_text_selectors = [
                        "a.pui__xtsQN-[data-pui-click-code='rv.replyfold']",  # 정확한 패턴
                        ".pui__J0tczd a.pui__xtsQN-",  # 컨테이너 내 텍스트 링크
                        "a[data-pui-click-code='rv.replyfold']",  # data 속성 기반
                    ]
                    
                    reply_text_container = None
                    for selector in reply_text_selectors:
                        try:
                            reply_text_container = await reply_section.query_selector(selector)
                            if reply_text_container:
                                print(f"답글 텍스트 컨테이너 발견 (선택자: {selector})")
                                break
                        except:
                            continue
                    
                    if reply_text_container:
                        # 더보기 버튼 처리
                        more_button_selectors = [
                            "a.pui__wFzIYl[aria-expanded='false'][data-pui-click-code='rv.replyfold']",
                            "a.pui__wFzIYl[aria-expanded='false']",
                            ".pui__J0tczd a.pui__wFzIYl",
                            "a.pui__wFzIYl",
                        ]
                        
                        more_reply_button = None
                        for selector in more_button_selectors:
                            try:
                                more_reply_button = await reply_section.query_selector(selector)
                                if more_reply_button:
                                    print(f"더보기 버튼 발견 (선택자: {selector})")
                                    break
                            except:
                                continue
                        
                        # 더보기 버튼 클릭
                        if more_reply_button:
                            try:
                                aria_expanded = await more_reply_button.get_attribute('aria-expanded')
                                button_text = await more_reply_button.text_content()
                                print(f"버튼 상태 - aria-expanded: {aria_expanded}, 텍스트: {button_text}")
                                
                                if aria_expanded == 'false' or (button_text and '더보기' in button_text):
                                    print("답글 더보기 버튼 클릭 중...")
                                    await more_reply_button.click()
                                    await page.wait_for_timeout(1500)
                                    print("더보기 버튼 클릭 완료")
                            except Exception as button_error:
                                print(f"버튼 클릭 중 오류: {button_error}")
                        
                        # 답글 텍스트 추출
                        reply_text = await reply_text_container.text_content()
                        if reply_text:
                            cleaned_reply = reply_text.strip()
                            if cleaned_reply and len(cleaned_reply) > 10:
                                print(f"사업자 답글 추출 완료 ({len(cleaned_reply)}자): {cleaned_reply[:100]}...")
                                result['reply_text'] = cleaned_reply
                
                return result
            
            # 3. 답글 버튼이 없는 경우 - 기존 로직으로 답글 섹션 확인
            reply_section_selectors = [
                ".pui__GbW8H7.pui__BDGQvd",
                ".pui__GbW8H7",
            ]
            
            for selector in reply_section_selectors:
                try:
                    reply_section = await review_element.query_selector(selector)
                    if reply_section:
                        # 답글 섹션이 있으면 sent로 간주
                        print(f"답글 섹션 발견 - reply_status: sent (버튼 없음)")
                        result['reply_status'] = 'sent'
                        
                        # 답글 텍스트 추출 (위의 로직 재사용)
                        reply_text_container = await reply_section.query_selector("a[data-pui-click-code='rv.replyfold']")
                        if reply_text_container:
                            reply_text = await reply_text_container.text_content()
                            if reply_text:
                                cleaned_reply = reply_text.strip()
                                if cleaned_reply and len(cleaned_reply) > 10:
                                    result['reply_text'] = cleaned_reply
                        break
                except:
                    continue
            
            # 답글 상태를 확인할 수 없는 경우
            if result['reply_status'] is None:
                print("⚠️ 답글 상태를 확인할 수 없음")
            
            return result
            
        except Exception as e:
            print(f"사업자 답글 추출 중 오류: {str(e)}")
            return {'reply_text': None, 'reply_status': None}
    
    async def _check_receipt(self, review_element) -> bool:
        """영수증 첨부 여부 확인"""
        try:
            receipt_element = await review_element.query_selector(".pui__lHDwSH")
            if receipt_element:
                receipt_text = await receipt_element.text_content()
                return '영수증' in receipt_text
            return False
            
        except Exception as e:
            print(f"영수증 확인 중 오류: {str(e)}")
            return False
    
    async def _generate_review_id(self, review_element) -> str:
        """네이버 리뷰 고유 ID 추출"""
        try:
            # 방법 1: 결제 정보 링크에서 리뷰 ID 추출
            # 예: https://m.place.naver.com/my/review/689f2e547d44f69239bcf8e3/paymentInfo#showReceipt
            payment_link = await review_element.query_selector("a[data-pui-click-code='rv.paymentinfo']")
            if payment_link:
                href = await payment_link.get_attribute('href')
                print(f"결제 정보 링크 발견: {href}")
                
                if href and '/my/review/' in href:
                    # URL에서 리뷰 ID 추출
                    # /my/review/689f2e547d44f69239bcf8e3/paymentInfo 형태에서 ID 추출
                    import re
                    match = re.search(r'/my/review/([a-f0-9]+)/', href)
                    if match:
                        review_id = match.group(1)
                        print(f"✅ 네이버 리뷰 ID 추출 성공: {review_id}")
                        return review_id
                    
                    # 대체 방법: split으로 추출
                    parts = href.split('/my/review/')
                    if len(parts) > 1:
                        review_id = parts[1].split('/')[0]
                        # #showReceipt 같은 해시 제거
                        review_id = review_id.split('#')[0]
                        if review_id and len(review_id) == 24:  # 네이버 리뷰 ID는 보통 24자
                            print(f"✅ 네이버 리뷰 ID 추출 성공 (split 방법): {review_id}")
                            return review_id
            else:
                print("⚠️ 결제 정보 링크를 찾을 수 없음 (영수증이 없는 리뷰)")
            
            # 방법 2: 영수증이 없는 리뷰의 경우 고유 ID 생성
            # 리뷰 작성일 + 사용자 정보 + 리뷰 텍스트로 고유 ID 생성
            import hashlib
            
            # 작성일 추출
            date_element = await review_element.query_selector(".pui__4rEbt5 time")
            date_text = ""
            if date_element:
                date_text = await date_element.text_content()
            
            # 사용자 이름 추출
            reviewer_name = ""
            name_element = await review_element.query_selector(".pui__NMi-Dp")
            if name_element:
                reviewer_name = await name_element.text_content()
            
            # 리뷰 텍스트 추출 (처음 100자)
            review_text = ""
            text_element = await review_element.query_selector("a.pui__xtsQN-")
            if text_element:
                review_text = await text_element.text_content()
                review_text = review_text[:100] if review_text else ""
            
            # 프로필 URL에서 사용자 ID 추출
            user_id = ""
            profile_link = await review_element.query_selector("a[data-pui-click-code='profile']")
            if profile_link:
                href = await profile_link.get_attribute('href')
                if href and '/my/' in href:
                    parts = href.split('/my/')
                    if len(parts) > 1:
                        user_id = parts[1].split('/')[0]
            
            # 고유 ID 생성
            if user_id and (date_text or review_text):
                # 사용자 ID + 날짜 + 리뷰 텍스트 조합
                unique_string = f"{user_id}_{date_text}_{review_text[:50]}"
                review_id = hashlib.md5(unique_string.encode()).hexdigest()[:24]
                print(f"🔧 네이버 리뷰 ID 생성 (영수증 없는 리뷰): {review_id}")
                return review_id
            elif reviewer_name and date_text and review_text:
                # 사용자 이름 + 날짜 + 리뷰 텍스트 조합
                unique_string = f"{reviewer_name}_{date_text}_{review_text[:50]}"
                review_id = hashlib.md5(unique_string.encode()).hexdigest()[:24]
                print(f"🔧 네이버 리뷰 ID 생성 (이름 기반): {review_id}")
                return review_id
            
            # 방법 3: 리뷰 요소의 data 속성 확인
            # 일부 페이지에서는 data-review-id 같은 속성이 있을 수 있음
            data_attrs = await review_element.evaluate("el => Object.keys(el.dataset)")
            for attr in data_attrs:
                if 'review' in attr.lower() or 'id' in attr.lower():
                    value = await review_element.evaluate(f"el => el.dataset['{attr}']")
                    if value:
                        print(f"네이버 리뷰 ID 추출 성공 (data 속성): {value}")
                        return value
            
            # 폴백: 해시 기반 고유 ID 생성
            import hashlib
            text_element = await review_element.query_selector("a.pui__xtsQN-")
            if text_element:
                text_content = await text_element.text_content()
                review_id = hashlib.md5(text_content.encode()).hexdigest()[:24]
                print(f"네이버 리뷰 ID 생성 (텍스트 해시): {review_id}")
                return review_id
            
            # 최종 폴백
            fallback_id = f"review_{int(datetime.now().timestamp() * 1000)}"
            print(f"네이버 리뷰 ID 생성 (타임스탬프): {fallback_id}")
            return fallback_id
            
        except Exception as e:
            print(f"리뷰 ID 추출 중 오류: {str(e)}")
            return f"review_{int(datetime.now().timestamp() * 1000)}"
    
    async def _extract_reviewer_name(self, review_element) -> str:
        """리뷰어 이름만 빠르게 추출 (ID 생성용)"""
        try:
            name_element = await review_element.query_selector(".pui__NMi-Dp")
            if name_element:
                return await name_element.text_content()
            return ""
        except:
            return ""
    
    async def _extract_review_text_for_id(self, review_element) -> str:
        """리뷰 텍스트만 빠르게 추출 (ID 생성용)"""
        try:
            text_element = await review_element.query_selector("a.pui__xtsQN-")
            if text_element:
                return await text_element.text_content()
            return ""
        except:
            return ""
    
    def _extract_number(self, text: str) -> int:
        """텍스트에서 숫자 추출"""
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else 0
    
    def _parse_date(self, date_text: str) -> str:
        """날짜 텍스트 파싱"""
        try:
            # "2025. 8. 5(화)" 형태를 "2025-08-05" 형태로 변환
            import re
            date_match = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', date_text)
            if date_match:
                year, month, day = date_match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            return date_text
            
        except Exception as e:
            print(f"날짜 파싱 중 오류: {str(e)}")
            return date_text
    
    async def _process_review_results(self, reviews: List[Dict], store_id: str, user_id: str) -> Dict:
        """리뷰 결과 처리 및 Supabase reviews_naver 테이블에 저장"""
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
                    'table_used': 'reviews_naver'
                }
            
            # platform_store_id 조회
            platform_store_result = self.supabase.table('platform_stores').select('id').eq('user_id', user_id).eq('platform_store_id', store_id).eq('platform', 'naver').single().execute()
            
            if not platform_store_result.data:
                print(f"platform_stores 테이블에서 store_id {store_id}를 찾을 수 없습니다.")
                return {
                    'success': False,
                    'error': f'Store not found in platform_stores: {store_id}',
                    'reviews_found': reviews_found,
                    'reviews_new': 0,
                    'reviews_updated': 0
                }
            
            platform_store_uuid = platform_store_result.data['id']
            print(f"Platform store UUID: {platform_store_uuid}")
            
            # 기존 리뷰 확인 (중복 방지)
            existing_reviews_result = self.supabase.table('reviews_naver').select('naver_review_id').eq('platform_store_id', platform_store_uuid).execute()
            existing_review_ids = {review['naver_review_id'] for review in existing_reviews_result.data}
            
            print(f"기존 리뷰 수: {len(existing_review_ids)}")
            
            # 새로운 리뷰만 필터링하여 데이터 변환
            new_reviews_data = []
            for review in reviews:
                naver_review_id = review.get('review_id', '')
                
                # 이미 존재하는 리뷰인지 확인
                if naver_review_id in existing_review_ids:
                    print(f"중복 리뷰 건너뛰기: {naver_review_id}")
                    continue
                
                # reviews_naver 테이블 구조에 맞게 데이터 변환 (실제 스키마에 맞춤)
                # 리뷰어 통계에서 레벨 추출
                reviewer_stats = review.get('reviewer_stats', {})
                reviewer_level = f"리뷰 {reviewer_stats.get('review_count', 0)}" if reviewer_stats else None
                
                # 키워드를 JSONB 형식으로 변환
                keywords_list = review.get('keywords', [])
                extracted_keywords_jsonb = json.dumps(keywords_list, ensure_ascii=False) if keywords_list else '[]'
                
                # naver_metadata에 reviewer_stats 포함
                naver_metadata = {
                    'images': review.get('images', []),
                    'keywords': review.get('keywords', []),
                    'has_receipt': review.get('has_receipt', False),
                    'visit_date': review.get('visit_date', ''),
                    'reviewer_profile_url': review.get('reviewer_profile_url', ''),
                    'reviewer_stats': reviewer_stats,  # 여기에 통계 정보 저장
                    'crawled_at': datetime.now().isoformat()
                }
                
                review_data = {
                    'platform_store_id': platform_store_uuid,
                    'naver_review_id': naver_review_id,
                    'naver_review_url': f"https://new.smartplace.naver.com/bizes/place/{store_id}/reviews",
                    'reviewer_name': review.get('reviewer_name', ''),
                    'reviewer_id': review.get('reviewer_profile_url', '').split('/')[-1] if review.get('reviewer_profile_url') else '',
                    'reviewer_level': reviewer_level,  # reviewer_stats 대신 reviewer_level 사용
                    'rating': review.get('rating') if review.get('rating') else None,
                    'review_text': review.get('review_text', ''),
                    'review_date': review.get('created_date', ''),
                    'reply_text': review.get('reply_text'),  # 사업자 답글 텍스트
                    'reply_status': review.get('reply_status'),  # 답글 상태 (pending/completed/None)
                    'has_photos': len(review.get('images', [])) > 0,
                    'photo_count': len(review.get('images', [])),
                    'is_visited_review': review.get('has_receipt', False),  # 영수증 = 방문 인증
                    'extracted_keywords': extracted_keywords_jsonb,  # JSONB 형식
                    'naver_metadata': json.dumps(naver_metadata, ensure_ascii=False),  # JSONB 형식
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
                    'table_used': 'reviews_naver'
                }
            
            # Supabase에 새 리뷰들 일괄 삽입
            print(f"Supabase에 {reviews_new}개의 새 리뷰 저장 중...")
            insert_result = self.supabase.table('reviews_naver').insert(new_reviews_data).execute()
            
            if insert_result.data:
                print(f"성공적으로 {len(insert_result.data)}개의 리뷰를 Supabase에 저장했습니다.")
                
                # platform_stores 테이블의 last_crawled_at 업데이트 (존재하는 컬럼만 사용)
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
                    'reviews_new': reviews_new,
                    'reviews_updated': reviews_updated,
                    'table_used': 'reviews_naver',
                    'platform_store_id': platform_store_uuid
                }
            else:
                raise Exception("Supabase 삽입 결과가 비어있습니다.")
            
        except Exception as e:
            error_msg = f"Supabase 저장 중 오류: {str(e)}"
            print(error_msg)
            
            # platform_stores 업데이트 오류는 무시하고 리뷰 저장 성공 여부만 확인
            if "Could not find the 'naver_last_crawl" in str(e) and reviews_new > 0:
                print("platform_stores 스키마 오류이지만 리뷰 저장은 성공 - success=True 반환")
                return {
                    'success': True,
                    'reviews_found': reviews_found,
                    'reviews_new': reviews_new,
                    'reviews_updated': reviews_updated,
                    'table_used': 'reviews_naver',
                    'platform_store_id': platform_store_uuid,
                    'warning': 'platform_stores 업데이트 실패 (스키마 오류)'
                }
            
            # 오류 발생시 platform_stores 테이블에 오류 정보 기록 (존재하는 컬럼만 사용)
            try:
                if 'platform_store_uuid' in locals():
                    self.supabase.table('platform_stores').update({
                        'last_crawled_at': datetime.now().isoformat()
                    }).eq('id', platform_store_uuid).execute()
            except:
                pass
            
            return {
                'success': False,
                'error': error_msg,
                'reviews_found': reviews_found,
                'reviews_new': 0,
                'reviews_updated': 0
            }

async def main():
    parser = argparse.ArgumentParser(description='네이버 리뷰 크롤링')
    parser.add_argument('--email', required=True, help='네이버 이메일/아이디')
    parser.add_argument('--password', required=True, help='네이버 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID (platform_store_id)')
    parser.add_argument('--user-id', required=True, help='사용자 ID (UUID)')
    parser.add_argument('--days', type=int, default=7, help='크롤링 기간 (일)')
    parser.add_argument('--mode', default='auto', help='실행 모드')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드')
    parser.add_argument('--timeout', type=int, default=30000, help='타임아웃 (ms)')
    parser.add_argument('--force-fresh', action='store_true', help='기존 세션 무시하고 강제 새 로그인')
    
    args = parser.parse_args()
    
    crawler = NaverReviewCrawler(
        headless=args.headless, 
        timeout=args.timeout,
        force_fresh_login=args.force_fresh
    )
    result = await crawler.crawl_reviews(
        args.email, 
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