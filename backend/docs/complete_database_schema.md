# 전체 데이터베이스 스키마 (최신 업데이트 반영)

## ENUM 타입 정의

```sql
-- 구독 요금제
CREATE TYPE subscription_plan AS ENUM ('free', 'basic', 'premium', 'enterprise');

-- 플랫폼 종류
CREATE TYPE platform_type AS ENUM ('naver', 'baemin', 'yogiyo', 'coupangeats');

-- 리뷰 감정 분석
CREATE TYPE review_sentiment AS ENUM ('positive', 'negative', 'neutral');

-- 답글 상태
CREATE TYPE reply_status AS ENUM ('draft', 'pending_approval', 'approved', 'sent', 'failed');

-- 리뷰 초안 사용 상태
CREATE TYPE draft_usage_status AS ENUM ('generated', 'viewed', 'copied', 'posted', 'ignored');

-- 에러 심각도
CREATE TYPE error_severity AS ENUM ('low', 'medium', 'high', 'critical');

-- 답글 스타일
CREATE TYPE reply_style AS ENUM ('friendly', 'formal', 'casual');

-- 기간 유형
CREATE TYPE period_type AS ENUM ('daily', 'weekly', 'monthly');

-- 에러 카테고리
CREATE TYPE error_category AS ENUM ('crawling', 'ai_generation', 'api', 'database', 'payment', 'notification');
```

## 1. users 테이블 - 사용자 정보 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **기본 정보** |
| id | UUID | gen_random_uuid() | PRIMARY KEY | 사용자 고유 식별자 |
| email | VARCHAR(255) | - | UNIQUE NOT NULL | 로그인용 이메일 주소 |
| name | VARCHAR(100) | - | NOT NULL | 사용자 이름 |
| phone | VARCHAR(20) | - | - | 연락처 |
| **카카오 OAuth 정보** |
| kakao_id | VARCHAR(50) | - | UNIQUE | 카카오 고유 ID |
| kakao_nickname | VARCHAR(100) | - | - | 카카오 닉네임 |
| profile_image_url | TEXT | - | - | 프로필 이미지 URL |
| **구독 및 사용량 관리** |
| subscription_plan | subscription_plan | 'free' | ENUM | 구독 요금제 |
| subscription_start_date | TIMESTAMP WITH TIME ZONE | - | - | 구독 시작일 |
| subscription_end_date | TIMESTAMP WITH TIME ZONE | - | - | 구독 만료일 |
| monthly_store_limit | INT | 1 | - | 월 등록 가능 매장 수 |
| monthly_ai_reply_limit | INT | 100 | - | 월 AI 답글 생성 한도 |
| monthly_draft_limit | INT | 50 | - | 월 초안 생성 한도 |
| current_month_stores | INT | 0 | - | 현재 월 등록된 매장 수 |
| current_month_ai_replies | INT | 0 | - | 현재 월 AI 답글 사용량 |
| current_month_drafts | INT | 0 | - | 현재 월 초안 사용량 |
| usage_reset_date | DATE | - | - | 사용량 리셋 날짜 |
| **추가 정보** |
| business_type | VARCHAR(50) | - | - | 사업 유형 |
| referral_code | VARCHAR(20) | - | UNIQUE | 추천 코드 |
| referred_by | VARCHAR(20) | - | - | 추천인 코드 |
| **약관 동의** |
| terms_agreed | BOOLEAN | false | - | 이용약관 동의 |
| privacy_agreed | BOOLEAN | false | - | 개인정보 동의 |
| marketing_agreed | BOOLEAN | false | - | 마케팅 동의 |
| agreement_timestamp | TIMESTAMP WITH TIME ZONE | - | - | 약관 동의 시각 |
| **메타데이터** |
| is_active | BOOLEAN | true | - | 계정 활성화 상태 |
| last_login_at | TIMESTAMP WITH TIME ZONE | - | - | 마지막 로그인 시각 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 계정 생성일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 정보 수정일 |

