"""L3 — CONVICTION FILL-RANKING: the last registry-cleared in-sample lever.

The live book activates 6,359 entry windows and funds only 168 (**2.6%**), skipping 19,728 signal-days
for lack of cash while holding ~7 names at all times. So WHO gets the scarce capital is the dominant
decision — and the only change that ever worked on this book (0094) was exactly a fill-ordering change
(CRS-rank). This tests replacing CRS-rank with a TRAINED multi-feature conviction score.

Non-diluting by construction: the trade SET is unchanged (nothing added or dropped) — only the ORDER in
which candidates are offered the cash.

Clean OOS design: the ranker is trained ONLY on 2019-2021 trades and judged on the **2022-26 continuous
slice**, which it has never seen. Baseline to beat: **1.29**.

Guards: R1 (baseline asserted 1.034/-34.8%/168) · R3 (2022-26 slice) · R11 (a loss is a FINDING).

    python scripts/diag_conviction_rank.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from nq.data.weekly import load_weekly_panel
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import P2_EXIT

FEATS = ["crs_dist", "ext_sig", "risk_frac", "slope44", "atr_pct", "vol_ratio", "dist_52wh"]
PARAMS = dict(objective="binary", n_estimators=250, num_leaves=15, max_depth=4, learning_rate=0.02,
              subsample=0.8, colsample_bytree=0.8, min_child_samples=30, reg_lambda=1.0,
              random_state=0, verbose=-1)
TRAIN_LO, TRAIN_HI = pd.Timestamp("2019-01-01"), pd.Timestamp("2021-12-31")


def weekly_featmap():
    wp = load_weekly_panel(cache=True).sort_values(["ticker", "week_end"])
    wp["tr_pct"] = (wp["h"] - wp["l"]) / wp["c"]
    g = wp.groupby("ticker")
    wp["atr_pct"] = g["tr_pct"].transform(lambda x: x.rolling(10).mean()) * 100
    wp["vol_ratio"] = g["v"].transform(lambda x: x / x.rolling(10).mean().shift(1))
    wp["h52"] = g["h"].transform(lambda x: x.rolling(52).max())
    return {(r.ticker, r.week_end): (r.c, r.sma44, r.slope44, r.atr_pct, r.vol_ratio, r.h52)
            for r in wp.itertuples()}


def window_features(P, fmap):
    """Per entry window: features from the COMPLETED signal week (the bar before the entry week) -> PIT-safe."""
    rows = {}
    for t, s in P.items():
        dates = pd.DatetimeIndex(s["dates"])
        for e0, win in s["entry_win"].items():
            if e0 < 1:
                continue
            sig_date = dates[e0 - 1]                    # last day of the SIGNAL week
            f = fmap.get((t, sig_date))
            if f is None:
                continue
            c, sma, slope, atr, vr, h52 = f
            if not (c and c > 0 and sma and sma == sma):
                continue
            stop = win[1]
            rows[(t, e0)] = dict(
                crs_dist=float(win[3]), ext_sig=float(c / sma - 1.0),
                risk_frac=float((c - stop) / c) if c > 0 else np.nan,
                slope44=float(slope) if slope == slope else np.nan,
                atr_pct=float(atr) if atr == atr else np.nan,
                vol_ratio=float(vr) if vr == vr else np.nan,
                dist_52wh=float(c / h52 - 1.0) if (h52 and h52 > 0) else np.nan,
                sig_date=sig_date)
    return rows


def labels_from_uncapped(P, mem):
    """Outcome per entry window from the UNCAPPED touch run (every signal fills => a label for each)."""
    led = []
    R94.backtest(P, mem, ledger=led, start="2017-01-01", uncapped=True, **P2_EXIT)
    didx = {t: {d: i for i, d in enumerate(pd.DatetimeIndex(s["dates"]))} for t, s in P.items()}
    dmap = {t: {d: e0 for e0, w in s["entry_win"].items() for d in w[0]} for t, s in P.items()}
    lab = {}
    for r in led:
        t = r["tkr"]; j0 = didx[t].get(pd.Timestamp(r["entry_date"]))
        e0 = dmap[t].get(j0) if j0 is not None else None
        if e0 is not None:
            lab[(t, e0)] = 1 if r["R"] > 0 else 0
    return lab


def stats(curve):
    e = curve.sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    rr = r[r.index >= "2022-01-01"]
    return dict(sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan,
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                dd=(e / e.cummax() - 1).min(),
                s22=rr.mean() / rr.std() * np.sqrt(252) if rr.std() else np.nan)


def main():
    ohlcv = corrected_universe(); mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)                       # touch-only = the LIVE book

    # ---- R1 baseline assertion ----
    mA = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(mA["sharpe"] - 1.034) < 0.005 and mA["trades"] == 168, "R1 baseline FAILED"
    a = stats(mA["curve"])

    fmap = weekly_featmap()
    W = window_features(P, fmap)
    lab = labels_from_uncapped(P, mem)
    print(f"entry windows with features: {len(W)}   labelled (uncapped outcomes): {len(lab)}")

    # ---- train the ranker on 2019-2021 ONLY ----
    keys = [k for k in W if k in lab]
    tr_keys = [k for k in keys if TRAIN_LO <= W[k]["sig_date"] <= TRAIN_HI]
    ho_keys = [k for k in keys if W[k]["sig_date"] > TRAIN_HI]
    Xtr = pd.DataFrame([{f: W[k][f] for f in FEATS} for k in tr_keys])
    ytr = np.array([lab[k] for k in tr_keys])
    Xho = pd.DataFrame([{f: W[k][f] for f in FEATS} for k in ho_keys])
    yho = np.array([lab[k] for k in ho_keys])
    print(f"train(2019-21) N={len(ytr)} win={ytr.mean()*100:.1f}%   OOS(2022-26) N={len(yho)} win={yho.mean()*100:.1f}%")
    m = lgb.LGBMClassifier(**PARAMS).fit(Xtr, ytr)
    print(f"ranker AUC: train={roc_auc_score(ytr, m.predict_proba(Xtr)[:,1]):.3f} (ignore)  "
          f"OOS 2022-26={roc_auc_score(yho, m.predict_proba(Xho)[:,1]):.3f}  <-- the judge")

    # ---- score EVERY window, run the capped book ranked by conviction ----
    allk = list(W)
    Xall = pd.DataFrame([{f: W[k][f] for f in FEATS} for k in allk])
    sc = m.predict_proba(Xall)[:, 1]
    conv = {k: float(s) for k, s in zip(allk, sc)}
    mC = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, fill_order="conviction", conv_score=conv, **P2_EXIT)
    c = stats(mC["curve"])

    print("\n=== capped Rs10L book — fill ordering (trade SET identical; only ORDER changes) ===")
    print(f"  {'config':30s} {'tr':>4s} {'Sharpe':>6s} {'CAGR':>6s} {'MaxDD':>7s} {'22-26':>6s}")
    print(f"  {'A  CRS-rank (live baseline)':30s} {mA['trades']:4d} {a['sharpe']:6.2f} {a['cagr']*100:5.1f}% "
          f"{a['dd']*100:6.1f}% {a['s22']:6.2f}")
    print(f"  {'C  CONVICTION-rank (L3)':30s} {mC['trades']:4d} {c['sharpe']:6.2f} {c['cagr']*100:5.1f}% "
          f"{c['dd']*100:6.1f}% {c['s22']:6.2f}")
    verdict = "BEATS baseline" if c["s22"] > a["s22"] else "LOSES -> a FINDING, not a retune trigger (R11)"
    print(f"\n  2022-26 gate (OOS for the ranker): {c['s22']:.2f} vs {a['s22']:.2f} -> {verdict}")


if __name__ == "__main__":
    main()
