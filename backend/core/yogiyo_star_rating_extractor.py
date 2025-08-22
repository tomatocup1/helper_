#!/usr/bin/env python3
"""
요기요 별점 추출기
SVG clipPath 분석을 통한 정확한 별점 추출
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from bs4 import BeautifulSoup
from playwright.async_api import ElementHandle, Page

logger = logging.getLogger(__name__)


class YogiyoStarRatingExtractor:
    """요기요 별점 추출 전문 클래스"""
    
    def __init__(self):
        # 요기요 별점 색상 정의
        self.FILLED_STAR_COLORS = [
            'hsla(45, 100%, 59%, 1)',  # 노란색 (채워진 별)
            '#FFC400',                  # 노란색 HEX
            'rgb(255, 196, 0)',        # 노란색 RGB
        ]
        
        self.EMPTY_STAR_COLORS = [
            '#f2f2f2',                 # 회색 (빈 별)
            'rgb(242, 242, 242)',      # 회색 RGB
        ]
    
    async def extract_overall_rating(self, review_element: ElementHandle) -> float:
        """
        전체 별점 추출 (숫자 텍스트 방식)
        예: <h6 class="cknzqP">5.0</h6>
        """
        try:
            # 전체 별점 텍스트 요소 찾기
            rating_selectors = [
                'h6.Typography__StyledTypography-sc-r9ksfy-0.cknzqP',
                'h6.cknzqP',
                'h6:has-text(".")',  # 소수점이 있는 h6
            ]
            
            for selector in rating_selectors:
                try:
                    rating_element = await review_element.query_selector(selector)
                    if rating_element:
                        rating_text = await rating_element.inner_text()
                        # 숫자 추출
                        match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                        if match:
                            rating = float(match.group(1))
                            logger.debug(f"전체 별점 추출 성공: {rating}")
                            return rating
                except Exception:
                    continue
            
            logger.warning("전체 별점을 찾을 수 없음")
            return 0.0
            
        except Exception as e:
            logger.error(f"전체 별점 추출 실패: {e}")
            return 0.0
    
    async def extract_sub_ratings(self, review_element: ElementHandle) -> Dict[str, int]:
        """
        맛/양 별점 추출 (SVG 분석 방식)
        """
        sub_ratings = {
            'taste': 0,
            'quantity': 0
        }
        
        try:
            # 평가 그룹 컨테이너 찾기
            rating_groups = await review_element.query_selector_all('div.RatingGroup___StyledDiv3-sc-pty1mk-3')
            
            if not rating_groups:
                # 백업 셀렉터
                rating_groups = await review_element.query_selector_all('div.tttps')
            
            for group in rating_groups:
                try:
                    group_html = await group.inner_html()
                    group_text = await group.inner_text()
                    
                    # 카테고리 판별 (맛/양)
                    category = None
                    if '맛' in group_text:
                        category = 'taste'
                    elif '양' in group_text:
                        category = 'quantity'
                    
                    if not category:
                        continue
                    
                    # SVG 분석 방법 1: clipPath rect width
                    rating = await self._extract_rating_from_svg_clippath(group_html)
                    
                    # SVG 분석 방법 2: fill 색상 카운트
                    if rating == 0:
                        rating = await self._extract_rating_from_svg_fill(group)
                    
                    # 텍스트에서 직접 추출 (백업)
                    if rating == 0:
                        match = re.search(r'(\d+)$', group_text)
                        if match:
                            rating = int(match.group(1))
                    
                    sub_ratings[category] = rating
                    logger.debug(f"{category} 별점: {rating}")
                    
                except Exception as e:
                    logger.error(f"서브 별점 그룹 처리 실패: {e}")
                    continue
            
            return sub_ratings
            
        except Exception as e:
            logger.error(f"서브 별점 추출 실패: {e}")
            return sub_ratings
    
    async def _extract_rating_from_svg_clippath(self, html: str) -> int:
        """
        SVG clipPath의 rect width 값으로 별점 계산
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # clipPath 내의 rect 요소 찾기
            clip_paths = soup.find_all('clipPath')
            
            for clip_path in clip_paths:
                rect = clip_path.find('rect')
                if rect and 'width' in rect.attrs:
                    width = rect['width']
                    try:
                        # width 값으로 별점 계산
                        # 21 = 1개, 42 = 2개, 63 = 3개, 84 = 4개, 105 = 5개
                        width_value = float(width)
                        rating = round(width_value / 21)
                        if 1 <= rating <= 5:
                            return rating
                    except:
                        pass
            
            return 0
            
        except Exception as e:
            logger.error(f"clipPath 별점 추출 실패: {e}")
            return 0
    
    async def _extract_rating_from_svg_fill(self, group_element: ElementHandle) -> int:
        """
        SVG fill 색상으로 별점 계산
        """
        try:
            # SVG 요소들 찾기
            svg_elements = await group_element.query_selector_all('svg')
            filled_count = 0
            
            for svg in svg_elements:
                svg_html = await svg.inner_html()
                
                # 채워진 별 확인
                is_filled = False
                for color in self.FILLED_STAR_COLORS:
                    if color in svg_html:
                        is_filled = True
                        break
                
                if is_filled:
                    filled_count += 1
            
            # 5개 이상이면 잘못된 것 (별은 최대 5개)
            if filled_count > 5:
                return 0
            
            return filled_count
            
        except Exception as e:
            logger.error(f"SVG fill 별점 추출 실패: {e}")
            return 0
    
    async def extract_all_ratings(self, review_element: ElementHandle) -> Dict[str, Any]:
        """
        모든 별점 정보 추출
        """
        try:
            # 전체 별점
            overall_rating = await self.extract_overall_rating(review_element)
            
            # 맛/양 별점
            sub_ratings = await self.extract_sub_ratings(review_element)
            
            result = {
                'overall': overall_rating,
                'taste': sub_ratings.get('taste', 0),
                'quantity': sub_ratings.get('quantity', 0),
                'extraction_method': 'svg_analysis',
                'confidence': self._calculate_confidence(overall_rating, sub_ratings)
            }
            
            logger.info(f"별점 추출 완료: 전체 {overall_rating}, 맛 {sub_ratings['taste']}, 양 {sub_ratings['quantity']}")
            
            return result
            
        except Exception as e:
            logger.error(f"전체 별점 추출 실패: {e}")
            return {
                'overall': 0.0,
                'taste': 0,
                'quantity': 0,
                'extraction_method': 'failed',
                'confidence': 0.0
            }
    
    def _calculate_confidence(self, overall: float, sub_ratings: Dict[str, int]) -> float:
        """
        추출된 별점의 신뢰도 계산
        """
        confidence = 1.0
        
        # 전체 별점이 없으면 신뢰도 감소
        if overall == 0:
            confidence *= 0.5
        
        # 서브 별점이 하나도 없으면 신뢰도 감소
        if sub_ratings['taste'] == 0 and sub_ratings['quantity'] == 0:
            confidence *= 0.7
        
        # 전체 별점과 서브 별점 평균의 차이가 크면 신뢰도 감소
        if sub_ratings['taste'] > 0 or sub_ratings['quantity'] > 0:
            sub_avg = (sub_ratings['taste'] + sub_ratings['quantity']) / 2
            if abs(overall - sub_avg) > 1:
                confidence *= 0.8
        
        return round(confidence, 2)
    
    async def extract_from_page_script(self, page: Page, review_index: int) -> Dict[str, Any]:
        """
        JavaScript를 사용한 별점 추출 (백업 방법)
        """
        try:
            result = await page.evaluate(f"""
                () => {{
                    const reviews = document.querySelectorAll('div.ReviewItem__Container-sc-1oxgj67-0');
                    if (reviews.length <= {review_index}) return null;
                    
                    const review = reviews[{review_index}];
                    
                    // 전체 별점
                    const overallElement = review.querySelector('h6.cknzqP');
                    const overall = overallElement ? parseFloat(overallElement.textContent) : 0;
                    
                    // 맛 별점
                    let taste = 0;
                    const tasteGroup = Array.from(review.querySelectorAll('div.tttps')).find(el => el.textContent.includes('맛'));
                    if (tasteGroup) {{
                        const tasteValue = tasteGroup.querySelector('p.iAqjFc');
                        taste = tasteValue ? parseInt(tasteValue.textContent) : 0;
                    }}
                    
                    // 양 별점
                    let quantity = 0;
                    const quantityGroup = Array.from(review.querySelectorAll('div.tttps')).find(el => el.textContent.includes('양'));
                    if (quantityGroup) {{
                        const quantityValue = quantityGroup.querySelector('p.iAqjFc');
                        quantity = quantityValue ? parseInt(quantityValue.textContent) : 0;
                    }}
                    
                    return {{
                        overall: overall,
                        taste: taste,
                        quantity: quantity
                    }};
                }}
            """)
            
            if result:
                result['extraction_method'] = 'javascript'
                result['confidence'] = 0.9
                return result
            
            return {
                'overall': 0.0,
                'taste': 0,
                'quantity': 0,
                'extraction_method': 'failed',
                'confidence': 0.0
            }
            
        except Exception as e:
            logger.error(f"JavaScript 별점 추출 실패: {e}")
            return {
                'overall': 0.0,
                'taste': 0,
                'quantity': 0,
                'extraction_method': 'failed',
                'confidence': 0.0
            }


