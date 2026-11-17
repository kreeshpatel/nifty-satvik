"""EXPLORE (tier 0, descriptive): how fast does each ranker's information decay?

Owner request 2026-11-17. Dataset A only — the weekly panel 2019-01-01..2024-06-30, prices cut at 2024-06-30 and the
cut asserted. Descriptive: no trial, no screen row, no sealed read, nothing live changes, nothing adopted.

Two rankers, measured the same way on the same panel so the two decay curves are comparable:

  crs_dist           the live weekly-swing ranker (0094): weekly close / Nifty-50 weekly close, over its own
                     40-week mean, minus one — recomputed exactly as scripts/run_bhanushali_weekly_rank.py does.
  sma200_slope_63    the momentum book's sole entry ranker, confirmed by finding 0001: the % change of the
                     200-day SMA over the last 63 sessions, read at the same Friday.

**One universe for both, stated plainly.** Both ICs are measured on the PIT Nifty-500 members at each Friday — the
live swing universe. The momentum book trades its own canonical universe, so its IC *level* here is not its IC on
its own book; what is comparable, and what this study is about, is the **shape of the decay**.

For each Friday and each horizon h in {1, 2, 4, 8, 13, 26} weeks (39 and 52 added after the first pass, see the note):
  IC_h(week) = cross-sectional Spearman correlation between the rank value at that Friday and the forward return
               from that Friday's weekly close to the close h weeks later, over the eligible members.

Reported per horizon: mean IC, its 95% band, the share of weeks with IC > 0, and the median cross-section size. The
bands and the half-life CI come from a **moving-block bootstrap over weeks** (block = 13 weeks, 2000 resamples),
because overlapping forward windows make consecutive weekly ICs strongly dependent and an iid interval would be far
too narrow.

Half-life: least squares fit of mean IC_h = IC_0 * exp(-lambda * h) over the six horizons (fitted on the resample,
so the CI is the bootstrap distribution of ln(2)/lambda). A resample whose fit does not decay gives no half-life and
is reported as such rather than clipped.

    python pipelines/diagnostics/explore_ic_decay_halflife.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from nq.lab import runs as L  # noqa: E402

OUT_MD = ROOT / "diagnostics" / "research" / "explore" / "2026-11-17_ic_decay_halflife.md"
OUT_JSON = OUT_MD.with_suffix(".json")
HORIZONS = [1, 2, 4, 8, 13, 26, 39, 52]   # 39 and 52 added after the first run: nothing decayed inside 26
START, CUT = "2019-01-01", "2024-06-30"
BLOCK, NBOOT, SEED = 13, 2000, 20261117
MIN_NAMES = 50


def weekly_panel():
    """Friday-stamped weekly closes and both ranker values, over PIT Nifty-500 members."""
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_path1 import corrected_universe
    from nq.data.membership import load_membership
    from nq.data.features import compute_features

    px = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(CUT)] for t, df in corrected_universe().items()}
    px = {t: df for t, df in px.items() if len(df) > 300}
    assert max(df.index.max() for df in px.values()) <= pd.Timestamp(CUT), "sealed data reached the lab"
    mem = load_membership()
    n50 = L.load_nifty()
    n50w = n50.resample("W-FRI").last().dropna()

    close, crs, slope = {}, {}, {}
    for t, df in px.items():
        w = df["Close"].resample("W-FRI").last().dropna()
        if len(w) < 60:
            continue
        iw = n50w.reindex(w.index, method="ffill")
        rs = w / iw.replace(0, np.nan)
        close[t] = w
        crs[t] = rs / rs.rolling(R94.CRS_LEN).mean() - 1.0
        f = compute_features(df, ticker=t)
        if f is None:
            continue
        slope[t] = f["sma200_slope_63"].resample("W-FRI").last()
    C = pd.DataFrame(close).sort_index()
    return C, pd.DataFrame(crs).reindex_like(C), pd.DataFrame(slope).reindex(C.index).reindex(columns=C.columns), mem


def eligibility(C: pd.DataFrame, mem) -> pd.DataFrame:
    from run_bhanushali_weekly_rank import ticker_in_index_on
    fridays = C.index[(C.index >= pd.Timestamp(START)) & (C.index <= pd.Timestamp(CUT))]
    rows = {}
    for f in fridays:
        rows[f] = pd.Series({t: (mem is None or ticker_in_index_on(t, f.date(), mem)) for t in C.columns})
    return pd.DataFrame(rows).T


def weekly_ic(C: pd.DataFrame, R: pd.DataFrame, elig: pd.DataFrame) -> pd.DataFrame:
    """One Spearman IC per (Friday, horizon). NaN where the forward close or the cross-section is missing."""
    out = {}
    pos = {d: i for i, d in enumerate(C.index)}
    for h in HORIZONS:
        vals = {}
        for f in elig.index:
            i = pos[f]
            if i + h >= len(C.index):
                continue
            ok = elig.loc[f] & R.loc[f].notna() & C.loc[f].notna() & C.iloc[i + h].notna() & (C.loc[f] > 0)
            names = ok[ok].index
            if len(names) < MIN_NAMES:
                continue
            fwd = C.iloc[i + h][names] / C.loc[f, names] - 1.0
            vals[f] = float(pd.Series(R.loc[f, names].values).corr(pd.Series(fwd.values), method="spearman"))
        out[h] = pd.Series(vals)
    return pd.DataFrame(out).sort_index()


def block_resamples(n: int, rng: np.random.Generator):
    nb = int(np.ceil(n / BLOCK))
    for _ in range(NBOOT):
        starts = rng.integers(0, max(n - BLOCK, 1), size=nb)
        yield np.concatenate([np.arange(s, s + BLOCK) for s in starts])[:n] % n


def decay_fit(mean_ic: np.ndarray) -> float | None:
    """ln(2)/lambda from least squares on ln(IC_h) vs h; None when the curve does not decay positively."""
    h = np.array(HORIZONS, dtype=float)
    ok = mean_ic > 0
    if ok.sum() < 3:
        return None
    b, _ = np.polyfit(h[ok], np.log(mean_ic[ok]), 1)[:2]
    if b >= 0:
        return None
    return float(np.log(2) / -b)


def summarise(ic: pd.DataFrame, rng: np.random.Generator) -> dict:
    v = ic.to_numpy(float)
    n = len(ic)
    means = np.nanmean(v, axis=0)
    boot_means, boot_hl = [], []
    for idx in block_resamples(n, rng):
        m = np.nanmean(v[idx], axis=0)
        boot_means.append(m)
        hl = decay_fit(m)
        if hl is not None and hl < 500:
            boot_hl.append(hl)
    B = np.array(boot_means)
    per_h = []
    for j, h in enumerate(HORIZONS):
        col = ic[h].dropna()
        per_h.append({"h_weeks": h, "mean_ic": round(float(means[j]), 4),
                      "ci95": [round(float(np.nanpercentile(B[:, j], 2.5)), 4),
                               round(float(np.nanpercentile(B[:, j], 97.5)), 4)],
                      "pct_weeks_positive": round(float((col > 0).mean() * 100), 1), "n_weeks": int(len(col))})
    hl = decay_fit(means)
    return {"per_horizon": per_h, "half_life_weeks": None if hl is None else round(hl, 2),
            "half_life_ci95": ([round(float(np.percentile(boot_hl, 2.5)), 2),
                                round(float(np.percentile(boot_hl, 97.5)), 2)] if len(boot_hl) > NBOOT * 0.5 else None),
            "resamples_that_decayed_pct": round(len(boot_hl) / NBOOT * 100, 1),
            "ic_1w_over_ic_26w": (round(float(means[0] / means[-1]), 2) if means[-1] > 0 else None)}


def md_rows(s: dict) -> str:
    out = ["| horizon | mean IC | 95% band (block bootstrap) | weeks IC > 0 | weeks |", "|---|---|---|---|---|"]
    for r in s["per_horizon"]:
        out.append(f"| {r['h_weeks']}w | {r['mean_ic']:+.4f} | [{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}] | "
                   f"{r['pct_weeks_positive']}% | {r['n_weeks']} |")
    return "\n".join(out)


def main() -> int:
    rng = np.random.default_rng(SEED)
    C, CRS, SLP, mem = weekly_panel()
    elig = eligibility(C, mem)
    res = {"tier": "EXPLORE", "window": f"{START}..{CUT}", "cut_asserted": True, "horizons_weeks": HORIZONS,
           "universe": "PIT Nifty-500 members at each Friday (the live swing universe), min 50 names in a cross-section",
           "bootstrap": {"kind": "moving block over weeks", "block_weeks": BLOCK, "resamples": NBOOT, "seed": SEED},
           "rankers": {}}
    ics = {}
    for name, R in (("crs_dist (live swing ranker, 0094)", CRS), ("sma200_slope_63 (momentum ranker, 0001)", SLP)):
        ic = weekly_ic(C, R, elig)
        ics[name] = ic
        res["rankers"][name] = summarise(ic, rng)
        res["rankers"][name]["median_cross_section"] = int(elig.sum(axis=1).median())

    md = ["# 2026-11-17 — IC decay and half-life of the two rankers", "",
          "**Tier:** EXPLORE, descriptive. Weekly panel 2019-01-01..2024-06-30, prices cut at 2024-06-30 and the cut "
          "asserted. No trial, no screen row, **no sealed read**, nothing live changed, nothing adopted. Standing "
          "counts unchanged.", "",
          "**What is measured.** For each Friday and each horizon *h*, the cross-sectional Spearman correlation "
          "between the ranker's value and the forward return from that Friday's weekly close to the close *h* weeks "
          "later, over the PIT Nifty-500 members. Mean IC per horizon, then an exponential fit "
          "`IC(h) = IC₀·e^(−λh)` whose half-life is `ln2/λ`.", "",
          "**Why the bands are wide.** Overlapping forward windows make consecutive weekly ICs strongly dependent, so "
          "the intervals come from a **moving-block bootstrap over weeks** (block 13 weeks, 2,000 resamples). An iid "
          "interval here would be several times too narrow and would be wrong.", "",
          "**One universe for both.** Both rankers are measured on the live swing universe so the two curves are "
          "comparable. The momentum book trades its own canonical universe, so its IC *level* below is not its IC on "
          "its own book — the **shape of the decay** is the comparable part.", ""]
    for name in res["rankers"]:
        s = res["rankers"][name]
        hl = "no decay fitted" if s["half_life_weeks"] is None else f"**{s['half_life_weeks']} weeks**"
        ci = "" if not s["half_life_ci95"] else f", 95% CI [{s['half_life_ci95'][0]}, {s['half_life_ci95'][1]}]"
        md += [f"## {name}", "", md_rows(s), "",
               f"Half-life: {hl}{ci}. {s['resamples_that_decayed_pct']}% of resamples produced a decaying fit. "
               f"Median cross-section: {s['median_cross_section']} names.", ""]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(res["rankers"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
