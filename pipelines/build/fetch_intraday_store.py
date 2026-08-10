"""Fetch the intraday bar store from Kite, and audit it on the way out.

The elected direction out of the resolution ceiling: n_eff = 37 independent 63-day windows on the
daily panel caps the dSharpe half-width at ±0.59 permanently, and only a genuinely new sample moves
that. Scope is the F&O universe (`pipelines/build/build_fo_universe.py`), taken as EVER-members so
names that left the segment are fetched too — a universe pinned to today's list is survivorship
through a different door.

CREDENTIALS come from the environment only, matching the repo's existing convention
(`dashboard/backend/routers/kite.py`, `refresh_kite_session.py`)::

    KITE_API_KEY        your app's API key
    KITE_ACCESS_TOKEN   a live access token (refresh_kite_session.py mints one)

Nothing here reads a credential from a file, prints one, or writes one to an artifact.

Restartable. One parquet per symbol under ``data/intraday/<interval>/``; a symbol already on disk is
skipped unless ``--refetch``. An interrupted multi-year run resumes where it stopped.

    python pipelines/build/fetch_intraday_store.py --interval 15minute
    python pipelines/build/fetch_intraday_store.py --interval 15minute --limit 5   # smoke
    python pipelines/build/fetch_intraday_store.py --audit-only                    # no network

WHAT IS NOT SETTLED, and is deliberately not guessed at. Kite serves AS-TRADED prices, so a split or
bonus appears as an unmarked overnight seam — the VEDL lesson. `--audit-only` runs
`split_seam_candidates` over the store and lists them. It does not correct them, because a demerger
produces the same seam shape and is not a split: the value genuinely left the company, and
"adjusting" it fabricates return. Adjudication belongs in
`nq.data.adjustment_guard.KNOWN_SEAMS`, with a cause and a provenance, one name at a time.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.fo_universe import membership_spans  # noqa: E402
from nq.data.intraday import (coverage_report, fetch_symbol, split_seam_candidates)  # noqa: E402

MEMBERSHIP = ROOT / "data" / "fo_membership.parquet"
STORE = ROOT / "data" / "intraday"
AUDIT = ROOT / "diagnostics" / "research" / "intraday_coverage.json"

# Kite documents 3 requests/second. 0.34s between calls keeps us under it with a margin; the
# throttle is per REQUEST, and fetch_symbol issues one per page.
MIN_INTERVAL_S = 0.34

# Known-delisted F&O names, carried so the coverage audit can report the tail explicitly. ADR-0015
# waived the delisted PROBE as a build gate; it did not waive measuring what we ended up with.
DELISTED_MARKERS = ("DHFL", "JETAIRWAYS", "ALBK", "LAKSHVILAS", "INFRATEL")


def _rel(p: Path) -> str:
    """Repo-relative for display, falling back to the full path. `Path.relative_to` RAISES when the
    target is outside ROOT, which turns a cosmetic log line into a crash the moment anything is
    redirected elsewhere."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _universe(limit: int | None) -> list[str]:
    if not MEMBERSHIP.exists():
        raise SystemExit(f"{_rel(MEMBERSHIP)} not found — run "
                         f"pipelines/build/build_fo_universe.py first")
    spans = membership_spans(pd.read_parquet(MEMBERSHIP))
    syms = spans.sort_values("n_sessions", ascending=False)["symbol"].tolist()
    return syms[:limit] if limit else syms


def _load_store(interval: str) -> dict[str, pd.DataFrame]:
    d = STORE / interval
    if not d.is_dir():
        return {}
    return {p.stem: pd.read_parquet(p) for p in sorted(d.glob("*.parquet"))}


