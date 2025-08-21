# 🎨 프론트엔드 문서

Helper B 프로젝트의 프론트엔드 개발 및 UI/UX 관련 문서입니다.

## 📄 문서 목록

### 성능 및 최적화
- **[성능 디버깅](PERFORMANCE_DEBUG.md)**
  - 성능 측정 방법
  - 최적화 기법
  - 번들 사이즈 관리
  - 렌더링 최적화

### 문제 해결
- **[복구 가이드](RECOVERY-INSTRUCTIONS.md)**
  - 일반적인 오류 해결
  - 개발 환경 복구
  - 빌드 오류 해결
  - 배포 문제 해결

- **[Supabase 연동 수정](README_SUPABASE_FIX.md)**
  - Supabase 클라이언트 설정
  - 인증 연동 문제
  - 실시간 구독 설정
  - 에러 처리

### 기타 문서
- **[프론트엔드 원본 README](frontend_original_README.md)**
  - 프론트엔드 초기 설정
  - 레거시 참조 문서

## 🎨 프론트엔드 아키텍처

### 기술 스택
```yaml
프레임워크: Next.js 14 (App Router)
언어: TypeScript
스타일링: Tailwind CSS
컴포넌트: shadcn/ui
상태관리: Zustand
폼 처리: React Hook Form
API 통신: Axios
인증: Supabase Auth
```

## 📁 프로젝트 구조

```
src/
├── app/                # Next.js 14 App Router
│   ├── (auth)/        # 인증 관련 페이지
│   ├── dashboard/     # 대시보드
│   ├── stores/        # 매장 관리
│   └── api/          # API 라우트
├── components/        # 재사용 컴포넌트
│   ├── ui/           # 기본 UI 컴포넌트
│   ├── forms/        # 폼 컴포넌트
│   └── charts/       # 차트 컴포넌트
├── hooks/            # 커스텀 훅
├── lib/              # 유틸리티 함수
├── services/         # API 서비스
├── store/            # 전역 상태 관리
└── types/            # TypeScript 타입 정의
```

## 🎯 주요 기능

### 1. 대시보드
- 실시간 통계 표시
- 차트 및 그래프
- 알림 센터

### 2. 매장 관리
- 매장 정보 CRUD
- 플랫폼 연동 설정
- 리뷰 관리

### 3. AI 답글 관리
- 답글 템플릿 설정
- 자동 답글 규칙
- 답글 히스토리

### 4. 분석 및 리포트
- 리뷰 분석
- 감정 분석 결과
- 성과 리포트

## 🚀 개발 시작하기

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 프로덕션 실행
npm start
```

## 🎨 UI 컴포넌트

### shadcn/ui 컴포넌트 추가
```bash
npx shadcn-ui@latest add [component-name]
```

### 사용 가능한 컴포넌트
- Button, Card, Dialog
- Form, Input, Select
- Table, Tabs
- Chart, Badge
- 등등...

## 🧪 테스트

```bash
# 단위 테스트
npm test

# E2E 테스트
npm run test:e2e

# 테스트 커버리지
npm run test:coverage
```

## 🔗 관련 문서
- [시스템 아키텍처](../01-architecture/SYSTEM_ARCHITECTURE.md)
- [API 레퍼런스](../01-architecture/API_REFERENCE.md)
- [개발 가이드](../04-development/DEVELOPMENT_GUIDE.md)