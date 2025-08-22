#!/usr/bin/env python3
"""
요기요 DSID (DOM Stable ID) 생성기
리뷰 ID가 없는 요기요에서 각 리뷰를 유일하게 식별하기 위한 해시 기반 ID 생성 시스템
"""

import hashlib
import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class YogiyoDSIDGenerator:
    """요기요 리뷰용 DSID 생성 및 매칭 엔진"""
    
    def __init__(self):
        self.page_salt = None
        self.content_hashes = []
        self.rolling_hashes = []
        self.dsids = []
        
    def normalize_content(self, html: str) -> str:
        """
        HTML 콘텐츠 정규화
        - 불안정한 속성 제거 (style, aria-*, srcset, 추적 쿼리)
        - 숫자 포맷 통일
        - 공백/이모지/개행 축소
        """
        if not html:
            return ""
            
        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(html, 'html.parser')
        
        # 불안정한 속성 제거
        for tag in soup.find_all(True):
            # 제거할 속성들
            attrs_to_remove = []
            for attr in tag.attrs:
                if (attr.startswith('aria-') or 
                    attr.startswith('data-') or
                    attr in ['style', 'srcset', 'id', 'class']):
                    attrs_to_remove.append(attr)
            
            for attr in attrs_to_remove:
                del tag.attrs[attr]
        
        # 텍스트 추출 및 정규화
        text = soup.get_text(separator=' ', strip=True)
        
        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 숫자 포맷 통일 (예: 1,234 -> 1234)
        text = re.sub(r'(\d+),(\d+)', r'\1\2', text)
        
        # 이모지 제거 (선택적)
        text = re.sub(r'[^\w\s가-힣.,!?]', '', text)
        
        return text.strip()
    
    def convert_relative_time(self, time_str: str) -> str:
        """
        상대 시간을 절대 시간으로 변환
        예: "14시간 전" -> "2025-08-21"
        """
        if not time_str:
            return ""
            
        # 이미 날짜 형식인 경우
        if re.match(r'\d{4}\.\d{2}\.\d{2}', time_str):
            return time_str
            
        now = datetime.now()
        
        # 패턴 매칭
        patterns = {
            r'(\d+)시간 전': lambda m: now - timedelta(hours=int(m.group(1))),
            r'(\d+)분 전': lambda m: now - timedelta(minutes=int(m.group(1))),
            r'(\d+)일 전': lambda m: now - timedelta(days=int(m.group(1))),
            r'어제': lambda m: now - timedelta(days=1),
            r'오늘': lambda m: now,
        }
        
        for pattern, converter in patterns.items():
            match = re.match(pattern, time_str)
            if match:
                result_date = converter(match)
                return result_date.strftime('%Y.%m.%d')
        
        return time_str
    
    def calculate_content_hash(self, review_element: Dict) -> str:
        """
        리뷰 요소의 콘텐츠 해시 계산 C[i]
        """
        # 주요 필드 추출 및 정규화
        normalized_parts = []
        
        # 리뷰어 이름
        if review_element.get('reviewer_name'):
            normalized_parts.append(self.normalize_content(review_element['reviewer_name']))
        
        # 날짜 (상대시간 변환)
        if review_element.get('review_date'):
            date_str = self.convert_relative_time(review_element['review_date'])
            normalized_parts.append(date_str)
        
        # 리뷰 텍스트
        if review_element.get('review_text'):
            normalized_parts.append(self.normalize_content(review_element['review_text']))
        
        # 주문 메뉴
        if review_element.get('order_menu'):
            normalized_parts.append(self.normalize_content(review_element['order_menu']))
        
        # 별점
        if review_element.get('rating'):
            normalized_parts.append(str(review_element['rating']))
        
        # 맛/양 별점
        if review_element.get('taste_rating'):
            normalized_parts.append(f"taste:{review_element['taste_rating']}")
        if review_element.get('quantity_rating'):
            normalized_parts.append(f"quantity:{review_element['quantity_rating']}")
        
        # 이미지 URL (있는 경우)
        if review_element.get('image_urls'):
            for url in review_element['image_urls']:
                # URL에서 쿼리 파라미터 제거
                clean_url = url.split('?')[0]
                normalized_parts.append(clean_url)
        
        # 모든 부분을 결합하여 해시 생성
        content = '|'.join(normalized_parts)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def calculate_rolling_hash(self, content_hash: str, prev_rolling_hash: Optional[str] = None) -> str:
        """
        롤링 해시 계산 R[i]
        R[0] = SHA256(C[0] || PAGE_SALT)
        R[i] = SHA256(C[i] || R[i-1])
        """
        if prev_rolling_hash is None:
            # 첫 번째 요소
            combined = f"{content_hash}|{self.page_salt or 'default_salt'}"
        else:
            # 이후 요소들
            combined = f"{content_hash}|{prev_rolling_hash}"
        
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def calculate_dsid(self, index: int, content_hashes: List[str], 
                       rolling_hashes: List[str]) -> str:
        """
        최종 DSID 계산
        DSID[i] = SHA256(C[i] || R[i-1] || C[i+1] || PAGE_SALT)
        """
        parts = []
        
        # 현재 콘텐츠 해시
        parts.append(content_hashes[index])
        
        # 이전 롤링 해시 (있는 경우)
        if index > 0:
            parts.append(rolling_hashes[index - 1])
        else:
            parts.append("START")
        
        # 다음 콘텐츠 해시 (있는 경우)
        if index < len(content_hashes) - 1:
            parts.append(content_hashes[index + 1])
        else:
            parts.append("END")
        
        # 페이지 솔트
        parts.append(self.page_salt or 'default_salt')
        
        combined = '|'.join(parts)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]  # 16자리로 축약
    
    def calculate_neighbor_window_hash(self, index: int, content_hashes: List[str]) -> str:
        """
        5-이웃 윈도우 해시 계산 (더 강한 유일성)
        DSID2 = SHA256(C[i-2] || C[i-1] || C[i] || C[i+1] || C[i+2] || PAGE_SALT)
        """
        window = []
        
        # i-2
        if index >= 2:
            window.append(content_hashes[index - 2])
        else:
            window.append("NONE")
        
        # i-1
        if index >= 1:
            window.append(content_hashes[index - 1])
        else:
            window.append("NONE")
        
        # i
        window.append(content_hashes[index])
        
        # i+1
        if index < len(content_hashes) - 1:
            window.append(content_hashes[index + 1])
        else:
            window.append("NONE")
        
        # i+2
        if index < len(content_hashes) - 2:
            window.append(content_hashes[index + 2])
        else:
            window.append("NONE")
        
        # 페이지 솔트
        window.append(self.page_salt or 'default_salt')
        
        combined = '|'.join(window)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def generate_page_salt(self, url: str, sort_option: str = "", filter_option: str = "") -> str:
        """
        페이지 솔트 생성 (URL, 정렬, 필터 조건 기반)
        """
        salt_parts = [
            url,
            f"sort:{sort_option}",
            f"filter:{filter_option}",
            datetime.now().strftime('%Y-%m-%d')  # 날짜 포함
        ]
        
        salt_string = '|'.join(salt_parts)
        self.page_salt = hashlib.md5(salt_string.encode('utf-8')).hexdigest()[:8]
        return self.page_salt
    
    def process_review_list(self, reviews: List[Dict], url: str = "", 
                           sort_option: str = "", filter_option: str = "") -> List[Dict]:
        """
        리뷰 리스트 전체 처리 - DSID 생성
        """
        # 페이지 솔트 생성
        self.generate_page_salt(url, sort_option, filter_option)
        
        # 초기화
        self.content_hashes = []
        self.rolling_hashes = []
        self.dsids = []
        
        # 1단계: 모든 콘텐츠 해시 계산
        for review in reviews:
            content_hash = self.calculate_content_hash(review)
            self.content_hashes.append(content_hash)
        
        # 2단계: 롤링 해시 계산
        for i, content_hash in enumerate(self.content_hashes):
            if i == 0:
                rolling_hash = self.calculate_rolling_hash(content_hash, None)
            else:
                rolling_hash = self.calculate_rolling_hash(content_hash, self.rolling_hashes[i-1])
            self.rolling_hashes.append(rolling_hash)
        
        # 3단계: DSID 및 이웃 윈도우 해시 계산
        for i in range(len(reviews)):
            dsid = self.calculate_dsid(i, self.content_hashes, self.rolling_hashes)
            neighbor_hash = self.calculate_neighbor_window_hash(i, self.content_hashes)
            
            # 리뷰 객체에 DSID 정보 추가
            reviews[i]['dsid'] = dsid
            reviews[i]['content_hash'] = self.content_hashes[i][:16]  # 축약
            reviews[i]['rolling_hash'] = self.rolling_hashes[i][:16]  # 축약
            reviews[i]['neighbor_hash'] = neighbor_hash[:16]  # 축약
            reviews[i]['page_salt'] = self.page_salt
            reviews[i]['index_hint'] = i
            
            self.dsids.append(dsid)
            
            logger.debug(f"리뷰 {i+1} DSID 생성: {dsid}")
        
        return reviews
    
    def find_review_by_dsid(self, target_dsid: str, current_reviews: List[Dict]) -> Optional[Dict]:
        """
        DSID로 리뷰 찾기 (재탐색)
        1차: DSID 완전 일치
        2차: 콘텐츠 해시 일치 + 근접 롤링 해시
        3차: 슬라이딩 윈도우 매칭
        """
        # 현재 페이지의 DSID 재계산
        processed_reviews = self.process_review_list(current_reviews.copy())
        
        # 1차: DSID 완전 일치
        for review in processed_reviews:
            if review['dsid'] == target_dsid:
                logger.info(f"DSID 완전 일치 발견: {target_dsid}")
                return review
        
        # 2차: 콘텐츠 해시 기반 매칭
        # TODO: 데이터베이스에서 원본 content_hash를 가져와서 비교
        
        # 3차: 슬라이딩 윈도우 매칭
        # TODO: 이웃 해시 기반 유사도 계산
        
        logger.warning(f"DSID {target_dsid}에 해당하는 리뷰를 찾을 수 없습니다")
        return None
    
    def validate_dsid_stability(self, reviews1: List[Dict], reviews2: List[Dict]) -> float:
        """
        DSID 안정성 검증 (테스트용)
        같은 리뷰 리스트에 대해 DSID가 일관되게 생성되는지 확인
        """
        # 두 리스트 처리
        processed1 = self.process_review_list(reviews1.copy())
        processed2 = self.process_review_list(reviews2.copy())
        
        # DSID 비교
        matching_count = 0
        for r1, r2 in zip(processed1, processed2):
            if r1['dsid'] == r2['dsid']:
                matching_count += 1
        
        stability_rate = matching_count / max(len(processed1), len(processed2))
        logger.info(f"DSID 안정성: {stability_rate:.2%}")
        
        return stability_rate


