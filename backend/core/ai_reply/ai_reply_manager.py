"""
AI 답글 생성 및 관리 통합 시스템
Integrated AI Reply Generation and Management System
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

import openai
from supabase import create_client, Client
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 멀티플랫폼 어댑터 시스템 임포트
from platform_adapters import MultiPlatformManager, Platform, UnifiedReview, parse_platform_list
from korean_reply_system import KoreanReplyGenerator, ReviewPriority, KoreanTone


class ReplyStatus(Enum):
    """답글 상태"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class ReviewAnalysis:
    """리뷰 분석 결과"""
    sentiment: str  # positive, negative, neutral
    sentiment_score: float  # 0.0 ~ 1.0
    risk_level: str  # low_risk, medium_risk, high_risk
    requires_approval: bool
    keywords: List[str]
    delay_hours: int = 0
    approval_reason: str = ""  # 승인 필요 이유


@dataclass
class ReplyResult:
    """답글 생성 결과"""
    ai_generated_reply: str
    complete_reply: str
    ai_model_used: str
    ai_generation_time_ms: int
    ai_confidence_score: float


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    score: float  # 0.0 ~ 1.0
    issues: List[str]
    warnings: List[str]
    suggestions: List[str]
    length_check: bool
    tone_check: bool
    content_relevance: bool
    safety_check: bool


@dataclass
class ProcessingResult:
    """처리 결과"""
    review_id: str
    status: str  # success, failed, skipped
    error_message: Optional[str] = None
    reply_status: Optional[str] = None
    requires_approval: Optional[bool] = None


@dataclass
class BatchSummary:
    """배치 처리 요약"""
    total_reviews: int
    processed: int
    success: int
    failed: int
    skipped: int
    high_risk: int
    requires_approval: int
    auto_approved: int
    processing_time_seconds: float
    results: List[ProcessingResult]


class AIReplyManager:
    """AI 답글 생성 및 관리 통합 시스템 - 다중 플랫폼 지원"""
    
    def __init__(self):
        # 로거 초기화
        import logging
        self.logger = logging.getLogger(__name__)

        # OpenAI 클라이언트 초기화
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다")

        self.openai_client = openai.AsyncOpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '400'))
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))  # 더 일관된 응답을 위해 낮춤

        # 한국형 답글 생성기 초기화
        self.korean_generator = KoreanReplyGenerator()
        
        # Supabase 클라이언트 초기화
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase 환경 변수가 설정되지 않았습니다")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Multi-platform manager 초기화
        self.platform_manager = MultiPlatformManager(self.supabase)
        
        # 처리 제한 설정
        self.max_concurrent = 5  # 동시 처리 리뷰 수
        self.rate_limit_delay = 1.0  # API 호출 간 대기 시간 (초)
        self.max_retries = 3  # 최대 재시도 횟수
        
        # 플랫폼별 설정
        self.supported_platforms = ['naver', 'baemin', 'yogiyo', 'coupangeats']
        
        # 위험 지표 초기화
        self.risk_indicators = self._initialize_risk_indicators()
        self.forbidden_words = self._load_forbidden_words()
        self.sensitive_patterns = self._load_sensitive_patterns()
        self.required_elements = self._load_required_elements()
    
    def _get_table_name(self, platform: str) -> str:
        """플랫폼별 테이블명 반환"""
        if platform not in self.supported_platforms:
            raise ValueError(f"지원하지 않는 플랫폼: {platform}")
        return f"reviews_{platform}"
    
    def _get_review_id_field(self, platform: str) -> str:
        """플랫폼별 리뷰 ID 필드명 반환"""
        if platform not in self.supported_platforms:
            raise ValueError(f"지원하지 않는 플랫폼: {platform}")
        return f"{platform}_review_id"
    
    def _get_review_url_field(self, platform: str) -> str:
        """플랫폼별 리뷰 URL 필드명 반환"""
        if platform not in self.supported_platforms:
            raise ValueError(f"지원하지 않는 플랫폼: {platform}")
        return f"{platform}_review_url"
    
    def _get_metadata_field(self, platform: str) -> str:
        """플랫폼별 메타데이터 필드명 반환"""
        if platform not in self.supported_platforms:
            raise ValueError(f"지원하지 않는 플랫폼: {platform}")
        return f"{platform}_metadata"
    
    def _get_failure_field(self, platform: str) -> str:
        """플랫폼별 실패 사유 필드명 반환"""
        field_mapping = {
            'naver': 'failure_reason',
            'baemin': 'failure_reason',
            'yogiyo': 'reply_error_message',
            'coupangeats': 'reply_error_message'
        }
        return field_mapping.get(platform, 'failure_reason')
    
    def _initialize_risk_indicators(self) -> Dict:
        """위험 지표 초기화 - 실제 클레임/질문/문제 중심"""
        return {
            "high_risk": {
                "keywords": [
                    # 법적/행정 문제
                    "환불", "신고", "고소", "소비자보호원", "보건소", "신고하겠", 
                    # 위생/안전 문제
                    "식중독", "배탈", "벌레", "이물질", "상한", "썩은", "곰팡이",
                    # 심각한 서비스 문제
                    "사기", "최악", "절대", "다시는"
                ],
                "delay_hours": 48,
                "reason": "법적/위생/심각한 문제"
            },
            "medium_risk": {
                "keywords": [
                    # 질문이나 요청
                    "문의", "질문", "궁금", "알려주", "연락", "전화",
                    # 특별한 요청
                    "예약", "주문", "메뉴", "가격", "영업시간",
                    # 불만사항
                    "실망", "불친절", "차별", "무시"
                ],
                "delay_hours": 24,
                "reason": "질문/요청/불만사항"
            },
            "review_only": {
                "keywords": [
                    # 단순 평가 (자동 승인 가능)
                    "맛있", "맛없", "좋", "별로", "그저그래", "괜찮", "추천"
                ],
                "delay_hours": 0,
                "reason": "일반 리뷰"
            }
        }
    
    def _load_forbidden_words(self) -> List[str]:
        """금지 단어 목록"""
        return [
            # 욕설 및 비속어
            "씨발", "개새끼", "병신", "지랄", "좆", "미친",
            # 차별적 표현
            "장애인", "정신병", "바보", "멍청",
            # 법적 위험 표현
            "고소", "신고", "법정", "변호사", "소송",
            # 과도한 약속
            "100% 보장", "절대", "무조건", "완벽",
            # 개인정보 관련
            "전화번호", "주소", "계좌번호"
        ]
    
    def _load_sensitive_patterns(self) -> List[str]:
        """민감한 패턴 목록"""
        return [
            r"돈.*드리[겠다|ㅁ]",  # 금전 제공 약속
            r"무료.*제공",  # 무료 제공 약속
            r"법적.*책임",  # 법적 책임 언급
            r"의료.*상담",  # 의료 조언
            r"개인.*정보",  # 개인정보 요청
            r"\d{3}-\d{3,4}-\d{4}",  # 전화번호 패턴
        ]
    
    def _load_required_elements(self) -> Dict[str, List[str]]:
        """답글 유형별 필수 요소"""
        return {
            "positive": ["감사", "기쁘", "좋", "만족"],
            "negative": ["죄송", "사과", "개선", "미안"],
            "neutral": ["감사", "의견", "참고"]
        }
    
    # ===== 1. 리뷰 분석 기능 =====
    
    async def analyze_review(self, review_data: Dict, store_settings: Dict) -> ReviewAnalysis:
        """리뷰 분석 및 위험도 평가 (AI 기반 승인 판단 통합)"""
        
        review_text = review_data.get('review_text') or ""
        rating = review_data.get('rating') or 3
        
        # 1. 감정 분석
        sentiment, sentiment_score = self._analyze_sentiment(review_text, rating)
        
        # 2. 한국형 우선순위 평가 (4단계)
        priority, priority_reason = self.korean_generator.get_priority_level(
            review_text, rating, store_settings
        )
        
        # 3. 기본 위험도 매핑 및 지연 시간 (승인 여부는 AI로 별도 판단)
        risk_level, delay_hours, _ = self._map_priority_to_settings(
            priority, store_settings
        )
        
        # 4. AI 기반 승인 필요 여부 판단
        try:
            ai_requires_approval, ai_reason = await self._ai_determine_requires_approval(
                review_text, rating, review_data, store_settings
            )
            approval_reason = f"AI 판단: {ai_reason}"
        except Exception as e:
            # AI 판단 실패시 기존 로직 사용
            self.logger.warning(f"AI 승인 판단 실패, 기존 로직 사용: {e}")
            _, _, ai_requires_approval = self._map_priority_to_settings(priority, store_settings)
            approval_reason = f"기존 로직: {priority_reason}"
        
        # 5. 키워드 추출
        keywords = self._extract_keywords(review_text)
        
        return ReviewAnalysis(
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            risk_level=risk_level,
            requires_approval=ai_requires_approval,
            keywords=keywords,
            delay_hours=delay_hours,
            approval_reason=approval_reason
        )
    
    def _map_priority_to_settings(self, priority: ReviewPriority, 
                                 store_settings: Dict) -> Tuple[str, int, bool]:
        """우선순위를 위험도, 지연시간, 승인필요 여부로 매핑 (단순화된 2단계)"""
        
        if priority == ReviewPriority.REQUIRES_APPROVAL:
            # 사장님 확인 필요: 48시간 후 답글 (모레 00시)
            return "medium_risk", 48, True
        
        elif priority == ReviewPriority.AUTO:
            # 자동 답글 가능: 24시간 후 답글 (내일 00시)
            return "low_risk", 24, False
        
        else:
            # 기본값: 안전을 위해 승인 필요로 설정
            return "medium_risk", 48, True
    
    def _analyze_sentiment(self, review_text: str, rating: int) -> Tuple[str, float]:
        """감정 분석"""
        
        # rating이 None인 경우를 대비해 기본값 설정
        rating = rating or 3
        
        # review_text가 None인 경우를 대비해 기본값 설정
        review_text = review_text or ""
        review_text = review_text.lower()
        
        # 평점 기반 기본 감정
        if rating >= 4:
            base_sentiment = "positive"
            base_score = 0.7 + (rating - 4) * 0.15  # 4점: 0.7, 5점: 0.85
        elif rating <= 2:
            base_sentiment = "negative"
            base_score = 0.3 - (rating - 1) * 0.15  # 1점: 0.15, 2점: 0.3
        else:
            base_sentiment = "neutral"
            base_score = 0.5
        
        # 텍스트 기반 감정 보정 (텍스트가 있는 경우에만)
        if review_text:
            positive_words = ["맛있", "좋", "만족", "친절", "깨끗", "분위기", "추천"]
            negative_words = ["맛없", "별로", "실망", "불친절", "더러", "시끄럽", "비싸"]
            
            positive_count = sum(1 for word in positive_words if word in review_text)
            negative_count = sum(1 for word in negative_words if word in review_text)
            
            # 보정 적용
            if positive_count > negative_count and base_sentiment != "positive":
                base_sentiment = "positive"
                base_score = min(0.8, base_score + 0.2)
            elif negative_count > positive_count and base_sentiment != "negative":
                base_sentiment = "negative"
                base_score = max(0.2, base_score - 0.2)
        
        return base_sentiment, base_score
    
    async def _assess_risk_level(self, review_text: str, rating: int) -> Tuple[str, int, str]:
        """AI 기반 위험도 평가"""
        
        # rating이 None인 경우를 대비해 기본값 설정
        rating = rating or 3
        
        # review_text가 None인 경우를 대비해 기본값 설정
        review_text = review_text or ""
        
        try:
            # AI에게 위험도 평가 요청
            risk_prompt = f"""
다음 고객 리뷰를 분석하여 사장님의 직접 확인이 필요한지 판단해주세요.

리뷰 내용: "{review_text}"
평점: {rating}점/5점

판단 기준:
1. HIGH_RISK (사장님 확인 필수):
   - 법적 문제: 환불 요구, 신고 위협, 소비자보호원 언급
   - 위생/안전: 식중독, 이물질, 위생 문제
   - 심각한 클레임: 사기, 차별, 심각한 서비스 불만

2. MEDIUM_RISK (사장님 확인 권장):
   - 질문/문의: 가격, 메뉴, 예약, 영업시간 문의
   - 특별 요청: 개인적인 연락 요청
   - 1점 리뷰: 심각한 불만 표현

3. LOW_RISK (자동 처리 가능):
   - 일반적인 맛/서비스 평가
   - 단순 추천/비추천
   - 긍정적 리뷰 (4-5점)

응답 형식:
위험도: [HIGH_RISK/MEDIUM_RISK/LOW_RISK]
이유: [구체적인 이유를 한 줄로]
"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 고객 리뷰 위험도 평가 전문가입니다. 정확하고 일관된 평가를 해주세요."},
                    {"role": "user", "content": risk_prompt}
                ],
                max_tokens=100,
                temperature=0.1  # 일관된 평가를 위해 낮은 온도
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # AI 응답 파싱
            risk_level, reason = self._parse_ai_risk_assessment(ai_response)
            
            # 지연 시간 결정
            if risk_level == "high_risk":
                delay_hours = 48
            elif risk_level == "medium_risk":
                delay_hours = 24
            else:
                delay_hours = 0
            
            return risk_level, delay_hours, reason
            
        except Exception as e:
            print(f"AI 위험도 평가 실패, 기본 로직 사용: {str(e)}")
            # AI 실패시 기본 키워드 기반 평가로 폴백
            return self._fallback_risk_assessment(review_text, rating)
    
    def _parse_ai_risk_assessment(self, ai_response: str) -> Tuple[str, str]:
        """AI 위험도 평가 응답 파싱"""
        
        lines = ai_response.strip().split('\n')
        risk_level = "low_risk"
        reason = "AI 평가 결과"
        
        for line in lines:
            if "위험도:" in line:
                if "HIGH_RISK" in line.upper():
                    risk_level = "high_risk"
                elif "MEDIUM_RISK" in line.upper():
                    risk_level = "medium_risk"
                else:
                    risk_level = "low_risk"
            elif "이유:" in line:
                reason = line.replace("이유:", "").strip()
        
        return risk_level, reason
    
    def _fallback_risk_assessment(self, review_text: str, rating: int) -> Tuple[str, int, str]:
        """AI 실패시 기본 키워드 기반 평가"""
        
        # 고위험 키워드 확인
        high_risk_keywords = [kw for kw in self.risk_indicators["high_risk"]["keywords"] if kw in review_text]
        if high_risk_keywords:
            return "high_risk", 48, f"고위험 키워드: {', '.join(high_risk_keywords)}"
        
        # 중위험 키워드 확인
        medium_risk_keywords = [kw for kw in self.risk_indicators["medium_risk"]["keywords"] if kw in review_text]
        if medium_risk_keywords:
            return "medium_risk", 24, f"질문/요청: {', '.join(medium_risk_keywords)}"
        
        # rating이 있는 경우에만 별점 기반 평가
        if rating is not None:
            # 1점 리뷰는 중위험으로 처리
            if rating == 1:
                return "medium_risk", 24, "1점 리뷰 (심각한 불만)"
            
            # 2점 리뷰는 저위험으로 처리
            if rating == 2:
                return "low_risk", 12, "2점 리뷰 (부정적 의견)"
        
        return "low_risk", 0, "일반 리뷰"
    
    def _requires_approval(self, risk_level: str, sentiment: str, rating: int, store_settings: Dict) -> bool:
        """승인 필요 여부 결정"""
        
        # rating이 None인 경우를 대비해 기본값 설정
        rating = rating or 3
        
        # 고위험은 무조건 승인 필요
        if risk_level == "high_risk":
            return True
        
        # 1점 리뷰는 무조건 승인 필요
        if rating == 1:
            return True
        
        # 중위험은 매장 설정에 따라
        if risk_level == "medium_risk":
            return store_settings.get('manual_approval_medium_risk', True)
        
        # 부정 리뷰는 매장 설정에 따라
        if sentiment == "negative":
            return store_settings.get('manual_approval_negative', True)
        
        return False
    
    def _extract_keywords(self, review_text: str) -> List[str]:
        """키워드 추출"""
        
        # 일반적인 키워드들
        keywords = []
        keyword_patterns = {
            "음식": ["맛", "음식", "요리", "메뉴"],
            "서비스": ["서비스", "직원", "친절", "불친절"],
            "분위기": ["분위기", "인테리어", "깨끗", "더러"],
            "가격": ["비싸", "저렴", "가격", "비용"],
            "위치": ["위치", "교통", "주차", "접근"],
            "품질": ["품질", "신선", "상한", "맛있", "맛없"]
        }
        
        for category, words in keyword_patterns.items():
            if any(word in review_text for word in words):
                keywords.append(category)
        
        return keywords
    
    async def _ai_determine_requires_approval(self, review_text: str, rating: int, 
                                            review_data: Dict, store_settings: Dict) -> Tuple[bool, str]:
        """AI 기반 사장님 확인 필요 여부 판단"""
        
        try:
            # 시스템 프롬프트 구성
            system_prompt = """