## 2. platform_stores 테이블 - 플랫폼별 매장 정보

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **기본 매장 정보** |
| id | UUID | gen_random_uuid() | PRIMARY KEY | 매장 고유 식별자 |
| user_id | UUID | - | NOT NULL, FK(users) | 매장 소유자 ID |
| store_name | VARCHAR(200) | - | NOT NULL | 매장명 |
| business_type | VARCHAR(50) | - | - | 업종 |
| address | TEXT | - | - | 매장 주소 |
| phone | VARCHAR(20) | - | - | 매장 전화번호 |
| business_registration_number | VARCHAR(20) | - | - | 사업자등록번호 |
| **플랫폼 연결 정보** |
| platform | platform_type | - | NOT NULL, ENUM | 플랫폼 종류 |
| platform_store_id | VARCHAR(100) | - | NOT NULL | 플랫폼에서의 매장 ID |
| platform_url | TEXT | - | - | 플랫폼 매장 URL |
| platform_id | VARCHAR(255) | - | - | 플랫폼 로그인 ID |
| platform_pw | TEXT | - | - | 암호화된 비밀번호 |
| sub_type | VARCHAR(20) | NULL | - | 서비스 타입 |
| **크롤링 설정** |
| crawling_enabled | BOOLEAN | true | - | 크롤링 활성화 |
| crawling_interval_minutes | INT | 30 | - | 크롤링 주기(분) |
| last_crawled_at | TIMESTAMP WITH TIME ZONE | - | - | 마지막 크롤링 시각 |
| next_crawl_at | TIMESTAMP WITH TIME ZONE | - | - | 다음 크롤링 예정 시각 |
| **AI 답글 설정** |
| auto_reply_enabled | BOOLEAN | false | - | 자동 답글 활성화 |
| reply_style | reply_style | 'friendly' | ENUM | 답글 스타일 |
| custom_instructions | TEXT | - | - | 맞춤 답글 지침 |
| greeting_template | VARCHAR(200) | - | - | 답글 첫인사 템플릿 |
| closing_template | VARCHAR(200) | - | - | 답글 마무리 템플릿 |
| reply_tone | VARCHAR(20) | 'friendly' | - | 답글 톤앤매너 |
| min_reply_length | INTEGER | 50 | - | 최소 답글 길이 |
| max_reply_length | INTEGER | 200 | - | 최대 답글 길이 |
| brand_voice | TEXT | - | - | 매장 브랜드 보이스 |
| **자동화 규칙** |
| negative_review_delay_hours | INT | 48 | - | 부정 리뷰 답글 지연 시간 |
| auto_approve_positive | BOOLEAN | true | - | 긍정 리뷰 자동 승인 |
| require_approval_negative | BOOLEAN | true | - | 부정 리뷰 승인 필요 |
| **SEO/브랜딩** |
| branding_keywords | JSONB | '[]'::jsonb | - | 브랜딩 키워드 |
| seo_keywords | TEXT[] | - | - | SEO 키워드 배열 |
| **네이버 특화** |
| naver_id | VARCHAR(100) | - | - | 네이버 로그인 ID |
| naver_password_encrypted | TEXT | - | - | 암호화된 네이버 비밀번호 |
| naver_session_active | BOOLEAN | false | - | 네이버 세션 활성 상태 |
| naver_last_login | TIMESTAMP WITH TIME ZONE | - | - | 네이버 마지막 로그인 |
| naver_device_registered | BOOLEAN | false | - | 네이버 기기 등록 상태 |
| naver_login_attempts | INTEGER | 0 | - | 네이버 로그인 시도 횟수 |
| naver_profile_path | TEXT | - | - | 네이버 브라우저 프로필 경로 |
| **쿠팡잇츠 특화** |
| coupangeats_session_active | BOOLEAN | false | - | 쿠팡잇츠 세션 활성 상태 |
| coupangeats_last_login | TIMESTAMP WITH TIME ZONE | - | - | 쿠팡잇츠 마지막 로그인 |
| **상태 정보** |
| is_active | BOOLEAN | true | - | 매장 활성화 상태 |
| is_verified | BOOLEAN | false | - | 매장 검증 상태 |
| verification_date | TIMESTAMP WITH TIME ZONE | - | - | 검증 완료 날짜 |
| platform_metadata | JSONB | '{}'::jsonb | - | 플랫폼별 메타데이터 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 매장 등록일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 정보 수정일 |

