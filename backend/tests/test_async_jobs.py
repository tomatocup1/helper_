"""
비동기 작업 시스템 테스트
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from backend.services.async_jobs import job_manager, task_monitor
from backend.services.async_jobs.tasks import crawl_baemin_stores

class TestBaeminJobManager:
    """배민 작업 관리자 테스트"""
    
    @patch('backend.services.async_jobs.job_manager.BaeminJobManager.get_user_active_task')
    @patch('backend.services.async_jobs.tasks.crawl_baemin_stores.delay')
    def test_start_crawling_job_success(self, mock_delay, mock_active_task):
        """크롤링 작업 시작 성공 테스트"""
        # 기존 활성 작업 없음
        mock_active_task.return_value = None
        
        # Mock task result
        mock_task_result = Mock()
        mock_task_result.id = "test-task-id-123"
        mock_delay.return_value = mock_task_result
        
        # 작업 시작
        result = job_manager.start_crawling_job("test-user-123")
        
        # 검증
        assert result["success"] == True
        assert result["task_id"] == "test-task-id-123"
        assert "크롤링 작업이 시작되었습니다" in result["message"]
        mock_delay.assert_called_once()
    
    @patch('backend.services.async_jobs.job_manager.BaeminJobManager.get_user_active_task')
    def test_start_crawling_job_already_active(self, mock_active_task):
        """이미 활성 작업이 있는 경우 테스트"""
        # 기존 활성 작업 있음
        mock_active_task.return_value = {
            "task_id": "existing-task-123",
            "user_id": "test-user-123",
            "status": "PROGRESS"
        }
        
        # 작업 시작 시도
        result = job_manager.start_crawling_job("test-user-123")
        
        # 검증
        assert result["success"] == False
        assert "이미 진행 중인 크롤링 작업이 있습니다" in result["message"]
        assert "existing_task" in result
    
    @patch('backend.services.async_jobs.job_manager.AsyncResult')
    def test_get_task_status(self, mock_async_result):
        """작업 상태 조회 테스트"""
        # Mock Celery result
        mock_result = Mock()
        mock_result.status = "SUCCESS"
        mock_result.result = {"stores": [], "summary": {"valid_count": 5}}
        mock_result.successful.return_value = True
        mock_result.failed.return_value = False
        mock_async_result.return_value = mock_result
        
        # 상태 조회
        status = job_manager.get_task_status("test-task-123")
        
        # 검증
        assert status["task_id"] == "test-task-123"
        assert status["status"] == "SUCCESS"
        assert status["result"] is not None
    
    @patch('backend.services.async_jobs.job_manager.BaeminJobManager.get_task_info')
    @patch('backend.services.async_jobs.job_manager.celery_app.control.revoke')
    def test_cancel_task_success(self, mock_revoke, mock_get_task_info):
        """작업 취소 성공 테스트"""
        # 작업 정보 mock
        mock_get_task_info.return_value = {
            "task_id": "test-task-123",
            "user_id": "test-user-123"
        }
        
        # 작업 취소
        result = job_manager.cancel_task("test-task-123", "test-user-123")
        
        # 검증
        assert result["success"] == True
        assert "작업이 취소되었습니다" in result["message"]
        mock_revoke.assert_called_once_with("test-task-123", terminate=True)
    
    @patch('backend.services.async_jobs.job_manager.BaeminJobManager.get_task_info')
    def test_cancel_task_unauthorized(self, mock_get_task_info):
        """권한 없는 작업 취소 시도 테스트"""
        # 다른 사용자의 작업
        mock_get_task_info.return_value = {
            "task_id": "test-task-123",
            "user_id": "other-user-456"
        }
        
        # 작업 취소 시도
        result = job_manager.cancel_task("test-task-123", "test-user-123")
        
        # 검증
        assert result["success"] == False
        assert "권한이 없습니다" in result["message"]

class TestTaskMonitor:
    """작업 모니터링 테스트"""
    
    @patch('backend.services.async_jobs.monitor.TaskMonitor.celery_app.control.inspect')
    def test_get_worker_stats(self, mock_inspect):
        """워커 상태 조회 테스트"""
        # Mock inspect data
        mock_inspect_obj = Mock()
        mock_inspect_obj.active.return_value = {
            "worker1@hostname": [
                {"id": "task1", "name": "crawl_baemin_stores"}
            ]
        }
        mock_inspect_obj.stats.return_value = {
            "worker1@hostname": {"pool": {"max-concurrency": 2}}
        }
        mock_inspect.return_value = mock_inspect_obj
        
        # 상태 조회
        stats = task_monitor.get_worker_stats()
        
        # 검증
        assert stats["total_workers"] == 1
        assert "worker1@hostname" in stats["workers"]
        assert stats["workers"]["worker1@hostname"]["active_tasks"] == 1
    
    @patch('backend.services.async_jobs.monitor.TaskMonitor.redis_client.llen')
    def test_get_queue_stats(self, mock_llen):
        """큐 상태 조회 테스트"""
        # Mock Redis queue lengths
        mock_llen.side_effect = [5, 2, 0]  # 큐별 대기 작업 수
        
        # 상태 조회
        stats = task_monitor.get_queue_stats()
        
        # 검증
        assert "queues" in stats
        queues = stats["queues"]
        assert queues["baemin_crawler"]["pending_tasks"] == 5
        assert queues["progress_updates"]["pending_tasks"] == 2
        assert queues["default"]["pending_tasks"] == 0
    
    @patch('backend.services.async_jobs.monitor.TaskMonitor.redis_client.ping')
    @patch('backend.services.async_jobs.monitor.TaskMonitor.get_worker_stats')
    def test_get_system_health(self, mock_worker_stats, mock_redis_ping):
        """시스템 건강성 체크 테스트"""
        # Redis 정상, 워커 1개 활성
        mock_redis_ping.return_value = True
        mock_worker_stats.return_value = {
            "workers": {"worker1@hostname": {}}
        }
        
        # 건강성 체크
        health = task_monitor.get_system_health()
        
        # 검증
        assert health["overall_healthy"] == True
        assert health["redis_healthy"] == True
        assert health["workers_healthy"] == True
        assert health["worker_count"] == 1

@pytest.mark.asyncio
class TestAsyncTasks:
    """비동기 작업 테스트"""
    
    @patch('backend.services.async_jobs.tasks.BaeminCrawlerService')
    @patch('backend.services.async_jobs.tasks.BaeminAuthService')
    async def test_crawling_task_success(self, mock_auth_service, mock_crawler_service):
        """크롤링 작업 성공 테스트"""
        # Mock services
        mock_auth_instance = Mock()
        mock_auth_service.return_value = mock_auth_instance
        
        mock_crawler_instance = Mock()
        mock_crawler_service.return_value = mock_crawler_instance
        
        # Mock crawling result
        mock_crawler_instance.crawl_stores.return_value = {
            "success": True,
            "stores": [{"store_name": "테스트 매장"}],
            "summary": {"valid_count": 1}
        }
        
        # 크롤링 작업 실행 (실제로는 Celery에서 호출됨)
        from backend.services.async_jobs.tasks import _run_crawling_task
        
        def mock_progress_callback(data):
            print(f"Progress: {data}")
        
        result = await _run_crawling_task("test-user-123", mock_progress_callback)
        
        # 검증
        assert result["success"] == True
        assert len(result["stores"]) == 1
        assert result["summary"]["valid_count"] == 1

if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v"])