"""
배달의민족 인증 서비스 (간단한 버전)
Redis 없이 메모리에서만 관리
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from playwright.async_api import async_playwright
from supabase import create_client, Client

from ..shared.logger import get_logger
from ..shared.config import settings

logger = get_logger(__name__)

class BaeminAuthService:
    """배달의민족 인증 및 세션 관리 서비스 (간단한 버전)"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL if hasattr(settings, 'SUPABASE_URL') and settings.SUPABASE_URL 
            else os.getenv('NEXT_PUBLIC_SUPABASE_URL', ''),
            settings.SUPABASE_SERVICE_KEY if hasattr(settings, 'SUPABASE_SERVICE_KEY') and settings.SUPABASE_SERVICE_KEY
            else os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
        )
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        # 메모리에 임시 저장
        self.credentials_cache = {}
        self.session_cache = {}
        
    async def initialize(self):
        """서비스 초기화 (Redis 없이)"""
        logger.info("BaeminAuthService initialized (simple mode)")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """암호화 키 생성 또는 조회"""
        key_file = os.path.join(settings.DATA_DIR if hasattr(settings, 'DATA_DIR') else 'data', 'baemin_encryption.key')
        
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt_password(self, password: str) -> str:
        """비밀번호 암호화"""
        return self.fernet.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """비밀번호 복호화"""
        return self.fernet.decrypt(encrypted_password.encode()).decode()
    
    async def store_credentials(
        self, 
        user_id: str, 
        username: str, 
        password: str
    ) -> Dict[str, Any]:
        """로그인 정보 저장 (메모리에)"""
        try:
            encrypted_password = self.encrypt_password(password)
            
            # 메모리에 저장
            self.credentials_cache[user_id] = {
                "username": username,
                "password": encrypted_password,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"Credentials stored for user {user_id}")
            
            return {
                "success": True,
                "message": "인증 정보가 저장되었습니다"
            }
            
        except Exception as e:
            logger.error(f"Failed to store credentials for user {user_id}: {e}")
            return {
                "success": False,
                "message": f"인증 정보 저장 실패: {str(e)}"
            }
    
    async def get_credentials(self, user_id: str) -> Optional[Dict[str, str]]:
        """저장된 로그인 정보 조회"""
        try:
            # 메모리에서 조회
            if user_id in self.credentials_cache:
                creds = self.credentials_cache[user_id]
                return {
                    "username": creds["username"],
                    "password": self.decrypt_password(creds["password"])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get credentials for user {user_id}: {e}")
            return None
    
    async def verify_credentials(
        self, 
        username: str, 
        password: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """배민 로그인 정보 검증 (브라우저 표시)"""
        browser = None
        try:
            async with async_playwright() as p:
                # headless를 False로 설정하여 브라우저 표시
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
                
                # 로그인 페이지 접근
                logger.info("Navigating to Baemin login page...")
                await page.goto("https://biz-member.baemin.com/login", timeout=timeout * 1000)
                
                # 로그인 정보 입력
                logger.info("Entering login credentials...")
                await page.fill('input[data-testid="id"]', username)
                await page.fill('input[data-testid="password"]', password)
                
                # 로그인 버튼 클릭
                logger.info("Clicking login button...")
                await page.click('button[type="submit"]')
                
                # 결과 대기
                await page.wait_for_timeout(3000)
                
                current_url = page.url
                logger.info(f"Current URL after login: {current_url}")
                
                if "login" not in current_url:
                    # 로그인 성공
                    cookies = await context.cookies()
                    session_data = json.dumps([{
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie['domain'],
                        'path': cookie['path']
                    } for cookie in cookies])
                    
                    return {
                        "success": True,
                        "message": "로그인 성공",
                        "session_data": session_data,
                        "redirect_url": current_url
                    }
                else:
                    return {
                        "success": False,
                        "message": "로그인 정보가 올바르지 않습니다.",
                        "error_code": "invalid_credentials"
                    }
                
        except Exception as e:
            logger.error(f"Login verification failed: {e}")
            return {
                "success": False,
                "message": f"로그인 검증 중 오류 발생: {str(e)}",
                "error_code": "verification_error"
            }
        
        finally:
            if browser:
                await browser.close()
    
    async def update_session_status(
        self, 
        user_id: str, 
        is_active: bool,
        session_data: Optional[str] = None
    ) -> bool:
        """세션 상태 업데이트 (메모리에)"""
        try:
            self.session_cache[user_id] = {
                "is_active": is_active,
                "last_update": datetime.now().isoformat(),
                "session_data": session_data or ""
            }
            
            logger.info(f"Session status updated for user {user_id}: {is_active}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session status for user {user_id}: {e}")
            return False
    
    async def get_session_status(self, user_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        if user_id in self.session_cache:
            return self.session_cache[user_id]
        
        return {
            "is_active": False,
            "last_update": None,
            "session_data": ""
        }
    
    async def cleanup_expired_sessions(self):
        """만료된 세션 정리 (필요시 구현)"""
        pass
    
    async def close(self):
        """서비스 종료"""
        logger.info("BaeminAuthService closed")