#!/usr/bin/env python3
"""
배달의민족 자동 답글 등록 스크립트
- Supabase에서 필요한 정보 자동 조회
- 활성 매장의 답글 대기 리뷰 자동 처리
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from baemin_reply_poster import BaeminReplyPoster
from password_decrypt import decrypt_password


async def main():
    parser = argparse.ArgumentParser(description='배달의민족 답글 자동 등록 (Supabase 연동)')
    parser.add_argument('--user-id', help='사용자 ID (미지정시 기본값 사용)')
    parser.add_argument('--store-id', help='특정 매장 ID만 처리')
    parser.add_argument('--max-replies', type=int, default=10, help='최대 답글 등록 수 (기본: 10)')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드')
    parser.add_argument('--dry-run', action='store_true', help='실제 등록 없이 대상 리뷰만 확인')
    
    args = parser.parse_args()
    
    # Supabase 초기화
    load_dotenv()
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("[ERROR] Supabase 환경변수가 설정되지 않았습니다.")
        return False
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # 기본 사용자 ID 설정
    user_id = args.user_id or "a7654c42-10ed-435f-97d8-d2c2dfeccbcb"
    
    print("=" * 60)
    print("배달의민족 자동 답글 등록")
    print("=" * 60)
    print(f"사용자 ID: {user_id}")
    
    # 1. 활성 배민 매장 조회
    print("\n1. 활성 배민 매장 조회 중...")
    
    query = supabase.table('platform_stores')\
        .select('id, platform_store_id, store_name, platform_id, platform_pw')\
        .eq('user_id', user_id)\
        .eq('platform', 'baemin')\
        .eq('is_active', True)
    
    # 특정 매장 ID가 지정된 경우
    if args.store_id:
        query = query.eq('platform_store_id', args.store_id)
    
    stores_result = query.execute()
    
    if not stores_result.data:
        print("[ERROR] 활성 배민 매장이 없습니다.")
        return False
    
    print(f"[OK] {len(stores_result.data)}개의 활성 매장 발견")
    
    total_processed = 0
    total_success = 0
    total_failed = 0
    
    # 2. 각 매장별로 답글 등록 처리
    for store in stores_result.data:
        store_id = store['platform_store_id']
        store_name = store['store_name']
        store_uuid = store['id']
        
        print(f"\n{'='*50}")
        print(f"매장: {store_name} (ID: {store_id})")
        print(f"{'='*50}")
        
        # 답글 대기 리뷰 확인
        reviews_result = supabase.table('reviews_baemin')\
            .select('id, baemin_review_id, reviewer_name, rating')\
            .eq('platform_store_id', store_uuid)\
            .eq('reply_status', 'draft')\
            .neq('reply_text', None)\
            .limit(args.max_replies)\
            .execute()
        
        if not reviews_result.data:
            print("[INFO] 답글 대기 리뷰가 없습니다.")
            continue
        
        print(f"[FOUND] {len(reviews_result.data)}개의 답글 대기 리뷰 발견")
        
        # Dry run 모드인 경우 리뷰 정보만 출력
        if args.dry_run:
            for review in reviews_result.data:
                print(f"  - 리뷰 ID: {review['baemin_review_id']}")
                print(f"    작성자: {review['reviewer_name']} (평점: {review['rating']})")
            continue
        
        # 계정 정보 확인 및 복호화
        username = store.get('platform_id') or os.getenv('BAEMIN_USERNAME')
        encrypted_password = store.get('platform_pw')
        
        if not username:
            print("[WARN] 이 매장의 배민 계정 아이디가 없습니다.")
            print("  platform_stores 테이블에 platform_id를 저장하세요.")
            continue
        
        # 비밀번호 복호화
        try:
            if encrypted_password:
                password = decrypt_password(encrypted_password)
            else:
                password = os.getenv('BAEMIN_PASSWORD')
                if not password:
                    print("[WARN] 이 매장의 배민 계정 비밀번호가 없습니다.")
                    print("  platform_stores 테이블에 platform_pw를 저장하거나")
                    print("  BAEMIN_PASSWORD 환경변수를 설정하세요.")
                    continue
        except Exception as e:
            print(f"[ERROR] 비밀번호 복호화 실패: {str(e)}")
            continue
        
        # 답글 등록 실행
        print(f"\n[START] 답글 등록 시작...")
        
        try:
            poster = BaeminReplyPoster(
                headless=args.headless,
                timeout=30000
            )
            
            result = await poster.post_replies_batch(
                username=username,
                password=password,
                platform_store_id=store_id,
                user_id=user_id,
                max_replies=args.max_replies
            )
            
            total_processed += result.get('total', 0)
            total_success += result.get('success_count', 0)
            total_failed += result.get('failed_count', 0)
            
            if result['success']:
                print(f"[OK] 처리 완료: 성공 {result['success_count']}개, 실패 {result['failed_count']}개")
            else:
                print(f"[ERROR] 처리 실패: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"[ERROR] 오류 발생: {str(e)}")
            total_failed += len(reviews_result.data)
    
    # 3. 전체 결과 요약
    print(f"\n{'='*60}")
    print("[SUMMARY] 전체 처리 결과")
    print(f"{'='*60}")
    print(f"총 처리 시도: {total_processed}개")
    print(f"성공: {total_success}개")
    print(f"실패: {total_failed}개")
    
    if not args.dry_run and total_success > 0:
        print(f"\n[SUCCESS] {total_success}개의 리뷰에 답글이 성공적으로 등록되었습니다!")
    
    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)