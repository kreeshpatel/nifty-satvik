"""Adversarial pass on the generic-dip trigger result (0024 §3b) before it settles into the ledger:
(1) OVERLAP — is the generic-dip pool a new lever or a rediscovery of Engine B (the 44-SMA pullback)?
    Jaccard / directional overlap of (ticker, signal-index ±3 bars) between the two signal sets.
(2) ERROR BARS — per-year 20d/60d excess (vs a YEAR-MATCHED universe control) + a cluster block bootstrap
    (events resampled by calendar-month cluster, 2000 draws) on the fill-basis excess returns.
Note: the +0.23/+2.13pp quoted in 0024 §3b was already FILL-basis (same corrected loop as the RSI pool).
Diagnostic only (no n_trials, no portfolio, no costs).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from diag_rsi_recovery import pool_masks  # noqa: E402
from run_bhanushali_practitioner import prep  # noqa: E402

START = pd.Timestamp("2017-01-01")
HZ = (20, 60)


def main() -> int:
    P = prep(load_ohlcv_cache(OHLCV_CACHE))
    # --- (1) overlap between generic-dip events and Engine-B pullback events ---
    n_dip = n_b = n_dip_near_b = n_b_near_dip = 0
    events = []                                                        # fill-basis dip events for (2)
    usum = {h: {} for h in HZ}; ucnt = {h: {} for h in HZ}             # year-matched universe control
    for t, s in P.items():
        c, h_, l_, o_ = s["c"], s["h"], s["l"], s["o"]
        n = len(c)
        _, dip = pool_masks(s)
        engB = s["strong"] & s["hold44"] & s["qgreen"] & s["hvc"]
        in_win = s["dates"] >= START
        di = np.flatnonzero(dip & in_win); bi = np.flatnonzero(engB & in_win)
        n_dip += len(di); n_b += len(bi)
        if len(bi):
            for i in di:
                if np.abs(bi - i).min() <= 3:
                    n_dip_near_b += 1
        if len(di):
            for i in bi:
                if np.abs(di - i).min() <= 3:
                    n_b_near_dip += 1
        # universe control accumulators by year
        for h in HZ:
            v = np.full(n, np.nan); v[:-h] = c[h:] / c[:-h] - 1.0
            ok = in_win & np.isfinite(v)
            for yr, val in zip(s["dates"].year[ok], v[ok]):
                usum[h][yr] = usum[h].get(yr, 0.0) + val
                ucnt[h][yr] = ucnt[h].get(yr, 0) + 1
        # fill-basis dip events
        for i in di:
            if i + 3 + max(HZ) >= n:
                continue
            trig, stop = h_[i] * 1.001, l_[i] * 0.999
            for k in range(1, 4):
                if l_[i + k] <= stop:
                    break
                if h_[i + k] >= trig:
                    j = i + k
                    fill = max(o_[j], trig)
                    events.append(dict(tkr=t, d=s["dates"][j],
                                       **{f"f{h}": c[j + h] / fill - 1.0 for h in HZ}))
                    break
    um = {h: {yr: usum[h][yr] / ucnt[h][yr] for yr in usum[h]} for h in HZ}
    inter = (n_dip_near_b + n_b_near_dip) / 2.0
    print("=== (1) overlap: generic-dip pool vs Engine-B (44-SMA pullback) signal set ===")
    print(f"  dip events {n_dip} | engine-B events {n_b}")
    print(f"  dip events with a B signal within +/-3 bars: {n_dip_near_b} ({100*n_dip_near_b/max(n_dip,1):.0f}%)")
    print(f"  B events with a dip signal within +/-3 bars: {n_b_near_dip} ({100*n_b_near_dip/max(n_b,1):.0f}%)")
    print(f"  Jaccard (approx, +/-3 bars): {inter/(n_dip + n_b - inter):.2f}")

    E = pd.DataFrame(events)
    for h in HZ:
        E[f"x{h}"] = E[f"f{h}"] - E["d"].dt.year.map(um[h])
    print(f"\n=== (2) fill-basis TRIGGERED dip events: {len(E)} | excess vs YEAR-MATCHED universe ===")
    print("  per-year table:")
    g = E.groupby(E["d"].dt.year)
    for yr, grp in g:
        print(f"    {yr}: n {len(grp):>4} | 20d excess {grp['x20'].mean()*100:+5.2f}pp | 60d excess {grp['x60'].mean()*100:+5.2f}pp")
    print(f"  pooled: 20d {E['x20'].mean()*100:+.2f}pp | 60d {E['x60'].mean()*100:+.2f}pp")
    rng = np.random.default_rng(7)
    E["cl"] = E["d"].dt.to_period("M")
    cls = E["cl"].unique()
    groups = {cl: grp for cl, grp in E.groupby("cl")}
    for h in HZ:
        means = []
        for _ in range(2000):
            take = rng.choice(cls, size=len(cls), replace=True)
            v = np.concatenate([groups[cl][f"x{h}"].to_numpy() for cl in take])
            means.append(v.mean())
        lo, hi = np.percentile(means, [2.5, 97.5])
        print(f"  {h}d excess cluster-bootstrap 95% CI (by calendar month, 2000 draws): "
              f"[{lo*100:+.2f}, {hi*100:+.2f}]pp {'(excludes 0)' if lo > 0 or hi < 0 else '(INCLUDES 0)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
