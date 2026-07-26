"""Pre-reg 0104 - tighten the live ext_cap 0.20 -> 0.15 on the weekly-swing book.

Runs the LIVE book config (A-grade-only + max_risk 0.10 + max_notional 0.20 + config-P scaled exit)
twice, changing ONLY ext_cap, and scores 0.15 vs 0.20 against the pre-committed bar in
diagnostics/research/preregistry/0104-extcap-tighten-swing.md. Re-run (not ledger-filter) so freed cash
redeploys honestly.

    python scripts/run_0104_extcap_swing.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
import run_bhanushali_weekly_rank as R94  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import _row, _slices  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

# live config (mirrors run_bhanushali_cron LIVE_DISCIPLINE + LIVE_EXIT=config P)
SE = dict(tp1_r=2.0, tp1_frac=0.40, tp2_r=3.0, tp2_frac=0.0, pattern_frac=0.40, pattern_arm_r=2.5,
          runner_sma_buffer=0.0)
LIVE = dict(max_risk_pct=0.10, max_notional_pct=0.20, scaled_exit=SE)


def _calmar(m):
    return m["cagr"] / abs(m["dd"]) if m["dd"] else float("nan")


def _dci(a, b, block=DEFAULT_BLOCK, n=5000, seed=12345):
    idx = a.index.intersection(b.index); x = a.reindex(idx).to_numpy(float); y = b.reindex(idx).to_numpy(float)
    N = len(x); rng = np.random.default_rng(seed); nb = int(np.ceil(N / block)); dd = []
    for _ in range(n):
        s = rng.integers(0, N - block + 1, size=nb)
        sel = np.concatenate([np.arange(k, k + block) for k in s])[:N]
        dd.append(sharpe_fn(x[sel]) - sharpe_fn(y[sel]))
    return tuple(float(v) for v in np.percentile(dd, [2.5, 97.5]))


def main() -> int:
    print("=== pre-reg 0104: ext_cap 0.20 -> 0.15 on the live swing config ===")
    ohlcv = corrected_universe(); mem = load_membership()
    P = prep_weekly_rank(ohlcv)
    a_set = R94.grade_a_entries(P)
    print(f"corrected universe: {len(P)} names | A-grade set {len(a_set)} entries | live config (A-only + "
          f"max_risk 0.10 + max_notional 0.20 + config-P exit)\n")

    base = backtest(P, mem, a_grade=a_set, ext_cap=0.20, **LIVE)   # current live
    cand = backtest(P, mem, a_grade=a_set, ext_cap=0.15, **LIVE)   # tightened

    print(_row("baseline ext_cap 0.20", base))
    print(_row("candidate ext_cap 0.15", cand))
    ba, bb, bc = _slices(base); ca, cb, cc = _slices(cand)
    print(f"    slice Sharpe 0.20: 2017-18* {ba:+.2f} | 2019-21 {bb:+.2f} | 2022-26 {bc:+.2f}")
    print(f"    slice Sharpe 0.15: 2017-18* {ca:+.2f} | 2019-21 {cb:+.2f} | 2022-26 {cc:+.2f}")

    d_sh = cand["sharpe"] - base["sharpe"]; d_cagr = (cand["cagr"] - base["cagr"]) * 100
    d_dd = (cand["dd"] - base["dd"]) * 100; d_s22 = cc - bc
    print(f"\n  trades {base['trades']}->{cand['trades']} | expR {base['expR']:+.2f}->{cand['expR']:+.2f} | "
          f"win {base['wr']*100:.0f}%->{cand['wr']*100:.0f}%")
    print(f"  dSharpe {d_sh:+.3f} | dCAGR {d_cagr:+.2f}pp | dMaxDD {d_dd:+.2f}pp (positive=shallower) | "
          f"Calmar {_calmar(base):.2f}->{_calmar(cand):.2f} | d(2022-26) {d_s22:+.3f}")
    lo, hi = _dci(cand["ret"], base["ret"])
    n_tr = cumulative_n_trials()
    ci = block_bootstrap_metric(cand["ret"].to_numpy(float), sharpe_fn, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    print(f"  dSharpe 95% CI [{lo:+.3f}, {hi:+.3f}] | cand bootstrap CI [{ci.lower:+.3f},{ci.upper:+.3f}] | "
          f"n_indep~{len(cand['ret'])/63:.0f}")

    bar = {"dSharpe >= +0.05": d_sh >= 0.05, "dMaxDD >= 0pp": d_dd >= 0.0,
           "2022-26 not worse >0.05": d_s22 >= -0.05, "dCAGR >= -3.0pp": d_cagr >= -3.0}
    print("\n  pre-committed bar (0104):")
    for k, v in bar.items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    verdict = ("ADOPT-candidate -> forward-wall watch" if all(bar.values())
               else "KILL / UNDERPOWERED - keep live ext_cap 0.20")
    print(f"\n  n_trials (this run counted): {n_tr}\n  VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
