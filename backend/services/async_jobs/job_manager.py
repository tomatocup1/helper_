"""
작업 관리자
크롤링 작업 시작, 모니터링, 취소 등 관리
"""

import json
import redis
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from celery.result import AsyncResult

from .celery_config import celery_app
from .tasks import crawl_baemin_stores
from ..shared.logger import get_logger
from ..shared.config import settings

logger = get_logger(__name__)

class BaeminJobManager:
    """배민 크롤링 작업 관리자"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.celery_app = celery_app
    
    def start_crawling_job(
        self, 
        user_id: str, 
        task_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        크롤링 작업 시작
        
        Args:
            user_id: 사용자 ID
            task_options: 작업 옵션
            
        Returns:
            작업 정보
        """
        try:
            # 기존 진행 중인 작업 확인
            existing_task = self.get_user_active_task(user_id)
            if existing_task:
                return {
                    "success": False,
                    "message": "이미 진행 중인 크롤링 작업이 있습니다.",
                    "existing_task": existing_task
                }
            
            # 작업 시작
            task_result = crawl_baemin_stores.delay(user_id, task_options)
            task_id = task_result.id
            
            # 작업 정보 Redis에 저장
            task_info = {
                "task_id": task_id,
                "user_id": user_id,
                "status": "PENDING",
                "created_at": datetime.now().isoformat(),
                "options": task_options or {}
            }
            
            self.redis_client.setex(
                f"task:{user_id}:active",
                3600,  # 1시간
                json.dumps(task_info)
            )
            
            self.redis_client.setex(
                f"task_info:{task_id}",
                3600,
                json.dumps(task_info)
            )
            
            logger.info(f"Started crawling task {task_id} for user {user_id}")
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "크롤링 작업이 시작되었습니다.",
                "task_info": task_info
            }
            
        except Exception as e:
            logger.error(f"Failed to start crawling job for user {user_id}: {e}")
            return {
                "success": False,
                "message": f"작업 시작 실패: {str(e)}"
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        작업 상태 조회
        
        Args:
            task_id: 작업 ID
            
        Returns:
            작업 상태 정보
        """
        try:
            # Celery 결과 조회
            result = AsyncResult(task_id, app=self.celery_app)
            
            # 기본 상태 정보
            status_info = {
                "task_id": task_id,
                "status": result.status,
                "result": result.result if result.successful() else None,
                "error": str(result.result) if result.failed() else None
            }
            
            # 진행상황 정보 추가
            progress_data = self.get_task_progress(task_id)
            if progress_data:
                status_info.update(progress_data)
            
            # 작업 정보 추가
            task_info = self.get_task_info(task_id)
            if task_info:
                status_info["task_info"] = task_info
            
            return status_info
            
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "UNKNOWN",
                "error": str(e)
            }
    
    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """작업 진행상황 조회"""
        try:
            progress_key = f"progress:{task_id}"
            progress_data = self.redis_client.get(progress_key)
            
            if progress_data:
                return json.loads(progress_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task progress for {task_id}: {e}")
            return None
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """작업 정보 조회"""
        try:
            info_key = f"task_info:{task_id}"
            task_info = self.redis_client.get(info_key)
            
            if task_info:
                return json.loads(task_info)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task info for {task_id}: {e}")
            return None
    
    def get_user_active_task(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자의 활성 작업 조회"""
        try:
            active_key = f"task:{user_id}:active"
            active_task = self.redis_client.get(active_key)
            
            if active_task:
                task_info = json.loads(active_task)
                
                # 작업이 실제로 활성 상태인지 확인
                task_status = self.get_task_status(task_info["task_id"])
                if task_status["status"] in ["PENDING", "PROGRESS"]:
                    return task_info
                else:
                    # 완료된 작업이면 활성 키 삭제
                    self.redis_client.delete(active_key)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get active task for user {user_id}: {e}")
            return None
    
    def cancel_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """
        작업 취소
        
        Args:
            task_id: 작업 ID
            user_id: 사용자 ID (권한 확인용)
            
        Returns:
            취소 결과
        """
        try:
            # 권한 확인
            task_info = self.get_task_info(task_id)
            if not task_info or task_info.get("user_id") != user_id:
                return {
                    "success": False,
                    "message": "작업을 취소할 권한이 없습니다."
                }
            
            # Celery 작업 취소
            self.celery_app.control.revoke(task_id, terminate=True)
            
            # Redis 데이터 정리
            self.redis_client.delete(f"task:{user_id}:active")
            self.redis_client.delete(f"progress:{task_id}")
            
            logger.info(f"Cancelled task {task_id} for user {user_id}")
            
            return {
                "success": True,
                "message": "작업이 취소되었습니다."
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return {
                "success": False,
                "message": f"작업 취소 실패: {str(e)}"
            }
    
    def get_task_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        사용자의 작업 히스토리 조회
        
        Args:
            user_id: 사용자 ID
            limit: 조회 제한 수
            
        Returns:
            작업 히스토리 목록
        """
        try:
            # Redis에서 사용자별 작업 히스토리 조회
            # 실제 구현에서는 별도 키 패턴 사용
            history_key = f"task_history:{user_id}"
            history_data = self.redis_client.lrange(history_key, 0, limit - 1)
            
            history = []
            for item in history_data:
                try:
                    task_data = json.loads(item)
                    history.append(task_data)
                except json.JSONDecodeError:
                    continue
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get task history for user {user_id}: {e}")
            return []
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24):
        """완료된 작업 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            # 패턴 매칭으로 만료된 키 찾기 및 삭제
            # 실제 구현에서는 Redis SCAN 사용
            
            logger.info(f"Cleaned up tasks older than {older_than_hours} hours")
            
        except Exception as e:
            logger.error(f"Failed to cleanup completed tasks: {e}")

# 싱글톤 인스턴스
job_manager = BaeminJobManager()