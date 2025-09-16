"""
카카오 알림톡 발송 시스템
베타 서비스용 알림톡 연동 모듈
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import httpx
from supabase import create_client, Client
import logging

# 로거 설정
logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """알림 우선순위 레벨"""
    CRITICAL = "critical"  # 별점 1-2점, 컴플레인
    HIGH = "high"          # 별점 3점, 긴급 대응 필요
    NORMAL = "normal"      # 별점 4-5점, 정보성

@dataclass
class AlimTalkTemplate:
    """알림톡 템플릿"""
    template_code: str
    message: str
    buttons: Optional[List[Dict[str, str]]] = None

class KakaoAlimTalkService:
    """카카오 알림톡 서비스"""

    def __init__(self):
        self.api_key = os.getenv('KAKAO_API_KEY')
        self.sender_key = os.getenv('KAKAO_SENDER_KEY')
        self.supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not all([self.api_key, self.sender_key, self.supabase_url, self.supabase_key]):
            raise ValueError("카카오 알림톡 설정이 누락되었습니다.")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.base_url = "https://alimtalk-api.bizmsg.kr"

        # 템플릿 정의
        self.templates = {
            AlertLevel.CRITICAL: AlimTalkTemplate(
                template_code="CRITICAL_REVIEW",
                message="""🚨 긴급 리뷰 알림

매장: {store_name}
플랫폼: {platform}
별점: {rating}점
작성자: {reviewer_name}

리뷰 내용:
{review_content}

즉시 확인이 필요합니다.""",
                buttons=[
                    {"name": "리뷰 확인", "type": "WL", "url_mobile": "{review_url}"}
                ]
            ),
            AlertLevel.HIGH: AlimTalkTemplate(
                template_code="HIGH_REVIEW",
                message="""⚠️ 중요 리뷰 알림

매장: {store_name}
플랫폼: {platform}
별점: {rating}점
작성자: {reviewer_name}

리뷰 내용:
{review_content}

답글 작성을 검토해주세요.""",
                buttons=[
                    {"name": "리뷰 확인", "type": "WL", "url_mobile": "{review_url}"}
                ]
            ),
            AlertLevel.NORMAL: AlimTalkTemplate(
                template_code="NORMAL_REVIEW",
                message="""📝 새 리뷰 알림

매장: {store_name}
플랫폼: {platform}
별점: {rating}점

