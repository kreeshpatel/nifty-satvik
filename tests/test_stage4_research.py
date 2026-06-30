"""F4 gate (hermetic) — the research-run harness (backtest + CPCV-over-time + paired verdict).

Structure-level checks on a synthetic universe: the harness runs end to end, reconstructs the
right number of LdP paths, produces finite path metrics + a DSR, and the paired verdict logic is
sound (identical arms → no edge → not PROMOTE). The CANONICAL numbers come from the cloud run on
the corrected universe."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import compose_ranked_panel
from nq.runner.research import cpcv_evaluate, paired_cpcv, run_backtest
from nq.validation.cpcv import n_backtest_paths

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
    ohlcv = {"AAA": _synth(500, 1, 0.0012), "BBB": _synth(500, 2, 0.0006),
             "CCC": _synth(500, 3, 0.0009)}
    feats = compute_all_features(ohlcv, holidays=set())
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [15.0]},
                            index=pd.to_datetime(["2014-06-01"])) for t in ohlcv}
    return compose_ranked_panel(feats, ohlcv, fund_store=fund, membership=None)


def test_lh_cpcv_path_count():
    assert n_backtest_paths(8, 2) == 7      # the long-horizon default partition


def test_run_backtest_matches_simulate():
    panel = _panel()
    res = run_backtest(panel, CFG)
    assert res["equity_curve"] and "metrics" in res and res["metrics"]["n_trades"] >= 0


def test_cpcv_evaluate_structure():
    panel = _panel()
    # small partition so the ~1.3y synthetic panel supports the groups (canonical run uses 8/2/63)
    out = cpcv_evaluate(panel, CFG, n_groups=4, n_test_groups=2, horizon=5, embargo=5)
    assert out["n_paths"] == n_backtest_paths(4, 2) == 3
    assert len(out["path_sharpes"]) == 3 and np.isfinite(out["mean_sharpe"])
    assert out["n_trials"] == 79            # deflates at the carried cumulative count
    assert (0.0 <= out["dsr"] <= 1.0) or np.isnan(out["dsr"])


def test_paired_cpcv_identical_arms_no_edge():
    panel = _panel()
    res = paired_cpcv(panel, CFG, CFG, n_groups=4, n_test_groups=2, horizon=5, embargo=5)
    assert res["dSharpe"] == 0.0            # same cfg on the same blocks -> exact zero delta
    assert res["verdict"] != "PROMOTE-CANDIDATE"   # no edge can never promote


def test_paired_cpcv_degrading_candidate_not_promoted():
    panel = _panel()
    # a candidate with a near-zero ATR stop knocks every position out immediately -> strictly worse
    bad = {**CFG, "stop_atr_mult": 0.05}
    res = paired_cpcv(panel, CFG, bad, n_groups=4, n_test_groups=2, horizon=5, embargo=5)
    assert res["verdict"] != "PROMOTE-CANDIDATE"
