#!/usr/bin/env python3
"""
비밀번호 복호화 유틸리티
프론트엔드와 동일한 AES-256-GCM 복호화
"""

import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

def decrypt_password(encrypted_data: str) -> str:
    """
    AES-256-GCM 복호화
    형식: iv:authTag:encrypted
    """
    try:
        # 환경변수에서 암호화 키 가져오기
        load_dotenv()
        secret_key = os.getenv('ENCRYPTION_KEY', 'your-32-character-secret-key-here!')
        
        # 암호화된 데이터 파싱
        parts = encrypted_data.split(':')
        if len(parts) != 3:
            raise ValueError('Invalid encrypted data format')
        
        iv = bytes.fromhex(parts[0])
        auth_tag = bytes.fromhex(parts[1])
        encrypted = bytes.fromhex(parts[2])
        
        # 키 생성 (SHA256 해시)
        key = hashlib.sha256(secret_key.encode()).digest()
        
        # AES-256-GCM 복호화
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, auth_tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # AAD 설정 (프론트엔드와 동일)
        decryptor.authenticate_additional_data(b'additional-data')
        
        # 복호화
        decrypted = decryptor.update(encrypted) + decryptor.finalize()
        
        return decrypted.decode('utf-8')
        
    except Exception as e:
        raise Exception(f"Failed to decrypt password: {str(e)}")


if __name__ == "__main__":
    # 테스트
    from supabase import create_client
    
    load_dotenv()
    supabase = create_client(
        os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )
    
    # 큰집닭강정 오산점 비밀번호 복호화 테스트
    result = supabase.table('platform_stores')\
        .select('store_name, platform_id, platform_pw')\
        .eq('platform_store_id', '14638971')\
        .eq('platform', 'baemin')\
        .single()\
        .execute()
    
    if result.data:
        store = result.data
        print(f"매장: {store['store_name']}")
        print(f"ID: {store['platform_id']}")
        
        try:
            decrypted_pw = decrypt_password(store['platform_pw'])
            print(f"복호화 성공! 비밀번호 길이: {len(decrypted_pw)}자")
        except Exception as e:
            print(f"복호화 실패: {str(e)}")