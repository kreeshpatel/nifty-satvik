"""0126 — the line-hugger screen. LABEL SCREEN (ledger row #13). No trial. Sealed set untouched.

Pre-registration: `diagnostics/research/preregistry/0126-line-hugger-screen.md` — every definition,
question, failure mode and door is frozen there and is NOT re-opened here. Nothing in this script
sweeps a threshold: the rare/chronic split is the population MEDIAN by construction.

The hypothesis: some names sit on their 44-week line for months and fire the touch signal repeatedly;
others touch rarely. Is that name-level base rate information the funnel does not already have?

Train-only discipline (pre-reg §3): sealed rows are dropped at read time, BEFORE any statistic. This
script cannot report on them — it does not retain them.

Reproduce:
    python scripts/diag_hug_index_screen_0126.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.data.weekly import build_weekly_panel  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

# ---- FROZEN (pre-reg §1). Nothing here is swept. ----
WINDOW = 52            # weeks of trailing history
HUG_BAND = 5.0         # |ext| < 5% counts as "on the line"
MIN_COVER = 40         # of WINDOW weeks needing a finite sma44, else the trade is excluded
TOUCH_BAND = 0.07      # house touch definition: wlow <= wsma*(1+0.07) and wclose > wsma
COOLDOWN_WEEKS = 8     # Q3
TRAIN_END = pd.Timestamp("2024-06-30")

SUBSTRATE = ROOT / "research" / "substrate" / "context_windows.parquet"
OUT_JSON = ROOT / "diagnostics" / "research" / "hug_index_screen_0126.json"
OUT_MD = ROOT / "diagnostics" / "research" / "hug_index_screen_0126.md"

EXT_EDGES = [-np.inf, 5.0, 10.0, 15.0, np.inf]
EXT_NAMES = ["<5%", "5-10%", "10-15%", ">15%"]


def boot_ci(x: np.ndarray, n: int = 4000, seed: int = 0) -> tuple[float, float]:
    """Percentile CI of the mean. Fixed seed — the number must be reproducible."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if x.size < 3:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, x.size, size=(n, x.size))].mean(axis=1)
    return (round(float(np.percentile(means, 2.5)), 3), round(float(np.percentile(means, 97.5)), 3))


