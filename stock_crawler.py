import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import time
import os

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    try:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "curl_cffi"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        from curl_cffi import requests as cffi_requests
    except Exception:
        cffi_requests = None

# PTT Stock Board configuration
PTT_URL = "https://www.ptt.cc"
STOCK_BOARD_URL = f"{PTT_URL}/bbs/Stock/index.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.ptt.cc/bbs/Stock/index.html",
}
COOKIES = {"over18": "1"}

# Telegram Channels list (可自訂新增多個公開 Telegram 頻道)
TELEGRAM_CHANNELS = ["ptt_stock_follow_chat"]

# 熱門概念題材成分股清單 (用於族群集體暴漲/重挫監控)
HOT_THEMES = {
    "💡 CPO矽光子": ["3450", "6442", "3081", "3163", "4979", "3363", "6451", "6213"],
    "⚡ CoWoS先進封裝": ["3131", "3583", "6187", "6640", "3680", "1560", "2330"],
    "🤖 AI伺服器/散熱": ["2382", "3231", "2376", "6669", "3017", "3324", "2421", "2356"],
    "🔌 重電與綠能": ["1519", "1503", "1513", "1514", "6806", "3708"],
    "🦾 機器人概念": ["2359", "4566", "6188", "4562", "8374", "4576"],
    "🚢 貨櫃航運": ["2603", "2609", "2615"],
    "✈️ 航空雙雄": ["2610", "2618", "2646"],
    "🏦 金控指標": ["2881", "2882", "2891", "2886", "2884", "2892"],
    "📱 IC設計": ["2454", "3034", "2379", "3443", "3661", "6526"]
}

CUSTOM_NICKNAMES = {
    "發哥": "聯發科 (2454)", "公公": "鴻海 (2317)", "海公公": "鴻海 (2317)",
    "肉鬆": "廣達 (2382)", "二哥": "聯電 (2303)", "神山": "台積電 (2330)",
    "大哥": "台積電 (2330)", "長榮": "長榮 (2603)", "陽明": "陽明 (2609)",
    "萬海": "萬海 (2615)", "阿榮": "長榮 (2603)", "阿明": "陽明 (2609)",
    "阿海": "萬海 (2615)", "水手": "航運股", "船長": "航運股",
    "喵喵": "群創 (3481)", "戀人": "友達 (2409)", "包子": "群創/友達 (面板)",
    "滷肉": "聯詠 (3034)", "螃蟹": "瑞昱 (2379)", "假G": "台積電 (2330)",
    "台G": "台積電 (2330)", "gg": "台積電 (2330)", "GG": "台積電 (2330)",
    "紅茶店": "宏達電 (2498)", "三雄": "航運股", "皮衣男": "NVIDIA概念股",
    "老黃": "NVIDIA概念股", "AI妖股": "緯創 (3231)", "緯老軟": "緯軟 (4953)",
    "大G": "大立光 (3008)", "星宇": "星宇航空 (2646)",
    "大力光": "大立光 (3008)", "大力": "大立光 (3008)", "大立光": "大立光 (3008)"
}

POSITIVE_WORDS = ["低估", "便宜", "超跌", "打底", "轉強", "轉機", "突破", "成長", "利多", "買", "加碼", "看好", "殖利率", "配息", "營收", "獲利", "噴", "賺", "舒服"]
NEGATIVE_WORDS = ["高估", "太貴", "套", "爛", "跌", "崩", "利空", "賣", "空", "減碼", "看壞", "虧", "衰退", "泡沫", "出貨", "破底", "丸子", "綠"]
UNDERVALUED_WORDS = ["低估", "便宜", "本益比低", "淨值比低", "殖利率", "配息", "超跌", "價值", "被錯殺", "低基期"]
HYPE_WORDS = ["噴", "飆", "妖", "歐印", "all in", "ALL IN", "無腦", "上車", "嘎", "火箭", "目標價"]
FUNDAMENTAL_WORDS = ["營收", "法說", "毛利", "財報", "EPS", "展望", "盈餘", "配息", "殖利率", "基本面", "淨利"]
PANIC_WORDS = ["畢業", "停損", "斷頭", "違約", "抬出場", "救命", "砍在最低", "腰斬", "痛失", "賣在最低", "爆開", "慘", "崩", "套", "丸子", "輸光", "救我"]
SARCASM_WORDS = ["穩了", "送分題", "利多出盡", "多蛙", "空蛙", "這波送錢", "感謝主力", "救命", "丸子", "99", "越爛越噴", "出貨文", "倒給散戶", "少年股神", "哲哲", "老蘇", "這檔沒救了", "主力在洗盤"]

EVENT_RULES = {
    "法說": "法說會", "注意": "注意股", "處置": "處置股", "違約": "違約交割",
    "庫藏": "庫藏股", "除權": "除權息", "除息": "除權息", "營收": "營收揭曉",
    "財報": "財報發布", "CoWoS": "CoWoS概念", "CPO": "CPO矽光子",
    "漲停鎖死": "漲停鎖死", "鎖漲停": "漲停鎖死", "漲停板": "漲停板",
    "跌停鎖死": "跌停鎖死", "鎖跌停": "跌停鎖死", "跌停板": "跌停板"
}

FOREIGN_WORDS = ["外資", "小麥", "外資買", "外資賣", "外資倒"]
TRUST_WORDS = ["投信", "大哥買", "大哥賣", "投信買", "投信賣", "作帳", "結帳"]

def safe_get(url, is_json=False):
    for attempt in range(3):
        try:
            if cffi_requests and "ptt.cc" in url:
                res = cffi_requests.get(url, headers=HEADERS, cookies=COOKIES, impersonate="chrome124", timeout=12)
            else:
                res = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=12)
            if res.status_code == 200:
                return res.json() if is_json else res.text
            elif res.status_code == 403:
                print(f"[safe_get] 403 Forbidden for {url}")
        except Exception as e:
            time.sleep(0.5)
    return {} if is_json else ""

