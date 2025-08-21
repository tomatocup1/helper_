#!/usr/bin/env python3
"""
쿠팡잇츠 별점 추출 실제 HTML 구조 디버깅
"""

import asyncio
import logging
from pathlib import Path
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.coupang_star_rating_extractor import CoupangStarRatingExtractor
from backend.services.shared.logger import get_logger
from playwright.async_api import async_playwright

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

async def debug_rating_in_real_structure():
    """실제 쿠팡잇츠 HTML 구조에서 별점 추출 디버깅"""
    
    # 실제 쿠팡잇츠 리뷰 HTML 구조 (크롤링 시 실제로 발견되는 구조)
    real_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Coupang Eats Reviews</title>
    </head>
    <body>
        <!-- 실제 쿠팡잇츠 리뷰 구조 -->
        <li data-testid="review-item">
            <div>
                <div>
                    <div>
                        <strong>주문번호: 0ELMJG</strong>
                    </div>
                </div>
                <div>
                    <span>김**</span>
                    <span>3회 주문</span>
                    <!-- 별점 영역 -->
                    <div>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#FFC400" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#FFC400" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#FFC400" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#FFC400" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#dfe3e8" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                    </div>
                    <div>2024.08.19 주문</div>
                    <div>2024.08.20 작성</div>
                </div>
                <div>
                    <div>맛있게 잘 먹었습니다!</div>
                </div>
                <div>
                    <span>(2~3인세트) 만족 100% 완전닭다리살 닭강정</span>
                    <span>배달</span>
                </div>
            </div>
        </li>

        <!-- 별점만 있는 리뷰 -->
        <li data-testid="review-item">
            <div>
                <div>
                    <div>
                        <strong>주문번호: 0FHKML</strong>
                    </div>
                </div>
                <div>
                    <span>박**</span>
                    <span>1회 주문</span>
                    <!-- 별점 영역 (2점) -->
                    <div>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#FFC400" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#FFC400" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#dfe3e8" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#dfe3e8" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path fill="#dfe3e8" d="M8 0l2.462 4.856L16 5.644l-4 3.912.944 5.444L8 12.388l-4.944 2.612L4 9.556 0 5.644l5.538-.788L8 0z"></path>
                        </svg>
                    </div>
                    <div>2024.08.18 주문</div>
                    <div>2024.08.19 작성</div>
                </div>
                <!-- 별점만 있고 리뷰 텍스트 없음 -->
            </div>
        </li>
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 테스트 HTML 로드
        await page.set_content(real_html)
        
        # 별점 추출기 초기화
        extractor = CoupangStarRatingExtractor()
        
        # 모든 리뷰 아이템 찾기
        review_items = await page.query_selector_all('li[data-testid="review-item"]')
        logger.info(f"총 {len(review_items)}개의 리뷰 아이템 발견")
        
        for i, review_item in enumerate(review_items):
            logger.info(f"\n=== 리뷰 {i+1} 테스트 ===")
            
            # 주문번호 확인
            order_number_element = await review_item.query_selector('strong:has-text("주문번호")')
            if order_number_element:
                order_number = await order_number_element.inner_text()
                logger.info(f"주문번호: {order_number}")
            
            # 별점 추출 테스트
            result = await extractor.extract_rating_with_fallback(review_item)
            logger.info(f"별점 추출 결과: {result}")
            
            # 리뷰 텍스트 확인
            review_text_candidates = await review_item.query_selector_all('div')
            for candidate in review_text_candidates:
                text = await candidate.inner_text()
                if len(text) > 10 and any(keyword in text for keyword in ['맛', '좋', '나쁘', '최고', '별로']):
                    logger.info(f"리뷰 텍스트: {text}")
                    break
        
        await browser.close()

async def test_svg_direct_access():
    """SVG 요소 직접 접근 테스트"""
    
    # 간단한 SVG 별점 구조
    svg_test_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div id="rating-container">
            <svg width="16" height="16"><path fill="#FFC400" d="star-path"></path></svg>
            <svg width="16" height="16"><path fill="#FFC400" d="star-path"></path></svg>
            <svg width="16" height="16"><path fill="#FFC400" d="star-path"></path></svg>
            <svg width="16" height="16"><path fill="#dfe3e8" d="star-path"></path></svg>
            <svg width="16" height="16"><path fill="#dfe3e8" d="star-path"></path></svg>
        </div>
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        await page.set_content(svg_test_html)
        
        extractor = CoupangStarRatingExtractor()
        container = await page.query_selector('#rating-container')
        
        if container:
            logger.info("=== 직접 SVG 접근 테스트 ===")
            result = await extractor.extract_rating_with_fallback(container)
            logger.info(f"결과: {result}")
        
        await browser.close()

if __name__ == "__main__":
    logger.info("쿠팡잇츠 별점 추출 디버깅 시작")
    asyncio.run(debug_rating_in_real_structure())
    logger.info("직접 SVG 테스트 시작")
    asyncio.run(test_svg_direct_access())