## 3. reviews_naver 테이블 - 네이버 리뷰 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **리뷰 식별** |
| id | UUID | gen_random_uuid() | PRIMARY KEY | 리뷰 고유 식별자 |
| platform_store_id | UUID | - | NOT NULL, FK | 매장 ID |
| naver_review_id | VARCHAR(100) | - | UNIQUE NOT NULL | 네이버 리뷰 고유 ID |
| naver_review_url | TEXT | - | - | 네이버 리뷰 URL |
| **리뷰어 정보** |
| reviewer_name | VARCHAR(100) | - | - | 리뷰어 이름 |
| reviewer_id | VARCHAR(100) | - | - | 리뷰어 ID |
| reviewer_level | VARCHAR(50) | - | - | 리뷰어 등급 |
| **리뷰 내용** |
| rating | INT | - | CHECK (1-5) | 별점 |
| review_text | TEXT | - | - | 리뷰 텍스트 |
| review_date | TIMESTAMP WITH TIME ZONE | - | - | 리뷰 작성일 |
| **AI 분석** |
| sentiment | review_sentiment | - | ENUM | 감정 분석 결과 |
| sentiment_score | FLOAT | - | CHECK (-1.0 to 1.0) | 감정 점수 |
| extracted_keywords | JSONB | '[]'::jsonb | - | 추출된 키워드 |
| inserted_keywords | TEXT[] | - | - | 삽입된 키워드 |
| **답글 관리** |
| reply_text | TEXT | - | - | 실제 답글 텍스트 |
| reply_status | reply_status | 'draft' | ENUM | 답글 상태 |
| ai_generated_reply | TEXT | - | - | AI 생성 답글 |
| ai_model_used | VARCHAR(50) | 'gpt-4' | - | 사용된 AI 모델 |
| ai_generation_time_ms | INT | - | - | AI 생성 소요 시간 |
| ai_confidence_score | FLOAT | - | CHECK (0.0-1.0) | AI 생성 신뢰도 |
| reply_naturalness_score | FLOAT | - | - | 답글 자연스러움 점수 |
| **승인 워크플로우** |
| requires_approval | BOOLEAN | false | - | 승인 필요 여부 |
| approved_by | UUID | - | FK(users) | 승인자 ID |
| approved_at | TIMESTAMP WITH TIME ZONE | - | - | 승인 시각 |
| approval_notes | TEXT | - | - | 승인 메모 |
| **발송 및 스케줄링** |
| reply_sent_at | TIMESTAMP WITH TIME ZONE | - | - | 답글 발송 시각 |
| reply_failed_at | TIMESTAMP WITH TIME ZONE | - | - | 발송 실패 시각 |
| failure_reason | TEXT | - | - | 발송 실패 사유 |
| retry_count | INT | 0 | - | 재시도 횟수 |
| scheduled_reply_date | TIMESTAMP WITH TIME ZONE | - | - | 답글 스케줄 시각 |
| schedulable_reply_date | TIMESTAMP | - | - | 답글 게시 가능 시각 |
| censorship_reason | TEXT | - | - | 검열 사유 |
| **네이버 특화** |
| has_photos | BOOLEAN | false | - | 사진 첨부 여부 |
| photo_count | INT | 0 | - | 사진 개수 |
| is_visited_review | BOOLEAN | false | - | 방문 리뷰 여부 |
| naver_metadata | JSONB | '{}'::jsonb | - | 네이버 관련 메타데이터 |
| **타임스탬프** |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 리뷰 수집일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 정보 수정일 |

