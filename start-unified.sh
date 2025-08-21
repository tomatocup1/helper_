#!/bin/bash

# 통합 포트 설정으로 서비스 시작 스크립트

echo "🚀 Starting Store Helper with Unified Port Configuration (localhost:4000)"
echo "================================================"

# 환경 변수 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다. .env.example을 복사합니다..."
    cp .env.example .env
    echo "✅ .env 파일이 생성되었습니다. 필요한 환경 변수를 설정해주세요."
    exit 1
fi

# Docker Compose 버전 확인
echo "📋 Docker 버전 확인..."
docker --version
docker-compose --version

# 기존 컨테이너 정리
echo "🧹 기존 컨테이너 정리..."
docker-compose down

# 네트워크 생성 (존재하지 않는 경우)
echo "🌐 Docker 네트워크 설정..."
docker network create storehelper-network 2>/dev/null || true

# 서비스 시작
echo "🏗️  서비스 빌드 및 시작..."
docker-compose up -d --build

# 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중... (30초)"
sleep 30

echo "📊 서비스 상태 확인:"
docker-compose ps

# 헬스체크
echo "🏥 헬스체크 수행..."
curl -f http://localhost:4000/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Nginx 프록시가 정상적으로 작동 중입니다."
else
    echo "❌ Nginx 프록시 연결 실패. 로그를 확인하세요:"
    echo "   docker-compose logs nginx"
fi

echo ""
echo "================================================"
echo "✨ 서비스 접근 URL:"
echo "   📱 메인 애플리케이션: http://localhost:4000/"
echo "   👨‍💼 관리자 대시보드: http://localhost:4000/admin"
echo "   🔌 API 서버: http://localhost:4000/api"
echo "   🕷️  크롤러: http://localhost:4000/crawler"
echo "   ⏰ 스케줄러: http://localhost:4000/scheduler"
echo ""
echo "📚 추가 명령어:"
echo "   로그 보기: docker-compose logs -f [service-name]"
echo "   서비스 중지: docker-compose down"
echo "   서비스 재시작: docker-compose restart [service-name]"
echo "================================================"