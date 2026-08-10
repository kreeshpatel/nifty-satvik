"""Harvest NSE daily F&O bhavcopies for NIFTY index options (2017-01-01 .. today), keeping ONLY the
NIFTY OPTIDX/IDO rows, and accumulate the normalized long frame to data/_fo_oi_raw.parquet.

Two schemas span the window (see nq/data/options_oi):
  * date <  2024-07-01 -> OLD  : archives.nseindia.com/content/historical/DERIVATIVES/YYYY/MON/foDDMONYYYYbhav.csv.zip
  * date >= 2024-07-01 -> UDiFF: nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip
On a miss it falls back to the OTHER format (covers the exact cutover fuzz + UDiFF backfill). Restartable:
skips dates already in the parquet. HEAD is unreliable on archives.nseindia.com (503) -> always GET.

    python scripts/harvest_fo_bhavcopy.py                 # full harvest (downloads)
    python scripts/harvest_fo_bhavcopy.py --start 2024-01-01
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.nse_bhavcopy import fetch_for_date  # noqa: E402
from nq.data.options_oi import OI_RAW_PATH, parse_fo_bhavcopy  # noqa: E402

# URL templates, the 2024-07 UDiFF cutover and the dual-scheme fallback moved to
# nq.data.nse_bhavcopy on 2026-08-10 so the F&O universe builder could share them rather than
# copy them. Behaviour here is unchanged: same primary/secondary order, same silent-None on a miss.
RAW = OI_RAW_PATH


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=str(pd.Timestamp.today().normalize().date()))
    args = ap.parse_args()

    have = pd.read_parquet(RAW) if RAW.exists() else pd.DataFrame(columns=["date"])
    done = set(pd.to_datetime(have["date"]).dt.normalize().unique()) if len(have) else set()
    parts = [have] if len(have) else []
    days = [d for d in pd.bdate_range(args.start, args.end) if d.normalize() not in done]
    print(f"days {args.start}..{args.end}: total {len(pd.bdate_range(args.start, args.end))} | "
          f"already have {len(done)} | to fetch {len(days)}", flush=True)

    sess = requests.Session()
    n_ok = n_rows = n_miss = 0
    for k, d in enumerate(days):
        df = fetch_for_date(sess, d)
        if df is not None:
            lf = parse_fo_bhavcopy(df, d)
            if len(lf):
                parts.append(lf)
                n_rows += len(lf)
                n_ok += 1
            else:
                n_miss += 1  # file present but no NIFTY options (pre-listing / odd day)
        else:
            n_miss += 1  # holiday / missing file
        if k % 100 == 99 or k == len(days) - 1:
            pd.concat(parts, ignore_index=True).to_parquet(RAW, index=False)
            print(f"  {k+1}/{len(days)} | option-days ok {n_ok} miss {n_miss} | rows {n_rows} | "
                  f"last {d.date()}", flush=True)
        time.sleep(0.25)

    if parts:
        pd.concat(parts, ignore_index=True).to_parquet(RAW, index=False)
    tot = pd.read_parquet(RAW)
    print(f"DONE. {tot['date'].nunique()} option-days, {len(tot)} rows -> {RAW}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
