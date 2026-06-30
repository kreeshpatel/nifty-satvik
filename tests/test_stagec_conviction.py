"""Stage C — conviction score + rank-IC null (hermetic).

Pins the mechanism (the score is a per-date z-blend within the selectable pool; NaN factors don't
penalise; quintiles 1..5) and the significance tool (perfect rank → IC 1 & p≈0; random → IC≈0 &
high p). The canonical conviction IC verdict comes from the pinned cloud/dev run (run_conviction_c2)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from config import load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import compose_ranked_panel
from nq.research.conviction import CONVICTION_COL, QUINTILE_COL, add_conviction_score
from nq.validation.factor_ic import permutation_ic_pvalue, spearman_ic

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
             "CCC": _synth(600, 3, 0.0009), "DDD": _synth(600, 4, 0.0003),
             "EEE": _synth(600, 5, 0.0015), "FFF": _synth(600, 6, 0.0008)}
    feats = compute_all_features(ohlcv, holidays=set())
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [10.0 + i * 3]},
                            index=pd.to_datetime(["2014-06-01"])) for i, t in enumerate(ohlcv)}
    return compose_ranked_panel(feats, ohlcv, fund_store=fund, membership=None)


# ── IC + null tool ──────────────────────────────────────────────────────────

def test_spearman_perfect_and_monotone():
    x = np.arange(50, dtype=float)
    assert spearman_ic(x, 2 * x + 1) == pytest.approx(1.0)    # monotone increasing → +1
    assert spearman_ic(x, -x) == pytest.approx(-1.0)          # monotone decreasing → −1


def test_permutation_null_detects_signal_and_noise():
    rng = np.random.default_rng(0)
    x = rng.normal(size=400)
    strong = permutation_ic_pvalue(x, x + rng.normal(scale=0.1, size=400), n_perm=400)
    assert strong["ic"] > 0.8 and strong["p_value"] < 0.05
    noise = permutation_ic_pvalue(x, rng.normal(size=400), n_perm=400)
    assert noise["p_value"] > 0.05                   # random → indistinguishable from chance


def test_block_permutation_more_conservative_than_iid():
    # x and y share a slow common trend (autocorrelated/time-clustered) -> the IID shuffle breaks
    # that structure and gives a too-narrow null (spuriously small p). The block permutation
    # preserves it, so its p must be >= the IID p.
    rng = np.random.default_rng(3)
    common = np.cumsum(rng.normal(size=600))         # random walk = strong serial correlation
    x = common + rng.normal(size=600)
    y = common + rng.normal(size=600)
    iid = permutation_ic_pvalue(x, y, n_perm=400, block=None)
    blk = permutation_ic_pvalue(x, y, n_perm=400, block=40)
    assert blk["block"] == 40
    assert blk["p_value"] >= iid["p_value"]


def test_block_returns_psr_mintrl():
    # the per-window significance basis: ~n/63 non-overlapping windows, PSR/MinTRL sane
    from nq.runner.research import block_returns
    from nq.validation.dsr import min_track_record_length, probabilistic_sharpe_ratio
    rng = np.random.default_rng(1)
    daily = rng.normal(0.0006, 0.01, 2520)             # ~10y daily returns
    assert block_returns(daily, 63).size == 40         # 2520/63 = 40 independent windows
    assert 0.9 < probabilistic_sharpe_ratio(0.4, 40) <= 1.0     # strong per-window SR -> high PSR
    assert np.isfinite(min_track_record_length(0.4))            # certifiable
    assert min_track_record_length(0.0) == float("inf")        # SR <= 0 never certifiable


# ── conviction score ────────────────────────────────────────────────────────

def test_conviction_columns_and_pool_only():
    p = add_conviction_score(_panel(), gate_quantile=float(CFG["gate_quantile"]))
    assert CONVICTION_COL in p.columns and QUINTILE_COL in p.columns
    # only the selectable pool (rank >= 1 - q) gets a score; sub-gate rows are NaN
    gated_out = p[p["trend_rank"] < (1.0 - float(CFG["gate_quantile"]))]
    assert gated_out[CONVICTION_COL].isna().all()
    scored = p[p[CONVICTION_COL].notna()]
    assert len(scored) > 0


def test_conviction_zblend_centered_per_date():
    p = add_conviction_score(_panel(), gate_quantile=1.0)   # whole cross-section in the pool
    # an equal-weight mean of per-date z-scored factors is ~centered each date
    daily_mean = p.groupby("date")[CONVICTION_COL].mean().dropna()
    assert np.allclose(daily_mean.to_numpy(), 0.0, atol=1e-9)


def test_conviction_handles_missing_roe():
    # drop ROE entirely → score still computed from the remaining 3 factors (no all-NaN)
    pan = _panel().drop(columns=[c for c in ("roe",) if c in _panel().columns], errors="ignore")
    p = add_conviction_score(pan, gate_quantile=1.0)
    assert p[CONVICTION_COL].notna().any()
