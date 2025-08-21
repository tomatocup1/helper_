#!/usr/bin/env python3
"""
네이버 자동 로그인 시스템
- 브라우저 프로필 기반 persistent context 사용
- 기기 등록 자동화 및 2차 인증 우회
- 계정별 세션 관리 및 재사용
"""

import os
import sys
import json
import hashlib
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 캐차 해결 모듈 임포트
try:
    from captcha_solver import CaptchaSolver
    CAPTCHA_SOLVER_AVAILABLE = True
except ImportError:
    CAPTCHA_SOLVER_AVAILABLE = False
    print("캐차 해결 모듈을 사용할 수 없습니다. 기본 로그인만 시도합니다.")

class NaverAutoLogin:
    def __init__(self, headless=True, timeout=30000, force_fresh_login=False):
        self.headless = headless
        self.timeout = timeout
        self.force_fresh_login = force_fresh_login
        self.browser_data_dir = os.path.join("logs", "browser_profiles", "naver")
        os.makedirs(self.browser_data_dir, exist_ok=True)
        
        # 캐차 해결 시스템을 수동 모드로 설정
        self.captcha_solver = None
        print("캐차 수동 해결 모드 활성화됨")
        
    def _get_browser_profile_path(self, platform_id: str) -> str:
        """계정별 브라우저 프로필 경로 생성"""
        account_hash = hashlib.md5(platform_id.encode()).hexdigest()[:10]
        profile_path = os.path.join(self.browser_data_dir, f"profile_{account_hash}")
        os.makedirs(profile_path, exist_ok=True)
        return profile_path
    
    def _get_consistent_user_agent(self) -> str:
        """일관된 User-Agent 반환"""
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    async def _close_popup_if_exists(self, page) -> bool:
        """로그인 후 나타나는 팝업 닫기"""
        try:
            print("팝업 확인 및 닫기 처리 중...")
            
            # 다양한 팝업 닫기 버튼 선택자들
            popup_close_selectors = [
                "i.fn-booking.fn-booking-close1",           # 사용자가 제공한 선택자
                ".fn-booking-close1",                       # 클래스만
                "i[aria-label='닫기']",                     # aria-label 속성
                ".popup_close",                             # 일반적인 팝업 닫기
                ".modal_close",                             # 모달 닫기
                "button[class*='close']",                   # 닫기 버튼
                ".btn_close",                               # 버튼 타입 닫기
                "[data-action='close']",                    # 데이터 액션
                ".layer_close"                              # 레이어 닫기
            ]
            
            for selector in popup_close_selectors:
                try:
                    # 팝업 요소가 있는지 확인 (짧은 타임아웃)
                    close_button = await page.wait_for_selector(selector, timeout=2000)
                    if close_button:
                        # 요소가 실제로 보이는지 확인
                        is_visible = await close_button.is_visible()
                        if is_visible:
                            print(f"팝업 닫기 버튼 발견: {selector}")
                            await close_button.click()
                            await page.wait_for_timeout(1000)  # 팝업 닫힘 대기
                            print("팝업 닫기 완료")
                            return True
                except Exception:
                    # 이 선택자로는 팝업을 찾지 못함, 다음 시도
                    continue
                    
            print("팝업이 없거나 이미 닫혀있음")
            return False
            
        except Exception as e:
            print(f"팝업 처리 중 오류: {str(e)}")
            return False
    
    async def _setup_browser_context(self, profile_path: str):
        """브라우저 컨텍스트 설정"""
        p = await async_playwright().start()
        
        # 브라우저 arguments
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-gpu',
            '--disable-web-security',
            '--no-sandbox',
            '--disable-features=VizDisplayCompositor'
        ]
        
        # Persistent context로 브라우저 시작
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=self.headless,
            args=browser_args,
            user_agent=self._get_consistent_user_agent(),
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            viewport={'width': 1280, 'height': 720},
            java_script_enabled=True,
            accept_downloads=True,
            ignore_https_errors=True
        )
        
        # 자동화 감지 방지 스크립트 추가
        await browser.add_init_script("""
            // Webdriver 속성 제거
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Chrome 속성 추가
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 플러그인 정보 설정
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 언어 설정
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });
            
            // 플랫폼 설정
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
        """)
        
        return browser, p
    
    async def login(self, platform_id: str, platform_password: str, keep_browser_open: bool = False) -> dict:
        """네이버 로그인 실행"""
        profile_path = self._get_browser_profile_path(platform_id)
        browser = None
        playwright = None
        
        try:
            print(f"Starting login for: {platform_id}")
            print(f"Profile path: {profile_path}")
            
            # 브라우저 설정
            browser, playwright = await self._setup_browser_context(profile_path)
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            # 기존 세션 확인 (참고용)
            has_existing_session = False
            if not self.force_fresh_login:
                session_check = await self._check_existing_session(page)
                has_existing_session = session_check['success']
                if has_existing_session:
                    print("기존 세션 감지됨 - 기기등록 건너뛰기 모드로 로그인 진행")
                else:
                    print("기존 세션 없음 - 전체 로그인 과정 진행")
            else:
                print("강제 새 로그인 모드 - 기존 세션 확인 건너뜀")
            
            print("새 로그인 시도...")
            
            # 현재 URL 확인
            current_url = page.url
            print(f"현재 페이지: {current_url}")
            
            # 이미 로그인 페이지에 있는지 확인
            if "nid.naver.com" not in current_url:
                # 로그인 페이지로 이동
                login_url = "https://nid.naver.com/nidlogin.login?svctype=1&locale=ko_KR&url=https%3A%2F%2Fnew.smartplace.naver.com%2F&area=bbt"
                print(f"로그인 페이지로 이동: {login_url}")
                await page.goto(login_url, wait_until='networkidle', timeout=self.timeout)
            else:
                print("이미 로그인 페이지에 있음")
            
            # 로그인 폼 작성
            await self._fill_login_form(page, platform_id, platform_password)
            
            # 로그인 버튼 클릭
            print("로그인 버튼 클릭 중...")
            try:
                # 파일에서 제공된 정확한 로그인 버튼 선택자
                login_selectors = [
                    "#log\\.login",                                    # 공식 선택자 (파일 제공)
                    "button.btn_login.off.next_step.nlog-click",      # 파일의 정확한 클래스 조합
                    "button[id='log.login']",                         # id 속성으로 직접 접근
                    "button[type='submit'].btn_login",                # submit + 클래스
                    ".btn_login",                                     # 클래스명으로 접근
                    "button[type='submit']"                           # submit 버튼 백업
                ]
                
                login_clicked = False
                for selector in login_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        await page.click(selector)
                        print(f"로그인 버튼 클릭 성공: {selector}")
                        login_clicked = True
                        break
                    except:
                        continue
                
                if not login_clicked:
                    raise Exception("로그인 버튼을 찾을 수 없습니다")
                    
            except Exception as e:
                print(f"로그인 버튼 클릭 실패: {str(e)}")
                # 페이지의 버튼들 확인
                try:
                    buttons = await page.query_selector_all("button, input[type='submit'], input[type='button']")
                    print(f"페이지에서 발견된 버튼 수: {len(buttons)}")
                    for i, btn in enumerate(buttons):
                        btn_text = await btn.text_content()
                        btn_id = await btn.get_attribute("id")
                        btn_class = await btn.get_attribute("class")
                        print(f"Button {i}: text='{btn_text}', id={btn_id}, class={btn_class}")
                except:
                    pass
                raise
            
            # 캐차 처리
            await asyncio.sleep(2)  # 로그인 후 페이지 로딩 대기
            current_url = page.url
            print(f"로그인 버튼 클릭 후 URL: {current_url}")
            
            # 캐차 간단 처리 - 기본 대기만
            if "captcha" in current_url.lower() or "nidlogin" in current_url:
                print("🔍 캐차 감지 - 3초 대기 후 진행")
                await asyncio.sleep(3)
            
            # 로그인 결과 대기 및 처리
            result = await self._handle_login_result(page, platform_id, profile_path, has_existing_session)
            
            # 브라우저를 유지할 경우 세션 정보에 브라우저 객체 추가
            if keep_browser_open and result['success']:
                result['browser'] = browser
                result['playwright'] = playwright
                result['page'] = page
                
            return result
            
        except Exception as e:
            print(f"로그인 중 오류 발생: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'session_id': None
            }
        finally:
            # 브라우저를 유지하지 않는 경우에만 정리
            if not keep_browser_open:
                if browser:
                    await browser.close()
                if playwright:
                    await playwright.stop()
            else:
                # 브라우저를 유지할 경우 반환값에 포함
                if browser and playwright:
                    print("브라우저 세션 유지 중 - 크롤링에서 재사용 예정")
    
    async def _check_existing_session(self, page) -> dict:
        """기존 세션 확인 - 매우 엄격한 로그인 상태 확인"""
        try:
            print("기존 세션 확인 중...")
            
            # 스마트플레이스 메인 페이지로 이동
            await page.goto("https://new.smartplace.naver.com/", timeout=self.timeout)
            await page.wait_for_timeout(5000)  # 충분한 대기 시간
            
            current_url = page.url
            print(f"이동 후 URL: {current_url}")
            
            # 로그인 페이지로 리디렉션 되었는지 확인
            if "nid.naver.com" in current_url:
                print("로그인이 필요함 - 로그인 페이지로 리디렉션됨")
                return {'success': False}
            
            # 실제 스마트플레이스 페이지인지 확인
            try:
                # 더 엄격한 세션 확인: 실제 로그인된 사용자만 접근 가능한 요소 확인
                await page.wait_for_timeout(3000)
                
                # 로그인된 사용자만 볼 수 있는 요소들을 더 구체적으로 확인
                user_specific_selectors = [
                    "a[href*='/smartplace/profile']",  # 프로필 링크
                    "a[href*='/my/']",                 # 마이페이지 링크
                    ".user_menu",                      # 사용자 메뉴
                    ".profile_area",                   # 프로필 영역
                    "button[data-test='user-menu']"    # 사용자 메뉴 버튼
                ]
                
                valid_session = False
                for selector in user_specific_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000)
                        if element:
                            # 요소가 실제로 보이는지 확인
                            is_visible = await element.is_visible()
                            if is_visible:
                                print(f"유효한 세션 요소 발견: {selector}")
                                valid_session = True
                                break
                    except:
                        continue
                
                # 추가 확인: 페이지에서 로그인 요구 버튼이나 폼 확인
                login_required_elements = await page.query_selector_all("a[href*='nid.naver.com'], button:has-text('로그인'), .login_btn")
                
                if len(login_required_elements) > 0:
                    print(f"로그인 요구 요소 발견: {len(login_required_elements)}개")
                    valid_session = False
                
                if valid_session:
                    print("기존 세션 유효함 - 확실한 로그인 상태 확인됨")
                    return {
                        'success': True,
                        'session_id': 'existing',
                        'device_registered': True,
                        'message': 'Existing session valid'
                    }
                else:
                    print("세션 무효 - 새로운 로그인 필요")
                    return {'success': False}
                    
            except Exception as e:
                print(f"세션 유효성 확인 실패: {str(e)} - 새 로그인 필요")
                return {'success': False}
            
        except Exception as e:
            print(f"세션 확인 중 오류: {str(e)} - 새 로그인 필요")
            return {'success': False}
    
    async def _fill_login_form(self, page, platform_id: str, platform_password: str):
        """로그인 폼 작성"""
        print("로그인 폼 작성 중...")
        
        try:
            # 파일에서 제공된 정확한 ID 입력 필드 선택자
            print("ID 입력 필드 찾는 중...")
            id_selectors = [
                "#id",                                    # 기본 선택자
                "input[name='id']",                       # name 속성 기반
                "input.input_id",                         # 파일에서 제공된 클래스
                "input[title='아이디']",                   # title 속성 기반
                "input[aria-label='아이디 또는 전화번호']"  # aria-label 기반
            ]
            
            id_filled = False
            for selector in id_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    await page.fill(selector, "")  # 기존 내용 클리어
                    await page.fill(selector, platform_id)
                    await page.wait_for_timeout(500)
                    print(f"ID 입력 완료 ({selector}): {platform_id}")
                    id_filled = True
                    break
                except:
                    continue
                    
            if not id_filled:
                raise Exception("ID 입력 필드를 찾을 수 없습니다")
            
            # 파일에서 제공된 정확한 비밀번호 입력 필드 선택자
            print("비밀번호 입력 필드 찾는 중...")
            pw_selectors = [
                "#pw",                                    # 기본 선택자
                "input[name='pw']",                       # name 속성 기반
                "input.input_pw",                         # 파일에서 제공된 클래스
                "input[type='password']",                 # type 속성 기반
                "input[title='비밀번호']",                 # title 속성 기반
                "input[aria-label='비밀번호']"             # aria-label 기반
            ]
            
            pw_filled = False
            for selector in pw_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    await page.fill(selector, "")  # 기존 내용 클리어
                    await page.fill(selector, platform_password)
                    await page.wait_for_timeout(500)
                    print(f"비밀번호 입력 완료 ({selector})")
                    pw_filled = True
                    break
                except:
                    continue
                    
            if not pw_filled:
                raise Exception("비밀번호 입력 필드를 찾을 수 없습니다")
            
            print("로그인 정보 입력 완료")
            
        except Exception as e:
            print(f"로그인 폼 작성 중 오류: {str(e)}")
            # 현재 페이지 정보 출력
            current_url = page.url
            print(f"현재 URL: {current_url}")
            
            # 페이지에 있는 input 필드들 확인
            try:
                inputs = await page.query_selector_all("input")
                print(f"페이지에서 발견된 input 필드 수: {len(inputs)}")
                for i, inp in enumerate(inputs):
                    inp_type = await inp.get_attribute("type")
                    inp_id = await inp.get_attribute("id")
                    inp_name = await inp.get_attribute("name")
                    print(f"Input {i}: type={inp_type}, id={inp_id}, name={inp_name}")
            except:
                pass
            
            raise
    
    async def _handle_login_result(self, page, platform_id: str, profile_path: str, has_existing_session: bool = False) -> dict:
        """로그인 결과 처리"""
        try:
            # 로그인 후 리디렉션 대기
            await page.wait_for_timeout(3000)
            current_url = page.url
            
            print(f"로그인 후 URL: {current_url}")
            
            # 기기 등록 페이지 확인
            if "deviceConfirm" in current_url:
                if has_existing_session:
                    print("⚠️ 경고: 기존 세션이 있음에도 기기등록 페이지 나타남 - 세션 만료 가능성")
                print("기기 등록 페이지 감지 - 자동 등록 진행")
                return await self._handle_device_registration(page, platform_id, profile_path)
            elif has_existing_session and "deviceConfirm" not in current_url:
                print("✅ 기존 세션 활용 성공 - 기기등록 페이지 건너뛰기 완료")
            
            # 2차 인증 페이지 확인 (파일에서 명시된 URL 패턴 포함)
            elif "need2" in current_url or "nid.naver.com/login/ext/need2" in current_url:
                print("2차 인증 페이지 감지")
                print(f"2차 인증 URL: {current_url}")
                
                # 기존 세션이 있었다면 세션 만료로 판단
                if has_existing_session:
                    print("⚠️ 기존 세션이 있었으나 2차 인증 요구됨 - 세션 만료 가능성")
                
                return {
                    'success': False,
                    'error': '2차 인증이 필요합니다. 브라우저 프로필이 만료되었을 수 있습니다.',
                    'session_id': None,
                    'requires_2fa': True,
                    'suggestion': '프로필을 삭제하고 다시 기기 등록을 시도하세요.'
                }
            
            # 로그인 오류 페이지 확인
            elif "nid.naver.com" in current_url and "error" in current_url:
                error_text = await self._extract_error_message(page)
                return {
                    'success': False,
                    'error': f'로그인 실패: {error_text}',
                    'session_id': None
                }
            
            # 성공적인 로그인
            elif "smartplace.naver.com" in current_url:
                success_msg = "로그인 성공"
                if has_existing_session:
                    success_msg += " (기존 세션 활용으로 기기등록 건너뛰기)"
                print(success_msg)
                
                return await self._save_session_info(platform_id, profile_path, device_registered=True)
            
            # 기타 경우
            else:
                await page.wait_for_timeout(5000)  # 추가 대기
                final_url = page.url
                
                if "smartplace.naver.com" in final_url:
                    success_msg = "로그인 성공 (지연된 리디렉션)"
                    if has_existing_session:
                        success_msg += " (기존 세션 활용으로 기기등록 건너뛰기)"
                    print(success_msg)
                    
                    return await self._save_session_info(platform_id, profile_path, device_registered=True)
                else:
                    print(f"예상치 못한 URL: {final_url}")
                    return {
                        'success': False,
                        'error': f'예상치 못한 리디렉션: {final_url}',
                        'session_id': None
                    }
            
        except Exception as e:
            print(f"로그인 결과 처리 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'session_id': None
            }
    
    async def _handle_device_registration(self, page, platform_id: str, profile_path: str) -> dict:
        """기기 등록 처리"""
        try:
            print("기기 등록 진행 중...")
            
            # 파일에서 제공된 정확한 기기 등록 버튼 선택자
            registration_selectors = [
                "#new\\.save",                           # 파일에서 제공된 정확한 선택자
                "a[id='new.save']",                      # id 속성 기반
                "a.btn[href='#']",                       # 파일의 정확한 구조
                "a.btn:has-text('등록')",                # 텍스트 기반
                "button:has-text('등록')",               # 버튼 버전
                ".btn:has-text('등록')"                  # 클래스 기반
            ]
            
            registration_clicked = False
            for selector in registration_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    await page.click(selector)
                    print(f"등록 버튼 클릭 성공: {selector}")
                    registration_clicked = True
                    break
                except:
                    continue
            
            if not registration_clicked:
                # 페이지의 모든 링크와 버튼 확인
                try:
                    buttons = await page.query_selector_all("a, button")
                    print(f"페이지에서 발견된 링크/버튼 수: {len(buttons)}")
                    for i, btn in enumerate(buttons):
                        btn_text = await btn.text_content()
                        btn_href = await btn.get_attribute("href")
                        if btn_text and ("등록" in btn_text or "register" in btn_text.lower()):
                            print(f"등록 관련 요소 {i}: text='{btn_text}', href={btn_href}")
                            try:
                                await btn.click()
                                print(f"등록 버튼 대체 클릭 성공")
                                registration_clicked = True
                                break
                            except:
                                continue
                except:
                    pass
            
            if not registration_clicked:
                raise Exception("등록 버튼을 찾을 수 없습니다")
            
            # 등록 완료 대기 및 리디렉션 확인
            print("등록 처리 대기 중...")
            await page.wait_for_timeout(5000)
            
            # 스마트플레이스로 리디렉션 확인 (URL 패턴 여러개 시도)
            final_url = page.url
            print(f"등록 후 URL: {final_url}")
            
            if "smartplace.naver.com" in final_url:
                print("기기 등록 완료 및 스마트플레이스 접속 확인")
                
                return await self._save_session_info(platform_id, profile_path, device_registered=True)
            else:
                # 추가 대기 후 재확인
                await page.wait_for_timeout(5000)
                final_url = page.url
                if "smartplace.naver.com" in final_url:
                    print("기기 등록 완료 (지연된 리디렉션)")
                    
                    return await self._save_session_info(platform_id, profile_path, device_registered=True)
                else:
                    print(f"예상치 못한 등록 후 URL: {final_url}")
                    return {
                        'success': False,
                        'error': f'기기 등록 후 예상치 못한 페이지: {final_url}',
                        'session_id': None
                    }
            
        except Exception as e:
            print(f"기기 등록 중 오류: {str(e)}")
            return {
                'success': False,
                'error': f'기기 등록 실패: {str(e)}',
                'session_id': None
            }
    
    async def _extract_error_message(self, page) -> str:
        """오류 메시지 추출"""
        try:
            # 일반적인 오류 메시지 선택자들
            error_selectors = [
                ".error_msg",
                ".error_message", 
                "#err_common",
                ".login_error"
            ]
            
            for selector in error_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    error_text = await element.text_content()
                    if error_text and error_text.strip():
                        return error_text.strip()
                except:
                    continue
            
            return "알 수 없는 로그인 오류"
            
        except Exception:
            return "오류 메시지를 추출할 수 없음"
    
    async def _save_session_info(self, platform_id: str, profile_path: str, device_registered: bool = False) -> dict:
        """세션 정보 저장 (기존 platform_stores 테이블 활용)"""
        try:
            session_id = hashlib.md5(platform_id.encode()).hexdigest()[:10]
            
            # 로컬 세션 정보 파일 저장 (파일에서 명시된 구조 기반)
            current_time = datetime.now()
            session_info = {
                "platform_id": platform_id,
                "session_id": session_id,
                "profile_path": profile_path,
                "device_registered": device_registered,
                "login_time": current_time.isoformat(),
                "expires_at": current_time.isoformat(),
                "naver_session_active": True,
                "naver_device_registered": device_registered,
                "naver_last_login": current_time.isoformat(),
                # 파일에서 명시된 추가 정보
                "browser_fingerprint": {
                    "user_agent": self._get_consistent_user_agent(),
                    "viewport": "1280x720",
                    "locale": "ko-KR",
                    "timezone": "Asia/Seoul"
                },
                "authentication_history": {
                    "first_registration": current_time.isoformat() if device_registered else None,
                    "last_success": current_time.isoformat(),
                    "bypass_2fa": device_registered
                }
            }
            
            session_file = os.path.join(profile_path, "session_info.json")
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, ensure_ascii=False, indent=2)
            
            # platform_stores 테이블 업데이트용 정보 준비
            platform_stores_update = {
                'naver_session_active': True,
                'naver_last_login': datetime.now().isoformat(),
                'naver_device_registered': device_registered,
                'naver_profile_path': profile_path,
                'naver_login_attempts': 0,  # 성공시 0으로 리셋
                'last_crawled_at': None,  # 다음 크롤링을 위해 초기화
                'next_crawl_at': datetime.now().isoformat()
            }
            
            print(f"세션 정보 저장 완료: {session_file}")
            print(f"platform_stores 업데이트 정보 준비됨")
            
            return {
                'success': True,
                'session_id': session_id,
                'profile_path': profile_path,
                'device_registered': device_registered,
                'platform_stores_update': platform_stores_update,
                'message': 'Login successful - ready for platform_stores update'
            }
            
        except Exception as e:
            print(f"세션 정보 저장 중 오류: {str(e)}")
            return {
                'success': False,
                'error': f'세션 저장 실패: {str(e)}',
                'session_id': None
            }

async def main():
    parser = argparse.ArgumentParser(description='네이버 자동 로그인')
    parser.add_argument('--email', required=True, help='네이버 이메일/아이디')
    parser.add_argument('--password', required=True, help='네이버 비밀번호')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드')
    parser.add_argument('--timeout', type=int, default=30000, help='타임아웃 (ms)')
    parser.add_argument('--force-fresh', action='store_true', help='기존 세션 무시하고 강제 새 로그인')
    
    args = parser.parse_args()
    
    login_system = NaverAutoLogin(
        headless=args.headless, 
        timeout=args.timeout,
        force_fresh_login=args.force_fresh
    )
    result = await login_system.login(args.email, args.password)
    
    # 결과 출력 (JSON 형태)
    print(f"LOGIN_RESULT:{json.dumps(result, ensure_ascii=False)}")
    
    return result['success']

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)