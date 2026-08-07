"""Gate-0/1 MEASUREMENT of the owner's daily Supertrend(10,3) + RS(14) + RSI(14)>60 system.

This is a measurement, NOT a trial: it makes no PROMOTE/KILL decision on the honest base and
therefore does not touch diagnostics/research/n_trials.json (standing 138). Its job is to answer,
for the price of a diagnostic, the only question that gates a pre-registration:

    does the triple-condition entry carry a forward edge over its own same-day universe?

Indicator definitions are the TradingView built-ins, verbatim:

  Supertrend(atrLength=10, factor=3), TV support/solutions/43000634738
      hl2        = (high + low) / 2
      ATR        = ta.atr(10)                    -> Wilder RMA (seed = SMA(10))
      basicUpper = hl2 + 3*ATR ; basicLower = hl2 - 3*ATR
      upperBand  = basicUpper < prevUpper or prevClose > prevUpper ? basicUpper : prevUpper
      lowerBand  = basicLower > prevLower or prevClose < prevLower ? basicLower : prevLower
      dir        = prevST == prevUpper ? (close > upperBand ? UP : DOWN)
                                       : (close < lowerBand ? DOWN : UP)
      superTrend = dir == UP ? lowerBand : upperBand
  RSI(14)  = ta.rsi, Wilder RMA on up/down moves.
  RS(14)   = RS / SMA(RS, 14) - 1 > 0, where RS = close / NIFTY-50 close (the house CRS form,
             length 14 per the owner; identical in shape to Mansfield RS, differing only in scaling).

All three are trailing-only on adjusted daily closes -> PIT-legal by construction (no join, no
vendor timestamp, nothing to truncation-test beyond the OHLCV cache itself).

Universe: pinned OHLCV + delisted backfill + alias map (survivorship-corrected), masked to PIT
Nifty-500 membership. Window >=2019 only (pre-2018 membership is back-extended).

Edge is reported DATE-DEMEANED: a signal's forward return minus the same-day cross-sectional mean
over eligible members. A pooled universe mean would confound the signal with the calendar (the
system fires in up-markets by construction, so it must be scored against the up-market days it
actually traded).

    python scripts/diag_supertrend_system.py
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
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

START = pd.Timestamp("2019-01-01")          # the programme trusts >=2019 only
ATR_LEN, ST_FACTOR = 10, 3.0                # TradingView defaults
RSI_LEN, RSI_THR = 14, 60.0
RS_LEN = 14                                 # owner: "RS 14"
FWDS = (5, 10, 21, 63)
MIN_BARS = 300


def rma(x: np.ndarray, n: int) -> np.ndarray:
    """Wilder / Pine ``ta.rma``: seed = SMA(first n), then a_i = a_{i-1} + (x_i - a_{i-1})/n."""
    s = pd.Series(np.asarray(x, dtype=float))
    out = np.full(len(s), np.nan)
    if len(s) < n:
        return out
    tail = s.iloc[n - 1:].copy()
    tail.iloc[0] = s.iloc[:n].mean()
    out[n - 1:] = tail.ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    return out


def wilder_rsi(close: np.ndarray, n: int = RSI_LEN) -> np.ndarray:
    d = np.diff(close, prepend=np.nan)
    up = rma(np.clip(d, 0.0, None), n)
    dn = rma(np.clip(-d, 0.0, None), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = up / np.where(dn == 0.0, np.nan, dn)
    out = 100.0 - 100.0 / (1.0 + rs)
    out[np.isfinite(up) & (dn == 0.0)] = 100.0          # all-up window -> RSI 100 (Pine behaviour)
    return out


def supertrend(h: np.ndarray, l: np.ndarray, c: np.ndarray,
               atr_len: int = ATR_LEN, factor: float = ST_FACTOR) -> tuple[np.ndarray, np.ndarray]:
    """Return (supertrend_line, is_uptrend). Verbatim TradingView band-ratchet + flip logic."""
    n = len(c)
    prev_c = np.concatenate([[np.nan], c[:-1]])
    tr = np.nanmax(np.vstack([h - l, np.abs(h - prev_c), np.abs(l - prev_c)]), axis=0)
    tr[0] = h[0] - l[0]
    atr = rma(tr, atr_len)
    hl2 = (h + l) / 2.0
    basic_up = hl2 + factor * atr
    basic_dn = hl2 - factor * atr

    line = np.full(n, np.nan)
    up_trend = np.zeros(n, dtype=bool)
    upper = lower = np.nan
    prev_line = np.nan
    prev_upper = prev_lower = np.nan
    for i in range(n):
        if not np.isfinite(basic_up[i]):
            continue
        if not np.isfinite(prev_upper):                 # first bar with an ATR
            upper, lower = basic_up[i], basic_dn[i]
            up_trend[i] = False                         # TV seeds DOWN until ATR exists
            line[i] = upper
            prev_upper, prev_lower, prev_line = upper, lower, line[i]
            continue
        pc = c[i - 1]
        upper = basic_up[i] if (basic_up[i] < prev_upper or pc > prev_upper) else prev_upper
        lower = basic_dn[i] if (basic_dn[i] > prev_lower or pc < prev_lower) else prev_lower
        if prev_line == prev_upper:
            up = c[i] > upper
        else:
            up = not (c[i] < lower)
        up_trend[i] = up
        line[i] = lower if up else upper
        prev_upper, prev_lower, prev_line = upper, lower, line[i]
    return line, up_trend


def build(ohlcv: dict, membership) -> pd.DataFrame:
    """Long frame: one row per (ticker, date) that is a PIT member with all three legs defined."""
    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    frames, skipped = [], 0
    for tkr, df in ohlcv.items():
        if len(df) < MIN_BARS:
            skipped += 1
            continue
        periods = membership.get(tkr.upper()) if membership else None
        if not periods:
            skipped += 1
            continue
        idx = pd.DatetimeIndex(df.index)
        h, l, c = (df[x].to_numpy(float) for x in ("High", "Low", "Close"))
        line, up = supertrend(h, l, c)
        rsi = wilder_rsi(c)
        ia = n50.reindex(idx, method="ffill").to_numpy(float)
        rs = np.where(ia > 0, c / ia, np.nan)
        rs_sma = pd.Series(rs).rolling(RS_LEN).mean().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            rs_dist = rs / rs_sma - 1.0

        mem = np.zeros(len(idx), dtype=bool)
        for d_from, d_to in periods:
            mem |= (idx >= pd.Timestamp(d_from)) & (idx <= pd.Timestamp(d_to))

        row = {"ticker": tkr, "date": idx, "close": c, "st_line": line,
               "st_up": up, "rsi": rsi, "rs_dist": rs_dist, "member": mem}
        for k in FWDS:
            f = np.full(len(c), np.nan)
            f[:-k] = c[k:] / c[:-k] - 1.0
            row[f"f{k}"] = f
        frames.append(pd.DataFrame(row))
    print(f"  names built {len(frames)}  (skipped {skipped}: short history or never an index member)")
    out = pd.concat(frames, ignore_index=True)
    out = out[out["member"] & (out["date"] >= START)]
    ok = np.isfinite(out["st_line"]) & np.isfinite(out["rsi"]) & np.isfinite(out["rs_dist"])
    dropped = int((~ok).sum())
    print(f"  member-days >=2019 {len(out):,}  warm-up drops {dropped:,} ({dropped/max(len(out),1)*100:.1f}%)")
    return out[ok].copy()


def demeaned_edge(df: pd.DataFrame, mask: np.ndarray, label: str) -> None:
    """Signal forward return minus the same-day cross-sectional mean over eligible members."""
    n = int(mask.sum())
    if n < 200:
        print(f"  {label:<26} n={n:>7,}  (too few)")
        return
    parts = []
    for k in FWDS:
        col = f"f{k}"
        sub = df[np.isfinite(df[col])]
        m = mask[np.isfinite(df[col]).to_numpy()]
        dm = sub[col].to_numpy() - sub.groupby("date")[col].transform("mean").to_numpy()
        sig = dm[m]
        if len(sig) < 200:
            parts.append(f"{k}d n/a")
            continue
        se = sig.std(ddof=1) / np.sqrt(len(sig))
        parts.append(f"{k}d {sig.mean()*100:+.2f}pp±{1.96*se*100:.2f}")
    print(f"  {label:<26} n={n:>7,}  " + "  ".join(parts))


def main() -> int:
    print("=== GATE-1 coverage / construction ===")
    ohlcv = corrected_universe()
    membership = load_membership()
    print(f"  ohlcv series {len(ohlcv)}  membership tickers {len(membership or {})}")
    df = build(ohlcv, membership)
    df = df.sort_values(["date", "ticker"]).reset_index(drop=True)
    print(f"  window {df['date'].min().date()} -> {df['date'].max().date()}  "
          f"trading days {df['date'].nunique():,}  mean eligible names/day {len(df)/df['date'].nunique():.0f}")

    st = df["st_up"].to_numpy()
    rsi_ok = (df["rsi"].to_numpy() > RSI_THR)
    rs_ok = (df["rs_dist"].to_numpy() > 0.0)
    triple = st & rsi_ok & rs_ok

    print("\n=== leg prevalence (share of eligible member-days) ===")
    for lbl, m in (("supertrend green", st), (f"RSI(14) > {RSI_THR:.0f}", rsi_ok),
                   ("RS(14) > 0", rs_ok), ("ALL THREE", triple)):
        print(f"  {lbl:<26} {m.mean()*100:>5.1f}%")

    df["_triple"] = triple
    df["_prev"] = df.groupby("ticker")["_triple"].shift(1).fillna(False).to_numpy().astype(bool)
    fresh = (df["_triple"] & ~df["_prev"]).to_numpy()
    per_day = df[fresh].groupby("date").size()
    print(f"\n=== slot pressure (FRESH triples: condition true today, false yesterday) ===")
    print(f"  fresh signals {int(fresh.sum()):,} over {df['date'].nunique():,} days  "
          f"mean {per_day.mean():.1f}/day  median {per_day.median():.0f}  p90 {per_day.quantile(0.9):.0f}  max {per_day.max():.0f}")

    print("\n=== ENTRY EDGE, date-demeaned vs same-day eligible universe (close->close) ===")
    print("  (a CI straddling zero means the leg carries nothing beyond the day it fired on)")
    demeaned_edge(df, st & ~rsi_ok & ~rs_ok, "ST green only")
    demeaned_edge(df, rsi_ok, f"RSI>{RSI_THR:.0f} (alone)")
    demeaned_edge(df, rs_ok, "RS>0 (alone)")
    demeaned_edge(df, st, "ST green (alone)")
    demeaned_edge(df, st & rsi_ok, "ST + RSI")
    demeaned_edge(df, st & rs_ok, "ST + RS")
    demeaned_edge(df, rsi_ok & rs_ok, "RSI + RS")
    demeaned_edge(df, triple, "TRIPLE (the strategy)")
    demeaned_edge(df, fresh, "TRIPLE, fresh cross only")

    print("\n=== TRIPLE per-year (date-demeaned 21d, the decision leg) ===")
    sub = df[np.isfinite(df["f21"])].copy()
    sub["dm"] = sub["f21"] - sub.groupby("date")["f21"].transform("mean")
    m21 = triple[np.isfinite(df["f21"]).to_numpy()]
    sub["sig"] = m21
    for yr, g in sub.groupby(sub["date"].dt.year):
        s = g[g["sig"]]["dm"]
        if len(s) < 100:
            print(f"  {yr}  n={len(s):>6,}  (too few)")
            continue
        se = s.std(ddof=1) / np.sqrt(len(s))
        print(f"  {yr}  n={len(s):>6,}  {s.mean()*100:+.2f}pp ± {1.96*se*100:.2f}  "
              f"{'+' if s.mean() > 0 else '-'}")

    print("\n=== EXIT-RULE mechanics (any two of: ST red, RS<0, RSI<60) ===")
    two_of_three = ((~st).astype(int) + (~rs_ok).astype(int) + (~rsi_ok).astype(int)) >= 2
    df["_exit"] = two_of_three
    print(f"  exit condition true on {two_of_three.mean()*100:.1f}% of eligible member-days")
    for lbl, m in (("ST red", ~st), ("RS<0", ~rs_ok), ("RSI<60", ~rsi_ok)):
        print(f"    leg {lbl:<8} true {m.mean()*100:>5.1f}%  |  of exit-days, this leg is one of the two: "
              f"{(m & two_of_three).sum()/max(two_of_three.sum(),1)*100:>5.1f}%")
    print("\n  NOTE — the stop conflict: with the Supertrend line used as an intraday trailing stop,")
    print("  a close below the line (leg 'ST red') is unreachable except on a gap-through, so the")
    print("  2-of-3 exit collapses in practice to 'ST stop OR (RS<0 AND RSI<60)'. Owner call required.")

    print(f"\n  standing counts: screens 16 · sealed opens 1 · n_trials 138 (unchanged — this is a "
          f"measurement, not a trial)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
