"""
리뷰 모니터링 및 알림 시스템
실시간 리뷰 감지 및 알림톡 발송
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from supabase import create_client, Client
from kakao_alimtalk import KakaoAlimTalkService, AlertLevel

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ReviewEvent:
    """리뷰 이벤트 정보"""
    review_id: str
    store_id: str
    platform: str
    rating: int
    content: str
    reviewer_name: str
    created_at: datetime
    is_urgent: bool = False

class ReviewMonitor:
    """리뷰 모니터링 시스템"""

    def __init__(self):
        self.supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Supabase 설정이 누락되었습니다.")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.alimtalk = KakaoAlimTalkService()

        # 모니터링 설정
        self.check_interval = 300  # 5분마다 체크
        self.platforms = ['naver', 'baemin', 'coupangeats', 'yogiyo']
        self.last_check_time = None

    async def get_new_reviews(self, since: datetime) -> List[ReviewEvent]:
        """신규 리뷰 조회"""
        new_reviews = []

        for platform in self.platforms:
            try:
                table_name = f'reviews_{platform}'
                response = self.supabase.table(table_name).select(
                    'id, store_id, rating, content, reviewer_name, created_at'
                ).gte('created_at', since.isoformat()).order(
                    'created_at', desc=True
                ).execute()

                for review_data in response.data:
                    review = ReviewEvent(
                        review_id=review_data['id'],
                        store_id=review_data['store_id'],
                        platform=platform,
                        rating=review_data.get('rating', 5),
                        content=review_data.get('content', ''),
                        reviewer_name=review_data.get('reviewer_name', '익명'),
                        created_at=datetime.fromisoformat(review_data['created_at'].replace('Z', '+00:00'))
                    )

                    # 긴급도 판단
                    review.is_urgent = await self._is_urgent_review(review)
                    new_reviews.append(review)

            except Exception as e:
                logger.error(f"{platform} 리뷰 조회 실패: {e}")

        return sorted(new_reviews, key=lambda x: x.created_at, reverse=True)

    async def _is_urgent_review(self, review: ReviewEvent) -> bool:
        """긴급 리뷰 판단"""
        # 별점 기준
        if review.rating <= 2:
            return True

        # 부정적 키워드 검사
        urgent_keywords = [
            '최악', '환불', '신고', '컴플레인', '위생', '머리카락',
            '벌레', '음식물중독', '식중독', '불결', '더러움'
        ]

        content_lower = review.content.lower()
        if any(keyword in content_lower for keyword in urgent_keywords):
            return True

        return False

    async def process_new_reviews(self, reviews: List[ReviewEvent]) -> Dict[str, int]:
        """신규 리뷰 처리"""
        stats = {
            'total': len(reviews),
            'urgent': 0,
            'normal': 0,
            'notifications_sent': 0,
            'notifications_failed': 0
        }

        # 긴급/일반 분류
        urgent_reviews = [r for r in reviews if r.is_urgent]
        normal_reviews = [r for r in reviews if not r.is_urgent]

        stats['urgent'] = len(urgent_reviews)
        stats['normal'] = len(normal_reviews)

        # 긴급 리뷰 즉시 알림
        for review in urgent_reviews:
            try:
                success = await self.alimtalk.send_review_alert(review.review_id)
                if success:
                    stats['notifications_sent'] += 1
                    logger.info(f"긴급 리뷰 알림 발송 성공: {review.review_id}")
                else:
                    stats['notifications_failed'] += 1
                    logger.error(f"긴급 리뷰 알림 발송 실패: {review.review_id}")

                # 연속 발송 제한
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"긴급 리뷰 알림 처리 오류: {e}")
                stats['notifications_failed'] += 1

        # 일반 리뷰 배치 처리 (매장별로 그룹화)
        if normal_reviews:
            await self._process_normal_reviews_batch(normal_reviews, stats)

        return stats

    async def _process_normal_reviews_batch(
        self,
        reviews: List[ReviewEvent],
        stats: Dict[str, int]
    ):
        """일반 리뷰 배치 처리"""
        # 매장별로 그룹화
        store_reviews: Dict[str, List[ReviewEvent]] = {}
        for review in reviews:
            if review.store_id not in store_reviews:
                store_reviews[review.store_id] = []
            store_reviews[review.store_id].append(review)

        # 매장별 일일 요약 알림 (5개 이상인 경우만)
        for store_id, store_review_list in store_reviews.items():
            if len(store_review_list) >= 5:
                try:
                    # 대표 리뷰로 알림 발송 (가장 최근 리뷰)
                    latest_review = max(store_review_list, key=lambda x: x.created_at)
                    success = await self.alimtalk.send_review_alert(latest_review.review_id)

                    if success:
                        stats['notifications_sent'] += 1
                        logger.info(f"매장 일일 요약 알림 발송: {store_id} ({len(store_review_list)}개 리뷰)")
                    else:
                        stats['notifications_failed'] += 1

                except Exception as e:
                    logger.error(f"일일 요약 알림 처리 오류: {e}")
                    stats['notifications_failed'] += 1

    async def check_store_settings(self, store_id: str) -> Dict[str, Any]:
        """매장별 알림 설정 조회"""
        try:
            response = self.supabase.table('store_notification_settings').select(
                '*'
            ).eq('store_id', store_id).single().execute()

            if response.data:
                return response.data
            else:
                # 기본 설정 반환
                return {
                    'urgent_notifications': True,
                    'daily_summary': True,
                    'notification_hours_start': 9,
                    'notification_hours_end': 22,
                    'min_rating_threshold': 3
                }

        except Exception as e:
            logger.error(f"매장 설정 조회 실패: {e}")
            return {}

    async def is_notification_time(self, store_id: str) -> bool:
        """알림 발송 가능 시간 체크"""
        settings = await self.check_store_settings(store_id)
        current_hour = datetime.now().hour

        start_hour = settings.get('notification_hours_start', 9)
        end_hour = settings.get('notification_hours_end', 22)

        return start_hour <= current_hour <= end_hour

    async def monitor_loop(self):
        """모니터링 메인 루프"""
        logger.info("리뷰 모니터링 시작")

        if not self.last_check_time:
            # 첫 실행 시 30분 전부터 체크
            self.last_check_time = datetime.now() - timedelta(minutes=30)

        while True:
            try:
                current_time = datetime.now()
                logger.info(f"리뷰 모니터링 실행: {current_time}")

                # 신규 리뷰 조회
                new_reviews = await self.get_new_reviews(self.last_check_time)

                if new_reviews:
                    logger.info(f"신규 리뷰 {len(new_reviews)}개 발견")

                    # 리뷰 처리
                    stats = await self.process_new_reviews(new_reviews)

                    # 통계 로깅
                    logger.info(f"처리 완료: {stats}")

                    # 모니터링 로그 저장
                    await self._save_monitoring_log(stats)

                else:
                    logger.info("신규 리뷰 없음")

                # 마지막 체크 시간 업데이트
                self.last_check_time = current_time

                # 다음 체크까지 대기
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도

    async def _save_monitoring_log(self, stats: Dict[str, int]):
        """모니터링 로그 저장"""
        try:
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'total_reviews': stats['total'],
                'urgent_reviews': stats['urgent'],
                'normal_reviews': stats['normal'],
                'notifications_sent': stats['notifications_sent'],
                'notifications_failed': stats['notifications_failed'],
                'created_at': datetime.now().isoformat()
            }

            self.supabase.table('monitoring_logs').insert(log_data).execute()

        except Exception as e:
            logger.error(f"모니터링 로그 저장 실패: {e}")

    async def manual_check(self, hours_back: int = 1) -> Dict[str, int]:
        """수동 체크 (테스트용)"""
        since = datetime.now() - timedelta(hours=hours_back)
        reviews = await self.get_new_reviews(since)
        return await self.process_new_reviews(reviews)

# CLI 실행부
async def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='리뷰 모니터링 시스템')
    parser.add_argument('--mode', choices=['monitor', 'test'], default='monitor',
                       help='실행 모드 (monitor: 지속 모니터링, test: 테스트)')
    parser.add_argument('--hours', type=int, default=1,
                       help='테스트 모드에서 확인할 시간 (시간)')

    args = parser.parse_args()

    monitor = ReviewMonitor()

    if args.mode == 'test':
        logger.info(f"테스트 모드: 최근 {args.hours}시간 리뷰 체크")
        stats = await monitor.manual_check(args.hours)
        logger.info(f"테스트 결과: {stats}")
    else:
        logger.info("모니터링 모드 시작")
        await monitor.monitor_loop()

if __name__ == "__main__":
    import os
    asyncio.run(main())