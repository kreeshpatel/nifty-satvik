"""Stage B of pre-reg 0116 (MEASUREMENT, 0 trials) — the FROZEN rule on the full substrate, sealed set
opened here, once.

Frozen rule (Amendment 1): SKIP signals whose pre-entry path_eff > the TRAIN 66.7th percentile (constant
computed from train 2019-01..2024-06). This script reports kept-vs-skipped per-trade R, conditional on
ext-band x CRS-tercile cells, separately for TRAIN and the SEALED 2024-07+ slice, plus the mechanism
readout (post-exit label composition of skipped trades) and the sealed per-year table.

Pre-committed bar: sealed conditional kept-minus-skipped dMeanR >= +0.10, same sign as train, and >=50%
of the train effect size.

    python scripts/diag_context_stageB.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CTX = ROOT / "research" / "substrate" / "context_windows.parquet"


def cond_delta(s: pd.DataFrame, rr: str) -> tuple[float, int]:
    """n-weighted kept-minus-skipped mean R within ext_band x crs_t cells (>=20 per side)."""
    sp, wt = [], []
    for _, cell in s.groupby(["ext_band", "crs_t"], observed=True):
        k, x = cell[~cell["skip"]][rr], cell[cell["skip"]][rr]
        if len(k) < 20 or len(x) < 10:
            continue
        sp.append(k.mean() - x.mean()); wt.append(len(cell))
    return (float(np.average(sp, weights=wt)) if sp else np.nan), int(sum(wt))


def main() -> int:
    d = pd.read_parquet(CTX)
    col = {c.lower(): c for c in d.columns}
    en_d, rr = col["entry_date"], col["r"]
    ext, crs = col.get("ext_vs_sma"), col.get("rank_crs")
    d[en_d] = pd.to_datetime(d[en_d])
    d = d.dropna(subset=["path_eff", rr]).copy()
    d["ext_band"] = pd.cut(d[ext], [-np.inf, 10, 20, np.inf], labels=["e0", "e1", "e2"])
    d["crs_t"] = pd.qcut(d[crs].rank(method="first"), 3, labels=["c0", "c1", "c2"])
    train = d[(d[en_d] >= "2019-01-01") & (d[en_d] <= "2024-06-30")]
    THR = float(np.percentile(train["path_eff"], 66.7))     # THE frozen constant
    d["skip"] = d["path_eff"] > THR
    print(f"frozen threshold: path_eff > {THR:.4f} -> SKIP | train n={len(train)}")

    sealed = d[d[en_d] >= "2024-07-01"]
    for tag, s in (("TRAIN", d[(d[en_d] >= "2019-01-01") & (d[en_d] <= "2024-06-30")], ),
                   ("SEALED", sealed,)):
        s = s.copy()
        cd, n = cond_delta(s, rr)
        kept, skip = s[~s["skip"]], s[s["skip"]]
        print(f"\n[{tag}] n={len(s)} | skipped {len(skip)} ({len(skip)/len(s)*100:.0f}%)")
        print(f"  raw:  kept meanR {kept[rr].mean():+.3f} (win {(kept[rr]>0).mean()*100:.0f}%) vs "
              f"skipped {skip[rr].mean():+.3f} (win {(skip[rr]>0).mean()*100:.0f}%) -> d {kept[rr].mean()-skip[rr].mean():+.3f}")
        print(f"  CONDITIONAL kept-minus-skipped dMeanR: {cd:+.3f}  (cells n={n})")
    # mechanism: post-exit label composition, kept vs skipped (train+sealed pooled)
    print("\nmechanism readout (label rates, kept vs skipped):")
    for lab in ("false_touch", "noise_stop", "exit_too_early"):
        if lab in d:
            l = d[lab].astype(float)
            print(f"  {lab:<15} kept {l[~d['skip']].mean():.3f} | skipped {l[d['skip']].mean():.3f}")
    print("\nsealed per-year kept-vs-skipped dMeanR (raw):")
    for y, g in sealed.groupby(sealed[en_d].dt.year):
        k, x = g[~g["skip"]][rr], g[g["skip"]][rr]
        if len(k) > 20 and len(x) > 10:
            print(f"  {y}: {k.mean()-x.mean():+.3f}  (kept {len(k)} / skipped {len(x)})")
    # verdict vs the pre-committed bar
    tr_cd, _ = cond_delta(d[(d[en_d] >= "2019-01-01") & (d[en_d] <= "2024-06-30")].copy(), rr)
    se_cd, _ = cond_delta(sealed.copy(), rr)
    ok = (np.sign(se_cd) == np.sign(tr_cd)) and se_cd >= 0.10 and abs(se_cd) >= 0.5 * abs(tr_cd)
    print(f"\nBAR: sealed conditional d >= +0.10, train sign, >=50% of train ({tr_cd:+.3f}) "
          f"-> sealed {se_cd:+.3f} -> {'PASS -> Stage C' if ok else 'FAIL -> record and stop'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
