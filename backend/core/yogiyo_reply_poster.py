#!/usr/bin/env python3
"""
요기요 답글 등록/수정 시스템
DSID 기반 리뷰 재탐색 및 답글 관리
"""

import asyncio
import argparse
import json
import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from backend.services.shared.logger import get_logger
from backend.services.shared.config import settings
from backend.core.yogiyo_dsid_generator import YogiyoDSIDGenerator

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


class YogiyoReplyPoster:
    """요기요 답글 등록/수정 클래스"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.dsid_generator = YogiyoDSIDGenerator()
        self.login_url = "https://ceo.yogiyo.co.kr/login/"
        self.reviews_url = "https://ceo.yogiyo.co.kr/reviews"
        
    async def post_replies(
        self,
        username: str,
        password: str,
        store_id: str,
        review_dsids: List[str],
        reply_texts: List[str]
    ) -> Dict[str, Any]:
        """
        여러 리뷰에 답글 등록
        
        Args:
            username: 로그인 ID
            password: 로그인 비밀번호
            store_id: 플랫폼 매장 ID
            review_dsids: 답글 달 리뷰의 DSID 리스트
            reply_texts: 답글 텍스트 리스트
            
        Returns:
            Dict: 답글 등록 결과
        """
        browser = None
        
        try:
            # Playwright 브라우저 시작
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=settings.HEADLESS_BROWSER if hasattr(settings, 'HEADLESS_BROWSER') else False,
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
                """)
                
                # 1. 로그인 수행
                login_success = await self._login(page, username, password)
                if not login_success:
                    return {
                        "success": False,
                        "message": "로그인 실패",
                        "posted_count": 0
                    }
                
                # 2. 리뷰 페이지 이동
                await self._navigate_to_reviews(page)
                
                # 3. 매장 선택
                store_selected = await self._select_store(page, store_id)
                if not store_selected:
                    return {
                        "success": False,
                        "message": f"매장 선택 실패: {store_id}",
                        "posted_count": 0
                    }
                
                # 4. 각 리뷰에 답글 등록
                posted_count = 0
                failed_dsids = []
                
                for dsid, reply_text in zip(review_dsids, reply_texts):
                    success = await self._post_single_reply(page, dsid, reply_text, store_id)
                    if success:
                        posted_count += 1
                        logger.info(f"답글 등록 성공: DSID {dsid}")
                    else:
                        failed_dsids.append(dsid)
                        logger.error(f"답글 등록 실패: DSID {dsid}")
                    
                    # 잠시 대기
                    await page.wait_for_timeout(2000)
                
                return {
                    "success": True,
                    "message": f"답글 등록 완료: {posted_count}/{len(review_dsids)}개 성공",
                    "posted_count": posted_count,
                    "failed_dsids": failed_dsids
                }
                
        except Exception as e:
            logger.error(f"답글 등록 중 오류 발생: {e}")
            return {
                "success": False,
                "message": str(e),
                "posted_count": 0
            }
        finally:
            if browser:
                await browser.close()
    
    async def _login(self, page: Page, username: str, password: str) -> bool:
        """요기요 로그인"""
        try:
            logger.info("요기요 로그인 시작...")
            
            await page.goto(self.login_url, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            await page.fill('input[name="username"]', username)
            await page.wait_for_timeout(500)
            
            await page.fill('input[name="password"]', password)
            await page.wait_for_timeout(500)
            
            # 로그인 버튼 클릭
            await page.click('div.sc-dkzDqf.gsOnC')
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            if 'login' not in current_url:
                logger.info("로그인 성공")
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
            await page.wait_for_timeout(3000)
            logger.info("리뷰 페이지 이동 완료")
        except Exception as e:
            logger.error(f"리뷰 페이지 이동 실패: {e}")
            raise
    
    async def _select_store(self, page: Page, store_id: str) -> bool:
        """매장 선택"""
        try:
            logger.info(f"매장 선택: {store_id}")
            
            # 드롭다운 클릭
            await page.click('div.StoreSelector__SelectedStore-sc-1rowjsb-13')
            await page.wait_for_timeout(2000)
            
            # 매장 목록 대기
            await page.wait_for_selector('ul.List__VendorList-sc-2ocjy3-8', timeout=10000)
            
            # 매장 선택
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
                await page.wait_for_timeout(3000)
                return True
            else:
                logger.error(f"매장을 찾을 수 없음: {store_id}")
                return False
                
        except Exception as e:
            logger.error(f"매장 선택 중 오류: {e}")
            return False
    
    async def _post_single_reply(self, page: Page, dsid: str, reply_text: str, store_id: str) -> bool:
        """
        개별 리뷰에 답글 등록
        DSID로 리뷰를 찾아서 답글 등록
        """
        try:
            logger.info(f"DSID {dsid}에 답글 등록 시도...")
            
            # 1. 현재 페이지의 모든 리뷰 수집
            reviews = await self._collect_current_page_reviews(page)
            
            # 2. DSID로 타겟 리뷰 찾기
            target_review = self.dsid_generator.find_review_by_dsid(dsid, reviews)
            
            if not target_review:
                # 다음 페이지에서 찾기 시도
                logger.warning(f"현재 페이지에서 DSID {dsid}를 찾을 수 없음. 다음 페이지 검색...")
                
                # 최대 5페이지까지 검색
                for page_num in range(5):
                    has_next = await self._go_to_next_page(page)
                    if not has_next:
                        break
                    
                    reviews = await self._collect_current_page_reviews(page)
                    target_review = self.dsid_generator.find_review_by_dsid(dsid, reviews)
                    
                    if target_review:
                        break
            
            if not target_review:
                logger.error(f"DSID {dsid}에 해당하는 리뷰를 찾을 수 없음")
                return False
            
            # 3. 리뷰 인덱스 기반으로 답글 등록
            review_index = target_review.get('index_hint', 0)
            
            # 댓글쓰기 버튼 클릭
            reply_button_clicked = await page.evaluate(f"""
                () => {{
                    const reviews = document.querySelectorAll('div.ReviewItem__Container-sc-1oxgj67-0');
                    if (reviews.length <= {review_index}) return false;
                    
                    const review = reviews[{review_index}];
                    
                    // 이미 답글이 있는지 확인
                    const existingReply = review.querySelector('div.ReviewReply__ReplyContent-sc-1536a88-7');
                    if (existingReply) {{
                        // 수정 버튼 클릭
                        const editButton = review.querySelector('div.sc-dkzDqf.SIGGG');
                        if (editButton) {{
                            editButton.click();
                            return 'edit';
                        }}
                    }} else {{
                        // 댓글쓰기 버튼 클릭
                        const replyButton = review.querySelector('button.ReviewReply__AddReplyButton-sc-1536a88-10');
                        if (replyButton) {{
                            replyButton.click();
                            return 'new';
                        }}
                    }}
                    
                    return false;
                }}
            """)
            
            if not reply_button_clicked:
                logger.error(f"답글 버튼을 찾을 수 없음: DSID {dsid}")
                return False
            
            await page.wait_for_timeout(1000)
            
            # 답글 텍스트 입력
            textarea_selector = 'textarea.ReviewReply__CustomTextarea-sc-1536a88-5'
            await page.wait_for_selector(textarea_selector, timeout=5000)
            
            # 기존 텍스트 클리어 후 새 텍스트 입력
            await page.fill(textarea_selector, '')
            await page.type(textarea_selector, reply_text)
            await page.wait_for_timeout(500)
            
            # 등록 버튼 클릭
            register_button_selectors = [
                'button:has-text("등록")',
                'div.sc-dkzDqf.cxmxbn',
                'button.sc-bczRLJ.ifUnxI'
            ]
            
            for selector in register_button_selectors:
                try:
                    await page.click(selector)
                    logger.info(f"등록 버튼 클릭 성공: {selector}")
                    break
                except:
                    continue
            
            await page.wait_for_timeout(2000)
            
            # 답글 등록 확인
            reply_posted = await page.evaluate(f"""
                () => {{
                    const reviews = document.querySelectorAll('div.ReviewItem__Container-sc-1oxgj67-0');
                    if (reviews.length <= {review_index}) return false;
                    
                    const review = reviews[{review_index}];
                    const replyContent = review.querySelector('div.ReviewReply__ReplyContent-sc-1536a88-7');
                    
                    return replyContent !== null;
                }}
            """)
            
            if reply_posted:
                # 데이터베이스 업데이트
                await self._update_reply_in_db(dsid, reply_text, store_id)
                logger.info(f"답글 등록 성공: DSID {dsid}")
                return True
            else:
                logger.error(f"답글 등록 확인 실패: DSID {dsid}")
                return False
            
        except Exception as e:
            logger.error(f"답글 등록 중 오류: {e}")
            return False
    
    async def _collect_current_page_reviews(self, page: Page) -> List[Dict[str, Any]]:
        """현재 페이지의 리뷰 데이터 수집 (DSID 생성용)"""
        reviews = []
        
        try:
            # JavaScript로 리뷰 데이터 수집
            page_reviews = await page.evaluate("""
                () => {
                    const reviews = [];
                    const reviewElements = document.querySelectorAll('div.ReviewItem__Container-sc-1oxgj67-0');
                    
                    reviewElements.forEach((element, index) => {
                        const review = {};
                        
                        // 리뷰어 이름
                        const nameElement = element.querySelector('h6.dZvFzq');
                        review.reviewer_name = nameElement ? nameElement.textContent : '익명';
                        
                        // 별점
                        const ratingElement = element.querySelector('h6.cknzqP');
                        review.rating = ratingElement ? parseFloat(ratingElement.textContent) : 0;
                        
                        // 리뷰 날짜
                        const dateElement = element.querySelector('p.jwoVKl');
                        review.review_date = dateElement ? dateElement.textContent : '';
                        
                        // 리뷰 텍스트
                        const textElement = element.querySelector('p.blUkHI');
                        review.review_text = textElement ? textElement.textContent : '';
                        
                        // 주문 메뉴
                        const menuElement = element.querySelector('p.jlzcvj');
                        review.order_menu = menuElement ? menuElement.textContent : '';
                        
                        // 맛/양 별점
                        const tasteGroup = Array.from(element.querySelectorAll('div.tttps')).find(el => el.textContent.includes('맛'));
                        if (tasteGroup) {
                            const tasteValue = tasteGroup.querySelector('p.iAqjFc');
                            review.taste_rating = tasteValue ? parseInt(tasteValue.textContent) : 0;
                        }
                        
                        const quantityGroup = Array.from(element.querySelectorAll('div.tttps')).find(el => el.textContent.includes('양'));
                        if (quantityGroup) {
                            const quantityValue = quantityGroup.querySelector('p.iAqjFc');
                            review.quantity_rating = quantityValue ? parseInt(quantityValue.textContent) : 0;
                        }
                        
                        // 이미지 URL
                        review.image_urls = [];
                        const images = element.querySelectorAll('img.hOzzCg');
                        images.forEach(img => {
                            if (img.src) review.image_urls.push(img.src);
                        });
                        
                        reviews.push(review);
                    });
                    
                    return reviews;
                }
            """)
            
            return page_reviews
            
        except Exception as e:
            logger.error(f"리뷰 수집 중 오류: {e}")
            return []
    
    async def _go_to_next_page(self, page: Page) -> bool:
        """다음 페이지로 이동"""
        try:
            next_button = await page.query_selector('button:has-text("다음")')
            if not next_button:
                next_button = await page.query_selector('button[aria-label="다음 페이지"]')
            
            if next_button:
                is_disabled = await next_button.get_attribute('disabled')
                if is_disabled:
                    return False
                
                await next_button.click()
                await page.wait_for_timeout(2000)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"다음 페이지 이동 실패: {e}")
            return False
    
    async def _update_reply_in_db(self, dsid: str, reply_text: str, store_id: str):
        """데이터베이스에 답글 정보 업데이트"""
        try:
            # 답글 정보 업데이트
            update_data = {
                'owner_reply': reply_text,
                'owner_reply_date': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.supabase.table('yogiyo_reviews').update(update_data).eq('yogiyo_review_id', dsid).execute()
            logger.info(f"DB 업데이트 완료: DSID {dsid}")
            
        except Exception as e:
            logger.error(f"DB 업데이트 실패: {e}")


async def main():
    """테스트용 메인 함수"""
    parser = argparse.ArgumentParser(description='요기요 답글 등록')
    parser.add_argument('--username', required=True, help='요기요 로그인 ID')
    parser.add_argument('--password', required=True, help='요기요 로그인 비밀번호')
    parser.add_argument('--store-id', required=True, help='플랫폼 매장 ID')
    parser.add_argument('--dsids', required=True, help='답글 달 리뷰 DSID (콤마 구분)')
    parser.add_argument('--replies', required=True, help='답글 텍스트 (콤마 구분)')
    
    args = parser.parse_args()
    
    # DSID와 답글 텍스트 파싱
    dsids = args.dsids.split(',')
    replies = args.replies.split('|')  # 답글은 파이프로 구분 (콤마가 내용에 있을 수 있음)
    
    if len(dsids) != len(replies):
        print("DSID 개수와 답글 개수가 일치하지 않습니다.")
        return
    
    poster = YogiyoReplyPoster()
    result = await poster.post_replies(
        username=args.username,
        password=args.password,
        store_id=args.store_id,
        review_dsids=dsids,
        reply_texts=replies
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())