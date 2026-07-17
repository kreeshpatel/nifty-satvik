"""OWNER SPEC 2026-07-16 — 20% capital-per-name cap + a strict 60%@2R / 40%@3R exit.

Verbatim owner instruction:
    "we can put a max cap of 20 percent capital per name cap and also change the 2R sell 60%, and all 40
     as 3R. no runners and if not 3R then at 2R. like if it reaches 3R then fine if not then sell at
     44SMA levels till then wait"

Read as ONE conjunction (owner standing rule: "we need to test it combined and only trade exists if all
the requirement fulfills"):
    * position notional capped at 20% of sizing equity per name
    * 60% off at 2R (resting limit, intraweek)
    * 40% off at 3R if it gets there; if it never does, that 40% exits on the weekly close below the 44w
      SMA. No runners beyond that.
    * R capped at 5% (owner: "R of 15 percent is too much. we can max tackle R of 5")

Arms (K=3 declared): the spec; the spec without the R cap; the spec plus the three signal-side guards.
Judged on the 2022-26 CONTINUOUS SLICE (R3) vs baseline all-grades 1.29 and random null 0.74 (sd 0.24).

    python scripts/run_owner_6040_poscap.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import P2_EXIT

SCALED = dict(tp1_r=2.0, tp1_frac=0.60, tp2_r=3.0, tp2_frac=0.40)
GUARDS = dict(slope_min=0.06, prior_above_n=2, prior_above_lookback=4, require_progress=True)
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
        out.update(win=(R > 0).mean() * 100, meanR=R.mean(),
                   riskpct=np.median([(x["entry"] - x["stop0"]) / x["entry"] * 100 for x in led]))
        from collections import Counter
        out["mix"] = Counter(x.get("reason", "?") for x in led).most_common(4)
    return out


def show(lab, m):
    x = f" | win {m['win']:.0f}% meanR {m['meanR']:+.2f} medR% {m['riskpct']:.1f}" if "win" in m else ""
    print(f"  {lab:34s} tr={m['tr']:4d} Sh={m['sh']:5.2f} CAGR={m['cagr']*100:5.1f}% "
          f"DD={m['dd']*100:6.1f}% [22-26 {m['s22']:5.2f}]{x}")


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    Pg = R94.prep_weekly_rank(ohlcv, **GUARDS)

    ledb = []
    mb = R94.backtest(P, mem, ledger=ledb, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mb["sharpe"] - 1.0342) < 0.001 and mb["trades"] == 168, "R1 baseline FAILED"

    arms = [
        ("BASE (live P2 exit)", P, dict(**P2_EXIT)),
        ("SPEC 60/40 +Rcap5 +cap20", P, dict(scaled_exit=SCALED, max_risk_pct=0.05, max_notional_pct=0.20)),
        ("  ...no R cap", P, dict(scaled_exit=SCALED, max_notional_pct=0.20)),
        ("  ...+ 3 signal guards", Pg, dict(scaled_exit=SCALED, max_risk_pct=0.05, max_notional_pct=0.20)),
    ]
    print("=== OWNER SPEC (Rs10L, 2% risk target, all-grades) ===")
    res = []
    for lab, PP, kw in arms:
        led = []
        m = R94.backtest(PP, mem, ledger=led, start="2017-01-01", eq0=EQ0, **kw)
        s = stats(m["curve"], m["trades"], led); res.append((lab, s)); show(lab, s)
        print(f"       exit mix: {s['mix']}")

    print(f"\n=== VERDICT — 2022-26 continuous slice (R3); baseline {BASE_S22:.2f}, null {NULL_S22:.2f} ===")
    for lab, s in res[1:]:
        z = (s["s22"] - NULL_S22) / NULL_SD
        print(f"  {lab:34s} {s['s22']:5.2f}  vs base {s['s22']-BASE_S22:+.2f}  "
              f"({z:+.1f} sigma of null)  {'BEATS' if s['s22'] > BASE_S22 else 'LOSES'}")


if __name__ == "__main__":
    main()
