"""Pre-reg 0105 - intraday hard stop vs the close-only weekly stop on the frozen 0094 swing book.

baseline = backtest(hard_stop=False) [byte-identical 0094 record]; candidate = backtest(hard_stop=True).
Scored against the exit-improvement bar in diagnostics/research/preregistry/0105-hardstop-swing.md.

    python scripts/run_0105_hardstop_swing.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import _row, _slices  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

REC_SHARPE, REC_DD = 1.132, -0.424


def _calmar(m):
    return m["cagr"] / abs(m["dd"]) if m["dd"] else float("nan")


def _dsh_ci(br, cr, block=DEFAULT_BLOCK, n=5000, seed=12345):
    idx = br.index.intersection(cr.index)
    b = br.reindex(idx).to_numpy(float); c = cr.reindex(idx).to_numpy(float)
    N = len(b); rng = np.random.default_rng(seed); nb = int(np.ceil(N / block)); diffs = []
    for _ in range(n):
        st = rng.integers(0, N - block + 1, size=nb)
        sel = np.concatenate([np.arange(s, s + block) for s in st])[:N]
        diffs.append(sharpe_fn(c[sel]) - sharpe_fn(b[sel]))
    return tuple(float(x) for x in np.percentile(diffs, [2.5, 97.5]))


def main() -> int:
    print("=== pre-reg 0105: intraday hard stop on the frozen 0094 swing book ===")
    ohlcv = corrected_universe(); mem = load_membership(); P = prep_weekly_rank(ohlcv)
    base = backtest(P, mem)
    cand = backtest(P, mem, hard_stop=True)
    ok = abs(base["sharpe"] - REC_SHARPE) < 0.02 and abs(base["dd"] - REC_DD) < 0.01
    print(f"[invariant] baseline {base['sharpe']:+.3f}/{base['dd']*100:.1f}% -> "
          f"{'OK reproduces 0094' if ok else 'MISMATCH'}\n")
    print(_row("close-only stop (0094)", base))
    print(_row("intraday hard stop    ", cand))
    ba, bb, bc = _slices(base); ca, cb, cc = _slices(cand)
    print(f"    slice Sharpe base: {ba:+.2f}/{bb:+.2f}/{bc:+.2f} | hard: {ca:+.2f}/{cb:+.2f}/{cc:+.2f}")
    print(f"    exit-reason mix base {base['reasons']}")
    print(f"    exit-reason mix hard {cand['reasons']}")
    dS = cand["sharpe"] - base["sharpe"]; dC = (cand["cagr"] - base["cagr"]) * 100
    dD = (cand["dd"] - base["dd"]) * 100; d22 = cc - bc
    lo, hi = _dsh_ci(base["ret"], cand["ret"])
    print(f"\n  dSharpe {dS:+.3f} [{lo:+.3f},{hi:+.3f}] | dCAGR {dC:+.2f}pp | dMaxDD {dD:+.2f}pp "
          f"| Calmar {_calmar(base):.2f}->{_calmar(cand):.2f} | d(2022-26) {d22:+.3f}")
    print(f"  trades {base['trades']} -> {cand['trades']} | win {base['wr']*100:.0f}% -> {cand['wr']*100:.0f}% "
          f"| expR {base['expR']:+.2f} -> {cand['expR']:+.2f}")
    bar = {"dSharpe>=+0.05": dS >= 0.05, "dMaxDD>=+2.0pp": dD >= 2.0,
           "dCAGR>=-2.0pp": dC >= -2.0, "2022-26 not worse >0.05": d22 >= -0.05}
    print("\n  pre-committed bar (0105):")
    for k, v in bar.items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    print(f"\n  n_trials {cumulative_n_trials()} | VERDICT: "
          f"{'SHADOW -> forward wall' if all(bar.values()) else 'KILL / UNDERPOWERED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
