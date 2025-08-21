#!/usr/bin/env python3
"""
통합 별점 추출 엔진
- 다양한 플랫폼의 별점 구조 분석 및 추출
- SVG, CSS 클래스, 이미지 등 다양한 방식 지원
- 견고한 에러 처리 및 폴백 메커니즘
"""

import re
from typing import Optional, Dict, List, Tuple
from datetime import datetime

class StarRatingExtractor:
    """통합 별점 추출기"""
    
    def __init__(self):
        # 플랫폼별 별점 구조 정의
        self.platform_configs = {
            'baemin': {
                'container_selectors': [
                    'div.rating-stars',
                    'div.star-rating',
                    'div[class*="rating"]',
                    'div[class*="star"]'
                ],
                'star_selectors': [
                    'svg',
                    'span[class*="star"]',
                    'i[class*="star"]'
                ],
                'active_colors': ['#FFC600', '#ffc600', '#FFD700', '#ffd700'],
                'inactive_colors': ['#D5D7D9', '#d5d7d9', '#CCCCCC', '#cccccc', '#E0E0E0'],
                'active_classes': ['star-active', 'star-filled', 'filled'],
                'inactive_classes': ['star-inactive', 'star-empty', 'empty']
            },
            'naver': {
                'container_selectors': [
                    'div.rating_star',
                    'div[class*="rating"]',
                    'div[class*="star"]'
                ],
                'star_selectors': [
                    'span.star',
                    'i[class*="star"]',
                    'svg'
                ],
                'active_colors': ['#FFD700', '#ffd700', '#FFC600'],
                'inactive_colors': ['#CCCCCC', '#cccccc', '#E0E0E0'],
                'active_classes': ['star-on', 'star-filled', 'active'],
                'inactive_classes': ['star-off', 'star-empty', 'inactive']
            },
            'yogiyo': {
                'container_selectors': [
                    'div.rating-display',
                    'div[class*="rating"]',
                    'div[class*="star"]'
                ],
                'star_selectors': [
                    'svg',
                    'span[class*="star"]',
                    'i[class*="star"]'
                ],
                'active_colors': ['#FF6B35', '#ff6b35', '#FFC600'],
                'inactive_colors': ['#D5D7D9', '#d5d7d9', '#CCCCCC'],
                'active_classes': ['star-active', 'filled'],
                'inactive_classes': ['star-inactive', 'empty']
            },
            'coupangeats': {
                'container_selectors': [
                    'div.star-rating',
                    'div[class*="rating"]',
                    'div[class*="star"]'
                ],
                'star_selectors': [
                    'svg',
                    'span[class*="star"]',
                    'i[class*="star"]'
                ],
                'active_colors': ['#FA622F', '#fa622f', '#FFC600'],
                'inactive_colors': ['#D5D7D9', '#d5d7d9', '#CCCCCC'],
                'active_classes': ['star-active', 'filled'],
                'inactive_classes': ['star-inactive', 'empty']
            }
        }
    
    async def extract_rating(self, review_element, platform: str = 'baemin') -> Optional[int]:
        """메인 별점 추출 함수"""
        try:
            print(f"[{platform}] 별점 추출 시작")
            
            # 1. SVG 기반 추출 시도
            rating = await self._extract_from_svg(review_element, platform)
            if rating is not None:
                print(f"[{platform}] SVG 기반 별점 추출 성공: {rating}/5")
                return rating
            
            # 2. CSS 클래스 기반 추출 시도
            rating = await self._extract_from_css_classes(review_element, platform)
            if rating is not None:
                print(f"[{platform}] CSS 클래스 기반 별점 추출 성공: {rating}/5")
                return rating
            
            # 3. 텍스트 기반 추출 시도
            rating = await self._extract_from_text(review_element, platform)
            if rating is not None:
                print(f"[{platform}] 텍스트 기반 별점 추출 성공: {rating}/5")
                return rating
            
            # 4. 스타일 속성 기반 추출 시도
            rating = await self._extract_from_styles(review_element, platform)
            if rating is not None:
                print(f"[{platform}] 스타일 기반 별점 추출 성공: {rating}/5")
                return rating
            
            print(f"[{platform}] 모든 방법으로 별점 추출 실패")
            return None
            
        except Exception as e:
            print(f"[{platform}] 별점 추출 중 오류: {str(e)}")
            return None
    
    async def _extract_from_svg(self, review_element, platform: str) -> Optional[int]:
        """SVG 기반 별점 추출"""
        try:
            config = self.platform_configs.get(platform, self.platform_configs['baemin'])
            
            # 별점 컨테이너 찾기 - 더 유연한 방법
            rating_container = None
            
            # 먼저 일반적인 컨테이너 선택자로 시도
            for selector in config['container_selectors']:
                rating_container = await review_element.query_selector(selector)
                if rating_container:
                    break
            
            # 컨테이너를 못 찾았으면 SVG를 직접 찾기
            if not rating_container:
                # SVG가 포함된 div 찾기 (배민의 경우)
                svg_parent = await review_element.query_selector('div:has(svg[width="16"][height="16"])')
                if svg_parent:
                    rating_container = svg_parent
                    print(f"[{platform}] SVG: 직접 SVG 부모 요소 발견")
                else:
                    # 그래도 못 찾으면 review_element 자체를 컨테이너로 사용
                    rating_container = review_element
                    print(f"[{platform}] SVG: 전체 요소에서 검색")
            
            # SVG 요소들 찾기
            star_elements = await rating_container.query_selector_all("svg")
            if not star_elements:
                print(f"[{platform}] SVG: SVG 요소를 찾을 수 없음")
                return None
            
            print(f"[{platform}] SVG: {len(star_elements)}개의 별 요소 발견")
            
            active_count = 0
            for i, star_element in enumerate(star_elements):
                is_active = await self._check_svg_star_active(star_element, config)
                if is_active:
                    active_count += 1
                print(f"[{platform}] SVG: 별 {i+1} - {'활성' if is_active else '비활성'}")
            
            return active_count if active_count > 0 else None
            
        except Exception as e:
            print(f"[{platform}] SVG 별점 추출 중 오류: {str(e)}")
            return None
    
    async def _check_svg_star_active(self, star_element, config: Dict) -> bool:
        """SVG 별의 활성 상태 확인"""
        try:
            # 1. SVG 자체의 fill 속성 확인
            fill_color = await star_element.get_attribute('fill')
            if fill_color and any(color.lower() in fill_color.lower() for color in config['active_colors']):
                return True
            
            # 2. path 요소의 fill 속성 확인
            path_elements = await star_element.query_selector_all('path')
            for path_element in path_elements:
                path_fill = await path_element.get_attribute('fill')
                if path_fill and any(color.lower() in path_fill.lower() for color in config['active_colors']):
                    return True
            
            # 3. style 속성 확인
            style = await star_element.get_attribute('style')
            if style:
                for color in config['active_colors']:
                    if color.lower() in style.lower():
                        return True
            
            # 4. 클래스 확인
            class_list = await star_element.get_attribute('class')
            if class_list:
                for active_class in config['active_classes']:
                    if active_class in class_list:
                        return True
            
            return False
            
        except Exception as e:
            print(f"SVG 별 상태 확인 중 오류: {str(e)}")
            return False
    
    async def _extract_from_css_classes(self, review_element, platform: str) -> Optional[int]:
        """CSS 클래스 기반 별점 추출"""
        try:
            config = self.platform_configs.get(platform, self.platform_configs['baemin'])
            
            # 별점 컨테이너 찾기
            rating_container = None
            for selector in config['container_selectors']:
                rating_container = await review_element.query_selector(selector)
                if rating_container:
                    break
            
            if not rating_container:
                return None
            
            # 별 요소들 찾기
            star_elements = []
            for selector in config['star_selectors']:
                stars = await rating_container.query_selector_all(selector)
                if stars:
                    star_elements = stars
                    break
            
            if not star_elements:
                return None
            
            print(f"[{platform}] CSS 클래스: {len(star_elements)}개의 별 요소 발견")
            
            active_count = 0
            for i, star_element in enumerate(star_elements):
                class_list = await star_element.get_attribute('class')
                if class_list:
                    is_active = any(active_class in class_list for active_class in config['active_classes'])
                    if is_active:
                        active_count += 1
                    print(f"[{platform}] CSS 클래스: 별 {i+1} - {'활성' if is_active else '비활성'} (클래스: {class_list})")
            
            return active_count if active_count > 0 else None
            
        except Exception as e:
            print(f"[{platform}] CSS 클래스 별점 추출 중 오류: {str(e)}")
            return None
    
    async def _extract_from_text(self, review_element, platform: str) -> Optional[int]:
        """텍스트 기반 별점 추출"""
        try:
            # 별점 관련 텍스트 패턴 찾기
            rating_patterns = [
                r'(\d+)점',
                r'(\d+)/5',
                r'(\d+)★',
                r'★(\d+)',
                r'Rating:\s*(\d+)',
                r'평점:\s*(\d+)',
                r'별점:\s*(\d+)'
            ]
            
            # 리뷰 요소의 모든 텍스트 가져오기
            text_content = await review_element.text_content()
            if not text_content:
                return None
            
            print(f"[{platform}] 텍스트 분석: {text_content[:100]}...")
            
            for pattern in rating_patterns:
                match = re.search(pattern, text_content)
                if match:
                    rating = int(match.group(1))
                    if 1 <= rating <= 5:
                        print(f"[{platform}] 텍스트에서 별점 발견: {rating}/5 (패턴: {pattern})")
                        return rating
            
            return None
            
        except Exception as e:
            print(f"[{platform}] 텍스트 별점 추출 중 오류: {str(e)}")
            return None
    
    async def _extract_from_styles(self, review_element, platform: str) -> Optional[int]:
        """스타일 속성 기반 별점 추출"""
        try:
            config = self.platform_configs.get(platform, self.platform_configs['baemin'])
            
            # 별점 컨테이너 찾기
            rating_container = None
            for selector in config['container_selectors']:
                rating_container = await review_element.query_selector(selector)
                if rating_container:
                    break
            
            if not rating_container:
                return None
            
            # width 기반 별점 추출 (width: 80% = 4점 등)
            style = await rating_container.get_attribute('style')
            if style and 'width:' in style:
                width_match = re.search(r'width:\s*(\d+(?:\.\d+)?)%', style)
                if width_match:
                    width_percent = float(width_match.group(1))
                    rating = round(width_percent / 20)  # 20% = 1점
                    if 1 <= rating <= 5:
                        print(f"[{platform}] 스타일 width에서 별점 추출: {rating}/5 ({width_percent}%)")
                        return rating
            
            # data 속성 확인
            data_rating = await rating_container.get_attribute('data-rating')
            if data_rating:
                try:
                    rating = int(float(data_rating))
                    if 1 <= rating <= 5:
                        print(f"[{platform}] data-rating에서 별점 추출: {rating}/5")
                        return rating
                except ValueError:
                    pass
            
            return None
            
        except Exception as e:
            print(f"[{platform}] 스타일 별점 추출 중 오류: {str(e)}")
            return None
    
    async def extract_detailed_rating(self, review_element, platform: str = 'baemin') -> Dict:
        """상세 별점 정보 추출 (전체 별점 + 세부 항목별 별점)"""
        try:
            result = {
                'overall_rating': None,
                'food_rating': None,
                'delivery_rating': None,
                'packaging_rating': None,
                'service_rating': None
            }
            
            # 전체 별점 추출
            overall_rating = await self.extract_rating(review_element, platform)
            result['overall_rating'] = overall_rating
            
            # 플랫폼별 세부 별점 추출
            if platform == 'baemin':
                # 배민의 경우 음식, 배송, 포장 별점이 있을 수 있음
                detail_ratings = await self._extract_baemin_detail_ratings(review_element)
                result.update(detail_ratings)
            
            return result
            
        except Exception as e:
            print(f"[{platform}] 상세 별점 추출 중 오류: {str(e)}")
            return {'overall_rating': None}
    
    async def _extract_baemin_detail_ratings(self, review_element) -> Dict:
        """배민 세부 별점 추출"""
        try:
            detail_ratings = {
                'food_rating': None,
                'delivery_rating': None,
                'packaging_rating': None
            }
            
            # 세부 별점 섹션 찾기
            detail_sections = await review_element.query_selector_all("div[class*='detail-rating']")
            
            for section in detail_sections:
                section_text = await section.text_content()
                if not section_text:
                    continue
                
                # 텍스트 기반으로 카테고리 판단
                if any(keyword in section_text for keyword in ['음식', '맛', 'food']):
                    rating = await self.extract_rating(section, 'baemin')
                    detail_ratings['food_rating'] = rating
                elif any(keyword in section_text for keyword in ['배송', '배달', 'delivery']):
                    rating = await self.extract_rating(section, 'baemin')
                    detail_ratings['delivery_rating'] = rating
                elif any(keyword in section_text for keyword in ['포장', 'packaging']):
                    rating = await self.extract_rating(section, 'baemin')
                    detail_ratings['packaging_rating'] = rating
            
            return detail_ratings
            
        except Exception as e:
            print(f"배민 세부 별점 추출 중 오류: {str(e)}")
            return {'food_rating': None, 'delivery_rating': None, 'packaging_rating': None}
    
    def validate_rating(self, rating: Optional[int]) -> bool:
        """별점 유효성 검사"""
        return rating is not None and isinstance(rating, int) and 1 <= rating <= 5
    
    async def debug_rating_structure(self, review_element, platform: str = 'baemin'):
        """별점 구조 디버깅 (개발용)"""
        try:
            print(f"\n=== [{platform}] 별점 구조 디버깅 ===")
            
            config = self.platform_configs.get(platform, self.platform_configs['baemin'])
            
            # 1. 컨테이너 찾기
            print("1. 컨테이너 검색:")
            for selector in config['container_selectors']:
                container = await review_element.query_selector(selector)
                if container:
                    print(f"   ✓ 발견: {selector}")
                    
                    # 컨테이너 내 요소들 분석
                    svg_elements = await container.query_selector_all("svg")
                    print(f"   SVG 요소: {len(svg_elements)}개")
                    
                    for i, svg in enumerate(svg_elements[:5]):  # 최대 5개만 출력
                        fill = await svg.get_attribute('fill')
                        style = await svg.get_attribute('style')
                        class_list = await svg.get_attribute('class')
                        print(f"     SVG {i+1}: fill={fill}, style={style}, class={class_list}")
                else:
                    print(f"   ✗ 없음: {selector}")
            
            # 2. 전체 HTML 구조 출력
            print("\n2. HTML 구조 샘플:")
            html_content = await review_element.inner_html()
            print(html_content[:500] + "..." if len(html_content) > 500 else html_content)
            
            print("=== 디버깅 완료 ===\n")
            
        except Exception as e:
            print(f"별점 구조 디버깅 중 오류: {str(e)}")

# 사용 예시
async def test_extractor():
    """테스트 함수"""
    extractor = StarRatingExtractor()
    
    # 실제 사용시에는 review_element를 playwright에서 가져온 요소로 사용
    print("별점 추출기 테스트 완료")
    print("사용 방법:")
    print("1. extractor = StarRatingExtractor()")
    print("2. rating = await extractor.extract_rating(review_element, 'baemin')")
    print("3. detailed = await extractor.extract_detailed_rating(review_element, 'baemin')")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_extractor())