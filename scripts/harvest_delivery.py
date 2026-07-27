"""Harvest NSE security-wise DELIVERY data (census candidate #1; owner-signed 2026-07-27).

Clone of the proven harvest_fo_bhavcopy pattern: daily archive files, restartable, polite pacing.
Two published formats span 2019->present:
  * MTO_DDMMYYYY.DAT            (archives.nseindia.com/archives/equities/mto/...) — the full span.
  * sec_bhavdata_full_DDMMYYYY.csv (products/content/...) — ~2020-07 onward, carries DELIV_* columns.
Primary = sec_bhavdata for dates >= 2020-07-01 else MTO; fallback to the other on a miss. ALL EQ/BE
rows are kept (universe filtering happens at build time via the alias map — safer than filtering at
harvest). Output: data/_delivery_raw.parquet  [symbol, series, date, src, traded_qty, deliv_qty,
deliv_pct].

PIT: each file is published the SAME EVENING (post-settlement, ~18:00 IST) and never restated;
availability = trade date after close. Files are immutable -> the truncation test is exact.

    python scripts/harvest_delivery.py [--start 2019-01-01]
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "_delivery_raw.parquet"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.nseindia.com/"}
SEC_FROM = pd.Timestamp("2020-07-01")


def _url_mto(d: pd.Timestamp) -> str:
    return f"https://archives.nseindia.com/archives/equities/mto/MTO_{d.strftime('%d%m%Y')}.DAT"


def _url_sec(d: pd.Timestamp) -> str:
    return f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv"


def _fetch(sess: requests.Session, url: str) -> str | None:
    try:
        r = sess.get(url, headers=HDR, timeout=40)
        return r.text if r.status_code == 200 and r.content else None
    except Exception:
        return None


def parse_mto(text: str, d: pd.Timestamp) -> pd.DataFrame:
    """MTO .DAT: data rows start '20,' -> rec,sr,symbol,series,traded_qty,deliv_qty,deliv_pct."""
    rows = []
    for ln in text.splitlines():
        if not ln.startswith("20,"):
            continue
        p = [x.strip() for x in ln.split(",")]
        if len(p) < 7:
            continue
        try:
            rows.append((p[2], p[3], float(p[4]), float(p[5]), float(p[6])))
        except ValueError:
            continue
    df = pd.DataFrame(rows, columns=["symbol", "series", "traded_qty", "deliv_qty", "deliv_pct"])
    df = df[df["series"].isin(("EQ", "BE"))]
    df["date"] = d; df["src"] = "mto"
    return df


def parse_sec(text: str, d: pd.Timestamp) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.strip() for c in df.columns]
    for c in ("SYMBOL", "SERIES"):
        df[c] = df[c].astype(str).str.strip()
    df = df[df["SERIES"].isin(("EQ", "BE"))]
    out = pd.DataFrame({
        "symbol": df["SYMBOL"], "series": df["SERIES"],
        "traded_qty": pd.to_numeric(df["TTL_TRD_QNTY"], errors="coerce"),
        "deliv_qty": pd.to_numeric(df["DELIV_QTY"], errors="coerce"),
        "deliv_pct": pd.to_numeric(df["DELIV_PER"], errors="coerce"),
    })
    out["date"] = d; out["src"] = "sec"
    return out.dropna(subset=["deliv_pct"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default=str(pd.Timestamp.today().normalize().date()))
    args = ap.parse_args()
    have = pd.read_parquet(RAW) if RAW.exists() else pd.DataFrame(columns=["date"])
    done = set(pd.to_datetime(have["date"]).dt.normalize().unique()) if len(have) else set()
    parts = [have] if len(have) else []
    days = [d for d in pd.bdate_range(args.start, args.end) if d.normalize() not in done]
    print(f"delivery harvest {args.start}..{args.end}: to fetch {len(days)} (have {len(done)})", flush=True)
    sess = requests.Session(); n_ok = n_miss = 0
    for k, d in enumerate(days):
        primary, secondary = ((_url_sec(d), _url_mto(d)) if d >= SEC_FROM else (_url_mto(d), _url_sec(d)))
        txt = _fetch(sess, primary); src_primary = True
        if txt is None:
            txt = _fetch(sess, secondary); src_primary = False
        if txt is not None:
            use_sec = (d >= SEC_FROM) == src_primary
            df = parse_sec(txt, d) if use_sec else parse_mto(txt, d)
            if len(df):
                parts.append(df); n_ok += 1
            else:
                n_miss += 1
        else:
            n_miss += 1
        if k % 100 == 99 or k == len(days) - 1:
            pd.concat(parts, ignore_index=True).to_parquet(RAW, index=False)
            print(f"  {k+1}/{len(days)} | ok {n_ok} miss {n_miss} | last {d.date()}", flush=True)
        time.sleep(0.25)
    if parts:
        allp = pd.concat(parts, ignore_index=True)
        allp.to_parquet(RAW, index=False)
        print(f"DONE. {allp['date'].nunique()} days, {len(allp)} rows -> {RAW}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
