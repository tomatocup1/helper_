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
    brandVoice: Optional[str] = ""
    greetingTemplate: Optional[str] = ""
    closingTemplate: Optional[str] = ""
    seoKeywords: List[str] = []
    autoApprovalDelayHours: int = 48
    operationType: Optional[str] = "both"

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
    allow_origins=["*"],  # 모든 도메인 허용 (프로덕션에서는 특정 도메인만 지정 권장)
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
    """모든 플랫폼 스토어 목록 조회"""
    try:
        response = supabase.table('platform_stores').select("*").execute()
        return {"success": True, "stores": response.data}
    except Exception as e:
        print(f"Error fetching stores: {e}")
        return {"success": False, "stores": [], "error": str(e)}

@app.get("/api/user-stores/{user_id}")
async def get_user_stores(user_id: str):
    """특정 사용자의 스토어 목록 조회"""
    try:
        # platform_stores 테이블에서 user_id로 조회
        response = supabase.table('platform_stores').select("*").eq('user_id', user_id).execute()
        return {"success": True, "stores": response.data}
    except Exception as e:
        print(f"Error fetching user stores: {e}")
        return {"success": False, "stores": [], "error": str(e)}

@app.post("/api/stores")
async def create_store(store_data: dict):
    """새 플랫폼 스토어 생성"""
    try:
        response = supabase.table('platform_stores').insert(store_data).execute()
        return {"success": True, "store": response.data[0] if response.data else None}
    except Exception as e:
        print(f"Error creating store: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/platform-stores/{platform}")
async def get_platform_stores(platform: str):
    """특정 플랫폼의 스토어 목록 조회"""
    try:
        response = supabase.table('platform_stores').select("*").eq('platform', platform).execute()
        return {"success": True, "stores": response.data}
    except Exception as e:
        print(f"Error fetching {platform} stores: {e}")
        return {"success": False, "stores": [], "error": str(e)}

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
@app.get("/api/reply-settings/{store_id}")
async def get_reply_settings(store_id: str):
    """매장 답글 설정 조회 (platform_stores 테이블 사용)"""
    try:
        print(f"[BACKEND DEBUG] 설정 조회 요청: store_id={store_id}")

        # platform_stores 테이블에서 store_id로 조회
        response = supabase.table('platform_stores').select("*").eq('id', store_id).execute()
        print(f"[BACKEND DEBUG] 조회 결과: {response}")

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
                    "autoApprovalDelayHours": settings.get("auto_approval_delay_hours", 48),
                    "operationType": settings.get("operation_type", "both")
                }
            }
        else:
            print(f"[BACKEND DEBUG] 매장을 찾을 수 없음: {store_id}")
            return {
                "success": False,
                "error": f"Store not found: {store_id}"
            }
    except Exception as e:
        print(f"[BACKEND DEBUG] 설정 조회 오류: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/reply-settings/{store_id}")
async def update_reply_settings(store_id: str, settings: ReplySettings):
    """매장 답글 설정 업데이트 (platform_stores 테이블 사용)"""
    try:
        print(f"[BACKEND DEBUG] 설정 저장 요청: store_id={store_id}")
        print(f"[BACKEND DEBUG] 받은 설정: {settings}")

        # platform_stores 테이블 형식으로 변환
        db_settings = {
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

        print(f"[BACKEND DEBUG] DB 설정 변환: {db_settings}")

        # platform_stores 테이블에서 매장 설정 업데이트
        response = supabase.table('platform_stores').update(db_settings).eq('id', store_id).execute()
        print(f"[BACKEND DEBUG] 업데이트 결과: {response}")

        if response.data and len(response.data) > 0:
            return {
                "success": True,
                "message": "Settings updated successfully",
                "updated_store": response.data[0]
            }
        else:
            return {
                "success": False,
                "error": "Store not found or update failed"
            }

    except Exception as e:
        print(f"[BACKEND DEBUG] 전체 오류: {e}")
        print(f"[BACKEND DEBUG] 오류 타입: {type(e)}")
        return {"success": False, "error": str(e)}

# 리뷰 관련 엔드포인트
@app.get("/api/v1/reviews")
async def get_reviews(limit: int = 500, user_id: str = None, platform: str = None):
    """리뷰 목록 조회"""
    try:
        all_reviews = []

        # 각 플랫폼 테이블에서 리뷰 조회
        platforms = ['naver', 'baemin', 'coupangeats', 'yogiyo']

        for plat in platforms:
            if platform and platform != plat:
                continue

            table_name = f'reviews_{plat}'

            if user_id:
                # 먼저 해당 사용자의 platform_stores 조회
                stores_response = supabase.table('platform_stores').select('id').eq('user_id', user_id).eq('platform', plat).execute()

                if stores_response.data:
                    store_ids = [store['id'] for store in stores_response.data]

                    # 각 스토어의 리뷰 조회
                    for store_id in store_ids:
                        reviews_response = supabase.table(table_name).select('*').eq('platform_store_id', store_id).limit(limit).execute()

                        if reviews_response.data:
                            for review in reviews_response.data:
                                review['platform'] = plat
                                all_reviews.append(review)
            else:
                # 전체 리뷰 조회
                reviews_response = supabase.table(table_name).select('*').limit(limit).execute()

                if reviews_response.data:
                    for review in reviews_response.data:
                        review['platform'] = plat
                        all_reviews.append(review)

        # 날짜순 정렬
        all_reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return {
            "success": True,
            "reviews": all_reviews[:limit],
            "total": len(all_reviews)
        }
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        return {"success": False, "reviews": [], "error": str(e)}

@app.get("/api/dashboard/stats/{user_id}")
async def get_dashboard_stats(user_id: str):
    """대시보드 통계 조회"""
    try:
        # 사용자의 스토어 조회
        stores_response = supabase.table('platform_stores').select('*').eq('user_id', user_id).execute()
        stores = stores_response.data or []

        # 각 플랫폼별 리뷰 수 계산
        total_reviews = 0
        pending_replies = 0
        avg_rating = 0
        ratings_sum = 0
        ratings_count = 0

        for store in stores:
            platform = store['platform']
            store_id = store['id']
            table_name = f'reviews_{platform}'

            # 리뷰 조회
            reviews_response = supabase.table(table_name).select('*').eq('platform_store_id', store_id).execute()

            if reviews_response.data:
                total_reviews += len(reviews_response.data)

                for review in reviews_response.data:
                    # 답글 대기 중인 리뷰 계산
                    if not review.get('owner_reply'):
                        pending_replies += 1

                    # 평점 계산 (네이버는 평점이 없을 수 있음)
                    if review.get('rating'):
                        ratings_sum += review['rating']
                        ratings_count += 1

        # 평균 평점 계산
        if ratings_count > 0:
            avg_rating = round(ratings_sum / ratings_count, 1)

        return {
            "success": True,
            "stats": {
                "totalStores": len(stores),
                "totalReviews": total_reviews,
                "pendingReplies": pending_replies,
                "avgRating": avg_rating,
                "recentActivity": {
                    "today": 0,  # TODO: 실제 계산 필요
                    "week": 0,
                    "month": total_reviews
                }
            }
        }
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        return {"success": False, "stats": None, "error": str(e)}

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