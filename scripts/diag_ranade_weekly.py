"""Supertrend + Pivot on WEEKLY bars — a specification family, not a single variant.

The daily book gets stopped out on 60% of trades at a 12-day median hold. Weekly bars are a
genuinely new formulation (new bar construction, new indicator behaviour), not a re-test, so it is
legitimate under the collision rule. Two design choices are ambiguous, and per the 0133 §4 law
("specification uncertainty is a multiplicity axis") both are priced rather than chosen:

  the TREND FILTER
      literal transplant  EMA200 on WEEKLY bars = a 200-WEEK (~4 year) filter
      calendar-matched    EMA40  on weekly bars ~ the daily EMA200 in calendar time
  the STOP
      literal   2 x ATR(14) on WEEKLY bars  -> ~2.2x wider than daily -> smaller positions,
                more concurrent names, and therefore exposure to 0131's seat-dilution mechanism
      matched   2 x ATR(14) on DAILY bars   -> position sizing comparable to the daily book

CELLS
  D    daily reference (the book from 0133/0136)
  W1   weekly bars, ST(10,3)w, EMA200w, weekly ATR stop      <- literal transplant
  W2   weekly bars, ST(10,3)w, EMA40w,  weekly ATR stop      <- calendar-matched trend
  W3   weekly bars, ST(10,3)w, EMA40w,  DAILY ATR stop       <- calendar-matched trend AND sizing

EXECUTION MODEL. Signals are computed on completed weekly bars only; the trade is entered at the
OPEN OF THE FIRST DAILY BAR AFTER the signal week closes, and the stop/target are then managed on
DAILY bars. This avoids the intrabar ambiguity that would arise from managing on weekly bars (a
weekly bar can contain both the stop and the target, and any ordering rule would be a fiction) and
matches how the trade would actually be run.

Reported on TRAIN 2019-2023 / HOLDOUT 2024-2026 and the full window, against the passive benchmark
that 0136 established as the binding gate. Window starts 2017 (2016 excluded, 0133 §3a-CORRECTION).

MEASUREMENT class; `n_trials` stays 138. Nothing here is promotable.

    python scripts/diag_ranade_weekly.py
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
from diag_supertrend_system import rma, supertrend  # noqa: E402
from diag_swing_strategy_survey import (EQ0, MAXPOS, NOTIONAL_CAP, RISK, build_base,  # noqa: E402
                                        ema, monthly_pivot)
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

START, END, COST = "2017-01-01", "2026-06-30", 0.0025
TRAIN, HOLD = ("2019-01-01", "2023-12-31"), ("2024-01-01", "2026-06-30")


def weekly_signals(d, *, ema_len: int, weekly_stop: bool):
    """Return list of (exec_daily_i, stop_price, rs55) for each fresh weekly signal."""
    idx = d["idx"]
    df = pd.DataFrame({"o": d["o"], "h": d["h"], "l": d["l"], "c": d["c"]}, index=idx)
    W = df.resample("W-FRI").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    if len(W) < ema_len + 20:
        return []
    wo, wh, wl, wc = (W[x].to_numpy(float) for x in ("o", "h", "l", "c"))
    _, up = supertrend(wh, wl, wc, 10, 3.0)
    trend = wc > ema(wc, ema_len)
    piv = monthly_pivot(W.index, wh, wl, wc)
    pc = np.concatenate([[np.nan], wc[:-1]])
    pp = np.concatenate([[np.nan], piv[:-1]])
    cross = np.nan_to_num((wc > piv) & (pc <= pp), nan=False)
    sig = up & np.nan_to_num(trend, nan=False) & cross
    sig = sig & ~np.concatenate([[False], sig[:-1]])

    prev_c = np.concatenate([[np.nan], wc[:-1]])
    tr = np.nanmax(np.vstack([wh - wl, np.abs(wh - prev_c), np.abs(wl - prev_c)]), axis=0)
    tr[0] = wh[0] - wl[0]
    watr = rma(tr, 14)

    # map each week to the first DAILY bar strictly after that week's last trading day
    last_day = pd.Series(np.arange(len(idx)), index=idx).resample("W-FRI").last().reindex(W.index)
    out = []
    for k in np.flatnonzero(sig):
        ld = last_day.iloc[k]
        if not np.isfinite(ld):
            continue
        j = int(ld) + 1
        if j >= len(idx) or not d["mem"][j]:
            continue
        stop = wc[k] - 2.0 * (watr[k] if weekly_stop else d["atr"][int(ld)])
        if not np.isfinite(stop):
            continue
        rs = d["rs55"][int(ld)]
        if not np.isfinite(rs):
            continue
        out.append((j, float(stop), float(rs)))
    return out


def run_cell(P, *, ema_len, weekly_stop, start, end, daily=False):
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    cands = {}
    for tkr, d in P.items():
        if daily:
            from diag_ranade_deepdive import legs
            for i in np.flatnonzero(legs(d) & d["mem"]):
                if i + 1 < len(d["c"]) and np.isfinite(d["rs55"][i]) and lo <= d["idx"][i + 1] <= hi:
                    cands.setdefault(d["idx"][i + 1], []).append(
                        (float(d["rs55"][i]), tkr, i + 1, float(d["c"][i] - 2.0 * d["atr"][i])))
        else:
            for j, stop, rs in weekly_signals(d, ema_len=ema_len, weekly_stop=weekly_stop):
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
                seats=float(np.mean(npos)), eq=eq)


CELLS = [
    ("D   daily reference", dict(daily=True, ema_len=200, weekly_stop=False)),
    ("W1  weekly, EMA200w, weekly ATR stop", dict(daily=False, ema_len=200, weekly_stop=True)),
    ("W2  weekly, EMA40w,  weekly ATR stop", dict(daily=False, ema_len=40, weekly_stop=True)),
    ("W3  weekly, EMA40w,  DAILY ATR stop", dict(daily=False, ema_len=40, weekly_stop=False)),
]


def main() -> int:
    print("=== Supertrend + Pivot on WEEKLY bars — specification family ===")
    print("    weekly SIGNAL -> entry at the first daily open after the week closes -> DAILY stop/target")
    print(f"    window {START}..{END}   TRAIN {TRAIN[0][:4]}-{TRAIN[1][:4]}  HOLDOUT {HOLD[0][:4]}-{HOLD[1][:4]}\n")
    P = build_base(corrected_universe(), load_membership())
    print(f"  names {len(P)}\n")
    for tag, kw in CELLS:
        print(f"  {tag}")
        for wtag, (s, e) in (("TRAIN  ", TRAIN), ("HOLDOUT", HOLD), ("FULL   ", (START, END))):
            m = run_cell(P, start=s, end=e, **kw)
            print(f"      {wtag}  CAGR {m['cagr']*100:>7.2f}%  Sh {m['sharpe']:>6.3f}  DD {m['dd']*100:>6.1f}%  "
                  f"n {m['n']:>5,}  win {m['win']*100:>4.1f}%  R {m['meanR']:>+5.2f}  "
                  f"hold {m['hold']:>4.0f}d  stop {m['stop_pct']*100:>4.1f}%  seats {m['seats']:>4.1f}")
    print("\n  BINDING BENCHMARK (0136): equal-weight passive ownership ~15.5% CAGR / Sharpe ~0.85-0.95")
    print("  reference: NIFTY-50 buy-and-hold 11.95% / Sharpe 0.787 / DD -38.4%")
    print("  standing counts: screens 19 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
