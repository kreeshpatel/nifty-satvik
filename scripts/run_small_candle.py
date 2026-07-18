"""THE PRE-REGISTERED RUN — small-candle selection + 60/30/10 exit.

Frozen in research/preregistry_small_candle.md BEFORE this run. No retuning (R4/R11).

    max_ctl_pct=0.05 (signal (close-low)/close <= 5% => R <= 5% by construction)
    min_body_frac=0.50 ("solid green" — body >= half the range)
    NO position cap · NO R cap · scaled_exit 60%@2R / 30%@3R / residual 10% runs to the 44w SMA

Judged on the 2022-26 continuous slice (R3). Baseline all-grades 1.29 · null 0.74 (sd 0.24).

    python scripts/run_small_candle.py
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import P2_EXIT

CANDLE = dict(max_ctl_pct=0.05, min_body_frac=0.50)
GUARDS = dict(slope_min=0.06, prior_above_n=2, prior_above_lookback=4, require_progress=True)
SCALED = dict(scaled_exit=dict(tp1_r=2.0, tp1_frac=0.60, tp2_r=3.0, tp2_frac=0.30))
BASE_S22, NULL_S22, NULL_SD = 1.29, 0.74, 0.24


def stats(c, tr, led=None):
    e = c.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]
    dd = (e / e.cummax() - 1).min(); cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    out = dict(sh=r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan, cagr=cagr, dd=dd,
               s22=rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan, tr=tr)
    if led:
        R = np.array([x["R"] for x in led])
        rp = float(np.median([(x["entry"] - x["stop0"]) / x["entry"] * 100 for x in led]))
        out.update(win=(R > 0).mean() * 100, meanR=R.mean(), riskpct=rp,
                   move=R.mean() * rp,                      # meanR x R% = actual move captured
                   notional=2.0 / rp * 100,                 # 2% risk / R% = % of equity per name
                   mix=Counter(x.get("reason", "?") for x in led).most_common(4))
    return out


def show(lab, m):
    print(f"  {lab:32s} tr={m['tr']:4d} Sh={m['sh']:5.2f} CAGR={m['cagr']*100:5.1f}% DD={m['dd']*100:6.1f}% "
          f"[22-26 {m['s22']:5.2f}] | win {m['win']:.0f}% meanR {m['meanR']:+.2f} medR% {m['riskpct']:4.1f} "
          f"move {m['move']:+5.1f}% notional/name {m['notional']:4.0f}%")
    print(f"       exit mix: {m['mix']}")


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    Pc = R94.prep_weekly_rank(ohlcv, **CANDLE)
    Pcg = R94.prep_weekly_rank(ohlcv, **CANDLE, **GUARDS)

    n0 = sum(len(s["entry_win"]) for s in P.values())
    nc = sum(len(s["entry_win"]) for s in Pc.values())
    print(f"=== pool: {n0} windows -> {nc} ({nc/n0*100:.1f}%) after candle<=5% AND body>=50% ===\n")

    ledb = []
    mb = R94.backtest(P, mem, ledger=ledb, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mb["sharpe"] - 1.0342) < 0.001 and mb["trades"] == 168, "R1 baseline FAILED"

    arms = [("BASE (live P2 exit)", P, dict(**P2_EXIT)),
            ("SPEC candle + 60/30/10", Pc, dict(**SCALED)),
            ("  candle + live P2 exit", Pc, dict(**P2_EXIT)),
            ("  SPEC + 3 signal guards", Pcg, dict(**SCALED))]
    print("=== SMALL-CANDLE SPEC (Rs10L, 2% risk, all-grades, NO caps) ===")
    res = []
    for lab, PP, kw in arms:
        led = []
        m = R94.backtest(PP, mem, ledger=led, start="2017-01-01", eq0=EQ0, **kw)
        s = stats(m["curve"], m["trades"], led); res.append((lab, s)); show(lab, s)

    print(f"\n=== VERDICT — 2022-26 continuous slice (R3); baseline {BASE_S22:.2f}, null {NULL_S22:.2f} ===")
    for lab, s in res[1:]:
        z = (s["s22"] - NULL_S22) / NULL_SD
        print(f"  {lab:32s} {s['s22']:5.2f}  vs base {s['s22']-BASE_S22:+.2f}  ({z:+.1f} sigma of null)  "
              f"{'BEATS' if s['s22'] > BASE_S22 else 'LOSES'}")


if __name__ == "__main__":
    main()