## 4. reviews_baemin 테이블 - 배민 리뷰 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **기본 구조** | (reviews_naver와 유사) |
| **추가된 컬럼** |
| requires_approval | BOOLEAN | false | - | 승인 필요 여부 |
| failure_reason | TEXT | - | - | 답글 발송 실패 사유 |
| scheduled_reply_date | TIMESTAMP WITH TIME ZONE | - | - | 답글 예약 발송 시각 |
| schedulable_reply_date | TIMESTAMP | - | - | 답글 게시 가능 시각 |
| inserted_keywords | TEXT[] | - | - | 삽입된 키워드 |
| reply_naturalness_score | FLOAT | - | - | 답글 자연스러움 점수 |
| censorship_reason | TEXT | - | - | 검열 사유 |

## 5. reviews_yogiyo 테이블 - 요기요 리뷰 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **DSID 시스템** |
| yogiyo_dsid | VARCHAR(16) | - | NOT NULL | DSID (DOM Stable ID) |
| content_hash | VARCHAR(16) | - | NOT NULL | 콘텐츠 해시 |
| rolling_hash | VARCHAR(16) | - | NOT NULL | 롤링 해시 |
| neighbor_hash | VARCHAR(16) | - | NOT NULL | 이웃 윈도우 해시 |
| page_salt | VARCHAR(8) | - | NOT NULL | 페이지 솔트 |
| index_hint | INTEGER | 0 | NOT NULL | 페이지 내 순서 힌트 |
| **평점 시스템** |
| overall_rating | DECIMAL(2,1) | - | CHECK (0.0-5.0) | 전체 별점 |
| taste_rating | INTEGER | - | CHECK (0-5) | 맛 별점 |
| quantity_rating | INTEGER | - | CHECK (0-5) | 양 별점 |
| rating_extraction_method | VARCHAR(50) | 'svg_analysis' | - | 별점 추출 방법 |
| rating_confidence | DECIMAL(3,2) | 1.0 | - | 별점 추출 신뢰도 |
| **주문 정보** |
| order_menu | TEXT | - | - | 주문 메뉴 |
| order_menu_items | JSONB | '[]'::jsonb | - | 구조화된 메뉴 목록 |
| **날짜 처리** |
| review_date | DATE | - | NOT NULL | 파싱된 리뷰 날짜 |
| original_review_date | VARCHAR(50) | - | - | 원본 날짜 문자열 |
| **추가된 컬럼** |
| requires_approval | BOOLEAN | false | - | 승인 필요 여부 |
| schedulable_reply_date | TIMESTAMP | - | - | 답글 게시 가능 시각 |
| inserted_keywords | TEXT[] | - | - | 삽입된 키워드 |
| reply_naturalness_score | FLOAT | - | - | 답글 자연스러움 점수 |
| censorship_reason | TEXT | - | - | 검열 사유 |
| **답글 관리** |
| reply_status | VARCHAR(20) | 'draft' | CHECK | 답글 상태 |
| reply_error_message | TEXT | - | - | 답글 오류 메시지 |
| **메타데이터** |
| yogiyo_metadata | JSONB | '{}'::jsonb | - | 요기요 전용 메타데이터 |

## 6. reviews_coupangeats 테이블 - 쿠팡이츠 리뷰 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **고유 식별자** |
| coupangeats_review_id | VARCHAR(100) | - | NOT NULL | 쿠팡이츠 리뷰 고유 ID |
| coupangeats_review_url | TEXT | - | - | 쿠팡이츠 리뷰 URL |
| **리뷰어 정보** |
| order_count | VARCHAR(50) | - | - | 주문 횟수 정보 |
| **주문 정보** |
| order_date | DATE | - | - | 주문 날짜 |
| order_menu_items | JSONB | '[]'::jsonb | - | 주문 메뉴 목록 |
| delivery_method | VARCHAR(100) | - | - | 배송 방법 |
| **추가된 컬럼** |
| requires_approval | BOOLEAN | false | - | 승인 필요 여부 |
| scheduled_reply_date | TIMESTAMP WITH TIME ZONE | - | - | 답글 예약 발송 시각 |
| schedulable_reply_date | TIMESTAMP | - | - | 답글 게시 가능 시각 |
| inserted_keywords | TEXT[] | - | - | 삽입된 키워드 |
| reply_naturalness_score | FLOAT | - | - | 답글 자연스러움 점수 |
| censorship_reason | TEXT | - | - | 검열 사유 |
| **답글 관리** |
| reply_status | VARCHAR(20) | 'draft' | CHECK | 답글 상태 |
| reply_error_message | TEXT | - | - | 답글 오류 메시지 |
| **메타데이터** |
| coupangeats_metadata | JSONB | '{}'::jsonb | - | 쿠팡이츠 전용 메타데이터 |

