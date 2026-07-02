#!/bin/bash
export PATH=$PATH:/usr/local/bin:/opt/homebrew/bin:/opt/anaconda3/bin
cd "$(dirname "$0")"

# Initialize Conda for Python environment
if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
    source "/opt/anaconda3/etc/profile.d/conda.sh"
    conda activate base
fi

echo "======================================"
echo "🚀 Starting Signal Dashboard (Local)"
echo "======================================"

echo "[1/3] Fetching latest PTT data (This may take 30-60 seconds)..."
/opt/anaconda3/bin/python stock_crawler.py

# Start Backend
echo "[2/3] Starting Backend API Server (FastAPI)..."
/opt/anaconda3/bin/uvicorn main:app --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > backend.pid

# Start Frontend
echo "[3/3] Starting Frontend App (Vite/React)..."
cd signal-dashboard
/usr/local/bin/npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid

echo ""
echo "✅ Everything is up and running!"
echo "👉 Open your browser: http://localhost:5173"
echo "--------------------------------------"
echo "💡 To stop the dashboard completely and save battery, run: ./stop.sh"
echo "======================================"

sleep 3
open http://localhost:5173
