# 우리가게 도우미 백엔드

## 핵심 기능
1. **매장 불러오기**: 네이버 스마트플레이스 매장 정보 수집
2. **리뷰 크롤링**: 고객 리뷰 자동 수집 및 분석  
3. **AI 답글 생성**: OpenAI를 활용한 맞춤형 답글 자동 생성
4. **AI 답글 등록**: 생성된 답글의 네이버 플랫폼 자동 등록

## 디렉토리 구조

```
backend/
├── ai_reply_system.py      # AI 답글 시스템 엔트리포인트
├── store_crawler.py        # 매장 크롤링 엔트리포인트
├── requirements.txt        # Python 의존성
├── .env.example           # 환경변수 예제
├── core/                  # 핵심 모듈
│   ├── ai_reply/          # AI 답글 생성
│   ├── captcha_solver.py  # 캐차 해결
│   ├── naver_login_auto.py # 네이버 로그인 자동화
│   ├── naver_reply_poster.py # 답글 등록
│   ├── naver_review_crawler.py # 리뷰 크롤링
│   └── naver_statistics_crawler.py # 통계 크롤링
├── docs/                  # 문서
└── sql/                   # 데이터베이스 스키마
```

## 사용법

### 매장 크롤링
```bash
# 리뷰 크롤링
python store_crawler.py reviews [store_id]

# 통계 크롤링  
python store_crawler.py stats [store_id]
```

### AI 답글 시스템
```bash
# AI 답글 생성
python ai_reply_system.py generate

# 답글 등록
python ai_reply_system.py post
```

## 환경 설정

1. `.env` 파일 생성 (`.env.example` 참조)
2. 필요한 패키지 설치:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

## 정리된 내용

- ✅ 테스트 파일 제거 (6개)
- ✅ 디버그 파일 제거 (4개) 
- ✅ 로그 디렉토리 제거
- ✅ 사용하지 않는 FastAPI 서버 제거
- ✅ 중복 SQL 파일 제거
- ✅ 문서 파일 정리
- ✅ 핵심 기능별 모듈화
- ✅ 통합 엔트리포인트 생성