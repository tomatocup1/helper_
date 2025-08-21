#!/usr/bin/env python3
"""
특정 주문번호(1SU2MK) 리뷰의 HTML 구조 상세 분석
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

async def debug_specific_review():
    """1SU2MK 주문번호 리뷰의 HTML 구조 상세 분석"""
    
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
            
            # 1SU2MK 주문번호를 포함한 요소 찾기
            target_elements = await page.query_selector_all('*:has-text("1SU2MK")')
            logger.info(f"1SU2MK를 포함한 요소 {len(target_elements)}개 발견")
            
            for i, element in enumerate(target_elements):
                try:
                    element_text = await element.inner_text()
                    element_html = await element.inner_html()
                    
                    # 1SU2MK를 포함한 요소의 상위 컨테이너들 분석
                    logger.info(f"\n=== 요소 {i+1} ===")
                    logger.info(f"텍스트: {element_text[:200]}...")
                    
                    # 상위로 올라가며 분석
                    current = element
                    for level in range(10):
                        try:
                            parent = await current.query_selector('xpath=..')
                            if not parent:
                                break
                            
                            parent_text = await parent.inner_text()
                            parent_html = await parent.inner_html()
                            
                            # 리뷰어 정보가 있는지 확인
                            has_reviewer = any(cls in parent_html for cls in ['css-hdvjju', 'eqn7l9b7'])
                            has_star_rating = 'svg' in parent_html and ('FFC400' in parent_html or 'dfe3e8' in parent_html)
                            has_review_text = any(cls in parent_html for cls in ['css-16m6tj', 'eqn7l9b5'])
                            
                            if has_reviewer or has_star_rating or has_review_text:
                                logger.info(f"\n--- 레벨 {level} 상위 요소 (리뷰 데이터 포함) ---")
                                logger.info(f"텍스트 길이: {len(parent_text)}")
                                logger.info(f"리뷰어 정보: {has_reviewer}")
                                logger.info(f"별점 SVG: {has_star_rating}")
                                logger.info(f"리뷰 텍스트: {has_review_text}")
                                logger.info(f"텍스트 미리보기: {parent_text[:300]}...")
                                
                                # HTML 파일로 저장
                                filename = f"review_1SU2MK_element_{i+1}_level_{level}.html"
                                with open(filename, 'w', encoding='utf-8') as f:
                                    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>1SU2MK 리뷰 분석 - 요소 {i+1} 레벨 {level}</title>
</head>
<body>
    <h1>1SU2MK 리뷰 구조 분석</h1>
    <h2>요소 {i+1} - 레벨 {level}</h2>
    <p><strong>텍스트 길이:</strong> {len(parent_text)}</p>
    <p><strong>리뷰어 정보:</strong> {has_reviewer}</p>
    <p><strong>별점 SVG:</strong> {has_star_rating}</p>
    <p><strong>리뷰 텍스트:</strong> {has_review_text}</p>
    <div style="border: 1px solid #ccc; padding: 20px; margin: 10px;">
{parent_html}
    </div>
</body>
</html>""")
                                logger.info(f"HTML 저장: {filename}")
                            
                            current = parent
                            
                        except Exception:
                            break
                    
                except Exception as e:
                    logger.error(f"요소 {i+1} 분석 실패: {e}")
                    
            # 전체 페이지 스크린샷
            await page.screenshot(path="debug_1SU2MK_page.png", full_page=True)
            logger.info("페이지 스크린샷 저장: debug_1SU2MK_page.png")
            
        except Exception as e:
            logger.error(f"분석 실패: {e}")
        
        finally:
            # 브라우저를 자동으로 닫지 않고 수동으로 확인할 수 있게 함
            logger.info("브라우저가 열려있습니다. 수동으로 확인 후 닫아주세요.")
            await asyncio.sleep(30)  # 30초 대기
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_specific_review())