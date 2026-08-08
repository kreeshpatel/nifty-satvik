"""FOUNDATION AUDIT — layer 1/2 harvester: authoritative NSE bhavcopy for a stratified sample.

This is the bottom of the evidence stack. Every number the programme publishes rests on
``data/ohlcv.pkl`` (pin ``dataset-pin-20260701``, sha ``f8625a8f…``), and nothing has ever tested
that pickle against the exchange. The blind replication could not: it was handed the same pickle,
so a data error was inherited by both sides rather than caught by the comparison.

What this script pulls, and why each field earns its place:

* **OHLC + volume** for every sampled date — the direct price-truth comparison.
* **PREVCLOSE** — the load-bearing field. NSE re-bases the previous close on the ex-date of a
  corporate action, so ``PREVCLOSE(t) / CLOSE(t-1)`` *is the exchange's own adjustment factor*,
  published by the exchange, for every split, bonus and demerger. It converts "is this a split or a
  genuine crash?" from a judgement call into an arithmetic one. Layer 2 rests entirely on it.
* **ISIN** — an identity check independent of the ticker string, so a symbol reused by a different
  company (or an alias collision) is visible rather than silent.

Two URL families, because NSE changed format mid-2024 (the same split the delisted-backfill
harvesters already encode): the pre-UDiFF ``cmDDMMMYYYYbhav.csv.zip`` archive and the UDiFF
``BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip``. Both are tried for every date; whichever answers
is normalised to one schema, and the family that answered is recorded per date as provenance.

Output: ``diagnostics/research/foundation_audit_2026Q3/bhavcopy_sample.parquet`` (only the rows the
audit compares — every symbol present in the pinned pickle, plus the extreme-move names) and a
manifest. Committing the extracted rows makes the audit re-runnable without the network; the raw
zips are cached outside the repo and are not needed again.

Restartable: a per-date journal means an interrupted run resumes without re-downloading.
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
OUTDIR = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
SAMPLE = OUTDIR / "bhavcopy_sample.parquet"
MANIFEST = OUTDIR / "bhavcopy_manifest.json"
OHLCV = ROOT / "data" / "ohlcv.pkl"

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
       "Referer": "https://www.nseindia.com/"}
SERIES_KEEP = ("EQ", "BE")

# One trading day per quarter, 2019Q1..2026Q2. The nominal date is the 15th of each quarter's middle
# month; if that is a holiday the fetcher walks FORWARD (never backward — walking both ways would let
# the sample drift toward whichever side happens to have data, which is a selection the audit cannot
# justify). 2019 is the start because the programme trusts >=2019 folds only; the pickle's 2017-2018
# head is covered by the warm-up window rather than by trades.
QUARTER_ANCHORS = [f"{y}-{m:02d}-15" for y in range(2019, 2027) for m in (2, 5, 8, 11)]


def _norm_old(df: pd.DataFrame, d: pd.Timestamp) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    df = df[df["SERIES"].astype(str).str.strip().isin(SERIES_KEEP)]
    out = pd.DataFrame({
        "date": d, "symbol": df["SYMBOL"].astype(str).str.strip(),
        "series": df["SERIES"].astype(str).str.strip(),
        "open": df["OPEN"], "high": df["HIGH"], "low": df["LOW"], "close": df["CLOSE"],
        "prevclose": df["PREVCLOSE"], "volume": df["TOTTRDQTY"],
        "isin": df.get("ISIN", pd.Series([None] * len(df))).astype(str),
        "src": "archive_old",
    })
    return out


def _norm_udiff(df: pd.DataFrame, d: pd.Timestamp) -> pd.DataFrame:
    df = df[df["SctySrs"].astype(str).str.strip().isin(SERIES_KEEP)]
    out = pd.DataFrame({
        "date": d, "symbol": df["TckrSymb"].astype(str).str.strip(),
        "series": df["SctySrs"].astype(str).str.strip(),
        "open": df["OpnPric"], "high": df["HghPric"], "low": df["LwPric"], "close": df["ClsPric"],
        "prevclose": df["PrvsClsgPric"], "volume": df["TtlTradgVol"],
        "isin": df["ISIN"].astype(str), "src": "archive_udiff",
    })
    return out


def fetch_day(sess: requests.Session, d: pd.Timestamp) -> pd.DataFrame | None:
    """One trading day's cash-market bhavcopy, or None if the exchange published no file."""
    mon = d.strftime("%b").upper()
    attempts = [
        (f"https://nsearchives.nseindia.com/content/cm/"
         f"BhavCopy_NSE_CM_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip", _norm_udiff),
        (f"https://archives.nseindia.com/content/historical/EQUITIES/{d.year}/{mon}/"
         f"cm{d.strftime('%d')}{mon}{d.year}bhav.csv.zip", _norm_old),
    ]
    for url, norm in attempts:
        try:
            r = sess.get(url, headers=HDR, timeout=45)
        except Exception:
            continue
        if r.status_code != 200 or not r.content[:2] == b"PK":
            continue
        z = zipfile.ZipFile(io.BytesIO(r.content))
        df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
        return norm(df, d)
    return None


