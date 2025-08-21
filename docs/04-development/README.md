# 💻 개발 가이드

Helper B 프로젝트 개발을 위한 가이드라인과 베스트 프랙티스 문서입니다.

## 📄 문서 목록

### 개발 워크플로우
- **[개발 가이드](DEVELOPMENT_GUIDE.md)**
  - 코딩 규칙 및 컨벤션
  - Git 워크플로우
  - 테스트 작성 방법
  - 코드 리뷰 프로세스
  - CI/CD 파이프라인

### 마이그레이션
- **[레거시 통합](LEGACY_INTEGRATION.md)**
  - 기존 코드 마이그레이션 전략
  - 레거시 시스템과의 호환성
  - 단계별 마이그레이션 계획
  - 데이터 마이그레이션

## 🛠️ 개발 도구

### 필수 도구
- **IDE**: VS Code (권장) 또는 PyCharm
- **Git**: 버전 관리
- **Docker**: 컨테이너화
- **Postman/Insomnia**: API 테스트

### VS Code 확장 프로그램
- Python
- Prettier
- ESLint
- GitLens
- Docker

## 📝 코딩 컨벤션

### Python (백엔드)
- PEP 8 스타일 가이드 준수
- Type hints 사용
- Docstring 작성 필수
- Black 포매터 사용

### TypeScript/JavaScript (프론트엔드)
- ESLint + Prettier 설정
- 함수형 컴포넌트 사용
- TypeScript strict mode
- 명시적 타입 정의

## 🧪 테스트

### 테스트 구조
```
tests/
├── unit/           # 단위 테스트
├── integration/    # 통합 테스트
├── e2e/           # End-to-End 테스트
└── fixtures/      # 테스트 데이터
```

### 테스트 실행
```bash
# 백엔드 테스트
pytest

# 프론트엔드 테스트
npm test

# E2E 테스트
npm run test:e2e
```

## 🔄 Git 워크플로우

1. **Feature Branch**: `feature/기능명`
2. **Bug Fix**: `fix/버그명`
3. **Hotfix**: `hotfix/긴급수정`
4. **Release**: `release/버전`

### 커밋 메시지 규칙
- `feat:` 새로운 기능
- `fix:` 버그 수정
- `docs:` 문서 수정
- `style:` 코드 포맷팅
- `refactor:` 코드 리팩토링
- `test:` 테스트 추가/수정
- `chore:` 빌드 업무, 패키지 매니저 설정

## 🔗 관련 문서
- [시스템 아키텍처](../01-architecture/SYSTEM_ARCHITECTURE.md)
- [API 레퍼런스](../01-architecture/API_REFERENCE.md)
- [설치 가이드](../03-setup/SETUP.md)