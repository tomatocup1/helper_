# 📊 네이버 스마트플레이스 통계 시스템 구현 완료

## 🎯 시스템 개요

네이버 스마트플레이스 통계 데이터를 수집하고 웹에서 시각화하는 완전한 시스템이 구현되었습니다.

## 📁 생성된 파일 목록

### 🖥️ 프론트엔드 (웹페이지)

1. **네이버 통계 페이지**
   ```
   C:\helper\store-helper-project\frontend\src\app\analytics\naver\page.tsx
   ```

2. **시각화 컴포넌트**
   ```
   C:\helper\store-helper-project\frontend\src\components\analytics\StatisticsChart.tsx
   ```

3. **API 엔드포인트**
   ```
   C:\helper\store-helper-project\frontend\src\app\api\analytics\naver\route.ts
   C:\helper\store-helper-project\frontend\src\app\api\crawling\statistics\route.ts
   C:\helper\store-helper-project\frontend\src\app\api\stores\route.ts
   ```

4. **유틸리티**
   ```
   C:\helper\store-helper-project\frontend\src\lib\auth-utils.ts
   ```

5. **네비게이션 업데이트**
   ```
   C:\helper\store-helper-project\frontend\src\components\layout\AppHeader.tsx (수정됨)
   ```

### 🐍 백엔드 (크롤링)

1. **메인 크롤링 엔진**
   ```
   C:\helper\store-helper-project\backend\scripts\naver_statistics_crawler.py
   ```

2. **배치 실행 스크립트**
   ```
   C:\helper\store-helper-project\backend\scripts\run_statistics_crawler.py
   ```

3. **데이터베이스 스키마**
   ```
   C:\helper\store-helper-project\backend\scripts\sql\create_statistics_naver_table_fixed.sql
   ```

4. **사용 가이드**
   ```
   C:\helper\store-helper-project\backend\scripts\README_statistics.md
   ```

## 🚀 주요 기능

### 📈 웹 대시보드
- **반응형 디자인**: 모바일/데스크톱 완전 대응
- **실시간 차트**: Recharts 기반 인터랙티브 시각화
- **매장 선택**: 드롭다운으로 매장별 통계 확인
- **기간 필터**: 7일/30일/90일 기간별 분석
- **원클릭 크롤링**: 새로고침 버튼으로 즉시 데이터 수집

### 📊 수집 데이터
**방문 전 지표 (3개)**
- 플레이스 유입 (전일 대비 증감률 포함)
- 예약·주문 신청 (전일 대비 증감률 포함)
- 스마트콜 통화 (전일 대비 증감률 포함)

**방문 후 지표 (1개)**
- 리뷰 등록 (전일 대비 증감률 포함)

**유입 분석**
- 유입 채널 순위 (파이 차트 + 순위 표)
- 유입 키워드 순위 (바 차트 + 순위 표)

### 🎨 시각화 컴포넌트
- **트렌드 차트**: 시간에 따른 지표 변화 라인 차트
- **파이 차트**: 유입 채널 분포 시각화
- **바 차트**: 인기 검색 키워드 순위
- **요약 카드**: 최신 지표 한눈에 보기

## 🔧 설치 및 설정

### 1. 데이터베이스 설정
```sql
-- Supabase SQL Editor에서 실행
-- C:\helper\store-helper-project\backend\scripts\sql\create_statistics_naver_table_fixed.sql 파일 내용 실행
```

### 2. 프론트엔드 패키지 설치
```bash
cd C:\helper\store-helper-project\frontend
npm install recharts date-fns
```

### 3. 환경변수 확인
```bash
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

## 🖱️ 사용법

### 웹 대시보드 접속
```
https://your-domain.com/analytics/naver
```

1. **매장 선택**: 상단 드롭다운에서 네이버 매장 선택
2. **기간 설정**: 7일/30일/90일 중 분석 기간 선택
3. **데이터 수집**: "새로고침" 버튼 클릭으로 최신 통계 크롤링
4. **차트 확인**: 트렌드, 채널, 키워드 분석 차트 확인

### 수동 크롤링 (터미널)
```bash
# 단일 매장
cd C:\helper\store-helper-project\backend\scripts
python naver_statistics_crawler.py \
  --email "account@naver.com" \
  --password "password" \
  --store-id "platform_store_id" \
  --user-id "user_uuid" \
  --headless

# 배치 처리
python run_statistics_crawler.py --batch --headless
```

## 🎯 네비게이션 경로

통계 분석 메뉴가 확장되어 다음 경로로 접근할 수 있습니다:
- **전체 통계**: `/analytics`
- **네이버 통계**: `/analytics/naver` ← **새로 추가**

## 🔄 데이터 플로우

```
1. 웹에서 "새로고침" 버튼 클릭
   ↓
2. API 호출 (/api/crawling/statistics)
   ↓
3. Python 크롤링 스크립트 실행
   ↓
4. 네이버 스마트플레이스 로그인 및 통계 페이지 접속
   ↓
5. 통계 데이터 추출 (URL 기반 날짜 필터 적용)
   ↓
6. Supabase statistics_naver 테이블에 저장
   ↓
7. 웹페이지에서 API로 데이터 조회 및 차트 렌더링
```

## 📱 UI/UX 특징

### 반응형 설계
- **데스크톱**: 4열 그리드 레이아웃
- **태블릿**: 2열 그리드 레이아웃  
- **모바일**: 1열 스택 레이아웃

### 시각적 요소
- **트렌드 아이콘**: 상승(초록), 하락(빨강), 변동없음(회색)
- **색상 시스템**: 브랜드 일관성 유지
- **로딩 애니메이션**: 스켈레톤 UI 적용
- **차트 인터랙션**: 호버 툴팁, 범례 표시

## 🔒 보안 기능

- **행 수준 보안(RLS)**: 사용자별 데이터 격리
- **JWT 인증**: API 엔드포인트 보안
- **매장 소유권 확인**: 본인 매장만 접근 가능
- **입력 검증**: SQL 인젝션 방지

## 🛠️ 기술 스택

### 프론트엔드
- **Next.js 14**: React 기반 풀스택 프레임워크
- **TypeScript**: 타입 안정성
- **Tailwind CSS**: 유틸리티 기반 스타일링
- **Recharts**: 반응형 차트 라이브러리
- **Shadcn/ui**: 일관된 UI 컴포넌트
- **date-fns**: 날짜 처리 라이브러리

### 백엔드
- **Python**: 크롤링 스크립트
- **Playwright**: 브라우저 자동화
- **Supabase**: 데이터베이스 및 인증
- **PostgreSQL**: 관계형 데이터베이스

## 🎊 완성도

✅ **크롤링 시스템**: 네이버 2차 인증 우회, 안정적 데이터 수집  
✅ **웹 대시보드**: 반응형, 인터랙티브 차트  
✅ **API 설계**: RESTful, 보안 적용  
✅ **데이터베이스**: 정규화, 인덱싱 최적화  
✅ **에러 처리**: 재시도 로직, 사용자 친화적 메시지  
✅ **UI/UX**: 모바일 우선, 접근성 고려  

이제 네이버 스마트플레이스 통계를 웹에서 실시간으로 확인하고 관리할 수 있습니다! 🎯