# 🏗️ 시스템 아키텍처

## 📋 개요

우리가게 도우미는 **마이크로서비스 아키텍처**를 기반으로 설계된 확장 가능한 플랫폼입니다. 각 서버가 독립적인 역할을 담당하여 높은 가용성과 확장성을 제공합니다.

## 🎯 아키텍처 원칙

### 핵심 설계 원칙
1. **마이크로서비스**: 독립적 배포 및 스케일링
2. **비동기 처리**: 논블로킹 I/O로 높은 처리량 달성
3. **이벤트 드리븐**: 서비스 간 느슨한 결합
4. **상태 비저장**: 수평 확장 지원
5. **장애 격리**: 한 서비스 장애가 전체에 영향 최소화

### 품질 속성
- **성능**: 10,000 동시 사용자 지원
- **가용성**: 99.9% 업타임 보장
- **확장성**: 수평/수직 확장 지원
- **보안**: 다중 계층 보안 적용
- **유지보수성**: 모듈화된 구조

## 🏛️ 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[웹 브라우저]
        MOBILE[모바일 앱]
        API_CLIENT[API 클라이언트]
    end

    subgraph "CDN & Load Balancer"
        CDN[CloudFlare CDN]
        LB[Load Balancer]
    end

    subgraph "Application Layer"
        subgraph "서버 B - API Gateway"
            B1[API Server B-1]
            B2[API Server B-2]
            B3[API Server B-N]
        end

        subgraph "서버 A - AI & Crawling"
            A1[Crawler A-1]
            A2[AI Engine A-2]
            A3[Data Processor A-3]
        end

        subgraph "서버 C - Scheduler"
            C1[Job Scheduler]
            C2[Queue Manager]
            C3[Task Executor]
        end
    end

    subgraph "Message Queue"
        REDIS[Redis Cluster]
        CELERY[Celery Workers]
    end

    subgraph "Database Layer"
        SUPABASE[(Supabase PostgreSQL)]
        REPLICA[(Read Replica)]
    end

    subgraph "External Services"
        OPENAI[OpenAI GPT-4]
        NAVER[네이버 플레이스]
        KAKAO[카카오맵]
        GOOGLE[구글 마이 비즈니스]
        PAYMENT[결제 게이트웨이]
    end

    subgraph "Monitoring"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana]
        LOGS[로그 수집기]
    end

    WEB --> CDN
    MOBILE --> LB
    API_CLIENT --> LB
    CDN --> LB
    LB --> B1
    LB --> B2
    LB --> B3

    B1 --> SUPABASE
    B2 --> SUPABASE
    B3 --> REPLICA

    B1 --> REDIS
    A1 --> REDIS
    C1 --> REDIS

    A1 --> NAVER
    A1 --> KAKAO
    A1 --> GOOGLE
    A2 --> OPENAI
    
    B1 --> PAYMENT
    
    C1 --> CELERY
    CELERY --> A1
    CELERY --> A2

    PROMETHEUS --> B1
    PROMETHEUS --> A1
    PROMETHEUS --> C1
    GRAFANA --> PROMETHEUS
    LOGS --> B1
    LOGS --> A1
    LOGS --> C1
