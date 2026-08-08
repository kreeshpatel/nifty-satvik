"""Build the golden fixture + expectations for ``nq.engine.rebalance_book``.

WHY THIS EXISTS. Golden masters covered `portfolio.simulate` (test_stage2_golden), the feature layer
(test_stage1_golden) and the live swing engine (test_r94_golden). The engine carrying pre-registration
0001 — `rebalance_book` — had none: `tests/test_rebalance_book.py` is 33 synthetic-panel property
tests on twelve hand-built names, with no fixture, no hash and no real data. It is also the engine
that produced six defects in a single session (2026-08-07), which makes it the least proven engine in
the repo and the only one without a pinned real-data output.

WHAT IS PINNED, and what is deliberately not. The 0001 production panel is ~1.5M rows and cannot be
committed. This fixture is a deterministic real-data SLICE of the same MID-band universe, sized so it
still exercises every path the engine has: entry, buffer hysteresis, equal-weight trimming, exit by
falling out of the ranking, the ADV participation cap, and the stale force-close. It pins the
ENGINE's behaviour. The 0001 *result* is pinned separately in `research/0001-xsec-momentum/`.

The book is deliberately smaller than production (top_n=10, buffer 1.5 -> cap 15) so a 25-name
fixture can drive it. A golden that needs 45 names to hold 30 would need a fixture too large to
commit, and would pin no path the smaller book does not.

Determinism. Names are chosen by median rupee turnover over the window with ticker as the tiebreak;
no RNG, no clock, no network. Re-running must reproduce the CSV byte-for-byte.

    python scripts/build_rebalance_golden_fixture.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "pipelines" / "research"))
from nq.data.membership import load_membership  # noqa: E402
from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book  # noqa: E402
from nq.universe import build_universe  # noqa: E402

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "rebalance_golden_panel.csv"
EXPECTED_JSON = ROOT / "tests" / "fixtures" / "rebalance_golden_expected.json"

# The golden window and book. Fixed here, and mirrored in the test.
START, END = "2017-01-01", "2019-12-31"
N_NAMES = 25
BOOK = dict(top_n=10, buffer_mult=1.5, max_position_pct=15.0, cadence="M")
CAPITAL = 1_000_000.0
COLS = ["date", "ticker", "open", "high", "low", "close", "adv_rupees_20d", "rank"]


def fixture_csv_sha16(path: Path) -> str:
    """Digest over NEWLINE-NORMALISED bytes.

    Hashing raw bytes makes the check platform-dependent: with core.autocrlf=true a Windows working
    tree holds CRLF while git stores (and Linux CI checks out) LF, so the identical committed file
    hashes two ways and CI goes red while local is green. That exact failure is why
    `test_r94_golden.py` normalises, and why `.gitattributes` also marks these fixtures `-text`.
    Belt and braces: either alone would do, and both together cost nothing.
    """
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()[:16]


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def ledger_hash(trades: list[dict]) -> str:
    """Every trade's identity and outcome — catches drift that nets out in the aggregate metrics."""
    return _digest([(t["ticker"], str(t["entry_date"]), str(t["exit_date"]), t["reason"],
                     int(t["qty"]), round(float(t["return_pct"]), 4)) for t in trades])


def curve_hash(curve: list[dict]) -> str:
    """The full equity path, not just its endpoint — two very different paths can share a final
    value, and the drawdown lives in the path."""
    return _digest([(e["date"], round(float(e["equity"]), 2), int(e["n_positions"])) for e in curve])


