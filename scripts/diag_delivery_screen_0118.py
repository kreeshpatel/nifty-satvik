"""THE 0118 SCREEN — run ONCE as pre-registered (diagnostics/research/preregistry/0118-*.md).

MEASUREMENT: 0 trials. Screen-ledger row #7 (running screen count 7 — stated per the standing rule).
Train entries 2019-01-01..2024-06-30 ONLY; the sealed 2024-07+ slice is never read here.

Builds the PIT delivery features (nq.data.delivery), joins each substrate trade at the last available
date <= its signal-week Friday, and answers the three pre-registered questions with conditional
(ext-band x CRS-tercile) effects, bootstrap CIs, per-year signs, and the ADV-tercile liquidity-proxy
check. One run; no retunes.

    python scripts/diag_delivery_screen_0118.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.delivery import DELIVERY_RAW_PATH, FEATURES, apply_alias_map, derive_delivery_features  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

CTX = ROOT / "research" / "substrate" / "context_windows.parquet"
TRAIN_LO, TRAIN_HI = "2019-01-01", "2024-06-30"
RNG = np.random.default_rng(20260727)


def ci_diff(a, b, n=2000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 20 or len(b) < 20:
        return np.nan, np.nan, np.nan
    d = [RNG.choice(a, len(a)).mean() - RNG.choice(b, len(b)).mean() for _ in range(n)]
    return float(a.mean() - b.mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main() -> int:
    print("SCREEN LEDGER: this is screen #7 against the banked label dataset (rows 1-6 = 0116/0117).")
    oh = load_ohlcv_cache(OHLCV_CACHE)
    raw = apply_alias_map(pd.read_parquet(DELIVERY_RAW_PATH))
    raw["date"] = pd.to_datetime(raw["date"]).astype("datetime64[ns]")
    # daily returns for the down-day feature
    rets = []
    for s, g in raw.groupby("symbol"):
        if s in oh:
            r = oh[s]["Close"].pct_change()
            r.index = pd.to_datetime(r.index).astype("datetime64[ns]")
            rr = g[["date"]].copy(); rr["ret"] = r.reindex(g["date"]).to_numpy()
            rets.append(rr["ret"])
        else:
            rets.append(pd.Series(np.nan, index=g.index))
    raw["ret"] = pd.concat(rets).sort_index()
    feats = derive_delivery_features(raw)

    t = pd.read_parquet(CTX)
    col = {c.lower(): c for c in t.columns}
    t["entry_date"] = pd.to_datetime(t[col["entry_date"]])
    t = t[(t["entry_date"] >= TRAIN_LO) & (t["entry_date"] <= TRAIN_HI)].copy()   # TRAIN ONLY
    t["sig_fri"] = (t["entry_date"] - pd.to_timedelta(t["entry_date"].dt.weekday + 3, unit="D")).astype("datetime64[ns]")
    # join: last feature row <= sig_fri per symbol
    fa = {s: (g["date"].to_numpy(), g[list(FEATURES)].to_numpy()) for s, g in feats.groupby("symbol")}
    F = np.full((len(t), len(FEATURES)), np.nan)
    for k, (_, r) in enumerate(t.iterrows()):
        a = fa.get(r[col["ticker"]])
        if a is None:
            continue
        i = np.searchsorted(a[0], np.datetime64(r["sig_fri"]), "right") - 1
        if i >= 0 and (r["sig_fri"] - pd.Timestamp(a[0][i])).days <= 10:
            F[k] = a[1][i]
    for j, f in enumerate(FEATURES):
        t[f] = F[:, j]
    print(f"TRAIN trades {len(t)} | feature join coverage: "
          f"{ {f: round(t[f].notna().mean()*100) for f in FEATURES} }")

    rr = col["r"]; ext = col.get("ext_vs_sma"); crs = col.get("rank_crs")
    t["ext_band"] = pd.cut(t[ext], [-np.inf, 10, 20, np.inf], labels=["e0", "e1", "e2"])
    t["crs_t"] = pd.qcut(t[crs].rank(method="first"), 3, labels=["c0", "c1", "c2"])
    adv = []
    for _, r in t.iterrows():
        g = oh.get(r[col["ticker"]])
        if g is None:
            adv.append(np.nan); continue
        g_ = g[g.index < r["entry_date"]]
        adv.append(float((g_["Close"] * g_["Volume"]).tail(20).mean()) if len(g_) > 25 else np.nan)
    t["adv_t"] = pd.qcut(pd.Series(adv).rank(method="first"), 3, labels=["a0", "a1", "a2"])
    t["yr"] = t["entry_date"].dt.year

    def cond_contrast(sub_a, sub_b, f):
        """n-weighted mean(f|a)-mean(f|b) within ext x crs cells."""
        sp, wt = [], []
        both = pd.concat([sub_a.assign(_g=1), sub_b.assign(_g=0)])
        for _, cell in both.groupby(["ext_band", "crs_t"], observed=True):
            a, b = cell[cell["_g"] == 1][f].dropna(), cell[cell["_g"] == 0][f].dropna()
            if len(a) < 15 or len(b) < 15:
                continue
            sp.append(a.mean() - b.mean()); wt.append(len(cell))
        return float(np.average(sp, weights=wt)) if sp else np.nan

    print("\n=== Q1: false_touch vs noise_stop (does delivery know which stop victim recovers?) ===")
    ft = t[t["false_touch"] == True]; ns = t[t["noise_stop"] == True]   # noqa: E712
    print(f"cohorts: false_touch n={len(ft)}, noise_stop n={len(ns)}")
    for f in FEATURES:
        m, lo, hi = ci_diff(ft[f], ns[f])
        cd = cond_contrast(ft, ns, f)
        star = " *" if (lo == lo and (lo > 0 or hi < 0)) else ""
        print(f"  {f:<12} ft-vs-ns raw {m:+.3f} [{lo:+.3f},{hi:+.3f}]{star} | conditional {cd:+.3f}")

    print("\n=== Q2: exit_too_early winners vs ordinary winners ===")
    w = t[t[rr] > 0]
    te = w[w["exit_too_early"] == True]; tn = w[w["exit_too_early"] == False]   # noqa: E712
    for f in FEATURES:
        m, lo, hi = ci_diff(te[f], tn[f])
        star = " *" if (lo == lo and (lo > 0 or hi < 0)) else ""
        print(f"  {f:<12} early-vs-ord raw {m:+.3f} [{lo:+.3f},{hi:+.3f}]{star}")

    print("\n=== Q3: conditional R-gradient (top-vs-bottom feature tercile, within cells) + per-year ===")
    for f in FEATURES:
        s = t.dropna(subset=[f, rr]).copy()
        if len(s) < 400:
            print(f"  {f:<12} insufficient n"); continue
        sp, wt, hi_all, lo_all = [], [], [], []
        for _, cell in s.groupby(["ext_band", "crs_t"], observed=True):
            if len(cell) < 30:
                continue
            q = pd.qcut(cell[f].rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
            hi_, lo_ = cell[q == 2][rr], cell[q == 0][rr]
            if len(hi_) < 8 or len(lo_) < 8:
                continue
            sp.append(hi_.mean() - lo_.mean()); wt.append(len(cell))
            hi_all.append(hi_.to_numpy()); lo_all.append(lo_.to_numpy())
        cd = float(np.average(sp, weights=wt)) if sp else np.nan
        _, lo, hi = ci_diff(np.concatenate(hi_all) if hi_all else [], np.concatenate(lo_all) if lo_all else [])
        signs = []
        for y, gy in s.groupby("yr"):
            if len(gy) < 60:
                continue
            q = pd.qcut(gy[f].rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
            signs.append(np.sign(gy[q == 2][rr].mean() - gy[q == 0][rr].mean()))
        dom = int(max((np.array(signs) > 0).sum(), (np.array(signs) < 0).sum())) if signs else 0
        # liquidity-proxy check: does the gradient survive within ADV terciles?
        adv_ok = []
        for _, ga in s.groupby("adv_t", observed=True):
            if len(ga) < 150:
                continue
            q = pd.qcut(ga[f].rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
            adv_ok.append(np.sign(ga[q == 2][rr].mean() - ga[q == 0][rr].mean()))
        print(f"  {f:<12} cond dR {cd:+.3f} [{lo:+.3f},{hi:+.3f}] | yr-sign {dom}/{len(signs)} | "
              f"ADV-tercile signs {adv_ok}")
    print("\nBar: >=0.15R-equivalent with CI excluding 0 on Q1 or Q3, sign >=4/6 years, surviving ADV "
          "conditioning. Anything less -> KILL (delivery closes; census #2 is next).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
