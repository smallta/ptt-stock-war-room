import os
import time
import requests
import json
import re
from stock_crawler import main as run_crawler

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8837287745:AAGq7-ZQKt_PwzowODDbpc4pzdDhoyfcw1k")
ALLOWED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1815627011")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Error sending msg:", e)

def get_market_summary_reply():
    if not os.path.exists("market_data.json"):
        return "⚠️ 尚未產生數據，請發送 /crawl 手動觸發即時爬蟲。"
        
    try:
        with open("market_data.json", "r", encoding="utf-8") as f:
            market = json.load(f)
        with open("detail_data.json", "r", encoding="utf-8") as f:
            details = json.load(f)
        with open("hot_stocks_sentiment.csv", "r", encoding="utf-8-sig") as f:
            import pandas as pd
            df = pd.read_csv(f)
            stocks_data = df.to_dict(orient="records")
    except Exception as e:
        return f"⚠️ 讀取數據失敗: {e}"

    taiex = market.get("TAIEXSummary", {})
    inst_amt = market.get("RealInstitutionalStats", {}).get("Amounts", {})
    
    f_amt = inst_amt.get("Foreign", {}).get("net", "-")
    t_amt = inst_amt.get("Trust", {}).get("net", "-")
    d_amt = inst_amt.get("Dealer", {}).get("net", "-")
    tot_amt = inst_amt.get("Total", {}).get("net", "-")
    
    lines = [
        "📊 <b>【即時戰情摘要】</b>\n",
        f"📈 <b>加權指數</b>：{taiex.get('TAIEX', '-')} 點 ({taiex.get('Change', '-')} / {taiex.get('ChangePercent', '-')})",
        f"🚨 <b>絕望反向指標</b>：{market.get('PanicIndex', 0)} 分\n",
        "🏛️ <b>三大法人買賣金額</b>：",
        f"外資: <code>{f_amt}</code> | 投信: <code>{t_amt}</code> | 自營商: <code>{d_amt}</code>",
        f"三大法人合計: <code>{tot_amt}</code>\n",
        "🔥 <b>熱門焦點 Top 5</b>："
    ]
    
    for idx, r in enumerate(stocks_data[:5], 1):
        chg = str(r.get("Change", ""))
        icon = "🔴" if chg.startswith("+") else ("🟢" if chg.startswith("-") else "⚪")
        lines.append(f"{idx}. <b>{r['Stock']}</b> (分數 {r['Score']})")
        lines.append(f"   收盤: ${r['Price']} {icon} ({r['ChangePercent']}) | 外資: {r['ForeignNet']}張")
        lines.append(f"   Tag: {r['Risk']}\n")
        
    lines.append(f"💡 <b>風向總結</b>：{market.get('MarketSummary', '')}")
    return "\n".join(lines)

def get_stock_detail_reply(query):
    if not os.path.exists("hot_stocks_sentiment.csv"):
        return "⚠️ 尚未產生數據，請發送 /crawl 執行爬蟲。"
        
    import pandas as pd
    df = pd.read_csv("hot_stocks_sentiment.csv")
    stocks = df.to_dict(orient="records")
    
    target = None
    q = query.strip().lower()
    for s in stocks:
        st_name = str(s["Stock"]).lower()
        if q in st_name:
            target = s
            break
            
    if not target:
        return f"🔍 找不到與「{query}」相關的股票，請確認名稱或代號。"
        
    with open("detail_data.json", "r", encoding="utf-8") as f:
        details = json.load(f)
        
    st_key = target["Stock"]
    dt = details.get(st_key, {})
    comments = dt.get("Comments", [])[:5]
    
    chg = str(target.get("Change", ""))
    icon = "🔴" if chg.startswith("+") else ("🟢" if chg.startswith("-") else "⚪")
    
    lines = [
        f"🔍 <b>【{st_key} 個股即時情報】</b>\n",
        f"💰 <b>收盤價</b>：${target['Price']} {icon} {target['Change']} ({target['ChangePercent']})",
        f"📊 <b>綜合熱度分數</b>：{target['Score']} 分 (討論 {target['Mentions']} 則 / {target['UniqueUsers']} 人)",
        f"🏛️ <b>三大法人</b>：外資 {target['ForeignNet']}張 | 投信 {target['TrustNet']}張 | 法人 {target['TotalNet']}張",
        f"📈 <b>基本面估值</b>：PE {target['PE']} | PB {target['PB']} | 殖利率 {target['Yield']}%",
        f"⚠️ <b>風險特徵 Tag</b>：{target['Risk']}\n",
        "💬 <b>最新鄉民推文摘錄</b>："
    ]
    
    for c in comments:
        lines.append(f"• 👤 <i>{c['user']}</i>: {c['text']}")
        
    return "\n".join(lines)

