"""Stage-4 — SIZING SLEEVES: does the zoo's per-trade edge survive the capital cap?

Stage 1 showed the setup families (cup/double-bottom/ascending-base) win per-trade; the registry's
iron law is that adding them to ONE shared 15-slot book dilutes it (they cannibalise capital). The
hypothesis: give each family its OWN capital sleeve so they diversify, not compete.

Faithful to the engine of record: it reuses `backtest()` (the capped Rs10L book, CRS-ranked fills, P2
exit). A "sleeve" = the same engine run on a copy of P whose entry windows are FILTERED to one setup
family, with its own capital budget. Sleeve equity curves are summed. No frozen code is edited.

Compares, all under the live P2 exit, continuous-slice sub-periods (never fresh-capital):
  A touch-only Rs10L (baseline)      B all-setups SHARED Rs10L (dilution)
  C sleeves Rs10L split (6 families)  D sleeves Rs10L split (touch+cup+double_bottom)

    python scripts/diag_sleeves.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_weekly_rank as R94  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_faithful import EQ0  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

P2_EXIT = dict(no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)
NAMES = {0: "touch44", 1: "box", 2: "trend_pullback", 3: "sr_pivot",
         6: "cup_handle", 7: "ascending_base", 8: "double_bottom"}


def filter_P(P, origins):
    """A shallow copy of P whose entry_win is restricted to the given origin set (heavy arrays shared)."""
    keep = set(origins)
    out = {}
    for t, s in P.items():
        s2 = dict(s)
        s2["entry_win"] = {k: v for k, v in s["entry_win"].items() if v[5] in keep}
        out[t] = s2
    return out


def curve_of(P, mem, origins, eq0):
    Pf = filter_P(P, origins)
    m = R94.backtest(Pf, mem, start="2017-01-01", eq0=eq0, **P2_EXIT)
    return m["curve"], m["trades"]


def metrics(curve, label, trades=None):
    e = curve.sort_index()
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan")
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    dd = (e / e.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd else float("nan")

    def slice_sharpe(a, b):
        rr = r[(r.index >= a) & (r.index < b)]
        return rr.mean() / rr.std() * np.sqrt(252) if len(rr) > 5 and rr.std() else float("nan")
    s1 = slice_sharpe("2017-01-01", "2022-01-01")
    s2 = slice_sharpe("2022-01-01", "2027-01-01")
    tr = f"{trades:4d}" if trades is not None else "   -"
    print(f"{label:34s} tr={tr}  Sharpe={sharpe:5.2f}  CAGR={cagr*100:5.1f}%  MaxDD={dd*100:6.1f}%  "
          f"Calmar={calmar:4.2f}  [17-21 {s1:4.2f} | 22-26 {s2:4.2f}]")
    return dict(sharpe=sharpe, cagr=cagr, dd=dd, calmar=calmar)


def combine(curves):
    """Sum independent sleeve equity curves on the union of dates (ffill between a sleeve's marks)."""
    idx = sorted(set().union(*[set(c.index) for c in curves]))
    tot = None
    for c in curves:
        s = c.reindex(idx).ffill().bfill()
        tot = s if tot is None else tot + s
    return tot


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv, box_breakout=True, trend_pullback=True, sr_pivot=True,
                             zoo_origins=(6, 7, 8))   # skip vcp/flag (4,5): too rare to size
    print("built wide prep; running sleeve experiments (P2 exit, Rs10L total)\n")

    # A — baseline touch-only, full Rs10L
    cA, tA = curve_of(P, mem, [0], EQ0)
    metrics(cA, "A  touch-only Rs10L (baseline)", tA)

    # B — all setups, SHARED Rs10L cap (the dilution case)
    allo = [0, 1, 2, 3, 6, 7, 8]
    cB, tB = curve_of(P, mem, allo, EQ0)
    metrics(cB, "B  all-setups SHARED Rs10L", tB)

    # C — sleeves: Rs10L split equally across 6 families (drop thin sr_pivot from sleeves)
    fam_c = [0, 1, 2, 6, 7, 8]
    per = EQ0 / len(fam_c)
    cs, ts = [], 0
    for f in fam_c:
        c, t = curve_of(P, mem, [f], per); cs.append(c); ts += t
    metrics(combine(cs), f"C  sleeves Rs10L/{len(fam_c)} (6 families)", ts)

    # D — concentrated sleeves: touch + cup + double_bottom (the high-N per-trade winners)
    fam_d = [0, 6, 8]
    per = EQ0 / len(fam_d)
    cs, ts = [], 0
    for f in fam_d:
        c, t = curve_of(P, mem, [f], per); cs.append(c); ts += t
    metrics(combine(cs), f"D  sleeves Rs10L/{len(fam_d)} (touch+cup+dblbottom)", ts)

    # per-family standalone (each on full Rs10L) — the raw sleeve quality
    print("\n  per-family standalone (each Rs10L, for reference):")
    for f in fam_c:
        c, t = curve_of(P, mem, [f], EQ0)
        metrics(c, f"   {NAMES[f]}", t)


if __name__ == "__main__":
    main()
