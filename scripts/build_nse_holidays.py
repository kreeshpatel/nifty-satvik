"""Regenerate ``config.NSE_HOLIDAYS`` from NSE's authoritative holiday master (M10).

## Why this exists

The committed calendar was **estimated, not sourced**. Diffed against NSE's own
`holiday-master?type=trading` CM segment on 2026-08-06, the 2026 block had **10 holidays missing and
8 dates NSE does not list** — 15 of them on weekdays, i.e. 15 wrong trading-day answers in the
current year. Four were spot-checked against actual exchange bhavcopy and NSE was right every time:

| date | committed said | NSE said | bhavcopy |
|---|---|---|---|
| 2026-03-30 | holiday | trading | **present (2,552 rows)** |
| 2026-02-17 | holiday | trading | **present (2,512 rows)** |
| 2026-03-26 | trading | holiday (Ram Navami) | **absent** |
| 2026-01-15 | trading | holiday (Municipal Election) | **absent** |

A hand-maintained calendar drifts silently, and everything that asks "is this a trading day?" —
the phantom-bar drop, the forward wall's gap markers, the quarterly review dates — inherits the
drift without any signal. This makes the calendar **sourced and regenerable** instead.

## What it does

Fetches the CM segment, prints a full diff against the committed set, and emits a ready-to-paste
`NSE_HOLIDAYS` block plus the `NSE_HOLIDAYS_COVERED_THROUGH` bound. It **does not write config.py** —
changing the calendar changes a data input, so the diff is reviewed by a human first.

    python scripts/build_nse_holidays.py            # diff only
    python scripts/build_nse_holidays.py --emit     # diff + the block to paste
    python scripts/build_nse_holidays.py --verify   # also check each disputed date against bhavcopy

## The 2027 problem this does NOT solve

As of 2026-08-06 **NSE has published only 2026** — every segment returns 2026 rows and nothing
beyond. So the 2027 dates the Jan/Apr review cadence needs **do not exist yet at the source**, and no
script can invent them. That is why `config.NSE_HOLIDAYS_COVERED_THROUGH` and its guard exist: the
calendar now knows where it stops, and asking it about a later date raises instead of guessing.
Re-run this script once NSE publishes 2027 (historically in December).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

API = "https://www.nseindia.com/api/holiday-master?type=trading"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120 Safari/537.36",
       "Referer": "https://www.nseindia.com/", "Accept": "*/*"}


def fetch() -> dict[str, str]:
    """{iso date -> description} for the CM (cash market) segment."""
    s = requests.Session()
    s.get("https://www.nseindia.com/", headers=HDR, timeout=25)
    j = s.get(API, headers=HDR, timeout=40).json()
    return {pd.Timestamp(x["tradingDate"]).date().isoformat(): str(x.get("description", "")).strip()
            for x in j["CM"]}


def main(argv: list[str]) -> int:
    from config import NSE_HOLIDAYS

    nse = fetch()
    committed = set(NSE_HOLIDAYS)
    years_nse = sorted({d[:4] for d in nse})
    print(f"NSE CM segment: {len(nse)} dates, years {years_nse}")
    print(f"committed:      {len(committed)} dates, years {sorted({d[:4] for d in committed})}")

    # only compare years NSE actually publishes — it does not serve history
    scope = {d for d in committed if d[:4] in years_nse}
    missing = sorted(set(nse) - scope)
    extra = sorted(scope - set(nse))

    def _bites(d: str) -> str:
        return "WEEKDAY" if pd.Timestamp(d).weekday() < 5 else "weekend"

    print(f"\nMISSING from config ({len(missing)}) — NSE says holiday, config does not:")
    for d in missing:
        print(f"   {d}  {_bites(d):<8} {nse[d][:52]}")
    print(f"\nNOT ON NSE'S LIST ({len(extra)}) — config says holiday, NSE does not:")
    for d in extra:
        print(f"   {d}  {_bites(d):<8}")
    n_bite = sum(1 for d in missing + extra if pd.Timestamp(d).weekday() < 5)
    print(f"\n{n_bite} of {len(missing) + len(extra)} differences fall on a WEEKDAY "
          f"(a weekend difference cannot change any trading-day answer).")

    if "--verify" in argv:
        from audit_foundation_bhavcopy_2026Q3 import fetch_day
        print("\nverifying disputed WEEKDAY dates against actual exchange bhavcopy:")
        s = requests.Session()
        for d in [x for x in missing + extra if pd.Timestamp(x).weekday() < 5][:12]:
            got = fetch_day(s, pd.Timestamp(d))
            present = got is not None and len(got) > 0
            claim = "NSE: holiday" if d in nse else "NSE: trading"
            ok = (not present) if d in nse else present
            print(f"   {d}  {claim:<14} bhavcopy {'PRESENT' if present else 'ABSENT ':<8} "
                  f"-> NSE {'CONFIRMED' if ok else 'CONTRADICTED'}")

    if "--emit" in argv:
        keep_old = sorted(d for d in committed if d[:4] not in years_nse)
        all_d = sorted(set(keep_old) | set(nse))
        # coverage is the last date the calendar is AUTHORITATIVE FOR, which is the end
        # of the last published year — not the last holiday in it. NSE publishes a full
        # year at a time, so every day of that year is a known answer.
        covered = f"{max(years_nse)}-12-31"
        print("\n# ---- paste into config.py ----")
        print("NSE_HOLIDAYS = {")
        for i in range(0, len(all_d), 4):
            print("    " + " ".join(f"'{d}'," for d in all_d[i:i + 4]))
        print("}")
        print(f"NSE_HOLIDAYS_COVERED_THROUGH = '{covered}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
