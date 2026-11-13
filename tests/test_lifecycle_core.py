"""Strategy-lifecycle core (ADR-0020): bands are write-once and monotone, status edges are exact, records append only."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipelines" / "lifecycle"))
import core as C  # noqa: E402


def _band():
    rng = np.random.default_rng(7)
    bt = rng.normal(0.004, 0.03, 300)
    paths = [rng.normal(0.004, 0.03, 300) for _ in range(4)]
    return C.build_band("demo", bt, paths, worst_backtest_dd_pct=-40.0, built="2026-01-01")


# ------------------------------------------------------------------ bands
def test_percentiles_are_monotone_in_every_table():
    band = _band()
    C.check_monotone(band)                                   # raises on a violation
    for h in C.HORIZONS:
        t = band["horizons"][str(h)]["cum_return_pct"]["band"]
        assert t["p5"] <= t["p25"] <= t["p50"] <= t["p75"] <= t["p95"]


def test_the_band_is_never_narrower_than_either_source():
    blk = _band()["horizons"]["26"]["cum_return_pct"]
    for src in ("ensemble", "bootstrap"):
        assert blk["band"]["p5"] <= blk[src]["p5"] and blk["band"]["p95"] >= blk[src]["p95"]
    dd = _band()["horizons"]["26"]["drawdown_depth_pct"]
    for src in ("ensemble", "bootstrap"):
        assert dd["band"]["p95"] >= dd[src]["p95"]


def test_check_monotone_rejects_a_broken_table():
    band = _band()
    band["horizons"]["13"]["cum_return_pct"]["band"]["p25"] = 999.0
    with pytest.raises(ValueError):
        C.check_monotone(band)


def test_a_band_file_is_write_once(tmp_path):
    f = tmp_path / "demo_bands_2026-01-01.json"
    C.write_once(f, {"a": 1})
    before = f.read_bytes()
    with pytest.raises(FileExistsError):
        C.write_once(f, {"a": 2})
    assert f.read_bytes() == before


def test_bootstrap_is_deterministic():
    r = np.random.default_rng(1).normal(0, 0.02, 120)
    a, b = C.stationary_bootstrap(r, 13, n=50), C.stationary_bootstrap(r, 13, n=50)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


# ------------------------------------------------------------------ status
H = {"cum_return_pct": {"band": {"p5": -10.0, "p25": 0.0, "p50": 8.0, "p75": 15.0, "p95": 30.0}},
     "drawdown_depth_pct": {"band": {"p5": 2.0, "p25": 5.0, "p50": 9.0, "p75": 14.0, "p95": 20.0}}}


@pytest.mark.parametrize("ret, dd, want", [
    (0.0, 5.0, "GREEN"),          # exactly on the 25th percentile
    (-0.01, 5.0, "AMBER"),        # just under it
    (-10.0, 5.0, "AMBER"),        # exactly on the 5th percentile
    (-10.01, 5.0, "RED"),         # just under it
    (12.0, 20.0, "GREEN"),        # drawdown exactly on the band's 95th percentile
    (12.0, 20.01, "AMBER"),       # good return, drawdown past the band
    (12.0, 50.0, "AMBER"),        # exactly on the breaker (1.25 x 40) is not a breach
    (12.0, 50.01, "RED"),         # past the breaker, whatever the return
])
def test_status_edges(ret, dd, want):
    assert C.classify(ret, dd, H, worst_backtest_dd_pct=-40.0)["status"] == want


def test_the_breaker_is_flagged_separately():
    out = C.classify(12.0, 55.0, H, worst_backtest_dd_pct=-40.0)
    assert out["status"] == "RED" and out["drawdown_breaker"] is True
    assert C.classify(-20.0, 5.0, H, worst_backtest_dd_pct=-40.0)["drawdown_breaker"] is False


def test_nearest_horizon_and_percentile_bracket():
    assert [C.nearest_horizon(w) for w in (1, 13, 19, 20, 39, 40, 78, 200)] == [13, 13, 13, 26, 26, 52, 52, 104]
    assert C.return_percentile(-11, H) == "below 5th" and C.return_percentile(-10, H) == "5th-25th"
    assert C.return_percentile(8, H) == "50th-75th" and C.return_percentile(31, H) == "above 95th"


# ------------------------------------------------------------------ records
def test_records_are_append_only(tmp_path):
    f = tmp_path / "demo.csv"
    assert C.append_row(f, {"date": "2026-11-14", "nav": 1000000.0, "weekly_return": 0.0}) is True
    assert C.append_row(f, {"date": "2026-11-21", "nav": 1010000.0, "weekly_return": 0.01, "holdings": 30}) is True
    first_two = f.read_text(encoding="utf-8")
    assert C.append_row(f, {"date": "2026-11-21", "nav": 5.0, "weekly_return": -0.99}) is False     # same week: no rewrite
    assert f.read_text(encoding="utf-8") == first_two
    with pytest.raises(ValueError):
        C.append_row(f, {"date": "2026-11-07", "nav": 1.0, "weekly_return": 0.0})                    # the past is closed
    assert f.read_text(encoding="utf-8") == first_two
    C.append_row(f, {"date": "2026-11-28", "nav": 1020000.0, "weekly_return": 0.0099})
    assert f.read_text(encoding="utf-8").startswith(first_two)
    assert list(C.read_record(f).columns) == list(C.RECORD_COLUMNS) and len(C.read_record(f)) == 3


def test_vol_target_caps_exposure_at_one_and_uses_only_the_past():
    import pandas as pd
    idx = pd.bdate_range("2026-01-01", periods=80)
    rng = np.random.default_rng(3)
    a, b = pd.Series(rng.normal(0, 0.03, 80), index=idx), pd.Series(rng.normal(0, 0.03, 80), index=idx)
    r, expo = C.vol_target_blend(a, b)
    assert expo.max() <= 1.0 and (expo.iloc[:20] == 1.0).all()
    a2 = a.copy(); a2.iloc[-1] = 0.5                                   # changing today's return cannot change today's exposure
    assert C.vol_target_blend(a2, b)[1].iloc[-1] == expo.iloc[-1]


# ------------------------------------------------------------------ execution tracking error
def test_tracking_error_signs_and_units():
    model = {"A__2026-11-02": {"entry": 100.0, "stop": 90.0, "exit": 120.0}}
    fills = [{"signal_id": "A__2026-11-02", "side": "BUY", "qty": 10, "price": 101.0},     # paid 1% more: +100 bps, +0.1R
             {"signal_id": "A__2026-11-02", "side": "SELL", "qty": 10, "price": 118.8},    # sold 1% lower: +100 bps, +0.12R
             {"signal_id": "UNKNOWN__x", "side": "BUY", "qty": 1, "price": 5.0}]           # no model trade: ignored
    out = C.tracking_error(fills, model)
    assert out["n_fills_matched"] == 2
    assert out["buy_mean_bps"] == 100.0 and out["sell_mean_bps"] == 100.0
    assert abs(out["mean_slippage_R"] - 0.11) < 1e-9


def test_tracking_error_with_no_fills_says_so():
    assert C.tracking_error([], {})["n_fills_matched"] == 0
