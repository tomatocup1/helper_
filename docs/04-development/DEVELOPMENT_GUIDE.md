# 🛠️ 개발 가이드

## 📋 개요

우리가게 도우미 프로젝트의 개발 환경 설정부터 배포까지의 전체 개발 워크플로우를 안내합니다.

## 🚀 빠른 시작

### 필수 요구사항

| 도구 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.11+ | 백엔드 개발 |
| **Node.js** | 18+ | 프론트엔드 개발 |
| **Docker** | 20.0+ | 컨테이너 환경 |
| **Git** | 2.30+ | 버전 관리 |
| **PostgreSQL** | 14+ | 데이터베이스 (로컬 개발 시) |

### 1단계: 프로젝트 클론
```bash
git clone https://github.com/your-org/store-helper.git
cd store-helper
```

### 2단계: 환경 설정
```bash
# 환경 변수 파일 생성
cp .env.example .env

# 개발 환경 설정 스크립트 실행
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 3단계: Docker 환경 실행
```bash
# 전체 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f server-b
```

### 4단계: 개발 서버 접속
- **API 문서**: http://localhost:8000/docs
- **프론트엔드**: http://localhost:3000
- **관리자 대시보드**: http://localhost:3001

## 🏗️ 백엔드 개발 (Server B)

### 개발 환경 설정

#### Python 가상환경 설정
```bash
cd backend/server-b

# pyenv를 사용하는 경우
pyenv install 3.11.5
pyenv local 3.11.5

# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Linux/Mac)
source venv/bin/activate

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

#### 환경 변수 설정
```bash
# backend/server-b/.env
DEBUG=True
LOG_LEVEL=INFO

# Supabase 설정
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# 데이터베이스 설정
SUPABASE_DB_HOST=localhost
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your_password

# JWT 설정
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# OpenAI 설정
OPENAI_API_KEY=your_openai_api_key

# Redis 설정
REDIS_URL=redis://localhost:6379/0

# CORS 설정
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
```

#### 개발 서버 실행
```bash
# 데이터베이스 초기화
python app/scripts/init_db.py

# 개발 서버 시작
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 또는 Python 스크립트로 실행
python app/main.py
```

### 코드 구조

```
backend/server-b/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 애플리케이션 진입점
│   ├── config.py            # 설정 관리
│   ├── api/                 # API 엔드포인트
│   │   ├── __init__.py
│   │   ├── auth.py          # 인증 API
│   │   ├── users.py         # 사용자 관리 API
│   │   ├── stores.py        # 매장 관리 API
│   │   ├── reviews.py       # 리뷰 관리 API
│   │   ├── analytics.py     # 분석 API
│   │   ├── payments.py      # 결제 API
│   │   └── health.py        # 헬스체크 API
│   ├── models/              # 데이터베이스 모델
│   │   ├── __init__.py
│   │   ├── base.py          # 기본 모델 클래스
│   │   ├── user.py          # 사용자 모델
│   │   ├── store.py         # 매장 모델
│   │   ├── review.py        # 리뷰 모델
│   │   └── ...
│   ├── middleware/          # 미들웨어
│   │   ├── __init__.py
│   │   ├── logging.py       # 로깅 미들웨어
│   │   └── rate_limit.py    # 속도 제한 미들웨어
│   ├── utils/               # 유틸리티
│   │   ├── __init__.py
│   │   └── database.py      # 데이터베이스 유틸리티
│   └── scripts/             # 관리 스크립트
│       └── init_db.py       # 데이터베이스 초기화
├── tests/                   # 테스트 코드
├── requirements.txt         # Python 의존성
└── Dockerfile              # Docker 설정
```

### API 개발 가이드

#### 1. 새 API 엔드포인트 추가
```python
# app/api/example.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.utils.database import get_db

router = APIRouter()

class ExampleRequest(BaseModel):
    name: str
    description: str

class ExampleResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime

@router.post("/", response_model=ExampleResponse)
async def create_example(
    request: ExampleRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """새 예제 생성"""
    # 비즈니스 로직 구현
    return ExampleResponse(...)
```

#### 2. 메인 앱에 라우터 등록
```python
# app/main.py
from app.api import example

app.include_router(
    example.router,
    prefix="/api/v1/examples",
    tags=["Examples"]
)
```

#### 3. 데이터베이스 모델 추가
```python
# app/models/example.py
from sqlalchemy import Column, String, DateTime, Text
from .base import Base

class Example(Base):
    __tablename__ = "examples"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
```

### 테스트 작성

#### 단위 테스트
```python
# tests/test_api_example.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_example():
    response = client.post(
        "/api/v1/examples/",
        json={"name": "Test Example", "description": "Test description"},
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Example"

@pytest.mark.asyncio
async def test_database_operations():
    # 데이터베이스 테스트 코드
    pass
```

