#!/usr/bin/env python3
"""
쿠팡잇츠 별점 추출 디버깅 스크립트
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

async def test_rating_extraction():
    """별점 추출 테스트를 위한 HTML 샘플 생성 및 테스트"""
    
    # 쿠팡잇츠 별점 HTML 샘플 (실제 구조 기반)
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test Rating</title>
    </head>
    <body>
        <!-- 5점 리뷰 -->
        <div class="review-item" id="review-5star">
            <div class="rating">
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#FFC400" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#FFC400" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#FFC400" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#FFC400" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#FFC400" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
            </div>
            <div class="reviewer">김**</div>
            <div class="review-text">정말 맛있어요!</div>
        </div>

        <!-- 3점 리뷰 -->
        <div class="review-item" id="review-3star">
            <div class="rating">
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#FFC400" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#FFC400" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#FFC400" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#dfe3e8" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
                <svg width="16" height="16" viewBox="0 0 16 16">
                    <path fill="#dfe3e8" d="M8 0l2.4 4.8L16 5.6l-4 3.9.9 5.5L8 12.4l-4.9 2.6L4 9.5 0 5.6l5.6-.8z"/>
                </svg>
            </div>
            <div class="reviewer">박**</div>
            <div class="review-text">보통이에요</div>
        </div>
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 테스트 HTML 로드
        await page.set_content(test_html)
        
        # 별점 추출기 초기화
        extractor = CoupangStarRatingExtractor()
        
        # 5점 리뷰 테스트
        logger.info("=== 5점 리뷰 테스트 ===")
        review_5star = await page.query_selector('#review-5star')
        if review_5star:
            result_5star = await extractor.extract_rating_with_fallback(review_5star)
            logger.info(f"5점 리뷰 결과: {result_5star}")
        
        # 3점 리뷰 테스트  
        logger.info("=== 3점 리뷰 테스트 ===")
        review_3star = await page.query_selector('#review-3star')
        if review_3star:
            result_3star = await extractor.extract_rating_with_fallback(review_3star)
            logger.info(f"3점 리뷰 결과: {result_3star}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_rating_extraction())