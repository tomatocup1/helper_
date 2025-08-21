#!/usr/bin/env python3
"""
쿠팡잇츠 페이지 디버깅 스크립트
실제 페이지 구조를 확인하여 selector 개선
"""

import asyncio
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import async_playwright

async def debug_coupang_page():
    """쿠팡잇츠 페이지 구조 디버깅"""
    
    username = input("쿠팡잇츠 로그인 ID: ")
    password = input("쿠팡잇츠 로그인 비밀번호: ")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 브라우저 표시
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1366, "height": 768}
        )
        
        page = await context.new_page()
        
        try:
            print("1. 로그인 페이지로 이동...")
            await page.goto("https://store.coupangeats.com/merchant/login")
            await page.wait_for_timeout(2000)
            
            print("2. 로그인 수행...")
            await page.fill('#loginId', username)
            await page.fill('#password', password)
            await page.click('button[type="submit"]')
            
            await page.wait_for_timeout(5000)
            
            print("3. 리뷰 페이지로 이동...")
            await page.goto("https://store.coupangeats.com/merchant/management/reviews")
            await page.wait_for_timeout(5000)
            
            print("4. 페이지 스크린샷 저장...")
            await page.screenshot(path=f"coupangeats_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            print("5. 드롭다운 관련 요소 찾기...")
            
            # 모든 가능한 드롭다운 요소들 찾기
            dropdown_candidates = await page.query_selector_all('div:has(svg), button:has(svg), [class*="button"]')
            
            print(f"드롭다운 후보 요소 수: {len(dropdown_candidates)}")
            
            for i, element in enumerate(dropdown_candidates[:10]):  # 처음 10개만
                try:
                    text = await element.inner_text()
                    tag = await element.evaluate('el => el.tagName')
                    classes = await element.get_attribute('class')
                    
                    print(f"  {i+1}. {tag} - '{text[:50]}...' - classes: {classes}")
                    
                    if '708561' in text or '큰집닭강정' in text:
                        print(f"    ★ 매장 관련 요소 발견!")
                        
                except Exception as e:
                    print(f"  {i+1}. 오류: {e}")
            
            print("\n6. 날짜 관련 요소 찾기...")
            
            # 날짜 관련 요소들 찾기
            date_candidates = await page.query_selector_all('div:has-text("오늘"), span:has-text("오늘"), [class*="eylfi"]')
            
            print(f"날짜 후보 요소 수: {len(date_candidates)}")
            
            for i, element in enumerate(date_candidates):
                try:
                    text = await element.inner_text()
                    tag = await element.evaluate('el => el.tagName')
                    classes = await element.get_attribute('class')
                    
                    print(f"  {i+1}. {tag} - '{text}' - classes: {classes}")
                    
                except Exception as e:
                    print(f"  {i+1}. 오류: {e}")
            
            print("\n7. 미답변 탭 관련 요소 찾기...")
            
            # 미답변 탭 요소들 찾기
            tab_candidates = await page.query_selector_all('*:has-text("미답변"), [class*="e1kgpv5e"], [class*="css-1cnakc9"]')
            
            print(f"미답변 탭 후보 요소 수: {len(tab_candidates)}")
            
            for i, element in enumerate(tab_candidates):
                try:
                    text = await element.inner_text()
                    tag = await element.evaluate('el => el.tagName')
                    classes = await element.get_attribute('class')
                    
                    print(f"  {i+1}. {tag} - '{text}' - classes: {classes}")
                    
                except Exception as e:
                    print(f"  {i+1}. 오류: {e}")
            
            print("\n8. 전체 페이지 HTML 구조 저장...")
            
            # 페이지 HTML 저장
            html_content = await page.content()
            with open(f"coupangeats_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            print("디버깅 완료! 브라우저를 닫으려면 Enter를 누르세요...")
            input()
            
        except Exception as e:
            print(f"디버깅 중 오류: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(debug_coupang_page())