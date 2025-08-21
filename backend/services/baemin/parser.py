"""
배달의민족 데이터 파싱 유틸리티
매장 정보 추출 및 변환
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ..shared.logger import get_logger

logger = get_logger(__name__)

@dataclass
class BaeminStoreInfo:
    """배민 매장 정보 데이터 클래스"""
    platform_store_id: str
    store_name: str
    business_type: str
    sub_type: str
    full_text: str
    is_valid: bool = True
    error_message: Optional[str] = None

class BaeminDataParser:
    """배달의민족 데이터 파싱 클래스"""
    
    @staticmethod
    def parse_store_option(option_value: str, option_text: str) -> BaeminStoreInfo:
        """
        배민 매장 드롭박스 옵션에서 매장 정보 추출
        
        예시:
        option_value: "14522306"
        option_text: "[음식배달] 더클램스 & 화채꽃이야기 / 카페·디저트 14522306"
        """
        try:
            # 기본 정보 설정
            store_info = BaeminStoreInfo(
                platform_store_id=option_value.strip(),
                store_name="",
                business_type="",
                sub_type="",
                full_text=option_text.strip()
            )
            
            # 옵션 텍스트 파싱
            text = option_text.strip()
            
            # 정규식 패턴으로 파싱
            # 패턴: [서브타입] 매장명 / 업종 ID
            pattern = r'(\[.+?\])\s*(.+?)\s*/\s*(.+?)\s*(\d+)(?:\s+.*)?$'
            match = re.match(pattern, text)
            
            if match:
                sub_type = match.group(1).strip()
                store_name = match.group(2).strip()
                business_type = match.group(3).strip()
                extracted_id = match.group(4).strip()
                
                # ID 일치성 확인
                if extracted_id != option_value.strip():
                    logger.warning(f"ID mismatch: option_value={option_value}, extracted={extracted_id}")
                
                store_info.sub_type = sub_type
                store_info.store_name = store_name
                store_info.business_type = business_type
                
            else:
                # 대체 파싱 시도 (더 유연한 패턴)
                fallback_pattern = r'(\[.+?\])\s*(.+?)(?:\s*/\s*(.+?))?(?:\s+(\d+))?'
                fallback_match = re.match(fallback_pattern, text)
                
                if fallback_match:
                    store_info.sub_type = fallback_match.group(1) or ""
                    store_info.store_name = fallback_match.group(2) or ""
                    store_info.business_type = fallback_match.group(3) or ""
                else:
                    # 파싱 실패
                    store_info.is_valid = False
                    store_info.error_message = f"Failed to parse store option: {text}"
                    logger.error(f"Failed to parse baemin store option: {text}")
            
            # 데이터 정제
            store_info = BaeminDataParser._clean_store_info(store_info)
            
            return store_info
            
        except Exception as e:
            logger.error(f"Error parsing store option: {e}")
            return BaeminStoreInfo(
                platform_store_id=option_value,
                store_name="",
                business_type="",
                sub_type="",
                full_text=option_text,
                is_valid=False,
                error_message=str(e)
            )
    
    @staticmethod
    def _clean_store_info(store_info: BaeminStoreInfo) -> BaeminStoreInfo:
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
            
            # 매장명에서 ID 제거 (끝에 숫자가 붙은 경우)
            store_info.store_name = re.sub(r'\s+\d+$', '', store_info.store_name)
        
        # 업종 정제
        if store_info.business_type:
            store_info.business_type = store_info.business_type.strip()
            # 쉼표를 구분자로 사용
            store_info.business_type = store_info.business_type.replace('·', ',')
        
        # 서브타입 정제
        if store_info.sub_type:
            store_info.sub_type = store_info.sub_type.strip()
        
        return store_info
    
    @staticmethod
    def parse_multiple_stores(options_data: List[Dict[str, str]]) -> List[BaeminStoreInfo]:
        """여러 매장 정보 일괄 파싱"""
        stores = []
        
        for option in options_data:
            value = option.get('value', '')
            text = option.get('text', '')
            
            if value and text:
                store_info = BaeminDataParser.parse_store_option(value, text)
                stores.append(store_info)
            else:
                logger.warning(f"Invalid option data: {option}")
        
        return stores
    
    @staticmethod
    def filter_valid_stores(stores: List[BaeminStoreInfo]) -> List[BaeminStoreInfo]:
        """유효한 매장 정보만 필터링"""
        valid_stores = []
        
        for store in stores:
            if store.is_valid and store.platform_store_id and store.store_name:
                valid_stores.append(store)
            else:
                logger.warning(f"Invalid store filtered out: {store}")
        
        return valid_stores
    
    @staticmethod
    def to_database_format(store: BaeminStoreInfo, user_id: str) -> Dict[str, Any]:
        """데이터베이스 저장 형식으로 변환"""
        return {
            'user_id': user_id,
            'platform': 'baemin',
            'platform_store_id': store.platform_store_id,
            'store_name': store.store_name,
            'business_type': store.business_type,
            'sub_type': store.sub_type,
            'is_active': True,
            'crawling_enabled': True,
            'auto_reply_enabled': False,  # 배민은 기본 비활성화
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
        
        # 서브타입 형식 검증
        sub_type = store_data.get('sub_type', '')
        if sub_type and not re.match(r'^\[.+\]$', sub_type):
            errors.append(f"Invalid sub_type format: {sub_type}")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'data': store_data
        }
    
    @staticmethod
    def get_store_summary(stores: List[BaeminStoreInfo]) -> Dict[str, Any]:
        """매장 목록 요약 정보 생성"""
        total_count = len(stores)
        valid_count = len([s for s in stores if s.is_valid])
        invalid_count = total_count - valid_count
        
        # 업종별 분류
        business_types = {}
        sub_types = {}
        
        for store in stores:
            if store.is_valid:
                if store.business_type:
                    business_types[store.business_type] = business_types.get(store.business_type, 0) + 1
                if store.sub_type:
                    sub_types[store.sub_type] = sub_types.get(store.sub_type, 0) + 1
        
        return {
            'total_count': total_count,
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'business_types': business_types,
            'sub_types': sub_types,
            'errors': [store.error_message for store in stores if not store.is_valid and store.error_message]
        }