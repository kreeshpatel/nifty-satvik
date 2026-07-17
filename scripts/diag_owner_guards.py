"""Two OWNER-FOUND entry guards from a manual TradingView chart review (2026-07-16).

The owner reviewed the worst trades against the taught rule and flagged five things. Three map to
already-KILLED tests (0088 buy-stop confirmation — killed because buying the week's HIGH doubles the
entry->stop width to 12.8%; 0092 visibly-rising-MA tightening; and "entry candle must have a body",
which is 0088's confirmation by another name). TWO are genuinely new and untested:

  G1 ext_floor  — KENNAMET (-1.5%) and NAVA (-1.8%) FILLED BELOW the 44w SMA. The signal requires
                  close > SMA, but the 0089 in-range fill can still land below the line when the entry
                  week opens down through it. Guard: skip a fill whose open is not above the SMA.
  G2 progress   — RAINBOW's signal week was green (close>open) but closed 1444.8 vs the prior week's
                  1454.3, i.e. BELOW the previous close: a green candle inside a downswing. `qgreen`
                  never requires progress. Guard: require signal close > prior week's close.

Both are PIT-safe (G2 is a signal-week condition; G1 reads the fill open, observed before we buy).
Declared K=3 (G1, G2, G1+G2). Judged on the 2022-26 continuous slice; baseline (all-grades) = 1.29.

    python scripts/diag_owner_guards.py
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


def stats(c, tr):
    e = c.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]; r1 = r[r.index < "2022-01-01"]
    dd = (e / e.cummax() - 1).min(); cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    return dict(sh=r.mean() / r.std() * np.sqrt(252), cagr=cagr, dd=dd, calmar=cagr / abs(dd),
                s17=r1.mean() / r1.std() * np.sqrt(252), s22=rr.mean() / rr.std() * np.sqrt(252), tr=tr)


def show(lab, m):
    print(f"  {lab:34s} tr={m['tr']:4d} Sh={m['sh']:5.2f} CAGR={m['cagr']*100:5.1f}% DD={m['dd']*100:6.1f}% "
          f"Calmar={m['calmar']:4.2f} [17-21 {m['s17']:5.2f} | 22-26 {m['s22']:5.2f}]")


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)

    # G2: windows whose SIGNAL week closed above the PRIOR week's close (progress), PIT-safe
    prog = set()
    for t, s in P.items():
        dates = pd.DatetimeIndex(s["dates"]); c = np.asarray(s["c"], float)
        iso = dates.isocalendar(); keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
        weeks, cur, prev = [], [], None
        for i, k in enumerate(keys):
            if prev is not None and k != prev:
                weeks.append(cur); cur = []
            cur.append(i); prev = k
        if cur:
            weeks.append(cur)
        wc = np.array([c[d[-1]] for d in weeks])
        d2w = {i: wp for wp, d in enumerate(weeks) for i in d}
        for e0 in s["entry_win"]:
            k = d2w.get(e0, 0) - 1                       # the SIGNAL week
            if k >= 1 and wc[k] > wc[k - 1]:
                prog.add((t, e0))
    nall = sum(len(s["entry_win"]) for s in P.values())
    print(f"entry windows {nall}  |  G2 'signal close > prior close': {len(prog)} ({len(prog)/nall*100:.0f}%)\n")

    print("=== OWNER GUARDS (Rs10L, 2% risk, P2 exit; baseline 22-26 = 1.29) ===")
    base = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(base["sharpe"] - 1.034) < 0.005, "R1 baseline FAILED"
    b = stats(base["curve"], base["trades"]); show("BASE (all-grades, live rule)", b)

    g1 = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, ext_floor=0.0, **P2_EXIT)
    show("G1 fill must be ABOVE the SMA", stats(g1["curve"], g1["trades"]))

    g2 = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, a_grade=prog, **P2_EXIT)
    show("G2 signal close > prior close", stats(g2["curve"], g2["trades"]))

    g3 = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, ext_floor=0.0, a_grade=prog, **P2_EXIT)
    show("G3 both guards", stats(g3["curve"], g3["trades"]))

    print(f"\n=== VERDICT (22-26 gate, baseline {b['s22']:.2f}) ===")
    for lab, m in [("G1 above-SMA fill", g1), ("G2 progress", g2), ("G3 both", g3)]:
        v = stats(m["curve"], m["trades"])["s22"]
        print(f"  {lab:22s} {v:5.2f}  -> {'BEATS baseline' if v > b['s22'] else 'loses (a FINDING — R11)'}")


if __name__ == "__main__":
    main()
