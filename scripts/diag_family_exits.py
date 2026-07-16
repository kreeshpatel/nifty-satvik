"""Step 1 (correct order) — per-family EXIT co-optimization, then re-sizing with per-family exits.

Stage 3 showed breakout families (box/cup/double_bottom) trend cleaner (31-34% MFE capture) while the
touch spikes-and-reverts (12%). Principled hypothesis: breakout families want a LET-IT-RUN exit, the
touch wants the book-half + cut-the-blowoff exit it already has (P2 / finding 0099).

We test a SMALL principled archetype set per family (not a grid — honest about 3x multiple testing),
on the continuous-slice 2022-26 gate, then rebuild the sleeve book with each family on ITS best exit
and compare to the uniform-exit sleeve and the live baseline. Measurement only; nothing ships here.

    python scripts/diag_family_exits.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import filter_P, combine

NAMES = {0: "touch44", 1: "box", 6: "cup_handle", 7: "ascending_base", 8: "double_bottom"}
FAMILIES = [0, 1, 6, 7, 8]

# Three principled exit archetypes (motivated by the capture characterization):
EXITS = {
    "P2 (book+blowoff)": dict(no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5),   # the touch-tuned one
    "let-run (no blowoff)": dict(no_time_cap=True),                                          # half@2R + 20d-trail only, no early blowoff cut
    "tight-capture (lockin)": dict(no_time_cap=False, blowoff_arm_r=2.0, lockin_mfe=2.0, lockin_at=1.0),
}


def metrics(curve, trades=None):
    e = curve.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    dd = (e / e.cummax() - 1).min()
    rr = r[(r.index >= "2022-01-01")]
    s22 = rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan
    return dict(sharpe=sh, cagr=cagr, dd=dd, calmar=cagr / abs(dd) if dd else np.nan, s22=s22, trades=trades)


def run(P, mem, origins, exit_cfg, eq0):
    m = R94.backtest(filter_P(P, origins), mem, start="2017-01-01", eq0=eq0, **exit_cfg)
    return m["curve"], m["trades"]


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv, box_breakout=True, trend_pullback=True, sr_pivot=True, zoo_origins=(6, 7, 8))

    print("=== per-family exit archetypes (Rs10L each; * = best by 2022-26 slice) ===")
    best_exit = {}
    for f in FAMILIES:
        print(f"\n{NAMES[f]}:")
        rows = {}
        for en, ec in EXITS.items():
            c, t = run(P, mem, [f], ec, EQ0); rows[en] = (metrics(c, t), ec)
        best = max(rows, key=lambda k: (rows[k][0]["s22"] if rows[k][0]["s22"] == rows[k][0]["s22"] else -9))
        best_exit[f] = rows[best][1]
        for en, (mm, _) in rows.items():
            star = " *" if en == best else "  "
            print(f"  {en:24s} tr={mm['trades']:4d} Sh={mm['sharpe']:5.2f} CAGR={mm['cagr']*100:5.1f}% "
                  f"DD={mm['dd']*100:6.1f}% Calmar={mm['calmar']:4.2f} 22-26={mm['s22']:5.2f}{star}")

    print("\n=== re-sizing: sleeve (touch+cup+dblbottom) with UNIFORM vs PER-FAMILY exits ===")
    sleeve = [0, 6, 8]; per = EQ0 / len(sleeve)
    # baseline: live touch book (P2)
    cb, tb = run(P, mem, [0], EXITS["P2 (book+blowoff)"], EQ0)
    print(f"  A  live touch (P2)           " + fmt(metrics(cb, tb)))
    # uniform-exit sleeve (all P2)
    cu = combine([run(P, mem, [f], EXITS["P2 (book+blowoff)"], per)[0] for f in sleeve])
    print(f"  D  sleeve uniform P2 exit    " + fmt(metrics(cu)))
    # per-family-exit sleeve
    cp = combine([run(P, mem, [f], best_exit[f], per)[0] for f in sleeve])
    print(f"  D* sleeve PER-FAMILY exits   " + fmt(metrics(cp)))
    print("\n  (per-family exits chosen: " + ", ".join(f"{NAMES[f]}={[k for k,v in EXITS.items() if v is best_exit[f]][0]}" for f in sleeve) + ")")
    print("  NOTE: 3 archetypes x 5 families = multiple testing; treat 'best' as exploratory, forward-wall certifies.")


def fmt(m):
    return f"Sh={m['sharpe']:5.2f} CAGR={m['cagr']*100:5.1f}% DD={m['dd']*100:6.1f}% Calmar={m['calmar']:4.2f} 22-26={m['s22']:5.2f}"


if __name__ == "__main__":
    main()
