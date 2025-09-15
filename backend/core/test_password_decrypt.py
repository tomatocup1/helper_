#!/usr/bin/env python3
"""
비밀번호 복호화 테스트
"""

import os
import sys
import codecs
from dotenv import load_dotenv
from supabase import create_client

# Windows 환경 UTF-8 설정
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# 현재 디렉토리 경로 추가
sys.path.append(os.path.dirname(__file__))
from password_decrypt import decrypt_password

# 환경변수 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Supabase 클라이언트 생성
supabase = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# 네이버 계정 정보 조회
print("🔍 네이버 계정 정보 조회 중...")
result = supabase.table('platform_stores')\
    .select('store_name, platform_id, platform_pw')\
    .eq('platform', 'naver')\
    .eq('is_active', True)\
    .limit(1)\
    .execute()

if result.data:
    store = result.data[0]
    print(f"\n📍 매장: {store['store_name']}")
    print(f"📧 ID: {store['platform_id']}")
    print(f"🔐 암호화된 비밀번호 (첫 50자): {store['platform_pw'][:50]}...")
    
    # ENCRYPTION_KEY로 시도
    try:
        decrypted_pw = decrypt_password(store['platform_pw'], platform='generic')
        print(f"✅ 복호화 성공 (ENCRYPTION_KEY 사용)!")
        print(f"   비밀번호 길이: {len(decrypted_pw)}자")
        print(f"   비밀번호 첫 3자: {decrypted_pw[:3]}***")
    except Exception as e:
        print(f"❌ 복호화 실패 (ENCRYPTION_KEY): {str(e)}")
        
        # NAVER_ENCRYPTION_KEY로 시도
        try:
            decrypted_pw = decrypt_password(store['platform_pw'], platform='naver')
            print(f"✅ 복호화 성공 (NAVER_ENCRYPTION_KEY 사용)!")
            print(f"   비밀번호 길이: {len(decrypted_pw)}자")
            print(f"   비밀번호 첫 3자: {decrypted_pw[:3]}***")
        except Exception as e2:
            print(f"❌ 복호화 실패 (NAVER_ENCRYPTION_KEY): {str(e2)}")
            
            # 환경변수 확인
            print("\n📋 환경변수 상태:")
            print(f"   ENCRYPTION_KEY 존재: {os.getenv('ENCRYPTION_KEY') is not None}")
            print(f"   NAVER_ENCRYPTION_KEY 존재: {os.getenv('NAVER_ENCRYPTION_KEY') is not None}")
else:
    print("❌ 네이버 계정 정보를 찾을 수 없습니다.")