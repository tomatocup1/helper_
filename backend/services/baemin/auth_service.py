"""
배달의민족 인증 서비스
로그인, 세션 관리, 암호화 처리
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import os
from cryptography.fernet import Fernet
import aioredis
from playwright.async_api import async_playwright, Browser, Page
from supabase import create_client, Client

from ..shared.logger import get_logger
from ..shared.config import settings

logger = get_logger(__name__)

class BaeminAuthService:
    """배달의민족 인증 및 세션 관리 서비스"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self.redis_client: Optional[aioredis.Redis] = None
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
    async def initialize(self):
        """서비스 초기화"""
        try:
            self.redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("BaeminAuthService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BaeminAuthService: {e}")
            raise
    
    def _get_or_create_encryption_key(self) -> bytes:
        """암호화 키 생성 또는 조회"""
        key_file = os.path.join(settings.DATA_DIR, 'baemin_encryption.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(settings.DATA_DIR, exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt_password(self, password: str) -> str:
        """비밀번호 암호화"""
        return self.fernet.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """비밀번호 복호화"""
        return self.fernet.decrypt(encrypted_password.encode()).decode()
    
    async def save_credentials(
        self, 
        user_id: str, 
        username: str, 
        password: str
    ) -> bool:
        """로그인 정보 저장 (암호화)"""
        try:
            encrypted_password = self.encrypt_password(password)
            
            # Redis에 임시 저장 (세션용)
            session_key = f"baemin_creds:{user_id}"
            await self.redis_client.hset(session_key, mapping={
                "username": username,
                "password": encrypted_password,
                "created_at": datetime.now().isoformat()
            })
            await self.redis_client.expire(session_key, 3600)  # 1시간 TTL
            
            # Supabase에 영구 저장 (옵션)
            if settings.SAVE_CREDENTIALS_TO_DB:
                result = self.supabase.table("platform_stores").update({
                    "platform_id": username,
                    "platform_pw": encrypted_password,
                    "updated_at": datetime.now().isoformat()
                }).eq("user_id", user_id).eq("platform", "baemin").execute()
                
                logger.info(f"Credentials saved for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save credentials for user {user_id}: {e}")
            return False
    
    async def get_credentials(self, user_id: str) -> Optional[Dict[str, str]]:
        """저장된 로그인 정보 조회"""
        try:
            # Redis에서 먼저 조회
            session_key = f"baemin_creds:{user_id}"
            creds = await self.redis_client.hgetall(session_key)
            
            if creds and "username" in creds:
                return {
                    "username": creds["username"],
                    "password": self.decrypt_password(creds["password"])
                }
            
            # Redis에 없으면 Supabase에서 조회
            if settings.SAVE_CREDENTIALS_TO_DB:
                result = self.supabase.table("platform_stores").select(
                    "platform_id, platform_pw"
                ).eq("user_id", user_id).eq("platform", "baemin").limit(1).execute()
                
                if result.data:
                    store = result.data[0]
                    if store["platform_id"] and store["platform_pw"]:
                        password = self.decrypt_password(store["platform_pw"])
                        
                        # Redis에 캐시
                        await self.redis_client.hset(session_key, mapping={
                            "username": store["platform_id"],
                            "password": store["platform_pw"],
                            "created_at": datetime.now().isoformat()
                        })
                        await self.redis_client.expire(session_key, 3600)
                        
                        return {
                            "username": store["platform_id"],
                            "password": password
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
        """배민 로그인 정보 검증"""
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
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
                await page.goto("https://biz-member.baemin.com/login", timeout=timeout * 1000)
                
                # 로그인 정보 입력
                await page.fill('input[data-testid="id"]', username)
                await page.fill('input[data-testid="password"]', password)
                
                # 로그인 버튼 클릭
                await page.click('button[type="submit"]')
                
                # 결과 대기
                await page.wait_for_timeout(3000)
                
                current_url = page.url
                
                if "dashboard" in current_url or "main" in current_url:
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
                
                elif "login" in current_url:
                    # 로그인 실패 - 에러 메시지 추출
                    error_elements = await page.query_selector_all('.error-message, .alert-danger, [class*="error"]')
                    error_message = "로그인 정보가 올바르지 않습니다."
                    
                    if error_elements:
                        error_text = await error_elements[0].text_content()
                        if error_text and error_text.strip():
                            error_message = error_text.strip()
                    
                    return {
                        "success": False,
                        "message": error_message,
                        "error_code": "invalid_credentials"
                    }
                
                else:
                    # 예상치 못한 리다이렉트
                    return {
                        "success": False,
                        "message": f"예상치 못한 리다이렉트: {current_url}",
                        "error_code": "unexpected_redirect"
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
        """세션 상태 업데이트"""
        try:
            # Redis에 세션 상태 저장
            session_key = f"baemin_session:{user_id}"
            session_info = {
                "is_active": str(is_active),
                "last_update": datetime.now().isoformat(),
                "session_data": session_data or ""
            }
            
            await self.redis_client.hset(session_key, mapping=session_info)
            if is_active:
                await self.redis_client.expire(session_key, 7200)  # 2시간 TTL
            
            # Supabase 업데이트
            result = self.supabase.table("platform_stores").update({
                "baemin_session_active": is_active,
                "baemin_last_login": datetime.now().isoformat() if is_active else None,
                "updated_at": datetime.now().isoformat()
            }).eq("user_id", user_id).eq("platform", "baemin").execute()
            
            logger.info(f"Session status updated for user {user_id}: {is_active}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session status for user {user_id}: {e}")
            return False
    
    async def get_session_status(self, user_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        try:
            # Redis에서 먼저 조회
            session_key = f"baemin_session:{user_id}"
            session_info = await self.redis_client.hgetall(session_key)
            
            if session_info:
                return {
                    "is_active": session_info.get("is_active", "false").lower() == "true",
                    "last_update": session_info.get("last_update"),
                    "session_data": session_info.get("session_data", "")
                }
            
            # Redis에 없으면 Supabase에서 조회
            result = self.supabase.table("platform_stores").select(
                "baemin_session_active, baemin_last_login"
            ).eq("user_id", user_id).eq("platform", "baemin").limit(1).execute()
            
            if result.data:
                store = result.data[0]
                return {
                    "is_active": store.get("baemin_session_active", False),
                    "last_update": store.get("baemin_last_login"),
                    "session_data": ""
                }
            
            return {
                "is_active": False,
                "last_update": None,
                "session_data": ""
            }
            
        except Exception as e:
            logger.error(f"Failed to get session status for user {user_id}: {e}")
            return {
                "is_active": False,
                "last_update": None,
                "session_data": ""
            }
    
    async def cleanup_expired_sessions(self):
        """만료된 세션 정리"""
        try:
            # 2시간 이상 된 세션을 비활성화
            cutoff_time = datetime.now() - timedelta(hours=2)
            
            result = self.supabase.table("platform_stores").update({
                "baemin_session_active": False,
                "updated_at": datetime.now().isoformat()
            }).eq("platform", "baemin").lt(
                "baemin_last_login", cutoff_time.isoformat()
            ).eq("baemin_session_active", True).execute()
            
            cleaned_count = len(result.data) if result.data else 0
            logger.info(f"Cleaned up {cleaned_count} expired baemin sessions")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
    
    async def close(self):
        """서비스 종료"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("BaeminAuthService closed")