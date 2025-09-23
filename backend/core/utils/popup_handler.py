#!/usr/bin/env python3
"""
범용 팝업 처리 핸들러
- 플랫폼별 팝업 패턴 대응
- 안정적인 3단계 폴백 메커니즘
- SVG 기반 우선 처리 및 포괄적 텍스트 매칭
"""

import asyncio
from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


class PopupHandler:
    """범용 팝업 처리 클래스"""

    @staticmethod
    async def handle_baemin_popup(page: Page) -> bool:
        """
        배민 특화 팝업 처리 함수

        우선순위:
        1. SVG 닫기 버튼 (X 아이콘)
        2. "보지 않기" 포괄적 패턴 (오늘 하루, 7일 동안, 일주일 등)
        3. 기본 닫기 패턴
        4. JavaScript 폴백
        5. ESC 키 처리

        Args:
            page: Playwright Page 객체

        Returns:
            bool: 팝업 처리 성공 여부
        """
        try:
            print("[POPUP] 배민 팝업 확인 중...")

            # 500ms 초기 대기 - 팝업 애니메이션 완료 대기
            await asyncio.sleep(0.5)

            # 안전한 셀렉터만 사용 (검증된 패턴만)
            close_selectors = [
                # 1순위: 명확한 닫기 버튼만 (aria-label로 확실히 식별되는 것)
                'button[aria-label="닫기"]',
                'div[role="dialog"] button[aria-label="닫기"]',

                # 2순위: SVG 닫기 버튼 (X 아이콘) - 단, 팝업 내부에 있는 것만
                'div[role="dialog"] button svg[xmlns="http://www.w3.org/2000/svg"]',
                'div[role="alertdialog"] button svg[xmlns="http://www.w3.org/2000/svg"]',

                # 3순위: "보지 않기" 패턴 - 단, 팝업 내부에 있는 것만
                'div[role="dialog"] button:has-text("보지 않기")',
                'div[role="dialog"] button:has-text("보지않기")',

                # 4순위: 배민 특화 패턴 (검증된 것만)
                'button.IconButton_b_c9kn_uw474i2[aria-label="닫기"]',
                'button.TextButton_b_c9kn_1j0jumh3:has-text("오늘 하루 보지 않기")',
            ]

            # 팝업 존재 확인
            popup_exists = await page.query_selector('div[role="dialog"], div[role="alertdialog"], [class*="modal"], [class*="popup"]')
            if not popup_exists:
                print("   [SUCCESS] 팝업 없음 - 처리 완료")
                return True

            popup_class = await popup_exists.get_attribute('class')
            popup_html_full = await popup_exists.inner_html()
            popup_html = popup_html_full[:200] if popup_html_full else "HTML 없음"  # 처음 200자만
            print(f"   [DETECT] 팝업 감지됨! 클래스: {popup_class}")
            print(f"   [INFO] 팝업 HTML 미리보기: {popup_html}...")
            print(f"   [START] {len(close_selectors)}개 셀렉터로 닫기 시도 시작...")

            # 1-3순위: 일반적인 방법으로 2회 시도
            for i, selector in enumerate(close_selectors, 1):
                try:
                    print(f"   [TRY] 시도 {i}/{len(close_selectors)}: {selector}")

                    # 닫기 버튼 찾기 (최대 2초 대기)
                    close_button = await page.query_selector(selector)
                    if close_button:
                        # 버튼 활성화 확인
                        is_visible = await close_button.is_visible()
                        is_enabled = await close_button.is_enabled()
                        button_text = await close_button.text_content() or "텍스트 없음"

                        print(f"   [FOUND] 버튼 발견: '{button_text}' (보임: {is_visible}, 활성: {is_enabled})")

                        # 안전성 검증: 닫기 관련 텍스트가 있는지 확인
                        safe_to_click = False
                        if button_text and any(keyword in button_text for keyword in ["닫기", "보지 않기", "보지않기"]):
                            safe_to_click = True
                        elif selector in ['button[aria-label="닫기"]', 'div[role="dialog"] button[aria-label="닫기"]']:
                            safe_to_click = True
                        elif "svg" in selector and "dialog" in selector:
                            safe_to_click = True

                        if is_visible and is_enabled and safe_to_click:
                            print(f"   [CLICK] 안전 검증 완료, 버튼 클릭 시도: {selector}")
                            await close_button.click()

                            # 클릭 후 500ms 대기
                            await asyncio.sleep(0.5)

                            # 팝업이 실제로 사라졌는지 확인
                            popup_gone = await page.query_selector('div[role="dialog"], div[role="alertdialog"]')
                            if not popup_gone:
                                print(f"   [SUCCESS] 배민 팝업 닫기 성공: {selector}")
                                return True
                            else:
                                print(f"   [WARNING] 팝업이 여전히 존재함, 다른 방법 시도")
                        else:
                            print(f"   [SKIP] 안전 검증 실패 또는 버튼이 비활성화됨 (안전: {safe_to_click})")
                    else:
                        print(f"   [NOTFOUND] 셀렉터로 버튼을 찾을 수 없음: {selector}")

                    # 2회 시도 후 JavaScript 폴백으로 전환
                    if i >= 2:
                        print(f"   [FALLBACK] 2회 시도 완료, JavaScript 폴백으로 전환 (시도된 셀렉터: {i}개)")
                        break

                except PlaywrightTimeoutError:
                    print(f"   [TIMEOUT] 타임아웃: {selector}")
                    continue
                except Exception as e:
                    print(f"   [ERROR] 셀렉터 오류: {selector} - {str(e)}")
                    continue

            # 2회 실패 후 JavaScript 폴백 적용 (더 안전하게)
            print("   [JAVASCRIPT] JavaScript로 팝업 강제 닫기 시도...")
            try:
                await page.evaluate("""
                    // 1. aria-label="닫기" 버튼만 클릭 (가장 안전)
                    const closeButtons = document.querySelectorAll('button[aria-label="닫기"]');
                    closeButtons.forEach(btn => {
                        console.log('Clicking close button:', btn);
                        btn.click();
                    });

                    // 2. 팝업 내부의 "보지 않기" 텍스트 버튼만 클릭
                    const dialogs = document.querySelectorAll('div[role="dialog"], div[role="alertdialog"]');
                    dialogs.forEach(dialog => {
                        const textButtons = Array.from(dialog.querySelectorAll('button'))
                            .filter(btn => btn.textContent && (
                                btn.textContent.includes('보지 않기') ||
                                btn.textContent.includes('보지않기') ||
                                btn.textContent.includes('닫기')
                            ));
                        textButtons.forEach(btn => {
                            console.log('Clicking safe text button:', btn.textContent);
                            btn.click();
                        });
                    });

                    // 3. 마지막 수단: role="dialog"인 요소들만 제거
                    const dialogsToRemove = document.querySelectorAll('div[role="dialog"], div[role="alertdialog"]');
                    dialogsToRemove.forEach(dialog => {
                        console.log('Removing dialog:', dialog);
                        dialog.remove();
                    });

                    console.log('Safe JavaScript popup removal completed');
                """)

                # JavaScript 실행 후 500ms 대기
                await asyncio.sleep(0.5)

                # 팝업 제거 확인
                popup_exists = await page.query_selector('div[role="dialog"], div[role="alertdialog"]')
                if not popup_exists:
                    print("   [SUCCESS] JavaScript로 팝업 강제 제거 완료")
                    return True

            except Exception as e:
                print(f"   [ERROR] JavaScript 팝업 제거 실패: {str(e)}")

            # 최후 수단: ESC 키 처리
            try:
                print("   [KEYBOARD] ESC 키로 팝업 닫기 시도...")
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.5)

                # 팝업이 사라졌는지 확인
                popup_exists = await page.query_selector('div[role="dialog"], div[role="alertdialog"]')
                if not popup_exists:
                    print("   [SUCCESS] ESC 키로 팝업 닫기 성공")
                    return True

            except Exception as e:
                print(f"   [ERROR] ESC 키 팝업 닫기 실패: {str(e)}")

            print("   [WARNING] 모든 팝업 닫기 시도 실패 (무시하고 계속 진행)")
            return False

        except Exception as e:
            error_msg = f"팝업 처리 중 치명적 오류: {str(e)}"
            print(f"   [CRITICAL] {error_msg}")
            # 에러를 stderr로도 출력하여 automation_runner에서 확인 가능하도록
            import sys
            print(error_msg, file=sys.stderr)
            return False

    @staticmethod
    async def handle_coupang_popup(page: Page) -> bool:
        """쿠팡이츠 팝업 처리 (향후 확장용)"""
        # TODO: 쿠팡이츠 특화 팝업 처리 로직 구현
        return True

    @staticmethod
    async def handle_yogiyo_popup(page: Page) -> bool:
        """요기요 팝업 처리 (향후 확장용)"""
        # TODO: 요기요 특화 팝업 처리 로직 구현
        return True

    @staticmethod
    async def handle_naver_popup(page: Page) -> bool:
        """네이버 팝업 처리 (향후 확장용)"""
        # TODO: 네이버 특화 팝업 처리 로직 구현
        return True