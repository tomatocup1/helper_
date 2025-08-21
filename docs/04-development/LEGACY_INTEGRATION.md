# 🔄 기존 코드 통합 가이드

## 📋 개요

"우리가게 도우미" 프로젝트에 기존에 개발된 프로그램들을 안전하고 효율적으로 통합하기 위한 종합 가이드입니다.

## 🎯 통합 목표

### 주요 목표
1. **기존 자산 최대 활용**: 이미 개발된 코드의 재사용성 극대화
2. **품질 향상**: 기존 코드를 현재 아키텍처 표준에 맞게 개선
3. **개발 효율성**: 검증된 코드 활용으로 개발 속도 향상
4. **시스템 일관성**: 통합된 시스템의 아키텍처 일관성 유지

### 성공 기준
- [ ] 기존 코드 90% 이상 재활용
- [ ] 통합 후 성능 기존 대비 동등 이상
- [ ] 코드 품질 현재 프로젝트 표준 만족
- [ ] 통합 일정 지연 최소화

## 📁 통합 대상 분류

### 🕷️ 크롤링 시스템
**대상**: 네이버, 카카오, 구글 리뷰 크롤러
**현재 서버**: Server A (크롤링 & AI)
**통합 우선순위**: 높음

**예상 구성요소**:
- 브라우저 자동화 코드 (Selenium, Playwright)
- 사이트별 파싱 로직
- 데이터 추출 및 정제 로직
- 에러 처리 및 재시도 메커니즘

### 🤖 AI/ML 시스템  
**대상**: 감정 분석, 자동 답글 생성, 키워드 추출
**현재 서버**: Server A (크롤링 & AI)
**통합 우선순위**: 높음

**예상 구성요소**:
- 자연어 처리 모델
- 감정 분석 알고리즘
- GPT 연동 코드
- 텍스트 전처리 파이프라인

### 🔌 API 시스템
**대상**: 기존 REST API, 데이터 처리 로직
**현재 서버**: Server B (API 서버)
**통합 우선순위**: 보통

**예상 구성요소**:
- API 엔드포인트 코드
- 비즈니스 로직
- 데이터 검증 로직
- 인증/권한 시스템

### 🎨 프론트엔드
**대상**: 관리자 대시보드, UI 컴포넌트
**현재 서버**: 프론트엔드
**통합 우선순위**: 보통

**예상 구성요소**:
- React/Vue 컴포넌트
- 상태 관리 로직
- 차트/그래프 컴포넌트
- 스타일시트

## 🔄 통합 프로세스

### Phase 1: 수집 및 분석 (1주차)

#### 1.1 코드 수집
```bash
# 1. 기존 코드를 legacy/original-code/ 에 분류별 복사
cp -r /path/to/existing/naver-crawler legacy/original-code/crawlers/
cp -r /path/to/existing/ai-reply-system legacy/original-code/ai-systems/
cp -r /path/to/existing/api-server legacy/original-code/apis/
cp -r /path/to/existing/dashboard legacy/original-code/frontend/
```

#### 1.2 코드 분석 및 문서화
각 코드에 대해 다음 분석 수행:

**기능 분석**:
- 주요 기능 목록 작성
- 입력/출력 데이터 형식 파악
- 핵심 알고리즘 이해

**기술 분석**:
- 사용된 기술 스택 확인
- 의존성 라이브러리 목록
- 호환성 이슈 점검

**품질 분석**:
```bash
# 코드 품질 자동 분석
python tools/code-analysis/quality_checker.py \
  --path legacy/original-code/crawlers/naver-crawler \
  --output analysis/naver-crawler-quality.json

# 보안 취약점 스캔
python tools/code-analysis/security_scanner.py \
  --path legacy/original-code/ \
  --output analysis/security-report.json
```

#### 1.3 통합 계획 수립
각 코드별로 `legacy/analysis/integration-plan-[코드명].md` 작성:
- 재사용 가능 부분 식별
- 수정 필요 사항 정리
- 예상 작업 시간 산정
- 리스크 요인 분석

### Phase 2: 적응 및 수정 (2-3주차)

