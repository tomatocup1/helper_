"""
배달의민족 서비스 패키지
"""

try:
    from .auth_service import BaeminAuthService
except ImportError:
    from .auth_service_simple import BaeminAuthService
from .crawler_service import BaeminCrawlerService
from .parser import BaeminDataParser

__all__ = [
    "BaeminAuthService",
    "BaeminCrawlerService", 
    "BaeminDataParser"
]