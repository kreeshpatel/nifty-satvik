"""0094-RF — the OWNER RULE-FAITHFUL variant. THE pre-registered run (research/preregistry_owner_variant.md).

Frozen by the owner BEFORE this run; no retuning under any outcome (R4/R11).

    slope_min=0.06 · prior_above_n=2/lookback=4 · require_progress=True
    entry_mode="buystop" · stop_atr_mult=1.0 · ext_floor=0.0 · P2 exit · 2% risk · all-grades

Gates: 2022-26 continuous slice (R3). Baseline all-grades 1.29 · A-only 1.17 · random null 0.74 (sigma 0.24).

    python scripts/run_0094rf.py
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

# ---- THE FROZEN SPEC ----
PREP = dict(slope_min=0.06, prior_above_n=2, prior_above_lookback=4, require_progress=True)
FILL = dict(entry_mode="buystop", stop_atr_mult=1.0, ext_floor=0.0)
BASE_S22, AONLY_S22, NULL_S22, NULL_SD = 1.29, 1.17, 0.74, 0.24


def stats(c, tr, led=None):
    e = c.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]; r1 = r[r.index < "2022-01-01"]
    dd = (e / e.cummax() - 1).min(); cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    out = dict(sh=r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan, cagr=cagr, dd=dd,
               calmar=cagr / abs(dd) if dd else np.nan,
               s17=r1.mean() / r1.std() * np.sqrt(252) if r1.std() else np.nan,
               s22=rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan, tr=tr)
    if led:
        R = np.array([x["R"] for x in led])
        out.update(win=(R > 0).mean() * 100, meanR=R.mean(),
                   riskpct=np.median([(x["entry"] - x["stop0"]) / x["entry"] * 100 for x in led]))
    return out


def show(lab, m):
    extra = ""
    if "win" in m:
        extra = f" | win {m['win']:.0f}% meanR {m['meanR']:+.3f} med-risk {m['riskpct']:.1f}%"
    print(f"  {lab:30s} tr={m['tr']:4d} Sh={m['sh']:5.2f} CAGR={m['cagr']*100:5.1f}% DD={m['dd']*100:6.1f}% "
          f"Calmar={m['calmar']:4.2f} [17-21 {m['s17']:5.2f} | 22-26 {m['s22']:5.2f}]{extra}")


def main():
    ohlcv = corrected_universe(); mem = load_membership()

    # R1 baseline assertion (must hold before we trust anything)
    Pb = R94.prep_weekly_rank(ohlcv)
    ledb = []
    mb = R94.backtest(Pb, mem, ledger=ledb, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mb["sharpe"] - 1.034) < 0.005 and mb["trades"] == 168, "R1 baseline FAILED"
    nb = sum(len(s["entry_win"]) for s in Pb.values())

    # THE FROZEN RUN
    Pr = R94.prep_weekly_rank(ohlcv, **PREP)
    nr = sum(len(s["entry_win"]) for s in Pr.values())
    ledr = []
    mr = R94.backtest(Pr, mem, ledger=ledr, start="2017-01-01", eq0=EQ0, **FILL, **P2_EXIT)

    print(f"=== signal pool: {nb} windows -> {nr} ({nr/nb*100:.0f}%) after the 3 signal-side guards ===\n")
    print("=== 0094-RF — THE PRE-REGISTERED RUN (Rs10L, 2% risk, P2 exit, all-grades) ===")
    show("BASE (live rule)", stats(mb["curve"], mb["trades"], ledb))
    show("0094-RF (frozen spec)", stats(mr["curve"], mr["trades"], ledr))

    s = stats(mr["curve"], mr["trades"], ledr)
    z = (s["s22"] - NULL_S22) / NULL_SD
    print(f"\n=== VERDICT — 2022-26 continuous slice (R3) ===")
    print(f"  0094-RF   {s['s22']:.2f}")
    print(f"  vs BASE   {BASE_S22:.2f}   -> {s['s22']-BASE_S22:+.2f}  {'BEATS' if s['s22']>BASE_S22 else 'LOSES'}")
    print(f"  vs A-only {AONLY_S22:.2f}   -> {s['s22']-AONLY_S22:+.2f}")
    print(f"  vs NULL   {NULL_S22:.2f}   -> {s['s22']-NULL_S22:+.2f}  ({z:+.1f} sigma of the random-selection null)")
    print(f"\n  NOTE: the null (0.74/sd 0.24) was measured on the ORIGINAL 8,518-window pool; 0094-RF trades a")
    print(f"        different pool, so it is a reference point, not an exact null for this spec.")
    if s["tr"] < 60:
        print(f"  !! trade count {s['tr']} is very low — the pre-reg flagged this as itself a finding.")


if __name__ == "__main__":
    main()