```

## 🖥️ 서버별 상세 아키텍처

### 🔌 서버 B - API Gateway & User Management

**역할**: 사용자 요청 처리, 인증, 매장 관리, 결제 처리

#### 기술 스택
- **Framework**: FastAPI 0.104+
- **Database ORM**: SQLAlchemy 2.0 (Async)
- **Authentication**: Supabase Auth + JWT
- **Validation**: Pydantic V2
- **Documentation**: OpenAPI/Swagger

#### 내부 구조
```mermaid
graph TB
    subgraph "API Layer"
        AUTH[Authentication API]
        USER[User Management API]
        STORE[Store Management API]
        REVIEW[Review Management API]
        ANALYTICS[Analytics API]
        PAYMENT[Payment API]
    end

    subgraph "Business Logic"
        AUTH_SERVICE[Auth Service]
        USER_SERVICE[User Service]
        STORE_SERVICE[Store Service]
        REVIEW_SERVICE[Review Service]
        ANALYTICS_SERVICE[Analytics Service]
        PAYMENT_SERVICE[Payment Service]
    end

    subgraph "Data Layer"
        USER_MODEL[User Model]
        STORE_MODEL[Store Model]
        REVIEW_MODEL[Review Model]
        PAYMENT_MODEL[Payment Model]
        KEYWORD_MODEL[Keyword Model]
    end

    subgraph "Middleware"
        CORS[CORS Middleware]
        RATE_LIMIT[Rate Limiting]
        LOGGING[Request Logging]
        AUTH_MW[Auth Middleware]
    end

    AUTH --> AUTH_SERVICE
    USER --> USER_SERVICE
    STORE --> STORE_SERVICE
    REVIEW --> REVIEW_SERVICE
    ANALYTICS --> ANALYTICS_SERVICE
    PAYMENT --> PAYMENT_SERVICE

    AUTH_SERVICE --> USER_MODEL
    USER_SERVICE --> USER_MODEL
    STORE_SERVICE --> STORE_MODEL
    REVIEW_SERVICE --> REVIEW_MODEL
    ANALYTICS_SERVICE --> KEYWORD_MODEL
    PAYMENT_SERVICE --> PAYMENT_MODEL
```

#### API 엔드포인트 구조
```
/api/v1/
├── auth/
│   ├── login
│   ├── register
│   ├── refresh
│   └── logout
├── users/
│   ├── me
│   ├── settings
│   └── subscription
├── stores/
│   ├── / (CRUD)
│   ├── {id}/stats
│   └── {id}/crawl
├── reviews/
│   ├── / (조회/필터링)
│   ├── {id}/reply
│   └── {id}/check-complete
├── analytics/
│   ├── dashboard
│   ├── trends/rating
│   ├── keywords
│   └── recommendations
└── payments/
    ├── plans
    ├── subscription
    ├── history
    └── methods
```

### 🤖 서버 A - AI & Crawling Engine

**역할**: 리뷰 크롤링, AI 답글 생성, 감정 분석

#### 기술 스택
- **Framework**: FastAPI + Asyncio
- **Crawling**: Playwright (Multi-browser)
- **AI**: OpenAI GPT-4, 사용자 정의 프롬프트
- **Queue**: Celery + Redis
- **Monitoring**: 실시간 성능 추적

#### 크롤링 아키텍처
```mermaid
graph TB
    subgraph "Crawling Controller"
        SCHEDULER[크롤링 스케줄러]
        QUEUE_MANAGER[큐 매니저]
        RATE_LIMITER[속도 제한기]
    end

    subgraph "Browser Pool"
        CHROME1[Chrome Instance 1]
        CHROME2[Chrome Instance 2]
        FIREFOX1[Firefox Instance 1]
        SAFARI1[Safari Instance 1]
    end

    subgraph "Platform Crawlers"
        NAVER_CRAWLER[네이버 크롤러]
        KAKAO_CRAWLER[카카오 크롤러]
        GOOGLE_CRAWLER[구글 크롤러]
    end

    subgraph "Data Processing"
        EXTRACTOR[데이터 추출기]
        VALIDATOR[데이터 검증기]
        DEDUPLICATOR[중복 제거기]
        ENRICHER[데이터 보강기]
    end

    subgraph "AI Processing"
        SENTIMENT[감정 분석]
        KEYWORD[키워드 추출]
        REPLY_GEN[답글 생성]
        QUALITY_CHECK[품질 검사]
    end

    SCHEDULER --> QUEUE_MANAGER
    QUEUE_MANAGER --> RATE_LIMITER
    RATE_LIMITER --> NAVER_CRAWLER
    RATE_LIMITER --> KAKAO_CRAWLER
    RATE_LIMITER --> GOOGLE_CRAWLER

    NAVER_CRAWLER --> CHROME1
    KAKAO_CRAWLER --> CHROME2
    GOOGLE_CRAWLER --> FIREFOX1

    NAVER_CRAWLER --> EXTRACTOR
    KAKAO_CRAWLER --> EXTRACTOR
    GOOGLE_CRAWLER --> EXTRACTOR

    EXTRACTOR --> VALIDATOR
    VALIDATOR --> DEDUPLICATOR
    DEDUPLICATOR --> ENRICHER

    ENRICHER --> SENTIMENT
    ENRICHER --> KEYWORD
    ENRICHER --> REPLY_GEN
    REPLY_GEN --> QUALITY_CHECK
