"""
Celery 설정 및 초기화
"""

import os
from celery import Celery
from ..shared.config import settings

# Celery 앱 초기화
celery_app = Celery(
    'baemin_crawler',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['backend.services.async_jobs.tasks']
)

# Celery 설정
celery_app.conf.update(
    # 작업 결과 설정
    result_expires=3600,  # 1시간
    result_serializer='json',
    task_serializer='json',
    accept_content=['json'],
    
    # 작업자 설정
    worker_concurrency=2,  # 동시 작업 수
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # 작업 라우팅
    task_routes={
        'backend.services.async_jobs.tasks.crawl_baemin_stores': {'queue': 'baemin_crawler'},
        'backend.services.async_jobs.tasks.update_crawl_progress': {'queue': 'progress_updates'},
    },
    
    # 재시도 설정
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # 타임존 설정
    timezone='Asia/Seoul',
    enable_utc=True,
    
    # 모니터링
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# 큐 정의
celery_app.conf.task_default_queue = 'default'
celery_app.conf.task_queues = {
    'baemin_crawler': {
        'exchange': 'baemin_crawler',
        'routing_key': 'baemin_crawler',
    },
    'progress_updates': {
        'exchange': 'progress_updates', 
        'routing_key': 'progress_updates',
    }
}

if __name__ == '__main__':
    celery_app.start()