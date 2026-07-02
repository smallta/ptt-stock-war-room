from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import csv
import os

app = FastAPI(title="Investment Signal API")

# Enable CORS for the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stocks")
def get_stocks():
    if not os.path.exists("hot_stocks_sentiment.csv"):
        raise HTTPException(status_code=404, detail="Data not found. Run crawler first.")
    
    results = []
    with open("hot_stocks_sentiment.csv", "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Type casting
            try:
                row["Score"] = float(row["Score"])
                row["Mentions"] = int(row["Mentions"])
                row["UniqueUsers"] = int(row["UniqueUsers"])
                row["PE"] = float(row["PE"]) if row["PE"] != "-" else None
                results.append(row)
            except ValueError:
                pass # skip invalid rows if any
    return results

import subprocess

@app.get("/api/details")
def get_details():
    if not os.path.exists("detail_data.json"):
        # Fallback to older keyword_data.json if detail_data.json is not there yet
        if os.path.exists("keyword_data.json"):
             with open("keyword_data.json", "r", encoding="utf-8") as f:
                 kw = json.load(f)
                 return {k: {"Keywords": v, "Comments": []} for k, v in kw.items()}
        raise HTTPException(status_code=404, detail="Data not found. Run crawler first.")
        
    with open("detail_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/market")
def get_market_data():
    if not os.path.exists("market_data.json"):
        return {
            "FearGreedIndex": 50,
            "TotalCommentsParsed": 0,
            "SectorRotation": [],
            "MarketSummary": "尚未有足夠資料產生大盤速報。"
        }
    with open("market_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/crawl")
def trigger_crawler():
    try:
        # Run the crawler script as a subprocess
        subprocess.run(["python3", "stock_crawler.py"], check=True)
        return {"status": "success", "message": "Data refreshed successfully"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail="Crawler failed to run")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
