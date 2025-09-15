#!/usr/bin/env python3
"""
요기요 리뷰 크롤러
DSID 기반 리뷰 식별 시스템을 사용한 리뷰 수집
"""

import asyncio
import argparse
import json
import os
import sys
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import hashlib

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from backend.services.shared.logger import get_logger
from backend.services.shared.config import settings
from backend.core.yogiyo_dsid_generator import YogiyoDSIDGenerator
from backend.core.yogiyo_star_rating_extractor import YogiyoStarRatingExtractor

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


class YogiyoReviewCrawler:
    """요기요 리뷰 크롤러 - DSID 기반"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.dsid_generator = YogiyoDSIDGenerator()
        self.star_extractor = YogiyoStarRatingExtractor()
        self.login_url = "https://ceo.yogiyo.co.kr/login/"
        self.reviews_url = "https://ceo.yogiyo.co.kr/reviews"
        
    async def crawl_reviews(
        self,
        username: str,
        password: str,
        store_id: str,
        days: int = 7,
        max_scrolls: int = 10
    ) -> Dict[str, Any]:
        """
        요기요 리뷰 크롤링 메인 함수 (무한 스크롤 방식)
        
        Args:
            username: 로그인 ID
            password: 로그인 비밀번호
            store_id: 플랫폼 매장 ID
            days: 크롤링 기간 (일)
            max_scrolls: 최대 스크롤 횟수
            
        Returns:
            Dict: 크롤링 결과
        """
        browser = None
        
        try:
            # Playwright 브라우저 시작
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,  # 브라우저 창을 표시하여 디버깅 가능
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                
                page = await context.new_page()
                
                # 자동화 감지 방지 스크립트 추가
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
                    Object.defineProperty(navigator, 'permissions', {
                        get: () => ({
                            query: () => Promise.resolve({state: 'granted'})
                        })
                    });
                """)
                
                # 1. 로그인 수행
                login_success = await self._login(page, username, password)
                if not login_success:
                    return {
                        "success": False,
                        "message": "로그인 실패",
                        "reviews": []
                    }
                
                # 2. 리뷰 페이지 이동
                await self._navigate_to_reviews(page)
                
                # 3. 매장 선택
                store_selected = await self._select_store(page, store_id)
                if not store_selected:
                    return {
                        "success": False,
                        "message": f"매장 선택 실패: {store_id}",
                        "reviews": []
                    }
                
                # 4. 리뷰 수집 (무한 스크롤)
                reviews = await self._collect_reviews(page, max_scrolls)
                
                # 5. DSID 생성 및 처리
                processed_reviews = self.dsid_generator.process_review_list(
                    reviews,
                    url=self.reviews_url,
                    sort_option='latest',
                    filter_option='all'
                )
                
                # 6. 데이터베이스 저장
                saved_count = await self._save_reviews_to_db(processed_reviews, store_id)
                
                return {
                    "success": True,
                    "message": f"리뷰 수집 완료: {len(reviews)}개 발견, {saved_count}개 저장",
                    "reviews": processed_reviews,
                    "saved_count": saved_count
                }
                
        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {e}")
            return {
                "success": False,
                "message": str(e),
                "reviews": []
            }
        finally:
            if browser:
                await browser.close()
    
    async def _login(self, page: Page, username: str, password: str) -> bool:
        """요기요 로그인"""
        try:
            logger.info("요기요 로그인 시작...")
            
            # 로그인 페이지로 이동
            await page.goto(self.login_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(1000)  # 2초 -> 1초로 단축

            # ID 입력
            await page.fill('input[name="username"]', username)
            await page.wait_for_timeout(200)  # 500ms -> 200ms로 단축

            # 비밀번호 입력
            await page.fill('input[name="password"]', password)
            await page.wait_for_timeout(200)  # 500ms -> 200ms로 단축

            # 로그인 버튼 클릭 - 정확한 셀렉터 우선 사용
            login_button_selectors = [
                'button[type="submit"]',  # 가장 정확한 셀렉터를 첫 번째로
                'button.sc-bczRLJ.claiZC.sc-eCYdqJ.hsiXYt[type="submit"]',  # 구체적인 클래스
                'button:has-text("로그인")',  # 텍스트 기반 fallback
            ]

            button_clicked = False
            for selector in login_button_selectors:
                try:
                    await page.click(selector, timeout=2000)  # 빠른 타임아웃 설정
                    logger.info(f"로그인 버튼 클릭 성공: {selector}")
                    button_clicked = True
                    break
                except:
                    logger.debug(f"셀렉터 실패: {selector}")
                    continue

            if not button_clicked:
                logger.error("로그인 버튼을 찾을 수 없습니다")
                return False

            # 로그인 완료 대기 (페이지 이동 감지)
            try:
                await page.wait_for_url(lambda url: 'login' not in url, timeout=5000)
                logger.info("로그인 성공 - 페이지 이동 감지")
            except:
                # URL 변경이 없어도 일단 대기
                await page.wait_for_timeout(2000)  # 3초 -> 2초로 단축
            
            # 로그인 성공 확인
            current_url = page.url
            if 'login' not in current_url:
                logger.info(f"로그인 성공 (URL: {current_url})")
                return True
            else:
                logger.error("로그인 실패")
                return False
                
        except Exception as e:
            logger.error(f"로그인 중 오류: {e}")
            return False
    
    async def _navigate_to_reviews(self, page: Page):
        """리뷰 페이지로 이동"""
        try:
            logger.info("리뷰 페이지로 이동 중...")
            await page.goto(self.reviews_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(1500)  # 3초 -> 1.5초로 단축
            logger.info("리뷰 페이지 이동 완료")
        except Exception as e:
            logger.error(f"리뷰 페이지 이동 실패: {e}")
            raise
    
    async def _select_store(self, page: Page, store_id: str) -> bool:
        """매장 선택"""
        try:
            logger.info(f"매장 선택: {store_id}")
            
            # 드롭다운 클릭
            dropdown_selectors = [
                'div.StoreSelector__SelectedStore-sc-1rowjsb-13',
                'button.StoreSelector__DropdownButton-sc-1rowjsb-11',
                'div[role="menu"]'
            ]
            
            for selector in dropdown_selectors:
                try:
                    await page.click(selector)
                    logger.info(f"드롭다운 클릭 성공: {selector}")
                    break
                except:
                    continue
            
            await page.wait_for_timeout(1000)  # 2초 -> 1초로 단축

            # 매장 목록 대기
            await page.wait_for_selector('ul.List__VendorList-sc-2ocjy3-8', timeout=5000)  # 10초 -> 5초로 단축
            
            # 매장 선택 (platform_store_id 기준)
            store_selected = await page.evaluate(f"""
                () => {{
                    const storeElements = document.querySelectorAll('li.List__Vendor-sc-2ocjy3-7');
                    
                    for (const element of storeElements) {{
                        const idElement = element.querySelector('span.List__VendorID-sc-2ocjy3-1');
                        if (idElement) {{
                            const storeIdText = idElement.textContent.trim();
                            const storeId = storeIdText.replace('ID.', '').trim();
                            
                            if (storeId === '{store_id}') {{
                                element.click();
                                return true;
                            }}
                        }}
                    }}
                    
                    return false;
                }}
            """)
            
            if store_selected:
                logger.info(f"매장 선택 완료: {store_id}")
                await page.wait_for_timeout(1500)  # 3초 -> 1.5초로 단축
                
                # 미답변 탭 클릭
                unanswered_clicked = await self._click_unanswered_tab(page)
                if unanswered_clicked:
                    logger.info("미답변 탭 클릭 완료")
                else:
                    logger.warning("미답변 탭 클릭 실패 - 전체 리뷰에서 크롤링")
                
                return True
            else:
                logger.error(f"매장을 찾을 수 없음: {store_id}")
                return False
                
        except Exception as e:
            logger.error(f"매장 선택 중 오류: {e}")
            return False
    
    async def _click_unanswered_tab(self, page: Page) -> bool:
        """미답변 탭 클릭"""
        try:
            # 미답변 탭 셀렉터들
            unanswered_selectors = [
                'li:has-text("미답변")',
                'li.InnerTab__TabItem-sc-14s9mjy-0:has-text("미답변")',
                'li.expvkr:has-text("미답변")',
                'li.hWCMEW:has-text("미답변")',
                '[class*="TabItem"]:has-text("미답변")',
                '[class*="InnerTab"]:has-text("미답변")'
            ]
            
            for selector in unanswered_selectors:
                try:
                    # 탭이 존재하는지 확인
                    tab_element = await page.query_selector(selector)
                    if tab_element:
                        # 탭 텍스트 확인
                        tab_text = await tab_element.inner_text()
                        logger.debug(f"탭 발견: {tab_text}")
                        
                        # 미답변 탭인지 확인하고 클릭
                        if '미답변' in tab_text:
                            await tab_element.click()
                            await page.wait_for_timeout(2000)
                            
                            # 클릭 후 페이지 변화 확인
                            await page.wait_for_load_state('networkidle', timeout=5000)
                            
                            logger.info(f"미답변 탭 클릭 성공: {tab_text}")
                            return True
                except Exception as e:
                    logger.debug(f"셀렉터 {selector} 시도 실패: {e}")
                    continue
            
            # JavaScript로 직접 시도
            logger.debug("JavaScript로 미답변 탭 클릭 시도")
            clicked = await page.evaluate("""
                () => {
                    // 모든 li 요소에서 "미답변"이 포함된 요소 찾기
                    const tabs = document.querySelectorAll('li');
                    for (const tab of tabs) {
                        if (tab.textContent && tab.textContent.includes('미답변')) {
                            tab.click();
                            return true;
                        }
                    }
                    
                    // 클래스명으로도 시도
                    const tabElements = document.querySelectorAll('[class*="TabItem"], [class*="InnerTab"]');
                    for (const tab of tabElements) {
                        if (tab.textContent && tab.textContent.includes('미답변')) {
                            tab.click();
                            return true;
                        }
                    }
                    
                    return false;
                }
            """)
            
            if clicked:
                await page.wait_for_timeout(2000)
                logger.info("JavaScript로 미답변 탭 클릭 성공")
                return True
            
            logger.warning("미답변 탭을 찾을 수 없습니다.")
            return False
            
        except Exception as e:
            logger.error(f"미답변 탭 클릭 중 오류: {e}")
            return False
    
    async def _collect_reviews(self, page: Page, max_scrolls: int) -> List[Dict[str, Any]]:
        """무한 스크롤을 통한 리뷰 수집"""
        all_reviews = []
        previous_review_count = 0
        no_new_reviews_count = 0
        max_no_new_reviews = 3  # 연속으로 새 리뷰가 없을 때까지의 최대 시도 횟수
        
        try:
            for scroll_count in range(max_scrolls):
                logger.info(f"스크롤 {scroll_count + 1}/{max_scrolls} 진행 중...")
                
                # 현재 페이지의 모든 리뷰 추출
                current_reviews = await self._extract_reviews_from_page(page)
                logger.info(f"현재 페이지에서 {len(current_reviews)}개 리뷰 발견")
                
                # 새로운 리뷰가 있는지 확인 (중복 제거)
                new_reviews = []
                for review in current_reviews:
                    # DSID나 기본 식별자로 중복 체크
                    review_identifier = f"{review.get('reviewer_name', '')}_{review.get('review_date', '')}_{review.get('review_text', '')[:50]}"
                    
                    is_duplicate = False
                    for existing_review in all_reviews:
                        existing_identifier = f"{existing_review.get('reviewer_name', '')}_{existing_review.get('review_date', '')}_{existing_review.get('review_text', '')[:50]}"
                        if review_identifier == existing_identifier:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        new_reviews.append(review)
                
                all_reviews.extend(new_reviews)
                logger.info(f"새로 추가된 리뷰: {len(new_reviews)}개, 총 리뷰: {len(all_reviews)}개")
                
                # 새로운 리뷰가 없으면 카운트 증가
                if len(new_reviews) == 0:
                    no_new_reviews_count += 1
                    if no_new_reviews_count >= max_no_new_reviews:
                        logger.info("더 이상 새로운 리뷰가 없어 스크롤을 중단합니다.")
                        break
                else:
                    no_new_reviews_count = 0  # 새 리뷰가 있으면 카운트 리셋
                
                # 마지막 스크롤이 아니면 스크롤 다운 실행
                if scroll_count < max_scrolls - 1:
                    scroll_success = await self._scroll_to_load_more_reviews(page)
                    if not scroll_success:
                        logger.info("더 이상 스크롤할 수 없어 수집을 중단합니다.")
                        break
                    
                    # 스크롤 후 로딩 대기
                    await page.wait_for_timeout(3000)
                
        except Exception as e:
            logger.error(f"무한 스크롤 리뷰 수집 중 오류: {e}")
            
        logger.info(f"무한 스크롤 완료 - 총 {len(all_reviews)}개 리뷰 수집")
        return all_reviews
    
    async def _extract_reviews_from_page(self, page: Page) -> List[Dict[str, Any]]:
        """현재 페이지에서 리뷰 추출"""
        reviews = []
        skipped_replied_reviews = 0
        
        try:
            # 리뷰 컨테이너 찾기
            review_containers = await page.query_selector_all('div.ReviewItem__Container-sc-1oxgj67-0')
            
            if not review_containers:
                # 백업 셀렉터
                review_containers = await page.query_selector_all('div[class*="ReviewItem"]')
            
            logger.info(f"리뷰 컨테이너 {len(review_containers)}개 발견")
            
            for i, container in enumerate(review_containers):
                try:
                    review_data = await self._extract_single_review(container, i + 1)
                    if review_data:
                        reviews.append(review_data)
                    else:
                        # None이 반환된 경우는 이미 답글이 있어서 스킵된 경우
                        skipped_replied_reviews += 1
                except Exception as e:
                    logger.error(f"리뷰 {i+1} 추출 실패: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"페이지 리뷰 추출 실패: {e}")
        
        # 추출 결과 로깅
        total_containers = len(review_containers) if 'review_containers' in locals() else 0
        logger.info(f"페이지 추출 완료 - 전체: {total_containers}개, 수집: {len(reviews)}개, 답글있어서 스킵: {skipped_replied_reviews}개")
        
        return reviews
    
    async def _extract_single_review(self, review_element, review_number: int) -> Optional[Dict[str, Any]]:
        """개별 리뷰 데이터 추출 (이미 답변된 리뷰는 스킵)"""
        try:
            logger.debug(f"리뷰 {review_number} 추출 시작...")
            
            # 먼저 이미 답변된 리뷰인지 확인
            has_owner_reply = await self._check_if_review_has_reply(review_element)
            if has_owner_reply:
                logger.info(f"리뷰 {review_number}: 이미 사장님 답글이 있어 스킵합니다.")
                return None
            
            # 리뷰어 이름
            reviewer_name = ""
            reviewer_element = await review_element.query_selector('h6.Typography__StyledTypography-sc-r9ksfy-0.dZvFzq')
            if reviewer_element:
                reviewer_name = await reviewer_element.inner_text()
            
            # 전체 별점
            rating = 0.0
            rating_element = await review_element.query_selector('h6.Typography__StyledTypography-sc-r9ksfy-0.cknzqP')
            if rating_element:
                rating_text = await rating_element.inner_text()
                try:
                    rating = float(rating_text)
                except:
                    pass
            
            # 맛/양 별점 (SVG 분석 필요)
            taste_rating = await self._extract_sub_rating(review_element, '맛')
            quantity_rating = await self._extract_sub_rating(review_element, '양')
            
            # 리뷰 날짜
            review_date = ""
            date_element = await review_element.query_selector('p.Typography__StyledTypography-sc-r9ksfy-0.jwoVKl')
            if date_element:
                review_date = await date_element.inner_text()
                # 상대시간 변환
                review_date = self._convert_relative_time(review_date)
            
            # 리뷰 텍스트
            review_text = ""
            text_element = await review_element.query_selector('p.ReviewItem__CommentTypography-sc-1oxgj67-3.blUkHI')
            if not text_element:
                text_element = await review_element.query_selector('p.Typography__StyledTypography-sc-r9ksfy-0.hLRURJ')
            if text_element:
                review_text = await text_element.inner_text()
            
            # 주문 메뉴
            order_menu = ""
            menu_element = await review_element.query_selector('p.Typography__StyledTypography-sc-r9ksfy-0.jlzcvj')
            if menu_element:
                order_menu = await menu_element.inner_text()
            
            # 리뷰 이미지
            image_urls = []
            image_elements = await review_element.query_selector_all('img.ReviewItem__Image-sc-1oxgj67-1.hOzzCg')
            for img in image_elements:
                src = await img.get_attribute('src')
                if src:
                    image_urls.append(src)
            
            # 사장님 답글 확인
            owner_reply = None  # 기본값을 None으로 설정 (DB에 null로 저장됨)
            reply_element = await review_element.query_selector('div.ReviewReply__ReplyContent-sc-1536a88-7')
            if reply_element:
                reply_text = await reply_element.inner_text()
                # 답글이 실제로 있는 경우만 저장
                if reply_text and reply_text.strip():
                    owner_reply = reply_text.strip()
            
            review_data = {
                'reviewer_name': reviewer_name or '익명',
                'rating': rating,
                'taste_rating': taste_rating,
                'quantity_rating': quantity_rating,
                'review_text': review_text,
                'review_date': review_date,
                'order_menu': order_menu,
                'image_urls': image_urls,
                'owner_reply': owner_reply,
                'has_photos': len(image_urls) > 0,
                'yogiyo_metadata': {
                    'extracted_at': datetime.now().isoformat(),
                    'review_number': review_number
                }
            }
            
            logger.info(f"리뷰 {review_number} 추출 완료: {reviewer_name} ({rating}점, {review_date})")
            
            return review_data
            
        except Exception as e:
            logger.error(f"개별 리뷰 추출 실패: {e}")
            return None
    
    async def _check_if_review_has_reply(self, review_element) -> bool:
        """리뷰에 이미 사장님 답글이 있는지 확인"""
        try:
            # 1차: 사장님 답글 컨테이너가 있는지 확인 (가장 정확한 방법)
            # 사용자가 제공한 HTML 구조: ReviewReply__Reply-sc-1536a88-1
            reply_selectors = [
                'div.ReviewReply__Reply-sc-1536a88-1',
                'div[class*="ReviewReply__Reply"]',
                'div.ReviewReply__ReplyContent-sc-1536a88-7',
                'div[class*="ReviewReply__ReplyContent"]',
            ]
            
            for selector in reply_selectors:
                reply_element = await review_element.query_selector(selector)
                if reply_element:
                    # 답글 내용이 실제로 있는지 확인
                    reply_text = await reply_element.inner_text()
                    reply_text = reply_text.strip()
                    
                    if reply_text and len(reply_text) > 5:  # 최소 5글자 이상
                        logger.debug(f"사장님 답글 발견: {reply_text[:50]}...")
                        return True
            
            # 2차: "댓글쓰기" 버튼 없이 답글이 표시된 경우 확인
            # 답글이 있으면 "댓글쓰기" 버튼이 "답글 수정" 등으로 바뀔 수 있음
            reply_buttons = await review_element.query_selector_all('button')
            for button in reply_buttons:
                try:
                    button_text = await button.inner_text()
                    if button_text and ("답글 수정" in button_text or "답글 삭제" in button_text):
                        logger.debug(f"답글 수정/삭제 버튼 발견: {button_text}")
                        return True
                except:
                    continue
            
            # 3차: 실제 사장님 답글 텍스트 패턴 확인 (매우 보수적으로)
            all_text = await review_element.inner_text()
            # 명확한 사장님 답글 패턴만 확인
            owner_reply_patterns = [
                "사장님 답글:",
                "매장 답글:",
                "사장님이 답글",
                "매장에서 답글",
                "Owner Reply:",
                "Store Reply:"
            ]
            
            for pattern in owner_reply_patterns:
                if pattern in all_text:
                    logger.debug(f"사장님 답글 패턴 발견: {pattern}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"답글 확인 중 오류: {e}")
            # 오류가 발생하면 안전하게 False 반환 (리뷰를 건너뛰지 않음)
            return False
    
    async def _extract_sub_rating(self, review_element, rating_type: str) -> int:
        """맛/양 별점 추출"""
        try:
            # 맛 또는 양 컨테이너 찾기
            rating_containers = await review_element.query_selector_all('div.RatingGroup___StyledDiv3-sc-pty1mk-3.tttps')
            
            for container in rating_containers:
                label_text = await container.inner_text()
                if rating_type in label_text:
                    # SVG 분석으로 별점 계산
                    svg_elements = await container.query_selector_all('svg')
                    filled_count = 0
                    
                    for svg in svg_elements:
                        svg_html = await svg.inner_html()
                        # 채워진 별 확인 (노란색)
                        if 'hsla(45, 100%, 59%, 1)' in svg_html or '#FFC400' in svg_html:
                            filled_count += 1
                    
                    return filled_count
            
            return 0
            
        except Exception as e:
            logger.error(f"{rating_type} 별점 추출 실패: {e}")
            return 0
    
    def _convert_relative_time(self, time_str: str) -> str:
        """상대 시간을 절대 날짜로 변환"""
        if not time_str:
            return ""
        
        # 이미 날짜 형식인 경우
        if re.match(r'\d{4}\.\d{2}\.\d{2}', time_str):
            return time_str
        
        now = datetime.now()
        
        # 패턴 매칭
        patterns = {
            r'(\d+)시간 전': lambda m: now - timedelta(hours=int(m.group(1))),
            r'(\d+)분 전': lambda m: now - timedelta(minutes=int(m.group(1))),
            r'(\d+)일 전': lambda m: now - timedelta(days=int(m.group(1))),
            r'어제': lambda m: now - timedelta(days=1),
            r'오늘': lambda m: now,
        }
        
        for pattern, converter in patterns.items():
            match = re.match(pattern, time_str)
            if match:
                result_date = converter(match)
                return result_date.strftime('%Y.%m.%d')
        
        return time_str
    
    async def _scroll_to_load_more_reviews(self, page: Page) -> bool:
        """무한 스크롤을 통해 더 많은 리뷰 로드"""
        try:
            # 현재 페이지 높이 확인
            previous_height = await page.evaluate("document.body.scrollHeight")
            
            # 페이지 끝까지 스크롤
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # 스크롤 후 로딩 대기 (더 긴 대기 시간)
            await page.wait_for_timeout(3000)
            
            # 새로운 콘텐츠가 로드되었는지 확인
            new_height = await page.evaluate("document.body.scrollHeight")
            
            if new_height > previous_height:
                logger.debug(f"스크롤 성공: {previous_height} → {new_height}")
                
                # "더보기" 버튼이 있다면 클릭 시도
                await self._try_click_load_more_button(page)
                
                return True
            else:
                logger.debug("더 이상 로드할 콘텐츠가 없습니다.")
                return False
                
        except Exception as e:
            logger.error(f"스크롤 실행 중 오류: {e}")
            return False
    
    async def _try_click_load_more_button(self, page: Page) -> bool:
        """더보기 버튼이 있으면 클릭"""
        try:
            # 요기요에서 사용할 수 있는 "더보기" 버튼 셀렉터들
            load_more_selectors = [
                'button:has-text("더보기")',
                'button:has-text("더 보기")',
                'button:has-text("리뷰 더보기")',
                '.load-more-button',
                '.more-reviews-btn',
                '[data-testid="load-more"]'
            ]
            
            for selector in load_more_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        # 버튼이 보이고 클릭 가능한지 확인
                        is_visible = await button.is_visible()
                        is_enabled = await button.is_enabled()
                        
                        if is_visible and is_enabled:
                            await button.click()
                            logger.debug(f"더보기 버튼 클릭 성공: {selector}")
                            await page.wait_for_timeout(2000)
                            return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"더보기 버튼 클릭 시도 중 오류: {e}")
            return False
    
    async def _save_reviews_to_db(self, reviews: List[Dict], store_id: str) -> int:
        """리뷰를 데이터베이스에 저장"""
        saved_count = 0
        
        try:
            # 매장 UUID 조회
            store_response = self.supabase.table('platform_stores').select('*').eq('platform_store_id', store_id).execute()
            
            if not store_response.data:
                logger.error(f"매장을 찾을 수 없음: {store_id}")
                return 0
            
            store_uuid = store_response.data[0]['id']
            
            for review in reviews:
                try:
                    # 리뷰 데이터 준비 (reviews_yogiyo 테이블 스키마에 맞춤)
                    review_data = {
                        'platform_store_id': store_uuid,
                        'yogiyo_dsid': review['dsid'],  # DSID를 리뷰 ID로 사용
                        'reviewer_name': review.get('reviewer_name', '익명'),
                        'overall_rating': review.get('rating', 0.0),
                        'taste_rating': review.get('taste_rating', 0),
                        'quantity_rating': review.get('quantity_rating', 0),
                        'review_text': review.get('review_text', ''),
                        'review_date': review.get('review_date', ''),
                        'order_menu': review.get('order_menu', ''),
                        'photo_urls': review.get('image_urls', []),
                        'has_photos': review.get('has_photos', False),
                        'reply_text': review.get('owner_reply'),  # None을 유지하여 DB에 null로 저장
                        
                        # DSID 관련 필드
                        'content_hash': review.get('content_hash', ''),
                        'rolling_hash': review.get('rolling_hash', ''),
                        'neighbor_hash': review.get('neighbor_hash', ''),
                        'page_salt': review.get('page_salt', ''),
                        'index_hint': review.get('index_hint', 0),
                        
                        # 메타데이터
                        'yogiyo_metadata': review.get('yogiyo_metadata', {})
                    }
                    
                    # 중복 체크 후 저장
                    existing = self.supabase.table('reviews_yogiyo').select('id').eq('yogiyo_dsid', review['dsid']).execute()
                    
                    if not existing.data:
                        self.supabase.table('reviews_yogiyo').insert(review_data).execute()
                        saved_count += 1
                        logger.info(f"리뷰 저장: {review['reviewer_name']} (DSID: {review['dsid']})")
                    else:
                        logger.info(f"중복 리뷰 건너뛰기: {review['reviewer_name']} (DSID: {review['dsid']})")
                        
                except Exception as e:
                    logger.error(f"리뷰 저장 실패: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"데이터베이스 저장 중 오류: {e}")
            
        return saved_count


async def main():
    """테스트용 메인 함수"""
    parser = argparse.ArgumentParser(description='요기요 리뷰 크롤러')
    parser.add_argument('--username', required=True, help='요기요 로그인 ID')
    parser.add_argument('--password', required=True, help='요기요 로그인 비밀번호')
    parser.add_argument('--store-id', required=True, help='플랫폼 매장 ID')
    parser.add_argument('--days', type=int, default=7, help='크롤링 기간 (일)')
    parser.add_argument('--max-scrolls', type=int, default=10, help='최대 스크롤 횟수')
    
    args = parser.parse_args()
    
    crawler = YogiyoReviewCrawler()
    result = await crawler.crawl_reviews(
        username=args.username,
        password=args.password,
        store_id=args.store_id,
        days=args.days,
        max_scrolls=args.max_scrolls
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())