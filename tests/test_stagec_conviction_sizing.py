"""Stage C / C3 — conviction-weighted sizing engine overlay (hermetic).

Pins the three properties the C3 trial relies on: (1) inert when the flag is off (golden-safe);
(2) the tilt actually engages (some per-trade qty changes); (3) it is MEAN-PRESERVED — selection is
unchanged (same trade set) and aggregate deployed capital is ~unchanged (a redistribution, not a
size-up). The canonical ΔSharpe/DSR verdict comes from the pinned cloud run (run_conviction_c3)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import compose_ranked_panel
from nq.engine.portfolio import DEFAULT_CONVICTION_MULT, simulate
from nq.research.conviction import CONVICTION_COL, QUINTILE_COL, add_conviction_score

CFG = load_frozen_cfg()


def _synth(n, seed, drift):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(drift, 0.012, n)))
    high, low = close * 1.004, close * 0.996
    open_ = close * (1 + rng.normal(0, 0.003, n))
    vol = rng.integers(3_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
                        index=pd.bdate_range("2015-01-01", periods=n))


def _panel():
    # enough names that the rank-gated pool (top ~50%) has >= 5 distinct convictions -> real quintiles
    rng = np.random.default_rng(7)
    ohlcv = {f"N{i:02d}": _synth(600, i + 1, float(d))
             for i, d in enumerate(rng.uniform(0.0002, 0.0015, 16))}
    feats = compute_all_features(ohlcv, holidays=set())
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [6.0 + i * 1.5]},
                            index=pd.to_datetime(["2014-06-01"])) for i, t in enumerate(ohlcv)}
    return add_conviction_score(
        compose_ranked_panel(feats, ohlcv, fund_store=fund, membership=None),
        gate_quantile=float(CFG["gate_quantile"]))


def _trade_key(tr):
    return {(t["entry_date"], t["ticker"]) for t in tr}


def _notional(tr):
    return float(sum(t["qty"] * t["entry"] for t in tr))


def test_default_mult_is_mean_one_and_monotone():
    vals = [DEFAULT_CONVICTION_MULT[q] for q in (1, 2, 3, 4, 5)]
    assert vals == sorted(vals)                       # higher quintile -> larger multiplier
    assert abs(sum(vals) / len(vals) - 1.0) < 1e-9    # symmetric around 1.0 across quintiles


def test_conviction_sizing_off_is_noop():
    p = _panel()
    base = simulate(p, CFG)
    # flag off: presence of the conviction columns must not change anything
    p_nocol = p.drop(columns=[CONVICTION_COL, QUINTILE_COL])
    assert base["metrics"]["n_trades"] == simulate(p_nocol, CFG)["metrics"]["n_trades"]
    assert _notional(base["trades"]) == _notional(simulate(p_nocol, CFG)["trades"])


# Isolate the MECHANISM: small risk_per_trade + loose cap so the risk-budget term binds (not the 15%
# cap), making the multiplier's effect on size observable. Under the real frozen cfg the 15% cap
# largely CLIPS the tilt (the Kelly-predicted muting) — measured empirically by the C3 cloud run.
_CFG_MECH = None


def _cfg_mech():
    global _CFG_MECH
    if _CFG_MECH is None:
        _CFG_MECH = {**CFG, "risk_per_trade_pct": 0.2, "max_position_pct": 100.0}
    return _CFG_MECH


def test_conviction_sizing_engages():
    p = _panel()
    cfg = _cfg_mech()
    base = simulate(p, cfg)
    cand = simulate(p, {**cfg, "conviction_size": True})
    bq = {(t["entry_date"], t["ticker"]): t["qty"] for t in base["trades"]}
    cq = {(t["entry_date"], t["ticker"]): t["qty"] for t in cand["trades"]}
    shared = set(bq) & set(cq)
    assert any(bq[k] != cq[k] for k in shared)        # the tilt changed at least one position size


def test_conviction_sizing_preserves_selection_and_capital():
    p = _panel()
    cfg = _cfg_mech()
    base, cand = simulate(p, cfg), simulate(p, {**cfg, "conviction_size": True})
    bk, ck = _trade_key(base["trades"]), _trade_key(cand["trades"])
    assert len(bk & ck) / max(len(bk | ck), 1) > 0.9   # same names/dates -> selection unchanged
    ratio = _notional(cand["trades"]) / _notional(base["trades"])
    assert 0.8 < ratio < 1.2                            # aggregate capital ~unchanged (mean-preserved)
