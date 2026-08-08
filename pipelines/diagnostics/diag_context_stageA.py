"""Stage A of pre-reg 0116 (MEASUREMENT, 0 trials) — do path-shape features separate trades BEYOND
extension and CRS, on the TRAIN years only?

Protocol (fixed in the pre-reg): entries 2019-01-01..2024-06-30 ONLY (the 2024-07+ sealed set is NOT
read by this script — enforced below). For each path-shape feature: top-vs-bottom tercile spread in
per-trade R (mean + median, bootstrap 95% CI), computed WITHIN ext-band (<=10/10-20/>20%) x CRS-tercile
cells and averaged across cells (the conditional/marginal effect), plus the raw pooled spread (reported,
no verdict weight), plus the per-year sign table. Stage-A bar: conditional spread >= +0.15R AND same
sign in >=4 of the 5.5 train years.

    python scripts/diag_context_stageA.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CTX = ROOT / "research" / "substrate" / "context_windows.parquet"
TRAIN_LO, TRAIN_HI = "2019-01-01", "2024-06-30"   # sealed set (>= 2024-07-01) NEVER read here
FEATS = ["path_eff", "gap_share", "gap_max", "runup21", "dd_hi21", "updays", "accel",
         "range_comp", "vol_burst", "rs21"]
RNG = np.random.default_rng(20260727)


def boot_ci(a: np.ndarray, b: np.ndarray, n: int = 2000):
    """95% CI of mean(a)-mean(b)."""
    d = [RNG.choice(a, len(a)).mean() - RNG.choice(b, len(b)).mean() for _ in range(n)]
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main() -> int:
    d = pd.read_parquet(CTX)
    col = {c.lower(): c for c in d.columns}
    en_d = col.get("entry_date"); rr = col.get("r")
    ext = col.get("ext_vs_sma") or col.get("ext"); crs = col.get("rank_crs") or col.get("rank")
    d[en_d] = pd.to_datetime(d[en_d])
    d = d[(d[en_d] >= TRAIN_LO) & (d[en_d] <= TRAIN_HI)].copy()   # TRAIN ONLY — the firewall
    print(f"TRAIN slice: {len(d)} trades ({TRAIN_LO}..{TRAIN_HI}); sealed set untouched")
    d["ext_band"] = pd.cut(d[ext], [-np.inf, 10, 20, np.inf], labels=["e0", "e1", "e2"])
    d["crs_t"] = pd.qcut(d[crs].rank(method="first"), 3, labels=["c0", "c1", "c2"])
    d["yr"] = d[en_d].dt.year

    print(f"\n{'feature':<12}{'raw dR':>8}{'COND dR':>9}{'CI':>18}{'medR dR':>9}{'yr-sign':>9}  verdict")
    for f in FEATS:
        s = d.dropna(subset=[f, rr])
        if len(s) < 300:
            print(f"{f:<12}  insufficient n={len(s)}"); continue
        s = s.copy(); s["q"] = pd.qcut(s[f].rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
        raw = s[s["q"] == 2][rr].mean() - s[s["q"] == 0][rr].mean()
        # conditional: within ext_band x crs_t cells, tercile split INSIDE the cell, then n-weighted avg
        cond_sp, cond_n, hi_all, lo_all = [], [], [], []
        for _, cell in s.groupby(["ext_band", "crs_t"], observed=True):
            if len(cell) < 30:
                continue
            cq = pd.qcut(cell[f].rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
            hi, lo = cell[cq == 2][rr], cell[cq == 0][rr]
            if len(hi) < 8 or len(lo) < 8:
                continue
            cond_sp.append(hi.mean() - lo.mean()); cond_n.append(len(cell))
            hi_all.append(hi.to_numpy()); lo_all.append(lo.to_numpy())
        if not cond_sp:
            print(f"{f:<12}  no valid cells"); continue
        cond = float(np.average(cond_sp, weights=cond_n))
        lo_ci, hi_ci = boot_ci(np.concatenate(hi_all), np.concatenate(lo_all))
        med = float(np.median(np.concatenate(hi_all)) - np.median(np.concatenate(lo_all)))
        yr_signs = []
        for y, gy in s.groupby("yr"):
            if len(gy) < 60:
                continue
            q = pd.qcut(gy[f].rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
            yr_signs.append(np.sign(gy[q == 2][rr].mean() - gy[q == 0][rr].mean()))
        dom = int(max((np.array(yr_signs) > 0).sum(), (np.array(yr_signs) < 0).sum())) if yr_signs else 0
        bar = abs(cond) >= 0.15 and dom >= 4
        print(f"{f:<12}{raw:>+8.2f}{cond:>+9.2f}  [{lo_ci:+.2f},{hi_ci:+.2f}]{med:>+9.2f}"
              f"{dom:>6}/{len(yr_signs)}   {'CANDIDATE' if bar else '—'}")
    print("\nStage-A bar: |conditional spread| >= 0.15R AND dominant sign in >=4 train years.")
    print("Anything passing goes to the rule-freeze amendment; sealed set stays closed until then.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
