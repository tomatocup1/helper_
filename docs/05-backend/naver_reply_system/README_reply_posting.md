# 네이버 답글 자동 등록 시스템

## 개요
Supabase에서 승인된 AI 답글을 가져와 네이버 스마트플레이스에 자동으로 등록하는 시스템입니다.

## 주요 기능
- ✅ Supabase에서 승인된 답글 자동 조회
- ✅ 계정별 브라우저 프로필 관리 (2FA 우회)
- ✅ 네이버 로그인 자동화
- ✅ 리뷰별 답글 자동 등록
- ✅ 등록 상태 실시간 업데이트
- ✅ CLI 및 API 인터페이스 제공

## 시스템 요구사항
- Python 3.8+
- Playwright (브라우저 자동화)
- Supabase 계정
- Windows/Mac/Linux 지원

## 설치 및 설정

### 1. 환경 변수 설정
```bash
# .env.example을 .env로 복사
cp .env.example .env

# 환경 변수 편집
nano .env
```

필수 환경 변수:
- `SUPABASE_URL`: Supabase 프로젝트 URL
- `SUPABASE_KEY`: Supabase Anon Key

### 2. 의존성 설치
```bash
pip install playwright supabase python-dotenv
playwright install chromium
```

### 3. Supabase 테이블 구조

#### reviews_naver 테이블
```sql
-- 필수 컬럼들
id (text, primary key)
naver_review_id (text) -- 네이버 리뷰 고유 ID
store_id (text)
platform_store_code (text) -- 네이버 매장 코드
reviewer_name (text)
review_text (text)
rating (integer)
ai_generated_reply (text) -- AI가 생성한 답글
reply_status (text) -- 'approved', 'sent', 'failed', NULL
reply_sent_at (timestamp) -- 답글 전송 시각
reply_posted_at (timestamp) -- 실제 네이버에 등록된 시각
reply_error (text) -- 오류 메시지
approved_at (timestamp)
created_at (timestamp)
updated_at (timestamp)
```

#### platform_stores 테이블
```sql
-- 매장 및 계정 정보
id (uuid, primary key)
user_id (uuid) -- 사용자 ID
store_name (varchar) -- 매장명
platform (platform_type) -- 'naver'
platform_store_id (varchar) -- 네이버 매장 코드
platform_id (varchar) -- 네이버 로그인 ID
platform_pw (text) -- 네이버 로그인 비밀번호

-- 답글 설정
auto_reply_enabled (boolean) -- 자동 답글 활성화
reply_style (reply_style) -- 'friendly', 'professional', 'casual'
custom_instructions (text) -- 맞춤 지침
branding_keywords (jsonb) -- 브랜딩 키워드 배열
auto_approve_positive (boolean) -- 긍정 리뷰 자동 승인

-- 상태
is_active (boolean) -- 활성 상태
created_at (timestamp)
updated_at (timestamp)
```

### 4. 매장 및 계정 정보 설정
`platform_stores` 테이블에 다음과 같이 설정:

```sql
-- 예시 데이터
INSERT INTO platform_stores (
    user_id, store_name, platform, platform_store_id,
    platform_id, platform_pw, auto_reply_enabled, reply_style,
    branding_keywords, auto_approve_positive, is_active
) VALUES (
    'user-uuid', '맛있는 카페', 'naver', '12345678',
    'your_naver_id', 'your_naver_password', true, 'friendly',
    '["맛집", "친절", "깨끗"]'::jsonb, true, true
);
```

## 사용법

### CLI 사용법

#### 기본 실행 (10개 처리)
```bash
python post_replies.py
```

#### 처리할 개수 지정
```bash
python post_replies.py --limit 20
```

#### 테스트 실행 (실제 등록하지 않음)
```bash
python post_replies.py --dry-run
```

#### 도움말
```bash
python post_replies.py --help
```

### API 사용법

#### 백그라운드 실행
```bash
POST /api/v1/reviews/post-replies
Content-Type: application/json

{
  "limit": 10,
  "dry_run": false
}
```

