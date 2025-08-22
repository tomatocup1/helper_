"""
간단한 배달의민족/쿠팡이츠/요기요 API 서버
FastAPI를 사용한 REST API 서버
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path
import sys
from datetime import datetime

# Add services directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

app = FastAPI(title="Store Platform API")

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
    return {"message": "Store Platform API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/status")
async def api_status():
    return {
        "service": "Store Platform API",
        "version": "1.0.0",
        "status": "operational",
        "supported_platforms": ["baemin", "coupangeats", "yogiyo"]
    }

# 플랫폼 연결 엔드포인트
@app.post("/api/v1/platform/connect")
async def connect_platform(request_data: dict):
    """플랫폼 연결 엔드포인트"""
    import asyncio
    
    platform = request_data.get('platform')
    credentials = request_data.get('credentials', {})
    
    print(f"[API] {platform} 연결 요청 받음: {credentials.get('username', 'N/A')}")
    
    if platform == 'baemin':
        from services.baemin.simple_crawler import BaeminCrawler
        
        crawler = BaeminCrawler()
        try:
            success, stores, message = await crawler.get_stores_async(
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
            print(f"[배민] 오류: {e}")
            return {
                "success": False,
                "message": f"배민 크롤링 오류: {str(e)}",
                "stores": [],
                "platform": platform,
                "timestamp": datetime.now().isoformat()
            }
            
    elif platform == 'coupangeats':
        from services.coupangeats.simple_crawler import CoupangEatsCrawler
        
        try:
            async with CoupangEatsCrawler() as crawler:
                success, stores, message = await crawler.crawl_stores(
                    credentials.get('username', ''),
                    credentials.get('password', '')
                )
                
                return {
                    "success": success,
                    "message": message,
                    "stores": stores or [],  # stores가 None인 경우 빈 배열 반환
                    "platform": platform,
                    "timestamp": datetime.now().isoformat(),
                    "error_type": None if success else "login_failed"
                }
        except Exception as e:
            print(f"[쿠팡이츠] 크롤링 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "message": f"쿠팡이츠 크롤링 중 오류가 발생했습니다: {str(e)}",
                "stores": [],
                "platform": platform,
                "timestamp": datetime.now().isoformat(),
                "error_type": "crawler_exception"
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

# 리뷰 조회 엔드포인트
@app.get("/api/v1/reviews")
async def get_reviews(platform: str = None, store_id: str = None, limit: int = 100, offset: int = 0):
    """리뷰 조회 엔드포인트"""
    try:
        from supabase import create_client
        import os
        
        # Supabase 클라이언트 생성
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            return {
                "success": False,
                "message": "Supabase 설정이 올바르지 않습니다",
                "reviews": []
            }
        
        supabase = create_client(supabase_url, supabase_key)
        
        # 플랫폼별 테이블 이름 매핑
        table_mapping = {
            "naver": "reviews_naver",
            "yogiyo": "reviews_yogiyo", 
            "coupangeats": "reviews_coupangeats",
            "baemin": "reviews_baemin"
        }
        
        all_reviews = []
        
        # 특정 플랫폼만 조회
        if platform and platform in table_mapping:
            table_name = table_mapping[platform]
            query = supabase.from_(table_name).select('*')
            
            if store_id:
                query = query.eq('platform_store_id', store_id)
            
            query = query.order('review_date', desc=True).limit(limit)
            result = query.execute()
            
            if result.data:
                for review in result.data:
                    review['platform'] = platform
                all_reviews.extend(result.data)
        
        # 모든 플랫폼에서 조회
        else:
            for platform_name, table_name in table_mapping.items():
                try:
                    query = supabase.from_(table_name).select('*')
                    
                    if store_id:
                        query = query.eq('platform_store_id', store_id)
                    
                    query = query.order('review_date', desc=True).limit(limit // len(table_mapping))
                    result = query.execute()
                    
                    if result.data:
                        for review in result.data:
                            review['platform'] = platform_name
                        all_reviews.extend(result.data)
                        
                except Exception as e:
                    print(f"[{platform_name}] 리뷰 조회 실패: {e}")
                    continue
        
        # 날짜순 정렬
        all_reviews.sort(key=lambda x: x.get('review_date', ''), reverse=True)
        
        return {
            "success": True,
            "message": f"리뷰 조회 완료: {len(all_reviews)}개",
            "reviews": all_reviews[:limit],
            "count": len(all_reviews),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[리뷰 조회] 오류: {e}")
        return {
            "success": False,
            "message": f"리뷰 조회 중 오류: {str(e)}",
            "reviews": []
        }

# 요기요 리뷰 크롤링 엔드포인트
@app.post("/api/v1/yogiyo/crawl")
async def crawl_yogiyo_reviews(request_data: dict):
    """요기요 리뷰 크롤링 엔드포인트"""
    try:
        from core.yogiyo_review_crawler import YogiyoReviewCrawler
        import asyncio
        
        username = request_data.get('username')
        password = request_data.get('password') 
        store_id = request_data.get('store_id')
        max_scrolls = request_data.get('max_scrolls', 10)
        days = request_data.get('days', 7)
        
        if not username or not password or not store_id:
            return {
                "success": False,
                "message": "username, password, store_id가 필요합니다",
                "reviews": []
            }
        
        print(f"[API] 요기요 리뷰 크롤링 시작: {username}, 매장: {store_id}")
        
        crawler = YogiyoReviewCrawler()
        result = await crawler.crawl_reviews(
            username=username,
            password=password,
            store_id=store_id,
            max_scrolls=max_scrolls,
            days=days
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "reviews": result["reviews"],
            "saved_count": result.get("saved_count", 0),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[요기요 크롤링] 오류: {e}")
        return {
            "success": False,
            "message": f"요기요 크롤링 중 오류: {str(e)}",
            "reviews": []
        }

if __name__ == "__main__":
    # 기본 포트는 8001, 환경변수로 변경 가능
    port = int(os.getenv("BACKEND_PORT", 8001))
    print(f"[서버] http://localhost:{port} 에서 시작됩니다")
    print("[지원 플랫폼] 배달의민족, 쿠팡이츠, 요기요")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)