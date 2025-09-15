#!/usr/bin/env python3
"""
다중 사용자 통합 자동화 런너
Multi-User Integrated Automation Runner for 우리가게 도우미
"""

import os
import sys
import asyncio
import argparse
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

# 프로젝트 경로 설정
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'core'))

from automation.user_manager import UserManager, UserInfo
from automation.platform_orchestrator import PlatformOrchestrator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'automation_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class AutomationRunner:
    """다중 사용자 통합 자동화 런너"""

    def __init__(self):
        """초기화"""
        self.user_manager = UserManager()
        self.orchestrator = PlatformOrchestrator()
        self.supported_platforms = ['naver', 'baemin', 'yogiyo', 'coupangeats']

    async def run_single_user(
        self,
        user_id: str,
        platforms: Optional[List[str]] = None,
        skip_crawling: bool = False,
        skip_ai_reply: bool = False,
        skip_posting: bool = False
    ) -> Dict[str, Any]:
        """단일 사용자 자동화 실행"""

        if platforms is None:
            platforms = self.supported_platforms

        # 플랫폼 유효성 검사
        invalid_platforms = [p for p in platforms if p not in self.supported_platforms]
        if invalid_platforms:
            raise ValueError(f"지원하지 않는 플랫폼: {invalid_platforms}")

        logger.info(f"[AUTOMATION] 단일 사용자 자동화 시작: {user_id}")
        logger.info(f"[AUTOMATION] 대상 플랫폼: {', '.join(platforms)}")

        start_time = datetime.now()

        # 사용자 정보 조회
        user = await self.user_manager.get_user_by_id(user_id)
        if not user:
            error_msg = f"사용자를 찾을 수 없습니다: {user_id}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'user_id': user_id,
                'execution_time': 0
            }

        logger.info(f"[USER] {user.name} ({user.email})")

        # 사용자 매장 확인
        all_stores = await self.user_manager.get_user_stores(user_id)
        platform_stores = {p: [s for s in all_stores if s.platform == p] for p in platforms}

        total_stores = sum(len(stores) for stores in platform_stores.values())
        if total_stores == 0:
            logger.warning(f"[WARNING] 처리할 매장이 없습니다: {user.name}")
            return {
                'success': True,
                'message': '처리할 매장이 없습니다',
                'user_id': user_id,
                'user_name': user.name,
                'platforms': platforms,
                'stores_count': 0,
                'execution_time': (datetime.now() - start_time).total_seconds()
            }

        logger.info(f"[STORES] 처리할 매장: {total_stores}개")
        for platform, stores in platform_stores.items():
            if stores:
                logger.info(f"   - {platform}: {len(stores)}개")

        # 워크플로우 실행
        try:
            results = {
                'crawling': [],
                'ai_reply': [],
                'posting': []
            }

            # 1단계: 크롤링
            if not skip_crawling:
                logger.info(f"[STEP1] 크롤링 시작")
                for platform in platforms:
                    stores = platform_stores[platform]
                    for store in stores:
                        if store.crawling_enabled:
                            logger.info(f"   [CRAWLING] [{platform}] {store.store_name} 크롤링 중...")
                            result = await self.orchestrator.run_crawler(platform, store)
                            results['crawling'].append({
                                'platform': platform,
                                'store': store,
                                'result': result
                            })
                        else:
                            logger.info(f"   [SKIP] [{platform}] {store.store_name} 크롤링 비활성화")

            # 2단계: AI 답글 생성
            if not skip_ai_reply:
                logger.info(f"[STEP2] AI 답글 생성")
                ai_result = await self.orchestrator.run_ai_reply_generation(user_id, platforms)
                results['ai_reply'].append({
                    'user_id': user_id,
                    'result': ai_result
                })

            # 3단계: 답글 등록
            if not skip_posting:
                logger.info(f"[STEP3] 답글 등록")
                for platform in platforms:
                    stores = platform_stores[platform]
                    for store in stores:
                        if store.auto_reply_enabled:
                            logger.info(f"   [POSTING] [{platform}] {store.store_name} 답글 등록 중...")
                            result = await self.orchestrator.run_reply_poster(platform, store)
                            results['posting'].append({
                                'platform': platform,
                                'store': store,
                                'result': result
                            })
                        else:
                            logger.info(f"   [SKIP] [{platform}] {store.store_name} 자동 답글 비활성화")

            execution_time = (datetime.now() - start_time).total_seconds()

            # 결과 집계
            crawling_success = sum(1 for r in results['crawling'] if r['result'].success)
            crawling_total = len(results['crawling'])
            ai_success = sum(1 for r in results['ai_reply'] if r['result'].success)
            posting_success = sum(1 for r in results['posting'] if r['result'].success)
            posting_total = len(results['posting'])

            logger.info(f"[SUCCESS] 사용자 자동화 완료: {user.name}")
            logger.info(f"   [CRAWLING] {crawling_success}/{crawling_total}")
            logger.info(f"   [AI_REPLY] {ai_success}/1")
            logger.info(f"   [POSTING] {posting_success}/{posting_total}")
            logger.info(f"   [TIME] 실행 시간: {execution_time:.1f}초")

            return {
                'success': True,
                'message': f'자동화 완료: {user.name}',
                'user_id': user_id,
                'user_name': user.name,
                'platforms': platforms,
                'stores_count': total_stores,
                'execution_time': execution_time,
                'results': {
                    'crawling': {'success': crawling_success, 'total': crawling_total},
                    'ai_reply': {'success': ai_success, 'total': 1},
                    'posting': {'success': posting_success, 'total': posting_total}
                },
                'details': results
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"사용자 자동화 실행 중 오류: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'user_id': user_id,
                'user_name': user.name if user else 'Unknown',
                'execution_time': execution_time,
                'error': str(e)
            }

    async def run_all_users(
        self,
        platforms: Optional[List[str]] = None,
        skip_crawling: bool = False,
        skip_ai_reply: bool = False,
        skip_posting: bool = False,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """모든 활성 사용자 자동화 실행"""

        if platforms is None:
            platforms = self.supported_platforms

        logger.info(f"[AUTOMATION] 전체 사용자 자동화 시작")
        logger.info(f"[AUTOMATION] 대상 플랫폼: {', '.join(platforms)}")

        start_time = datetime.now()

        # 모든 활성 사용자 조회
        users = await self.user_manager.get_all_active_users()
        if not users:
            logger.warning("[WARNING] 활성 사용자가 없습니다")
            return {
                'success': True,
                'message': '활성 사용자가 없습니다',
                'total_users': 0,
                'execution_time': (datetime.now() - start_time).total_seconds()
            }

        logger.info(f"[USERS] 활성 사용자: {len(users)}명")

        # 사용자별 매장 정보 확인
        users_with_stores = []
        for user in users:
            stores = await self.user_manager.get_user_stores(user.id)
            platform_stores = [s for s in stores if s.platform in platforms]
            if platform_stores:
                users_with_stores.append(user)
                logger.info(f"   [USER] {user.name}: {len(platform_stores)}개 매장")

        if not users_with_stores:
            logger.warning("[WARNING] 처리할 매장이 있는 사용자가 없습니다")
            return {
                'success': True,
                'message': '처리할 매장이 있는 사용자가 없습니다',
                'total_users': len(users),
                'users_with_stores': 0,
                'execution_time': (datetime.now() - start_time).total_seconds()
            }

        logger.info(f"[STORES] 매장이 있는 사용자: {len(users_with_stores)}명")

        # 동시 실행 제한을 위한 세마포어
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_user_with_semaphore(user: UserInfo):
            async with semaphore:
                return await self.run_single_user(
                    user.id,
                    platforms,
                    skip_crawling,
                    skip_ai_reply,
                    skip_posting
                )

        # 모든 사용자 병렬 실행
        logger.info(f"[PARALLEL] {len(users_with_stores)}명 사용자 병렬 처리 시작 (최대 동시 실행: {max_concurrent})")

        try:
            user_results = await asyncio.gather(
                *[run_user_with_semaphore(user) for user in users_with_stores],
                return_exceptions=True
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # 결과 집계
            successful_users = []
            failed_users = []

            for i, result in enumerate(user_results):
                if isinstance(result, Exception):
                    failed_users.append({
                        'user': users_with_stores[i],
                        'error': str(result)
                    })
                elif result.get('success'):
                    successful_users.append(result)
                else:
                    failed_users.append({
                        'user': users_with_stores[i],
                        'error': result.get('message', 'Unknown error')
                    })

            # 전체 통계 계산
            total_crawling_success = sum(r.get('results', {}).get('crawling', {}).get('success', 0) for r in successful_users)
            total_crawling_total = sum(r.get('results', {}).get('crawling', {}).get('total', 0) for r in successful_users)
            total_ai_success = sum(r.get('results', {}).get('ai_reply', {}).get('success', 0) for r in successful_users)
            total_posting_success = sum(r.get('results', {}).get('posting', {}).get('success', 0) for r in successful_users)
            total_posting_total = sum(r.get('results', {}).get('posting', {}).get('total', 0) for r in successful_users)

            logger.info(f"[SUCCESS] 전체 사용자 자동화 완료")
            logger.info(f"   [USERS] 성공 사용자: {len(successful_users)}/{len(users_with_stores)}")
            logger.info(f"   [CRAWLING] 전체 크롤링: {total_crawling_success}/{total_crawling_total}")
            logger.info(f"   [AI_REPLY] 전체 AI 답글: {total_ai_success}/{len(successful_users)}")
            logger.info(f"   [POSTING] 전체 답글 등록: {total_posting_success}/{total_posting_total}")
            logger.info(f"   [TIME] 총 실행 시간: {execution_time:.1f}초")

            return {
                'success': True,
                'message': f'전체 자동화 완료: {len(successful_users)}/{len(users_with_stores)} 사용자 성공',
                'total_users': len(users),
                'users_with_stores': len(users_with_stores),
                'successful_users': len(successful_users),
                'failed_users': len(failed_users),
                'platforms': platforms,
                'execution_time': execution_time,
                'statistics': {
                    'crawling': {'success': total_crawling_success, 'total': total_crawling_total},
                    'ai_reply': {'success': total_ai_success, 'total': len(successful_users)},
                    'posting': {'success': total_posting_success, 'total': total_posting_total}
                },
                'user_results': successful_users,
                'failed_users': failed_users
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"전체 사용자 자동화 실행 중 오류: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'execution_time': execution_time,
                'error': str(e)
            }

    def print_summary(self, result: Dict[str, Any]):
        """실행 결과 요약 출력"""
        print("\n" + "="*60)
        print("[SUMMARY] 자동화 실행 결과 요약")
        print("="*60)

        if result.get('success'):
            print(f"[SUCCESS] 실행 상태: 성공")
            print(f"[MESSAGE] 메시지: {result['message']}")

            if 'successful_users' in result:
                # 전체 사용자 실행 결과
                print(f"[USERS] 대상 사용자: {result['users_with_stores']}명")
                print(f"[SUCCESS] 성공 사용자: {result['successful_users']}명")
                print(f"[FAILED] 실패 사용자: {result['failed_users']}명")

                if result['statistics']:
                    stats = result['statistics']
                    print(f"[CRAWLING] 크롤링: {stats['crawling']['success']}/{stats['crawling']['total']}")
                    print(f"[AI_REPLY] AI 답글: {stats['ai_reply']['success']}/{stats['ai_reply']['total']}")
                    print(f"[POSTING] 답글 등록: {stats['posting']['success']}/{stats['posting']['total']}")
            else:
                # 단일 사용자 실행 결과
                print(f"[USER] 사용자: {result.get('user_name', 'Unknown')}")
                print(f"[STORES] 매장 수: {result.get('stores_count', 0)}개")

                if result.get('results'):
                    res = result['results']
                    print(f"[CRAWLING] 크롤링: {res['crawling']['success']}/{res['crawling']['total']}")
                    print(f"[AI_REPLY] AI 답글: {res['ai_reply']['success']}/{res['ai_reply']['total']}")
                    print(f"[POSTING] 답글 등록: {res['posting']['success']}/{res['posting']['total']}")

            print(f"[TIME] 실행 시간: {result['execution_time']:.1f}초")

            if result.get('failed_users'):
                print("\n[FAILED_USERS] 실패한 사용자:")
                for failed in result['failed_users']:
                    if isinstance(failed, dict) and 'user' in failed:
                        print(f"   - {failed['user'].name}: {failed['error']}")
                    else:
                        print(f"   - {failed}")

        else:
            print(f"[FAILED] 실행 상태: 실패")
            print(f"[MESSAGE] 메시지: {result['message']}")
            if result.get('error'):
                print(f"[ERROR] 오류 상세: {result['error']}")

        print("="*60)


async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='우리가게 도우미 다중 사용자 통합 자동화 런너',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 모든 사용자, 모든 플랫폼 실행
  python automation_runner.py --all-users

  # 특정 사용자만 실행
  python automation_runner.py --user-id "a7654c42-10ed-435f-97d8-d2c2dfeccbcb"

  # 특정 플랫폼만 실행
  python automation_runner.py --all-users --platforms naver,baemin

  # 크롤링만 실행 (AI 답글 및 등록 제외)
  python automation_runner.py --all-users --skip-ai-reply --skip-posting

  # 테스트 모드 (크롤링 제외)
  python automation_runner.py --user-id "test-user" --skip-crawling
        """
    )

    # 실행 대상 옵션
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument('--all-users', action='store_true', help='모든 활성 사용자 실행')
    target_group.add_argument('--user-id', type=str, help='특정 사용자 ID 실행')

    # 플랫폼 옵션
    parser.add_argument('--platforms', type=str, help='실행할 플랫폼 (콤마로 구분, 예: naver,baemin,yogiyo,coupangeats)')

    # 단계별 실행 제어
    parser.add_argument('--skip-crawling', action='store_true', help='크롤링 단계 건너뛰기')
    parser.add_argument('--skip-ai-reply', action='store_true', help='AI 답글 생성 단계 건너뛰기')
    parser.add_argument('--skip-posting', action='store_true', help='답글 등록 단계 건너뛰기')

    # 성능 옵션
    parser.add_argument('--max-concurrent', type=int, default=3, help='최대 동시 실행 사용자 수 (기본값: 3)')

    args = parser.parse_args()

    # 플랫폼 파싱
    platforms = None
    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(',')]
        supported_platforms = ['naver', 'baemin', 'yogiyo', 'coupangeats']
        invalid_platforms = [p for p in platforms if p not in supported_platforms]
        if invalid_platforms:
            print(f"❌ 지원하지 않는 플랫폼: {invalid_platforms}")
            print(f"✅ 지원되는 플랫폼: {supported_platforms}")
            return

    # 자동화 런너 실행
    runner = AutomationRunner()

    try:
        if args.all_users:
            print("[AUTOMATION] 모든 사용자 자동화 실행")
            result = await runner.run_all_users(
                platforms=platforms,
                skip_crawling=args.skip_crawling,
                skip_ai_reply=args.skip_ai_reply,
                skip_posting=args.skip_posting,
                max_concurrent=args.max_concurrent
            )
        else:
            print(f"[AUTOMATION] 단일 사용자 자동화 실행: {args.user_id}")
            result = await runner.run_single_user(
                args.user_id,
                platforms=platforms,
                skip_crawling=args.skip_crawling,
                skip_ai_reply=args.skip_ai_reply,
                skip_posting=args.skip_posting
            )

        runner.print_summary(result)

    except KeyboardInterrupt:
        print("\n[WARNING] 사용자에 의해 중단되었습니다")
    except Exception as e:
        print(f"\n[ERROR] 실행 중 오류 발생: {e}")
        logger.exception("실행 중 예외 발생")


if __name__ == "__main__":
    asyncio.run(main())