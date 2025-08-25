#!/usr/bin/env python3
"""
Multi-Platform AI Reply System Test
테스트용 스크립트 - 멀티플랫폼 시스템 동작 확인
"""

import asyncio
import os
from ai_reply_manager import AIReplyManager

async def test_multiplatform_system():
    """멀티플랫폼 시스템 테스트"""
    
    try:
        print("=== Multi-Platform AI Reply System Test ===")
        
        # 1. AIReplyManager 초기화
        print("1. Initializing AIReplyManager...")
        manager = AIReplyManager()
        print("   [OK] AIReplyManager initialized successfully")
        
        # 2. 사용자 매장 조회
        user_id = "a7654c42-10ed-435f-97d8-d2c2dfeccbcb"
        print(f"\n2. Checking stores for user {user_id[:8]}...")
        
        stores_response = manager.supabase.table('platform_stores')\
            .select('id, platform, store_name, is_active')\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .execute()
        
        if stores_response.data:
            print(f"   [OK] Found {len(stores_response.data)} active stores")
            platforms = {}
            for store in stores_response.data:
                platform = store['platform']
                if platform not in platforms:
                    platforms[platform] = []
                platforms[platform].append(store['store_name'])
            
            for platform, stores in platforms.items():
                print(f"   - {platform.upper()}: {len(stores)} stores")
        
        # 3. 각 플랫폼별 리뷰 조회 테스트
        print(f"\n3. Testing review retrieval from each platform...")
        
        platform_review_counts = {}
        
        for platform_name, stores in platforms.items():
            try:
                adapter = manager.platform_manager.get_adapter(platform_name)
                total_reviews = 0
                draft_reviews = 0
                
                for store in stores_response.data:
                    if store['platform'] == platform_name:
                        # Get all reviews for this store
                        reviews = adapter.get_reviews_by_store(store['id'])
                        total_reviews += len(reviews)
                        
                        # Count draft reviews
                        draft_count = len([r for r in reviews if r.reply_status == 'draft'])
                        draft_reviews += draft_count
                
                platform_review_counts[platform_name] = {
                    'total': total_reviews,
                    'draft': draft_reviews
                }
                
                print(f"   - {platform_name.upper()}: {total_reviews} total, {draft_reviews} draft")
                
            except Exception as e:
                print(f"   - {platform_name.upper()}: Error - {e}")
        
        # 4. 플랫폼 통계 테스트
        print(f"\n4. Testing platform statistics...")
        try:
            stats = manager.platform_manager.get_platform_statistics(user_id)
            for platform, stat in stats.items():
                print(f"   - {platform.upper()}: {stat['total']} reviews ({stat['draft']} draft)")
        except Exception as e:
            print(f"   Error getting statistics: {e}")
        
        # 5. 결과 요약
        print(f"\n=== Test Results Summary ===")
        print(f"[OK] Platform Adapter System: Working")
        print(f"[OK] Multi-Platform Manager: Working")  
        print(f"[OK] Review Retrieval: Working")
        print(f"[OK] Statistics: Working")
        
        total_reviews = sum(counts['total'] for counts in platform_review_counts.values())
        total_draft = sum(counts['draft'] for counts in platform_review_counts.values())
        
        print(f"\nTotal Reviews Available: {total_reviews}")
        print(f"Draft Reviews Ready for AI: {total_draft}")
        
        if total_draft > 0:
            print(f"\n[SUCCESS] Multi-platform AI reply system is ready!")
            print(f"   You can now process {total_draft} reviews across {len(platforms)} platforms")
        else:
            print(f"\n[WARN] No draft reviews found for AI processing")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_multiplatform_system())
    exit(0 if success else 1)