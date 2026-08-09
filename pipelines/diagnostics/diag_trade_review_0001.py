"""MEASUREMENT (no trial): re-derive 0001's headline numbers independently, then dump the trade
ledger with entry-time signal context so the owner can review individual decisions."""
import sys, json
sys.path.insert(0, r"C:\nifty-satvik"); sys.path.insert(0, r"C:\nifty-satvik\scripts")
import numpy as np, pandas as pd
from pipelines.research.run_0001_xsec_momentum import (BAND, END, START, add_signals, run)
from run_bhanushali_path1 import corrected_universe
from nq.data.membership import load_membership
from nq.universe import build_universe

OUT = r"C:\nifty-satvik\diagnostics\trade_review"

print("building panel ...", flush=True)
u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
p = add_signals(u)
keep = p["ticker"].isin(p.loc[p["size_band"] == BAND, "ticker"].unique())
band = p[keep].copy()
band["rank"] = np.where(band["eligible"] & (band["size_band"] == BAND) & band["nms"].notna(),
                        band["nms"], np.nan)
print("running candidate book ...", flush=True)
res = run(band)
tr = pd.DataFrame(res["trades"]); cur = pd.DataFrame(res["equity_curve"])
m = res["metrics"]

# ---------- 1. WIRING RECONCILIATION: re-derive every headline from primitives ----------
cur["date"] = pd.to_datetime(cur["date"]); cur = cur.sort_values("date")
eq = cur["equity"].to_numpy(float)
yrs = (cur["date"].iloc[-1] - cur["date"].iloc[0]).days / 365.25
cagr = ((eq[-1] / eq[0]) ** (1 / yrs) - 1) * 100
r = pd.Series(eq).pct_change().dropna()
sharpe = r.mean() / r.std() * np.sqrt(252)
dd = ((pd.Series(eq) / pd.Series(eq).cummax()) - 1).min() * 100
print("\n=== WIRING RECONCILIATION (mine vs engine) ===")
for k, mine, eng in [("CAGR%", cagr, m.get("cagr_pct")), ("Sharpe", sharpe, m.get("sharpe")),
                     ("MaxDD%", dd, m.get("max_drawdown_pct")),
                     ("final_equity", eq[-1], m.get("final_equity")),
                     ("n_trades", len(tr), m.get("n_trades"))]:
    ok = "OK " if (eng is not None and abs(float(mine) - float(eng)) < max(0.02, abs(float(eng))*2e-4)) else "MISMATCH"
    print(f"  {ok} {k:14s} mine {float(mine):>14.4f}   engine {eng}")
print(f"  years {yrs:.3f} | curve {cur['date'].min().date()} -> {cur['date'].max().date()} | rows {len(cur)}")

# PnL reconciliation: do trade PnLs explain the equity change?
print(f"  sum(trade pnl) {tr['pnl'].sum():,.0f} vs equity change {eq[-1]-eq[0]:,.0f} "
      f"(open positions at end explain the rest)")

# ---------- 2. entry-time signal context = the REASON TO BUY ----------
band["date"] = pd.to_datetime(band["date"])
dates = np.sort(band["date"].unique())
prev = {d: dates[i-1] for i, d in enumerate(dates) if i > 0}
band["nms_rank_pct"] = band.groupby("date")["rank"].rank(pct=True)
band["n_rankable"] = band.groupby("date")["rank"].transform("count")
ctx = band.set_index(["date", "ticker"])[["nms", "nms_rank_pct", "n_rankable", "mr12", "mr6",
                                          "close", "turnover_63d"]]
tr["entry_date"] = pd.to_datetime(tr["entry_date"]); tr["exit_date"] = pd.to_datetime(tr["exit_date"])
tr["decision_date"] = tr["entry_date"].map(lambda d: prev.get(d, d))   # rank read at t, fill t+1
j = tr.join(ctx, on=["decision_date", "ticker"])
j["nms_rank_in_band"] = (1 - j["nms_rank_pct"]) * j["n_rankable"] + 1   # 1 = best
j.to_csv(f"{OUT}/all_trades_0001.csv", index=False)
print(f"\n  wrote {len(j):,} trades with entry context -> diagnostics/trade_review/all_trades_0001.csv")
print(f"  entry-context join coverage: {j['nms'].notna().mean()*100:.1f}%")
print(f"  by reason: {j['reason'].value_counts().to_dict()}")
