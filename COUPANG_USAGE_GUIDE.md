# 🏪 쿠팡잇츠 리뷰 관리 시스템 사용 가이드

배달의민족과 동일한 방식으로 구현된 쿠팡잇츠 전용 리뷰 크롤링 및 답글 시스템입니다.

## 📋 시스템 구성

### 1. 핵심 파일들
```
backend/core/
├── coupang_review_crawler.py         # 메인 크롤러
├── coupang_star_rating_extractor.py  # 별점 추출 엔진
└── coupang_reply_poster.py           # 자동 답글 시스템

database/migrations/
├── create_reviews_coupangeats_table.sql  # 리뷰 테이블
└── add_coupangeats_columns.sql           # 매장 테이블 확장
```

### 2. 실행 스크립트들
```
run_coupang_crawler.py        # 크롤러 실행용
test_coupang_crawler.py       # 통합 테스트용
debug_coupang_page.py         # 디버깅용
```

## 🚀 사용 방법

### 1. 환경 설정

```bash
# 환경변수 설정 (.env 파일)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key
HEADLESS_BROWSER=false  # 브라우저 표시 여부
```

### 2. 데이터베이스 설정

```sql
-- 1. 리뷰 테이블 생성
\i database/migrations/create_reviews_coupangeats_table.sql

-- 2. 매장 테이블 확장
\i database/migrations/add_coupangeats_columns.sql
```

### 3. 리뷰 크롤링

#### 기본 사용법
```bash
python run_coupang_crawler.py \
  --username "your_id" \
  --password "your_password" \
  --store-id "708561" \
  --days 7 \
  --max-pages 5
```

#### 파라미터 설명
- `--username`: 쿠팡잇츠 로그인 ID
- `--password`: 쿠팡잇츠 로그인 비밀번호
- `--store-id`: 매장 ID (드롭다운에서 선택할 ID)
- `--days`: 크롤링 기간 (7, 30, 90일)
- `--max-pages`: 최대 크롤링 페이지 수

### 4. 자동 답글 등록

```bash
python backend/core/coupang_reply_poster.py \
  --username "your_id" \
  --password "your_password" \
  --store-id "708561" \
  --max-replies 10 \
  --test-mode  # 테스트용 (실제 등록 안함)
```

## 🎯 주요 기능

### 1. 지능형 요소 탐지
- **다중 Selector 시스템**: 페이지 변경에 강한 fallback 구조
- **동적 로딩 대응**: JavaScript 렌더링 완료 대기
- **에러 복구**: 타임아웃 시 대안 경로 자동 시도

### 2. 고급 별점 추출
```python
# 3단계 별점 추출 시스템
1. SVG 색상 분석: #FFC400 (활성) vs #dfe3e8 (비활성)
2. JavaScript 평가: DOM 직접 분석
3. CSS 클래스 분석: 클래스명 패턴 매칭
```

### 3. 완전한 리뷰 데이터
- **기본 정보**: 리뷰어명, 별점, 텍스트, 날짜
- **주문 정보**: 메뉴 목록, 주문번호, 수령방식
- **특수 필드**: 주문횟수, 이미지 URL
- **메타데이터**: 추출 방식, 신뢰도, 크롤링 시간

### 4. 쿠팡잇츠 특화 기능
- **복수 매장 지원**: 한 계정의 여러 매장 관리
- **빈 리뷰 텍스트 처리**: 별점만 있는 리뷰도 정상 처리
- **주문번호 기반 ID**: 고유한 리뷰 식별자
- **수령방식 정보**: 배달/포장 구분

## 📊 데이터베이스 스키마

### reviews_coupangeats 테이블
```sql
-- 핵심 필드들
coupangeats_review_id    VARCHAR(100)  -- 주문번호 기반 ID
reviewer_name            VARCHAR(100)  -- 리뷰어 이름
order_count             VARCHAR(50)   -- "3회 주문" 형태
rating                  INTEGER       -- 1-5점 별점
review_text             TEXT          -- 리뷰 내용 (NULL 가능)
review_date            DATE          -- 리뷰 작성일
order_date             DATE          -- 실제 주문일
delivery_method        VARCHAR(100)  -- 수령방식
order_menu_items       JSONB         -- 주문 메뉴 목록
photo_urls             JSONB         -- 리뷰 이미지 URL
```

### 인덱스 최적화
- 매장별 조회 최적화
- 날짜 범위 검색 최적화
- 답글 상태별 필터링
- 텍스트 검색 (한국어 지원)

## 🔧 문제 해결

### 1. 로그인 실패
- 계정 정보 확인
- 2단계 인증 설정 해제
- IP 차단 확인

### 2. 페이지 로딩 오류
```bash
# 디버깅 모드로 확인
python debug_coupang_page.py
```

### 3. Selector 오류
- 페이지 구조 변경 시 발생
- HTML 파일 저장해서 구조 분석
- Selector 업데이트 필요

### 4. 데이터베이스 연결 오류
```bash
# 환경변수 확인
echo $NEXT_PUBLIC_SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY
```

## 📈 성능 최적화

### 1. 크롤링 성능
- **병렬 처리**: 페이지별 동시 수집
- **지능형 대기**: 필요한 만큼만 대기
- **선택적 수집**: 중복 리뷰 자동 스킵

### 2. 데이터베이스 성능
- **인덱스 활용**: 주요 조회 패턴 최적화
- **JSONB 검색**: 메뉴, 메타데이터 고속 검색
- **RLS 보안**: 사용자별 데이터 격리

## 🎪 고급 활용

### 1. 배치 크롤링
```python
# cron job으로 정기 실행
0 */6 * * * cd /path/to/project && python run_coupang_crawler.py --username "..." --password "..." --store-id "708561"
```

### 2. 통계 분석
```sql
-- 매장별 리뷰 통계
SELECT * FROM reviews_coupangeats_stats 
WHERE store_name LIKE '%큰집닭강정%';

-- 답글 대기 리뷰 조회
SELECT * FROM get_coupangeats_pending_replies('user_id', 50);
```

### 3. 자동화 워크플로우
1. **정기 크롤링** → 새 리뷰 수집
2. **AI 답글 생성** → 개인화된 답글 작성
3. **자동 포스팅** → 답글 자동 등록
4. **성과 분석** → 리뷰 개선 트렌드 분석

## 🔒 보안 사항

- **환경변수 사용**: 하드코딩 금지
- **RLS 정책**: 사용자별 데이터 격리
- **암호화**: 민감 정보 암호화 저장
- **접근 로그**: 모든 작업 로그 기록

---

**💡 팁**: 처음 사용시에는 `--test-mode`로 테스트 후 실제 운영하는 것을 권장합니다.