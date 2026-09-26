"""The daily position ledger: it must record everything and change nothing.

Added 2026-09-25 on the owner's instruction, after Track P2 could not answer a portfolio-level
question from any committed artifact. `curve` recorded what the book was WORTH each session; nothing
recorded what it HELD. Reconstructing holdings from the trade ledger failed by 34% of NAV, because
the live exit sells in tranches -- config P is 40% at +2R, 40% on the pattern trigger armed at
+2.5R and a 20% runner, with `tp2_frac = 0.0` so nothing sells at +3R -- and the trade ledger carries
at most one of them.

Two properties are asserted, and the first is the one that matters on a live book:

  1. **It changes nothing.** The engine's outputs with the log on must be byte-identical to the same
     run with it off. `tests/test_r94_golden.py` pins the frozen and live cells against a stored
     expectation; this pins the two runs against EACH OTHER, which catches a drift introduced by the
     logging code itself even if the golden fixture were ever regenerated.
  2. **It reconciles.** cash + Σ notional must equal the equity the engine reports that session. A
     position ledger that does not add up to the NAV is worse than none, because it would be trusted.

The fixture is the hermetic synthetic universe (no RNG, no network, no live cache) that the golden
master already uses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture(scope="module")
def runs():
    """The same backtest twice: once with the log off (the default), once with it on."""
    import run_bhanushali_weekly_rank as R94
    from build_r94_golden_fixture import synth_universe

    ohlcv, _index = synth_universe()
    prep = R94.prep_weekly_rank(ohlcv)

    def go(log):
        ledger: list = []
        out = R94.backtest(prep, None, ledger=ledger, ext_cap=0.20, max_risk_pct=0.10,
                           max_notional_pct=0.20, position_log=log)
        return out, ledger

    off_out, off_led = go(None)
    log: list = []
    on_out, on_led = go(log)
    return {"off": (off_out, off_led), "on": (on_out, on_led), "log": log}


def _blob(out: dict, ledger: list) -> str:
    """Everything the engine returns, rendered deterministically for an exact comparison."""
    return json.dumps({"out": out, "ledger": ledger}, sort_keys=True, default=str)


def test_the_log_changes_nothing(runs):
    off_out, off_led = runs["off"]
    on_out, on_led = runs["on"]
    assert _blob(on_out, on_led) == _blob(off_out, off_led), (
        "the daily position ledger altered the engine's output. It is observation only: rows are "
        "appended to a caller-owned list and never read back, so any diff here is a defect in the "
        "logging code, not a configuration choice.")


def test_the_log_actually_recorded_something(runs):
    """A guard that passes because nothing ran is the failure mode this whole file exists to avoid."""
    log = runs["log"]
    assert len(log) > 0, "no position rows recorded — the fixture produced no held positions"
    assert {"date", "tkr", "shares", "mark_px", "notional", "cash", "equity"} <= set(log[0])


def test_cash_plus_notional_equals_the_equity_the_engine_reports(runs):
    """The reconciliation the trade-ledger reconstruction could not pass."""
    log = runs["log"]
    by_day: dict = {}
    for row in log:
        cell = by_day.setdefault(row["date"], {"notional": 0.0, "cash": row["cash"],
                                               "equity": row["equity"]})
        cell["notional"] += row["notional"]
        # cash and equity are book-level: every row for a session must agree on them
        assert cell["cash"] == row["cash"]
        assert cell["equity"] == row["equity"]
    assert by_day, "no sessions recorded"
    for day, cell in by_day.items():
        assert cell["cash"] + cell["notional"] == pytest.approx(cell["equity"], rel=1e-12), (
            f"{day}: cash {cell['cash']} + notional {cell['notional']} != equity {cell['equity']}")


def test_every_session_with_a_held_name_is_covered(runs):
    """The share path must have no holes: a name held across a session needs a row for it."""
    _out, ledger = runs["on"]
    import pandas as pd
    log = pd.DataFrame(runs["log"])
    sessions = sorted(log["date"].unique())
    logged = {(pd.Timestamp(r.date).normalize(), r.tkr) for r in log.itertuples(index=False)}
    for t in ledger:
        a = pd.Timestamp(t["entry_date"]).normalize()
        b = pd.Timestamp(t["exit_date"]).normalize()
        # the exit fills at that session's price and the position leaves the book, so the covered
        # span is [entry, exit) — the entry session itself is held from its close
        span = [d for d in sessions if a <= pd.Timestamp(d).normalize() < b]
        missing = [d for d in span if (pd.Timestamp(d).normalize(), t["tkr"]) not in logged]
        assert not missing, f"{t['tkr']} held but unlogged on {missing[:5]}"


def test_shares_fall_at_a_recorded_tranche_and_never_rise(runs):
    """The property the trade ledger could not express — this is the whole point of the change."""
    import pandas as pd
    log = pd.DataFrame(runs["log"]).sort_values(["tkr", "date"])
    for tkr, g in log.groupby("tkr"):
        sh = g["shares"].to_numpy(float)
        # within one continuous holding shares only ever decrease (tranches); a RE-ENTRY resets them
        # upward, and those are separated by a gap in the session sequence
        dates = pd.DatetimeIndex(g["date"]).normalize()
        sessions = sorted(pd.DatetimeIndex(log["date"]).normalize().unique())
        pos = {d: i for i, d in enumerate(sessions)}
        for k in range(1, len(sh)):
            contiguous = pos[dates[k]] == pos[dates[k - 1]] + 1
            if contiguous:
                assert sh[k] <= sh[k - 1] + 1e-9, (
                    f"{tkr}: shares rose from {sh[k - 1]} to {sh[k]} inside one holding")