def build_panel() -> pd.DataFrame:
    """The deterministic real-data slice."""
    from run_0001_xsec_momentum import BAND, add_signals
    from run_bhanushali_path1 import corrected_universe

    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)

    # Band membership gates the RANK, never the ROWS — the same rule pre-registration 0001 had to
    # learn the hard way. Filtering rows by `size_band == MID` deletes a name's prices the moment it
    # crosses the rank-100/101 boundary, which churns constantly; the engine then cannot price a
    # sale and force-closes days later at a stale mark. Building the fixture that way produced a
    # panel with 2,518 rows across 481 sessions (about 5 names quotable per day against a 15-slot
    # book), 28 stale closes out of 317 trades, and a -18.6% CAGR — a golden that would have pinned
    # the bug rather than the engine.
    # Deterministic name choice: the names that spend the MOST SESSIONS actually rankable in the
    # band, ticker as tiebreak.
    #
    # Selecting by raw turnover instead is the trap, and it is not obvious: the highest-turnover
    # names among those that were ever MID are, on most days, LARGE — turnover rank 1-100 — so they
    # are ineligible for a MID book nearly all the time. That choice produced a fixture where only
    # ~3.4 of 15 slots were ever filled, so the buffer, trim and cap paths the golden exists to pin
    # were barely exercised. Time-in-band is the property the book actually needs.
    rankable = p["eligible"] & (p["size_band"] == BAND) & p["nms"].notna()
    tenure = (p[rankable].groupby("ticker").size().rename("sessions")
              .reset_index().sort_values(["sessions", "ticker"], ascending=[False, True]))
    names = sorted(tenure["ticker"].head(N_NAMES).tolist())

    q = p[p["ticker"].isin(names)].copy()
    q["rank"] = np.where(q["eligible"] & (q["size_band"] == BAND) & q["nms"].notna(),
                         q["nms"], np.nan)
    q = q[COLS].sort_values(["date", "ticker"]).reset_index(drop=True)
    q["date"] = q["date"].dt.strftime("%Y-%m-%d")
    for c in ("open", "high", "low", "close", "adv_rupees_20d", "rank"):
        q[c] = q[c].astype(float).round(6)
    return q


def run_golden(panel: pd.DataFrame) -> dict:
    cfg = RebalanceConfig(**BOOK)
    bt = simulate_rebalance_book(panel, cfg=cfg, start=START, end=END, initial_capital=CAPITAL)
    m = bt["metrics"]
    reasons: dict[str, int] = {}
    for t in bt["trades"]:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
    return {
        "n_trades": len(bt["trades"]),
        "n_sessions": len(bt["equity_curve"]),
        "final_equity": m["final_equity"],
        "cagr_pct": m["cagr_pct"],
        "sharpe": m["sharpe"],
        "sortino": m["sortino"],
        "max_drawdown_pct": m["max_drawdown_pct"],
        "calmar": m["calmar"],
        "turnover_per_year": m["turnover_per_year"],
        "avg_positions_held": m["avg_positions_held"],
        "avg_hold_days": m["avg_hold_days"],
        "win_rate_pct": m["win_rate_pct"],
        "profit_factor": m["profit_factor"],
        "years": m["years"],
        "exit_reasons": reasons,
        "ledger_hash": ledger_hash(bt["trades"]),
        "curve_hash": curve_hash(bt["equity_curve"]),
    }


def main() -> int:
    print("=== building the rebalance_book golden fixture ===")
    panel = build_panel()
    FIXTURE_CSV.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" so the committed bytes are LF on every platform
    panel.to_csv(FIXTURE_CSV, index=False, lineterminator="\n")
    size_mb = FIXTURE_CSV.stat().st_size / 1e6
    print(f"  {FIXTURE_CSV.name}: {len(panel):,} rows · {panel['ticker'].nunique()} names "
          f"· {size_mb:.2f} MB")

    cells = run_golden(pd.read_csv(FIXTURE_CSV))
    expected = {
        "window": [START, END], "book": BOOK, "initial_capital": CAPITAL,
        "n_names": int(panel["ticker"].nunique()),
        "fixture_csv_sha16": fixture_csv_sha16(FIXTURE_CSV),
        "cells": {"frozen_0001_engine": cells},
    }
    EXPECTED_JSON.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"  fixture sha16 {expected['fixture_csv_sha16']}")
    for k, v in cells.items():
        print(f"    {k:<20} {v}")
    print(f"\n  -> {EXPECTED_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
