"""CORRECTION 2026-10-19 helper: isolate the membership effect in 0143.

The attribution ledger kept accruing after 0143 (11 -> 28 closed trades), so the re-run's population B is
not the population B that 0143 measured. This compares the PIT-gated population A (trades.csv, historical
rows) against the ORIGINAL 11 live trades (trades_membership_off.csv, live rows), so the only thing that
differs from 0143 is the membership gate. Output: like_for_like.json.

    python diagnostics/research/stop_width/2026-09-25/like_for_like.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import diag_stop_width as SW  # noqa: E402
from nq.brain import portfolio as PF  # noqa: E402

new = pd.read_csv(HERE / "trades.csv")
old = pd.read_csv(HERE / "trades_membership_off.csv")
hist = new[new["population"] == "historical"]
live11 = old[old["population"] == "live"]
hl, ll = hist[hist["r_multiple"] < 0], live11[live11["r_multiple"] < 0]


def diff(col):
    pt, lo, hi = PF.cluster_bootstrap_two_sample(hl[col], hl["ticker"], ll[col], ll["ticker"],
                                                 n_boot=SW.N_BOOT, seed=SW.SEED)
    return {"live_minus_historical": round(pt, 3), "ci": [round(lo, 3), round(hi, 3)],
            "excludes_zero": bool(lo > 0 or hi < 0)}


out = {
    "what": "PIT-gated population A vs the ORIGINAL 11 live trades (only the membership gate differs from 0143)",
    "A_n": int(len(hist)), "A_losses": int(len(hl)),
    "A_loss_median_stop_width_pct": round(float(hl["stop_width_pct"].median()), 3),
    "A_loss_median_return_pct": round(float(hl["return_pct"].median()), 3),
    "A_loss_median_R": round(float(hl["r_multiple"].median()), 3),
    "A_all_median_stop_width_pct": round(float(hist["stop_width_pct"].median()), 3),
    "B11_n": int(len(live11)), "B11_loss_median_stop_width_pct": round(float(ll["stop_width_pct"].median()), 3),
    "differences_live_minus_historical (losses)": {c: diff(c) for c in ("stop_width_pct", "return_pct", "r_multiple")},
    "reexpression": SW._reexpress(live11, float(hl["stop_width_pct"].median())),
}
(HERE / "like_for_like.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(json.dumps(out, indent=2))
