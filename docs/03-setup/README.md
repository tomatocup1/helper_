# ⚙️ 설치 및 설정 가이드

Helper B 프로젝트의 설치와 환경 설정에 관한 모든 문서입니다.

## 📄 문서 목록

### 기본 설치
- **[설치 가이드](SETUP.md)**
  - 시스템 요구사항
  - 의존성 설치
  - 환경 변수 설정
  - 초기 실행 방법

### Supabase 설정
- **[Supabase 설정 가이드](SUPABASE_SETUP_GUIDE.md)**
  - Supabase 프로젝트 생성
  - 데이터베이스 연결
  - Auth 설정
  - Storage 설정

- **[Supabase 문제 해결](SUPABASE_FIX_GUIDE.md)**
  - 일반적인 오류 해결
  - 연결 문제
  - 권한 설정
  - 성능 최적화

### 포트 설정
- **[로컬 개발 환경 (4000)](README_LOCAL_4000.md)**
  - 포트 4000 사용 설정
  - 로컬 개발 환경 구성
  - 디버깅 설정

- **[통합 포트 설정](README_UNIFIED_PORT.md)**
  - 포트 통합 구성
  - 프록시 설정
  - 서비스 간 통신

## 🚀 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/helper-b.git

# 2. 의존성 설치
npm install
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 4. 데이터베이스 초기화
npm run db:migrate

# 5. 서버 실행
npm run dev
```

## ⚠️ 자주 발생하는 문제

1. **포트 충돌**: 3000, 4000, 8000 포트가 사용 중인지 확인
2. **Supabase 연결**: API 키와 URL이 올바른지 확인
3. **Python 버전**: Python 3.11 이상 필요
4. **Node 버전**: Node.js 18 이상 필요

## 🔗 관련 문서
- [개발 가이드](../04-development/DEVELOPMENT_GUIDE.md)
- [시스템 아키텍처](../01-architecture/SYSTEM_ARCHITECTURE.md)
- [API 레퍼런스](../01-architecture/API_REFERENCE.md)