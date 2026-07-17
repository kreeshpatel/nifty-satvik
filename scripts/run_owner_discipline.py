"""THE PRE-REGISTERED RUN — the owner's discipline config.

Frozen in research/preregistry_owner_discipline.md BEFORE this run. n_trials 115->116. No retuning (R4).

    ext_cap=0.20        skip any fill priced >20% above the signal-week 44w SMA (rule-faithful SELECTION;
                        the stop stays the candle low)
    max_risk_pct=0.10   stop = max(signal-week low, entry x 0.90) — R capped at 10%
    max_notional_pct=0.20   no name exceeds 20% of sizing equity (contains the R cap's concentration)
    live P2 exit, 2% risk, all-grades

A RISK-APPETITE config, not an edge hunt. The owner pre-accepted a return cost. Reference points:
baseline all-grades 1.29 · random null 0.74 (sd 0.24). Reported, NOT pass/fail.

    python scripts/run_owner_discipline.py
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

SPEC = dict(ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20)
BASE_S22, NULL_S22, NULL_SD = 1.29, 0.74, 0.24


def stats(c, tr, led):
    e = c.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]
    dd = (e / e.cummax() - 1).min(); cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    R = np.array([x["R"] for x in led])
    rp = float(np.median([(x["entry"] - x["stop0"]) / x["entry"] * 100 for x in led]))
    held = np.array([x.get("held_weeks", np.nan) for x in led], float)
    return dict(sh=r.mean() / r.std() * np.sqrt(252), cagr=cagr, dd=dd,
                s22=rr.mean() / rr.std() * np.sqrt(252), tr=tr,
                win=(R > 0).mean() * 100, meanR=R.mean(), riskpct=rp, move=R.mean() * rp,
                notional=2.0 / rp * 100, hold_mean=np.nanmean(held), hold_med=np.nanmedian(held),
                mix=Counter(x.get("reason", "?") for x in led).most_common(5))


def show(lab, m):
    print(f"  {lab:26s} tr={m['tr']:4d} Sh={m['sh']:5.2f} CAGR={m['cagr']*100:5.1f}% DD={m['dd']*100:6.1f}% "
          f"[22-26 {m['s22']:5.2f}]")
    print(f"       win {m['win']:.0f}%  meanR {m['meanR']:+.2f}  medR% {m['riskpct']:4.1f}  "
          f"move {m['move']:+5.1f}%  notional/name {m['notional']:4.0f}%  "
          f"hold {m['hold_mean']:.1f}wk mean / {m['hold_med']:.0f}wk med")
    print(f"       exit mix: {m['mix']}")


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)

    ledb = []
    mb = R94.backtest(P, mem, ledger=ledb, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mb["sharpe"] - 1.0342) < 0.001 and mb["trades"] == 168, "R1 baseline FAILED"

    leds = []
    ms = R94.backtest(P, mem, ledger=leds, start="2017-01-01", eq0=EQ0, **SPEC, **P2_EXIT)

    print("=== OWNER DISCIPLINE CONFIG (Rs10L, 2% risk, all-grades, live P2 exit) ===")
    b = stats(mb["curve"], mb["trades"], ledb); s = stats(ms["curve"], ms["trades"], leds)
    show("BASE (live)", b)
    show("SPEC ext20+R10+pos20", s)

    print(f"\n=== THE COST/BENEFIT TABLE — the owner's decision ===")
    rows = [("Sharpe (full)", b["sh"], s["sh"], "higher better"),
            ("2022-26 slice", b["s22"], s["s22"], "higher better"),
            ("CAGR %", b["cagr"] * 100, s["cagr"] * 100, "higher better"),
            ("MaxDD %", b["dd"] * 100, s["dd"] * 100, "less negative better"),
            ("trades", b["tr"], s["tr"], ""),
            ("median R %", b["riskpct"], s["riskpct"], "owner wants <=10"),
            ("notional/name %", b["notional"], s["notional"], "lower = less concentrated"),
            ("mean hold (wk)", b["hold_mean"], s["hold_mean"], "owner wants shorter"),
            ("move captured %", b["move"], s["move"], "higher better")]
    print(f"  {'metric':18s} {'BASE':>9s} {'SPEC':>9s}  {'delta':>9s}   note")
    for lab, x, y, note in rows:
        print(f"  {lab:18s} {x:9.2f} {y:9.2f}  {y-x:+9.2f}   {note}")

    z = (s["s22"] - NULL_S22) / NULL_SD
    print(f"\n  reference: baseline 22-26 {BASE_S22:.2f} · random null {NULL_S22:.2f} (sd {NULL_SD:.2f})"
          f" -> SPEC is {z:+.1f} sigma of the null")
    print("  NOT a pass/fail gate — the owner pre-accepted a return cost. This is the price tag.")


if __name__ == "__main__":
    main()
