"""The wall's OHLCV-depth guard — the gate that decides deep-fetch vs no-op.

The one behaviour that matters: a cache that already runs deep must NOT trigger a download (or a
local dev machine re-fetches 3 years every run), and a uniformly shallow runner cache MUST. The
gate is `_earliest(cache) > target`, and `_earliest` is min-over-names so one freshly-listed name
in an otherwise-deep cache does not force a needless fetch.
"""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.ensure_ohlcv_depth import _earliest, main


def _df(start: str, n: int = 30) -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=n, name="Date")
    return pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1}, index=idx)


def test_earliest_is_min_over_names_not_max():
    """A deep cache with one recently-listed name still reports its EARLIEST date, so the gate stays
    a no-op there rather than re-fetching on account of the new name."""
    cache = {"OLD": _df("2019-01-01"), "IPO": _df("2026-01-01")}
    assert _earliest(cache) == pd.Timestamp("2019-01-01")


def test_earliest_none_on_empty_cache():
    assert _earliest({}) is None


def test_deep_cache_is_a_noop_and_never_downloads(monkeypatch):
    """The load-bearing negative: reaching back past the target must not call download_ohlcv."""
    import scripts.ensure_ohlcv_depth as mod

    monkeypatch.setattr(mod, "load_ohlcv_cache", lambda _c: {"A": _df("2019-01-01")})

    def _boom(*a, **k):  # a download here would be the bug
        raise AssertionError("deep cache must not deep-fetch")

    monkeypatch.setattr(mod, "download_ohlcv", _boom)
    monkeypatch.setattr(mod, "build_universe", lambda _m: ["A"])
    rc = main(["--start", "2023-06-01", "--mode", "current", "--cache", "x.pkl"])
    assert rc == 0


def test_shallow_cache_triggers_a_deep_fetch(monkeypatch):
    """The positive: a uniformly shallow cache (every name from the same warmup start) deep-fetches."""
    import scripts.ensure_ohlcv_depth as mod

    monkeypatch.setattr(mod, "load_ohlcv_cache", lambda _c: {"A": _df("2025-01-27")})
    calls: list[tuple] = []

    def _dl(tickers, start, end):
        calls.append((tuple(tickers), start, end))
        return {"A": _df("2023-06-01", n=800)}

    monkeypatch.setattr(mod, "download_ohlcv", _dl)
    monkeypatch.setattr(mod, "merge_ohlcv", lambda a, b: b)
    monkeypatch.setattr(mod, "save_ohlcv_cache", lambda o, c: None)
    monkeypatch.setattr(mod, "build_universe", lambda _m: ["A"])
    rc = main(["--start", "2023-06-01", "--mode", "current", "--cache", "x.pkl", "--end", "2026-06-30"])
    assert rc == 0
    assert calls and calls[0][1] == "2023-06-01", "must deep-fetch from the requested start"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