def get_stocks():
    print("Fetching Stock lists and valuations...")
    stocks = {}
    valuations = {}
    price_data = {}
    
    # TWSE Prices & Change
    data = safe_get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", is_json=True)
    if isinstance(data, list):
        for i in data:
            code = i.get("Code", "")
            if len(code) == 4:
                stocks[code] = i["Name"]
                close_p = i.get("ClosingPrice", "-")
                chg_raw = i.get("Change", "0")
                try:
                    c_val = float(close_p.replace(",", ""))
                    chg_val = float(chg_raw.replace(",", ""))
                    prev = c_val - chg_val
                    pct = (chg_val / prev * 100) if prev > 0 else 0
                    chg_str = f"+{chg_val:.2f}" if chg_val > 0 else f"{chg_val:.2f}"
                    pct_str = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
                except:
                    chg_str = "-"
                    pct_str = "-"
                price_data[code] = {"Price": close_p, "Change": chg_str, "ChangePercent": pct_str}

    # TPEx Prices & Change
    data = safe_get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes", is_json=True)
    if isinstance(data, list):
        for i in data:
            code = i.get("SecuritiesCompanyCode", "")
            if len(code) == 4:
                stocks[code] = i["CompanyName"]
                close_p = i.get("Close", "-")
                chg_raw = i.get("Change", "0")
                try:
                    c_val = float(close_p.replace(",", ""))
                    chg_val = float(chg_raw.replace(",", ""))
                    prev = c_val - chg_val
                    pct = (chg_val / prev * 100) if prev > 0 else 0
                    chg_str = f"+{chg_val:.2f}" if chg_val > 0 else f"{chg_val:.2f}"
                    pct_str = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
                except:
                    chg_str = "-"
                    pct_str = "-"
                price_data[code] = {"Price": close_p, "Change": chg_str, "ChangePercent": pct_str}

    # TWSE Valuations
    data = safe_get("https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL", is_json=True)
    if isinstance(data, list):
        for i in data:
            if len(i.get("Code", "")) == 4:
                valuations[i["Code"]] = {
                    "PE": i.get("PEratio", "-"),
                    "Yield": i.get("DividendYield", "-"),
                    "PB": i.get("PBratio", "-")
                }

    # Sectors (TWSE)
    sectors = {}
    twse_sector_map = {
        "01": "水泥工業", "02": "食品工業", "03": "塑膠工業", "04": "紡織纖維", "05": "電機機械",
        "06": "電器電纜", "07": "化學工業", "08": "玻璃陶瓷", "09": "造紙工業", "10": "鋼鐵工業",
        "11": "橡膠工業", "12": "汽車工業", "14": "建材營造", "15": "航運業", "16": "觀光餐旅",
        "17": "金融保險", "18": "貿易百貨", "20": "其他", "21": "化學工業", "22": "生技醫療業",
        "23": "油電燃氣業", "24": "半導體業", "25": "電腦及週邊設備業", "26": "光電業",
        "27": "通信網路業", "28": "電子零組件業", "29": "電子通路業", "30": "資訊服務業",
        "31": "其他電子業", "32": "文化創意業", "33": "農業科技業", "34": "電子商務業", "35": "綠能環保"
    }
    data = safe_get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", is_json=True)
    if isinstance(data, list):
        for i in data:
            if len(i.get("公司代號", "")) == 4:
                code = i.get("產業別", "")
                sectors[i["公司代號"]] = twse_sector_map.get(code, code if code else "其他")

    # TPEx Valuations
    data = safe_get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis", is_json=True)
    if isinstance(data, list):
        for i in data:
            if len(i.get("SecuritiesCompanyCode", "")) == 4:
                valuations[i["SecuritiesCompanyCode"]] = {
                    "PE": i.get("PriceEarningRatio", "-"),
                    "PB": i.get("PriceBookRatio", "-"),
                    "Yield": i.get("YieldRatio", "-")
                }

    return stocks, valuations, sectors, price_data

def get_institutional_amount():
    amt_data = {
        "Foreign": {"buy": "-", "sell": "-", "net": "-"},
        "Trust": {"buy": "-", "sell": "-", "net": "-"},
        "Dealer": {"buy": "-", "sell": "-", "net": "-", "self_net": "-", "hedge_net": "-"},
        "Total": {"buy": "-", "sell": "-", "net": "-"}
    }
    try:
        url = "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
        res = safe_get(url, is_json=True)
        if isinstance(res, dict) and res.get("data"):
            dealer_buy = 0.0
            dealer_sell = 0.0
            dealer_net = 0.0
            self_net = 0.0
            hedge_net = 0.0
            
            for row in res["data"]:
                name = row[0]
                b_val = float(row[1].replace(",", "")) / 1e8
                s_val = float(row[2].replace(",", "")) / 1e8
                n_val = float(row[3].replace(",", "")) / 1e8
                
                b_str = f"{b_val:.2f}億"
                s_str = f"{s_val:.2f}億"
                n_str = f"+{n_val:.2f}億" if n_val > 0 else f"{n_val:.2f}億"
                
                if "外資及陸資" in name:
                    amt_data["Foreign"] = {"buy": b_str, "sell": s_str, "net": n_str}
                elif "投信" in name:
                    amt_data["Trust"] = {"buy": b_str, "sell": s_str, "net": n_str}
                elif "自行買賣" in name:
                    dealer_buy += b_val
                    dealer_sell += s_val
                    dealer_net += n_val
                    self_net = n_val
                elif "避險" in name:
                    dealer_buy += b_val
                    dealer_sell += s_val
                    dealer_net += n_val
                    hedge_net = n_val
                elif "合計" in name:
                    amt_data["Total"] = {"buy": b_str, "sell": s_str, "net": n_str}
                    
            d_n_str = f"+{dealer_net:.2f}億" if dealer_net > 0 else f"{dealer_net:.2f}億"
            self_n_str = f"+{self_net:.2f}億" if self_net > 0 else f"{self_net:.2f}億"
            hedge_n_str = f"+{hedge_net:.2f}億" if hedge_net > 0 else f"{hedge_net:.2f}億"
            
            amt_data["Dealer"] = {
                "buy": f"{dealer_buy:.2f}億",
                "sell": f"{dealer_sell:.2f}億",
                "net": d_n_str,
                "self_net": self_n_str,
                "hedge_net": hedge_n_str
            }
    except Exception as e:
        print(f"Error fetching institutional amounts: {e}")
    return amt_data

def get_institutional_data():
    inst_data = {}
    summary = {
        "ForeignBuyCount": 0, "ForeignSellCount": 0, "ForeignTotalNet": 0, "ForeignTopBuy": [],
        "TrustBuyCount": 0, "TrustSellCount": 0, "TrustTotalNet": 0, "TrustTopBuy": [],
        "Amounts": get_institutional_amount()
    }
    try:
        url = "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=ALLBUT0999"
        res = safe_get(url, is_json=True)
        if isinstance(res, dict):
            data = res.get("data", [])
            f_buy, f_sell, f_tot = 0, 0, 0
            t_buy, t_sell, t_tot = 0, 0, 0
            f_list, t_list = [], []
            
            for row in data:
                code = row[0].strip()
                name = row[1].strip()
                if len(code) == 4:
                    try:
                        foreign_net = int(row[4].replace(",", "")) // 1000
                        trust_net = int(row[10].replace(",", "")) // 1000
                        dealer_net = int(row[11].replace(",", "")) // 1000
                        total_net = int(row[18].replace(",", "")) // 1000
                        
                        inst_data[code] = {
                            "ForeignNet": foreign_net,
                            "TrustNet": trust_net,
                            "DealerNet": dealer_net,
                            "TotalNet": total_net
                        }
                        
                        f_tot += foreign_net
                        t_tot += trust_net
                        
                        if foreign_net > 0: f_buy += 1
                        elif foreign_net < 0: f_sell += 1
                        
                        if trust_net > 0: t_buy += 1
                        elif trust_net < 0: t_sell += 1
                        
                        f_list.append({"name": name, "code": code, "net": foreign_net})
                        t_list.append({"name": name, "code": code, "net": trust_net})
                    except:
                        pass
                        
            summary["ForeignBuyCount"] = f_buy
            summary["ForeignSellCount"] = f_sell
            summary["ForeignTotalNet"] = f_tot
            summary["ForeignTopBuy"] = sorted(f_list, key=lambda x: x["net"], reverse=True)[:3]
            
            summary["TrustBuyCount"] = t_buy
            summary["TrustSellCount"] = t_sell
            summary["TrustTotalNet"] = t_tot
            summary["TrustTopBuy"] = sorted(t_list, key=lambda x: x["net"], reverse=True)[:3]
    except Exception as e:
        print(f"Error fetching institutional data: {e}")
    return inst_data, summary

