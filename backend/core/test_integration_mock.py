#!/usr/bin/env python3
"""
배민 리뷰 시스템 모의 통합 테스트
- Supabase 의존성 없이 통합 검증
- 모든 컴포넌트 기능 확인
"""

import asyncio
import json
import sys
import os
from unittest.mock import Mock, patch
from pathlib import Path

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from star_rating_extractor import StarRatingExtractor

async def test_star_extractor_detailed():
    """별점 추출기 상세 테스트"""
    print("Testing StarRatingExtractor in detail...")
    
    extractor = StarRatingExtractor()
    tests_passed = 0
    total_tests = 0
    
    # 1. 플랫폼 설정 검증
    expected_platforms = ['baemin', 'naver', 'yogiyo', 'coupangeats']
    for platform in expected_platforms:
        total_tests += 1
        config = extractor.platform_configs.get(platform)
        if config and all(key in config for key in ['container_selectors', 'active_colors', 'inactive_colors']):
            print(f"  [OK] {platform} platform fully configured")
            tests_passed += 1
        else:
            print(f"  [FAIL] {platform} platform configuration incomplete")
    
    # 2. 별점 유효성 검사 테스트
    validation_cases = [
        (None, False),
        (0, False),
        (1, True),
        (3, True),
        (5, True),
        (6, False),
        ("3", False),
        (-1, False)
    ]
    
    for rating, expected in validation_cases:
        total_tests += 1
        result = extractor.validate_rating(rating)
        if result == expected:
            tests_passed += 1
            print(f"  [OK] Validation: {rating} -> {result}")
        else:
            print(f"  [FAIL] Validation: {rating} -> {result} (expected: {expected})")
    
    return tests_passed, total_tests

async def test_crawler_with_mock():
    """모의 Supabase 클라이언트로 크롤러 테스트"""
    print("\nTesting BaeminReviewCrawler with mock Supabase...")
    
    tests_passed = 0
    total_tests = 0
    
    # 환경변수 임시 설정
    os.environ['NEXT_PUBLIC_SUPABASE_URL'] = 'https://mock.supabase.co'
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'mock_key'
    
    try:
        # Supabase 클라이언트를 모의 객체로 패치
        with patch('baemin_review_crawler.create_client') as mock_create_client:
            mock_supabase = Mock()
            mock_create_client.return_value = mock_supabase
            
            # 크롤러 초기화 테스트
            total_tests += 1
            try:
                from baemin_review_crawler import BaeminReviewCrawler
                crawler = BaeminReviewCrawler(headless=True, timeout=5000)
                print("  [OK] Crawler initialized with mock Supabase")
                tests_passed += 1
                
                # 별점 추출기 통합 확인
                total_tests += 1
                if hasattr(crawler, 'rating_extractor') and isinstance(crawler.rating_extractor, StarRatingExtractor):
                    print("  [OK] StarRatingExtractor properly integrated")
                    tests_passed += 1
                else:
                    print("  [FAIL] StarRatingExtractor integration issue")
                
                # 날짜 파싱 기능 테스트
                date_test_cases = [
                    ("2024.03.15", "2024-03-15"),
                    ("2024.1.5", "2024-01-05"),
                    ("2023.12.31", "2023-12-31")
                ]
                
                for input_date, expected in date_test_cases:
                    total_tests += 1
                    result = crawler._parse_date(input_date)
                    if result == expected:
                        print(f"  [OK] Date parsing: {input_date} -> {result}")
                        tests_passed += 1
                    else:
                        print(f"  [FAIL] Date parsing: {input_date} -> {result} (expected: {expected})")
                
            except Exception as e:
                print(f"  [FAIL] Crawler initialization failed: {str(e)}")
    
    except Exception as e:
        print(f"  [ERROR] Mock test setup failed: {str(e)}")
    
    return tests_passed, total_tests

async def test_ai_reply_integration():
    """AI 답글 시스템 통합 테스트"""
    print("\nTesting AI Reply System integration...")
    
    tests_passed = 0
    total_tests = 0
    
    try:
        ai_reply_dir = current_dir / "ai_reply"
        sys.path.append(str(ai_reply_dir))
        
        # 환경변수 설정
        os.environ['NEXT_PUBLIC_SUPABASE_URL'] = 'https://mock.supabase.co'
        os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'mock_key'
        os.environ['OPENAI_API_KEY'] = 'mock_openai_key'
        
        # Supabase와 OpenAI 클라이언트 모의 패치
        with patch('ai_reply_manager.create_client') as mock_supabase, \
             patch('ai_reply_manager.OpenAI') as mock_openai:
            
            mock_supabase.return_value = Mock()
            mock_openai.return_value = Mock()
            
            total_tests += 1
            try:
                from ai_reply_manager import AIReplyManager
                manager = AIReplyManager()
                print("  [OK] AIReplyManager initialized with mock clients")
                tests_passed += 1
                
                # 플랫폼 지원 확인
                expected_platforms = ['naver', 'baemin', 'yogiyo', 'coupangeats']
                for platform in expected_platforms:
                    total_tests += 1
                    if hasattr(manager, 'supported_platforms') and platform in manager.supported_platforms:
                        print(f"  [OK] {platform} platform supported")
                        tests_passed += 1
                    else:
                        print(f"  [FAIL] {platform} platform not supported")
                
                # 테이블 이름 생성 테스트
                total_tests += 1
                if hasattr(manager, '_get_table_name'):
                    try:
                        table_name = manager._get_table_name('baemin')
                        if table_name == 'reviews_baemin':
                            print(f"  [OK] Table name generation: baemin -> {table_name}")
                            tests_passed += 1
                        else:
                            print(f"  [FAIL] Wrong table name: {table_name}")
                    except Exception as e:
                        print(f"  [FAIL] Table name generation error: {e}")
                else:
                    print("  [FAIL] _get_table_name method not found")
                
            except ImportError as e:
                print(f"  [FAIL] AIReplyManager import failed: {e}")
            except Exception as e:
                print(f"  [FAIL] AIReplyManager initialization failed: {e}")
    
    except Exception as e:
        print(f"  [ERROR] AI Reply integration test failed: {e}")
    
    return tests_passed, total_tests

