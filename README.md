# 우리가게 도우미 (Store Helper)

소상공인을 위한 AI 리뷰 관리 및 CRM 서비스

## 📚 문서 센터
프로젝트 문서는 [docs/README.md](docs/README.md)에서 체계적으로 정리되어 있습니다.

### 빠른 링크
- 📊 [프로젝트 진행 상황](docs/02-progress/PROGRESS_STATUS.md)
- 🏗️ [시스템 아키텍처](docs/01-architecture/SYSTEM_ARCHITECTURE.md)
- ⚙️ [설치 가이드](docs/03-setup/SETUP.md)
- 💻 [개발 가이드](docs/04-development/DEVELOPMENT_GUIDE.md)

## 🎯 프로젝트 개요

"우리가게 도우미"는 소상공인들이 온라인 리뷰를 효율적으로 관리하고 고객과의 소통을 자동화할 수 있도록 도와주는 종합 플랫폼입니다.

### 주요 기능
- 🤖 AI 기반 리뷰 답글 자동 생성
- 📊 리뷰 분석 및 통계 대시보드
- 🔍 네이버 플레이스 리뷰 자동 크롤링
- 📱 QR 코드를 통한 고객 리뷰 초안 생성
- 📈 매장 순위 분석 및 트렌드 리포트

## 🏗️ 시스템 아키텍처

### 마이크로서비스 구조
- **서버 A**: 리뷰 크롤링 및 AI 답글 생성 (24시간 자동)
- **서버 B**: 사용자 API 및 매장 관리 (사용자 요청 처리)
- **서버 C**: 스케줄러 및 자동화 작업 (시간대별 배치 작업)

### 기술 스택
- **Backend**: Python FastAPI, Celery, Redis
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Database**: Supabase (PostgreSQL)
- **Crawling**: Playwright
- **AI**: OpenAI GPT-4o-mini
- **Infrastructure**: Docker, GitHub Actions

## 🚀 빠른 시작

### 필수 요구사항
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### 설치 및 실행

1. 프로젝트 클론
```bash
git clone https://github.com/your-org/store-helper.git
cd store-helper
```

2. 환경 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 환경 변수 설정
```

3. 프로젝트 설정 스크립트 실행
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

4. 서비스 시작
```bash
docker-compose up -d
```

5. 개발 서버 접속
- 프론트엔드: http://localhost:3000
- API 서버: http://localhost:8000
- 관리자 대시보드: http://localhost:3001

## 📚 문서

모든 문서는 [docs/](docs/) 폴더에 체계적으로 정리되어 있습니다.

- [시스템 아키텍처](docs/01-architecture/SYSTEM_ARCHITECTURE.md)
- [데이터베이스 설계](docs/01-architecture/DATABASE_DESIGN.md)
- [API 레퍼런스](docs/01-architecture/API_REFERENCE.md)
- [설치 가이드](docs/03-setup/SETUP.md)
- [개발 가이드](docs/04-development/DEVELOPMENT_GUIDE.md)

## 🛠️ 개발 가이드

### 브랜치 전략
- `main`: 프로덕션 릴리즈
- `develop`: 개발 통합
- `feature/*`: 기능 개발
- `hotfix/*`: 긴급 수정

### 커밋 규칙
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드 설정 등
```

### 테스트 실행
```bash
# 백엔드 테스트
cd backend/server-b
pytest

# 프론트엔드 테스트
cd frontend
npm test

# E2E 테스트
cd frontend
npm run e2e
```

## 📊 성능 목표

- **동시 사용자**: 10,000명
- **크롤링 처리량**: 시간당 3,000개 리뷰
- **API 응답 시간**: 평균 200ms 이하
- **가용성**: 99.9%

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 문의

- Email: contact@storehelper.com
- Website: https://storehelper.com
- Issues: https://github.com/your-org/store-helper/issues

---

Made with ❤️ for Korean small business owners