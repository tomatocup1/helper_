"""
간단한 Python 백엔드 서버
FastAPI를 사용한 REST API 서버
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path
import sys
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from supabase import create_client, Client

# Add core directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / 'core'))
sys.path.append(str(current_dir))

app = FastAPI(title="Store Helper Backend API")

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://efcdjsrumdrhmpingglp.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmY2Rqc3J1bWRyaG1waW5nZ2xwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTU2Mzc0MiwiZXhwIjoyMDcxMTM5NzQyfQ.grPU1SM6Y7rYwxcAf8f_txT0h6_DmRl4G0s-cyWOGrI")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Pydantic 모델들
class ReplySettings(BaseModel):
    autoReplyEnabled: bool = False
    replyTone: str = 'friendly'
    minReplyLength: int = 50
    maxReplyLength: int = 200
    brandVoice: str = ""
    greetingTemplate: str = ""
    closingTemplate: str = ""
    seoKeywords: List[str] = []
    autoApprovalDelayHours: int = 48

class StoreInfo(BaseModel):
    id: str
    store_name: str
    platform: str
    platform_store_id: str
    auto_reply_enabled: bool
    reply_tone: str

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:4000",
        "https://*.vercel.app",  # Vercel 배포 도메인
        "https://store-helper-frontend.vercel.app",  # 특정 Vercel 앱
        "*"  # 개발 중에는 모든 도메인 허용
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Store Helper Backend API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/status")
async def api_status():
    return {
        "service": "Store Helper Backend",
        "version": "1.0.0",
        "status": "operational"
    }

# 스토어 관련 엔드포인트
@app.get("/api/stores")
async def get_stores():
    """모든 스토어 목록 조회"""
    try:
        response = supabase.table('stores').select("*").execute()
        return {"success": True, "stores": response.data}
    except Exception as e:
        print(f"Error fetching stores: {e}")
        return {"success": False, "stores": [], "error": str(e)}

@app.get("/api/user-stores/{user_id}")
async def get_user_stores(user_id: str):
    """특정 사용자의 스토어 목록 조회"""
    try:
        # stores 테이블에서 user_id로 조회
        response = supabase.table('stores').select("*").eq('user_id', user_id).execute()
        return {"success": True, "stores": response.data}
    except Exception as e:
        print(f"Error fetching user stores: {e}")
        return {"success": False, "stores": [], "error": str(e)}

@app.post("/api/stores")
async def create_store(store_data: dict):
    """새 스토어 생성"""
    try:
        response = supabase.table('stores').insert(store_data).execute()
        return {"success": True, "store": response.data[0] if response.data else None}
    except Exception as e:
        print(f"Error creating store: {e}")
        return {"success": False, "error": str(e)}

# 크롤러 관련 엔드포인트
@app.post("/crawler/start")
async def start_crawler(store_id: str):
    # 크롤러 로직 구현
    return {"message": f"Crawler started for store {store_id}", "status": "started"}

@app.get("/crawler/status/{task_id}")
async def crawler_status(task_id: str):
    return {"task_id": task_id, "status": "in_progress", "progress": 50}

# 스케줄러 관련 엔드포인트
@app.post("/scheduler/create")
async def create_schedule(schedule_data: dict):
    return {"message": "Schedule created", "schedule_id": "sch_123"}

@app.get("/scheduler/list")
async def list_schedules():
    return {"schedules": []}

# AI 답글 관련 엔드포인트
@app.post("/ai/generate-reply")
async def generate_reply(review_data: dict):
    return {"reply": "감사합니다. 더 나은 서비스를 제공하도록 노력하겠습니다."}

# 답글 설정 관련 엔드포인트
@app.get("/api/reply-settings/{user_id}")
async def get_reply_settings(user_id: str):
    """사용자 답글 설정 조회"""
    try:
        # ai_reply_settings 테이블에서 user_id로 조회
        response = supabase.table('ai_reply_settings').select("*").eq('user_id', user_id).execute()

        if response.data and len(response.data) > 0:
            settings = response.data[0]
            return {
                "success": True,
                "settings": {
                    "autoReplyEnabled": settings.get("auto_reply_enabled", False),
                    "replyTone": settings.get("reply_tone", "friendly"),
                    "minReplyLength": settings.get("min_reply_length", 50),
                    "maxReplyLength": settings.get("max_reply_length", 200),
                    "brandVoice": settings.get("brand_voice", ""),
                    "greetingTemplate": settings.get("greeting_template", ""),
                    "closingTemplate": settings.get("closing_template", ""),
                    "seoKeywords": settings.get("seo_keywords", []),
                    "autoApprovalDelayHours": settings.get("auto_approval_delay_hours", 48)
                }
            }
        else:
            # 기본 설정 반환
            return {
                "success": True,
                "settings": {
                    "autoReplyEnabled": False,
                    "replyTone": "friendly",
                    "minReplyLength": 50,
                    "maxReplyLength": 200,
                    "brandVoice": "",
                    "greetingTemplate": "",
                    "closingTemplate": "",
                    "seoKeywords": [],
                    "autoApprovalDelayHours": 48
                }
            }
    except Exception as e:
        print(f"Error fetching reply settings: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/reply-settings/{user_id}")
async def update_reply_settings(user_id: str, settings: ReplySettings):
    """사용자 답글 설정 업데이트"""
    try:
        # DB 형식으로 변환
        db_settings = {
            "user_id": user_id,
            "auto_reply_enabled": settings.autoReplyEnabled,
            "reply_tone": settings.replyTone,
            "min_reply_length": settings.minReplyLength,
            "max_reply_length": settings.maxReplyLength,
            "brand_voice": settings.brandVoice,
            "greeting_template": settings.greetingTemplate,
            "closing_template": settings.closingTemplate,
            "seo_keywords": settings.seoKeywords,
            "auto_approval_delay_hours": settings.autoApprovalDelayHours
        }

        # 기존 설정이 있는지 확인
        existing = supabase.table('ai_reply_settings').select("*").eq('user_id', user_id).execute()

        if existing.data and len(existing.data) > 0:
            # 업데이트
            response = supabase.table('ai_reply_settings').update(db_settings).eq('user_id', user_id).execute()
        else:
            # 새로 생성
            response = supabase.table('ai_reply_settings').insert(db_settings).execute()

        return {"success": True, "message": "Settings updated successfully"}
    except Exception as e:
        print(f"Error updating reply settings: {e}")
        return {"success": False, "error": str(e)}

# 플랫폼 연결 엔드포인트
@app.post("/api/v1/platform/connect")
async def connect_platform(request_data: dict):
    """플랫폼 연결 엔드포인트"""
    import asyncio
    from datetime import datetime
    
    platform = request_data.get('platform')
    credentials = request_data.get('credentials', {})
    
    print(f"[API] {platform} 연결 요청 받음: {credentials.get('username', 'N/A')}")
    
    if platform == 'coupangeats':
        from services.coupangeats.simple_crawler import CoupangEatsCrawler
        
        async with CoupangEatsCrawler() as crawler:
            success, stores, message = await crawler.crawl_stores(
                credentials.get('username', ''),
                credentials.get('password', '')
            )
            
            return {
                "success": success,
                "message": message,
                "stores": stores,
                "platform": platform,
                "timestamp": datetime.now().isoformat()
            }
            
    elif platform == 'yogiyo':
        from services.yogiyo.simple_crawler import YogiyoCrawler
        
        async with YogiyoCrawler() as crawler:
            success, stores, message = await crawler.crawl_stores(
                credentials.get('username', ''),
                credentials.get('password', '')
            )
            
            return {
                "success": success,
                "message": message,
                "stores": stores,
                "platform": platform,
                "timestamp": datetime.now().isoformat()
            }
            
    else:
        return {
            "success": False,
            "message": f"지원하지 않는 플랫폼: {platform}",
            "stores": [],
            "platform": platform,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # 기본 포트는 8001, 환경변수로 변경 가능
    port = int(os.getenv("BACKEND_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)