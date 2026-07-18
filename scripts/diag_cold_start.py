"""COLD START — the gap the backtest never models, and whether a lower risk% buys early diversification.

The backtest's ~7-10 concurrent positions ACCUMULATED over years (as the book grew and positions
half-booked at 2R, freeing capital). Deploying fresh capital TODAY you start at 0 positions, and with
2% risk against 2.5-6% stops a single fill is 33-79% of the book — so the first weeks are far more
CONCENTRATED than the steady state on which the −34.8% drawdown was measured. That is a real,
undocumented risk.

Measured across MANY start dates (not one lucky one), for two DECLARED risk levels (R9: K=2):
  * how many positions you actually hold at week 4 / 8 / 12
  * the largest single position as a share of the book during the ramp
  * the drawdown suffered in the first 6 months
  * and the full-period cost, since risk% is a Phase-3 sizing knob (settled at 2%) — changing it
    permanently is a re-litigation, so this is reported honestly, not as a proposal.

    python scripts/diag_cold_start.py
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

RISKS = [0.01, 0.02]                       # declared K=2; 2% is the live rule
STARTS = pd.date_range("2019-01-01", "2024-07-01", freq="2QS")   # 12 cold starts, survivorship-clean era


def cold_start_profile(P, mem, start, risk):
    led = []
    m = R94.backtest(P, mem, ledger=led, start=str(start.date()), eq0=EQ0, risk_pct=risk, **P2_EXIT)
    if not led:
        return None
    d = pd.DataFrame(led)
    d["entry_date"] = pd.to_datetime(d.entry_date); d["exit_date"] = pd.to_datetime(d.exit_date)
    d["risk_frac"] = (d.entry - d.stop0) / d.entry
    d["notional_pct"] = risk / d.risk_frac * 100          # share of equity at entry
    out = {"start": start.date(), "risk": risk}
    for wk in (4, 8, 12):
        t = start + pd.Timedelta(weeks=wk)
        out[f"pos_w{wk}"] = int(((d.entry_date <= t) & (d.exit_date >= t)).sum())
    ramp = d[d.entry_date <= start + pd.Timedelta(weeks=12)]
    out["max_pos_pct"] = float(ramp.notional_pct.max()) if len(ramp) else np.nan
    out["n_ramp_trades"] = int(len(ramp))
    e = m["curve"].sort_index()
    e6 = e[e.index <= start + pd.Timedelta(days=182)]
    out["dd_first6mo"] = float((e6 / e6.cummax() - 1).min()) if len(e6) > 2 else np.nan
    r = e.pct_change().dropna()
    out["sharpe_full"] = r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    out["cagr_full"] = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    out["dd_full"] = float((e / e.cummax() - 1).min())
    return out


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    mA = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mA["sharpe"] - 1.034) < 0.005 and mA["trades"] == 168, "R1 baseline FAILED"
    print(f"R1 baseline OK (1.034 / 168). Cold starts: {len(STARTS)} dates x {len(RISKS)} risk levels\n")

    rows = []
    for risk in RISKS:
        for s in STARTS:
            p = cold_start_profile(P, mem, s, risk)
            if p:
                rows.append(p)
        print(f"  ...risk={risk*100:.0f}% done", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(ROOT / "research" / "substrate" / "cold_start_sims.csv", index=False)

    print("\n=== THE COLD-START RAMP (median across start dates) ===")
    print(f"{'risk':>5s} {'pos@wk4':>8s} {'pos@wk8':>8s} {'pos@wk12':>9s} {'max single pos':>15s} {'DD first 6mo':>13s}")
    for risk, g in d.groupby("risk"):
        print(f"{risk*100:4.0f}% {g.pos_w4.median():8.0f} {g.pos_w8.median():8.0f} {g.pos_w12.median():9.0f} "
              f"{g.max_pos_pct.median():14.0f}% {g.dd_first6mo.median()*100:12.1f}%")

    print("\n=== WHAT IT COSTS OVER THE FULL RUN (median across start dates) ===")
    print(f"{'risk':>5s} {'Sharpe':>7s} {'CAGR':>7s} {'MaxDD':>8s}")
    for risk, g in d.groupby("risk"):
        print(f"{risk*100:4.0f}% {g.sharpe_full.median():7.2f} {g.cagr_full.median()*100:6.1f}% "
              f"{g.dd_full.median()*100:7.1f}%")

    a = d[d.risk == 0.02]; b = d[d.risk == 0.01]
    print("\n=== VERDICT ===")
    print(f"  diversification at wk12: {a.pos_w12.median():.0f} names @2% -> {b.pos_w12.median():.0f} names @1%")
    print(f"  largest single position: {a.max_pos_pct.median():.0f}% @2% -> {b.max_pos_pct.median():.0f}% @1%")
    print(f"  first-6mo drawdown:      {a.dd_first6mo.median()*100:.1f}% @2% -> {b.dd_first6mo.median()*100:.1f}% @1%")
    print(f"  full-run CAGR cost:      {a.cagr_full.median()*100:.1f}% @2% -> {b.cagr_full.median()*100:.1f}% @1%")
    print(f"  full-run Sharpe:         {a.sharpe_full.median():.2f} @2% -> {b.sharpe_full.median():.2f} @1%")


if __name__ == "__main__":
    main()
