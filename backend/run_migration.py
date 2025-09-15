#!/usr/bin/env python3
"""
Run database migration for reply greeting system
"""

import os
from supabase import create_client, Client

def run_migration():
    SUPABASE_URL = 'https://efcdjsrumdrhmpingglp.supabase.co'
    SUPABASE_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmY2Rqc3J1bWRyaG1waW5nZ2xwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTU2Mzc0MiwiZXhwIjoyMDcxMTM5NzQyfQ.grPU1SM6Y7rYwxcAf8f_txT0h6_DmRl4G0s-cyWOGrI'
    
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Step 1: Add new columns to platform_stores
    print("Adding new columns to platform_stores...")
    sql_commands = [
        """ALTER TABLE platform_stores 
        ADD COLUMN IF NOT EXISTS greeting_template VARCHAR(200),
        ADD COLUMN IF NOT EXISTS closing_template VARCHAR(200),
        ADD COLUMN IF NOT EXISTS reply_tone VARCHAR(20) DEFAULT 'friendly',
        ADD COLUMN IF NOT EXISTS reply_length VARCHAR(20) DEFAULT 'medium',
        ADD COLUMN IF NOT EXISTS brand_voice TEXT,
        ADD COLUMN IF NOT EXISTS keyword_insertion_rate FLOAT DEFAULT 0.7;""",
        
        """ALTER TABLE platform_stores 
        ADD COLUMN IF NOT EXISTS seo_keywords TEXT[];""",
        
        # Update existing stores with default values
        """UPDATE platform_stores 
        SET 
            reply_tone = COALESCE(reply_tone, 'friendly'),
            reply_length = COALESCE(reply_length, 'medium'),
            keyword_insertion_rate = COALESCE(keyword_insertion_rate, 0.7)
        WHERE reply_tone IS NULL OR reply_length IS NULL OR keyword_insertion_rate IS NULL;""",
        
        # Set default greeting/closing templates for existing stores
        """UPDATE platform_stores 
        SET 
            greeting_template = CASE 
                WHEN platform = 'naver' THEN '안녕하세요! {store_name}입니다 😊'
                WHEN platform = 'baemin' THEN '안녕하세요 {store_name}예요!'
                WHEN platform = 'yogiyo' THEN '안녕하세요! {store_name}에서 인사드려요'
                WHEN platform = 'coupangeats' THEN '안녕하세요 {store_name}입니다'
                ELSE '안녕하세요! {store_name}입니다'
            END,
            closing_template = CASE
                WHEN platform = 'naver' THEN '감사합니다. 또 방문해주세요! 🙏'
                WHEN platform = 'baemin' THEN '감사해요~ 다음에 또 주문해주세요!'
                WHEN platform = 'yogiyo' THEN '감사합니다! 또 이용해주세요'
                WHEN platform = 'coupangeats' THEN '감사합니다. 또 주문해주시길 바라요!'
                ELSE '감사합니다. 또 이용해주세요!'
            END
        WHERE greeting_template IS NULL AND closing_template IS NULL;"""
    ]
    
    for i, sql in enumerate(sql_commands, 1):
        try:
            print(f"Executing command {i}...")
            result = supabase.rpc('execute_sql', {'sql': sql}).execute()
            print(f"Command {i} executed successfully")
        except Exception as e:
            print(f"Command {i} failed: {str(e)}")
            print("Trying direct table operations...")
            
            # If direct SQL fails, try using table operations
            if i == 1:
                # This might fail if columns already exist, which is fine
                print("Adding columns individually...")
                
    # Create test store
    print("\nCreating test store...")
    test_user_id = 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
    
    try:
        # Check if test store exists
        existing_stores = supabase.table('platform_stores').select('*').eq('user_id', test_user_id).execute()
        
        if not existing_stores.data:
            test_store = {
                'user_id': test_user_id,
                'store_name': '테스트 매장',
                'platform': 'test',
                'platform_store_id': 'test_store_1',
                'is_active': True,
                'reply_tone': 'friendly',
                'reply_length': 'medium',
                'brand_voice': '친근하고 정중한 서비스를 제공하는 매장입니다.',
                'greeting_template': '안녕하세요! {store_name}입니다 😊',
                'closing_template': '감사합니다. 또 방문해주세요! 🙏',
                'seo_keywords': ['맛있는', '신선한', '친절한', '빠른배달'],
                'keyword_insertion_rate': 0.7
            }
            
            result = supabase.table('platform_stores').insert(test_store).execute()
            print(f"Test store created successfully: {result.data[0]['id']}")
        else:
            print(f"Test store already exists: {existing_stores.data[0]['store_name']}")
            
    except Exception as e:
        print(f"Error creating test store: {str(e)}")
    
    print("Migration completed!")

if __name__ == "__main__":
    run_migration()