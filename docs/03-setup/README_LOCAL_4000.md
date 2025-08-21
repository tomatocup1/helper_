# 로컬 개발 환경 - Port 4000 통합 가이드

## 🎯 개요
Docker 없이 로컬에서 모든 서비스를 `localhost:4000` 하나의 포트로 접근할 수 있도록 설정합니다.

## 🏗️ 아키텍처

```
┌──────────────────────────────────────────┐
│         localhost:4000                    │
│     (Node.js Proxy Server)                │
└────────────┬─────────────────────────────┘
             │
    ┌────────┼────────┬────────┬──────────┐
    ▼        ▼        ▼        ▼          ▼
Frontend   API    Backend  Scheduler   Admin
 :3000    :3000    :8001     :8002     :3001
```

## 📦 설치 방법

### 1. 의존성 패키지 설치

```bash
# 루트 디렉토리에서
npm install

# Frontend 패키지 설치
cd frontend
npm install
cd ..

# Python 패키지 설치 (필요시)
cd backend
pip install -r requirements.txt
cd ..
```

### 2. FastAPI 설치 (Python Backend용)

```bash
pip install fastapi uvicorn
```

## 🚀 실행 방법

### Windows 사용자

```bash
# 대화형 스크립트 실행
start-local.bat
```

### Mac/Linux 사용자

```bash
# 실행 권한 부여
chmod +x start-local.sh

# 대화형 스크립트 실행
./start-local.sh
```

### 수동 실행 (각각 다른 터미널에서)

```bash
# 터미널 1: 프록시 서버
npm run proxy

# 터미널 2: Frontend
cd frontend
npm run dev

# 터미널 3: Python Backend (선택사항)
cd backend
python server.py
```

## 📍 접근 URL

모든 서비스는 `http://localhost:4000`을 통해 접근:

| 서비스 | URL | 설명 |
|--------|-----|------|
| 메인 앱 | http://localhost:4000/ | Next.js Frontend |
| API | http://localhost:4000/api | Next.js API Routes |
| 크롤러 | http://localhost:4000/crawler | Python Backend |
| 스케줄러 | http://localhost:4000/scheduler | Python Scheduler |
| 헬스체크 | http://localhost:4000/health | 프록시 상태 확인 |
| 프록시 상태 | http://localhost:4000/proxy-status | 라우팅 정보 |

## 🛠️ 개발 팁

### Hot Module Reload
- Frontend의 HMR(Hot Module Reload)이 자동으로 작동합니다
- 코드 수정 시 브라우저가 자동으로 새로고침됩니다

### 프록시 설정 수정
`proxy-server.js` 파일에서 라우팅 규칙을 수정할 수 있습니다:

```javascript
const services = {
  '/custom-path': {
    target: 'http://localhost:port',
    changeOrigin: true,
  }
};
```

### 환경 변수 설정
`.env.local` 파일에서 환경 변수를 설정:

```env
NEXT_PUBLIC_API_URL=http://localhost:4000/api
BACKEND_PORT=8001
```

## 🔧 트러블슈팅

### 포트 충돌 발생 시

```bash
# Windows - 포트 사용 확인
netstat -ano | findstr :4000

# Mac/Linux - 포트 사용 확인
lsof -i :4000

# 프로세스 종료 후 재시작
```

### 프록시 서버 오류

1. `node_modules` 삭제 후 재설치:
```bash
rm -rf node_modules
npm install
```

2. 프록시 서버 로그 확인:
```bash
npm run proxy:dev  # nodemon으로 실행 (자동 재시작)
```

### Frontend 연결 오류

Frontend의 API 호출 URL 확인:
```javascript
// 올바른 설정
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000/api';
```

## 📊 성능 최적화

### 개발 모드 최적화
- 프록시 서버는 매우 가볍고 빠릅니다 (~10MB 메모리)
- 모든 요청이 단일 포트를 통해 라우팅되어 CORS 문제가 없습니다
- WebSocket 지원으로 실시간 업데이트가 가능합니다

### 프로덕션 준비
프로덕션 환경에서는 Nginx나 Apache를 사용하는 것을 권장합니다.

## 🔐 보안 주의사항

- 이 설정은 **개발 환경**용입니다
- 프로덕션에서는 적절한 보안 설정이 필요합니다
- `.env.local` 파일은 git에 커밋하지 마세요

## 📝 추가 스크립트

`package.json`에 정의된 유용한 스크립트:

```bash
# 프록시 서버만 실행
npm run proxy

# 개발 모드로 프록시 실행 (자동 재시작)
npm run proxy:dev

# Frontend 실행
npm run dev:frontend

# 모든 서비스 동시 실행
npm run dev:all
```

## 🤝 기여

문제가 있거나 개선 사항이 있다면 이슈를 등록해주세요!