def _audit(interval: str, requested: list[str]) -> int:
    store = _load_store(interval)
    rep = coverage_report(store, requested, interval, delisted=list(DELISTED_MARKERS))
    print(rep.summary())

    seams = {}
    for sym, bars in store.items():
        cand = split_seam_candidates(bars)
        if len(cand):
            seams[sym] = [{"date": str(r["date"])[:10], "ratio": round(float(r["ratio"]), 4),
                           "nearest": round(float(r["nearest_ratio"]), 4)}
                          for _, r in cand.iterrows()]

    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps({
        "_doc": "Gate-1 coverage of the intraday store. Descriptive: it measures, it does not gate.",
        "reproduce": f"python pipelines/build/fetch_intraday_store.py --interval {interval} --audit-only",
        "interval": interval,
        "n_requested": rep.n_requested, "n_present": rep.n_present,
        "linkage_pct": rep.linkage_pct,
        "bars_by_year": rep.by_year,
        "absent_symbols": list(rep.empty_symbols),
        "delisted_requested": list(rep.delisted_requested),
        "delisted_present": list(rep.delisted_present),
        "delisted_pct": rep.delisted_pct,
        "survivorship_note": (
            "ADR-0015 waived the delisted-name PROBE as a build gate, on the ground that finding "
            "0025 measured survivorship bias scaling with holding period and an intraday book is "
            "the short end. The waiver is of the gate, not of this measurement. Any result computed "
            "on this store must state the delisted coverage above rather than imply one."),
        "split_seam_candidates": seams,
        "corporate_action_status": (
            "UNVERIFIED. Kite serves as-traded prices, so the seams listed above are CANDIDATES, "
            "not corrections. A demerger produces the same shape as a split and is not one. "
            "Adjudicate per name into nq.data.adjustment_guard.KNOWN_SEAMS with a cause."),
    }, indent=1), encoding="utf-8")

    n_seams = sum(len(v) for v in seams.values())
    print(f"split-seam candidates: {n_seams} across {len(seams)} symbols (CANDIDATES, not corrections)")
    print(f"wrote {_rel(AUDIT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", default="15minute")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=str(pd.Timestamp.today().normalize().date()))
    ap.add_argument("--limit", type=int, default=None, help="most-active N symbols (smoke runs)")
    ap.add_argument("--refetch", action="store_true", help="re-fetch symbols already on disk")
    ap.add_argument("--audit-only", action="store_true", help="audit what exists; no network")
    args = ap.parse_args()

    requested = _universe(args.limit)
    if args.audit_only:
        return _audit(args.interval, requested)

    api_key = os.getenv("KITE_API_KEY", "").strip()
    access_token = os.getenv("KITE_ACCESS_TOKEN", "").strip()
    if not api_key or not access_token:
        print("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in the environment.")
        print("This script never reads a credential from a file and never prints one.")
        return 2

    from kiteconnect import KiteConnect                       # noqa: PLC0415 — optional dep

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    print(f"resolving instrument tokens ...", flush=True)
    tokens = {r["tradingsymbol"]: r["instrument_token"] for r in kite.instruments("NSE")}
    print(f"  {len(tokens):,} listed NSE instruments | universe requested {len(requested)}\n",
          flush=True)

    out_dir = STORE / args.interval
    out_dir.mkdir(parents=True, exist_ok=True)
    last_call = [0.0]

    def historical(token, a, b, interval):
        wait = MIN_INTERVAL_S - (time.monotonic() - last_call[0])
        if wait > 0:
            time.sleep(wait)
        last_call[0] = time.monotonic()
        return kite.historical_data(token, a, b, interval)

    n_ok = n_skip = n_absent = n_fail = 0
    for i, sym in enumerate(requested, 1):
        dest = out_dir / f"{sym}.parquet"
        if dest.exists() and not args.refetch:
            n_skip += 1
            continue
        token = tokens.get(sym)
        if token is None:
            # Expected for names that left the segment: Kite lists what is CURRENTLY tradable.
            # Counted and reported rather than treated as an error — this is the delisted tail the
            # coverage audit exists to quantify.
            n_absent += 1
            continue
        try:
            bars = fetch_symbol(historical, token, args.start, args.end, args.interval,
                                on_error="skip")
        except Exception as exc:                              # noqa: BLE001 — report, keep going
            n_fail += 1
            print(f"  [{i}/{len(requested)}] {sym}: FAILED {type(exc).__name__}", flush=True)
            continue
        if len(bars):
            bars.to_parquet(dest, index=False)
            n_ok += 1
        else:
            n_absent += 1
        if i % 25 == 0 or i == len(requested):
            print(f"  [{i}/{len(requested)}] ok {n_ok} | skipped {n_skip} | "
                  f"no data {n_absent} | failed {n_fail}", flush=True)

    print(f"\nDONE. fetched {n_ok}, already had {n_skip}, no data {n_absent}, failed {n_fail}\n")
    return _audit(args.interval, requested)


if __name__ == "__main__":
    raise SystemExit(main())
