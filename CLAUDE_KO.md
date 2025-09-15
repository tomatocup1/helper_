# CLAUDE_KO.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소의 코드를 다룰 때 참고할 가이드입니다.

## 프로젝트 개요

**우리가게 도우미 (Store Helper)**는 한국 소상공인을 위한 종합 리뷰 관리 및 CRM 플랫폼입니다. AI 기반 답글 생성을 통해 여러 플랫폼(네이버, 배민, 쿠팡이츠, 요기요)의 온라인 리뷰 관리를 자동화합니다.

## 아키텍처 개요

### 기술 스택
- **프론트엔드**: Next.js 14, TypeScript, Tailwind CSS, Shadcn UI 컴포넌트
- **백엔드**: Python FastAPI, Playwright (크롤링용)
- **데이터베이스**: Supabase (PostgreSQL)
- **AI**: OpenAI GPT-4o-mini (리뷰 답글 생성)
- **인프라**: Docker, 통합 포트(4000)용 프록시 서버

### 프로젝트 구조
```
C:\helper_B\
├── frontend/          # Next.js 애플리케이션
├── backend/           # Python FastAPI 서버 + 크롤러
│   ├── core/         # 플랫폼별 크롤러 & AI 답글 시스템
│   └── services/     # 플랫폼 서비스 (배민, 쿠팡이츠, 요기요)
├── database/         # Supabase 마이그레이션 & 스키마
└── docs/            # 종합 문서
```

## 필수 개발 명령어

### 빠른 시작 (Windows)
```bash
# 통합 포트 4000에서 모든 서비스 시작
start-local.bat

# 옵션 1: 프록시만 (수동 서비스 시작)
# 옵션 2: 프록시 + 프론트엔드
# 옵션 3: 모든 서비스 (개발 권장)
```

### 프론트엔드 개발
```bash
cd frontend
npm install
npm run dev          # 포트 3000에서 실행
npm run build        # 프로덕션 빌드
npm run lint         # ESLint 실행
```

### 백엔드 개발
```bash
cd backend
pip install -r requirements.txt  # 의존성 설치
python server.py                 # FastAPI 서버 포트 8001에서 실행

# 특정 크롤러 실행
python core/naver_review_crawler.py
python core/baemin_review_crawler.py
python core/coupang_review_crawler.py
python core/yogiyo_review_crawler.py

# AI 답글 시스템 실행
python core/ai_reply/main.py
```

### 데이터베이스 작업
```bash
# 마이그레이션은 database/migrations/에 위치
# Supabase 대시보드를 통해 자동 적용됨
```

## 핵심 아키텍처 패턴

### 1. 멀티 플랫폼 리뷰 시스템
각 플랫폼마다 고유한 구조를 가진 리뷰를 처리합니다:
- **네이버**: 숫자 평점 없음, 평균 계산 시 특별 처리 필요
- **배민/쿠팡이츠/요기요**: 표준 1-5 별점 평점
- 각 플랫폼은 전용 테이블 보유: `reviews_naver`, `reviews_baemin`, `reviews_coupangeats`, `reviews_yogiyo`

### 2. 플랫폼 매장 관리
- `platform_stores` 테이블에 자격 증명 및 매장 정보 저장
- 플랫폼별 암호화 키를 사용한 자격 증명 암호화
- 비밀번호 암/복호화는 `backend/core/password_decrypt.py`에서 처리

### 3. AI 답글 생성 흐름
```
1. 크롤러가 새 리뷰 수집 → 플랫폼별 테이블에 저장
2. AI 시스템이 리뷰 처리 → 상황별 답글 생성
3. 답글 상태 추적: draft → pending_approval → approved → sent
4. 플랫폼별 포스터가 승인된 답글을 다시 전송
```

### 4. 인증 및 권한 부여
- Supabase Auth로 사용자 관리
- API 인증용 JWT 토큰
- 역할 기반 접근 제어 (owner, admin)

## 주요 데이터베이스 테이블

### 핵심 테이블
- `users`: 사용자 계정
- `stores`: 실제 매장 정보
- `platform_stores`: 암호화된 자격 증명을 포함한 플랫폼별 매장 설정
- `reviews_[platform]`: 플랫폼별 리뷰 테이블
- `ai_reply_settings`: 커스터마이징 가능한 AI 답글 설정

## 환경 변수

### 필수 `.env` 변수
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# OpenAI
OPENAI_API_KEY=

