"""MEASUREMENT (no trial) — the 20 best / flattest / worst positions for owner review, each with why it was bought.

Committed 2026-08-09 after a red-team audit found the artifacts in diagnostics/trade_review/ had
been committed with NO generator: `grep -rn "positions_0001|trade_review" --include=*.py` matched
nothing, so the numbers could be verified against each other but never against the engine. A
decision-grade number whose producer is not committed is exactly what reproduce-before-trust
forbids.
"""
import sys; sys.path.insert(0, r"C:\nifty-satvik")
import pandas as pd, numpy as np
OUT = r"C:\nifty-satvik\diagnostics\trade_review"
p = pd.read_csv(f"{OUT}/positions_0001.csv", parse_dates=["entry_date","last_exit"])

def why(r):
    pctile = 100*(1 - (r.rank_in_band-1)/max(r.n_rankable-1,1))
    return (f"NMS {r.nms:.2f} — ranked #{int(r.rank_in_band)} of {int(r.n_rankable)} in the MID band "
            f"({pctile:.0f}th pct). 12m vol-adj momentum {r.mr12:+.2f}, 6m {r.mr6:+.2f}.")

def dump(df, title, fname):
    lines = [f"# {title}", ""]
    lines.append("| # | ticker | entry | exit | days | ret% | P&L ₹ | exit reason | why it was bought |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, (_, r) in enumerate(df.iterrows(), 1):
        lines.append(f"| {i} | **{r.ticker}** | {r.entry_date.date()} | {r.last_exit.date()} | "
                     f"{int(r.days_held)} | {r.return_pct:+.1f} | {r.pnl:+,.0f} | {r.final_reason} | {why(r)} |")
    open(f"{OUT}/{fname}", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return len(df)

best  = p.nlargest(20, "return_pct")
worst = p.nsmallest(20, "return_pct")
flat  = p.assign(absr=p["return_pct"].abs()).nsmallest(20, "absr")

dump(best,  "20 BEST positions — study 0001 (cross-sectional momentum, MID band, top-30 monthly)", "top20_best.md")
dump(worst, "20 WORST positions — study 0001", "top20_worst.md")
dump(flat,  "20 FLATTEST positions (exited at ~0%) — study 0001", "top20_flat.md")

for nm, d in (("BEST",best),("FLAT",flat),("WORST",worst)):
    print(f"\n=== {nm} 20 ===  ret% {d.return_pct.min():+.1f}..{d.return_pct.max():+.1f} | "
          f"pnl {d.pnl.sum():+,.0f} | mean days {d.days_held.mean():.0f} | "
          f"mean rank-in-band #{d.rank_in_band.mean():.0f} of ~{d.n_rankable.mean():.0f}")
    print("  " + ", ".join(f"{r.ticker}({r.return_pct:+.0f}%)" for _, r in d.head(8).iterrows()))

print("\n=== does entry rank predict outcome? (the thing the book assumes) ===")
p["q"] = pd.qcut(p["rank_in_band"], 5, labels=["Q1 best rank","Q2","Q3","Q4","Q5 worst rank"])
print(p.groupby("q", observed=True).agg(n=("return_pct","size"), mean_ret=("return_pct","mean"),
       median=("return_pct","median"), win=("return_pct", lambda s:(s>0).mean()*100)).round(2).to_string())
from scipy.stats import spearmanr
ic, pv = spearmanr(p["rank_in_band"], p["return_pct"])
print(f"\n  Spearman(entry rank, position return) = {ic:+.4f}  p={pv:.3f}   "
      f"(negative = better rank -> better return)")