당신은 온라인 리뷰 관리 전문가입니다. 리뷰 내용을 분석하여 자동 답글 대신 사장님이 직접 확인하고 답변해야 하는지 판단해주세요.

**사장님 확인이 필요한 경우:**
1. 심각한 불만/클레임 (식중독, 위생 문제, 법적 위험)
2. 구체적인 질문이나 요청 (메뉴 문의, 예약, 개인적 요청)  
3. 복잡한 상황 (환불 요구, 특별한 사연, 개인적 경험담)
4. 1-2점 매우 낮은 평점의 강한 불만
5. 개인화된 응답이 필요한 특별한 칭찬이나 감사

**자동 답글 가능한 경우:**
1. 단순한 긍정적 평가 ("맛있어요", "좋아요")
2. 간단한 부정적 평가 (특별한 조치 불필요)
3. 표준화된 응답으로 충분한 일반적 의견

응답 형식:
- requires_approval: true/false
- reason: 판단 근거 (한 줄로 간단히)
"""

            # 사용자 프롬프트 구성
            review_info = []
            review_info.append(f"평점: {rating}점/5점")
            if review_text:
                review_info.append(f"리뷰 내용: {review_text}")
            else:
                review_info.append("리뷰 내용: (평점만 남김)")
            
            # 추가 컨텍스트 정보
            platform = review_data.get('platform', 'unknown')
            review_info.append(f"플랫폼: {platform}")
            
            user_prompt = f"""
다음 리뷰를 분석하여 사장님 확인이 필요한지 판단해주세요:

{chr(10).join(review_info)}

