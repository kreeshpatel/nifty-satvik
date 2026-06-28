"""Stage-2 — panel builder coherence (hermetic, synthetic).

The byte-for-byte equivalence proof is the golden gate (test_stage2_golden). This pins that
build_ohlc_panel + compose_ranked_panel wire the Stage-1 predicates together correctly: the OHLC
join aligns, solvency drops a high-D/E name, the rank is a per-date percentile in (0, 1], and the
composed panel runs through simulate end-to-end.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import build_ohlc_panel, compose_ranked_panel
from nq.engine.portfolio import simulate


def _synth(n: int, seed: int, drift: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(drift, 0.012, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    vol = rng.integers(3_000_000, 5_000_000, n).astype(float)   # adv ~ 3-5e8 >> 5cr -> large+mid
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
                        index=pd.bdate_range("2015-01-01", periods=n))


def _fund(de: float) -> pd.DataFrame:
    return pd.DataFrame({"debt_equity": [de], "roe": [15.0]},
                        index=pd.to_datetime(["2014-06-01"]))


def test_build_ohlc_panel_joins_features_and_prices():
    ohlcv = {"A": _synth(400, 1, 0.0010), "B": _synth(400, 2, 0.0002)}
    feats = compute_all_features(ohlcv, holidays=set())
    panel = build_ohlc_panel(feats, ohlcv)
    assert set(panel["ticker"].unique()) == {"A", "B"}
    for col in ("date", "ticker", "open", "high", "low", "close", "volume",
                "sma200_slope_63", "atr_pct_63", "adv_rupees_20d", "sector"):
        assert col in panel.columns
    # the join is inner on shared dates → no all-NaN OHLC rows
    assert panel[["open", "high", "low", "close"]].notna().all().all()


def test_compose_ranked_panel_eligibility_and_rank():
    ohlcv = {"A": _synth(400, 1, 0.0012), "B": _synth(400, 2, 0.0004), "C": _synth(400, 3, -0.0008)}
    feats = compute_all_features(ohlcv, holidays=set())
    fund = {"A": _fund(0.3), "B": _fund(0.5), "C": _fund(2.0)}   # C is over-levered → dropped
    panel = compose_ranked_panel(feats, ohlcv, fund_store=fund, membership=None)

    assert "C" not in set(panel["ticker"].unique()), "over-levered name must be dropped by solvency"
    assert {"A", "B"}.issubset(set(panel["ticker"].unique()))
    # trend_rank is a per-date percentile in (0, 1]
    r = panel["trend_rank"].dropna()
    assert (r > 0).all() and (r <= 1.0).all()
    # within a date with both names, the larger sma200_slope_63 gets the larger rank
    for _d, g in panel.dropna(subset=["trend_rank", "sma200_slope_63"]).groupby("date"):
        if len(g) == 2:
            g = g.sort_values("sma200_slope_63")
            assert g["trend_rank"].is_monotonic_increasing
            break


def test_composed_panel_runs_through_simulate():
    ohlcv = {"A": _synth(400, 1, 0.0012), "B": _synth(400, 2, 0.0004)}
    feats = compute_all_features(ohlcv, holidays=set())
    fund = {"A": _fund(0.3), "B": _fund(0.5)}
    panel = compose_ranked_panel(feats, ohlcv, fund_store=fund, membership=None)
    res = simulate(panel, load_frozen_cfg(), initial_capital=1_000_000.0)
    assert res["equity_curve"], "simulate must produce an equity curve on the composed panel"
    assert "n_trades" in res["metrics"] and res["metrics"]["n_trades"] >= 0
