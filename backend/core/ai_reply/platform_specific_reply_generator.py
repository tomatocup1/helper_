#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
플랫폼별 특화 답글 생성 시스템
Platform-Specific Reply Generator System

각 플랫폼(네이버, 배민, 요기요, 쿠팡이츠)의 고유 데이터를 활용하여
맞춤형 답글을 생성하는 시스템
"""

import random
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta


class ReviewContentAnalyzer:
    """리뷰 내용 분석 엔진"""
    
    def __init__(self):
        # 메뉴 관련 키워드
        self.menu_keywords = {
            "chicken": ["치킨", "닭", "후라이드", "양념", "간장", "마늘", "허니", "크리스피"],
            "pizza": ["피자", "페페로니", "마르게리타", "하와이안", "콤비네이션"],
            "korean": ["김치찌개", "된장찌개", "불고기", "갈비", "삼겹살", "냉면", "비빔밥"],
            "chinese": ["짜장면", "짬뽕", "탕수육", "마파두부", "깐풍기", "양장피"],
            "western": ["파스타", "스테이크", "리조또", "샐러드", "햄버거", "샌드위치"],
            "japanese": ["초밥", "라멘", "돈카츠", "우동", "규동", "카레"],
            "dessert": ["케이크", "아이스크림", "마카롱", "쿠키", "타르트", "푸딩"],
            "drink": ["커피", "라떼", "아메리카노", "차", "음료", "주스", "맥주", "소주"]
        }
        
        # 긍정적 평가 키워드
        self.positive_keywords = {
            "taste": ["맛있", "맛있어", "맛나", "맛있네", "맛좋", "존맛", "JMT", "꿀맛"],
            "service": ["친절", "빨리", "빠른", "신속", "정성", "세심", "깔끔"],
            "atmosphere": ["분위기", "좋은", "깨끗", "넓은", "편안", "아늑"],
            "portion": ["양많", "푸짐", "든든", "배불러", "양도많고", "가격대비"],
            "freshness": ["신선", "새로운", "따뜻", "갓", "금방", "뜨거운"]
        }
        
        # 부정적 평가 키워드
        self.negative_keywords = {
            "taste": ["맛없", "짜", "단", "싱거", "별로", "이상한맛", "맛이없"],
            "service": ["불친절", "늦", "느린", "오래", "무례", "불편"],
            "cleanliness": ["더럽", "지저분", "냄새", "벌레", "이물질", "곰팡이"],
            "portion": ["양적", "작", "부족", "비싸", "가성비"],
            "temperature": ["차갑", "식", "미지근", "뜨겁지않"]
        }
        
        # 상황 컨텍스트
        self.situation_keywords = {
            "date": ["데이트", "연인", "남친", "여친", "애인", "커플"],
            "family": ["가족", "부모", "아이", "아기", "식구", "온가족"],
            "friends": ["친구", "동료", "회식", "모임", "파티", "술"],
            "alone": ["혼자", "1인", "혼밥", "야식", "간단"],
            "business": ["회의", "미팅", "접대", "손님", "비즈니스"],
            "celebration": ["생일", "기념일", "축하", "파티", "이벤트"]
        }
    
    def extract_mentioned_menus(self, review_text: str, order_menu: str = None) -> List[str]:
        """리뷰에서 언급된 메뉴 추출"""
        mentioned = []
        text_lower = review_text.lower()
        
        # 주문 메뉴에서 추출 (우선순위)
        if order_menu:
            for category, items in self.menu_keywords.items():
                for item in items:
                    if item in order_menu.lower():
                        mentioned.append(item)
        
        # 리뷰 텍스트에서 추출
        for category, items in self.menu_keywords.items():
            for item in items:
                if item in text_lower:
                    mentioned.append(item)
        
        # 중복 제거 및 길이순 정렬 (긴 것부터)
        mentioned = list(set(mentioned))
        mentioned.sort(key=len, reverse=True)
        
        return mentioned[:3]  # 최대 3개까지
    
    def extract_positive_aspects(self, review_text: str) -> List[Tuple[str, str]]:
        """긍정적 평가 요소 추출 (카테고리, 키워드)"""
        aspects = []
        text_lower = review_text.lower()
        
        for category, keywords in self.positive_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    aspects.append((category, keyword))
        
        return aspects[:3]  # 최대 3개까지
    
    def extract_negative_aspects(self, review_text: str) -> List[Tuple[str, str]]:
        """부정적 평가 요소 추출 (카테고리, 키워드)"""
        aspects = []
        text_lower = review_text.lower()
        
        for category, keywords in self.negative_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    aspects.append((category, keyword))
        
        return aspects[:3]  # 최대 3개까지
    
    def detect_situation_context(self, review_text: str) -> Optional[str]:
        """상황 컨텍스트 감지"""
        text_lower = review_text.lower()
        
        for situation, keywords in self.situation_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return situation
        
        return None


class PlatformSpecificReplyGenerator:
    """플랫폼별 특화 답글 생성기"""
    
    def __init__(self):
        self.analyzer = ReviewContentAnalyzer()
        
        # 플랫폼별 인사말 패턴
        self.greeting_patterns = {
            "formal": [
                "안녕하세요 {customer}님!",
                "{customer}님 안녕하세요!",
                "반갑습니다 {customer}님!",
                "{customer}님께 인사드려요!"
            ],
            "friendly": [
                "안녕하세요 {customer}님~",
                "{customer}님 안녕하세요~",
                "어서오세요 {customer}님!",
                "{customer}님 반갑네요!"
            ],
            "casual": [
                "{customer}님 안녕하세요!",
                "와 {customer}님!",
                "{customer}님 감사해요!",
                "어머 {customer}님!"
            ]
        }
        
        # 감사 표현 패턴
        self.thanks_patterns = {
            "regular": [
                "좋은 리뷰 감사해요",
                "따뜻한 후기 감사합니다",
                "소중한 리뷰 감사드려요",
                "이런 후기 정말 감사해요",
                "리뷰 남겨주셔서 감사해요"
            ],
            "loyal": [
                "늘 감사해요",
                "항상 고마워요",
                "계속 찾아주셔서 감사해요",
                "단골이 되어주셔서 고마워요",
                "꾸준히 사랑해주셔서 감사해요"
            ],
            "photo": [
                "사진까지 올려주셔서 감사해요",
                "예쁜 사진 감사합니다",
                "사진 리뷰 너무 감사해요",
                "사진으로 보니 더 기뻐요",
                "인증샷까지 감사드려요"
            ]
        }
        
        # 마무리 인사 패턴 (날씨 관련 멘트 제외)
        self.closing_patterns = [
            "오늘도 좋은 하루 되세요!",
            "건강하시고 또 뵈어요!",
            "항상 건강하세요!",
            "다음에 또 놀러오세요!",
            "언제든 편하게 오세요!",
            "가족분들과도 함께 오세요!",
            "맛있는 거 많이 드시고 행복하세요!",
            "좋은 일만 가득하시길 바라요!",
            "늘 응원하고 있어요!",
            "즐거운 시간 되세요!",
            "또 뵙기를 기대할게요!",
            "언제나 최선을 다하겠습니다!"
        ]
    
    def get_operation_aware_closing(self, operation_type: str, rating: int = 5) -> str:
        """매장 운영 방식에 맞는 마무리 메시지 생성"""
        
        if operation_type == 'delivery_only':
            # 배달전용 매장 - 방문 관련 표현 금지
            if rating >= 4:
                return random.choice([
                    "다음에도 맛있는 음식으로 찾아뵐게요!",
                    "또 주문해주세요!",
                    "다음 주문도 기다리고 있을게요!",
                    "언제든 주문해주세요!",
                    "맛있는 음식으로 또 찾아뵐게요!",
                    "다음에도 빠른 배달로 만나요!"
                ])
            else:
                return random.choice([
                    "더 나은 서비스로 찾아뵐게요.",
                    "다음엔 꼭 만족시켜드릴게요.",
                    "더 맛있는 음식으로 보답하겠습니다."
                ])
        
        elif operation_type == 'dine_in_only':
            # 홀전용 매장 - 배달 관련 표현 금지
            if rating >= 4:
                return random.choice([
                    "다음에도 매장에서 뵙겠습니다!",
                    "또 방문해주세요!",
                    "매장에서 기다리고 있을게요!",
                    "언제든 편하게 방문해주세요!",
                    "다음 방문도 기대할게요!",
                    "또 오셔서 맛있게 드세요!"
                ])
            else:
                return random.choice([
                    "다음 방문엔 더 나은 서비스로 모시겠습니다.",
                    "매장에서 더 좋은 모습으로 뵙겠습니다.",
                    "다음엔 꼭 만족시켜드리겠습니다."
                ])
        
        elif operation_type == 'takeout_only':
            # 포장전용 매장
            if rating >= 4:
                return random.choice([
                    "다음 포장도 기다릴게요!",
                    "또 포장하러 오세요!",
                    "언제든 포장 주문해주세요!",
                    "맛있게 가져가세요!",
                    "다음에도 포장으로 만나요!"
                ])
            else:
                return random.choice([
                    "다음 포장은 더 신경쓰겠습니다.",
                    "더 나은 포장 서비스로 보답하겠습니다."
                ])
        
        else:  # 'both' or default
            # 배달+홀 또는 기본값
            if rating >= 4:
                return random.choice([
                    "다음에도 맛있는 음식으로 만나요!",
                    "또 이용해주세요!",
                    "언제든 편하게 이용해주세요!",
                    "다음에도 좋은 서비스로 보답할게요!",
                    "또 찾아주세요!"
                ])
            else:
                return random.choice([
                    "더 나은 서비스로 보답하겠습니다.",
                    "다음엔 꼭 만족시켜드리겠습니다."
                ])
    
    def generate_coupang_reply(self, review_data: Dict, store_settings: Dict) -> str:
        """쿠팡이츠 특화 답글 생성"""
        customer = review_data.get('reviewer_name', '고객')
        review_text = review_data.get('review_text', '')
        rating = review_data.get('rating', 5)
        order_count = review_data.get('order_count', '')  # "3회 주문"
        order_menu_items = review_data.get('order_menu_items', [])
        order_date = review_data.get('order_date')
        review_date = review_data.get('review_date')
        
        # 리뷰 분석
        mentioned_menus = self.analyzer.extract_mentioned_menus(review_text, str(order_menu_items))
        positive_aspects = self.analyzer.extract_positive_aspects(review_text)
        negative_aspects = self.analyzer.extract_negative_aspects(review_text)
        situation = self.analyzer.detect_situation_context(review_text)
        
        # 단골 고객 여부 판단
        is_loyal = any(char.isdigit() and int(char) >= 3 for char in order_count) if order_count else False
        
        parts = []
        
        # 1. 인사말
        if is_loyal:
            parts.append(f"{customer}님 늘 감사해요!")
        else:
            greeting_style = "friendly" if rating >= 4 else "formal"
            greeting = random.choice(self.greeting_patterns[greeting_style]).format(customer=customer)
            parts.append(greeting)
        
        # 2. 단골 고객 특별 언급
        if is_loyal and order_count:
            parts.append(f"{order_count}해주신 단골고객님이시네요.")
        
        # 3. 메뉴별 맞춤 응답
        if mentioned_menus and rating >= 4:
            menu = mentioned_menus[0]
            responses = [
                f"{menu} 맛있게 드셨다니 기뻐요!",
                f"{menu} 만족해주셔서 감사해요!",
                f"{menu} 좋게 봐주셔서 고마워요!",
                f"{menu} 맛있다고 해주시니 뿌듯해요!"
            ]
            parts.append(random.choice(responses))
        
        # 4. 긍정적 평가에 대한 응답
        if positive_aspects and rating >= 4:
            aspect_category, aspect_word = positive_aspects[0]
            if aspect_category == "taste":
                responses = [
                    f"{aspect_word}다고 해주시니 정말 기뻐요!",
                    f"{aspect_word}게 드셨다니 보람을 느껴요!",
                    f"맛에 만족해주셔서 감사해요!"
                ]
            elif aspect_category == "service":
                responses = [
                    f"{aspect_word}하다고 해주셔서 힘이 나요!",
                    f"서비스도 좋게 봐주셔서 감사해요!",
                    f"{aspect_word}게 해드릴 수 있어서 다행이에요!"
                ]
            else:
                responses = [
                    f"{aspect_word}다고 해주셔서 고마워요!",
                    f"좋게 평가해주셔서 감사해요!"
                ]
            parts.append(random.choice(responses))
        
        # 5. 부정적 피드백에 대한 응답
        elif negative_aspects:
            aspect_category, aspect_word = negative_aspects[0]
            apologies = [
                f"{aspect_word}다고 하시니 정말 죄송해요.",
                f"기대에 못 미쳐서 죄송합니다.",
                f"불편을 드려서 죄송해요.",
                f"만족스럽지 못해서 죄송합니다."
            ]
            parts.append(random.choice(apologies))
            parts.append("더 나은 서비스를 위해 개선하겠습니다.")
        
        # 6. 상황별 추가 멘트
        if situation == "family":
            parts.append("가족분들과 좋은 시간 보내셨길 바라요!")
        elif situation == "date":
            parts.append("연인분과 즐거운 시간 되셨기를 바라요!")
        elif situation == "friends":
            parts.append("친구분들과 즐겁게 드셨길 바라요!")
        
        # 7. 주문-리뷰 시간차 언급 (자연스럽게)
        if order_date and review_date:
            try:
                order_dt = datetime.strptime(str(order_date), '%Y-%m-%d')
                review_dt = datetime.strptime(str(review_date), '%Y-%m-%d')
                diff_days = (review_dt - order_dt).days
                
                if diff_days <= 1:
                    parts.append("빠른 리뷰까지 감사드려요!")
            except:
                pass
        
        # 8. 마무리 (운영 방식 고려)
        operation_type = store_settings.get('operation_type', 'both')
        if rating >= 4:
            parts.append(self.get_operation_aware_closing(operation_type, rating))
        
        parts.append(random.choice(self.closing_patterns))
        
        return " ".join(parts)
    
    def generate_baemin_reply(self, review_data: Dict, store_settings: Dict) -> str:
        """배민 특화 답글 생성"""
        customer = review_data.get('reviewer_name', '고객')
        review_text = review_data.get('review_text', '')
        rating = review_data.get('rating', 5)
        order_menu_items = review_data.get('order_menu_items', [])
        baemin_metadata = review_data.get('baemin_metadata', {})
        
        # 리뷰 분석
        mentioned_menus = self.analyzer.extract_mentioned_menus(review_text, str(order_menu_items))
        positive_aspects = self.analyzer.extract_positive_aspects(review_text)
        negative_aspects = self.analyzer.extract_negative_aspects(review_text)
        
        parts = []
        
        # 1. 인사말
        greeting_style = "friendly" if rating >= 4 else "formal"
        greeting = random.choice(self.greeting_patterns[greeting_style]).format(customer=customer)
        parts.append(greeting)
        
        # 2. 배달 서비스 관련 언급
        if "배달" in review_text.lower() or any("빠르" in review_text.lower() for _ in [1]):
            delivery_responses = [
                "배달 서비스도 만족해주셔서 감사해요!",
                "빠른 배달로 따뜻하게 드실 수 있어서 다행이에요!",
                "배달까지 좋게 봐주셔서 고마워요!",
                "신속한 배달로 맛있게 드실 수 있어서 기뻐요!"
            ]
            parts.append(random.choice(delivery_responses))
        
        # 3. 메뉴별 맞춤 응답
        if mentioned_menus and rating >= 4:
            menu = mentioned_menus[0]
            menu_responses = [
                f"{menu} 맛에 만족해주셔서 기뻐요!",
                f"저희 {menu} 좋아해주셔서 감사해요!",
                f"{menu} 맛있게 드셨다니 보람을 느껴요!",
                f"{menu} 추천하신 거 같아서 고마워요!"
            ]
            parts.append(random.choice(menu_responses))
        
        # 4. 긍정/부정 피드백 응답
        if positive_aspects and rating >= 4:
            parts.append("좋은 평가 해주셔서 정말 감사합니다!")
            parts.append("앞으로도 더욱 맛있는 음식으로 보답하겠어요!")
        elif negative_aspects:
            parts.append("불편을 드려서 죄송합니다.")
            parts.append("더 나은 서비스를 위해 노력하겠습니다.")
        
        # 5. 재주문 유도 (운영 방식 고려)
        operation_type = store_settings.get('operation_type', 'both')
        if rating >= 4:
            parts.append(self.get_operation_aware_closing(operation_type, rating))
        
        parts.append(random.choice(self.closing_patterns))
        
        return " ".join(parts)
    
    def generate_yogiyo_reply(self, review_data: Dict, store_settings: Dict) -> str:
        """요기요 특화 답글 생성 (가장 풍부한 데이터 활용)"""
        customer = review_data.get('reviewer_name', '고객')
        review_text = review_data.get('review_text', '')
        overall_rating = review_data.get('overall_rating', 5.0)
        taste_rating = review_data.get('taste_rating')
        quantity_rating = review_data.get('quantity_rating')
        order_menu = review_data.get('order_menu', '')
        
        # 리뷰 분석
        mentioned_menus = self.analyzer.extract_mentioned_menus(review_text, order_menu)
        positive_aspects = self.analyzer.extract_positive_aspects(review_text)
        negative_aspects = self.analyzer.extract_negative_aspects(review_text)
        situation = self.analyzer.detect_situation_context(review_text)
        
        parts = []
        
        # 1. 인사말
        greeting_style = "casual" if overall_rating >= 4.5 else "friendly"
        greeting = random.choice(self.greeting_patterns[greeting_style]).format(customer=customer)
        parts.append(greeting)
        
        # 2. 세분화된 별점 언급 (요기요만의 특징!)
        rating_mentions = []
        if taste_rating and taste_rating >= 4:
            rating_mentions.append(f"맛 {taste_rating}점")
        if quantity_rating and quantity_rating >= 4:
            rating_mentions.append(f"양 {quantity_rating}점")
        
        if rating_mentions:
            if len(rating_mentions) == 2:
                parts.append(f"{', '.join(rating_mentions)} 모두 주셔서 감사해요!")
            else:
                parts.append(f"{rating_mentions[0]} 주셔서 감사해요!")
        elif overall_rating == 5.0:
            parts.append("5.0점 만점 평가 감사드려요!")
        
        # 3. 상세한 주문 메뉴 옵션 언급
        if order_menu and len(order_menu) > 50:  # 상세한 옵션이 있는 경우
            menu_parts = []
            if "맵기" in order_menu:
                menu_parts.append("맵기 조절")
            if "사이즈" in order_menu:
                menu_parts.append("사이즈 선택")
            if "추가" in order_menu or "옵션" in order_menu:
                menu_parts.append("옵션 선택")
            
            if menu_parts:
                parts.append(f"{', '.join(menu_parts)}까지 세심하게 신경써주셔서 감사해요!")
        
        # 4. 메뉴별 맞춤 응답
        if mentioned_menus and overall_rating >= 4:
            menu = mentioned_menus[0]
            if "곱창" in menu:
                parts.append("저희 곱창 단골이 되어주셔서 고마워요!")
            else:
                responses = [
                    f"{menu} 맛있게 드셨다니 기뻐요!",
                    f"저희 {menu} 사랑해주셔서 감사해요!",
                    f"{menu} 만족해주셔서 뿌듯해요!"
                ]
                parts.append(random.choice(responses))
        
        # 5. 긍정적 평가 구체적 응답
        if positive_aspects and overall_rating >= 4:
            aspect_category, aspect_word = positive_aspects[0]
            
            if aspect_category == "taste":
                parts.append(f"맛에 대한 칭찬 정말 감사해요!")
            elif aspect_category == "service":
                if "빨리" in aspect_word or "빠른" in aspect_word:
                    parts.append("빠른 배달 칭찬해주셔서 고마워요!")
                else:
                    parts.append("서비스도 좋게 봐주셔서 감사해요!")
            elif aspect_category == "portion":
                if quantity_rating and quantity_rating >= 4:
                    parts.append("양도 만족스러우셨군요!")
                else:
                    parts.append("푸짐하다고 해주셔서 기뻐요!")
        
        # 6. 상황별 추가 멘트
        if situation == "alone":
            parts.append("혼밥도 맛있게 드셨길 바라요!")
        elif situation == "friends":
            parts.append("친구분들과 즐거운 시간 되셨나요?")
        
        # 7. 부정적 피드백 응답
        if negative_aspects:
            parts.append("아쉬운 부분이 있으셨다니 죄송해요.")
            parts.append("더 맛있게 준비해서 만족드릴게요!")
        
        # 8. 마무리 (운영 방식 고려)
        operation_type = store_settings.get('operation_type', 'both')
        if overall_rating >= 4:
            parts.append(self.get_operation_aware_closing(operation_type, overall_rating))
        
        parts.append(random.choice(self.closing_patterns))
        
        return " ".join(parts)
    
    def generate_naver_reply(self, review_data: Dict, store_settings: Dict) -> str:
        """네이버 특화 답글 생성"""
        customer = review_data.get('reviewer_name', '고객')
        review_text = review_data.get('review_text', '')
        visit_count = review_data.get('visit_count')  # "14번째 방문"
        recommended_keywords = review_data.get('recommended_keywords', [])
        has_photos = review_data.get('has_photos', False)
        visit_date = review_data.get('visit_date')
        review_date = review_data.get('review_date')
        
        # 리뷰 분석
        mentioned_menus = self.analyzer.extract_mentioned_menus(review_text)
        positive_aspects = self.analyzer.extract_positive_aspects(review_text)
        negative_aspects = self.analyzer.extract_negative_aspects(review_text)
        situation = self.analyzer.detect_situation_context(review_text)
        
        # 단골 여부 판단
        is_loyal = False
        visit_num = 0
        if visit_count and any(char.isdigit() for char in str(visit_count)):
            numbers = re.findall(r'\d+', str(visit_count))
            if numbers:
                visit_num = int(numbers[0])
                is_loyal = visit_num >= 3
        
        parts = []
        
        # 1. 인사말 (단골 고객 특별 인사)
        if is_loyal and visit_num >= 10:
            parts.append(f"{customer}님! {visit_num}번째 방문해주신 단골님이시네요!")
        elif is_loyal:
            parts.append(f"{customer}님! 단골고객으로 찾아주셔서 늘 감사해요!")
        else:
            greeting = random.choice(self.greeting_patterns["friendly"]).format(customer=customer)
            parts.append(greeting)
        
        # 2. 사진 리뷰 감사 인사
        if has_photos:
            photo_thanks = random.choice(self.thanks_patterns["photo"])
            parts.append(photo_thanks)
        
        # 3. 추천 키워드 활용
        if recommended_keywords:
            keyword_responses = {
                "음식이 맛있어요": "맛있다고 평가해주셔서 감사해요!",
                "고기 질이 좋아요": "고기 품질까지 인정해주시니 뿌듯해요!",
                "특별한 메뉴가 있어요": "저희만의 특별한 메뉴 좋아해주셔서 고마워요!",
                "친절해요": "친절하다고 해주시니 직원들도 기뻐할 거예요!",
                "단체모임 하기 좋아요": "단체 모임 장소로 선택해주셔서 영광이에요!",
                "분위기가 좋아요": "분위기까지 좋게 봐주셔서 감사해요!",
                "가격이 합리적이에요": "가성비도 만족해주셔서 다행이에요!"
            }
            
            for keyword in recommended_keywords[:2]:  # 최대 2개까지
                if keyword in keyword_responses:
                    parts.append(keyword_responses[keyword])
                    break
        
        # 4. 메뉴별 맞춤 응답
        if mentioned_menus:
            menu = mentioned_menus[0]
            menu_responses = [
                f"저희 {menu} 좋아해주셔서 감사해요!",
                f"{menu} 맛에 만족하셨다니 기뻐요!",
                f"{menu}은/는 저희 자신 있는 메뉴거든요!",
                f"{menu} 드시고 좋은 평가 해주셔서 고마워요!"
            ]
            parts.append(random.choice(menu_responses))
        
        # 5. 긍정적 평가 응답
        if positive_aspects:
            aspect_category, aspect_word = positive_aspects[0]
            if aspect_category == "taste":
                parts.append("맛에 대한 칭찬이 가장 기뻐요!")
            elif aspect_category == "service":
                parts.append("서비스도 좋게 봐주셔서 감사합니다!")
            elif aspect_category == "atmosphere":
                parts.append("분위기까지 마음에 드셨다니 다행이에요!")
        
        # 6. 부정적 피드백 응답
        if negative_aspects:
            parts.append("아쉬운 점이 있으셨다니 죄송해요.")
            parts.append("말씀해주신 부분 개선해서 더 만족드릴게요!")
        
        # 7. 단골 고객 특별 멘트
        if is_loyal:
            loyal_messages = [
                "늘 찾아주셔서 정말 감사해요!",
                "단골님 덕분에 힘이 나요!",
                "항상 감사한 마음이에요!",
                "꾸준히 사랑해주셔서 고마워요!"
            ]
            parts.append(random.choice(loyal_messages))
        
        # 8. 상황별 추가 멘트
        if situation == "date":
            parts.append("연인분과 좋은 추억 만드셨길 바라요!")
        elif situation == "family":
            parts.append("가족분들과 즐거운 시간 되셨나요?")
        elif situation == "friends":
            parts.append("친구분들과 좋은 시간 보내셨길 바라요!")
        
        # 9. 마무리 (운영 방식 고려)
        operation_type = store_settings.get('operation_type', 'both')
        rating = review_data.get('rating', 5)  # 네이버는 rating 없을 수 있음
        
        if is_loyal:
            parts.append("앞으로도 변함없는 맛으로 보답하겠습니다!")
        else:
            parts.append(self.get_operation_aware_closing(operation_type, rating))
        
        parts.append(random.choice(self.closing_patterns))
        
        return " ".join(parts)
    
    def generate_reply_by_platform(self, review_data: Dict, store_settings: Dict, platform: str) -> str:
        """플랫폼에 따른 답글 생성 라우팅"""
        
        # 기본 데이터 검증
        if not review_data.get('review_text') and not review_data.get('rating'):
            # 리뷰 텍스트도 별점도 없는 경우 기본 답글
            customer = review_data.get('reviewer_name', '고객')
            operation_type = store_settings.get('operation_type', 'both')
            
            # 운영 방식에 맞는 기본 답글
            if operation_type == 'delivery_only':
                return f"{customer}님 주문해주셔서 감사합니다! 다음에도 맛있는 음식으로 찾아뵐게요. 건강하시고 또 주문해주세요!"
            elif operation_type == 'dine_in_only':
                return f"{customer}님 방문해주셔서 감사합니다! 다음에도 매장에서 뵙겠습니다. 건강하시고 또 놀러오세요!"
            elif operation_type == 'takeout_only':
                return f"{customer}님 포장 주문해주셔서 감사합니다! 다음에도 맛있게 가져가세요. 건강하세요!"
            else:
                return f"{customer}님 이용해주셔서 감사합니다! 다음에도 좋은 서비스로 보답하겠습니다. 건강하시고 또 뵈어요!"
        
        try:
            # platform이 None인 경우 처리
            if not platform:
                print("[WARNING] Platform is None, using generic reply")
                return self._generate_generic_reply(review_data, store_settings)
                
            platform_lower = platform.lower() if isinstance(platform, str) else str(platform).lower()
            
            if platform_lower == 'coupangeats':
                return self.generate_coupang_reply(review_data, store_settings)
            elif platform_lower == 'baemin':
                return self.generate_baemin_reply(review_data, store_settings)
            elif platform_lower == 'yogiyo':
                return self.generate_yogiyo_reply(review_data, store_settings)
            elif platform_lower == 'naver':
                return self.generate_naver_reply(review_data, store_settings)
            else:
                # 알 수 없는 플랫폼의 경우 기본 답글
                return self._generate_generic_reply(review_data, store_settings)
                
        except Exception as e:
            print(f"[WARNING] Platform-specific reply generation failed: {e}")
            # 에러 발생 시 기본 답글로 fallback
            return self._generate_generic_reply(review_data, store_settings)
    
    def _generate_generic_reply(self, review_data: Dict, store_settings: Dict) -> str:
        """기본 답글 생성 (플랫폼 특화 실패 시 fallback)"""
        customer = review_data.get('reviewer_name', '고객')
        review_text = review_data.get('review_text', '')
        rating = review_data.get('rating', 5)
        operation_type = store_settings.get('operation_type', 'both')
        
        parts = []
        
        # 인사말
        parts.append(f"{customer}님 안녕하세요!")
        
        # 리뷰 감사
        parts.append("소중한 리뷰 감사드려요!")
        
        # 별점/내용에 따른 응답
        if rating and rating >= 4:
            parts.append("좋은 평가 해주셔서 정말 기뻐요!")
            parts.append(self.get_operation_aware_closing(operation_type, rating))
        elif rating and rating <= 2:
            parts.append("기대에 못 미쳐서 죄송해요.")
            parts.append("더 나은 서비스를 위해 개선하겠습니다.")
        else:
            parts.append(self.get_operation_aware_closing(operation_type, rating))
        
        parts.append(random.choice(self.closing_patterns))
        
        return " ".join(parts)