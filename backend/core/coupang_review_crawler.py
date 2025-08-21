#!/usr/bin/env python3
"""
쿠팡잇츠 리뷰 크롤러
로그인 → 리뷰 페이지 이동 → 매장 선택 → 날짜 필터 → 리뷰 수집
"""

import asyncio
import argparse
import json
import os
import sys
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import hashlib

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from backend.services.shared.logger import get_logger
from backend.services.shared.config import settings
from backend.core.coupang_star_rating_extractor import CoupangStarRatingExtractor

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

class CoupangReviewCrawler:
    """쿠팡잇츠 리뷰 크롤러"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.star_extractor = CoupangStarRatingExtractor()
        
    async def crawl_reviews(
        self,
        username: str,
        password: str,
        store_id: str,
        days: int = 7,
        max_pages: int = 5
    ) -> Dict[str, Any]:
        """
        쿠팡잇츠 리뷰 크롤링 메인 함수
        
        Args:
            username: 로그인 ID
            password: 로그인 비밀번호  
            store_id: 플랫폼 매장 ID
            days: 크롤링 기간 (일)
            max_pages: 최대 페이지 수
            
        Returns:
            Dict: 크롤링 결과
        """
        browser = None
        
        try:
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
                        "reviews": []
                    }
                
                # 2. 리뷰 페이지 이동
                await self._navigate_to_reviews_page(page)
                
                # 3. 모달 창 닫기 (적극적으로 여러 번 시도)
                await page.wait_for_timeout(2000)  # 페이지 로딩 완료 대기
                await self._close_modal_if_exists(page)
                await page.wait_for_timeout(1000)  # 첫 번째 모달 닫기 후 대기
                await self._close_modal_if_exists(page)  # 두 번째 시도
                
                # 4. 매장 선택
                await self._select_store(page, store_id)
                
                # 5. 날짜 필터 적용
                await self._apply_date_filter(page, days)
                
                # 6. 미답변 탭 클릭
                await self._click_unanswered_tab(page)
                
                # 7. 리뷰 수집
                reviews = await self._collect_reviews(page, max_pages)
                
                # 8. 데이터베이스 저장
                saved_count = await self._save_reviews(reviews, store_id)
                
                return {
                    "success": True,
                    "message": f"리뷰 수집 완료: {len(reviews)}개 수집, {saved_count}개 저장",
                    "reviews": reviews,
                    "saved_count": saved_count
                }
                
        except Exception as e:
            logger.error(f"Crawling failed: {e}")
            return {
                "success": False,
                "message": f"크롤링 실패: {str(e)}",
                "reviews": []
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
            
            # 로그인 필드 확인
            login_id_field = await page.query_selector('#loginId')
            password_field = await page.query_selector('#password')
            submit_button = await page.query_selector('button[type="submit"]')
            
            if not login_id_field or not password_field or not submit_button:
                logger.error("로그인 필드를 찾을 수 없습니다")
                return False
            
            # 로그인 정보 입력
            await page.fill('#loginId', username)
            await page.fill('#password', password)
            
            logger.info("로그인 정보 입력 완료")
            
            # 로그인 버튼 클릭
            await submit_button.click()
            
            # 결과 대기 (더 긴 시간 대기)
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            logger.info(f"로그인 후 URL: {current_url}")
            
            # 로그인 성공 확인
            # 1. URL이 login 페이지에서 벗어났는지 확인
            if "login" not in current_url:
                logger.info("로그인 성공 (URL 기준)")
                return True
            
            # 2. 에러 메시지 확인
            error_elements = await page.query_selector_all('.error-message, .alert, [class*="error"]')
            if error_elements:
                for error_element in error_elements:
                    error_text = await error_element.inner_text()
                    logger.error(f"로그인 에러 메시지: {error_text}")
            
            # 3. 대안 성공 지표 확인
            success_indicators = [
                'a[href*="reviews"]',  # 리뷰 링크
                '[class*="dashboard"]',  # 대시보드
                '.merchant-info',  # 매장 정보
            ]
            
            for selector in success_indicators:
                element = await page.query_selector(selector)
                if element:
                    logger.info(f"로그인 성공 (요소 기준: {selector})")
                    return True
            
            logger.error("로그인 실패 - 모든 지표가 실패")
            return False
                
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            # 스크린샷 저장 (디버깅용)
            try:
                await page.screenshot(path=f"login_error_{int(time.time())}.png")
            except:
                pass
            return False
    
    async def _navigate_to_reviews_page(self, page: Page):
        """리뷰 페이지로 이동"""
        try:
            logger.info("리뷰 페이지로 이동...")
            
            # 여러 방법으로 리뷰 페이지 접근 시도
            review_urls = [
                "https://store.coupangeats.com/merchant/management/reviews",
                f"https://store.coupangeats.com/merchant/management/reviews",
            ]
            
            for url in review_urls:
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    await page.wait_for_timeout(3000)
                    
                    # 페이지가 정상적으로 로드되었는지 확인
                    current_url = page.url
                    if "reviews" in current_url and "error" not in current_url.lower():
                        logger.info("리뷰 페이지 이동 완료")
                        return
                        
                except Exception as e:
                    logger.warning(f"URL {url} 접근 실패: {e}")
                    continue
            
            # 모든 시도 실패시 네비게이션 메뉴를 통한 접근
            logger.info("직접 URL 접근 실패, 네비게이션 메뉴 시도...")
            review_nav_selectors = [
                'a[href*="reviews"]',
                'nav a:has-text("리뷰")',
                '[data-testid*="review"]',
                'a:has-text("리뷰 관리")',
            ]
            
            for selector in review_nav_selectors:
                try:
                    nav_link = await page.query_selector(selector)
                    if nav_link:
                        await nav_link.click()
                        await page.wait_for_timeout(3000)
                        logger.info(f"네비게이션을 통한 리뷰 페이지 접근 완료: {selector}")
                        return
                except Exception:
                    continue
            
            raise Exception("리뷰 페이지 접근 불가")
            
        except Exception as e:
            logger.error(f"리뷰 페이지 이동 실패: {e}")
            raise
    
    async def _close_modal_if_exists(self, page: Page):
        """모달 창 닫기 (매장 불러오기와 동일한 방식 + 강화)"""
        try:
            logger.info("모달 창 탐지 및 닫기 시작...")
            
            # 1. 매장 불러오기에서 사용하는 정확한 Speak Up 모달 닫기 버튼
            close_button = await page.query_selector('button.dialog-modal-wrapper__body--close-button')
            if close_button:
                await close_button.click()
                logger.info("✅ 쿠팡잇츠 Speak Up 모달 닫기 성공 (dialog-modal-wrapper__body--close-button)")
                await page.wait_for_timeout(1000)
                return True
            
            # 2. 다양한 모달 닫기 버튼들 시도
            modal_close_selectors = [
                # 일반적인 모달 닫기 패턴들
                'button[class*="close"]',
                'button[class*="dialog-close"]', 
                'button.modal-close',
                '.modal-close',
                
                # 쿠팡잇츠 특화 패턴들  
                'button[class*="dialog-modal"]',
                'div[class*="dialog"] button',
                '[class*="modal-wrapper"] button',
                
                # 텍스트 기반 닫기 버튼들
                'button:has-text("닫기")',
                'button:has-text("확인")', 
                'button:has-text("OK")',
                'button:has-text("Close")',
                'button:has-text("×")',
                
                # 역할 기반 탐지
                '[role="dialog"] button',
                '[role="modal"] button',
                
                # 속성 기반 탐지
                'button[data-testid*="close"]',
                'button[data-testid*="modal"]',
                'button[aria-label*="close"]',
                'button[aria-label*="닫기"]',
                'button[title*="닫기"]',
                'button[title*="close"]',
                
                # X 버튼 패턴들
                'button:has(svg)',  # SVG 아이콘이 있는 버튼
                'button:has(span):has-text("×")',
                '.close-btn',
                '.btn-close',
            ]
            
            for i, selector in enumerate(modal_close_selectors):
                try:
                    close_button = await page.query_selector(selector)
                    if close_button:
                        # 버튼이 실제로 보이는지 확인
                        is_visible = await close_button.is_visible()
                        if is_visible:
                            await close_button.click()
                            logger.info(f"✅ 모달 창 닫기 성공: {selector}")
                            await page.wait_for_timeout(1000)
                            return True
                        else:
                            logger.debug(f"모달 버튼 존재하지만 숨겨짐: {selector}")
                            
                except Exception as e:
                    logger.debug(f"Selector {selector} 시도 중 오류: {e}")
                    continue
            
            # 3. JavaScript를 통한 모달 탐지 및 닫기
            try:
                modal_found = await page.evaluate('''
                    () => {
                        // 모든 가능한 모달 관련 요소들 찾기
                        const modalSelectors = [
                            '.modal', '.dialog', '.popup', '.overlay', 
                            '[role="dialog"]', '[role="modal"]',
                            '[class*="modal"]', '[class*="dialog"]', '[class*="popup"]'
                        ];
                        
                        for (const selector of modalSelectors) {
                            const modals = document.querySelectorAll(selector);
                            for (const modal of modals) {
                                if (modal.style.display !== 'none' && 
                                    window.getComputedStyle(modal).display !== 'none') {
                                    
                                    // 모달 내의 닫기 버튼 찾기
                                    const closeButtons = modal.querySelectorAll(
                                        'button, [role="button"], .close, .btn-close, [data-dismiss]'
                                    );
                                    
                                    for (const btn of closeButtons) {
                                        const text = btn.textContent.toLowerCase();
                                        const classes = btn.className.toLowerCase();
                                        
                                        if (text.includes('닫기') || text.includes('close') || 
                                            text.includes('×') || text.includes('확인') ||
                                            classes.includes('close') || classes.includes('cancel')) {
                                            
                                            btn.click();
                                            return true;
                                        }
                                    }
                                }
                            }
                        }
                        return false;
                    }
                ''')
                
                if modal_found:
                    logger.info("✅ JavaScript를 통한 모달 닫기 성공")
                    await page.wait_for_timeout(1000)
                    return True
                    
            except Exception as e:
                logger.debug(f"JavaScript 모달 닫기 오류: {e}")
            
            # 4. ESC 키로 모달 닫기 시도 (최후 수단)
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(500)
            logger.debug("ESC 키로 모달 닫기 시도")
            
            logger.info("모달을 찾을 수 없거나 이미 닫혀있음")
            return False
            
        except Exception as e:
            logger.debug(f"모달 창 닫기 시도 중 오류 (무시 가능): {e}")
            return False
    
    async def _select_store(self, page: Page, store_id: str):
        """매장 선택"""
        try:
            logger.info(f"매장 선택: {store_id}")
            
            # 여러 가능한 드롭다운 selector 시도
            dropdown_selectors = [
                '.button:has(svg)',
                'div.button:has(svg)', 
                '[class*="button"]:has(svg)',
                'button:has(svg)',
                '.css-12zocqj',  # 제공된 HTML의 span 클래스
                'div:has(span.css-12zocqj)',  # 상위 div
            ]
            
            dropdown_button = None
            for selector in dropdown_selectors:
                try:
                    dropdown_button = await page.query_selector(selector)
                    if dropdown_button:
                        logger.info(f"드롭다운 버튼 발견: {selector}")
                        break
                except Exception:
                    continue
            
            if dropdown_button:
                await dropdown_button.click()
                await page.wait_for_timeout(2000)  # 드롭다운 열리는 시간 증가
                
                # 매장 목록 selector 여러 시도
                option_selectors = [
                    '.options li',
                    'ul.options li',
                    'li.option-active',
                    'li:has-text("' + store_id + '")',
                    'li',  # 모든 li 요소
                ]
                
                store_options = []
                for selector in option_selectors:
                    try:
                        store_options = await page.query_selector_all(selector)
                        if store_options:
                            logger.info(f"매장 옵션 발견: {selector}, {len(store_options)}개")
                            break
                    except Exception:
                        continue
                
                if not store_options:
                    logger.warning("매장 옵션을 찾을 수 없습니다.")
                    return
                
                # 매장 찾기
                for option in store_options:
                    try:
                        option_text = await option.inner_text()
                        logger.debug(f"매장 옵션: {option_text}")
                        
                        # "매장명(store_id)" 형태에서 store_id 찾기
                        if f"({store_id})" in option_text or store_id in option_text:
                            await option.click()
                            logger.info(f"매장 선택 완료: {option_text}")
                            await page.wait_for_timeout(2000)
                            return
                    except Exception as e:
                        logger.debug(f"옵션 처리 중 오류: {e}")
                        continue
                        
                logger.warning(f"매장 ID {store_id}를 찾을 수 없습니다.")
            else:
                logger.warning("매장 드롭다운을 찾을 수 없습니다.")
                
        except Exception as e:
            logger.error(f"매장 선택 실패: {e}")
    
    async def _apply_date_filter(self, page: Page, days: int):
        """날짜 필터 적용"""
        try:
            logger.info(f"날짜 필터 적용: 최근 {days}일")
            
            # 여러 날짜 드롭다운 selector 시도
            date_dropdown_selectors = [
                '.css-1rkgd7l.eylfi1j5',
                'div:has-text("오늘"):has(svg)',
                '[class*="eylfi1j"]:has(svg)',
                'div:has(span:text("오늘"))',
                'div:has(svg):has-text("오늘")',
            ]
            
            date_dropdown = None
            for selector in date_dropdown_selectors:
                try:
                    date_dropdown = await page.query_selector(selector)
                    if date_dropdown:
                        logger.info(f"날짜 드롭다운 발견: {selector}")
                        break
                except Exception:
                    continue
            
            if date_dropdown:
                await date_dropdown.click()
                await page.wait_for_timeout(2000)
                
                # 날짜 옵션 선택 (라디오 버튼과 label 모두 시도)
                if days <= 7:
                    radio_selectors = [
                        # 제공된 HTML 구조에 맞는 정확한 selector들
                        'label:has(input[type="radio"][value="1"])',  # label 전체 클릭
                        'label:has-text("최근 1주일")',  # 텍스트로 label 찾기
                        'input[type="radio"][value="1"]',  # 실제 input
                        'input[name="quick"][value="1"]',  # name 속성으로 찾기
                        'label:has(input[name="quick"][value="1"])',  # label + name 조합
                        'span:has-text("최근 1주일")',  # span 텍스트
                    ]
                    
                    week_radio = None
                    for selector in radio_selectors:
                        try:
                            week_radio = await page.query_selector(selector)
                            if week_radio:
                                # 요소가 실제로 보이는지 확인
                                is_visible = await week_radio.is_visible()
                                if is_visible:
                                    logger.info(f"날짜 라디오 버튼 발견 (보임): {selector}")
                                    break
                                else:
                                    logger.debug(f"날짜 라디오 버튼 발견하지만 숨겨짐: {selector}")
                                    week_radio = None
                        except Exception as e:
                            logger.debug(f"날짜 라디오 selector {selector} 오류: {e}")
                            continue
                    
                    if week_radio:
                        try:
                            await week_radio.click()
                            logger.info("✅ 최근 1주일 선택 클릭 성공")
                            await page.wait_for_timeout(2000)  # 선택 후 충분히 대기
                            
                            # 실제로 선택되었는지 확인
                            selected = await page.evaluate('''
                                () => {
                                    const radio = document.querySelector('input[type="radio"][value="1"]');
                                    return radio ? radio.checked : false;
                                }
                            ''')
                            
                            if selected:
                                logger.info("✅ 최근 1주일 선택 확인됨")
                            else:
                                logger.warning("⚠️ 최근 1주일 선택이 확인되지 않음")
                                
                        except Exception as e:
                            logger.error(f"최근 1주일 선택 클릭 실패: {e}")
                    else:
                        logger.warning("최근 1주일 라디오 버튼을 찾을 수 없습니다.")
                else:
                    logger.info("7일을 초과하는 기간은 기본값을 사용합니다.")
            else:
                logger.warning("날짜 드롭다운을 찾을 수 없습니다.")
                    
        except Exception as e:
            logger.error(f"날짜 필터 적용 실패: {e}")
    
    async def _click_unanswered_tab(self, page: Page):
        """미답변 탭 클릭"""
        try:
            logger.info("미답변 탭 클릭")
            
            # 미답변 탭 selector들
            tab_selectors = [
                'strong:has-text("미답변")',
                'div:has-text("미답변")',
                'span:has-text("미답변")',
                '[class*="e1kgpv5e"]:has-text("미답변")',
                '.css-1cnakc9:has-text("미답변")',
                '.css-6by9e4:has-text("미답변")',
            ]
            
            unanswered_tab = None
            for selector in tab_selectors:
                try:
                    unanswered_tab = await page.query_selector(selector)
                    if unanswered_tab:
                        logger.info(f"미답변 탭 발견: {selector}")
                        break
                except Exception:
                    continue
            
            if unanswered_tab:
                # 여러 단계의 부모 요소에서 클릭 가능한 요소 찾기
                clickable_element = unanswered_tab
                
                for i in range(5):  # 최대 5단계 위로 올라가며 시도
                    try:
                        await clickable_element.click()
                        logger.info("미답변 탭 클릭 완료")
                        await page.wait_for_timeout(3000)  # 로딩 시간 증가
                        return
                    except Exception:
                        # 부모 요소로 이동
                        try:
                            clickable_element = await clickable_element.query_selector('xpath=..')
                            if not clickable_element:
                                break
                        except Exception:
                            break
                
                logger.warning("미답변 탭 클릭 실패 - 모든 부모 요소 시도 완료")
            else:
                logger.warning("미답변 탭을 찾을 수 없습니다.")
                
        except Exception as e:
            logger.error(f"미답변 탭 클릭 실패: {e}")
    
    async def _click_all_reviews_tab(self, page: Page):
        """전체 리뷰 탭 클릭"""
        try:
            logger.info("전체 리뷰 탭 클릭")
            
            # 여러 전체 탭 selector 시도
            all_reviews_selectors = [
                'strong:has-text("전체")',
                'div:has-text("전체")',
                'span:has-text("전체")',
                'strong:has-text("답변완료")',  # 답변완료 탭도 시도
                'div:has-text("답변완료")',
                '[class*="e1kgpv5e"]:has-text("전체")',
                '.css-1cnakc9:has-text("전체")',
                '.css-6by9e4:has-text("전체")',
            ]
            
            all_reviews_tab = None
            for selector in all_reviews_selectors:
                try:
                    all_reviews_tab = await page.query_selector(selector)
                    if all_reviews_tab:
                        logger.info(f"전체 리뷰 탭 발견: {selector}")
                        break
                except Exception:
                    continue
            
            if all_reviews_tab:
                # 여러 단계의 부모 요소에서 클릭 가능한 요소 찾기
                clickable_element = all_reviews_tab
                
                for i in range(5):  # 최대 5단계 위로 올라가며 시도
                    try:
                        await clickable_element.click()
                        logger.info("전체 리뷰 탭 클릭 완료")
                        await page.wait_for_timeout(3000)  # 로딩 시간 증가
                        return
                    except Exception:
                        # 부모 요소로 이동
                        try:
                            clickable_element = await clickable_element.query_selector('xpath=..')
                            if not clickable_element:
                                break
                        except Exception:
                            break
                
                logger.warning("전체 리뷰 탭 클릭 실패 - 모든 부모 요소 시도 완료")
            else:
                logger.warning("전체 리뷰 탭을 찾을 수 없습니다.")
                
        except Exception as e:
            logger.error(f"전체 리뷰 탭 클릭 실패: {e}")
    
    async def _collect_reviews(self, page: Page, max_pages: int) -> List[Dict[str, Any]]:
        """리뷰 수집"""
        reviews = []
        current_page = 1
        
        try:
            while current_page <= max_pages:
                logger.info(f"페이지 {current_page} 리뷰 수집 중...")
                
                # 현재 페이지의 리뷰 수집
                page_reviews = await self._extract_reviews_from_page(page)
                reviews.extend(page_reviews)
                
                logger.info(f"페이지 {current_page}에서 {len(page_reviews)}개 리뷰 수집")
                
                # 다음 페이지로 이동
                if current_page < max_pages:
                    has_next = await self._go_to_next_page(page)
                    if not has_next:
                        logger.info("다음 페이지가 없습니다.")
                        break
                
                current_page += 1
                await page.wait_for_timeout(2000)
                
        except Exception as e:
            logger.error(f"리뷰 수집 중 오류: {e}")
            
        logger.info(f"총 {len(reviews)}개 리뷰 수집 완료")
        return reviews
    
    async def _extract_reviews_from_page(self, page: Page) -> List[Dict[str, Any]]:
        """현재 페이지에서 리뷰 추출 (실제 리뷰 컨테이너 기준)"""
        reviews = []
        
        try:
            # 더 정확한 리뷰 컨테이너 찾기 - 주문번호가 있는 요소를 기준으로
            # 실제 개별 리뷰 아이템을 직접 찾는 방식으로 변경
            review_items = []
            
            # 실제 리뷰 데이터가 있는 컨테이너만 찾기
            # 1. 리뷰어 정보 클래스를 기준으로 찾기 (가장 확실한 방법)
            reviewer_elements = await page.query_selector_all('.css-hdvjju.eqn7l9b7')
            logger.info(f"리뷰어 정보 요소 {len(reviewer_elements)}개 발견")
            
            for reviewer_element in reviewer_elements:
                try:
                    # 리뷰어 요소에서 상위로 올라가며 완전한 리뷰 컨테이너 찾기
                    current = reviewer_element
                    for level in range(8):  # 최대 8단계 위로
                        parent = await current.query_selector('xpath=..')
                        if not parent:
                            break
                        
                        # 부모 요소의 크기와 내용 확인
                        try:
                            parent_text = await parent.inner_text()
                            parent_html = await parent.inner_html()
                            
                            # 완전한 리뷰 컨테이너인지 확인 - 모든 필수 요소가 있어야 함
                            has_reviewer = 'css-hdvjju' in parent_html and 'eqn7l9b7' in parent_html  # 리뷰어 정보
                            has_date = 'css-1bqps6x' in parent_html and 'eqn7l9b8' in parent_html  # 리뷰 날짜
                            has_order_info = '주문번호' in parent_text  # 주문 정보
                            has_reasonable_size = 100 < len(parent_text) < 1500  # 적절한 크기
                            
                            # SVG나 리뷰 텍스트 중 하나는 있어야 함 (별점만 있거나 리뷰 텍스트만 있거나)
                            has_rating_or_text = ('svg' in parent_html) or ('css-16m6tj' in parent_html and 'eqn7l9b5' in parent_html)
                            
                            # 페이지 헤더가 아닌지 확인
                            not_page_header = not any(bad in parent_text for bad in ['리뷰 관리', 'review-wrapper-title', '총평점', '미답변'])
                            
                            is_complete_review = (
                                has_reviewer and 
                                has_date and 
                                has_order_info and 
                                has_reasonable_size and
                                has_rating_or_text and
                                not_page_header
                            )
                            
                            if is_complete_review:
                                review_items.append(parent)
                                logger.debug(f"완전한 리뷰 컨테이너 발견 (레벨 {level}): {parent_text[:100]}...")
                                break
                                
                        except Exception:
                            pass
                        
                        current = parent
                        
                except Exception:
                    continue
            
            # 2. 백업: 주문번호가 있으면서 실제 리뷰 데이터도 있는 경우 추가로 찾기
            if len(review_items) < 3:  # 리뷰가 적게 발견된 경우 추가 검색
                order_number_elements = await page.query_selector_all('li:has(strong:has-text("주문번호"))')
                logger.info(f"백업 검색: 주문번호가 있는 요소 {len(order_number_elements)}개 발견")
                
                for order_element in order_number_elements:
                    try:
                        # 주문번호 요소에서 상위로 올라가며 실제 리뷰 컨테이너 찾기
                        current = order_element
                        for level in range(8):  # 최대 8단계 위로
                            parent = await current.query_selector('xpath=..')
                            if not parent:
                                break
                            
                            # 부모 요소의 크기와 내용 확인
                            try:
                                parent_text = await parent.inner_text()
                                parent_html = await parent.inner_html()
                                
                                # 실제 리뷰 데이터가 있는지 확인 (리뷰어 클래스 존재)
                                has_review_data = any(cls in parent_html for cls in ['css-hdvjju', 'eqn7l9b7'])
                                has_reasonable_size = 50 < len(parent_text) < 1000
                                has_order_info = '주문번호' in parent_text
                                not_page_header = not any(bad in parent_text for bad in ['리뷰 관리', 'review-wrapper-title', '총평점'])
                                
                                if has_review_data and has_reasonable_size and has_order_info and not_page_header:
                                    # 이미 추가된 컨테이너인지 확인
                                    is_duplicate = False
                                    for existing_item in review_items:
                                        try:
                                            existing_text = await existing_item.inner_text()
                                            if existing_text[:100] == parent_text[:100]:
                                                is_duplicate = True
                                                break
                                        except Exception:
                                            pass
                                    
                                    if not is_duplicate:
                                        review_items.append(parent)
                                        logger.debug(f"백업 리뷰 컨테이너 발견 (레벨 {level}): {parent_text[:50]}...")
                                    break
                                    
                            except Exception:
                                pass
                            
                            current = parent
                            
                    except Exception:
                        continue
            
            # 중복 제거
            unique_containers = []
            seen_texts = set()
            for container in review_items:
                try:
                    container_text = await container.inner_text()
                    text_key = container_text[:100]  # 처음 100자로 중복 판별
                    if text_key not in seen_texts:
                        unique_containers.append(container)
                        seen_texts.add(text_key)
                except Exception:
                    continue
            
            review_containers = unique_containers
            
            # 주문번호 기준으로 찾지 못하면 기존 방식 사용
            if not review_containers:
                logger.info("주문번호 기반 컨테이너를 찾을 수 없어 리뷰어 이름 기반으로 시도")
                reviewer_elements = await page.query_selector_all('.css-hdvjju.eqn7l9b7')
                
                # 리뷰어 요소를 기반으로 상위 컨테이너 찾기
                seen_containers = set()
                for reviewer_element in reviewer_elements:
                    try:
                        # 상위 요소로 올라가며 실제 리뷰 컨테이너 찾기
                        container = reviewer_element
                        for level in range(10):  # 최대 10단계 위로
                            container = await container.query_selector('xpath=..')
                            if not container:
                                break
                            
                            # 주문번호나 주문메뉴가 있는 컨테이너인지 확인
                            has_order_info = await container.query_selector('li:has(strong:has-text("주문"))') is not None
                            if has_order_info:
                                container_id = id(container)
                                if container_id not in seen_containers:
                                    review_containers.append(container)
                                    seen_containers.add(container_id)
                                break
                    except Exception:
                        continue
            
            logger.info(f"총 {len(review_containers)}개의 고유 리뷰 컨테이너 발견")
            
            # 1SU2MK 주문번호를 포함하는 리뷰 찾기 및 디버깅
            target_review_found = False
            for i, review_container in enumerate(review_containers):
                try:
                    container_text = await review_container.inner_text()
                    if "1SU2MK" in container_text:
                        logger.info(f"=== 1SU2MK 리뷰 발견 (컨테이너 {i+1}) ===")
                        html_content = await review_container.inner_html()
                        
                        # HTML 파일로 저장
                        filename = f"1SU2MK_review_structure.html"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>1SU2MK 리뷰 구조 분석</title>
</head>
<body>
    <h1>1SU2MK 리뷰 HTML 구조</h1>
    <div style="border: 1px solid #ccc; padding: 20px; margin: 10px;">
{html_content}
    </div>
</body>
</html>""")
                        logger.info(f"1SU2MK 리뷰 HTML 저장: {filename}")
                        
                        # 텍스트도 저장
                        text_filename = f"1SU2MK_review_text.txt"
                        with open(text_filename, 'w', encoding='utf-8') as f:
                            f.write(f"1SU2MK 리뷰 텍스트 내용:\n")
                            f.write("="*50 + "\n")
                            f.write(container_text)
                        logger.info(f"1SU2MK 리뷰 텍스트 저장: {text_filename}")
                        
                        target_review_found = True
                        break
                except Exception as e:
                    logger.error(f"1SU2MK 리뷰 분석 실패: {e}")
                    
            if not target_review_found:
                logger.warning("1SU2MK 리뷰를 찾을 수 없습니다.")
            
            # 첫 번째 리뷰의 HTML 구조 디버깅 출력
            if review_containers:
                logger.info("=== 첫 번째 리뷰 HTML 구조 디버깅 ===")
                first_review = review_containers[0]
                try:
                    html_content = await first_review.inner_html()
                    logger.info(f"첫 번째 리뷰 HTML: {html_content[:800]}...")
                    
                    # 첫 번째 리뷰도 파일로 저장
                    filename = f"first_review_structure.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>첫 번째 리뷰 구조 분석</title>
