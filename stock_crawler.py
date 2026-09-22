import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import time

# PTT Stock Board configuration
PTT_URL = "https://www.ptt.cc"
STOCK_BOARD_URL = f"{PTT_URL}/bbs/Stock/index.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}
COOKIES = {"over18": "1"}

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
            res = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=10)
            if res.status_code == 200:
                return res.json() if is_json else res.text
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

def crawl_telegram_chat():
    print("Fetching Telegram Chat Channel (t.me/s/ptt_stock_follow_chat)...")
    comments = []
    try:
        url = "https://t.me/s/ptt_stock_follow_chat"
        html = safe_get(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            msgs = soup.find_all("div", class_="js-message_text")
            for m in msgs:
                text = m.text.strip()
                if "：" in text:
                    parts = text.split("：", 1)
                    user_str = parts[0].strip().replace("\n", " ")
                    content_str = parts[1].strip()
                    comments.append({
                        "user": f"📱 [TG] {user_str}",
                        "content": content_str,
                        "time": "TG即時推播"
                    })
                else:
                    comments.append({
                        "user": "📱 [TG推播]",
                        "content": text,
                        "time": "TG即時推播"
                    })
    except Exception as e:
        print(f"Error crawling Telegram channel: {e}")
    print(f"Found {len(comments)} messages from Telegram.")
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

def analyze(comments, stocks, valuations, sectors, price_data, inst_data, inst_summary):
    stats = {}
    code_pattern = re.compile(r'\b\d{4}\b')
    name_to_code = {v: k for k, v in stocks.items()}
    price_pattern = re.compile(r'(?:上看|目標|站上|停損|關卡|進場|目標價|買在|賣在|看)\s*(\d{3,5})|(\d{3,5})\s*(?:元|塊|上看|目標)')
    
    global_pos = 0
    global_neg = 0
    global_und = 0
    global_hyp = 0
    global_panic = 0
    
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
        
        global_pos += pos
        global_neg += neg
        global_und += und
        global_hyp += hyp
        global_panic += panic
        
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
                    "Pos": 0, "Neg": 0, "Und": 0, "Hyp": 0, "Fund": 0, "Panic": 0,
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
            st["TargetPrices"].extend(prices)
            st["Events"].update(events)
            
            for w in POSITIVE_WORDS + NEGATIVE_WORDS + UNDERVALUED_WORDS + HYPE_WORDS + FUNDAMENTAL_WORDS:
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
        
        results.append({
            "Stock": key,
            "Code": data["Code"],
            "Sector": sector,
            "Score": round(score, 1),
            "Price": p_info.get("Price", "-"),
            "Change": p_info.get("Change", "-"),
            "ChangePercent": p_info.get("ChangePercent", "-"),
            "ForeignNet": inst.get("ForeignNet", "-"),
            "TrustNet": inst.get("TrustNet", "-"),
            "TotalNet": inst.get("TotalNet", "-"),
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
        
    taiex_info = get_taiex_info()
    taiex_trend = get_taiex_intraday_trend()
    market_data = {
        "FearGreedIndex": fear_greed_index,
        "PanicIndex": panic_index,
        "TotalCommentsParsed": len(comments),
        "TAIEXSummary": taiex_info,
        "TAIEXIntradayTrend": taiex_trend,
        "RealInstitutionalStats": inst_summary,
        "InstitutionalSentiment": {
            "ForeignBullish": foreign_pos, "ForeignBearish": foreign_neg,
            "TrustBullish": trust_pos, "TrustBearish": trust_neg
        },
        "TimelineSentiment": timeline_stats,
        "SectorRotation": sector_rotation,
        "MarketSummary": " ".join(summary_parts)
    }
        
    return sorted_results, market_data

def generate_tg_digest(results, market_data):
    today = time.strftime("%Y-%m-%d")
    taiex = market_data.get("TAIEXSummary", {})
    inst_amt = market_data.get("RealInstitutionalStats", {}).get("Amounts", {})
    
    f_amt = inst_amt.get("Foreign", {}).get("net", "-")
    t_amt = inst_amt.get("Trust", {}).get("net", "-")
    d_amt = inst_amt.get("Dealer", {}).get("net", "-")
    tot_amt = inst_amt.get("Total", {}).get("net", "-")
    
    lines = [
        f"📊 【PTT 戰情室 · 今日盤後情報總結】 ({today})\n",
        f"📈 今日大盤加權指數：{taiex.get('TAIEX', '-')} 點 ({taiex.get('Change', '-')} / {taiex.get('ChangePercent', '-')})",
        f"🚨 絕望/畢業反向指標：{market_data.get('PanicIndex', 0)} 分\n",
        "🏛️ 三大法人買賣金額 (證交所官方)：",
        f"- 外資：{f_amt} ｜ 投信：{t_amt} ｜ 自營商：{d_amt}",
        f"- 三大法人合計：{tot_amt}\n",
        "🔥 鄉民熱門焦點標的 Top 5："
    ]
    
    for idx, r in enumerate(results[:5], 1):
        chg_icon = "🔴" if str(r.get("Change", "")).startswith("+") else ("🟢" if str(r.get("Change", "")).startswith("-") else "⚪")
        lines.append(f"{idx}. {r['Stock']} | 評分 {r['Score']}")
        lines.append(f"   收盤: ${r['Price']} {chg_icon} ({r['ChangePercent']}) | 外資: {r['ForeignNet']}張 | 投信: {r['TrustNet']}張")
        lines.append(f"   情報Tag: {r['Risk']}\n")
        
    lines.append(f"💡 戰情總結：{market_data.get('MarketSummary', '')}")
    lines.append("\n👉 查看完整視覺化儀表板: http://localhost:8520/dashboard/index.html")
    
    digest_text = "\n".join(lines)
    with open("tg_digest_report.txt", "w", encoding="utf-8") as f:
        f.write(digest_text)
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
    res, market_data = analyze(all_comments, stocks, valuations, sectors, price_data, inst_data, inst_summary)
    
    generate_tg_digest(res, market_data)
    
    csv_data = [{k: (", ".join(v) if isinstance(v, list) else v) for k, v in r.items() if k not in ("Keywords", "Comments", "Code")} for r in res]
    df = pd.DataFrame(csv_data)
    df.to_csv("hot_stocks_sentiment.csv", index=False, encoding="utf-8-sig")
    
    with open("detail_data.json", "w", encoding="utf-8") as f:
        json.dump({r["Stock"]: {"Keywords": r["Keywords"], "Comments": r["Comments"]} for r in res}, f, ensure_ascii=False, indent=2)
        
    with open("market_data.json", "w", encoding="utf-8") as f:
        json.dump(market_data, f, ensure_ascii=False, indent=2)
        
    # 7-Day History Snapshot
    import os
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

    print("✅ 分析完成！已同步產生數據與 7 天歷程至 dashboard/data.js。")

if __name__ == "__main__":
    main()