## 7. statistics_naver 테이블 - 네이버 통계

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **기본 정보** |
| id | UUID | gen_random_uuid() | PRIMARY KEY | 통계 고유 ID |
| platform_store_id | UUID | - | NOT NULL, FK | 매장 ID |
| date | DATE | - | NOT NULL | 통계 날짜 |
| **방문 전 지표** |
| place_inflow | INTEGER | 0 | NOT NULL | 플레이스 유입 횟수 |
| place_inflow_change | DECIMAL(5,2) | - | - | 플레이스 유입 증감률(%) |
| reservation_order | INTEGER | 0 | NOT NULL | 예약/주문 신청 횟수 |
| reservation_order_change | DECIMAL(5,2) | - | - | 예약/주문 증감률(%) |
| smart_call | INTEGER | 0 | NOT NULL | 스마트콜 통화 횟수 |
| smart_call_change | DECIMAL(5,2) | - | - | 스마트콜 증감률(%) |
| **방문 후 지표** |
| review_registration | INTEGER | 0 | NOT NULL | 리뷰 등록 횟수 |
| review_registration_change | DECIMAL(5,2) | - | - | 리뷰 등록 증감률(%) |
| **유입 분석** |
| inflow_channels | JSONB | '[]'::jsonb | - | 유입 채널 순위 데이터 |
| inflow_keywords | JSONB | '[]'::jsonb | - | 유입 키워드 순위 데이터 |
| **타임스탬프** |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 생성일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 수정일 |

## 8. error_logs 테이블 - 에러 추적

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **에러 분류** |
| id | UUID | gen_random_uuid() | PRIMARY KEY | 에러 고유 ID |
| error_category | error_category | - | NOT NULL, ENUM | 에러 카테고리 |
| error_type | VARCHAR(100) | - | - | 세부 에러 타입 |
| severity | error_severity | - | NOT NULL, ENUM | 심각도 |
| **에러 정보** |
| error_message | TEXT | - | NOT NULL | 에러 메시지 |
| error_details | JSONB | '{}'::jsonb | - | 상세 에러 정보 |
| **관련 정보** |
| user_id | UUID | - | FK(users) | 관련 사용자 |
| platform_store_id | UUID | - | FK | 관련 매장 |
| related_table | VARCHAR(100) | - | - | 관련 테이블명 |
| related_record_id | UUID | - | - | 관련 레코드 ID |
| **시스템 정보** |
| server_name | VARCHAR(50) | - | - | 에러 발생 서버 |
| service_name | VARCHAR(100) | - | - | 에러 발생 서비스 |
| function_name | VARCHAR(200) | - | - | 에러 발생 함수 |
| **해결 정보** |
| is_resolved | BOOLEAN | false | - | 해결 여부 |
| resolved_at | TIMESTAMP WITH TIME ZONE | - | - | 해결 시각 |
| resolved_by | UUID | - | FK(users) | 해결자 |
| resolution_notes | TEXT | - | - | 해결 방법 메모 |
| **요청 정보** |
| request_url | TEXT | - | - | 요청 URL |
| request_method | VARCHAR(10) | - | - | HTTP 메소드 |
| user_agent | TEXT | - | - | 사용자 에이전트 |
| ip_address | INET | - | - | IP 주소 |
| **타임스탬프** |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 에러 발생일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 정보 수정일 |

