"""MEASUREMENT (0 trials): PBO via CSCV (Bailey-Lopez de Prado) over the swing cfg-lever search family.

DSR corrects the Sharpe THRESHOLD; it never measured whether the SEARCH PROCEDURE is overfit. PBO answers:
P(the in-sample-best config underperforms the median config out-of-sample). Method: re-run the 17 cfg-gated
swing configurations actually searched (stops/floors/ext-caps/exits/vol-target), build the M x T monthly-
return matrix, split T into S=12 contiguous blocks, and over all C(12,6)=924 IS/OOS combinations record the
OOS rank of each combination's IS-best config. PBO = fraction of combos where the IS-best lands below the
OOS median. Also reports IS->OOS Sharpe degradation. Scope: the cfg-lever family on the frozen 0094 engine
(the cross-SCRIPT family 0084-0099 is not re-runnable here; stated limitation).

    python scripts/diag_pbo_cscv.py     (~12 min; writes research/exports/pbo_cscv_results.json + matrix)
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

MATRIX = ROOT / "research" / "exports" / "pbo_monthly_matrix.csv"
OUT = ROOT / "research" / "exports" / "pbo_cscv_results.json"

CONFIGS = {
    "base": {},
    "hard_stop": {"hard_stop": True},
    "widen10": {"stop_widen_pct": 0.10},
    "widen20": {"stop_widen_pct": 0.20},
    "disaster05": {"disaster_floor_pct": 0.05},
    "disaster10": {"disaster_floor_pct": 0.10},
    "disaster15": {"disaster_floor_pct": 0.15},
    "extcap10": {"ext_cap": 0.10},
    "extcap15": {"ext_cap": 0.15},
    "extcap20": {"ext_cap": 0.20},
    "voltarget": {"vol_target": (0.15, 42, 0.40)},
    "p2exit": {"no_time_cap": True, "wk20_trail_pct": 0.04, "blowoff_arm_r": 2.5},
    "scaledP": {"scaled_exit": {"tp1_r": 2.0, "tp1_frac": 0.40, "tp2_r": 3.0, "tp2_frac": 0.0,
                                "pattern_frac": 0.40, "pattern_arm_r": 2.5, "runner_sma_buffer": 0.0}},
    "tp_on_high": {"tp_on_high": True},
    "earlycut": {"early_cut_pct": 8.0, "early_cut_weeks": 2},
    "maxrisk10": {"max_risk_pct": 0.10},
    "notional20": {"max_notional_pct": 0.20},
}


def sharpe(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    return float(x.mean() / x.std() * np.sqrt(12)) if len(x) > 5 and x.std() else np.nan


def main() -> int:
    if MATRIX.exists():
        mat = pd.read_csv(MATRIX, index_col=0, parse_dates=True)
        print(f"[cache] matrix {mat.shape}")
    else:
        oh = corrected_universe(); mem = load_membership(); P = prep_weekly_rank(oh)
        cols = {}
        for i, (nm, kw) in enumerate(CONFIGS.items()):
            t0 = time.time()
            m = backtest(P, mem, **kw)
            r = m["ret"].dropna()
            cols[nm] = (1 + r).resample("ME").prod() - 1
            print(f"  [{i+1}/{len(CONFIGS)}] {nm:<12} Sharpe {m['sharpe']:+.3f}  ({time.time()-t0:.0f}s)", flush=True)
        mat = pd.DataFrame(cols).dropna(how="all")
        mat.to_csv(MATRIX)
        print(f"matrix {mat.shape} -> {MATRIX}")

    M = mat.shape[1]
    # S=12 contiguous month-blocks -> C(12,6)=924 IS/OOS splits
    blocks = np.array_split(np.arange(len(mat)), 12)
    combos = list(itertools.combinations(range(12), 6))
    ranks, is_best_names, degr = [], [], []
    for c in combos:
        is_idx = np.concatenate([blocks[i] for i in c])
        oos_idx = np.concatenate([blocks[i] for i in range(12) if i not in c])
        is_sh = mat.iloc[is_idx].apply(lambda col: sharpe(col.to_numpy()))
        oos_sh = mat.iloc[oos_idx].apply(lambda col: sharpe(col.to_numpy()))
        best = is_sh.idxmax()
        is_best_names.append(best)
        # OOS relative rank of the IS-best (1 = best OOS, M = worst)
        rank = int((oos_sh > oos_sh[best]).sum()) + 1
        ranks.append(rank)
        degr.append((float(is_sh[best]), float(oos_sh[best]), float(oos_sh.median())))
    ranks = np.array(ranks)
    pbo = float((ranks > M / 2).mean())
    w = ranks / (M + 1.0)
    logits = np.log((1 - w) / w)
    d = pd.DataFrame(degr, columns=["is_best_sh", "oos_best_sh", "oos_median_sh"])
    from collections import Counter
    freq = Counter(is_best_names)
    res = {
        "n_configs": M, "n_months": int(len(mat)), "n_combos": len(combos),
        "PBO": round(pbo, 3),
        "mean_oos_rank_of_is_best": round(float(ranks.mean()), 2),
        "mean_logit": round(float(logits.mean()), 3),
        "is_best_sharpe_mean": round(float(d["is_best_sh"].mean()), 3),
        "oos_sharpe_of_is_best_mean": round(float(d["oos_best_sh"].mean()), 3),
        "oos_median_sharpe_mean": round(float(d["oos_median_sh"].mean()), 3),
        "is_best_frequency": dict(freq.most_common()),
    }
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(f"\nPBO = {pbo:.1%}  (P that the IS-best config underperforms the OOS median; <=20% healthy, "
          f">=50% = the search is overfit)")
    print(f"IS->OOS degradation of the IS-best: {res['is_best_sharpe_mean']} -> {res['oos_sharpe_of_is_best_mean']} "
          f"(OOS median {res['oos_median_sharpe_mean']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
