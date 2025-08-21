"""
쿠팡잇츠 별점 추출 엔진
SVG 기반 별점 시스템 처리
"""

import re
from typing import Optional, List, Dict, Any
from playwright.async_api import ElementHandle

from backend.services.shared.logger import get_logger

logger = get_logger(__name__)

class CoupangStarRatingExtractor:
    """쿠팡잇츠 별점 추출 클래스"""
    
    def __init__(self):
        # 쿠팡잇츠 별점 색상 정의
        self.active_color = "#FFC400"  # 활성 별점 색상
        self.inactive_color = "#dfe3e8"  # 비활성 별점 색상
        
    async def extract_rating(self, review_element: ElementHandle) -> Optional[int]:
        """
        리뷰 요소에서 별점 추출
        
        Args:
            review_element: 리뷰 요소 (ElementHandle)
            
        Returns:
            Optional[int]: 별점 (1-5) 또는 None
        """
        try:
            logger.debug("Starting star rating extraction...")
            
            # 별점 전용 SVG 찾기 (페이지 전체 SVG 제외)
            rating_svg_selectors = [
                'svg[width="16"][height="16"]',  # 별점 SVG 크기
                'div:has(svg[width="16"]) svg',  # 별점 컨테이너 내 SVG
                'svg path[fill*="FFC400"], svg path[fill*="dfe3e8"]',  # 별점 색상 SVG
            ]
            
            svg_elements = []
            for selector in rating_svg_selectors:
                try:
                    elements = await review_element.query_selector_all(selector)
                    if elements and len(elements) <= 10:  # 별점은 최대 5개, 여유를 둔 10개 제한
                        svg_elements = elements
                        logger.debug(f"Found {len(svg_elements)} rating SVG elements using: {selector}")
                        break
                except Exception:
                    continue
            
            if svg_elements:
                # 각 SVG에서 별점 색상 확인
                active_stars = 0
                for i, svg_element in enumerate(svg_elements):
                    try:
                        is_active = await self._is_star_active(svg_element)
                        logger.debug(f"Rating SVG {i+1}: active={is_active}")
                        if is_active:
                            active_stars += 1
                    except Exception as e:
                        logger.debug(f"Error checking rating SVG {i+1}: {e}")
                        continue
                
                logger.debug(f"Rating SVG analysis: {active_stars}/{len(svg_elements)} active stars")
                
                if active_stars > 0 and active_stars <= 5:
                    return active_stars
            
            # SVG 별점 컨테이너 찾기 (기존 방식)
            rating_container = await self._find_rating_container(review_element)
            if not rating_container:
                logger.debug("No rating container found")
                return None
                
            # SVG 요소들 가져오기
            svg_elements = await rating_container.query_selector_all('svg')
            if not svg_elements:
                logger.warning("SVG elements not found in rating container")
                return None
            
            # 각 별점 SVG 분석
            active_stars = 0
            total_stars = len(svg_elements)
            
            for i, svg_element in enumerate(svg_elements):
                try:
                    is_active = await self._is_star_active(svg_element)
                    logger.debug(f"Container SVG {i+1}: active={is_active}")
                    if is_active:
                        active_stars += 1
                except Exception as e:
                    logger.debug(f"Error checking container SVG {i+1}: {e}")
                    continue
                    
            logger.debug(f"Container analysis: {active_stars}/{total_stars} active stars")
            
            # 별점 유효성 검증
            if active_stars > 5:
                logger.warning(f"Invalid star count: {active_stars}, capping to 5")
                active_stars = 5
                
            return active_stars if active_stars > 0 else None
            
        except Exception as e:
            logger.error(f"Error extracting star rating: {e}")
            return None
    
    async def _find_rating_container(self, review_element: ElementHandle) -> Optional[ElementHandle]:
        """별점 컨테이너 요소 찾기"""
        try:
            # 쿠팡잇츠는 별점이 div 안에 여러 SVG로 구성
            rating_selectors = [
                'div:has(svg[width="16"][height="16"])',  # 기본 별점 컨테이너
                'div > svg[width="16"][height="16"]:first-child',  # 첫 번째 SVG의 부모
                '[class*="rating"] div',  # rating 클래스가 포함된 div
                'div:has(path[fill="#FFC400"])',  # 활성 별점이 있는 div
            ]
            
            for selector in rating_selectors:
                try:
                    container = await review_element.query_selector(selector)
                    if container:
                        # SVG 요소가 실제로 있는지 확인
                        svg_count = await container.evaluate('el => el.querySelectorAll("svg").length')
                        if svg_count >= 3:  # 최소 3개 이상의 별점 SVG가 있어야 함
                            logger.debug(f"Found rating container with {svg_count} SVG elements using selector: {selector}")
                            return container
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
                    
            # 대안: 부모 요소에서 SVG 찾기
            svg_parent = await review_element.query_selector('div:has(svg)')
            if svg_parent:
                svg_count = await svg_parent.evaluate('el => el.querySelectorAll("svg").length')
                if svg_count >= 3:
                    return svg_parent
                    
            return None
            
        except Exception as e:
            logger.error(f"Error finding rating container: {e}")
            return None
    
    async def _is_star_active(self, svg_element: ElementHandle) -> bool:
        """개별 별점 SVG가 활성 상태인지 확인"""
        try:
            # 방법 1: path 요소의 fill 속성 확인
            path_element = await svg_element.query_selector('path')
            if path_element:
                fill_color = await path_element.get_attribute('fill')
                if fill_color:
                    # 색상 정규화 (대소문자, # 제거)
                    fill_color = fill_color.upper().replace('#', '')
                    active_color_normalized = self.active_color.upper().replace('#', '')
                    
                    is_active = fill_color == active_color_normalized
                    logger.debug(f"Star fill color: {fill_color}, expected: {active_color_normalized}, active: {is_active}")
                    
                    if is_active:
                        return True
            
            # 방법 2: JavaScript로 계산된 스타일 확인
            computed_color = await svg_element.evaluate('''
                (element) => {
                    const path = element.querySelector('path');
                    if (!path) return null;
                    
                    // 직접 fill 속성
                    const directFill = path.getAttribute('fill');
                    if (directFill) return directFill;
                    
                    // 계산된 스타일
                    const computedStyle = window.getComputedStyle(path);
                    return computedStyle.fill || null;
                }
            ''')
            
            if computed_color:
                # 색상 변환 (rgb를 hex로 변환하는 경우 등)
                normalized_color = self._normalize_color(computed_color)
                active_color_normalized = self.active_color.upper().replace('#', '')
                
                is_active = normalized_color == active_color_normalized
                logger.debug(f"Computed color: {computed_color} -> {normalized_color}, active: {is_active}")
                
                if is_active:
                    return True
            
            # 방법 3: SVG 전체 innerHTML 확인 (마지막 수단)
            svg_html = await svg_element.inner_html()
            is_active = self.active_color.lower() in svg_html.lower() or self.active_color.upper() in svg_html
            logger.debug(f"SVG HTML contains active color: {is_active}")
            
            return is_active
            
        except Exception as e:
            logger.error(f"Error checking star active state: {e}")
            return False
    
    def _normalize_color(self, color: str) -> str:
        """색상을 정규화 (RGB를 HEX로 변환 등)"""
        try:
            color = color.strip().upper()
            
            # 이미 HEX 형태인 경우
            if color.startswith('#'):
                return color.replace('#', '')
            
            # RGB 형태인 경우 (예: rgb(255, 196, 0))
            if color.startswith('RGB'):
                # rgb(255, 196, 0) 형태에서 숫자 추출
                import re
                matches = re.findall(r'\d+', color)
                if len(matches) >= 3:
                    r, g, b = int(matches[0]), int(matches[1]), int(matches[2])
                    return f"{r:02X}{g:02X}{b:02X}"
            
            # 원본 그대로 반환 (# 제거)
            return color.replace('#', '')
            
        except Exception as e:
            logger.debug(f"Color normalization failed for {color}: {e}")
            return color.upper().replace('#', '')
    
    async def extract_rating_with_fallback(self, review_element: ElementHandle) -> Dict[str, Any]:
        """
        별점 추출 (fallback 방식 포함)
        
        Returns:
            Dict: {
                'rating': int or None,
                'extraction_method': str,
                'confidence': float
            }
        """
        result = {
            'rating': None,
            'extraction_method': 'none',
            'confidence': 0.0
        }
        
        try:
            # 기본 방식으로 별점 추출
            rating = await self.extract_rating(review_element)
            if rating is not None:
                result['rating'] = rating
                result['extraction_method'] = 'svg_analysis'
                result['confidence'] = 0.9
                return result
            
            # 대안 1: JavaScript 평가로 별점 추출
            rating = await self._extract_rating_js(review_element)
            if rating is not None:
                result['rating'] = rating
                result['extraction_method'] = 'javascript_evaluation'
                result['confidence'] = 0.8
                return result
            
            # 대안 2: CSS 클래스나 속성으로 추출
            rating = await self._extract_rating_css(review_element)
            if rating is not None:
                result['rating'] = rating
                result['extraction_method'] = 'css_class_analysis'
                result['confidence'] = 0.7
                return result
                
            logger.warning("All rating extraction methods failed")
            return result
            
        except Exception as e:
            logger.error(f"Error in rating extraction with fallback: {e}")
            return result
    
    async def _extract_rating_js(self, review_element: ElementHandle) -> Optional[int]:
        """JavaScript를 사용한 별점 추출"""
        try:
            rating = await review_element.evaluate('''
                (element) => {
                    console.log('JavaScript rating extraction started');
                    
                    // 방법 1: SVG path 요소들을 찾아서 fill 색상 확인
                    const paths = element.querySelectorAll('svg path[fill*="FFC400"], svg path[fill*="ffc400"], svg path[fill*="#FFC400"], svg path[fill*="#ffc400"]');
                    console.log('Found paths with FFC400:', paths.length);
                    if (paths.length > 0 && paths.length <= 5) {
                        return paths.length;
                    }
                    
                    // 방법 2: 모든 SVG 확인
                    const svgs = element.querySelectorAll('svg');
                    console.log('Total SVGs found:', svgs.length);
                    let activeCount = 0;
                    
                    for (let i = 0; i < svgs.length; i++) {
                        const svg = svgs[i];
                        const path = svg.querySelector('path');
                        if (path) {
                            // 직접 속성 확인
                            const fill = path.getAttribute('fill') || '';
                            console.log(`SVG ${i+1} fill attribute:`, fill);
                            
                            if (fill.toUpperCase().includes('FFC400')) {
                                activeCount++;
                                console.log(`SVG ${i+1} is active (fill attribute)`);
                                continue;
                            }
                            
                            // 계산된 스타일 확인
                            const computedStyle = window.getComputedStyle(path);
                            const computedFill = computedStyle.fill || '';
                            console.log(`SVG ${i+1} computed fill:`, computedFill);
                            
                            if (computedFill.includes('rgb(255, 196, 0)') || computedFill.toUpperCase().includes('FFC400')) {
                                activeCount++;
                                console.log(`SVG ${i+1} is active (computed style)`);
                            }
                        }
                    }
                    
                    console.log('Active count:', activeCount);
                    
                    // 방법 3: innerHTML 전체 텍스트 검색
                    if (activeCount === 0) {
                        const innerHTML = element.innerHTML;
                        const ffc400Matches = (innerHTML.match(/FFC400|ffc400|#FFC400|#ffc400/gi) || []).length;
                        console.log('FFC400 matches in innerHTML:', ffc400Matches);
                        
                        if (ffc400Matches > 0 && ffc400Matches <= 5) {
                            return ffc400Matches;
                        }
                    }
                    
                    return activeCount > 0 && activeCount <= 5 ? activeCount : null;
                }
            ''')
            
            logger.debug(f"JavaScript extraction result: {rating}")
            
            if isinstance(rating, (int, float)) and 1 <= rating <= 5:
                return int(rating)
                
            return None
            
        except Exception as e:
            logger.error(f"JavaScript rating extraction failed: {e}")
            return None
    
    async def _extract_rating_css(self, review_element: ElementHandle) -> Optional[int]:
        """CSS 클래스/속성을 이용한 별점 추출"""
        try:
            # 별점 관련 속성이나 클래스 찾기
            rating_attrs = await review_element.evaluate('''
                (element) => {
                    // data-rating, rating 등의 속성 확인
                    const ratingAttr = element.getAttribute('data-rating') || 
                                     element.getAttribute('rating') ||
                                     element.querySelector('[data-rating]')?.getAttribute('data-rating');
                    
                    if (ratingAttr) {
                        const rating = parseInt(ratingAttr);
                        if (!isNaN(rating) && rating >= 1 && rating <= 5) {
                            return rating;
                        }
                    }
                    
                    // 클래스명에서 별점 찾기
                    const classNames = element.className || '';
                    const ratingMatch = classNames.match(/rating[_-]?(\\d)/i);
                    if (ratingMatch) {
                        const rating = parseInt(ratingMatch[1]);
                        if (rating >= 1 && rating <= 5) {
                            return rating;
                        }
                    }
                    
                    return null;
                }
            ''')
            
            if isinstance(rating_attrs, (int, float)) and 1 <= rating_attrs <= 5:
                return int(rating_attrs)
                
            return None
            
        except Exception as e:
            logger.error(f"CSS rating extraction failed: {e}")
            return None