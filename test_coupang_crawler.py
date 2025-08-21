#!/usr/bin/env python3
"""
쿠팡잇츠 크롤러 테스트 스크립트
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.core.coupang_review_crawler import CoupangReviewCrawler
from backend.core.coupang_reply_poster import CoupangReplyPoster
from backend.shared.logger import get_logger

logger = get_logger(__name__)

async def test_crawler():
    """크롤러 테스트"""
    print("=== 쿠팡잇츠 리뷰 크롤러 테스트 ===")
    
    # 테스트 계정 정보 (실제 사용 시 변경 필요)
    username = input("쿠팡잇츠 로그인 ID: ")
    password = input("쿠팡잇츠 로그인 비밀번호: ")
    store_id = input("매장 ID (예: 708561): ")
    
    crawler = CoupangReviewCrawler()
    
    try:
        result = await crawler.crawl_reviews(
            username=username,
            password=password,
            store_id=store_id,
            days=7,
            max_pages=2
        )
        
        print("\n=== 크롤링 결과 ===")
        print(f"성공 여부: {result['success']}")
        print(f"메시지: {result['message']}")
        print(f"수집된 리뷰 수: {len(result.get('reviews', []))}")
        print(f"저장된 리뷰 수: {result.get('saved_count', 0)}")
        
        # 첫 번째 리뷰 상세 정보 출력
        if result.get('reviews'):
            first_review = result['reviews'][0]
            print("\n=== 첫 번째 리뷰 예시 ===")
            print(f"리뷰어: {first_review.get('reviewer_name')}")
            print(f"별점: {first_review.get('rating')}")
            print(f"리뷰 텍스트: {first_review.get('review_text')}")
            print(f"리뷰 날짜: {first_review.get('review_date')}")
            print(f"주문 메뉴: {first_review.get('order_menu_items')}")
            
    except Exception as e:
        logger.error(f"크롤러 테스트 실패: {e}")
        print(f"테스트 실패: {e}")

async def test_reply_poster():
    """답글 포스터 테스트"""
    print("\n=== 쿠팡잇츠 답글 포스터 테스트 ===")
    
    # 테스트 계정 정보
    username = input("쿠팡잇츠 로그인 ID: ")
    password = input("쿠팡잇츠 로그인 비밀번호: ")
    store_id = input("매장 ID (예: 708561): ")
    test_mode = input("테스트 모드? (y/n): ").lower() == 'y'
    
    poster = CoupangReplyPoster()
    
    try:
        result = await poster.post_replies(
            username=username,
            password=password,
            store_id=store_id,
            max_replies=5,
            test_mode=test_mode
        )
        
        print("\n=== 답글 포스팅 결과 ===")
        print(f"성공 여부: {result['success']}")
        print(f"메시지: {result['message']}")
        print(f"포스팅된 답글 수: {len(result.get('posted_replies', []))}")
        
        # 포스팅된 답글 정보 출력
        for reply in result.get('posted_replies', []):
            print(f"\n- 리뷰어: {reply.get('reviewer_name')}")
            print(f"  상태: {reply.get('status')}")
            print(f"  답글: {reply.get('reply_text')}")
            
    except Exception as e:
        logger.error(f"답글 포스터 테스트 실패: {e}")
        print(f"테스트 실패: {e}")

async def main():
    """메인 함수"""
    print("쿠팡잇츠 시스템 테스트")
    print("1. 리뷰 크롤러 테스트")
    print("2. 답글 포스터 테스트")
    print("3. 전체 테스트")
    
    choice = input("선택하세요 (1-3): ")
    
    if choice == "1":
        await test_crawler()
    elif choice == "2":
        await test_reply_poster()
    elif choice == "3":
        await test_crawler()
        await test_reply_poster()
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    asyncio.run(main())