#### 2.1 아키텍처 맞춤 수정
```python
# 예: 기존 크롤러 현대화
# Before (기존 코드)
def crawl_naver_reviews(store_id):
    driver = webdriver.Chrome()
    # 하드코딩된 설정
    # 동기 처리
    # 제한적인 에러 처리
    
# After (적응된 코드)
class NaverReviewCrawler(BaseCrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(config)
        self.browser_pool = BrowserPool()
    
    async def crawl_reviews(self, store_id: str) -> List[Review]:
        # 설정 주입
        # 비동기 처리
        # 체계적 에러 처리
        # 구조화된 로깅
```

#### 2.2 코드 표준화
```bash
# 코딩 스타일 자동 변환
python tools/migration-scripts/style_converter.py \
  --input legacy/original-code/crawlers/ \
  --output legacy/adapted/components/crawlers/ \
  --format black

# 프로젝트 구조에 맞게 재배치
python tools/migration-scripts/structure_migrator.py \
  --source legacy/adapted/components/ \
  --target backend/server-a/app/
```

#### 2.3 테스트 코드 작성
```bash
# 기본 테스트 케이스 자동 생성
python tools/migration-scripts/test_generator.py \
  --source legacy/adapted/components/crawlers/naver_crawler.py \
  --output tests/unit/crawlers/test_naver_crawler.py

# 통합 테스트 케이스 작성
python tools/templates/generators/test_generator.py \
  --type integration \
  --component NaverCrawler \
  --output tests/integration/
```

### Phase 3: 통합 및 검증 (4주차)

#### 3.1 서버별 통합
```bash
# Server A에 크롤링 컴포넌트 통합
cp legacy/adapted/components/crawlers/* backend/server-a/app/crawlers/
cp legacy/adapted/components/ai/* backend/server-a/app/ai/

# Server B에 API 컴포넌트 통합  
cp legacy/adapted/components/api/* backend/server-b/app/services/

# 프론트엔드에 UI 컴포넌트 통합
cp legacy/adapted/components/ui/* frontend/src/components/
```

#### 3.2 종합 테스트
```bash
# 단위 테스트
pytest tests/unit/ --cov=backend/server-a/ --cov-report=html

# 통합 테스트
pytest tests/integration/ --maxfail=1 --tb=short

# E2E 테스트
playwright test --project=chromium
```

#### 3.3 성능 검증
```bash
# 성능 벤치마크
python tools/code-analysis/performance_profiler.py \
  --component NaverCrawler \
  --benchmark legacy/benchmarks/naver-crawler-original.json

# 메모리 사용량 분석
python tools/validators/memory_validator.py \
  --process crawler \
  --max-memory 2GB
```

## 📊 통합 매트릭스

### 컴포넌트별 통합 전략

| 컴포넌트 | 통합 방식 | 수정 범위 | 예상 시간 | 리스크 |
|----------|-----------|-----------|-----------|--------|
| **네이버 크롤러** | 아키텍처 적응 | 중간 | 1주 | 낮음 |
| **카카오 크롤러** | 아키텍처 적응 | 중간 | 1주 | 낮음 |
| **감정 분석 AI** | 모듈 통합 | 낮음 | 3일 | 낮음 |
| **답글 생성 AI** | API 통합 | 높음 | 1.5주 | 보통 |
| **API 서버** | 선택적 통합 | 높음 | 2주 | 높음 |
| **대시보드 UI** | 컴포넌트 이식 | 중간 | 1주 | 보통 |

### 기술 스택 호환성

| 기존 기술 | 현재 기술 | 호환성 | 마이그레이션 방법 |
|-----------|-----------|--------|------------------|
| Selenium | Playwright | 부분 | 브라우저 드라이버 교체 |
| Flask | FastAPI | 낮음 | 엔드포인트 재작성 |
| scikit-learn | OpenAI API | 낮음 | AI 모델 교체 |
| jQuery | React | 낮음 | 컴포넌트 재작성 |
| MySQL | PostgreSQL | 높음 | SQL 구문 조정 |

## 🛠️ 도구 활용 가이드

