"""What if the owner does NOT buy every recommendation?  Position-level adoption bootstrap."""
import sys; sys.path.insert(0, r"C:\nifty-satvik")
import numpy as np, pandas as pd
OUT = r"C:\nifty-satvik\diagnostics\trade_review"
p = pd.read_csv(f"{OUT}/positions_0001.csv", parse_dates=["entry_date"])
full = p["return_pct"].mean(); rng = np.random.default_rng(12345); N = 4000

print(f"full book: {len(p)} positions, mean position return {full:+.2f}%\n")
print("Adoption   mean    p5      p25     median  p75     p95    P(worse than full)  P(mean<0)")
rows=[]
for a in (0.10, 0.25, 0.50, 0.75, 0.90):
    draws=[]
    for _ in range(N):
        m = rng.random(len(p)) < a
        if m.sum() < 5: continue
        draws.append(p.loc[m, "return_pct"].mean())
    d = np.array(draws)
    print(f"  {a*100:3.0f}%   {d.mean():+6.2f}  {np.percentile(d,5):+6.2f}  {np.percentile(d,25):+6.2f}  "
          f"{np.median(d):+6.2f}  {np.percentile(d,75):+6.2f}  {np.percentile(d,95):+6.2f}   "
          f"{(d<full).mean()*100:5.1f}%           {(d<0).mean()*100:5.1f}%")
    rows.append((a, d.mean(), np.percentile(d,5), np.percentile(d,95), (d<full).mean()))

print("\n=== does picking the BEST-RANKED half help? (rank showed no predictive power) ===")
med = p["rank_in_band"].median()
top_half = p[p["rank_in_band"] <= med]["return_pct"].mean()
bot_half = p[p["rank_in_band"] >  med]["return_pct"].mean()
print(f"  buy only the better-ranked half : {top_half:+.2f}%")
print(f"  buy only the worse-ranked half  : {bot_half:+.2f}%")
print(f"  buy everything                  : {full:+.2f}%")

print("\n=== how much of the P&L is in how few names? ===")
s = p.sort_values("pnl", ascending=False).reset_index(drop=True)
tot = p["pnl"].sum(); cum = s["pnl"].cumsum()
for frac in (0.5, 0.8, 1.0):
    n = int((cum <= tot*frac).sum())+1
    print(f"  {frac*100:3.0f}% of total P&L comes from the top {n:>3} positions "
          f"({n/len(p)*100:4.1f}% of all positions)")
print(f"\n  P(a random 50%-adopter misses a given top-20 name) = 50%")
miss = [(rng.random(20) < 0.5).sum() for _ in range(20000)]
print(f"  expected top-20 names captured by a 50% adopter: {np.mean(miss):.1f} of 20 "
      f"(5th pct {np.percentile(miss,5):.0f}, 95th {np.percentile(miss,95):.0f})")
