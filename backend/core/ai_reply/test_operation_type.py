#!/usr/bin/env python3
"""
운영 방식별 AI 답글 생성 테스트 스크립트
Test script for operation type aware AI reply generation
"""

import asyncio
import os
import sys
from datetime import datetime

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# 현재 디렉토리를 파이썬 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_reply_manager import AIReplyManager


async def test_operation_types():
    """운영 방식별 답글 생성 테스트"""
    
    print("=" * 60)
    print("운영 방식별 AI 답글 생성 테스트")
    print("=" * 60)
    
    manager = AIReplyManager()
    
    # 테스트 리뷰 데이터
    test_reviews = [
        {
            "review_text": "배달이 빨라서 좋았어요! 음식도 맛있고 양도 많아요!",
            "rating": 5,
            "reviewer_name": "테스트1"
        },
        {
            "review_text": "매장이 깨끗하고 직원분들이 친절해요. 분위기도 좋아요!",
            "rating": 4,
            "reviewer_name": "테스트2"
        },
        {
            "review_text": "포장 주문했는데 깔끔하게 잘 포장해주셨어요.",
            "rating": 5,
            "reviewer_name": "테스트3"
        }
    ]
    
    # 운영 방식별 매장 설정
    operation_types = [
        ("delivery_only", "배달전용"),
        ("dine_in_only", "홀전용"),
        ("takeout_only", "포장전용"),
        ("both", "배달+홀")
    ]
    
    for op_type, op_name in operation_types:
        print(f"\n\n{'='*60}")
        print(f"테스트: {op_name} 매장 ({op_type})")
        print(f"{'='*60}")
        
        # 매장 설정
        store_settings = {
            "store_name": f"{op_name} 테스트 매장",
            "business_type": "음식점",
            "operation_type": op_type,
            "reply_tone": "friendly",
            "min_reply_length": 50,
            "max_reply_length": 200
        }
        
        for i, review in enumerate(test_reviews, 1):
            print(f"\n[리뷰 {i}]")
            print(f"작성자: {review['reviewer_name']}")
            print(f"평점: {review['rating']}점")
            print(f"내용: {review['review_text']}")
            
            try:
                # AI 답글 생성
                result = await manager.generate_reply(review, store_settings)
                
                print(f"\n[생성된 답글]")
                print(result.complete_reply)
                
                # 운영 방식별 금지어 체크
                reply_text = result.complete_reply.lower()
                
                if op_type == 'delivery_only':
                    forbidden = ["방문", "오셔서", "매장에서", "가게에 오시면", "홀에서"]
                    found = [word for word in forbidden if word in reply_text]
                    if found:
                        print(f"⚠️ 경고: 배달전용인데 금지어 발견: {found}")
                    else:
                        print("✅ 배달전용 금지어 체크 통과")
                
                elif op_type == 'dine_in_only':
                    forbidden = ["배달", "배송", "라이더", "주문"]
                    found = [word for word in forbidden if word in reply_text]
                    if found:
                        print(f"⚠️ 경고: 홀전용인데 금지어 발견: {found}")
                    else:
                        print("✅ 홀전용 금지어 체크 통과")
                
                elif op_type == 'takeout_only':
                    forbidden = ["배달", "홀에서", "매장에서 드시고", "방문해서 드"]
                    found = [word for word in forbidden if word in reply_text]
                    if found:
                        print(f"⚠️ 경고: 포장전용인데 금지어 발견: {found}")
                    else:
                        print("✅ 포장전용 금지어 체크 통과")
                
                print(f"AI 신뢰도: {result.ai_confidence_score:.2f}")
                print(f"생성 시간: {result.ai_generation_time_ms}ms")
                
            except Exception as e:
                print(f"❌ 에러 발생: {str(e)}")
    
    print(f"\n\n{'='*60}")
    print("테스트 완료!")
    print(f"{'='*60}")


async def main():
    """메인 함수"""
    
    # 환경 변수 확인
    required_env = ['OPENAI_API_KEY', 'NEXT_PUBLIC_SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"[ERROR] 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_env)}")
        return
    
    # OpenAI API 키 확인
    if os.getenv('OPENAI_API_KEY') == 'your_openai_api_key_here':
        print("[ERROR] OpenAI API 키를 실제 값으로 설정해주세요")
        return
    
    try:
        await test_operation_types()
    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())