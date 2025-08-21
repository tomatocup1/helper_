# 비동기 작업 시스템 가이드

배민 크롤링을 위한 Celery 기반 비동기 작업 처리 시스템입니다.

## 시스템 구조

### 핵심 컴포넌트

1. **Celery App** (`celery_config.py`)
   - Redis 브로커/백엔드 사용
   - 큐별 작업 라우팅
   - 재시도 및 타임아웃 설정

2. **Task Definitions** (`tasks.py`)
   - `crawl_baemin_stores`: 배민 매장 크롤링 작업
   - `update_crawl_progress`: 진행상황 업데이트
   - `cleanup_expired_tasks`: 만료된 작업 정리

3. **Job Manager** (`job_manager.py`)
   - 작업 시작/취소/모니터링
   - Redis 기반 상태 관리
   - 사용자별 작업 히스토리

4. **Monitor** (`monitor.py`)
   - 워커/큐/작업 상태 모니터링
   - 시스템 건강성 체크
   - 실패 작업 추적

## 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Redis 설치

```bash
# Windows (Scoop)
scoop install redis

# macOS
brew install redis

# Ubuntu
sudo apt install redis-server
```

### 3. 환경변수 설정

```bash
# .env 파일
REDIS_URL=redis://localhost:6379
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
HEADLESS_BROWSER=true
LOG_LEVEL=INFO
```

## 실행 방법

### 로컬 개발 환경

**모든 서비스 한번에 실행:**
```bash
python backend/scripts/run_local.py
```

**개별 서비스 실행:**
```bash
# Redis 서버
redis-server

# Celery Worker
python backend/scripts/start_worker.py

# Celery Beat (스케줄러)
python backend/scripts/start_beat.py

# Flower (모니터링 UI)
celery -A backend.services.async_jobs.celery_config flower --port=5555
```

### Docker 환경

```bash
docker-compose -f docker-compose.async.yml up -d
```

## 사용 예제

### 크롤링 작업 시작

```python
from backend.services.async_jobs import job_manager

# 작업 시작
result = job_manager.start_crawling_job(
    user_id="user123",
    task_options={"timeout": 120}
)

if result["success"]:
    task_id = result["task_id"]
    print(f"작업 시작됨: {task_id}")
else:
    print(f"작업 시작 실패: {result['message']}")
```

### 작업 상태 조회

```python
# 작업 상태 확인
status = job_manager.get_task_status(task_id)
print(f"상태: {status['status']}")
print(f"진행률: {status.get('progress', 0)}%")

# 활성 작업 조회
active_task = job_manager.get_user_active_task("user123")
if active_task:
    print(f"진행 중인 작업: {active_task['task_id']}")
```

### 작업 취소

```python
# 작업 취소
cancel_result = job_manager.cancel_task(task_id, "user123")
if cancel_result["success"]:
    print("작업이 취소되었습니다")
```

### 시스템 모니터링

```python
from backend.services.async_jobs import task_monitor

# 워커 상태
worker_stats = task_monitor.get_worker_stats()
print(f"활성 워커: {worker_stats['total_workers']}개")

# 큐 상태
queue_stats = task_monitor.get_queue_stats()
for queue, info in queue_stats["queues"].items():
    print(f"{queue}: {info['pending_tasks']}개 대기")

# 시스템 건강성
health = task_monitor.get_system_health()
print(f"시스템 정상: {health['overall_healthy']}")
```

## 작업 흐름

### 크롤링 작업 생명주기

1. **시작** (`PENDING`)
   - 작업 큐에 추가
   - Redis에 작업 정보 저장

2. **진행** (`PROGRESS`)
   - 브라우저 시작 및 로그인
   - 매장 데이터 추출
   - 실시간 진행상황 업데이트

3. **완료** (`SUCCESS`) 또는 **실패** (`FAILURE`)
   - 결과 데이터베이스 저장
   - 최종 상태 업데이트
   - 리소스 정리

### 진행상황 콜백

```python
def progress_callback(progress_data):
    print(f"단계: {progress_data['step']}")
    print(f"메시지: {progress_data['message']}")
    print(f"진행률: {progress_data['progress']}%")

# 콜백과 함께 크롤링 실행
await crawler_service.crawl_stores(
    user_id="user123",
    progress_callback=progress_callback
)
```

## 모니터링 및 디버깅

### Flower UI 접근

브라우저에서 `http://localhost:5555` 접근하여:
- 실시간 작업 모니터링
- 워커 상태 확인
- 작업 히스토리 조회
- 실패한 작업 재시도

### 로그 확인

```bash
# 일반 로그
tail -f backend/data/logs/baemin_service.log

# Celery 워커 로그
celery -A backend.services.async_jobs.celery_config events
```

### Redis 데이터 확인

```bash
# Redis CLI 접속
redis-cli

# 작업 큐 확인
LLEN celery:baemin_crawler

# 진행상황 확인
GET progress:task-id-here

# 작업 정보 확인  
GET task_info:task-id-here
```

## 트러블슈팅

### 일반적인 문제

1. **Redis 연결 실패**
   ```bash
   # Redis 서버 상태 확인
   redis-cli ping
   # 응답: PONG (정상)
   ```

2. **워커가 작업을 처리하지 않음**
   ```bash
   # 워커 로그 확인
   celery -A backend.services.async_jobs.celery_config worker --loglevel=debug
   ```

3. **브라우저 시작 실패**
   ```bash
   # Playwright 브라우저 설치
   playwright install chromium
   ```

4. **메모리 부족**
   ```bash
   # 워커 동시 실행 수 조정
   celery -A backend.services.async_jobs.celery_config worker --concurrency=1
   ```

### 성능 최적화

1. **워커 수 조정**
   - CPU 코어 수에 맞춰 조정
   - 메모리 사용량 모니터링

2. **큐 분리**
   - 크롤링과 진행상황 업데이트 큐 분리
   - 우선순위 기반 작업 처리

3. **Redis 설정**
   - 메모리 최적화
   - 영속성 설정

## API 통합

프론트엔드와의 통합을 위한 API 엔드포인트는 별도 구현 예정:
- `POST /api/baemin/start-crawling`
- `GET /api/baemin/task-status/{task_id}`
- `DELETE /api/baemin/cancel-task/{task_id}`
- WebSocket을 통한 실시간 진행상황 업데이트