# 🔌 API 레퍼런스

## 📋 개요

우리가게 도우미 API는 **RESTful** 설계 원칙을 따르며, **JSON** 형태의 데이터를 주고받습니다. 모든 API는 **JWT 토큰 기반 인증**을 사용합니다.

## 🌐 기본 정보

### Base URL
```
Development: http://localhost:8000/api/v1
Production:  https://api.storehelper.com/api/v1
```

### 인증
```http
Authorization: Bearer {JWT_TOKEN}
```

### 공통 헤더
```http
Content-Type: application/json
Accept: application/json
User-Agent: StoreHelper-Client/1.0
```

## 🔐 인증 API

### POST /auth/login
사용자 로그인

**요청**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "remember_me": false
}
```

**응답**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_uuid",
    "email": "user@example.com",
    "name": "홍길동",
    "subscription_tier": "basic"
  }
}
```

### POST /auth/register
사용자 회원가입

**요청**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "name": "신규 사용자",
  "phone": "010-1234-5678",
  "business_number": "123-45-67890"
}
```

**응답**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "new_user_uuid",
    "email": "newuser@example.com",
    "name": "신규 사용자",
    "subscription_tier": "free"
  }
}
```

### POST /auth/refresh
토큰 갱신

**요청**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**응답**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## 👤 사용자 관리 API

### GET /users/me
현재 사용자 정보 조회

**응답**
```json
{
  "id": "user_uuid",
  "email": "user@example.com",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "business_number": "123-45-67890",
  "subscription": {
    "tier": "basic",
    "start_date": "2024-08-01T00:00:00Z",
    "end_date": "2024-09-01T00:00:00Z",
    "auto_renewal": true,
    "features": ["basic_analytics", "auto_reply", "email_support"]
  },
  "settings": {
    "notifications_enabled": true,
    "email_notifications": true,
    "sms_notifications": false,
    "language": "ko",
    "timezone": "Asia/Seoul"
  },
  "stats": {
    "total_stores": 2,
    "total_reviews": 156,
    "this_month_reviews": 45,
    "reply_rate": 85.5
  },
  "created_at": "2024-07-01T10:30:00Z",
  "updated_at": "2024-08-13T14:25:00Z"
}
```

### PUT /users/me
사용자 정보 수정

**요청**
```json
{
  "name": "홍길동",
  "phone": "010-9876-5432",
  "business_number": "987-65-43210"
}
```

### PUT /users/settings
사용자 설정 수정

**요청**
```json
{
  "notifications_enabled": true,
  "email_notifications": true,
  "sms_notifications": false,
  "language": "ko",
  "timezone": "Asia/Seoul"
}
```

## 🏪 매장 관리 API

### GET /stores
매장 목록 조회

**쿼리 파라미터**
- `skip`: 건너뛸 개수 (기본값: 0)
- `limit`: 가져올 개수 (기본값: 100, 최대: 100)

**응답**
```json
[
  {
    "id": "store_uuid",
    "name": "테스트 카페",
    "platform": "naver",
    "platform_store_id": "12345",
    "address": "서울시 강남구 테헤란로 123",
    "category": "카페",
    "phone": "02-1234-5678",
    "status": "active",
    "menu_items": [
      {"name": "아메리카노", "price": 4500},
      {"name": "카페라떼", "price": 5000}
    ],
    "keywords": ["맛있는", "친절한", "깨끗한"],
    "operating_hours": {
      "monday": {"open": "08:00", "close": "22:00"},
      "tuesday": {"open": "08:00", "close": "22:00"}
    },
    "is_crawling_enabled": true,
    "is_auto_reply_enabled": true,
    "stats": {
      "total_reviews": 156,
      "average_rating": 4.3,
      "reply_rate": 85.5
    },
    "last_crawled_at": "2024-08-13T14:30:00Z",
    "created_at": "2024-07-01T10:00:00Z",
    "updated_at": "2024-08-13T14:30:00Z"
  }
]
```

### POST /stores
매장 등록

