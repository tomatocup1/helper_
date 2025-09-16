# 🚀 베타 서비스 배포 가이드

## 📋 개요

Store Helper 베타 서비스 배포를 위한 완전한 가이드입니다. 40개 계정(120개 가게) 관리와 알림톡 시스템을 포함한 본격적인 서비스 런칭을 위한 모든 단계를 다룹니다.

## 🎯 베타 서비스 목표

- **규모**: 40개 계정, 120개 가게 관리
- **플랫폼**: 네이버, 배민, 쿠팡이츠, 요기요
- **핵심 기능**: 자동 리뷰 크롤링, AI 답글 생성, 알림톡 발송
- **가용성**: 99.9% 업타임 목표

## 📁 프로젝트 구조

```
helper_B/
├── frontend/                 # Next.js 프론트엔드
│   ├── Dockerfile           # 프로덕션용 Docker 설정
│   └── src/app/beta-monitoring/  # 베타 모니터링 대시보드
├── backend/                 # Python 백엔드
│   ├── Dockerfile          # 프로덕션용 Docker 설정
│   ├── requirements.txt    # Python 의존성
│   ├── core/
│   │   ├── kakao_alimtalk.py      # 알림톡 시스템
│   │   ├── review_monitor.py      # 리뷰 모니터링
│   │   └── beta_onboarding.py     # 베타 온보딩
├── infrastructure/terraform/     # AWS 인프라 구성
│   ├── main.tf             # 메인 인프라
│   ├── ecs.tf              # ECS 서비스
│   ├── database.tf         # RDS & Redis
│   └── variables.tf        # 설정 변수
└── docker-compose.yml      # 로컬 개발용
```

## 🏗️ Phase 1: MVP 베타 배포 (1-2주)

### 1.1 환경 설정

**필수 환경변수 설정:**
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=your-openai-key

# 카카오 알림톡
KAKAO_API_KEY=your-kakao-key
KAKAO_SENDER_KEY=your-sender-key

# 암호화 키들
NAVER_ENCRYPTION_KEY=auto-generated
BAEMIN_ENCRYPTION_KEY=auto-generated
COUPANGEATS_ENCRYPTION_KEY=auto-generated
YOGIYO_ENCRYPTION_KEY=auto-generated

# JWT
JWT_SECRET_KEY=super-secret-jwt-key
```

### 1.2 Docker 이미지 빌드

```bash
# 프론트엔드 빌드
cd frontend
docker build -t storehelper-frontend:latest .

# 백엔드 빌드
cd backend
docker build -t storehelper-backend:latest .
```

### 1.3 AWS 인프라 배포

```bash
# Terraform 초기화
cd infrastructure/terraform
terraform init

# 인프라 계획 확인
terraform plan

# 인프라 배포
terraform apply
```

### 1.4 베타 계정 온보딩

```bash
# 베타 계정 자동 온보딩
cd backend/core
python beta_onboarding.py --mode onboard

# 온보딩 상태 확인
python beta_onboarding.py --mode report
```

## 🔄 Phase 2: 스케일링 베타 (3-4주)

### 2.1 시스템 모니터링 설정

**모니터링 대시보드 접속:**
- URL: `https://your-domain.com/beta-monitoring`
- 실시간 시스템 상태 확인
- 매장별 활성도 모니터링

### 2.2 알림톡 시스템 테스트

```bash
# 알림톡 발송 테스트
cd backend/core
python review_monitor.py --mode test --hours 1

# 실시간 모니터링 시작
python review_monitor.py --mode monitor
```

### 2.3 성능 최적화

**데이터베이스 인덱스 추가:**
```sql
-- 리뷰 검색 최적화
CREATE INDEX idx_reviews_store_date ON reviews_naver (store_id, created_at DESC);
CREATE INDEX idx_reviews_store_date ON reviews_baemin (store_id, created_at DESC);
CREATE INDEX idx_reviews_store_date ON reviews_coupangeats (store_id, created_at DESC);
CREATE INDEX idx_reviews_store_date ON reviews_yogiyo (store_id, created_at DESC);

-- 알림톡 로그 최적화
CREATE INDEX idx_alimtalk_logs_date ON alimtalk_logs (sent_at DESC);
```

## 🎯 Phase 3: 상용화 준비 (5-8주)

### 3.1 자동 스케일링 설정

```bash
# ECS 서비스 스케일링 설정
aws ecs put-scaling-policy \
  --service-name storehelper-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling
```

### 3.2 백업 및 복구 설정

```bash
# RDS 자동 백업 활성화
aws rds modify-db-instance \
  --db-instance-identifier storehelper-database \
  --backup-retention-period 7
```

### 3.3 보안 강화

**SSL/TLS 인증서 설정:**
- AWS Certificate Manager 사용
- CloudFront HTTPS 적용
- API Rate Limiting 구현

