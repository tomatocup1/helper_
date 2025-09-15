#!/usr/bin/env python3
"""
사용자 및 매장 관리 모듈
User and Store Management Module
"""

import os
import sys
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

# 프로젝트 경로 설정
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'core'))

from supabase import create_client, Client
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

@dataclass
class UserInfo:
    """사용자 정보"""
    id: str
    email: str
    name: str
    is_active: bool
    subscription_plan: str
    created_at: str

@dataclass
class StoreInfo:
    """매장 정보"""
    id: str
    user_id: str
    store_name: str
    platform: str
    platform_store_id: str
    platform_id: Optional[str]
    platform_pw: Optional[str]
    is_active: bool
    crawling_enabled: bool
    auto_reply_enabled: bool


class UserManager:
    """사용자 및 매장 관리 클래스"""

    def __init__(self):
        """초기화"""
        self.supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL 또는 Service Role Key가 설정되지 않았습니다")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    async def get_all_active_users(self) -> List[UserInfo]:
        """모든 활성 사용자 조회"""
        try:
            response = self.supabase.table('users')\
                .select('id, email, name, is_active, subscription_plan, created_at')\
                .eq('is_active', True)\
                .execute()

            users = []
            for user_data in response.data:
                users.append(UserInfo(
                    id=user_data['id'],
                    email=user_data['email'],
                    name=user_data['name'],
                    is_active=user_data['is_active'],
                    subscription_plan=user_data.get('subscription_plan', 'free'),
                    created_at=user_data['created_at']
                ))

            return users

        except Exception as e:
            print(f"ERROR 사용자 조회 실패: {e}")
            return []

    async def get_user_by_id(self, user_id: str) -> Optional[UserInfo]:
        """특정 사용자 조회"""
        try:
            response = self.supabase.table('users')\
                .select('id, email, name, is_active, subscription_plan, created_at')\
                .eq('id', user_id)\
                .eq('is_active', True)\
                .single()\
                .execute()

            if response.data:
                user_data = response.data
                return UserInfo(
                    id=user_data['id'],
                    email=user_data['email'],
                    name=user_data['name'],
                    is_active=user_data['is_active'],
                    subscription_plan=user_data.get('subscription_plan', 'free'),
                    created_at=user_data['created_at']
                )

            return None

        except Exception as e:
            print(f"ERROR 사용자 조회 실패 (ID: {user_id}): {e}")
            return None

    async def get_user_stores(self, user_id: str, platform: Optional[str] = None) -> List[StoreInfo]:
        """사용자의 매장 정보 조회"""
        try:
            query = self.supabase.table('platform_stores')\
                .select('id, user_id, store_name, platform, platform_store_id, platform_id, platform_pw, is_active, crawling_enabled, auto_reply_enabled')\
                .eq('user_id', user_id)\
                .eq('is_active', True)

            if platform:
                query = query.eq('platform', platform)

            response = query.execute()

            stores = []
            for store_data in response.data:
                stores.append(StoreInfo(
                    id=store_data['id'],
                    user_id=store_data['user_id'],
                    store_name=store_data['store_name'],
                    platform=store_data['platform'],
                    platform_store_id=store_data['platform_store_id'],
                    platform_id=store_data.get('platform_id'),
                    platform_pw=store_data.get('platform_pw'),
                    is_active=store_data['is_active'],
                    crawling_enabled=store_data.get('crawling_enabled', True),
                    auto_reply_enabled=store_data.get('auto_reply_enabled', False)
                ))

            return stores

        except Exception as e:
            print(f"ERROR 매장 조회 실패 (사용자: {user_id}): {e}")
            return []

    async def get_all_active_stores(self) -> Dict[str, List[StoreInfo]]:
        """모든 활성 사용자의 매장 정보 조회 (사용자별 그룹화)"""
        try:
            users = await self.get_all_active_users()
            all_stores = {}

            for user in users:
                stores = await self.get_user_stores(user.id)
                if stores:
                    all_stores[user.id] = {
                        'user_info': user,
                        'stores': stores
                    }

            return all_stores

        except Exception as e:
            print(f"ERROR 전체 매장 조회 실패: {e}")
            return {}

    async def get_stores_by_platform(self, platform: str) -> Dict[str, List[StoreInfo]]:
        """특정 플랫폼의 모든 매장 조회 (사용자별 그룹화)"""
        try:
            users = await self.get_all_active_users()
            platform_stores = {}

            for user in users:
                stores = await self.get_user_stores(user.id, platform)
                if stores:
                    platform_stores[user.id] = {
                        'user_info': user,
                        'stores': stores
                    }

            return platform_stores

        except Exception as e:
            print(f"ERROR {platform} 매장 조회 실패: {e}")
            return {}

    def print_user_summary(self, user: UserInfo, stores: List[StoreInfo]):
        """사용자 요약 정보 출력"""
        platform_counts = {}
        for store in stores:
            platform = store.platform
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        platform_summary = ", ".join([f"{platform} {count}개" for platform, count in platform_counts.items()])

        print(f"USER: {user.name} ({user.email})")
        print(f"   구독: {user.subscription_plan}")
        print(f"   매장: 총 {len(stores)}개 ({platform_summary})")
        print(f"   가입: {user.created_at}")

    def print_all_users_summary(self, all_stores: Dict[str, List[StoreInfo]]):
        """전체 사용자 요약 정보 출력"""
        total_users = len(all_stores)
        total_stores = sum(len(data['stores']) for data in all_stores.values())

        platform_totals = {}
        for data in all_stores.values():
            for store in data['stores']:
                platform = store.platform
                platform_totals[platform] = platform_totals.get(platform, 0) + 1

        print("="*60)
        print("전체 사용자 및 매장 현황")
        print("="*60)
        print(f"활성 사용자: {total_users}명")
        print(f"총 매장: {total_stores}개")
        print("플랫폼별 매장 수:")
        for platform, count in platform_totals.items():
            print(f"   - {platform}: {count}개")
        print("-"*60)

        for user_id, data in all_stores.items():
            self.print_user_summary(data['user_info'], data['stores'])
            print()


# 테스트 실행
async def main():
    """테스트 실행"""
    manager = UserManager()

    print("[AUTOMATION] 사용자 및 매장 관리 시스템 테스트")
    print("="*60)

    # 모든 활성 사용자 조회
    print("\n[1] 모든 활성 사용자 조회")
    users = await manager.get_all_active_users()
    print(f"활성 사용자: {len(users)}명")

    # 모든 매장 조회
    print("\n[2] 모든 매장 조회")
    all_stores = await manager.get_all_active_stores()
    manager.print_all_users_summary(all_stores)

    # 플랫폼별 매장 조회 테스트
    print("\n[3] 플랫폼별 매장 조회 테스트")
    for platform in ['naver', 'baemin', 'yogiyo', 'coupangeats']:
        platform_stores = await manager.get_stores_by_platform(platform)
        platform_count = sum(len(data['stores']) for data in platform_stores.values())
        print(f"   {platform}: {platform_count}개 매장 ({len(platform_stores)}명 사용자)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())