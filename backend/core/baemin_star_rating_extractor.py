"""
배달의민족 별점 추출 엔진
SVG 기반 별점 시스템 처리
"""

import re
from typing import Optional, List, Dict, Any
from playwright.async_api import ElementHandle

class BaeminStarRatingExtractor:
    """배달의민족 별점 추출 클래스"""
    
    def __init__(self):
        # 배민 별점 색상 정의 (실제 배민 색상)
        self.active_color = "#FFC600"  # 활성 별점 색상 (노란색)
        self.inactive_color = "#D5D7D9"  # 비활성 별점 색상 (회색)
        
    async def extract_rating(self, review_element: ElementHandle, platform: str = 'baemin') -> Optional[int]:
        """
        리뷰 요소에서 별점 추출
        
        Args:
            review_element: 리뷰 요소 (ElementHandle)
            
        Returns:
            Optional[int]: 별점 (1-5) 또는 None
        """
        try:
            # 방법 1: 배민 SVG 별점 추출 (path의 fill 속성 확인)
            svg_stars = await review_element.query_selector_all('svg[viewBox="0 0 24 24"]')
            if svg_stars and len(svg_stars) > 0:
                filled_count = 0
                for star in svg_stars[:5]:  # 최대 5개 별만 확인
                    # path 요소의 fill 속성 확인 (배민은 path 안에 fill 속성이 있음)
                    path = await star.query_selector('path')
                    if path:
                        path_fill = await path.get_attribute('fill')
                        if path_fill and self.active_color in path_fill:
                            filled_count += 1
                
                if filled_count > 0:
                    return min(filled_count, 5)
            
            # 방법 2: 텍스트 기반 별점 추출
            rating_text = await review_element.inner_text()
            
            # "별점 5" 형식
            rating_match = re.search(r'별점\s*(\d)', rating_text)
            if rating_match:
                return int(rating_match.group(1))
            
            # "5점" 형식
            rating_match = re.search(r'(\d)점', rating_text)
            if rating_match:
                rating = int(rating_match.group(1))
                if 1 <= rating <= 5:
                    return rating
            
            # "⭐⭐⭐⭐⭐" 형식
            star_count = len(re.findall(r'⭐|★', rating_text))
            if star_count > 0:
                return min(star_count, 5)
            
            # 방법 3: 클래스 기반 별점 추출
            rating_element = await review_element.query_selector('[class*="rating"], [class*="star"]')
            if rating_element:
                class_name = await rating_element.get_attribute('class')
                if class_name:
                    # "rating-5", "star-5" 등의 패턴
                    rating_match = re.search(r'(?:rating|star)[-_]?(\d)', class_name)
                    if rating_match:
                        return int(rating_match.group(1))
            
            # 방법 4: data 속성 기반 별점 추출
            data_rating = await review_element.get_attribute('data-rating')
            if data_rating:
                try:
                    rating = int(float(data_rating))
                    if 1 <= rating <= 5:
                        return rating
                except (ValueError, TypeError):
                    pass
            
            return None
            
        except Exception as e:
            print(f"별점 추출 중 오류: {e}")
            return None
    
    async def extract_all_ratings(self, page) -> List[int]:
        """
        페이지의 모든 리뷰에서 별점 추출
        
        Args:
            page: Playwright page 객체
            
        Returns:
            List[int]: 별점 리스트
        """
        ratings = []
        
        # 리뷰 요소들 찾기
        review_elements = await page.query_selector_all('[class*="review"], [class*="Review"]')
        
        for element in review_elements:
            rating = await self.extract_rating(element)
            if rating:
                ratings.append(rating)
        
        return ratings
    
    def calculate_average(self, ratings: List[int]) -> float:
        """
        평균 별점 계산
        
        Args:
            ratings: 별점 리스트
            
        Returns:
            float: 평균 별점
        """
        if not ratings:
            return 0.0
        
        return round(sum(ratings) / len(ratings), 1)


# 이전 버전과의 호환성을 위한 별칭
StarRatingExtractor = BaeminStarRatingExtractor