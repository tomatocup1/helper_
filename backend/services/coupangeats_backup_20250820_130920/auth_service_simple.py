"""
쿠팡이츠 인증 서비스
크롤링을 위한 로그인 정보 암호화 저장
"""

import os
import json
import uuid
from typing import Dict, Optional, Tuple
from pathlib import Path
from cryptography.fernet import Fernet
from datetime import datetime, timedelta

from ..shared.logger import get_logger
from ..shared.config import settings

logger = get_logger(__name__)

class CoupangEatsAuthService:
    """쿠팡이츠 인증 서비스 (Redis 없이 간단 버전)"""
    
    def __init__(self):
        self.data_dir = Path(settings.DATA_DIR)
        self.credentials_dir = self.data_dir / "coupangeats_credentials"
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        # 암호화 키 설정 - 배민과 동일한 키 파일 사용
        key_file = self.data_dir / "coupangeats_encryption.key"
        
        if key_file.exists():
            # 기존 키 사용
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            # 새 키 생성 및 저장
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.info("Generated new encryption key for CoupangEats")
        
        self.cipher = Fernet(key)
        
        logger.info("CoupangEats Auth Service initialized")
    
    async def store_credentials(
        self, 
        user_id: str, 
        username: str, 
        password: str
    ) -> Dict[str, any]:
        """
        사용자의 쿠팡이츠 로그인 정보를 암호화하여 저장
        
        Args:
            user_id: 사용자 ID
            username: 쿠팡이츠 아이디
            password: 쿠팡이츠 비밀번호
            
        Returns:
            저장 결과 딕셔너리
        """
        try:
            # 비밀번호 암호화
            encrypted_password = self.cipher.encrypt(password.encode()).decode()
            
            # 인증 정보 구성
            credentials = {
                "user_id": user_id,
                "username": username,
                "encrypted_password": encrypted_password,
                "created_at": datetime.now().isoformat(),
                "last_used": None,
                "session_active": False
            }
            
            # 파일에 저장
            credentials_file = self.credentials_dir / f"{user_id}_coupangeats.json"
            with open(credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Credentials stored for user {user_id}")
            
            return {
                "success": True,
                "message": "쿠팡이츠 로그인 정보가 안전하게 저장되었습니다.",
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Failed to store credentials for user {user_id}: {e}")
            return {
                "success": False,
                "message": f"로그인 정보 저장 실패: {str(e)}",
                "user_id": user_id
            }
    
    async def get_credentials(self, user_id: str) -> Optional[Dict[str, str]]:
        """
        사용자의 쿠팡이츠 로그인 정보 조회 및 복호화
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            복호화된 로그인 정보 또는 None
        """
        try:
            credentials_file = self.credentials_dir / f"{user_id}_coupangeats.json"
            
            if not credentials_file.exists():
                logger.warning(f"No credentials found for user {user_id}")
                return None
            
            # 파일에서 읽기
            with open(credentials_file, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            # 비밀번호 복호화
            encrypted_password = credentials["encrypted_password"]
            try:
                decrypted_password = self.cipher.decrypt(encrypted_password.encode()).decode()
            except Exception as decrypt_error:
                logger.error(f"Failed to decrypt password for user {user_id}: {decrypt_error}")
                return None
            
            # 마지막 사용 시간 업데이트
            credentials["last_used"] = datetime.now().isoformat()
            with open(credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, ensure_ascii=False, indent=2)
            
            return {
                "username": credentials["username"],
                "password": decrypted_password,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get credentials for user {user_id}: {e}")
            return None
    
    async def update_session_status(
        self, 
        user_id: str, 
        is_active: bool, 
        session_data: Optional[str] = None
    ) -> Dict[str, any]:
        """
        세션 상태 업데이트
        
        Args:
            user_id: 사용자 ID
            is_active: 세션 활성 상태
            session_data: 선택적 세션 데이터
            
        Returns:
            업데이트 결과
        """
        try:
            credentials_file = self.credentials_dir / f"{user_id}_coupangeats.json"
            
            if not credentials_file.exists():
                return {
                    "success": False,
                    "message": "사용자 인증 정보가 없습니다."
                }
            
            # 기존 정보 읽기
            with open(credentials_file, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            # 세션 상태 업데이트
            credentials["session_active"] = is_active
            credentials["last_session_update"] = datetime.now().isoformat()
            
            if session_data:
                credentials["session_data"] = session_data
            
            # 파일에 저장
            with open(credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Session status updated for user {user_id}: active={is_active}")
            
            return {
                "success": True,
                "message": "세션 상태가 업데이트되었습니다.",
                "user_id": user_id,
                "session_active": is_active
            }
            
        except Exception as e:
            logger.error(f"Failed to update session status for user {user_id}: {e}")
            return {
                "success": False,
                "message": f"세션 상태 업데이트 실패: {str(e)}"
            }
    
    async def delete_credentials(self, user_id: str) -> Dict[str, any]:
        """
        사용자의 쿠팡이츠 로그인 정보 삭제
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            삭제 결과
        """
        try:
            credentials_file = self.credentials_dir / f"{user_id}_coupangeats.json"
            
            if credentials_file.exists():
                credentials_file.unlink()
                logger.info(f"Credentials deleted for user {user_id}")
                return {
                    "success": True,
                    "message": "쿠팡이츠 로그인 정보가 삭제되었습니다."
                }
            else:
                return {
                    "success": False,
                    "message": "삭제할 로그인 정보가 없습니다."
                }
                
        except Exception as e:
            logger.error(f"Failed to delete credentials for user {user_id}: {e}")
            return {
                "success": False,
                "message": f"로그인 정보 삭제 실패: {str(e)}"
            }