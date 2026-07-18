"""Can CRS's WITHIN-BUCKET skill be kept while re-allocating toward the BETTER buckets?

The dissection found a paradox: CRS puts 64% of picks in the >15% bucket (pool mean +0.31R) while nearly
ignoring 0-5% (pool mean +0.58R) — it allocates to the WORSE pool and wins anyway via within-bucket skill
(+0.228R/trade). This asks whether the allocation can be fixed without losing the skill.

Two DECLARED variants (R9: K=2, fixed before running — not a search):
  H1 stratified-CRS : rank by CRS PERCENTILE WITHIN the candidate's own extension bucket. Neutralises
                      the extension tilt, keeps within-bucket skill. No fitted prior.
  H2 bucket-prior   : allocate to the better buckets first (prior = pool meanR by bucket computed on
                      2019-21 ONLY -> OOS-honest for the 2022-26 gate), tie-broken by within-bucket CRS.

Note: the crude ancestors of this idea (`near_sma` fill-order, `ext_cap`) were REJECTED — but neither was
tested against a NULL, which is the instrument we now have. Baseline 22-26 = 1.29; random null = 0.74.

    python scripts/diag_crs_stratified.py
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

BINS = [-100, 0, 5, 10, 15, 100]
LAB = ["<0%", "0-5%", "5-10%", "10-15%", ">15%"]
NULL_S22 = 0.74   # random-selection null mean on the 22-26 slice (MONTECARLO_null.md)


def stats(curve, trades=None):
    e = curve.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]
    return dict(sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan,
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                dd=(e / e.cummax() - 1).min(),
                s22=rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan, trades=trades)


def show(lab, m):
    print(f"  {lab:34s} tr={m['trades']:4d} Sh={m['sharpe']:5.2f} CAGR={m['cagr']*100:5.1f}% "
          f"DD={m['dd']*100:6.1f}% 22-26={m['s22']:5.2f}")


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)

    # per-window: signal-week extension bucket + raw CRS (both PIT-safe, from the completed signal week)
    wp = load_weekly_panel(cache=True)
    fm = {(r.ticker, r.week_end): (r.c, r.sma44) for r in wp.itertuples()}
    rows = []
    for t, s in P.items():
        dates = pd.DatetimeIndex(s["dates"])
        for e0, w in s["entry_win"].items():
            if e0 < 1:
                continue
            f = fm.get((t, dates[e0 - 1]))
            if not f or not f[1] or f[1] != f[1] or f[1] <= 0:
                continue
            rows.append(dict(t=t, e0=e0, ext=(f[0] / f[1] - 1) * 100, crs=float(w[3])))
    W = pd.DataFrame(rows)
    W["b"] = pd.cut(W.ext, bins=BINS, labels=LAB)
    # H1: CRS percentile WITHIN the candidate's own bucket
    W["crs_pct_in_b"] = W.groupby("b", observed=True)["crs"].rank(pct=True)

    # H2 prior: pool meanR by bucket from the TRAIN slice only (2019-21) -> OOS-honest for 22-26
    sub = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    tr = sub[(sub.setup == "touch44") & (sub.entry_date >= "2019-01-01") & (sub.entry_date <= "2021-12-31")].copy()
    tr["b"] = pd.cut(tr.ext_vs_sma, bins=BINS, labels=LAB)
    prior = tr.groupby("b", observed=True)["R"].mean()
    print("H2 bucket prior (train 2019-21 pool meanR):")
    print("  " + "  ".join(f"{b}={prior.get(b, float('nan')):+.2f}" for b in LAB))
    order = {b: i for i, b in enumerate(prior.sort_values(ascending=False).index)}   # 0 = best bucket
    W["prior_rank"] = W["b"].map(order).astype(float)

    # ---- baseline ----
    mA = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mA["sharpe"] - 1.034) < 0.005 and mA["trades"] == 168, "R1 baseline FAILED"
    print(f"\n=== capped Rs10L book (baseline 22-26 = 1.29; random null = {NULL_S22}) ===")
    show("A  CRS-rank (LIVE baseline)", stats(mA["curve"], mA["trades"]))

    # ---- H1: stratified CRS ----
    conv1 = {(r.t, r.e0): float(r.crs_pct_in_b) for r in W.itertuples() if r.crs_pct_in_b == r.crs_pct_in_b}
    m1 = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, fill_order="conviction", conv_score=conv1, **P2_EXIT)
    show("H1 stratified-CRS (tilt stripped)", stats(m1["curve"], m1["trades"]))

    # ---- H2: bucket-prior first, within-bucket CRS as tie-break ----
    conv2 = {(r.t, r.e0): float(-r.prior_rank * 10 + r.crs_pct_in_b)
             for r in W.itertuples() if r.prior_rank == r.prior_rank and r.crs_pct_in_b == r.crs_pct_in_b}
    m2 = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, fill_order="conviction", conv_score=conv2, **P2_EXIT)
    show("H2 bucket-prior + CRS tiebreak", stats(m2["curve"], m2["trades"]))

    print("\n  vs baseline 1.29 / null 0.74 on the 22-26 gate:")
    for lab, m in [("H1", m1), ("H2", m2)]:
        v = stats(m["curve"])["s22"]
        print(f"    {lab}: {v:.2f}  -> {'BEATS baseline' if v > 1.29 else ('beats null but LOSES to baseline' if v > NULL_S22 else 'below the RANDOM null')}")


if __name__ == "__main__":
    main()