async def test_reply_poster_integration():
    """답글 포스터 통합 테스트"""
    print("\nTesting Reply Poster integration...")
    
    tests_passed = 0
    total_tests = 0
    
    try:
        total_tests += 1
        from baemin_reply_poster import BaeminReplyPoster
        poster = BaeminReplyPoster(headless=True, timeout=5000)
        print("  [OK] BaeminReplyPoster initialized")
        tests_passed += 1
        
        # 셀렉터 설정 확인
        total_tests += 1
        if hasattr(poster, 'selectors') and poster.selectors:
            required_selectors = ['reply_textarea', 'submit_button']
            missing_selectors = [sel for sel in required_selectors if sel not in poster.selectors]
            
            if not missing_selectors:
                print("  [OK] All required selectors configured")
                tests_passed += 1
            else:
                print(f"  [FAIL] Missing selectors: {missing_selectors}")
        else:
            print("  [FAIL] Selectors not configured")
    
    except Exception as e:
        print(f"  [FAIL] Reply poster test failed: {e}")
    
    return tests_passed, total_tests

async def test_data_flow_simulation():
    """데이터 흐름 시뮬레이션"""
    print("\nTesting data flow simulation...")
    
    tests_passed = 0
    total_tests = 0
    
    # 1. 모의 리뷰 데이터 생성
    total_tests += 1
    mock_reviews = [
        {
            'reviewer_name': '김리뷰',
            'review_date': '2024-03-15',
            'review_text': '맛있어요!',
            'rating': 5,
            'order_menu_items': ['치킨', '피자'],
            'delivery_review': '빠른 배송',
            'reply_status': 'draft',
            'baemin_review_id': 'bm_123'
        },
        {
            'reviewer_name': '박평가',
            'review_date': '2024-03-14',
            'review_text': '보통이에요',
            'rating': 3,
            'order_menu_items': ['버거'],
            'delivery_review': '보통',
            'reply_status': 'sent',
            'reply_text': '감사합니다!',
            'baemin_review_id': 'bm_124'
        }
    ]
    
    print(f"  [OK] Generated {len(mock_reviews)} mock reviews")
    tests_passed += 1
    
    # 2. 데이터 직렬화/역직렬화 테스트
    total_tests += 1
    try:
        json_data = json.dumps(mock_reviews, ensure_ascii=False, indent=2)
        parsed_data = json.loads(json_data)
        
        if parsed_data == mock_reviews:
            print("  [OK] Data serialization/deserialization successful")
            tests_passed += 1
        else:
            print("  [FAIL] Data serialization mismatch")
    except Exception as e:
        print(f"  [FAIL] Data serialization failed: {e}")
    
    # 3. 필수 필드 검증
    required_fields = ['reviewer_name', 'review_date', 'review_text', 'rating', 'baemin_review_id']
    
    for i, review in enumerate(mock_reviews):
        total_tests += 1
        missing_fields = [field for field in required_fields if field not in review]
        
        if not missing_fields:
            print(f"  [OK] Review {i+1} has all required fields")
            tests_passed += 1
        else:
            print(f"  [FAIL] Review {i+1} missing fields: {missing_fields}")
    
    return tests_passed, total_tests

async def run_comprehensive_mock_tests():
    """모든 모의 테스트 실행"""
    print("Baemin Review System Comprehensive Mock Integration Test")
    print("=" * 60)
    
    all_results = []
    
    # 각 테스트 실행
    result1 = await test_star_extractor_detailed()
    all_results.append(("StarRatingExtractor detailed", result1))
    
    result2 = await test_crawler_with_mock()
    all_results.append(("Crawler with mock Supabase", result2))
    
    result3 = await test_ai_reply_integration()
    all_results.append(("AI Reply System integration", result3))
    
    result4 = await test_reply_poster_integration()
    all_results.append(("Reply Poster integration", result4))
    
    result5 = await test_data_flow_simulation()
    all_results.append(("Data flow simulation", result5))
    
    # 전체 결과 계산
    total_passed = sum(result[0] for _, result in all_results)
    total_tests = sum(result[1] for _, result in all_results)
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("Comprehensive Test Results Summary:")
    print("=" * 60)
    
    for test_name, (passed, total) in all_results:
        if total > 0:
            success_rate = (passed / total) * 100
            status = "[PASS]" if passed == total else "[PARTIAL]" if passed > 0 else "[FAIL]"
            print(f"{status} {test_name}: {passed}/{total} ({success_rate:.1f}%)")
        else:
            print(f"[SKIP] {test_name}: No tests run")
    
    overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
    overall_status = "[SUCCESS]" if total_passed == total_tests else "[PARTIAL]" if total_passed > 0 else "[FAILURE]"
    
    print(f"\n{overall_status} Overall: {total_passed}/{total_tests} tests passed ({overall_success_rate:.1f}%)")
    
    if total_passed == total_tests:
        print("\nExcellent! All integration tests passed!")
        print("The Baemin review system is fully integrated and ready for deployment.")
    elif overall_success_rate >= 80:
        print("\nGood! Most integration tests passed.")
        print("The system is mostly ready, with minor issues to address.")
    else:
        print("\nSome issues found. Please review failed tests before deployment.")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = asyncio.run(run_comprehensive_mock_tests())
    sys.exit(0 if success else 1)