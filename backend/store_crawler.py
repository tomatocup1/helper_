#!/usr/bin/env python3
"""
우리가게 도우미 - 매장 크롤링 엔트리포인트
Main entry point for store crawling operations.
"""

import sys
import os
from pathlib import Path

# Add core directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / 'core'))

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python store_crawler.py reviews [store_id]  # 리뷰 크롤링")
        print("  python store_crawler.py stats [store_id]    # 통계 크롤링") 
        return
    
    operation = sys.argv[1]
    
    if operation == 'reviews':
        from naver_review_crawler import main as review_main
        review_main()
    elif operation == 'stats':
        from naver_statistics_crawler import main as stats_main  
        stats_main()
    else:
        print(f"알 수 없는 작업: {operation}")

if __name__ == "__main__":
    main()