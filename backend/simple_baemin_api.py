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
async def get_reviews(platform: str = None, store_id: str = None, user_id: str = None, limit: int = 100, offset: int = 0):
    """리뷰 조회 엔드포인트"""
    try:
        from supabase import create_client
        import os
        
        # Supabase 클라이언트 생성 (Service Role 키 사용)
        supabase_url = "https://efcdjsrumdrhmpingglp.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmY2Rqc3J1bWRyaG1waW5nZ2xwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTU2Mzc0MiwiZXhwIjoyMDcxMTM5NzQyfQ.grPU1SM6Y7rYwxcAf8f_txT0h6_DmRl4G0s-cyWOGrI"
        
        supabase = create_client(supabase_url, supabase_key)
        
        # 플랫폼별 테이블 이름 매핑
        table_mapping = {
            "naver": "reviews_naver",
            "yogiyo": "reviews_yogiyo", 
            "coupangeats": "reviews_coupangeats",
            "baemin": "reviews_baemin"
        }
        
        all_reviews = []
        
        
        # 사용자 매장 목록 조회 (user_id가 제공된 경우)
        user_store_ids = []
        if user_id:
            try:
                stores_result = supabase.from_('platform_stores').select('id').eq('user_id', user_id).eq('is_active', True).execute()
                if stores_result.data:
                    user_store_ids = [store['id'] for store in stores_result.data]
                else:
                    return {
                        "success": True,
                        "message": "사용자 매장 없음",
                        "reviews": [],
                        "count": 0,
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                pass
        
        # 특정 플랫폼만 조회
        if platform and platform in table_mapping:
            table_name = table_mapping[platform]
            query = supabase.from_(table_name).select('*')
            
            if store_id:
                query = query.eq('platform_store_id', store_id)
            # elif user_store_ids:  # 사용자 매장 필터 적용
            #     query = query.in_('platform_store_id', user_store_ids)
            
            query = query.order('review_date', desc=True).limit(limit)
            result = query.execute()
            
            if result.data:
                for review in result.data:
                    review['platform'] = platform
                all_reviews.extend(result.data)
        
        # 모든 플랫폼에서 조회 (간소화)
        else:
            print("[DEBUG] 전체 플랫폼 조회 시작")
            # 배민 직접 테스트
            print("[DEBUG] 배민 직접 조회 시작")
            try:
                baemin_result = supabase.from_('reviews_baemin').select('*').limit(10).execute()
                print(f"[DEBUG] 배민 직접 결과: {len(baemin_result.data) if baemin_result.data else 0}개")
                if baemin_result.data:
                    for review in baemin_result.data:
                        review['platform'] = 'baemin'
                    all_reviews.extend(baemin_result.data)
            except Exception as e:
                print(f"[DEBUG] 배민 직접 조회 실패: {e}")
            
            # 요기요 직접 테스트  
            print("[DEBUG] 요기요 직접 조회 시작")
            try:
                yogiyo_result = supabase.from_('reviews_yogiyo').select('*').limit(10).execute()
                print(f"[DEBUG] 요기요 직접 결과: {len(yogiyo_result.data) if yogiyo_result.data else 0}개")
                if yogiyo_result.data:
                    for review in yogiyo_result.data:
                        review['platform'] = 'yogiyo'
                    all_reviews.extend(yogiyo_result.data)
            except Exception as e:
                print(f"[DEBUG] 요기요 직접 조회 실패: {e}")
            
            # 기존 네이버 쿠팡 조회 유지
            for platform_name, table_name in table_mapping.items():
                if platform_name in ['baemin', 'yogiyo']:
                    continue  # 이미 직접 조회했으므로 스킵
                    
                try:
                    query = supabase.from_(table_name).select('*')
                    if store_id:
                        query = query.eq('platform_store_id', store_id)
                    query = query.order('review_date', desc=True).limit(limit)
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

# 대시보드 통계 API
@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    """대시보드 통계 데이터 조회"""
    try:
        from supabase import create_client, Client
        import os
        from datetime import datetime, timedelta
        
        # Supabase 연결
        url = "https://efcdjsrumdrhmpingglp.supabase.co"
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmY2Rqc3J1bWRyaG1waW5nZ2xwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1NjM3NDIsImV4cCI6MjA3MTEzOTc0Mn0.dloKe37YsQuV6pBw_S7VjINi-lGmwCXsDdOPwTI4Ncg"
        supabase: Client = create_client(url, key)
        
        # 오늘과 어제 날짜
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # 1. 매장 통계
        stores_response = supabase.table('platform_stores').select('*').execute()
        total_stores = len(stores_response.data) if stores_response.data else 0
        active_stores = len([s for s in (stores_response.data or []) if s.get('is_active', True)])
        
        # 2. 리뷰 통계 (모든 플랫폼)
        all_reviews = []
        review_tables = ['reviews_naver', 'reviews_baemin', 'reviews_yogiyo', 'reviews_coupangeats']
        
        total_reviews = 0
        total_rating_sum = 0
        reviews_with_rating = 0
        new_reviews_today = 0
        pending_replies = 0
        
        for table in review_tables:
            try:
                response = supabase.table(table).select('*').execute()
                if response.data:
                    table_reviews = response.data
                    total_reviews += len(table_reviews)
                    
                    for review in table_reviews:
                        # 평점 통계
                        rating = review.get('rating')
                        if rating and isinstance(rating, (int, float)) and 1 <= rating <= 5:
                            total_rating_sum += rating
                            reviews_with_rating += 1
                        
                        # 오늘 새 리뷰 카운트
                        review_date = review.get('review_date')
                        if review_date:
                            try:
                                review_dt = datetime.fromisoformat(review_date.replace('Z', '+00:00'))
                                if review_dt.date() == today:
                                    new_reviews_today += 1
                            except:
                                pass
                        
                        # 답글 대기 중인 리뷰
                        reply_status = review.get('reply_status', 'draft')
                        if reply_status in ['draft', 'pending_approval']:
                            pending_replies += 1
                            
            except Exception as e:
                print(f"Error fetching {table}: {e}")
                continue
        
        # 평균 평점 계산
        average_rating = round(total_rating_sum / reviews_with_rating, 1) if reviews_with_rating > 0 else 0.0
        
        # 답글 완료율 계산
        replied_reviews = total_reviews - pending_replies
        reply_rate = round((replied_reviews / total_reviews) * 100, 1) if total_reviews > 0 else 0.0
        
        # 3. 최근 리뷰 5개 (모든 플랫폼에서)
        recent_reviews = []
        for table in review_tables:
            try:
                # 플랫폼 이름 추출
                platform = table.replace('reviews_', '')
                
                response = supabase.table(table).select('*, platform_stores(store_name)').order('review_date', desc=True).limit(10).execute()
                if response.data:
                    for review in response.data:
                        recent_reviews.append({
                            'id': review.get('id'),
                            'platform': platform,
                            'store_name': review.get('platform_stores', {}).get('store_name', 'Unknown Store'),
                            'reviewer_name': review.get('reviewer_name', 'Anonymous'),
                            'rating': review.get('rating', 0),
                            'review_text': review.get('review_text', '')[:100] + '...' if len(review.get('review_text', '')) > 100 else review.get('review_text', ''),
                            'sentiment': review.get('sentiment', 'neutral'),
                            'reply_status': review.get('reply_status', 'draft'),
                            'review_date': review.get('review_date')
                        })
            except Exception as e:
                print(f"Error fetching recent reviews from {table}: {e}")
                continue
        
        # 날짜순 정렬 후 5개만 선택
        recent_reviews.sort(key=lambda x: x.get('review_date', ''), reverse=True)
        recent_reviews = recent_reviews[:5]
        
        # 4. 알림 생성 (부정적 리뷰, 증가 트렌드 등)
        alerts = []
        
        # 부정적 리뷰 알림
        negative_reviews = [r for r in recent_reviews if r.get('rating', 5) <= 2]
        if negative_reviews:
            alerts.append({
                'type': 'warning',
                'message': f'{len(negative_reviews)}개의 부정적 리뷰가 있습니다.',
                'action': '확인 필요'
            })
        
        # 답글 대기 알림
        if pending_replies > 0:
            alerts.append({
                'type': 'info',
                'message': f'{pending_replies}개의 리뷰가 답글을 기다리고 있습니다.',
                'action': '답글 작성하기'
            })
        
        return {
            "success": True,
            "data": {
                "overview": {
                    "total_stores": total_stores,
                    "active_stores": active_stores,
                    "total_reviews": total_reviews,
                    "average_rating": average_rating,
                    "reply_rate": reply_rate,
                    "new_reviews_today": new_reviews_today,
                    "pending_replies": pending_replies
                },
                "recent_reviews": recent_reviews,
                "alerts": alerts
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Dashboard stats error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "overview": {
                    "total_stores": 0,
                    "active_stores": 0,
                    "total_reviews": 0,
                    "average_rating": 0.0,
                    "reply_rate": 0.0,
                    "new_reviews_today": 0,
                    "pending_replies": 0
                },
                "recent_reviews": [],
                "alerts": []
            }
        }

if __name__ == "__main__":
    # 기본 포트는 8001, 환경변수로 변경 가능
    port = int(os.getenv("BACKEND_PORT", 8001))
    print(f"[서버] http://localhost:{port} 에서 시작됩니다")
    print("[지원 플랫폼] 배달의민족, 쿠팡이츠, 요기요")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)