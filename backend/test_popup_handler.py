#!/usr/bin/env python3
"""
배민 팝업 핸들러 테스트 스크립트
- 새로운 범용 팝업 핸들러 기능 테스트
- SVG 기반 우선 처리 및 "보지 않기" 포괄적 매칭 검증
"""

import os
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "core"))

from core.utils.popup_handler import PopupHandler

async def test_popup_handler():
    """배민 팝업 핸들러 테스트"""

    print("🧪 배민 팝업 핸들러 테스트 시작...")

    async with async_playwright() as p:
        # 브라우저 시작 (테스트용으로 headless=False)
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-first-run',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()

        try:
            print("📱 배민 메인 페이지 접속...")
            await page.goto('https://www.baemin.com', wait_until='networkidle')
            await page.wait_for_timeout(3000)

            # 1. 먼저 팝업이 있는지 확인
            print("🔍 팝업 존재 여부 확인...")
            popup_exists = await page.query_selector('div[role="dialog"], div[role="alertdialog"], [class*="modal"], [class*="popup"]')

            if popup_exists:
                print("🎯 팝업 감지됨! 핸들러 실행...")
                result = await PopupHandler.handle_baemin_popup(page)

                if result:
                    print("✅ 팝업 처리 성공!")
                else:
                    print("❌ 팝업 처리 실패")

                # 팝업 처리 후 상태 확인
                await page.wait_for_timeout(2000)
                remaining_popup = await page.query_selector('div[role="dialog"], div[role="alertdialog"]')
                if remaining_popup:
                    print("⚠️ 팝업이 여전히 남아있음")
                else:
                    print("✅ 팝업 완전 제거 확인")
            else:
                print("ℹ️ 현재 팝업이 없습니다")

                # 팝업이 없을 때도 핸들러 테스트
                print("🎯 팝업 핸들러 안전성 테스트...")
                result = await PopupHandler.handle_baemin_popup(page)
                print(f"✅ 팝업 없는 상황에서 핸들러 테스트 완료: {result}")

            print("⏳ 페이지 상태 확인을 위해 잠시 대기...")
            print("   (수동으로 팝업이 나타나는지 확인하고 Ctrl+C로 종료하세요)")

            # 무한 대기 (사용자가 Ctrl+C로 종료)
            try:
                while True:
                    await page.wait_for_timeout(5000)
                    # 5초마다 팝업 체크
                    popup_check = await page.query_selector('div[role="dialog"], div[role="alertdialog"]')
                    if popup_check:
                        print("🚨 새로운 팝업 감지! 자동 처리 시도...")
                        await PopupHandler.handle_baemin_popup(page)
            except KeyboardInterrupt:
                print("\n⌨️ 사용자가 테스트를 중단했습니다")

        except Exception as e:
            print(f"❌ 테스트 중 오류: {str(e)}")

        finally:
            await browser.close()
            print("🏁 테스트 완료")

async def test_selectors():
    """셀렉터 우선순위 테스트"""

    print("\n🔍 셀렉터 우선순위 테스트...")

    # 새로운 팝업 핸들러의 셀렉터 우선순위 출력
    selectors = [
        # 1순위: SVG 닫기 버튼
        'button svg[xmlns="http://www.w3.org/2000/svg"]',
        '[role="button"] svg[xmlns="http://www.w3.org/2000/svg"]',
        'button:has(svg[xmlns="http://www.w3.org/2000/svg"])',

        # 2순위: 포괄적 "보지 않기" 패턴
        'button:has-text("보지 않기")',
        'button:has-text("보지않기")',

        # 3순위: 기본 닫기 패턴
        '[aria-label="닫기"]',
        'button[aria-label="닫기"]',
        'button:has-text("닫기")',
    ]

    print("📋 새로운 팝업 핸들러 우선순위:")
    for i, selector in enumerate(selectors, 1):
        print(f"   {i}. {selector}")

    print("\n💡 주요 개선사항:")
    print("   ✅ SVG 닫기 버튼 우선 처리")
    print("   ✅ '보지 않기' 포괄적 패턴 매칭")
    print("   ✅ 500ms 초기 대기 + 최대 2초 동적 대기")
    print("   ✅ 2회 실패 후 JavaScript 폴백")
    print("   ✅ 범용 함수화로 유지보수성 향상")

if __name__ == "__main__":
    print("🚀 배민 팝업 핸들러 종합 테스트")
    print("=" * 50)

    # 환경변수 로드
    load_dotenv()

    # 셀렉터 우선순위 테스트
    asyncio.run(test_selectors())

    # 실제 팝업 핸들러 테스트
    print("\n" + "=" * 50)
    asyncio.run(test_popup_handler())