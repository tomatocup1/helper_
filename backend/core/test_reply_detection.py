"""
요기요 리뷰 크롤러 답글 감지 기능 테스트
"""

import asyncio
import logging
from pathlib import Path
import sys

# 현재 디렉토리를 경로에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from yogiyo_review_crawler import YogiyoReviewCrawler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yogiyo_reply_detection_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

async def test_reply_detection():
    """답글 감지 기능 테스트"""
    
    print("=" * 60)
    print("요기요 리뷰 크롤러 - 답글 감지 기능 테스트")
    print("=" * 60)
    
    # 테스트용 크롤러 초기화
    crawler = YogiyoReviewCrawler()
    
    try:
        print("\n1. 크롤러 초기화 완료")
        
        print("\n2. 테스트용 매장에서 리뷰 수집을 시작합니다...")
        print("   - 답글이 있는 리뷰는 자동으로 스킵됩니다")
        print("   - 미답변 리뷰만 수집됩니다")
        
        # 실제 테스트를 위해서는 사용자가 제공한 매장 정보가 필요
        print("\n이 테스트를 실행하려면 다음 정보가 필요합니다:")
        print("- username: 요기요 계정 아이디")
        print("- password: 요기요 계정 비밀번호")
        print("- store_id: 테스트할 매장의 플랫폼 스토어 ID")
        
        print("\n테스트 실행 예시:")
        print("python test_reply_detection.py")
        print("(실행 시 크롤러가 시작되고 답글 감지 결과를 확인할 수 있습니다)")
        
        # 실제 테스트 실행 (실제 계정 정보가 필요)
        test_mode = True  # 실제 테스트할 때는 False로 변경
        
        if not test_mode:
            # 실제 크롤링 테스트
            result = await crawler.crawl_reviews(
                username="your_username",  # 실제 아이디 입력
                password="your_password",  # 실제 비밀번호 입력
                store_id="your_store_id",  # 실제 매장 ID 입력
                max_scrolls=2  # 테스트용으로 2페이지만
            )
            
            if result['success']:
                print(f"\n✅ 테스트 성공!")
                print(f"   - 총 수집된 리뷰: {len(result['reviews'])}개")
                print(f"   - 답글이 있어서 스킵된 리뷰는 로그에서 확인 가능")
                
                # 수집된 리뷰 중 일부 정보 표시
                for i, review in enumerate(result['reviews'][:3]):
                    print(f"\n   리뷰 {i+1}:")
                    print(f"     작성자: {review['reviewer_name']}")
                    print(f"     평점: {review['rating']}")
                    print(f"     내용: {review['review_text'][:50]}...")
                    print(f"     날짜: {review['review_date']}")
            else:
                print(f"\n❌ 테스트 실패: {result['message']}")
        else:
            print("\n🔧 테스트 모드: 실제 크롤링은 실행하지 않습니다")
            print("실제 테스트를 위해서는 test_mode를 False로 변경하고")
            print("username, password, store_id를 실제 값으로 입력하세요")
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}")
        print(f"\n❌ 테스트 실행 중 오류: {e}")
    
    finally:
        print("\n" + "=" * 60)
        print("테스트 완료")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_reply_detection())