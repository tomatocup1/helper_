# Render용 Python 백엔드 Dockerfile
FROM python:3.11-slim

# 시스템 업데이트 및 필수 패키지 설치
# Playwright Chrome 실행에 필요한 최소 패키지만 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치
RUN playwright install chromium
RUN playwright install-deps chromium

# 앱 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUTF8=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 포트 설정
EXPOSE 8001

# 서버 시작
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]