"""AUDIT (no trial): re-read 0001's DSR at a defensible trial count, and compare books honestly.

Study 0001 reports **DSR 0.991** and passes all seven gates. Its own `result.md` §3 warns, under
"What does NOT support this result", that this figure "is close to uninformative at `n_trials = 2`"
because the counter had been reset from 138 that same day, and that "that gate should be re-read once
the counter reflects genuine accumulated testing". Nobody re-read it. This does.

Why the reset does not lower the real bar. `nq/validation/dsr.lifetime_n_trials` states the argument
in its own docstring: the 138 trials happened, they ran on the same 2017-2026 daily Indian equity
history every number since is measured on, and they raised the bar whether or not a JSON field
records them. DSR deflates by the expected maximum Sharpe across the search actually performed.

The comparison this enables. The swing book's certification is DSR **0.894 at n_trials 114**
(`forward/prereg_swing.md` §1), computed by the same `_dsr_from_bootstrap` on the same per-window
basis. Comparing that to 0001's 0.991-at-2 is comparing a heavily deflated number to a barely
deflated one. Deflating both at a common count is the only comparison that means anything.

    python pipelines/diagnostics/diag_dsr_common_count.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.data.membership import load_membership  # noqa: E402
from nq.runner.research import _daily_returns, _dsr_from_bootstrap, _window_sig  # noqa: E402
from nq.universe import build_universe  # noqa: E402
from nq.validation.bootstrap import block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials, lifetime_n_trials  # noqa: E402
from nq.validation.metrics import sharpe  # noqa: E402
from pipelines.research.run_0001_xsec_momentum import BAND, END, START, add_signals, run  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

SWING_CERT = {"dsr": 0.894, "n_trials": 114, "sharpe": 1.132}
OUT = ROOT / "diagnostics" / "research" / "dsr_common_count.json"


def main() -> int:
    print("rebuilding 0001 ...", flush=True)
    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)
    keep = p["ticker"].isin(p.loc[p["size_band"] == BAND, "ticker"].unique())
    band = p[keep].copy()
    band["rank"] = np.where(band["eligible"] & (band["size_band"] == BAND) & band["nms"].notna(),
                            band["nms"], np.nan)
    bt = run(band)
    rets = _daily_returns(bt["equity_curve"]).to_numpy(float)
    ci = block_bootstrap_metric(rets, sharpe, block_size=63, n_samples=5000, seed=12345)
    sr_w, n_w, skew, kurt = _window_sig(rets)

    counts = {"committed_post_reset": cumulative_n_trials(),
              "swing_certification": SWING_CERT["n_trials"],
              "lifetime": lifetime_n_trials()}
    dsr = {k: round(_dsr_from_bootstrap(rets, n, (ci.lower, ci.upper)), 4) for k, n in counts.items()}

    out = {
        "_doc": "AUDIT, no trial. 0001's DSR re-read at defensible trial counts.",
        "reproduce": "python pipelines/diagnostics/diag_dsr_common_count.py",
        "study_0001": {
            "annualised_sharpe": bt["metrics"]["sharpe"],
            "per_window_sharpe": round(float(sr_w), 4),
            "n_eff_windows": int(n_w),
            "skew": round(float(skew), 3), "kurtosis": round(float(kurt), 3),
            "bootstrap_sharpe_ci": [round(ci.lower, 3), round(ci.upper, 3)],
            "n_trials": counts, "dsr_at": dsr,
        },
        "swing_certification": SWING_CERT,
        "reading": (
            f"At the swing book's own certification count ({SWING_CERT['n_trials']}), 0001 scores "
            f"DSR {dsr['swing_certification']} against the swing book's {SWING_CERT['dsr']}. The "
            f"0001 headline of {dsr['committed_post_reset']} exists only because the counter was "
            f"reset to {counts['committed_post_reset']} hours before the run. 0001 does not clear "
            f"the DSR>0.95 gate at any defensible count."
        ),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"\n0001: annualised Sharpe {bt['metrics']['sharpe']} | per-window {sr_w:.4f} | "
          f"n_eff {int(n_w)} | CI [{ci.lower:.3f}, {ci.upper:.3f}]")
    for k, n in counts.items():
        print(f"  DSR @ n_trials={n:>4} ({k:<20s}) = {dsr[k]:.4f}")
    print(f"\n  swing book certification: DSR {SWING_CERT['dsr']} @ n_trials {SWING_CERT['n_trials']}")
    print(f"  -> at a COMMON count the swing book leads {SWING_CERT['dsr']} to "
          f"{dsr['swing_certification']}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
