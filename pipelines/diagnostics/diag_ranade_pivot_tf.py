"""Pivot timeframe + level as a specification family, on weekly bars.

Owner proposal (from a TradingView Pivots panel): Type=Traditional, **Pivots timeframe = Quarterly**,
"Use daily-based values" checked, on a 1W chart.

Two things change versus everything tested so far:
  PERIOD  monthly -> QUARTERLY. Quarterly levels sit much further apart, so crosses are rarer and
          each one is a larger move. Fewer, bigger signals.
  SOURCE  "Use daily-based values" means the higher-timeframe H/L/C is aggregated from DAILY bars
          rather than from the chart's own weekly bars. This script does exactly that: pivots are
          built on the daily series and then read at each week's close.

Traditional formula, prior completed period:
    P  = (H + L + C) / 3
    R1 = 2P - L          S1 = 2P - H

Per 0133 §4 (specification uncertainty is a multiplicity axis) the family is priced whole rather
than a single cell chosen: {monthly, quarterly} x {P, R1}. The R1 arm also finally tests the reading
the Ranade sources actually describe ("entry when the candle closes above the R1 level"), which
0132's daily test found losing on the daily timeframe -- weekly + quarterly is a new formulation of
it, not a re-run.

Signals on completed weekly bars, entry at the first daily open after the week closes, stop/target
managed on daily bars. Trend filter EMA40w (~the daily EMA200 in calendar time; EMA200w is ~3.9
years and is not defined on our 2017-start history until late 2020).

MEASUREMENT class; `n_trials` stays 138. Binding benchmark remains passive ownership (0136).

    python scripts/diag_ranade_pivot_tf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from diag_ranade_weekly import COST, END, HOLD, START, TRAIN  # noqa: E402
from diag_supertrend_system import rma, supertrend  # noqa: E402
from diag_swing_strategy_survey import (EQ0, MAXPOS, NOTIONAL_CAP, RISK, build_base,  # noqa: E402
                                        ema, period_pivot)
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402


def daily_based_pivot(idx: pd.DatetimeIndex, h, l, c, freq: str, level: str) -> pd.Series:
    """Traditional pivot of the PRIOR completed period, aggregated from DAILY bars
    ("Use daily-based values"). freq is a PERIOD alias: "M" or "Q".

    Uses the corrected period-mapping helper -- see period_pivot's CORRECTNESS NOTE for the
    two-periods-stale bug this replaces."""
    return pd.Series(period_pivot(idx, h, l, c, freq=freq, level=level), index=idx)


def weekly_signals(d, *, freq: str, level: str, ema_len: int = 40):
    idx = d["idx"]
    piv_daily = daily_based_pivot(idx, d["h"], d["l"], d["c"], freq, level)
    df = pd.DataFrame({"o": d["o"], "h": d["h"], "l": d["l"], "c": d["c"]}, index=idx)
    W = df.resample("W-FRI").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    if len(W) < ema_len + 10:
        return []
    wo, wh, wl, wc = (W[x].to_numpy(float) for x in ("o", "h", "l", "c"))
    _, up = supertrend(wh, wl, wc, 10, 3.0)
    trend = wc > ema(wc, ema_len)
    piv_w = piv_daily.resample("W-FRI").last().reindex(W.index).to_numpy(float)
    pc = np.concatenate([[np.nan], wc[:-1]])
    pp = np.concatenate([[np.nan], piv_w[:-1]])
    cross = np.nan_to_num((wc > piv_w) & (pc <= pp), nan=False)
    sig = up & np.nan_to_num(trend, nan=False) & cross
    sig = sig & ~np.concatenate([[False], sig[:-1]])

    prev_c = np.concatenate([[np.nan], wc[:-1]])
    tr = np.nanmax(np.vstack([wh - wl, np.abs(wh - prev_c), np.abs(wl - prev_c)]), axis=0)
    tr[0] = wh[0] - wl[0]
    watr = rma(tr, 14)
    last_day = pd.Series(np.arange(len(idx)), index=idx).resample("W-FRI").last().reindex(W.index)

    out = []
    for k in np.flatnonzero(sig):
        ld = last_day.iloc[k]
        if not np.isfinite(ld):
            continue
        j = int(ld) + 1
        if j >= len(idx) or not d["mem"][j] or not np.isfinite(watr[k]):
            continue
        stop = wc[k] - 2.0 * watr[k]
        rs = d["rs55"][int(ld)]
        if not np.isfinite(stop) or not np.isfinite(rs):
            continue
        out.append((j, float(stop), float(rs)))
    return out


def run_cell(P, *, freq, level, start, end):
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    cands = {}
    for tkr, d in P.items():
        for j, stop, rs in weekly_signals(d, freq=freq, level=level):
            if lo <= d["idx"][j] <= hi:
                cands.setdefault(d["idx"][j], []).append((rs, tkr, j, stop))
    dates = [x for x in sorted(set().union(*[set(d["idx"]) for d in P.values()])) if lo <= x <= hi]
    cash = equity = EQ0
    open_pos, eqc, trades, npos = {}, [], [], []
    for dt in dates:
        for tkr in list(open_pos):
            p, d = open_pos[tkr], P[tkr]
            i = d["pos"].get(dt)
            if i is None:
                continue
            p["held"] += 1
            px = why = None
            if d["l"][i] <= p["stop"]:
                px, why = min(d["o"][i], p["stop"]), "stop"
            elif d["h"][i] >= p["target"]:
                px, why = max(d["o"][i], p["target"]), "target"
            elif p["held"] >= 252:
                px, why = d["c"][i], "maxhold"
            if px is not None:
                cash += p["shares"] * px * (1 - COST)
                trades.append(dict(r=(px - p["entry"]) / p["r_unit"], why=why, held=p["held"],
                                   stop_pct=(p["entry"] - p["stop"]) / p["entry"]))
                del open_pos[tkr]
        for rs, tkr, j, stop in sorted(cands.get(dt, []), reverse=True):
            if len(open_pos) >= MAXPOS or tkr in open_pos:
                continue
            d = P[tkr]
            entry = d["o"][j]
            if not np.isfinite(entry) or entry <= stop:
                continue
            sh = min(equity * RISK / (entry - stop), equity * NOTIONAL_CAP / entry)
            if sh <= 0 or sh * entry * (1 + COST) > cash:
                continue
            cash -= sh * entry * (1 + COST)
            open_pos[tkr] = dict(entry=entry, stop=stop, r_unit=entry - stop, shares=sh, held=0,
                                 target=entry + 2.0 * (entry - stop))
        equity = cash + sum(p["shares"] * (P[t]["c"][P[t]["pos"][dt]] if dt in P[t]["pos"] else p["entry"])
                            for t, p in open_pos.items())
        eqc.append((dt, equity))
        npos.append(len(open_pos))
    eq = pd.Series(dict(eqc)).sort_index()
    ret = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    t = pd.DataFrame(trades)
    return dict(cagr=(eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan,
                sharpe=ret.mean() / ret.std() * np.sqrt(252) if ret.std() else np.nan,
                dd=(eq / eq.cummax() - 1).min(), n=len(t),
                win=(t["r"] > 0).mean() if len(t) else np.nan,
                meanR=t["r"].mean() if len(t) else np.nan,
                hold=t["held"].median() if len(t) else np.nan,
                stop_pct=t["stop_pct"].median() if len(t) else np.nan,
                seats=float(np.mean(npos)))


CELLS = [("monthly  P  (the incumbent)", "M", "P"),
         ("monthly  R1", "M", "R1"),
         ("QUARTERLY P  <- owner proposal", "Q", "P"),
         ("QUARTERLY R1 <- proposal + sourced level", "Q", "R1")]


def main() -> int:
    print("=== PIVOT TIMEFRAME x LEVEL on weekly bars — Traditional, daily-based values ===")
    print("    weekly SIGNAL (ST 10,3 + EMA40w + pivot cross) -> next daily open -> daily stop/target\n")
    P = build_base(corrected_universe(), load_membership())
    print(f"  names {len(P)}\n")
    for tag, freq, level in CELLS:
        print(f"  {tag}")
        for wtag, (s, e) in (("TRAIN  ", TRAIN), ("HOLDOUT", HOLD), ("FULL   ", (START, END))):
            m = run_cell(P, freq=freq, level=level, start=s, end=e)
            print(f"      {wtag}  CAGR {m['cagr']*100:>7.2f}%  Sh {m['sharpe']:>6.3f}  "
                  f"DD {m['dd']*100:>6.1f}%  n {m['n']:>4,}  win {m['win']*100:>4.1f}%  "
                  f"R {m['meanR']:>+5.2f}  hold {m['hold']:>4.0f}d  stop {m['stop_pct']*100:>4.1f}%  "
                  f"seats {m['seats']:>4.1f}")
    print("\n  BINDING BENCHMARK (0136): equal-weight passive ~15.5% CAGR / Sharpe ~0.85-0.95")
    print("  NIFTY-50 buy-and-hold 11.95% / Sharpe 0.787 / DD -38.4%")
    print("  standing counts: screens 19 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