def diff_ci(a: np.ndarray, b: np.ndarray, n: int = 4000, seed: int = 0) -> tuple[float, float]:
    """Percentile CI of mean(a) - mean(b), resampling both arms independently."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if a.size < 3 or b.size < 3:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    da = a[rng.integers(0, a.size, size=(n, a.size))].mean(axis=1)
    db = b[rng.integers(0, b.size, size=(n, b.size))].mean(axis=1)
    d = da - db
    return (round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3))


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |",
           "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(
            "—" if (r[c] is None or (isinstance(r[c], float) and np.isnan(r[c]))) else str(r[c])
            for c in cols) + " |")
    return "\n".join(out)


# ------------------------------------------------------------------ the frozen feature
def hug_features(panel: pd.DataFrame) -> pd.DataFrame:
    """PIT trailing-52w name-level features, one row per (ticker, week_end).

    The window is the 52 COMPLETED weeks strictly before the signal week — week k is never in its
    own window (`.shift(1)` before every rolling call).
    """
    rows = []
    for tkr, g in panel.groupby("ticker", sort=True):
        g = g.sort_values("week_end", kind="mergesort")
        c = g["c"].to_numpy(float)
        lo = g["l"].to_numpy(float)
        sma = g["sma44"].to_numpy(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            ext = np.abs(c / sma - 1.0) * 100.0
            touch = (lo <= sma * (1 + TOUCH_BAND)) & (c > sma)
        s_ext = pd.Series(ext)
        s_hug = pd.Series((ext < HUG_BAND).astype(float)).where(~np.isnan(ext))
        s_tch = pd.Series(np.where(np.isnan(sma), np.nan, touch.astype(float)))
        cover = s_ext.notna().astype(float).shift(1).rolling(WINDOW, min_periods=1).sum()
        rows.append(pd.DataFrame({
            "ticker": tkr, "week_end": g["week_end"].to_numpy(),
            "hug_index": s_hug.shift(1).rolling(WINDOW, min_periods=MIN_COVER).mean().to_numpy(),
            "median_abs_ext": s_ext.shift(1).rolling(WINDOW, min_periods=MIN_COVER).median().to_numpy(),
            "touch_count": s_tch.shift(1).rolling(WINDOW, min_periods=MIN_COVER).sum().to_numpy(),
            "cover": cover.to_numpy(),
        }))
    out = pd.concat(rows, ignore_index=True)
    out.loc[out["cover"] < MIN_COVER, ["hug_index", "median_abs_ext", "touch_count"]] = np.nan
    return out


def adv_at_entry(ohlcv: dict, pairs: pd.DataFrame) -> pd.Series:
    """20d rupee ADV at the entry date — the pre-registered robustness stratifier (the substrate
    carries no ADV column, so it is joined here from the pinned cache)."""
    want = {t: set(pd.DatetimeIndex(g["entry_date"])) for t, g in pairs.groupby("ticker")}
    hit: dict[tuple[str, pd.Timestamp], float] = {}
    for tkr, df in ohlcv.items():
        if tkr not in want or "Volume" not in df.columns:
            continue
        idx = pd.to_datetime(df.index)
        adv = pd.Series(df["Close"].to_numpy(float) * df["Volume"].to_numpy(float),
                        index=idx).rolling(20).mean()
        for d, v in adv.reindex(pd.DatetimeIndex(sorted(want[tkr]))).items():
            hit[(tkr, d)] = float(v)
    return pd.Series([hit.get((t, d), np.nan)
                      for t, d in zip(pairs["ticker"], pairs["entry_date"])], index=pairs.index)


def cohort(df: pd.DataFrame, col: str = "R") -> dict:
    r = df[col].to_numpy(float)
    r = r[~np.isnan(r)]
    if r.size == 0:
        return dict(N=0, meanR=None, medR=None, win_pct=None)
    return dict(N=int(r.size), meanR=round(float(r.mean()), 3),
                medR=round(float(np.median(r)), 3),
                win_pct=round(100.0 * float((r > 0).mean()), 1))


def conditional_delta(df: pd.DataFrame, flag: str, value: str = "R") -> dict:
    """Effect BEYOND the ext-band x CRS-tercile cells: within-cell demeaning, then hi-vs-lo.

    This is the pre-registered form — a marginal difference that vanishes under demeaning was the
    cells' effect all along, which §4.1 names as a KILL rather than a discovery.
    """
    d = df.dropna(subset=[value, flag, "cell"]).copy()
    d["resid"] = d[value] - d.groupby("cell")[value].transform("mean")
    hi = d.loc[d[flag], "resid"].to_numpy(float)
    lo = d.loc[~d[flag], "resid"].to_numpy(float)
    if hi.size < 3 or lo.size < 3:
        return dict(n_hi=int(hi.size), n_lo=int(lo.size), cond_delta=None, ci=None)
    return dict(n_hi=int(hi.size), n_lo=int(lo.size),
                cond_delta=round(float(hi.mean() - lo.mean()), 3), ci=list(diff_ci(hi, lo)))


def per_year_sign(df: pd.DataFrame, flag: str, value: str = "R") -> dict:
    out = {}
    for y, g in df.dropna(subset=[value, flag]).groupby(df["entry_date"].dt.year):
        hi, lo = g.loc[g[flag], value], g.loc[~g[flag], value]
        out[int(y)] = (round(float(hi.mean() - lo.mean()), 3)
                       if len(hi) >= 3 and len(lo) >= 3 else None)
    vals = [v for v in out.values() if v is not None]
    pos = sum(1 for v in vals if v > 0)
    return dict(by_year=out, n_years=len(vals), n_positive=pos,
                consistency=f"{max(pos, len(vals) - pos)}/{len(vals)}" if vals else "0/0")


def main() -> None:
    # ---- load, then DROP the sealed set before any statistic exists (pre-reg §3) ----
    sub = pd.read_parquet(SUBSTRATE)
    n_all = len(sub)
    sub["entry_date"] = pd.to_datetime(sub["entry_date"])
    train = sub[(sub["split"] == "train") & (sub["entry_date"] <= TRAIN_END)].copy()
    n_dropped = n_all - len(train)
    del sub                                        # sealed rows are not retained in this process

    ohlcv = corrected_universe()
    panel = build_weekly_panel(ohlcv)
    feats = hug_features(panel)

    # PIT join: the signal week is the last completed week at or before the entry date.
    train = train.sort_values("entry_date", kind="mergesort")
    feats["week_end"] = pd.to_datetime(feats["week_end"]).astype("datetime64[ns]")
    feats = feats.sort_values("week_end", kind="mergesort")
    m = pd.merge_asof(train, feats, left_on="entry_date", right_on="week_end", by="ticker",
                      direction="backward", allow_exact_matches=True)
    n_join = int(m["hug_index"].notna().sum())
    n_excl = int(len(m) - n_join)
    m = m.dropna(subset=["hug_index"]).copy()

    m["adv20"] = adv_at_entry(ohlcv, m[["ticker", "entry_date"]])
    m["ext_band"] = pd.cut(m["ext_vs_sma"], EXT_EDGES, labels=EXT_NAMES, right=False)
    m["crs_t"] = pd.qcut(m["rank_crs"], 3, labels=["loCRS", "midCRS", "hiCRS"])
    m["cell"] = m["ext_band"].astype(str) + " x " + m["crs_t"].astype(str)
    hug_med = float(m["hug_index"].median())
    m["chronic"] = m["hug_index"] > hug_med           # median split — frozen, not swept

    res: dict = {
        "_doc": "0126 line-hugger screen (LABEL SCREEN #13; 0 trials; sealed untouched).",
        "prereg": "diagnostics/research/preregistry/0126-line-hugger-screen.md",
        "rows_in_substrate": n_all, "rows_train_used": int(len(m)),
        "rows_dropped_not_train": int(n_dropped),
        "rows_excluded_coverage": n_excl,
        "hug_index_median_split": round(hug_med, 4),
        "hug_index_quartiles": [round(float(q), 4) for q in m["hug_index"].quantile([.25, .5, .75])],
    }

    # ---- §4 confound checks FIRST: a confirmed confound is a KILL, not a discovery ----
    res["confounds"] = {
        "corr_hug_rank_crs": round(float(m["hug_index"].corr(m["rank_crs"])), 3),
        "corr_hug_atr_pct": round(float(m["hug_index"].corr(m["atr_pct"])), 3),
        "corr_hug_ext_vs_sma": round(float(m["hug_index"].corr(m["ext_vs_sma"])), 3),
        "corr_hug_median_abs_ext": round(float(m["hug_index"].corr(m["median_abs_ext"])), 3),
        "corr_hug_touch_count": round(float(m["hug_index"].corr(m["touch_count"])), 3),
    }

    # ---- Q1: discrimination ----
    q1 = {}
    for lab in ("false_touch", "noise_stop"):
        if lab not in m.columns:
            continue
        d = m.dropna(subset=[lab])
        hi, lo = d.loc[d["chronic"], lab].astype(float), d.loc[~d["chronic"], lab].astype(float)
        q1[lab] = dict(chronic_rate_pct=round(100.0 * float(hi.mean()), 1),
                       rare_rate_pct=round(100.0 * float(lo.mean()), 1),
                       delta_pp=round(100.0 * float(hi.mean() - lo.mean()), 1),
                       ci_pp=[round(100 * x, 1) for x in diff_ci(hi.to_numpy(), lo.to_numpy())],
                       conditional=conditional_delta(d.assign(**{lab: d[lab].astype(float)}),
                                                     "chronic", lab))
    q1["R_conditional"] = conditional_delta(m, "chronic", "R")
    q1["R_per_year"] = per_year_sign(m, "chronic", "R")
    q1["R_marginal"] = {"chronic": cohort(m[m["chronic"]]), "rare": cohort(m[~m["chronic"]])}
    res["Q1_discrimination"] = q1

    # ---- Q2: THE refinement question — split the <5% band's core by hug ----
    band = m[m["ext_band"] == "<5%"].copy()
    if len(band) >= 6:
        bmed = float(band["hug_index"].median())      # median split WITHIN the band
        band["chronic_band"] = band["hug_index"] > bmed
        rare_r = band.loc[~band["chronic_band"], "R"].to_numpy(float)
        chr_r = band.loc[band["chronic_band"], "R"].to_numpy(float)
        res["Q2_deep_band_split"] = {
            "band_total": cohort(band), "band_hug_median": round(bmed, 4),
            "rare_touch": {**cohort(band[~band["chronic_band"]]), "ci": list(boot_ci(rare_r))},
            "chronic_hugger": {**cohort(band[band["chronic_band"]]), "ci": list(boot_ci(chr_r))},
            "delta_rare_minus_chronic": round(float(np.nanmean(rare_r) - np.nanmean(chr_r)), 3),
            "delta_ci": list(diff_ci(rare_r, chr_r)),
            "conditional_within_band_cells": conditional_delta(
                band.assign(cell=band["crs_t"].astype(str)), "chronic_band", "R"),
            "per_year": per_year_sign(band, "chronic_band", "R"),
            "by_crs_tercile": {
                str(t): {"rare": cohort(g[~g["chronic_band"]]), "chronic": cohort(g[g["chronic_band"]])}
                for t, g in band.groupby("crs_t", observed=True)},
        }
    else:
        res["Q2_deep_band_split"] = {"N": int(len(band)), "note": "band too thin to split"}

    # ---- Q3: the cooldown formulation ----
    m2 = m.sort_values(["ticker", "entry_date"], kind="mergesort").copy()
    stopped = (m2["reason"].astype(str) == "stop")
    hot = np.zeros(len(m2), bool)
    prev_stop: dict[str, pd.Timestamp] = {}
    for i, (tkr, ed, st) in enumerate(zip(m2["ticker"], m2["entry_date"], stopped)):
        last = prev_stop.get(tkr)
        if last is not None and (ed - last).days <= COOLDOWN_WEEKS * 7:
            hot[i] = True
        if st:
            prev_stop[tkr] = ed
    m2["hot_retouch"] = hot
    hot_r = m2.loc[m2["hot_retouch"], "R"].to_numpy(float)
    cold_r = m2.loc[~m2["hot_retouch"], "R"].to_numpy(float)
    res["Q3_cooldown"] = {
        "cooldown_weeks": COOLDOWN_WEEKS,
        "hot_retouch": {**cohort(m2[m2["hot_retouch"]]), "ci": list(boot_ci(hot_r))},
        "cold_touch": {**cohort(m2[~m2["hot_retouch"]]), "ci": list(boot_ci(cold_r))},
        "delta_hot_minus_cold": (round(float(np.nanmean(hot_r) - np.nanmean(cold_r)), 3)
                                 if hot_r.size and cold_r.size else None),
        "delta_ci": list(diff_ci(hot_r, cold_r)),
        "conditional": conditional_delta(m2, "hot_retouch", "R"),
        "per_year": per_year_sign(m2, "hot_retouch", "R"),
        "activation_share_pct": round(100.0 * float(m2["hot_retouch"].mean()), 1),
    }

    # ---- ADV robustness (pre-registered leg) ----
    m["adv_t"] = pd.qcut(m["adv20"], 3, labels=["lowADV", "midADV", "hiADV"])
    res["adv_robustness_Q1"] = {
        str(t): conditional_delta(g, "chronic", "R")
        for t, g in m.dropna(subset=["adv_t"]).groupby("adv_t", observed=True)}
    if "Q2_deep_band_split" in res and "rare_touch" in res["Q2_deep_band_split"]:
        res["adv_robustness_Q2"] = {
            str(t): {"rare": cohort(g[~g["chronic_band"]]), "chronic": cohort(g[g["chronic_band"]])}
            for t, g in band.dropna(subset=["adv_t"]).groupby("adv_t", observed=True)
        } if "adv_t" in band.columns else {"note": "adv not joined on band subset"}

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")

    # ---- markdown readout ----
    md = [
        "# 0126 — line-hugger screen (LABEL SCREEN #13)",
        "",
        "**0 trials. Sealed set untouched. Judge log unread. No engine change.**",
        "**Standing counts: screens 13 · sealed opens 1 · n_trials 138.**",
        "",
        f"Train rows used **{res['rows_train_used']}** of {n_all} "
        f"({n_dropped} not-train dropped before any statistic; {n_excl} excluded on the "
        f"{MIN_COVER}/{WINDOW}-week coverage rule).",
        f"`hug_index` quartiles {res['hug_index_quartiles']}; median split at "
        f"**{res['hug_index_median_split']}**.",
        "",
        "## §4 confound checks (a confirmed confound is a KILL, not a discovery)",
        "",
        md_table(pd.DataFrame([{"pair": k, "corr": v} for k, v in res["confounds"].items()])),
        "",
        "## Q1 — discrimination (chronic vs rare, conditional on ext × CRS cells)",
        "",
        "```", json.dumps(res["Q1_discrimination"], indent=2, default=str), "```",
        "",
        "## Q2 — the refinement question: the <5% band's core, split by hug",
        "",
        "```", json.dumps(res["Q2_deep_band_split"], indent=2, default=str), "```",
        "",
        "## Q3 — cooldown: re-touch within 8 weeks of a stop-out vs cold touches",
        "",
        "```", json.dumps(res["Q3_cooldown"], indent=2, default=str), "```",
        "",
        "## ADV-tercile robustness (pre-registered leg)",
        "",
        "```", json.dumps({"Q1": res["adv_robustness_Q1"],
                           "Q2": res.get("adv_robustness_Q2")}, indent=2, default=str), "```",
        "",
        "Reproduce: `python scripts/diag_hug_index_screen_0126.py`",
        "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write("\n".join(md).encode(enc, "replace").decode(enc, "replace") + "\n")


if __name__ == "__main__":
    main()
