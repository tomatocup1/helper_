#!/usr/bin/env python3
"""
실제 쿠팡잇츠 리뷰 HTML 구조 저장 스크립트
"""

import asyncio
import logging
from pathlib import Path
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.shared.logger import get_logger
from playwright.async_api import async_playwright

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

async def save_review_html_structure():
    """실제 쿠팡잇츠 리뷰 HTML 구조를 파일로 저장"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        page = await context.new_page()
        
        try:
            # 로그인
            await page.goto("https://store.coupangeats.com/merchant/login", timeout=30000)
            await page.wait_for_timeout(2000)
            
            await page.fill('#loginId', "hong7704002646")
            await page.fill('#password', "bin986200#")
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
            
            # 리뷰 페이지로 이동
            await page.goto("https://store.coupangeats.com/merchant/management/reviews", timeout=15000)
            await page.wait_for_timeout(3000)
            
            # 모달 닫기
            try:
                close_button = await page.query_selector('.dialog-modal-wrapper__body--close-button')
                if close_button:
                    await close_button.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            try:
                close_button = await page.query_selector('button:has(svg)')
                if close_button:
                    await close_button.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # 매장 선택 (708561)
            try:
                dropdown = await page.query_selector('.button:has(svg)')
                if dropdown:
                    await dropdown.click()
                    await page.wait_for_timeout(1000)
                    
                    options = await page.query_selector_all('.options li')
                    for option in options:
                        text = await option.inner_text()
                        if "708561" in text:
                            await option.click()
                            break
                    await page.wait_for_timeout(2000)
            except Exception as e:
                logger.error(f"매장 선택 실패: {e}")
            
            # 날짜 필터 (최근 1주일)
            try:
                date_dropdown = await page.query_selector('.css-1rkgd7l.eylfi1j5')
                if date_dropdown:
                    await date_dropdown.click()
                    await page.wait_for_timeout(1000)
                    
                    radio_button = await page.query_selector('label:has(input[type="radio"][value="1"])')
                    if radio_button:
                        await radio_button.click()
                        await page.wait_for_timeout(2000)
            except Exception as e:
                logger.error(f"날짜 필터 실패: {e}")
            
            # 미답변 탭 클릭
            try:
                unanswered_tab = await page.query_selector('strong:has-text("미답변")')
                if unanswered_tab:
                    await unanswered_tab.click()
                    await page.wait_for_timeout(3000)
            except Exception as e:
                logger.error(f"미답변 탭 클릭 실패: {e}")
            
            # 리뷰 컨테이너 찾기
            review_containers = await page.query_selector_all('li:has(strong:has-text("주문번호"))')
            logger.info(f"총 {len(review_containers)}개 리뷰 발견")
            
            if review_containers:
                # 첫 3개 리뷰의 HTML 구조 저장
                for i, container in enumerate(review_containers[:3]):
                    try:
                        html_content = await container.inner_html()
                        
                        # HTML 파일로 저장
                        filename = f"coupang_review_{i+1}_structure.html"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>쿠팡잇츠 리뷰 {i+1} 구조</title>
</head>
<body>
    <h1>쿠팡잇츠 리뷰 {i+1} HTML 구조</h1>
    <div style="border: 1px solid #ccc; padding: 20px; margin: 10px;">
{html_content}
    </div>
</body>
</html>""")
                        
                        logger.info(f"리뷰 {i+1} HTML 구조 저장: {filename}")
                        
                        # 텍스트 버전도 저장
                        text_filename = f"coupang_review_{i+1}_text.txt"
                        inner_text = await container.inner_text()
                        with open(text_filename, 'w', encoding='utf-8') as f:
                            f.write(f"리뷰 {i+1} 텍스트 내용:\n")
                            f.write("="*50 + "\n")
                            f.write(inner_text)
                        
                        logger.info(f"리뷰 {i+1} 텍스트 저장: {text_filename}")
                        
                    except Exception as e:
                        logger.error(f"리뷰 {i+1} 저장 실패: {e}")
            
            # 전체 페이지 스크린샷
            await page.screenshot(path="coupang_reviews_page.png", full_page=True)
            logger.info("페이지 스크린샷 저장: coupang_reviews_page.png")
            
        except Exception as e:
            logger.error(f"HTML 구조 저장 실패: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(save_review_html_structure())