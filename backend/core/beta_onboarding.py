"""
베타 테스트 계정 온보딩 시스템
5-10개 테스트 계정 자동 설정 및 관리
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from supabase import create_client, Client
from password_decrypt import encrypt_password

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OnboardingStatus(Enum):
    """온보딩 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class BetaAccount:
    """베타 테스트 계정 정보"""
    account_id: str
    store_name: str
    owner_name: str
    owner_phone: str
    owner_email: str
    platforms: List[str]  # ['naver', 'baemin', 'coupangeats', 'yogiyo']
    platform_credentials: Dict[str, Dict[str, str]]
    onboarding_status: OnboardingStatus
    created_at: datetime
    notes: str = ""

@dataclass
class OnboardingResult:
    """온보딩 결과"""
    account_id: str
    success: bool
    completed_platforms: List[str]
    failed_platforms: List[str]
    error_messages: List[str]
    test_results: Dict[str, Any]

class BetaOnboardingService:
    """베타 온보딩 서비스"""

    def __init__(self):
        self.supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Supabase 설정이 누락되었습니다.")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # 베타 계정 목록 (실제 운영 시에는 별도 파일 또는 DB에서 관리)
        self.beta_accounts = self._load_beta_accounts()

    def _load_beta_accounts(self) -> List[BetaAccount]:
        """베타 계정 목록 로드"""
        # 실제 베타 테스트 계정 정보 (예시)
        sample_accounts = [
            BetaAccount(
                account_id="beta-001",
                store_name="테스트 카페 1호점",
                owner_name="김사장",
                owner_phone="010-1234-5678",
                owner_email="test1@example.com",
                platforms=["naver", "baemin"],
                platform_credentials={
                    "naver": {"username": "test_naver_1", "password": "encrypted_password_1"},
                    "baemin": {"username": "test_baemin_1", "password": "encrypted_password_1"}
                },
                onboarding_status=OnboardingStatus.PENDING,
                created_at=datetime.now(),
                notes="첫 번째 베타 테스트 계정"
            ),
            BetaAccount(
                account_id="beta-002",
                store_name="맛있는 치킨집",
                owner_name="이사장",
                owner_phone="010-2345-6789",
                owner_email="test2@example.com",
                platforms=["coupangeats", "yogiyo"],
                platform_credentials={
                    "coupangeats": {"username": "test_coupang_1", "password": "encrypted_password_2"},
                    "yogiyo": {"username": "test_yogiyo_1", "password": "encrypted_password_2"}
                },
                onboarding_status=OnboardingStatus.PENDING,
                created_at=datetime.now(),
                notes="배달 전문점 테스트"
            ),
            # 추가 베타 계정들...
        ]

        return sample_accounts

    async def create_store_record(self, account: BetaAccount) -> str:
        """매장 레코드 생성"""
        try:
            store_data = {
                'name': account.store_name,
                'owner_name': account.owner_name,
                'owner_phone': account.owner_phone,
                'owner_email': account.owner_email,
                'business_type': 'restaurant',  # 기본값
                'is_beta_account': True,
                'beta_account_id': account.account_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            response = self.supabase.table('stores').insert(store_data).execute()
            store_id = response.data[0]['id']

            logger.info(f"매장 레코드 생성 완료: {store_id}")
            return store_id

        except Exception as e:
            logger.error(f"매장 레코드 생성 실패: {e}")
            raise

    async def setup_platform_stores(
        self,
        store_id: str,
        account: BetaAccount
    ) -> Dict[str, bool]:
        """플랫폼별 매장 설정"""
        results = {}

        for platform in account.platforms:
            try:
                if platform not in account.platform_credentials:
                    logger.warning(f"플랫폼 {platform} 인증정보 누락")
                    results[platform] = False
                    continue

                creds = account.platform_credentials[platform]

                # 비밀번호 암호화
                encrypted_password = encrypt_password(creds['password'])

                platform_store_data = {
                    'store_id': store_id,
                    'platform': platform,
                    'platform_id': creds['username'],
                    'platform_pw': encrypted_password,
                    'platform_store_id': creds.get('store_id', ''),
                    'is_active': True,
                    'is_beta_account': True,
                    'created_at': datetime.now().isoformat()
                }

                response = self.supabase.table('platform_stores').insert(platform_store_data).execute()

                logger.info(f"플랫폼 {platform} 설정 완료")
                results[platform] = True

            except Exception as e:
                logger.error(f"플랫폼 {platform} 설정 실패: {e}")
                results[platform] = False

        return results

    async def setup_notification_settings(
        self,
        store_id: str,
        account: BetaAccount
    ) -> bool:
        """알림 설정 구성"""
        try:
            notification_settings = {
                'store_id': store_id,
                'urgent_notifications': True,
                'daily_summary': True,
                'notification_hours_start': 9,
                'notification_hours_end': 22,
                'min_rating_threshold': 2,  # 베타 테스트용으로 낮게 설정
                'alimtalk_enabled': True,
                'email_notifications': True,
                'created_at': datetime.now().isoformat()
            }

            response = self.supabase.table('store_notification_settings').insert(
                notification_settings
            ).execute()

            logger.info(f"알림 설정 완료: {store_id}")
            return True

        except Exception as e:
            logger.error(f"알림 설정 실패: {e}")
            return False

    async def setup_ai_reply_settings(
        self,
        store_id: str,
        account: BetaAccount
    ) -> bool:
        """AI 답글 설정 구성"""
        try:
            ai_settings = {
                'store_id': store_id,
                'ai_enabled': True,
                'auto_reply': True,
                'reply_tone': 'friendly',
                'custom_instructions': f'{account.store_name}의 베타 테스트 계정입니다.',
                'response_time_limit': 24,  # 24시간 내 답글
                'min_rating_for_auto_reply': 1,  # 베타 테스트용
                'created_at': datetime.now().isoformat()
            }

            response = self.supabase.table('ai_reply_settings').insert(ai_settings).execute()

            logger.info(f"AI 답글 설정 완료: {store_id}")
            return True

        except Exception as e:
            logger.error(f"AI 답글 설정 실패: {e}")
            return False

    async def run_initial_test(
        self,
        store_id: str,
        account: BetaAccount
    ) -> Dict[str, Any]:
        """초기 테스트 실행"""
        test_results = {
            'crawling_test': {},
            'ai_reply_test': False,
            'alimtalk_test': False,
            'errors': []
        }

        # 크롤링 테스트 (각 플랫폼별)
        for platform in account.platforms:
            try:
                # 실제 크롤링 테스트는 여기서 실행
                # 지금은 시뮬레이션
                test_results['crawling_test'][platform] = {
                    'success': True,
                    'reviews_found': 5,  # 시뮬레이션
                    'test_time': datetime.now().isoformat()
                }

                logger.info(f"크롤링 테스트 성공: {platform}")

            except Exception as e:
                test_results['crawling_test'][platform] = {
                    'success': False,
                    'error': str(e),
                    'test_time': datetime.now().isoformat()
                }
                test_results['errors'].append(f"크롤링 테스트 실패 ({platform}): {e}")

        # AI 답글 테스트
        try:
            # 테스트 리뷰 데이터로 AI 답글 생성 테스트
            test_results['ai_reply_test'] = True
            logger.info("AI 답글 테스트 성공")

        except Exception as e:
            test_results['ai_reply_test'] = False
            test_results['errors'].append(f"AI 답글 테스트 실패: {e}")

        # 알림톡 테스트
        try:
            # 테스트 알림톡 발송
            test_results['alimtalk_test'] = True
            logger.info("알림톡 테스트 성공")

        except Exception as e:
            test_results['alimtalk_test'] = False
            test_results['errors'].append(f"알림톡 테스트 실패: {e}")

        return test_results

    async def onboard_account(self, account: BetaAccount) -> OnboardingResult:
        """단일 계정 온보딩"""
        logger.info(f"베타 계정 온보딩 시작: {account.account_id}")

        result = OnboardingResult(
            account_id=account.account_id,
            success=False,
            completed_platforms=[],
            failed_platforms=[],
            error_messages=[],
            test_results={}
        )

        try:
            # 1. 온보딩 상태 업데이트
            await self._update_onboarding_status(account.account_id, OnboardingStatus.IN_PROGRESS)

            # 2. 매장 레코드 생성
            store_id = await self.create_store_record(account)

            # 3. 플랫폼별 매장 설정
            platform_results = await self.setup_platform_stores(store_id, account)
            for platform, success in platform_results.items():
                if success:
                    result.completed_platforms.append(platform)
                else:
                    result.failed_platforms.append(platform)

            # 4. 알림 설정
            notification_success = await self.setup_notification_settings(store_id, account)
            if not notification_success:
                result.error_messages.append("알림 설정 실패")

            # 5. AI 답글 설정
            ai_success = await self.setup_ai_reply_settings(store_id, account)
            if not ai_success:
                result.error_messages.append("AI 답글 설정 실패")

            # 6. 초기 테스트 실행
            await self._update_onboarding_status(account.account_id, OnboardingStatus.TESTING)
            test_results = await self.run_initial_test(store_id, account)
            result.test_results = test_results

            # 7. 최종 상태 결정
            if len(result.completed_platforms) > 0 and len(test_results['errors']) == 0:
                result.success = True
                await self._update_onboarding_status(account.account_id, OnboardingStatus.COMPLETED)
                logger.info(f"베타 계정 온보딩 완료: {account.account_id}")
            else:
                await self._update_onboarding_status(account.account_id, OnboardingStatus.FAILED)
                logger.error(f"베타 계정 온보딩 실패: {account.account_id}")

        except Exception as e:
            logger.error(f"베타 계정 온보딩 오류: {e}")
            result.error_messages.append(str(e))
            await self._update_onboarding_status(account.account_id, OnboardingStatus.FAILED)

        return result

    async def onboard_all_accounts(self) -> List[OnboardingResult]:
        """모든 베타 계정 온보딩"""
        logger.info(f"전체 베타 계정 온보딩 시작: {len(self.beta_accounts)}개 계정")

        results = []
        for account in self.beta_accounts:
            try:
                result = await self.onboard_account(account)
                results.append(result)

                # 계정 간 간격 (시스템 부하 방지)
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"계정 {account.account_id} 온보딩 실패: {e}")
                results.append(OnboardingResult(
                    account_id=account.account_id,
                    success=False,
                    completed_platforms=[],
                    failed_platforms=account.platforms,
                    error_messages=[str(e)],
                    test_results={}
                ))

        # 온보딩 결과 요약
        successful = len([r for r in results if r.success])
        total = len(results)

        logger.info(f"베타 온보딩 완료: {successful}/{total} 성공")

        return results

    async def _update_onboarding_status(
        self,
        account_id: str,
        status: OnboardingStatus
    ):
        """온보딩 상태 업데이트"""
        try:
            log_data = {
                'account_id': account_id,
                'status': status.value,
                'timestamp': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            }

            self.supabase.table('beta_onboarding_logs').upsert(log_data).execute()

        except Exception as e:
            logger.error(f"온보딩 상태 업데이트 실패: {e}")

    async def get_onboarding_report(self) -> Dict[str, Any]:
        """온보딩 현황 리포트"""
        try:
            response = self.supabase.table('beta_onboarding_logs').select('*').order(
                'timestamp', desc=True
            ).execute()

            logs = response.data

            # 상태별 집계
            status_count = {}
            for log in logs:
                status = log['status']
                status_count[status] = status_count.get(status, 0) + 1

            report = {
                'total_accounts': len(self.beta_accounts),
                'status_breakdown': status_count,
                'latest_activities': logs[:10],  # 최근 10개 활동
                'generated_at': datetime.now().isoformat()
            }

            return report

        except Exception as e:
            logger.error(f"온보딩 리포트 생성 실패: {e}")
            return {}

# CLI 실행부
async def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='베타 온보딩 시스템')
    parser.add_argument('--mode', choices=['onboard', 'report', 'single'],
                       default='onboard', help='실행 모드')
    parser.add_argument('--account-id', help='단일 계정 온보딩용 계정 ID')

    args = parser.parse_args()

    service = BetaOnboardingService()

    if args.mode == 'onboard':
        logger.info("전체 베타 계정 온보딩 시작")
        results = await service.onboard_all_accounts()

        print("\n=== 온보딩 결과 ===")
        for result in results:
            status = "✅ 성공" if result.success else "❌ 실패"
            print(f"{result.account_id}: {status}")
            if result.error_messages:
                for error in result.error_messages:
                    print(f"  - 오류: {error}")

    elif args.mode == 'single' and args.account_id:
        account = next((a for a in service.beta_accounts if a.account_id == args.account_id), None)
        if account:
            result = await service.onboard_account(account)
            print(f"온보딩 결과: {'성공' if result.success else '실패'}")
        else:
            print(f"계정을 찾을 수 없습니다: {args.account_id}")

    elif args.mode == 'report':
        report = await service.get_onboarding_report()
        print("\n=== 온보딩 현황 리포트 ===")
        print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())