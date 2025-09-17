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

# Import existing APIs
from simple_baemin_api import app as baemin_app

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

# 기존 baemin_app의 모든 라우트를 마운트
app.mount("/api", baemin_app)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main_server:app", host="0.0.0.0", port=port, reload=False)