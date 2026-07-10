"""
build_hdfc_equity_master.py — compress HDFC Securities' Security Master CSV
(a multi-MB dump of every NSE/BSE/MCX instrument across all segments — equity,
options, futures, currency) down to a small committed JSON mapping
SYMBOL -> {exchange, token} for cash-market equities only.

Why this exists: /oapi/v1/fetch-ltp takes a numeric HDFC `token` + `exchange`,
never a ticker symbol — the raw CSV is the only place that mapping lives, and
it's too large (~9MB, 120k+ rows, mostly derivatives) to ship/commit as-is or
parse on every request.

Dedup rule (verified against the 2026-07-10 export, 239 same-(symbol,exchange)
collision groups out of 11,073 total EQUITY rows): the raw CSV mixes real
equity lines with bonds/NCDs/mutual-fund-NCDs/rights/partly-paid variants that
sloppily share the same `symbol_name`. A single suffix filter (e.g. requiring
security_id to end in "EQNR") is NOT enough — it wrongly excludes legitimate,
unambiguous listings that don't follow that convention (e.g. SYRMA's
security_id is "SYRMASGS", DELHIVERY's is "DELHIVERY" — no EQNR, no collision,
still a real equity). So: include every (symbol, exchange) pair by default,
and only apply a tiebreak cascade when there's a genuine collision:
    1. exactly one row's security_id equals the symbol (alnum-normalized)  -> 93 resolved
    2. else exactly one row's security_id ends in "EQNR"                  -> 82 resolved
    3. else the row with the highest close_price (junk/dead rows show 0)  -> 58 resolved
    4. else first row, deterministic (6 residual — all illiquid/zero-price
       mutual-fund-NCD tickers outside any real trading universe)
Prefer NSE over BSE per the app's NSE-first convention (nq.data conventions).

Usage:
    python scripts/build_hdfc_equity_master.py <path-to-ir-security-master.csv>

Re-run whenever you export a fresh Security Master CSV from developer.hdfcsec.com
(new listings need re-running this; existing tokens are stable long-term).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "backend" / "data" / "hdfc_equity_master.json"
EXCHANGE_PRIORITY = {"NSE": 0, "BSE": 1}


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _price(r: dict) -> float:
    try:
        return float(r.get("close_price") or 0)
    except ValueError:
        return 0.0


def _resolve_collision(symbol: str, group: list[dict]) -> dict:
    exact = [r for r in group if _norm(r["security_id"]) == _norm(symbol)]
    if len(exact) == 1:
        return exact[0]
    eqnr = [r for r in group if r["security_id"].endswith("EQNR")]
    if len(eqnr) == 1:
        return eqnr[0]
    best = max(group, key=_price)
    return best  # falls back to group[0] equivalent when all prices are 0


def build(csv_path: str) -> dict:
    with open(csv_path, encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.DictReader(f))

    candidates = [
        r for r in rows
        if r.get("instrument_segment") == "EQUITY" and r.get("symbol_name", "").strip()
    ]

    by_sym_exch: dict[tuple, list[dict]] = defaultdict(list)
    for r in candidates:
        sym = r["symbol_name"].strip().upper()
        by_sym_exch[(sym, r["exchange"])].append(r)

    by_symbol: dict[str, dict] = {}
    for (sym, exch), group in by_sym_exch.items():
        row = group[0] if len(group) == 1 else _resolve_collision(sym, group)
        existing = by_symbol.get(sym)
        if existing and EXCHANGE_PRIORITY.get(exch, 9) >= EXCHANGE_PRIORITY.get(existing["exchange"], 9):
            continue  # keep the higher-priority (NSE) entry already recorded
        by_symbol[sym] = {"exchange": exch, "token": row["exch_security_id"]}

    return dict(sorted(by_symbol.items()))


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    master = build(sys.argv[1])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(master, indent=0, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(master)} symbols -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
