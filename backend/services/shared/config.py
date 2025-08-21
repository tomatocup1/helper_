"""
공통 설정 파일
"""

import os
from pathlib import Path

# .env 파일 로드
def load_env():
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

class Settings:
    """애플리케이션 설정"""
    
    # 기본 디렉토리
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    
    # Supabase 설정
    SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Redis 설정
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # 브라우저 설정
    HEADLESS_BROWSER = False  # 개발 모드로 headless 비활성화
    
    # 보안 설정
    SAVE_CREDENTIALS_TO_DB = os.getenv("SAVE_CREDENTIALS_TO_DB", "false").lower() == "true"
    
    # 크롤링 설정
    DEFAULT_TIMEOUT = int(os.getenv("CRAWLING_TIMEOUT", "60"))
    MAX_CONCURRENT_CRAWLS = int(os.getenv("MAX_CONCURRENT_CRAWLS", "5"))
    
    # 로깅 설정
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", str(DATA_DIR / "logs" / "baemin_service.log"))
    
    # Celery 설정
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    CELERY_TASK_SERIALIZER = os.getenv("CELERY_TASK_SERIALIZER", "json")
    CELERY_RESULT_SERIALIZER = os.getenv("CELERY_RESULT_SERIALIZER", "json")

settings = Settings()