JSON 형식으로 응답해주세요:
{{
    "requires_approval": true/false,
    "reason": "판단 근거"
}}
"""

            # OpenAI API 호출
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # 일관성을 위해 낮은 temperature
                max_tokens=200
            )
            
            # 응답 파싱
            response_text = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                import json
                result = json.loads(response_text)
                requires_approval = result.get('requires_approval', True)  # 기본값은 True (안전)
                reason = result.get('reason', 'AI 분석 결과')
                
                return requires_approval, reason
                
            except json.JSONDecodeError:
                # JSON 파싱 실패시 텍스트에서 추출 시도
                if 'false' in response_text.lower() or 'requires_approval": false' in response_text.lower():
                    return False, "AI 분석: 자동 답글 가능"
                else:
                    return True, "AI 분석: 사장님 확인 권장"
            
        except Exception as e:
            self.logger.error(f"AI 승인 판단 실패: {e}")
            # 오류 발생시 안전하게 승인 필요로 설정
            return True, f"AI 분석 오류 - 안전을 위해 승인 필요로 설정"
    
    # ===== 2. AI 답글 생성 기능 =====
    
    async def generate_reply(self, review_data: Dict, store_settings: Dict, platform: str = 'naver') -> ReplyResult:
        """AI 답글 생성 (한국형 개선)"""
        
        start_time = time.time()
        
        try:
            # 1. 리뷰 분석
            analysis = await self.analyze_review(review_data, store_settings)
            
            # 2. 우선순위 판단
            priority, _ = self.korean_generator.get_priority_level(
                review_data.get('review_text', ''),
                review_data.get('rating', 3),
                store_settings
            )
            
            # 3. OpenAI를 사용한 자연스러운 답글 생성
            # 우선순위가 높거나 위험한 리뷰는 반드시 AI 사용
            use_ai = priority == ReviewPriority.REQUIRES_APPROVAL or \
                    analysis.risk_level in ["high", "critical"] or \
                    True  # 항상 AI 사용하도록 설정
            
            if use_ai:
                # AI를 사용한 답글 생성
                ai_reply, tokens_used, confidence = await self._generate_ai_body(
                    review_data, store_settings, analysis
                )
            else:
                # 템플릿 기반 답글 (폴백)
                ai_reply = self.korean_generator.generate_long_natural_reply(
                    review_data, store_settings, analysis.sentiment, priority, platform
                )
                confidence = 0.7
                tokens_used = 0
            
            # 6. 완전한 답글 구성
            complete_reply = self._build_complete_reply(ai_reply, store_settings, review_data)
            
            generation_time = int((time.time() - start_time) * 1000)
            
            return ReplyResult(
                ai_generated_reply=ai_reply,
                complete_reply=complete_reply,
                ai_model_used=self.model if use_ai else "korean_template",
                ai_generation_time_ms=generation_time,
                ai_confidence_score=confidence
            )
            
        except Exception as e:
            raise Exception(f"AI 답글 생성 실패: {str(e)}")
    
    async def _generate_reply_after_failure(self, review_data: Dict, store_settings: Dict, 
                                           previous_reply: str, failure_reason: str, platform: str) -> ReplyResult:
        """실패한 답글을 재생성 - DB에 저장된 실패 사유 활용"""
        
        start_time = time.time()
        
        try:
            # 실패 사유 분석을 위한 프롬프트
            prompt = f"""
이전 답글이 플랫폼에서 거부되었습니다. 실패 정보를 참고하여 새 답글을 작성하세요.

[리뷰 정보]
- 작성자: {review_data.get('reviewer_name', '고객님')}
- 평점: {review_data.get('rating', 3)}점
- 리뷰 내용: {review_data.get('review_text', '')}

[실패한 답글]
{previous_reply}

[플랫폼 거부 사유]
{failure_reason}

[재생성 지침]
1. 실패 사유에 명시된 금지어나 문제 표현을 피하세요
2. 만약 작성자 닉네임이 문제라면 "고객님"으로 변경
3. "시 방" 패턴이 생기는 "다시 방문" 대신 "또 찾아", "재방문", "다음에도 이용" 등 사용
4. 타 플랫폼명(배민, 요기요, 쿠팡 등)은 언급하지 마세요
5. 이전 답글의 의미는 유지하되 표현을 완전히 바꿔주세요

플랫폼: {platform}
매장명: {store_settings.get('store_name', '저희 가게')}

새로운 답글을 작성해주세요:"""
            
            # OpenAI API 호출
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"당신은 {store_settings.get('store_name', '가게')} 사장님입니다. 플랫폼 정책을 이해하고 금지어를 회피하는 답글 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.9  # 다양한 표현을 위해 약간 높게
            )
            
            new_reply = response.choices[0].message.content.strip()
            generation_time = int((time.time() - start_time) * 1000)
            
            # 인사말과 마무리말 추가
            complete_reply = self._build_complete_reply(new_reply, store_settings, review_data)
            
            return ReplyResult(
                ai_generated_reply=new_reply,
                complete_reply=complete_reply,
                ai_model_used=self.model,
                ai_generation_time_ms=generation_time,
                ai_confidence_score=0.85  # 재생성은 약간 낮은 신뢰도
            )
            
        except Exception as e:
            raise Exception(f"답글 재생성 실패: {str(e)}")
    
    async def _generate_ai_body(self, review_data: Dict, store_settings: Dict, 
                               analysis: ReviewAnalysis) -> Tuple[str, int, float]:
        """AI 답글 본문 생성"""
        
        prompt = self._build_dynamic_prompt(review_data, store_settings, analysis)
        
        try:
            # 매장 설정 기반 동적 최대 토큰 수 계산
            max_length = store_settings.get('max_reply_length', 200)
            # 한국어 특성상 토큰 수는 글자 수의 약 1.5배 정도로 설정
            dynamic_max_tokens = min(int(max_length * 1.5), 500)  # 최대 500 토큰으로 제한
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(store_settings)},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=dynamic_max_tokens,  # 동적 답글 길이 제한
                temperature=0.8,  # 더 창의적이고 자연스러운 답변
                presence_penalty=0.3,  # 적당한 반복 방지
                frequency_penalty=0.3,  # 다양한 표현 사용
                top_p=0.95  # 더 다양한 단어 선택
            )
            
            ai_reply = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            
            # 신뢰도 계산 (간단한 휴리스틱)
            confidence = min(1.0, 0.7 + (len(ai_reply) / 200) * 0.3)
            
            return ai_reply, tokens_used, confidence
            
        except Exception as e:
            raise Exception(f"OpenAI API 호출 실패: {str(e)}")
    
    def _get_system_prompt(self, store_settings: Dict) -> str:
        """매장별 설정을 반영한 개인화된 시스템 프롬프트"""
        
        # 매장 기본 정보
        store_name = store_settings.get('store_name', '저희 가게')
        business_type = store_settings.get('business_type', '가게')
        operation_type = store_settings.get('operation_type', 'both')  # 매장 운영 방식
        
        # 개인화 설정
        reply_tone = store_settings.get('reply_tone', 'friendly')
        min_length = store_settings.get('min_reply_length', 50)
        max_length = store_settings.get('max_reply_length', 200)
        brand_voice = store_settings.get('brand_voice', '')
        custom_instructions = store_settings.get('custom_instructions', '')
        
        # 톤앤매너별 맞춤 지침
        tone_instructions = {
            'friendly': "친근하고 따뜻한 말투로, 이모티콘도 적절히 사용하여",
            'formal': "정중하고 격식있는 표현으로, 존댓말을 정확히 사용하여",
            'casual': "편안하고 자연스러운 구어체로, 친구처럼 편하게"
        }
        
        tone_guide = tone_instructions.get(reply_tone, tone_instructions['friendly'])
        
        # 운영 방식별 금지 표현
        operation_restrictions = {
            'delivery_only': """
5. [배달전용 매장] 절대 금지 표현:
   - "방문해주세요", "오셔서", "매장에서", "가게에 오시면" 등 매장 방문 관련 표현 금지
   - "다음에도 배달로 이용해주세요", "또 주문해주세요" 등으로 대체""",
            'dine_in_only': """
5. [홀전용 매장] 절대 금지 표현:
   - "배달", "배송", "라이더" 등 배달 관련 표현 금지
   - "매장에서 뵙겠습니다", "방문해주셔서" 등으로 표현""",
            'takeout_only': """
5. [포장전용 매장] 절대 금지 표현:
   - "배달", "홀에서", "매장에서 드시고" 등 배달/홀 관련 표현 금지
   - "포장 주문", "가져가실 때" 등으로 표현""",
            'both': """
5. [배달+홀 매장] 상황에 맞는 표현 사용:
   - 배달 리뷰: 배달 관련 표현 사용
   - 방문 리뷰: 매장 방문 관련 표현 사용"""
        }
        
        operation_guide = operation_restrictions.get(operation_type, operation_restrictions['both'])
        
        # 기본 프롬프트 구성
        base_prompt = f"""당신은 "{store_name}" {business_type} 사장님입니다. 실제 한국 소상공인처럼 자연스럽고 진솔한 답글을 작성하세요.

답글 스타일: {tone_guide}
답글 길이: {min_length}-{max_length}자 (한국어 기준)
매장 운영 방식: {operation_type.replace('_', ' ').title()}

[금지어 주의사항 - 매우 중요]
1. "다시 방문"이라는 표현 금지 → "또 찾아", "재방문", "다음에도 이용" 등으로 대체
2. 타 플랫폼명 언급 금지 (배민, 요기요, 쿠팡 등)
3. 리뷰어 닉네임에 문제가 있을 경우 "고객님"으로 호칭
4. "시 방" 패턴이 생기는 모든 표현 주의
{operation_guide}

핵심 원칙:
1. 리뷰 내용에 구체적으로 반응 (리뷰어가 언급한 메뉴, 상황 등을 그대로 언급)
2. 템플릿 문장 절대 금지
3. 설정된 길이 범위 내에서 진솔하게 작성
4. 자연스러운 한국어 구어체 사용
5. 매장 운영 방식에 맞는 표현만 사용 (배달전용/홀전용/포장전용 구분)"""

        # 브랜드 보이스 추가
        if brand_voice:
            base_prompt += f"""
5. 매장 특성: {brand_voice}"""

        # 톤별 구체적 예시
        if reply_tone == 'friendly':
            base_prompt += """

좋은 예시:
- "닭강정 맛있게 드셨다니 다행이네요 ㅎㅎ"
- "배달 늦어서 죄송해요 ㅠㅠ 다음엔 더 빨리 보내드릴게요"
- "별점 감사해요! 덕분에 힘이 나네요"
"""
        elif reply_tone == 'formal':
            base_prompt += """

좋은 예시:
- "소중한 리뷰 남겨주셔서 진심으로 감사드립니다"
- "불편을 드려 죄송합니다. 즉시 개선하겠습니다"
- "고객님의 만족을 위해 최선을 다하겠습니다"
"""
        elif reply_tone == 'casual':
            base_prompt += """

좋은 예시:
- "맛있게 드셨다니 기분 좋네요~"
- "아 늦어서 미안해요! 다음엔 빨리 보낼게요"
- "리뷰 고마워요 덕분에 힘이 나요"
"""

        base_prompt += """

사용 금지:
× "귀하" "고객님의 소중한 의견" "최선을 다하겠습니다" (formal 톤이 아닌 경우)
× "앞으로도 변함없는" "더욱 발전하는" 
× 날씨 관련 인사
× 과도한 이모티콘이나 느낌표 (formal 톤의 경우)"""

        # 사용자 정의 지침 추가
        if custom_instructions:
            base_prompt += f"""

