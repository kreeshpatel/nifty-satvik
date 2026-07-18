"""POOL QUALITY vs SELECTION SKILL — can we raise the RANDOM floor (0.67), not the CRS ceiling?

Owner's reframing: don't build a better picker (the Monte-Carlo null proved CRS-rank is already at the
99-100th percentile — the ceiling). Instead make the POOL so good that even a random pick is fine, i.e.
raise the null mean itself. This matters because the honest forward expectation spans 0.67 (no selection
skill persists) to 1.03 (full skill) — raising the FLOOR is real risk reduction.

The target: the 5-10% entry-extension band is 36% of the touch pool but returns ~0 (+0.09R, median
-1.03R) and holds only 10% of total R — a capital-drainer that is NOT where the fat tail lives.

This is the test the registry never ran: ext-caps were judged on the CRS-SELECTED book (and rejected).
Here we ask the de-confounded question — does removing the band raise the RANDOM-selection null?

Pool filter is PIT-safe: it uses the SIGNAL-week extension (completed bar, known before the fill).

    python scripts/diag_pool_filter.py [N_SIMS]
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from nq.data.weekly import load_weekly_panel
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import P2_EXIT

N_SIMS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
OUT = ROOT / "research" / "substrate" / "pool_filter_sims.csv"
TRAP_LO, TRAP_HI = 0.05, 0.10          # the dead band (pre-declared from the measured pool structure)


def stats(curve, trades=None):
    e = curve.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]
    return dict(sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan,
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                dd=(e / e.cummax() - 1).min(),
                s22=rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan, trades=trades)


def sig_ext_map(P):
    """Signal-week extension (close/sma44 - 1) per entry window — PIT-safe (completed bar)."""
    wp = load_weekly_panel(cache=True)
    fm = {(r.ticker, r.week_end): (r.c, r.sma44) for r in wp.itertuples()}
    out = {}
    for t, s in P.items():
        dates = pd.DatetimeIndex(s["dates"])
        for e0 in s["entry_win"]:
            if e0 < 1:
                continue
            f = fm.get((t, dates[e0 - 1]))
            if f and f[1] and f[1] == f[1] and f[1] > 0:
                out[(t, e0)] = f[0] / f[1] - 1.0
    return out


def drop_band(P, ext, lo, hi):
    """Remove entry windows whose SIGNAL-week extension sits in [lo, hi) — a POOL filter, not a selector."""
    out = {}
    for t, s in P.items():
        s2 = dict(s)
        s2["entry_win"] = {e0: w for e0, w in s["entry_win"].items()
                           if not (lo <= ext.get((t, e0), -9) < hi)}
        out[t] = s2
    return out


def null_dist(P, mem, keys, n, tag):
    rows = []
    for seed in range(n):
        rng = np.random.default_rng(seed)
        conv = {k: float(v) for k, v in zip(keys, rng.random(len(keys)))}
        m = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, fill_order="conviction",
                         conv_score=conv, **P2_EXIT)
        r = stats(m["curve"], m["trades"]); r["seed"] = seed; r["pool"] = tag
        rows.append(r)
        if (seed + 1) % 10 == 0:
            print(f"    {tag}: {seed+1}/{n}", flush=True)
    return pd.DataFrame(rows)


def summarize(df, tag):
    print(f"  {tag:22s} Sharpe {df.sharpe.mean():.2f}+-{df.sharpe.std():.2f}  "
          f"CAGR {df.cagr.mean()*100:5.1f}%  DD {df.dd.mean()*100:6.1f}%  "
          f"22-26 {df.s22.mean():.2f}+-{df.s22.std():.2f}  tr {df.trades.mean():.0f}")


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    ext = sig_ext_map(P)
    Pf = drop_band(P, ext, TRAP_LO, TRAP_HI)
    nA = sum(len(s["entry_win"]) for s in P.values())
    nB = sum(len(s["entry_win"]) for s in Pf.values())
    print(f"pool A (all): {nA} windows   pool B (5-10% band dropped): {nB}  (-{(1-nB/nA)*100:.0f}%)\n")

    # CRS-selected book on each pool (the ceiling)
    mA = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mA["sharpe"] - 1.034) < 0.005, "R1 baseline FAILED"
    a = stats(mA["curve"], mA["trades"])
    mB = R94.backtest(Pf, mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    b = stats(mB["curve"], mB["trades"])
    print("=== CRS-rank (the ceiling) ===")
    print(f"  {'A pool=all (LIVE)':22s} Sharpe {a['sharpe']:.2f}  CAGR {a['cagr']*100:5.1f}%  "
          f"DD {a['dd']*100:6.1f}%  22-26 {a['s22']:.2f}  tr {a['trades']}")
    print(f"  {'B pool=band dropped':22s} Sharpe {b['sharpe']:.2f}  CAGR {b['cagr']*100:5.1f}%  "
          f"DD {b['dd']*100:6.1f}%  22-26 {b['s22']:.2f}  tr {b['trades']}")

    print(f"\n=== RANDOM-selection null (the FLOOR) — {N_SIMS} sims each ===")
    dA = null_dist(P, mem, list(ext), N_SIMS, "A all")
    dB = null_dist(Pf, mem, [k for k in ext if not (TRAP_LO <= ext[k] < TRAP_HI)], N_SIMS, "B filtered")
    pd.concat([dA, dB]).to_csv(OUT, index=False)
    summarize(dA, "A pool=all")
    summarize(dB, "B pool=band dropped")
    lift = dB.sharpe.mean() - dA.sharpe.mean()
    l22 = dB.s22.mean() - dA.s22.mean()
    print(f"\n  FLOOR LIFT: Sharpe {lift:+.2f}   22-26 {l22:+.2f}  -> "
          f"{'POOL IMPROVED (random floor rises)' if lift > 0 else 'no pool improvement'}")
    print(f"  CEILING (CRS) change: 22-26 {b['s22']-a['s22']:+.2f}")


if __name__ == "__main__":
    main()