# 플랫폼 암호화 키 (자동 생성)
NAVER_ENCRYPTION_KEY=
BAEMIN_ENCRYPTION_KEY=
COUPANGEATS_ENCRYPTION_KEY=
YOGIYO_ENCRYPTION_KEY=
```

## 일반적인 개발 작업

### 새 리뷰 플랫폼 추가
1. `backend/core/[플랫폼]_review_crawler.py`에 크롤러 생성
2. `database/migrations/`에 데이터베이스 마이그레이션 생성
3. `backend/core/ai_reply/platform_adapters.py`에 플랫폼 어댑터 추가
4. 프론트엔드 리뷰 표시 컴포넌트 업데이트

### AI 답글 템플릿 수정
1. 설정은 `ai_reply_settings` 테이블에 저장됨
2. `/owner-replies/settings` 페이지에서 설정 가능
3. 템플릿은 변수 지원: {customer_name}, {store_name}, {menu_items}

### 크롤러 테스트
```python
# 개별 크롤러 테스트
cd backend
python -m pytest tests/test_[플랫폼]_crawler.py

# 특정 매장으로 크롤러 실행
python core/[플랫폼]_review_crawler.py --store-id [UUID]
```

## 플랫폼별 고려사항

### 네이버
- 영구 프로필을 사용한 브라우저 자동화
- 숫자 평점 없음 (평점 없음)
- 캡차 처리를 포함한 복잡한 로그인 흐름

### 배민
- 암호화된 API 통신
- 세션 기반 인증
- 속도 제한 고려사항

### 쿠팡이츠
- 헤드리스 브라우저 자동화
- 동적 콘텐츠 로딩
- 페이지네이션 처리

### 요기요
- DSID 기반 인증
- 복잡한 리뷰 구조
- 다양한 리뷰 유형 (배달, 맛, 양)

## 디버깅 팁

### 리뷰 페이지 문제
- `frontend/src/app/owner-replies/reviews/page.tsx` 확인
- 플랫폼 필터 로직 검증
- 올바른 평점 계산 확인 (rating=0 제외)

### 크롤러 실패
- `backend/core/logs/browser_profiles/`에서 브라우저 프로필 확인
- `platform_stores` 테이블에서 플랫폼 자격 증명 확인
- `backend/[플랫폼]_service.log`에서 크롤러 로그 검토

### AI 답글 생성
- OpenAI API 키 유효성 확인
- 올바른 설정을 위한 `ai_reply_settings` 검토
- 토큰 사용량 및 속도 제한 모니터링

## 포트 설정

로컬 실행 시 기본 포트:
- **프록시 서버**: 4000 (통합 접근점)
- **프론트엔드**: 3000
- **백엔드 API**: 8001
- **스케줄러**: 8002
- **관리자 대시보드**: 3001 (별도 실행 시)

프록시 서버 사용 시 `http://localhost:3000`을 통해 모든 것에 접근 가능합니다.

## 주요 파일 경로

### 자주 수정되는 파일
- **리뷰 페이지 UI**: `frontend/src/app/owner-replies/reviews/page.tsx`
- **매장 관리**: `frontend/src/app/stores/page.tsx`
- **AI 답글 생성**: `backend/core/ai_reply/ai_reply_manager.py`
- **플랫폼 어댑터**: `backend/core/ai_reply/platform_adapters.py`

### 크롤러 파일
- **네이버**: `backend/core/naver_review_crawler.py`
- **배민**: `backend/core/baemin_review_crawler.py`
- **쿠팡이츠**: `backend/core/coupang_review_crawler.py`
- **요기요**: `backend/core/yogiyo_review_crawler.py`

### API 엔드포인트
- **배민 간단 API**: `backend/simple_baemin_api.py`
- **메인 서버**: `backend/server.py`
- **프론트엔드 API 라우트**: `frontend/src/app/api/`

## 문제 해결 체크리스트

### 리뷰가 표시되지 않을 때
1. ✅ Supabase 연결 확인
2. ✅ 플랫폼 필터 상태 확인
3. ✅ 날짜 필터 범위 확인
4. ✅ 매장 선택 상태 확인

### 크롤러가 작동하지 않을 때
1. ✅ 플랫폼 로그인 정보 확인
2. ✅ 브라우저 프로필 상태 확인
3. ✅ 네트워크 연결 확인
4. ✅ 플랫폼 API 변경 사항 확인

### AI 답글이 생성되지 않을 때
1. ✅ OpenAI API 키 및 잔액 확인
2. ✅ AI 답글 설정 활성화 확인
3. ✅ 리뷰 언어 및 내용 확인
4. ✅ 토큰 제한 확인