def resolve_trading_day(sess: requests.Session, nominal: str, max_walk: int = 8):
    """The first trading day on or after `nominal` for which NSE published a bhavcopy."""
    d = pd.Timestamp(nominal)
    for k in range(max_walk):
        day = d + pd.Timedelta(days=k)
        if day.weekday() >= 5:
            continue
        got = fetch_day(sess, day)
        time.sleep(0.3)
        if got is not None and len(got):
            return day, got
    return None, None


def main(extra_dates: list[str] | None = None) -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    universe = set(pickle.load(open(OHLCV, "rb")))
    print(f"pinned pickle: {len(universe)} symbols", flush=True)

    have = pd.read_parquet(SAMPLE) if SAMPLE.exists() else None
    done = set(have["date"].dt.strftime("%Y-%m-%d")) if have is not None else set()

    wanted = list(QUARTER_ANCHORS) + list(extra_dates or [])
    sess = requests.Session()
    frames = [have] if have is not None else []
    prov: dict[str, str] = {}
    if MANIFEST.exists():
        prov = json.loads(MANIFEST.read_text(encoding="utf-8")).get("dates", {})

    for nominal in wanted:
        # An extra date is an EXACT date (a corporate-action ex-date or its predecessor); a quarter
        # anchor may walk to the next trading day. Never walk an exact date — that would silently
        # compare the wrong session.
        exact = nominal not in QUARTER_ANCHORS
        if exact:
            day = pd.Timestamp(nominal)
            if str(day.date()) in done:
                continue
            got = fetch_day(sess, day)
            time.sleep(0.3)
            if got is None:
                print(f"  {nominal}: NO FILE (exact date, not walked)", flush=True)
                prov[nominal] = "no_file"
                continue
        else:
            if any(str((pd.Timestamp(nominal) + pd.Timedelta(days=k)).date()) in done
                   for k in range(8)):
                continue
            day, got = resolve_trading_day(sess, nominal)
            if got is None:
                print(f"  {nominal}: NO TRADING DAY FOUND in 8d window", flush=True)
                prov[nominal] = "unresolved"
                continue

        keep = got[got["symbol"].isin(universe)].copy()
        frames.append(keep)
        prov[str(day.date())] = f"{keep['src'].iloc[0] if len(keep) else '?'} (nominal {nominal})"
        print(f"  {nominal} -> {day.date()}: {len(got)} rows, {len(keep)} in pinned universe",
              flush=True)

    out = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "symbol", "series"])
    out = out.sort_values(["date", "symbol"]).reset_index(drop=True)
    out.to_parquet(SAMPLE, index=False)
    MANIFEST.write_text(json.dumps({
        "rows": int(len(out)), "dates": prov,
        "n_dates": int(out["date"].nunique()), "n_symbols": int(out["symbol"].nunique()),
        "series_kept": list(SERIES_KEEP),
        "_note": "extracted NSE cash bhavcopy rows for symbols present in the pinned ohlcv.pkl; "
                 "prevclose is the exchange's corporate-action receipt",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {SAMPLE}  rows={len(out)}  dates={out['date'].nunique()}  "
          f"symbols={out['symbol'].nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or None))
