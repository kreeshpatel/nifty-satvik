"""The incremental top-up must actually reach the cache.

`download_ohlcv` dropped any name returning fewer than 50 usable bars. That is correct for a
FULL-history pull — a name with a handful of bars cannot warm up a 44-week SMA. It was fatal for the
INCREMENTAL path: `run_bhanushali_cron._refresh_ohlcv` asks for a ~25-day window, roughly 18 trading
bars, so every warm name was discarded, `merge_ohlcv` folded an empty dict into the cache, and the
cron printed a success line over an unchanged cache.

The observable consequence was a book that only advanced when the monthly actions/cache key rolled
and every name came back cold. The 2026-08-10 run succeeded, committed, and published
`generated_at: 2026-07-31` — the last session before the 2026-08-01 rebuild. The dashboard was not
stale because a job failed; it was stale because a job SUCCEEDED without new data.

Hermetic: yfinance is stubbed, so nothing here opens a socket.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

import nq.data.ohlcv as O

_spec = importlib.util.spec_from_file_location(
    "check_ohlcv_topup_contract",
    Path(__file__).resolve().parents[1] / "scripts" / "check_ohlcv_topup_contract.py")
_cc = importlib.util.module_from_spec(_spec)
sys.modules["check_ohlcv_topup_contract"] = _cc
_spec.loader.exec_module(_cc)


class _FakeYF:
    """Returns `n_bars` sessions per ticker in yfinance's group_by='ticker' MultiIndex shape."""

    def __init__(self, n_bars: int):
        self.n_bars = n_bars
        self.calls: list[dict] = []

    def download(self, tickers, start=None, end=None, group_by=None, auto_adjust=None,
                 threads=None, progress=None):
        self.calls.append({"tickers": list(tickers), "start": start, "end": end})
        idx = pd.bdate_range(end=pd.Timestamp("2026-08-10"), periods=self.n_bars)
        frames = {}
        for t in tickers:
            frames[t] = pd.DataFrame(
                {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 100}, index=idx)
        return pd.concat(frames, axis=1)


@pytest.fixture()
def stub(monkeypatch):
    def _install(n_bars: int) -> _FakeYF:
        fake = _FakeYF(n_bars)
        monkeypatch.setitem(sys.modules, "yfinance", fake)
        # `download_ohlcv` does `import time` INSIDE the function, so there is no module attribute
        # to patch — the real module is what it resolves, and the per-batch sleep is 1s.
        monkeypatch.setattr("time.sleep", lambda *_: None)
        return fake
    return _install


@pytest.fixture()
def tmp_probe():
    """Write a throwaway module into scripts/ and return the checker's findings for it.

    The checker scans real source directories, so a probe has to live in one; naming it with a
    leading underscore keeps it out of import paths, and it is removed even when the test fails.

    The name carries the pid so two pytest processes (xdist, or a stray parallel run) cannot race
    on one path — the loser would otherwise read the winner's source and the leftover would be
    picked up by the very check it is testing.
    """
    import os
    from pathlib import Path
    stem = f"__ohlcv_contract_probe_{os.getpid()}"
    probe = Path(__file__).resolve().parents[1] / "scripts" / f"{stem}.py"

    def _run(src: str) -> list[str]:
        probe.write_text(src, encoding="utf-8")
        try:
            return [p for p in _cc.verify() if stem in p]
        finally:
            probe.unlink(missing_ok=True)
    return _run


# --------------------------------------------------------------------------- the defect
def test_a_short_window_is_dropped_at_the_default_and_this_was_the_bug(stub):
    """18 bars is what a 25-day top-up returns. At the default it vanishes — silently."""
    stub(18)
    out = O.download_ohlcv(["RELIANCE", "CUB"], start="2026-07-15", end="2026-08-11")
    assert out == {}, "the top-up path was discarding every warm name"


def test_min_bars_one_lets_the_top_up_through(stub):
    stub(18)
    out = O.download_ohlcv(["RELIANCE", "CUB"], start="2026-07-15", end="2026-08-11", min_bars=1)
    assert set(out) == {"RELIANCE", "CUB"}
    assert all(len(df) == 18 for df in out.values())


def test_the_default_is_unchanged_for_a_full_history_pull(stub):
    """The 50-bar floor still rejects junk on the path it was written for."""
    # Two tickers: the cron batches 25, so the multi-ticker branch is the live path. (The
    # single-ticker branch assumes flat columns and is a separate question this does not touch.)
    stub(60)
    assert set(O.download_ohlcv(["RELIANCE", "CUB"], start="2015-01-01", end="2026-08-11")) \
        == {"RELIANCE", "CUB"}
    stub(49)
    assert O.download_ohlcv(["RELIANCE", "CUB"], start="2015-01-01", end="2026-08-11") == {}


