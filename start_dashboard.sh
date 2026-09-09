#!/bin/bash
echo "啟動 PTT 股市戰情室伺服器..."
cd "/Users/Sephiroth/Desktop/爬文"
nohup python3 -m http.server 8765 > /dev/null 2>&1 &
sleep 1
echo "開啟瀏覽器前往儀表板..."
open "http://localhost:8765/dashboard/index.html"
echo "✅ 戰情室已啟動！"
