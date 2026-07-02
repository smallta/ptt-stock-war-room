import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# PTT Stock Board configuration
PTT_URL = "https://www.ptt.cc"
STOCK_BOARD_URL = f"{PTT_URL}/bbs/Stock/index.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
    "大G": "大立光 (3008)", "星宇": "星宇航空 (2646)"
}

POSITIVE_WORDS = ["低估", "便宜", "超跌", "打底", "轉強", "轉機", "突破", "成長", "利多", "買", "加碼", "看好", "殖利率", "配息", "營收", "獲利", "噴", "賺", "舒服"]
NEGATIVE_WORDS = ["高估", "太貴", "套", "爛", "跌", "崩", "利空", "賣", "空", "減碼", "看壞", "虧", "衰退", "泡沫", "出貨", "破底", "丸子", "綠"]
UNDERVALUED_WORDS = ["低估", "便宜", "本益比低", "淨值比低", "殖利率", "配息", "超跌", "價值", "被錯殺", "低基期"]
HYPE_WORDS = ["噴", "飆", "妖", "歐印", "all in", "ALL IN", "無腦", "上車", "嘎", "火箭", "目標價"]
FUNDAMENTAL_WORDS = ["營收", "法說", "毛利", "財報", "EPS", "展望", "盈餘", "配息", "殖利率", "基本面", "淨利"]

def get_stocks():
    print("Fetching Stock lists and valuations...")
    stocks = {}
    valuations = {}
    
    # TWSE Prices
    try:
        r = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=10)
        for i in r.json():
            if len(i.get("Code", "")) == 4:
                stocks[i["Code"]] = i["Name"]
    except Exception as e: print("TWSE Price Error:", e)

    # TPEx Prices
    try:
        r = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes", timeout=10)
        for i in r.json():
            if len(i.get("SecuritiesCompanyCode", "")) == 4:
                stocks[i["SecuritiesCompanyCode"]] = i["CompanyName"]
    except Exception as e: print("TPEx Price Error:", e)

    # TWSE Valuations
    try:
        r = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL", timeout=10)
        for i in r.json():
            if len(i.get("Code", "")) == 4:
                valuations[i["Code"]] = {
                    "PE": i.get("PEratio", "-"),
                    "Yield": i.get("DividendYield", "-"),
                    "PB": i.get("PBratio", "-")
                }
    except Exception as e: print("TWSE Val Error:", e)

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
    try:
        r = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=10)
        for i in r.json():
            if len(i.get("公司代號", "")) == 4:
                code = i.get("產業別", "")
                sectors[i["公司代號"]] = twse_sector_map.get(code, code if code else "其他")
    except Exception as e: print("TWSE Sector Error:", e)
    
    # Fallback common sectors
    fallback_sectors = {
        "2330": "半導體業", "2454": "半導體業", "2303": "半導體業",
        "2603": "航運業", "2609": "航運業", "2615": "航運業",
        "2317": "其他電子業", "3231": "電腦及週邊設備業", "2382": "電腦及週邊設備業"
    }
    for k, v in fallback_sectors.items():
        if k not in sectors or sectors[k] in ("其他", ""): sectors[k] = v

    # TPEx Valuations
    try:
        r = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis", timeout=10)
        for i in r.json():
            if len(i.get("SecuritiesCompanyCode", "")) == 4:
                valuations[i["SecuritiesCompanyCode"]] = {
                    "PE": i.get("PriceEarningRatio", "-"),
                    "PB": i.get("PriceBookRatio", "-"),
                    "Yield": i.get("YieldRatio", "-")
                }
    except Exception as e: print("TPEx Val Error:", e)

    return stocks, valuations, sectors

