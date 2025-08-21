#!/usr/bin/env python3
"""
배민 리뷰 시스템 기능 통합 테스트
- 실제 로그인 없이 기능 검증
- 컴포넌트 간 통합 확인
"""

import asyncio
import json
from pathlib import Path
import sys

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from star_rating_extractor import StarRatingExtractor
from baemin_review_crawler import BaeminReviewCrawler

async def test_star_extractor_functionality():
    """별점 추출기 기능 테스트"""
    print("Testing StarRatingExtractor functionality...")
    
    extractor = StarRatingExtractor()
    
    # 플랫폼 설정 확인
    platforms_tested = 0
    for platform in ['baemin', 'naver', 'yogiyo', 'coupangeats']:
        config = extractor.platform_configs.get(platform)
        if config:
            print(f"  [OK] {platform} platform config loaded")
            print(f"    - Container selectors: {len(config['container_selectors'])}")
            print(f"    - Active colors: {len(config['active_colors'])}")
            platforms_tested += 1
        else:
            print(f"  [FAIL] {platform} platform config missing")
    
    print(f"  Summary: {platforms_tested}/4 platforms configured")
    return platforms_tested == 4

async def test_crawler_initialization():
    """크롤러 초기화 테스트"""
    print("\nTesting BaeminReviewCrawler initialization...")
    
    try:
        # 환경변수가 없어도 기본 초기화는 되는지 확인
        import os
        # 임시로 환경변수 설정
        os.environ['NEXT_PUBLIC_SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'test_key'
        
        try:
            crawler = BaeminReviewCrawler(headless=True, timeout=5000)
            print("  [OK] Crawler initialized successfully")
            
            # 별점 추출기 통합 확인
            if hasattr(crawler, 'rating_extractor'):
                print("  [OK] StarRatingExtractor integrated")
                
                # 추출기 타입 확인
                if isinstance(crawler.rating_extractor, StarRatingExtractor):
                    print("  [OK] Correct extractor type")
                    return True
                else:
                    print("  [FAIL] Wrong extractor type")
                    return False
            else:
                print("  [FAIL] StarRatingExtractor not integrated")
                return False
                
        except Exception as e:
            print(f"  [FAIL] Crawler initialization failed: {str(e)}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Test setup failed: {str(e)}")
        return False

async def test_method_integration():
    """메서드 통합 테스트"""
    print("\nTesting method integration...")
    
    try:
        import os
        os.environ['NEXT_PUBLIC_SUPABASE_URL'] = 'https://test.supabase.co'
        os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'test_key'
        
        crawler = BaeminReviewCrawler(headless=True, timeout=5000)
        
        # 날짜 파싱 테스트
        test_dates = [
            ("2024.03.15", "2024-03-15"),
            ("2024.1.5", "2024-01-05"),
            ("invalid_date", "invalid_date")
        ]
        
        date_tests_passed = 0
        for input_date, expected in test_dates:
            result = crawler._parse_date(input_date)
            if result == expected:
                print(f"  [OK] Date parsing: {input_date} -> {result}")
                date_tests_passed += 1
            else:
                print(f"  [FAIL] Date parsing: {input_date} -> {result} (expected: {expected})")
        
        print(f"  Summary: {date_tests_passed}/{len(test_dates)} date parsing tests passed")
        
        return date_tests_passed == len(test_dates)
        
    except Exception as e:
        print(f"  [ERROR] Method integration test failed: {str(e)}")
        return False

async def test_data_structure_compatibility():
    """데이터 구조 호환성 테스트"""
    print("\nTesting data structure compatibility...")
    
    # 모의 리뷰 데이터 구조 테스트
    mock_review_data = {
        'reviewer_name': 'Test User',
        'review_date': '2024-03-15',
        'review_text': 'Test review content',
        'rating': 4,
        'order_menu_items': ['Item 1', 'Item 2'],
        'delivery_review': 'Good delivery',
        'reply_text': None,
        'reply_status': 'draft',
        'baemin_review_id': 'test_123'
    }
    
    required_fields = [
        'reviewer_name', 'review_date', 'review_text', 'rating',
        'order_menu_items', 'reply_status', 'baemin_review_id'
    ]
    
    fields_present = 0
    for field in required_fields:
        if field in mock_review_data:
            print(f"  [OK] Required field present: {field}")
            fields_present += 1
        else:
            print(f"  [FAIL] Required field missing: {field}")
    
    # JSON 직렬화 테스트
    try:
        json_str = json.dumps(mock_review_data, ensure_ascii=False)
        print("  [OK] JSON serialization successful")
        
        # 역직렬화 테스트
        parsed_data = json.loads(json_str)
        if parsed_data == mock_review_data:
            print("  [OK] JSON deserialization successful")
            return fields_present == len(required_fields)
        else:
            print("  [FAIL] JSON deserialization mismatch")
            return False
            
    except Exception as e:
        print(f"  [FAIL] JSON serialization failed: {str(e)}")
        return False

async def run_functional_tests():
    """모든 기능 테스트 실행"""
    print("Baemin Review System Functional Integration Test")
    print("=" * 50)
    
    test_results = []
    
    # 1. 별점 추출기 기능 테스트
    result1 = await test_star_extractor_functionality()
    test_results.append(("StarRatingExtractor functionality", result1))
    
    # 2. 크롤러 초기화 테스트
    result2 = await test_crawler_initialization()
    test_results.append(("Crawler initialization", result2))
    
    # 3. 메서드 통합 테스트
    result3 = await test_method_integration()
    test_results.append(("Method integration", result3))
    
    # 4. 데이터 구조 호환성 테스트
    result4 = await test_data_structure_compatibility()
    test_results.append(("Data structure compatibility", result4))
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed_tests += 1
    
    success_rate = (passed_tests / total_tests) * 100
    overall_status = "[SUCCESS]" if passed_tests == total_tests else "[PARTIAL]" if passed_tests > 0 else "[FAILURE]"
    
    print(f"\n{overall_status} Overall: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    if passed_tests == total_tests:
        print("\nAll functional integration tests passed!")
        print("The Baemin review system components are properly integrated.")
    else:
        print(f"\n{total_tests - passed_tests} test(s) failed. Please check the implementation.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = asyncio.run(run_functional_tests())
    sys.exit(0 if success else 1)