```

#### AI 답글 생성 파이프라인
```mermaid
graph LR
    REVIEW[리뷰 입력] --> ANALYZE[감정 분석]
    ANALYZE --> CONTEXT[컨텍스트 구성]
    CONTEXT --> PROMPT[프롬프트 생성]
    PROMPT --> GPT4[GPT-4 API]
    GPT4 --> FILTER[필터링]
    FILTER --> VALIDATE[품질 검증]
    VALIDATE --> STORE[답글 저장]
    STORE --> APPROVE[승인 대기]
```

### ⏰ 서버 C - Task Scheduler & Automation

**역할**: 배치 작업 스케줄링, 자동화 워크플로우, 시스템 모니터링

#### 기술 스택
- **Scheduler**: Celery Beat + Redis
- **Task Queue**: Celery Workers
- **Monitoring**: Flower (Celery 모니터링)
- **Automation**: 사용자 정의 워크플로우

#### 스케줄링 아키텍처
```mermaid
graph TB
    subgraph "Scheduler Core"
        BEAT[Celery Beat]
        CRON[Cron Jobs]
        TRIGGER[이벤트 트리거]
    end

    subgraph "Task Types"
        CRAWL_TASK[크롤링 작업]
        AI_TASK[AI 답글 생성]
        ANALYTICS_TASK[분석 작업]
        CLEANUP_TASK[정리 작업]
        NOTIFICATION_TASK[알림 발송]
    end

    subgraph "Worker Pool"
        WORKER1[Worker 1]
        WORKER2[Worker 2]
        WORKER3[Worker 3]
        WORKERN[Worker N]
    end

    subgraph "Task Queue"
        HIGH_PRIORITY[고우선순위 큐]
        NORMAL_PRIORITY[일반 큐]
        LOW_PRIORITY[저우선순위 큐]
    end

    BEAT --> CRAWL_TASK
    CRON --> ANALYTICS_TASK
    TRIGGER --> NOTIFICATION_TASK

    CRAWL_TASK --> HIGH_PRIORITY
    AI_TASK --> HIGH_PRIORITY
    ANALYTICS_TASK --> NORMAL_PRIORITY
    CLEANUP_TASK --> LOW_PRIORITY
    NOTIFICATION_TASK --> NORMAL_PRIORITY

    HIGH_PRIORITY --> WORKER1
    NORMAL_PRIORITY --> WORKER2
    LOW_PRIORITY --> WORKER3
```

#### 자동화 워크플로우
```mermaid
graph TD
    START[시작] --> SCHEDULE{스케줄 시간?}
    SCHEDULE -->|매시간| CRAWL[리뷰 크롤링]
    SCHEDULE -->|새 리뷰 발견| AI_REPLY[AI 답글 생성]
    SCHEDULE -->|매일 오전 9시| DAILY_REPORT[일일 리포트]
    SCHEDULE -->|매주 월요일| WEEKLY_ANALYSIS[주간 분석]
    
    CRAWL --> CHECK_NEW{새 리뷰?}
    CHECK_NEW -->|Yes| ANALYZE[감정 분석]
    CHECK_NEW -->|No| END[종료]
    
    ANALYZE --> NEGATIVE{부정적?}
    NEGATIVE -->|Yes| URGENT_NOTIFY[긴급 알림]
    NEGATIVE -->|No| AI_REPLY
    
    AI_REPLY --> REVIEW_REPLY[답글 검토 요청]
    URGENT_NOTIFY --> REVIEW_REPLY
    REVIEW_REPLY --> END
    
    DAILY_REPORT --> EMAIL[이메일 발송]
    WEEKLY_ANALYSIS --> DASHBOARD[대시보드 업데이트]
    EMAIL --> END
    DASHBOARD --> END
