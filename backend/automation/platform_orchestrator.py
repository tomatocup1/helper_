#!/usr/bin/env python3
"""
플랫폼별 워크플로우 실행 관리자
Platform-specific Workflow Orchestrator
"""

import os
import sys
import asyncio
import subprocess
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

# 프로젝트 경로 설정
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'core'))

from automation.user_manager import UserManager, StoreInfo, UserInfo
from core.password_decrypt import decrypt_password

# 로깅 설정 (DEBUG 레벨로 변경)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """실행 결과"""
    success: bool
    message: str
    details: Dict[str, Any] = None
    execution_time: float = 0.0
    error: Optional[str] = None


class PlatformOrchestrator:
    """플랫폼별 워크플로우 실행 관리자"""

    def __init__(self):
        """초기화"""
        self.user_manager = UserManager()
        self.core_path = os.path.join(project_root, 'core')
        self.ai_reply_path = os.path.join(self.core_path, 'ai_reply')

    def _get_utf8_env(self) -> Dict[str, str]:
        """UTF-8 환경변수가 설정된 환경변수 딕셔너리 반환"""
        env = os.environ.copy()

        # UTF-8 강제 설정
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'

        # Windows 콘솔 인코딩 설정
        if os.name == 'nt':
            env['PYTHONLEGACYWINDOWSSTDIO'] = '0'

        return env

    def get_platform_scripts(self) -> Dict[str, Dict[str, str]]:
        """플랫폼별 스크립트 경로 반환"""
        return {
            'naver': {
                'crawler': os.path.join(self.core_path, 'naver_review_crawler.py'),
                'poster': os.path.join(self.core_path, 'naver_reply_poster.py')
            },
            'baemin': {
                'crawler': os.path.join(self.core_path, 'baemin_review_crawler.py'),
                'poster': os.path.join(self.core_path, 'baemin_auto_reply.py')
            },
            'yogiyo': {
                'crawler': os.path.join(self.core_path, 'yogiyo_review_crawler.py'),
                'poster': os.path.join(self.core_path, 'yogiyo_reply_poster.py')
            },
            'coupangeats': {
                'crawler': os.path.join(self.core_path, 'coupang_review_crawler.py'),
                'poster': os.path.join(self.core_path, 'run_coupang_reply_poster.py')
            }
        }

    async def run_crawler(self, platform: str, store: StoreInfo) -> ExecutionResult:
        """특정 플랫폼의 크롤러 실행"""
        start_time = datetime.now()
        scripts = self.get_platform_scripts()

        if platform not in scripts:
            return ExecutionResult(
                success=False,
                message=f"지원하지 않는 플랫폼: {platform}",
                error="UNSUPPORTED_PLATFORM"
            )

        try:
            # 암호화된 패스워드 복호화
            if store.platform_pw:
                decrypted_password = decrypt_password(store.platform_pw, platform.upper())
            else:
                logger.warning(f"[{platform}] 패스워드가 없습니다: {store.store_name}")
                return ExecutionResult(
                    success=False,
                    message=f"패스워드가 설정되지 않았습니다",
                    error="NO_PASSWORD"
                )

            # 플랫폼별 크롤러 명령어 구성
            crawler_script = scripts[platform]['crawler']
            cmd = ["python", crawler_script]

            if platform == 'naver':
                cmd.extend([
                    "--email", store.platform_id,
                    "--password", decrypted_password,
                    "--store-id", store.platform_store_id,
                    "--user-id", store.user_id,
                    "--days", "7"
                ])
            elif platform == 'baemin':
                cmd.extend([
                    "--username", store.platform_id,
                    "--password", decrypted_password,
                    "--store-id", store.platform_store_id,
                    "--user-id", store.user_id
                ])
            elif platform == 'yogiyo':
                cmd.extend([
                    "--username", store.platform_id,
                    "--password", decrypted_password,
                    "--store-id", store.platform_store_id,
                    "--days", "7",
                    "--max-scrolls", "15"
                ])
            elif platform == 'coupangeats':
                cmd.extend([
                    "--username", store.platform_id,
                    "--password", decrypted_password,
                    "--store-id", store.platform_store_id,
                    "--days", "7",
                    "--max-pages", "5"
                ])

            logger.info(f"[{platform}] 크롤링 시작: {store.store_name}")
            logger.debug(f"[{platform}] 실행 명령어: {' '.join(cmd)}")
            logger.debug(f"[{platform}] 작업 디렉토리: {self.core_path}")

            # 크롤러 파일 존재 확인
            crawler_path = os.path.join(self.core_path, os.path.basename(crawler_script))
            logger.debug(f"[{platform}] 크롤러 파일 경로: {crawler_path}")
            logger.debug(f"[{platform}] 크롤러 파일 존재: {os.path.exists(crawler_path)}")

            # 환경 확인
            logger.debug(f"[{platform}] 현재 작업 디렉토리: {os.getcwd()}")
            logger.debug(f"[{platform}] Python 실행 파일: {sys.executable}")

            # 크롤러 실행 (실시간 출력을 위해 Popen 사용)
            # 환경변수 상속하여 subprocess 실행
            import subprocess

            # Popen으로 실시간 출력 확인
            process = subprocess.Popen(
                cmd,
                cwd=self.core_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=self._get_utf8_env(),
                shell=False
            )

            # 실시간 출력 읽기
            stdout_lines = []
            stderr_lines = []

            try:
                stdout, stderr = process.communicate(timeout=300)  # 5분 타임아웃
                stdout_lines = stdout.split('\n') if stdout else []
                stderr_lines = stderr.split('\n') if stderr else []

                # 결과 객체 생성 (기존 호환성 유지)
                class Result:
                    def __init__(self, returncode, stdout, stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr

                result = Result(process.returncode, stdout, stderr)

            except subprocess.TimeoutExpired:
                process.kill()
                raise

            execution_time = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0:
                logger.info(f"[{platform}] 크롤링 완료: {store.store_name} ({execution_time:.1f}초)")

                # 상세 로그 출력 (크롤링 진행 상황 확인)
                if result.stdout.strip():
                    stdout_lines = result.stdout.strip().split('\n')

                    # 중요한 로그 라인들을 INFO 레벨로 출력
                    important_keywords = [
                        'CRAWLING_RESULT:', '[START]', '[SUCCESS]', '[ERROR]',
                        '[SCROLL]', '[TARGET]', '[SEARCH]', '미답변', '리뷰',
                        'reviews_found', 'reviews_new'
                    ]

                    for line in stdout_lines:
                        if any(keyword in line for keyword in important_keywords):
                            logger.info(f"[{platform}] {line.strip()}")

                    # 전체 STDOUT도 DEBUG 레벨로 출력
                    logger.debug(f"[{platform}] 전체 STDOUT: {result.stdout.strip()}")

                # 성공해도 stderr가 있으면 경고 출력 (팝업 관련 로그 확인용)
                if result.stderr.strip():
                    logger.warning(f"[{platform}] 크롤링 경고 로그: {result.stderr.strip()}")

                return ExecutionResult(
                    success=True,
                    message=f"크롤링 완료",
                    execution_time=execution_time,
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )
            else:
                logger.error(f"[{platform}] 크롤링 실패: {store.store_name}")
                logger.error(f"[{platform}] STDOUT: {result.stdout}")
                logger.error(f"[{platform}] STDERR: {result.stderr}")
                return ExecutionResult(
                    success=False,
                    message=f"크롤링 실패: {result.stderr[:200]}",
                    execution_time=execution_time,
                    error="CRAWLER_FAILED",
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )

        except subprocess.TimeoutExpired:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{platform}] 크롤링 타임아웃: {store.store_name}")
            return ExecutionResult(
                success=False,
                message="크롤링 타임아웃 (5분 초과)",
                execution_time=execution_time,
                error="TIMEOUT"
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{platform}] 크롤링 오류: {store.store_name} - {e}")
            return ExecutionResult(
                success=False,
                message=f"크롤링 오류: {str(e)}",
                execution_time=execution_time,
                error="EXCEPTION"
            )

    async def run_ai_reply_generation(self, user_id: str, platforms: List[str] = None) -> ExecutionResult:
        """AI 답글 생성 실행"""
        start_time = datetime.now()

        try:
            cmd = ["python", "main.py", "--batch", "--user-id", user_id]

            if platforms:
                # 특정 플랫폼만 처리하는 옵션이 있다면 추가
                pass

            logger.info(f"[AI] 답글 생성 시작: 사용자 {user_id}")

            result = subprocess.run(
                cmd,
                cwd=self.ai_reply_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10분 타임아웃 (네이버는 무한스크롤로 시간이 더 필요)
                encoding='utf-8',
                errors='replace',
                env=self._get_utf8_env()
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0:
                logger.info(f"[AI] 답글 생성 완료: 사용자 {user_id} ({execution_time:.1f}초)")
                return ExecutionResult(
                    success=True,
                    message="AI 답글 생성 완료",
                    execution_time=execution_time,
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )
            else:
                logger.error(f"[AI] 답글 생성 실패: 사용자 {user_id} - {result.stderr}")
                return ExecutionResult(
                    success=False,
                    message=f"AI 답글 생성 실패: {result.stderr[:200]}",
                    execution_time=execution_time,
                    error="AI_FAILED",
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )

        except subprocess.TimeoutExpired:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[AI] 답글 생성 타임아웃: 사용자 {user_id}")
            return ExecutionResult(
                success=False,
                message="AI 답글 생성 타임아웃 (3분 초과)",
                execution_time=execution_time,
                error="TIMEOUT"
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[AI] 답글 생성 오류: 사용자 {user_id} - {e}")
            return ExecutionResult(
                success=False,
                message=f"AI 답글 생성 오류: {str(e)}",
                execution_time=execution_time,
                error="EXCEPTION"
            )

    async def run_reply_poster(self, platform: str, store: StoreInfo) -> ExecutionResult:
        """특정 플랫폼의 답글 등록기 실행"""
        start_time = datetime.now()
        scripts = self.get_platform_scripts()

        if platform not in scripts:
            return ExecutionResult(
                success=False,
                message=f"지원하지 않는 플랫폼: {platform}",
                error="UNSUPPORTED_PLATFORM"
            )

        try:
            poster_script = scripts[platform]['poster']
            cmd = ["python", poster_script]

            if platform == 'naver':
                # 네이버: 전체 미답변 리뷰 처리 (limit 제거)
                pass
            elif platform == 'baemin':
                cmd.extend(["--store-id", store.platform_store_id])
            elif platform == 'yogiyo':
                # 요기요: 전체 미답변 리뷰 처리 (limit 제거)
                pass
            elif platform == 'coupangeats':
                cmd.extend([
                    "--store-uuid", store.id
                    # 쿠팡이츠: 전체 미답변 리뷰 처리 (limit 제거)
                ])

            logger.info(f"[{platform}] 답글 등록 시작: {store.store_name}")

            result = subprocess.run(
                cmd,
                cwd=self.core_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10분 타임아웃 (네이버는 무한스크롤로 시간이 더 필요)
                encoding='utf-8',
                errors='replace',
                env=self._get_utf8_env()
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0:
                logger.info(f"[{platform}] 답글 등록 완료: {store.store_name} ({execution_time:.1f}초)")
                return ExecutionResult(
                    success=True,
                    message="답글 등록 완료",
                    execution_time=execution_time,
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )
            else:
                logger.error(f"[{platform}] 답글 등록 실패: {store.store_name} - {result.stderr}")
                return ExecutionResult(
                    success=False,
                    message=f"답글 등록 실패: {result.stderr[:200]}",
                    execution_time=execution_time,
                    error="POSTER_FAILED",
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )

        except subprocess.TimeoutExpired:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{platform}] 답글 등록 타임아웃: {store.store_name}")
            return ExecutionResult(
                success=False,
                message="답글 등록 타임아웃 (3분 초과)",
                execution_time=execution_time,
                error="TIMEOUT"
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{platform}] 답글 등록 오류: {store.store_name} - {e}")
            return ExecutionResult(
                success=False,
                message=f"답글 등록 오류: {str(e)}",
                execution_time=execution_time,
                error="EXCEPTION"
            )

    async def run_full_workflow_for_user(self, user: UserInfo, platforms: List[str] = None) -> Dict[str, List[ExecutionResult]]:
        """사용자의 전체 워크플로우 실행 (크롤링 → AI 답글 → 답글 등록)"""
        if platforms is None:
            platforms = ['naver', 'baemin', 'yogiyo', 'coupangeats']

        results = {
            'crawling': [],
            'ai_reply': [],
            'posting': []
        }

        logger.info(f"🚀 사용자 워크플로우 시작: {user.name} ({user.email})")

        # 1단계: 플랫폼별 크롤링
        for platform in platforms:
            stores = await self.user_manager.get_user_stores(user.id, platform)

            for store in stores:
                if store.crawling_enabled:
                    result = await self.run_crawler(platform, store)
                    results['crawling'].append({
                        'platform': platform,
                        'store': store,
                        'result': result
                    })
                else:
                    logger.info(f"[{platform}] 크롤링 비활성화: {store.store_name}")

        # 2단계: AI 답글 생성
        ai_result = await self.run_ai_reply_generation(user.id, platforms)
        results['ai_reply'].append({
            'user_id': user.id,
            'result': ai_result
        })

        # 3단계: 플랫폼별 답글 등록
        for platform in platforms:
            stores = await self.user_manager.get_user_stores(user.id, platform)

            for store in stores:
                if store.auto_reply_enabled:
                    result = await self.run_reply_poster(platform, store)
                    results['posting'].append({
                        'platform': platform,
                        'store': store,
                        'result': result
                    })
                else:
                    logger.info(f"[{platform}] 자동 답글 비활성화: {store.store_name}")

        return results

    def print_workflow_summary(self, user: UserInfo, results: Dict[str, List[ExecutionResult]]):
        """워크플로우 실행 결과 요약 출력"""
        print("="*60)
        print(f"📊 {user.name} 워크플로우 실행 결과")
        print("="*60)

        # 크롤링 결과
        crawling_success = sum(1 for r in results['crawling'] if r['result'].success)
        crawling_total = len(results['crawling'])
        print(f"📥 크롤링: {crawling_success}/{crawling_total} 성공")

        # AI 답글 결과
        ai_success = sum(1 for r in results['ai_reply'] if r['result'].success)
        ai_total = len(results['ai_reply'])
        print(f"🤖 AI 답글: {ai_success}/{ai_total} 성공")

        # 답글 등록 결과
        posting_success = sum(1 for r in results['posting'] if r['result'].success)
        posting_total = len(results['posting'])
        print(f"📤 답글 등록: {posting_success}/{posting_total} 성공")

        print("-"*60)

        # 실패한 작업들 상세 출력
        for category, items in results.items():
            failed_items = [item for item in items if not item['result'].success]
            if failed_items:
                print(f"❌ {category} 실패:")
                for item in failed_items:
                    if 'store' in item:
                        print(f"   - {item['platform']}: {item['store'].store_name} - {item['result'].message}")
                    else:
                        print(f"   - 사용자 {item['user_id']}: {item['result'].message}")


# 테스트 실행
async def main():
    """테스트 실행"""
    orchestrator = PlatformOrchestrator()

    print("🚀 플랫폼 오케스트레이터 테스트")
    print("="*60)

    # 테스트용 사용자 ID
    test_user_id = "a7654c42-10ed-435f-97d8-d2c2dfeccbcb"

    user = await orchestrator.user_manager.get_user_by_id(test_user_id)
    if user:
        print(f"테스트 사용자: {user.name} ({user.email})")

        # 전체 워크플로우 실행
        results = await orchestrator.run_full_workflow_for_user(user, ['yogiyo'])
        orchestrator.print_workflow_summary(user, results)
    else:
        print(f"사용자를 찾을 수 없습니다: {test_user_id}")


if __name__ == "__main__":
    asyncio.run(main())