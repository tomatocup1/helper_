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

# Add core directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / 'core'))

app = FastAPI(title="Store Helper Backend API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:4000"],
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