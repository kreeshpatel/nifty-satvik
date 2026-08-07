"""Harvest NSE bulk + block deals (census candidate #3 — DATA ACQUISITION ONLY; the label screen is
NOT authorized this session; ledger discipline unchanged).

Source: the NSE historical APIs (warmed session, month windows, restartable):
  /api/historical/bulk-deals?from=DD-MM-YYYY&to=DD-MM-YYYY
  /api/historical/block-deals?from=...&to=...
PIT: deal lists are published same-evening EOD and never restated -> availability = trade date after
close (the delivery-layer assumption class; stated). Event rows are immutable -> truncation trivial.

Output: data/_bulkblock_raw.parquet [deal_type, symbol, date, client, side, qty, price, fetched_win]

    python scripts/harvest_bulkblock.py [--start 2019-01]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "_bulkblock_raw.parquet"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126 Safari/537.36",
       "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9",
       "Referer": "https://www.nseindia.com/"}
APIS = {"bulk": "https://www.nseindia.com/api/historical/bulk-deals?from={f}&to={t}",
        "block": "https://www.nseindia.com/api/historical/block-deals?from={f}&to={t}"}
FIELDS = {"symbol": ("BD_SYMBOL", "symbol"), "date": ("BD_DT_DATE", "date"),
          "client": ("BD_CLIENT_NAME", "clientName"), "side": ("BD_BUY_SELL", "buySell"),
          "qty": ("BD_QTY_TRD", "qty"), "price": ("BD_TP_WATP", "watp")}


def _get(sess, url):
    r = sess.get(url, headers=HDR, timeout=30)
    if r.status_code != 200:
        sess.get("https://www.nseindia.com/report-detail/display-bulk-and-block-deals",
                 headers=HDR, timeout=25)
        r = sess.get(url, headers=HDR, timeout=30)
    return r.json() if r.status_code == 200 else None


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--start", default="2019-01")
    args = ap.parse_args()
    have = pd.read_parquet(RAW) if RAW.exists() else pd.DataFrame(columns=["fetched_win"])
    done = set(have["fetched_win"].unique()) if len(have) else set()
    parts = [have] if len(have) else []
    sess = requests.Session()
    sess.get("https://www.nseindia.com/report-detail/display-bulk-and-block-deals", headers=HDR, timeout=25)
    cur = pd.Timestamp(args.start + "-01"); end = pd.Timestamp.today().normalize()
    wins = []
    while cur <= end:
        nxt = cur + pd.offsets.MonthEnd(0)
        key = cur.strftime("%Y-%m")
        if key not in done:
            wins.append((cur.strftime("%d-%m-%Y"), min(nxt, end).strftime("%d-%m-%Y"), key))
        cur = nxt + pd.Timedelta(days=1)
    print(f"bulk/block harvest: {len(wins)} month-windows (have {len(done)})", flush=True)
    n_rec = 0
    for k, (f, t, key) in enumerate(wins):
        for typ, api in APIS.items():
            try:
                j = _get(sess, api.format(f=f, t=t))
                rec = (j or {}).get("data", []) if isinstance(j, dict) else (j or [])
                rows = []
                for x in rec:
                    row = {"deal_type": typ, "fetched_win": key}
                    for out, keys in FIELDS.items():
                        row[out] = next((x[kk] for kk in keys if kk in x), None)
                    rows.append(row)
                if rows:
                    parts.append(pd.DataFrame(rows)); n_rec += len(rows)
            except Exception:
                pass
            time.sleep(0.8)
        if k % 12 == 11 or k == len(wins) - 1:
            pd.concat(parts, ignore_index=True).to_parquet(RAW, index=False)
            print(f"  {k+1}/{len(wins)} | records {n_rec} | last {key}", flush=True)
    if parts:
        allp = pd.concat(parts, ignore_index=True)
        allp.to_parquet(RAW, index=False)
        print(f"DONE. {len(allp)} rows -> {RAW}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
