"""FULL AUDIT of the live config + re-test of the GRADE-B trades under a daily 14-EMA gate.

Two things:
 1. AUDIT — the live paper book runs `a_grade=grade_a_entries(P)` (Grade-A only, top-5 CRS per setup
    week; run_bhanushali_cron.py:346-349) while the research baseline used all session runs WITHOUT
    a_grade (= ALL grades). Those are different books. This prints both, so we know what is actually live.
 2. GRADE-B RE-TEST — A-only vs all-grades was NEVER decided in-sample (routed to the forward wall,
    prereg_swing.md §7a), so testing B is legitimately open, not a relitigation. Owner's new formulation:
    admit a B signal ONLY if the stock is above its daily 14-EMA at the signal close.

PIT-safety: the gate reads the SIGNAL day (the completed Friday, index e0-1) — the fill is the next
week's open, so the EMA is fully known before we buy.

Judged on the 2022-26 continuous slice (R3). Declared K=1 filter (14-EMA), no sweep (R4).

    python scripts/diag_grade_b.py
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
from diag_sleeves import P2_EXIT

EMA_SPAN = 14


def stats(curve, trades):
    e = curve.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]; r1 = r[r.index < "2022-01-01"]
    dd = (e / e.cummax() - 1).min()
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    return dict(sh=r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan, cagr=cagr, dd=dd,
                calmar=cagr / abs(dd) if dd else np.nan,
                s17=r1.mean() / r1.std() * np.sqrt(252) if r1.std() else np.nan,
                s22=rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan, tr=trades)


def show(lab, m):
    print(f"  {lab:32s} tr={m['tr']:4d} Sh={m['sh']:5.2f} CAGR={m['cagr']*100:5.1f}% DD={m['dd']*100:6.1f}% "
          f"Calmar={m['calmar']:4.2f} [17-21 {m['s17']:5.2f} | 22-26 {m['s22']:5.2f}]")


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)

    all_win = {(t, e0) for t, s in P.items() for e0 in s["entry_win"]}
    a_set = R94.grade_a_entries(P, top_n=5)
    b_set = all_win - a_set
    print(f"entry windows: {len(all_win)}  | Grade A (top-5 CRS/week): {len(a_set)}  | Grade B: {len(b_set)}")

    # daily 14-EMA gate, read at the SIGNAL day (e0-1) -> known before the next-week fill
    b_pass = set()
    for t, s in P.items():
        c = np.asarray(s["c"], float)
        ema = pd.Series(c).ewm(span=EMA_SPAN, adjust=False).mean().to_numpy()
        for e0 in s["entry_win"]:
            if (t, e0) in a_set or e0 < 1:
                continue
            if c[e0 - 1] > ema[e0 - 1]:
                b_pass.add((t, e0))
    print(f"Grade-B passing the daily 14-EMA gate at the signal close: {len(b_pass)} "
          f"({len(b_pass)/max(len(b_set),1)*100:.0f}% of B)\n")

    print("=== AUDIT + GRADE-B TEST (Rs10L, 2% risk, P2 exit; baseline gate = 22-26) ===")
    runs = {}
    for lab, ag in [("ALL grades (research baseline)", None),
                    ("A-only  <- THE LIVE PAPER BOOK", a_set),
                    ("A + B(above 14-EMA)  [owner]", a_set | b_pass),
                    ("A + ALL B (= all grades)", a_set | b_set)]:
        m = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, a_grade=ag, **P2_EXIT)
        runs[lab] = stats(m["curve"], m["trades"]); show(lab, runs[lab])

    print("\n=== VERDICT (22-26 continuous slice) ===")
    base = runs["ALL grades (research baseline)"]["s22"]
    live = runs["A-only  <- THE LIVE PAPER BOOK"]["s22"]
    owner = runs["A + B(above 14-EMA)  [owner]"]["s22"]
    print(f"  research baseline (all grades) : {base:.2f}")
    print(f"  LIVE paper book (A-only)       : {live:.2f}   -> {'the live book is BETTER' if live > base else 'the live book is WORSE than the research baseline'}")
    print(f"  A + 14-EMA-filtered B (owner)  : {owner:.2f}   -> vs live {owner-live:+.2f} | vs research base {owner-base:+.2f}")
    best = max(runs, key=lambda k: runs[k]["s22"])
    print(f"\n  best on the 22-26 gate: {best} ({runs[best]['s22']:.2f})")


if __name__ == "__main__":
    main()