**요청**
```json
{
  "name": "새로운 카페",
  "platform": "naver",
  "platform_store_id": "67890",
  "address": "서울시 서초구 강남대로 456",
  "category": "카페",
  "phone": "02-9876-5432",
  "menu_items": [
    {"name": "아메리카노", "price": 4000},
    {"name": "카페라떼", "price": 4500}
  ],
  "keywords": ["신선한", "빠른", "저렴한"]
}
```

**응답 (201 Created)**
```json
{
  "id": "new_store_uuid",
  "name": "새로운 카페",
  "platform": "naver",
  "platform_store_id": "67890",
  "address": "서울시 서초구 강남대로 456",
  "category": "카페",
  "phone": "02-9876-5432",
  "status": "pending",
  "menu_items": [
    {"name": "아메리카노", "price": 4000},
    {"name": "카페라떼", "price": 4500}
  ],
  "keywords": ["신선한", "빠른", "저렴한"],
  "is_crawling_enabled": true,
  "is_auto_reply_enabled": true,
  "stats": {
    "total_reviews": 0,
    "average_rating": 0.0,
    "reply_rate": 0.0
  },
  "created_at": "2024-08-13T15:00:00Z",
  "updated_at": "2024-08-13T15:00:00Z"
}
```

### GET /stores/{store_id}
매장 상세 조회

**응답**
```json
{
  "id": "store_uuid",
  "name": "테스트 카페",
  "platform": "naver",
  "platform_store_id": "12345",
  "address": "서울시 강남구 테헤란로 123",
  "category": "카페",
  "phone": "02-1234-5678",
  "status": "active",
  "menu_items": [
    {"name": "아메리카노", "price": 4500},
    {"name": "카페라떼", "price": 5000}
  ],
  "keywords": ["맛있는", "친절한", "깨끗한"],
  "operating_hours": {
    "monday": {"open": "08:00", "close": "22:00"},
    "tuesday": {"open": "08:00", "close": "22:00"}
  },
  "is_crawling_enabled": true,
  "is_auto_reply_enabled": true,
  "stats": {
    "total_reviews": 156,
    "average_rating": 4.3,
    "reply_rate": 85.5
  },
  "last_crawled_at": "2024-08-13T14:30:00Z",
  "created_at": "2024-07-01T10:00:00Z",
  "updated_at": "2024-08-13T14:30:00Z"
}
```

### PUT /stores/{store_id}
매장 정보 수정

**요청**
```json
{
  "name": "수정된 카페명",
  "phone": "02-1111-2222",
  "operating_hours": {
    "monday": {"open": "09:00", "close": "21:00"},
    "tuesday": {"open": "09:00", "close": "21:00"}
  },
  "is_crawling_enabled": true,
  "is_auto_reply_enabled": false
}
```

### POST /stores/{store_id}/crawl
매장 크롤링 수동 실행

**응답**
```json
{
  "message": "크롤링이 시작되었습니다.",
  "store_id": "store_uuid",
  "status": "started"
}
```

## 📝 리뷰 관리 API

### GET /reviews
리뷰 목록 조회

**쿼리 파라미터**
- `store_id`: 매장 ID (선택)
- `sentiment`: 감정 (positive/negative/neutral, 선택)
- `has_reply`: 답글 여부 (true/false, 선택)
- `requires_check`: 확인 필요 여부 (true/false, 선택)
- `date_from`: 시작 날짜 (YYYY-MM-DD, 선택)
- `date_to`: 종료 날짜 (YYYY-MM-DD, 선택)
- `skip`: 건너뛸 개수 (기본값: 0)
- `limit`: 가져올 개수 (기본값: 50, 최대: 100)

