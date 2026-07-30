"""Stage 1 of the post-entry study (MEASUREMENT, 0 trials) — mine the banked 0116 labels.

Three readouts on TRAIN years only (2019-01..2024-06; the 2024-07+ sealed set is not read):
 1. WHIPSAW vs FALSE-TOUCH: are noise_stop trades (stopped, then recovered) distinguishable from
    false_touch trades (stopped, never recovered) AT STOP TIME, using only bars <= exit?
 2. LEFT-ON-TABLE: do day-10 in-flight signatures mark the exit_too_early winners while open?
 3. ROTATION BOUND: hindsight upper bound on any cut/rotate rule — R-per-week of capital in the
    capped book's eventual losers vs the same-week substrate alternative.

In-flight features use ONLY bars up to the decision time inside the trade (the restated firewall);
post-exit labels grade, never feed. Committed per reproduce-before-trust.

    python scripts/diag_postentry_stage1.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

CTX = ROOT / "research" / "substrate" / "context_windows.parquet"
CAPPED = ROOT / "research" / "exports" / "bhanushali_weekly_rank_0094_trades.csv"
TRAIN_LO, TRAIN_HI = "2019-01-01", "2024-06-30"
RNG = np.random.default_rng(20260727)


def ci_diff(a, b, n=2000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = [RNG.choice(a, len(a)).mean() - RNG.choice(b, len(b)).mean() for _ in range(n)]
    return float(np.mean(a) - np.mean(b)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main() -> int:
    d = pd.read_parquet(CTX)
    col = {c.lower(): c for c in d.columns}
    en_d, ex_d, rr = col["entry_date"], col["exit_date"], col["r"]
    d[en_d] = pd.to_datetime(d[en_d]); d[ex_d] = pd.to_datetime(d[ex_d])
    d = d[(d[en_d] >= TRAIN_LO) & (d[en_d] <= TRAIN_HI)].copy()   # TRAIN ONLY
    oh = load_ohlcv_cache(OHLCV_CACHE)
    print(f"TRAIN slice: {len(d)} trades; sealed set untouched")

    # ── in-flight path features (bars strictly within [entry, exit] / up to day-10) ──
    wk44 = {}
    def sma44_at(t, dt):
        if t not in oh: return np.nan
        if t not in wk44:
            w = oh[t]["Close"].resample("W-FRI").last().dropna()
            wk44[t] = (w, w.rolling(44).mean())
        w, s = wk44[t]; p = w.index[w.index <= dt]
        return (float(w.loc[p[-1]]), float(s.loc[p[-1]])) if len(p) and s.loc[p[-1]] == s.loc[p[-1]] else (np.nan, np.nan)

    rows = []
    for i, r0 in d.iterrows():
        t = r0[col["ticker"]]
        if t not in oh: continue
        g = oh[t]; seg = g[(g.index >= r0[en_d]) & (g.index <= r0[ex_d])]
        if len(seg) < 3: continue
        en, stp = float(r0[col["entry"]]), float(r0[col["stop"]])
        risk = en - stp
        if risk <= 0: continue
        c = seg["Close"].to_numpy(float); o = seg["Open"].to_numpy(float); lo = seg["Low"].to_numpy(float)
        trough = int(np.argmin(lo))
        mae_depth = (lo[trough] - en) / risk                      # in R (negative)
        tt_trough = trough + 1
        mae_speed = mae_depth / tt_trough
        # gap share of the decline entry -> trough
        gaps = o[1:trough + 1] - c[:trough]; neg_gap = -gaps[gaps < 0].sum()
        tot_dn = max(en - lo[trough], 1e-9)
        dd_gap_share = float(neg_gap / tot_dn)
        wcl, wsma = sma44_at(t, r0[ex_d])
        wk_intact = bool(wcl > wsma) if wcl == wcl and wsma == wsma else None
        # day-10 in-flight marks (only defined when held that long)
        f10 = {}
        if len(seg) >= 12:
            s10 = seg.iloc[:10]
            r10 = s10["Close"].pct_change().dropna()
            f10 = dict(mfe10=(s10["High"].max() - en) / risk, mae10=(s10["Low"].min() - en) / risk,
                       vol10=float(r10.std()), above10=float((s10["Close"] > en).mean()),
                       ret10=(s10["Close"].iloc[-1] - en) / risk)
        rows.append(dict(idx=i, days_held=len(seg), mae_depth=mae_depth, tt_trough=tt_trough,
                         mae_speed=mae_speed, dd_gap_share=dd_gap_share, wk_intact=wk_intact, **f10))
    F = pd.DataFrame(rows).set_index("idx")
    d = d.join(F, how="inner")
    print(f"in-flight features computed for {len(d)}")

    # ════ 1. WHIPSAW (noise_stop) vs FALSE-TOUCH at stop time ════
    ns = d[d["noise_stop"] == True]; ft = d[d["false_touch"] == True]   # noqa: E712
    print(f"\n=== 1. WHIPSAW vs FALSE-TOUCH (train: noise_stop n={len(ns)}, false_touch n={len(ft)}) ===")
    print(f"{'feature':<14}{'noise_stop':>11}{'false_tch':>11}{'diff':>8}{'CI':>19}")
    for f in ("mae_depth", "tt_trough", "mae_speed", "dd_gap_share", "days_held"):
        a, b = ns[f].dropna(), ft[f].dropna()
        m, lo_, hi_ = ci_diff(a, b)
        star = " *" if (lo_ > 0 or hi_ < 0) else ""
        print(f"{f:<14}{a.mean():>11.3f}{b.mean():>11.3f}{m:>+8.3f}  [{lo_:+.3f},{hi_:+.3f}]{star}")
    wi = d[d["noise_stop"].notna() | d["false_touch"].notna()]
    for lab, sub in (("noise_stop", ns), ("false_touch", ft)):
        v = sub["wk_intact"].dropna()
        print(f"  wk_intact at stop: {lab:<12} {v.mean()*100:.0f}% (n={len(v)})")
    # giveback quantification
    exit_px = d[col["exit_px"]] if col.get("exit_px") else None
    gb = (ns["post_ret21"] * d.loc[ns.index, col["exit_px"]] / (d.loc[ns.index, col["entry"]] - d.loc[ns.index, col["stop"]])).dropna()
    print(f"  whipsaw giveback (post-exit 21d move in R, noise_stop cohort): total {gb.sum():+.0f}R "
          f"across {len(gb)} trades (mean {gb.mean():+.2f}R) — the HINDSIGHT pool a discriminator could chase")

    # ════ 2. LEFT-ON-TABLE: day-10 marks vs exit_too_early (winners held >=12d) ════
    w = d[(d[rr] > 0) & d["mfe10"].notna()]
    te = w[w["exit_too_early"] == True]; tn = w[w["exit_too_early"] == False]   # noqa: E712
    print(f"\n=== 2. LEFT-ON-TABLE at day-10 (winners: too_early n={len(te)} vs not n={len(tn)}) ===")
    for f in ("mfe10", "mae10", "vol10", "above10", "ret10"):
        m, lo_, hi_ = ci_diff(te[f].dropna(), tn[f].dropna())
        star = " *" if (lo_ > 0 or hi_ < 0) else ""
        print(f"  {f:<8} too_early {te[f].mean():+.3f} vs other {tn[f].mean():+.3f} -> d {m:+.3f} [{lo_:+.3f},{hi_:+.3f}]{star}")
    # does day-10 strength predict final opportunity quality (the pyramid premise), all trades?
    a = d.dropna(subset=["ret10", "opp_quality_R"])
    from scipy.stats import spearmanr
    ic = spearmanr(a["ret10"], a["opp_quality_R"]).statistic
    ic2 = spearmanr(a["ret10"], a[rr]).statistic
    # per-year persistence of ret10 -> final R
    yr_ic = {y: spearmanr(g["ret10"], g[rr]).statistic for y, g in a.groupby(a[en_d].dt.year) if len(g) > 80}
    print(f"  IC(ret10 -> opp_quality_R) {ic:+.3f} | IC(ret10 -> final R) {ic2:+.3f}")
    print("  per-year IC(ret10->R):", {y: round(v, 2) for y, v in yr_ic.items()})

    # ════ 3. ROTATION BOUND (capped book losers vs same-week substrate queue) ════
    cap = pd.read_csv(CAPPED); cap["entry_date"] = pd.to_datetime(cap["entry_date"])
    cap = cap[(cap["entry_date"] >= TRAIN_LO) & (cap["entry_date"] <= TRAIN_HI)]
    sub = d.copy(); sub["iw"] = sub[en_d].dt.isocalendar().year.astype(str) + "-" + sub[en_d].dt.isocalendar().week.astype(str)
    cap["iw"] = cap["entry_date"].dt.isocalendar().year.astype(str) + "-" + cap["entry_date"].dt.isocalendar().week.astype(str)
    wk_alt = sub.groupby("iw")[rr].median()
    losers = cap[cap["R"] < 0]
    alt = losers["iw"].map(wk_alt).fillna(0.0)
    bound = float((alt - losers["R"]).clip(lower=0).sum())
    print(f"\n=== 3. ROTATION BOUND (train, capped book) ===")
    print(f"  capped losers n={len(losers)} totalR {losers['R'].sum():+.1f} | same-week substrate median-alt R "
          f"sum {alt.sum():+.1f}")
    print(f"  HINDSIGHT upper bound on any cut+rotate rule: +{bound:.1f}R over 5.5y "
          f"(~{bound/5.5:.1f}R/yr) — requires knowing losers in advance; any real rule captures a fraction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