매장 사장님의 특별 지침:
{custom_instructions}"""

        return base_prompt.strip()
    
    def _build_dynamic_prompt(self, review_data: Dict, store_settings: Dict, 
                             analysis: ReviewAnalysis) -> str:
        """SEO 키워드와 브랜드 보이스를 반영한 동적 프롬프트 생성"""
        
        reviewer_name = review_data.get('reviewer_name', '고객')
        raw_review_text = review_data.get('review_text')
        # 리뷰 텍스트 처리: None, 빈문자열, 'None' 문자열을 빈문자열로 통일
        review_text = ''
        if raw_review_text and str(raw_review_text).strip() and str(raw_review_text).strip().lower() != 'none':
            review_text = str(raw_review_text).strip()
        
        rating = review_data.get('rating', 3)
        order_menu = review_data.get('order_menu_items', [])
        
        # 개인화 설정
        min_length = store_settings.get('min_reply_length', 50)
        max_length = store_settings.get('max_reply_length', 200)
        seo_keywords = store_settings.get('seo_keywords', [])
        brand_voice = store_settings.get('brand_voice', '')
        reply_tone = store_settings.get('reply_tone', 'friendly')
        operation_type = store_settings.get('operation_type', 'both')  # 매장 운영 방식
        
        # 메뉴 정보 처리
        menu_str = ""
        if order_menu and isinstance(order_menu, list):
            menu_items = [item.get('menu_name', '') for item in order_menu if isinstance(item, dict)]
            if menu_items:
                menu_str = f"주문 메뉴: {', '.join(menu_items)}"
        
        # SEO 키워드 정보 (자연스럽게 포함할 수 있는 키워드들)
        seo_context = ""
        if seo_keywords and isinstance(seo_keywords, list) and len(seo_keywords) > 0:
            # 빈 문자열이 아닌 키워드만 필터링
            valid_keywords = [kw.strip() for kw in seo_keywords if kw and kw.strip()]
            if valid_keywords:
                seo_context = f"""

