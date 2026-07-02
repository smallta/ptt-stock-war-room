#!/bin/bash
export PATH=$PATH:/usr/local/bin:/opt/homebrew/bin:/opt/anaconda3/bin
cd "$(dirname "$0")"


echo "======================================"
echo "🛑 Stopping Signal Dashboard..."
echo "======================================"

if [ -f backend.pid ]; then
    kill $(cat backend.pid) 2>/dev/null
    rm backend.pid
    echo "[x] Backend Server stopped."
fi

if [ -f frontend.pid ]; then
    kill $(cat frontend.pid) 2>/dev/null
    rm frontend.pid
    echo "[x] Frontend App stopped."
fi

# Fallback cleanup for any lingering processes
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null

echo "✅ All services have been completely shut down."
echo "🔋 Zero battery drain guaranteed!"
echo "======================================"
