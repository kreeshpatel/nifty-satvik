"""Stage-2 (free half) — does any ENTRY-TIME feature predict trade outcome OUT-OF-SAMPLE?

Trains a LightGBM classifier on the wide substrate to separate winning from losing trades using
ONLY features knowable at entry (strict leakage guard — no MAE/MFE/held/reason/R). Trained on
2019-22, judged on the 2023-26 HOLDOUT only (in-sample fit on this small sample is meaningless —
[[pursue-learning-bot-judge-oos]]). Reports holdout AUC, holdout permutation importance (OOS-honest),
and the practical test: does the model's predicted-good quintile actually realize higher meanR OOS?

    python scripts/diag_substrate_ml.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lightgbm as lgb  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

SUB = ROOT / "research" / "substrate" / "trades.parquet"

# Entry-time, PIT-safe features ONLY. Everything outcome/forward is excluded by omission.
CONT_FEATURES = ["ext_vs_sma", "risk_pct", "rank_crs", "atr_pct", "vol_ratio",
                 "dist_52wh_pct", "ep", "bp", "roe", "low_debt"]
LEAK_COLS = ["mae_pct", "mfe_pct", "mae_first2wk", "held_weeks", "reason", "exit_px", "R", "exit_date"]

PARAMS = dict(objective="binary", n_estimators=300, num_leaves=15, max_depth=4,
              learning_rate=0.02, subsample=0.8, colsample_bytree=0.8,
              min_child_samples=40, reg_lambda=1.0, random_state=0, verbose=-1)


def _xy(df, use_setup):
    cols = list(CONT_FEATURES)
    X = df[cols].copy()
    if use_setup:
        d = pd.get_dummies(df["setup"], prefix="s")
        X = pd.concat([X.reset_index(drop=True), d.reset_index(drop=True)], axis=1)
    y = (df["R"].to_numpy() > 0).astype(int)
    return X, y


def run(df, use_setup, label):
    tr = df[df.split == "train"]
    ho = df[df.split == "holdout"]
    Xtr, ytr = _xy(tr, use_setup)
    Xho, yho = _xy(ho, use_setup)
    Xho = Xho.reindex(columns=Xtr.columns, fill_value=0)  # align dummy cols
    m = lgb.LGBMClassifier(**PARAMS)
    m.fit(Xtr, ytr)
    p_tr = m.predict_proba(Xtr)[:, 1]
    p_ho = m.predict_proba(Xho)[:, 1]
    auc_tr = roc_auc_score(ytr, p_tr)
    auc_ho = roc_auc_score(yho, p_ho)
    base = yho.mean()
    print(f"\n=== {label} (setup_dummies={use_setup}) ===")
    print(f"  train N={len(ytr)} win={ytr.mean()*100:.1f}%   holdout N={len(yho)} win={base*100:.1f}%")
    print(f"  AUC  train={auc_tr:.3f} (in-sample, ignore)   HOLDOUT={auc_ho:.3f}  <-- the judge")
    # practical test: realized meanR by predicted-score quintile on the HOLDOUT
    ho2 = ho.copy(); ho2["p"] = p_ho
    ho2["q"] = pd.qcut(ho2["p"], 5, labels=False, duplicates="drop")
    print("  holdout realized outcome by predicted-good quintile:")
    for q, g in ho2.groupby("q"):
        print(f"    Q{int(q)+1}: N={len(g):4d}  win={ (g.R>0).mean()*100:5.1f}%  meanR={g.R.mean():+.3f}  medR={g.R.median():+.3f}")
    # OOS-honest permutation importance on the holdout
    pi = permutation_importance(m, Xho, yho, scoring="roc_auc", n_repeats=10, random_state=0)
    imp = pd.Series(pi.importances_mean, index=Xho.columns).sort_values(ascending=False)
    print("  holdout permutation importance (top 8, drop in AUC):")
    for k, v in imp.head(8).items():
        print(f"    {k:16s} {v:+.4f}")
    return auc_ho


def direction(df):
    """For the strongest continuous features, holdout win% by feature quintile (direction of edge)."""
    ho = df[df.split == "holdout"]
    print("\n=== holdout win% by feature quintile (direction) ===")
    for f in ["ext_vs_sma", "dist_52wh_pct", "vol_ratio", "atr_pct", "roe"]:
        s = ho[[f, "R"]].dropna()
        if len(s) < 100:
            continue
        s = s.copy(); s["q"] = pd.qcut(s[f], 5, labels=False, duplicates="drop")
        wr = s.groupby("q").apply(lambda g: (g.R > 0).mean() * 100)
        rng = f"[{s[f].min():.1f}..{s[f].max():.1f}]"
        print(f"  {f:14s} {rng:20s} win% by quintile: " + " ".join(f"{w:4.0f}" for w in wr))


if __name__ == "__main__":
    df = pd.read_parquet(SUB)
    df = df[df.split.isin(["train", "holdout"])].reset_index(drop=True)
    print(f"substrate: train={ (df.split=='train').sum()}  holdout={ (df.split=='holdout').sum()}")
    a1 = run(df, use_setup=False, label="continuous features only")
    a2 = run(df, use_setup=True, label="continuous + setup identity")
    direction(df)
    print(f"\nSUMMARY holdout AUC: continuous-only={a1:.3f}  +setup={a2:.3f}  (0.50 = no OOS signal)")