def find_chat_urls():
    chat_urls = []
    current_url = STOCK_BOARD_URL
    for _ in range(3):
        res = requests.get(current_url, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")
        for entry in soup.find_all("div", class_="r-ent"):
            title_tag = entry.find("div", class_="title").find("a")
            if title_tag and ("盤中閒聊" in title_tag.text or "盤後閒聊" in title_tag.text):
                chat_urls.append(PTT_URL + title_tag["href"])
        paging = soup.find("div", class_="btn-group-paging")
        if paging:
            current_url = PTT_URL + paging.find_all("a")[1]["href"]
        else:
            break
    return list(set(chat_urls))

def crawl_comments(url):
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    comments = []
    for push in soup.find_all("div", class_="push"):
        uid_tag = push.find("span", class_=lambda c: c and "push-userid" in c)
        content_tag = push.find("span", class_="push-content")
        if uid_tag and content_tag:
            comments.append({
                "user": uid_tag.text.strip(),
                "content": content_tag.text.lstrip(": ")
            })
    return comments

def analyze(comments, stocks, valuations, sectors):
    stats = {}
    code_pattern = re.compile(r'\b\d{4}\b')
    name_to_code = {v: k for k, v in stocks.items()}
    
    global_pos = 0
    global_neg = 0
    global_und = 0
    global_hyp = 0
    
    for c in comments:
        user = c["user"]
        text = c["content"]
        
        matched = set()
        for code in code_pattern.findall(text):
            if code in stocks: matched.add(f"{stocks[code]} ({code})")
        for name, code in name_to_code.items():
            if name in text: matched.add(f"{name} ({code})")
        for nick, full in CUSTOM_NICKNAMES.items():
            if nick in text: matched.add(full)
            
        if not matched: continue
        
        def count_with_negation(words, text, is_negative_word=False):
            count = 0
            for w in words:
                idx = text.find(w)
                while idx != -1:
                    preceding = text[max(0, idx-2):idx]
                    has_neg = any(n in preceding for n in ["不", "沒", "未"])
                    
                    if has_neg:
                        if is_negative_word:
                            pass # "不跌" -> not negative
                        else:
                            pass # "不噴" -> not positive
                    else:
                        count += 1
                    idx = text.find(w, idx + len(w))
            return count

        pos = count_with_negation(POSITIVE_WORDS, text)
        neg = count_with_negation(NEGATIVE_WORDS, text, True)
        und = count_with_negation(UNDERVALUED_WORDS, text)
        hyp = count_with_negation(HYPE_WORDS, text)
        fund = count_with_negation(FUNDAMENTAL_WORDS, text)
        
        # Add to global sentiment
        global_pos += pos
        global_neg += neg
        global_und += und
        global_hyp += hyp
        
        for key in matched:
            if "分析師" in key or "航運股" in key or "面板" in key: continue
            
            code_match = re.search(r'\((\d{4})\)', key)
            code = code_match.group(1) if code_match else ""
            
            if key not in stats:
                stats[key] = {
                    "Code": code, "Mentions": 0, "Users": set(), "UserCounts": {},
                    "Pos": 0, "Neg": 0, "Und": 0, "Hyp": 0, "Fund": 0,
                    "Keywords": {}, "Comments": []
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
            
            # Track exact keywords
            for w in POSITIVE_WORDS + NEGATIVE_WORDS + UNDERVALUED_WORDS + HYPE_WORDS + FUNDAMENTAL_WORDS:
                if w in text:
                    st["Keywords"][w] = st["Keywords"].get(w, 0) + 1
                    
            # Keep up to 15 latest comments for context
            if len(st["Comments"]) < 15:
                st["Comments"].append({"user": user, "text": text})

    results = []
    for key, data in stats.items():
        unique_users = len(data["Users"])
        top_user_mentions = max(data["UserCounts"].values()) if data["UserCounts"] else 0
        concentration = top_user_mentions / data["Mentions"] if data["Mentions"] > 0 else 0
        
        # Cap mentions per user to prevent spam
        capped_mentions = sum(min(count, 3) for count in data["UserCounts"].values())
        
        score = (capped_mentions * 2 + unique_users * 3 + data["Pos"] * 2 + 
                 data["Und"] * 5 - data["Neg"] * 2 - data["Hyp"] * 2 + data["Fund"] * 3)
                 
        val = valuations.get(data["Code"], {})
        sector = sectors.get(data["Code"], "其他")
        
        risk = []
        if data["Hyp"] >= 2: risk.append("炒作詞多")
        if concentration >= 0.5 and data["Mentions"] >= 3: risk.append("集中度高(防洗版)")
        if data["Neg"] > data["Pos"]: risk.append("偏負面")
        
        results.append({
            "Stock": key,
            "Code": data["Code"],
            "Sector": sector,
            "Score": round(score, 1),
            "Mentions": data["Mentions"],
            "UniqueUsers": unique_users,
            "PE": val.get("PE", "-"),
            "PB": val.get("PB", "-"),
            "Yield": val.get("Yield", "-"),
            "Concentration": f"{int(concentration*100)}%",
            "Risk": "、".join(risk) if risk else "無",
            "Keywords": data["Keywords"],
            "Comments": data["Comments"]
        })
        
    sorted_results = sorted(results, key=lambda x: x["Score"], reverse=True)
    
    # Calculate Fear & Greed Index
    total_greed = global_pos + global_hyp
    total_fear = global_neg + global_und
    if total_greed + total_fear == 0:
        fear_greed_index = 50
    else:
        fear_greed_index = int((total_greed / (total_greed + total_fear)) * 100)
        
    # Aggregate by Sector
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
        if s == "其他" and len(sector_stats) > 1: continue # Skip if possible
        sector_rotation.append({
            "Sector": s,
            "Mentions": data["Mentions"],
            "AvgScore": round(data["TotalScore"] / data["Count"], 1),
            "TopStocks": data["TopStocks"]
        })
    sector_rotation = sorted(sector_rotation, key=lambda x: x["Mentions"], reverse=True)[:5]
    
    # Generate Rule-based AI Summary
    summary_parts = []
    if fear_greed_index >= 70:
        summary_parts.append(f"🔥 市場情緒目前處於【極度貪婪】({fear_greed_index}分)，多數鄉民強力看好後市，請留意追高與大盤反轉風險。")
    elif fear_greed_index >= 55:
        summary_parts.append(f"📈 市場情緒目前【偏向樂觀】({fear_greed_index}分)，散戶做多意願較高。")
    elif fear_greed_index <= 30:
        summary_parts.append(f"❄️ 市場情緒目前處於【極度恐懼】({fear_greed_index}分)，恐慌與停損言論激增，可留意超跌後的地板反彈契機。")
    elif fear_greed_index <= 45:
        summary_parts.append(f"📉 市場情緒目前【偏向悲觀】({fear_greed_index}分)，散戶信心不足，觀望氣氛濃厚。")
    else:
        summary_parts.append(f"⚖️ 市場情緒目前【中立震盪】({fear_greed_index}分)，多空雙方力道均衡。")
        
    if sector_rotation:
        top_sector = sector_rotation[0]
        top_stocks = "、".join(top_sector["TopStocks"])
        summary_parts.append(f"資金與討論度高度集中在【{top_sector['Sector']}】，其中以 {top_stocks} 最受矚目。")
        if len(sector_rotation) > 1:
            second_sector = sector_rotation[1]
            summary_parts.append(f"另外，【{second_sector['Sector']}】也出現了明顯的輪動跡象。")
            
    market_data = {
        "FearGreedIndex": fear_greed_index,
        "TotalCommentsParsed": len(comments),
        "SectorRotation": sector_rotation,
        "MarketSummary": " ".join(summary_parts)
    }
        
    return sorted_results, market_data

def main():
    print("Fetching Chat URLs...")
    urls = find_chat_urls()
    print(f"Found {len(urls)} chat articles.")
    
    all_comments = []
    for url in urls:
        all_comments.extend(crawl_comments(url))
        
    stocks, valuations, sectors = get_stocks()
    res, market_data = analyze(all_comments, stocks, valuations, sectors)
    
    # Separate CSV data and JSON detail data
    csv_data = [{k: v for k, v in r.items() if k not in ("Keywords", "Comments", "Code")} for r in res]
    df = pd.DataFrame(csv_data)
    df.to_csv("hot_stocks_sentiment.csv", index=False, encoding="utf-8-sig")
    
    import json
    with open("detail_data.json", "w", encoding="utf-8") as f:
        json.dump({r["Stock"]: {"Keywords": r["Keywords"], "Comments": r["Comments"]} for r in res}, f, ensure_ascii=False, indent=2)
        
    with open("market_data.json", "w", encoding="utf-8") as f:
        json.dump(market_data, f, ensure_ascii=False, indent=2)
        
    print("✅ 分析完成，已存至 hot_stocks_sentiment.csv, detail_data.json 與 market_data.json")

if __name__ == "__main__":
    main()
