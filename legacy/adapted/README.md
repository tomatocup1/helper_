# 🔧 Adapted Code Repository

## 📋 개요

기존 코드를 현재 "우리가게 도우미" 프로젝트 아키텍처에 맞게 수정하고 최적화한 코드를 저장하는 공간입니다.

## 📁 폴더 구조

### 🧩 components/
**용도**: 재사용 가능한 컴포넌트들
**구조**:
```
components/
├── crawlers/          # 크롤링 컴포넌트
│   ├── base_crawler.py
│   ├── naver_crawler.py
│   ├── kakao_crawler.py
│   └── google_crawler.py
├── ai/                # AI 처리 컴포넌트  
│   ├── sentiment_analyzer.py
│   ├── reply_generator.py
│   ├── keyword_extractor.py
│   └── text_classifier.py
├── api/               # API 컴포넌트
│   ├── base_service.py
│   ├── auth_handler.py
│   ├── data_validator.py
│   └── response_formatter.py
└── ui/                # UI 컴포넌트
    ├── charts/
    ├── forms/
    ├── tables/
    └── modals/
```

### 🛠️ utilities/
**용도**: 공통 유틸리티 함수들
**구조**:
```
utilities/
├── data/              # 데이터 처리 유틸리티
│   ├── processors.py
│   ├── validators.py
│   ├── transformers.py
│   └── cleaners.py
├── network/           # 네트워크 관련 유틸리티
│   ├── http_client.py
│   ├── rate_limiter.py
│   ├── proxy_manager.py
│   └── retry_handler.py
├── security/          # 보안 관련 유틸리티
│   ├── encryption.py
│   ├── auth_utils.py
│   ├── input_sanitizer.py
│   └── token_manager.py
└── monitoring/        # 모니터링 유틸리티
    ├── logger.py
    ├── metrics.py
    ├── profiler.py
    └── alerting.py
```

### 📋 templates/
**용도**: 코드 템플릿 및 보일러플레이트
**구조**:
```
templates/
├── crawler/           # 크롤러 템플릿
│   ├── base_template.py
│   ├── async_crawler.py
│   └── batch_crawler.py
├── api/               # API 템플릿
│   ├── fastapi_endpoint.py
│   ├── pydantic_models.py
│   └── middleware_template.py
├── ai/                # AI 모델 템플릿
│   ├── model_trainer.py
│   ├── inference_engine.py
│   └── evaluation_metrics.py
└── frontend/          # 프론트엔드 템플릿
    ├── react_component.tsx
    ├── hook_template.ts
    └── page_template.tsx
```

## 🔄 적응 과정

### 1단계: 원본 분석
```bash
# 원본 코드 위치 확인
ls legacy/original-code/[category]/[code-name]/

# 코드 리뷰 수행
# 결과: legacy/analysis/code-review-[code-name].md
```

### 2단계: 아키텍처 매핑
```python
# 예: 기존 크롤러를 현재 아키텍처에 맞게 수정

# 기존 코드 (절차적 프로그래밍)
def crawl_naver():
    # 하드코딩된 설정
    # 동기 처리
    # 에러 처리 부족
    pass

# 적응된 코드 (객체지향 + 비동기)
class NaverCrawler(BaseCrawler):
    async def crawl(self, config: CrawlerConfig) -> CrawlResult:
        # 설정 주입
        # 비동기 처리
        # 체계적 에러 처리
        pass
```

### 3단계: 코드 표준화
- **코딩 스타일**: Black, Prettier 적용
- **타입 힌트**: Python typing, TypeScript 적용
- **문서화**: Docstring, JSDoc 추가
- **테스트**: 단위 테스트 작성

### 4단계: 성능 최적화
- **비동기 처리**: asyncio, Promise 활용
- **메모리 최적화**: 제너레이터, 스트리밍 적용
- **캐싱**: Redis 통합
- **배치 처리**: 대용량 데이터 처리 최적화

## 📝 적응 가이드라인

### 코딩 표준
```python
# Python 코드 예시
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import asyncio
import logging

class ComponentConfig(BaseModel):
    """컴포넌트 설정 모델"""
    name: str
    version: str
    settings: Dict[str, Any]

class BaseComponent:
    """기본 컴포넌트 클래스"""
    
    def __init__(self, config: ComponentConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def process(self, data: Any) -> Optional[Any]:
        """메인 처리 로직"""
        try:
            self.logger.info(f"Processing with {self.config.name}")
            result = await self._execute(data)
            return result
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise
    
    async def _execute(self, data: Any) -> Any:
        """구현해야 할 추상 메서드"""
        raise NotImplementedError
```

