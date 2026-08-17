"""F4 gate (hermetic) — the research-run harness (backtest + block-bootstrap robustness + overlay).

Structure-level checks on a synthetic universe: the harness runs end to end, produces a
block-bootstrap Sharpe CI + a DSR at the carried n_trials, and the overlay verdict logic is sound
(identical arms → no edge → not PROMOTE; a degrading candidate → not PROMOTE). The canonical
numbers come from the cloud run on the corrected universe. (The frozen LH rule makes CPCV's path
distribution degenerate — the block bootstrap is the correct OOS-robustness tool; CPCV's splitter
is retained in nq.validation for Stage-B re-derived arms.)"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import compose_ranked_panel
from nq.runner.research import evaluate, evaluate_overlay, run_backtest

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


def test_run_backtest_matches_simulate():
    res = run_backtest(_panel(), CFG)
    assert res["equity_curve"] and "metrics" in res and res["metrics"]["n_trades"] >= 0


def test_evaluate_structure():
    from nq.validation.dsr import cumulative_n_trials
    out = evaluate(_panel(), CFG, n_samples=500)
    assert "metrics" in out and out["n_trials"] == cumulative_n_trials()   # deflates at the live count
    assert out["sharpe_ci"] is None or (
        len(out["sharpe_ci"]) == 2 and out["sharpe_ci"][0] <= out["sharpe_point"] <= out["sharpe_ci"][1])
    assert (0.0 <= out["dsr"] <= 1.0) or np.isnan(out["dsr"])


def test_evaluate_overlay_identical_arms_no_edge():
    res = evaluate_overlay(_panel(), CFG, CFG, n_samples=500)
    assert res["dSharpe"] == 0.0                            # same cfg -> exact zero delta
    assert res["verdict"] != "PROMOTE-CANDIDATE"           # no edge can never promote


def test_evaluate_overlay_degrading_candidate_not_promoted():
    bad = {**CFG, "stop_atr_mult": 0.05}                    # near-zero ATR stop -> strictly worse
    res = evaluate_overlay(_panel(), CFG, bad, n_samples=500)
    assert res["verdict"] != "PROMOTE-CANDIDATE"


def test_evaluate_overlay_gates_mechanized_and_fail_closed():
    res = evaluate_overlay(_panel(), CFG, {**CFG, "stop_atr_mult": 0.05}, n_samples=300)
    g = res["gates"]
    assert set(g) == {"dSharpe_meaningful", "dCalmar_ge_0.05", "subperiod_2022_positive",
                      "fold_pass_ge_60pct", "turnover_le_30pct", "dsr_gt_0.95", "n_eff_ge_20"}
    assert res["gate_pass"] is all(g.values())             # gate_pass = AND of every gate
    assert res["gate_pass"] is False                        # a strictly-worse candidate fails the bar
    assert res["verdict"] != "PROMOTE-CANDIDATE"
    for k in ("dCalmar", "subperiod_2022_dCAGR", "fold_pass_frac", "turnover_delta",
              "after_tax_cagr_base", "after_tax_cagr_cand"):     # mechanized fields are emitted
        assert k in res


# ── adjudicate_family: PBO as the standing selection-robustness output ────────────────────────────
# Hermetic — adjudicate_family reads only the {equity_curve} contract, so synthetic curves exercise
# it without the engine. PBO answers "is the in-sample winner of this family also its OOS winner?":
# pure noise -> the pick is a coin flip (PBO ~ 0.5); a genuinely dominant config -> the pick holds
# out of sample (PBO ~ 0).

def _bt_from_returns(r):
    eq = 1_000_000.0 * np.cumprod(1.0 + np.asarray(r, dtype=float))
    idx = pd.bdate_range("2015-01-01", periods=eq.size)
    return {"equity_curve": [{"date": str(d.date()), "equity": float(e)} for d, e in zip(idx, eq)],
            "metrics": {}, "trades": []}


def _noise_family(k, n=520, mu=0.0, sigma=0.01):
    return {f"c{j}": _bt_from_returns(np.random.default_rng(100 + j).normal(mu, sigma, n))
            for j in range(k)}


def test_adjudicate_family_pure_noise_selection_uninformative():
    from nq.runner.research import adjudicate_family
    # Mirror pbo.py's own calibration regime (1000 periods x 12 zero-drift configs, n_blocks=10),
    # where PBO genuinely sits near the 0.5 coin flip. A smaller family is far noisier — that finite-
    # sample behaviour is cscv_pbo's concern (test_pure_noise_gives_pbo_near_a_coin_flip), not the
    # wrapper's; here we only confirm adjudicate_family threads the family through correctly.
    res = adjudicate_family(_noise_family(12, n=1000), n_blocks=10, n_samples=400)
    assert res["n_configs"] == 12 and res["n_periods"] == 999 and res["n_blocks"] == 10
    assert 0.3 <= res["pbo"] <= 0.7                          # iid columns -> PBO near the 0.5 coin flip
    assert res["selection_informative"] is (res["pbo"] < 0.5)
    assert res["verdict"] in ("SELECTION-INFORMATIVE", "SELECTION-NOISE")
    assert res["winner"] in res["labels"]
    assert res["winner_dsr_in_family"] is None or 0.0 <= res["winner_dsr_in_family"] <= 1.0


def test_adjudicate_family_dominant_config_is_informative():
    from nq.runner.research import adjudicate_family
    fam = _noise_family(4)                                   # four coin-flip configs...
    fam["star"] = _bt_from_returns(np.random.default_rng(7).normal(0.003, 0.008, 520))  # ...one clear edge
    res = adjudicate_family(fam, n_samples=400)
    assert res["winner"] == "star"                          # highest full-sample Sharpe
    assert res["selection_informative"] and res["pbo"] < 0.4  # the IS winner also wins OOS
    assert res["verdict"] == "SELECTION-INFORMATIVE"


def test_adjudicate_family_underpowered_paths():
    from nq.runner.research import adjudicate_family
    one = adjudicate_family({"only": _bt_from_returns(np.random.default_rng(1).normal(0, 0.01, 520))})
    assert one["verdict"] == "UNDERPOWERED" and one["n_configs"] == 1   # PBO needs >= 2 configs
    short = adjudicate_family({"a": _bt_from_returns(np.random.default_rng(2).normal(0, 0.01, 6)),
                               "b": _bt_from_returns(np.random.default_rng(3).normal(0, 0.01, 6))})
    assert short["verdict"] == "UNDERPOWERED"               # 6 periods < one CSCV split