```

## 💾 데이터 아키텍처

### 데이터베이스 설계

#### 주 데이터베이스 (Supabase PostgreSQL)
```mermaid
erDiagram
    users ||--o{ stores : owns
    users ||--o{ subscriptions : has
    users ||--o{ payments : makes
    users ||--o{ notifications : receives
    users ||--o{ api_keys : generates

    stores ||--o{ reviews : receives
    stores ||--o{ keywords : analyzed_for
    stores ||--o{ crawlingsession : crawled_in

    reviews ||--o{ review_replies : has
    reviews }o--|| crawlingsession : found_in

    subscriptions ||--o{ payments : paid_with

    users {
        string id PK
        string email UK
        string name
        string subscription_tier
        datetime created_at
        datetime updated_at
    }

    stores {
        string id PK
        string user_id FK
        string name
        string platform
        string platform_store_id
        string status
        json settings
        datetime created_at
    }

    reviews {
        string id PK
        string store_id FK
        string platform_review_id
        string reviewer_name
        int rating
        text content
        string sentiment
        float sentiment_score
        json keywords
        datetime review_date
        datetime crawled_at
    }

    review_replies {
        string id PK
        string review_id FK
        text content
        string reply_type
        string status
        boolean is_posted_to_platform
        datetime created_at
    }
```

#### 데이터 파티셔닝 전략
```sql
-- 리뷰 테이블 월별 파티셔닝
CREATE TABLE reviews_2024_08 PARTITION OF reviews
FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');

-- 크롤링 세션 일별 파티셔닝
CREATE TABLE crawlingsession_daily PARTITION OF crawlingsession
FOR VALUES FROM ('2024-08-13') TO ('2024-08-14');
```

#### 인덱스 최적화
```sql
-- 복합 인덱스 (성능 최적화)
CREATE INDEX idx_reviews_store_date ON reviews(store_id, review_date DESC);
CREATE INDEX idx_keywords_store_trend ON keywords(store_id, is_trending, this_week_count DESC);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = false;

-- 부분 인덱스 (저장 공간 최적화)
CREATE INDEX idx_reviews_negative ON reviews(store_id, sentiment_score) WHERE sentiment_score < -0.3;
```

### 캐싱 전략

#### Redis 캐시 계층
```mermaid
graph TB
    subgraph "Application"
        API[API 서버]
        CRAWLER[크롤러]
    end

    subgraph "Cache Layer"
        L1[L1: Application Cache]
        L2[L2: Redis Cache]
        L3[L3: Database Query Cache]
    end

    subgraph "Storage"
        DB[(PostgreSQL)]
    end

    API --> L1
    L1 --> L2
    L2 --> L3
    L3 --> DB

    CRAWLER --> L2
```

#### 캐시 정책
```yaml
cache_policies:
  user_session:
    ttl: 3600  # 1시간
    type: "string"
    pattern: "session:{user_id}"
  
  store_stats:
    ttl: 1800  # 30분
    type: "hash"
    pattern: "stats:{store_id}:{date}"
  
  api_rate_limit:
    ttl: 60    # 1분
    type: "counter"
    pattern: "rate:{ip}:{endpoint}"
  
  crawling_lock:
    ttl: 3600  # 1시간
    type: "lock"
    pattern: "crawl:{store_id}"
```

## 🔒 보안 아키텍처

### 다중 계층 보안

```mermaid
graph TB
    subgraph "Network Security"
        WAF[Web Application Firewall]
        DDoS[DDoS Protection]
        CDN_SEC[CDN Security]
    end

    subgraph "Application Security"
        JWT[JWT Token]
        RATE_LIMIT[Rate Limiting]
        INPUT_VAL[Input Validation]
        SQL_INJ[SQL Injection Prevention]
    end

    subgraph "Data Security"
        ENCRYPT[Data Encryption]
        BACKUP_ENC[Backup Encryption]
        KEY_MGMT[Key Management]
    end

    subgraph "Infrastructure Security"
        VPC[Virtual Private Cloud]
        FIREWALL[Network Firewall]
        SSL[SSL/TLS]
    end

    WAF --> JWT
    DDoS --> RATE_LIMIT
    CDN_SEC --> INPUT_VAL
    
    JWT --> ENCRYPT
    RATE_LIMIT --> BACKUP_ENC
    INPUT_VAL --> KEY_MGMT
    
    ENCRYPT --> VPC
    BACKUP_ENC --> FIREWALL
    KEY_MGMT --> SSL
```

### 인증 및 권한 시스템

#### JWT 토큰 구조
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": "uuid",
    "email": "user@example.com",
    "subscription_tier": "premium",
    "permissions": ["read", "write", "admin"],
    "iat": 1692000000,
    "exp": 1692003600
  }
}
```

#### 권한 매트릭스
| 역할 | 매장 관리 | 리뷰 답글 | 분석 조회 | 결제 관리 | 시스템 설정 |
|------|-----------|-----------|-----------|-----------|-------------|
| **Free** | 1개 | ❌ | 기본 | ❌ | ❌ |
| **Basic** | 3개 | ✅ | 기본 | ✅ | ❌ |
| **Premium** | 10개 | ✅ | 고급 | ✅ | ❌ |
| **Enterprise** | 무제한 | ✅ | 전체 | ✅ | ✅ |
| **Admin** | 무제한 | ✅ | 전체 | ✅ | ✅ |

## 📊 성능 및 확장성

### 성능 목표

| 메트릭 | 목표 | 현재 | 측정 방법 |
|--------|------|------|-----------|
| **API 응답 시간** | < 200ms | TBD | P95 레이턴시 |
| **동시 사용자** | 10,000명 | TBD | 로드 테스트 |
| **크롤링 처리량** | 3,000/시간 | TBD | 수집 메트릭 |
| **데이터베이스 쿼리** | < 50ms | TBD | 평균 쿼리 시간 |
| **가용성** | 99.9% | TBD | 업타임 모니터링 |

### 확장성 전략

#### 수평 확장 (Scale Out)
```mermaid
graph TB
    subgraph "Current Setup"
        LB1[Load Balancer]
        API1[API Server 1]
        API2[API Server 2]
        DB1[(Master DB)]
        REDIS1[Redis 1]
    end

    subgraph "Scaled Setup"
        LB2[Load Balancer Cluster]
        API3[API Server 1-N]
        CRAWLER1[Crawler 1-N]
        DB2[(Master + Replicas)]
        REDIS2[Redis Cluster]
    end

    LB1 --> API1
    LB1 --> API2
    API1 --> DB1
    API2 --> DB1
    API1 --> REDIS1
    API2 --> REDIS1

    LB2 --> API3
    LB2 --> CRAWLER1
    API3 --> DB2
    CRAWLER1 --> DB2
    API3 --> REDIS2
    CRAWLER1 --> REDIS2
```

#### 수직 확장 (Scale Up)
```yaml
server_specs:
  development:
    cpu: "2 cores"
    memory: "4GB"
    storage: "50GB SSD"
  
  production_small:
    cpu: "4 cores"
    memory: "16GB"
    storage: "200GB SSD"
  
  production_large:
    cpu: "16 cores"
    memory: "64GB"
    storage: "1TB NVMe"
  
  enterprise:
    cpu: "32 cores"
    memory: "128GB"
    storage: "2TB NVMe"
```

## 🔄 데이터 흐름

### 실시간 데이터 파이프라인

```mermaid
graph LR
    subgraph "Data Sources"
        NAVER[네이버 플레이스]
        KAKAO[카카오맵]
        GOOGLE[구글]
        USER_INPUT[사용자 입력]
    end

    subgraph "Ingestion Layer"
        CRAWLER[크롤러]
        API_GATEWAY[API Gateway]
        WEBHOOK[웹훅]
    end

    subgraph "Processing Layer"
        QUEUE[Message Queue]
        PROCESSOR[Data Processor]
        AI_ENGINE[AI Engine]
    end

    subgraph "Storage Layer"
        POSTGRES[(PostgreSQL)]
        REDIS[(Redis Cache)]
        S3[(File Storage)]
    end

    subgraph "Analytics Layer"
        ANALYTICS[분석 엔진]
        REPORTING[리포팅]
        DASHBOARD[대시보드]
    end

    NAVER --> CRAWLER
    KAKAO --> CRAWLER
    GOOGLE --> CRAWLER
    USER_INPUT --> API_GATEWAY

    CRAWLER --> QUEUE
    API_GATEWAY --> QUEUE
    WEBHOOK --> QUEUE

    QUEUE --> PROCESSOR
    PROCESSOR --> AI_ENGINE
    PROCESSOR --> POSTGRES
    PROCESSOR --> REDIS

    AI_ENGINE --> POSTGRES
    POSTGRES --> ANALYTICS
    REDIS --> ANALYTICS

    ANALYTICS --> REPORTING
    ANALYTICS --> DASHBOARD
```

### 배치 처리 워크플로우

```mermaid
graph TD
    START[배치 시작] --> EXTRACT[데이터 추출]
    EXTRACT --> TRANSFORM[데이터 변환]
    TRANSFORM --> LOAD[데이터 적재]
    LOAD --> ANALYZE[분석 실행]
    ANALYZE --> REPORT[리포트 생성]
    REPORT --> NOTIFY[알림 발송]
    NOTIFY --> CLEANUP[정리 작업]
    CLEANUP --> END[완료]

    EXTRACT --> ERROR_HANDLER[에러 처리]
    TRANSFORM --> ERROR_HANDLER
    LOAD --> ERROR_HANDLER
    ANALYZE --> ERROR_HANDLER
    ERROR_HANDLER --> RETRY{재시도?}
    RETRY -->|Yes| EXTRACT
    RETRY -->|No| ALERT[관리자 알림]
    ALERT --> END
```

## 🚨 장애 대응 및 복구

### 장애 시나리오 및 대응

| 장애 유형 | 감지 시간 | 복구 목표 | 대응 방법 |
|-----------|-----------|-----------|-----------|
| **API 서버 다운** | < 1분 | < 5분 | 로드밸런서 자동 라우팅 |
| **데이터베이스 장애** | < 2분 | < 10분 | 읽기 전용 모드 + 복제본 승격 |
| **크롤링 서비스 중단** | < 5분 | < 30분 | 백업 크롤러 활성화 |
| **외부 API 장애** | < 10분 | 외부 복구 시까지 | 캐시된 데이터 사용 |

### 백업 및 복구 전략

```mermaid
graph TB
    subgraph "Primary Site"
        PRIMARY_DB[(Primary DB)]
        PRIMARY_APP[Primary App]
        PRIMARY_REDIS[Primary Redis]
    end

    subgraph "Backup Systems"
        REPLICA_DB[(Replica DB)]
        BACKUP_APP[Standby App]
        BACKUP_REDIS[Backup Redis]
    end

    subgraph "External Backup"
        S3_BACKUP[(S3 Backup)]
        POINT_IN_TIME[Point-in-time Recovery]
    end

    PRIMARY_DB -.->|실시간 복제| REPLICA_DB
    PRIMARY_APP -.->|동기화| BACKUP_APP
    PRIMARY_REDIS -.->|백업| BACKUP_REDIS

    PRIMARY_DB -->|일일 백업| S3_BACKUP
    PRIMARY_DB -->|WAL 로그| POINT_IN_TIME
```

---

*상세한 구현 가이드는 [개발 가이드](DEVELOPMENT_GUIDE.md) 및 [배포 가이드](DEPLOYMENT.md)를 참조하세요.*