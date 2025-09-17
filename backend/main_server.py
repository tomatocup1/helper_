"""
통합된 Store Helper Backend API 서버
모든 플랫폼 API를 하나로 통합
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path
import sys

# Add directories to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / 'core'))

app = FastAPI(title="Store Helper Unified Backend API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:4000",
        "https://*.vercel.app",
        "*"  # 개발 중에는 모든 도메인 허용
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기본 엔드포인트들
@app.get("/")
async def root():
    return {"message": "Store Helper Unified Backend API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Import and include all routes from simple_baemin_api
try:
    from simple_baemin_api import app as baemin_app

    # baemin_app의 모든 라우트를 현재 앱에 복사
    for route in baemin_app.routes:
        app.router.routes.append(route)

    print("Successfully included all routes from simple_baemin_api")
except Exception as e:
    print(f"Error importing simple_baemin_api: {e}")

    # 기본 API 엔드포인트들 추가
    @app.get("/api/stores")
    async def get_stores():
        return {"stores": [], "message": "Backend integration in progress"}

    @app.get("/api/v1/stores")
    async def get_v1_stores():
        return {"stores": [], "message": "Backend integration in progress"}

    @app.post("/api/v1/stores")
    async def create_store(request: dict):
        return {"success": False, "message": "Backend service unavailable"}

    @app.get("/api/v1/stores/{store_id}")
    async def get_store(store_id: str):
        return {"store": None, "message": "Backend service unavailable"}

    @app.put("/api/v1/stores/{store_id}")
    async def update_store(store_id: str, request: dict):
        return {"success": False, "message": "Backend service unavailable"}

    @app.get("/api/user-stores/{user_id}")
    async def get_user_stores(user_id: str):
        return {"stores": [], "message": "Backend integration in progress"}

    @app.post("/api/v1/platform/connect")
    async def connect_platform(request: dict):
        return {"success": False, "message": "Backend service unavailable"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main_server:app", host="0.0.0.0", port=port, reload=False)