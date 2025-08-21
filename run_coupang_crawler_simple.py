#!/usr/bin/env python3
"""
쿠팡잇츠 크롤러 단순화 버전 (필터 없이 현재 리뷰 수집)
"""

import asyncio
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import async_playwright
from backend.services.shared.logger import get_logger
from backend.core.coupang_star_rating_extractor import CoupangStarRatingExtractor

logger = get_logger(__name__)

async def simple_crawl():
    """간단한 쿠팡잇츠 크롤링"""
    
    username = "hong7704002646"  # 하드코딩으로 테스트
    password = "bin986200#"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 브라우저 표시
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1366, "height": 768}
        )
        
        page = await context.new_page()
        
        try:
            print("1. 로그인...")
            await page.goto("https://store.coupangeats.com/merchant/login")
            await page.wait_for_timeout(2000)
            
            await page.fill('#loginId', username)
            await page.fill('#password', password)
            await page.click('button[type="submit"]')
            
            await page.wait_for_timeout(3000)
            
            print("2. 리뷰 페이지로 이동...")
            await page.goto("https://store.coupangeats.com/merchant/management/reviews")
            await page.wait_for_timeout(5000)
            
            print("3. 현재 페이지의 리뷰 찾기...")
            
            # 리뷰 관련 요소들을 다양한 방법으로 찾기
            review_selectors = [
                '.css-hdvjju.eqn7l9b7',  # 원래 selector (리뷰어 이름)
                'div:has(b):has-text("회 주문")',  # "3회 주문" 형태
                '[class*="eqn7l9b7"]',
                'div:has(b):has([class*="eqn7l9b8"])',  # 날짜가 있는 div
                '.css-1bqps6x.eqn7l9b8',  # 날짜 요소
            ]
            
            reviews_found = []
            
            for selector in review_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    print(f"  {selector}: {len(elements)}개 발견")
                    
                    if elements:
                        reviews_found.extend(elements)
                        break
                        
                except Exception as e:
                    print(f"  {selector}: 오류 - {e}")
            
            if not reviews_found:
                print("4. 대안 방법으로 리뷰 찾기...")
                
                # 페이지의 모든 텍스트 요소에서 "회 주문" 패턴 찾기
                order_elements = await page.query_selector_all('*:has-text("회 주문")')
                print(f"  '회 주문' 포함 요소: {len(order_elements)}개")
                
                for element in order_elements[:5]:  # 처음 5개만 분석
                    try:
                        text = await element.inner_text()
                        print(f"    - {text[:100]}")
                        
                        # 상위 컨테이너 찾기
                        parent = element
                        for _ in range(5):
                            parent = await parent.query_selector('xpath=..')
                            if not parent:
                                break
                                
                            parent_text = await parent.inner_text()
                            if len(parent_text.split('\n')) >= 3:  # 여러 줄이면 리뷰 컨테이너일 가능성
                                reviews_found.append(parent)
                                print(f"      → 리뷰 컨테이너로 판단")
                                break
                                
                    except Exception as e:
                        continue
            
            print(f"\n5. 리뷰 분석 시작 (총 {len(reviews_found)}개)...")
            
            star_extractor = CoupangStarRatingExtractor()
            
            for i, review_element in enumerate(reviews_found[:3]):  # 처음 3개만 분석
                try:
                    print(f"\n=== 리뷰 {i+1} ===")
                    
                    # 전체 텍스트 출력
                    full_text = await review_element.inner_text()
                    print(f"전체 텍스트: {full_text[:200]}...")
                    
                    # 별점 추출 시도
                    rating_result = await star_extractor.extract_rating_with_fallback(review_element)
                    print(f"별점: {rating_result['rating']} (방식: {rating_result['extraction_method']})")
                    
                    # 개별 요소 분석
                    reviewer_element = await review_element.query_selector('b')
                    if reviewer_element:
                        reviewer_name = await reviewer_element.inner_text()
                        print(f"리뷰어: {reviewer_name}")
                    
                    date_element = await review_element.query_selector('[class*="css-1bqps6x"], span:has-text("-")')
                    if date_element:
                        review_date = await date_element.inner_text()
                        print(f"날짜: {review_date}")
                    
                    text_element = await review_element.query_selector('p')
                    if text_element:
                        review_text = await text_element.inner_text()
                        print(f"리뷰 텍스트: {review_text}")
                    
                except Exception as e:
                    print(f"리뷰 {i+1} 분석 오류: {e}")
            
            print("\n6. 스크린샷 저장...")
            await page.screenshot(path=f"coupangeats_simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            print("\n분석 완료! 브라우저를 닫으려면 Enter를 누르세요...")
            input()
            
        except Exception as e:
            print(f"크롤링 중 오류: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(simple_crawl())