```typescript
// TypeScript 코드 예시
interface ComponentConfig {
  name: string;
  version: string;
  settings: Record<string, any>;
}

abstract class BaseComponent {
  protected config: ComponentConfig;
  protected logger: Logger;

  constructor(config: ComponentConfig) {
    this.config = config;
    this.logger = new Logger(this.constructor.name);
  }

  async process(data: any): Promise<any> {
    try {
      this.logger.info(`Processing with ${this.config.name}`);
      const result = await this.execute(data);
      return result;
    } catch (error) {
      this.logger.error(`Processing failed: ${error}`);
      throw error;
    }
  }

  protected abstract execute(data: any): Promise<any>;
}
```

### 에러 처리 패턴
```python
from enum import Enum
from typing import Union

class ErrorCode(Enum):
    NETWORK_ERROR = "NETWORK_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"

class ComponentError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: Dict[str, Any] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

# 사용 예시
async def safe_process(data):
    try:
        result = await risky_operation(data)
        return result
    except NetworkException as e:
        raise ComponentError(
            ErrorCode.NETWORK_ERROR,
            "Network operation failed",
            {"original_error": str(e)}
        )
```

### 로깅 패턴
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_event(self, level: str, event: str, **kwargs):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "level": level,
            **kwargs
        }
        self.logger.info(json.dumps(log_data))

# 사용 예시
logger = StructuredLogger("crawler")
logger.log_event("info", "crawling_started", store_id="12345", platform="naver")
```

## 🧪 테스트 패턴

### 단위 테스트 템플릿
```python
import pytest
from unittest.mock import Mock, AsyncMock
from components.crawlers.base_crawler import BaseCrawler

class TestBaseCrawler:
    @pytest.fixture
    def crawler_config(self):
        return CrawlerConfig(
            name="test_crawler",
            version="1.0.0",
            settings={"timeout": 30}
        )
    
    @pytest.fixture
    def crawler(self, crawler_config):
        return BaseCrawler(crawler_config)
    
    @pytest.mark.asyncio
    async def test_crawl_success(self, crawler):
        # Given
        test_data = {"url": "http://example.com"}
        
        # When
        result = await crawler.crawl(test_data)
        
        # Then
        assert result is not None
        assert result.status == "success"
    
    @pytest.mark.asyncio
    async def test_crawl_failure(self, crawler):
        # Given
        invalid_data = {"url": "invalid_url"}
        
        # When & Then
        with pytest.raises(ComponentError) as exc_info:
            await crawler.crawl(invalid_data)
        
        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
```

## 📊 품질 체크리스트

### 코드 품질
- [ ] **타입 힌트**: 모든 함수에 타입 힌트 추가
- [ ] **문서화**: Docstring 및 주석 완비
- [ ] **테스트**: 80% 이상 커버리지
- [ ] **린팅**: Flake8, ESLint 통과
- [ ] **포맷팅**: Black, Prettier 적용

### 아키텍처 준수
- [ ] **의존성 주입**: 하드코딩 제거
- [ ] **비동기 처리**: I/O 바운드 작업 비동기화
- [ ] **에러 처리**: 표준 에러 처리 패턴 적용
- [ ] **로깅**: 구조화된 로깅 적용
- [ ] **설정 관리**: 환경변수 활용

### 성능 최적화
- [ ] **메모리 효율성**: 메모리 누수 없음
- [ ] **처리 속도**: 성능 요구사항 만족
- [ ] **확장성**: 수평 확장 지원
- [ ] **캐싱**: 적절한 캐싱 전략 적용

## 🚀 배포 준비

### 패키징
```bash
# Python 컴포넌트
cd components/
python setup.py sdist bdist_wheel

# TypeScript 컴포넌트  
cd ui/
npm run build
npm pack
```

### 통합 테스트
```bash
# 컴포넌트 간 통합 테스트
pytest tests/integration/

# E2E 테스트
playwright test
```

### 문서 생성
```bash
# API 문서 자동 생성
sphinx-build -b html docs/ docs/_build/html

# TypeScript 문서
typedoc --out docs src
```

## 📞 다음 단계

적응 완료된 컴포넌트는:
1. **통합 테스트** 수행
2. **해당 서버 폴더**로 이동
3. **문서 업데이트**
4. **배포 준비**

---

*이 폴더는 기존 자산을 현재 프로젝트에 최적화하여 통합하기 위해 만들어졌습니다.*