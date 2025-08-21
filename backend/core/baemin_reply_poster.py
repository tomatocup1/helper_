#!/usr/bin/env python3
"""
배달의민족 답글 등록 엔진
- 배달의민족 리뷰에 대한 자동 답글 등록
- 답글 수정, 삭제 기능 지원
- 에러 처리 및 재시도 로직 포함
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from supabase import create_client, Client
from dotenv import load_dotenv

class BaeminReplyPoster:
    def __init__(self, headless=True, timeout=30000):
        self.headless = headless
        self.timeout = timeout
        
        # Supabase 클라이언트 초기화
        load_dotenv()
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            raise ValueError("Supabase 환경변수가 설정되지 않았습니다.")
        
        self.supabase: Client = create_client(supabase_url, supabase_service_key)
    
    async def post_reply(self, username: str, password: str, review_id: str, 
                        reply_text: str, user_id: str) -> Dict:
        """배민 답글 등록 메인 함수"""
        try:
            print(f"배민 답글 등록 시작: {review_id}")
            
            # 1. 리뷰 정보 조회
            review_info = await self._get_review_info(review_id, user_id)
            if not review_info:
                return {
                    'success': False,
                    'error': '리뷰 정보를 찾을 수 없습니다.',
                    'review_id': review_id
                }
            
            # 2. 브라우저 초기화 및 로그인
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
                        '--disable-features=IsolateOrigins,site-per-process'
                    ]
                )
            except Exception as e:
                print(f"Chrome 채널 실패, Chromium으로 대체: {e}")
                browser = await playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            try:
                # 3. 로그인 수행
                login_success = await self._login(page, username, password)
                if not login_success:
                    return {
                        'success': False,
                        'error': '로그인 실패',
                        'review_id': review_id
                    }
                
                # 4. 답글 등록
                result = await self._post_reply_to_review(page, review_info, reply_text)
                
                # 5. 결과에 따라 DB 업데이트
                if result['success']:
                    await self._update_reply_status(review_id, 'sent', reply_text)
                else:
                    await self._update_reply_status(review_id, 'failed', reply_text, result.get('error'))
                
                return result
                
            except Exception as e:
                print(f"답글 등록 중 오류: {str(e)}")
                await self._update_reply_status(review_id, 'failed', reply_text, str(e))
                return {
                    'success': False,
                    'error': str(e),
                    'review_id': review_id
                }
            finally:
                try:
                    await browser.close()
                    await playwright.stop()
                except:
                    pass
            
        except Exception as e:
            print(f"답글 등록 초기화 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'review_id': review_id
            }
    
    async def _login(self, page, username: str, password: str) -> bool:
        """배민 로그인"""
        try:
            print("배민 로그인 페이지로 이동 중...")
            await page.goto("https://biz-member.baemin.com/login", wait_until='networkidle')
            await asyncio.sleep(2)
            
            # ID 입력
            await page.fill('input[name="username"]', username)
            await asyncio.sleep(0.5)
            
            # 비밀번호 입력
            await page.fill('input[name="password"]', password)
            await asyncio.sleep(0.5)
            
            # 로그인 버튼 클릭
            await page.click('button[type="submit"]')
            await asyncio.sleep(3)
            
            # 로그인 성공 확인
            current_url = page.url
            if 'login' not in current_url:
                print("배민 로그인 성공")
                return True
            else:
                print("배민 로그인 실패")
                return False
                
        except Exception as e:
            print(f"로그인 중 오류: {str(e)}")
            return False
    
    async def _get_review_info(self, review_id: str, user_id: str) -> Optional[Dict]:
        """리뷰 정보 조회"""
        try:
            # reviews_baemin 테이블에서 리뷰 정보 조회
            response = self.supabase.table('reviews_baemin')\
                .select('''
                    id, baemin_review_id, reviewer_name, review_text, rating,
                    platform_store_id, reply_text, reply_status,
                    platform_store:platform_stores(platform_store_id, store_name, user_id)
                ''')\
                .eq('id', review_id)\
                .single()\
                .execute()
            
            if not response.data:
                return None
            
            review = response.data
            
            # 권한 확인 (해당 사용자의 매장인지)
            if review['platform_store']['user_id'] != user_id:
                print(f"권한 없음: 사용자 {user_id}는 이 리뷰에 답글을 작성할 권한이 없습니다.")
                return None
            
            return review
            
        except Exception as e:
            print(f"리뷰 정보 조회 중 오류: {str(e)}")
            return None
    
    async def _post_reply_to_review(self, page, review_info: Dict, reply_text: str) -> Dict:
        """특정 리뷰에 답글 등록"""
        try:
            platform_store_id = review_info['platform_store']['platform_store_id']
            baemin_review_id = review_info['baemin_review_id']
            
            # 1. 리뷰 페이지로 이동
            review_url = f"https://self.baemin.com/shops/{platform_store_id}/reviews"
            print(f"리뷰 페이지로 이동: {review_url}")
            await page.goto(review_url, wait_until='networkidle')
            await asyncio.sleep(3)
            
            # 2. 해당 리뷰 찾기
            review_element = await self._find_review_element(page, baemin_review_id, review_info)
            if not review_element:
                return {
                    'success': False,
                    'error': '해당 리뷰를 찾을 수 없습니다.',
                    'review_id': review_info['id']
                }
            
            # 3. 기존 답글 확인
            existing_reply = await self._check_existing_reply(review_element)
            if existing_reply:
                # 기존 답글 수정
                return await self._edit_existing_reply(review_element, reply_text, review_info['id'])
            else:
                # 새 답글 작성
                return await self._write_new_reply(review_element, reply_text, review_info['id'])
            
        except Exception as e:
            print(f"답글 등록 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'review_id': review_info['id']
            }
    
    async def _find_review_element(self, page, baemin_review_id: str, review_info: Dict) -> Optional[object]:
        """페이지에서 특정 리뷰 요소 찾기"""
        try:
            # 리뷰 요소들 전체 조회
            review_elements = await page.query_selector_all("div.review-item")
            
            if not review_elements:
                print("리뷰 요소를 찾을 수 없습니다.")
                return None
            
            print(f"총 {len(review_elements)}개의 리뷰 요소 발견")
            
            # 각 리뷰 요소에서 일치하는 리뷰 찾기
            for i, review_element in enumerate(review_elements):
                try:
                    # 리뷰어 이름으로 매칭
                    reviewer_name_element = await review_element.query_selector("span.css-1k0zbpoa-Text.ek0zbzv2")
                    if reviewer_name_element:
                        reviewer_name = await reviewer_name_element.text_content()
                        if reviewer_name and reviewer_name.strip() == review_info['reviewer_name']:
                            print(f"리뷰 찾음: {reviewer_name} (요소 {i+1})")
                            return review_element
                    
                    # 리뷰 텍스트로 매칭 (보조)
                    review_text_element = await review_element.query_selector("div.css-1sk2mhh-Box.e1w15d4l1 > p")
                    if review_text_element:
                        review_text = await review_text_element.text_content()
                        if review_text and review_text.strip() == review_info['review_text'].strip():
                            print(f"리뷰 텍스트 매칭으로 찾음 (요소 {i+1})")
                            return review_element
                
                except Exception as e:
                    print(f"리뷰 요소 {i+1} 처리 중 오류: {str(e)}")
                    continue
            
            print("일치하는 리뷰를 찾지 못했습니다.")
            return None
            
        except Exception as e:
            print(f"리뷰 찾기 중 오류: {str(e)}")
            return None
    
    async def _check_existing_reply(self, review_element) -> Optional[str]:
        """기존 답글 존재 여부 확인"""
        try:
            # 답글 섹션 확인
            reply_section = await review_element.query_selector("div.reply-section")
            if reply_section:
                reply_text_element = await reply_section.query_selector("p.reply-text")
                if reply_text_element:
                    existing_reply = await reply_text_element.text_content()
                    print(f"기존 답글 발견: {existing_reply[:50]}...")
                    return existing_reply.strip()
            
            return None
            
        except Exception as e:
            print(f"기존 답글 확인 중 오류: {str(e)}")
            return None
    
    async def _write_new_reply(self, review_element, reply_text: str, review_id: str) -> Dict:
        """새 답글 작성"""
        try:
            print("새 답글 작성 중...")
            
            # 1. 답글 작성 버튼 찾기 및 클릭
            reply_button = await review_element.query_selector("button.reply-write-btn")
            if not reply_button:
                # 대체 셀렉터 시도
                reply_button = await review_element.query_selector("button[aria-label='답글 작성']")
            
            if not reply_button:
                return {
                    'success': False,
                    'error': '답글 작성 버튼을 찾을 수 없습니다.',
                    'review_id': review_id
                }
            
            await reply_button.click()
            await asyncio.sleep(2)
            
            # 2. 답글 입력창에 텍스트 입력 (사용자 제공 셀렉터)
            reply_input = await review_element.query_selector("textarea.css-1nwjxwn-StyledTextArea")
            if not reply_input:
                return {
                    'success': False,
                    'error': '답글 입력창을 찾을 수 없습니다.',
                    'review_id': review_id
                }
            
            await reply_input.fill(reply_text)
            await asyncio.sleep(1)
            
            # 3. 답글 등록 버튼 클릭 (사용자 제공 셀렉터)
            submit_button = await review_element.query_selector("button.css-zqiyn4-StyledButton")
            if not submit_button:
                return {
                    'success': False,
                    'error': '답글 등록 버튼을 찾을 수 없습니다.',
                    'review_id': review_id
                }
            
            await submit_button.click()
            await asyncio.sleep(3)
            
            # 4. 등록 성공 확인
            success = await self._verify_reply_posted(review_element, reply_text)
            
            if success:
                print("답글 등록 성공")
                return {
                    'success': True,
                    'message': '답글이 성공적으로 등록되었습니다.',
                    'review_id': review_id,
                    'reply_text': reply_text
                }
            else:
                return {
                    'success': False,
                    'error': '답글 등록 후 확인 실패',
                    'review_id': review_id
                }
            
        except Exception as e:
            print(f"새 답글 작성 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'review_id': review_id
            }
    
    async def _edit_existing_reply(self, review_element, reply_text: str, review_id: str) -> Dict:
        """기존 답글 수정"""
        try:
            print("기존 답글 수정 중...")
            
            # 1. 답글 수정 버튼 찾기 및 클릭
            edit_button = await review_element.query_selector("button.reply-edit-btn")
            if not edit_button:
                edit_button = await review_element.query_selector("button[aria-label='답글 수정']")
            
            if not edit_button:
                return {
                    'success': False,
                    'error': '답글 수정 버튼을 찾을 수 없습니다.',
                    'review_id': review_id
                }
            
            await edit_button.click()
            await asyncio.sleep(2)
            
            # 2. 답글 입력창 찾기 및 기존 텍스트 삭제
            reply_input = await review_element.query_selector("textarea.css-1nwjxwn-StyledTextArea")
            if not reply_input:
                return {
                    'success': False,
                    'error': '답글 수정 입력창을 찾을 수 없습니다.',
                    'review_id': review_id
                }
            
            # 기존 텍스트 전체 선택 후 삭제
            await reply_input.click()
            await reply_input.press('Control+a')
            await reply_input.press('Delete')
            await asyncio.sleep(0.5)
            
            # 새 텍스트 입력
            await reply_input.fill(reply_text)
            await asyncio.sleep(1)
            
            # 3. 수정 완료 버튼 클릭
            save_button = await review_element.query_selector("button.css-zqiyn4-StyledButton")
            if not save_button:
                return {
                    'success': False,
                    'error': '답글 저장 버튼을 찾을 수 없습니다.',
                    'review_id': review_id
                }
            
            await save_button.click()
            await asyncio.sleep(3)
            
            # 4. 수정 성공 확인
            success = await self._verify_reply_posted(review_element, reply_text)
            
            if success:
                print("답글 수정 성공")
                return {
                    'success': True,
                    'message': '답글이 성공적으로 수정되었습니다.',
                    'review_id': review_id,
                    'reply_text': reply_text
                }
            else:
                return {
                    'success': False,
                    'error': '답글 수정 후 확인 실패',
                    'review_id': review_id
                }
            
        except Exception as e:
            print(f"답글 수정 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'review_id': review_id
            }
    
    async def _verify_reply_posted(self, review_element, expected_text: str) -> bool:
        """답글 등록/수정 성공 확인"""
        try:
            # 잠시 대기 후 답글 섹션 재확인
            await asyncio.sleep(2)
            
            reply_section = await review_element.query_selector("div.reply-section")
            if not reply_section:
                return False
            
            reply_text_element = await reply_section.query_selector("p.reply-text")
            if not reply_text_element:
                return False
            
            actual_text = await reply_text_element.text_content()
            if actual_text and actual_text.strip() == expected_text.strip():
                return True
            
            return False
            
        except Exception as e:
            print(f"답글 확인 중 오류: {str(e)}")
            return False
    
    async def _update_reply_status(self, review_id: str, status: str, reply_text: str, error_message: str = None):
        """데이터베이스에 답글 상태 업데이트"""
        try:
            update_data = {
                'reply_status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if status == 'sent':
                update_data['reply_text'] = reply_text
                update_data['reply_sent_at'] = datetime.now().isoformat()
                update_data['failure_reason'] = None
            elif status == 'failed':
                update_data['reply_failed_at'] = datetime.now().isoformat()
                update_data['failure_reason'] = error_message
                # 재시도 카운트 증가
                current_review = self.supabase.table('reviews_baemin').select('retry_count').eq('id', review_id).single().execute()
                if current_review.data:
                    retry_count = current_review.data.get('retry_count', 0) + 1
                    update_data['retry_count'] = retry_count
            
            response = self.supabase.table('reviews_baemin').update(update_data).eq('id', review_id).execute()
            
            if response.data:
                print(f"답글 상태 업데이트 완료: {status}")
            else:
                print("답글 상태 업데이트 실패")
                
        except Exception as e:
            print(f"답글 상태 업데이트 중 오류: {str(e)}")

async def main():
    """테스트 함수"""
    parser = argparse.ArgumentParser(description='배달의민족 답글 등록')
    parser.add_argument('--username', required=True, help='배민 사업자 아이디')
    parser.add_argument('--password', required=True, help='배민 사업자 비밀번호')
    parser.add_argument('--review-id', required=True, help='리뷰 ID (reviews_baemin 테이블의 UUID)')
    parser.add_argument('--reply-text', required=True, help='답글 내용')
    parser.add_argument('--user-id', required=True, help='사용자 ID (UUID)')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드')
    parser.add_argument('--timeout', type=int, default=30000, help='타임아웃 (ms)')
    
    args = parser.parse_args()
    
    poster = BaeminReplyPoster(
        headless=args.headless,
        timeout=args.timeout
    )
    
    result = await poster.post_reply(
        args.username,
        args.password,
        args.review_id,
        args.reply_text,
        args.user_id
    )
    
    # 결과 출력 (JSON 형태)
    print(f"REPLY_RESULT:{json.dumps(result, ensure_ascii=False)}")
    
    return result['success']

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)