def handle_update(update):
    msg = update.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip()
    
    if not text or (ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID):
        return

    print(f"Received TG command: {text} from {chat_id}")
    
    if text in ["/start", "/help"]:
        reply = (
            "🤖 <b>【PTT 戰情室即時 Telegram 助手】</b>\n\n"
            "您可以發送以下指令隨時獲取即時情報：\n"
            "• <b>/now</b> 或 <b>/summary</b> : 獲取最新大盤與熱門股摘要\n"
            "• <b>/crawl</b> : 立即觸發最新 PTT + Telegram 即時爬蟲\n"
            "• <b>/stock 代號或名稱</b> : 查詢特定股票 (例: <code>/stock 2330</code> 或 <code>/stock 大立光</code>)\n"
            "• <b>/hot</b> : 查看今日 Top 10 熱門討論股"
        )
        send_message(chat_id, reply)
    elif text in ["/now", "/summary"]:
        reply = get_market_summary_reply()
        send_message(chat_id, reply)
    elif text == "/crawl":
        send_message(chat_id, "🚀 正在為您即時抓取 PTT 與 Telegram 最新數據，請稍候約 10 秒...")
        try:
            run_crawler()
            reply = get_market_summary_reply()
            send_message(chat_id, "✅ 爬蟲完成！最新戰情摘要如下：\n\n" + reply)
        except Exception as e:
            send_message(chat_id, f"❌ 執行爬蟲失敗: {e}")
    elif text == "/hot":
        if not os.path.exists("hot_stocks_sentiment.csv"):
            send_message(chat_id, "⚠️ 尚未產生數據，請發送 /crawl。")
            return
        import pandas as pd
        df = pd.read_csv("hot_stocks_sentiment.csv")
        stocks = df.to_dict(orient="records")[:10]
        lines = ["🔥 <b>【今日 Top 10 熱門討論股】</b>\n"]
        for idx, s in enumerate(stocks, 1):
            chg = str(s.get("Change", ""))
            icon = "🔴" if chg.startswith("+") else ("🟢" if chg.startswith("-") else "⚪")
            lines.append(f"{idx}. <b>{s['Stock']}</b> - 分數 {s['Score']} | 收盤 ${s['Price']} {icon} ({s['ChangePercent']})")
        send_message(chat_id, "\n".join(lines))
    elif text.startswith("/stock"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "💡 請輸入欲查詢的股票代號或名稱，例如：<code>/stock 2330</code> 或 <code>/stock 鴻海</code>")
        else:
            reply = get_stock_detail_reply(parts[1])
            send_message(chat_id, reply)
    elif text.startswith("/"):
        # Handle /2330 or /鴻海 directly
        st_query = text.lstrip("/")
        reply = get_stock_detail_reply(st_query)
        send_message(chat_id, reply)

def main_polling():
    print("🤖 Telegram 戰情室即時點播助手已啟動 (Polling mode)...")
    offset = 0
    while True:
        try:
            url = f"{BASE_URL}/getUpdates?offset={offset}&timeout=10"
            res = requests.get(url, timeout=15).json()
            if res.get("ok"):
                updates = res.get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    handle_update(update)
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    main_polling()