</head>
<body>
    <h1>첫 번째 리뷰 HTML 구조</h1>
    <div style="border: 1px solid #ccc; padding: 20px; margin: 10px;">
{html_content}
    </div>
</body>
</html>""")
                    logger.info(f"첫 번째 리뷰 HTML 저장: {filename}")
                    
                except Exception as e:
                    logger.error(f"HTML 디버깅 실패: {e}")
            
            # 각 컨테이너에서 리뷰 데이터 추출
            for i, review_container in enumerate(review_containers):
                try:
                    review_data = await self._extract_single_review(review_container, i + 1)
                    if review_data:
                        # 중복 체크 (주문번호나 해시 기준)
                        existing_ids = [r['coupangeats_review_id'] for r in reviews]
                        if review_data['coupangeats_review_id'] not in existing_ids:
                            reviews.append(review_data)
                            logger.debug(f"리뷰 추가: {review_data['reviewer_name']} (ID: {review_data['coupangeats_review_id']})")
                        else:
                            logger.debug(f"중복 리뷰 건너뛰기: {review_data['reviewer_name']} (ID: {review_data['coupangeats_review_id']})")
                        
                except Exception as e:
                    logger.error(f"리뷰 {i+1} 추출 실패: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"페이지 리뷰 추출 실패: {e}")
            
        return reviews
    
    async def _extract_single_review(self, review_element, review_number: int) -> Optional[Dict[str, Any]]:
        """개별 리뷰 데이터 추출 - 사용자 제공 HTML 구조 기반"""
        try:
            logger.debug(f"리뷰 {review_number} 추출 시작...")
            
            # 전체 텍스트 내용 가져오기 (디버깅용)
            full_text = await review_element.inner_text()
            logger.debug(f"리뷰 {review_number} 전체 텍스트: {full_text[:500]}...")
            
            # HTML 구조 디버깅
            html_content = await review_element.inner_html()
            logger.debug(f"리뷰 {review_number} HTML 구조: {html_content[:800]}...")
            
            # 1. 리뷰어 정보 추출 (.css-hdvjju.eqn7l9b7)
            reviewer_name = ""
            order_count = ""
            
            # 리뷰어 요소 찾기 (여러 방법 시도)
            reviewer_selectors = [
                '.css-hdvjju.eqn7l9b7',  # 기본 selector
                'div[class*="css-hdvjju"]',
                'div[class*="eqn7l9b7"]',
                'div:has(b)',  # b 태그가 있는 div
                'b'  # 직접 b 태그
            ]
            
            reviewer_element = None
            for selector in reviewer_selectors:
                try:
                    reviewer_element = await review_element.query_selector(selector)
                    if reviewer_element:
                        logger.debug(f"리뷰어 요소 발견: {selector}")
                        break
                except Exception:
                    continue
            
            if reviewer_element:
                reviewer_text = await reviewer_element.inner_text()
                logger.debug(f"리뷰어 정보: {reviewer_text}")
                
                # <b>엄**</b><b>3회 주문</b> 형태에서 분리
                # 또는 "엄**3회 주문" 형태
                import re
                
                # 리뷰어 이름 추출 (**가 포함된 부분)
                name_match = re.search(r'([^\n]*\*\*[^\n\d]*)', reviewer_text)
                if name_match:
                    reviewer_name = name_match.group(1).strip()
                
                # 주문횟수 추출
                order_match = re.search(r'(\d+회 \s*주문)', reviewer_text)
                if order_match:
                    order_count = order_match.group(1).strip()
                
                logger.debug(f"파싱 결과 - 리뷰어: '{reviewer_name}', 주문횟수: '{order_count}'")
            else:
                logger.warning("리뷰어 요소를 찾을 수 없습니다. HTML 구조를 확인해주세요.")
            
            # 2. 리뷰 날짜 추출 (.css-1bqps6x.eqn7l9b8)
            review_date = ""
            date_element = await review_element.query_selector('.css-1bqps6x.eqn7l9b8')
            if date_element:
                date_text = await date_element.inner_text()
                logger.debug(f"리뷰 날짜: {date_text}")
                
                # 날짜 형식 정규화 (2024.08.19 → 2024-08-19)
                import re
                date_match = re.search(r'(\d{4})[.\-](\d{2})[.\-](\d{2})', date_text)
                if date_match:
                    year, month, day = date_match.groups()
                    review_date = f"{year}-{month}-{day}"
            
            # 3. 리뷰 텍스트 추출 (.css-16m6tj.eqn7l9b5)
            review_text = None
            text_element = await review_element.query_selector('.css-16m6tj.eqn7l9b5')
            if text_element:
                review_text = await text_element.inner_text()
                if review_text:
                    review_text = review_text.strip()
                    if len(review_text) == 0:
                        review_text = None
            
            # 4. 주문번호와 주문일 추출
            coupangeats_review_id = ""
            order_date = ""
            
            order_info_element = await review_element.query_selector('li:has(strong:has-text("주문번호")) p')
            if order_info_element:
                order_info = await order_info_element.inner_text()
                logger.debug(f"주문 정보: {order_info}")
                
                # "0ELMJGㆍ2025-08-18(주문일)" 형태에서 추출
                import re
                
                # 주문번호 추출 (첫 번째 영숫자 조합)
                order_id_match = re.search(r'^([A-Z0-9]+)', order_info.strip())
                if order_id_match:
                    coupangeats_review_id = order_id_match.group(1)
                
                # 주문일 추출 (날짜 패턴)
                date_match = re.search(r'(\d{4}[-.]\d{2}[-.]\d{2})', order_info)
                if date_match:
                    date_str = date_match.group(1)
                    order_date = date_str.replace('.', '-')  # 2025.08.18 -> 2025-08-18
                
                logger.debug(f"파싱 결과 - 주문번호: '{coupangeats_review_id}', 주문일: '{order_date}'")
            
            # 5. 주문 메뉴 추출
            order_menu = ""
            menu_element = await review_element.query_selector('li:has(strong:has-text("주문메뉴")) p')
            if menu_element:
                order_menu = (await menu_element.inner_text()).strip()
                logger.debug(f"주문 메뉴: '{order_menu}'")
            
            # 6. 수령방식 추출
            delivery_method = ""
            delivery_element = await review_element.query_selector('li:has(strong:has-text("수령방식")) p')
            if delivery_element:
                delivery_method = await delivery_element.inner_text()
            
            # 7. 이미지 URL 추출
            image_element = await review_element.query_selector('img[src*="coupangcdn.com"]')
            image_url = await image_element.get_attribute('src') if image_element else None
            
            # 8. 별점 추출
            rating_data = await self.star_extractor.extract_rating_with_fallback(review_element)
            rating = rating_data.get('rating')
            
            # 리뷰 ID 생성 (주문번호 우선, 없으면 고유 해시)
            if coupangeats_review_id and coupangeats_review_id.strip():
                review_id = coupangeats_review_id.strip()
                logger.debug(f"주문번호 기반 ID 사용: {review_id}")
            else:
                # 더 고유한 해시 기반 ID 생성
                hash_input = f"{reviewer_name}_{review_date}_{order_date}_{review_text or 'no_text'}_{order_menu}_{delivery_method}_{review_number}_{datetime.now().isoformat()}"
                review_id = hashlib.md5(hash_input.encode()).hexdigest()[:12]
                logger.debug(f"해시 기반 ID 생성: {review_id}")
            
            # 기본값 설정 (NULL 방지)
            if not review_date and order_date:
                review_date = order_date
            elif not review_date:
                review_date = datetime.now().strftime('%Y-%m-%d')
            
            if not order_date and review_date:
                order_date = review_date
            elif not order_date:
                order_date = datetime.now().strftime('%Y-%m-%d')
            
            review_data = {
                'coupangeats_review_id': review_id,
                'reviewer_name': reviewer_name or "익명",
                'order_count': order_count or "",
                'rating': rating,
                'review_text': review_text,
                'review_date': review_date,
                'order_date': order_date,
                'order_menu_items': [order_menu] if order_menu else [],
                'delivery_method': delivery_method or "",
                'has_photos': bool(image_url),
                'photo_urls': [image_url] if image_url else [],
                'coupangeats_metadata': {
                    'order_count': order_count or "",
                    'delivery_method': delivery_method or "",
                    'extraction_method': rating_data.get('extraction_method', 'none'),
                    'rating_confidence': rating_data.get('confidence', 0.0),
                    'crawled_at': datetime.now().isoformat(),
                    'full_text_preview': full_text[:200]  # 디버깅용
                },
                'extracted_number': review_number
            }
            
            logger.info(f"리뷰 {review_number} 추출 완료: {reviewer_name} ({rating}점, {review_date})")
            return review_data
            
        except Exception as e:
            logger.error(f"리뷰 {review_number} 추출 실패: {e}")
            return None
    
    async def _go_to_next_page(self, page: Page) -> bool:
        """다음 페이지로 이동"""
        try:
            # Next 버튼 찾기
            next_button = await page.query_selector('button[data-at="next-btn"]:not(.hide-btn)')
            if next_button:
                await next_button.click()
                await page.wait_for_timeout(2000)
                logger.info("다음 페이지로 이동")
                return True
            else:
                logger.info("다음 페이지 버튼을 찾을 수 없습니다.")
                return False
                
        except Exception as e:
            logger.error(f"다음 페이지 이동 실패: {e}")
            return False
    
    async def _save_reviews(self, reviews: List[Dict[str, Any]], store_id: str) -> int:
        """리뷰 데이터를 데이터베이스에 저장"""
        if not reviews:
            return 0
        
        try:
            # platform_stores에서 UUID 조회
            store_response = self.supabase.table('platform_stores').select('id').eq('platform_store_id', store_id).eq('platform', 'coupangeats').execute()
            
            if not store_response.data:
                logger.error(f"매장을 찾을 수 없습니다: {store_id}")
                return 0
            
            platform_store_uuid = store_response.data[0]['id']
            logger.info(f"매장 UUID: {platform_store_uuid}")
            
            saved_count = 0
            
            for review in reviews:
                try:
                    # 리뷰 데이터 정리 (날짜 유효성 검사 포함)
                    review_insert = {
                        'platform_store_id': platform_store_uuid,
                        'coupangeats_review_id': review['coupangeats_review_id'],
                        'reviewer_name': review['reviewer_name'],
                        'rating': review['rating'],
                        'review_text': review['review_text'],
                        'review_date': review['review_date'] if review['review_date'] and review['review_date'].strip() else None,
                        'order_date': review['order_date'] if review['order_date'] and review['order_date'].strip() else None,
                        'order_menu_items': json.dumps(review['order_menu_items'], ensure_ascii=False),
                        'delivery_method': review['delivery_method'],
                        'order_count': review['order_count'],
                        'has_photos': review['has_photos'],
                        'photo_urls': json.dumps(review['photo_urls'], ensure_ascii=False),
                        'coupangeats_metadata': json.dumps(review['coupangeats_metadata'], ensure_ascii=False),
                        'reply_status': 'draft'
                    }
                    
                    # 개별 삽입 (중복 처리)
                    result = self.supabase.table('reviews_coupangeats').insert(review_insert).execute()
                    
                    if result.data:
                        saved_count += 1
                        logger.info(f"리뷰 저장 완료: {review['reviewer_name']} (ID: {review['coupangeats_review_id']})")
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        logger.info(f"중복 리뷰 건너뛰기: {review['reviewer_name']} (ID: {review['coupangeats_review_id']})")
                    else:
                        logger.error(f"리뷰 저장 실패: {review['reviewer_name']} - {e}")
            
            logger.info(f"총 {saved_count}개 리뷰 저장 완료")
            return saved_count
            
        except Exception as e:
            logger.error(f"리뷰 저장 중 오류: {e}")
            return 0


async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='쿠팡잇츠 리뷰 크롤러')
    parser.add_argument('--username', required=True, help='쿠팡잇츠 로그인 ID')
    parser.add_argument('--password', required=True, help='쿠팡잇츠 로그인 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID')
    parser.add_argument('--days', type=int, default=7, help='크롤링 기간 (기본: 7일)')
    parser.add_argument('--max-pages', type=int, default=5, help='최대 페이지 수 (기본: 5)')
    
    args = parser.parse_args()
    
    crawler = CoupangReviewCrawler()
    result = await crawler.crawl_reviews(
        username=args.username,
        password=args.password,
        store_id=args.store_id,
        days=args.days,
        max_pages=args.max_pages
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())