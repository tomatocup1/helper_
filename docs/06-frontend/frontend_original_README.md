# 우리가게 도우미 - Frontend

소상공인을 위한 스마트 리뷰 관리 서비스의 프론트엔드 애플리케이션입니다.

## 🚀 빠른 시작

### 1. 환경 변수 설정
```bash
cp .env.local.example .env.local
```

`.env.local` 파일에 Supabase 정보를 입력하세요:
```bash
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 2. 의존성 설치 및 실행
```bash
npm install
npm run dev
```

### 3. 회원가입 테스트
1. http://localhost:3000/register 접속
2. 계정 정보 입력:
   - 이메일: test@example.com
   - 비밀번호: test123456
   - 이름: 테스트 사장님
   - 전화번호: 010-1234-5678 (선택)
   - 사업자등록번호: 123-45-67890 (선택)
   - 약관 동의: 체크

### 4. 로그인 테스트
회원가입 후 자동으로 대시보드로 이동하거나, `/login`에서 로그인 가능

## 🔧 기술 스택

- **Framework**: Next.js 15.4.6 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **State Management**: Zustand
- **Authentication**: Supabase Auth
- **Database**: Supabase PostgreSQL
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **Charts**: Recharts
- **Build Tool**: Turbopack

## 📱 주요 기능

### ✅ 구현 완료
- 🔐 **사용자 인증**: Supabase를 통한 로그인/회원가입, JWT 토큰 관리
- 📱 **반응형 디자인**: 모바일, 태블릿, 데스크톱 최적화
- 🎨 **모던 UI**: shadcn/ui 기반 일관된 디자인 시스템
- ⚡ **성능 최적화**: Turbopack, 이미지 최적화, 코드 스플리팅
- 🌍 **국제화**: 한국어 기본, 다국어 지원 준비
- 🔄 **상태 관리**: Zustand를 활용한 간단하고 효율적인 상태 관리
- 📊 **대시보드**: 매장 관리, 리뷰 관리, 분석 리포트, 설정 페이지

### 🚧 개발 예정
- 매장 등록 및 플랫폼 연동
- 리뷰 크롤링 및 AI 답글 생성
- 실시간 알림 시스템
- 결제 및 구독 관리

## 🏗️ 프로젝트 구조

```
src/
├── app/                    # Next.js App Router 페이지
│   ├── layout.tsx         # 루트 레이아웃
│   ├── page.tsx           # 홈 페이지
│   ├── login/             # 로그인 페이지
│   ├── register/          # 회원가입 페이지
│   ├── dashboard/         # 대시보드 페이지들
│   │   ├── page.tsx       # 메인 대시보드
│   │   └── layout.tsx     # 대시보드 레이아웃
│   ├── stores/            # 매장 관리 페이지
│   ├── reviews/           # 리뷰 관리 페이지
│   ├── analytics/         # 분석 리포트 페이지
│   └── settings/          # 설정 페이지
├── components/            # 재사용 가능한 컴포넌트
│   ├── ui/               # 기본 UI 컴포넌트 (shadcn/ui)
│   ├── forms/            # 폼 컴포넌트
│   └── charts/           # 차트 컴포넌트
├── lib/                  # 유틸리티 및 설정
│   ├── supabase/         # Supabase 클라이언트 설정
│   ├── api.ts           # API 클라이언트
│   └── utils.ts         # 공통 유틸리티
├── hooks/               # 커스텀 훅
├── store/               # 상태 관리 (Zustand)
├── types/               # TypeScript 타입 정의
│   ├── index.ts         # 일반 타입
│   └── database.ts      # Supabase 데이터베이스 타입
└── styles/              # 전역 스타일
```

## 🛠️ 개발 환경 설정

### 필수 요구사항
- Node.js 18.0.0 이상
- npm 또는 yarn
- Supabase 프로젝트

### 설정 단계
1. **Supabase 프로젝트 생성**: [설정 가이드](../docs/supabase-setup.md) 참조
2. **환경 변수 설정**: `.env.local` 파일 구성
3. **데이터베이스 스키마 실행**: Supabase SQL Editor에서 스키마 실행
4. **의존성 설치**: `npm install`
5. **개발 서버 실행**: `npm run dev`

### 사용 가능한 스크립트

```bash
# 개발 서버 시작 (Turbopack 사용)
npm run dev

# 프로덕션 빌드
npm run build

# 프로덕션 서버 시작
npm run start

# 린트 검사
npm run lint

