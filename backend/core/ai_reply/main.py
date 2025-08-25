#!/usr/bin/env python3
"""
AI 답글 생성 시스템 메인 실행 스크립트
Main execution script for AI Reply Generation System
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import List

# 현재 디렉토리를 파이썬 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_reply_manager import AIReplyManager


class AIReplySystem:
    """AI 답글 생성 시스템 통합 관리"""
    
    def __init__(self):
        self.manager = AIReplyManager()
    
    async def generate_single_reply(self, review_id: str) -> bool:
        """단일 리뷰 답글 생성"""
        
        try:
            print(f"[AI] 리뷰 {review_id[:8]}... 답글 생성 시작")
            
            # 1. 리뷰 정보 조회
            review = await self._get_review(review_id)
            if not review:
                print(f"[ERROR] 리뷰를 찾을 수 없습니다: {review_id}")
                return False
            
            # 2. 매장 설정 조회
            store = await self._get_store(review['platform_store_id'])
            if not store:
                print(f"[ERROR] 매장 정보를 찾을 수 없습니다")
                return False
            
            # 3. AI 답글 생성
            result = await self.manager.generate_reply(review, store)
            
            # 4. 답글 검증
            analysis = await self.manager.analyze_review(review, store)
            validation = await self.manager.validate_reply(
                result.complete_reply, review, store, analysis.sentiment
            )
            
            # 5. 결과 출력
            print(f"\n{'='*60}")
            print(f"[REPLY] 생성된 답글")
            print(f"{'='*60}")
            print(result.complete_reply)
            print(f"\n{'='*60}")
            print(f"[ANALYSIS] 분석 결과")
            print(f"{'='*60}")
            print(f"감정: {analysis.sentiment} ({analysis.sentiment_score:.2f})")
            print(f"위험도: {analysis.risk_level}")
            print(f"승인 필요: {'예' if analysis.requires_approval else '아니오'}")
            print(f"키워드: {', '.join(analysis.keywords)}")
            print(f"\n{'='*60}")
            print(f"[VALIDATION] 품질 검증")
            print(f"{'='*60}")
            print(f"검증 통과: {'예' if validation.is_valid else '아니오'}")
            print(f"품질 점수: {validation.score:.2f}/1.0")
            print(f"AI 신뢰도: {result.ai_confidence_score:.2f}/1.0")
            print(f"생성 시간: {result.ai_generation_time_ms}ms")
            
            if validation.issues:
                print(f"[WARN] 이슈: {', '.join(validation.issues)}")
            if validation.warnings:
                print(f"⚡ 경고: {', '.join(validation.warnings)}")
            if validation.suggestions:
                print(f"💡 제안: {', '.join(validation.suggestions)}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 답글 생성 실패: {str(e)}")
            return False
    
    async def batch_process(self, user_id: str = None, store_id: str = None, limit: int = None, 
                          platforms: List[str] = None) -> bool:
        """배치 처리 (멀티플랫폼 지원)"""
        
        try:
            if user_id:
                # 사용자 기반 멀티플랫폼 처리
                print(f"[USER] 사용자 {user_id[:8]}... 멀티플랫폼 배치 처리 시작")
                if platforms:
                    print(f"   대상 플랫폼: {[p.upper() for p in platforms]}")
                
                results = await self.manager.process_user_reviews(user_id, platforms, limit)
                
                # 성공 여부 판단
                total_success = sum(summary.success for summary in results.values())
                return total_success > 0
                
            elif store_id:
                # 기존 방식: 단일 매장 처리 (기본 플랫폼 naver)
                platform = platforms[0] if platforms else 'naver'
                print(f"[STORE] 매장 {store_id} ({platform}) 배치 처리 시작")
                summary = await self.manager.process_store_reviews(store_id, platform, limit)
                return summary.success > 0
                
            else:
                # 전체 매장 처리 (기존 방식)
                print("[BATCH] 전체 매장 배치 처리 시작")
                results = await self.manager.process_all_active_stores(limit)
                return len(results) > 0
            
        except Exception as e:
            print(f"[ERROR] 배치 처리 실패: {str(e)}")
            return False
    
    async def manage_approvals(self, user_id: str, store_id: str = None) -> bool:
        """승인 관리"""
        
        try:
            print(f"[USER] 사용자 {user_id[:8]}... 승인 관리")
            
            # 승인 대기 중인 리뷰 조회
            pending = await self.manager.get_pending_approvals(user_id, store_id)
            
            if not pending:
                print("[OK] 승인 대기 중인 리뷰가 없습니다")
                return True
            
            print(f"[PENDING] 승인 대기 중인 리뷰: {len(pending)}개")
            
            for i, review in enumerate(pending[:5], 1):  # 처음 5개만 표시
                print(f"\n{i}. [{review.get('platform_store', {}).get('store_name', '매장')}]")
                print(f"   작성자: {review.get('reviewer_name', '익명')} ({review.get('rating', 0)}점)")
                print(f"   리뷰: {review.get('review_text', '')[:100]}...")
                print(f"   AI 답글: {review.get('ai_generated_reply', '')[:100]}...")
                print(f"   신뢰도: {review.get('ai_confidence_score', 0):.2f}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 승인 관리 실패: {str(e)}")
            return False
    
    async def auto_approve_positive(self, store_id: str) -> bool:
        """긍정 리뷰 자동 승인"""
        
        try:
            count = await self.manager.auto_approve_positive_reviews(store_id)
            print(f"[OK] 긍정 리뷰 {count}개 자동 승인 완료")
            return True
            
        except Exception as e:
            print(f"[ERROR] 자동 승인 실패: {str(e)}")
            return False
    
    async def approve_reply(self, review_id: str, user_id: str, notes: str = None) -> bool:
        """답글 승인"""
        
        try:
            success = await self.manager.approve_reply(review_id, user_id, notes)
            if success:
                print(f"[OK] 리뷰 {review_id[:8]} 승인 완료")
            return success
            
        except Exception as e:
            print(f"[ERROR] 답글 승인 실패: {str(e)}")
            return False
    
    async def reject_reply(self, review_id: str, user_id: str, reason: str) -> bool:
        """답글 거부"""
        
        try:
            success = await self.manager.reject_reply(review_id, user_id, reason)
            if success:
                print(f"[OK] 리뷰 {review_id[:8]} 거부 완료")
            return success
            
        except Exception as e:
            print(f"[ERROR] 답글 거부 실패: {str(e)}")
            return False
    
    async def _get_review(self, review_id: str):
        """리뷰 조회"""
        from supabase import create_client
        import os
        
        supabase = create_client(
            os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        response = supabase.table('reviews_naver')\
            .select('*')\
            .eq('id', review_id)\
            .single()\
            .execute()
        
        return response.data
    
    async def _get_store(self, store_id: str):
        """매장 조회"""
        from supabase import create_client
        import os
        
        supabase = create_client(
            os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        response = supabase.table('platform_stores')\
            .select('*')\
            .eq('id', store_id)\
            .single()\
            .execute()
        
        return response.data


async def main():
    """메인 함수"""
    
    parser = argparse.ArgumentParser(
        description='AI 답글 생성 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 단일 리뷰 답글 생성
  python main.py --review-id "12345678-1234-1234-1234-123456789012"
  
  # 사용자 전체 플랫폼 배치 처리 (NEW)
  python main.py --batch --user-id "a7654c42-10ed-435f-97d8-d2c2dfeccbcb" --all-platforms
  
  # 사용자 특정 플랫폼만 처리 (NEW)
  python main.py --batch --user-id "a7654c42-10ed-435f-97d8-d2c2dfeccbcb" --platform baemin --limit 5
  
  # 사용자 여러 플랫폼 처리 (NEW)
  python main.py --batch --user-id "a7654c42-10ed-435f-97d8-d2c2dfeccbcb" --platforms baemin yogiyo
  
  # 특정 매장 배치 처리
  python main.py --batch --store-id "87654321-4321-4321-4321-210987654321" --limit 10
  
  # 전체 매장 배치 처리
  python main.py --batch --all-stores --limit 5
  
  # 승인 관리
  python main.py --approvals --user-id "11111111-1111-1111-1111-111111111111"
  
  # 긍정 리뷰 자동 승인
  python main.py --auto-approve --store-id "87654321-4321-4321-4321-210987654321"
  
  # 답글 승인
  python main.py --approve --review-id "12345678..." --user-id "11111111..." --notes "승인"
  
  # 답글 거부
  python main.py --reject --review-id "12345678..." --user-id "11111111..." --reason "부적절한 내용"
        """
    )
    
    # 모드 선택
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--review-id', type=str, help='단일 리뷰 답글 생성')
    mode_group.add_argument('--batch', action='store_true', help='배치 처리 모드')
    mode_group.add_argument('--approvals', action='store_true', help='승인 관리 모드')
    mode_group.add_argument('--auto-approve', action='store_true', help='긍정 리뷰 자동 승인')
    mode_group.add_argument('--approve', action='store_true', help='답글 승인')
    mode_group.add_argument('--reject', action='store_true', help='답글 거부')
    
    # 배치 처리 옵션
    parser.add_argument('--store-id', type=str, help='특정 매장 ID')
    parser.add_argument('--all-stores', action='store_true', help='모든 활성 매장')
    parser.add_argument('--limit', type=int, help='처리할 리뷰 수 제한')
    
    # 승인/거부 옵션
    parser.add_argument('--user-id', type=str, help='사용자 ID')
    parser.add_argument('--notes', type=str, help='승인 메모')
    parser.add_argument('--reason', type=str, help='거부 사유')
    
    # 멀티플랫폼 옵션
    parser.add_argument('--platform', type=str, choices=['naver', 'baemin', 'yogiyo', 'coupangeats'], 
                       help='특정 플랫폼만 처리')
    parser.add_argument('--platforms', type=str, nargs='+', 
                       choices=['naver', 'baemin', 'yogiyo', 'coupangeats'],
                       help='여러 플랫폼 처리')
    parser.add_argument('--all-platforms', action='store_true', help='모든 플랫폼 처리')
    
    # 기타 옵션
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 출력')
    parser.add_argument('--dry-run', action='store_true', help='시뮬레이션 모드')
    
    args = parser.parse_args()
    
    # 환경 변수 확인
    required_env = ['OPENAI_API_KEY', 'NEXT_PUBLIC_SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"[ERROR] 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_env)}")
        print("[INFO] .env 파일을 확인해주세요")
        return
    
    # OpenAI API 키 확인
    if os.getenv('OPENAI_API_KEY') == 'your_openai_api_key_here':
        print("[ERROR] OpenAI API 키를 실제 값으로 설정해주세요")
        print("[INFO] .env 파일에서 OPENAI_API_KEY를 업데이트하세요")
        return
    
    try:
        system = AIReplySystem()
        success = False
        
        # 플랫폼 설정 처리
        platforms = None
        if args.all_platforms:
            platforms = ['naver', 'baemin', 'yogiyo', 'coupangeats']
        elif args.platforms:
            platforms = args.platforms
        elif args.platform:
            platforms = [args.platform]
        
        print(f"[START] AI 답글 생성 시스템 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if platforms:
            print(f"[TARGET] 대상 플랫폼: {[p.upper() for p in platforms]}")
        
        if args.review_id:
            # 단일 리뷰 처리
            success = await system.generate_single_reply(args.review_id)
            
        elif args.batch:
            # 배치 처리
            if args.user_id:
                # 사용자 기반 멀티플랫폼 처리 (새로운 기능)
                success = await system.batch_process(
                    user_id=args.user_id, limit=args.limit, platforms=platforms
                )
            elif args.all_stores:
                # 전체 매장 처리 (기존 방식)
                success = await system.batch_process(limit=args.limit)
            elif args.store_id:
                # 특정 매장 처리
                success = await system.batch_process(
                    store_id=args.store_id, limit=args.limit, platforms=platforms
                )
            else:
                print("[ERROR] --user-id, --store-id, 또는 --all-stores 옵션 중 하나를 지정해주세요")
                return
        
        elif args.approvals:
            # 승인 관리
            if not args.user_id:
                print("[ERROR] --user-id 옵션을 지정해주세요")
                return
            success = await system.manage_approvals(args.user_id, args.store_id)
        
        elif args.auto_approve:
            # 자동 승인
            if not args.store_id:
                print("[ERROR] --store-id 옵션을 지정해주세요")
                return
            success = await system.auto_approve_positive(args.store_id)
        
        elif args.approve:
            # 답글 승인
            if not args.review_id or not args.user_id:
                print("[ERROR] --review-id와 --user-id 옵션을 지정해주세요")
                return
            success = await system.approve_reply(args.review_id, args.user_id, args.notes)
        
        elif args.reject:
            # 답글 거부
            if not args.review_id or not args.user_id or not args.reason:
                print("[ERROR] --review-id, --user-id, --reason 옵션을 지정해주세요")
                return
            success = await system.reject_reply(args.review_id, args.user_id, args.reason)
        
        if success:
            print(f"\n[SUCCESS] 작업 완료 - {datetime.now().strftime('%H:%M:%S')}")
        else:
            print(f"\n[FAILED] 작업 실패 - {datetime.now().strftime('%H:%M:%S')}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n[STOP] 사용자에 의해 중단되었습니다")
    except Exception as e:
        print(f"\n[ERROR] 예상치 못한 오류: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())