# 테스트 코드
if __name__ == "__main__":
    import asyncio
    from playwright.async_api import async_playwright
    
    async def test_extractor():
        """별점 추출기 테스트"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            # 테스트 HTML (실제 요기요 리뷰 구조)
            test_html = """
            <div class="ReviewItem__Container-sc-1oxgj67-0">
                <h6 class="Typography__StyledTypography-sc-r9ksfy-0 cknzqP">4.5</h6>
                <div class="RatingGroup___StyledDiv3-sc-pty1mk-3 tttps">
                    <p>맛</p>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f2f2f2">
                        <clipPath id="starClip1">
                            <rect width="84" height="24"></rect>
                        </clipPath>
                        <use clip-path="url(#starClip1)" fill="hsla(45, 100%, 59%, 1)"></use>
                    </svg>
                    <p class="Typography__StyledTypography-sc-r9ksfy-0 iAqjFc">4</p>
                </div>
                <div class="RatingGroup___StyledDiv3-sc-pty1mk-3 tttps">
                    <p>양</p>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f2f2f2">
                        <clipPath id="starClip2">
                            <rect width="105" height="24"></rect>
                        </clipPath>
                        <use clip-path="url(#starClip2)" fill="hsla(45, 100%, 59%, 1)"></use>
                    </svg>
                    <p class="Typography__StyledTypography-sc-r9ksfy-0 iAqjFc">5</p>
                </div>
            </div>
            """
            
            await page.set_content(test_html)
            
            # 별점 추출기 테스트
            extractor = YogiyoStarRatingExtractor()
            review_element = await page.query_selector('div.ReviewItem__Container-sc-1oxgj67-0')
            
            if review_element:
                ratings = await extractor.extract_all_ratings(review_element)
                print(f"추출된 별점: {ratings}")
            
            await browser.close()
    
    # 테스트 실행
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_extractor())