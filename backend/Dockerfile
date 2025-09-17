# =====================================
# 프로덕션용 Python Backend Dockerfile
# Playwright 지원 + 한글 폰트 + 최적화
# =====================================

# Stage 1: Python 베이스 이미지 (Playwright 지원)
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy AS base

LABEL maintainer="storehelper-team"
LABEL version="1.0"

# 환경변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# 시스템 의존성 및 한글 폰트 설치
RUN apt-get update && apt-get install -y \
    fonts-nanum \
    fonts-nanum-coding \
    fonts-nanum-extra \
    language-pack-ko \
    locales \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 한국어 로케일 설정
RUN locale-gen ko_KR.UTF-8
ENV LANG=ko_KR.UTF-8
ENV LANGUAGE=ko_KR:ko
ENV LC_ALL=ko_KR.UTF-8

# 작업 디렉토리 설정
WORKDIR /app

# Stage 2: 프로덕션 런타임 (단순화된 버전)
FROM base AS production

# Python 의존성 파일 복사
COPY requirements.txt .

# pip 업그레이드 및 의존성 설치
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치
RUN playwright install chromium
RUN playwright install-deps chromium

# 보안을 위한 non-root 사용자 생성
RUN groupadd --gid 1001 appgroup
RUN useradd --uid 1001 --gid 1001 --create-home appuser

# 작업 디렉토리 설정 및 권한 설정
WORKDIR /app

# 애플리케이션 코드 복사
COPY --chown=appuser:appgroup . .

# 로그 디렉토리 생성
RUN mkdir -p /app/logs && chown -R appuser:appgroup /app/logs

# 브라우저 프로필 디렉토리 생성
RUN mkdir -p /app/core/logs/browser_profiles && chown -R appuser:appgroup /app/core/logs

# 사용자 전환
USER appuser

# 포트 노출
EXPOSE 8001

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# 애플리케이션 시작 (Gunicorn 사용)
CMD ["gunicorn", "main_server:app", "--bind", "0.0.0.0:8001", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "120", "--keep-alive", "2"]