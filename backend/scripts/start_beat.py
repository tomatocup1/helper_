#!/usr/bin/env python3
"""
Celery Beat (스케줄러) 시작 스크립트
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.async_jobs.celery_config import celery_app

# 주기적 작업 스케줄 설정
celery_app.conf.beat_schedule = {
    'cleanup-expired-tasks': {
        'task': 'cleanup_expired_tasks',
        'schedule': 3600.0,  # 1시간마다
    },
}

if __name__ == '__main__':
    # Celery Beat 시작
    celery_app.start([
        'beat',
        '--loglevel=info'
    ])