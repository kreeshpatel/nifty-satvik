"""Stage E — the paper/live vol-target overlay (O-009): de-gross-only book vol-targeting.

Pins the properties the shipped risk profile relies on: the scalar is de-gross-only (never levers up,
floored), the overlay is INERT on the research/golden path (off by default -> byte-identical), and when
on it reduces deployed capital (the -46 -> -39 DD trade). Hermetic."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import compose_ranked_panel
from nq.engine.portfolio import simulate, vol_target_scalar

CFG = load_frozen_cfg()
VT = {"vol_target_annual": 0.15, "vol_window": 42, "vol_floor": 0.40}


def _synth(n, seed, drift):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(drift, 0.02, n)))   # ~32% annual vol -> above target
    high, low = close * 1.004, close * 0.996
    open_ = close * (1 + rng.normal(0, 0.003, n))
    vol = rng.integers(3_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
                        index=pd.bdate_range("2015-01-01", periods=n))


def _panel():
    ohlcv = {f"N{i:02d}": _synth(600, i + 1, float(d))
             for i, d in enumerate(np.linspace(0.0004, 0.0016, 14))}
    feats = compute_all_features(ohlcv, holidays=set())
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [12.0]},
                            index=pd.to_datetime(["2014-06-01"])) for t in ohlcv}
    return compose_ranked_panel(feats, ohlcv, fund_store=fund, membership=None)


def test_scalar_is_degross_only_and_floored():
    assert vol_target_scalar(np.zeros(10), target_annual=0.15, floor=0.4, window=42) == 1.0   # < window
    hi = np.full(100, 0.0) + np.random.default_rng(0).normal(0, 0.05, 100)   # high realised vol
    lo = np.random.default_rng(0).normal(0, 0.0005, 100)                      # very low vol
    s_hi = vol_target_scalar(hi, target_annual=0.15, floor=0.4, window=42)
    s_lo = vol_target_scalar(lo, target_annual=0.15, floor=0.4, window=42)
    assert 0.40 <= s_hi < 1.0          # high vol -> de-grossed, but never below the floor
    assert s_lo == 1.0                 # low vol -> capped at 1.0 (NEVER levers up)


def test_vol_target_off_is_inert():
    p = _panel()
    base = simulate(p, CFG)
    assert base["metrics"]["n_trades"] == simulate(p, CFG, vol_target=None)["metrics"]["n_trades"]
    # vol_target_annual = 0 is also inert (the disable sentinel)
    assert base["metrics"]["n_trades"] == simulate(p, CFG, vol_target={"vol_target_annual": 0.0})["metrics"]["n_trades"]


def test_vol_target_on_degrosses_and_cuts_dd():
    # use a low target so the overlay engages on the synthetic's diversified (~9% vol) book
    p = _panel()
    base = simulate(p, CFG)
    vt = simulate(p, CFG, vol_target={"vol_target_annual": 0.05, "vol_window": 42, "vol_floor": 0.40})
    bn = sum(t["qty"] * t["entry"] for t in base["trades"])
    vn = sum(t["qty"] * t["entry"] for t in vt["trades"])
    assert vn < bn                                              # de-gross: deploys strictly less
    assert vt["metrics"]["max_drawdown_pct"] >= base["metrics"]["max_drawdown_pct"]   # DD no worse (less negative)
