#!/bin/bash
echo "🚀 正在為您自動抓取 PTT 股板與 Telegram 最新數據..."
cd "/Users/Sephiroth/Desktop/爬文"
python3 stock_crawler.py
python3 send_telegram_bot.py

echo "🌐 啟動戰情室伺服器與 Telegram 即時互動點播機器人..."
pkill -f server.py || true
pkill -f tg_interactive_bot.py || true
nohup python3 server.py > /dev/null 2>&1 &
nohup python3 tg_interactive_bot.py > /dev/null 2>&1 &
sleep 1

echo "✨ 開啟瀏覽器查看最新戰情..."
open "http://localhost:8520/dashboard/index.html"
