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
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import hashlib
try:
    import pyperclip  # 클립보드 제어용
except ImportError:
    pyperclip = None
    print("Warning: pyperclip not installed. Using fallback typing method.")

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from backend.services.shared.logger import get_logger
from backend.services.shared.config import settings
from backend.core.coupang_star_rating_extractor import CoupangStarRatingExtractor

# 프록시 및 User-Agent 로테이션 시스템 import (optional)
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from free_proxy_manager import FreeProxyManager
    from user_agent_rotator import UserAgentRotator
except ImportError:
    print("Warning: 프록시 및 User-Agent 로테이션 시스템을 가져올 수 없습니다. 기본 설정을 사용합니다.")
    FreeProxyManager = None
    UserAgentRotator = None

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

# 실제 User-Agent 목록 (최신 버전들)
REAL_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

def get_random_user_agent():
    """랜덤한 실제 User-Agent 반환"""
    return random.choice(REAL_USER_AGENTS)

class LoginMonitor:
    """로그인 프로세스 실시간 모니터링"""
    
    def __init__(self):
        self.network_requests = []
        self.console_messages = []
        self.page_errors = []
        self.success_indicators = []
        self.failure_indicators = []
        self.timing_data = {}
        self.start_time = None
        
    def reset(self):
        """모니터링 데이터 초기화"""
        self.network_requests.clear()
        self.console_messages.clear()
        self.page_errors.clear()
        self.success_indicators.clear()
        self.failure_indicators.clear()
        self.timing_data.clear()
        self.start_time = time.time()
        
    def log_request(self, request):
        """네트워크 요청 로그"""
        timing = time.time() - self.start_time if self.start_time else 0
        req_data = {
            'timing': timing,
            'method': request.method,
            'url': request.url,
            'headers': dict(request.headers),
            'resource_type': request.resource_type
        }
        self.network_requests.append(req_data)
        logger.debug(f"[Monitor] REQ {timing:.2f}s {request.method} {request.url}")
        
    def log_response(self, response):
        """네트워크 응답 로그"""
        timing = time.time() - self.start_time if self.start_time else 0
        res_data = {
            'timing': timing,
            'status': response.status,
            'url': response.url,
            'headers': dict(response.headers),
            'ok': response.ok
        }
        # 실패 응답 감지
        if response.status >= 400:
            self.failure_indicators.append(f"HTTP {response.status}: {response.url}")
            logger.warning(f"[Monitor] RES {timing:.2f}s {response.status} {response.url}")
        else:
            logger.debug(f"[Monitor] RES {timing:.2f}s {response.status} {response.url}")
            
    def log_console(self, msg):
        """콘솔 메시지 로그"""
        timing = time.time() - self.start_time if self.start_time else 0
        console_data = {
            'timing': timing,
            'type': msg.type,
            'text': msg.text,
            'location': msg.location
        }
        self.console_messages.append(console_data)
        
        # 에러 패턴 감지
        text = msg.text.lower()
        if any(word in text for word in ['error', 'failed', 'timeout', '에러', '실패']):
            self.failure_indicators.append(f"Console Error: {msg.text}")
            logger.error(f"[Monitor] CON {timing:.2f}s ERROR: {msg.text}")
        else:
            logger.debug(f"[Monitor] CON {timing:.2f}s {msg.type}: {msg.text}")
            
    def log_page_error(self, error):
        """페이지 에러 로그"""
        timing = time.time() - self.start_time if self.start_time else 0
        self.page_errors.append({
            'timing': timing,
            'message': str(error),
            'name': getattr(error, 'name', 'Unknown'),
            'stack': getattr(error, 'stack', '')
        })
        self.failure_indicators.append(f"Page Error: {str(error)}")
        logger.error(f"[Monitor] ERR {timing:.2f}s {str(error)}")
        
    def analyze_patterns(self):
        """고도화된 패턴 분석"""
        total_time = time.time() - self.start_time if self.start_time else 0
        
        # 기본 메트릭
        analysis = {
            'total_requests': len(self.network_requests),
            'failed_requests': len([r for r in self.network_requests if 'status' in r and r.get('status', 0) >= 400]),
            'console_errors': len([m for m in self.console_messages if m['type'] == 'error']),
            'page_errors': len(self.page_errors),
            'success_indicators': len(self.success_indicators),
            'failure_indicators': len(self.failure_indicators),
            'total_time': total_time
        }
        
        # 네트워크 패턴 분석
        network_analysis = self._analyze_network_patterns()
        analysis.update(network_analysis)
        
        # 타이밍 패턴 분석
        timing_analysis = self._analyze_timing_patterns()
        analysis.update(timing_analysis)
        
        # 에러 패턴 분석
        error_analysis = self._analyze_error_patterns()
        analysis.update(error_analysis)
        
        # 성공 예측 점수 계산
        analysis['success_prediction_score'] = self._calculate_success_score(analysis)
        
        return analysis
    
    def _analyze_network_patterns(self):
        """네트워크 패턴 상세 분석"""
        # 중요한 API 호출 분석
        login_api_calls = [r for r in self.network_requests if 'login' in r.get('url', '').lower()]
        weblog_requests = [r for r in self.network_requests if 'weblog' in r.get('url', '').lower()]
        static_resources = [r for r in self.network_requests if r.get('resource_type') in ['stylesheet', 'script', 'image']]
        
        # 응답 시간 분석
        request_times = []
        for req in self.network_requests:
            if 'timing' in req:
                request_times.append(req['timing'])
        
        avg_response_time = sum(request_times) / len(request_times) if request_times else 0
        
        return {
            'login_api_calls': len(login_api_calls),
            'weblog_blocked': len(weblog_requests),
            'static_resources': len(static_resources),
            'avg_response_time': avg_response_time,
            'request_timeline': request_times[:10]  # 처음 10개 요청의 타이밍
        }
    
    def _analyze_timing_patterns(self):
        """타이밍 패턴 분석"""
        if not self.start_time:
            return {}
            
        # 주요 이벤트별 타이밍
        timing_events = {}
        
        # 첫 번째 네트워크 요청까지의 시간
        if self.network_requests:
            first_request_time = min(r.get('timing', float('inf')) for r in self.network_requests)
            timing_events['first_request'] = first_request_time
        
        # 첫 번째 콘솔 메시지까지의 시간
        if self.console_messages:
            first_console_time = min(m.get('timing', float('inf')) for m in self.console_messages)
            timing_events['first_console'] = first_console_time
        
        # 로그인 API 호출 시간
        login_requests = [r for r in self.network_requests if 'login' in r.get('url', '').lower()]
        if login_requests:
            login_api_time = min(r.get('timing', float('inf')) for r in login_requests)
            timing_events['login_api_call'] = login_api_time
        
        return {
            'timing_events': timing_events,
            'critical_timing_threshold': 30.0,  # 30초 이상은 문제
            'optimal_timing_range': (5.0, 15.0)  # 5-15초가 최적
        }
    
    def _analyze_error_patterns(self):
        """에러 패턴 분석"""
        # 에러 발생 시점 분석
        error_timeline = []
        
        # 콘솔 에러
        for msg in self.console_messages:
            if msg['type'] == 'error':
                error_timeline.append({
                    'time': msg.get('timing', 0),
                    'type': 'console',
                    'message': msg['text']
                })
        
        # 네트워크 에러
        for req in self.network_requests:
            if 'status' in req and req['status'] >= 400:
                error_timeline.append({
                    'time': req.get('timing', 0),
                    'type': 'network',
                    'message': f"HTTP {req['status']}: {req['url']}"
                })
        
        # 페이지 에러
        for error in self.page_errors:
            error_timeline.append({
                'time': error.get('timing', 0),
                'type': 'page',
                'message': error['message']
            })
        
        # 에러 타입별 분류
        error_types = {}
        for error in error_timeline:
            error_type = error['type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'error_timeline': sorted(error_timeline, key=lambda x: x['time']),
            'error_types': error_types,
            'total_errors': len(error_timeline)
        }
    
    def _calculate_success_score(self, analysis):
        """성공 가능성 점수 계산 (0-100)"""
        score = 100  # 기본 100점에서 시작
        
        # 에러가 있으면 점수 차감
        score -= analysis.get('console_errors', 0) * 10
        score -= analysis.get('page_errors', 0) * 15
        score -= analysis.get('failed_requests', 0) * 5
        
        # 실패 지표가 있으면 점수 차감
        score -= len(self.failure_indicators) * 20
        
        # 성공 지표가 있으면 점수 추가
        score += len(self.success_indicators) * 10
        
        # 타이밍이 너무 길면 점수 차감
        if analysis.get('total_time', 0) > 60:  # 60초 초과
            score -= 30
        elif analysis.get('total_time', 0) > 30:  # 30초 초과
            score -= 15
        
        # 로그인 API 호출이 있으면 점수 추가
        if analysis.get('login_api_calls', 0) > 0:
            score += 15
        
        # 점수 범위 제한 (0-100)
        return max(0, min(100, score))

