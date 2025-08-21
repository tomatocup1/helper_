"""
배민 크롤링 API 서버
FastAPI 기반 REST API
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.async_jobs import job_manager, task_monitor
from services.baemin import BaeminAuthService, BaeminCrawlerService
from services.shared.logger import get_logger
from services.shared.config import settings

logger = get_logger(__name__)

app = FastAPI(
    title="배민 크롤링 API",
    description="배달의민족 매장 정보 크롤링 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:4000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 모델
class CrawlRequest(BaseModel):
    platform_id: str
    platform_password: str
    user_id: str = "test-user-123"
    sync: bool = False  # 동기식/비동기식 선택
    timeout: int = 120

class CrawlResponse(BaseModel):
    success: bool
    task_id: Optional[str] = None
    stores: Optional[list] = None
    error_message: Optional[str] = None
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# API 엔드포인트
@app.post("/api/baemin/crawl", response_model=CrawlResponse)
async def crawl_baemin_stores(request: CrawlRequest):
    """
    배민 매장 크롤링 시작
    sync=True: 동기식 (결과를 바로 반환)
    sync=False: 비동기식 (task_id 반환)
    """
    try:
        logger.info(f"Crawl request for user {request.user_id}, sync={request.sync}")
        
        # 인증 서비스 초기화
        auth_service = BaeminAuthService()
        
        # 인증 정보 저장 (동기/비동기 모두 필요)
        store_result = await auth_service.store_credentials(
            request.user_id, 
            request.platform_id, 
            request.platform_password
        )
        
        if not store_result["success"]:
            return CrawlResponse(
                success=False,
                error_message=store_result["message"],
                message="인증 정보 저장 실패"
            )
        
        if request.sync:
            # 동기식 크롤링 - 직접 크롤링 실행
            crawler_service = BaeminCrawlerService(auth_service)
            
            # 크롤링 실행
            progress_data = []
            def progress_callback(data):
                progress_data.append(data)
                logger.info(f"Progress: {data}")
            
            result = await crawler_service.crawl_stores(
                user_id=request.user_id,
                progress_callback=progress_callback,
                timeout=request.timeout
            )
            
            if result["success"]:
                return CrawlResponse(
                    success=True,
                    stores=result["stores"],
                    message=f"크롤링 완료! {len(result['stores'])}개 매장 발견"
                )
            else:
                return CrawlResponse(
                    success=False,
                    error_message=result["error_message"],
                    message="크롤링 실패"
                )
        
        else:
            # 비동기식 크롤링 - Celery 작업 큐에 추가
            job_result = job_manager.start_crawling_job(
                user_id=request.user_id,
                task_options={
                    "timeout": request.timeout
                }
            )
            
            if job_result["success"]:
                return CrawlResponse(
                    success=True,
                    task_id=job_result["task_id"],
                    message="크롤링 작업이 시작되었습니다"
                )
            else:
                return CrawlResponse(
                    success=False,
                    error_message=job_result["message"],
                    message="작업 시작 실패"
                )
                
    except Exception as e:
        logger.error(f"Crawl API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/baemin/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """작업 상태 조회"""
    try:
        status_info = job_manager.get_task_status(task_id)
        
        return TaskStatusResponse(
            task_id=task_id,
            status=status_info["status"],
            progress=status_info.get("progress"),
            result=status_info.get("result"),
            error=status_info.get("error")
        )
        
    except Exception as e:
        logger.error(f"Task status API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/baemin/task/{task_id}")
async def cancel_task(task_id: str, user_id: str = "test-user-123"):
    """작업 취소"""
    try:
        result = job_manager.cancel_task(task_id, user_id)
        
        if result["success"]:
            return {"message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Cancel task API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/baemin/user/{user_id}/stores")
async def get_user_stores(user_id: str):
    """사용자의 등록된 매장 목록 조회"""
    try:
        auth_service = BaeminAuthService()
        crawler_service = BaeminCrawlerService(auth_service)
        
        result = await crawler_service.get_user_stores(user_id)
        return result
        
    except Exception as e:
        logger.error(f"Get user stores API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/health")
async def system_health():
    """시스템 건강성 체크"""
    try:
        health_info = task_monitor.get_system_health()
        worker_stats = task_monitor.get_worker_stats()
        queue_stats = task_monitor.get_queue_stats()
        
        return {
            "health": health_info,
            "workers": worker_stats,
            "queues": queue_stats,
            "timestamp": health_info.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"Health check API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/monitor")
async def system_monitor():
    """시스템 모니터링 정보"""
    try:
        return {
            "workers": task_monitor.get_worker_stats(),
            "queues": task_monitor.get_queue_stats(),
            "tasks": task_monitor.get_task_stats(),
            "failures": task_monitor.get_recent_failures(limit=5)
        }
        
    except Exception as e:
        logger.error(f"Monitor API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """API 루트"""
    return {
        "message": "배민 크롤링 API 서버",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )