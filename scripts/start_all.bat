@echo off
echo Starting all services for Baemin Store Helper...

REM Start Redis server
echo Starting Redis server...
start "Redis Server" redis-server --port 6379

REM Wait for Redis to start
timeout /t 3

REM Start Celery Worker
echo Starting Celery Worker...
start "Celery Worker" /D "C:\helper_B\backend" python scripts\start_worker.py

REM Start FastAPI Backend
echo Starting FastAPI Backend...
start "FastAPI Backend" /D "C:\helper_B\backend\api" python app.py

REM Wait for backend to start
timeout /t 5

REM Start Frontend
echo Starting Next.js Frontend...
start "Frontend" /D "C:\helper_B\frontend" npm run dev

REM Wait for frontend to start
timeout /t 5

REM Start Proxy Server
echo Starting Proxy Server...
start "Proxy Server" /D "C:\helper_B" node proxy-server.js

echo.
echo ==============================
echo All services started!
echo ==============================
echo Frontend: http://localhost:3000
echo Proxy: http://localhost:4000
echo Backend API: http://localhost:8001
echo ==============================
echo.

pause