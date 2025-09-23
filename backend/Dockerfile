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

# Playwright 브라우저 및 의존성 설치
RUN playwright install --with-deps chromium

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