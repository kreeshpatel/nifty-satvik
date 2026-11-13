"""A split re-fetch REPLACES the cached series; it is never merged (2026-11-07 CONCORDBIO halt)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402


def _s(dates, close):
    return pd.DataFrame({"Close": close}, index=pd.DatetimeIndex(dates))


def test_old_bars_outside_the_refetch_window_do_not_survive():
    old = {"X": _s(["2024-01-01", "2025-06-01", "2026-11-03"], [200.0, 220.0, 240.0]), "Y": _s(["2026-11-03"], [5.0])}
    full = {"X": _s(["2025-06-01", "2026-11-03", "2026-11-06"], [110.0, 120.0, 121.0])}
    out = C._replace_readjusted(old, full)
    assert list(out["X"]["Close"]) == [110.0, 120.0, 121.0]      # the 2024 pre-split bar is gone
    assert out["Y"] is old["Y"]                                    # other names untouched


def test_an_empty_refetch_keeps_the_old_series():
    old = {"X": _s(["2026-11-03"], [240.0])}
    assert C._replace_readjusted(old, {"X": _s([], [])})["X"] is old["X"]
    assert C._replace_readjusted(old, {})["X"] is old["X"]