# 타입 체크
npm run type-check
```

## 📊 페이지별 기능

### 1. 홈 페이지 (`/`)
- 서비스 소개 및 특징
- 가격 플랜 안내
- 회원가입 유도

### 2. 로그인 (`/login`)
- 이메일/비밀번호 로그인
- 로그인 상태 유지 옵션
- 비밀번호 찾기 링크

### 3. 회원가입 (`/register`)
- 계정 생성 (이메일, 비밀번호, 이름)
- 선택적 정보 (전화번호, 사업자등록번호)
- 약관 동의 (이용약관, 개인정보처리방침)

### 4. 대시보드 (`/dashboard`)
- 매장 현황 요약 (등록된 매장, 리뷰 수, 평균 평점, 답글 완료율)
- 최근 리뷰 목록
- 알림 및 빠른 액션
- 구독 정보

### 5. 매장 관리 (`/stores`)
- 등록된 매장 목록
- 매장별 통계 (평점, 리뷰 수, 월 고객 수)
- 플랫폼 연동 상태
- 새 매장 등록

### 6. 리뷰 관리 (`/reviews`)
- 전체 리뷰 목록 및 필터링
- 감정 분석 결과 (긍정/부정/중립)
- AI 답글 생성 및 수동 답글 작성
- 답글 상태 관리

### 7. 분석 리포트 (`/analytics`)
- 월별 리뷰 추이 차트
- 감정 분석 파이 차트
- 평점 분포 및 인기 키워드
- 매장별 성과 비교
- AI 인사이트 및 권장사항

### 8. 설정 (`/settings`)
- 프로필 관리
- 구독 플랜 관리
- 알림 설정
- 플랫폼 연동 관리
- API 설정
- 보안 설정

## 🎨 디자인 시스템

### 색상 팔레트
```css
/* 브랜드 컬러 */
--brand-50: #f0f9ff
--brand-100: #e0f2fe
--brand-500: #0ea5e9
--brand-600: #0284c7

/* 시멘틱 컬러 */
--success: #10b981
--warning: #f59e0b
--error: #ef4444
--info: #3b82f6
```

### 컴포넌트 사용 예시
```tsx
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function ExampleComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>제목</CardTitle>
      </CardHeader>
      <CardContent>
        <Button variant="brand" size="lg">
          버튼
        </Button>
      </CardContent>
    </Card>
  )
}
```

## 🔗 Supabase 연동

### 인증 시스템
```tsx
import { useAuth } from '@/store/auth-store-supabase'

export function Component() {
  const { user, login, logout, isLoading } = useAuth()
  
  const handleLogin = async () => {
    const success = await login(email, password)
    if (success) {
      // 로그인 성공 처리
    }
  }
  
  return (
    <div>
      {user ? (
        <p>{user.name}님 환영합니다</p>
      ) : (
        <button onClick={handleLogin}>로그인</button>
      )}
    </div>
  )
}
```

### 데이터베이스 접근
```tsx
import { createClient } from '@/lib/supabase/client'

const supabase = createClient()

// 매장 목록 조회
const { data: stores } = await supabase
  .from('platform_stores')
  .select('*')
  .eq('user_id', user.id)
```

## 🧪 테스트

### 단위 테스트 (예정)
```bash
npm run test
```

### E2E 테스트 (예정)
```bash
npm run test:e2e
```

## 📈 성능 최적화

- **이미지 최적화**: Next.js Image 컴포넌트 사용
- **코드 스플리팅**: 동적 import 활용
- **캐싱**: Supabase 캐싱 및 브라우저 캐시 활용
- **번들 분석**: webpack-bundle-analyzer 사용

## 🚀 배포

### Vercel 배포 (권장)
```bash
# Vercel CLI 설치
npm i -g vercel

# 배포
vercel
```

### 환경 변수 설정
Vercel Dashboard에서 환경 변수 설정:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## 🔍 문제 해결

### 회원가입/로그인 오류
1. `.env.local` 파일의 Supabase URL과 Key 확인
2. Supabase 프로젝트가 활성화되어 있는지 확인
3. 데이터베이스 스키마가 올바르게 실행되었는지 확인

### 개발 서버 오류
```bash
# 의존성 재설치
rm -rf node_modules package-lock.json
npm install

# Next.js 캐시 클리어
rm -rf .next
npm run dev
```

## 📚 참고 자료

- [Next.js 문서](https://nextjs.org/docs)
- [Supabase 문서](https://supabase.com/docs)
- [Tailwind CSS 문서](https://tailwindcss.com/docs)
- [shadcn/ui 문서](https://ui.shadcn.com/)
- [Zustand 문서](https://zustand-demo.pmnd.rs/)

## 📞 지원

문제가 발생하거나 질문이 있으시면:
- GitHub Issues에 문제 등록
- 개발팀 Slack 채널 #frontend
- 이메일: dev@storehelper.com