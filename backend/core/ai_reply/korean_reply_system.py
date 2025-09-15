"""
한국형 AI 답글 생성 시스템
Korean-style AI Reply Generation System with Natural Language Processing
"""

import re
import random
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from enum import Enum
from platform_specific_reply_generator import PlatformSpecificReplyGenerator

class ReviewPriority(Enum):
    """리뷰 확인 우선순위 - 단순화된 2단계"""
    REQUIRES_APPROVAL = "requires_approval"  # 사장님 확인 필요 (48시간 후)
    AUTO = "auto"                           # 자동 답글 가능 (24시간 후)

class KoreanTone(Enum):
    """한국식 답글 톤앤매너"""
    FRIENDLY = "friendly"       # 친근함 (일반 고객)
    FORMAL = "formal"          # 정중함 (중요 고객/컴플레인)
    CASUAL = "casual"          # 캐주얼 (젊은 고객층)
    SINCERE = "sincere"        # 진정성 (사과/개선)

class KoreanReplyGenerator:
    """한국 정서에 맞는 자연스러운 답글 생성기"""
    
    def __init__(self):
        # 플랫폼별 특화 답글 생성기 초기화
        self.platform_generator = PlatformSpecificReplyGenerator()
        
        # 한국식 인사말 템플릿
        self.greetings = {
            "friendly": [
                "{customer}님 안녕하세요!",
                "{customer}님, 반갑습니다!",
                "안녕하세요 {customer}님!",
                "{customer}님 어서오세요!",
            ],
            "formal": [
                "{customer}님 안녕하십니까.",
                "{customer}님께 감사의 말씀을 드립니다.",
                "{customer}님, 귀중한 시간 내주셔서 감사합니다.",
            ],
            "casual": [
                "{customer}님 안녕하세요~",
                "{customer}님 반가워요!",
                "안녕하세요 {customer}님 ^^",
            ]
        }
        
        # 한국식 감사 표현
        self.thanks = {
            "positive": [
                "좋은 말씀 남겨주셔서 정말 감사드려요",
                "따뜻한 리뷰 너무 감사합니다",
                "칭찬해 주셔서 더욱 힘이 납니다",
                "좋게 봐주셔서 진심으로 감사드립니다",
                "소중한 리뷰 감사합니다",
            ],
            "negative": [
                "귀중한 의견 감사드립니다",
                "말씀해 주신 부분 정말 죄송합니다",
                "불편을 드려서 진심으로 죄송합니다", 
                "실망시켜 드려 정말 죄송합니다",
                "소중한 피드백 감사드리며, 깊이 사과드립니다",
            ],
            "neutral": [
                "방문해 주셔서 감사합니다",
                "리뷰 남겨주셔서 감사해요",
                "소중한 시간 내주셔서 감사합니다",
            ]
        }
        
        # 한국식 사과 표현 (핵심!)
        self.apologies = {
            "strong": [
                "정말 죄송합니다",
                "진심으로 사과드립니다", 
                "깊이 사과의 말씀을 드립니다",
                "너무 죄송한 마음입니다",
            ],
            "mild": [
                "불편을 드려 죄송합니다",
                "기대에 못 미쳐 죄송해요",
                "아쉬움을 드려 죄송합니다",
                "만족스럽지 못해 죄송합니다",
            ],
            "service": [
                "서비스가 부족했던 점 죄송합니다",
                "응대가 미흡했던 점 사과드립니다",
                "불친절했던 부분 정말 죄송합니다",
            ]
        }
        
        # 개선 약속 표현
        self.improvements = {
            "immediate": [
                "즉시 개선하겠습니다",
                "바로 시정하도록 하겠습니다",
                "당장 조치를 취하겠습니다",
                "오늘부터 바로 개선하겠습니다",
            ],
            "general": [
                "더 나은 서비스를 위해 노력하겠습니다",
                "앞으로 개선해 나가겠습니다",
                "더욱 신경쓰도록 하겠습니다",
                "말씀하신 부분 꼭 개선하겠습니다",
            ],
            "specific": {
                "taste": "맛을 더욱 개선하여 만족드릴 수 있도록 하겠습니다",
                "service": "직원 교육을 강화하여 서비스 개선하겠습니다",
                "cleanliness": "위생관리를 더욱 철저히 하겠습니다",
                "waiting": "대기시간을 단축할 수 있도록 개선하겠습니다",
                "price": "가격대비 만족도를 높일 수 있도록 노력하겠습니다",
            }
        }
        
        # 재방문 유도 (자연스럽게)
        self.revisit = {
            "positive": [
                "또 뵙기를 기대하겠습니다",
                "다음에도 좋은 시간 보내실 수 있도록 하겠습니다",
                "언제든 편하게 방문해 주세요",
                "또 놀러오세요",
            ],
            "negative": [
                "다음엔 꼭 만족드릴 수 있도록 하겠습니다",
                "한 번 더 기회를 주신다면 실망시키지 않겠습니다",
                "개선된 모습으로 다시 찾아주시길 부탁드립니다",
            ],
            "neutral": [
                "또 방문해 주세요",
                "다음에도 잘 부탁드립니다",
                "언제든 환영입니다",
            ]
        }
        
        # 자연스러운 장문 답글 템플릿 (150-400자) - 다양한 변형
        self.natural_templates = {
            "auto_positive": [
                "{customer}님 안녕하세요! 저희 {store}을/를 좋게 봐주셔서 정말 감사합니다. 이런 후기를 받으면 하루 종일 기분이 좋아져요. 앞으로도 {customer}님이 만족하실 수 있도록 더욱 노력하겠습니다. 건강하시고 또 뵙기를 기대할게요!",
                "와 {customer}님 감사해요! 정말 힘이 되는 리뷰네요. 요즘 같이 힘든 시기에 이런 따뜻한 말씀 한마디가 얼마나 큰 힘이 되는지 모르실 거예요. {customer}님 덕분에 오늘도 열심히 할 수 있을 것 같아요. 다음에도 좋은 음식으로 보답할게요!",
                "안녕하세요 {customer}님! 맛있게 드셨다니 다행이에요. 솔직히 매번 새로운 손님들이 오실 때마다 만족하실지 떨리기도 하는데, 이렇게 좋은 평가를 해주시니 정말 고맙습니다. 다음에 또 오시면 더 맛있는 메뉴로 놀라게 해드릴게요!",
                "{customer}님 후기 감사드려요! 사실 요리하는 입장에서는 손님들이 어떻게 느끼실지가 제일 궁금하고 중요한데, 이렇게 직접 말씀해 주시니까 너무 기뻐요. {store} 사장이 직접 인사드립니다. 언제든 편하게 놀러 오세요!",
                "어머 {customer}님! 이런 좋은 리뷰까지 남겨주시다니 정말 감동이에요. 저희가 정성껏 준비한 음식을 이렇게 인정해 주시니 보람을 느껴요. 앞으로도 변함없는 맛과 정성으로 맞이하겠습니다. 가족들과도 함께 오세요!",
                "{customer}님 정말 고마워요! 바쁜 일상 중에 시간 내서 이런 따뜻한 후기까지 써주시니 감사할 따름이에요. 이런 분들 때문에 매일 새벽부터 장보러 나가는 것도 힘이 나는 것 같아요. 건강하시고 자주 뵈어요!"
            ],
            "check_question": [
                "{customer}님 안녕하세요! 맛있게 드시고 {question}도 해주셔서 감사해요. 이런 관심 정말 고마워요! 다음에 오실 때 더 자세히 설명드릴 수 있도록 준비해놓을게요. 항상 더 나은 서비스를 위해 노력하고 있으니 언제든 편하게 말씀해주세요.",
                "어머 {customer}님! 좋은 리뷰에 {question}까지 해주시다니 정말 감사드려요. 손님들이 이렇게 세심하게 신경 써주시면 저희도 더 열심히 하게 돼요. 좋은 아이디어 주셔서 고맙습니다. 다음에 또 뵐 때까지 더 준비해서 만족시켜드릴게요!",
                "{customer}님 후기 정말 감사해요! {question}에 대해서도 신경 써주시고... 사실 이런 피드백이 저희한테는 정말 소중해요. 손님들 덕분에 항상 새로운 걸 배우고 개선할 수 있거든요. 다음에 방문하시면 더 좋은 모습 보여드릴게요!",
                "와 {customer}님! 맛있게 드시고 {question}도 챙겨주시다니 정말 고맙네요. 이런 세심한 관심 덕분에 저희도 계속 발전할 수 있어요. 앞으로도 더 좋은 서비스로 보답하도록 하겠습니다. 언제든 놀러오세요!",
                "{customer}님 정말 감사드려요! 리뷰도 써주시고 {question}까지... 이런 분들 때문에 장사하는 재미가 있어요. 손님들의 소중한 의견 하나하나가 저희에게는 큰 도움이 돼요. 다음에 또 좋은 소식으로 찾아뵐게요!"
            ],
            "normal_complaint": [
                "안녕하세요 {customer}님. 저희 가게에서 불편을 드려서 정말 죄송해요. {complaint} 부분 정말 미안합니다. 매번 완벽할 순 없지만 그래도 손님들이 기분 좋게 드실 수 있도록 더 신경쓸게요. 다음에 또 기회 주시면 더 나은 모습 보여드리겠습니다.",
                "{customer}님 죄송합니다. {complaint} 이야기 들으니 정말 죄송하네요. 사실 이런 피드백이 뼈 아프긴 하지만 정말 필요한 지적이라고 생각해요. 앞으로는 이런 일이 없도록 더 꼼꼼히 챙기겠습니다. 한 번 더 와주시면 실망시키지 않을게요.",
                "어휴 {customer}님... {complaint} 때문에 기분 나쁘셨을 텐데 정말 죄송해요. 요즘 정신이 없었다고 변명하기도 그렇고, 그냥 저희가 더 신경 못 써서 그런 것 같아요. 다음에는 꼭 만족스럽게 해드릴 테니 한 번만 더 기회 주세요.",
                "{customer}님 진짜 죄송합니다. {complaint} 부분은 저희가 놓친 거네요. 직원들한테도 다시 한 번 주의하라고 말하고, 앞으로는 더 세심하게 신경쓰겠습니다. 이런 일로 기분 상하셨을 텐데... 다음에 오시면 기분 좋게 드실 수 있도록 하겠어요.",
                "안녕하세요 {customer}님. {complaint} 문제로 불편하셨다니 정말 죄송해요. 솔직히 이런 리뷰 받으면 마음이 무거워지긴 하는데, 그래도 말씀해 주셔서 감사해요. 개선할 수 있는 기회니까요. 다음엔 분명히 더 좋은 서비스로 보답하겠습니다.",
                "{customer}님께서 {complaint} 때문에 실망하셨군요. 정말 죄송합니다. 완벽하지 않은 저희 때문에 기분 나쁘게 해드린 것 같아서 마음이 아파요. 앞으로는 이런 일이 없도록 더욱 주의깊게 준비하겠습니다. 용서해 주세요."
            ],
            "danger_serious": [
                "{customer}님 정말 죄송합니다. {serious_issue} 때문에 고생하셨다니... 말이 안 나오네요. 이런 심각한 일이 저희 가게에서 일어났다는 게 너무 충격이에요. 즉시 모든 걸 다시 점검하고 재발 방지를 위해 최선을 다하겠습니다. 정말 죄송하고 또 죄송합니다.",
                "어떻게 이런 일이... {customer}님께 {serious_issue} 일이 생겼다니 정말 죄송해요. 장사를 하면서 이런 일이 제일 두렵고 절대 있어서는 안 되는 건데... 당장 전체적으로 다시 점검하고 관리를 더욱 철저히 하겠습니다. 진심으로 사과드립니다.",
                "{customer}님... {serious_issue} 문제로 이렇게 큰 고생을 시켜드려서 정말 죄송합니다. 사장으로서 책임감을 느끼고 있어요. 이런 일이 다시는 일어나지 않도록 모든 시설과 관리 체계를 전면 재점검하겠습니다. 너무너무 죄송합니다.",
                "정말 죄송합니다 {customer}님. {serious_issue} 일로 이렇게 피해를 입히게 되다니... 장사하면서 이런 게 제일 무섭고 걱정되는 부분이었는데 정말 일어나고 말았네요. 모든 위생 관리를 다시 처음부터 점검하고 개선하겠습니다. 진심으로 사과드려요.",
                "{customer}님께서 {serious_issue}로 고생하셨다니 정말 마음이 무거워요. 이런 심각한 문제가 생긴 것에 대해 깊이 반성하고 있습니다. 위생 관리부터 모든 것을 다시 철저히 점검해서 이런 일이 절대 재발하지 않도록 하겠습니다. 정말 죄송합니다.",
                "안녕하세요 {customer}님... {serious_issue} 때문에 이렇게 큰 일을 당하셨다니 어떻게 사과를 드려야 할지 모르겠어요. 저희의 부주의로 인해 이런 일이 생긴 것 같아서 정말 죄송하고 책임감을 느껴요. 전면적으로 관리 시스템을 재정비하겠습니다. 진심으로 사과드립니다."
            ]
        }
        
        # 이모티콘 사용 (적절히)
        self.emoticons = {
            "positive": ["😊", "🙏", "💕", "👍", "😄"],
            "negative": ["🙏", "😢", "💦"],
            "neutral": ["😊", "🙏"]
        }

    def get_priority_level(self, review_text: str, rating: int, 
                          store_settings: Dict) -> Tuple[ReviewPriority, str]:
        """리뷰 우선순위 판단 - 단순화된 2단계"""
        
        review_lower = review_text.lower() if review_text else ""
        
        # REQUIRES_APPROVAL: 사장님 확인 필요 - 복잡하거나 중요한 리뷰
        approval_keywords = [
            # 법적/위생 문제
            "소비자보호원", "보건소", "고소", "신고", "경찰",
            "식중독", "배탈", "구토", "설사", "병원", "응급실",
            "벌레", "바퀴벌레", "머리카락", "이물질", "곰팡이", "상한",
            # 환불/클레임
            "환불", "돈돌려", "반품", "사기", "속임수", "거짓말", "환불거부",
            # 질문/문의
            "문의", "질문", "궁금", "언제", "어떻게", "추천", "메뉴",
            "전화", "연락", "답변", "설명",
            # 개선/차별 관련
            "차별", "무시", "인종차별", "성차별", "개선", "바꿔", "고쳐",
            # 극단적 불만
            "최악", "다시는", "절대", "두번다시", "비추천",
            # 복잡한 상황
            "하지만", "그런데", "근데", "빼고", "말고"
        ]
        
        for keyword in approval_keywords:
            if keyword in review_lower:
                return ReviewPriority.REQUIRES_APPROVAL, f"사장님 확인 필요: {keyword}"
        
        # rating 기반 분류 (1-2점은 승인 필요, 3점 이상은 자동)
        if rating is not None:
            if rating <= 2:
                return ReviewPriority.REQUIRES_APPROVAL, f"{rating}점 저평가 - 사장님 확인 필요"
            elif rating >= 3:
                return ReviewPriority.AUTO, f"{rating}점 평가 - 자동 답글 가능"
        
        # 네이버(rating=None) 또는 분류 불가한 경우
        # 긍정적 키워드가 있으면 AUTO, 없으면 승인 필요
        positive_keywords = ["맛있", "좋", "만족", "최고", "추천", "감사", "고마워"]
        for keyword in positive_keywords:
            if keyword in review_lower:
                return ReviewPriority.AUTO, "긍정적 텍스트 - 자동 답글 가능"
        
        # 기본값: 사장님 확인 필요 (안전한 선택)
        return ReviewPriority.REQUIRES_APPROVAL, "분류 불가 - 안전을 위해 사장님 확인"

    def generate_long_natural_reply(self, review_data: Dict, store_settings: Dict, 
                                   sentiment: str, priority: ReviewPriority, platform: str = None) -> str:
        """플랫폼별 특화 답글 생성 - 새로운 시스템"""
        
        # 플랫폼 정보가 없으면 store_settings에서 추출 시도
        if not platform:
            platform = store_settings.get('platform', 'naver')  # 기본값은 네이버
        
        try:
            # 플랫폼별 특화 답글 생성
            reply = self.platform_generator.generate_reply_by_platform(
                review_data, store_settings, platform
            )
            
            # 자연스러운 변형 추가
            reply = self._add_natural_variations(reply)
            
            # 길이 체크 및 조정 (150-400자)
            reply = self._adjust_reply_length(reply)
            
            return reply
            
        except Exception as e:
            print(f"[WARNING] Platform-specific reply generation failed: {e}")
            # 에러 시 기본 템플릿 시스템으로 fallback
            return self._fallback_template_reply(review_data, store_settings, sentiment, priority)
    
    def _adjust_reply_length(self, reply: str) -> str:
        """답글 길이 조정 (150-400자)"""
        if len(reply) < 150:
            # 너무 짧으면 추가 내용 (날씨 관련 멘트 제외)
            additions = [
                " 오늘도 좋은 하루 되세요!",
                " 항상 건강하시고 행복하세요!",
                " 다음에 뵐 때까지 건강하세요!",
                " 가족분들과도 함께 오시면 더욱 좋겠어요!",
                " 맛있는 음식 드시고 좋은 일만 가득하시길 바랍니다!",
                " 맛있는 거 많이 드시고 힘내세요!",
                " 언제나 응원하고 있어요!",
                " 또 뵙기를 기대하고 있을게요!",
                " 좋은 시간 보내셨길 바라요!"
            ]
            reply += random.choice(additions)
        elif len(reply) > 400:
            # 너무 길면 줄임
            reply = reply[:380] + "..."
        
        return reply
    
    def _fallback_template_reply(self, review_data: Dict, store_settings: Dict, 
                                sentiment: str, priority: ReviewPriority) -> str:
        """기존 템플릿 시스템 fallback (에러 시 사용)"""
        customer_name = review_data.get('reviewer_name', '고객')
        review_text = review_data.get('review_text', '')
        
        # 간단한 기본 답글 생성
        if sentiment == "positive":
            return f"{customer_name}님 안녕하세요! 좋은 리뷰 감사드려요! 앞으로도 더 나은 서비스로 보답하겠습니다. 건강하시고 또 뵈어요!"
        elif sentiment == "negative":
            return f"{customer_name}님 안녕하세요. 불편을 드려서 죄송합니다. 말씀해주신 부분 개선해서 더 만족드릴 수 있도록 하겠습니다. 감사합니다."
        else:
            return f"{customer_name}님 방문해주셔서 감사합니다! 소중한 리뷰 감사드려요. 앞으로도 좋은 서비스로 맞이하겠습니다. 건강하세요!"
    
    def _add_natural_variations(self, reply: str) -> str:
        """자연스러운 변형 추가 (30% 확률로 소소한 변화)"""
        
        if random.random() < 0.3:  # 30% 확률
            # 작은 변형들
            variations = [
                ("정말", random.choice(["진짜", "너무", "정말"])),
                ("감사합니다", random.choice(["감사해요", "고마워요", "감사드려요"])),
                ("안녕하세요", random.choice(["안녕하세요", "어서오세요", "반갑습니다"])),
                ("죄송합니다", random.choice(["죄송해요", "미안해요", "죄송합니다"])),
                ("다음에", random.choice(["다음에", "또", "언제든"])),
                ("노력하겠습니다", random.choice(["노력할게요", "신경쓸게요", "열심히 하겠어요"]))
            ]
            
            for original, replacement in variations:
                if original in reply and random.random() < 0.5:  # 50% 확률로 각 변형 적용
                    reply = reply.replace(original, replacement, 1)  # 첫 번째만 변경
        
        return reply

    def generate_natural_reply(self, review_data: Dict, store_settings: Dict, 
                              sentiment: str, priority: ReviewPriority) -> str:
        """자연스러운 한국식 답글 생성"""
        
        customer_name = review_data.get('reviewer_name', '고객')
        review_text = review_data.get('review_text', '')
        rating = review_data.get('rating', 3)
        tone = store_settings.get('reply_tone', 'friendly')
        
        # 답글 구성 요소
        parts = []
        
        # 1. 인사말 (선택적)
        if store_settings.get('greeting_template'):
            greeting = store_settings['greeting_template'].replace('{store_name}', 
                                                                  store_settings.get('store_name', '저희 가게'))
            greeting = greeting.replace('{customer_name}', customer_name)
            parts.append(greeting)
        else:
            # 자연스러운 인사
            if random.random() < 0.7:  # 70% 확률로 인사
                greetings = self.greetings.get(tone, self.greetings['friendly'])
                greeting = random.choice(greetings).format(customer=customer_name)
                parts.append(greeting)
        
        # 2. 감사/사과 표현 (핵심!)
        if sentiment == "positive":
            thanks = random.choice(self.thanks['positive'])
            parts.append(thanks)
        elif sentiment == "negative":
            # 부정 리뷰는 반드시 사과
            if priority == ReviewPriority.REQUIRES_APPROVAL:
                apology = random.choice(self.apologies['strong'])
            else:
                apology = random.choice(self.apologies['mild'])
            parts.append(apology)
            
            # 추가 감사 (피드백에 대한)
            if random.random() < 0.5:
                parts.append(random.choice(self.thanks['negative']))
        else:
            parts.append(random.choice(self.thanks['neutral']))
        
        # 3. 구체적 응답 (리뷰 내용에 대한)
        specific_response = self._generate_specific_response(review_text, sentiment, priority)
        if specific_response:
            parts.append(specific_response)
        
        # 4. 개선 약속 (부정 리뷰의 경우)
        if sentiment == "negative" and priority != ReviewPriority.AUTO:
            improvement = self._get_improvement_promise(review_text, priority)
            parts.append(improvement)
        
        # 5. 재방문 유도 (자연스럽게)
        if store_settings.get('closing_template'):
            closing = store_settings['closing_template'].replace('{store_name}', 
                                                                store_settings.get('store_name', '저희 가게'))
            parts.append(closing)
        else:
            # 우선순위에 따라 다른 톤
            if priority == ReviewPriority.AUTO:
                revisit = random.choice(self.revisit['positive'])
            elif priority == ReviewPriority.REQUIRES_APPROVAL:
                revisit = random.choice(self.revisit['negative'])
            else:
                revisit = random.choice(self.revisit['neutral'])
            
            if random.random() < 0.6:  # 60% 확률로 재방문 유도
                parts.append(revisit)
        
        # 6. 이모티콘 (적절히)
        if random.random() < 0.3:  # 30% 확률
            emoticons = self.emoticons.get(sentiment, self.emoticons['neutral'])
            parts.append(random.choice(emoticons))
        
        # 답글 조합
        reply = ' '.join(parts)
        
        # 자연스러움을 위한 변형
        reply = self._add_naturalness(reply, tone)
        
        # SEO 키워드 자연스럽게 삽입
        if store_settings.get('seo_keywords'):
            reply = self._insert_keywords_naturally(reply, store_settings['seo_keywords'])
        
        return reply

    def _generate_specific_response(self, review_text: str, sentiment: str, 
                                   priority: ReviewPriority) -> Optional[str]:
        """리뷰 내용에 대한 구체적 응답"""
        
        if not review_text:
            return None
        
        review_lower = review_text.lower()
        responses = []
        
        # 맛 관련
        if any(word in review_lower for word in ['맛있', '맛이', '맛도']):
            if sentiment == "positive":
                responses.append("맛있게 드셨다니 정말 기쁩니다")
            else:
                responses.append("맛이 기대에 못 미쳐드린 점 죄송합니다")
        
        # 서비스 관련
        if any(word in review_lower for word in ['직원', '서비스', '친절']):
            if sentiment == "positive":
                responses.append("직원들에게 전달하겠습니다")
            else:
                responses.append("서비스 교육을 더욱 강화하겠습니다")
        
        # 가격 관련
        if any(word in review_lower for word in ['가격', '비싸', '저렴']):
            if sentiment == "positive":
                responses.append("가성비를 인정해주셔서 감사합니다")
            else:
                responses.append("가격 대비 만족도를 높이도록 노력하겠습니다")
        
        # 위생 관련
        if any(word in review_lower for word in ['깨끗', '청결', '위생', '더럽']):
            if sentiment == "positive":
                responses.append("청결 유지에 더욱 신경쓰겠습니다")
            else:
                responses.append("위생 관리를 더욱 철저히 하겠습니다")
        
        # 대기시간 관련
        if any(word in review_lower for word in ['대기', '오래', '기다']):
            if sentiment == "negative":
                responses.append("대기 시간으로 불편을 드려 죄송합니다")
        
        return random.choice(responses) if responses else None

    def _get_improvement_promise(self, review_text: str, priority: ReviewPriority) -> str:
        """개선 약속 문구"""
        
        if priority == ReviewPriority.REQUIRES_APPROVAL:
            return random.choice(self.improvements['immediate'])
        
        # 구체적 개선 약속
        review_lower = review_text.lower() if review_text else ""
        
        if any(word in review_lower for word in ['맛', '음식']):
            return self.improvements['specific']['taste']
        elif any(word in review_lower for word in ['직원', '서비스', '친절']):
            return self.improvements['specific']['service']
        elif any(word in review_lower for word in ['위생', '청결', '더럽']):
            return self.improvements['specific']['cleanliness']
        elif any(word in review_lower for word in ['대기', '오래']):
            return self.improvements['specific']['waiting']
        elif any(word in review_lower for word in ['가격', '비싸']):
            return self.improvements['specific']['price']
        
        return random.choice(self.improvements['general'])

    def _add_naturalness(self, reply: str, tone: str) -> str:
        """자연스러움 추가"""
        
        # 중복 제거
        reply = re.sub(r'(\b\w+\b)(?:\s+\1)+', r'\1', reply)
        
        # 톤에 따른 어미 조정
        if tone == "casual":
            reply = reply.replace("습니다", "어요")
            reply = reply.replace("됩니다", "돼요")
        elif tone == "formal":
            reply = reply.replace("어요", "습니다")
            reply = reply.replace("돼요", "됩니다")
        
        # 자연스러운 연결
        reply = reply.replace("  ", " ")
        reply = reply.replace("..", ".")
        
        return reply.strip()

    def _insert_keywords_naturally(self, reply: str, keywords: List[str]) -> str:
        """SEO 키워드 자연스럽게 삽입"""
        
        if not keywords:
            return reply
        
        # 최대 2개까지만 자연스럽게 삽입
        keywords_to_insert = keywords[:2]
        
        for keyword in keywords_to_insert:
            # 이미 포함되어 있으면 스킵
            if keyword in reply:
                continue
            
            # 자연스러운 위치에 삽입
            if "저희" in reply and "저희 가게" not in reply:
                reply = reply.replace("저희", f"저희 {keyword}", 1)
                break
            elif "다음" in reply:
                reply = reply.replace("다음", f"다음에 {keyword}에", 1)
                break
        
        return reply

    def calculate_naturalness_score(self, reply: str) -> float:
        """답글 자연스러움 점수 (0~1)"""
        
        score = 1.0
        
        # 너무 짧거나 긴 답글
        length = len(reply)
        if length < 20:
            score -= 0.3
        elif length > 300:
            score -= 0.2
        
        # AI스러운 표현 체크
        ai_patterns = [
            "당신의 피드백", "귀하의 의견", "유감입니다", 
            "안타깝습니다", "저희는 항상", "최선을 다하겠습니다"
        ]
        for pattern in ai_patterns:
            if pattern in reply:
                score -= 0.1
        
        # 한국적 표현 사용 (가점)
        korean_patterns = [
            "죄송합니다", "감사합니다", "드려요", "주세요",
            "정말", "너무", "진짜"
        ]
        korean_count = sum(1 for pattern in korean_patterns if pattern in reply)
        score += min(korean_count * 0.05, 0.2)
        
        # 이모티콘 적절성
        emoticon_count = len(re.findall(r'[😊🙏💕👍😄😢💦]', reply))
        if emoticon_count == 1:
            score += 0.05
        elif emoticon_count > 2:
            score -= 0.1
        
        # 반복 표현
        words = reply.split()
        unique_ratio = len(set(words)) / len(words) if words else 0
        if unique_ratio < 0.7:
            score -= 0.15
        
        return max(0.0, min(1.0, score))