**응답**
```json
[
  {
    "id": "review_uuid",
    "store_id": "store_uuid",
    "platform_review_id": "naver_12345",
    "reviewer_name": "김고객",
    "rating": 5,
    "content": "정말 맛있었어요! 직원분들도 친절하시고 분위기도 좋네요.",
    "images": [],
    "sentiment": "positive",
    "sentiment_score": 0.8,
    "keywords": ["맛있는", "친절한", "분위기"],
    "reply_content": "소중한 리뷰 감사합니다. 앞으로도 최선을 다하겠습니다!",
    "reply_status": "replied",
    "requires_owner_check": false,
    "review_date": "2024-08-12T16:30:00Z",
    "created_at": "2024-08-12T17:00:00Z"
  },
  {
    "id": "review_uuid_2",
    "store_id": "store_uuid",
    "platform_review_id": "naver_12346",
    "reviewer_name": "이고객",
    "rating": 2,
    "content": "서비스가 좀 아쉬웠어요. 음식은 괜찮았는데 직원이 불친절했습니다.",
    "images": [],
    "sentiment": "negative",
    "sentiment_score": -0.6,
    "keywords": ["불친절", "서비스"],
    "reply_content": null,
    "reply_status": "pending",
    "requires_owner_check": true,
    "review_date": "2024-08-13T10:15:00Z",
    "created_at": "2024-08-13T10:30:00Z"
  }
]
```

### GET /reviews/{review_id}
리뷰 상세 조회

**응답**
```json
{
  "id": "review_uuid",
  "store_id": "store_uuid",
  "platform_review_id": "naver_12345",
  "reviewer_name": "김고객",
  "rating": 5,
  "content": "정말 맛있었어요! 직원분들도 친절하시고 분위기도 좋네요.",
  "images": [],
  "sentiment": "positive",
  "sentiment_score": 0.8,
  "keywords": ["맛있는", "친절한", "분위기"],
  "reply_content": "소중한 리뷰 감사합니다. 앞으로도 최선을 다하겠습니다!",
  "reply_status": "replied",
  "requires_owner_check": false,
  "review_date": "2024-08-12T16:30:00Z",
  "created_at": "2024-08-12T17:00:00Z"
}
```

### POST /reviews/{review_id}/reply
리뷰 답글 작성

**요청**
```json
{
  "content": "소중한 리뷰 감사합니다. 지적해주신 부분 개선하도록 노력하겠습니다.",
  "auto_post": true
}
```

**응답**
```json
{
  "message": "답글이 성공적으로 작성되었습니다.",
  "review_id": "review_uuid",
  "auto_post": true
}
```

### POST /reviews/{review_id}/check-complete
리뷰 확인 완료 처리

**응답**
```json
{
  "message": "리뷰 확인이 완료되었습니다."
}
```

## 📊 분석 API

### GET /analytics/dashboard
대시보드 통계 조회

**쿼리 파라미터**
- `store_id`: 매장 ID (선택)
- `period`: 기간 (week/month/quarter/year, 기본값: month)

**응답**
```json
{
  "overview": {
    "total_reviews": 156,
    "new_reviews": 12,
    "average_rating": 4.3,
    "rating_distribution": {
      "5": 89,
      "4": 34,
      "3": 18,
      "2": 10,
      "1": 5
    },
    "sentiment_distribution": {
      "positive": 89,
      "neutral": 45,
      "negative": 22
    },
    "reply_rate": 85.5,
    "average_reply_time_hours": 2.5
  },
  "recent_trends": {
    "period": "month",
    "data_points": [
      {
        "date": "2024-08-06",
        "value": 4.1,
        "count": 8
      },
      {
        "date": "2024-08-07",
        "value": 4.2,
        "count": 9
      }
    ],
    "trend_direction": "up",
    "growth_rate": 12.5
  },
  "top_keywords": [
    {"keyword": "맛있는", "count": 45, "sentiment": "positive"},
    {"keyword": "친절한", "count": 32, "sentiment": "positive"},
    {"keyword": "깨끗한", "count": 28, "sentiment": "positive"}
  ],
  "recommendations": [
    {
      "priority": "high",
      "category": "service",
      "title": "응답 시간 개선",
      "description": "리뷰 답글 평균 응답 시간을 2시간 이내로 단축하여 고객 만족도를 향상시키세요.",
      "expected_impact": "고객 만족도 15% 향상",
      "implementation_difficulty": "쉬움"
    }
  ],
  "alerts": [
    {
      "type": "warning",
      "message": "이번 주 부정적 리뷰가 20% 증가했습니다.",
      "action": "서비스 품질 점검이 필요합니다."
    }
  ]
}
```

### GET /analytics/trends/rating
평점 트렌드 분석

