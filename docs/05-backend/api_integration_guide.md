# API 통합 가이드

프론트엔드와 백엔드 API 통합 완료 가이드입니다.

## 🚀 시스템 아키텍처

```
프론트엔드 (Next.js)     →     프록시 서버     →     백엔드 API (FastAPI)
http://localhost:3000        http://localhost:4000        http://localhost:8001
                                     ↓
                              비동기 작업 시스템 (Celery + Redis)
```

## 📋 API 엔드포인트

### 배민 크롤링 API

**POST /crawler/api/baemin/crawl**
```json
{
  "platform_id": "user_login_id",
  "platform_password": "user_password", 
  "user_id": "test-user-123",
  "sync": true,
  "timeout": 120
}
```

**응답 (동기식):**
```json
{
  "success": true,
  "stores": [
    {
      "user_id": "test-user-123",
      "platform": "baemin", 
      "platform_store_id": "14522306",
      "store_name": "더클램스 & 화채꽃이야기",
      "business_type": "카페·디저트",
      "sub_type": "[음식배달]",
      "is_active": true,
      "crawling_enabled": true,
      "auto_reply_enabled": false
    }
  ],
  "message": "크롤링 완료! 1개 매장 발견"
}
```

### 작업 상태 조회

**GET /crawler/api/baemin/task/{task_id}**
```json
{
  "task_id": "abc123",
  "status": "SUCCESS",
  "progress": 100,
  "result": {...},
  "error": null
}
```

### 시스템 모니터링

**GET /crawler/api/system/health**
```json
{
  "health": {
    "overall_healthy": true,
    "redis_healthy": true,
    "workers_healthy": true,
    "worker_count": 1
  },
  "workers": {...},
  "queues": {...}
}
```

## 🔧 서비스 실행

### 자동 실행 (권장)

**Windows:**
```bash
scripts/start_all.bat
```

**Linux/macOS:**
```bash
scripts/start_all.sh
```

### 수동 실행

**1. Redis 서버**
```bash
redis-server --port 6379
```

**2. Celery Worker**
```bash
cd backend
python scripts/start_worker.py
```

**3. FastAPI 백엔드**
```bash
cd backend/api
python app.py
```

**4. Next.js 프론트엔드**
```bash
cd frontend
npm run dev
```

**5. 프록시 서버**
```bash
node proxy-server.js
```

## 🔍 프론트엔드 통합 상태

### 기존 UI (완료 ✅)
- `/stores/add` 페이지: 플랫폼 선택 및 매장 등록 UI
- 3단계 위저드: 플랫폼 선택 → 계정 연결 → 매장 수집
- 실시간 진행상황 표시
- 매장 선택 및 일괄 등록

### API 통합 (완료 ✅)
- `/api/v1/platform/connect` 엔드포인트
- 배민 크롤러 실제 연동 구현
- 백엔드 fallback 처리
- 에러 핸들링 및 사용자 피드백

## 📊 데이터 흐름

### 배민 매장 등록 프로세스

1. **사용자 입력**: 프론트엔드에서 배민 계정 정보 입력
2. **API 호출**: `/api/v1/platform/connect`에서 백엔드 크롤링 API 호출
3. **인증 정보 저장**: Redis에 암호화되어 저장
4. **크롤링 실행**: Playwright로 배민 사이트 크롤링
5. **데이터 파싱**: 매장 정보 추출 및 정제
6. **응답 반환**: 프론트엔드로 매장 목록 전달
7. **매장 등록**: 사용자가 선택한 매장을 DB에 저장

## 🛠️ 개발 & 디버깅

### 로그 확인

**백엔드 API 로그:**
```bash
tail -f backend/data/logs/baemin_service.log
```

**Celery Worker 로그:**
```bash
celery -A backend.services.async_jobs.celery_config events
```

### API 테스트

**curl 예제:**
```bash
curl -X POST http://localhost:4000/crawler/api/baemin/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "platform_id": "test_id",
    "platform_password": "test_password",
    "user_id": "test-user-123",
    "sync": true
  }'
```

**Postman Collection:**
- Base URL: `http://localhost:4000/crawler`
- Headers: `Content-Type: application/json`

### Flower 모니터링

브라우저에서 접속: `http://localhost:5555`
- 실시간 작업 모니터링
- 워커 상태 확인
- 실패한 작업 재시도

## 🚨 트러블슈팅

### 일반적인 문제

**1. 백엔드 연결 실패**
```
해결: Redis 서버가 실행 중인지 확인
redis-cli ping  # 응답: PONG
```

**2. 크롤링 실패**
```
해결: Playwright 브라우저 설치
playwright install chromium
```

**3. 프록시 오류**
```
해결: 포트 충돌 확인
netstat -ano | findstr :4000
```

**4. 인증 정보 저장 실패**
```
해결: Supabase 환경변수 확인
echo $NEXT_PUBLIC_SUPABASE_URL
echo $SUPABASE_SERVICE_KEY
```

### 성능 최적화

**1. Celery Worker 수 조정**
```python
# celery_config.py
worker_concurrency=4  # CPU 코어 수에 맞춰 조정
```

**2. Redis 메모리 최적화**
```bash
redis-cli config set maxmemory 256mb
redis-cli config set maxmemory-policy allkeys-lru
```

**3. 크롤링 타임아웃 조정**
```python
# 환경변수로 설정
CRAWLING_TIMEOUT=180  # 3분
```

## 🎯 다음 단계

1. **WebSocket 실시간 업데이트**: 크롤링 진행상황 실시간 전송
2. **배치 크롤링**: 여러 사용자 동시 크롤링
3. **스케줄링**: 정기적 매장 정보 업데이트
4. **모니터링 대시보드**: 시스템 상태 실시간 모니터링
5. **에러 알림**: 실패한 작업 자동 알림

## 📝 API 명세서

Swagger UI: `http://localhost:8001/docs`
ReDoc: `http://localhost:8001/redoc`