#!/bin/bash
echo "啟動 PTT 股市戰情室伺服器..."
echo "正在讀取 CSV 數據..."

# 在根目錄 (爬文資料夾) 啟動伺服器，以便讀取 csv 與 dashboard/index.html
# 檢查是否有被佔用的 port，預設使用 8000
python3 -m http.server 8000 &
SERVER_PID=$!

echo "伺服器已啟動於 PID $SERVER_PID"
echo "開啟瀏覽器前往儀表板..."

# Mac 指令：開啟網頁
open "http://localhost:8000/dashboard/index.html"

echo "儀表板已開啟！您可以按 Ctrl+C 來停止伺服器。"
# 等待進程，這樣 Ctrl+C 可以中斷它
wait $SERVER_PID
