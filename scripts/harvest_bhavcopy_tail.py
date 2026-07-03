"""Tail pass of the bhavcopy harvest: NSE switched formats mid-2024, so the main harvester's old-format
URLs 404 after ~2024-07. This pass covers 2024-07-01..2026-03-31 with the new UDiFF format
(BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip) and appends into the same raw pkl. Restartable via its
own done-journal.
"""
from __future__ import annotations

import io
import json
import pickle
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "_backfill_bhav_raw.pkl"
DONE = ROOT / "data" / "_backfill_bhav_tail_done.json"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.nseindia.com/"}

from harvest_bhavcopy_backfill import TARGETS  # noqa: E402


def main() -> int:
    raw = pickle.load(open(RAW, "rb"))
    done = set(json.load(open(DONE))) if DONE.exists() else set()
    days = [d for d in pd.bdate_range("2024-07-01", "2026-03-31") if str(d.date()) not in done]
    print(f"tail days remaining {len(days)}", flush=True)
    sess = requests.Session()
    n_ok = n_miss = 0
    for k, d in enumerate(days):
        url = (f"https://nsearchives.nseindia.com/content/cm/"
               f"BhavCopy_NSE_CM_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip")
        try:
            r = sess.get(url, headers=HDR, timeout=30)
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
                df = df[(df["SctySrs"].isin(("EQ", "BE"))) & (df["TckrSymb"].isin(TARGETS))]
                for _, row in df.iterrows():
                    raw.setdefault(row["TckrSymb"], []).append(
                        (str(d.date()), row["OpnPric"], row["HghPric"], row["LwPric"],
                         row["ClsPric"], row["TtlTradgVol"]))
                n_ok += 1
            else:
                n_miss += 1
        except Exception:
            n_miss += 1
        done.add(str(d.date()))
        if k % 100 == 99 or k == len(days) - 1:
            pickle.dump(raw, open(RAW, "wb"))
            json.dump(sorted(done), open(DONE, "w"))
            print(f"  {k+1}/{len(days)} | ok {n_ok} miss {n_miss}", flush=True)
        time.sleep(0.25)
    pickle.dump(raw, open(RAW, "wb"))
    json.dump(sorted(done), open(DONE, "w"))
    print("TAIL DONE.")
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    raise SystemExit(main())
