#!/usr/bin/env python3
"""
로컬 개발 환경에서 모든 서비스 실행
Redis + Celery Worker + Celery Beat 동시 실행
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from multiprocessing import Process

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def start_redis():
    """Redis 서버 시작"""
    try:
        print("Starting Redis server...")
        return subprocess.Popen([
            "redis-server", 
            "--port", "6379",
            "--save", "60", "1000"
        ])
    except FileNotFoundError:
        print("Redis not found. Please install Redis first.")
        print("Windows: scoop install redis")
        print("macOS: brew install redis")
        print("Ubuntu: sudo apt install redis-server")
        return None

def start_celery_worker():
    """Celery Worker 시작"""
    print("Starting Celery Worker...")
    
    # 환경변수 설정
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    return subprocess.Popen([
        sys.executable,
        str(project_root / "backend" / "scripts" / "start_worker.py")
    ], env=env)

def start_celery_beat():
    """Celery Beat 시작"""
    print("Starting Celery Beat...")
    
    # 환경변수 설정
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    return subprocess.Popen([
        sys.executable,
        str(project_root / "backend" / "scripts" / "start_beat.py")
    ], env=env)

def start_flower():
    """Flower (Celery 모니터링) 시작"""
    print("Starting Flower monitoring...")
    
    # 환경변수 설정
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    return subprocess.Popen([
        "celery", 
        "-A", "backend.services.async_jobs.celery_config",
        "flower",
        "--port=5555"
    ], env=env)

def main():
    """메인 실행 함수"""
    processes = []
    
    try:
        # Redis 시작
        redis_proc = start_redis()
        if redis_proc:
            processes.append(("Redis", redis_proc))
            time.sleep(2)  # Redis 시작 대기
        
        # Celery Worker 시작
        worker_proc = start_celery_worker()
        if worker_proc:
            processes.append(("Celery Worker", worker_proc))
            time.sleep(1)
        
        # Celery Beat 시작
        beat_proc = start_celery_beat()
        if beat_proc:
            processes.append(("Celery Beat", beat_proc))
            time.sleep(1)
        
        # Flower 시작 (선택사항)
        flower_proc = start_flower()
        if flower_proc:
            processes.append(("Flower", flower_proc))
        
        print("\n=== All services started ===")
        print("Celery Worker: Running")
        print("Celery Beat: Running") 
        print("Flower UI: http://localhost:5555")
        print("Redis: localhost:6379")
        print("\nPress Ctrl+C to stop all services")
        
        # 프로세스 모니터링
        while True:
            time.sleep(1)
            # 프로세스 상태 확인
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"Warning: {name} process terminated")
    
    except KeyboardInterrupt:
        print("\nShutting down services...")
        
        # 모든 프로세스 종료
        for name, proc in processes:
            try:
                print(f"Stopping {name}...")
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"Force killing {name}...")
                proc.kill()
            except Exception as e:
                print(f"Error stopping {name}: {e}")
        
        print("All services stopped.")

if __name__ == "__main__":
    main()