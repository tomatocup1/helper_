#!/usr/bin/env python3
"""
우리가게 도우미 - AI 답글 시스템 엔트리포인트
Main entry point for AI reply generation and posting.
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
        print("  python ai_reply_system.py generate  # AI 답글 생성")
        print("  python ai_reply_system.py post      # 답글 등록") 
        return
    
    operation = sys.argv[1]
    
    if operation == 'generate':
        from ai_reply.main import main as ai_main
        ai_main()
    elif operation == 'post':
        # Import the CLI from post_replies.py
        import asyncio
        from naver_reply_poster import NaverReplyPoster
        
        async def run_poster():
            poster = NaverReplyPoster()
            await poster.process_approved_replies()
            
        asyncio.run(run_poster())
    else:
        print(f"알 수 없는 작업: {operation}")

if __name__ == "__main__":
    main()