**쿼리 파라미터**
- `store_id`: 매장 ID (선택)
- `period`: 기간 (week/month/quarter/year, 기본값: month)
- `interval`: 간격 (day/week/month, 기본값: day)

**응답**
```json
{
  "period": "month",
  "data_points": [
    {
      "date": "2024-08-01",
      "value": 4.0,
      "count": 5
    },
    {
      "date": "2024-08-02",
      "value": 4.1,
      "count": 3
    }
  ],
  "trend_direction": "up",
  "growth_rate": 8.5
}
```

### GET /analytics/keywords
키워드 분석

**쿼리 파라미터**
- `store_id`: 매장 ID (선택)
- `period`: 기간 (week/month/quarter/year, 기본값: month)
- `limit`: 개수 제한 (기본값: 20, 최대: 100)

**응답**
```json
{
  "positive_keywords": [
    {"keyword": "맛있는", "count": 45, "growth": 12.5},
    {"keyword": "친절한", "count": 32, "growth": 8.3},
    {"keyword": "깨끗한", "count": 28, "growth": 15.2}
  ],
  "negative_keywords": [
    {"keyword": "느린", "count": 8, "growth": -5.2},
    {"keyword": "시끄러운", "count": 5, "growth": 2.1}
  ],
  "trending_keywords": [
    {"keyword": "분위기", "count": 22, "growth": 45.2},
    {"keyword": "가성비", "count": 18, "growth": 32.1}
  ],
  "keyword_trends": {
    "맛있는": [
      {
        "date": "2024-08-06",
        "value": 17.0,
        "count": 17
      },
      {
        "date": "2024-08-07",
        "value": 18.0,
        "count": 18
      }
    ]
  }
}
```

## 💳 결제 API

### GET /payments/plans
구독 플랜 목록 조회

**응답**
```json
[
  {
    "tier": "free",
    "name": "무료 체험",
    "description": "서비스를 체험해보세요",
    "monthly_price": 0,
    "yearly_price": 0,
    "features": [
      "매장 1개 등록",
      "월 10개 리뷰 분석",
      "기본 AI 답글",
      "이메일 지원"
    ],
    "limits": {
      "max_stores": 1,
      "monthly_reviews": 10,
      "monthly_replies": 10,
      "analytics_history_days": 7
    },
    "popular": false
  },
  {
    "tier": "basic",
    "name": "베이직",
    "description": "소규모 매장에 적합",
    "monthly_price": 29000,
    "yearly_price": 290000,
    "features": [
      "매장 3개 등록",
      "월 100개 리뷰 분석",
      "AI 자동 답글",
      "기본 분석 리포트",
      "이메일 지원"
    ],
    "limits": {
      "max_stores": 3,
      "monthly_reviews": 100,
      "monthly_replies": 100,
      "analytics_history_days": 30
    },
    "popular": true
  }
]
```

### GET /payments/subscription
현재 구독 정보 조회

**응답**
```json
{
  "tier": "basic",
  "name": "베이직",
  "start_date": "2024-07-15T00:00:00Z",
  "end_date": "2024-08-15T00:00:00Z",
  "auto_renewal": true,
  "payment_method": "카드 (**** 1234)",
  "next_billing_date": "2024-08-15T00:00:00Z",
  "remaining_days": 25,
  "usage": {
    "stores": 1,
    "monthly_reviews": 25,
    "monthly_replies": 20
  },
  "limits": {
    "max_stores": 3,
    "monthly_reviews": 100,
    "monthly_replies": 100
  }
}
```

### POST /payments/subscription/change
구독 플랜 변경

**요청**
```json
{
  "target_tier": "premium",
  "billing_cycle": "monthly",
  "payment_method": "card",
  "auto_renewal": true
}
```

**응답**
```json
{
  "message": "구독 플랜 변경이 처리되었습니다.",
  "new_tier": "premium",
  "billing_cycle": "monthly",
  "effective_date": "2024-08-13T15:30:00Z"
}
```

### GET /payments/history
결제 내역 조회

**쿼리 파라미터**
- `skip`: 건너뛸 개수 (기본값: 0)
- `limit`: 가져올 개수 (기본값: 50, 최대: 100)

