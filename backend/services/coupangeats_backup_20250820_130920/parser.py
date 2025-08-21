"""
쿠팡이츠 데이터 파싱 유틸리티
매장 정보 추출 및 변환
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ..shared.logger import get_logger

logger = get_logger(__name__)

@dataclass
class CoupangEatsStoreInfo:
    """쿠팡이츠 매장 정보 데이터 클래스"""
    platform_store_id: str
    store_name: str
    full_text: str
    is_valid: bool = True
    error_message: Optional[str] = None

class CoupangEatsDataParser:
    """쿠팡이츠 데이터 파싱 클래스"""
    
    @staticmethod
    def parse_store_option(option_text: str) -> CoupangEatsStoreInfo:
        """
        쿠팡이츠 매장 드롭다운 옵션에서 매장 정보 추출
        
        예시:
        option_text: "큰집닭강정(708561)"
        
        Returns:
            CoupangEatsStoreInfo 객체
        """
        try:
            # 기본 정보 설정
            store_info = CoupangEatsStoreInfo(
                platform_store_id="",
                store_name="",
                full_text=option_text.strip()
            )
            
            # 옵션 텍스트 파싱
            text = option_text.strip()
            
            # 정규식 패턴으로 파싱 - 매장명(ID) 형식
            # 패턴: 매장명(숫자ID)
            pattern = r'^(.+?)\((\d+)\)$'
            match = re.match(pattern, text)
            
            if match:
                store_name = match.group(1).strip()
                platform_store_id = match.group(2).strip()
                
                store_info.store_name = store_name
                store_info.platform_store_id = platform_store_id
                
            else:
                # 대체 파싱 시도 (괄호 없는 경우)
                fallback_pattern = r'^(.+?)(\d+)$'
                fallback_match = re.match(fallback_pattern, text)
                
                if fallback_match and len(fallback_match.group(2)) >= 4:
                    # ID가 4자리 이상인 경우만 유효하다고 간주
                    store_info.store_name = fallback_match.group(1).strip()
                    store_info.platform_store_id = fallback_match.group(2).strip()
                else:
                    # 파싱 실패
                    store_info.is_valid = False
                    store_info.error_message = f"Failed to parse store option: {text}"
                    logger.error(f"Failed to parse coupangeats store option: {text}")
            
            # 데이터 정제
            store_info = CoupangEatsDataParser._clean_store_info(store_info)
            
            return store_info
            
        except Exception as e:
            logger.error(f"Error parsing store option: {e}")
            return CoupangEatsStoreInfo(
                platform_store_id="",
                store_name="",
                full_text=option_text,
                is_valid=False,
                error_message=str(e)
            )
    
    @staticmethod
    def _clean_store_info(store_info: CoupangEatsStoreInfo) -> CoupangEatsStoreInfo:
        """매장 정보 데이터 정제"""
        # 매장명 정제
        if store_info.store_name:
            # HTML 엔티티 디코딩
            store_info.store_name = store_info.store_name.replace('&amp;', '&')
            store_info.store_name = store_info.store_name.replace('&lt;', '<')
            store_info.store_name = store_info.store_name.replace('&gt;', '>')
            store_info.store_name = store_info.store_name.replace('&quot;', '"')
            
            # 불필요한 공백 제거
            store_info.store_name = ' '.join(store_info.store_name.split())
        
        return store_info
    
    @staticmethod
    def parse_multiple_stores(options_data: List[str]) -> List[CoupangEatsStoreInfo]:
        """여러 매장 정보 일괄 파싱"""
        stores = []
        
        for option_text in options_data:
            if option_text and option_text.strip():
                store_info = CoupangEatsDataParser.parse_store_option(option_text)
                stores.append(store_info)
            else:
                logger.warning(f"Empty or invalid option data: {option_text}")
        
        return stores
    
    @staticmethod
    def filter_valid_stores(stores: List[CoupangEatsStoreInfo]) -> List[CoupangEatsStoreInfo]:
        """유효한 매장 정보만 필터링"""
        valid_stores = []
        
        for store in stores:
            if store.is_valid and store.platform_store_id and store.store_name:
                valid_stores.append(store)
            else:
                logger.warning(f"Invalid store filtered out: {store}")
        
        return valid_stores
    
    @staticmethod
    def to_database_format(store: CoupangEatsStoreInfo, user_id: str) -> Dict[str, Any]:
        """데이터베이스 저장 형식으로 변환"""
        return {
            'user_id': user_id,
            'platform': 'coupangeats',
            'platform_store_id': store.platform_store_id,
            'store_name': store.store_name,
            'business_type': None,  # 쿠팡이츠는 업종 정보 없음
            'is_active': True,
            'crawling_enabled': True,
            'auto_reply_enabled': False,  # 쿠팡이츠는 기본 비활성화
        }
    
    @staticmethod
    def validate_store_data(store_data: Dict[str, Any]) -> Dict[str, Any]:
        """매장 데이터 유효성 검증"""
        errors = []
        
        # 필수 필드 검증
        required_fields = ['platform_store_id', 'store_name']
        for field in required_fields:
            if not store_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # 플랫폼 매장 ID 형식 검증 (숫자만)
        platform_store_id = store_data.get('platform_store_id', '')
        if platform_store_id and not platform_store_id.isdigit():
            errors.append(f"Invalid platform_store_id format: {platform_store_id}")
        
        # 매장명 길이 검증
        store_name = store_data.get('store_name', '')
        if len(store_name) > 200:
            errors.append(f"Store name too long: {len(store_name)} chars")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'data': store_data
        }
    
    @staticmethod
    def get_store_summary(stores: List[CoupangEatsStoreInfo]) -> Dict[str, Any]:
        """매장 목록 요약 정보 생성"""
        total_count = len(stores)
        valid_count = len([s for s in stores if s.is_valid])
        invalid_count = total_count - valid_count
        
        # 매장명 분석 (쿠팡이츠는 업종 정보가 없어서 매장명으로 카테고리 추정)
        store_categories = {}
        
        for store in stores:
            if store.is_valid and store.store_name:
                # 매장명에서 카테고리 추정
                name = store.store_name.lower()
                category = "기타"
                
                if any(word in name for word in ['치킨', '닭', '통닭']):
                    category = "치킨"
                elif any(word in name for word in ['피자', 'pizza']):
                    category = "피자"
                elif any(word in name for word in ['족발', '보쌈']):
                    category = "족발/보쌈"
                elif any(word in name for word in ['중국', '중화', '짜장', '짬뽕']):
                    category = "중식"
                elif any(word in name for word in ['한식', '백반', '정식']):
                    category = "한식"
                elif any(word in name for word in ['카페', '커피', 'coffee']):
                    category = "카페/디저트"
                elif any(word in name for word in ['버거', 'burger', '햄버거']):
                    category = "패스트푸드"
                
                store_categories[category] = store_categories.get(category, 0) + 1
        
        return {
            'total_count': total_count,
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'store_categories': store_categories,
            'errors': [store.error_message for store in stores if not store.is_valid and store.error_message]
        }