class AdaptiveRetryStrategy:
    """적응형 재시도 전략"""
    
    def __init__(self):
        self.failure_history = []
        self.success_history = []
        self.retry_strategies = {
            'timeout': self._timeout_strategy,
            'network': self._network_strategy,
            'validation': self._validation_strategy,
            'general': self._general_strategy
        }
    
    def analyze_failure_and_get_strategy(self, analysis: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        """실패 분석 후 최적의 재시도 전략 결정"""
        failure_type = self._classify_failure_type(analysis)
        
        logger.info(f"[Retry] 실패 유형 분석: {failure_type}")
        
        # 실패 히스토리에 추가
        self.failure_history.append({
            'attempt': attempt,
            'failure_type': failure_type,
            'analysis': analysis,
            'timestamp': time.time()
        })
        
        # 적응형 전략 결정
        strategy = self.retry_strategies.get(failure_type, self.retry_strategies['general'])
        return strategy(analysis, attempt, len(self.failure_history))
    
    def record_success(self, analysis: Dict[str, Any], attempt: int):
        """성공 기록"""
        self.success_history.append({
            'attempt': attempt,
            'analysis': analysis,
            'timestamp': time.time()
        })
        logger.info(f"[Retry] 성공 패턴 기록: 시도 {attempt}회 만에 성공")
    
    def _classify_failure_type(self, analysis: Dict[str, Any]) -> str:
        """실패 유형 분류"""
        # 성공 예측 점수 기반 분류
        success_score = analysis.get('success_prediction_score', 0)
        
        # 타임아웃 관련 실패
        if analysis.get('total_time', 0) > 30 or success_score < 20:
            return 'timeout'
        
        # 네트워크 관련 실패
        if analysis.get('failed_requests', 0) > 0 or analysis.get('console_errors', 0) > 2:
            return 'network'
        
        # 로그인 검증 실패
        if analysis.get('login_api_calls', 0) > 0 and len(analysis.get('failure_indicators', [])) > 0:
            return 'validation'
        
        return 'general'
    
    def _timeout_strategy(self, analysis: Dict[str, Any], attempt: int, total_failures: int) -> Dict[str, Any]:
        """타임아웃 전용 전략"""
        logger.info("[Retry] 타임아웃 전략 적용")
        
        # 점진적으로 대기 시간 증가
        base_wait = 10000  # 10초 기본
        progressive_wait = base_wait + (attempt * 5000)  # 시도마다 5초씩 추가
        max_wait = 30000  # 최대 30초
        
        wait_time = min(progressive_wait, max_wait)
        
        return {
            'wait_time': wait_time,
            'should_reload': True,
            'clear_cache': attempt > 3,
            'strategy_name': 'Timeout Strategy',
            'extra_actions': [
                'Clear browser cache' if attempt > 3 else None,
                'Extended page wait',
                'Network stabilization'
            ]
        }
    
    def _network_strategy(self, analysis: Dict[str, Any], attempt: int, total_failures: int) -> Dict[str, Any]:
        """네트워크 오류 전용 전략"""
        logger.info("[Retry] 네트워크 오류 전략 적용")
        
        # 네트워크 오류는 짧은 간격으로 빠른 재시도
        wait_time = random.randint(3000, 7000) + (attempt * 2000)
        
        return {
            'wait_time': wait_time,
            'should_reload': attempt % 2 == 0,  # 2번에 한 번 리로드
            'clear_cache': False,
            'strategy_name': 'Network Error Strategy',
            'extra_actions': [
                'Network request optimization',
                'Header refresh',
                'Connection reset' if attempt > 2 else None
            ]
        }
    
    def _validation_strategy(self, analysis: Dict[str, Any], attempt: int, total_failures: int) -> Dict[str, Any]:
        """로그인 검증 실패 전용 전략"""
        logger.info("[Retry] 로그인 검증 전략 적용")
        
        # 검증 실패는 중간 정도 대기
        wait_time = random.randint(5000, 10000) + (attempt * 3000)
        
        return {
            'wait_time': wait_time,
            'should_reload': True,
            'clear_cache': attempt > 2,
            'strategy_name': 'Validation Failure Strategy',
            'extra_actions': [
                'Extended validation wait',
                'Multiple validation methods',
                'DOM state verification'
            ]
        }
    
    def _general_strategy(self, analysis: Dict[str, Any], attempt: int, total_failures: int) -> Dict[str, Any]:
        """일반 전략"""
        logger.info("[Retry] 일반 재시도 전략 적용")
        
        # 적응형 백오프
        wait_time = random.randint(4000, 8000) + (attempt * 2500)
        
        return {
            'wait_time': wait_time,
            'should_reload': attempt > 1,
            'clear_cache': attempt > 4,
            'strategy_name': 'General Strategy',
            'extra_actions': [
                'Standard retry process',
                'Progressive backoff'
            ]
        }
    
    def get_success_insights(self) -> Dict[str, Any]:
        """성공 패턴 인사이트 제공"""
        if not self.success_history:
            return {}
        
        success_attempts = [s['attempt'] for s in self.success_history]
        avg_attempts = sum(success_attempts) / len(success_attempts)
        
        return {
            'success_count': len(self.success_history),
            'avg_attempts_to_success': avg_attempts,
            'best_attempt': min(success_attempts),
            'worst_attempt': max(success_attempts)
        }

class CoupangReviewCrawler:
    """쿠팡잇츠 리뷰 크롤러"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.star_extractor = CoupangStarRatingExtractor()
        self.monitor = LoginMonitor()
        self.success_patterns = []  # 성공 패턴 저장
        self.failure_patterns = []  # 실패 패턴 저장
        self.retry_strategy = AdaptiveRetryStrategy()  # 적응형 재시도 전략
        
        # 프록시 및 User-Agent 로테이션 시스템 초기화
        self.proxy_manager = FreeProxyManager() if FreeProxyManager else None
        self.ua_rotator = UserAgentRotator() if UserAgentRotator else None
        self.current_proxy = None
        self.current_user_agent = None
        
    async def _setup_monitoring(self, page: Page):
        """페이지 모니터링 설정"""
        # 네트워크 이벤트 모니터링
        page.on("request", self.monitor.log_request)
        page.on("response", self.monitor.log_response)
        
        # 콘솔 메시지 모니터링
        page.on("console", self.monitor.log_console)
        
        # 페이지 에러 모니터링
        page.on("pageerror", self.monitor.log_page_error)
        
        # 로드 이벤트 모니터링
        page.on("load", lambda: logger.debug("[Monitor] Page loaded"))
        page.on("domcontentloaded", lambda: logger.debug("[Monitor] DOM content loaded"))
        
        logger.debug("[Monitor] 모니터링 시스템 활성화됨")
        
    async def _advanced_login_with_monitoring(self, page: Page, username: str, password: str, attempt: int = 1) -> bool:
        """모니터링 시스템이 통합된 고급 로그인"""
        try:
            logger.debug(f"[Monitor] 로그인 시도 {attempt} 시작...")
            self.monitor.reset()  # 모니터링 데이터 초기화
            
            # 모니터링 설정
            await self._setup_monitoring(page)
            
            # 기존 스텔스 로그인 로직 실행
            success = await self._login_with_stealth_monitored(page, username, password)
            
            # 패턴 분석
            analysis = self.monitor.analyze_patterns()
            logger.debug(f"[Monitor] 분석 결과: {analysis}")
            
            if success:
                self.success_patterns.append(analysis)
                logger.debug(f"[Monitor] 성공 패턴 저장: {len(self.success_patterns)}개")
            else:
                self.failure_patterns.append(analysis)
                logger.debug(f"[Monitor] 실패 패턴 저장: {len(self.failure_patterns)}개")
                
            return success
            
        except Exception as e:
            logger.error(f"[Monitor] 모니터링 로그인 오류: {e}")
            analysis = self.monitor.analyze_patterns()
            analysis['exception'] = str(e)
            self.failure_patterns.append(analysis)
            return False
            
    async def _login_with_stealth_monitored(self, page: Page, username: str, password: str) -> bool:
        """모니터링 기능이 통합된 스텔스 모드 로그인"""
        try:
            logger.info("🕵️ 스텔스 모드 로그인 시작...")
            
            # 브라우저 상태 사전 확인
            await self._pre_login_validation(page)
            
            # 네트워크 인터셉트 및 스텔스 스크립트 주입
            await self._setup_network_intercept(page)
            await self._inject_advanced_stealth_scripts(page)
            await self._inject_stability_enhancements(page)
            
            # 로그인 페이지로 이동
            logger.debug("[Monitor] 로그인 페이지로 이동 중...")
            navigation_start = time.time()
            await page.goto("https://store.coupangeats.com/merchant/login", wait_until='domcontentloaded', timeout=30000)
            navigation_time = time.time() - navigation_start
            logger.debug(f"[Monitor] 페이지 로딩 시간: {navigation_time:.2f}초")
            
            # DOM 안정화 대기 (더 긴 시간)
            await page.wait_for_timeout(random.randint(4000, 7000))
            
            # 페이지 상태 검증
            page_title = await page.title()
            current_url = page.url
            logger.debug(f"[Monitor] 페이지 제목: {page_title}")
            logger.debug(f"[Monitor] 현재 URL: {current_url}")
            
            # 성공 지표 체크 (이미 로그인된 상태인지)
            if "/merchant/login" not in current_url:
                logger.info("✅ 이미 로그인된 상태")
                self.monitor.success_indicators.append("Already logged in")
                return True
            
            # 로그인 필드 확인
            logger.debug("[Monitor] 로그인 필드 찾는 중...")
            await page.wait_for_selector('#loginId', timeout=10000)
            await page.wait_for_selector('#password', timeout=10000)
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
            
            # 간단한 대기 시간
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            # 자격 증명 입력 (클립보드 방식 우선 사용)
            logger.debug("[Monitor] 자격 증명 입력 시작...")
            input_start = time.time()
            
            # 간단한 클립보드 로그인 (복잡한 마우스 이동 제거)
            if pyperclip:
                try:
                    logger.info("[Monitor] 📋 클립보드 로그인 시작...")
                    
                    # ID 입력 - 랜덤 클릭 적용
                    id_input = await page.query_selector('#loginId')
                    if id_input:
                        box = await id_input.bounding_box()
                        if box:
                            # 입력 필드 내부의 랜덤 위치 클릭 (15% 마진)
                            margin_x = box['width'] * 0.15
                            margin_y = box['height'] * 0.15
                            click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                            click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                            
                            await page.mouse.click(click_x, click_y)
                            logger.info(f"[Monitor] ID 필드 랜덤 클릭: ({click_x:.1f}, {click_y:.1f})")
                        else:
                            await page.click('#loginId')
                            logger.info("[Monitor] ID 필드 일반 클릭")
                    else:
                        await page.click('#loginId')
                    
                    # ID 필드 클릭 후 약 1초 대기 (사람처럼)
                    await page.wait_for_timeout(random.randint(800, 1200))
                    
                    # Ctrl+A - 전체 선택 (가끔 두 번 누르기)
                    await page.keyboard.press('Control+A')
                    await page.wait_for_timeout(random.randint(500, 1000))  # 선택 확인하는 시간
                    
                    # 5% 확률로 Ctrl+A 한 번 더 (실수처럼)
                    if random.random() < 0.05:
                        await page.keyboard.press('Control+A')
                        await page.wait_for_timeout(random.randint(200, 400))
                        logger.info("[Monitor] Ctrl+A 두 번 누름 (인간적 실수)")
                    
                    # 클립보드에 복사
                    pyperclip.copy(username)
                    await page.wait_for_timeout(random.randint(300, 700))  # 복사 처리 시간
                    
                    # Ctrl+V - 붙여넣기
                    await page.keyboard.press('Control+V')
                    await page.wait_for_timeout(random.randint(400, 800))  # 붙여넣기 확인
                    
                    # 10% 확률로 필드 재클릭 (확인하는 듯한 행동)
                    if random.random() < 0.1:
                        if id_input:
                            await page.click('#loginId')
                            await page.wait_for_timeout(random.randint(200, 400))
                            logger.info("[Monitor] ID 필드 재확인 클릭")
                    
                    logger.info("[Monitor] ID 입력 완료")
                    
                    # PW 입력 - 랜덤 클릭 적용
                    pw_input = await page.query_selector('#password')
                    if pw_input:
                        box = await pw_input.bounding_box()
                        if box:
                            # 입력 필드 내부의 랜덤 위치 클릭 (15% 마진)
                            margin_x = box['width'] * 0.15
                            margin_y = box['height'] * 0.15
                            click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                            click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                            
                            await page.mouse.click(click_x, click_y)
                            logger.info(f"[Monitor] PW 필드 랜덤 클릭: ({click_x:.1f}, {click_y:.1f})")
                        else:
                            await page.click('#password')
                            logger.info("[Monitor] PW 필드 일반 클릭")
                    else:
                        await page.click('#password')
                    
                    # PW 필드 클릭 후 약 1초 대기 (사람처럼)
                    await page.wait_for_timeout(random.randint(800, 1200))
                    
                    # 마우스를 다른 곳으로 이동 (자연스러운 행동)
                    await page.mouse.move(
                        random.randint(300, 600),
                        random.randint(200, 400),
                        steps=random.randint(5, 10)
                    )
                    await page.wait_for_timeout(random.randint(200, 400))
                    
                    # Ctrl+A - 전체 선택
                    await page.keyboard.press('Control+A')
                    await page.wait_for_timeout(random.randint(400, 900))  # 선택 확인
                    
                    # 클립보드에 복사
                    pyperclip.copy(password)
                    await page.wait_for_timeout(random.randint(350, 750))  # 복사 처리
                    
                    # Ctrl+V - 붙여넣기
                    await page.keyboard.press('Control+V')
                    await page.wait_for_timeout(random.randint(500, 900))  # 붙여넣기 확인
                    
                    # 15% 확률로 필드 재클릭 (비밀번호 확인하는 듯)
                    if random.random() < 0.15:
                        if pw_input:
                            await page.click('#password')
                            await page.wait_for_timeout(random.randint(300, 500))
                            logger.info("[Monitor] PW 필드 재확인 클릭")
                    
                    logger.info("[Monitor] PW 입력 완료")
                    
                except Exception as clipboard_error:
                    logger.warning(f"[Monitor] 클립보드 방식 실패, JavaScript 직접 입력으로 전환: {clipboard_error}")
                    await self._javascript_input_fallback(page, username, password)
            else:
                logger.info("[Monitor] pyperclip 없음 - JavaScript를 통한 직접 입력 방식 사용...")
                await self._javascript_input_fallback(page, username, password)
            
            input_time = time.time() - input_start
            logger.debug(f"[Monitor] 입력 완료 시간: {input_time:.2f}초")
            
            # 자연스러운 페이지 상호작용 추가
            await self._natural_page_interaction(page)
            
            # 로그인 버튼에 대한 망설임 표현
            await self._human_like_hesitation(page, 'button[type="submit"]')
            
            # 간단한 마우스 이동 후 로그인 버튼 클릭
            logger.info("[Monitor] 🎯 로그인 버튼 클릭...")
            await page.wait_for_timeout(random.randint(500, 1000))  # 잠시 대기
            click_start = time.time()
            
            # 버튼 랜덤 클릭
            box = await submit_button.bounding_box()
            if box:
                margin_x = box['width'] * 0.15
                margin_y = box['height'] * 0.15
                click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                
                await page.mouse.click(click_x, click_y)
                logger.info(f"[Monitor] ✅ 랜덤 위치 클릭: ({click_x:.1f}, {click_y:.1f})")
            else:
                await submit_button.click()
                logger.info("[Monitor] ✅ 일반 클릭 완료")
            
            logger.info("[Monitor] 🚀 로그인 버튼 클릭 완료 - 응답 대기 시작")
            
            # 로그인 응답 대기 및 분석 (빠른 실패 감지 포함)
            logger.debug("[Monitor] 로그인 응답 분석 중...")
            
            # 1단계: API 응답 대기 (진단 결과 기반 개선)
            logger.info("[Monitor] 로그인 API 응답 대기 중 (진단 기반 개선)...")
            api_success_detected = False
            quick_fail_detected = False
            
            # API 응답을 더 길게 대기 (진단에서 API는 성공했음)
            for i in range(8):  # 3초 → 8초로 연장
                await page.wait_for_timeout(1000)
                current_url = page.url
                
                # URL이 변경되었으면 성공 확실
                if "/merchant/login" not in current_url:
                    logger.info(f"[Monitor] ✅ URL 변경 감지! 로그인 성공: {current_url}")
                    api_success_detected = True
                    break
                    
                # 네트워크 모니터에서 성공적인 API 응답 확인 (속성 확인 후 사용)
                try:
                    if hasattr(self.monitor, 'responses') and self.monitor.responses:
                        recent_responses = [r for r in self.monitor.responses[-5:] if 'login' in r.get('url', '')]
                        success_responses = [r for r in recent_responses if r.get('status') == 200]
                    elif hasattr(self.monitor, 'response_log') and self.monitor.response_log:
                        recent_responses = [r for r in self.monitor.response_log[-5:] if 'login' in r.get('url', '')]
                        success_responses = [r for r in recent_responses if r.get('status') == 200]
                    else:
                        success_responses = []
                except Exception as attr_error:
                    logger.debug(f"[Monitor] 응답 로그 접근 오류: {attr_error}")
                    success_responses = []
                
                if success_responses and i >= 2:  # 2초 후부터 API 응답 고려
                    logger.info(f"[Monitor] 로그인 API 성공 응답 감지 (200 OK) - 추가 대기 중...")
                    # API 성공 시 추가로 3초 더 대기
                    for j in range(3):
                        await page.wait_for_timeout(1000)
                        if "/merchant/login" not in page.url:
                            logger.info(f"[Monitor] ✅ API 성공 후 리다이렉션 완료: {page.url}")
                            api_success_detected = True
                            break
                    if api_success_detected:
                        break
                    
                # 에러 메시지가 있으면 즉시 실패
                error_selectors = [
                    '.error-message', '.alert-danger', '.error', 
                    '[class*="error"]', '[class*="alert"]',
                    '.login-error', '.warning'
                ]
                
                for selector in error_selectors:
                    error_element = await page.query_selector(selector)
                    if error_element:
                        error_text = await error_element.inner_text()
                        if error_text and error_text.strip():
                            logger.error(f"[Monitor] 에러 메시지 감지: {error_text}")
                            quick_fail_detected = True
                            break
                
                if quick_fail_detected:
                    break
                    
                logger.debug(f"[Monitor] API 응답 대기 {i+1}/8 - 아직 로그인 페이지")
            
            # 최종 판단
            if api_success_detected:
                logger.info("[Monitor] ✅ 로그인 성공 확인됨")
                return True
            elif quick_fail_detected:
                logger.error("[Monitor] ❌ 에러 메시지로 인한 실패")
                return False
            else:
                # 8초 후에도 변화가 없으면 실패로 판단하지만 더 관대하게
                logger.warning("[Monitor] ⚠️ 8초 대기 완료 - 응답 지연 가능성")
                # 한 번 더 확인 (최종 체크)
                await page.wait_for_timeout(2000)  # 추가 2초 대기
                if "/merchant/login" not in page.url:
                    logger.info(f"[Monitor] ✅ 지연된 성공 감지: {page.url}")
                    return True
                return False
            
            # 2단계: 정상적인 URL 변경 대기
            try:
                logger.debug("[Monitor] 정상 URL 변경 대기 중...")
                await page.wait_for_url(lambda url: "/merchant/login" not in url, timeout=12000)  # 나머지 12초
                url_change_time = time.time() - click_start
                logger.debug(f"[Monitor] URL 변경 시간: {url_change_time:.2f}초")
                self.monitor.success_indicators.append(f"URL changed in {url_change_time:.2f}s")
            except:
                logger.debug("[Monitor] URL 변경 타임아웃 - 수동 확인 진행")
            
            # 다중 방법으로 로그인 성공 확인
            return await self._verify_login_success_monitored(page)
            
        except Exception as e:
            logger.error(f"[Monitor] 스텔스 로그인 오류: {e}")
            self.monitor.failure_indicators.append(f"Exception: {str(e)}")
            return False
            
    # ==================== 간단한 로그인 헬퍼 메서드들 ====================
        
    async def _verify_login_success_monitored(self, page: Page) -> bool:
        """모니터링이 통합된 로그인 성공 검증 - 엄격한 버전"""
        verification_start = time.time()
        max_attempts = 15  # 검증 시도 횟수
        
        for attempt in range(max_attempts):
            logger.debug(f"[Monitor] 로그인 검증 {attempt + 1}/{max_attempts}")
            
            current_url = page.url
            page_title = await page.title()
            logger.debug(f"[Monitor] URL: {current_url}")
            logger.debug(f"[Monitor] 제목: {page_title}")
            
            # 먼저 실패 조건들을 엄격하게 확인
            
            # 1. 여전히 로그인 페이지에 있는지 확인
            if "/merchant/login" in current_url:
                logger.debug(f"[Monitor] 아직 로그인 페이지에 있음: {current_url}")
                
                # 로그인 에러 메시지 엄격 확인
                try:
                    # 다양한 에러 메시지 패턴 확인
                    error_selectors = [
                        '.error', '.alert', '[class*="error"]', '[class*="alert"]',
                        '.invalid-feedback', '.form-error', '.login-error',
                        'div[role="alert"]', '.notification.is-danger'
                    ]
                    
                    for selector in error_selectors:
                        error_elements = await page.query_selector_all(selector)
                        for error_element in error_elements:
                            try:
                                error_text = await error_element.inner_text()
                                if error_text and error_text.strip():
                                    # 에러 메시지가 보이면 즉시 실패로 판단
                                    if any(keyword in error_text for keyword in ['맞지', '않습', '실패', '오류', '틀렸', 'invalid', 'error', 'failed']):
                                        logger.error(f"[Monitor] ❌ 로그인 에러 감지: {error_text.strip()}")
                                        self.monitor.failure_indicators.append(f"Error message detected: {error_text.strip()}")
                                        return False
                            except:
                                continue
                except Exception as e:
                    logger.debug(f"에러 메시지 확인 중 예외: {e}")
                
                # 로그인 폼이 여전히 존재하는지 확인 (실패 지표)
                try:
                    login_form = await page.query_selector('form')
                    username_field = await page.query_selector('#loginId, input[name="username"], input[type="email"]')
                    password_field = await page.query_selector('#password, input[name="password"], input[type="password"]')
                    
                    if login_form and username_field and password_field:
                        logger.debug("[Monitor] 로그인 폼이 여전히 존재함 - 로그인 실패로 판단")
                        # 하지만 즉시 실패로 판단하지 않고 계속 확인 (페이지 전환 중일 수 있음)
                except:
                    pass
            
            # 2. 성공 조건들을 엄격하게 확인
            else:
                # URL이 로그인 페이지가 아님 - 성공 가능성 높음
                
                # 관리자 페이지 URL 패턴 확인
                success_url_patterns = [
                    "management", "dashboard", "store", "reviews", 
                    "merchant/main", "merchant/home", "admin"
                ]
                
                url_success = any(pattern in current_url for pattern in success_url_patterns)
                
                if url_success:
                    # DOM 요소로 2차 검증
                    try:
                        # 관리자 페이지 특징적인 요소들 확인
                        admin_selectors = [
                            'a[href*="management"]', 'a[href*="reviews"]', 'a[href*="dashboard"]',
                            '[class*="dashboard"]', '[class*="merchant"]', '[class*="admin"]',
                            'nav.navbar', '.sidebar', '.main-content', '.user-menu',
                            'button[data-test="logout"]', 'a[href*="logout"]'
                        ]
                        
                        dom_success = False
                        found_elements = []
                        
                        for selector in admin_selectors:
                            try:
                                element = await page.query_selector(selector)
                                if element:
                                    dom_success = True
                                    found_elements.append(selector)
                            except:
                                continue
                        
                        if dom_success:
                            verification_time = time.time() - verification_start
                            logger.info(f"✅ 로그인 성공 확인! ({verification_time:.1f}s)")
                            logger.debug(f"[Monitor] - URL 패턴: {current_url}")
                            logger.debug(f"[Monitor] - DOM 요소: {found_elements}")
                            
                            self.monitor.success_indicators.append(f"Login verified in {verification_time:.2f}s")
                            self.monitor.success_indicators.append(f"URL pattern: {current_url}")
                            self.monitor.success_indicators.append(f"DOM elements: {found_elements}")
                            
                            return True
                        else:
                            logger.debug(f"[Monitor] URL은 변경되었지만 DOM 요소 확인 실패")
                            # DOM 확인 실패해도 URL이 변경되었으면 일정 시간 더 기다려봄
                    except Exception as e:
                        logger.debug(f"[Monitor] DOM 검증 중 예외: {e}")
                        
                    # URL은 변경되었지만 DOM 검증이 애매한 경우 - 추가 대기
                    logger.debug("[Monitor] URL 변경 확인됨, DOM 로딩 대기 중...")
                    await page.wait_for_timeout(3000)  # 3초 추가 대기
                    continue
            
            # 3. 페이지가 로딩 중인지 확인
            try:
                loading_state = await page.evaluate('document.readyState')
                if loading_state != 'complete':
                    logger.debug(f"[Monitor] 페이지 로딩 중 (readyState: {loading_state})")
                    await page.wait_for_timeout(2000)
                    continue
            except:
                pass
            
            # 일반적인 대기
            await page.wait_for_timeout(2000)
        
        # 최대 시도 횟수 도달 - 최종 실패 판정
        logger.error("[Monitor] ❌ 로그인 검증 실패 - 최대 시도 횟수 초과")
        logger.error(f"[Monitor] 최종 URL: {page.url}")
        logger.error(f"[Monitor] 최종 제목: {await page.title()}")
        
        self.monitor.failure_indicators.append("Login verification timeout")
        self.monitor.failure_indicators.append(f"Final URL: {page.url}")
        
        return False
        
    def _analyze_success_patterns(self):
        """성공 패턴 분석"""
        if len(self.success_patterns) < 2:
            return
            
        logger.debug(f"[Monitor] 성공 패턴 분석 시작 ({len(self.success_patterns)}개 패턴)")
        
        # 공통 특성 추출
        avg_total_time = sum(p.get('total_time', 0) for p in self.success_patterns) / len(self.success_patterns)
        avg_requests = sum(p.get('total_requests', 0) for p in self.success_patterns) / len(self.success_patterns)
        
        # 성공하는 네트워크 패턴 분석
        success_indicators = []
        for pattern in self.success_patterns:
            success_indicators.extend(pattern.get('success_indicators', []))
        
        logger.debug(f"[Monitor] 성공 패턴 특성:")
        logger.info(f"  - 평균 완료 시간: {avg_total_time:.2f}초")
        logger.info(f"  - 평균 네트워크 요청: {avg_requests:.1f}개")
        logger.info(f"  - 공통 성공 지표: {set(success_indicators)}")
        
    def _analyze_failure_patterns(self):
        """실패 패턴 분석"""
        if not self.failure_patterns:
            return
            
        logger.debug(f"[Monitor] 실패 패턴 분석 시작 ({len(self.failure_patterns)}개 패턴)")
        
        # 실패 원인 분류
        failure_reasons = {}
        for pattern in self.failure_patterns:
            for indicator in pattern.get('failure_indicators', []):
                reason_type = self._categorize_failure(indicator)
                failure_reasons[reason_type] = failure_reasons.get(reason_type, 0) + 1
        
        logger.debug(f"[Monitor] 실패 원인 분포:")
        for reason, count in failure_reasons.items():
            percentage = (count / len(self.failure_patterns)) * 100
            logger.info(f"  - {reason}: {count}회 ({percentage:.1f}%)")
            
        # 가장 일반적인 실패 원인
        if failure_reasons:
            most_common = max(failure_reasons, key=failure_reasons.get)
            logger.debug(f"[Monitor] 주요 실패 원인: {most_common}")
            
    def _categorize_failure(self, indicator: str) -> str:
        """실패 지표를 카테고리별로 분류"""
        indicator_lower = indicator.lower()
        
        if 'timeout' in indicator_lower:
            return 'Timeout'
        elif 'http' in indicator_lower and ('400' in indicator_lower or '500' in indicator_lower):
            return 'HTTP Error'
        elif 'error' in indicator_lower and 'console' in indicator_lower:
            return 'Console Error'
        elif 'login' in indicator_lower and ('failed' in indicator_lower or '실패' in indicator_lower):
            return 'Login Failure'
        elif 'exception' in indicator_lower:
            return 'Exception'
        else:
            return 'Other'
        
    async def crawl_reviews(
        self,
        username: str,
        password: str,
        store_id: str,
        days: int = 7,
        max_pages: int = 5,
        use_stealth: bool = True  # 스텔스 모드 기본 활성화
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
            # Playwright 브라우저 시작 (스텔스 모드 강화)
            async with async_playwright() as p:
                if use_stealth:
                    # 스텔스 모드: 최신 2024년 고급 안티 디텍션 설정
                    browser_args = [
                        # 핵심 자동화 탐지 우회 (최우선)
                        '--disable-blink-features=AutomationControlled',
                        '--exclude-switches=enable-automation',
                        '--disable-automation',
                        '--disable-extensions-http-throttling',
                        '--disable-extensions-file-access-check',
                        
                        # WebGL 정상화 (콘솔 에러 해결) - 핵심!
                        '--use-gl=desktop',  # swiftshader 대신 desktop 사용
                        '--enable-webgl',
                        '--enable-webgl2',
                        '--enable-accelerated-2d-canvas',
                        '--enable-gpu-rasterization',
                        '--ignore-gpu-blocklist',
                        '--enable-unsafe-webgl',
                        '--enable-unsafe-swiftshader',
                        '--force-color-profile=srgb',
                        '--enable-features=Canvas2dImageChromium',
                        
                        # Navigator 속성들 정상화
                        '--enable-features=NetworkService,NetworkServiceInProcess',
                        '--disable-features=TranslateUI',
                        '--disable-ipc-flooding-protection',
                        '--disable-background-timer-throttling',
                        '--disable-renderer-backgrounding',
                        '--disable-backgrounding-occluded-windows',
                        
                        # 플러그인 및 미디어 지원
                        '--enable-plugins',
                        '--enable-media-stream',
                        '--use-fake-ui-for-media-stream',
                        '--allow-running-insecure-content',
                        
                        # 네트워크 프로토콜 최적화
                        '--disable-http2',  # HTTP/2 문제 해결
                        '--disable-quic',
                        '--disable-features=Http2Grease',
                        '--disable-features=VizDisplayCompositor',
                        
                        # JavaScript 에러 방지 (중요!)
                        '--disable-features=VizDisplayCompositor',
                        '--disable-features=ScriptStreaming',
                        '--disable-strict-mixed-content-checking',
                        '--disable-mixed-content-autoupgrade',
                        '--disable-component-extensions-with-background-pages',
                        
                        # 보안 관련 (개발용으로만)
                        '--disable-web-security',
                        '--disable-features=site-per-process',
                        '--disable-site-isolation-trials',
                        '--ignore-certificate-errors',
                        '--ignore-ssl-errors',
                        '--allow-running-insecure-content',
                        
                        # 추적 방지 강화
                        '--disable-sync',
                        '--disable-background-mode',
                        '--disable-extensions',
                        '--disable-plugins-discovery',
                        '--disable-preconnect',
                        '--disable-dns-prefetch',
                        '--disable-domain-reliability',
                        
                        # 기본 설정
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-popup-blocking',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--window-size=1920,1080',
                    ]
                else:
                    # 일반 모드: 기존 설정
                    browser_args = [
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-infobars',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-http2',
                        '--disable-quic',
                        '--disable-features=VizDisplayCompositor',
                    ]
                
                browser = await p.chromium.launch(
                    headless=False,  # 절대 헤드리스 사용 안함
                    args=browser_args
                )
                
                # 컨텍스트 설정 (스텔스 모드 강화)
                if use_stealth:
                    # 랜덤 User-Agent 사용
                    selected_ua = get_random_user_agent()
                    logger.info(f"🎭 선택된 User-Agent: {selected_ua[:50]}...")
                    
                    context = await browser.new_context(
                        user_agent=selected_ua,
                        viewport={"width": random.randint(1900, 1920), "height": random.randint(1060, 1080)},
                        locale="ko-KR",
                        timezone_id="Asia/Seoul",
                        geolocation={"latitude": 37.5665, "longitude": 126.9780},
                        permissions=["geolocation", "notifications"],
                        color_scheme="light",
                        device_scale_factor=1,
                        is_mobile=False,
                        has_touch=False,
                        ignore_https_errors=True,
                    )
                else:
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        viewport={"width": 1366, "height": 768},
                        locale="ko-KR"
                    )
                
                page = await context.new_page()
                
                # 스텔스 스크립트 주입
                if use_stealth:
                    await self._setup_network_intercept(page)
                    await self._inject_advanced_stealth_scripts(page)
                else:
                    await page.add_init_script("""
                        // WebDriver 속성만 제거
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined,
                        });
                        
                        // Chrome 객체만 추가
                        window.chrome = {
                            runtime: {},
                        };
                    """)
                
                # 1. 모니터링 시스템을 통한 고급 로그인 (재시도 로직 포함)
                login_success = False
                max_attempts = 10  # 최대 시도 횟수 증가
                
                for attempt in range(1, max_attempts + 1):
                    logger.debug(f"[Monitor] 로그인 시도 {attempt}/{max_attempts}")
                    
                    try:
                        if use_stealth:
                            # 모니터링 시스템을 사용한 고급 로그인
                            login_success = await self._advanced_login_with_monitoring(page, username, password, attempt)
                        else:
                            # 기존 방식 (필요시)
                            login_success = await self._login(page, username, password)
                            
                        if login_success:
                            logger.info(f"✅ 로그인 성공! ({attempt}번째 시도)")
                            
                            # 성공 패턴 기록
                            if self.success_patterns:
                                latest_success = self.success_patterns[-1]
                                self.retry_strategy.record_success(latest_success, attempt)
                                logger.debug(f"[Monitor] 축적된 성공 패턴: {len(self.success_patterns)}개")
                                self._analyze_success_patterns()
                            break
                        else:
                            if attempt < max_attempts:
                                logger.warning(f"❌ 로그인 실패 - {max_attempts - attempt}번 더 시도 남음")
                                
                                # 적응형 재시도 전략 적용
                                if self.failure_patterns:
                                    latest_failure = self.failure_patterns[-1]
                                    
                                    # AI 기반 재시도 전략 결정
                                    retry_strategy = self.retry_strategy.analyze_failure_and_get_strategy(latest_failure, attempt)
                                    
                                    logger.debug(f"[Monitor] 적용 전략: {retry_strategy['strategy_name']}")
                                    logger.debug(f"[Monitor] 적응형 대기: {retry_strategy['wait_time']/1000:.1f}초")
                                    
                                    # 추가 액션 실행
                                    extra_actions = [action for action in retry_strategy['extra_actions'] if action]
                                    if extra_actions:
                                        logger.debug(f"[Monitor] 추가 액션: {', '.join(extra_actions)}")
                                    
                                    # 전략별 대기 시간 적용
                                    await page.wait_for_timeout(retry_strategy['wait_time'])
                                    
                                    # 캐시 클리어 (필요시)
                                    if retry_strategy.get('clear_cache', False):
                                        logger.debug("[Monitor] 브라우저 캐시 클리어 중...")
                                        await page.evaluate('''
                                            // localStorage와 sessionStorage 클리어
                                            localStorage.clear();
                                            sessionStorage.clear();
                                            // 캐시 강제 새로고침을 위한 헤더 수정
                                            if (window.performance) {
                                                window.performance.mark('cache-clear');
                                            }
                                        ''')
                                        await page.wait_for_timeout(2000)
                                    
                                    # 페이지 리로드 (전략에 따라)
                                    if retry_strategy.get('should_reload', True):
                                        logger.debug("[Monitor] 페이지 상태 초기화 중...")
                                        await page.reload(wait_until='domcontentloaded', timeout=30000)
                                        await page.wait_for_timeout(3000)
                                else:
                                    # 패턴이 없는 경우 기본 전략
                                    logger.debug("[Monitor] 기본 재시도 전략 적용")
                                    await page.wait_for_timeout(random.randint(5000, 10000))
                                    await page.reload(wait_until='domcontentloaded', timeout=30000)
                                    await page.wait_for_timeout(3000)
                            else:
                                logger.error(f"[Monitor] ❌ 모든 로그인 시도 실패 ({max_attempts}번)")
                                
                                # 실패 패턴 종합 분석 및 인사이트 제공
                                self._analyze_failure_patterns()
                                
                                # 재시도 전략 인사이트 출력
                                insights = self.retry_strategy.get_success_insights()
                                if insights:
                                    logger.debug(f"[Monitor] 성공 인사이트: {insights}")
                                else:
                                    logger.debug("[Monitor] 성공 기록이 없습니다. 기본 설정을 재검토하세요.")
                                
                    except Exception as e:
                        logger.error(f"[Monitor] 로그인 시도 {attempt} 중 예외: {e}")
                        if attempt < max_attempts:
                            await page.wait_for_timeout(random.randint(3000, 8000))
                            continue
                
                if not login_success:
                    return {
                        "success": False,
                        "message": f"로그인 실패 (총 {max_attempts}번 시도)",
                        "reviews": []
                    }
                
                # 2. 리뷰 페이지 이동
                await self._navigate_to_reviews_page(page)
                
                # 3. 모달 창 닫기 (최적화된 시간)
                await page.wait_for_timeout(1500)  # 페이지 로딩 완료 대기
                await self._close_modal_if_exists(page)
                await page.wait_for_timeout(500)  # 첫 번째 모달 닫기 후 대기
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
    
    async def _setup_network_intercept(self, page: Page):
        """네트워크 레벨 인터셉트 설정"""
        async def handle_request(route, request):
            """요청 핸들러"""
            url = request.url
            
            # 웹로그 요청 차단
            if 'weblog/submit' in url:
                logger.debug(f"[Network] 웹로그 요청 차단: {url}")
                await route.fulfill(
                    status=200,
                    content_type='application/json',
                    body='{"success": true}'
                )
                return
            
            # 로그인 API 요청 모니터링
            if '/api/v1/merchant/login' in url:
                logger.info(f"[Network] 로그인 API 요청 감지: {request.method} {url}")
                
                # HTTP/2 에러 방지를 위한 헤더 수정
                headers = dict(request.headers)
                headers['Connection'] = 'keep-alive'
                headers['Upgrade-Insecure-Requests'] = '1'
                
                # 요청 계속 진행 (헤더 수정됨)
                await route.continue_(headers=headers)
                return
            
            # 다른 요청은 정상 진행
            await route.continue_()
        
        # 요청 인터셉트 활성화
        await page.route("**/*", handle_request)
        logger.info("[Network] 네트워크 인터셉트 활성화")
    
    async def _inject_advanced_stealth_scripts(self, page: Page):
        """2025년 강화된 스텔스 스크립트 주입 - JavaScript 에러 방지 포함"""
        await page.add_init_script("""
            (() => {
                'use strict';
                
                // ===== JavaScript 에러 방지 (최우선) =====
                try {
                    // 문법 에러 방지를 위한 전역 에러 핸들러
                    window.addEventListener('error', function(e) {
                        if (e.message && e.message.includes('Unexpected token')) {
                            e.preventDefault();
                            e.stopPropagation();
                            return false;
                        }
                    }, true);
                    
                    // SyntaxError 방지
                    const originalEval = window.eval;
                    window.eval = function(code) {
                        try {
                            return originalEval.call(this, code);
                        } catch (e) {
                            if (e instanceof SyntaxError) {
                                console.log('[Stealth] SyntaxError 방지됨:', e.message);
                                return undefined;
                            }
                            throw e;
                        }
                    };
                    
                } catch (e) {
                    // 에러 핸들러 설정 실패해도 계속 진행
                }
                
                // ===== 1. WebDriver 속성 완전 제거 =====
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                delete navigator.__proto__.webdriver;
                delete navigator.webdriver;
                
                // ===== 2. Chrome 객체 완벽 재현 =====
                if (!window.chrome) {
                    window.chrome = {};
                }
                
                window.chrome.app = {
                    isInstalled: false,
                    InstallState: {
                        DISABLED: 'disabled',
                        INSTALLED: 'installed', 
                        NOT_INSTALLED: 'not_installed'
                    },
                    RunningState: {
                        CANNOT_RUN: 'cannot_run',
                        READY_TO_RUN: 'ready_to_run',
                        RUNNING: 'running'
                    }
                };
                
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
                    connect: () => ({ disconnect: () => {} }),
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
                
                window.chrome.csi = function() {
                    return {
                        onloadT: Date.now(),
                        pageT: Date.now() + Math.random() * 100,
                        startE: Date.now() - Math.random() * 1000,
                        tran: 15
                    };
                };
                
                window.chrome.loadTimes = function() {
                    return {
                        commitLoadTime: Date.now() / 1000,
                        connectionInfo: 'h2',
                        finishDocumentLoadTime: Date.now() / 1000,
                        finishLoadTime: Date.now() / 1000,
                        firstPaintAfterLoadTime: 0,
                        firstPaintTime: Date.now() / 1000,
                        navigationType: 'Other',
                        npnNegotiatedProtocol: 'h2',
                        requestTime: Date.now() / 1000,
                        startLoadTime: Date.now() / 1000,
                        wasAlternateProtocolAvailable: false,
                        wasFetchedViaSpdy: true,
                        wasNpnNegotiated: true
                    }
                }
            };
            
            // ===== 3. Navigator 속성들 완벽 정상화 =====
            
            // 3.1 Plugin 배열 정상화 (실제 Chrome과 동일)
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        name: 'Chrome PDF Plugin',
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer',
                        length: 1,
                        0: { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        description: '',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                        length: 1,
                        0: { type: 'application/pdf', suffixes: 'pdf', description: '' }
                    },
                    {
                        name: 'Native Client',
                        description: '',
                        filename: 'internal-nacl-plugin',
                        length: 2,
                        0: { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' },
                        1: { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable' }
                    }
                ]
            });
            
            // 3.2 언어 및 플랫폼 정상화 (한국 사용자 환경)
            Object.defineProperty(navigator, 'language', {
                get: () => 'ko-KR',
                configurable: true
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                configurable: true
            });
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
                configurable: true
            });
            Object.defineProperty(navigator, 'userAgent', {
                get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                configurable: true
            });
            
            // 3.3 하드웨어 속성 정상화
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
                configurable: true
            });
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true
            });
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0,
                configurable: true
            });
            
            // ===== 4. WebGL 및 Canvas 지문 정상화 =====
            
            // 4.1 WebGL 완전 정상화 (콘솔 에러 해결)
            try {
                // WebGL 어댑터 사용 가능 상태로 변경
                if (window.WebGLRenderingContext) {
                    // "No available adapters" 에러 해결
                    const originalGetContext = HTMLCanvasElement.prototype.getContext;
                    HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
                        if (contextType === 'webgl' || contextType === 'experimental-webgl') {
                            const ctx = originalGetContext.call(this, contextType, contextAttributes);
                            if (!ctx) {
                                // WebGL 컨텍스트 생성 실패시 재시도
                                return originalGetContext.call(this, 'experimental-webgl', {
                                    ...contextAttributes,
                                    failIfMajorPerformanceCaveat: false,
                                    antialias: false,
                                    alpha: false
                                });
                            }
                            return ctx;
                        }
                        return originalGetContext.call(this, contextType, contextAttributes);
                    };
                    
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        try {
                            // VENDOR
                            if (parameter === 37445) return 'Google Inc. (Intel)';
                            // RENDERER  
                            if (parameter === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                            // VERSION
                            if (parameter === 37447) return 'OpenGL ES 2.0 (ANGLE 2.1.0.0)';
                            // SHADING_LANGUAGE_VERSION
                            if (parameter === 35724) return 'OpenGL ES GLSL ES 1.0 (ANGLE 2.1.0.0)';
                            return getParameter.apply(this, arguments);
                        } catch (e) {
                            // getParameter 에러 방지
                            return 'Unknown';
                        }
                    };
                }
                
                // WebGL2 지원
                if (window.WebGL2RenderingContext) {
                    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                        try {
                            if (parameter === 37445) return 'Google Inc. (Intel)';
                            if (parameter === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                            if (parameter === 37447) return 'OpenGL ES 3.0 (ANGLE 2.1.0.0)';
                            if (parameter === 35724) return 'OpenGL ES GLSL ES 3.0 (ANGLE 2.1.0.0)';
                            return getParameter2.apply(this, arguments);
                        } catch (e) {
                            return 'Unknown';
                        }
                    };
                }
            } catch (e) {
                // WebGL 설정 실패해도 계속 진행
                console.log('[Stealth] WebGL 설정 완료');
            }
            
            // 4.2 Canvas 지문 노이즈 추가
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            
            HTMLCanvasElement.prototype.toDataURL = function(type, encoderOptions) {
                const result = originalToDataURL.apply(this, arguments);
                // 미세한 노이즈 추가 (너무 많으면 의심받음)
                if (Math.random() < 0.1) {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    canvas.width = this.width;
                    canvas.height = this.height;
                    const img = new Image();
                    img.onload = function() {
                        ctx.drawImage(img, 0, 0);
                        const imageData = ctx.getImageData(0, 0, 1, 1);
                        imageData.data[0] += Math.floor(Math.random() * 3) - 1;
                        ctx.putImageData(imageData, 0, 0);
                    };
                    img.src = result;
                }
                return result;
            };
            
            // ===== 5. Audio Context 지문 정상화 =====
            if (window.AudioContext || window.webkitAudioContext) {
                const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
                const originalGetChannelData = AudioBuffer.prototype.getChannelData;
                
                AudioBuffer.prototype.getChannelData = function(channel) {
                    const originalData = originalGetChannelData.apply(this, arguments);
                    // 미세한 오디오 노이즈 추가
                    for (let i = 0; i < originalData.length; i += 100) {
                        originalData[i] += (Math.random() - 0.5) * 0.0001;
                    }
                    return originalData;
                };
            }
            
            // 6. Permission API 정상화
            if (window.navigator.permissions && window.navigator.permissions.query) {
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => {
                    if (parameters.name === 'notifications') {
                        return Promise.resolve({ state: Notification.permission });
                    }
                    return originalQuery(parameters);
                };
            }
            
            // 7. Battery API 제거
            delete navigator.getBattery;
            
            // 8. 웹로그 및 API 인터셉터
            (function() {
                const originalXHROpen = XMLHttpRequest.prototype.open;
                const originalXHRSend = XMLHttpRequest.prototype.send;
                
                XMLHttpRequest.prototype.open = function(method, url, ...args) {
                    this._url = url;
                    this._method = method;
                    this._data = null;
                    
                    // HTTP/2 에러 방지를 위해 HTTP/1.1 강제
                    if (url.includes('/api/v1/merchant/login')) {
                        console.log('[Stealth] 로그인 API 요청 감지, HTTP/1.1로 전환');
                        // async를 false로 설정하여 동기 요청으로 변경 (HTTP/2 우회)
                        args[0] = true; // async를 true로 유지하되
                    }
                    
                    return originalXHROpen.apply(this, [method, url, ...args]);
                };
                
                XMLHttpRequest.prototype.send = function(data) {
                    this._data = data;
                    
                    // 웹로그 URL 감지 및 모킹
                    if (this._url && this._url.includes('weblog/submit')) {
                        console.log('[Stealth] 웹로그 요청 인터셉트:', this._url);
                        
                        // 가짜 성공 응답
                        setTimeout(() => {
                            Object.defineProperty(this, 'status', {value: 200});
                            Object.defineProperty(this, 'statusText', {value: 'OK'});
                            Object.defineProperty(this, 'readyState', {value: 4});
                            Object.defineProperty(this, 'responseText', {value: '{"success":true}'});
                            Object.defineProperty(this, 'response', {value: '{"success":true}'});
                            
                            const event = new Event('readystatechange');
                            this.dispatchEvent(event);
                            const loadEvent = new Event('load');
                            this.dispatchEvent(loadEvent);
                            const loadEndEvent = new Event('loadend');
                            this.dispatchEvent(loadEndEvent);
                        }, 50);
                        
                        return;
                    }
                    
                    // 로그인 API 에러 핸들링
                    if (this._url && this._url.includes('/api/v1/merchant/login')) {
                        const originalThis = this;
                        const originalOnError = this.onerror;
                        const originalOnReadyStateChange = this.onreadystatechange;
                        
                        // 에러 발생시 재시도
                        this.onerror = function(e) {
                            console.log('[Stealth] 로그인 API 에러 감지, 폴백 처리');
                            if (originalOnError) originalOnError.call(this, e);
                        };
                        
                        // readystate 모니터링
                        this.onreadystatechange = function() {
                            if (this.readyState === 4 && this.status === 0) {
                                console.log('[Stealth] HTTP/2 에러 감지, 응답 재구성');
                                // 에러 응답을 정상 응답으로 변경하지 않음 (실제 로그인 필요)
                            }
                            if (originalOnReadyStateChange) originalOnReadyStateChange.call(this);
                        };
                    }
                    
                    return originalXHRSend.apply(this, arguments);
                };
                
                // Fetch API 오버라이드
                const originalFetch = window.fetch;
                window.fetch = async function(url, options) {
                    if (typeof url === 'string' && url.includes('weblog/submit')) {
                        console.log('[Stealth] Fetch 웹로그 인터셉트:', url);
                        return new Response(JSON.stringify({success: true}), {
                            status: 200,
                            statusText: 'OK', 
                            headers: new Headers({'content-type': 'application/json'})
                        });
                    }
                    return originalFetch.apply(this, arguments);
                };
            })();
            
            console.log('[Stealth] 고급 스텔스 모드 활성화');
        """)
    
    async def _human_like_mouse_move(self, page: Page, start_x: int, start_y: int, end_x: int, end_y: int):
        """인간적인 마우스 움직임 시뮬레이션 (베지어 곡선)"""
        import math
        
        # 베지어 곡선의 제어점 생성 (자연스러운 곡선)
        control1_x = start_x + random.randint(-50, 50)
        control1_y = start_y + random.randint(-20, 20)
        control2_x = end_x + random.randint(-30, 30) 
        control2_y = end_y + random.randint(-15, 15)
        
        # 베지어 곡선을 따라 마우스 이동 (20단계)
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            
            # 베지어 곡선 공식
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * control1_x + 3*(1-t)*t**2 * control2_x + t**3 * end_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * control1_y + 3*(1-t)*t**2 * control2_y + t**3 * end_y
            
            await page.mouse.move(x, y)
            
            # 인간적인 속도 변화 (가속/감속)
            if i < steps // 3:
                delay = random.uniform(0.01, 0.03)  # 시작은 천천히
            elif i > 2 * steps // 3:
                delay = random.uniform(0.02, 0.04)  # 끝은 천천히
            else:
                delay = random.uniform(0.005, 0.015)  # 중간은 빠르게
                
            await asyncio.sleep(delay)
    
    async def _enhanced_clipboard_login(self, page: Page, username: str, password: str):
        """클립보드를 이용한 자연스러운 로그인 (Enhanced 버전과 완전 동일)"""
        logger.info("클립보드 붙여넣기 방식으로 로그인 시작...")
        
        # 1. ID 필드에 랜덤 위치 클릭 후 클립보드 붙여넣기
        id_input = await page.query_selector('#loginId')
        if id_input:
            box = await id_input.bounding_box()
            if box:
                # 입력 필드 내부의 랜덤 위치 클릭 (15% 마진)
                margin_x = box['width'] * 0.15
                margin_y = box['height'] * 0.15
                click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                
                await page.mouse.click(click_x, click_y)
                logger.info(f"ID 필드 랜덤 클릭: ({click_x:.1f}, {click_y:.1f})")
            else:
                await page.click('#loginId')
        else:
            await page.click('#loginId')
        
        # ID 필드 클릭 후 약 1초 대기 (사람처럼)
        await page.wait_for_timeout(random.randint(800, 1200))
        
        # 페이지 스크롤 살짝 (자연스러운 행동)
        await page.mouse.wheel(0, random.randint(-50, 50))
        await page.wait_for_timeout(random.randint(200, 400))
        
        # 필드 전체 선택 (Ctrl+A)
        await page.keyboard.press('Control+A')
        await page.wait_for_timeout(random.randint(500, 1000))  # 선택 확인 시간 증가
        
        # 8% 확률로 Ctrl+A 다시 (습관처럼)
        if random.random() < 0.08:
            await page.keyboard.press('Control+A')
            await page.wait_for_timeout(random.randint(200, 400))
            logger.info("ID 필드 Ctrl+A 두 번 (습관적 행동)")
        
        # 클립보드에 ID 복사
        pyperclip.copy(username)
        await page.wait_for_timeout(random.randint(400, 800))  # 복사 시간 증가
        
        # 붙여넣기 (Ctrl+V)
        await page.keyboard.press('Control+V')
        await page.wait_for_timeout(random.randint(600, 1200))  # 확인 시간 증가
        
        # 마우스를 다른 곳으로 이동
        await page.mouse.move(
            random.randint(400, 700),
            random.randint(300, 500),
            steps=random.randint(3, 7)
        )
        
        # 2. Tab키로 다음 필드로 이동하거나 직접 랜덤 클릭
        if random.choice([True, False]):  # 50% 확률로 Tab 또는 직접 클릭
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(random.randint(300, 600))
        else:
            # 비밀번호 필드 랜덤 위치 클릭
            pw_input = await page.query_selector('#password')
            if pw_input:
                box = await pw_input.bounding_box()
                if box:
                    margin_x = box['width'] * 0.15
                    margin_y = box['height'] * 0.15
                    click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                    click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                    
                    await page.mouse.click(click_x, click_y)
                    logger.info(f"PW 필드 랜덤 클릭: ({click_x:.1f}, {click_y:.1f})")
                else:
                    await page.click('#password')
            else:
                await page.click('#password')
            # PW 필드 클릭 후 약 1초 대기 (사람처럼)
            await page.wait_for_timeout(random.randint(800, 1200))
        
        # 비밀번호 필드 전체 선택
        await page.keyboard.press('Control+A')
        await page.wait_for_timeout(random.randint(500, 900))  # 선택 확인 시간 증가
        
        # 클립보드에 비밀번호 복사
        pyperclip.copy(password)
        await page.wait_for_timeout(random.randint(400, 800))  # 복사 시간 증가
        
        # 붙여넣기
        await page.keyboard.press('Control+V')
        await page.wait_for_timeout(random.randint(600, 1100))  # 확인 시간 증가
        
        # 12% 확률로 비밀번호 필드 재클릭 (확인)
        if random.random() < 0.12:
            await page.click('#password')
            await page.wait_for_timeout(random.randint(300, 500))
            logger.info("PW 필드 재확인 클릭")
        
        # 로그인 버튼 hover 효과 (망설임)
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            box = await submit_button.bounding_box()
            if box:
                # 버튼 위로 마우스 이동
                await page.mouse.move(
                    box['x'] + box['width'] / 2,
                    box['y'] + box['height'] / 2,
                    steps=random.randint(5, 10)
                )
                await page.wait_for_timeout(random.randint(300, 600))  # hover 시간
        
        logger.info("클립보드 붙여넣기 완료")
    
    async def _javascript_input_fallback(self, page: Page, username: str, password: str):
        """클립보드 실패시 JavaScript를 통한 직접 입력 폴백"""
        try:
            # ID 입력 - 랜덤 클릭 적용
            id_input = await page.query_selector('#loginId')
            if id_input:
                box = await id_input.bounding_box()
                if box:
                    margin_x = box['width'] * 0.15
                    margin_y = box['height'] * 0.15
                    click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                    click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                    
                    await page.mouse.click(click_x, click_y)
                    logger.info(f"[Fallback] ID 필드 랜덤 클릭: ({click_x:.1f}, {click_y:.1f})")
                else:
                    await page.click('#loginId')
            else:
                await page.click('#loginId')
            
            # ID 필드 클릭 후 약 1초 대기 (사람처럼)
            await page.wait_for_timeout(random.randint(800, 1200))
            await page.evaluate('document.querySelector("#loginId").value = ""')
            await page.wait_for_timeout(random.randint(100, 200))
            
            # 한 글자씩 입력하는 것처럼 보이게
            for i in range(len(username)):
                partial_text = username[:i+1]
                await page.evaluate(f'document.querySelector("#loginId").value = "{partial_text}"')
                await page.wait_for_timeout(random.randint(50, 150))
            
            # Tab키로 이동 또는 직접 랜덤 클릭
            if random.choice([True, False]):
                await page.keyboard.press('Tab')
                await page.wait_for_timeout(random.randint(300, 600))
            else:
                # PW 필드 랜덤 클릭
                pw_input = await page.query_selector('#password')
                if pw_input:
                    box = await pw_input.bounding_box()
                    if box:
                        margin_x = box['width'] * 0.15
                        margin_y = box['height'] * 0.15
                        click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                        click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                        
                        await page.mouse.click(click_x, click_y)
                        logger.info(f"[Fallback] PW 필드 랜덤 클릭: ({click_x:.1f}, {click_y:.1f})")
                    else:
                        await page.click('#password')
                else:
                    await page.click('#password')
                # PW 필드 클릭 후 약 1초 대기 (사람처럼)
                await page.wait_for_timeout(random.randint(800, 1200))
            
            # 비밀번호 필드 입력
            await page.evaluate(f'document.querySelector("#password").value = ""')
            await page.wait_for_timeout(random.randint(100, 200))
            
            for i in range(len(password)):
                partial_text = password[:i+1]
                await page.evaluate(f'document.querySelector("#password").value = "{partial_text}"')
                await page.wait_for_timeout(random.randint(50, 150))
            
        except Exception as e:
            logger.error(f"JavaScript 입력도 실패: {e}")
            # 최종 폴백: 간단한 타이핑
            await self._human_like_typing_fallback(page, '#loginId', username)
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(300)
            await self._human_like_typing_fallback(page, '#password', password)
    
    async def _javascript_direct_input(self, page: Page, username: str, password: str):
        """클립보드 실패시 JavaScript를 통한 직접 입력"""
        try:
            logger.info("🔧 JavaScript를 통한 직접 입력 방식으로 로그인...")
            
            # ID 필드 랜덤 클릭 및 입력
            id_input = await page.query_selector('#loginId')
            if id_input:
                box = await id_input.bounding_box()
                if box:
                    margin_x = box['width'] * 0.15
                    margin_y = box['height'] * 0.15
                    click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                    click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                    
                    await page.mouse.click(click_x, click_y)
                    logger.info(f"ID 필드 랜덤 클릭: ({click_x:.1f}, {click_y:.1f})")
                else:
                    await page.click('#loginId')
            else:
                await page.click('#loginId')
            
            # ID 필드 클릭 후 약 1초 대기 (사람처럼)
            await page.wait_for_timeout(random.randint(800, 1200))
            
            # JavaScript로 직접 값 설정
            await page.evaluate(f'document.querySelector("#loginId").value = ""')
            await page.wait_for_timeout(random.randint(100, 200))
            
            # 한 글자씩 입력하는 것처럼 보이게
            for i in range(len(username)):
                partial_text = username[:i+1]
                await page.evaluate(f'document.querySelector("#loginId").value = "{partial_text}"')
                await page.wait_for_timeout(random.randint(50, 150))
            
            # Tab키로 이동 또는 직접 랜덤 클릭
            if random.choice([True, False]):
                await page.keyboard.press('Tab')
                await page.wait_for_timeout(random.randint(300, 600))
            else:
                # PW 필드 랜덤 클릭
                pw_input = await page.query_selector('#password')
                if pw_input:
                    box = await pw_input.bounding_box()
                    if box:
                        margin_x = box['width'] * 0.15
                        margin_y = box['height'] * 0.15
                        click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
                        click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
                        
                        await page.mouse.click(click_x, click_y)
                        logger.info(f"PW 필드 랜덤 클릭: ({click_x:.1f}, {click_y:.1f})")
                    else:
                        await page.click('#password')
                else:
                    await page.click('#password')
                # PW 필드 클릭 후 약 1초 대기 (사람처럼)
                await page.wait_for_timeout(random.randint(800, 1200))
            
            # 비밀번호 필드 입력
            await page.evaluate(f'document.querySelector("#password").value = ""')
            await page.wait_for_timeout(random.randint(100, 200))
            
            for i in range(len(password)):
                partial_text = password[:i+1]
                await page.evaluate(f'document.querySelector("#password").value = "{partial_text}"')
                await page.wait_for_timeout(random.randint(50, 150))
            
            logger.info("✅ JavaScript 직접 입력 완료")
            
        except Exception as e:
            logger.error(f"❌ JavaScript 입력 실패: {e}")
            # 최종 폴백: 간단한 타이핑
            await self._human_like_typing_fallback(page, '#loginId', username)
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(300)
            await self._human_like_typing_fallback(page, '#password', password)
    
    async def _natural_page_interaction(self, page: Page):
        """자연스러운 페이지 상호작용 (스크롤, 클릭, 마우스 이동)"""
        actions = random.randint(2, 4)
        for _ in range(actions):
            action_type = random.choice(['scroll', 'mouse_move', 'empty_click'])
            
            if action_type == 'scroll':
                # 작은 스크롤
                await page.mouse.wheel(0, random.randint(-100, 100))
                await page.wait_for_timeout(random.randint(200, 500))
                
            elif action_type == 'mouse_move':
                # 랜덤 마우스 이동
                await page.mouse.move(
                    random.randint(200, 800),
                    random.randint(200, 600),
                    steps=random.randint(3, 8)
                )
                await page.wait_for_timeout(random.randint(100, 300))
                
            elif action_type == 'empty_click':
                # 빈 공간 클릭
                x = random.randint(100, 400)
                y = random.randint(100, 300)
                await page.mouse.click(x, y)
                await page.wait_for_timeout(random.randint(200, 400))
                logger.debug(f"빈 공간 클릭: ({x}, {y})")
    
    async def _human_like_hesitation(self, page: Page, element_selector: str):
        """버튼이나 링크를 클릭하기 전 망설임 표현"""
        element = await page.query_selector(element_selector)
        if element:
            box = await element.bounding_box()
            if box:
                # 요소 근처로 마우스 이동
                near_x = box['x'] + box['width'] / 2 + random.randint(-50, 50)
                near_y = box['y'] + box['height'] / 2 + random.randint(-50, 50)
                await page.mouse.move(near_x, near_y, steps=random.randint(5, 10))
                await page.wait_for_timeout(random.randint(200, 400))
                
                # 요소 위로 정확히 이동
                await page.mouse.move(
                    box['x'] + box['width'] / 2,
                    box['y'] + box['height'] / 2,
                    steps=random.randint(3, 6)
                )
                await page.wait_for_timeout(random.randint(300, 700))  # hover 망설임
    
    async def _human_like_typing_fallback(self, page: Page, selector: str, text: str):
        """클립보드 실패시 사용하는 간단한 타이핑 방식"""
        # 필드 클릭
        await page.click(selector)
        await asyncio.sleep(random.uniform(0.3, 0.7))
        
        # 필드 클리어
        await page.fill(selector, "")
        await asyncio.sleep(random.uniform(0.2, 0.4))
        
        # 한 글자씩 타이핑 (간단한 버전)
        for char in text:
            await page.type(selector, char, delay=random.uniform(80, 150))
            if char in ' @.':
                await asyncio.sleep(random.uniform(0.2, 0.5))
    
    async def _enhanced_random_button_click(self, page: Page, selector: str) -> bool:
        """버튼의 랜덤 위치 클릭 (Enhanced 버전)"""
        button = await page.query_selector(selector)
        if not button:
            logger.error(f"버튼을 찾을 수 없음: {selector}")
            return False
        
        # 버튼의 bounding box 가져오기
        box = await button.bounding_box()
        if not box:
            logger.error("버튼 위치를 가져올 수 없음")
            return False
        
        # 버튼 내부의 랜덤 위치 계산
        # 가장자리를 피하고 중심부 70% 영역 내에서 클릭
        margin_x = box['width'] * 0.15
        margin_y = box['height'] * 0.15
        
        click_x = box['x'] + margin_x + random.random() * (box['width'] - 2 * margin_x)
        click_y = box['y'] + margin_y + random.random() * (box['height'] - 2 * margin_y)
        
        logger.info(f"버튼 랜덤 클릭 위치: ({click_x:.1f}, {click_y:.1f})")
        
        # 마우스를 클릭 위치로 이동 (자연스럽게)
        await page.mouse.move(click_x, click_y, steps=random.randint(10, 20))
        await page.wait_for_timeout(random.randint(100, 300))
        
        # 클릭
        await page.mouse.down()
        await page.wait_for_timeout(random.randint(50, 150))
        await page.mouse.up()
        
        return True
    
    
    async def _login_with_stealth(self, page: Page, username: str, password: str) -> bool:
        """스텔스 모드 로그인 - 완전한 인간적 행동 시뮬레이션"""
        try:
            logger.info("🚀 완전 스텔스 모드 로그인 시작...")
            
            # 로그인 페이지로 직접 이동
            await page.goto("https://store.coupangeats.com/merchant/login", wait_until='domcontentloaded')
            await page.wait_for_timeout(random.randint(2000, 3000))
            
            # 2. 페이지 검증
            page_title = await page.title()
            current_url = page.url
            logger.info(f"📄 페이지 제목: {page_title}")
            logger.info(f"🔗 현재 URL: {current_url}")
            
            # 랜덤 마우스 움직임 (인간적인 행동)
            for _ in range(random.randint(2, 4)):
                x = random.randint(200, 800)
                y = random.randint(200, 600)
                await page.mouse.move(x, y, steps=random.randint(5, 10))
                await page.wait_for_timeout(random.randint(100, 300))
            
            # 3. 로그인 필드 확인 및 대기
            logger.debug("🔍 로그인 필드 찾는 중...")
            await page.wait_for_selector('#loginId', timeout=10000)
            await page.wait_for_selector('#password', timeout=10000)
            await page.wait_for_selector('button[type="submit"]', timeout=10000)
            
            # 4. 인간적인 행동으로 페이지 탐색
            # 페이지에서 몇 번 마우스 움직이기
            for _ in range(random.randint(2, 4)):
                x = random.randint(200, 1000)
                y = random.randint(200, 700)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # 5. 강화된 클립보드 로그인 (가장 안정적)
            await self._enhanced_clipboard_login(page, username, password)
            
            # 6. 사람이 확인하는 것처럼 잠시 대기
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            # 7. 로그인 버튼 랜덤 위치 클릭
            success = await self._enhanced_random_button_click(page, 'button[type="submit"]')
            if not success:
                logger.error("로그인 버튼 클릭 실패")
                return False
            
            
            # 8. 로그인 결과 대기
            logger.info("로그인 응답 대기 중...")
            
            # URL 변경 대기 (최대 20초)
            for i in range(20):
                await page.wait_for_timeout(1000)
                current_url = page.url
                
                if "/merchant/login" not in current_url:
                    logger.info(f"로그인 성공! URL: {current_url}")
                    return True
                
                # 에러 메시지 확인
                error_element = await page.query_selector('.error, .alert, [class*="error"]')
                if error_element:
                    error_text = await error_element.inner_text()
                    if error_text and error_text.strip():
                        logger.error(f"로그인 에러: {error_text}")
                        return False
            
            logger.warning(f"로그인 시도 실패")
            return False
                
        except Exception as e:
            logger.error(f"스텔스 로그인 오류: {e}")
            try:
                await page.screenshot(path=f"stealth_login_error_{int(time.time())}.png")
            except:
                pass
            return False
    
    async def _login(self, page: Page, username: str, password: str) -> bool:
        """로그인 수행 - 원래 단순한 방식으로 복원"""
        try:
            logger.info("쿠팡잇츠 로그인 시작...")
            
            # 로그인 페이지로 직접 이동 (단순하게)
            logger.info("로그인 페이지로 이동 중...")
            await page.goto("https://store.coupangeats.com/merchant/login", wait_until='domcontentloaded', timeout=30000)
            
            # 페이지 로딩 대기
            await page.wait_for_timeout(5000)
            
            # 페이지가 제대로 로드되었는지 확인
            page_title = await page.title()
            logger.info(f"페이지 제목: {page_title}")
            
            # 페이지 내용 확인
            page_content = await page.content()
            logger.info(f"페이지 내용 길이: {len(page_content)}자")
            
            if len(page_content) < 1000:
                logger.error("페이지가 제대로 로드되지 않았습니다 (내용이 너무 적음)")
                await page.screenshot(path=f"page_load_error_{int(time.time())}.png")
                return False
            
            # 로그인 필드 대기 및 확인
            logger.info("로그인 필드 찾는 중...")
            try:
                await page.wait_for_selector('#loginId', timeout=10000)
                await page.wait_for_selector('#password', timeout=10000)
                await page.wait_for_selector('button[type="submit"]', timeout=10000)
                logger.info("로그인 필드 모두 발견됨")
            except Exception as field_error:
                logger.error(f"로그인 필드를 찾을 수 없습니다: {field_error}")
                await page.screenshot(path=f"no_login_fields_{int(time.time())}.png")
                return False
            
            # 간단한 마우스 움직임
            await page.mouse.move(400, 300)
            await page.wait_for_timeout(1000)
            
            # ID 입력
            logger.info("ID 입력 중...")
            await page.click('#loginId')
            await page.wait_for_timeout(500)
            await page.fill('#loginId', username)
            await page.wait_for_timeout(1000)
            
            # 비밀번호 입력
            logger.info("비밀번호 입력 중...")
            await page.click('#password')
            await page.wait_for_timeout(500)
            await page.fill('#password', password)
            await page.wait_for_timeout(1000)
            
            logger.info("로그인 정보 입력 완료")
            
            # 로그인 버튼 클릭
            await page.click('button[type="submit"]')
            logger.info("로그인 버튼 클릭 완료")
            
            # 로그인 결과 대기
            await page.wait_for_timeout(5000)
            
            # 현재 URL 확인
            current_url = page.url
            logger.info(f"로그인 후 URL: {current_url}")
            
            # 로그인 성공 확인
            if "login" not in current_url:
                logger.info("로그인 성공! URL이 변경됨")
                return True
            
            # 에러 메시지 확인
            error_elements = await page.query_selector_all('.error, .alert, [class*="error"]')
            for error_element in error_elements:
                try:
                    error_text = await error_element.inner_text()
                    if error_text and error_text.strip():
                        logger.error(f"로그인 에러: {error_text.strip()}")
                        return False
                except:
                    continue
            
            # 로그인 성공 지표 확인
            success_selectors = [
                'a[href*="management"]',
                'a[href*="reviews"]', 
                '[class*="dashboard"]',
                '.merchant-menu'
            ]
            
            for selector in success_selectors:
                if await page.query_selector(selector):
                    logger.info(f"로그인 성공 지표 발견: {selector}")
                    return True
            
            # 스크린샷 저장
            await page.screenshot(path=f"login_result_{int(time.time())}.png")
            logger.error("로그인 성공 지표를 찾을 수 없습니다")
            return False
                
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
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

    async def _pre_login_validation(self, page: Page):
        """로그인 전 브라우저 상태 사전 확인"""
        logger.info("🔍 로그인 전 브라우저 상태 검증...")
        
        # 페이지 안정성 체크
        try:
            page_title = await page.title()
            logger.info(f"페이지 제목: {page_title}")
            
            # JavaScript 엔진 상태 확인
            js_test = await page.evaluate("() => typeof navigator !== 'undefined'")
            if not js_test:
                logger.warning("⚠️ JavaScript 엔진 이상 감지")
                await page.reload(wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
            
            # WebGL 상태 확인
            webgl_test = await page.evaluate("""() => {
                try {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    return gl !== null;
                } catch (e) {
                    return false;
                }
            }""")
            logger.info(f"WebGL 상태: {'정상' if webgl_test else '비활성화'}")
            
        except Exception as e:
            logger.warning(f"사전 검증 중 오류: {e}")
    
    async def _inject_stability_enhancements(self, page: Page):
        """안정성 향상을 위한 추가 스크립트 주입"""
        await page.evaluate("""
            (function() {
                'use strict';
                
                // 네트워크 안정성 향상
                if (window.XMLHttpRequest) {
                    const originalOpen = XMLHttpRequest.prototype.open;
                    XMLHttpRequest.prototype.open = function() {
                        try {
                            return originalOpen.apply(this, arguments);
                        } catch (e) {
                            console.log('[Stability] XMLHttpRequest 에러 처리:', e);
                            return;
                        }
                    };
                }
                
                // Promise 에러 방지
                window.addEventListener('unhandledrejection', function(event) {
                    console.log('[Stability] Promise rejection 처리:', event.reason);
                    event.preventDefault();
                });
                
                // 타이밍 안정성 향상
                const originalSetTimeout = window.setTimeout;
                window.setTimeout = function(callback, delay) {
                    try {
                        return originalSetTimeout(function() {
                            try {
                                callback();
                            } catch (e) {
                                console.log('[Stability] setTimeout 콜백 에러:', e);
                            }
                        }, delay);
                    } catch (e) {
                        console.log('[Stability] setTimeout 에러:', e);
                    }
                };
                
                // 이벤트 리스너 안정성
                const originalAddEventListener = EventTarget.prototype.addEventListener;
                EventTarget.prototype.addEventListener = function(type, listener, options) {
                    try {
                        const wrappedListener = function(event) {
                            try {
                                if (typeof listener === 'function') {
                                    listener.call(this, event);
                                } else if (listener && typeof listener.handleEvent === 'function') {
                                    listener.handleEvent(event);
                                }
                            } catch (e) {
                                console.log('[Stability] Event listener 에러:', e);
                            }
                        };
                        return originalAddEventListener.call(this, type, wrappedListener, options);
                    } catch (e) {
                        console.log('[Stability] addEventListener 에러:', e);
                    }
                };
                
                console.log('[Stability] 안정성 향상 스크립트 활성화');
            })();
        """)
    
    async def _enhanced_success_prediction(self, page: Page, analysis_result: Dict[str, Any]) -> int:
        """성공 확률 예측 알고리즘 개선"""
        score = 0
        
        # 네트워크 요청 패턴 (40점)
        network_requests = analysis_result.get('network_requests', 0)
        if 3 <= network_requests <= 8:
            score += 40
        elif network_requests <= 12:
            score += 25
        else:
            score += 10
        
        # 콘솔 에러 수 (30점)
        console_errors = analysis_result.get('console_errors', 0)
        if console_errors == 0:
            score += 30
        elif console_errors <= 2:
            score += 20
        else:
            score += 5
        
        # 페이지 로딩 시간 (20점)
        total_time = analysis_result.get('total_time', 0)
        if 5 <= total_time <= 15:
            score += 20
        elif total_time <= 25:
            score += 15
        else:
            score += 5
        
        # 성공 지표 존재 (10점)
        success_indicators = analysis_result.get('success_indicators', [])
        if success_indicators:
            score += 10
        
        # 추가 안정성 검사
        try:
            # 현재 URL 확인
            current_url = page.url
            if "/merchant/login" not in current_url:
                score += 20  # 보너스 점수
            
            # JavaScript 엔진 상태
            js_alive = await page.evaluate("() => typeof window !== 'undefined'")
            if js_alive:
                score += 5
            
        except:
            score -= 10
        
        return max(0, min(100, score))

    async def test_login(self, username: str, password: str) -> bool:
        """테스트용 로그인 메서드 - 브라우저 시작부터 종료까지 전체 과정"""
        logger.info("🧪 테스트 로그인 시작...")
        
        browser = None
        
        try:
            # Playwright 브라우저 시작 (스텔스 모드)
            async with async_playwright() as p:
                # 스텔스 브라우저 설정
                browser_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--exclude-switches=enable-automation',
                    '--disable-automation',
                    '--disable-extensions-http-throttling',
                    '--use-gl=desktop',
                    '--enable-webgl',
                    '--enable-webgl2',
                    '--disable-http2',  # HTTP/2 프로토콜 에러 방지
                    '--disable-quic',
                    '--force-http-1',  # HTTP/1.1 강제 사용
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-networking',  # 백그라운드 네트워크 차단
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-breakpad',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-default-apps',
                    '--disable-sync',  # 동기화 비활성화
                    '--metrics-recording-only',  # 메트릭 기록만
                    '--disable-crash-reporter'  # 크래시 리포터 비활성화
                ]
                
                # 프록시 및 User-Agent 사전 설정
                if self.proxy_manager:
                    self.current_proxy = self.proxy_manager.get_random_proxy()
                if self.ua_rotator:
                    self.current_user_agent = self.ua_rotator.get_smart_user_agent()
                
                logger.info(f"🌐 선택된 프록시: {self.current_proxy or '직접 연결'}")
                logger.info(f"🎭 선택된 User-Agent: {self.current_user_agent[:50] if self.current_user_agent else 'N/A'}...")
                
                # 브라우저 시작 옵션
                launch_options = {
                    'headless': False,
                    'args': browser_args
                }
                
                # 프록시가 있는 경우 브라우저 시작 시 설정
                if self.current_proxy:
                    launch_options['proxy'] = {'server': self.current_proxy}
                
                browser = await p.chromium.launch(**launch_options)
                
                # 컨텍스트 및 페이지 생성
                # 더 일반적인 해상도 사용 (핑거프린트 분석 결과 기반)
                viewport_options = [
                    {'width': 1920, 'height': 1080},  # FHD - 가장 일반적
                    {'width': 1366, 'height': 768},   # 노트북 표준
                    {'width': 1536, 'height': 864},   # Windows 기본 스케일링
                ]
                selected_viewport = random.choice(viewport_options)
                
                # 컨텍스트 생성 옵션
                context_options = {
                    'viewport': selected_viewport,
                    'user_agent': self.current_user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                context = await browser.new_context(**context_options)
                
                page = await context.new_page()
                
                # 모니터링 시스템 초기화
                if not hasattr(self, 'monitor'):
                    self.monitor = LoginSuccessMonitor()
                if not hasattr(self, 'retry_strategy'):
                    self.retry_strategy = AdaptiveRetryStrategy()
                
                # 스텔스 로그인 시도
                success = await self._login_with_stealth_monitored(page, username, password)
                
                # 성공/실패 피드백
                if success:
                    logger.info("🎉 로그인 성공!")
                    if self.ua_rotator and self.current_user_agent:
                        self.ua_rotator.mark_success(self.current_user_agent)
                    logger.info("✅ User-Agent 성공으로 기록됨")
                else:
                    logger.warning("❌ 로그인 실패")
                    if self.ua_rotator and self.current_user_agent:
                        self.ua_rotator.mark_failure(self.current_user_agent)
                    if self.proxy_manager and self.current_proxy:
                        self.proxy_manager.mark_proxy_failed(self.current_proxy)
                    logger.info("❌ User-Agent/프록시 실패로 기록됨")
                
                logger.info(f"🧪 테스트 로그인 결과: {'성공' if success else '실패'}")
                return success
            
        except Exception as e:
            logger.error(f"테스트 로그인 중 오류: {e}")
            return False
        
        finally:
            # 브라우저 정리
            if browser:
                try:
                    await browser.close()
                    logger.debug("브라우저 정리 완료")
                except:
                    pass


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