def get_margin_data():
    print("Fetching Margin Trading data (MI_MARGN)...")
    margin_stock_data = {}
    summary = {
        "MarginBalance": "-", "MarginDiff": "-", "MarginSharesDiff": 0, "ShortSharesDiff": 0
    }
    try:
        url = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?response=json&selectType=ALL"
        res = safe_get(url, is_json=True)
        if isinstance(res, dict) and "tables" in res:
            # Table 0: Credit Summary
            if len(res["tables"]) > 0 and "data" in res["tables"][0]:
                t0 = res["tables"][0]["data"]
                if len(t0) >= 3:
                    try:
                        m_today = float(t0[2][5].replace(",", "")) / 100000  # 仟元 -> 億元
                        m_prev = float(t0[2][4].replace(",", "")) / 100000
                        m_diff = m_today - m_prev
                        summary["MarginBalance"] = f"{m_today:.2f}億"
                        summary["MarginDiff"] = f"+{m_diff:.2f}億" if m_diff > 0 else f"{m_diff:.2f}億"
                        
                        m_s_diff = int(t0[0][5].replace(",", "")) - int(t0[0][4].replace(",", ""))
                        s_s_diff = int(t0[1][5].replace(",", "")) - int(t0[1][4].replace(",", ""))
                        summary["MarginSharesDiff"] = m_s_diff
                        summary["ShortSharesDiff"] = s_s_diff
                    except Exception as e:
                        print(f"Error parsing margin summary: {e}")
            
            # Table 1: Individual stocks
            if len(res["tables"]) > 1 and "data" in res["tables"][1]:
                t1 = res["tables"][1]["data"]
                for row in t1:
                    code = row[0].strip()
                    if len(code) == 4:
                        try:
                            m_diff = int(row[6].replace(",", "")) - int(row[5].replace(",", ""))
                            m_bal = row[6].strip()
                            s_diff = int(row[12].replace(",", "")) - int(row[11].replace(",", ""))
                            s_bal = row[12].strip()
                            margin_stock_data[code] = {
                                "MarginDiff": m_diff,
                                "MarginBalance": m_bal,
                                "ShortDiff": s_diff,
                                "ShortBalance": s_bal
                            }
                        except Exception:
                            continue
    except Exception as e:
        print(f"Error fetching margin data: {e}")
    return margin_stock_data, summary

def get_ai_market_summary(results, market_data, taiex_info):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # High quality rule-based AI heuristic fallback
        fg_idx = market_data.get("FearGreedIndex", 50)
        panic_idx = market_data.get("PanicIndex", 0)
        tot_net = market_data.get("RealInstitutionalStats", {}).get("Amounts", {}).get("Total", {}).get("net", "-")
        m_diff = market_data.get("MarginSummary", {}).get("MarginDiff", "-")
        
        lines = [
            f"🤖 【社群情緒風向】：目前社群恐懼貪婪指數為 {fg_idx} 分，絕望反向指數為 {panic_idx} 分。鄉民整體討論偏向{'狂熱追價' if fg_idx>=70 else ('謹慎觀望' if fg_idx>=40 else '恐慌拋售')}。",
            f"📊 【籌碼與浮額對抗】：三大法人今日合計買賣超 {tot_net}，信用交易融資增減 {m_diff}。需持續留意籌碼集中度高的族群是否出現大戶倒貨。",
            f"🎯 【焦點個股動態】：討論熱度最高之標的為 {results[0]['Stock'] if results else '台股龍頭'}，其籌碼訊號顯示為「{results[0].get('ChipSignal', '動向平衡') if results else '籌碼平衡'}」，建議搭配支撐壓力審慎操作。"
        ]
        return "\n".join(lines)
        
    try:
        top_stocks_summary = []
        for r in results[:8]:
            top_stocks_summary.append(
                f"- {r['Stock']} (收盤${r.get('Price','-')}, 漲跌{r.get('ChangePercent','-')}): 散戶提及{r.get('Mentions',0)}次, 外資{r.get('ForeignNet','-')}張, 投信{r.get('TrustNet','-')}張, 融資{r.get('MarginDiff','-')}張, 鄉民標籤: {', '.join(r.get('TopKeywords',[])[:3])}, 籌碼訊號: {r.get('ChipSignal','')}"
            )
        prompt = f"""你是一位資深台灣股市量化與社群心理分析專家。請分析今日 PTT 股版、Telegram 社群鄉民情緒與證交所官方籌碼數據：
大盤指數：{taiex_info.get('TAIEX', '-')} 點 ({taiex_info.get('ChangePercent', '-')})
絕望/停損指標：{market_data.get('PanicIndex', 0)} 分
三大法人買賣超合計：{market_data.get('RealInstitutionalStats', {}).get('Amounts', {}).get('Total', {}).get('net', '-')}
信用交易融資增減：{market_data.get('MarginSummary', {}).get('MarginDiff', '-')}

熱門焦點個股與籌碼：
{chr(10).join(top_stocks_summary)}

請輸出精簡專業的 3 點「AI 盤勢與社群情緒深度解讀」（包含散戶心理/反串、主力籌碼對抗、潛在風險/機會）："""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 400}
        }
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            res_json = res.json()
            ai_text = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return ai_text.strip()
    except Exception as e:
        print(f"AI Summary Error: {e}")
    return None

