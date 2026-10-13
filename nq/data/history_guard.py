"""History-truncation guard: a vendor that shortens a name's history must not erase an open trade.

2026-10-03: the vendor began serving HEG.NS only from 2026-07-17 after its 2026-09-07 demerger. With
fewer than 44 weekly bars the engine could not form the 44-week SMA, and because the weekly history is
rebuilt from inception every scan, the open HEG trade (ACTIVE on 2026-09-25) was deleted — no exit row,
no warning. The adjustment guard looks for price STEPS; it is blind to a series that simply got shorter.

This guard looks at the shape of each OPEN trade's series after every refresh:

  * missing   — an open name has no bars at all;
  * short     — fewer than ``MIN_WEEKS`` distinct weeks, so the SMA cannot exist;
  * truncated — the first bar moved LATER than in the cache the run started from.

Any of those on an open trade (held in the capital book, or ACTIVE in the uncapped tracker) raises,
halting the scan before the rebuild can rewrite the record. The route out is an owner decision recorded
in ``ACKNOWLEDGED`` with its date and reason — never widening the threshold to get the scan green.
Truncation on a name with no open trade is reported, not raised: it can only restate closed history,
which the snapshot drift log already flags.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

MIN_WEEKS = 45               # 44-week SMA + the signal week itself
TRUNCATION_TOLERANCE_DAYS = 30   # vendor start dates wobble by a few sessions; a month is not a wobble

# Owner-acknowledged truncations: {ticker: "YYYY-MM-DD reason"}. An entry silences the halt for that
# name only. HEG's trade was already erased and declared (option (c), 2026-10-13) before this guard
# existed, and HEG is no longer open, so it needs no entry.
ACKNOWLEDGED: dict[str, str] = {}


def history_starts(ohlcv: dict) -> dict[str, pd.Timestamp]:
    """First bar per name. Pure."""
    out = {}
    for t, df in (ohlcv or {}).items():
        if df is not None and len(df):
            out[t] = pd.Timestamp(df.index.min())
    return out


def open_tickers(results_dir: Path) -> set[str]:
    """Names with an open trade: the capital book's positions and the tracker's ACTIVE rows.

    The tracker matters as much as the book — HEG was erased from the tracker's history, which is the
    record the readiness gate counts."""
    names: set[str] = set()
    pf = results_dir / "paper_portfolio_weekly.json"
    hist = results_dir / "signals_history_weekly.json"
    try:
        names |= set(json.loads(pf.read_text(encoding="utf-8")).get("positions", {}))
    except Exception:            # absent/unreadable book -> the tracker still counts
        pass
    try:
        rows = json.loads(hist.read_text(encoding="utf-8"))
        rows = rows if isinstance(rows, list) else []
        names |= {r.get("ticker") for r in rows if isinstance(r, dict) and r.get("status") == "ACTIVE"}
    except Exception:
        pass
    names.discard(None)
    return names


def check_history(prev_starts: dict, ohlcv: dict, open_names, *,
                  acknowledged: dict | None = None) -> dict:
    """Classify every series problem; ``escalate`` lists the ones on open trades. Pure."""
    ack = ACKNOWLEDGED if acknowledged is None else acknowledged
    starts = history_starts(ohlcv)
    truncated = []
    for t, before in (prev_starts or {}).items():
        now = starts.get(t)
        if now is not None and (now - pd.Timestamp(before)).days > TRUNCATION_TOLERANCE_DAYS:
            truncated.append({"symbol": t, "was": str(pd.Timestamp(before).date()), "now": str(now.date())})
    trunc_names = {d["symbol"] for d in truncated}

    problems = []
    for t in sorted(open_names or ()):
        df = (ohlcv or {}).get(t)
        if df is None or not len(df):
            problems.append({"symbol": t, "why": "missing"})
            continue
        weeks = pd.DatetimeIndex(df.index).to_period("W").nunique()
        if weeks < MIN_WEEKS:
            problems.append({"symbol": t, "why": f"short ({weeks} weeks < {MIN_WEEKS})"})
        elif t in trunc_names:
            d = next(x for x in truncated if x["symbol"] == t)
            problems.append({"symbol": t, "why": f"truncated (start {d['was']} -> {d['now']})"})
    escalate = [p for p in problems if p["symbol"] not in ack]
    return {"truncated": truncated, "open_problems": problems, "escalate": escalate,
            "acknowledged": [p for p in problems if p["symbol"] in ack]}


def assert_open_history_intact(prev_starts: dict, ohlcv: dict, open_names, *,
                               acknowledged: dict | None = None) -> dict:
    """Raise when an open trade's series cannot carry it. Halting is the point: the alternative is a
    rebuild that deletes the trade and reports success."""
    rep = check_history(prev_starts, ohlcv, open_names, acknowledged=acknowledged)
    if rep["escalate"]:
        lines = "\n".join(f"  {p['symbol']}: {p['why']}" for p in rep["escalate"])
        raise ValueError(
            "HISTORY TRUNCATION ON AN OPEN TRADE — the weekly rebuild would erase it (HEG, 2026-10-03).\n"
            f"{lines}\n"
            "This returns to the owner. Record the decision in nq.data.history_guard.ACKNOWLEDGED with "
            "its date and reason; do NOT lower MIN_WEEKS or bypass this to get the scan green.")
    return rep
