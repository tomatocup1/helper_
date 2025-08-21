"""
Celery 작업 정의
배민 크롤링 및 관련 비동기 작업
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from celery import Task
from celery.signals import task_failure, task_success
from supabase import create_client

from .celery_config import celery_app
from ..baemin.auth_service import BaeminAuthService
from ..baemin.crawler_service import BaeminCrawlerService
from ..shared.logger import get_logger
from ..shared.config import settings

logger = get_logger(__name__)

class CallbackTask(Task):
    """진행상황 콜백을 지원하는 기본 작업 클래스"""
    
    def __init__(self):
        self.supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    def update_progress(self, task_id: str, progress_data: Dict[str, Any]):
        """작업 진행상황 업데이트"""
        try:
            # Redis에 진행상황 저장
            self.backend.set(
                f"progress:{task_id}",
                json.dumps(progress_data),
                ex=3600  # 1시간 만료
            )
            
            # WebSocket으로 실시간 전송 (나중에 구현)
            # emit_progress_update(task_id, progress_data)
            
            logger.info(f"Progress updated for task {task_id}: {progress_data}")
            
        except Exception as e:
            logger.error(f"Failed to update progress for task {task_id}: {e}")

@celery_app.task(bind=True, base=CallbackTask, name='crawl_baemin_stores')
def crawl_baemin_stores(self, user_id: str, task_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    배민 매장 크롤링 작업
    
    Args:
        user_id: 사용자 ID
        task_options: 작업 옵션 (타임아웃 등)
    
    Returns:
        크롤링 결과
    """
    task_id = self.request.id
    logger.info(f"Starting Baemin crawling task {task_id} for user {user_id}")
    
    # 작업 상태 초기화
    self.update_state(
        state='PROGRESS',
        meta={
            'step': 'initialization',
            'message': '크롤링 작업 시작...',
            'progress': 0,
            'user_id': user_id
        }
    )
    
    def progress_callback(progress_data):
        """진행상황 콜백 함수"""
        progress_data['task_id'] = task_id
        progress_data['user_id'] = user_id
        progress_data['timestamp'] = datetime.now().isoformat()
        
        # Celery 상태 업데이트
        self.update_state(
            state='PROGRESS',
            meta=progress_data
        )
        
        # 커스텀 진행상황 업데이트
        self.update_progress(task_id, progress_data)
    
    try:
        # 비동기 크롤링 실행
        result = asyncio.run(_run_crawling_task(user_id, progress_callback, task_options))
        
        # 성공 상태 업데이트
        self.update_state(
            state='SUCCESS',
            meta={
                'step': 'completed',
                'message': f"크롤링 완료! {result.get('summary', {}).get('valid_count', 0)}개 매장 발견",
                'progress': 100,
                'result': result,
                'user_id': user_id,
                'task_id': task_id,
                'completed_at': datetime.now().isoformat()
            }
        )
        
        logger.info(f"Baemin crawling task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_message = f"크롤링 중 오류 발생: {str(e)}"
        logger.error(f"Baemin crawling task {task_id} failed: {e}")
        
        # 실패 상태 업데이트  
        self.update_state(
            state='FAILURE',
            meta={
                'step': 'error',
                'message': error_message,
                'progress': 0,
                'error': str(e),
                'user_id': user_id,
                'task_id': task_id,
                'failed_at': datetime.now().isoformat()
            }
        )
        
        # 예외 재발생으로 Celery 실패 처리
        raise

async def _run_crawling_task(
    user_id: str, 
    progress_callback, 
    task_options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """실제 크롤링 작업 실행"""
    
    # 기본 옵션
    options = task_options or {}
    timeout = options.get('timeout', settings.DEFAULT_TIMEOUT)
    
    # 서비스 초기화
    auth_service = BaeminAuthService()
    crawler_service = BaeminCrawlerService(auth_service)
    
    # 크롤링 실행
    result = await crawler_service.crawl_stores(
        user_id=user_id,
        progress_callback=progress_callback,
        timeout=timeout
    )
    
    return result

@celery_app.task(name='update_crawl_progress')
def update_crawl_progress(task_id: str, progress_data: Dict[str, Any]) -> bool:
    """
    크롤링 진행상황 업데이트 작업
    WebSocket 전송 등 별도 처리가 필요한 경우 사용
    """
    try:
        logger.info(f"Updating progress for task {task_id}: {progress_data}")
        
        # 여기에 WebSocket 전송, 데이터베이스 업데이트 등 추가 로직 구현
        # emit_to_websocket(task_id, progress_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update progress for task {task_id}: {e}")
        return False

@celery_app.task(name='cleanup_expired_tasks')
def cleanup_expired_tasks():
    """만료된 작업 정리"""
    try:
        # Redis에서 만료된 진행상황 데이터 정리
        # 실제 구현은 Redis 패턴 매칭 사용
        logger.info("Cleaning up expired tasks...")
        return True
        
    except Exception as e:
        logger.error(f"Task cleanup failed: {e}")
        return False

# 작업 완료/실패 시그널 핸들러
@task_success.connect
def task_success_handler(sender=None, task_id=None, result=None, retval=None, **kwargs):
    """작업 성공 시 처리"""
    logger.info(f"Task {task_id} completed successfully")

@task_failure.connect  
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """작업 실패 시 처리"""
    logger.error(f"Task {task_id} failed: {exception}")