# 테스트 코드
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.DEBUG)
    
    # 테스트 리뷰 데이터
    test_reviews = [
        {
            'reviewer_name': 'di**',
            'review_date': '14시간 전',
            'review_text': '배달빠르고 맛있어요. 곱창은 여기서만 먹어요 ㅎㅎ',
            'order_menu': '[주문율 1위] 세친구 야채곱창',
            'rating': 5.0,
            'taste_rating': 5,
            'quantity_rating': 5,
            'image_urls': []
        },
        {
            'reviewer_name': 'ko**',
            'review_date': '2025.08.19',
            'review_text': '양이 많고 맛있어요',
            'order_menu': '알곱창 세트',
            'rating': 4.5,
            'taste_rating': 5,
            'quantity_rating': 4,
            'image_urls': ['https://example.com/image1.jpg']
        }
    ]
    
    # DSID 생성기 초기화
    generator = YogiyoDSIDGenerator()
    
    # DSID 생성
    processed_reviews = generator.process_review_list(
        test_reviews,
        url='https://ceo.yogiyo.co.kr/reviews',
        sort_option='latest',
        filter_option='unanswered'
    )
    
    # 결과 출력
    for i, review in enumerate(processed_reviews):
        print(f"\n리뷰 {i+1}:")
        print(f"  DSID: {review['dsid']}")
        print(f"  Content Hash: {review['content_hash']}")
        print(f"  Rolling Hash: {review['rolling_hash']}")
        print(f"  Neighbor Hash: {review['neighbor_hash']}")
        print(f"  리뷰어: {review['reviewer_name']}")
        print(f"  날짜: {review['review_date']}")
    
    # 안정성 테스트
    stability = generator.validate_dsid_stability(test_reviews, test_reviews)
    print(f"\n안정성 테스트 결과: {stability:.2%}")