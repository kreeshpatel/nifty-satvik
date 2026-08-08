"""The sub-period gate must SLICE one full run. Nothing enforced that until now.

CLAUDE.md names this as the most expensive defect class the programme has hit: a 2022-26 gate
computed by re-running the backtest from 2022 with fresh capital resets the equity peak and
reseasons the window boundary, giving a phantom base of Sharpe 0.762 / DD -40% against the correct
continuous slice of **0.570 / -46.3%**. A base that is 0.192 Sharpe too high is rigged against every
candidate measured on it, and it produced at least one documented false KILL (0071).

`_subperiod_cagr` slices correctly today. The gap is that only its *outputs* were tested — that the
gate keys exist, that `gate_pass` is their AND, that a worse candidate fails. A refactor to
`run_backtest(panel, cfg, start=sub_start)` would satisfy every one of those and reintroduce the
phantom, silently. So this file pins the two properties that make the slice a slice:

1. the sub-period CAGR compounds from the equity **already reached** at the window start, not from
   initial capital; and
2. `evaluate_overlay` runs the backtest over the caller's full window and only then slices — it
   never passes `sub_start` down as a run boundary.

Property 2 is structural rather than numeric on purpose. The numeric difference between a slice and
a fresh-capital re-run depends on the path, and a path where they happen to agree would let the
regression through.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nq.runner import research
from nq.runner.research import _subperiod_cagr

SUB_START = "2022-01-01"


def _curve(points: list[tuple[str, float]]) -> list[dict]:
    return [{"date": d, "equity": e} for d, e in points]


# A curve that DRAWS DOWN before the sub-window and then recovers — the shape that makes the two
# conventions disagree, and the shape 2022-26 actually had. Note the window needs at least two
# points inside it: the slice compounds between the first and last bar at-or-after `sub_start`, so
# the 2022-01-03 bar is what carries "the book is already down 20% when the window opens".
DRAWDOWN_THEN_RECOVERY = _curve([
    ("2017-01-01", 1_000_000.0),
    ("2021-12-31",   805_000.0),
    ("2022-01-03",   800_000.0),   # first in-window bar — down 20% from inception
    ("2025-12-31", 1_600_000.0),
])


def test_the_slice_compounds_from_the_equity_reached_at_the_window_start():
    """800k -> 1.6m over 3.99 calendar years = 2x = 18.963%/yr. A fresh-capital re-run would start
    the window at 1,000,000 and report 12.495% — a 6.5pp gap on the same book, in the flattering
    direction, which is exactly how the phantom 0.762 base was manufactured."""
    got = _subperiod_cagr(DRAWDOWN_THEN_RECOVERY, SUB_START, None)
    assert got == pytest.approx(18.963, abs=0.01), got

    yrs = (pd.Timestamp("2025-12-31") - pd.Timestamp("2022-01-03")).days / 365.25
    fresh_capital = ((1_600_000.0 / 1_000_000.0) ** (1.0 / yrs) - 1.0) * 100.0
    assert fresh_capital == pytest.approx(12.495, abs=0.01)
    assert got - fresh_capital > 5.0, (
        "the slice and a fresh-capital re-run returned nearly the same number on this fixture, so "
        "this test cannot distinguish them — pick a path where they diverge"
    )


def test_what_happened_before_the_window_reaches_the_gate_only_through_the_equity_level():
    """Two books with identical in-window paths but different histories must score identically.
    This is what 'continuous slice' means: the window is read off one run, not restarted."""
    calm = DRAWDOWN_THEN_RECOVERY
    violent = _curve([
        ("2017-01-01", 1_000_000.0),
        ("2019-06-30", 2_500_000.0),   # a boom the other book never had
        ("2020-03-23",   400_000.0),   # and a crash
        ("2021-12-31",   805_000.0),
        ("2022-01-03",   800_000.0),   # identical from here on
        ("2025-12-31", 1_600_000.0),
    ])
    assert _subperiod_cagr(calm, SUB_START, None) == _subperiod_cagr(violent, SUB_START, None)


def test_a_slice_shorter_than_two_points_is_uncomputable_not_zero():
    """Fail-closed: an uncomputable gate must return None so `gate_pass` cannot promote on it."""
    assert _subperiod_cagr(DRAWDOWN_THEN_RECOVERY, "2030-01-01", None) is None
    assert _subperiod_cagr([], SUB_START, None) is None


def test_evaluate_overlay_never_passes_sub_start_as_a_run_boundary(monkeypatch):
    """The structural guard. `sub_start` selects a slice of the result; it must never become the
    `start` of a backtest. If someone refactors to `run_backtest(panel, cfg, start=sub_start)` for
    speed or clarity, the phantom base comes back and every numeric gate test still passes."""
    seen: list[dict] = []

    def fake_run_backtest(panel, cfg, *, start=None, end=None, initial_capital=1_000_000.0, **kw):
        seen.append({"start": start, "end": end, "initial_capital": initial_capital})
        return {"equity_curve": [], "trades": [], "metrics": {}}

    monkeypatch.setattr(research, "run_backtest", fake_run_backtest)
    monkeypatch.setattr(research, "adjudicate", lambda *a, **k: {"verdict": "STUB"})

    research.evaluate_overlay(
        pd.DataFrame(), {"a": 1}, {"a": 2},
        start="2017-01-01", end="2026-06-30", sub_start=SUB_START,
    )

    assert len(seen) == 2, f"expected one base arm and one candidate arm, got {len(seen)}"
    for arm in seen:
        assert arm["start"] == "2017-01-01", (
            f"an arm was run from {arm['start']!r}. If that is the sub-window start, the equity "
            f"peak has been reset and the 2022-26 gate is the phantom 0.762 base again."
        )
        assert arm["end"] == "2026-06-30"
        assert arm["initial_capital"] == 1_000_000.0, (
            "both arms must start from the same capital; re-seeding one is the same defect wearing "
            "a different hat"
        )


def test_both_arms_are_run_over_the_same_window(monkeypatch):
    """A subtler version of the same failure: slicing the candidate but not the base."""
    seen: list[tuple] = []
    monkeypatch.setattr(
        research, "run_backtest",
        lambda panel, cfg, *, start=None, end=None, **kw: (
            seen.append((start, end)) or {"equity_curve": [], "trades": [], "metrics": {}}
        ),
    )
    monkeypatch.setattr(research, "adjudicate", lambda *a, **k: {})
    research.evaluate_overlay(pd.DataFrame(), {}, {}, start="2017-01-01", end="2026-06-30")
    assert len(set(seen)) == 1, f"base and candidate ran over different windows: {seen}"