#### 테스트 실행
```bash
# 전체 테스트 실행
pytest

# 특정 테스트 파일 실행
pytest tests/test_api_example.py

# 커버리지 포함 실행
pytest --cov=app tests/

# 테스트 병렬 실행
pytest -n auto
```

## 🎨 프론트엔드 개발

### 개발 환경 설정

#### Node.js 환경 설정
```bash
cd frontend

# Node.js 버전 확인
node --version  # v18.0.0 이상

# 의존성 설치
npm install

# 개발 서버 시작
npm run dev
```

#### 환경 변수 설정
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_ENV=development
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
```

### 프로젝트 구조 (예정)
```
frontend/
├── src/
│   ├── app/                 # Next.js 13+ App Router
│   │   ├── layout.tsx       # 루트 레이아웃
│   │   ├── page.tsx         # 홈 페이지
│   │   ├── login/           # 로그인 페이지
│   │   ├── dashboard/       # 대시보드
│   │   └── stores/          # 매장 관리
│   ├── components/          # 재사용 가능한 컴포넌트
│   │   ├── ui/              # shadcn/ui 컴포넌트
│   │   ├── forms/           # 폼 컴포넌트
│   │   └── charts/          # 차트 컴포넌트
│   ├── lib/                 # 유틸리티 및 설정
│   │   ├── api.ts           # API 클라이언트
│   │   ├── auth.ts          # 인증 설정
│   │   └── utils.ts         # 공통 유틸리티
│   ├── hooks/               # 커스텀 훅
│   ├── stores/              # 상태 관리 (Zustand)
│   └── types/               # TypeScript 타입 정의
├── public/                  # 정적 파일
├── package.json
├── tailwind.config.js       # Tailwind CSS 설정
├── next.config.js           # Next.js 설정
└── tsconfig.json           # TypeScript 설정
```

## 🔧 개발 도구 및 워크플로우

### 코드 품질 도구

#### Python (백엔드)
```bash
# 코드 포맷팅
black app/
isort app/

# 린팅
flake8 app/
pylint app/

# 타입 체킹
mypy app/

# 보안 검사
bandit -r app/
```

#### TypeScript (프론트엔드)
```bash
# 코드 포맷팅
npm run format

# 린팅
npm run lint

# 타입 체킹
npm run type-check