#### 동기 실행 (결과 대기)
```bash
POST /api/v1/reviews/post-replies/sync
Content-Type: application/json

{
  "limit": 5,
  "dry_run": true
}
```

## 워크플로우

### 1. 답글 생성 및 승인 과정
1. AI 답글 생성 시스템이 `reviews_naver.ai_generated_reply`에 답글 생성
2. 긍정 리뷰는 자동 승인 (`auto_approve_positive=true`)
3. 부정 리뷰는 사장님 검토 후 승인 (`reply_status='approved'`)

### 2. 답글 등록 과정
1. `reviews_naver`에서 미답변 리뷰 조회 (`reply_sent_at=NULL`, `ai_generated_reply` 존재)
2. `platform_stores`에서 해당 매장의 계정 정보 및 답글 규칙 조회
3. 계정별로 그룹화하여 브라우저 세션 관리
4. 네이버 로그인 (기기 등록 자동 처리)
5. 각 리뷰 페이지에서 답글 등록 (브랜딩 키워드 적용)
6. 성공시 `reply_status='sent'`, `reply_sent_at`, `reply_posted_at` 업데이트

### 3. 브라우저 프로필 관리
- 각 네이버 계정별로 고유한 브라우저 프로필 생성
- 로그인 정보와 쿠키를 영구 저장
- 2차 인증 기기 등록 정보 유지
- 다음 실행시 자동 로그인 가능

## 로그 및 모니터링

### 로그 파일 위치
```
logs/
├── naver_reply_poster.log        # 메인 로그
└── browser_profiles/             # 브라우저 프로필
    └── naver/
        ├── profile_a1b2c3d4e5/   # 계정별 프로필
        └── profile_f6g7h8i9j0/
```

### 통계 정보
실행 완료시 다음 통계가 출력됩니다:
- 총 가져온 답글 수
- 성공한 등록 수
- 실패한 등록 수
- 건너뛴 답글 수 (이미 답글 존재)
- 발생한 오류 목록

## 보안 고려사항

### 로그인 정보 보안
- Supabase RLS(Row Level Security) 설정 권장
- 로그인 정보는 암호화하여 저장 권장
- 환경 변수 파일(.env)은 git에 커밋하지 않음

### 브라우저 프로필 보안
- 브라우저 프로필 폴더를 백업하여 보관
- 프로필 폴더에 민감한 정보 포함됨 주의

## 문제 해결

### 자주 발생하는 문제

#### 1. 로그인 실패
- 네이버 계정 정보 확인
- 2차 인증 설정 확인
- 브라우저 프로필 삭제 후 재시도

#### 2. 리뷰를 찾을 수 없음
- `naver_review_id` 정확성 확인
- 리뷰가 삭제되었거나 비공개 처리 확인

#### 3. 답글 버튼이 없음
- 이미 답글이 존재하는지 확인
- 매장 관리자 권한 확인

### 디버깅 모드
헤드리스 모드를 비활성화하여 브라우저 창을 보면서 디버깅:

```python
# naver_reply_poster.py에서 수정
browser = await p.chromium.launch_persistent_context(
    user_data_dir=profile_path,
    headless=False,  # True에서 False로 변경
    # ...
)
```

## 성능 최적화

### 처리 속도 향상
- 계정별 병렬 처리
- 브라우저 프로필 재사용으로 로그인 시간 단축
- 요청 간 딜레이 조정으로 차단 방지

### 리소스 사용량 최적화
- 배치 크기 조정 (`--limit` 옵션)
- 메모리 사용량 모니터링
- 긴 실행시간 대비 타임아웃 설정

## 확장 가능성

### 다른 플랫폼 지원
- 구글 마이비즈니스
- 카카오맵
- 요기요/배달의민족

### 추가 기능
- 답글 수정 기능
- 답글 삭제 기능
- 예약 발송 기능
- 대량 처리 최적화