**응답**
```json
[
  {
    "id": "payment_uuid",
    "amount": 29000,
    "currency": "KRW",
    "description": "베이직 플랜 월 구독료",
    "status": "completed",
    "payment_method": "card",
    "transaction_id": "tx_12345",
    "billing_period_start": "2024-07-15",
    "billing_period_end": "2024-08-15",
    "created_at": "2024-07-10T10:00:00Z",
    "completed_at": "2024-07-10T10:01:23Z",
    "receipt_url": "https://example.com/receipts/payment_uuid.pdf"
  }
]
```

## ❌ 에러 응답

### 표준 에러 형식
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자 친화적인 에러 메시지",
    "details": "개발자용 상세 에러 정보",
    "timestamp": "2024-08-13T15:30:00Z",
    "path": "/api/v1/stores",
    "request_id": "req_12345"
  }
}
```

### 공통 에러 코드

| 코드 | HTTP 상태 | 설명 |
|------|-----------|------|
| `AUTHENTICATION_REQUIRED` | 401 | 인증이 필요합니다 |
| `INVALID_TOKEN` | 401 | 유효하지 않은 토큰입니다 |
| `TOKEN_EXPIRED` | 401 | 토큰이 만료되었습니다 |
| `PERMISSION_DENIED` | 403 | 권한이 없습니다 |
| `RESOURCE_NOT_FOUND` | 404 | 리소스를 찾을 수 없습니다 |
| `VALIDATION_ERROR` | 422 | 입력값 검증 실패 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 한도를 초과했습니다 |
| `INTERNAL_SERVER_ERROR` | 500 | 서버 내부 오류 |

### 입력값 검증 에러
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값이 올바르지 않습니다",
    "details": {
      "email": ["올바른 이메일 형식이 아닙니다"],
      "password": ["비밀번호는 최소 8자 이상이어야 합니다"]
    },
    "timestamp": "2024-08-13T15:30:00Z",
    "path": "/api/v1/auth/register",
    "request_id": "req_12345"
  }
}
```

## 📏 요청/응답 제한

### 요청 제한
- **요청 크기**: 최대 10MB
- **Rate Limiting**: 
  - 인증된 사용자: 1000 requests/hour
  - 인증되지 않은 사용자: 100 requests/hour
- **페이지네이션**: 최대 100개 항목

### 응답 형식
- **타임스탬프**: ISO 8601 형식 (UTC)
- **통화**: KRW (한국 원)
- **문자 인코딩**: UTF-8

## 🔧 SDK 및 클라이언트 라이브러리

### JavaScript/TypeScript
```bash
npm install @storehelper/api-client
```

```typescript
import { StoreHelperAPI } from '@storehelper/api-client';

const api = new StoreHelperAPI({
  baseURL: 'https://api.storehelper.com/api/v1',
  apiKey: 'your_api_key'
});

// 매장 목록 조회
const stores = await api.stores.list();

// 리뷰 목록 조회
const reviews = await api.reviews.list({
  store_id: 'store_uuid',
  sentiment: 'positive'
});
```

### Python
```bash
pip install storehelper-api
```

```python
from storehelper import StoreHelperAPI

api = StoreHelperAPI(
    base_url='https://api.storehelper.com/api/v1',
    api_key='your_api_key'
)

# 매장 목록 조회
stores = api.stores.list()

# 리뷰 목록 조회
reviews = api.reviews.list(
    store_id='store_uuid',
    sentiment='positive'
)
```

## 🔄 웹훅 (Webhooks)

### 이벤트 유형
- `review.created`: 새 리뷰 수집됨
- `review.replied`: 리뷰 답글 작성됨
- `store.stats_updated`: 매장 통계 업데이트됨
- `subscription.changed`: 구독 상태 변경됨

### 웹훅 페이로드 예시
```json
{
  "event": "review.created",
  "timestamp": "2024-08-13T15:30:00Z",
  "data": {
    "review_id": "review_uuid",
    "store_id": "store_uuid",
    "rating": 5,
    "sentiment": "positive",
    "requires_owner_check": false
  }
}
```

---

*API 사용법에 대한 자세한 예제는 [개발 가이드](DEVELOPMENT_GUIDE.md)를 참조하세요.*