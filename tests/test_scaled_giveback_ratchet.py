"""0148: the giveback ratchet on the scaled-exit branch is inert when absent and real when on.

Before 2026-10-13 the `lockin_mfe` lever sat after the scaled branch's `continue`, so passing it with the
live exit changed nothing — a lever that silently does nothing is how a study measures a no-op.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

SCALED = dict(tp1_r=2.0, tp1_frac=0.40, tp2_r=3.0, tp2_frac=0.0,
              pattern_frac=0.40, pattern_arm_r=2.5, runner_sma_buffer=0.0)
KW = dict(ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20)


@pytest.fixture(scope="module")
def prep():
    import run_bhanushali_weekly_rank as R94
    from build_r94_golden_fixture import synth_universe
    ohlcv, _ = synth_universe()
    return R94, R94.prep_weekly_rank(ohlcv)


def _run(R94, P, **scaled):
    led, ev = [], []
    R94.backtest(P, None, ledger=led, uncapped=True, event_log=ev, scaled_exit={**SCALED, **scaled}, **KW)
    return led, ev


def test_absent_and_zero_are_byte_identical_to_the_live_exit(prep):
    R94, P = prep
    base, _ = _run(R94, P)
    zero, _ = _run(R94, P, lockin_mfe=0.0)
    assert base == zero


def test_the_ratchet_fires_and_changes_outcomes_when_on(prep):
    """A low arm (1.0R -> 0.5R) so the hermetic fixture is certain to trigger it."""
    R94, P = prep
    base, _ = _run(R94, P)
    on, ev = _run(R94, P, lockin_mfe=1.0, lockin_at=0.5)
    fired = [e for e in ev if e.get("event_type") == "stop_ratchet" and e.get("reason_code") == "lockin_at"]
    assert fired, "the ratchet never fired on the fixture — the test would be vacuous"
    assert on != base, "the ratchet fired yet changed no trade"
    for e in fired:
        assert e["stop_after"] > e["stop_before"]
