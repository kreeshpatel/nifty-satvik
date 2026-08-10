"""MEASUREMENT (no trial) — collapses 2,951 sell rows into 926 POSITIONS -- trims are partial sells, not decisions.

Committed 2026-08-09 after a red-team audit found the artifacts in diagnostics/trade_review/ had
been committed with NO generator: `grep -rn "positions_0001|trade_review" --include=*.py` matched
nothing, so the numbers could be verified against each other but never against the engine. A
decision-grade number whose producer is not committed is exactly what reproduce-before-trust
forbids.
"""
import sys; sys.path.insert(0, r"C:\nifty-satvik")
import numpy as np, pandas as pd
OUT = r"C:\nifty-satvik\diagnostics\trade_review"
t = pd.read_csv(f"{OUT}/all_trades_0001.csv", parse_dates=["entry_date","exit_date","decision_date"])

# A POSITION = one (ticker, entry_date). Trims are partial sells of it, not separate decisions.
t["basis"] = t["qty"] * t["entry"]
g = t.groupby(["ticker", "entry_date"], as_index=False)
pos = g.agg(qty=("qty","sum"), basis=("basis","sum"), pnl=("pnl","sum"),
            entry_px=("entry","first"), last_exit=("exit_date","max"),
            days_held=("days_held","max"), n_sells=("reason","size"),
            n_trims=("reason", lambda s:(s=="rebalance_trim").sum()),
            final_reason=("reason","last"), nms=("nms","first"),
            rank_in_band=("nms_rank_in_band","first"), n_rankable=("n_rankable","first"),
            mr12=("mr12","first"), mr6=("mr6","first"), turnover=("turnover_63d","first"))
pos["return_pct"] = pos["pnl"] / pos["basis"] * 100
pos["exit_px_eff"] = (pos["basis"] + pos["pnl"]) / pos["qty"]
pos = pos.sort_values("entry_date")
pos.to_csv(f"{OUT}/positions_0001.csv", index=False)

print(f"POSITIONS: {len(pos):,} (from {len(t):,} trade rows)")
print(f"  mean return {pos['return_pct'].mean():+.2f}% | median {pos['return_pct'].median():+.2f}%")
print(f"  win rate {(pos['return_pct']>0).mean()*100:.1f}%   <-- vs the 73.09% headline computed on trade rows")
print(f"  mean days held {pos['days_held'].mean():.0f} | median {pos['days_held'].median():.0f}")
print(f"  total pnl {pos['pnl'].sum():,.0f}")
print(f"\n  P&L concentration:")
s = pos.sort_values("pnl", ascending=False)
for k in (5, 10, 20, 50):
    print(f"    top {k:>3} positions = {s['pnl'].head(k).sum()/pos['pnl'].sum()*100:5.1f}% of total P&L")
print(f"    positions with pnl>0: {(pos['pnl']>0).sum()} contributing {s[s.pnl>0]['pnl'].sum():,.0f}")
print(f"    positions with pnl<0: {(pos['pnl']<0).sum()} costing     {s[s.pnl<0]['pnl'].sum():,.0f}")
