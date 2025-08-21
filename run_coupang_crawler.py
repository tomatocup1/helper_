#!/usr/bin/env python3
"""
쿠팡잇츠 크롤러 실행 스크립트 (프로젝트 루트용)
"""

import asyncio
import argparse
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from backend.core.coupang_review_crawler import CoupangReviewCrawler

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='쿠팡잇츠 리뷰 크롤러')
    parser.add_argument('--username', required=True, help='쿠팡잇츠 로그인 ID')
    parser.add_argument('--password', required=True, help='쿠팡잇츠 로그인 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID')
    parser.add_argument('--days', type=int, default=7, help='크롤링 기간 (기본: 7일)')
    parser.add_argument('--max-pages', type=int, default=5, help='최대 페이지 수 (기본: 5)')
    
    args = parser.parse_args()
    
    print(f"쿠팡잇츠 리뷰 크롤링 시작...")
    print(f"매장 ID: {args.store_id}")
    print(f"기간: 최근 {args.days}일")
    print(f"최대 페이지: {args.max_pages}")
    print("-" * 50)
    
    crawler = CoupangReviewCrawler()
    result = await crawler.crawl_reviews(
        username=args.username,
        password=args.password,
        store_id=args.store_id,
        days=args.days,
        max_pages=args.max_pages
    )
    
    print("\n" + "=" * 50)
    print("크롤링 결과")
    print("=" * 50)
    print(f"성공 여부: {result['success']}")
    print(f"메시지: {result['message']}")
    
    if result['success']:
        print(f"수집된 리뷰 수: {len(result.get('reviews', []))}")
        print(f"저장된 리뷰 수: {result.get('saved_count', 0)}")
        
        # 첫 번째 리뷰 상세 정보
        if result.get('reviews'):
            first_review = result['reviews'][0]
            print(f"\n첫 번째 리뷰 예시:")
            print(f"  리뷰어: {first_review.get('reviewer_name')}")
            print(f"  별점: {first_review.get('rating')}점")
            print(f"  리뷰 텍스트: {first_review.get('review_text')}")
            print(f"  리뷰 날짜: {first_review.get('review_date')}")
    else:
        print(f"오류 내용: {result.get('message', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(main())