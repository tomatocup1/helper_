#!/usr/bin/env python3
"""
쿠팡 답글 포스터 실행 래퍼
기존 사용법을 유지하면서 Enhanced 로그인 시스템 사용

사용법:
python run_coupang_reply_poster.py --store-uuid 2a528120-06ae-462e-9ed9-946002618a9d --limit 5
"""

import asyncio
import argparse
import sys
import os

# 프로젝트 루트를 Python 경로에 추가 (backend/core에서 실행할 때)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.core.coupang_reply_poster import CoupangReplyPoster

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    from supabase import create_client, Client
    
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL', '')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL 또는 Service Key가 설정되지 않았습니다.")
    
    return create_client(supabase_url, supabase_key)

async def get_store_credentials(store_uuid: str):
    """매장 UUID로 로그인 정보 조회"""
    try:
        supabase = get_supabase_client()
        
        # platform_stores 테이블에서 쿠팡 매장 정보 조회
        response = supabase.table('platform_stores').select(
            'platform_id, platform_pw, platform_store_id'
        ).eq('id', store_uuid).eq('platform', 'coupangeats').single().execute()
        
        if not response.data:
            raise ValueError(f"매장 정보를 찾을 수 없습니다: {store_uuid}")
        
        store_data = response.data
        
        # 비밀번호 복호화
        from backend.core.password_decrypt import decrypt_password
        decrypted_password = decrypt_password(store_data['platform_pw'])
        
        return {
            'username': store_data['platform_id'],
            'password': decrypted_password,
            'platform_store_id': store_data['platform_store_id']
        }
        
    except Exception as e:
        print(f"[ERROR] 매장 정보 조회 실패: {e}")
        return None

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='쿠팡 답글 포스터 (기존 사용법 호환)')
    parser.add_argument('--store-uuid', required=True, help='매장 UUID')
    # --limit 제거 (전체 미답변 리뷰 처리)
    parser.add_argument('--test-mode', action='store_true', help='테스트 모드 (실제 답글 등록 안함)')
    
    args = parser.parse_args()
    
    print(f"[COUPANG] 쿠팡 답글 포스터 시작 (Enhanced 로그인)")
    print(f"매장 UUID: {args.store_uuid}")
    print(f"최대 답글 수: 전체 (제한 없음)")
    print(f"테스트 모드: {'예' if args.test_mode else '아니오'}")

    # 매장 정보 조회
    print("\n[INFO] 매장 정보 조회 중...")
    credentials = await get_store_credentials(args.store_uuid)

    if not credentials:
        print("[ERROR] 매장 정보 조회 실패 - 프로그램 종료")
        return
    
    print(f"[SUCCESS] 매장 정보 조회 성공")
    print(f"로그인 ID: {credentials['username']}")
    print(f"플랫폼 매장 ID: {credentials['platform_store_id']}")

    # Enhanced 로그인으로 답글 포스터 실행
    print(f"\n[INFO] Enhanced 로그인으로 답글 포스터 실행...")

    try:
        poster = CoupangReplyPoster()
        result = await poster.post_replies(
            username=credentials['username'],
            password=credentials['password'],
            store_id=credentials['platform_store_id'],
            max_replies=None,  # 전체 미답변 리뷰 처리
            test_mode=args.test_mode
        )

        print(f"\n[SUCCESS] 답글 포스터 완료!")
        print(f"성공: {result.get('success', False)}")
        print(f"메시지: {result.get('message', 'N/A')}")

        posted_replies = result.get('posted_replies', [])
        print(f"등록된 답글: {len(posted_replies)}개")

        if posted_replies:
            print(f"\n[REPLIES] 등록된 답글 목록:")
            for i, reply in enumerate(posted_replies, 1):
                print(f"  {i}. 리뷰ID: {reply.get('review_id', 'N/A')}")
                reply_text = reply.get('reply_text', 'N/A')[:50]
                # 윈도우 콘솔 출력용으로만 이모지 제거 (실제 DB에는 원본 그대로 저장됨)
                try:
                    # UTF-8로 인코딩 가능한지 확인하고, 안전하게 출력
                    print(f"     답글: {reply_text}...")
                except UnicodeEncodeError:
                    # 윈도우 콘솔에서 출력 불가능한 문자가 있을 경우에만 제거
                    reply_text_safe = reply_text.encode('ascii', errors='ignore').decode('ascii')
                    print(f"     답글: {reply_text_safe}...")
        
    except Exception as e:
        print(f"[ERROR] 답글 포스터 실행 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())