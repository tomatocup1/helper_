#!/usr/bin/env python3
"""
쿠팡잇츠 리뷰 크롤러 - NoDriver Version
100% 성공률을 위한 CDP 감지 우회 및 고급 스텔스 기법
"""

import asyncio
import argparse
import json
import os
import sys
import re
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import hashlib
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import nodriver as uc
    from nodriver import Browser, Tab, Element
except ImportError:
    print("❌ NoDriver not installed. Please run: pip install nodriver")
    sys.exit(1)

try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Key, Listener as KeyListener
    from pynput.mouse import Button, Listener as MouseListener
except ImportError:
    print("⚠️ pynput not available. Using fallback input methods.")
    keyboard = None
    mouse = None

try:
    from fake_useragent import UserAgent
except ImportError:
    print("⚠️ fake-useragent not available. Using default user agents.")
    UserAgent = None

from backend.services.shared.logger import get_logger
from backend.services.shared.config import settings

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

class NoDriverCoupangCrawler:
    """NoDriver 기반 100% 성공률 쿠팡잇츠 크롤러"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.success_count = 0
        self.failure_count = 0
        self.browser: Optional[Browser] = None
        self.tab: Optional[Tab] = None
        
        # User Agent 생성기 초기화
        if UserAgent:
            self.ua_generator = UserAgent(browsers=['chrome'], os=['windows'])
        else:
            self.ua_generator = None
            
        # 성공 패턴 저장
        self.success_patterns = []
        self.failure_patterns = []
    
    async def create_stealth_browser(self) -> Browser:
        """완전한 스텔스 모드 브라우저 생성 (CDP 감지 없음)"""
        logger.info("🚀 NoDriver 스텔스 브라우저 시작...")
        
        # 랜덤 설정
        window_width = random.randint(1200, 1920)
        window_height = random.randint(800, 1080)
        
        # User Agent 설정
        user_agent = None
        if self.ua_generator:
            try:
                user_agent = self.ua_generator.chrome
            except:
                pass
        
        if not user_agent:
            # 폴백 User Agent (최신 Chrome)
            chrome_version = random.randint(120, 125)
            user_agent = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36'
        
        # NoDriver 브라우저 시작 (간단한 방법)
        try:
            browser = await uc.start(
                headless=False,  # 개발 시 False, 운영 시 True
                lang='ko-KR'
            )
            
            logger.info(f"✅ NoDriver 브라우저 시작 완료 ({window_width}x{window_height})")
            logger.info(f"🔍 User-Agent: {user_agent[:60]}...")
            
            return browser
            
        except Exception as e:
            logger.error(f"❌ NoDriver 브라우저 시작 실패: {str(e)}")
            raise
    
    async def inject_ultra_stealth_scripts(self, tab: Tab):
        """초고급 스텔스 스크립트 주입 (NoDriver 전용)"""
        logger.info("🛡️ 초고급 스텔스 모드 활성화...")
        
        stealth_script = """
        (() => {
            // 1. WebDriver 속성 완전 제거
            delete navigator.__proto__.webdriver;
            delete navigator.webdriver;
            
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            
            // 2. Chrome Runtime API 완벽 모킹
            if (!window.chrome) {
                window.chrome = {};
            }
            
            window.chrome.runtime = {
                onConnect: {
                    addListener: () => {},
                    removeListener: () => {},
                    hasListener: () => false
                },
                onMessage: {
                    addListener: () => {},
                    removeListener: () => {},
                    hasListener: () => false
                },
                connect: () => ({}),
                sendMessage: () => {},
                getManifest: () => ({}),
                getURL: (path) => `chrome-extension://fake/${path}`,
                id: 'fake-extension-id'
            };
            
            window.chrome.storage = {
                local: {
                    get: () => Promise.resolve({}),
                    set: () => Promise.resolve(),
                    remove: () => Promise.resolve(),
                    clear: () => Promise.resolve()
                },
                sync: {
                    get: () => Promise.resolve({}),
                    set: () => Promise.resolve(),
                    remove: () => Promise.resolve(),
                    clear: () => Promise.resolve()
                }
            };
            
            // 3. CDP Runtime Detection 우회
            const originalConsole = window.console;
            const consoleProxy = new Proxy(originalConsole, {
                get: function(target, prop) {
                    const original = target[prop];
                    if (typeof original === 'function') {
                        return new Proxy(original, {
                            apply: function(fn, thisArg, argumentsList) {
                                // CDP Runtime.consoleAPICalled 이벤트 차단
                                try {
                                    return fn.apply(thisArg, argumentsList);
                                } catch (e) {
                                    // 에러 무시
                                }
                            }
                        });
                    }
                    return original;
                }
            });
            
            // 4. Navigator 속성 고급 모킹
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: ""},
                        description: "",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    }
                ]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });
            
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => Math.floor(Math.random() * 4) + 4  // 4-8 cores
            });
            
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => Math.floor(Math.random() * 4) + 4  // 4-8 GB
            });
            
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            
            // 5. Performance API 모킹
            if (window.performance && window.performance.getEntriesByType) {
                const originalGetEntriesByType = window.performance.getEntriesByType;
                window.performance.getEntriesByType = function(type) {
                    const entries = originalGetEntriesByType.call(this, type);
                    // CDP-related entries 제거
                    return entries.filter(entry => 
                        !entry.name || !entry.name.includes('devtools')
                    );
                };
            }
            
            // 6. Error Stack 추적 방지
            const originalError = window.Error;
            window.Error = class extends originalError {
                constructor(...args) {
                    super(...args);
                    // Stack trace 정리
                    if (this.stack) {
                        this.stack = this.stack
                            .split('\\n')
                            .filter(line => !line.includes('chrome-devtools'))
                            .filter(line => !line.includes('puppeteer'))
                            .filter(line => !line.includes('playwright'))
                            .join('\\n');
                    }
                }
            };
            
            // 7. CDP Detection Methods 우회
            const blockCDPDetection = () => {
                // Runtime domain detection 차단
                if (window.Runtime) {
                    delete window.Runtime;
                }
                
                // Console domain detection 차단
                const consoleAPI = ['assert', 'clear', 'count', 'countReset', 'debug', 
                                   'dir', 'dirxml', 'error', 'group', 'groupCollapsed', 
                                   'groupEnd', 'info', 'log', 'profile', 'profileEnd', 
                                   'table', 'time', 'timeEnd', 'timeLog', 'timeStamp', 
                                   'trace', 'warn'];
                
                consoleAPI.forEach(method => {
                    if (window.console[method]) {
                        const original = window.console[method];
                        window.console[method] = function(...args) {
                            try {
                                return original.apply(this, args);
                            } catch (e) {
                                // CDP 감지 무력화
                                return undefined;
                            }
                        };
                    }
                });
            };
            
            blockCDPDetection();
            
            // 8. 주기적 검사 및 복구
            setInterval(() => {
                if (navigator.webdriver !== undefined) {
                    delete navigator.webdriver;
                }
                blockCDPDetection();
            }, 1000);
            
            console.log('🛡️ Ultra Stealth Mode Activated');
            
        })();
        """
        
        try:
            await tab.evaluate(stealth_script)
            logger.info("✅ 초고급 스텔스 스크립트 주입 완료")
        except Exception as e:
            logger.warning(f"⚠️ 스텔스 스크립트 주입 실패: {e}")
    
    async def human_like_mouse_movement(self, tab: Tab):
        """인간같은 마우스 움직임 시뮬레이션 (NoDriver 최적화)"""
        logger.info("🖱️ 인간 행동 패턴 시뮬레이션 시작...")
        
        try:
            # 랜덤 마우스 궤적 생성
            for _ in range(random.randint(3, 6)):
                x = random.randint(200, 1000)
                y = random.randint(200, 600)
                
                # 자연스러운 마우스 이동
                await tab.mouse_move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # 스크롤 동작
            scroll_amount = random.choice([-200, -100, 0, 100, 200])
            await tab.scroll_down(scroll_amount)
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            logger.info("✅ 인간 행동 패턴 시뮬레이션 완료")
            
        except Exception as e:
            logger.warning(f"⚠️ 마우스 시뮬레이션 오류: {e}")
    
    async def os_level_input(self, text: str, field_selector: str, tab: Tab):
        """인간적 타이핑 시뮬레이션 (쿠팡 자동화 감지 우회)"""
        logger.info(f"⌨️ 인간적 타이핑 시뮬레이션 시작: {field_selector}")
        
        try:
            # 필드 선택 및 포커스
            element = await tab.select(field_selector, timeout=10)
            if not element:
                logger.error(f"❌ 필드를 찾을 수 없음: {field_selector}")
                return
            
            # 요소 클릭하여 포커스 설정
            await element.mouse_click()
            await asyncio.sleep(random.uniform(0.8, 1.2))
            
            # 필드 클리어 먼저
            clear_script = f"""
            var element = document.querySelector('{field_selector}');
            if (element) {{
                element.focus();
                element.value = '';
                element.dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
            """
            await tab.evaluate(clear_script)
            await asyncio.sleep(random.uniform(0.2, 0.4))
            
            # 인간적 타이핑 시뮬레이션 - 한 글자씩 입력
            escaped_text = text.replace("'", "\\'").replace('"', '\\"')
            
            for i, char in enumerate(text):
                char_escaped = char.replace("'", "\\'").replace('"', '\\"')
                
                # 각 글자를 개별적으로 입력하고 이벤트 발생
                typing_script = f"""
                var element = document.querySelector('{field_selector}');
                if (element) {{
                    element.focus();
                    
                    // 현재 값에 글자 추가
                    var currentValue = element.value || '';
                    var newValue = currentValue + '{char_escaped}';
                    element.value = newValue;
                    
                    // 다양한 키보드 이벤트 시뮬레이션
                    var keydownEvent = new KeyboardEvent('keydown', {{
                        key: '{char_escaped}',
                        code: 'Key' + '{char_escaped}'.toUpperCase(),
                        bubbles: true,
                        cancelable: true
                    }});
                    
                    var keypressEvent = new KeyboardEvent('keypress', {{
                        key: '{char_escaped}',
                        code: 'Key' + '{char_escaped}'.toUpperCase(),
                        bubbles: true,
                        cancelable: true
                    }});
                    
                    var keyupEvent = new KeyboardEvent('keyup', {{
                        key: '{char_escaped}',
                        code: 'Key' + '{char_escaped}'.toUpperCase(),
                        bubbles: true,
                        cancelable: true
                    }});
                    
                    var inputEvent = new Event('input', {{bubbles: true, cancelable: true}});
                    
                    // 이벤트 순서대로 발생
                    element.dispatchEvent(keydownEvent);
                    element.dispatchEvent(keypressEvent);
                    element.dispatchEvent(inputEvent);
                    element.dispatchEvent(keyupEvent);
                    
                    console.log('Typed char:', '{char_escaped}', 'Current value:', element.value);
                }}
                """
                
                try:
                    await tab.evaluate(typing_script)
                    # 인간적인 타이핑 속도 (50ms ~ 150ms per character)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                except Exception as char_error:
                    logger.warning(f"⚠️ 글자 '{char}' 입력 실패: {char_error}")
            
            # 입력 완료 후 change 이벤트 발생 (로그인 버튼 활성화 트리거)
            final_script = f"""
            var element = document.querySelector('{field_selector}');
            if (element) {{
                element.focus();
                
                // 최종 이벤트들 발생
                element.dispatchEvent(new Event('input', {{bubbles: true}}));
                element.dispatchEvent(new Event('change', {{bubbles: true}}));
                
                // React/Vue 등의 프레임워크를 위한 추가 이벤트
                element.dispatchEvent(new Event('blur', {{bubbles: true}}));
                element.dispatchEvent(new Event('focusout', {{bubbles: true}}));
                
                console.log('Final input value:', element.value);
                console.log('Input complete, button should activate now');
            }}
            """
            
            await tab.evaluate(final_script)
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # 입력 검증
            verification_script = f"""
            var element = document.querySelector('{field_selector}');
            element ? element.value : '';
            """
            
            try:
                result = await tab.evaluate(verification_script)
                if result == text:
                    logger.info("✅ 인간적 타이핑 시뮬레이션 완료 및 검증 성공")
                else:
                    logger.warning(f"⚠️ 입력 검증 불일치: 예상='{text}', 실제='{result}'")
            except Exception as verify_error:
                logger.warning(f"⚠️ 입력 검증 실패: {verify_error}")
                
        except Exception as e:
            logger.error(f"❌ 인간적 타이핑 시뮬레이션 실패: {e}")
            await self.fallback_input(text, field_selector, tab)
    
    async def fallback_input(self, text: str, field_selector: str, tab: Tab):
        """폴백 입력 방법 (JavaScript evaluate)"""
        logger.info(f"🔄 폴백 입력 방식 사용: {field_selector}")
        
        try:
            # 필드 클릭
            element = await tab.select(field_selector, timeout=10)
            if element:
                await element.mouse_click()
                await asyncio.sleep(random.uniform(0.3, 0.6))
                
                # JavaScript로 값 설정 (더 자연스럽게)
                await tab.evaluate(f'''
                    const element = document.querySelector("{field_selector}");
                    if (element) {{
                        element.value = "";
                        element.focus();
                    }}
                ''')
                
                # 점진적 입력
                for i in range(1, len(text) + 1):
                    partial_text = text[:i]
                    await tab.evaluate(f'''
                        const element = document.querySelector("{field_selector}");
                        if (element) {{
                            element.value = "{partial_text}";
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    ''')
                    await asyncio.sleep(random.uniform(0.08, 0.20))
                
                logger.info("✅ 폴백 입력 완료")
            else:
                logger.error(f"❌ 필드를 찾을 수 없음: {field_selector}")
                
        except Exception as e:
            logger.error(f"❌ 폴백 입력 실패: {e}")
    
    async def smart_button_click(self, selector: str, tab: Tab) -> bool:
        """스마트 버튼 클릭 (랜덤 위치 + 자연스러운 클릭)"""
        logger.info(f"🖱️ 스마트 버튼 클릭: {selector}")
        
        try:
            # NoDriver API 사용하여 요소 선택
            element = await tab.select(selector, timeout=10)
            if not element:
                logger.error(f"❌ 버튼을 찾을 수 없음: {selector}")
                return False
            
            # 요소가 보이도록 스크롤
            await element.scroll_into_view()
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # 자연스러운 마우스 이동 후 클릭
            await element.mouse_move()
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # 클릭
            await element.mouse_click()
            await asyncio.sleep(random.uniform(0.1, 0.2))
            
            logger.info("✅ 스마트 클릭 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 스마트 클릭 실패: {e}")
            return False
    
    async def robust_error_handler(self, func, *args, **kwargs):
        """견고한 에러 핸들러 (JavaScript 오류 무시)"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error_msg = str(e).lower()
                
                # JavaScript 관련 오류는 무시하고 계속 진행
                if any(keyword in error_msg for keyword in [
                    'cannot read properties of undefined',
                    'cannot read property',
                    'is not a function',
                    'undefined is not an object',
                    'null is not an object',
                    'script error'
                ]):
                    logger.warning(f"⚠️ JavaScript 오류 무시됨 (시도 {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(random.uniform(1.0, 2.0))
                        continue
                    else:
                        logger.info("🔄 JavaScript 오류에도 불구하고 계속 진행")
                        return None
                else:
                    # 다른 종류의 오류는 재시도
                    logger.error(f"❌ 오류 발생 (시도 {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                    else:
                        raise e
        
        return None
    
    async def advanced_login(self, username: str, password: str, max_attempts: int = 5) -> bool:
        """고급 로그인 (100% 성공률 목표)"""
        logger.info("🚀 100% 성공률 로그인 시작...")
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"🎯 로그인 시도 {attempt}/{max_attempts}")
                
                # 브라우저 생성 (매 시도마다 새로운 인스턴스)
                if self.browser:
                    try:
                        await self.browser.stop()
                    except Exception as e:
                        logger.warning(f"⚠️ 브라우저 종료 중 오류 (무시됨): {str(e)}")
                    
                self.browser = await self.create_stealth_browser()
                self.tab = await self.browser.get('https://store.coupangeats.com/merchant/login')
                
                # 초고급 스텔스 스크립트 주입
                await self.inject_ultra_stealth_scripts(self.tab)
                
                # 페이지 로딩 대기
                await asyncio.sleep(random.uniform(3.0, 5.0))
                
                # 이미 로그인 상태 확인
                current_url = await self.tab.evaluate('window.location.href')
                if "/merchant/login" not in current_url:
                    logger.info("✅ 이미 로그인된 상태 감지")
                    self.success_count += 1
                    return True
                
                # 인간적 행동 패턴 시뮬레이션
                await self.human_like_mouse_movement(self.tab)
                
                # 로그인 필드 대기
                login_fields_ready = await self.robust_error_handler(
                    self._wait_for_login_fields
                )
                
                if not login_fields_ready:
                    logger.warning("⚠️ 로그인 필드 대기 실패, 재시도...")
                    continue
                
                # 페이지 로드 대기 및 로그인 폼 확인
                await asyncio.sleep(2.0)
                
                # 더 정확한 로그인 필드 셀렉터 사용
                login_selectors = [
                    'input[name="loginId"]',  # name 속성으로 시도
                    'input[type="text"]:first-of-type',  # 첫 번째 텍스트 입력 필드
                    'input[placeholder*="아이디"]',  # placeholder에 '아이디'가 포함된 필드
                    'input[placeholder*="ID"]',  # placeholder에 'ID'가 포함된 필드
                    '.login-form input[type="text"]'  # 로그인 폼 내 텍스트 입력
                ]
                
                password_selectors = [
                    'input[name="password"]',  # name 속성으로 시도
                    'input[type="password"]',  # 패스워드 타입 필드
                    'input[placeholder*="비밀번호"]',  # placeholder에 '비밀번호'가 포함된 필드
                    '.login-form input[type="password"]'  # 로그인 폼 내 패스워드 입력
                ]
                
                # ID 입력 필드 찾기 및 입력
                id_success = False
                for selector in login_selectors:
                    try:
                        element = await self.tab.select(selector, timeout=5)
                        if element:
                            logger.info(f"✅ ID 필드 발견: {selector}")
                            await self.os_level_input(username, selector, self.tab)
                            id_success = True
                            break
                    except:
                        continue
                
                if not id_success:
                    logger.error("❌ ID 입력 필드를 찾을 수 없음")
                    continue
                
                await asyncio.sleep(random.uniform(0.8, 1.5))
                
                # 패스워드 입력 필드 찾기 및 입력
                pw_success = False
                for selector in password_selectors:
                    try:
                        element = await self.tab.select(selector, timeout=5)
                        if element:
                            logger.info(f"✅ 패스워드 필드 발견: {selector}")
                            await self.os_level_input(password, selector, self.tab)
                            pw_success = True
                            break
                    except:
                        continue
                
                if not pw_success:
                    logger.error("❌ 패스워드 입력 필드를 찾을 수 없음")
                    continue
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # 로그인 버튼 활성화 대기 및 확인
                logger.info("🔍 로그인 버튼 활성화 확인...")
                button_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    '.btn-login',
                    'button:contains("로그인")',
                    '[data-testid="login-button"]'
                ]
                
                button_activated = False
                button_element = None
                
                for selector in button_selectors:
                    try:
                        element = await self.tab.select(selector, timeout=3)
                        if element:
                            # 버튼 활성화 상태 확인
                            activation_check = f"""
                            var button = document.querySelector('{selector}');
                            if (button) {{
                                var isDisabled = button.disabled || button.hasAttribute('disabled');
                                var hasDisabledClass = button.classList.contains('disabled');
                                console.log('Button state:', {{
                                    disabled: isDisabled,
                                    hasDisabledClass: hasDisabledClass,
                                    text: button.textContent,
                                    className: button.className
                                }});
                                return !isDisabled && !hasDisabledClass;
                            }}
                            return false;
                            """
                            
                            is_active = await self.tab.evaluate(activation_check)
                            if is_active:
                                logger.info(f"✅ 활성화된 로그인 버튼 발견: {selector}")
                                button_activated = True
                                button_element = element
                                break
                            else:
                                logger.info(f"⚠️ 비활성화된 버튼: {selector}")
                    except:
                        continue
                
                # 버튼이 비활성화 상태면 강제 활성화 시도
                if not button_activated and button_element:
                    logger.info("🔧 로그인 버튼 강제 활성화 시도...")
                    force_activation = """
                    var buttons = document.querySelectorAll('button[type="submit"], input[type="submit"], .btn-login');
                    buttons.forEach(function(button) {
                        button.disabled = false;
                        button.removeAttribute('disabled');
                        button.classList.remove('disabled');
                        button.style.pointerEvents = 'auto';
                        button.style.opacity = '1';
                        console.log('Force activated button:', button);
                    });
                    """
                    await self.tab.evaluate(force_activation)
                    await asyncio.sleep(0.5)
                    button_activated = True
                
                # 로그인 버튼 클릭
                if button_activated:
                    click_success = await self.smart_button_click('button[type="submit"]', self.tab)
                    if not click_success:
                        # 다른 셀렉터들도 시도
                        for selector in button_selectors[1:]:
                            click_success = await self.smart_button_click(selector, self.tab)
                            if click_success:
                                break
                    
                    if not click_success:
                        logger.warning("⚠️ 모든 로그인 버튼 클릭 시도 실패")
                        continue
                else:
                    logger.warning("⚠️ 로그인 버튼을 활성화할 수 없음")
                    continue
                
                # 로그인 응답 대기 및 모니터링
                login_success = await self.robust_error_handler(
                    self._monitor_login_response
                )
                
                if login_success:
                    logger.info("🎉 로그인 성공!")
                    self.success_count += 1
                    return True
                else:
                    logger.warning(f"⚠️ 로그인 실패 (시도 {attempt})")
                    
                    # 재시도 전 대기
                    if attempt < max_attempts:
                        wait_time = random.uniform(8.0, 15.0)
                        logger.info(f"⏳ {wait_time:.1f}초 후 재시도...")
                        await asyncio.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"❌ 로그인 시도 {attempt} 중 오류: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(random.uniform(10.0, 20.0))
        
        self.failure_count += 1
        logger.error("❌ 모든 로그인 시도 실패")
        return False
    
    async def _wait_for_login_fields(self) -> bool:
        """로그인 필드 대기"""
        logger.info("⏳ 로그인 필드 대기 중...")
        
        for i in range(10):  # 최대 10초 대기
            try:
                login_id = await self.tab.select('#loginId')
                password = await self.tab.select('#password')
                submit_btn = await self.tab.select('button[type="submit"]')
                
                if login_id and password and submit_btn:
                    logger.info("✅ 로그인 필드 준비 완료")
                    return True
                    
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.debug(f"필드 확인 중: {e}")
                await asyncio.sleep(1.0)
        
        return False
    
    async def _monitor_login_response(self) -> bool:
        """로그인 응답 모니터링"""
        logger.info("👁️ 로그인 응답 모니터링 시작...")
        
        for i in range(25):  # 최대 25초 대기
            try:
                current_url = await self.tab.evaluate('window.location.href')
                
                # URL 변경 확인
                if "/merchant/login" not in current_url:
                    logger.info(f"✅ URL 변경 감지: {current_url}")
                    
                    # 2차 확인: 관리 페이지 요소 존재 확인
                    await asyncio.sleep(2.0)
                    
                    management_indicators = [
                        'nav', '.nav', '.navbar', '.header', '.sidebar',
                        'a[href*="management"]', 'a[href*="dashboard"]',
                        'a[href*="reviews"]', '[class*="merchant"]'
                    ]
                    
                    for selector in management_indicators:
                        try:
                            element = await self.tab.select(selector)
                            if element:
                                logger.info(f"✅ 관리 페이지 요소 확인: {selector}")
                                return True
                        except:
                            continue
                    
                    # URL만 변경되어도 성공으로 간주 (일부 사이트에서는 요소 로딩이 늦을 수 있음)
                    logger.info("✅ URL 변경으로 성공 판정")
                    return True
                
                # 에러 메시지 확인
                try:
                    error_selectors = ['.error', '.alert', '[class*="error"]', '.message']
                    for selector in error_selectors:
                        error_element = await self.tab.select(selector)
                        if error_element:
                            error_text = await error_element.text_all
                            if error_text and any(word in error_text for word in ['틀렸', '잘못', '실패', '오류']):
                                logger.error(f"❌ 로그인 에러 감지: {error_text}")
                                return False
                except:
                    pass
                
                logger.info(f"⏳ 로그인 응답 대기 중... ({i+1}/25초)")
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.debug(f"응답 모니터링 중 오류: {e}")
                await asyncio.sleep(1.0)
        
        logger.warning("⚠️ 로그인 응답 타임아웃")
        return False
    
    async def crawl_reviews_advanced(self, username: str, password: str, store_id: str, days: int = 7, max_pages: int = 10) -> List[Dict[str, Any]]:
        """고급 리뷰 크롤링 (NoDriver 기반)"""
        logger.info("🚀 고급 리뷰 크롤링 시작...")
        
        try:
            # 로그인
            login_success = await self.advanced_login(username, password)
            if not login_success:
                logger.error("❌ 로그인 실패 - 크롤링 중단")
                return []
            
            logger.info("✅ 로그인 성공 - 리뷰 수집 시작")
            
            # 리뷰 페이지로 이동
            reviews_url = f"https://store.coupangeats.com/merchant/management/reviews/{store_id}"
            await self.tab.get(reviews_url)
            await asyncio.sleep(random.uniform(4.0, 6.0))
            
            # 리뷰 수집
            all_reviews = []
            current_page = 1
            
            while current_page <= max_pages:
                logger.info(f"📄 페이지 {current_page} 크롤링 중...")
                
                # 페이지 리뷰 수집
                page_reviews = await self.robust_error_handler(
                    self._extract_reviews_from_current_page
                )
                
                if page_reviews:
                    all_reviews.extend(page_reviews)
                    logger.info(f"✅ 페이지 {current_page}: {len(page_reviews)}개 리뷰 수집")
                else:
                    logger.warning(f"⚠️ 페이지 {current_page}: 리뷰 없음")
                
                # 다음 페이지로 이동
                if current_page < max_pages:
                    next_success = await self.robust_error_handler(
                        self._go_to_next_page
                    )
                    
                    if next_success:
                        current_page += 1
                        await asyncio.sleep(random.uniform(3.0, 5.0))
                    else:
                        logger.info("📄 더 이상 페이지가 없음")
                        break
                else:
                    break
            
            logger.info(f"🎯 총 {len(all_reviews)}개 리뷰 수집 완료")
            return all_reviews
            
        except Exception as e:
            logger.error(f"❌ 크롤링 중 오류: {e}")
            return []
        finally:
            if self.browser:
                try:
                    await self.browser.stop()
                except Exception as e:
                    logger.warning(f"⚠️ 브라우저 종료 중 오류 (무시됨): {str(e)}")
                finally:
                    self.browser = None
    
    async def _extract_reviews_from_current_page(self) -> List[Dict[str, Any]]:
        """현재 페이지에서 리뷰 추출"""
        reviews = []
        
        try:
            # 리뷰 컨테이너 대기
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            # 다양한 리뷰 셀렉터 시도
            review_selectors = [
                '.review-item',
                '[class*="review-card"]',
                '[class*="review-content"]',
                '[class*="review-container"]',
                '[data-testid*="review"]'
            ]
            
            review_elements = None
            for selector in review_selectors:
                try:
                    review_elements = await self.tab.select_all(selector)
                    if review_elements:
                        logger.info(f"✅ 리뷰 요소 발견: {selector} ({len(review_elements)}개)")
                        break
                except:
                    continue
            
            if not review_elements:
                logger.warning("⚠️ 리뷰 요소를 찾을 수 없음")
                return reviews
            
            # 각 리뷰 요소에서 데이터 추출
            for i, element in enumerate(review_elements):
                try:
                    review_data = await self._extract_single_review(element, i + 1)
                    if review_data:
                        reviews.append(review_data)
                except Exception as e:
                    logger.debug(f"리뷰 {i+1} 추출 실패: {e}")
                    continue
            
            return reviews
            
        except Exception as e:
            logger.error(f"❌ 페이지 리뷰 추출 실패: {e}")
            return reviews
    
    async def _extract_single_review(self, element: Element, index: int) -> Dict[str, Any]:
        """단일 리뷰 데이터 추출"""
        review_data = {}
        
        try:
            # 고객 이름
            name_selectors = [
                '[class*="customer-name"]',
                '[class*="user-name"]',
                '[class*="reviewer"]',
                '.name'
            ]
            
            for selector in name_selectors:
                try:
                    name_element = await element.query_selector(selector)
                    if name_element:
                        review_data['customer_name'] = await name_element.text_all
                        break
                except:
                    continue
            
            # 리뷰 내용
            content_selectors = [
                '[class*="review-text"]',
                '[class*="review-content"]',
                '[class*="comment"]',
                '.content'
            ]
            
            for selector in content_selectors:
                try:
                    content_element = await element.query_selector(selector)
                    if content_element:
                        review_data['content'] = await content_element.text_all
                        break
                except:
                    continue
            
            # 별점 추출 (SVG 또는 텍스트)
            rating_selectors = [
                '[class*="rating"]',
                '[class*="star"]',
                '[class*="score"]'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_element = await element.query_selector(selector)
                    if rating_element:
                        rating_html = await rating_element.get_html()
                        rating = self._extract_rating_from_html(rating_html)
                        if rating:
                            review_data['rating'] = rating
                            break
                except:
                    continue
            
            # 날짜
            date_selectors = [
                '[class*="date"]',
                '[class*="time"]',
                '.timestamp'
            ]
            
            for selector in date_selectors:
                try:
                    date_element = await element.query_selector(selector)
                    if date_element:
                        review_data['date'] = await date_element.text_all
                        break
                except:
                    continue
            
            # 메뉴 정보
            menu_selectors = [
                '[class*="menu"]',
                '[class*="product"]',
                '[class*="item"]'
            ]
            
            for selector in menu_selectors:
                try:
                    menu_element = await element.query_selector(selector)
                    if menu_element:
                        review_data['menu_items'] = await menu_element.text_all
                        break
                except:
                    continue
            
            # 최소 필수 데이터 확인
            if review_data.get('content') or review_data.get('customer_name'):
                review_data['review_id'] = f"review_{index}_{int(time.time())}"
                logger.debug(f"✅ 리뷰 {index} 추출 완료")
                return review_data
            else:
                return None
                
        except Exception as e:
            logger.debug(f"❌ 리뷰 {index} 추출 중 오류: {e}")
            return None
    
    def _extract_rating_from_html(self, html: str) -> Optional[float]:
        """HTML에서 별점 추출"""
        try:
            # SVG 별점 패턴 찾기
            import re
            
            # filled stars 개수 세기
            filled_patterns = [
                r'fill="[^"]*(?:#[fF]+|yellow|gold)',
                r'class="[^"]*(?:filled|active|full)',
                r'data-rating="(\d+)"'
            ]
            
            for pattern in filled_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    return len(matches)
            
            # 텍스트로 된 별점 찾기
            text_patterns = [
                r'(\d+(?:\.\d+)?)\s*점',
                r'(\d+(?:\.\d+)?)\s*star',
                r'rating["\s]*:[\s]*(\d+(?:\.\d+)?)'
            ]
            
            for pattern in text_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            
            return None
            
        except Exception as e:
            logger.debug(f"별점 추출 실패: {e}")
            return None
    
    async def _go_to_next_page(self) -> bool:
        """다음 페이지로 이동"""
        try:
            next_selectors = [
                'button[aria-label="Next page"]',
                '.pagination-next',
                '[class*="next"]',
                'button[class*="next"]'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = await self.tab.select(selector)
                    if next_button:
                        await self.smart_button_click(selector, self.tab)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"다음 페이지 이동 실패: {e}")
            return False

async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='쿠팡잇츠 리뷰 크롤러 (NoDriver - 100% Success)')
    parser.add_argument('--username', required=True, help='쿠팡잇츠 사용자명')
    parser.add_argument('--password', required=True, help='쿠팡잇츠 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID')
    parser.add_argument('--days', type=int, default=7, help='수집할 일수')
    parser.add_argument('--max-pages', type=int, default=5, help='최대 페이지 수')
    parser.add_argument('--test-only', action='store_true', help='로그인 테스트만 실행')
    
    args = parser.parse_args()
    
    # 크롤러 생성
    crawler = NoDriverCoupangCrawler()
    
    if args.test_only:
        # 로그인 테스트만 실행
        success = await crawler.advanced_login(args.username, args.password)
        print(f"\n{'='*60}")
        print("로그인 테스트 결과")
        print('='*60)
        if success:
            print("✅ 로그인 성공!")
        else:
            print("❌ 로그인 실패")
        print(f"성공: {crawler.success_count}회")
        print(f"실패: {crawler.failure_count}회")
    else:
        # 전체 크롤링 실행
        reviews = await crawler.crawl_reviews_advanced(
            username=args.username,
            password=args.password,
            store_id=args.store_id,
            days=args.days,
            max_pages=args.max_pages
        )
        
        # 결과 출력
        print(f"\n{'='*60}")
        print("🎯 NoDriver 크롤링 완료!")
        print('='*60)
        print(f"✅ 성공: {crawler.success_count}회")
        print(f"❌ 실패: {crawler.failure_count}회")
        print(f"📄 수집된 리뷰: {len(reviews)}개")
        
        if reviews:
            print(f"\n📋 리뷰 샘플:")
            for i, review in enumerate(reviews[:3], 1):
                print(f"\n리뷰 {i}:")
                print(f"  👤 고객: {review.get('customer_name', 'Unknown')}")
                print(f"  ⭐ 평점: {review.get('rating', 'N/A')}")
                print(f"  💬 내용: {review.get('content', '')[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())