## 9. jobs 테이블 - 작업 큐 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| **기본 정보** |
| id | UUID | gen_random_uuid() | PRIMARY KEY | 작업 고유 ID |
| job_type | VARCHAR(100) | - | NOT NULL | 작업 유형 |
| resource_id | UUID | - | - | 관련 리소스 ID |
| idempotency_key | VARCHAR(255) | - | UNIQUE | 중복 실행 방지 키 |
| **작업 상태** |
| state | VARCHAR(50) | 'queued' | - | 작업 상태 |
| priority | INT | 5 | - | 우선순위 |
| attempts | INT | 0 | - | 시도 횟수 |
| max_attempts | INT | 3 | - | 최대 시도 횟수 |
| **스케줄링** |
| scheduled_at | TIMESTAMP WITH TIME ZONE | - | - | 예약 실행 시각 |
| started_at | TIMESTAMP WITH TIME ZONE | - | - | 실행 시작 시각 |
| completed_at | TIMESTAMP WITH TIME ZONE | - | - | 완료 시각 |
| failed_at | TIMESTAMP WITH TIME ZONE | - | - | 실패 시각 |
| **결과** |
| error_message | TEXT | - | - | 에러 메시지 |
| error_code | VARCHAR(50) | - | - | 에러 코드 |
| result | JSONB | - | - | 작업 결과 데이터 |
| metadata | JSONB | '{}'::jsonb | - | 작업 메타데이터 |
| **타임스탬프** |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 작업 생성일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 상태 수정일 |

## 10. browser_sessions 테이블 - 브라우저 세션 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| id | UUID | gen_random_uuid() | PRIMARY KEY | 세션 고유 ID |
| platform | platform_type | - | NOT NULL, ENUM | 플랫폼 종류 |
| platform_store_id | UUID | - | FK | 관련 매장 ID |
| session_data | TEXT | - | - | 암호화된 세션 데이터 |
| last_login_at | TIMESTAMP WITH TIME ZONE | - | - | 마지막 로그인 |
| last_success_at | TIMESTAMP WITH TIME ZONE | - | - | 마지막 성공 |
| fail_count | INT | 0 | - | 실패 횟수 |
| is_active | BOOLEAN | true | - | 활성 상태 |
| expires_at | TIMESTAMP WITH TIME ZONE | - | - | 만료 시각 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 생성일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 수정일 |

## 11. browser_profiles 테이블 - 브라우저 프로필 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| id | UUID | gen_random_uuid() | PRIMARY KEY | 프로필 고유 ID |
| user_id | UUID | - | NOT NULL, FK | 사용자 ID |
| platform | platform_type | - | NOT NULL, ENUM | 플랫폼 종류 |
| profile_name | VARCHAR(100) | - | NOT NULL | 프로필 이름 |
| profile_path | TEXT | - | NOT NULL | 브라우저 프로필 경로 |
| session_data | TEXT | - | - | 암호화된 쿠키 데이터 |
| last_used_at | TIMESTAMP WITH TIME ZONE | - | - | 마지막 사용 시각 |
| is_active | BOOLEAN | true | - | 활성 상태 |
| metadata | JSONB | '{}'::jsonb | - | 추가 메타데이터 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 생성일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 수정일 |

## 12. payments 테이블 - 결제 정보

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| id | UUID | gen_random_uuid() | PRIMARY KEY | 결제 고유 ID |
| user_id | UUID | - | NOT NULL, FK | 결제자 ID |
| toss_payment_key | VARCHAR(200) | - | UNIQUE | 토스 페이먼트 키 |
| toss_order_id | VARCHAR(200) | - | UNIQUE | 토스 주문 ID |
| plan | subscription_plan | - | NOT NULL, ENUM | 구독 요금제 |
| amount | INT | - | NOT NULL | 결제 금액 |
| currency | VARCHAR(3) | 'KRW' | - | 통화 |
| status | VARCHAR(50) | - | NOT NULL | 결제 상태 |
| method | VARCHAR(50) | - | - | 결제 수단 |
| billing_cycle | VARCHAR(20) | - | - | 결제 주기 |
| next_billing_date | DATE | - | - | 다음 결제일 |
| failed_reason | TEXT | - | - | 결제 실패 사유 |
| raw_webhook | JSONB | - | - | 원본 웹훅 데이터 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 결제일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 수정일 |

