"""Harvest NSE structured credit-rating filings (census #4; archive regime starts ~2023-02).

Native PIT: BroadcastDateTime (publication) + DateofCR (the rating action date). Month windows,
warmed session, restartable. Output: data/_ratings_raw.parquet

    python scripts/harvest_ratings.py [--start 2023-01]
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT/"data"/"_ratings_raw.parquet"
HDR = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
       "Accept":"application/json","Referer":"https://www.nseindia.com/"}
API = "https://www.nseindia.com/api/corporate-credit-rating?index=equities&from_date={f}&to_date={t}"
KEEP = ["Symbol","CompanyName","ISIN","NameOfCRAgency","CreditRating","RatingAction","Outlook",
        "DateofCR","BroadcastDateTime","CreditRatingEarlier","RatingActionEarlier","OutlookEarlier"]

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--start", default="2023-01")
    a = ap.parse_args()
    have = pd.read_parquet(RAW) if RAW.exists() else pd.DataFrame(columns=["fetched_win"])
    done = set(have["fetched_win"].unique()) if len(have) else set()
    parts = [have] if len(have) else []
    s = requests.Session()
    s.get("https://www.nseindia.com/companies-listing/corporate-filings-credit-rating", headers=HDR, timeout=25)
    cur = pd.Timestamp(a.start+"-01"); end = pd.Timestamp.today().normalize(); n = 0
    wins = []
    while cur <= end:
        nxt = cur+pd.offsets.MonthEnd(0); key = cur.strftime("%Y-%m")
        if key not in done:
            wins.append((cur.strftime("%d-%m-%Y"), min(nxt,end).strftime("%d-%m-%Y"), key))
        cur = nxt+pd.Timedelta(days=1)
    print(f"ratings harvest: {len(wins)} windows", flush=True)
    for k,(f,t,key) in enumerate(wins):
        try:
            r = s.get(API.format(f=f,t=t), headers=HDR, timeout=40)
            if r.status_code != 200:
                s.get("https://www.nseindia.com/companies-listing/corporate-filings-credit-rating",
                      headers=HDR, timeout=25)
                r = s.get(API.format(f=f,t=t), headers=HDR, timeout=40)
            rec = r.json() if r.status_code == 200 and len(r.content) > 2 else []
            rows = [{c: x.get(c) for c in KEEP} | {"fetched_win": key} for x in rec]
            if rows:
                parts.append(pd.DataFrame(rows)); n += len(rows)
        except Exception:
            pass
        if k % 10 == 9 or k == len(wins)-1:
            pd.concat(parts, ignore_index=True).to_parquet(RAW, index=False)
            print(f"  {k+1}/{len(wins)} | records {n} | last {key}", flush=True)
        time.sleep(1.0)
    if parts:
        allp = pd.concat(parts, ignore_index=True); allp.to_parquet(RAW, index=False)
        print(f"DONE. {len(allp)} records -> {RAW}", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
