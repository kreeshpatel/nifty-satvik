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

import sys
from datetime import date, timedelta

import pandas as pd
import pytest

import nq.data.ohlcv as O


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


# --------------------------------------------------------------------------- the caller
def test_the_cron_asks_for_min_bars_one_on_the_incremental_call():
    """Guard the fix at the call site: the default is fatal here and must never come back."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "scripts"
           / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    assert "download_ohlcv(warm, start=inc_start, end=today, min_bars=1)" in src


def test_the_incremental_window_is_shorter_than_the_default_floor():
    """Pins WHY the default is wrong here: 25 calendar days can never yield 50 sessions, so the
    default guarantees the top-up is discarded rather than merely risking it."""
    inc_start = date(2026, 8, 10) - timedelta(days=25)
    sessions = len(pd.bdate_range(inc_start, date(2026, 8, 10)))
    assert sessions < 50, f"{sessions} sessions in the top-up window"
