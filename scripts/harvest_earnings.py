"""Harvest the NSE board-meeting / results calendar (census candidate #2; owner-signed 2026-07-27).

Source: the NSE corporate-board-meetings API (probe-verified), which natively carries BOTH PIT layers:
  * bm_timestamp — the ANNOUNCEMENT broadcast datetime (when the future meeting became public), and
  * bm_date      — the EVENT date (the meeting/results day itself).
Month-window requests, 2019-01 -> present, warmed session (NSE APIs need site cookies), restartable
by month, polite pacing. ALL records are kept (purpose filtering happens at build time); records from
2019 include since-delisted symbols -> survivorship-free at source.

Output: data/_earnings_raw.parquet [symbol, isin, name, purpose, desc, event_date, ann_ts, fetched_win]

    python scripts/harvest_earnings.py [--start 2019-01]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "_earnings_raw.parquet"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126 Safari/537.36",
       "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9",
       "Referer": "https://www.nseindia.com/"}
API = "https://www.nseindia.com/api/corporate-board-meetings?index=equities&from_date={f}&to_date={t}"


def month_windows(start: str, end: pd.Timestamp):
    cur = pd.Timestamp(start + "-01")
    while cur <= end:
        nxt = (cur + pd.offsets.MonthEnd(0))
        yield cur.strftime("%d-%m-%Y"), min(nxt, end).strftime("%d-%m-%Y"), cur.strftime("%Y-%m")
        cur = nxt + pd.Timedelta(days=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01")
    args = ap.parse_args()
    have = pd.read_parquet(RAW) if RAW.exists() else pd.DataFrame(columns=["fetched_win"])
    done = set(have["fetched_win"].unique()) if len(have) else set()
    parts = [have] if len(have) else []
    sess = requests.Session()
    sess.get("https://www.nseindia.com/companies-listing/corporate-filings-board-meetings",
             headers=HDR, timeout=25)                      # cookie warmup
    wins = [(f, t, key) for f, t, key in month_windows(args.start, pd.Timestamp.today().normalize())
            if key not in done]
    print(f"earnings harvest: {len(wins)} month-windows to fetch (have {len(done)})", flush=True)
    n_ok = n_rec = 0
    for k, (f, t, key) in enumerate(wins):
        try:
            r = sess.get(API.format(f=f, t=t), headers=HDR, timeout=30)
            if r.status_code != 200:
                sess.get("https://www.nseindia.com/companies-listing/corporate-filings-board-meetings",
                         headers=HDR, timeout=25)          # re-warm and retry once
                r = sess.get(API.format(f=f, t=t), headers=HDR, timeout=30)
            j = r.json() if r.status_code == 200 else []
            rec = j if isinstance(j, list) else j.get("data", [])
            rows = [{"symbol": x.get("bm_symbol"), "isin": x.get("sm_isin"), "name": x.get("sm_name"),
                     "purpose": x.get("bm_purpose"), "desc": x.get("bm_desc"),
                     "event_date": x.get("bm_date"), "ann_ts": x.get("bm_timestamp"),
                     "fetched_win": key} for x in rec]
            if rows:
                parts.append(pd.DataFrame(rows)); n_ok += 1; n_rec += len(rows)
        except Exception:
            pass
        if k % 12 == 11 or k == len(wins) - 1:
            pd.concat(parts, ignore_index=True).to_parquet(RAW, index=False)
            print(f"  {k+1}/{len(wins)} windows | ok {n_ok} | records {n_rec} | last {key}", flush=True)
        time.sleep(1.0)
    if parts:
        allp = pd.concat(parts, ignore_index=True)
        allp.to_parquet(RAW, index=False)
        print(f"DONE. {len(allp)} records, {allp['symbol'].nunique()} symbols -> {RAW}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
