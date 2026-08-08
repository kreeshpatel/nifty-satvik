"""THE 0120 SCREEN - run ONCE as pre-registered. MEASUREMENT: 0 trials. Ledger row #9 (count 9).
Train entries 2019-01-01..2024-06-30 ONLY; sealed 2024H2+ never read.

    python scripts/diag_earnings_screen_0120.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table  # noqa: E402
from nq.data.delivery import apply_alias_map  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

TRAIN_LO, TRAIN_HI = "2019-01-01", "2024-06-30"
RNG = np.random.default_rng(20260727)

def ci_diff(a, b, n=2000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 20 or len(b) < 20:
        return np.nan, np.nan, np.nan
    d = [RNG.choice(a, len(a)).mean() - RNG.choice(b, len(b)).mean() for _ in range(n)]
    return float(a.mean()-b.mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))

def main() -> int:
    print("SCREEN LEDGER: row #9 (running count 9; sealed opens 1).")
    ev = build_event_table(apply_alias_map(pd.read_parquet(EARNINGS_RAW_PATH)))
    evs = {s: g.sort_values("event_date")[["event_date", "ann_ts"]].to_numpy() for s, g in ev.groupby("symbol")}
    t = pd.read_parquet(ROOT/"research"/"substrate"/"context_windows.parquet")
    col = {c.lower(): c for c in t.columns}
    for c in ("entry_date", "exit_date"):
        t[c] = pd.to_datetime(t[col[c]])
    t = t[(t["entry_date"] >= TRAIN_LO) & (t["entry_date"] <= TRAIN_HI)].copy()
    t["sig_fri"] = t["entry_date"] - pd.to_timedelta(t["entry_date"].dt.weekday + 3, unit="D")
    rr, ext, crs = col["r"], col["ext_vs_sma"], col["rank_crs"]
    t["ext_band"] = pd.cut(t[ext], [-np.inf, 10, 20, np.inf], labels=["e0", "e1", "e2"])
    t["crs_t"] = pd.qcut(t[crs].rank(method="first"), 3, labels=["c0", "c1", "c2"])
    t["yr"] = t["entry_date"].dt.year
    oh = load_ohlcv_cache(OHLCV_CACHE)
    adv = []
    for _, r in t.iterrows():
        g = oh.get(r[col["ticker"]])
        g_ = g[g.index < r["entry_date"]] if g is not None else None
        adv.append(float((g_["Close"]*g_["Volume"]).tail(20).mean()) if g_ is not None and len(g_) > 25 else np.nan)
    t["adv_t"] = pd.qcut(pd.Series(adv).rank(method="first"), 3, labels=["a0", "a1", "a2"])

    exp_n, prox, q3ev = [], [], []
    for _, r in t.iterrows():
        a = evs.get(r[col["ticker"]])
        if a is None:
            exp_n.append(np.nan); prox.append(np.nan); q3ev.append(np.nan); continue
        evd = a[:, 0]
        exp_n.append(int(((evd >= np.datetime64(r["entry_date"])) & (evd <= np.datetime64(r["exit_date"]))).sum()))
        monday = r["sig_fri"] + pd.Timedelta(days=3)
        known = a[a[:, 1] <= np.datetime64(r["sig_fri"])]
        prox.append(bool(((known[:, 0] >= np.datetime64(monday)) &
                          (known[:, 0] <= np.datetime64(monday + pd.Timedelta(days=14)))).any()) if len(known) else False)
        q3ev.append(bool(((evd > np.datetime64(r["exit_date"])) &
                          (evd <= np.datetime64(r["exit_date"] + pd.Timedelta(days=21)))).any()))
    t["n_events_held"] = exp_n; t["known_event_14cd"] = prox; t["event_post_exit21"] = q3ev

    def cond(sub_a, sub_b, f=rr):
        sp, wt = [], []
        both = pd.concat([sub_a.assign(_g=1), sub_b.assign(_g=0)])
        for _, cell in both.groupby(["ext_band", "crs_t"], observed=True):
            x, y = cell[cell["_g"] == 1][f].dropna(), cell[cell["_g"] == 0][f].dropna()
            if len(x) < 15 or len(y) < 15:
                continue
            sp.append(x.mean()-y.mean()); wt.append(len(cell))
        return float(np.average(sp, weights=wt)) if sp else np.nan

    print("\n=== Q1 (label-side): holding THROUGH a results event ===")
    e1 = t[t["n_events_held"] >= 1]; e0 = t[t["n_events_held"] == 0]
    print(f"BASE RATES (the event-frequency trap check): exposed {len(e1)} ({len(e1)/len(t)*100:.0f}%) "
          f"vs event-free {len(e0)} ({len(e0)/len(t)*100:.0f}%)")
    m, lo, hi = ci_diff(e1[rr], e0[rr])
    print(f"  dR exposed-vs-free: raw {m:+.3f} [{lo:+.3f},{hi:+.3f}] | conditional {cond(e1, e0):+.3f}")
    ft = t[t["false_touch"] == True]; ns = t[t["noise_stop"] == True]  # noqa: E712
    m2, lo2, hi2 = ci_diff(ft["n_events_held"].clip(0, 1), ns["n_events_held"].clip(0, 1))
    print(f"  event-struck rate: false_touch {ft['n_events_held'].clip(0,1).mean()*100:.0f}% vs "
          f"noise_stop {ns['n_events_held'].clip(0,1).mean()*100:.0f}% -> d {m2*100:+.1f}pp [{lo2*100:+.1f},{hi2*100:+.1f}]")

    print("\n=== Q2 (feature-side, PIT): KNOWN event within 14cd of entry-week Monday ===")
    p1 = t[t["known_event_14cd"] == True]; p0 = t[t["known_event_14cd"] == False]  # noqa: E712
    print(f"activation: {len(p1)} trades ({len(p1)/len(t)*100:.0f}%)")
    m3, lo3, hi3 = ci_diff(p1[rr], p0[rr])
    print(f"  dR known-near-event vs not: raw {m3:+.3f} [{lo3:+.3f},{hi3:+.3f}] | conditional {cond(p1, p0):+.3f}")
    signs = []
    for y, gy in t.groupby("yr"):
        a_, b_ = gy[gy["known_event_14cd"] == True][rr], gy[gy["known_event_14cd"] == False][rr]  # noqa: E712
        if len(a_) >= 15 and len(b_) >= 30:
            signs.append(np.sign(a_.mean()-b_.mean()))
    dom = int(max((np.array(signs) > 0).sum(), (np.array(signs) < 0).sum())) if signs else 0
    print(f"  per-year sign consistency: {dom}/{len(signs)}")
    advs = []
    for _, ga in t.groupby("adv_t", observed=True):
        a_, b_ = ga[ga["known_event_14cd"] == True][rr], ga[ga["known_event_14cd"] == False][rr]  # noqa: E712
        if len(a_) >= 15 and len(b_) >= 50:
            advs.append(round(float(a_.mean()-b_.mean()), 2))
    print(f"  ADV-tercile deltas: {advs}")

    print("\n=== Q3 (label-side): winners - true event inside 21d post-exit vs exit_too_early ===")
    w = t[t[rr] > 0]
    a_ = w[w["event_post_exit21"] == True]; b_ = w[w["event_post_exit21"] == False]  # noqa: E712
    r1 = a_["exit_too_early"].astype(float).mean(); r0 = b_["exit_too_early"].astype(float).mean()
    m4, lo4, hi4 = ci_diff(a_["exit_too_early"].astype(float), b_["exit_too_early"].astype(float))
    print(f"  exit_too_early rate: event-ahead {r1*100:.0f}% (n={len(a_)}) vs none {r0*100:.0f}% "
          f"(n={len(b_)}) -> d {m4*100:+.1f}pp [{lo4*100:+.1f},{hi4*100:+.1f}]")
    print("\nBar: >=0.15R-equivalent (or cohort-rate d) with CI excluding 0, sign >=4/6 years, ADV-robust.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
