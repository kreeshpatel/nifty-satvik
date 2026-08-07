"""Deep characterisation of the survey survivor: Supertrend + Pivot Points (CA Rachana Ranade).

Published rules (SOURCED): long when close > EMA200 AND Supertrend(10,3) is green AND close crosses
above the pivot; stop = 2 x ATR(14) below the entry candle; target = 2R.

WHAT THIS IS. The 9-cell survey selected this strategy on TRAIN 2019-2023 and confirmed it once on
HOLDOUT 2024-2026. That holdout is now SPENT. Nothing here can certify the strategy; everything
here characterises it — where its money comes from, which leg carries it, whether its parameters
sit on a plateau or a spike, and where it breaks. Those are measurements, and measurements are the
only thing left that costs nothing.

TWO DISCIPLINES, held throughout:

  1. The parameter surface (Part D) is a ROBUSTNESS AUDIT, not a search. A strategy whose
     performance is flat across neighbouring parameters is robust; one with a lone spike is fitted.
     The surface is reported whole. The maximum is NOT a recommendation and is not adopted.
  2. 2016-2018 (Part A) is the ONE slice of history neither train nor holdout has touched. It is
     spent here, once, as independent evidence. CAVEAT: pre-2018 index membership is the 2018-10
     set back-extended, so this window is mildly survivorship-contaminated and reads OPTIMISTIC.
     It is a directional check, not a clean number.

MEASUREMENT class; `n_trials` stays 138.

    python scripts/diag_ranade_deepdive.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS  # noqa: E402
from diag_supertrend_system import supertrend  # noqa: E402
from diag_swing_strategy_survey import (EQ0, MAXPOS, NOTIONAL_CAP, RISK, build_base,  # noqa: E402
                                        ema, fresh, monthly_pivot)
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

EARLY = ("2016-01-01", "2018-12-31")      # untouched by train and holdout
TRAIN = ("2019-01-01", "2023-12-31")
HOLD = ("2024-01-01", "2026-06-30")
_N50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
        .set_index("date")["nifty50_close"].sort_index())


def legs(d, *, use_ema=True, use_st=True, use_pivot=True):
    _, up = supertrend(d["h"], d["l"], d["c"], 10, 3.0)
    piv = monthly_pivot(d["idx"], d["h"], d["l"], d["c"])
    pc = np.concatenate([[np.nan], d["c"][:-1]])
    pp = np.concatenate([[np.nan], piv[:-1]])
    cross = np.nan_to_num((d["c"] > piv) & (pc <= pp), nan=False)
    ok = np.ones(len(d["c"]), bool)
    if use_st:
        ok &= up
    if use_ema:
        ok &= d["c"] > ema(d["c"], 200)
    if use_pivot:
        ok &= cross
    return fresh(ok)


def engine(P, *, start, end, atr_mult=2.0, target_r=2.0, cost=0.0025,
           use_ema=True, use_st=True, use_pivot=True, adv_band=None):
    """Same book as the survey. Returns (metrics, per-trade ledger with MFE/MAE in R)."""
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    cands = {}
    for tkr, d in P.items():
        sig = legs(d, use_ema=use_ema, use_st=use_st, use_pivot=use_pivot) & d["mem"]
        for i in np.flatnonzero(sig):
            if i + 1 >= len(d["c"]) or not np.isfinite(d["rs55"][i]):
                continue
            dt = d["idx"][i]
            if lo <= dt <= hi:
                cands.setdefault(dt, []).append((float(d["rs55"][i]), tkr, int(i)))

    dates = [x for x in sorted(set().union(*[set(d["idx"]) for d in P.values()])) if lo <= x <= hi]
    cash = equity = EQ0
    open_pos, eqc, trades = {}, [], []
    prev = None
    for dt in dates:
        for tkr in list(open_pos):
            p, d = open_pos[tkr], P[tkr]
            i = d["pos"].get(dt)
            if i is None:
                continue
            p["held"] += 1
            p["mfe"] = max(p["mfe"], (d["h"][i] - p["entry"]) / p["r_unit"])
            p["mae"] = min(p["mae"], (d["l"][i] - p["entry"]) / p["r_unit"])
            px = why = None
            if d["l"][i] <= p["stop"]:
                px, why = min(d["o"][i], p["stop"]), "stop"
            elif d["h"][i] >= p["target"]:
                px, why = max(d["o"][i], p["target"]), "target"
            elif p["held"] >= 252:
                px, why = d["c"][i], "maxhold"
            if px is not None:
                cash += p["shares"] * px * (1 - cost)
                trades.append(dict(ticker=tkr, entry_date=p["date"], exit_date=dt, why=why,
                                   r=(px - p["entry"]) / p["r_unit"], mfe=p["mfe"], mae=p["mae"],
                                   held=p["held"], adv=p["adv"], stop_pct=p["stop_pct"],
                                   equity_pnl=p["shares"] * (px * (1 - cost) - p["entry"] * (1 + cost)),
                                   ret=(px * (1 - cost) - p["entry"] * (1 + cost)) / p["entry"]))
                del open_pos[tkr]

        for _s, tkr, i in sorted(cands.get(prev, []), reverse=True) if prev else []:
            if len(open_pos) >= MAXPOS or tkr in open_pos:
                continue
            d = P[tkr]
            j = d["pos"].get(dt)
            if j is None or j != i + 1:
                continue
            adv = d["c"][i] * d["vma"][i] if np.isfinite(d["vma"][i]) else np.nan
            if adv_band is not None and (not np.isfinite(adv) or not adv_band[0] <= adv < adv_band[1]):
                continue
            entry = d["o"][j]
            s0 = d["c"][i] - atr_mult * d["atr"][i]
            if not np.isfinite(entry) or not np.isfinite(s0) or entry <= s0:
                continue
            sh = min(equity * RISK / (entry - s0), equity * NOTIONAL_CAP / entry)
            if sh <= 0 or sh * entry * (1 + cost) > cash:
                continue
            cash -= sh * entry * (1 + cost)
            open_pos[tkr] = dict(entry=entry, stop=s0, r_unit=entry - s0, shares=sh, held=0,
                                 target=entry + target_r * (entry - s0), date=dt, mfe=0.0, mae=0.0,
                                 adv=adv, stop_pct=(entry - s0) / entry)

        equity = cash + sum(p["shares"] * (P[t]["c"][P[t]["pos"][dt]] if dt in P[t]["pos"] else p["entry"])
                            for t, p in open_pos.items())
        eqc.append((dt, equity))
        prev = dt

    eq = pd.Series(dict(eqc)).sort_index()
    ret = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    t = pd.DataFrame(trades)
    m = dict(cagr=(eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan,
             sharpe=ret.mean() / ret.std() * np.sqrt(252) if ret.std() else np.nan,
             dd=(eq / eq.cummax() - 1).min(), n=len(t),
             win=(t["r"] > 0).mean() if len(t) else np.nan,
             meanR=t["r"].mean() if len(t) else np.nan, eq=eq)
    return m, t


def show(tag, m):
    print(f"  {tag:<34} CAGR {m['cagr']*100:>7.2f}%  Sh {m['sharpe']:>6.3f}  DD {m['dd']*100:>6.1f}%  "
          f"n {m['n']:>5,}  win {m['win']*100:>4.1f}%  R {m['meanR']:>+5.2f}")


def main() -> int:
    print("=== DEEP DIVE — Supertrend + Pivot Points (CA Rachana Ranade) ===\n")
    P = build_base(corrected_universe(), load_membership())
    print(f"  names {len(P)}\n")

    # ---------------------------------------------------------------- A. three windows
    print("=== A. THREE WINDOWS (2016-18 is the one slice never used for anything) ===")
    wins = {}
    for tag, (s, e) in (("2016-2018  UNTOUCHED*", EARLY), ("2019-2023  train", TRAIN),
                        ("2024-2026  holdout(spent)", HOLD)):
        m, t = engine(P, start=s, end=e)
        wins[tag] = (m, t)
        show(tag, m)
    print("  * pre-2018 membership is back-extended -> mildly survivorship-contaminated, reads OPTIMISTIC")

    full, ft = engine(P, start="2016-01-01", end="2026-06-30")
    show("FULL 2016-2026 (continuous)", full)
    print("\n  per-year net return, continuous run:")
    yr = full["eq"].resample("YE").last()
    yr = pd.concat([pd.Series([full["eq"].iloc[0]], index=[full["eq"].index[0]]), yr])
    for a, b in zip(yr.index[:-1], yr.index[1:]):
        v = (yr[b] / yr[a] - 1) * 100
        print(f"    {b.year}  {v:>+7.2f}%   {'#' * max(int(abs(v) / 2), 0)}")

    # ---------------------------------------------------------------- B. trade anatomy
    print("\n=== B. TRADE ANATOMY (continuous 2016-2026, n={:,}) ===".format(len(ft)))
    r = ft["r"].to_numpy()
    print(f"  exit mix: " + "  ".join(f"{k} {v*100:.0f}%" for k, v in
                                      ft['why'].value_counts(normalize=True).items()))
    print(f"  R:  p10 {np.percentile(r,10):+.2f}  p25 {np.percentile(r,25):+.2f}  "
          f"med {np.median(r):+.2f}  p75 {np.percentile(r,75):+.2f}  p90 {np.percentile(r,90):+.2f}  "
          f"max {r.max():+.1f}")
    print(f"  median stop width {ft['stop_pct'].median()*100:.1f}%   median hold {ft['held'].median():.0f}d")
    pnl = ft["equity_pnl"].to_numpy()
    order = np.argsort(-pnl)
    tot = pnl.sum()
    for k in (5, 10, 25):
        share = pnl[order[:k]].sum() / tot * 100 if tot else np.nan
        print(f"  top {k:>2} trades carry {share:>6.1f}% of total P&L")
    print(f"  CONCENTRATION CHECK: {(pnl>0).sum():,} winners fund {(pnl<=0).sum():,} losers")

    print("\n  MFE / MAE (in R) — is the 2R target and 2xATR stop well placed?")
    print(f"    MFE of ALL trades:      med {ft['mfe'].median():+.2f}  p75 {ft['mfe'].quantile(.75):+.2f}  "
          f"p90 {ft['mfe'].quantile(.90):+.2f}")
    tg = ft[ft["why"] == "target"]
    print(f"    MFE of TARGET exits:    med {tg['mfe'].median():+.2f}  p90 {tg['mfe'].quantile(.90):+.2f}  "
          f"(how much ran past +2R after we sold)")
    st = ft[ft["why"] == "stop"]
    print(f"    MFE of STOPPED trades:  med {st['mfe'].median():+.2f}  p75 {st['mfe'].quantile(.75):+.2f}  "
          f"(how far they went our way first)")
    print(f"    MAE of WINNERS:         med {ft[ft['r']>0]['mae'].median():+.2f}  "
          f"p10 {ft[ft['r']>0]['mae'].quantile(.10):+.2f}  (how much heat winners took)")

    # ---------------------------------------------------------------- C. leg decomposition
    print("\n=== C. WHICH LEG CARRIES IT? (leave-one-out) ===")
    for tag, kw in (("all three legs", {}), ("drop EMA200 filter", dict(use_ema=False)),
                    ("drop Supertrend", dict(use_st=False)), ("drop pivot cross", dict(use_pivot=False))):
        mt, _ = engine(P, start=TRAIN[0], end=TRAIN[1], **kw)
        me, _ = engine(P, start=EARLY[0], end=EARLY[1], **kw)
        print(f"  {tag:<22} train CAGR {mt['cagr']*100:>7.2f}% (n {mt['n']:>5,})   "
              f"2016-18 CAGR {me['cagr']*100:>7.2f}% (n {me['n']:>5,})")

    # ---------------------------------------------------------------- D. robustness surface
    print("\n=== D. PARAMETER ROBUSTNESS AUDIT (train only) — plateau or spike? ===")
    print("    NOT a search. The maximum is not adopted and is not a recommendation.")
    print(f"    {'':>10}" + "".join(f"{f'tgt {t}R':>12}" for t in (1.5, 2.0, 3.0)))
    for am in (1.5, 2.0, 2.5, 3.0):
        cells = []
        for tr_ in (1.5, 2.0, 3.0):
            m, _ = engine(P, start=TRAIN[0], end=TRAIN[1], atr_mult=am, target_r=tr_)
            cells.append(f"{m['cagr']*100:>11.2f}%")
        print(f"    ATR x{am:<4}" + "".join(cells))

    # ---------------------------------------------------------------- E. cost sensitivity
    print("\n=== E. COST SENSITIVITY (train) — how much edge is above the friction floor? ===")
    for c in (0.0005, 0.0015, 0.0025, 0.0040):
        m, _ = engine(P, start=TRAIN[0], end=TRAIN[1], cost=c)
        print(f"    {c*100:.2f}%/leg   CAGR {m['cagr']*100:>7.2f}%   Sharpe {m['sharpe']:>6.3f}")

    # ---------------------------------------------------------------- F. capacity
    print("\n=== F. CAPACITY — does it need small illiquid names? (train, ADV bands in Rs cr) ===")
    for lo_cr, hi_cr in ((0, 10), (10, 50), (50, 1e9)):
        m, _ = engine(P, start=TRAIN[0], end=TRAIN[1], adv_band=(lo_cr * 1e7, hi_cr * 1e7))
        lbl = f"ADV {lo_cr}-{hi_cr if hi_cr < 1e8 else '+'} cr"
        print(f"    {lbl:<16} CAGR {m['cagr']*100:>7.2f}%  n {m['n']:>5,}  R {m['meanR']:>+5.2f}")

    ft.to_csv(ROOT / "diagnostics" / "research" / "ranade_trades_2016_2026.csv", index=False)
    print("\n  ledger -> diagnostics/research/ranade_trades_2016_2026.csv")
    print("  standing counts: screens 17 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