총 {daily_review_count}개의 새 리뷰가 있습니다.
AI 답글이 자동 생성되었습니다.""",
                buttons=[
                    {"name": "대시보드", "type": "WL", "url_mobile": "{dashboard_url}"}
                ]
            )
        }

    async def determine_alert_level(self, review: Dict[str, Any]) -> AlertLevel:
        """리뷰 내용을 분석하여 알림 레벨 결정"""
        rating = review.get('rating', 5)
        content = review.get('content', '').lower()

        # 부정적 키워드 목록
        negative_keywords = [
            '최악', '별로', '실망', '불친절', '늦음', '차가움', '맛없음',
            '더러움', '불결', '환불', '컴플레인', '신고', '위생', '머리카락'
        ]

        # 별점 기준 판단
        if rating <= 2:
            return AlertLevel.CRITICAL
        elif rating == 3:
            return AlertLevel.HIGH

        # 키워드 기준 판단
        if any(keyword in content for keyword in negative_keywords):
            if rating <= 3:
                return AlertLevel.CRITICAL
            else:
                return AlertLevel.HIGH

        return AlertLevel.NORMAL

    async def get_store_info(self, store_uuid: str) -> Optional[Dict[str, Any]]:
        """매장 정보 조회"""
        try:
            response = self.supabase.table('stores').select(
                'name, owner_phone, platform_stores(*)'
            ).eq('id', store_uuid).single().execute()

            return response.data
        except Exception as e:
            logger.error(f"매장 정보 조회 실패: {e}")
            return None

    async def send_alimtalk(
        self,
        phone_number: str,
        template: AlimTalkTemplate,
        variables: Dict[str, str]
    ) -> bool:
        """알림톡 발송"""
        try:
            # 전화번호 포맷팅 (- 제거)
            formatted_phone = phone_number.replace('-', '').replace(' ', '')
            if not formatted_phone.startswith('010'):
                logger.error(f"잘못된 전화번호 형식: {phone_number}")
                return False

            # 메시지 변수 치환
            message = template.message.format(**variables)

            # API 요청 데이터
            payload = {
                "senderKey": self.sender_key,
                "templateCode": template.template_code,
                "recipientList": [
                    {
                        "recipientNo": formatted_phone,
                        "content": message,
                        "buttons": template.buttons or []
                    }
                ]
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v2/sender/{self.sender_key}/send",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"알림톡 발송 성공: {formatted_phone}")
                    return True
                else:
                    logger.error(f"알림톡 발송 실패: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"알림톡 발송 오류: {e}")
            return False

    async def send_review_alert(self, review_id: str) -> bool:
        """리뷰 알림 발송"""
        try:
            # 리뷰 정보 조회
            review_response = self.supabase.table('reviews_combined_view').select(
                '*, stores(name, owner_phone)'
            ).eq('id', review_id).single().execute()

            if not review_response.data:
                logger.error(f"리뷰를 찾을 수 없습니다: {review_id}")
                return False

            review = review_response.data
            store = review['stores']

            if not store['owner_phone']:
                logger.warning(f"매장 전화번호가 없습니다: {review['store_id']}")
                return False

            # 알림 레벨 결정
            alert_level = await self.determine_alert_level(review)
            template = self.templates[alert_level]

            # 변수 준비
            variables = {
                'store_name': store['name'],
                'platform': review['platform'],
                'rating': str(review.get('rating', 'N/A')),
                'reviewer_name': review.get('reviewer_name', '익명'),
                'review_content': review.get('content', '')[:100] + '...' if len(review.get('content', '')) > 100 else review.get('content', ''),
                'review_url': f"https://yourdomain.com/reviews/{review_id}",
                'dashboard_url': "https://yourdomain.com/dashboard"
            }

            # 일일 리뷰 수 (NORMAL 레벨용)
            if alert_level == AlertLevel.NORMAL:
                today = datetime.now().date()
                daily_count_response = self.supabase.table('reviews_combined_view').select(
                    'id'
                ).eq('store_id', review['store_id']).gte(
                    'created_at', today.isoformat()
                ).execute()

                variables['daily_review_count'] = str(len(daily_count_response.data))

            # 알림톡 발송
            success = await self.send_alimtalk(
                store['owner_phone'],
                template,
                variables
            )

            # 발송 결과 기록
            await self.log_alimtalk_result(review_id, alert_level, success)

            return success

        except Exception as e:
            logger.error(f"리뷰 알림 발송 실패: {e}")
            return False

    async def log_alimtalk_result(
        self,
        review_id: str,
        alert_level: AlertLevel,
        success: bool
    ):
        """알림톡 발송 결과 로깅"""
        try:
            log_data = {
                'review_id': review_id,
                'alert_level': alert_level.value,
                'sent_at': datetime.now().isoformat(),
                'success': success,
                'created_at': datetime.now().isoformat()
            }

            self.supabase.table('alimtalk_logs').insert(log_data).execute()

        except Exception as e:
            logger.error(f"알림톡 로그 저장 실패: {e}")

    async def send_batch_alerts(self, review_ids: List[str]) -> Dict[str, int]:
        """배치 알림 발송"""
        results = {'success': 0, 'failed': 0}

        # 초당 20건 제한을 위한 세마포어
        semaphore = asyncio.Semaphore(20)

        async def send_single_alert(review_id: str):
            async with semaphore:
                success = await self.send_review_alert(review_id)
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1

                # 초당 제한을 위한 대기
                await asyncio.sleep(0.05)  # 50ms 대기

        # 병렬 처리
        tasks = [send_single_alert(review_id) for review_id in review_ids]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"배치 알림 발송 완료: 성공 {results['success']}, 실패 {results['failed']}")
        return results

# 사용 예시
async def main():
    """알림톡 서비스 테스트"""
    service = KakaoAlimTalkService()

    # 테스트 리뷰 ID로 알림 발송
    # success = await service.send_review_alert("test-review-id")
    # print(f"알림 발송 결과: {success}")

if __name__ == "__main__":
    asyncio.run(main())