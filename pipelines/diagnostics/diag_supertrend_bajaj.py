"""The RESEARCHED Vivek Bajaj spec vs the spec as pasted — an attribution grid.

Finding 0132 tested the rules exactly as the owner pasted them (Supertrend 10,3 green + "RS of
Nifty > 0" read as CRS length 14 + RSI(14) > 60; exit = any two of the three negated). Web sources
for the original strategy state materially different parameters:

  RS is **RS55** — 55-bar outperformance vs Nifty, zero-centred ("55 is almost 3 month live market
      and a Fibonacci number"), NOT a 14-period CRS
  RSI threshold is **50**, not 60
  the EXIT uses **RS21** on the daily, a different period from the entry's RS55
  the real trigger is a **mother-daughter multi-timeframe**: daily = filter, **2-hourly = trigger**,
      with exit "RS21<0 (Daily), RSI<50, RS55<0 (2 Hour), or Supertrend changed to sell"

The 2-hourly leg is DATA-BLOCKED here — this repo holds daily bars only, so the daughter timeframe
cannot be reproduced at all. What can be tested is the daily reduction with the correct parameters,
which is what this script does, plus an attribution grid isolating which parameter carries the
difference.

RS55 is implemented as the growth-factor ratio:  (C_t / C_{t-55}) / (I_t / I_{t-55}) - 1, so
RS55 > 0 is exactly "the stock outperformed the index over the last 55 bars" — the stated
interpretation. (The looser phrasing "stock % performance divided by benchmark % performance" is
ill-defined when the index return is negative or near zero; the growth-factor form is the one that
matches the zero-line semantics every source describes.)

PRE-DECLARED, before running: four configurations, fixed below, no sweeps. NONE of them is a
promote candidate — 0132 is already NO TRIAL, and this exists to answer "is the pasted spec even
the real strategy", not to select a winner. Promoting anything here needs its own pre-registration.
MEASUREMENT class; `n_trials` stays 138.

    python scripts/diag_supertrend_bajaj.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS  # noqa: E402
from diag_supertrend_portfolio import MIN_BARS, line, run_portfolio  # noqa: E402
from diag_supertrend_system import supertrend, wilder_rsi  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402


def rs_outperf(c: np.ndarray, idx_close: np.ndarray, n: int) -> np.ndarray:
    """RS-n: (C_t/C_{t-n}) / (I_t/I_{t-n}) - 1.  >0 == outperformed the index over n bars."""
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    with np.errstate(divide="ignore", invalid="ignore"):
        stock = c[n:] / c[:-n]
        bench = idx_close[n:] / idx_close[:-n]
        out[n:] = stock / np.where(bench > 0, bench, np.nan) - 1.0
    return out


def crs_dist(c: np.ndarray, idx_close: np.ndarray, n: int) -> np.ndarray:
    """The house CRS form used in finding 0132: RS/SMA(RS,n) - 1, RS = close/index."""
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(idx_close > 0, c / idx_close, np.nan)
        return rs / pd.Series(rs).rolling(n).mean().to_numpy() - 1.0


def build(ohlcv: dict, membership, *, rs_kind: str, rs_len: int, rsi_thr: float,
          exit_kind: str, exit_rs_len: int = 21, swing_high: int = 0,
          regime_200dma: bool = False) -> dict:
    """swing_high>0 adds the published "crossing previous swing high" trigger (Donchian-N breakout).
    regime_200dma adds the published "only works when Nifty is above its 200 DMA" entry filter."""
    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    n50_ok = (n50 > n50.rolling(200).mean())
    P = {}
    for tkr, df in ohlcv.items():
        if len(df) < MIN_BARS or not membership.get(tkr.upper()):
            continue
        idx = pd.DatetimeIndex(df.index)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        ia = n50.reindex(idx, method="ffill").to_numpy(float)
        line_st, up = supertrend(h, l, c)
        rsi = wilder_rsi(c)
        rs = rs_outperf(c, ia, rs_len) if rs_kind == "outperf" else crs_dist(c, ia, rs_len)
        rs_exit = rs_outperf(c, ia, exit_rs_len) if rs_kind == "outperf" else rs

        rs_ok = np.nan_to_num(rs, nan=-9.0) > 0.0
        rsi_ok = np.nan_to_num(rsi, nan=0.0) > rsi_thr
        ok = np.isfinite(line_st) & np.isfinite(rsi) & np.isfinite(rs)

        mem = np.zeros(len(idx), dtype=bool)
        for d_from, d_to in membership[tkr.upper()]:
            mem |= (idx >= pd.Timestamp(d_from)) & (idx <= pd.Timestamp(d_to))

        triple = up & rsi_ok & rs_ok & ok & mem
        if swing_high > 0:                       # "crossing previous swing high" (Donchian-N)
            prior = pd.Series(h).shift(1).rolling(swing_high).max().to_numpy()
            triple &= np.nan_to_num(c > prior, nan=False)
        if regime_200dma:                        # "only works when Nifty is above its 200 DMA"
            triple &= n50_ok.reindex(idx, method="ffill").fillna(False).to_numpy().astype(bool)
        if exit_kind == "two_of_three":
            nfalse = (~up).astype(int) + (~rs_ok).astype(int) + (~rsi_ok).astype(int)
            ex = nfalse >= 2
        else:                                  # "any": RS21<0 OR RSI<thr OR Supertrend red
            ex = (~up) | (np.nan_to_num(rs_exit, nan=-9.0) < 0.0) | (~rsi_ok)
        P[tkr] = dict(dates=idx, o=o, h=h, l=l, c=c, line=line_st, rs_dist=rs,
                      triple=triple, exit2=ex & ok, pos={d: i for i, d in enumerate(idx)})
    return P


CONFIGS = [
    ("A  as pasted / finding 0132   CRS14, RSI>60, 2-of-3 exit",
     dict(rs_kind="crs", rs_len=14, rsi_thr=60.0, exit_kind="two_of_three")),
    ("B  BAJAJ daily reduction      RS55,  RSI>50, any-of exit (RS21)",
     dict(rs_kind="outperf", rs_len=55, rsi_thr=50.0, exit_kind="any")),
    ("C  B but with the 2-of-3 exit  (isolates the EXIT FORM)",
     dict(rs_kind="outperf", rs_len=55, rsi_thr=50.0, exit_kind="two_of_three")),
    ("D  B but RSI>60               (isolates the RSI THRESHOLD)",
     dict(rs_kind="outperf", rs_len=55, rsi_thr=60.0, exit_kind="any")),
    # --- the two further PUBLISHED legs the pasted images omitted, added in source order.
    # These are documented rules of the real strategy, not tuned parameters.
    ("E  + swing-high breakout trigger (Donchian-20)",
     dict(rs_kind="outperf", rs_len=55, rsi_thr=50.0, exit_kind="any", swing_high=20)),
    ("F  + Nifty>200DMA regime filter  = FULLEST daily reduction",
     dict(rs_kind="outperf", rs_len=55, rsi_thr=50.0, exit_kind="any", swing_high=20,
          regime_200dma=True)),
    ("G  F but with the 2-of-3 exit    (exit form on the full spec)",
     dict(rs_kind="outperf", rs_len=55, rsi_thr=50.0, exit_kind="two_of_three", swing_high=20,
          regime_200dma=True)),
]


def main() -> int:
    print("=== researched Bajaj spec vs the pasted spec — attribution grid ===")
    print("    DATA GATE: the real strategy triggers on a 2-HOURLY chart. This repo has daily bars")
    print("    only, so the daughter timeframe is NOT reproducible. Everything below is the DAILY")
    print("    reduction — a faithful test of the daily legs, not of the full published system.\n")
    ohlcv, membership = corrected_universe(), load_membership()
    hp = dict(start="2019-01-01", end="2026-06-30", cost=0.0025)
    for tag, kw in CONFIGS:
        P = build(ohlcv, membership, **kw)
        m = run_portfolio(P, **hp)
        line(tag, m)
        t = m["trades"]
        print(f"       {'':<50}meanR {m['meanR']:+.3f}   {t:,} trades over {m['years']:.1f}y")
    print("\n  reference: baseline_v1 CAGR 15.46% / Sharpe 0.667 / MaxDD -46.26%")
    print("  standing counts: screens 17 · sealed opens 1 · n_trials 138 (unchanged — measurement)")
    print("  NOT promote candidates. Any promotion needs its own pre-registration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