### 1. 코드 분석 도구
```bash
# 전체 프로젝트 품질 분석
python tools/code-analysis/quality_checker.py \
  --path legacy/original-code/ \
  --report-format html \
  --output analysis/quality-report.html

# 복잡도 분석
python tools/code-analysis/complexity_meter.py \
  --threshold 10 \
  --path legacy/original-code/
```

### 2. 마이그레이션 도구
```bash
# 자동 스타일 변환
python tools/migration-scripts/style_converter.py \
  --config tools/config.yml \
  --input legacy/original-code/crawlers/ \
  --output legacy/adapted/components/crawlers/

# 의존성 업데이트
python tools/migration-scripts/dependency_updater.py \
  --requirements legacy/original-code/crawlers/requirements.txt \
  --target-python 3.11 \
  --update-strategy conservative
```

### 3. 검증 도구
```bash
# API 호환성 검증
python tools/validators/api_validator.py \
  --legacy-spec legacy/original-code/apis/openapi.json \
  --current-spec backend/server-b/openapi.json \
  --check-compatibility

# 데이터베이스 스키마 검증
python tools/validators/db_schema_validator.py \
  --legacy-schema legacy/original-code/apis/schema.sql \
  --current-schema database/schemas/schema.sql
```

## 🚨 리스크 관리

### 주요 리스크 요인

| 리스크 | 확률 | 영향도 | 대응방안 |
|--------|------|--------|----------|
| **의존성 충돌** | 높음 | 중간 | 가상환경 격리, 점진적 업데이트 |
| **성능 저하** | 보통 | 높음 | 성능 벤치마크, 최적화 작업 |
| **보안 취약점** | 낮음 | 높음 | 보안 스캔, 코드 리뷰 |
| **호환성 문제** | 보통 | 중간 | 충분한 테스트, 단계별 통합 |

### 비상 계획

#### 롤백 계획
```bash
# 통합 전 상태로 롤백
git checkout pre-integration-backup

# 개별 컴포넌트 롤백
git revert [commit-hash] --no-edit
```

#### 대안 계획
- **완전 통합 실패 시**: 선택적 기능 통합
- **성능 이슈 시**: 기존 코드 참조하여 새로 개발
- **일정 지연 시**: 우선순위 재조정

## 📈 진행 상황 추적

### 주간 체크포인트

**Week 1: 수집 및 분석**
- [ ] 모든 기존 코드 수집 완료
- [ ] 코드 품질 분석 완료
- [ ] 통합 계획 수립 완료

**Week 2-3: 적응 및 수정**
- [ ] 크롤러 컴포넌트 적응 완료
- [ ] AI 시스템 적응 완료
- [ ] 테스트 코드 작성 완료

**Week 4: 통합 및 검증**
- [ ] 서버별 통합 완료
- [ ] 전체 테스트 통과
- [ ] 성능 검증 완료

### 성공 지표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| **코드 재사용률** | 90% 이상 | 라인 수 기준 |
| **테스트 커버리지** | 80% 이상 | pytest-cov |
| **성능 유지** | 기존 대비 100% | 벤치마크 테스트 |
| **품질 점수** | 8/10 이상 | 품질 분석 도구 |

## 📞 팀 협업 가이드

### 역할 분담
- **백엔드 개발자**: 크롤러, AI 시스템 통합
- **프론트엔드 개발자**: UI 컴포넌트 통합
- **QA**: 테스트 케이스 작성 및 검증
- **DevOps**: 배포 환경 설정

### 커뮤니케이션
- **일일 스탠드업**: 진행상황 공유
- **주간 리뷰**: 통합 결과 검토
- **이슈 보고**: Slack #legacy-integration 채널

### 문서화 규칙
- 모든 변경사항은 `CHANGELOG.md`에 기록
- 통합 과정에서 발견한 이슈는 GitHub Issues에 등록
- 중요한 결정사항은 ADR(Architecture Decision Record) 작성

---

*이 가이드는 기존 자산을 최대한 활용하여 프로젝트의 완성도와 효율성을 높이기 위해 작성되었습니다.*