def get_taiex_info():
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK"
        data = safe_get(url, is_json=True)
        if isinstance(data, list) and len(data) > 0:
            last = data[-1]
            taiex_val = float(last.get("TAIEX", "0").replace(",", ""))
            change_val = float(last.get("Change", "0").replace(",", ""))
            prev = taiex_val - change_val
            pct = (change_val / prev * 100) if prev > 0 else 0
            
            chg_str = f"+{change_val:.2f}" if change_val > 0 else f"{change_val:.2f}"
            pct_str = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
            return {
                "TAIEX": f"{taiex_val:,.2f}",
                "Change": chg_str,
                "ChangePercent": pct_str,
                "Date": last.get("Date", "")
            }
    except Exception as e:
        print(f"Error fetching TAIEX: {e}")
    return {"TAIEX": "-", "Change": "-", "ChangePercent": "-"}

def get_taiex_intraday_trend():
    trend = {}
    try:
        url = "https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_INDEX?response=json"
        res = safe_get(url, is_json=True)
        if isinstance(res, dict) and res.get("data"):
            raw_data = res["data"]
            tp = {}
            for row in raw_data:
                if len(row[0]) >= 5:
                    tp[row[0][:5]] = float(row[1].replace(",", ""))
            trend = {
                "早盤開盤": tp.get("09:30", tp.get("09:00", 0)),
                "盤中震盪": tp.get("11:30", tp.get("11:00", 0)),
                "尾盤收盤": tp.get("13:30", tp.get("13:00", 0)),
                "盤後夜間": tp.get("13:30", 0)
            }
    except Exception as e:
        print(f"Error fetching TAIEX intraday trend: {e}")
    return trend

def find_chat_urls():
    chat_urls = []
    current_url = STOCK_BOARD_URL
    for _ in range(20):
        html = safe_get(current_url)
        if not html: break
        soup = BeautifulSoup(html, "html.parser")
        for entry in soup.find_all("div", class_="r-ent"):
            title_tag = entry.find("div", class_="title").find("a")
            if title_tag and ("盤中閒聊" in title_tag.text or "盤後閒聊" in title_tag.text):
                chat_urls.append(PTT_URL + title_tag["href"])
        paging = soup.find("div", class_="btn-group-paging")
        if paging:
            current_url = PTT_URL + paging.find_all("a")[1]["href"]
        else:
            break
        time.sleep(0.05)
    # Preserve newest-first order
    return list(dict.fromkeys(chat_urls))

