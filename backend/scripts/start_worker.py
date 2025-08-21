#!/usr/bin/env python3
"""
Celery 워커 시작 스크립트
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.async_jobs.celery_config import celery_app

if __name__ == '__main__':
    # Celery 워커 시작
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--queues=baemin_crawler,progress_updates,default'
    ])