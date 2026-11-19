import sys, numpy as np, pandas as pd
D = sys.argv[1] if len(sys.argv) > 1 else "inputs"
closes = pd.read_parquet(f"{D}/closes.parquet"); closes.index = pd.to_datetime(closes.index)
tri = pd.read_csv(f"{D}/m150_tri.csv", parse_dates=["date"]).set_index("date")["tri"].sort_index()
idx_ret = tri.pct_change()
tr = pd.read_csv(f"{D}/trades.csv", parse_dates=["entry_date", "stop_time"])

flags = {"entry_not_session": 0, "stop_not_session": 0, "peak_reset": 0, "empty_leg": 0,
         "beta_n_lt_126": 0, "idx_missing_in_leg": 0, "idx_missing_in_beta": 0}
rows = []
for t in tr.itertuples():
    s = closes[t.ticker].dropna().sort_index()
    r = s.pct_change()
    if t.entry_date not in s.index: flags["entry_not_session"] += 1
    if t.stop_time not in s.index: flags["stop_not_session"] += 1
    pre = s.index[s.index < t.entry_date][-126:]
    pair = pd.DataFrame({"s": r.reindex(pre).values, "m": idx_ret.reindex(pre).values}, index=pre)
    if pair["m"].isna().any(): flags["idx_missing_in_beta"] += 1
    pair = pair.dropna()
    if len(pair) < 126: flags["beta_n_lt_126"] += 1
    beta = np.cov(pair["s"], pair["m"], ddof=1)[0, 1] / np.var(pair["m"], ddof=1)
    w = s[(s.index >= t.entry_date) & (s.index <= t.stop_time)]
    peak = w.idxmax()  # first among ties
    if peak == w.index[-1] and w.index[-1] == t.stop_time or peak == t.stop_time:
        peak = w.index[0]; flags["peak_reset"] += 1
    leg = s.index[(s.index > peak) & (s.index <= t.stop_time)]
    if len(leg) == 0: flags["empty_leg"] += 1
    r_leg = s[t.stop_time] / s[peak] - 1
    mr = idx_ret.reindex(leg)
    if mr.isna().any(): flags["idx_missing_in_leg"] += 1
    rm_leg = float(np.prod(1 + mr.fillna(0).values) - 1)
    rows.append(dict(ticker=t.ticker, cohort=t.cohort, beta=beta, n_beta=len(pair),
                     r_leg=r_leg, rm_leg=rm_leg, a=r_leg - beta * rm_leg))
df = pd.DataFrame(rows)
df.to_csv("per_trade.csv", index=False)
print(flags)
N, F = df[df.cohort == "noise_stop"], df[df.cohort == "false_touch"]
for name, g in [("noise_stop", N), ("false_touch", F)]:
    print(f"{name}: n={len(g)} mean={g.a.mean():.6f} median={g.a.median():.6f}")
diff = F.a.mean() - N.a.mean(); print(f"diff={diff:.6f}")
rng = np.random.default_rng(20261119)
def groups(g):
    u = sorted(g.ticker.unique()); return u, [g.a[g.ticker == k].values for k in u]
un, gn = groups(N); uf, gf = groups(F)
bs = []
for _ in range(2000):
    i = rng.integers(0, len(un), len(un)); j = rng.integers(0, len(uf), len(uf))
    an = np.concatenate([gn[k] for k in i]); af = np.concatenate([gf[k] for k in j])
    bs.append(af.mean() - an.mean())
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f"unique tickers noise={len(un)} false={len(uf)}; CI95=[{lo:.6f}, {hi:.6f}]")
print(f"pooled SD (all a, ddof1)={df.a.std(ddof=1):.6f}")
pv = ((len(N)-1)*N.a.var(ddof=1)+(len(F)-1)*F.a.var(ddof=1))/(len(N)+len(F)-2)
print(f"alt within-group pooled SD={np.sqrt(pv):.6f}")
print(df[["beta","n_beta","r_leg","rm_leg"]].describe().to_string())