선택적으로 자연스럽게 포함할 수 있는 키워드들 (강제로 모든 키워드를 넣지 말고 맥락에 맞는 것만 선택):
{', '.join(valid_keywords[:5])}  # 최대 5개만 표시"""
        
        # 브랜드 보이스 컨텍스트
        brand_context = ""
        if brand_voice:
            brand_context = f"""

매장 특성 및 브랜드 특징:
{brand_voice}"""
        
        # 감정별 가이드 (운영 방식 고려)
        sentiment_guide = ""
        operation_context = ""
        
        # 운영 방식별 추가 컨텍스트
        if operation_type == 'delivery_only':
            operation_context = " (배달전용 매장이므로 매장 방문 관련 표현 절대 금지)"
        elif operation_type == 'dine_in_only':
            operation_context = " (홀전용 매장이므로 배달 관련 표현 절대 금지)"
        elif operation_type == 'takeout_only':
            operation_context = " (포장전용 매장이므로 배달/홀 관련 표현 절대 금지)"
        
        if analysis.sentiment == "positive":
            if operation_type == 'delivery_only':
                sentiment_guide = "긍정적인 리뷰에 대해 감사함을 표현하고 다음 주문을 자연스럽게 유도하세요."
            elif operation_type == 'dine_in_only':
                sentiment_guide = "긍정적인 리뷰에 대해 감사함을 표현하고 매장 재방문을 자연스럽게 유도하세요."
            elif operation_type == 'takeout_only':
                sentiment_guide = "긍정적인 리뷰에 대해 감사함을 표현하고 다음 포장 주문을 자연스럽게 유도하세요."
            else:
                sentiment_guide = "긍정적인 리뷰에 대해 감사함을 표현하고 재이용을 자연스럽게 유도하세요."
        elif analysis.sentiment == "negative":
            sentiment_guide = "부정적인 리뷰에 대해 진심으로 사과하고 구체적인 개선 의지를 보여주세요."
        else:
            if operation_type == 'delivery_only':
                sentiment_guide = "중립적인 리뷰에 대해 주문에 감사하며 긍정적인 경험을 유도하세요."
            elif operation_type == 'dine_in_only':
                sentiment_guide = "중립적인 리뷰에 대해 방문에 감사하며 긍정적인 경험을 유도하세요."
            else:
                sentiment_guide = "중립적인 리뷰에 대해 이용에 감사하며 긍정적인 경험을 유도하세요."
        
        sentiment_guide += operation_context
        
        # 리뷰 텍스트 표시 처리
        review_display = ""
        if review_text:
            review_display = f'리뷰: "{review_text}"'
        else:
            review_display = "리뷰: (텍스트 리뷰 없이 평점만 남겨주심)"
        
        # 운영 방식 표시
        operation_display = {
            'delivery_only': '배달전용',
            'dine_in_only': '홀전용',
            'takeout_only': '포장전용',
            'both': '배달+홀'
        }
        
        # 기본 프롬프트 구성
        prompt = f"""
리뷰어: {reviewer_name}님
평점: {rating}점/5점
매장 운영 방식: {operation_display.get(operation_type, '배달+홀')}
{review_display}
{menu_str}{seo_context}{brand_context}

답글 작성 가이드:
- 길이: {min_length}-{max_length}자 (한국어 기준)
- 톤: {reply_tone} 스타일
- {sentiment_guide}

특별 지침:
- 매장 운영 방식({operation_display.get(operation_type, '배달+홀')})에 맞는 표현만 사용
- 리뷰 텍스트가 없는 경우: 평점에 감사하며 간단하고 따뜻하게 응답
- 리뷰가 없다고 아쉬워하거나 따지는 표현 금지
- "None", "빈값", "없음" 등의 표현 사용 금지

이 리뷰에 대해 설정된 스타일과 길이에 맞춰 진솔한 답글을 작성하세요.
리뷰 내용이 있으면 구체적으로 언급하고, 없으면 평점과 이용에 대해 감사를 표현하세요."""
        
        return prompt.strip()
    
    def _translate_sentiment(self, sentiment: str) -> str:
        """감정 한글 변환"""
        translations = {
            "positive": "긍정 😊",
            "negative": "부정 😔",
            "neutral": "중립 😐"
        }
        return translations.get(sentiment, sentiment)
    
    def _translate_priority(self, priority: ReviewPriority) -> str:
        """우선순위 한글 변환"""
        translations = {
            ReviewPriority.URGENT: "🚨 즉시확인",
            ReviewPriority.HIGH: "⚡ 높음",
            ReviewPriority.MEDIUM: "⚠️ 보통",
            ReviewPriority.LOW: "📝 낮음",
            ReviewPriority.AUTO: "✅ 자동처리"
        }
        return translations.get(priority, str(priority))
    
    def _build_complete_reply(self, ai_reply: str, store_settings: Dict, review_data: Dict = None) -> str:
        """새로운 템플릿 시스템을 사용한 완전한 답글 구성"""
        
        # 새로운 템플릿 시스템 우선 사용
        greeting_template = store_settings.get('greeting_template', '')
        closing_template = store_settings.get('closing_template', '')
        
        # 기존 설정 폴백
        if not greeting_template:
            greeting_template = store_settings.get('reply_greeting', '')
        if not closing_template:
            closing_template = store_settings.get('reply_closing', '')
        
        # 템플릿 변수 치환을 위한 컨텍스트 준비
        template_context = {
            'store_name': store_settings.get('store_name', '저희 가게'),
            'business_type': store_settings.get('business_type', '가게'),
            'reviewer_name': review_data.get('reviewer_name', '고객님') if review_data else '고객님',
        }
        
        reply_parts = []
        
        # 인사말 템플릿 처리
        if greeting_template:
            try:
                formatted_greeting = self._format_template(greeting_template, template_context)
                reply_parts.append(formatted_greeting)
            except Exception:
                # 템플릿 처리 실패시 원본 그대로 사용
                reply_parts.append(greeting_template)
        
        # AI 생성 답글 본문
        reply_parts.append(ai_reply)
        
        # 마무리말 템플릿 처리
        if closing_template:
            try:
                formatted_closing = self._format_template(closing_template, template_context)
                reply_parts.append(formatted_closing)
            except Exception:
                # 템플릿 처리 실패시 원본 그대로 사용
                reply_parts.append(closing_template)
        
        # 톤에 따른 적절한 구분자 선택
        reply_tone = store_settings.get('reply_tone', 'friendly')
        if reply_tone == 'formal':
            separator = ' '  # 정중한 톤은 공백으로만 구분
        else:
            separator = ' '  # 기본적으로 공백 구분
        
        complete_reply = separator.join(reply_parts)
        
        # 정리
        complete_reply = self._clean_reply(complete_reply)
        
        return complete_reply
    
    def _format_template(self, template: str, context: Dict[str, str]) -> str:
        """템플릿 문자열의 변수를 실제 값으로 치환"""
        
        formatted = template
        
        # 안전한 치환을 위해 하나씩 처리
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in formatted:
                formatted = formatted.replace(placeholder, value)
        
        return formatted
    
    def _clean_reply(self, reply_text: str) -> str:
        """답글 정리"""
        
        # 1. 여러 줄바꿈을 하나로
        cleaned = re.sub(r'\n{3,}', '\n\n', reply_text)
        
        # 2. 앞뒤 공백 제거
        cleaned = cleaned.strip()
        
        # 3. 중복 이모티콘 제거
        cleaned = re.sub(r'😊{2,}', '😊', cleaned)
        cleaned = re.sub(r'🙏{2,}', '🙏', cleaned)
        
        # 4. 과도한 느낌표 제거
        cleaned = re.sub(r'!{3,}', '!!', cleaned)
        
        return cleaned
    
    # ===== 3. 품질 검증 기능 =====
    
    async def validate_reply(self, reply_text: str, review_data: Dict, 
                           store_settings: Dict, sentiment: str = "neutral") -> ValidationResult:
        """답글 종합 검증"""
        
        issues = []
        warnings = []
        suggestions = []
        
        # 1. 길이 검증
        length_check = self._validate_length(reply_text, store_settings, issues, warnings)
        
        # 2. 톤 검증
        tone_check = self._validate_tone(reply_text, sentiment, store_settings, issues, warnings)
        
        # 3. 내용 관련성 검증
        content_relevance = self._validate_content_relevance(
            reply_text, review_data, issues, warnings, suggestions
        )
        
        # 4. 안전성 검증
        safety_check = self._validate_safety(reply_text, issues, warnings)
        
        # 5. 전체 점수 계산
        score = self._calculate_overall_score(
            length_check, tone_check, content_relevance, safety_check, len(issues)
        )
        
        # 6. 개선 제안
        self._generate_suggestions(reply_text, review_data, suggestions)
        
        is_valid = len(issues) == 0 and score >= 0.6
        
        return ValidationResult(
            is_valid=is_valid,
            score=score,
            issues=issues,
            warnings=warnings,
            suggestions=suggestions,
            length_check=length_check,
            tone_check=tone_check,
            content_relevance=content_relevance,
            safety_check=safety_check
        )
    
    def _validate_length(self, reply_text: str, store_settings: Dict, issues: List[str], warnings: List[str]) -> bool:
        """동적 길이 제한을 사용한 길이 검증"""
        
        length = len(reply_text.strip())
        
        # 매장별 설정된 길이 제한 사용
        min_length = store_settings.get('min_reply_length', 50)
        max_length = store_settings.get('max_reply_length', 200)
        
        # 최소 길이 검증
        if length < min_length:
            issues.append(f"답글이 너무 짧습니다 (최소 {min_length}자, 현재 {length}자)")
            return False
        elif length < min_length + 10:  # 설정값에서 10자 이내면 경고
            warnings.append(f"답글이 다소 짧습니다 (권장 {min_length + 10}자 이상, 현재 {length}자)")
        
        # 최대 길이 검증
        if length > max_length:
            issues.append(f"답글이 너무 깁니다 (최대 {max_length}자, 현재 {length}자)")
            return False
        elif length > max_length - 20:  # 설정값에서 20자 이내면 경고
            warnings.append(f"답글이 다소 깁니다 (권장 {max_length - 20}자 이하, 현재 {length}자)")
        
        return True
    
    def _validate_tone(self, reply_text: str, sentiment: str, store_settings: Dict,
                      issues: List[str], warnings: List[str]) -> bool:
        """톤 검증"""
        
        reply_lower = reply_text.lower()
        
        # 1. 감정에 맞는 필수 요소 확인
        required = self.required_elements.get(sentiment, [])
        missing_elements = []
        
        for element in required:
            if element not in reply_lower:
                missing_elements.append(element)
        
        if len(missing_elements) > len(required) * 0.5:  # 50% 이상 누락
            warnings.append(f"{sentiment} 리뷰에 적절한 표현이 부족합니다: {', '.join(missing_elements[:2])}")
        
        # 2. 존댓말 확인
        if not self._check_honorifics(reply_text):
            issues.append("존댓말을 사용해주세요")
            return False
        
        return True
    
    def _validate_content_relevance(self, reply_text: str, review_data: Dict,
                                  issues: List[str], warnings: List[str], 
                                  suggestions: List[str]) -> bool:
        """내용 관련성 검증"""
        
        review_text = review_data.get('review_text', '').lower()
        reply_lower = reply_text.lower()
        rating = review_data.get('rating', 3)
        
        if not review_text:
            return True  # 리뷰 텍스트가 없으면 검증 스킵
        
        # 평점과 답글 톤 일치성
        if rating >= 4:  # 긍정 리뷰
            if not any(positive in reply_lower for positive in ['감사', '기쁘', '좋', '만족']):
                warnings.append("긍정적인 리뷰에 대한 감사 표현을 추가해보세요")
        
        elif rating <= 2:  # 부정 리뷰
            if not any(negative in reply_lower for negative in ['죄송', '사과', '개선', '미안']):
                issues.append("부정적인 리뷰에 대한 사과 표현이 필요합니다")
                return False
        
        return True
    
    def _validate_safety(self, reply_text: str, issues: List[str], warnings: List[str]) -> bool:
        """안전성 검증"""
        
        reply_lower = reply_text.lower()
        
        # 1. 금지 단어 확인
        found_forbidden = [word for word in self.forbidden_words if word in reply_lower]
        if found_forbidden:
            issues.append(f"부적절한 표현이 포함되어 있습니다: {', '.join(found_forbidden)}")
            return False
        
        # 2. 민감한 패턴 확인
        for pattern in self.sensitive_patterns:
            if re.search(pattern, reply_text):
                warnings.append(f"주의가 필요한 표현이 있습니다: {pattern}")
        
        # 3. 개인정보 패턴 확인
        phone_pattern = r'\d{2,3}-\d{3,4}-\d{4}'
        if re.search(phone_pattern, reply_text):
            issues.append("개인정보(전화번호)가 포함되어 있습니다")
            return False
        
        return True
    
    def _check_honorifics(self, text: str) -> bool:
        """존댓말 사용 확인"""
        
        # 존댓말 패턴
        honorific_patterns = [
            r'습니다', r'세요', r'시죠', r'십시오', r'해요', r'드려', r'어요', r'아요'
        ]
        
        # 반말 패턴
        informal_patterns = [
            r'한다[\.!?]', r'이다[\.!?]', r'이야[\.!?]', r'야[\.!?]$'
        ]
        
        has_honorifics = any(re.search(pattern, text) for pattern in honorific_patterns)
        has_informal = any(re.search(pattern, text) for pattern in informal_patterns)
        
        return has_honorifics and not has_informal
    
    def _calculate_overall_score(self, length_check: bool, tone_check: bool,
                               content_relevance: bool, safety_check: bool,
                               issue_count: int) -> float:
        """전체 점수 계산"""
        
        base_score = 0.0
        
        if length_check:
            base_score += 0.2
        if tone_check:
            base_score += 0.3
        if content_relevance:
            base_score += 0.3
        if safety_check:
            base_score += 0.2
        
        # 이슈 개수에 따른 감점
        penalty = min(issue_count * 0.1, 0.5)
        
        return max(0.0, base_score - penalty)
    
    def _generate_suggestions(self, reply_text: str, review_data: Dict, 
                            suggestions: List[str]):
        """개선 제안 생성"""
        
        # 길이 기반 제안
        length = len(reply_text.strip())
        if length < 50:
            suggestions.append("더 구체적이고 따뜻한 표현을 추가해보세요")
        
        # 이모티콘 제안
        if '😊' not in reply_text and '🙏' not in reply_text:
            suggestions.append("적절한 이모티콘을 추가하면 더 친근해집니다")
        
        # 재방문 유도 제안
        if review_data.get('rating', 0) >= 4:
            if '재방문' not in reply_text and '다시' not in reply_text:
                suggestions.append("재방문을 자연스럽게 유도하는 표현을 추가해보세요")
        
        # 개선 약속 제안
        if review_data.get('rating', 0) <= 2:
            if '개선' not in reply_text and '노력' not in reply_text:
                suggestions.append("구체적인 개선 계획을 언급해보세요")
    
    # ===== 4. 멀티플랫폼 지원 기능 =====
    
    async def process_user_reviews(self, user_id: str, platforms: Optional[List[Union[str, Platform]]] = None, 
                                 limit: Optional[int] = None) -> Dict[str, BatchSummary]:
        """사용자의 모든 매장에서 리뷰 처리 (멀티플랫폼)"""
        
        start_time = datetime.now()
        
        if platforms is None:
            platforms = list(Platform)
        else:
            # 문자열을 Platform enum으로 변환
            platforms = parse_platform_list(platforms)
        
        print(f"[AI] 사용자 {user_id[:8]}... 멀티플랫폼 리뷰 처리 시작")
        print(f"   대상 플랫폼: {[p.value.upper() for p in platforms]}")
        
        # 플랫폼별 결과 저장
        platform_results = {}
        
        for platform in platforms:
            try:
                print(f"\n[PLATFORM] {platform.value.upper()} 플랫폼 처리 시작...")
                
                # 해당 플랫폼의 사용자 매장들 조회
                stores = await self._get_user_stores(user_id, platform.value)
                
                if not stores:
                    print(f"   매장 없음: {platform.value.upper()}")
                    platform_results[platform.value] = BatchSummary(
                        total_reviews=0, processed=0, success=0, failed=0, skipped=0,
                        high_risk=0, requires_approval=0, auto_approved=0,
                        processing_time_seconds=0.0, results=[]
                    )
                    continue
                
                print(f"   매장 수: {len(stores)}개")
                
                # 플랫폼별 전체 결과 누적
                all_results = []
                total_reviews_processed = 0
                
                for store in stores:
                    store_id = store['id']
                    store_name = store['store_name']
                    
                    print(f"   └─ [{store_name}] 처리 중...")
                    
                    # 매장별 리뷰 처리
                    store_summary = await self.process_store_reviews(
                        store_id, platform.value, limit
                    )
                    
                    all_results.extend(store_summary.results)
                    total_reviews_processed += store_summary.total_reviews
                    
                    # 매장 간 잠시 대기
                    await asyncio.sleep(1)
                
                # 플랫폼별 요약 계산
                platform_summary = self._calculate_summary(all_results, start_time)
                platform_results[platform.value] = platform_summary
                
                print(f"   [OK] {platform.value.upper()}: {total_reviews_processed}개 리뷰 중 {platform_summary.success}개 처리 완료")
                
            except Exception as e:
                print(f"   [ERROR] {platform.value.upper()} 플랫폼 처리 실패: {e}")
                platform_results[platform.value] = BatchSummary(
                    total_reviews=0, processed=0, success=0, failed=1, skipped=0,
                    high_risk=0, requires_approval=0, auto_approved=0,
                    processing_time_seconds=0.0, 
                    results=[ProcessingResult(user_id, "failed", str(e))]
                )
        
        # 전체 결과 요약 출력
        self._print_multiplatform_summary(platform_results, user_id)
        
        return platform_results
    
    async def get_user_draft_reviews(self, user_id: str, platforms: Optional[List[Union[str, Platform]]] = None,
                                   limit: Optional[int] = None) -> Dict[str, List[UnifiedReview]]:
        """사용자의 답글 대기 리뷰 조회 (멀티플랫폼)"""
        
        if platforms is None:
            platforms = list(Platform)
        else:
            platforms = parse_platform_list(platforms)
        
        print(f"[SEARCH] 사용자 {user_id[:8]}... 답글 대기 리뷰 조회")
        
        draft_reviews = self.platform_manager.get_draft_reviews_by_user(
            user_id, platforms, limit
        )
        
        # 결과 출력
        total_drafts = sum(len(reviews) for reviews in draft_reviews.values())
        print(f"   총 {total_drafts}개 답글 대기 리뷰 발견")
        
        for platform, reviews in draft_reviews.items():
            if reviews:
                print(f"   - {platform.value.upper()}: {len(reviews)}개")
        
        return draft_reviews
    
    def _print_multiplatform_summary(self, platform_results: Dict[str, BatchSummary], user_id: str):
        """멀티플랫폼 처리 결과 요약 출력"""
        
        print(f"\n{'='*80}")
        print(f"[RESULTS] 사용자 {user_id[:8]}... 멀티플랫폼 처리 결과")
        print(f"{'='*80}")
        
        total_reviews = sum(s.total_reviews for s in platform_results.values())
        total_success = sum(s.success for s in platform_results.values())
        total_failed = sum(s.failed for s in platform_results.values())
        total_approval = sum(s.requires_approval for s in platform_results.values())
        
        print(f"[TOTAL] 총 리뷰: {total_reviews}개")
        print(f"[OK] 처리 성공: {total_success}개")
        print(f"[ERROR] 처리 실패: {total_failed}개") 
        print(f"[PENDING] 승인 대기: {total_approval}개")
        print(f"\n플랫폼별 상세:")
        
        for platform, summary in platform_results.items():
            if summary.total_reviews > 0:
                print(f"  [PLATFORM] {platform.upper()}: {summary.total_reviews}개 리뷰, {summary.success}개 성공")
        
        if total_approval > 0:
            print(f"\n⚠️  총 {total_approval}개 리뷰가 사장님 승인을 기다리고 있습니다!")
    
    async def _get_user_stores(self, user_id: str, platform: str) -> List[Dict]:
        """사용자의 특정 플랫폼 매장 조회"""
        
        response = self.supabase.table('platform_stores')\
            .select('id, store_name, platform, is_active')\
            .eq('user_id', user_id)\
            .eq('platform', platform)\
            .eq('is_active', True)\
            .execute()
        
        return response.data or []

    # ===== 5. 배치 처리 기능 =====
    
    async def process_store_reviews(self, store_id: str, platform: str = 'naver', limit: Optional[int] = None) -> BatchSummary:
        """특정 매장의 미답변 리뷰 처리"""
        
        start_time = datetime.now()
        
        # 1. 매장 설정 로드
        store_settings = await self._get_store_settings(store_id)
        if not store_settings:
            raise ValueError(f"매장 정보를 찾을 수 없습니다: {store_id}")
        
        # 2. 미답변 리뷰 조회
        reviews = await self._get_unanswered_reviews(store_id, platform, limit)
        
        if not reviews:
            print(f"매장 {store_settings['store_name']} ({platform}): 처리할 리뷰가 없습니다")
            return BatchSummary(
                total_reviews=0, processed=0, success=0, failed=0, skipped=0,
                high_risk=0, requires_approval=0, auto_approved=0,
                processing_time_seconds=0.0, results=[]
            )
        
        print(f"매장 {store_settings['store_name']} ({platform}): {len(reviews)}개 리뷰 처리 시작")
        
        # 3. 세마포어로 동시 처리 제한
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 4. 배치 처리
        tasks = []
        for review in reviews:
            task = asyncio.create_task(
                self._process_single_review_with_semaphore(
                    semaphore, review, store_settings, platform
                )
            )
            tasks.append(task)
        
        # 5. 모든 작업 완료 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 6. 결과 정리
        processing_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processing_results.append(ProcessingResult(
                    review_id=reviews[i]['id'],
                    status="failed",
                    error_message=str(result)
                ))
            else:
                processing_results.append(result)
        
        # 7. 통계 계산
        summary = self._calculate_summary(processing_results, start_time)
        
        # 8. 결과 출력
        self._print_summary(store_settings['store_name'], summary)
        
        return summary
    
    async def process_all_active_stores(self, limit_per_store: Optional[int] = None) -> Dict[str, BatchSummary]:
        """모든 활성 매장의 리뷰 처리"""
        
        # 자동 답글이 활성화된 매장들 조회
        active_stores = await self._get_active_stores()
        
        if not active_stores:
            print("자동 답글이 활성화된 매장이 없습니다")
            return {}
        
        print(f"총 {len(active_stores)}개 매장의 리뷰 처리를 시작합니다")
        
        results = {}
        for store in active_stores:
            store_id = store['id']
            store_name = store['store_name']
            
            try:
                print(f"\n[{store_name}] 처리 시작...")
                summary = await self.process_store_reviews(store_id, limit_per_store)
                results[store_id] = summary
                
                # 매장 간 대기 시간
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"[{store_name}] 처리 실패: {str(e)}")
                results[store_id] = BatchSummary(
                    total_reviews=0, processed=0, success=0, failed=1, skipped=0,
                    high_risk=0, requires_approval=0, auto_approved=0,
                    processing_time_seconds=0.0, 
                    results=[ProcessingResult(store_id, "failed", str(e))]
                )
        
        # 전체 결과 요약
        self._print_overall_summary(results)
        
        return results
    
    async def _process_single_review_with_semaphore(self, semaphore: asyncio.Semaphore, 
                                                   review: Dict, store_settings: Dict, platform: str = 'naver') -> ProcessingResult:
        """세마포어를 사용한 단일 리뷰 처리"""
        
        async with semaphore:
            # API 호출 제한
            await asyncio.sleep(self.rate_limit_delay)
            return await self._process_single_review(review, store_settings, platform)
    
    async def _process_single_review(self, review: Union[Dict, UnifiedReview], store_settings: Dict, platform: str = 'naver') -> ProcessingResult:
        """단일 리뷰 처리 (재활용 로직 포함)"""
        
        # UnifiedReview 객체를 Dict로 변환 (호환성을 위해)
        if isinstance(review, UnifiedReview):
            review_dict = {
                'id': review.id,
                'reviewer_name': review.reviewer_name,
                'rating': review.rating,
                'review_text': review.review_text,
                'review_date': review.review_date,
                'reply_status': review.reply_status,
                'platform_store_id': review.platform_store_id
            }
            review_id = review.id
        else:
            review_dict = review
            review_id = review['id']
        
        try:
            # 기존 답글과 실패 사유 확인
            existing_reply = review_dict.get('reply_text')
            failure_field = self._get_failure_field(platform)
            failure_reason = review_dict.get(failure_field)
            
            # 네이버는 ai_generated_reply 필드도 확인
            if platform == 'naver':
                existing_reply = existing_reply or review_dict.get('ai_generated_reply')
            
            result = None
            
            if existing_reply and failure_reason:
                # 실패한 경우 재생성
                print(f"[RETRY] 리뷰 {review_id[:8]} ({platform}): 금지어로 실패한 답글 재생성")
                print(f"  - 실패 사유: {failure_reason[:100]}...")
                print(f"  - 작성자명: {review_dict.get('reviewer_name')}")
                
                # AI를 통한 재생성
                result = await self._generate_reply_after_failure(
                    review_data=review_dict,
                    store_settings=store_settings,
                    previous_reply=existing_reply,
                    failure_reason=failure_reason,
                    platform=platform
                )
                
            elif existing_reply and not failure_reason:
                # 성공한 답글은 스킵
                print(f"[SKIP] 리뷰 {review_id[:8]} ({platform}): 이미 성공한 답글 존재")
                return ProcessingResult(
                    review_id=review_id,
                    status="skipped",
                    reply_status=review_dict.get('reply_status', 'draft')
                )
                
            else:
                # 신규 생성
                print(f"[NEW] 리뷰 {review_id[:8]} ({platform}): 신규 답글 생성")
                result = await self.generate_reply(review_dict, store_settings, platform)
            
            # 2. 리뷰 분석 정보 추출
            analysis = await self.analyze_review(review_dict, store_settings)
            
            # 3. 우선순위 판단 (schedulable_reply_date 설정을 위해)
            priority, _ = self.korean_generator.get_priority_level(
                review_dict.get('review_text', ''),
                review_dict.get('rating', 3),
                store_settings
            )
            
            # 4. 답글 상태 결정
            reply_status = self._determine_reply_status(analysis, store_settings, platform)
            
            # 5. 데이터베이스 업데이트
            await self._update_review_with_reply(review_id, result, analysis, reply_status, platform, priority, review_dict)
            
            action = "재생성" if failure_reason else "생성"
            print(f"[OK] 리뷰 {review_id[:8]} ({platform}): {action} 완료 - {reply_status} ({analysis.risk_level})")
            
            return ProcessingResult(
                review_id=review_id,
                status="success",
                reply_status=reply_status,
                requires_approval=analysis.requires_approval
            )
            
        except Exception as e:
            print(f"[ERROR] 리뷰 {review_id[:8]} ({platform}) 처리 실패: {str(e)}")
            return ProcessingResult(
                review_id=review_id,
                status="failed",
                error_message=str(e)
            )
    
    def _determine_reply_status(self, analysis: ReviewAnalysis, store_settings: Dict, platform: str = 'naver') -> str:
        """답글 상태 결정"""
        
        if analysis.risk_level == "high_risk":
            return "draft"  # 고위험은 무조건 승인 대기
        
        if analysis.requires_approval:
            return "draft"  # 승인 필요한 경우 대기
        
        # 자동 승인 가능한 경우 (Naver만 approved 상태를 지원)
        if (platform == 'naver' and analysis.sentiment == "positive" and 
            store_settings.get('auto_approve_positive', False)):
            return "approved"
        
        return "draft"  # 기본값
    
    def _calculate_schedulable_date(self, priority: str, review_dict: Dict) -> str:
        """schedulable_reply_date 계산 - 00시 기준으로 정확한 날짜 계산"""
        
        if not review_dict or 'review_date' not in review_dict:
            # review_date가 없으면 현재 시간 기준으로 계산
            review_date = datetime.now().date()
        else:
            # review_date 파싱 (ISO 형식 가정)
            review_date_str = review_dict['review_date']
            try:
                parsed_datetime = datetime.fromisoformat(review_date_str.replace('Z', '+00:00'))
                review_date = parsed_datetime.date()  # 날짜만 추출
            except:
                # 파싱 실패시 현재 날짜 사용
                review_date = datetime.now().date()
        
        # 우선순위에 따른 지연 일수 설정
        priority_value = priority.value if hasattr(priority, 'value') else priority
        
        if priority_value == 'auto':  # AUTO: 단순 긍정 리뷰
            delay_days = 1  # 다음날 00시
        else:  # 사장님 확인 필요: 불만, 질문, 위험 모두
            delay_days = 2  # 모레 00시
        
        # 목표 날짜의 00시로 설정
        target_date = review_date + timedelta(days=delay_days)
        schedulable_datetime = datetime.combine(target_date, datetime.min.time())
        
        return schedulable_datetime.isoformat()
    
    async def _update_review_with_reply(self, review_id: str, result: ReplyResult, 
                                      analysis: ReviewAnalysis, reply_status: str, platform: str = 'naver',
                                      priority: str = None, review_dict: Dict = None):
        """리뷰 데이터베이스 업데이트 (모든 플랫폼 통합)"""
        
        table_name = self._get_table_name(platform)
        failure_field = self._get_failure_field(platform)
        
        # schedulable_reply_date 계산
        schedulable_reply_date = self._calculate_schedulable_date(priority, review_dict)
        
        # 기본 업데이트 데이터 (모든 플랫폼 공통)
        update_data = {
            'reply_status': reply_status,
            'reply_text': result.complete_reply,  # 모든 플랫폼에 답글 저장
            'requires_approval': analysis.requires_approval,  # 모든 플랫폼에 승인 필요 여부
            'schedulable_reply_date': schedulable_reply_date,
            'updated_at': datetime.now().isoformat()
        }
        
        # 실패 사유 필드 초기화 (성공 시)
        update_data[failure_field] = None
        
        # Naver 플랫폼만 추가 AI 관련 컬럼들이 있음
        if platform == 'naver':
            update_data.update({
                # AI 분석 결과
                'sentiment': analysis.sentiment,
                'sentiment_score': analysis.sentiment_score,
                # extracted_keywords는 크롤링에서 가져온 원본 키워드이므로 덮어쓰지 않음
                # 'extracted_keywords': analysis.keywords,  # 이 라인 제거!

                # AI 답글 정보
                'ai_generated_reply': result.ai_generated_reply,
                'ai_model_used': result.ai_model_used,
                'ai_generation_time_ms': result.ai_generation_time_ms,
                'ai_confidence_score': result.ai_confidence_score,
            })
        
        response = self.supabase.table(table_name).update(update_data).eq('id', review_id).execute()
        
        if not response.data:
            raise Exception(f"데이터베이스 업데이트 실패: {table_name}")
    
    async def _get_store_settings(self, store_id: str) -> Optional[Dict]:
        """매장 설정 조회"""
        
        response = self.supabase.table('platform_stores').select('*').eq('id', store_id).single().execute()
        
        return response.data if response.data else None
    
    async def _get_unanswered_reviews(self, store_id: str, platform: str = 'naver', limit: Optional[int] = None) -> List[Dict]:
        """미답변 리뷰 조회 (실패한 리뷰 포함)"""
        
        table_name = self._get_table_name(platform)
        failure_field = self._get_failure_field(platform)
        
        # 두 개의 쿼리로 나누어 실행 후 합치기
        all_reviews = []
        
        try:
            # 1차: 미답변 리뷰 조회
            if platform == 'naver':
                # Naver: ai_generated_reply가 null인 경우
                query1 = self.supabase.table(table_name)\
                    .select('*')\
                    .eq('platform_store_id', store_id)\
                    .is_('ai_generated_reply', 'null')\
                    .order('review_date', desc=False)
            else:
                # 배달 플랫폼들: reply_text가 null이거나 빈 문자열인 경우
                # 방법 1: null인 리뷰 조회
                query1 = self.supabase.table(table_name)\
                    .select('*')\
                    .eq('platform_store_id', store_id)\
                    .is_('reply_text', 'null')\
                    .order('review_date', desc=False)

            response1 = query1.execute()
            if response1.data:
                all_reviews.extend(response1.data)

            # 1-2차: 빈 문자열인 리뷰도 조회 (배달 플랫폼만)
            if platform != 'naver':
                query1b = self.supabase.table(table_name)\
                    .select('*')\
                    .eq('platform_store_id', store_id)\
                    .eq('reply_text', '')\
                    .order('review_date', desc=False)

                response1b = query1b.execute()
                if response1b.data:
                    # 중복 제거
                    existing_ids = {review['id'] for review in all_reviews}
                    for review in response1b.data:
                        if review['id'] not in existing_ids:
                            all_reviews.append(review)
            
            # 2차: 실패한 리뷰 조회
            query2 = self.supabase.table(table_name)\
                .select('*')\
                .eq('platform_store_id', store_id)\
                .not_.is_(failure_field, 'null')\
                .order('review_date', desc=False)
            
            response2 = query2.execute()
            if response2.data:
                # 중복 제거 (ID 기준)
                existing_ids = {review['id'] for review in all_reviews}
                for review in response2.data:
                    if review['id'] not in existing_ids:
                        all_reviews.append(review)
            
            # 날짜순 정렬
            all_reviews.sort(key=lambda x: x.get('review_date', ''))
            
            # 제한 적용
            if limit and len(all_reviews) > limit:
                all_reviews = all_reviews[:limit]
            
            return all_reviews
            
        except Exception as e:
            print(f"[ERROR] 리뷰 조회 실패 ({platform}): {str(e)}")
            return []
    
    async def _get_active_stores(self) -> List[Dict]:
        """자동 답글이 활성화된 매장 조회"""
        
        response = self.supabase.table('platform_stores')\
            .select('id, store_name, auto_reply_enabled')\
            .eq('auto_reply_enabled', True)\
            .eq('is_active', True)\
            .execute()
        
        return response.data or []
    
    def _calculate_summary(self, results: List[ProcessingResult], start_time: datetime) -> BatchSummary:
        """처리 결과 요약 계산"""
        
        total_reviews = len(results)
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        skipped_count = sum(1 for r in results if r.status == "skipped")
        
        requires_approval_count = sum(1 for r in results 
                                    if r.status == "success" and r.requires_approval)
        auto_approved_count = sum(1 for r in results 
                                if r.status == "success" and not r.requires_approval)
        
        # 고위험 리뷰는 결과에서 추정 (실제로는 분석 결과를 저장해야 함)
        high_risk_count = sum(1 for r in results 
                            if r.status == "success" and r.requires_approval)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return BatchSummary(
            total_reviews=total_reviews,
            processed=success_count + failed_count + skipped_count,
            success=success_count,
            failed=failed_count,
            skipped=skipped_count,
            high_risk=high_risk_count,
            requires_approval=requires_approval_count,
            auto_approved=auto_approved_count,
            processing_time_seconds=processing_time,
            results=results
        )
    
    def _print_summary(self, store_name: str, summary: BatchSummary):
        """처리 결과 요약 출력"""
        
        print(f"\n{'='*60}")
        print(f"[RESULTS] [{store_name}] 처리 결과 요약")
        print(f"{'='*60}")
        print(f"[TOTAL] 총 리뷰: {summary.total_reviews}개")
        print(f"[OK] 성공: {summary.success}개")
        print(f"[ERROR] 실패: {summary.failed}개")
        print(f"[SKIP] 건너뜀: {summary.skipped}개")
        print(f"[HIGH] 고위험: {summary.high_risk}개")
        print(f"[PENDING] 승인 대기: {summary.requires_approval}개")
        print(f"[AUTO] 자동 승인: {summary.auto_approved}개")
        print(f"[TIME] 처리 시간: {summary.processing_time_seconds:.1f}초")
        
        if summary.success > 0:
            avg_time = summary.processing_time_seconds / summary.success
            print(f"[AVG] 평균 처리 시간: {avg_time:.1f}초/리뷰")
    
    def _print_overall_summary(self, results: Dict[str, BatchSummary]):
        """전체 처리 결과 요약"""
        
        total_stores = len(results)
        total_reviews = sum(s.total_reviews for s in results.values())
        total_success = sum(s.success for s in results.values())
        total_requires_approval = sum(s.requires_approval for s in results.values())
        
        print(f"\n{'='*80}")
        print(f"[STORES] 전체 매장 처리 결과")
        print(f"{'='*80}")
        print(f"[STORES] 처리 매장: {total_stores}개")
        print(f"[TOTAL] 총 리뷰: {total_reviews}개")
        print(f"[OK] 성공: {total_success}개")
        print(f"[PENDING] 승인 필요: {total_requires_approval}개")
        
        if total_requires_approval > 0:
            print(f"\n⚠️  {total_requires_approval}개 리뷰가 사장님 승인을 기다리고 있습니다!")
    
    # ===== 5. 승인 워크플로우 기능 =====
    
    async def approve_reply(self, review_id: str, user_id: str, platform: str = 'naver',
                          notes: Optional[str] = None) -> bool:
        """답글 승인"""
        
        try:
            # 1. 리뷰 정보 조회
            review = await self._get_review(review_id, platform)
            if not review:
                raise ValueError("리뷰를 찾을 수 없습니다")
            
            # 2. 권한 확인
            if not await self._check_approval_permission(user_id, review['platform_store_id']):
                raise ValueError("승인 권한이 없습니다")
            
            # 3. 상태 업데이트
            table_name = self._get_table_name(platform)
            update_data = {
                'reply_status': ReplyStatus.APPROVED.value,
                'approved_by': user_id,
                'approved_at': datetime.now().isoformat(),
                'approval_notes': notes,
                'updated_at': datetime.now().isoformat()
            }
            
            # AI 생성 답글을 실제 답글로 복사
            if review.get('ai_generated_reply'):
                update_data['reply_text'] = review['ai_generated_reply']
            
            response = self.supabase.table(table_name)\
                .update(update_data)\
                .eq('id', review_id)\
                .execute()
            
            if not response.data:
                raise Exception("데이터베이스 업데이트 실패")
            
            print(f"[OK] 리뷰 {review_id[:8]} ({platform}) 승인 완료")
            return True
            
        except Exception as e:
            print(f"[ERROR] 승인 실패: {str(e)}")
            return False
    
    async def reject_reply(self, review_id: str, user_id: str, platform: str = 'naver',
                          reason: str = "") -> bool:
        """답글 거부"""
        
        try:
            # 1. 권한 확인
            review = await self._get_review(review_id, platform)
            if not review:
                raise ValueError("리뷰를 찾을 수 없습니다")
            
            if not await self._check_approval_permission(user_id, review['platform_store_id']):
                raise ValueError("거부 권한이 없습니다")
            
            # 2. 상태를 draft로 되돌림
            table_name = self._get_table_name(platform)
            update_data = {
                'reply_status': ReplyStatus.DRAFT.value,
                'ai_generated_reply': None,  # AI 답글 삭제
                'approval_notes': f"거부됨: {reason}",
                'updated_at': datetime.now().isoformat()
            }
            
            response = self.supabase.table(table_name)\
                .update(update_data)\
                .eq('id', review_id)\
                .execute()
            
            if not response.data:
                raise Exception("데이터베이스 업데이트 실패")
            
            print(f"[OK] 리뷰 {review_id[:8]} ({platform}) 거부 완료")
            return True
            
        except Exception as e:
            print(f"[ERROR] 거부 실패: {str(e)}")
            return False
    
    async def edit_and_approve_reply(self, review_id: str, user_id: str, 
                                   edited_reply: str, notes: Optional[str] = None) -> bool:
        """답글 수정 후 승인"""
        
        try:
            # 1. 권한 확인
            review = await self._get_review(review_id)
            if not review:
                raise ValueError("리뷰를 찾을 수 없습니다")
            
            if not await self._check_approval_permission(user_id, review['platform_store_id']):
                raise ValueError("수정 권한이 없습니다")
            
            # 2. 수정된 답글로 업데이트
            update_data = {
                'reply_text': edited_reply,
                'reply_status': ReplyStatus.APPROVED.value,
                'approved_by': user_id,
                'approved_at': datetime.now().isoformat(),
                'approval_notes': notes,
                'updated_at': datetime.now().isoformat()
            }
            
            response = self.supabase.table('reviews_naver')\
                .update(update_data)\
                .eq('id', review_id)\
                .execute()
            
            if not response.data:
                raise Exception("데이터베이스 업데이트 실패")
            
            print(f"[EDIT] 리뷰 {review_id[:8]} 수정 후 승인 완료")
            return True
            
        except Exception as e:
            print(f"[ERROR] 수정 실패: {str(e)}")
            return False
    
    async def get_pending_approvals(self, user_id: str, store_id: Optional[str] = None) -> List[Dict]:
        """승인 대기 중인 답글 조회 (우선순위 정렬)"""
        
        try:
            # 1. 사용자가 관리하는 매장들 조회
            if store_id:
                store_ids = [store_id]
            else:
                stores_response = self.supabase.table('platform_stores')\
                    .select('id')\
                    .eq('user_id', user_id)\
                    .eq('is_active', True)\
                    .execute()
                
                store_ids = [store['id'] for store in (stores_response.data or [])]
            
            if not store_ids:
                return []
            
            # 2. 승인 대기 중인 리뷰들 조회
            response = self.supabase.table('reviews_naver')\
                .select('''
                    id, naver_review_id, reviewer_name, rating, review_text, review_date,
                    sentiment, ai_generated_reply, ai_confidence_score, requires_approval,
                    platform_store_id, created_at,
                    platform_store:platform_stores(store_name, business_type)
                ''')\
                .in_('platform_store_id', store_ids)\
                .eq('reply_status', ReplyStatus.DRAFT.value)\
                .eq('requires_approval', True)\
                .not_.is_('ai_generated_reply', 'null')\
                .order('created_at', desc=False)\
                .execute()
            
            pending_reviews = response.data or []
            
            # 3. 각 리뷰에 우선순위 추가
            for review in pending_reviews:
                priority, reason = self.korean_generator.get_priority_level(
                    review.get('review_text', ''),
                    review.get('rating', 3),
                    {'store_name': review.get('platform_store', {}).get('store_name', '')}
                )
                review['priority'] = priority
                review['priority_reason'] = reason
                review['priority_score'] = self._get_priority_score(priority)
            
            # 4. 우선순위로 정렬 (점수가 낮을수록 높은 우선순위)
            pending_reviews.sort(key=lambda x: (
                x.get('priority_score', 999),
                x.get('created_at', '')
            ))
            
            return pending_reviews
            
        except Exception as e:
            print(f"승인 대기 조회 실패: {str(e)}")
            return []
    
    def _get_priority_score(self, priority: ReviewPriority) -> int:
        """우선순위를 숫자로 변환 (낮을수록 높은 우선순위)"""
        scores = {
            ReviewPriority.URGENT: 1,
            ReviewPriority.HIGH: 2,
            ReviewPriority.MEDIUM: 3,
            ReviewPriority.LOW: 4,
            ReviewPriority.AUTO: 5
        }
        return scores.get(priority, 999)
    
    async def auto_approve_positive_reviews(self, store_id: str) -> int:
        """긍정 리뷰 자동 승인"""
        
        try:
            # 매장 설정 확인
            store = await self._get_store_settings(store_id)
            if not store or not store.get('auto_approve_positive', False):
                return 0
            
            # 자동 승인 가능한 긍정 리뷰 조회
            response = self.supabase.table('reviews_naver')\
                .select('id')\
                .eq('platform_store_id', store_id)\
                .eq('reply_status', ReplyStatus.DRAFT.value)\
                .eq('sentiment', 'positive')\
                .eq('requires_approval', False)\
                .gte('rating', 4)\
                .not_.is_('ai_generated_reply', 'null')\
                .execute()
            
            auto_approve_reviews = response.data or []
            
            if not auto_approve_reviews:
                return 0
            
            # 일괄 승인
            review_ids = [review['id'] for review in auto_approve_reviews]
            
            for review_id in review_ids:
                await self.approve_reply(review_id, 'system', '긍정 리뷰 자동 승인')
            
            print(f"[OK] 긍정 리뷰 {len(review_ids)}개 자동 승인 완료")
            return len(review_ids)
            
        except Exception as e:
            print(f"[ERROR] 자동 승인 실패: {str(e)}")
            return 0
    
    async def _get_review(self, review_id: str, platform: str = 'naver') -> Optional[Dict]:
        """리뷰 정보 조회"""
        
        table_name = self._get_table_name(platform)
        response = self.supabase.table(table_name)\
            .select('*')\
            .eq('id', review_id)\
            .single()\
            .execute()
        
        return response.data if response.data else None
    
    async def _check_approval_permission(self, user_id: str, store_id: str) -> bool:
        """승인 권한 확인"""
        
        response = self.supabase.table('platform_stores')\
            .select('user_id')\
            .eq('id', store_id)\
            .eq('user_id', user_id)\
            .single()\
            .execute()
        
        return bool(response.data)
    
    def _is_high_risk_review(self, review: Dict) -> bool:
        """고위험 리뷰 판단"""
        
        # 1점 리뷰이거나 특정 키워드가 있으면 고위험
        if review.get('rating', 5) == 1:
            return True
        
        review_text = review.get('review_text', '').lower()
        high_risk_keywords = ['환불', '신고', '위생', '식중독', '이물질']
        
        return any(keyword in review_text for keyword in high_risk_keywords)


