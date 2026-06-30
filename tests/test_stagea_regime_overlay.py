"""Stage A — A5 harness-trust gate: the regime-to-cash overlay.

Two things are pinned here, hermetically:
  1. The overlay MECHANISM — the cfg-gated engine branch is inert by default (golden-safe), reads a
     per-date risk-off column, and genuinely suppresses NEW entries when risk-off.
  2. The HARNESS does not false-promote it — ``evaluate_overlay`` returns a non-promotion verdict on
     a no-edge regime candidate. (The canonical KILL verdict comes from the cloud run on the pinned
     corrected universe; here we prove the wiring + the no-false-promote property on a synthetic.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import compose_ranked_panel
from nq.engine.portfolio import simulate
from nq.research.overlays import REGIME_COL, REGIME_SMA_WINDOW, add_regime_gate_column
from nq.runner.research import evaluate_overlay

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
    ohlcv = {"AAA": _synth(600, 1, 0.0012), "BBB": _synth(600, 2, 0.0006),
             "CCC": _synth(600, 3, 0.0009)}
    feats = compute_all_features(ohlcv, holidays=set())
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [15.0]},
                            index=pd.to_datetime(["2014-06-01"])) for t in ohlcv}
    return compose_ranked_panel(feats, ohlcv, fund_store=fund, membership=None)


def test_regime_column_trailing_warmup_and_per_date_consistent():
    p = add_regime_gate_column(_panel())
    assert REGIME_COL in p.columns
    # all rows sharing a date carry the same regime value (the engine reads it off any row)
    per_date_nunique = p.groupby("date")[REGIME_COL].nunique()
    assert (per_date_nunique == 1).all()
    # no-lookahead warmup: before the SMA has REGIME_SMA_WINDOW obs, the date is risk-ON (False)
    first_dates = sorted(p["date"].unique())[:REGIME_SMA_WINDOW]
    warm = p[p["date"].isin(first_dates)]
    assert not warm[REGIME_COL].any()


def test_gate_is_no_op_without_flag_or_column():
    p = add_regime_gate_column(_panel())
    base = simulate(p, CFG)                                   # flag off -> column ignored
    # same panel, flag off => identical to a panel without the column at all
    p_nocol = p.drop(columns=[REGIME_COL])
    assert base["metrics"]["n_trades"] == simulate(p_nocol, CFG)["metrics"]["n_trades"]


def test_gate_suppresses_all_entries_when_fully_risk_off():
    p = _panel().copy()
    p[REGIME_COL] = True                                      # force every date risk-off
    base = simulate(p, CFG)                                   # no flag -> trades normally
    gated = simulate(p, {**CFG, "regime_gate": True})         # flag on -> no new entries ever
    assert base["metrics"]["n_trades"] > 0                    # the synthetic panel IS tradeable
    assert gated["metrics"]["n_trades"] == 0                  # regime-to-cash => zero entries


def test_harness_does_not_false_promote_regime_overlay():
    p = add_regime_gate_column(_panel())
    res = evaluate_overlay(p, CFG, {**CFG, "regime_gate": True}, n_samples=500)
    assert res["verdict"] != "PROMOTE-CANDIDATE"             # a no-edge overlay must not promote
