import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-nifty-satvik/26ce7f30-6a8b-5683-bd62-539ae0908694/scratchpad/replica")
import numpy as np
import pandas as pd
from sim import run, recompute_tax, bucket, dates, tax_days

HERE = "/tmp/claude-0/-home-user-nifty-satvik/26ce7f30-6a8b-5683-bd62-539ae0908694/scratchpad/replica"
out = []
P = out.append

at = run(tax=True)
pt = run(tax=False)
nc = run(tax=False, costs=False)
P("# RESULT (independent replica, from SPEC.md only)\n")
P(f"Tax days used: {sorted(dates[i].date().isoformat() for i in tax_days())}; final session {dates[-1].date()}; "
  f"calendar days {(dates[-1]-dates[0]).days}\n")
P("## A. Anchors\n")
P("| run | final cash | CAGR % |\n|---|---|---|")
for n, r in [("after-tax", at), ("pre-tax", pt), ("pre-tax no costs", nc)]:
    P(f"| {n} | {r['final_cash']:,.2f} | {100*r['cagr']:.2f} |")

P("\n## B. STCG/LTCG split (after-tax run)\n")
ev = pd.DataFrame(at["events"], columns=["period", "source", "cls", "hd", "gain"])
ev["bucket"] = ev["hd"].map(bucket)
order = ["0-30", "31-90", "91-180", "181-330", "331-364", "365+"]
g = ev.groupby(["source", "bucket", "cls"])["gain"].agg(["count", "sum"]).reset_index()
g["bucket"] = pd.Categorical(g["bucket"], order, ordered=True)
g = g.sort_values(["source", "bucket", "cls"])
P("| source | bucket | class | count | gain Rs |\n|---|---|---|---|---|")
for r in g.itertuples():
    P(f"| {r.source} | {r.bucket} | {r.cls} | {r.count} | {r.sum:,.0f} |")
P("\nBy bucket (all sources):\n\n| bucket | class | count | gain Rs |\n|---|---|---|---|")
gb = ev.groupby(["bucket", "cls"])["gain"].agg(["count", "sum"]).reset_index()
gb["bucket"] = pd.Categorical(gb["bucket"], order, ordered=True)
for r in gb.sort_values(["bucket", "cls"]).itertuples():
    P(f"| {r.bucket} | {r.cls} | {r.count} | {r.sum:,.0f} |")

P("\nTax per period:\n\n| period | settle date | net ST | net LT | slab | ST tax | LT tax | slab tax | total |\n|---|---|---|---|---|---|---|---|---|")
tot = {"ST": 0, "LT": 0, "SL": 0}
for (p, d, st, lt, sl, ST, LT, SL) in at["periods"]:
    P(f"| {p} | {d} | {ST:,.0f} | {LT:,.0f} | {SL:,.0f} | {st:,.0f} | {lt:,.0f} | {sl:,.0f} | {st+lt+sl:,.0f} |")
    tot["ST"] += st; tot["LT"] += lt; tot["SL"] += sl
total_tax = sum(tot.values())
P(f"\nTotal tax: {total_tax:,.2f}\n")
P("| class | count | gain Rs | tax Rs |\n|---|---|---|---|")
for c in ["ST", "LT", "SL"]:
    s = ev[ev.cls == c]
    P(f"| {c} | {len(s)} | {s.gain.sum():,.0f} | {tot[c]:,.0f} |")
base = recompute_tax(at["events"])
ceil = recompute_tax(at["events"], relabel_ceiling=True)
n331 = ((ev.hd >= 331) & (ev.hd <= 364) & (ev.cls != "SL")).sum()
P(f"\n331-364 ceiling: {n331} exits relabelled (gain {ev[(ev.hd>=331)&(ev.hd<=364)&(ev.cls!='SL')].gain.sum():,.0f}); "
  f"recomputed baseline tax {base:,.2f} (check vs run {total_tax:,.2f}); relabelled tax {ceil:,.2f}; "
  f"difference {ceil-base:,.2f}\n")

P("## C. Rebalance cost by trade size (pre-tax run)\n")
tr = pd.DataFrame(pt["trades"], columns=["i", "inst", "value", "cost", "nav"])
tr = tr[tr.i != 0].copy()
tr["size"] = tr.value.abs() / tr.nav
tr["turn"] = tr.value.abs()
TC, TT = tr.cost.sum(), tr.turn.sum()
P(f"n = {len(tr)}, total cost = {TC:,.2f}, total turnover = {TT:,.2f}\n")
pc = np.percentile(tr["size"] * 100, [10, 50, 90, 99])
P(f"size percentiles (% NAV, numpy linear): p10 {pc[0]:.4f}, p50 {pc[1]:.4f}, p90 {pc[2]:.4f}, p99 {pc[3]:.4f}\n")
P("| size band | n | cost share % | turnover share % |\n|---|---|---|---|")
s = tr["size"]
for lab, m in [("<0.5%", s < 0.005), ("0.5-1%", (s >= 0.005) & (s < 0.01)),
               ("1-2%", (s >= 0.01) & (s <= 0.02)), (">2%", s > 0.02)]:
    P(f"| {lab} | {m.sum()} | {100*tr.cost[m].sum()/TC:.2f} | {100*tr.turn[m].sum()/TT:.2f} |")
P("\n| band | cost of trades below band Rs | n |\n|---|---|---|")
for b in [0.005, 0.01, 0.02]:
    m = s < b
    P(f"| {100*b:.1f}% | {tr.cost[m].sum():,.2f} | {m.sum()} |")
P("\nBy instrument: " + ", ".join(f"{k}: n={len(v)} cost={v.cost.sum():,.0f}" for k, v in tr.groupby("inst")))

P("\n## D. Diagnostic variants (after-tax CAGR)\n")
b = at["cagr"]
variants = [
    ("baseline", {}),
    ("1 pass-through on session after exit", {"pt_next": True}),
    ("2 tax on first session of April", {"april": True}),
    ("3 same-day post-settle gains to current period", {"sameday_current": True}),
    ("4 no cost on tax-day trades", {"notax_day_cost": True}),
    ("5 LIFO", {"lifo": True}),
    ("6 no basis step-up on pass-through", {"no_stepup": True}),
    ("7 LT threshold >=365", {"lt_ge": True}),
    ("8a lot basis includes buy cost", {"basis_incl_cost": True}),
    ("8b basis incl buy cost AND sale gain net of sell cost", {"basis_incl_cost": True, "net_sell_cost": True}),
    ("8c sale gain net of sell cost only", {"net_sell_cost": True}),
    ("8d no tax day on 2019-03-29 (window starts in March 2019)", {"skip_first_taxday": True}),
    ("8e combo 8a + 7 (two changes)", {"basis_incl_cost": True, "lt_ge": True}),
]
P("| variant | after-tax CAGR % | delta pp | total tax Rs |\n|---|---|---|---|")
res = {}
for n, kw in variants:
    r = run(tax=True, **kw)
    tt = sum(st + lt + sl for (_, _, st, lt, sl, *_r) in r["periods"])
    res[n] = r["cagr"]
    P(f"| {n} | {100*r['cagr']:.4f} | {100*(r['cagr']-b):+.4f} | {tt:,.0f} |")
open(f"{HERE}/RESULT.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))
