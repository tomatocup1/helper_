#!/bin/bash

echo "Starting all services for Baemin Store Helper..."

# Start Redis server
echo "Starting Redis server..."
redis-server --port 6379 &
REDIS_PID=$!

# Wait for Redis to start
sleep 3

# Start Celery Worker
echo "Starting Celery Worker..."
cd ../backend
python scripts/start_worker.py &
WORKER_PID=$!

# Start FastAPI Backend
echo "Starting FastAPI Backend..."
cd api
python app.py &
API_PID=$!

# Wait for backend to start
sleep 5

# Start Frontend
echo "Starting Next.js Frontend..."
cd ../../frontend
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5

# Start Proxy Server
echo "Starting Proxy Server..."
cd ..
node proxy-server.js &
PROXY_PID=$!

echo ""
echo "=============================="
echo "All services started!"
echo "=============================="
echo "Frontend: http://localhost:3000"
echo "Proxy: http://localhost:4000"
echo "Backend API: http://localhost:8001"
echo "=============================="
echo ""

# Create cleanup function
cleanup() {
    echo "Stopping all services..."
    kill $REDIS_PID $WORKER_PID $API_PID $FRONTEND_PID $PROXY_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for user to stop
echo "Press Ctrl+C to stop all services"
wait