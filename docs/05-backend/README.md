# 🔧 백엔드 문서

Helper B 프로젝트의 백엔드 서버 및 API 관련 모든 문서입니다.

## 📄 문서 목록

### API 및 통합
- **[API 통합 가이드](api_integration_guide.md)**
  - REST API 설계 원칙
  - 엔드포인트 구조
  - 인증 및 권한
  - 에러 처리

- **[비동기 작업 가이드](async_jobs_guide.md)**
  - Celery 설정 및 사용
  - Redis 큐 시스템
  - 작업 스케줄링
  - 모니터링

### 네이버 관련 시스템
- **[네이버 통계 시스템](README_naver_statistics.md)**
  - 통계 수집 방법
  - 데이터 처리 파이프라인
  - 분석 알고리즘

- **[네이버 답글 시스템](naver_reply_system/)**
  - [시스템 요약](naver_reply_system/NAVER_REPLY_SYSTEM_SUMMARY.md)
  - [답글 포스팅](naver_reply_system/README_reply_posting.md)
  - [통계 수집](naver_reply_system/README_statistics.md)

### 기타 문서
- **[백엔드 원본 README](backend_original_README.md)**
  - 백엔드 초기 설정 정보
  - 레거시 참조 문서

## 🏗️ 백엔드 아키텍처

### 서버 구성
- **API 서버 (포트 8000)**: FastAPI 기반 REST API
- **크롤링 서버**: Playwright 기반 웹 크롤링
- **AI 서버**: OpenAI GPT 연동

### 주요 기술 스택
```yaml
언어: Python 3.11+
프레임워크: FastAPI
ORM: SQLAlchemy
데이터베이스: PostgreSQL (Supabase)
캐시: Redis
큐: Celery + RabbitMQ
크롤링: Playwright
AI: OpenAI API
```

## 📦 주요 모듈

### `/api` - API 엔드포인트
- 사용자 인증
- 매장 관리
- 리뷰 관리
- 통계 분석

### `/services` - 비즈니스 로직
- 크롤링 서비스
- AI 답글 생성
- 데이터 분석
- 알림 서비스

### `/core` - 핵심 기능
- 데이터베이스 연결
- 보안 설정
- 미들웨어
- 유틸리티

## 🔐 보안

- JWT 토큰 기반 인증
- Rate limiting
- CORS 설정
- SQL Injection 방어
- XSS 방어

## 🧪 테스트

```bash
# 단위 테스트
pytest tests/unit/

# 통합 테스트
pytest tests/integration/

# 커버리지 확인
pytest --cov=app tests/
```

## 🔗 관련 문서
- [시스템 아키텍처](../01-architecture/SYSTEM_ARCHITECTURE.md)
- [API 레퍼런스](../01-architecture/API_REFERENCE.md)
- [데이터베이스 설계](../01-architecture/DATABASE_DESIGN.md)