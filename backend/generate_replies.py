#!/usr/bin/env python3
"""
AI 답글 자동 생성 - 간단한 실행 스크립트
답글이 생성되지 않은 모든 리뷰에 대해 AI 답글을 자동 생성합니다.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add core directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / 'core'))
sys.path.append(str(current_dir / 'core' / 'ai_reply'))

from ai_reply.main import AIReplySystem

async def main():
    """답글이 없는 모든 리뷰에 대해 AI 답글 생성"""
    try:
        print("🤖 AI 답글 자동 생성 시작...")
        print("=" * 50)
        
        system = AIReplySystem()
        
        # --batch 옵션으로 답글이 없는 모든 리뷰에 대해 생성
        success = await system.batch_generate_replies(
            store_id=None,  # 모든 매장
            all_stores=True,
            limit=100  # 최대 100개
        )
        
        if success:
            print("\n✅ AI 답글 생성 완료!")
        else:
            print("\n❌ AI 답글 생성 중 오류 발생")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        return False

if __name__ == "__main__":
    # Windows 환경에서 UTF-8 인코딩 설정
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    
    asyncio.run(main())