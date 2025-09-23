# Render용 Python 백엔드 Dockerfile
# Ubuntu 기반 이미지 사용 (Playwright 공식 지원)
FROM ubuntu:22.04

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul
ENV PYTHONUNBUFFERED=1

# 시스템 업데이트 및 Python 3.11 설치
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    wget \
    curl \
    # Playwright 브라우저 실행에 필요한 추가 의존성
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Python 3.11을 기본 python3로 설정
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
RUN update-alternatives --set python3 /usr/bin/python3.11

# pip 업그레이드
RUN python3 -m pip install --upgrade pip

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 환경 변수 먼저 설정
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Playwright 브라우저 및 의존성 설치
RUN python3 -m playwright install chromium
RUN python3 -m playwright install-deps chromium

# 앱 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUTF8=1

# 포트 설정
EXPOSE 8001

# 서버 시작
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]