# 사용 예시 및 테스트
async def main():
    """테스트 함수"""
    
    try:
        manager = AIReplyManager()
        
        # 테스트 데이터
        test_review = {
            "id": "test-review-123",
            "review_text": "음식이 정말 맛있었어요. 직원분들도 친절하시고 분위기도 좋네요.",
            "rating": 5,
            "reviewer_name": "김고객",
            "review_date": "2024-01-15"
        }
        
        test_store = {
            "store_name": "맛집카페",
            "business_type": "카페",
            "reply_style": "friendly",
            "auto_reply_enabled": True,
            "auto_approve_positive": True,
            "branding_keywords": ["맛집카페", "신선한"],
            "seo_keywords": ["카페", "맛집"]
        }
        
        print("[AI] AI 답글 생성 테스트")
        print("="*50)
        
        # 1. 리뷰 분석
        analysis = await manager.analyze_review(test_review, test_store)
        print(f"감정: {analysis.sentiment} ({analysis.sentiment_score:.2f})")
        print(f"위험도: {analysis.risk_level}")
        print(f"승인 필요: {analysis.requires_approval}")
        print(f"키워드: {', '.join(analysis.keywords)}")
        
        # 2. AI 답글 생성
        reply_result = await manager.generate_reply(test_review, test_store)
        print(f"\n생성된 답글:")
        print(f"{reply_result.complete_reply}")
        print(f"\n신뢰도: {reply_result.ai_confidence_score:.2f}")
        print(f"생성 시간: {reply_result.ai_generation_time_ms}ms")
        
        # 3. 품질 검증
        validation = await manager.validate_reply(
            reply_result.complete_reply, test_review, test_store, analysis.sentiment
        )
        print(f"\n검증 결과: {'통과' if validation.is_valid else '실패'}")
        print(f"품질 점수: {validation.score:.2f}")
        
        if validation.warnings:
            print(f"경고: {', '.join(validation.warnings)}")
        if validation.suggestions:
            print(f"제안: {', '.join(validation.suggestions)}")
        
    except Exception as e:
        print(f"테스트 실패: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())