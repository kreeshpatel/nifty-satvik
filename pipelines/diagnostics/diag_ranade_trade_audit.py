"""Auditable trade ledger for the Supertrend+Pivot book — losers AND matched winners.

Purpose: let the owner verify the engine did what it claims, trade by trade, against a chart.
Every row carries the inputs, the derived levels and the outcome, so the arithmetic is checkable:

    signal_date   the bar whose CLOSE produced the signal (all indicators as of this bar)
    st_line / ema200 / pivot / atr14 / close_sig     the four rule inputs at the signal bar
    entry_date    the NEXT trading bar (execution is next-open; never the signal bar)
    entry_px      that bar's OPEN
    stop_px       close_sig - 2 x atr14        <- verifiable by hand
    target_px     entry_px + 2 x (entry_px - stop_px)
    exit_date / exit_px / why                  stop | target | maxhold
    R             (exit_px - entry_px) / (entry_px - stop_px)
    mfe_R / mae_R best and worst excursion during the hold, in R
    gap_flag      TRUE if the trade opened through its stop (fill worse than the stop level)

WHY WINNERS ARE INCLUDED. `program-laws` VIII: matched controls, never one-sided lists. A
loser-only list re-discovers whatever is common to ALL trades (extension, candle size, volatility)
and reads it as the cause of loss. Winners are sampled from the SAME years so any feature that
"explains" the losers can be checked against trades where it did not.

Window 2017-01-01..2026-06-30 (2016 excluded: ~21 eligible names, 0133 §3a-CORRECTION).

    python scripts/diag_ranade_trade_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from diag_ranade_deepdive import legs  # noqa: E402
from diag_swing_strategy_survey import (EQ0, MAXPOS, NOTIONAL_CAP, RISK, build_base,  # noqa: E402
                                        ema, monthly_pivot)
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

START, END, COST = "2017-01-01", "2026-06-30", 0.0025


def ledger(P) -> pd.DataFrame:
    lo, hi = pd.Timestamp(START), pd.Timestamp(END)
    cands = {}
    for tkr, d in P.items():
        d["ema200"] = ema(d["c"], 200)
        d["pivot"] = monthly_pivot(d["idx"], d["h"], d["l"], d["c"])
        for i in np.flatnonzero(legs(d) & d["mem"]):
            if i + 1 >= len(d["c"]) or not np.isfinite(d["rs55"][i]):
                continue
            if lo <= d["idx"][i] <= hi:
                cands.setdefault(d["idx"][i], []).append((float(d["rs55"][i]), tkr, int(i)))

    dates = [x for x in sorted(set().union(*[set(d["idx"]) for d in P.values()])) if lo <= x <= hi]
    cash = equity = EQ0
    open_pos, rows = {}, []
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
                cash += p["shares"] * px * (1 - COST)
                rows.append(dict(
                    ticker=tkr, signal_date=p["sig_date"].date(), entry_date=p["date"].date(),
                    exit_date=dt.date(), why=why,
                    close_sig=round(p["close_sig"], 2), st_line=round(p["st_line"], 2),
                    ema200=round(p["ema200"], 2), pivot=round(p["pivot"], 2),
                    atr14=round(p["atr"], 2),
                    entry_px=round(p["entry"], 2), stop_px=round(p["stop"], 2),
                    target_px=round(p["target"], 2), exit_px=round(px, 2),
                    R=round((px - p["entry"]) / p["r_unit"], 3),
                    mfe_R=round(p["mfe"], 2), mae_R=round(p["mae"], 2),
                    held_d=p["held"], stop_pct=round((p["entry"] - p["stop"]) / p["entry"] * 100, 1),
                    gap_flag=bool(why == "stop" and d["o"][i] < p["stop"]),
                    pnl=round(p["shares"] * (px * (1 - COST) - p["entry"] * (1 + COST)), 0)))
                del open_pos[tkr]

        for _s, tkr, i in sorted(cands.get(prev, []), reverse=True) if prev else []:
            if len(open_pos) >= MAXPOS or tkr in open_pos:
                continue
            d = P[tkr]
            j = d["pos"].get(dt)
            if j is None or j != i + 1:
                continue
            entry, s0 = d["o"][j], d["c"][i] - 2.0 * d["atr"][i]
            if not np.isfinite(entry) or not np.isfinite(s0) or entry <= s0:
                continue
            sh = min(equity * RISK / (entry - s0), equity * NOTIONAL_CAP / entry)
            if sh <= 0 or sh * entry * (1 + COST) > cash:
                continue
            cash -= sh * entry * (1 + COST)
            open_pos[tkr] = dict(entry=entry, stop=s0, r_unit=entry - s0, shares=sh, held=0,
                                 target=entry + 2.0 * (entry - s0), date=dt, mfe=0.0, mae=0.0,
                                 sig_date=d["idx"][i], close_sig=d["c"][i], st_line=d["line"][i]
                                 if "line" in d else np.nan, ema200=d["ema200"][i],
                                 pivot=d["pivot"][i], atr=d["atr"][i])

        equity = cash + sum(p["shares"] * (P[t]["c"][P[t]["pos"][dt]] if dt in P[t]["pos"] else p["entry"])
                            for t, p in open_pos.items())
        prev = dt
    return pd.DataFrame(rows)


def show(df, title, cols):
    print(f"\n=== {title} ===")
    print(df[cols].to_string(index=False))


def main() -> int:
    print("=== TRADE AUDIT — Supertrend + Pivot, 2017-2026 ===")
    P = build_base(corrected_universe(), load_membership())
    t = ledger(P)
    out = ROOT / "diagnostics" / "research" / "ranade_trade_audit.csv"
    t.to_csv(out, index=False)
    print(f"  {len(t):,} trades  ->  {out}")

    print("\n=== ARITHMETIC SELF-CHECK (these must all be TRUE) ===")
    chk_stop = np.isclose(t["stop_px"], t["close_sig"] - 2 * t["atr14"], atol=0.02)
    chk_tgt = np.isclose(t["target_px"], t["entry_px"] + 2 * (t["entry_px"] - t["stop_px"]), atol=0.02)
    chk_seq = pd.to_datetime(t["entry_date"]) > pd.to_datetime(t["signal_date"])
    chk_exit = pd.to_datetime(t["exit_date"]) >= pd.to_datetime(t["entry_date"])
    chk_rules = (t["close_sig"] > t["ema200"]) & (t["close_sig"] > t["pivot"])
    for name, c in (("stop = close_sig - 2*ATR", chk_stop), ("target = entry + 2R", chk_tgt),
                    ("entry AFTER signal bar", chk_seq), ("exit >= entry", chk_exit),
                    ("signal close > EMA200 and > pivot", chk_rules)):
        print(f"  {name:<36} {int(c.sum()):>5,}/{len(t):,}  {'OK' if c.all() else '** FAILURES'}")
    print(f"  gap-through-stop fills (worse than stop) {int(t['gap_flag'].sum()):>4,} "
          f"({t['gap_flag'].mean()*100:.1f}%)  — these are honest slippage, not bugs")

    cols = ["ticker", "signal_date", "entry_date", "exit_date", "why", "close_sig", "atr14",
            "entry_px", "stop_px", "target_px", "exit_px", "R", "mfe_R", "mae_R", "held_d",
            "stop_pct", "pnl"]
    losers = t[t["R"] < 0].sort_values("pnl")
    winners = t[t["R"] > 0].sort_values("pnl", ascending=False)
    show(losers.head(20), "20 WORST LOSERS by rupee P&L", cols)
    show(winners.head(20), "20 BEST WINNERS by rupee P&L (the matched control)", cols)

    print("\n=== LOSER vs WINNER, side by side (the comparison a loser-only list cannot make) ===")
    L, W = t[t["R"] < 0], t[t["R"] > 0]
    for f in ("stop_pct", "atr14", "held_d", "mfe_R"):
        print(f"  {f:<10} losers med {L[f].median():>8.2f}   winners med {W[f].median():>8.2f}")
    print(f"  {'count':<10} losers {len(L):>12,}   winners {len(W):>12,}")

    print("\n=== WHERE THE LOSSES CLUSTER ===")
    print("  by year:")
    ly = pd.to_datetime(t["entry_date"]).dt.year
    for y, g in t.groupby(ly):
        print(f"    {y}  trades {len(g):>4}  win {(g['R']>0).mean()*100:>4.1f}%  "
              f"meanR {g['R'].mean():>+5.2f}  net P&L {g['pnl'].sum():>12,.0f}")
    print("\n  worst single names by cumulative P&L:")
    byname = t.groupby("ticker")["pnl"].agg(["sum", "count"]).sort_values("sum").head(10)
    for n, r in byname.iterrows():
        print(f"    {n:<16} {r['sum']:>12,.0f}  over {int(r['count'])} trades")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
