"""Pre-reg 0083 — certify the frozen volume-confirmed momentum-pullback recipe. Is the in-sample ~1.0 Sharpe
real, or a Deflated-Sharpe artifact of the multi-parameter search? DSR @ cumulative n_trials + block-bootstrap
Sharpe CI + CONTINUOUS-SLICE sub-periods (sliced from ONE full run — never a fresh-capital re-run).
Frozen config: sig_strong_vol, stop=2.5xATR, RR=1:3, maxhold=40. No retuning; the config is locked in the pre-reg.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from diag_ma44_pullback import backtest, prep  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.runner.research import _dsr_from_bootstrap  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402

N_TRIALS = 101   # cumulative program search burden (family-wise DSR penalty)


def _sh(r):
    r = np.asarray(r, float)
    return r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan")


def main() -> int:
    P = prep(load_ohlcv_cache(OHLCV_CACHE))
    # ONE full-period run of the FROZEN config
    m = backtest(P, "sig_strong_vol", RR=3.0, stop_mode="atr25", maxhold=40, exit_mode="target")
    eq = m["curve"]
    r = eq.pct_change().dropna()
    a = r.to_numpy(float)

    full_sh = _sh(a)
    ci = block_bootstrap_metric(a, sharpe_fn, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dsr = _dsr_from_bootstrap(a, N_TRIALS, (ci.lower, ci.upper))
    # continuous-slice sub-periods (slice the ONE curve's daily returns; no re-run)
    pre = r[r.index < "2022-01-01"]; post = r[r.index >= "2022-01-01"]
    sh_pre, sh_post = _sh(pre.to_numpy()), _sh(post.to_numpy())

    print("=== 0083 hybrid momentum-pullback — CERTIFICATION (frozen config) ===")
    print(f"trades {m['trades']} | win {m['wr']*100:.1f}% | CAGR {m['cagr']*100:+.1f}% | MaxDD {m['dd']*100:.1f}%")
    print(f"full daily-Sharpe {full_sh:+.3f}  | bootstrap 95% CI [{ci.lower:+.3f}, {ci.upper:+.3f}]")
    print(f"DSR @ n_trials={N_TRIALS}: {dsr:.3f}   (gate: > 0.95)")
    print(f"continuous-slice sub-periods: 2017-21 Sharpe {sh_pre:+.3f} | 2022-26 Sharpe {sh_post:+.3f}")
    gates = {
        "DSR>0.95": bool(np.isfinite(dsr) and dsr > 0.95),
        "CI_low>0": bool(ci.lower > 0),
        "both_subperiods>0": bool(sh_pre > 0 and sh_post > 0),
    }
    print("\ngates:", {k: ("PASS" if v else "FAIL") for k, v in gates.items()})
    if all(gates.values()):
        verdict = "PROMOTE -> forward-wall watched sleeve"
    elif ci.lower > 0 and full_sh > 0:
        verdict = "UNDERPOWERED (real-looking but not certified at n_trials=101)"
    else:
        verdict = "KILL"
    print(f"VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
