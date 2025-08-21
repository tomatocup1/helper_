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

if __name__ == "__main__":
    # 기본 포트는 8001, 환경변수로 변경 가능
    port = int(os.getenv("BACKEND_PORT", 8001))
    print(f"[서버] http://localhost:{port} 에서 시작됩니다")
    print("[지원 플랫폼] 배달의민족, 쿠팡이츠, 요기요")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)