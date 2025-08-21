"""
공통 로거 설정
"""

import logging
import os
from pathlib import Path
from .config import settings

def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 생성"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        
        # 로그 디렉토리 생성
        log_dir = Path(settings.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 포매터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 파일 핸들러
        file_handler = logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger