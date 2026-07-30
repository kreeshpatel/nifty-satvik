"""0123 — analysis for the vision-grader screen: reliability gate, truncation-leakage check,
Phase-2 conditional separation screen, Phase-1.5 detector-agreement split.

Every number here is reproducible from the committed grade artifacts (grades_0123/*.jsonl) +
sample_0123.csv. No engine touched. Run as: python scripts/screen_0123.py <stage>
  stages: reliability | truncation | screen
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "research" / "substrate" / "grades_0123"
SAMPLE = ROOT / "research" / "substrate" / "sample_0123.csv"
GMAP = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


def _load(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


# ---------- kappa helpers ----------
def cohen_kappa(a, b, cats=None):
    a = list(a); b = list(b)
    cats = cats or sorted(set(a) | set(b))
    idx = {c: i for i, c in enumerate(cats)}
    n = len(a); K = len(cats)
    O = np.zeros((K, K))
    for x, y in zip(a, b):
        O[idx[x], idx[y]] += 1
    O /= n
    r = O.sum(1); c = O.sum(0)
    po = np.trace(O); pe = float(r @ c)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po


def weighted_kappa(a, b, cats, weight="quadratic"):
    a = list(a); b = list(b)
    idx = {c: i for i, c in enumerate(cats)}
    K = len(cats); n = len(a)
    O = np.zeros((K, K))
    for x, y in zip(a, b):
        O[idx[x], idx[y]] += 1
    r = O.sum(1); c = O.sum(0)
    E = np.outer(r, c) / n
    W = np.zeros((K, K))
    for i in range(K):
        for j in range(K):
            W[i, j] = (i - j) ** 2 if weight == "quadratic" else abs(i - j)
    num = (W * O).sum(); den = (W * E).sum()
    return 1 - num / den if den > 0 else 1.0


# ---------- STAGE 1: reliability gate ----------
def reliability():
    recs = _load(ART / "grades_selfconsistency.jsonl")
    by = {}
    for r in recs:
        by.setdefault(r["id"], []).append(r)
    pairs = {k: v for k, v in by.items() if len(v) >= 2}
    print(f"double-graded ids: {len(pairs)}  (records={len(recs)})")
    if len(pairs) < 20:
        print("INSUFFICIENT double-graded ids (<20) — cannot certify reliability.")
        return False

    g1 = [GMAP[v[0]["setup_grade"]] for v in pairs.values()]
    g2 = [GMAP[v[1]["setup_grade"]] for v in pairs.values()]
    wk = weighted_kappa(g1, g2, [0, 1, 2, 3, 4], "quadratic")
    within1 = np.mean([abs(x - y) <= 1 for x, y in zip(g1, g2)])

    t1 = [bool(v[0]["take_now"]) for v in pairs.values()]
    t2 = [bool(v[1]["take_now"]) for v in pairs.values()]
    tk, tagree = cohen_kappa(t1, t2, [False, True])

    b1 = [v[0]["breakout_stage"] for v in pairs.values()]
    b2 = [v[1]["breakout_stage"] for v in pairs.values()]
    _, bagree = cohen_kappa(b1, b2, ["pre", "at", "extended"])

    print("\nFROZEN RELIABILITY BAR (all must hold):")
    rows = [
        ("setup_grade quadratic-weighted kappa", wk, 0.45, wk >= 0.45),
        ("setup_grade within-1-grade agree", within1, 0.80, within1 >= 0.80),
        ("take_now Cohen kappa", tk, 0.45, tk >= 0.45),
        ("take_now raw agreement", tagree, 0.75, tagree >= 0.75),
        ("breakout_stage agreement", bagree, 0.65, bagree >= 0.65),
    ]
    for name, val, bar, ok in rows:
        print(f"  {name:38s} {val:6.3f}  bar>={bar:.2f}  {'PASS' if ok else 'FAIL'}")
    verdict = all(ok for *_, ok in rows)
    print(f"\nGATE: {'GO — grader reproduces itself' if verdict else 'STOP — instrument unreliable'}")
    return verdict


# ---------- STAGE 2: truncation-leakage gate ----------
def truncation():
    g60 = {r["id"]: r for r in _load(ART / "grades.jsonl")}
    g90 = {r["id"]: r for r in _load(ART / "grades_truncation.jsonl")}
    ids = [i for i in g90 if i in g60]
    print(f"paired hw60/hw90 charts: {len(ids)}")
    a = [GMAP[g60[i]["setup_grade"]] for i in ids]
    b = [GMAP[g90[i]["setup_grade"]] for i in ids]
    wk = weighted_kappa(a, b, [0, 1, 2, 3, 4], "quadratic")
    within1 = np.mean([abs(x - y) <= 1 for x, y in zip(a, b)])
    bias = np.mean([y - x for x, y in zip(a, b)])            # + => more history graded HIGHER
    tk, tagree = cohen_kappa([bool(g60[i]["take_now"]) for i in ids],
                             [bool(g90[i]["take_now"]) for i in ids], [False, True])
    _, bagree = cohen_kappa([g60[i]["breakout_stage"] for i in ids],
                            [g90[i]["breakout_stage"] for i in ids], ["pre", "at", "extended"])
    print("\nTRUNCATION-LEAKAGE (grades must NOT drift with history length; ref self-consistency wk=0.867):")
    rows = [
        ("setup_grade weighted-kappa (hw60 vs hw90)", wk, 0.45, wk >= 0.45),
        ("setup_grade within-1-grade agree", within1, 0.80, within1 >= 0.80),
        ("|mean grade drift| (directional)", abs(bias), 0.50, abs(bias) <= 0.50),  # <= is clean
        ("take_now agreement", tagree, 0.75, tagree >= 0.75),
        ("breakout_stage agreement", bagree, 0.65, bagree >= 0.65),
    ]
    for name, val, bar, ok in rows:
        op = "<=" if "drift" in name else ">="
        print(f"  {name:44s} {val:6.3f}  bar{op}{bar:.2f}  {'CLEAN' if ok else 'DRIFT'}")
    clean = all(ok for *_, ok in rows)
    print(f"  (directional bias signed = {bias:+.3f})")
    print(f"\nGATE: {'CLEAN — no leakage, screen authorized' if clean else 'VOID — grades drift with crop length (furniture leakage)'}")
    return clean


# ---------- merged frame ----------
def _merged():
    g = pd.DataFrame(_load(ART / "grades.jsonl"))
    g["grade"] = g["setup_grade"].map(GMAP)
    g["take"] = g["take_now"].astype(bool)
    s = pd.read_csv(SAMPLE)
    df = s.merge(g[["id", "grade", "take", "breakout_stage", "setup_type",
                    "box_region", "sr_zones"]], on="id", how="inner")
    df["cell"] = df["ext_band"] * 3 + df["crs_tercile"]
    df["year"] = pd.to_datetime(df["entry_date"]).dt.year
    return df


def _celladj(df, col):
    """subtract each ext x CRS cell's mean -> the within-cell (ext x CRS-controlled) residual."""
    return df[col] - df.groupby("cell")[col].transform("mean")


