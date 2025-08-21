# 네이버 스마트플레이스 통계 크롤링 시스템

기존 네이버 리뷰 크롤링 시스템의 로그인 메커니즘을 재사용하여 스마트플레이스 통계 페이지에서 데이터를 수집하는 시스템입니다.

## 🚀 주요 특징

### ✨ 기능
- **방문 전 지표**: 플레이스 유입, 예약·주문 신청, 스마트콜 통화
- **방문 후 지표**: 리뷰 등록  
- **유입 분석**: 키워드별/채널별 순위 데이터
- **URL 기반 날짜 필터**: 드롭박스 조작 없이 URL 파라미터로 날짜 지정
- **재시도 로직**: 네트워크 오류, 브라우저 문제 자동 재시도
- **배치 처리**: 여러 매장 일괄 처리

### 🔐 보안 기능
- **2차 인증 우회**: 기존 브라우저 프로필 재사용
- **세션 관리**: 계정별 독립적인 브라우저 프로필
- **RLS 보안**: Supabase 행 수준 보안 적용

## 📁 파일 구조

```
backend/scripts/
├── naver_statistics_crawler.py     # 메인 통계 크롤링 엔진
├── run_statistics_crawler.py       # 배치 실행 스크립트
├── naver_login_auto.py             # 기존 로그인 시스템 (재사용)
└── sql/
    └── create_statistics_naver_table.sql  # 데이터베이스 테이블 생성 스크립트
```

## 🗄️ 데이터베이스 스키마

### `statistics_naver` 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `id` | UUID | 기본키 |
| `platform_store_id` | UUID | 매장 ID (platform_stores 참조) |
| `date` | DATE | 통계 날짜 |
| `place_inflow` | INTEGER | 플레이스 유입 횟수 |
| `place_inflow_change` | DECIMAL | 플레이스 유입 증감률 (%) |
| `reservation_order` | INTEGER | 예약·주문 신청 횟수 |
| `reservation_order_change` | DECIMAL | 예약·주문 증감률 (%) |
| `smart_call` | INTEGER | 스마트콜 통화 횟수 |
| `smart_call_change` | DECIMAL | 스마트콜 증감률 (%) |
| `review_registration` | INTEGER | 리뷰 등록 횟수 |
| `review_registration_change` | DECIMAL | 리뷰 등록 증감률 (%) |
| `inflow_channels` | JSONB | 유입 채널 순위 데이터 |
| `inflow_keywords` | JSONB | 유입 키워드 순위 데이터 |

## ⚙️ 설치 및 설정

### 1. 데이터베이스 테이블 생성
```sql
-- Supabase SQL Editor에서 실행
-- sql/create_statistics_naver_table.sql 파일 내용 실행
```

### 2. 환경변수 설정
```bash
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### 3. Python 패키지 설치
```bash
pip install playwright supabase python-dotenv
playwright install chromium
```

## 🖥️ 사용법

### 단일 매장 통계 수집

```bash
# 기본 사용법 (전날 통계)
python naver_statistics_crawler.py \
  --email "account@naver.com" \
  --password "password" \
  --store-id "platform_store_id" \
  --user-id "user_uuid"

# 특정 날짜 통계
python naver_statistics_crawler.py \
  --email "account@naver.com" \
  --password "password" \
  --store-id "platform_store_id" \
  --user-id "user_uuid" \
  --date "2025-08-17"

# 헤드리스 모드 (백그라운드 실행)
python naver_statistics_crawler.py \
  --email "account@naver.com" \
  --password "password" \
  --store-id "platform_store_id" \
  --user-id "user_uuid" \
  --headless
```

### 배치 처리 (여러 매장 일괄)

```bash
# 전체 매장 배치 처리
python run_statistics_crawler.py --batch --headless

# 특정 날짜로 배치 처리
python run_statistics_crawler.py --batch --date "2025-08-17" --headless

# 재시도 설정 조정
python run_statistics_crawler.py --batch --max-retries 5 --retry-delay 10
```

### 단일 매장 (배치 스크립트 사용)

```bash
python run_statistics_crawler.py --single \
  --email "account@naver.com" \
  --password "password" \
  --store-id "platform_store_id" \
  --user-id "user_uuid" \
  --headless
```

## 🔄 작동 원리

### 1. URL 기반 날짜 필터 (단순화된 접근)
```
기존: 드롭박스 클릭 → "일간" 선택 → 날짜 변경
개선: URL 파라미터로 직접 지정
https://new.smartplace.naver.com/bizes/place/{store_id}/statistics?endDate=2025-08-17&startDate=2025-08-17&term=daily&menu=reports
```

### 2. 로그인 시스템 재사용
- `NaverAutoLogin` 클래스 활용
- 브라우저 프로필 기반 세션 관리
- 2차 인증 우회 메커니즘

### 3. 데이터 추출 과정
1. **방문 전 지표**: CSS 선택자로 각 지표 수치와 증감률 추출
2. **방문 후 지표**: 리뷰 등록 통계 추출
3. **유입 분석**: 탭 클릭 후 순위별 데이터 추출
4. **데이터 저장**: Supabase JSONB 형태로 구조화된 데이터 저장

### 4. 에러 처리
- **재시도 로직**: 네트워크 오류, 브라우저 문제 자동 재시도
- **지수적 백오프**: 재시도 간격 점진적 증가
- **오류 분류**: 재시도 가능/불가능 오류 구분

## 📊 수집 데이터 예시

### 방문 전 지표
```json
{
  "place_inflow": 111,
  "place_inflow_change": -100.0,
  "reservation_order": 2,
  "reservation_order_change": -100.0,
  "smart_call": 3,
  "smart_call_change": -100.0
}
```

### 유입 채널 순위
```json
[
  {"rank": 1, "channel_name": "네이버검색", "count": 46},
  {"rank": 2, "channel_name": "네이버지도", "count": 27},
  {"rank": 3, "channel_name": "페이스북", "count": 23}
]
```

### 유입 키워드 순위
```json
[
  {"rank": 1, "keyword": "청춘껍데기", "count": 11},
  {"rank": 2, "keyword": "구미인동삼겹살", "count": 4},
  {"rank": 3, "keyword": "청춘껍데기구미", "count": 4}
]
```

## 🔧 고급 설정

### 타임아웃 조정
```bash
--timeout 60000  # 60초 (기본값: 30초)
```

### 브라우저 프로필 초기화
```bash
--force-fresh  # 기존 세션 무시하고 새 로그인
```

### 로그 디렉토리
```
logs/browser_profiles/naver/profile_[hash]/  # 계정별 브라우저 프로필
```

## 🚨 주의사항

1. **네이버 서비스 약관 준수**: 과도한 크롤링 방지
2. **계정 보안**: 비밀번호 안전 관리
3. **브라우저 프로필**: 디스크 용량 관리 필요
4. **대기 시간**: 매장 간 적절한 간격 유지

## 🛠️ 트러블슈팅

### 로그인 실패
```bash
# 브라우저 프로필 초기화
--force-fresh

# 타임아웃 증가
--timeout 60000
```

### 페이지 로딩 실패
```bash
# 헤드리스 모드 해제 (디버깅용)
# --headless 플래그 제거

# 재시도 횟수 증가
--max-retries 5
```

### 데이터 추출 오류
- CSS 선택자 변경 시 코드 업데이트 필요
- 페이지 구조 변경 모니터링

## 📈 성능 최적화

- **배치 크기**: 매장당 2초 간격
- **메모리 사용**: 브라우저 프로필 재사용으로 최적화
- **병렬 처리**: 현재는 순차 처리 (네이버 서버 보호)