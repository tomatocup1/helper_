@echo off
echo ================================================
echo   🚀 Store Helper - Local Development (Port 4000)
echo ================================================
echo.

REM 필요한 패키지 설치 확인
echo 📦 패키지 설치 확인 중...
if not exist node_modules (
    echo Installing proxy server dependencies...
    call npm install
)

if not exist frontend\node_modules (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo.
echo ================================================
echo   서비스 시작 옵션을 선택하세요:
echo ================================================
echo   1. 프록시 서버만 시작 (수동으로 각 서비스 시작)
echo   2. 프록시 + Frontend 시작
echo   3. 프록시 + Frontend + Backend 모두 시작
echo   4. 종료
echo ================================================
set /p choice="선택 (1-4): "

if %choice%==1 goto proxy_only
if %choice%==2 goto proxy_frontend
if %choice%==3 goto all_services
if %choice%==4 goto end

:proxy_only
echo.
echo 🔄 프록시 서버 시작 중... (Port 4000)
echo.
echo 다른 터미널에서 서비스를 시작하세요:
echo   - Frontend: cd frontend ^&^& npm run dev
echo   - Backend: cd backend ^&^& python server.py
echo.
start "Proxy Server" cmd /k npm run proxy
goto success

:proxy_frontend
echo.
echo 🔄 프록시 서버와 Frontend 시작 중...
echo.
start "Proxy Server" cmd /k npm run proxy
timeout /t 2 /nobreak >nul
start "Frontend Server" cmd /k "cd frontend && npm run dev"
echo.
echo Backend는 수동으로 시작하세요:
echo   cd backend ^&^& python server.py
goto success

:all_services
echo.
echo 🔄 모든 서비스 시작 중...
echo.

REM 프록시 서버 시작
start "Proxy Server" cmd /k npm run proxy
timeout /t 2 /nobreak >nul

REM Frontend 시작
start "Frontend Server" cmd /k "cd frontend && npm run dev"
timeout /t 2 /nobreak >nul

REM Python Backend 시작
echo Python Backend 서버 시작 중...
start "Backend Server" cmd /k "cd backend && python server.py"

goto success

:success
echo.
echo ================================================
echo ✅ 서비스가 시작되었습니다!
echo ================================================
echo.
echo 📍 통합 접속 주소: http://localhost:4000
echo.
echo 🔗 서비스 엔드포인트:
echo    • 메인 앱:      http://localhost:4000/
echo    • API:          http://localhost:4000/api
echo    • 크롤러:       http://localhost:4000/crawler
echo    • 스케줄러:     http://localhost:4000/scheduler
echo    • 헬스체크:     http://localhost:4000/health
echo    • 프록시 상태:  http://localhost:4000/proxy-status
echo.
echo 💡 팁:
echo    • Ctrl+C로 각 터미널에서 서비스 종료
echo    • 로그는 각 터미널 창에서 확인
echo ================================================
echo.
pause
goto end

:end
echo 종료합니다...
exit /b