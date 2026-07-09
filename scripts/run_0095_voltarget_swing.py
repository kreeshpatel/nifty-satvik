"""Pre-reg 0095 - vol-target de-gross ported to the weekly-swing-0094 book.

Runs the FROZEN 0094 engine twice on the corrected universe (baseline = vol_target off, overlay =
vol_target (0.15, 42, 0.40)), verifies the engine invariant (baseline reproduces the 0094 run of
record byte-for-byte on the headline metrics), and scores the overlay against the pre-committed
DD-overlay bar fixed in diagnostics/research/preregistry/0095-voltarget-swing.md.

    python scripts/run_0095_voltarget_swing.py
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
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import _row, _slices  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

VT = (0.15, 42, 0.40)   # (target_annual, window, floor) - reused verbatim from promoted O-009 V2
# 0094 run of record (models/bhanushali_weekly/config.json), NET, corrected universe
REC_SHARPE, REC_DD = 1.132, -0.424


def _calmar(m):
    return m["cagr"] / abs(m["dd"]) if m["dd"] else float("nan")


def _dsharpe_ci(base_ret, cand_ret, block=DEFAULT_BLOCK, n=5000, seed=12345):
    """Block-bootstrap 95% CI of (Sharpe_cand - Sharpe_base) on the PAIRED daily returns."""
    idx = base_ret.index.intersection(cand_ret.index)
    b = base_ret.reindex(idx).to_numpy(float); c = cand_ret.reindex(idx).to_numpy(float)
    N = len(b); rng = np.random.default_rng(seed)
    nblocks = int(np.ceil(N / block))
    diffs = []
    for _ in range(n):
        starts = rng.integers(0, N - block + 1, size=nblocks)
        sel = np.concatenate([np.arange(s, s + block) for s in starts])[:N]
        diffs.append(sharpe_fn(c[sel]) - sharpe_fn(b[sel]))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(lo), float(hi)


def main() -> int:
    print("=== pre-reg 0095: vol-target de-gross ported to the weekly-swing-0094 book ===")
    ohlcv = corrected_universe(); mem = load_membership()
    P = prep_weekly_rank(ohlcv)
    print(f"corrected universe: {len(P)} names | vol_target={VT} (target_annual, window, floor)\n")

    base = backtest(P, mem)                      # NET, overlay OFF
    cand = backtest(P, mem, vol_target=VT)       # NET, overlay ON

    # ── engine invariant: baseline must reproduce the 0094 run of record ──
    d_sh, d_dd = abs(base["sharpe"] - REC_SHARPE), abs(base["dd"] - REC_DD)
    ok = d_sh < 0.02 and d_dd < 0.01
    print(f"[invariant] baseline Sharpe {base['sharpe']:+.3f} (rec {REC_SHARPE:+.3f}, d={d_sh:.3f}) | "
          f"DD {base['dd']*100:.1f}% (rec {REC_DD*100:.1f}%, d={d_dd*100:.2f}pp) -> "
          f"{'OK reproduces 0094' if ok else 'MISMATCH - investigate before trusting the overlay'}\n")

    print(_row("baseline (vol_target OFF)", base))
    print(_row("overlay  (vol_target ON) ", cand))
    ba, bb, bc = _slices(base); ca, cb, cc = _slices(cand)
    print(f"    slice Sharpe base: 2017-18* {ba:+.2f} | 2019-21 {bb:+.2f} | 2022-26 {bc:+.2f}")
    print(f"    slice Sharpe over: 2017-18* {ca:+.2f} | 2019-21 {cb:+.2f} | 2022-26 {cc:+.2f}")

    d_sharpe = cand["sharpe"] - base["sharpe"]
    d_cagr = (cand["cagr"] - base["cagr"]) * 100
    d_dd_pp = (cand["dd"] - base["dd"]) * -100     # +ve = drawdown got shallower (improved)
    d_slice22 = cc - bc
    print(f"\n  dSharpe {d_sharpe:+.3f} | dCAGR {d_cagr:+.2f}pp | dMaxDD {d_dd_pp:+.2f}pp (positive = shallower) "
          f"| Calmar {_calmar(base):.2f}->{_calmar(cand):.2f}")
    print(f"  d(2022-26 slice Sharpe) {d_slice22:+.3f}")

    lo, hi = _dsharpe_ci(base["ret"], cand["ret"])
    n_indep = len(base["ret"]) / 63.0
    print(f"  dSharpe block-bootstrap 95% CI [{lo:+.3f}, {hi:+.3f}] | n_independent~{n_indep:.0f} "
          f"(63d windows) -> {'adequate' if n_indep >= 20 else 'UNDERPOWERED'}")

    # ── pre-committed bar (0095): DD overlay ──
    bar = {
        "dMaxDD >= +3.0pp": d_dd_pp >= 3.0,
        "dSharpe >= -0.05": d_sharpe >= -0.05,
        "2022-26 slice not worse by >0.05": d_slice22 >= -0.05,
        "dCAGR >= -2.0pp": d_cagr >= -2.0,
    }
    print("\n  pre-committed bar (0095):")
    for k, v in bar.items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    verdict = ("SHADOW -> route vol-target to the forward wall" if all(bar.values())
               else "KILL / UNDERPOWERED - does not clear the 0095 bar")
    print(f"\n  n_trials (this run counted): {cumulative_n_trials()}")
    print(f"  VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