## 13. notifications 테이블 - 알림 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| id | UUID | gen_random_uuid() | PRIMARY KEY | 알림 고유 ID |
| user_id | UUID | - | FK | 수신자 사용자 ID |
| platform_store_id | UUID | - | FK | 관련 매장 ID |
| type | VARCHAR(50) | - | NOT NULL | 알림 타입 |
| template_id | VARCHAR(100) | - | - | 템플릿 ID |
| recipient | VARCHAR(255) | - | NOT NULL | 수신자 |
| subject | VARCHAR(255) | - | - | 제목 |
| content | TEXT | - | - | 내용 |
| status | VARCHAR(50) | 'pending' | - | 발송 상태 |
| sent_at | TIMESTAMP WITH TIME ZONE | - | - | 발송 완료 시각 |
| failed_at | TIMESTAMP WITH TIME ZONE | - | - | 발송 실패 시각 |
| failure_reason | TEXT | - | - | 발송 실패 사유 |
| metadata | JSONB | '{}'::jsonb | - | 추가 메타데이터 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 생성일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 수정일 |

## 14. audit_logs 테이블 - 감사 로그

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| id | UUID | gen_random_uuid() | PRIMARY KEY | 로그 고유 ID |
| user_id | UUID | - | FK | 액션 수행자 |
| action | VARCHAR(100) | - | NOT NULL | 수행 액션 |
| table_name | VARCHAR(100) | - | - | 대상 테이블 |
| record_id | UUID | - | - | 대상 레코드 ID |
| old_values | JSONB | - | - | 변경 전 값 |
| new_values | JSONB | - | - | 변경 후 값 |
| ip_address | INET | - | - | IP 주소 |
| user_agent | TEXT | - | - | 사용자 에이전트 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 액션 시각 |

## 15. qr_codes 테이블 - QR 코드 관리

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| id | UUID | gen_random_uuid() | PRIMARY KEY | QR 코드 고유 ID |
| platform_store_id | UUID | - | NOT NULL, FK | 매장 ID |
| code | VARCHAR(100) | - | UNIQUE NOT NULL | QR 코드 값 |
| name | VARCHAR(100) | - | - | QR 코드 이름 |
| description | TEXT | - | - | 설명 |
| redirect_url | TEXT | - | - | 리다이렉트 URL |
| scan_count | INT | 0 | - | 스캔 횟수 |
| is_active | BOOLEAN | true | - | 활성 상태 |
| expires_at | TIMESTAMP WITH TIME ZONE | - | - | 만료 시각 |
| metadata | JSONB | '{}'::jsonb | - | 메타데이터 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 생성일 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 수정일 |

## 16. rankings 테이블 - 검색 순위 추적

| 컬럼명 | 타입 | 기본값 | 제약조건 | 역할 |
|--------|------|--------|----------|------|
| id | UUID | gen_random_uuid() | PRIMARY KEY | 순위 기록 고유 ID |
| platform_store_id | UUID | - | NOT NULL, FK | 매장 ID |
| keyword | VARCHAR(100) | - | NOT NULL | 검색 키워드 |
| rank | INT | - | - | 순위 |
| total_results | INT | - | - | 전체 검색 결과 수 |
| checked_at | TIMESTAMP WITH TIME ZONE | - | NOT NULL | 확인 시각 |
| metadata | JSONB | '{}'::jsonb | - | 메타데이터 |
| created_at | TIMESTAMP WITH TIME ZONE | NOW() | - | 생성일 |

## 주요 변경사항 요약

**추가된 컬럼들:**

1. **reviews_baemin**:
   - `requires_approval` (사장님 승인 필요 여부)
   - `failure_reason` (답글 발송 실패 사유)
   - `scheduled_reply_date` (답글 예약 발송 시각)

2. **reviews_yogiyo**:
   - `requires_approval` (사장님 승인 필요 여부)

3. **reviews_coupangeats**:
   - `requires_approval` (사장님 승인 필요 여부)
   - `scheduled_reply_date` (답글 예약 발송 시각)

이제 모든 플랫폼에서 일관된 리뷰 관리 기능을 사용할 수 있습니다.