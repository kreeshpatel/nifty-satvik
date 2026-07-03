"""Harvest NSE daily bhavcopies for the unresolved delisted/merged members (backfill step 2, class b/c).
Downloads each trading day's cm bhavcopy zip (2017-01-01..2026-03-31), extracts ONLY the target symbols'
EQ rows, and accumulates per-symbol RAW OHLCV into data/_backfill_bhav_raw.pkl. Restartable: keeps a
done-dates journal (data/_backfill_bhav_done.json) and skips completed dates. RAW = unadjusted — the
corporate-action screen/adjustment happens in a separate step before anything enters the backfill cache.
"""
from __future__ import annotations

import io
import json
import pickle
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "_backfill_bhav_raw.pkl"
DONE = ROOT / "data" / "_backfill_bhav_done.json"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.nseindia.com/"}

TARGETS = ['8KMILES', 'AKZOINDIA', 'ALBK', 'ANDHRABANK', 'BHARATFIN', 'CAPF', 'CORPBANK', 'DENABANK',
           'DHANI', 'DHFL', 'EQUITAS', 'EXCELCROP', 'GDL', 'GEPIL', 'GET&D', 'GLS', 'GSKCONS',
           'GUJFLUORO', 'HEXAWARE', 'HSIL', 'IBVENTURES', 'INFIBEAM', 'INOXLEISUR', 'ISEC', 'ITDCEM',
           'JCHAC', 'JPASSOCIAT', 'JSLHISAR', 'LAKSHVILAS', 'LTI', 'LTIM', 'MAXINDIA', 'MFL', 'MINDTREE',
           'ORIENTBANK', 'PEL', 'SEQUENT', 'SREINFRA', 'SWANENERGY', 'SYNDIBANK', 'TATAMTRDVR', 'TATASPONGE',
           'TATASTLBSL', 'TATASTLLP', 'TCNSBRANDS', 'TIFIN', 'TV18BRDCST', 'UJJIVAN', 'VIJAYABANK',
           'ZOMATO', 'GSPL', 'SPICEJET']  # last two: NSE-side series to replace .BO fallbacks


def main() -> int:
    raw = pickle.load(open(RAW, "rb")) if RAW.exists() else {}
    done = set(json.load(open(DONE))) if DONE.exists() else set()
    days = pd.bdate_range("2017-01-01", "2026-03-31")
    todo = [d for d in days if str(d.date()) not in done]
    print(f"targets {len(TARGETS)} | days total {len(days)} | remaining {len(todo)}", flush=True)
    sess = requests.Session()
    n_ok = n_miss = 0
    for k, d in enumerate(todo):
        mon = d.strftime("%b").upper()
        url = (f"https://archives.nseindia.com/content/historical/EQUITIES/{d.year}/{mon}/"
               f"cm{d.strftime('%d')}{mon}{d.year}bhav.csv.zip")
        try:
            r = sess.get(url, headers=HDR, timeout=30)
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                df = pd.read_csv(z.open(z.namelist()[0]))
                df = df[(df["SERIES"].isin(("EQ", "BE"))) & (df["SYMBOL"].isin(TARGETS))]
                for _, row in df.iterrows():
                    raw.setdefault(row["SYMBOL"], []).append(
                        (str(d.date()), row["OPEN"], row["HIGH"], row["LOW"], row["CLOSE"], row["TOTTRDQTY"]))
                n_ok += 1
            else:
                n_miss += 1  # holiday / missing file
        except Exception:
            n_miss += 1
        done.add(str(d.date()))
        if k % 100 == 99 or k == len(todo) - 1:
            pickle.dump(raw, open(RAW, "wb"))
            json.dump(sorted(done), open(DONE, "w"))
            print(f"  {k+1}/{len(todo)} days | files ok {n_ok} miss {n_miss} | symbols {len(raw)}", flush=True)
        time.sleep(0.25)
    pickle.dump(raw, open(RAW, "wb"))
    json.dump(sorted(done), open(DONE, "w"))
    print("DONE. per-symbol row counts:")
    for t in sorted(raw):
        print(f"  {t:<12} {len(raw[t])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
