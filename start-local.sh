#!/bin/bash

echo "================================================"
echo "  🚀 Store Helper - Local Development (Port 4000)"
echo "================================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 필요한 패키지 설치 확인
echo "📦 패키지 설치 확인 중..."
if [ ! -d "node_modules" ]; then
    echo "Installing proxy server dependencies..."
    npm install
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "================================================"
echo "  서비스 시작 옵션을 선택하세요:"
echo "================================================"
echo "  1. 프록시 서버만 시작 (수동으로 각 서비스 시작)"
echo "  2. 프록시 + Frontend 시작"
echo "  3. 프록시 + Frontend + Backend 모두 시작"
echo "  4. 종료"
echo "================================================"
read -p "선택 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🔄 프록시 서버 시작 중... (Port 4000)"
        echo ""
        echo "다른 터미널에서 서비스를 시작하세요:"
        echo "  - Frontend: cd frontend && npm run dev"
        echo "  - Backend: cd backend && python server.py"
        echo ""
        npm run proxy
        ;;
    
    2)
        echo ""
        echo "🔄 프록시 서버와 Frontend 시작 중..."
        echo ""
        
        # 프록시 서버를 백그라운드에서 시작
        npm run proxy &
        PROXY_PID=$!
        sleep 2
        
        # Frontend 시작
        cd frontend && npm run dev &
        FRONTEND_PID=$!
        
        echo ""
        echo "Backend는 수동으로 시작하세요:"
        echo "  cd backend && python server.py"
        echo ""
        echo -e "${GREEN}서비스 PID:${NC}"
        echo "  - Proxy: $PROXY_PID"
        echo "  - Frontend: $FRONTEND_PID"
        echo ""
        echo "종료하려면 Ctrl+C를 누르세요..."
        
        # Wait for interrupt
        trap "kill $PROXY_PID $FRONTEND_PID 2>/dev/null; exit" INT
        wait
        ;;
    
    3)
        echo ""
        echo "🔄 모든 서비스 시작 중..."
        echo ""
        
        # 프록시 서버 시작
        npm run proxy &
        PROXY_PID=$!
        sleep 2
        
        # Frontend 시작
        cd frontend && npm run dev &
        FRONTEND_PID=$!
        cd ..
        sleep 2
        
        # Python Backend 시작
        cd backend && python server.py &
        BACKEND_PID=$!
        cd ..
        
        echo ""
        echo -e "${GREEN}✅ 모든 서비스가 시작되었습니다!${NC}"
        echo ""
        echo "서비스 PID:"
        echo "  - Proxy: $PROXY_PID"
        echo "  - Frontend: $FRONTEND_PID"
        echo "  - Backend: $BACKEND_PID"
        echo ""
        echo "종료하려면 Ctrl+C를 누르세요..."
        
        # Wait for interrupt and cleanup
        trap "kill $PROXY_PID $FRONTEND_PID $BACKEND_PID 2>/dev/null; exit" INT
        wait
        ;;
    
    4)
        echo "종료합니다..."
        exit 0
        ;;
    
    *)
        echo -e "${RED}잘못된 선택입니다.${NC}"
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo -e "${GREEN}✅ 서비스가 시작되었습니다!${NC}"
echo "================================================"
echo ""
echo "📍 통합 접속 주소: http://localhost:4000"
echo ""
echo "🔗 서비스 엔드포인트:"
echo "   • 메인 앱:      http://localhost:4000/"
echo "   • API:          http://localhost:4000/api"
echo "   • 크롤러:       http://localhost:4000/crawler"
echo "   • 스케줄러:     http://localhost:4000/scheduler"
echo "   • 헬스체크:     http://localhost:4000/health"
echo "   • 프록시 상태:  http://localhost:4000/proxy-status"
echo ""
echo "💡 팁:"
echo "   • Ctrl+C로 모든 서비스 종료"
echo "   • 로그는 현재 터미널에서 확인"
echo "================================================"