def test_an_empty_download_leaves_the_cache_untouched_rather_than_erroring():
    """The mechanism that turned the defect into SILENCE: merging nothing is a no-op, so the cron
    saw no exception and published a success line over a stale cache."""
    cached = {"RELIANCE": pd.DataFrame(
        {"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1},
        index=pd.bdate_range("2026-07-01", periods=20))}
    merged = O.merge_ohlcv(cached, {})
    assert set(merged) == {"RELIANCE"}
    assert len(merged["RELIANCE"]) == 20


# --------------------------------------------------------------------------- the callers
#
# This section used to be ONE test asserting a literal line of run_bhanushali_cron.py. It stayed
# green while `run_paper_cron.py` committed the identical defect and froze the forward wall for
# five sessions (2026-08-24 .. 2026-08-28), because it was watching the other file. A guard that
# pins one call site cannot see the second one, so the check now runs over every call site.

def test_no_call_site_relies_on_the_default_for_a_short_window():
    problems = _cc.verify()
    assert not problems, " | ".join(
        ["these download_ohlcv() calls will silently discard every name"]
        + problems
        + ["pass min_bars=1 on a top-up, or widen the window past the 50-session floor"])


# --- probe sources, as they appear (or appeared) in the real callers ------------------------
PRE_FIX = """
from datetime import date, timedelta
def main():
    dl_start = hist_start if not ohlcv else (date.today() - timedelta(days=15)).isoformat()
    fresh = download_ohlcv(universe, start=dl_start, end=end)
"""

FIXED = """
from datetime import date, timedelta
def main():
    topup_start = (date.today() - timedelta(days=15)).isoformat()
    fresh = download_ohlcv(universe, start=topup_start, end=end, min_bars=1)
"""

FULL_HISTORY = """
def main():
    fresh = download_ohlcv(universe, start=hist_start, end=end)
"""

WIDE_WINDOW = """
from datetime import date, timedelta
def main():
    dl_start = (date.today() - timedelta(days=120)).isoformat()
    fresh = download_ohlcv(tickers, start=dl_start, end=today)
"""

SHARED_NAME = """
from datetime import date, timedelta
def topup():
    dl_start = (date.today() - timedelta(days=15)).isoformat()
    return download_ohlcv(u, start=dl_start, end=e, min_bars=1)
def full():
    dl_start = '2015-01-01'
    return download_ohlcv(u, start=dl_start, end=e)
"""


def test_the_checker_catches_the_defect_that_froze_the_wall(tmp_probe):
    """The exact pre-fix line from run_paper_cron.py. If this stops firing, the guard is decorative."""
    hits = tmp_probe(PRE_FIX)
    assert hits, "the checker did not flag a 15-day top-up at the default"
    assert "15-day window" in hits[0]


def test_the_fix_satisfies_the_checker(tmp_probe):
    assert not tmp_probe(FIXED)


def test_a_full_history_pull_is_left_alone(tmp_probe):
    """The default is CORRECT there — a name with a handful of bars cannot warm up the features. A
    checker that forced min_bars=1 everywhere would readmit the junk the floor exists to reject."""
    assert not tmp_probe(FULL_HISTORY)


def test_the_monitors_120_day_window_is_not_flagged(tmp_probe):
    """run_bhanushali_monitor deliberately asks for ~120 days so the DEFAULT is satisfiable. That is
    a second valid way to hold the contract, and flagging it would be a false positive."""
    assert not tmp_probe(WIDE_WINDOW)


def test_a_sibling_functions_variable_does_not_decide_this_call(tmp_probe):
    """Each call resolves `start` in its OWN scope. Sharing a name across functions must not make a
    safe call inherit a neighbour's short window — that would be a false positive on correct code."""
    assert not tmp_probe(SHARED_NAME)


def test_the_incremental_window_is_shorter_than_the_default_floor():
    """Pins WHY the default is wrong here: 25 calendar days can never yield 50 sessions, so the
    default guarantees the top-up is discarded rather than merely risking it."""
    inc_start = date(2026, 8, 10) - timedelta(days=25)
    sessions = len(pd.bdate_range(inc_start, date(2026, 8, 10)))
    assert sessions < 50, f"{sessions} sessions in the top-up window"


def test_the_checkers_safe_window_agrees_with_that_arithmetic():
    """MIN_SAFE_WINDOW_DAYS is the checker's whole judgement call. Tie it to the fact it encodes,
    so a future edit that loosens it has to disagree with the calendar rather than with a comment."""
    span = timedelta(days=_cc.MIN_SAFE_WINDOW_DAYS)
    sessions = len(pd.bdate_range(date(2026, 8, 10) - span, date(2026, 8, 10)))
    assert sessions >= 50, (
        f"{_cc.MIN_SAFE_WINDOW_DAYS} days yields only {sessions} sessions — the checker would "
        f"clear a window that still cannot satisfy the default min_bars=50")
