"""Blind replica of the Amendment-2 harness-bias test, from SPEC.md only."""
import glob
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.join(HERE, "inputs")

ew = pd.read_csv(os.path.join(INP, "ew_universe.csv"), parse_dates=["date"]).set_index("date")["ew_universe_ret"]
assert ew.index.is_unique


def sharpe(x):
    return x.mean() / x.std(ddof=1) * np.sqrt(252)


rows = []
diag = []
for f in sorted(glob.glob(os.path.join(INP, "seed_*.csv"))):
    s = pd.read_csv(f, parse_dates=["date"]).set_index("date")
    assert s.index.is_unique and s.index.is_monotonic_increasing
    n_nan_pr = int(s["placebo_ret"].isna().sum())
    n_nan_ex = int(s["expo_prior_close"].isna().sum())
    ewa = ew.reindex(s.index)
    n_missing_ew = int(ewa.isna().sum())
    ewa = ewa.fillna(0.0)  # spec: missing date -> 0
    b = s["expo_prior_close"] * ewa
    inv = s["expo_prior_close"] > 0  # NaN expo -> False (excluded)
    p, bb = s.loc[inv, "placebo_ret"], b[inv]
    vr = p.std(ddof=1) / bb.std(ddof=1)
    sp, sb = sharpe(p), sharpe(bb)
    rows.append(dict(seed=os.path.basename(f), n_days=len(s), n_inv=int(inv.sum()),
                     d=(p.mean() - bb.mean()) * 252, vr=vr, g=sp - sb, p=sb * (1 / vr - 1),
                     mp=p.mean() * 252, mb=bb.mean() * 252, sp=sp, sb=sb))
    diag.append(dict(seed=os.path.basename(f), first=s.index[0].date(), last=s.index[-1].date(),
                     nan_pr=n_nan_pr, nan_ex=n_nan_ex, missing_ew=n_missing_ew,
                     expo_min=s["expo_prior_close"].min(), expo_max=s["expo_prior_close"].max(),
                     n_zero_expo=int((s["expo_prior_close"] == 0).sum()),
                     nonzero_ret_on_zero_expo=int(((s["expo_prior_close"] <= 0) & (s["placebo_ret"] != 0)).sum())))

r = pd.DataFrame(rows)
dg = pd.DataFrame(diag)
r.to_csv(os.path.join(HERE, "per_seed.csv"), index=False)
dg.to_csv(os.path.join(HERE, "per_seed_diag.csv"), index=False)

n = len(r)
md = r["d"].mean()
se = r["d"].std(ddof=1) / np.sqrt(n)
z = md / se
out = {
    "n_seeds": n,
    "mean_d_pct": md * 100,
    "SE_pct": se * 100,
    "z": z,
    "pass(|z|<3)": abs(z) < 3,
    "mean_vr": r["vr"].mean(),
    "mean_g": r["g"].mean(),
    "mean_p": r["p"].mean(),
    "mean_placebo_ann_pct": r["mp"].mean() * 100,
    "mean_baseline_ann_pct": r["mb"].mean() * 100,
    "n_invested_days_min": r["n_inv"].min(),
    "n_invested_days_max": r["n_inv"].max(),
    "n_invested_days_mean": r["n_inv"].mean(),
    "n_rows_per_seed_min": r["n_days"].min(),
    "n_rows_per_seed_max": r["n_days"].max(),
}
for k, v in out.items():
    print(f"{k}: {v}")
print("\nDIAG")
print(dg.describe(include="all").T.to_string())
print("first dates:", dg["first"].unique(), "last dates:", dg["last"].unique())
