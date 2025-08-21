#!/usr/bin/env python3
"""
쿠팡잇츠 답글 포스터
리뷰에 자동으로 답글을 등록하는 시스템
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from playwright.async_api import async_playwright, Page

from backend.services.shared.logger import get_logger
from backend.services.shared.config import settings

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

class CoupangReplyPoster:
    """쿠팡잇츠 답글 포스터"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
    async def post_replies(
        self,
        username: str,
        password: str,
        store_id: str,
        max_replies: int = 10,
        test_mode: bool = False
    ) -> Dict[str, Any]:
        """
        쿠팡잇츠 답글 포스팅 메인 함수
        
        Args:
            username: 로그인 ID
            password: 로그인 비밀번호
            store_id: 플랫폼 매장 ID
            max_replies: 최대 답글 수
            test_mode: 테스트 모드 (실제로 답글을 등록하지 않음)
            
        Returns:
            Dict: 답글 포스팅 결과
        """
        browser = None
        
        try:
            # 답글이 필요한 리뷰 조회
            pending_reviews = await self._get_pending_replies(store_id, max_replies)
            if not pending_reviews:
                return {
                    "success": True,
                    "message": "답글이 필요한 리뷰가 없습니다.",
                    "posted_replies": []
                }
                
            logger.info(f"답글이 필요한 리뷰: {len(pending_reviews)}개")
            
            # Playwright 브라우저 시작
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=settings.HEADLESS_BROWSER if hasattr(settings, 'HEADLESS_BROWSER') else False,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1366, "height": 768}
                )
                
                page = await context.new_page()
                
                # 1. 로그인 수행
                login_success = await self._login(page, username, password)
                if not login_success:
                    return {
                        "success": False,
                        "message": "로그인 실패",
                        "posted_replies": []
                    }
                
                # 2. 리뷰 페이지 이동
                await self._navigate_to_reviews_page(page)
                
                # 3. 매장 선택
                await self._select_store(page, store_id)
                
                # 4. 답글 포스팅
                posted_replies = []
                for review in pending_reviews:
                    try:
                        result = await self._post_single_reply(page, review, test_mode)
                        if result:
                            posted_replies.append(result)
                            
                    except Exception as e:
                        logger.error(f"답글 포스팅 실패: {review['coupangeats_review_id']} - {e}")
                        continue
                
                return {
                    "success": True,
                    "message": f"답글 포스팅 완료: {len(posted_replies)}개",
                    "posted_replies": posted_replies
                }
                
        except Exception as e:
            logger.error(f"Reply posting failed: {e}")
            return {
                "success": False,
                "message": f"답글 포스팅 실패: {str(e)}",
                "posted_replies": []
            }
        finally:
            if browser:
                await browser.close()
    
    async def _login(self, page: Page, username: str, password: str) -> bool:
        """로그인 수행"""
        try:
            logger.info("쿠팡잇츠 로그인 시작...")
            
            # 로그인 페이지 이동
            await page.goto("https://store.coupangeats.com/merchant/login", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # 로그인 정보 입력
            await page.fill('#loginId', username)
            await page.fill('#password', password)
            
            # 로그인 버튼 클릭
            await page.click('button[type="submit"]')
            
            # 결과 대기
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            logger.info(f"로그인 후 URL: {current_url}")
            
            # 로그인 성공 확인
            if "login" not in current_url:
                logger.info("로그인 성공")
                return True
            else:
                logger.error("로그인 실패")
                return False
                
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            return False
    
    async def _navigate_to_reviews_page(self, page: Page):
        """리뷰 페이지로 이동"""
        try:
            logger.info("리뷰 페이지로 이동...")
            await page.goto("https://store.coupangeats.com/merchant/management/reviews", 
                          wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            logger.info("리뷰 페이지 이동 완료")
            
        except Exception as e:
            logger.error(f"리뷰 페이지 이동 실패: {e}")
            raise
    
    async def _select_store(self, page: Page, store_id: str):
        """매장 선택"""
        try:
            logger.info(f"매장 선택: {store_id}")
            
            # 드롭다운 버튼 클릭
            dropdown_button = await page.query_selector('.button:has(svg)')
            if dropdown_button:
                await dropdown_button.click()
                await page.wait_for_timeout(1000)
                
                # 매장 목록에서 해당 store_id 찾기
                store_options = await page.query_selector_all('.options li')
                
                for option in store_options:
                    option_text = await option.inner_text()
                    if f"({store_id})" in option_text:
                        await option.click()
                        logger.info(f"매장 선택 완료: {option_text}")
                        await page.wait_for_timeout(1000)
                        return
                        
        except Exception as e:
            logger.error(f"매장 선택 실패: {e}")
    
    async def _post_single_reply(
        self, 
        page: Page, 
        review: Dict[str, Any], 
        test_mode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """개별 답글 포스팅"""
        try:
            review_id = review['coupangeats_review_id']
            reviewer_name = review['reviewer_name']
            
            logger.info(f"답글 포스팅 시작: {reviewer_name} (ID: {review_id})")
            
            # 리뷰 찾기 (reviewer_name과 review_text로 매칭)
            review_element = await self._find_review_element(page, review)
            if not review_element:
                logger.warning(f"리뷰 요소를 찾을 수 없습니다: {review_id}")
                return None
            
            # 답글 등록 버튼 찾기
            reply_button = await review_element.query_selector('button:has-text("사장님 댓글 등록하기")')
            if not reply_button:
                # 이미 답글이 있는 경우 수정 버튼 찾기
                edit_button = await review_element.query_selector('button:has-text("수정")')
                if edit_button:
                    return await self._edit_existing_reply(page, review_element, review, test_mode)
                else:
                    logger.warning(f"답글 등록/수정 버튼을 찾을 수 없습니다: {review_id}")
                    return None
            
            # 답글 등록 버튼 클릭
            await reply_button.click()
            await page.wait_for_timeout(1000)
            
            # 텍스트 박스 찾기
            textarea = await page.query_selector('textarea[name="review"]')
            if not textarea:
                logger.error(f"답글 입력 텍스트박스를 찾을 수 없습니다: {review_id}")
                return None
            
            # 답글 텍스트 생성
            reply_text = await self._generate_reply_text(review)
            
            if test_mode:
                logger.info(f"[TEST MODE] 답글 내용: {reply_text}")
                return {
                    "review_id": review['review_id'],
                    "reviewer_name": reviewer_name,
                    "reply_text": reply_text,
                    "status": "test_mode"
                }
            
            # 답글 입력
            await textarea.fill(reply_text)
            await page.wait_for_timeout(500)
            
            # 등록 버튼 클릭
            submit_button = await page.query_selector('span:has-text("등록")')
            if submit_button:
                submit_button_parent = await submit_button.query_selector('xpath=..')
                await submit_button_parent.click()
                await page.wait_for_timeout(2000)
                
                # 답글 상태 업데이트
                await self._update_reply_status(
                    review['review_id'], 
                    'sent', 
                    reply_text
                )
                
                logger.info(f"답글 등록 완료: {reviewer_name}")
                
                return {
                    "review_id": review['review_id'],
                    "reviewer_name": reviewer_name,
                    "reply_text": reply_text,
                    "status": "posted"
                }
            else:
                logger.error(f"등록 버튼을 찾을 수 없습니다: {review_id}")
                return None
                
        except Exception as e:
            logger.error(f"답글 포스팅 실패: {review['coupangeats_review_id']} - {e}")
            
            # 에러 상태 업데이트
            await self._update_reply_status(
                review['review_id'],
                'failed',
                error_message=str(e)
            )
            return None
    
    async def _find_review_element(self, page: Page, review: Dict[str, Any]):
        """페이지에서 특정 리뷰 요소 찾기"""
        try:
            # 리뷰어 이름으로 먼저 찾기
            reviewer_elements = await page.query_selector_all(f'b:has-text("{review["reviewer_name"]}")')
            
            for element in reviewer_elements:
                # 상위 리뷰 컨테이너 찾기
                review_container = element
                for _ in range(10):  # 최대 10단계 위로 올라가며 찾기
                    review_container = await review_container.query_selector('xpath=..')
                    if not review_container:
                        break
                    
                    # 리뷰 텍스트 매칭 확인
                    review_text_element = await review_container.query_selector('.css-16m6tj.eqn7l9b5')
                    if review_text_element:
                        page_review_text = await review_text_element.inner_text()
                        if review['review_text'] and review['review_text'].strip() in page_review_text:
                            return review_container
                        elif not review['review_text']:  # 텍스트가 없는 리뷰인 경우
                            return review_container
                            
            return None
            
        except Exception as e:
            logger.error(f"리뷰 요소 찾기 실패: {e}")
            return None
    
    async def _edit_existing_reply(
        self,
        page: Page,
        review_element,
        review: Dict[str, Any],
        test_mode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """기존 답글 수정"""
        try:
            review_id = review['coupangeats_review_id']
            
            logger.info(f"기존 답글 수정: {review_id}")
            
            # 수정 버튼 클릭
            edit_button = await review_element.query_selector('button:has-text("수정")')
            await edit_button.click()
            await page.wait_for_timeout(1000)
            
            # 수정용 텍스트박스 찾기
            textarea = await page.query_selector('textarea[name="review"]')
            if not textarea:
                logger.error(f"수정용 텍스트박스를 찾을 수 없습니다: {review_id}")
                return None
            
            # 새 답글 텍스트 생성
            reply_text = await self._generate_reply_text(review)
            
            if test_mode:
                logger.info(f"[TEST MODE] 수정할 답글 내용: {reply_text}")
                return {
                    "review_id": review['review_id'],
                    "reviewer_name": review['reviewer_name'],
                    "reply_text": reply_text,
                    "status": "test_mode_edit"
                }
            
            # 기존 텍스트 지우고 새 텍스트 입력
            await textarea.fill(reply_text)
            await page.wait_for_timeout(500)
            
            # 수정 버튼 클릭
            submit_button = await page.query_selector('span:has-text("수정")')
            if submit_button:
                submit_button_parent = await submit_button.query_selector('xpath=..')
                await submit_button_parent.click()
                await page.wait_for_timeout(2000)
                
                # 답글 상태 업데이트
                await self._update_reply_status(
                    review['review_id'],
                    'sent',
                    reply_text
                )
                
                logger.info(f"답글 수정 완료: {review['reviewer_name']}")
                
                return {
                    "review_id": review['review_id'],
                    "reviewer_name": review['reviewer_name'],
                    "reply_text": reply_text,
                    "status": "edited"
                }
            else:
                logger.error(f"수정 완료 버튼을 찾을 수 없습니다: {review_id}")
                return None
                
        except Exception as e:
            logger.error(f"답글 수정 실패: {review['coupangeats_review_id']} - {e}")
            return None
    
    async def _generate_reply_text(self, review: Dict[str, Any]) -> str:
        """답글 텍스트 생성"""
        rating = review.get('rating', 5)
        reviewer_name = review.get('reviewer_name', '고객')
        
        # 별점에 따른 답글 템플릿
        if rating >= 4:
            templates = [
                f"{reviewer_name}님, 좋은 리뷰 감사합니다! 항상 맛있는 음식으로 보답하겠습니다.",
                f"{reviewer_name}님께서 만족해 주셔서 정말 기쁩니다. 다음에도 찾아주세요!",
                f"감사한 리뷰 남겨주신 {reviewer_name}님! 앞으로도 최선을 다하겠습니다.",
            ]
        elif rating == 3:
            templates = [
                f"{reviewer_name}님, 리뷰 감사드립니다. 더 나은 서비스로 보답하겠습니다.",
                f"{reviewer_name}님의 소중한 의견 감사합니다. 개선하여 더 좋은 모습 보여드릴게요.",
            ]
        else:
            templates = [
                f"{reviewer_name}님, 불편을 끼쳐드려 죄송합니다. 앞으로 더욱 주의하겠습니다.",
                f"{reviewer_name}님께 실망을 드려 정말 죄송합니다. 개선하여 더 나은 서비스 제공하겠습니다.",
            ]
        
        import random
        return random.choice(templates)
    
    async def _get_pending_replies(self, store_id: str, limit: int) -> List[Dict[str, Any]]:
        """답글이 필요한 리뷰 조회"""
        try:
            # platform_stores에서 user_id 조회
            store_response = self.supabase.table('platform_stores').select('user_id').eq('platform_store_id', store_id).eq('platform', 'coupangeats').execute()
            
            if not store_response.data:
                logger.error(f"매장을 찾을 수 없습니다: {store_id}")
                return []
            
            user_id = store_response.data[0]['user_id']
            
            # 답글 대기 리뷰 조회
            result = self.supabase.rpc('get_coupangeats_pending_replies', {
                'p_user_id': user_id,
                'p_limit': limit
            }).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"답글 대기 리뷰 조회 실패: {e}")
            return []
    
    async def _update_reply_status(
        self, 
        review_id: str, 
        status: str, 
        reply_text: str = None, 
        error_message: str = None
    ):
        """답글 상태 업데이트"""
        try:
            result = self.supabase.rpc('update_coupangeats_reply_status', {
                'p_review_id': review_id,
                'p_reply_status': status,
                'p_reply_text': reply_text,
                'p_error_message': error_message
            }).execute()
            
            if result.data:
                logger.info(f"답글 상태 업데이트 완료: {review_id} -> {status}")
            
        except Exception as e:
            logger.error(f"답글 상태 업데이트 실패: {e}")


async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='쿠팡잇츠 답글 포스터')
    parser.add_argument('--username', required=True, help='쿠팡잇츠 로그인 ID')
    parser.add_argument('--password', required=True, help='쿠팡잇츠 로그인 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID')
    parser.add_argument('--max-replies', type=int, default=10, help='최대 답글 수 (기본: 10)')
    parser.add_argument('--test-mode', action='store_true', help='테스트 모드 (실제 답글 등록 안함)')
    
    args = parser.parse_args()
    
    poster = CoupangReplyPoster()
    result = await poster.post_replies(
        username=args.username,
        password=args.password,
        store_id=args.store_id,
        max_replies=args.max_replies,
        test_mode=args.test_mode
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())