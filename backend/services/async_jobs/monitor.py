"""
작업 모니터링 유틸리티
"""

import json
import redis
from typing import Dict, List, Any
from datetime import datetime
from celery.events.state import State
from celery import events

from .celery_config import celery_app
from ..shared.config import settings
from ..shared.logger import get_logger

logger = get_logger(__name__)

class TaskMonitor:
    """작업 모니터링 클래스"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.celery_app = celery_app
        self.state = State()
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """워커 상태 조회"""
        try:
            # 활성 워커 조회
            active_workers = self.celery_app.control.inspect().active()
            stats = self.celery_app.control.inspect().stats()
            
            worker_info = {}
            if active_workers:
                for worker_name, tasks in active_workers.items():
                    worker_stats = stats.get(worker_name, {}) if stats else {}
                    worker_info[worker_name] = {
                        "active_tasks": len(tasks),
                        "tasks": tasks,
                        "stats": worker_stats
                    }
            
            return {
                "total_workers": len(worker_info),
                "workers": worker_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return {"error": str(e)}
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """큐 상태 조회"""
        try:
            # 큐별 대기 작업 수 조회
            queue_stats = {}
            
            # Redis에서 큐 길이 조회
            queues = ['baemin_crawler', 'progress_updates', 'default']
            for queue_name in queues:
                queue_key = f"celery:{queue_name}"
                queue_length = self.redis_client.llen(queue_key)
                queue_stats[queue_name] = {
                    "pending_tasks": queue_length,
                    "queue_key": queue_key
                }
            
            return {
                "queues": queue_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}
    
    def get_task_stats(self) -> Dict[str, Any]:
        """전체 작업 통계"""
        try:
            # Celery 결과 백엔드에서 통계 조회
            reserved_tasks = self.celery_app.control.inspect().reserved()
            scheduled_tasks = self.celery_app.control.inspect().scheduled()
            
            total_reserved = 0
            total_scheduled = 0
            
            if reserved_tasks:
                total_reserved = sum(len(tasks) for tasks in reserved_tasks.values())
            
            if scheduled_tasks:
                total_scheduled = sum(len(tasks) for tasks in scheduled_tasks.values())
            
            return {
                "reserved_tasks": total_reserved,
                "scheduled_tasks": total_scheduled,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get task stats: {e}")
            return {"error": str(e)}
    
    def get_recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 실패한 작업 조회"""
        try:
            # Redis에서 실패 작업 로그 조회
            failure_key = "celery:task_failures"
            recent_failures = self.redis_client.lrange(failure_key, 0, limit - 1)
            
            failures = []
            for failure_data in recent_failures:
                try:
                    failure_info = json.loads(failure_data)
                    failures.append(failure_info)
                except json.JSONDecodeError:
                    continue
            
            return failures
            
        except Exception as e:
            logger.error(f"Failed to get recent failures: {e}")
            return []
    
    def get_system_health(self) -> Dict[str, Any]:
        """시스템 건강성 체크"""
        try:
            # Redis 연결 체크
            redis_healthy = False
            try:
                self.redis_client.ping()
                redis_healthy = True
            except Exception:
                pass
            
            # Celery 워커 체크
            worker_stats = self.get_worker_stats()
            worker_healthy = len(worker_stats.get("workers", {})) > 0
            
            # 큐 상태 체크
            queue_stats = self.get_queue_stats()
            queues_healthy = "error" not in queue_stats
            
            overall_health = redis_healthy and worker_healthy and queues_healthy
            
            return {
                "overall_healthy": overall_health,
                "redis_healthy": redis_healthy,
                "workers_healthy": worker_healthy,
                "queues_healthy": queues_healthy,
                "worker_count": len(worker_stats.get("workers", {})),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check system health: {e}")
            return {
                "overall_healthy": False,
                "error": str(e)
            }
    
    def log_task_failure(self, task_id: str, error: str, user_id: str = None):
        """작업 실패 로그 기록"""
        try:
            failure_info = {
                "task_id": task_id,
                "error": error,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Redis에 실패 로그 저장 (최대 100개 유지)
            failure_key = "celery:task_failures"
            self.redis_client.lpush(failure_key, json.dumps(failure_info))
            self.redis_client.ltrim(failure_key, 0, 99)
            
        except Exception as e:
            logger.error(f"Failed to log task failure: {e}")

# 싱글톤 인스턴스
task_monitor = TaskMonitor()