## 📊 모니터링 및 알림

### 주요 지표 (KPI)

**기술 지표:**
- 시스템 가용성: 99.9% 이상
- 크롤링 성공률: 95% 이상
- 알림톡 발송 성공률: 98% 이상
- 평균 응답시간: 2초 이내

**비즈니스 지표:**
- 일일 리뷰 처리량: 1,000-2,000개
- AI 답글 생성률: 90% 이상
- 고객 만족도: 4.5/5 이상

### 알림 설정

**Critical 알림 (즉시):**
- 시스템 다운타임
- 크롤링 실패율 >20%
- 데이터베이스 연결 실패

**Warning 알림 (10분 내):**
- 응답시간 >5초
- 메모리 사용률 >80%
- 크롤링 실패율 >10%

## 🚨 트러블슈팅

### 일반적인 문제들

**1. 크롤링 실패**
```bash
# 브라우저 프로필 초기화
rm -rf backend/core/logs/browser_profiles/*

# 크롤링 재시작
python automation_runner.py
```

**2. 알림톡 발송 실패**
```bash
# 카카오 API 상태 확인
curl -H "Authorization: Bearer $KAKAO_API_KEY" \
     https://alimtalk-api.bizmsg.kr/v2/status
```

**3. 데이터베이스 성능 저하**
```sql
-- 느린 쿼리 확인
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC LIMIT 10;
```

### 응급 대응 절차

**1. 시스템 다운 시:**
1. AWS ECS 서비스 재시작
2. 데이터베이스 연결 상태 확인
3. 로그 분석 및 원인 파악
4. 고객 공지사항 게시

**2. 크롤링 대량 실패 시:**
1. 플랫폼별 사이트 변경 확인
2. 브라우저 설정 업데이트
3. 수동 테스트 실행
4. 필요시 우회 로직 적용

## 💰 예상 비용

### 월간 운영비 (AWS 기준)

**인프라 비용:**
- ECS Fargate: $400/월
- RDS Aurora: $300/월
- ElastiCache: $150/월
- 기타 서비스: $200/월
- **총 인프라**: $1,050/월

**알림톡 비용:**
- 월 발송량: 25,000건
- 건당 비용: 15원
- **총 알림톡**: $375/월

**총 운영비**: **$1,425/월** (약 190만원)

### 수익 모델
- 계정당 월 이용료: 40,000원
- 40개 계정: 1,600,000원/월
- **순수익**: **약 410,000원/월**

## 🔧 유지보수

### 일일 점검사항
- [ ] 시스템 가용성 확인
- [ ] 크롤링 성공률 확인
- [ ] 알림톡 발송 상태 확인
- [ ] 리소스 사용량 모니터링

### 주간 점검사항
- [ ] 데이터베이스 성능 분석
- [ ] 로그 분석 및 정리
- [ ] 보안 업데이트 적용
- [ ] 백업 상태 확인

### 월간 점검사항
- [ ] 비용 분석 및 최적화
- [ ] 성능 개선사항 검토
- [ ] 고객 피드백 수집 및 분석
- [ ] 시스템 업그레이드 계획

## 📞 지원 및 연락처

**기술 지원:**
- 24/7 모니터링 시스템
- 슬랙 알림 채널: #storehelper-alerts
- 응급 연락처: 운영팀 전화번호

**고객 지원:**
- 이메일: support@storehelper.com
- 전화: 1588-1234
- 카카오톡 채널: @storehelper

---

## ✅ 배포 체크리스트

### 배포 전 확인사항
- [ ] 모든 환경변수 설정 완료
- [ ] Docker 이미지 빌드 및 테스트
- [ ] 데이터베이스 마이그레이션 완료
- [ ] SSL 인증서 설정
- [ ] 모니터링 대시보드 설정
- [ ] 백업 시스템 구성
- [ ] 보안 그룹 설정 확인

### 배포 후 확인사항
- [ ] 모든 서비스 정상 동작 확인
- [ ] 크롤링 테스트 실행
- [ ] AI 답글 생성 테스트
- [ ] 알림톡 발송 테스트
- [ ] 모니터링 알림 설정
- [ ] 성능 테스트 실행
- [ ] 사용자 피드백 수집 시작

### 베타 온보딩 확인사항
- [ ] 베타 계정 목록 준비
- [ ] 계정별 플랫폼 인증정보 수집
- [ ] 온보딩 스크립트 실행
- [ ] 각 계정별 테스트 완료
- [ ] 사용자 교육 자료 제공
- [ ] 고객 지원 채널 안내

**🎉 베타 서비스 런칭 준비 완료!**

이제 안정적이고 확장 가능한 베타 서비스로 40개 계정의 120개 가게를 효과적으로 관리할 수 있습니다.