def crawl_comments(url):
    html = safe_get(url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    comments = []
    for push in soup.find_all("div", class_="push"):
        uid_tag = push.find("span", class_=lambda c: c and "push-userid" in c)
        content_tag = push.find("span", class_="push-content")
        time_tag = push.find("span", class_="push-ipdatetime")
        if uid_tag and content_tag:
            comments.append({
                "user": uid_tag.text.strip(),
                "content": content_tag.text.lstrip(": "),
                "time": time_tag.text.strip() if time_tag else ""
            })
    return comments

def crawl_telegram_chat(max_pages=30):
    channels_str = os.environ.get("TELEGRAM_CHANNELS", "")
    ch_list = [c.strip().lstrip("@") for c in channels_str.split(",") if c.strip()] if channels_str else TELEGRAM_CHANNELS
    if "ptt_stock_follow_chat" not in ch_list:
        ch_list.insert(0, "ptt_stock_follow_chat")
        
    comments = []
    for ch in ch_list:
        print(f"Fetching Telegram Channel: t.me/s/{ch} (up to {max_pages} pages)...")
        before = None
        for page in range(max_pages):
            try:
                url = f"https://t.me/s/{ch}?before={before}" if before else f"https://t.me/s/{ch}"
                html = safe_get(url)
                if not html: break
                soup = BeautifulSoup(html, "html.parser")
                msgs = soup.find_all("div", class_="js-message_text")
                if not msgs: break
                for m in msgs:
                    text = m.text.strip()
                    if "：" in text:
                        parts = text.split("：", 1)
                        user_str = parts[0].strip().replace("\n", " ")
                        content_str = parts[1].strip()
                        comments.append({
                            "user": f"📱 [{ch}] {user_str}",
                            "content": content_str,
                            "time": "TG即時推播"
                        })
                    else:
                        comments.append({
                            "user": f"📱 [{ch}]",
                            "content": text,
                            "time": "TG即時推播"
                        })
                more = soup.find("a", class_="tme_messages_more")
                if more and "data-before" in more.attrs:
                    before = more["data-before"]
                else:
                    break
                time.sleep(0.05)
            except Exception as e:
                print(f"Error crawling Telegram channel {ch} page {page}: {e}")
                break
            
    print(f"Gathered {len(comments)} messages from {len(ch_list)} Telegram channel(s).")
    return comments

def parse_time_slot(time_str):
    if not time_str: return "盤後夜間"
    match = re.search(r'(\d{2}):(\d{2})', time_str)
    if not match: return "盤後夜間"
    hour = int(match.group(1))
    minute = int(match.group(2))
    total_min = hour * 60 + minute
    
    if 540 <= total_min <= 630: # 09:00 - 10:30
        return "早盤開盤"
    elif 630 < total_min <= 780: # 10:30 - 13:00
        return "盤中震盪"
    elif 780 < total_min <= 870: # 13:00 - 14:30
        return "尾盤收盤"
    else:
        return "盤後夜間"

def analyze(comments, stocks, valuations, sectors, price_data, inst_data, inst_summary, margin_data, margin_summary):
    stats = {}
    code_pattern = re.compile(r'\b\d{4}\b')
    name_to_code = {v: k for k, v in stocks.items()}
    price_pattern = re.compile(r'(?:上看|目標|站上|停損|關卡|進場|目標價|買在|賣在|看)\s*(\d{3,5})|(\d{3,5})\s*(?:元|塊|上看|目標)')
    
    global_pos = 0
    global_neg = 0
    global_und = 0
    global_hyp = 0
    global_panic = 0
    global_sarcasm = 0
    
    foreign_pos, foreign_neg = 0, 0
    trust_pos, trust_neg = 0, 0
    
    timeline_stats = {
        "早盤開盤": {"Pos": 0, "Neg": 0},
        "盤中震盪": {"Pos": 0, "Neg": 0},
        "尾盤收盤": {"Pos": 0, "Neg": 0},
        "盤後夜間": {"Pos": 0, "Neg": 0}
    }
    
    for c in comments:
        user = c["user"]
        text = c["content"]
        time_slot = parse_time_slot(c.get("time", ""))
        
        matched = set()
        for code in code_pattern.findall(text):
            if code in stocks: matched.add(f"{stocks[code]} ({code})")
        for name, code in name_to_code.items():
            if len(name) <= 2:
                if name == "大立" and ("大立光" in text or "大力光" in text or "大力" in text):
                    continue
                if name == "長榮" and ("長榮航" in text or "長榮航空" in text):
                    continue
                if name == "聯發" and ("聯發科" in text or "發哥" in text):
                    continue
                if name == "幸福" and not any(k in text for k in ["1108", "水泥", "幸福水泥", "幸福股", "買幸福", "賣幸福", "幸福1108"]):
                    continue
                if name == "第一" and not any(k in text for k in ["2892", "2706", "第一金", "第一店", "買第一", "賣第一"]):
                    continue
                if name == "世界" and not any(k in text for k in ["5347", "世界先進", "晶圓", "代工", "買世界", "賣世界"]):
                    continue
                if name == "大量" and not any(k in text for k in ["3167", "大量科技", "買大量", "賣大量"]):
                    continue
                if name == "統一" and any(k in text for k in ["統一發票", "統一編號", "統一回答", "統一說明", "統一發布", "統一標準", "統一整理", "統一規定"]) and not any(k in text for k in ["1216", "2855", "統一超", "統一金", "統一證", "買統一", "賣統一", "統一企業"]):
                    continue
                if name == "冠軍" and any(k in text for k in ["總冠軍", "世界冠軍", "拿冠軍", "冠軍賽", "衛冕冠軍"]) and not any(k in text for k in ["1806", "冠軍建", "買冠軍", "賣冠軍"]):
                    continue
                if name == "大同" and any(k in text for k in ["大同小異", "世界大同", "大同區"]) and not any(k in text for k in ["2371", "大同股", "買大同", "賣大同", "大同電"]):
                    continue
                if name == "巨大" and not any(k in text for k in ["9921", "捷安特", "自行車", "巨大股", "買巨大", "賣巨大"]):
                    continue
                if name == "全家" and any(k in text for k in ["全家大小", "全家人", "全家福", "祝全家", "全家平安"]) and not any(k in text for k in ["5903", "超商", "便利商店", "全家超商", "買全家", "賣全家"]):
                    continue
                if name == "世紀" and any(k in text for k in ["21世紀", "本世紀", "世紀大災難", "世紀帝國", "世紀之戰"]) and not any(k in text for k in ["5314", "9958", "世紀鋼", "買世紀", "賣世紀"]):
                    continue
                if name == "新興" and any(k in text for k in ["新興市場", "新興國家", "新興產業", "新興科技"]) and not any(k in text for k in ["2605", "新興航", "買新興", "賣新興"]):
                    continue
                if name == "陸海" and any(k in text for k in ["陸海空", "陸海運"]) and not any(k in text for k in ["5603", "買陸海", "賣陸海"]):
                    continue
                if name == "無敵" and not any(k in text for k in ["8201", "無敵科", "無敵科技", "無敵股", "買無敵", "賣無敵"]):
                    continue
                if name == "安心" and not any(k in text for k in ["1259", "摩斯", "安心食品", "安心股", "買安心", "賣安心"]):
                    continue
                if name == "數字" and not any(k in text for k in ["5287", "數字科技", "591", "數字股", "買數字", "賣數字"]):
                    continue
                if name == "地球" and not any(k in text for k in ["1324", "地球膠帶", "地球股", "買地球", "賣地球"]):
                    continue
                if name == "三星" and (any(k in text for k in ["韓國", "samsung", "Samsung", "SAMSUNG", "良率", "晶圓", "HBM", "手機", "面板", "三爽"]) or not any(k in text for k in ["5007", "三星科技", "三星螺帽", "買三星", "賣三星"])):
                    continue
                if name == "聯合" and any(k in text for k in ["聯合國", "聯合報", "聯合聲明", "聯合陣線", "聯合稽查", "聯合壟斷"]) and not any(k in text for k in ["4129", "聯合骨科", "買聯合", "賣聯合"]):
                    continue
                if name == "進階" and not any(k in text for k in ["3118", "進階生技", "買進階", "賣進階"]):
                    continue
                if name == "全新" and any(k in text for k in ["全新推出", "全新概念", "全新的", "全新上市", "全新改版", "全新設計", "全新體驗"]) and not any(k in text for k in ["2455", "PA", "砷化鎵", "磊晶", "全新光電", "買全新", "賣全新"]):
                    continue
                if name == "大成" and "大成鋼" in text:
                    continue
                if name == "中華" and any(k in text for k in ["中華電", "中華隊", "中華民國", "中華航", "中華職棒", "中華電信"]):
                    continue
                if name == "有益" and any(k in text for k in ["有益健康", "有益無害", "相當有益", "大有益"]) and not any(k in text for k in ["9962", "買有益", "賣有益"]):
                    continue
            if name in text: matched.add(f"{name} ({code})")
        for nick, full in CUSTOM_NICKNAMES.items():
            if nick in text: matched.add(full)
            
        if not matched: continue
        
        def count_words(words, text):
            return sum(1 for w in words if w in text)

        pos = count_words(POSITIVE_WORDS, text)
        neg = count_words(NEGATIVE_WORDS, text)
        und = count_words(UNDERVALUED_WORDS, text)
        hyp = count_words(HYPE_WORDS, text)
        fund = count_words(FUNDAMENTAL_WORDS, text)
        panic = count_words(PANIC_WORDS, text)
        sarcasm = count_words(SARCASM_WORDS, text)
        
        global_pos += pos
        global_neg += neg
        global_und += und
        global_hyp += hyp
        global_panic += panic
        global_sarcasm += sarcasm
        
        timeline_stats[time_slot]["Pos"] += pos
        timeline_stats[time_slot]["Neg"] += neg
        
        if any(w in text for w in FOREIGN_WORDS):
            if pos > neg: foreign_pos += 1
            elif neg > pos: foreign_neg += 1
        if any(w in text for w in TRUST_WORDS):
            if pos > neg: trust_pos += 1
            elif neg > pos: trust_neg += 1
            
        prices = []
        for p in price_pattern.findall(text):
            val = p[0] or p[1]
            if val:
                num = int(val)
                if 10 <= num <= 4000:
                    prices.append(num)
                    
        events = set()
        for kw, tag in EVENT_RULES.items():
            if kw in text:
                idx = text.find(kw)
                preceding = text[max(0, idx-3):idx]
                following = text[idx+len(kw):min(len(text), idx+len(kw)+3)]
                
                # Filter out hypothetical or negative statements like "會漲停嗎", "沒漲停", "不漲停", "假漲停"
                if any(n in preceding for n in ["不", "沒", "未", "假", "想", "會", "能", "希望"]):
                    if tag in ("漲停鎖死", "跌停鎖死", "違約交割", "漲停板", "跌停板"):
                        continue
                if any(n in following for n in ["嗎", "呢", "吧", "算嗎", "假"]):
                    if tag in ("漲停鎖死", "跌停鎖死", "違約交割", "漲停板", "跌停板"):
                        continue
                events.add(tag)
        
        for key in matched:
            if "分析師" in key or "航運股" in key or "面板" in key: continue
            
            code_match = re.search(r'\((\d{4})\)', key)
            code = code_match.group(1) if code_match else ""
            
            if key not in stats:
                stats[key] = {
                    "Code": code, "Mentions": 0, "Users": set(), "UserCounts": {},
                    "Pos": 0, "Neg": 0, "Und": 0, "Hyp": 0, "Fund": 0, "Panic": 0, "Sarcasm": 0,
                    "TargetPrices": [], "Events": set(), "Keywords": {}, "Comments": []
                }
                
            st = stats[key]
            st["Mentions"] += 1
            st["Users"].add(user)
            st["UserCounts"][user] = st["UserCounts"].get(user, 0) + 1
            st["Pos"] += pos
            st["Neg"] += neg
            st["Und"] += und
            st["Hyp"] += hyp
            st["Fund"] += fund
            st["Panic"] += panic
            st["Sarcasm"] += sarcasm
            st["TargetPrices"].extend(prices)
            st["Events"].update(events)
            
            for w in POSITIVE_WORDS + NEGATIVE_WORDS + UNDERVALUED_WORDS + HYPE_WORDS + FUNDAMENTAL_WORDS + SARCASM_WORDS:
                if w in text:
                    st["Keywords"][w] = st["Keywords"].get(w, 0) + 1
                    
            if len(st["Comments"]) < 25:
                st["Comments"].append({"user": user, "text": text, "time": c.get("time", "")})

    results = []
    for key, data in stats.items():
        unique_users = len(data["Users"])
        top_user_mentions = max(data["UserCounts"].values()) if data["UserCounts"] else 0
        concentration = top_user_mentions / data["Mentions"] if data["Mentions"] > 0 else 0
        
        capped_mentions = sum(min(count, 3) for count in data["UserCounts"].values())
        
        score = (capped_mentions * 2 + unique_users * 3 + data["Pos"] * 2 + 
                 data["Und"] * 5 - data["Neg"] * 2 - data["Hyp"] * 2 + data["Fund"] * 3)
                 
        val = valuations.get(data["Code"], {})
        sector = sectors.get(data["Code"], "其他")
        p_info = price_data.get(data["Code"], {})
        inst = inst_data.get(data["Code"], {})
        m_info = margin_data.get(data["Code"], {})
        
        avg_target = "-"
        if data["TargetPrices"]:
            avg_target = str(int(sum(data["TargetPrices"]) / len(data["TargetPrices"])))
            
        sorted_kw = sorted(data["Keywords"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_keywords = [k for k, v in sorted_kw]
        
        risk = []
        if data["Hyp"] >= 2: risk.append("炒作詞多")
        if concentration >= 0.5 and data["Mentions"] >= 3: risk.append("集中度高(防洗版)")
        if data["Neg"] > data["Pos"]: risk.append("偏負面")
        if data["Panic"] >= 2: risk.append("恐慌恐慌")
        if data["Sarcasm"] >= 2: risk.append("反串/迷因熱議")
        
        f_net = inst.get("ForeignNet", "-")
        t_net = inst.get("TrustNet", "-")
        m_diff = m_info.get("MarginDiff", "-")
        s_diff = m_info.get("ShortDiff", "-")
        
        # Chip Signal Engine (散戶情緒 vs 主力法人 & 融資券對抗訊號)
        chip_signal = "⚖️ 散戶與法人動向平衡"
        try:
            fn = int(f_net) if f_net != "-" else 0
            tn = int(t_net) if t_net != "-" else 0
            md = int(m_diff) if m_diff != "-" else 0
            
            if fn > 500 and tn > 0 and data["Neg"] >= data["Pos"]:
                chip_signal = "🟢 土洋合買 ✕ 散戶看空 (潛在軋空強多)"
            elif fn < -1500 and data["Pos"] > data["Neg"]:
                chip_signal = "🔴 外資大出貨 ✕ 散戶追高 (散戶套牢警報)"
            elif md > 800 and data["Pos"] > data["Neg"]:
                chip_signal = "⚠️ 融資暴增 ✕ 散戶狂熱 (籌碼過熱浮額多)"
            elif md < -300 and fn > 300:
                chip_signal = "💎 融資大減 ✕ 外資回補 (洗盤吸籌完畢)"
            elif fn > 1000 and tn > 200:
                chip_signal = "🔥 土洋法人同步重押"
            elif fn < -1000 and tn < -200:
                chip_signal = "❄️ 土洋法人雙向提款"
            elif data["Sarcasm"] >= 3:
                chip_signal = "🎭 鄉民反串迷因狂熱"
        except Exception:
            pass
            
        tot_sent = max(1, data["Pos"] + data["Neg"] + data["Sarcasm"])
        pos_pct = int((data["Pos"] / tot_sent) * 100)
        neg_pct = int((data["Neg"] / tot_sent) * 100)
        sarcasm_pct = int((data["Sarcasm"] / tot_sent) * 100)
        
        results.append({
            "Stock": key,
            "Code": data["Code"],
            "Sector": sector,
            "Score": round(score, 1),
            "Price": p_info.get("Price", "-"),
            "Change": p_info.get("Change", "-"),
            "ChangePercent": p_info.get("ChangePercent", "-"),
            "ForeignNet": f_net,
            "TrustNet": t_net,
            "TotalNet": inst.get("TotalNet", "-"),
            "MarginDiff": m_diff,
            "MarginBalance": m_info.get("MarginBalance", "-"),
            "ShortDiff": s_diff,
            "ShortBalance": m_info.get("ShortBalance", "-"),
            "ChipSignal": chip_signal,
            "BullishRatio": f"{pos_pct}%",
            "BearishRatio": f"{neg_pct}%",
            "SarcasmRatio": f"{sarcasm_pct}%",
            "Mentions": data["Mentions"],
            "UniqueUsers": unique_users,
            "PE": val.get("PE", "-"),
            "PB": val.get("PB", "-"),
            "Yield": val.get("Yield", "-"),
            "Concentration": f"{int(concentration*100)}%",
            "AvgTargetPrice": avg_target,
            "Events": list(data["Events"]),
            "TopKeywords": top_keywords,
            "Risk": "、".join(risk) if risk else "無",
            "Keywords": data["Keywords"],
            "Comments": data["Comments"]
        })
        
    sorted_results = sorted(results, key=lambda x: x["Score"], reverse=True)
    
    total_greed = global_pos + global_hyp
    total_fear = global_neg + global_und
    fear_greed_index = 50 if (total_greed + total_fear == 0) else int((total_greed / (total_greed + total_fear)) * 100)
    
    base_panic_ratio = (global_panic / max(1, global_pos + global_neg + global_panic))
    panic_index = min(100, max(5, int(base_panic_ratio * 300 + (global_panic * 0.4))))
    
    sector_stats = {}
    for r in sorted_results:
        s = r["Sector"]
        if s not in sector_stats:
            sector_stats[s] = {"Mentions": 0, "TotalScore": 0, "Count": 0, "TopStocks": []}
        sector_stats[s]["Mentions"] += r["Mentions"]
        sector_stats[s]["TotalScore"] += r["Score"]
        sector_stats[s]["Count"] += 1
        if len(sector_stats[s]["TopStocks"]) < 3:
            sector_stats[s]["TopStocks"].append(r["Stock"].split(" ")[0])
            
    sector_rotation = []
    for s, data in sector_stats.items():
        if s == "其他" and len(sector_stats) > 1: continue
        sector_rotation.append({
            "Sector": s,
            "Mentions": data["Mentions"],
            "AvgScore": round(data["TotalScore"] / data["Count"], 1),
            "TopStocks": data["TopStocks"]
        })
    sector_rotation = sorted(sector_rotation, key=lambda x: x["Mentions"], reverse=True)[:5]
    
    summary_parts = []
    if fear_greed_index >= 70:
        summary_parts.append(f"🔥 市場情緒目前處於【極度貪婪】({fear_greed_index}分)，多數鄉民強力看好後市，請留意追高與大盤反轉風險。")
    elif fear_greed_index <= 30:
        summary_parts.append(f"❄️ 市場情緒目前處於【極度恐懼】({fear_greed_index}分)，恐慌與停損言論激增，可留意超跌後的地板反彈契機。")
    else:
        summary_parts.append(f"⚖️ 市場情緒目前【中立震盪】({fear_greed_index}分)，多空雙方力道均衡。")
        
    if panic_index >= 60:
        summary_parts.append(f"🚨 警報：絕望/畢業指數偏高({panic_index}分)，散戶停損潮湧現！")
        
    if sector_rotation:
        top_sector = sector_rotation[0]
        top_stocks = "、".join(top_sector["TopStocks"])
        summary_parts.append(f"資金與討論度高度集中在【{top_sector['Sector']}】，其中以 {top_stocks} 最受矚目。")
        
    # Theme & Sector Momentum Alert Engine (族群與熱門概念題材異動監控)
    theme_stats = []
    sector_alerts = []
    for theme_name, codes in HOT_THEMES.items():
        theme_pcts = []
        theme_mentions = 0
        up_cnt, down_cnt, limit_up_cnt, limit_down_cnt = 0, 0, 0, 0
        top_constituents = []
        for code in codes:
            p_inf = price_data.get(code, {})
            chg_pct_str = p_inf.get("ChangePercent", "-")
            stock_name = stocks.get(code, code)
            try:
                pct_val = float(chg_pct_str.replace("%", "").replace("+", ""))
                theme_pcts.append(pct_val)
                if pct_val > 0: up_cnt += 1
                elif pct_val < 0: down_cnt += 1
                if pct_val >= 9.5: limit_up_cnt += 1
                elif pct_val <= -9.5: limit_down_cnt += 1
                top_constituents.append({
                    "stock": f"{stock_name} ({code})",
                    "price": p_inf.get("Price", "-"),
                    "changePercent": chg_pct_str,
                    "pct_val": pct_val
                })
            except:
                pass
            
            st_key = f"{stock_name} ({code})"
            if st_key in stats:
                theme_mentions += stats[st_key]["Mentions"]
                
        avg_pct = round(sum(theme_pcts) / len(theme_pcts), 2) if theme_pcts else 0.0
        avg_pct_str = f"+{avg_pct:.2f}%" if avg_pct > 0 else f"{avg_pct:.2f}%"
        
        alert_tag = "⚖️ 平穩震盪"
        if avg_pct >= 2.0 or limit_up_cnt >= 1:
            alert_tag = "🚀 族群齊揚強攻"
            sector_alerts.append({
                "theme": theme_name,
                "type": "surge",
                "avgChange": avg_pct_str,
                "alert": alert_tag,
                "topStocks": [f"{s['stock']}: ${s['price']} ({s['changePercent']})" for s in sorted(top_constituents, key=lambda x: x["pct_val"], reverse=True)[:3]]
            })
        elif avg_pct <= -1.8 or limit_down_cnt >= 1:
            alert_tag = "💥 族群重挫跳水"
            sector_alerts.append({
                "theme": theme_name,
                "type": "drop",
                "avgChange": avg_pct_str,
                "alert": alert_tag,
                "topStocks": [f"{s['stock']}: ${s['price']} ({s['changePercent']})" for s in sorted(top_constituents, key=lambda x: x["pct_val"])[:3]]
            })
        elif theme_mentions >= 20:
            alert_tag = "🔥 資金社群熱議"
            sector_alerts.append({
                "theme": theme_name,
                "type": "hot",
                "avgChange": avg_pct_str,
                "alert": alert_tag,
                "topStocks": [f"{s['stock']}: ${s['price']} ({s['changePercent']})" for s in top_constituents[:3]]
            })
            
        theme_stats.append({
            "Theme": theme_name,
            "AvgChange": avg_pct_str,
            "AvgChangeVal": avg_pct,
            "Alert": alert_tag,
            "UpCount": up_cnt,
            "DownCount": down_cnt,
            "Mentions": theme_mentions,
            "TopStocks": [f"{s['stock']} ({s['changePercent']})" for s in sorted(top_constituents, key=lambda x: x["pct_val"], reverse=True)[:3]]
        })
        
    theme_stats = sorted(theme_stats, key=lambda x: x["AvgChangeVal"], reverse=True)
    
    taiex_info = get_taiex_info()
    taiex_trend = get_taiex_intraday_trend()
    
    market_data = {
        "FearGreedIndex": fear_greed_index,
        "PanicIndex": panic_index,
        "TotalCommentsParsed": len(comments),
        "TAIEXSummary": taiex_info,
        "TAIEXIntradayTrend": taiex_trend,
        "RealInstitutionalStats": inst_summary,
        "MarginSummary": margin_summary,
        "SectorAlerts": sector_alerts,
        "ThemeStats": theme_stats,
        "InstitutionalSentiment": {
            "ForeignBullish": foreign_pos, "ForeignBearish": foreign_neg,
            "TrustBullish": trust_pos, "TrustBearish": trust_neg
        },
        "TimelineSentiment": timeline_stats,
        "SectorRotation": sector_rotation,
        "MarketSummary": " ".join(summary_parts)
    }
    
    # Generate AI / Sarcasm Summary
    ai_summary = get_ai_market_summary(sorted_results, market_data, taiex_info)
    market_data["AISummary"] = ai_summary
        
    return sorted_results, market_data

def generate_tg_digest(results, market_data):
    today = time.strftime("%Y-%m-%d")
    taiex = market_data.get("TAIEXSummary", {})
    inst_amt = market_data.get("RealInstitutionalStats", {}).get("Amounts", {})
    margin_s = market_data.get("MarginSummary", {})
    sector_alerts = market_data.get("SectorAlerts", [])
    
    f_amt = inst_amt.get("Foreign", {}).get("net", "-")
    t_amt = inst_amt.get("Trust", {}).get("net", "-")
    d_amt = inst_amt.get("Dealer", {}).get("net", "-")
    tot_amt = inst_amt.get("Total", {}).get("net", "-")
    
    m_bal = margin_s.get("MarginBalance", "-")
    m_diff = margin_s.get("MarginDiff", "-")
    m_shares = margin_s.get("MarginSharesDiff", 0)
    s_shares = margin_s.get("ShortSharesDiff", 0)
    m_shares_str = f"{m_shares:+d}張" if isinstance(m_shares, int) else str(m_shares)
    s_shares_str = f"{s_shares:+d}張" if isinstance(s_shares, int) else str(s_shares)
    
    gh_pages_url = os.environ.get("GITHUB_PAGES_URL", "https://smallta.github.io/ptt-stock-war-room/")
    
    lines = [
        f"📊 【PTT 戰情室 · 今日盤後情報總結】 ({today})\n",
        f"📈 今日大盤加權指數：{taiex.get('TAIEX', '-')} 點 ({taiex.get('Change', '-')} / {taiex.get('ChangePercent', '-')})",
        f"🚨 絕望/畢業反向指標：{market_data.get('PanicIndex', 0)} 分 (越高代表散戶洗盤越乾淨)\n",
        "🏛️ 三大法人買賣金額 (證交所官方)：",
        f"- 外資：{f_amt} ｜ 投信：{t_amt} ｜ 自營商：{d_amt}",
        f"- 三大法人合計：{tot_amt}",
        f"- 信用交易融資：{m_bal} (增減 {m_diff} / {m_shares_str})",
        f"- 信用交易融券：增減 {s_shares_str}\n",
    ]
    
    if sector_alerts:
        lines.append("🚨 【今日焦點族群異動警報】")
        for sa in sector_alerts:
            lines.append(f"- {sa['theme']} 【{sa['alert']} · 平均 {sa['avgChange']}】")
            lines.append(f"  指標成分股: {', '.join(sa['topStocks'])}\n")
            
    lines.append("🔥 鄉民熱門焦點標的與籌碼對抗訊號 Top 5：")
    for idx, r in enumerate(results[:5], 1):
        chg_icon = "🔴" if str(r.get("Change", "")).startswith("+") else ("🟢" if str(r.get("Change", "")).startswith("-") else "⚪")
        m_diff_val = r.get('MarginDiff', '-')
        m_diff_str = f"{m_diff_val:+d}張" if isinstance(m_diff_val, int) else f"{m_diff_val}張"
        lines.append(f"{idx}. {r['Stock']} | 評分 {r['Score']}")
        lines.append(f"   收盤: ${r['Price']} {chg_icon} ({r['ChangePercent']}) | 外資: {r['ForeignNet']}張 | 投信: {r['TrustNet']}張 | 融資: {m_diff_str}")
        lines.append(f"   籌碼訊號: {r.get('ChipSignal', '無')}")
        lines.append(f"   情報Tag: {r['Risk']}\n")
        
    if market_data.get("AISummary"):
        lines.append(f"🤖 【AI 深度情報解讀】：\n{market_data.get('AISummary')}\n")
        
    lines.append(f"💡 戰情總結：{market_data.get('MarketSummary', '')}")
    lines.append(f"\n👉 查看完整視覺化儀表板: {gh_pages_url}")
    
    digest_text = "\n".join(lines)
    with open("tg_digest_report.txt", "w", encoding="utf-8") as f:
        f.write(digest_text)
        
    # Auto-send if Telegram tokens are available
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or "8837287745:AAGq7-ZQKt_PwzowODDbpc4pzdDhoyfcw1k"
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or "1815627011"
    if bot_token and chat_id:
        try:
            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(tg_url, json={"chat_id": chat_id, "text": digest_text}, timeout=10)
            print("✅ 已自動推播最新戰情報告至 Telegram！")
        except Exception as e:
            print(f"⚠️ Telegram 自動推播略過: {e}")
            
    return digest_text

def main():
    print("Fetching Chat URLs...")
    urls = find_chat_urls()
    print(f"Found {len(urls)} chat articles.")
    
    all_comments = []
    for u in urls:
        all_comments.extend(crawl_comments(u))
        
    tg_comments = crawl_telegram_chat()
    all_comments.extend(tg_comments)
        
    stocks, valuations, sectors, price_data = get_stocks()
    inst_data, inst_summary = get_institutional_data()
    margin_data, margin_summary = get_margin_data()
    
    res, market_data = analyze(all_comments, stocks, valuations, sectors, price_data, inst_data, inst_summary, margin_data, margin_summary)
    
    generate_tg_digest(res, market_data)
    
    if len(res) == 0:
        print("⚠️ 警告：本次抓取未比對出熱門標的，啟動安全防護機制，保留前次完整標的與歷程數據！")
    else:
        csv_data = [{k: (", ".join(v) if isinstance(v, list) else v) for k, v in r.items() if k not in ("Keywords", "Comments", "Code")} for r in res]
        df = pd.DataFrame(csv_data)
        df.to_csv("hot_stocks_sentiment.csv", index=False, encoding="utf-8-sig")
        
        with open("detail_data.json", "w", encoding="utf-8") as f:
            json.dump({r["Stock"]: {"Keywords": r["Keywords"], "Comments": r["Comments"]} for r in res}, f, ensure_ascii=False, indent=2)
            
        # 7-Day History Snapshot
        today_str = time.strftime("%Y-%m-%d")
        history_file = "history_data.json"
        history = {}
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except: pass
            
        today_snapshot = {r["Stock"]: {"Score": r["Score"], "Mentions": r["Mentions"]} for r in res[:40]}
        history[today_str] = today_snapshot
        dates = sorted(history.keys())[-7:]
        history = {d: history[d] for d in dates}
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        # Generate dashboard/data.js for zero-server local opening
        detail_dict = {r["Stock"]: {"Keywords": r["Keywords"], "Comments": r["Comments"]} for r in res}
        data_js_content = f"""window.MARKET_DATA = {json.dumps(market_data, ensure_ascii=False)};
window.HOT_STOCKS_DATA = {json.dumps(csv_data, ensure_ascii=False)};
window.DETAIL_DATA = {json.dumps(detail_dict, ensure_ascii=False)};
window.HISTORY_DATA = {json.dumps(history, ensure_ascii=False)};
"""
        with open("dashboard/data.js", "w", encoding="utf-8") as f:
            f.write(data_js_content)

    with open("market_data.json", "w", encoding="utf-8") as f:
        json.dump(market_data, f, ensure_ascii=False, indent=2)

    print("✅ 分析完成！已同步產生數據與 7 天歷程至 dashboard/data.js。")

if __name__ == "__main__":
    main()