def _boot_ci(x, y, n=5000, seed=20260730):
    """95% CI on mean(x)-mean(y) by resampling each group."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x); y = np.asarray(y)
    d = [rng.choice(x, len(x)).mean() - rng.choice(y, len(y)).mean() for _ in range(n)]
    return float(np.mean(x) - np.mean(y)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


# ---------- STAGE 3: Phase-2 screen ----------
def screen():
    df = _merged()
    print(f"screen n={len(df)}  cohorts={df['cohort'].value_counts().to_dict()}")

    print("\n--- grade (0=F..4=A) by cohort [unconditional] ---")
    for c in ["strong_winner", "noise_stop", "false_touch"]:
        sub = df[df["cohort"] == c]
        print(f"  {c:14s} mean grade {sub['grade'].mean():.3f}  take_now {sub['take'].mean()*100:4.1f}%  n={len(sub)}")

    print("\n--- CONFOUND: grade vs extension / outcome ---")
    print(f"  corr(grade, ext_vs_sma) = {df['grade'].corr(df['ext_vs_sma']):+.3f}   "
          f"corr(grade, R) = {df['grade'].corr(df['R']):+.3f}")

    print("\n--- CONDITIONAL (cell-adjusted grade, beyond ext x CRS) ---")
    df["g_adj"] = _celladj(df, "grade")
    means = {c: df[df["cohort"] == c]["g_adj"] for c in df["cohort"].unique()}
    for pair in [("strong_winner", "false_touch"), ("strong_winner", "noise_stop"),
                 ("noise_stop", "false_touch")]:
        d, lo, hi = _boot_ci(means[pair[0]].values, means[pair[1]].values)
        clean = (lo > 0) or (hi < 0)
        print(f"  celladj grade {pair[0]:13s} - {pair[1]:13s} = {d:+.3f}  CI[{lo:+.3f},{hi:+.3f}]  "
              f"{'SEPARATES' if clean else 'CI straddles 0'}")

    # decisive pair for the 0117 axis: false_touch vs noise_stop
    print("\n--- PER-YEAR sign: cell-adj grade (strong_winner) - (stop-out mean), 2019-2024 ---")
    signs = []
    for y in range(2019, 2025):
        dy = df[df["year"] == y]
        if len(dy) < 15:
            continue
        sw = dy[dy["cohort"] == "strong_winner"]["g_adj"].mean()
        lo = dy[dy["cohort"].isin(["false_touch", "noise_stop"])]["g_adj"].mean()
        s = sw - lo
        signs.append(s > 0)
        print(f"  {y}: {s:+.3f}  {'+' if s>0 else '-'}  (n={len(dy)})")
    print(f"  positive years: {sum(signs)}/{len(signs)}  (bar >=5/6)")

    # take_now secondary: what do the 16 'take' trades resolve to?
    tk = df[df["take"]]
    print(f"\n--- take_now=True subset (n={len(tk)}): cohort mix {tk['cohort'].value_counts().to_dict()}  "
          f"mean R {tk['R'].mean():+.2f} vs book {df['R'].mean():+.2f} ---")

    # liquidity-proxy robustness (ADV not in substrate; vol_ratio proxy via re-join)
    print("\n--- robustness: cell-adj (SW - stopout) grade across liquidity-proxy terciles ---")
    par = pd.read_parquet(ROOT / "research" / "substrate" / "context_windows.parquet")
    par["entry_date"] = pd.to_datetime(par["entry_date"]).dt.date.astype(str)
    df2 = df.copy(); df2["entry_date"] = pd.to_datetime(df2["entry_date"]).dt.date.astype(str)
    df2 = df2.merge(par[["ticker", "entry_date", "vol_ratio"]].drop_duplicates(["ticker", "entry_date"]),
                    on=["ticker", "entry_date"], how="left")
    if df2["vol_ratio"].notna().any():
        q = df2["vol_ratio"].quantile([0.33, 0.67]).values
        df2["lt"] = df2["vol_ratio"].apply(lambda v: 0 if v <= q[0] else (1 if v <= q[1] else 2))
        for t in range(3):
            dt = df2[df2["lt"] == t]
            sw = dt[dt["cohort"] == "strong_winner"]["g_adj"].mean()
            lo = dt[dt["cohort"].isin(["false_touch", "noise_stop"])]["g_adj"].mean()
            print(f"    vol_ratio-tercile {t}: SW-stopout celladj grade = {sw-lo:+.3f} (n={len(dt)})")
    else:
        print("    (vol_ratio unavailable — ADV-tercile leg not run)")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "reliability"
    if stage == "reliability":
        reliability()
    elif stage == "truncation":
        truncation()
    elif stage == "screen":
        screen()
    else:
        print(f"stage {stage} not yet wired")
