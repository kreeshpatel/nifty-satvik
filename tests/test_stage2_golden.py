"""Stage-2 KEYSTONE gate — the golden master.

Pins :func:`nq.engine.portfolio.simulate` on the FIXED carried panel
(``tests/fixtures/lh_golden_panel.csv``) + the frozen ``config.json`` cfg. Reproducing the pinned
metrics + the trade-ledger hash byte-for-byte proves the rebuilt engine ≡ the validated strategy
(equivalence proof) and guards against any future drift in sizing / exits / cost model.

The pinned values are the validated source's golden (exit-parity-unified engine): a target touch
fills AT the target (a resting limit), the hard stop is gap-aware, and the hybrid time-stop is a
clean hard cap at max_hold.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from config import load_frozen_cfg
from nq.engine.portfolio import base_risk_qty, simulate

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "lh_golden_panel.csv"
START, END = "2017-01-01", "2019-12-31"

GOLDEN_METRICS = {
    "final_equity": 1641679.2, "total_return_pct": 64.17, "cagr_pct": 18.47,
    "sharpe": 1.464, "sortino": 2.297, "max_drawdown_pct": -13.06, "calmar": 1.41,
    "turnover_per_year": 47.9, "n_trades": 140, "n_reallocated_exits": 0,
    "win_rate_pct": 65.71, "profit_factor": 1.92, "avg_return_per_trade_pct": 2.981,
    "avg_hold_days": 32.4, "avg_positions_held": 6.46,
    "exit_reasons": {"stop": 28, "trailing": 87, "target": 10, "time": 15}, "years": 2.92,
}
GOLDEN_LEDGER_HASH = "dbc94a1856681195"
GOLDEN_N_TRADES = 140


def _ledger_hash(trades: list[dict]) -> str:
    led = [(t["ticker"], str(t["entry_date"]), str(t["exit_date"]), t["reason"],
            round(float(t["return_pct"]), 2)) for t in trades]
    return hashlib.sha256(json.dumps(led, sort_keys=True).encode()).hexdigest()[:16]


@pytest.fixture(scope="module")
def golden_run():
    assert FIXTURE.exists(), f"golden fixture missing: {FIXTURE}"
    panel = pd.read_csv(FIXTURE)
    return simulate(panel, load_frozen_cfg(), start=START, end=END, initial_capital=1_000_000.0)


def test_golden_metrics_pinned(golden_run):
    """Every headline metric must match the pinned golden exactly — a mismatch means the engine
    (or the frozen cfg) changed."""
    m = golden_run["metrics"]
    for k, v in GOLDEN_METRICS.items():
        assert m[k] == v, f"metric '{k}' drifted: got {m[k]!r}, golden {v!r}"


def test_golden_trade_ledger_hash(golden_run):
    """The full trade ledger (ticker/dates/reason/return) is hash-pinned — catches drift that
    nets out in the aggregate metrics."""
    trades = golden_run["trades"]
    assert len(trades) == GOLDEN_N_TRADES, f"n_trades {len(trades)} != golden {GOLDEN_N_TRADES}"
    assert _ledger_hash(trades) == GOLDEN_LEDGER_HASH, "trade ledger drifted vs golden"


def test_base_risk_qty_parity():
    """base_risk_qty is the SINGLE sizing source of truth (live + the backtest first pass). Pin a
    table of (equity, fill, risk_per_share, adv, risk_pct) → shares so a sizing change can't
    silently diverge live from backtest."""
    cases = [
        ((1_000_000, 1000.0, 80.0, 1e9, 3.0), 150),    # risk-budget binds
        ((1_000_000, 100.0, 8.0, 5e8, 3.0), 1500),     # 15% position cap binds
        ((1_000_000, 5000.0, 600.0, 2e8, 3.0), 30),    # 5% ADV cap binds
        ((1_000_000, 1000.0, 0.0, 1e9, 3.0), 0),       # zero-risk guard
    ]
    for (equity, fill, rps, adv, risk_pct), expected in cases:
        got = base_risk_qty(equity, fill, rps, adv, risk_pct)
        assert got == expected, f"base_risk_qty{(equity, fill, rps, adv, risk_pct)} = {got} != {expected}"
