import os
import requests

# Telegram Bot configurations
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8837287745:AAGq7-ZQKt_PwzowODDbpc4pzdDhoyfcw1k")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1815627011")

def send_digest():
    if not os.path.exists("tg_digest_report.txt"):
        print("⚠️ tg_digest_report.txt 不存在，請先執行 stock_crawler.py。")
        return
        
    with open("tg_digest_report.txt", "r", encoding="utf-8") as f:
        text = f.read()
        
    if not BOT_TOKEN or not CHAT_ID:
        print("\n📢 今日戰情報告已產出 (已儲存於 tg_digest_report.txt)：")
        print("=" * 50)
        print(text)
        print("=" * 50)
        print("\n💡 提示：若要自動推送到手機 Telegram App，只需提供您的 Telegram Bot Token 與 Chat ID 即可自動開啟播報！")
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ 已成功自動推送今日盤後戰情報告至您的 Telegram！")
        else:
            print("❌ 推送至 Telegram 失敗：", res.text)
    except Exception as e:
        print("❌ 發送失敗：", e)

if __name__ == "__main__":
    send_digest()
