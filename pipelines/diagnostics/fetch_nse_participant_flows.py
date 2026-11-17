"""Fetch NSE's daily participant-wise positioning (FII / DII / Pro / Client) into data/nse_participant_oi.csv.

Owner request 2026-11-17 (the FII/DII backlog item, approved). Read-only download, cached per day, polite rate.

**What this is, and what it is NOT.** The owner asked for FII/DII *net cash flows*. NSE's cash-market FII/DII figures
are published only for the latest day: `api/fiidiiTradeReact` ignores a date parameter and returns today, and there is
no dated archive file for the cash series (probed 2026-11-17: `fii_dii_<date>.csv` and `FIIDII_<date>.csv` both 404).
What NSE *does* archive daily, going back years, is participant-wise positioning in equity derivatives:

    https://archives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv

one row per client type (FII, DII, Pro, Client) with open interest in index futures, index options, stock futures and
stock options. That is institutional POSITIONING, not cash buying and selling. It is a genuine point-in-time series
with real dates, which is why it can be measured on history at all. Any readout must say which of the two it used.

    python pipelines/diagnostics/fetch_nse_participant_flows.py [--from 2019-01-01] [--to 2024-06-30]
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "nse_participant_oi.csv"
URL = "https://archives.nseindia.com/content/nsccl/fao_participant_oi_{d}.csv"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
PAUSE = 0.35


def parse(text: str, day: pd.Timestamp) -> pd.DataFrame:
    """The file's first line is a title; the real header is the second line."""
    df = pd.read_csv(io.StringIO(text), skiprows=1)
    df.columns = [c.strip().replace(" ", "_").lower() for c in df.columns]
    key = next((c for c in df.columns if "client" in c or "type" in c), df.columns[0])
    df = df.rename(columns={key: "client_type"})
    df["client_type"] = df["client_type"].astype(str).str.strip()
    df = df[df["client_type"].isin(["FII", "DII", "Pro", "Client"])].copy()
    for c in df.columns:
        if c != "client_type":
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "", regex=False), errors="coerce")
    df.insert(0, "date", day.strftime("%Y-%m-%d"))
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="2019-01-01")
    ap.add_argument("--to", dest="end", default="2024-06-30")
    a = ap.parse_args()
    have: set[str] = set()
    if OUT.exists():
        have = set(pd.read_csv(OUT, usecols=["date"])["date"].astype(str))
    s = requests.Session()
    s.get("https://www.nseindia.com/", headers=UA, timeout=20)
    rows, miss, err = [], 0, 0
    days = pd.bdate_range(a.start, a.end)
    for n, day in enumerate(days, 1):
        if day.strftime("%Y-%m-%d") in have:
            continue
        try:
            r = s.get(URL.format(d=day.strftime("%d%m%Y")), headers=UA, timeout=25)
            if r.status_code == 200 and "Client Type" in r.text[:400]:
                rows.append(parse(r.text, day))
            else:
                miss += 1                      # holiday, or a file the archive never had
        except Exception:                      # noqa: BLE001 — one bad day must not end the fetch
            err += 1
        time.sleep(PAUSE)
        if n % 200 == 0:
            sys.stdout.write(f"  {n}/{len(days)} sessions, {len(rows)} fetched, {miss} missing, {err} errors\n")
            sys.stdout.flush()
    if rows:
        new = pd.concat(rows, ignore_index=True)
        if OUT.exists():
            new = pd.concat([pd.read_csv(OUT), new], ignore_index=True).drop_duplicates(["date", "client_type"])
        new.sort_values(["date", "client_type"]).to_csv(OUT, index=False)
    sys.stdout.write(f"{OUT.name}: {len(rows)} day-rows added, {miss} days with no file, {err} errors\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
