# 통합 포트 설정 가이드 (localhost:4000)

## 개요
모든 서비스를 `localhost:4000` 하나의 포트를 통해 접근할 수 있도록 Nginx 리버스 프록시를 설정했습니다.

## 서비스 접근 URL

### 메인 서비스
- **메인 애플리케이션**: http://localhost:4000/
- **관리자 대시보드**: http://localhost:4000/admin

### API 서비스
- **API 서버**: http://localhost:4000/api
- **크롤러 서버**: http://localhost:4000/crawler
- **스케줄러 서버**: http://localhost:4000/scheduler

### 모니터링 도구 (선택사항)
- **Flower (Celery 모니터링)**: http://localhost:4000/flower/
- **Redis Commander**: http://localhost:4000/redis-commander/

### 데이터베이스 (직접 접근)
- **PostgreSQL**: localhost:5432 (직접 접근 필요 시)
- **Redis**: localhost:6379 (직접 접근 필요 시)

## 시작 방법

### 1. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 열어 필요한 환경 변수 설정
```

### 2. Docker Compose 실행

#### 기본 서비스만 실행
```bash
docker-compose up -d
```

#### 모니터링 도구 포함 실행
```bash
docker-compose --profile monitoring up -d
```

### 3. 서비스 확인
```bash
# 모든 컨테이너 상태 확인
docker-compose ps

# Nginx 로그 확인
docker-compose logs -f nginx

# 헬스체크
curl http://localhost:4000/health
```

## 개발 시 주의사항

### Frontend 환경 변수 업데이트
Frontend 애플리케이션에서 API를 호출할 때 다음과 같이 설정:

```javascript
// 기존 (여러 포트 사용)
const API_URL = 'http://localhost:8000';

// 변경 후 (통합 포트 사용)
const API_URL = 'http://localhost:4000/api';
```

### API 엔드포인트 경로
- API 서버: `/api`로 시작
- 크롤러 서버: `/crawler`로 시작
- 스케줄러 서버: `/scheduler`로 시작

## 트러블슈팅

### 포트 충돌 발생 시
```bash
# 포트 4000 사용 중인 프로세스 확인
netstat -ano | findstr :4000

# Docker 재시작
docker-compose down
docker-compose up -d
```

### Nginx 설정 변경 시
```bash
# nginx.conf 수정 후
docker-compose restart nginx
```

### 서비스별 로그 확인
```bash
# 특정 서비스 로그
docker-compose logs -f [service-name]

# 예시
docker-compose logs -f frontend
docker-compose logs -f api-server
docker-compose logs -f nginx
```

## 아키텍처 다이어그램

```
                          ┌─────────────────────────┐
                          │   localhost:4000        │
                          │       (Nginx)           │
                          └───────────┬─────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
   ┌─────────┐                  ┌─────────┐                  ┌─────────┐
   │/        │                  │/api     │                  │/admin   │
   │Frontend │                  │API      │                  │Admin    │
   │:3000    │                  │:8000    │                  │:3001    │
   └─────────┘                  └─────────┘                  └─────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
              ┌─────────┐       ┌─────────┐       ┌─────────┐
              │/crawler │       │/scheduler│       │/flower  │
              │:8001    │       │:8002    │       │:5555    │
              └─────────┘       └─────────┘       └─────────┘
```

## 보안 고려사항

1. **내부 서비스 격리**: 개별 서비스 포트는 외부에 노출되지 않고 Nginx를 통해서만 접근 가능
2. **프록시 헤더**: 실제 클라이언트 IP 및 프로토콜 정보 전달
3. **헬스체크**: 각 서비스 상태 모니터링
4. **로깅**: 중앙화된 접근 로그 관리

## 배포 환경 설정

프로덕션 환경에서는 다음 사항을 추가로 고려:

1. **SSL/TLS 설정**: Let's Encrypt를 통한 HTTPS 설정
2. **레이트 리미팅**: DDoS 공격 방지
3. **캐싱**: 정적 파일 캐싱 설정
4. **로드 밸런싱**: 서비스 인스턴스 확장 시 로드 밸런싱 설정