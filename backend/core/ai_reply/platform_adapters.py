#!/usr/bin/env python3
"""
Multi-Platform Review Adapter System
멀티플랫폼 리뷰 어댑터 시스템

이 모듈은 여러 리뷰 플랫폼(네이버, 배민, 요기요, 쿠팡이츠)의 
데이터를 통합된 인터페이스로 처리하기 위한 어댑터 패턴을 구현합니다.
"""

import os
import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, date
import logging

# Supabase 클라이언트 (지연 로딩)
try:
    from supabase import Client
except ImportError:
    Client = None

# 로거 설정
logger = logging.getLogger(__name__)


class Platform(Enum):
    """지원되는 리뷰 플랫폼"""
    NAVER = "naver"
    BAEMIN = "baemin" 
    YOGIYO = "yogiyo"
    COUPANGEATS = "coupangeats"


@dataclass
class UnifiedReview:
    """통합된 리뷰 데이터 구조"""
    # 공통 필드
    id: str
    platform_store_id: str
    platform: Platform
    reviewer_name: str
    rating: int
    review_text: str
    review_date: Union[date, str]
    reply_status: str = 'draft'
    
    # 선택적 필드
    reviewer_id: Optional[str] = None
    reviewer_level: Optional[str] = None
    reply_text: Optional[str] = None
    reply_posted_at: Optional[datetime] = None
    reply_error_message: Optional[str] = None
    has_photos: bool = False
    photo_urls: List[str] = field(default_factory=list)
    order_menu_items: List[str] = field(default_factory=list)
    
    # 플랫폼별 메타데이터
    platform_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 추가 정보
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """초기화 후 처리"""
        # 날짜 타입 정규화
        if isinstance(self.review_date, str):
            try:
                self.review_date = datetime.strptime(self.review_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                # 파싱 실패시 현재 날짜 사용
                self.review_date = datetime.now().date()
        
        # Platform enum 정규화
        if isinstance(self.platform, str):
            try:
                self.platform = Platform(self.platform.lower())
            except ValueError:
                logger.warning(f"Unknown platform: {self.platform}")


class PlatformAdapter(ABC):
    """플랫폼 어댑터 추상 클래스"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.platform = self.get_platform()
        self.table_name = self.get_table_name()
    
    @abstractmethod
    def get_platform(self) -> Platform:
        """플랫폼 타입 반환"""
        pass
    
    @abstractmethod
    def get_table_name(self) -> str:
        """테이블 이름 반환"""
        pass
    
    @abstractmethod
    def map_to_unified(self, raw_review: Dict[str, Any]) -> UnifiedReview:
        """플랫폼별 데이터를 통합 구조로 변환"""
        pass
    
    def get_reviews_by_store(self, platform_store_id: str, limit: Optional[int] = None) -> List[UnifiedReview]:
        """매장별 리뷰 조회"""
        try:
            query = self.supabase.table(self.table_name)\
                .select('*')\
                .eq('platform_store_id', platform_store_id)\
                .order('review_date', desc=True)
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            if not response.data:
                return []
            
            unified_reviews = []
            for raw_review in response.data:
                try:
                    unified_review = self.map_to_unified(raw_review)
                    unified_reviews.append(unified_review)
                except Exception as e:
                    logger.error(f"[ERROR] Failed to map review {raw_review.get('id', 'unknown')}: {e}")
                    continue
            
            return unified_reviews
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to get reviews for store {platform_store_id}: {e}")
            return []
    
    def get_draft_reviews(self, platform_store_id: str, limit: Optional[int] = None) -> List[UnifiedReview]:
        """답글 대기 중인 리뷰 조회"""
        try:
            query = self.supabase.table(self.table_name)\
                .select('*')\
                .eq('platform_store_id', platform_store_id)\
                .eq('reply_status', 'draft')\
                .order('review_date', desc=True)
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            if not response.data:
                return []
            
            return [self.map_to_unified(raw) for raw in response.data]
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to get draft reviews for store {platform_store_id}: {e}")
            return []


class NaverAdapter(PlatformAdapter):
    """네이버 플랫폼 어댑터"""
    
    def get_platform(self) -> Platform:
        return Platform.NAVER
    
    def get_table_name(self) -> str:
        return 'reviews_naver'
    
    def map_to_unified(self, raw_review: Dict[str, Any]) -> UnifiedReview:
        """네이버 리뷰 데이터를 통합 구조로 변환"""
        return UnifiedReview(
            id=raw_review['id'],
            platform_store_id=raw_review['platform_store_id'],
            platform=Platform.NAVER,
            reviewer_name=raw_review.get('reviewer_name', '익명'),
            reviewer_id=raw_review.get('reviewer_id'),
            reviewer_level=raw_review.get('reviewer_level'),
            rating=raw_review.get('rating', 5),
            review_text=raw_review.get('review_text', ''),
            review_date=raw_review.get('review_date'),
            reply_status=raw_review.get('reply_status', 'draft'),
            reply_text=raw_review.get('reply_text'),
            reply_posted_at=raw_review.get('reply_posted_at'),
            reply_error_message=raw_review.get('reply_error_message'),
            has_photos=raw_review.get('has_photos', False),
            photo_urls=raw_review.get('photo_urls', []) if raw_review.get('photo_urls') else [],
            order_menu_items=raw_review.get('order_menu_items', []) if raw_review.get('order_menu_items') else [],
            platform_metadata=raw_review.get('naver_metadata', {}) if raw_review.get('naver_metadata') else {},
            created_at=raw_review.get('created_at'),
            updated_at=raw_review.get('updated_at')
        )


class BaeminAdapter(PlatformAdapter):
    """배민 플랫폼 어댑터"""
    
    def get_platform(self) -> Platform:
        return Platform.BAEMIN
    
    def get_table_name(self) -> str:
        return 'reviews_baemin'
    
    def map_to_unified(self, raw_review: Dict[str, Any]) -> UnifiedReview:
        """배민 리뷰 데이터를 통합 구조로 변환"""
        return UnifiedReview(
            id=raw_review['id'],
            platform_store_id=raw_review['platform_store_id'],
            platform=Platform.BAEMIN,
            reviewer_name=raw_review.get('reviewer_name', '익명'),
            reviewer_id=raw_review.get('reviewer_id'),
            reviewer_level=raw_review.get('reviewer_level'),
            rating=raw_review.get('rating', 5),
            review_text=raw_review.get('review_text', ''),
            review_date=raw_review.get('review_date'),
            reply_status=raw_review.get('reply_status', 'draft'),
            reply_text=raw_review.get('reply_text'),
            reply_posted_at=raw_review.get('reply_posted_at'),
            reply_error_message=raw_review.get('reply_error_message'),
            has_photos=raw_review.get('has_photos', False),
            photo_urls=raw_review.get('photo_urls', []) if raw_review.get('photo_urls') else [],
            order_menu_items=raw_review.get('order_menu_items', []) if raw_review.get('order_menu_items') else [],
            platform_metadata=raw_review.get('baemin_metadata', {}) if raw_review.get('baemin_metadata') else {},
            created_at=raw_review.get('created_at'),
            updated_at=raw_review.get('updated_at')
        )


class YogiyoAdapter(PlatformAdapter):
    """요기요 플랫폼 어댑터"""
    
    def get_platform(self) -> Platform:
        return Platform.YOGIYO
    
    def get_table_name(self) -> str:
        return 'reviews_yogiyo'
    
    def map_to_unified(self, raw_review: Dict[str, Any]) -> UnifiedReview:
        """요기요 리뷰 데이터를 통합 구조로 변환"""
        return UnifiedReview(
            id=raw_review['id'],
            platform_store_id=raw_review['platform_store_id'],
            platform=Platform.YOGIYO,
            reviewer_name=raw_review.get('reviewer_name', '익명'),
            reviewer_id=raw_review.get('reviewer_id'),
            reviewer_level=raw_review.get('reviewer_level'),
            rating=raw_review.get('rating', 5),
            review_text=raw_review.get('review_text', ''),
            review_date=raw_review.get('review_date'),
            reply_status=raw_review.get('reply_status', 'draft'),
            reply_text=raw_review.get('reply_text'),
            reply_posted_at=raw_review.get('reply_posted_at'),
            reply_error_message=raw_review.get('reply_error_message'),
            has_photos=raw_review.get('has_photos', False),
            photo_urls=raw_review.get('photo_urls', []) if raw_review.get('photo_urls') else [],
            order_menu_items=raw_review.get('order_menu_items', []) if raw_review.get('order_menu_items') else [],
            platform_metadata=raw_review.get('yogiyo_metadata', {}) if raw_review.get('yogiyo_metadata') else {},
            created_at=raw_review.get('created_at'),
            updated_at=raw_review.get('updated_at')
        )


class CoupangEatsAdapter(PlatformAdapter):
    """쿠팡이츠 플랫폼 어댑터"""
    
    def get_platform(self) -> Platform:
        return Platform.COUPANGEATS
    
    def get_table_name(self) -> str:
        return 'reviews_coupangeats'
    
    def map_to_unified(self, raw_review: Dict[str, Any]) -> UnifiedReview:
        """쿠팡이츠 리뷰 데이터를 통합 구조로 변환"""
        return UnifiedReview(
            id=raw_review['id'],
            platform_store_id=raw_review['platform_store_id'],
            platform=Platform.COUPANGEATS,
            reviewer_name=raw_review.get('reviewer_name', '익명'),
            reviewer_id=raw_review.get('reviewer_id'),
            reviewer_level=raw_review.get('reviewer_level'),
            rating=raw_review.get('rating', 5),
            review_text=raw_review.get('review_text', ''),
            review_date=raw_review.get('review_date'),
            reply_status=raw_review.get('reply_status', 'draft'),
            reply_text=raw_review.get('reply_text'),
            reply_posted_at=raw_review.get('reply_posted_at'),
            reply_error_message=raw_review.get('reply_error_message'),
            has_photos=raw_review.get('has_photos', False),
            photo_urls=raw_review.get('photo_urls', []) if raw_review.get('photo_urls') else [],
            order_menu_items=raw_review.get('order_menu_items', []) if raw_review.get('order_menu_items') else [],
            platform_metadata=raw_review.get('coupangeats_metadata', {}) if raw_review.get('coupangeats_metadata') else {},
            created_at=raw_review.get('created_at'),
            updated_at=raw_review.get('updated_at')
        )


class MultiPlatformManager:
    """멀티플랫폼 리뷰 관리자"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        
        # 플랫폼별 어댑터 초기화
        self.adapters = {
            Platform.NAVER: NaverAdapter(supabase_client),
            Platform.BAEMIN: BaeminAdapter(supabase_client),
            Platform.YOGIYO: YogiyoAdapter(supabase_client),
            Platform.COUPANGEATS: CoupangEatsAdapter(supabase_client)
        }
    
    def get_adapter(self, platform: Union[str, Platform]) -> PlatformAdapter:
        """플랫폼별 어댑터 반환"""
        if isinstance(platform, str):
            try:
                platform = Platform(platform.lower())
            except ValueError:
                raise ValueError(f"Unsupported platform: {platform}")
        
        if platform not in self.adapters:
            raise ValueError(f"No adapter found for platform: {platform}")
        
        return self.adapters[platform]
    
    def get_all_reviews_by_user(self, user_id: str, platforms: Optional[List[Platform]] = None, 
                              limit_per_platform: Optional[int] = None) -> Dict[Platform, List[UnifiedReview]]:
        """사용자의 모든 매장에서 리뷰 조회 (멀티플랫폼)"""
        
        if platforms is None:
            platforms = list(Platform)
        
        # 사용자 매장 조회
        try:
            stores_response = self.supabase.table('platform_stores')\
                .select('id, platform, store_name, is_active')\
                .eq('user_id', user_id)\
                .eq('is_active', True)\
                .execute()
            
            if not stores_response.data:
                logger.warning(f"No active stores found for user: {user_id}")
                return {}
            
            user_stores = stores_response.data
        except Exception as e:
            logger.error(f"[ERROR] Failed to get user stores: {e}")
            return {}
        
        # 플랫폼별 리뷰 조회
        all_reviews = {}
        
        for platform in platforms:
            try:
                adapter = self.get_adapter(platform)
                platform_reviews = []
                
                # 해당 플랫폼의 매장들에서 리뷰 수집
                for store in user_stores:
                    if store['platform'] == platform.value:
                        store_reviews = adapter.get_reviews_by_store(store['id'], limit_per_platform)
                        platform_reviews.extend(store_reviews)
                
                all_reviews[platform] = platform_reviews
                logger.info(f"[OK] {platform.value.upper()}: {len(platform_reviews)} reviews")
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to get reviews from {platform.value}: {e}")
                all_reviews[platform] = []
        
        return all_reviews
    
    def get_draft_reviews_by_user(self, user_id: str, platforms: Optional[List[Platform]] = None,
                                limit_per_platform: Optional[int] = None) -> Dict[Platform, List[UnifiedReview]]:
        """사용자의 답글 대기 리뷰 조회 (멀티플랫폼)"""
        
        if platforms is None:
            platforms = list(Platform)
        
        # 사용자 매장 조회
        try:
            stores_response = self.supabase.table('platform_stores')\
                .select('id, platform, store_name, is_active')\
                .eq('user_id', user_id)\
                .eq('is_active', True)\
                .execute()
            
            if not stores_response.data:
                return {}
            
            user_stores = stores_response.data
        except Exception as e:
            logger.error(f"[ERROR] Failed to get user stores: {e}")
            return {}
        
        # 플랫폼별 답글 대기 리뷰 조회
        draft_reviews = {}
        
        for platform in platforms:
            try:
                adapter = self.get_adapter(platform)
                platform_drafts = []
                
                # 해당 플랫폼의 매장들에서 답글 대기 리뷰 수집
                for store in user_stores:
                    if store['platform'] == platform.value:
                        store_drafts = adapter.get_draft_reviews(store['id'], limit_per_platform)
                        platform_drafts.extend(store_drafts)
                
                draft_reviews[platform] = platform_drafts
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to get draft reviews from {platform.value}: {e}")
                draft_reviews[platform] = []
        
        return draft_reviews
    
    def get_platform_statistics(self, user_id: str) -> Dict[str, Dict[str, int]]:
        """플랫폼별 리뷰 통계 조회"""
        stats = {}
        
        all_reviews = self.get_all_reviews_by_user(user_id)
        
        for platform, reviews in all_reviews.items():
            draft_count = len([r for r in reviews if r.reply_status == 'draft'])
            stats[platform.value] = {
                'total': len(reviews),
                'draft': draft_count,
                'completed': len(reviews) - draft_count
            }
        
        return stats


# 유틸리티 함수들
def create_multiplatform_manager(supabase_url: str = None, supabase_key: str = None) -> MultiPlatformManager:
    """멀티플랫폼 매니저 생성 헬퍼 함수"""
    
    if not supabase_url:
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL') or os.getenv('SUPABASE_URL')
    if not supabase_key:
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL and key are required")
    
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        return MultiPlatformManager(supabase)
    except Exception as e:
        logger.error(f"[ERROR] Failed to create multiplatform manager: {e}")
        raise


def parse_platform_list(platforms: Optional[Union[str, List[str]]]) -> List[Platform]:
    """플랫폼 목록 파싱"""
    if not platforms:
        return list(Platform)
    
    if isinstance(platforms, str):
        platforms = [platforms]
    
    parsed_platforms = []
    for platform in platforms:
        try:
            parsed_platforms.append(Platform(platform.lower()))
        except ValueError:
            logger.warning(f"Unknown platform ignored: {platform}")
            continue
    
    return parsed_platforms if parsed_platforms else list(Platform)


if __name__ == "__main__":
    # 테스트 실행 예시
    print("Multi-Platform Review Adapter System")
    print("=" * 50)
    
    try:
        manager = create_multiplatform_manager()
        print("[OK] MultiPlatformManager created successfully")
        
        # 지원되는 플랫폼 출력
        print(f"Supported platforms: {[p.value for p in Platform]}")
        
    except Exception as e:
        print(f"[ERROR] {e}")