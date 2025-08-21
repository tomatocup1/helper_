#!/usr/bin/env python3
"""
배민 리뷰 시스템 통합 테스트
- 별점 추출기 검증
- 크롤러 통합 검증
- AI 답글 시스템 검증
- 답글 포스터 검증
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from star_rating_extractor import StarRatingExtractor
from baemin_review_crawler import BaeminReviewCrawler
from baemin_reply_poster import BaeminReplyPoster

# AI 답글 시스템 임포트
ai_reply_dir = current_dir / "ai_reply"
sys.path.append(str(ai_reply_dir))

try:
    from ai_reply_manager import AIReplyManager
except ImportError as e:
    print(f"AI 답글 매니저 임포트 실패: {e}")
    AIReplyManager = None

class BaeminIntegrationTester:
    """배민 시스템 통합 테스터"""
    
    def __init__(self):
        self.test_results = {
            'star_extractor': {'passed': 0, 'failed': 0, 'errors': []},
            'crawler_integration': {'passed': 0, 'failed': 0, 'errors': []},
            'ai_reply_system': {'passed': 0, 'failed': 0, 'errors': []},
            'reply_poster': {'passed': 0, 'failed': 0, 'errors': []},
            'overall': {'passed': 0, 'failed': 0, 'errors': []}
        }
    
    async def run_all_tests(self) -> Dict:
        """모든 테스트 실행"""
        print("🧪 배민 리뷰 시스템 통합 테스트 시작")
        print("=" * 60)
        
        try:
            # 1. 별점 추출기 테스트
            await self._test_star_extractor()
            
            # 2. 크롤러 통합 테스트
            await self._test_crawler_integration()
            
            # 3. AI 답글 시스템 테스트
            await self._test_ai_reply_system()
            
            # 4. 답글 포스터 테스트
            await self._test_reply_poster()
            
            # 5. 전체 결과 계산
            self._calculate_overall_results()
            
            # 6. 결과 출력
            self._print_test_summary()
            
            return self.test_results
            
        except Exception as e:
            print(f"❌ 통합 테스트 중 치명적 오류: {str(e)}")
            self.test_results['overall']['errors'].append(f"Fatal error: {str(e)}")
            return self.test_results
    
    async def _test_star_extractor(self):
        """별점 추출기 테스트"""
        print("\n🌟 별점 추출기 테스트")
        print("-" * 40)
        
        try:
            extractor = StarRatingExtractor()
            
            # 테스트 1: 인스턴스 생성 검증
            if extractor:
                self._log_pass('star_extractor', "인스턴스 생성 성공")
            else:
                self._log_fail('star_extractor', "인스턴스 생성 실패")
            
            # 테스트 2: 플랫폼 설정 검증
            platforms = ['baemin', 'naver', 'yogiyo', 'coupangeats']
            for platform in platforms:
                if platform in extractor.platform_configs:
                    self._log_pass('star_extractor', f"{platform} 플랫폼 설정 존재")
                else:
                    self._log_fail('star_extractor', f"{platform} 플랫폼 설정 누락")
            
            # 테스트 3: 별점 유효성 검사 함수
            test_cases = [
                (None, False),
                (0, False),
                (1, True),
                (3, True),
                (5, True),
                (6, False),
                ("3", False)
            ]
            
            for rating, expected in test_cases:
                result = extractor.validate_rating(rating)
                if result == expected:
                    self._log_pass('star_extractor', f"유효성 검사 통과: {rating} -> {result}")
                else:
                    self._log_fail('star_extractor', f"유효성 검사 실패: {rating} -> {result} (예상: {expected})")
            
        except Exception as e:
            self._log_fail('star_extractor', f"별점 추출기 테스트 오류: {str(e)}")
    
    async def _test_crawler_integration(self):
        """크롤러 통합 테스트"""
        print("\n🕷️ 크롤러 통합 테스트")
        print("-" * 40)
        
        try:
            # 환경변수 확인
            supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not supabase_url or not supabase_key:
                self._log_fail('crawler_integration', "Supabase 환경변수 누락")
                print("⚠️ 실제 크롤링 테스트를 위해서는 .env 파일에 Supabase 설정이 필요합니다.")
                return
            
            # 크롤러 인스턴스 생성 테스트
            try:
                crawler = BaeminReviewCrawler(headless=True, timeout=10000)
                self._log_pass('crawler_integration', "크롤러 인스턴스 생성 성공")
                
                # 별점 추출기 통합 확인
                if hasattr(crawler, 'rating_extractor') and crawler.rating_extractor:
                    self._log_pass('crawler_integration', "별점 추출기 통합 성공")
                else:
                    self._log_fail('crawler_integration', "별점 추출기 통합 실패")
                
                # Supabase 클라이언트 확인
                if hasattr(crawler, 'supabase') and crawler.supabase:
                    self._log_pass('crawler_integration', "Supabase 클라이언트 초기화 성공")
                else:
                    self._log_fail('crawler_integration', "Supabase 클라이언트 초기화 실패")
                
            except Exception as e:
                self._log_fail('crawler_integration', f"크롤러 초기화 실패: {str(e)}")
        
        except Exception as e:
            self._log_fail('crawler_integration', f"크롤러 테스트 오류: {str(e)}")
    
    async def _test_ai_reply_system(self):
        """AI 답글 시스템 테스트"""
        print("\n🤖 AI 답글 시스템 테스트")
        print("-" * 40)
        
        try:
            if AIReplyManager is None:
                self._log_fail('ai_reply_system', "AI 답글 매니저 임포트 실패")
                return
            
            # 환경변수 확인
            required_vars = [
                'NEXT_PUBLIC_SUPABASE_URL',
                'SUPABASE_SERVICE_ROLE_KEY',
                'OPENAI_API_KEY'
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                self._log_fail('ai_reply_system', f"환경변수 누락: {', '.join(missing_vars)}")
                print("⚠️ AI 답글 시스템 테스트를 위해서는 모든 환경변수가 필요합니다.")
                return
            
            # AI 답글 매니저 인스턴스 생성
            try:
                manager = AIReplyManager()
                self._log_pass('ai_reply_system', "AI 답글 매니저 인스턴스 생성 성공")
                
                # 지원 플랫폼 확인
                expected_platforms = ['naver', 'baemin', 'yogiyo', 'coupangeats']
                if hasattr(manager, 'supported_platforms'):
                    for platform in expected_platforms:
                        if platform in manager.supported_platforms:
                            self._log_pass('ai_reply_system', f"{platform} 플랫폼 지원 확인")
                        else:
                            self._log_fail('ai_reply_system', f"{platform} 플랫폼 지원 누락")
                else:
                    self._log_fail('ai_reply_system', "supported_platforms 속성 누락")
                
                # 테이블 이름 생성 함수 테스트
                if hasattr(manager, '_get_table_name'):
                    try:
                        table_name = manager._get_table_name('baemin')
                        if table_name == 'reviews_baemin':
                            self._log_pass('ai_reply_system', "테이블 이름 생성 함수 정상")
                        else:
                            self._log_fail('ai_reply_system', f"테이블 이름 생성 오류: {table_name}")
                    except Exception as e:
                        self._log_fail('ai_reply_system', f"테이블 이름 생성 함수 오류: {str(e)}")
                
            except Exception as e:
                self._log_fail('ai_reply_system', f"AI 답글 매니저 초기화 실패: {str(e)}")
        
        except Exception as e:
            self._log_fail('ai_reply_system', f"AI 답글 시스템 테스트 오류: {str(e)}")
    
    async def _test_reply_poster(self):
        """답글 포스터 테스트"""
        print("\n📝 답글 포스터 테스트")
        print("-" * 40)
        
        try:
            # 답글 포스터 인스턴스 생성
            try:
                poster = BaeminReplyPoster(headless=True, timeout=10000)
                self._log_pass('reply_poster', "답글 포스터 인스턴스 생성 성공")
                
                # 셀렉터 설정 확인
                if hasattr(poster, 'selectors') and poster.selectors:
                    required_selectors = ['reply_textarea', 'submit_button']
                    for selector_name in required_selectors:
                        if selector_name in poster.selectors:
                            self._log_pass('reply_poster', f"{selector_name} 셀렉터 설정 확인")
                        else:
                            self._log_fail('reply_poster', f"{selector_name} 셀렉터 설정 누락")
                else:
                    self._log_fail('reply_poster', "셀렉터 설정 누락")
                
            except Exception as e:
                self._log_fail('reply_poster', f"답글 포스터 초기화 실패: {str(e)}")
        
        except Exception as e:
            self._log_fail('reply_poster', f"답글 포스터 테스트 오류: {str(e)}")
    
    def _log_pass(self, category: str, message: str):
        """테스트 통과 로그"""
        self.test_results[category]['passed'] += 1
        print(f"  ✅ {message}")
    
    def _log_fail(self, category: str, message: str):
        """테스트 실패 로그"""
        self.test_results[category]['failed'] += 1
        self.test_results[category]['errors'].append(message)
        print(f"  ❌ {message}")
    
    def _calculate_overall_results(self):
        """전체 결과 계산"""
        total_passed = 0
        total_failed = 0
        all_errors = []
        
        for category, results in self.test_results.items():
            if category != 'overall':
                total_passed += results['passed']
                total_failed += results['failed']
                all_errors.extend(results['errors'])
        
        self.test_results['overall']['passed'] = total_passed
        self.test_results['overall']['failed'] = total_failed
        self.test_results['overall']['errors'] = all_errors
    
    def _print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        
        for category, results in self.test_results.items():
            if category == 'overall':
                continue
            
            total = results['passed'] + results['failed']
            if total == 0:
                continue
            
            success_rate = (results['passed'] / total) * 100
            status = "✅" if results['failed'] == 0 else "⚠️" if success_rate >= 70 else "❌"
            
            print(f"{status} {category.replace('_', ' ').title()}: "
                  f"{results['passed']}/{total} 통과 ({success_rate:.1f}%)")
            
            if results['errors']:
                for error in results['errors'][:3]:  # 최대 3개 오류만 표시
                    print(f"    - {error}")
                if len(results['errors']) > 3:
                    print(f"    ... 외 {len(results['errors']) - 3}개")
        
        # 전체 결과
        overall = self.test_results['overall']
        total_tests = overall['passed'] + overall['failed']
        
        if total_tests > 0:
            overall_success_rate = (overall['passed'] / total_tests) * 100
            overall_status = "🎉" if overall['failed'] == 0 else "⚠️" if overall_success_rate >= 70 else "💥"
            
            print(f"\n{overall_status} 전체 결과: {overall['passed']}/{total_tests} 통과 "
                  f"({overall_success_rate:.1f}%)")
        
        print("\n" + "=" * 60)

async def run_quick_validation():
    """빠른 검증 테스트"""
    print("Quick Validation Test")
    print("-" * 30)
    
    try:
        # 1. 파일 존재 확인
        required_files = [
            "star_rating_extractor.py",
            "baemin_review_crawler.py",
            "baemin_reply_poster.py",
            "ai_reply/ai_reply_manager.py"
        ]
        
        for file_name in required_files:
            file_path = Path(__file__).parent / file_name
            if file_path.exists():
                print(f"  [OK] {file_name} file exists")
            else:
                print(f"  [FAIL] {file_name} file missing")
        
        # 2. Basic import test
        try:
            from star_rating_extractor import StarRatingExtractor
            print("  [OK] StarRatingExtractor import success")
        except ImportError as e:
            print(f"  [FAIL] StarRatingExtractor import failed: {e}")
        
        try:
            from baemin_review_crawler import BaeminReviewCrawler
            print("  [OK] BaeminReviewCrawler import success")
        except ImportError as e:
            print(f"  [FAIL] BaeminReviewCrawler import failed: {e}")
        
        try:
            from baemin_reply_poster import BaeminReplyPoster
            print("  [OK] BaeminReplyPoster import success")
        except ImportError as e:
            print(f"  [FAIL] BaeminReplyPoster import failed: {e}")
        
        print("Quick validation completed!")
        
    except Exception as e:
        print(f"[ERROR] Quick validation error: {str(e)}")

async def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='배민 리뷰 시스템 통합 테스트')
    parser.add_argument('--quick', action='store_true', help='빠른 검증만 실행')
    parser.add_argument('--full', action='store_true', help='전체 통합 테스트 실행')
    
    args = parser.parse_args()
    
    if args.quick:
        await run_quick_validation()
    else:
        # 기본값은 전체 테스트
        tester = BaeminIntegrationTester()
        results = await tester.run_all_tests()
        
        # 결과를 JSON 파일로 저장
        results_file = Path(__file__).parent / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 상세 결과가 저장되었습니다: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())