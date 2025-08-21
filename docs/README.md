# 📚 Helper B 프로젝트 문서 센터

## 🎯 빠른 시작
프로젝트를 처음 시작하시나요? 아래 문서들을 순서대로 확인하세요:

1. **[프로젝트 개요](02-progress/PROJECT_OVERVIEW.md)** - 프로젝트 전체 이해
2. **[시스템 아키텍처](01-architecture/SYSTEM_ARCHITECTURE.md)** - 기술 스택 및 구조
3. **[설치 가이드](03-setup/SETUP.md)** - 프로젝트 설치 및 실행
4. **[개발 가이드](04-development/DEVELOPMENT_GUIDE.md)** - 개발 시작하기

## 📂 문서 구조

### 01. 🏗️ [아키텍처](01-architecture/)
시스템 설계와 기술 구조 관련 문서
- **[시스템 아키텍처](01-architecture/SYSTEM_ARCHITECTURE.md)** - 전체 시스템 구조 및 서버 아키텍처
- **[데이터베이스 설계](01-architecture/DATABASE_DESIGN.md)** - 데이터베이스 스키마 및 관계
- **[API 레퍼런스](01-architecture/API_REFERENCE.md)** - API 엔드포인트 및 사용법

### 02. 📊 [진행 상황](02-progress/)
프로젝트 진행 현황 및 로드맵
- **[진행 상황 대시보드](02-progress/PROGRESS_STATUS.md)** - 실시간 개발 진행률
- **[프로젝트 개요](02-progress/PROJECT_OVERVIEW.md)** - 프로젝트 목표 및 범위

### 03. ⚙️ [설치 및 설정](03-setup/)
프로젝트 설치 및 환경 설정 가이드
- **[기본 설치 가이드](03-setup/SETUP.md)** - 프로젝트 초기 설정
- **[Supabase 설정 가이드](03-setup/SUPABASE_SETUP_GUIDE.md)** - Supabase 연동 설정
- **[Supabase 문제 해결](03-setup/SUPABASE_FIX_GUIDE.md)** - Supabase 관련 이슈 해결
- **[로컬 개발 환경 (4000)](03-setup/README_LOCAL_4000.md)** - 포트 4000 로컬 설정
- **[통합 포트 설정](03-setup/README_UNIFIED_PORT.md)** - 포트 통합 구성

### 04. 💻 [개발](04-development/)
개발 가이드 및 베스트 프랙티스
- **[개발 가이드](04-development/DEVELOPMENT_GUIDE.md)** - 코딩 규칙 및 워크플로우
- **[레거시 통합](04-development/LEGACY_INTEGRATION.md)** - 기존 코드 마이그레이션

### 05. 🔧 [백엔드](05-backend/)
백엔드 서버 및 API 관련 문서
- **[API 통합 가이드](05-backend/api_integration_guide.md)** - API 통합 방법
- **[비동기 작업 가이드](05-backend/async_jobs_guide.md)** - Celery 및 큐 시스템
- **[네이버 통계](05-backend/README_naver_statistics.md)** - 네이버 통계 시스템
- **[네이버 답글 시스템](05-backend/naver_reply_system/)** - 네이버 자동 답글 시스템
  - [시스템 요약](05-backend/naver_reply_system/NAVER_REPLY_SYSTEM_SUMMARY.md)
  - [답글 포스팅](05-backend/naver_reply_system/README_reply_posting.md)
  - [통계 수집](05-backend/naver_reply_system/README_statistics.md)

### 06. 🎨 [프론트엔드](06-frontend/)
프론트엔드 개발 및 UI/UX 관련 문서
- **[성능 디버깅](06-frontend/PERFORMANCE_DEBUG.md)** - 프론트엔드 성능 최적화
- **[복구 가이드](06-frontend/RECOVERY-INSTRUCTIONS.md)** - 오류 복구 절차
- **[Supabase 연동 수정](06-frontend/README_SUPABASE_FIX.md)** - 프론트엔드 Supabase 이슈

### 07. 📦 [레거시](07-legacy/)
이전 버전 및 아카이브 문서

## 📊 프로젝트 현황 (2024년 8월 기준)

| 구성요소 | 진행률 | 상태 |
|---------|--------|------|
| 🗄️ **데이터베이스 설계** | 100% | ✅ 완료 |
| 🔌 **API 서버 B** | 90% | 🔄 진행중 |
| 🤖 **크롤링 서버 A** | 0% | ⏳ 대기 |
| ⏰ **스케줄러 서버 C** | 0% | ⏳ 대기 |
| 🎨 **프론트엔드** | 0% | ⏳ 대기 |
| 🐳 **Docker 환경** | 50% | 🔄 진행중 |

---

## 🚀 주요 기능별 가이드

### 크롤링 시스템
- 배민, 쿠팡이츠, 요기요 크롤링
- [API 통합 가이드](05-backend/api_integration_guide.md)
- [비동기 작업 처리](05-backend/async_jobs_guide.md)

### AI 답글 시스템
- [네이버 답글 시스템 요약](05-backend/naver_reply_system/NAVER_REPLY_SYSTEM_SUMMARY.md)
- [답글 자동 포스팅](05-backend/naver_reply_system/README_reply_posting.md)

### 통계 및 분석
- [네이버 통계 수집](05-backend/naver_reply_system/README_statistics.md)
- [통계 시스템 개요](05-backend/README_naver_statistics.md)

### 인증 및 보안
- [Supabase Auth 설정](03-setup/SUPABASE_SETUP_GUIDE.md)
- [데이터베이스 보안](01-architecture/DATABASE_DESIGN.md#security)

---

## 🔍 문서 검색 팁

- **설치 문제**: [03-setup](03-setup/) 폴더 확인
- **API 관련**: [API 레퍼런스](01-architecture/API_REFERENCE.md) 및 [API 통합 가이드](05-backend/api_integration_guide.md)
- **버그 해결**: 각 섹션의 troubleshooting 또는 fix 관련 문서
- **성능 최적화**: [성능 디버깅](06-frontend/PERFORMANCE_DEBUG.md)

---

## 📝 문서 업데이트 정책

- 새로운 기능 추가 시 관련 문서 즉시 업데이트
- 진행 상황은 주 단위로 업데이트
- 아키텍처 변경 시 반드시 문서화

---

## 🤝 기여 가이드

문서 개선에 기여하고 싶으신가요?
1. 해당 카테고리 폴더에서 문서 수정
2. 링크가 올바른지 확인
3. 이 README.md 파일도 필요시 업데이트

---

*최종 업데이트: 2025년 8월 21일*