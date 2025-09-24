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
    brandVoice: Optional[str] = None
    greetingTemplate: Optional[str] = None
    closingTemplate: Optional[str] = None
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
    allow_origins=[
        "https://helper-2-6f1fjj449-tomatocup1s-projects.vercel.app",
        "https://helper-2-ofwvbckme-tomatocup1s-projects.vercel.app",
        "https://*.vercel.app",
        "http://localhost:3000",
        "http://localhost:4000",
        "*"  # 모든 도메인 허용 (개발용)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
                    "autoApprovalDelayHours": settings.get("negative_review_delay_hours", 48),
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

        # platform_stores 테이블 형식으로 변환 (실제 스키마에 맞춤)
        db_settings = {
            "auto_reply_enabled": settings.autoReplyEnabled,
            "reply_tone": settings.replyTone,
            "min_reply_length": settings.minReplyLength,
            "max_reply_length": settings.maxReplyLength,
            "brand_voice": settings.brandVoice or "",
            "greeting_template": settings.greetingTemplate or "",
            "closing_template": settings.closingTemplate or "",
            "seo_keywords": settings.seoKeywords,
            "operation_type": settings.operationType,
            "negative_review_delay_hours": settings.autoApprovalDelayHours  # 스키마의 실제 컬럼명
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

@app.get("/api/dashboard/stats/")
async def get_dashboard_stats_default():
    """기본 테스트 대시보드 (user_id 없는 경우)"""
    # 테스트용 기본 사용자 ID로 리다이렉트
    return await get_dashboard_stats("10447e32-328a-4f83-94b4-bb824ced5c75")

@app.get("/api/dashboard/stats/{user_id}")
async def get_dashboard_stats(user_id: str):
    """대시보드 통계 조회"""
    try:
        from datetime import datetime, timedelta

        # 사용자의 스토어 조회
        stores_response = supabase.table('platform_stores').select('*').eq('user_id', user_id).execute()
        stores = stores_response.data or []

        print(f"[DEBUG] Found {len(stores)} stores for user {user_id}")
        if len(stores) == 0:
            print(f"[DEBUG] No stores found for user {user_id}, returning empty dashboard")

        # 각 플랫폼별 리뷰 수 계산
        total_reviews = 0
        pending_replies = 0
        avg_rating = 0
        ratings_sum = 0
        ratings_count = 0
        new_reviews_today = 0
        recent_reviews = []
        active_stores = 0

        # 오늘 날짜 계산 (한국 시간 기준)
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        for store in stores:
            platform = store['platform']
            store_id = store['id']
            store_name = store.get('store_name', '알 수 없는 매장')
            table_name = f'reviews_{platform}'

            # 자동 답글이 활성화된 스토어 카운트
            if store.get('auto_reply_enabled', False):
                active_stores += 1

            try:
                # 리뷰 조회 (최근 리뷰 포함)
                reviews_response = supabase.table(table_name).select('*').eq('platform_store_id', store_id).order('created_at', desc=True).limit(50).execute()

                if reviews_response.data:
                    total_reviews += len(reviews_response.data)

                    for review in reviews_response.data:
                        # 답글 대기 중인 리뷰 계산
                        has_reply = review.get('owner_reply') or review.get('reply_text')
                        if not has_reply:
                            pending_replies += 1

                        # 평점 계산 (네이버는 평점이 없을 수 있음)
                        rating = review.get('rating', 0)
                        if rating and rating > 0:
                            ratings_sum += rating
                            ratings_count += 1

                        # 오늘 리뷰 수 계산
                        review_date_str = review.get('created_at', '')
                        if review_date_str:
                            try:
                                review_date = datetime.fromisoformat(review_date_str.replace('Z', '+00:00')).date()
                                if review_date == today:
                                    new_reviews_today += 1
                            except:
                                pass

                        # 최근 리뷰 추가 (최대 10개)
                        if len(recent_reviews) < 10:
                            # 프론트엔드 호환 영어 형식으로 변경
                            sentiment = 'positive' if rating >= 4 else 'negative' if rating <= 2 else 'neutral'
                            reply_status = 'replied' if has_reply else 'pending'

                            recent_reviews.append({
                                "id": review.get('id', ''),
                                "platform": platform,
                                "store_name": store_name,
                                "reviewer_name": review.get('reviewer_name', '익명'),
                                "rating": rating,
                                "review_text": review.get('review_text', '')[:100] + ('...' if len(review.get('review_text', '')) > 100 else ''),
                                "sentiment": sentiment,
                                "reply_status": reply_status,
                                "review_date": review_date_str
                            })
            except Exception as store_error:
                print(f"Error processing store {store_id}: {store_error}")
                continue

        # 평균 평점 계산
        if ratings_count > 0:
            avg_rating = round(ratings_sum / ratings_count, 1)

        # 답글률 계산
        reply_rate = 0
        if total_reviews > 0:
            replied_reviews = total_reviews - pending_replies
            reply_rate = round((replied_reviews / total_reviews) * 100, 1)

        # 알림 생성
        alerts = []
        if len(stores) == 0:
            alerts.append({
                "type": "info",
                "message": "등록된 매장이 없습니다. 첫 번째 매장을 등록해보세요!",
                "action": "매장 등록하기"
            })
        else:
            if pending_replies > 5:
                alerts.append({
                    "type": "warning",
                    "message": f"{pending_replies}개의 답글 대기 중인 리뷰가 있습니다.",
                    "action": "답글 작성하기"
                })

            if avg_rating > 0 and avg_rating < 3.0:
                alerts.append({
                    "type": "alert",
                    "message": f"평균 평점이 {avg_rating}점으로 낮습니다.",
                    "action": "리뷰 관리하기"
                })

            if new_reviews_today > 0:
                alerts.append({
                    "type": "info",
                    "message": f"오늘 새로운 리뷰 {new_reviews_today}개가 등록되었습니다.",
                    "action": "리뷰 확인하기"
                })

        return {
            "success": True,
            "data": {
                "overview": {
                    "total_stores": len(stores),
                    "active_stores": active_stores,
                    "total_reviews": total_reviews,
                    "average_rating": avg_rating,
                    "reply_rate": reply_rate,
                    "new_reviews_today": new_reviews_today,
                    "pending_replies": pending_replies
                },
                "recent_reviews": recent_reviews,
                "alerts": alerts
            }
        }
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        return {"success": False, "data": None, "error": str(e)}

@app.get("/api/debug/stores")
async def debug_stores():
    """디버그: 모든 매장 정보 조회"""
    try:
        response = supabase.table('platform_stores').select('id, user_id, store_name, platform').limit(10).execute()
        return {"success": True, "stores": response.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/dashboard/store-stats/{user_id}/{store_id}")
async def get_store_dashboard_stats(user_id: str, store_id: str):
    """특정 매장의 대시보드 통계 조회"""
    try:
        from datetime import datetime, timedelta

        # 특정 스토어 조회 (보안을 위해 user_id 확인)
        store_response = supabase.table('platform_stores').select('*').eq('id', store_id).eq('user_id', user_id).execute()

        if not store_response.data:
            return {"success": False, "data": None, "error": "Store not found or access denied"}

        store = store_response.data[0]
        platform = store['platform']
        store_name = store.get('store_name', '알 수 없는 매장')
        table_name = f'reviews_{platform}'

        # 변수 초기화
        total_reviews = 0
        pending_replies = 0
        avg_rating = 0
        ratings_sum = 0
        ratings_count = 0
        new_reviews_today = 0
        recent_reviews = []

        # 오늘 날짜 계산
        today = datetime.now().date()

        try:
            # 해당 매장의 리뷰 조회
            reviews_response = supabase.table(table_name).select('*').eq('platform_store_id', store_id).order('created_at', desc=True).limit(50).execute()

            if reviews_response.data:
                total_reviews = len(reviews_response.data)

                for review in reviews_response.data:
                    # 답글 대기 중인 리뷰 계산
                    has_reply = review.get('owner_reply') or review.get('reply_text')
                    if not has_reply:
                        pending_replies += 1

                    # 평점 계산
                    rating = review.get('rating', 0)
                    if rating and rating > 0:
                        ratings_sum += rating
                        ratings_count += 1

                    # 오늘 리뷰 수 계산
                    review_date_str = review.get('created_at', '')
                    if review_date_str:
                        try:
                            review_date = datetime.fromisoformat(review_date_str.replace('Z', '+00:00')).date()
                            if review_date == today:
                                new_reviews_today += 1
                        except:
                            pass

                    # 최근 리뷰 추가 (최대 10개)
                    if len(recent_reviews) < 10:
                        sentiment = 'positive' if rating >= 4 else 'negative' if rating <= 2 else 'neutral'
                        reply_status = 'replied' if has_reply else 'pending'

                        recent_reviews.append({
                            "id": review.get('id', ''),
                            "platform": platform,
                            "store_name": store_name,
                            "reviewer_name": review.get('reviewer_name', '익명'),
                            "rating": rating,
                            "review_text": review.get('review_text', '')[:100] + ('...' if len(review.get('review_text', '')) > 100 else ''),
                            "sentiment": sentiment,
                            "reply_status": reply_status,
                            "review_date": review_date_str
                        })

        except Exception as review_error:
            print(f"Error processing reviews for store {store_id}: {review_error}")

        # 평균 평점 계산
        if ratings_count > 0:
            avg_rating = round(ratings_sum / ratings_count, 1)

        # 답글률 계산
        reply_rate = 0
        if total_reviews > 0:
            replied_reviews = total_reviews - pending_replies
            reply_rate = round((replied_reviews / total_reviews) * 100, 1)

        # 매장별 알림 생성
        alerts = []
        if pending_replies > 3:
            alerts.append({
                "type": "warning",
                "message": f"{store_name}에서 {pending_replies}개의 답글 대기 중입니다.",
                "action": "답글 작성하기"
            })

        if avg_rating > 0 and avg_rating < 3.0:
            alerts.append({
                "type": "alert",
                "message": f"{store_name}의 평균 평점이 {avg_rating}점으로 낮습니다.",
                "action": "리뷰 관리하기"
            })

        if new_reviews_today > 0:
            alerts.append({
                "type": "info",
                "message": f"{store_name}에 오늘 새로운 리뷰 {new_reviews_today}개가 등록되었습니다.",
                "action": "리뷰 확인하기"
            })

        return {
            "success": True,
            "data": {
                "overview": {
                    "total_stores": 1,  # 단일 매장
                    "active_stores": 1 if store.get('auto_reply_enabled', False) else 0,
                    "total_reviews": total_reviews,
                    "average_rating": avg_rating,
                    "reply_rate": reply_rate,
                    "new_reviews_today": new_reviews_today,
                    "pending_replies": pending_replies,
                    "store_info": {
                        "name": store_name,
                        "platform": platform,
                        "auto_reply_enabled": store.get('auto_reply_enabled', False)
                    }
                },
                "recent_reviews": recent_reviews,
                "alerts": alerts
            }
        }

    except Exception as e:
        print(f"Error fetching store dashboard stats: {e}")
        return {"success": False, "data": None, "error": str(e)}

# 플랫폼 연결 엔드포인트
@app.post("/api/v1/platform/connect")
async def connect_platform(request_data: dict):
    """플랫폼 연결 엔드포인트"""
    try:
        import asyncio
        from datetime import datetime

        platform = request_data.get('platform')
        credentials = request_data.get('credentials', {})

        print(f"[API] {platform} 연결 요청 받음: {credentials.get('username', 'N/A')}")

        if platform == 'coupangeats':
            try:
                from services.coupangeats.simple_crawler import CoupangEatsCrawler

                print(f"[DEBUG] CoupangEats real crawling for {credentials.get('username', 'N/A')}")

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
            except Exception as e:
                print(f"[ERROR] CoupangEats error: {e}")
                return {
                    "success": False,
                    "message": f"CoupangEats 오류: {str(e)}",
                    "stores": [],
                    "platform": platform,
                    "timestamp": datetime.now().isoformat()
                }

        elif platform == 'naver':
            try:
                # 네이버는 현재 간단한 응답만 반환
                print(f"[DEBUG] Naver platform not fully implemented yet")
                return {
                    "success": False,
                    "message": "네이버 플레이스 연동은 준비 중입니다",
                    "stores": [],
                    "platform": platform,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                print(f"[ERROR] Naver error: {e}")
                return {
                    "success": False,
                    "message": f"네이버 오류: {str(e)}",
                    "stores": [],
                    "platform": platform,
                    "timestamp": datetime.now().isoformat()
                }

        elif platform == 'baemin':
            try:
                # 임시로 Mock 데이터 반환 (배민 로그인 페이지 변경으로 인한 문제)
                print(f"[DEBUG] Baemin mock data (login page changed)")

                mock_stores = [
                    {
                        "store_name": "배민 테스트 매장 1",
                        "platform_store_id": "baemin-test-001",
                        "platform": "baemin",
                        "status": "active"
                    },
                    {
                        "store_name": "배민 테스트 매장 2",
                        "platform_store_id": "baemin-test-002",
                        "platform": "baemin",
                        "status": "active"
                    }
                ]

                return {
                    "success": True,
                    "message": "임시 Mock 데이터입니다 (배민 로그인 페이지 변경으로 인해)",
                    "stores": mock_stores,
                    "platform": platform,
                    "timestamp": datetime.now().isoformat()
                }

                # 실제 크롤러 코드 (현재 비활성화)
                # from services.baemin.simple_crawler import BaeminCrawler
                # crawler = BaeminCrawler()
                # success, stores, message = await crawler.get_stores_async(
                #     credentials.get('username', ''),
                #     credentials.get('password', '')
                # )
            except Exception as e:
                print(f"[ERROR] Baemin error: {e}")
                return {
                    "success": False,
                    "message": f"Baemin 오류: {str(e)}",
                    "stores": [],
                    "platform": platform,
                    "timestamp": datetime.now().isoformat()
                }

        elif platform == 'yogiyo':
            try:
                from services.yogiyo.simple_crawler import YogiyoCrawler

                print(f"[DEBUG] Yogiyo real crawling for {credentials.get('username', 'N/A')}")

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
            except Exception as e:
                print(f"[ERROR] Yogiyo error: {e}")
                return {
                    "success": False,
                    "message": f"Yogiyo 오류: {str(e)}",
                    "stores": [],
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

    except Exception as e:
        print(f"[ERROR] Platform connect general error: {e}")
        return {
            "success": False,
            "message": f"서버 오류: {str(e)}",
            "stores": [],
            "platform": request_data.get('platform', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # 기본 포트는 8001, 환경변수로 변경 가능
    port = int(os.getenv("BACKEND_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)