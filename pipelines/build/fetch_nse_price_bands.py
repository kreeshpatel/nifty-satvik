"""Fetch NSE's daily price-band history and band-hitter lists, 2019-01-01..2024-06-30, from the public archive.

Owner request 2026-11-18 (research/robust-sizing, Part 3 re-run with real bands). Data fetch only: nothing here
changes a rule, a trial or a sealed slice. The window stops at the training cut (2024-06-30).

SOURCES (public NSE archive, same host and headers as nq/data/nse_bhavcopy.py)
  bands     https://nsearchives.nseindia.com/content/equities/sec_list_DDMMYYYY.csv
            columns Symbol, Series, Security Name, Band, Remarks - the price band (%) in force that day for every
            security that HAS a band. F&O names carry no fixed band and are absent. The archive does not hold
            2019 files (HTTP 404); the first available date is recorded in the manifest.
  hitters   https://nsearchives.nseindia.com/archives/equities/bhavcopy/pr/PRDDMMYY.zip -> bhDDMMYY.csv
            columns SYMBOL, SERIES, SECURITY, HIGH/LOW, INDEX FLAG - every security that touched its upper (H) or
            lower (L) price band that session.

TRADING DAYS: the dates of diagnostics/research/benchmarks/tri/nifty_midcap150_momentum_50_tri.csv in the window.

OUTPUT (data/ is gitignored; re-run this script to rebuild)
  data/nse_bands/band_hitters.parquet   date, symbol, series, side (H/L)
  data/nse_bands/sec_list_bands.parquet date, symbol, series, band_pct
  data/nse_bands/manifest.json          per-day HTTP status, row counts, first/last dates, sha256 of both parquets
Raw downloads go to .cache/nse_bands/raw/ (untrusted; parsed as data only, never executed).

    python pipelines/build/fetch_nse_price_bands.py [--workers 4]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / ".cache" / "nse_bands" / "raw"
OUT = ROOT / "data" / "nse_bands"
TRI = ROOT / "diagnostics" / "research" / "benchmarks" / "tri" / "nifty_midcap150_momentum_50_tri.csv"
WINDOW = ("2019-01-01", "2024-06-30")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.nseindia.com/"}


def urls(d: pd.Timestamp) -> dict[str, str]:
    return {"sec_list": f"https://nsearchives.nseindia.com/content/equities/sec_list_{d:%d%m%Y}.csv",
            "pr": f"https://nsearchives.nseindia.com/archives/equities/bhavcopy/pr/PR{d:%d%m%y}.zip"}


def get(url: str, dest: Path) -> int:
    if dest.exists() and dest.stat().st_size > 0:
        return 200
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HDR, timeout=40)
            if r.status_code == 404:
                return 404
            if r.status_code == 200 and r.content and not r.content.lstrip().startswith(b"<"):
                dest.write_bytes(r.content)
                return 200
            if r.status_code == 200:              # an HTML error page served as 200 = not available
                return 404
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    return -1


def fetch_day(d: pd.Timestamp) -> dict:
    u = urls(d)
    return {"date": str(d.date()),
            "sec_list": get(u["sec_list"], RAW / f"sec_list_{d:%Y%m%d}.csv"),
            "pr": get(u["pr"], RAW / f"PR_{d:%Y%m%d}.zip")}


def parse_hitters(d: pd.Timestamp) -> pd.DataFrame:
    f = RAW / f"PR_{d:%Y%m%d}.zip"
    if not f.exists():
        return pd.DataFrame()
    with zipfile.ZipFile(f) as z:
        names = [n for n in z.namelist() if n.lower().startswith("bh") and n.lower().endswith(".csv")]
        if not names:
            return pd.DataFrame()
        df = pd.read_csv(io.BytesIO(z.read(names[0])), dtype=str, encoding="latin-1")
    df.columns = [c.strip().upper() for c in df.columns]
    side_col = next(c for c in df.columns if c.startswith("HIGH"))
    return pd.DataFrame({"date": d, "symbol": df["SYMBOL"].str.strip(), "series": df["SERIES"].str.strip(),
                         "side": df[side_col].str.strip().str.upper()})


def parse_bands(d: pd.Timestamp) -> pd.DataFrame:
    f = RAW / f"sec_list_{d:%Y%m%d}.csv"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f, dtype=str, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    return pd.DataFrame({"date": d, "symbol": df["Symbol"].str.strip(), "series": df["Series"].str.strip(),
                         "band_pct": pd.to_numeric(df["Band"], errors="coerce")})


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    idx = pd.DatetimeIndex(pd.read_csv(TRI, parse_dates=["date"])["date"])
    days = idx[(idx >= WINDOW[0]) & (idx <= WINDOW[1])]
    with ThreadPoolExecutor(a.workers) as ex:
        status = list(ex.map(fetch_day, days))
    hit = pd.concat([parse_hitters(d) for d in days], ignore_index=True)
    band = pd.concat([parse_bands(d) for d in days], ignore_index=True)
    hit.to_parquet(OUT / "band_hitters.parquet", index=False)
    band.to_parquet(OUT / "sec_list_bands.parquet", index=False)
    st = pd.DataFrame(status)
    man = {"window": WINDOW, "trading_days": int(len(days)),
           "pr_ok": int((st["pr"] == 200).sum()), "pr_missing": st.loc[st["pr"] != 200, "date"].tolist(),
           "sec_list_ok": int((st["sec_list"] == 200).sum()),
           "sec_list_first": st.loc[st["sec_list"] == 200, "date"].min(),
           "sec_list_missing_after_first": st.loc[(st["sec_list"] != 200) & (st["date"] >= st.loc[st["sec_list"] == 200, "date"].min()), "date"].tolist(),
           "hitter_rows": int(len(hit)), "lower_hits": int((hit["side"] == "L").sum()) if len(hit) else 0,
           "band_rows": int(len(band)),
           "sha256": {"band_hitters.parquet": sha(OUT / "band_hitters.parquet"),
                      "sec_list_bands.parquet": sha(OUT / "sec_list_bands.parquet")}}
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, list) else f"{len(v)} dates") for k, v in man.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