# 빌드
npm run build
```

### Git 워크플로우

#### 브랜치 전략
```
main           # 프로덕션 릴리즈
├── develop    # 개발 통합 브랜치
├── feature/*  # 기능 개발 브랜치
├── hotfix/*   # 긴급 수정 브랜치
└── release/*  # 릴리즈 준비 브랜치
```

#### 커밋 메시지 규칙
```
<type>(<scope>): <subject>

<body>

<footer>
```

**타입:**
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 수정
- `style`: 코드 포맷팅
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드 설정 등

**예시:**
```
feat(api): add review sentiment analysis endpoint

- Add POST /api/v1/reviews/{id}/analyze endpoint
- Integrate OpenAI GPT-4 for sentiment analysis
- Add sentiment score calculation logic

Closes #123
```

### IDE 설정

#### VS Code 설정
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./backend/server-b/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "typescript.preferences.importModuleSpecifier": "relative",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

#### 권장 VS Code 확장
```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode-remote.remote-containers"
  ]
}
```

## 🧪 테스트 전략

### 테스트 피라미드

```
    /\
   /  \     E2E Tests (5%)
  /____\    
 /      \   Integration Tests (15%)
/__________\ Unit Tests (80%)
```

### 백엔드 테스트

#### 테스트 환경 설정
```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from app.main import app

@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def authenticated_client(client):
    # 인증된 클라이언트 설정
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

#### API 테스트
```python
# tests/test_stores_api.py
@pytest.mark.asyncio
async def test_create_store(authenticated_client):
    store_data = {
        "name": "테스트 카페",
        "platform": "naver",
        "platform_store_id": "12345",
        "address": "서울시 강남구",
        "category": "카페"
    }
    
    response = await authenticated_client.post("/api/v1/stores/", json=store_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "테스트 카페"
    assert data["status"] == "pending"
```

### 프론트엔드 테스트 (예정)

#### 컴포넌트 테스트
```typescript
// __tests__/components/StoreCard.test.tsx
import { render, screen } from '@testing-library/react';
import StoreCard from '@/components/StoreCard';

const mockStore = {
  id: '1',
  name: '테스트 카페',
  platform: 'naver',
  status: 'active',
  stats: { total_reviews: 50, average_rating: 4.5 }
};

test('renders store information correctly', () => {
  render(<StoreCard store={mockStore} />);
  
  expect(screen.getByText('테스트 카페')).toBeInTheDocument();
  expect(screen.getByText('50개 리뷰')).toBeInTheDocument();
  expect(screen.getByText('4.5')).toBeInTheDocument();
});
```

#### E2E 테스트
```typescript
// e2e/store-management.spec.ts
import { test, expect } from '@playwright/test';

test('store creation flow', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="password"]', 'testpassword');
  await page.click('[type="submit"]');
  
  await page.goto('/stores/new');
  await page.fill('[name="name"]', '새로운 카페');
  await page.selectOption('[name="platform"]', 'naver');
  await page.fill('[name="platform_store_id"]', '67890');
  await page.click('[type="submit"]');
  
  await expect(page.locator('.success-message')).toBeVisible();
});
```

## 🐳 Docker 개발 환경

### Docker Compose 설정
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  server-b:
    build:
      context: ./backend/server-b
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend/server-b:/app
      - /app/venv  # 가상환경 제외
    environment:
      - DEBUG=True
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/storehelper_dev
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: storehelper_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 개발용 Dockerfile
```dockerfile
# backend/server-b/Dockerfile.dev
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 개발용 의존성 추가 설치
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8

# 소스 코드 복사 (개발 시에는 볼륨 마운트)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

## 🔍 디버깅 가이드

### 백엔드 디버깅

#### 로깅 설정
```python
# app/main.py
import logging

# 개발 환경에서 상세 로깅
if settings.DEBUG:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug.log')
        ]
    )
```

#### 디버거 사용
```python
# 중단점 설정
import pdb; pdb.set_trace()

# 또는 더 나은 디버거
import ipdb; ipdb.set_trace()

# VS Code 디버깅 설정
# .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "program": "app/main.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/backend/server-b"
    }
  ]
}
```

#### 데이터베이스 디버깅
```python
# SQL 쿼리 로깅
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# 슬로우 쿼리 모니터링
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.1:  # 100ms 이상 쿼리 로깅
        logger.warning(f"Slow query: {total:.2f}s - {statement[:100]}")
```

## 📊 성능 최적화

### 백엔드 최적화

#### 데이터베이스 최적화
```python
# 연결 풀 설정
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True
)

# 쿼리 최적화
from sqlalchemy.orm import selectinload, joinedload

# N+1 문제 해결
async def get_stores_with_reviews(db: AsyncSession):
    result = await db.execute(
        select(Store)
        .options(selectinload(Store.reviews))
        .where(Store.is_active == True)
    )
    return result.scalars().all()
```

#### 캐싱 전략
```python
# Redis 캐싱
import redis.asyncio as redis
from functools import wraps

redis_client = redis.Redis.from_url("redis://localhost:6379/0")

def cache_result(expiration: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 캐시에서 조회
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # 함수 실행 및 캐시 저장
            result = await func(*args, **kwargs)
            await redis_client.setex(
                cache_key, 
                expiration, 
                json.dumps(result, default=str)
            )
            return result
        return wrapper
    return decorator

# 사용 예시
@cache_result(expiration=1800)  # 30분 캐싱
async def get_store_stats(store_id: str):
    # 복잡한 통계 계산
    pass
```

## 🚀 배포 준비

### 프로덕션 빌드

#### 백엔드 프로덕션 설정
```python
# app/config.py
class ProductionSettings(Settings):
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    
    # 보안 설정
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    ALLOWED_HOSTS: List[str] = ["api.storehelper.com"]
    
    # 성능 설정
    DATABASE_POOL_SIZE: int = 50
    DATABASE_MAX_OVERFLOW: int = 100
```

#### 프론트엔드 프로덕션 빌드
```bash
# 타입 체크
npm run type-check

# 린트 검사
npm run lint

# 프로덕션 빌드
npm run build

# 빌드 결과 확인
npm run start
```

### 보안 체크리스트

#### 백엔드 보안
- [ ] 환경 변수로 민감 정보 관리
- [ ] HTTPS 강제 사용
- [ ] CORS 설정 적절히 구성
- [ ] SQL Injection 방지 (SQLAlchemy ORM 사용)
- [ ] Rate Limiting 적용
- [ ] 입력값 검증 (Pydantic)
- [ ] JWT 토큰 만료 시간 설정
- [ ] 에러 메시지에서 민감 정보 노출 방지

#### 프론트엔드 보안
- [ ] XSS 방지 (React 기본 보호 + 추가 검증)
- [ ] CSRF 토큰 사용
- [ ] Content Security Policy 설정
- [ ] 민감한 정보 브라우저 저장소에 저장 금지
- [ ] API 키 환경 변수 관리

---

*배포 관련 상세 내용은 [배포 가이드](DEPLOYMENT.md)를 참조하세요.*