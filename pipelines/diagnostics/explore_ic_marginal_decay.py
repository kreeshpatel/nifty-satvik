"""EXPLORE (tier 0, descriptive): MARGINAL IC decay of the two rankers, replacing the cumulative-return version.

Mission line: a ranker whose information dies in two weeks and one that lives for six months call for different
re-ranking cadences and different holding periods; getting this wrong costs return and drawdown on the 70/30 blend.
This measures which it is. It changes nothing by itself.

Owner correction 2026-11-17: the first version of this study (PR #206) measured CUMULATIVE forward returns, where a
rising curve is partly the arithmetic of a longer window rather than persistence of the signal. That result is
withdrawn. This run keeps the cumulative table, clearly labelled as not a decay measure, and adds the marginal
measure the question actually needs.

Verification rules 1-6 (CLAUDE.md "Mission and verification", skills/verify-before-report).

RULE 1 - METHOD BEFORE RESULT

  Window              2019-01-01..2024-06-30 Fridays. Prices cut at 2024-06-30 and the cut ASSERTED
                      (weekly_panel(), this file). Sealed slice B is never read.
  Universe            PIT Nifty-500 membership at each Friday, via nq.data.membership.load_membership() and
                      run_bhanushali_weekly_rank.ticker_in_index_on (the live swing universe rule). A cross-section
                      is skipped below MIN_NAMES=50. Median cross-section is reported.
  Weekly close        each ticker's daily Close resampled "W-FRI" .last() - the same Friday stamp for price, rank
                      and membership.
  crs_dist            rs = weekly close / Nifty-50 weekly close; crs = rs / rs.rolling(40).mean() - 1.
                      Formula of record: scripts/run_bhanushali_weekly_rank.py:296-298, CRS_LEN=40 at :46.
  sma200_slope_63     (SMA200 / SMA200.shift(63) - 1) * 100 on daily closes, read at the Friday.
                      Formula of record: nq/data/features.py:113-115. Momentum's ranker per finding 0001.
  CUMULATIVE IC(h)    per Friday t: Spearman( rank_t , close_{t+h}/close_t - 1 ) across the eligible names.
                      Kept for continuity and LABELLED NOT A DECAY MEASURE: the window grows with h.
  MARGINAL IC(h)      per Friday t: Spearman( rank_t , close_{t+h}/close_{t+h-1} - 1 ) - the return of WEEK t+h
                      ALONE. This is the decay measure: it asks what the rank still knows about one week, h weeks
                      later, with no accumulation.
  MARGINAL-4W IC(h)   per Friday t: Spearman( rank_t , close_{t+h}/close_{t+h-4} - 1 ) - the 4-week block ending at
                      h - sampled every 4th Friday so no two observations share a return window. Defined for h>=4.
                      Four such series exist (offsets 0..3); the reported value pools them and the bootstrap draws
                      whole offsets, so the independence claim is not quietly lost in the pooling.
  DEPENDENCE          consecutive weekly ICs are strongly dependent (overlapping cross-sections, autocorrelated
                      ranks), so EVERY band is a MOVING-BLOCK BOOTSTRAP over Fridays: block 13 weeks, 2000 draws,
                      seed 20261117. An iid interval would be several times too narrow. The marginal-4w variant
                      removes return-window overlap but not rank autocorrelation, which is why it, too, gets a
                      block bootstrap.
  HALF-LIFE           fitted on MARGINAL IC ONLY: least squares of ln(IC_h) on h over the horizons with IC_h > 0,
                      half-life = ln2 / -slope. Reported only if the slope is negative and >= 50% of bootstrap
                      resamples also produce a decaying fit; otherwise reported as NOT ESTIMABLE, with the curve
                      shown. No half-life is ever fitted on the cumulative curve.

RULE 4 - ANCHOR, reproduced in-run before any IC is computed: the uncapped live book on dataset A must return
  total R = 650.2 over 525 trades (diagnostics/research/2026-11_loss_diagnosis.json, 2019-01-01..2024-06-28).
  A mismatch beyond 0.1R aborts. 0001's 21.73% / 1.130 is NOT reproducible in-run (cloud run of record), so it is
  quoted, not reproduced, and that is stated in the report.

RULE 5 - SCOPE: horizons 1, 2, 4, 8, 13, 26 were requested. 39 and 52 were ADDED AFTER THE FIRST LOOK on the
  cumulative curve (nothing had turned by 26) and are carried here, labelled, counting toward multiplicity: 8
  horizons x 3 measures x 2 rankers = 48 looks, all descriptive, no trial budget spent.

    python pipelines/diagnostics/explore_ic_marginal_decay.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
from nq.lab import runs as L  # noqa: E402

OUT_MD = ROOT / "diagnostics" / "research" / "explore" / "2026-11-17_ic_marginal_decay.md"
OUT_JSON = OUT_MD.with_suffix(".json")
HORIZONS = [1, 2, 4, 8, 13, 26, 39, 52]
ADDED_AFTER_FIRST_LOOK = [39, 52]
START, CUT = "2019-01-01", "2024-06-30"
BLOCK, NBOOT, SEED, MIN_NAMES = 13, 2000, 20261117, 50
ANCHOR_TOTAL_R, ANCHOR_TRADES = 650.2, 525


# --------------------------------------------------------------------------------- rule 4: the anchor, first
def anchor() -> dict:
    import diag_loss_diagnosis_2026_11 as D
    cut, _P, _mem, _nifty, run = D.build_A()
    _, led = run(True)
    got_r, got_n = round(float(led.R.sum()), 1), int(len(led))
    ok = abs(got_r - ANCHOR_TOTAL_R) <= 0.1 and got_n == ANCHOR_TRADES
    res = {"anchor": "live A uncapped total R / trades", "expected": [ANCHOR_TOTAL_R, ANCHOR_TRADES],
           "reproduced": [got_r, got_n], "match": ok,
           "quoted_not_reproduced": {"0001 run of record": "21.73% CAGR / 1.130 Sharpe / -37.17% MaxDD",
                                     "why": "cloud run of record; not reproducible in this process"}}
    if not ok:
        raise SystemExit(f"ANCHOR MISMATCH: expected {ANCHOR_TOTAL_R}R/{ANCHOR_TRADES} trades, got {got_r}R/{got_n}. "
                         "Rule 4: stop.")
    return res


# --------------------------------------------------------------------------------- the panel
def weekly_panel():
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_path1 import corrected_universe
    from nq.data.features import compute_features
    from nq.data.membership import load_membership

    px = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(CUT)] for t, df in corrected_universe().items()}
    px = {t: df for t, df in px.items() if len(df) > 300}
    assert max(df.index.max() for df in px.values()) <= pd.Timestamp(CUT), "sealed data reached the lab"
    n50w = L.load_nifty().resample("W-FRI").last().dropna()
    close, crs, slope = {}, {}, {}
    for t, df in px.items():
        w = df["Close"].resample("W-FRI").last().dropna()
        if len(w) < 60:
            continue
        rs = w / n50w.reindex(w.index, method="ffill").replace(0, np.nan)
        close[t] = w
        crs[t] = rs / rs.rolling(R94.CRS_LEN).mean() - 1.0
        f = compute_features(df, ticker=t)
        if f is not None:
            slope[t] = f["sma200_slope_63"].resample("W-FRI").last()
    C = pd.DataFrame(close).sort_index()
    return C, pd.DataFrame(crs).reindex_like(C), pd.DataFrame(slope).reindex(C.index).reindex(columns=C.columns), load_membership()


def eligibility(C: pd.DataFrame, mem) -> pd.DataFrame:
    from run_bhanushali_weekly_rank import ticker_in_index_on
    fr = C.index[(C.index >= pd.Timestamp(START)) & (C.index <= pd.Timestamp(CUT))]
    return pd.DataFrame({f: pd.Series({t: (mem is None or ticker_in_index_on(t, f.date(), mem)) for t in C.columns})
                         for f in fr}).T


# --------------------------------------------------------------------------------- the three IC measures
def _ic(C, R, elig, i, f, i_from, i_to) -> float | None:
    if i_to >= len(C.index) or i_from < 0:
        return None
    ok = (elig.loc[f] & R.loc[f].notna() & C.iloc[i_from].notna() & C.iloc[i_to].notna()
          & (C.iloc[i_from] > 0) & (C.loc[f] > 0))
    names = ok[ok].index
    if len(names) < MIN_NAMES:
        return None
    fwd = C.iloc[i_to][names] / C.iloc[i_from][names] - 1.0
    return float(pd.Series(R.loc[f, names].values).corr(pd.Series(fwd.values), method="spearman"))


def ic_tables(C: pd.DataFrame, R: pd.DataFrame, elig: pd.DataFrame) -> dict[str, pd.DataFrame]:
    pos = {d: i for i, d in enumerate(C.index)}
    cum, mar = {}, {}
    m4: dict[int, dict[int, pd.Series]] = {}
    for h in HORIZONS:
        cv, mv = {}, {}
        off: dict[int, dict] = {o: {} for o in range(4)}
        for k, f in enumerate(elig.index):
            i = pos[f]
            c = _ic(C, R, elig, i, f, i, i + h)
            if c is not None:
                cv[f] = c
            m = _ic(C, R, elig, i, f, i + h - 1, i + h)
            if m is not None:
                mv[f] = m
            if h >= 4:
                b = _ic(C, R, elig, i, f, i + h - 4, i + h)
                if b is not None:
                    off[k % 4][f] = b
        cum[h], mar[h] = pd.Series(cv), pd.Series(mv)
        if h >= 4:
            m4[h] = {o: pd.Series(v) for o, v in off.items()}
    return {"cumulative": pd.DataFrame(cum).sort_index(), "marginal": pd.DataFrame(mar).sort_index(), "marginal_4w": m4}


# --------------------------------------------------------------------------------- bootstrap + fit
def blocks(n: int, rng) -> np.ndarray:
    nb = int(np.ceil(n / BLOCK))
    s = rng.integers(0, max(n - BLOCK, 1), size=nb)
    return np.concatenate([np.arange(x, x + BLOCK) for x in s])[:n] % n


def decay_fit(mean_ic: np.ndarray, hs: list[int]) -> float | None:
    h = np.array(hs, dtype=float)
    ok = np.asarray(mean_ic) > 0
    if ok.sum() < 3:
        return None
    b = np.polyfit(h[ok], np.log(np.asarray(mean_ic)[ok]), 1)[0]
    return None if b >= 0 else float(np.log(2) / -b)


def summarise(ic: pd.DataFrame, rng, hs: list[int] | None = None, fit: bool = False) -> dict:
    hs = hs or list(ic.columns)
    v = ic[hs].to_numpy(float)
    means = np.nanmean(v, axis=0)
    B, hl = [], []
    for _ in range(NBOOT):
        idx = blocks(len(ic), rng)
        m = np.nanmean(v[idx], axis=0)
        B.append(m)
        if fit:
            x = decay_fit(m, hs)
            if x is not None and x < 500:
                hl.append(x)
    B = np.array(B)
    rows = [{"h_weeks": h, "added_after_first_look": h in ADDED_AFTER_FIRST_LOOK,
             "mean_ic": round(float(means[j]), 4),
             "ci95": [round(float(np.nanpercentile(B[:, j], 2.5)), 4), round(float(np.nanpercentile(B[:, j], 97.5)), 4)],
             "pct_weeks_positive": round(float((ic[h].dropna() > 0).mean() * 100), 1),
             "n_obs": int(ic[h].notna().sum())} for j, h in enumerate(hs)]
    out = {"per_horizon": rows}
    if fit:
        f = decay_fit(means, hs)
        share = len(hl) / NBOOT * 100
        out |= {"half_life_weeks": None if (f is None or share < 50) else round(f, 2),
                "half_life_ci95": ([round(float(np.percentile(hl, 2.5)), 2), round(float(np.percentile(hl, 97.5)), 2)]
                                   if share >= 50 else None),
                "resamples_that_decayed_pct": round(share, 1),
                "not_estimable_reason": None if (f is not None and share >= 50) else
                ("the least-squares slope on ln(IC) vs h is not negative" if f is None else
                 f"only {share:.1f}% of resamples produced a decaying fit (<50%)")}
    return out


def md_table(rows: list[dict], label: str) -> str:
    out = [f"| horizon | {label} | 95% band (block bootstrap) | obs with IC > 0 | obs |", "|---|---|---|---|---|"]
    for r in rows:
        star = " *" if r["added_after_first_look"] else ""
        out.append(f"| {r['h_weeks']}w{star} | {r['mean_ic']:+.4f} | [{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}] | "
                   f"{r['pct_weeks_positive']}% | {r['n_obs']} |")
    return "\n".join(out)


def main() -> int:
    rng = np.random.default_rng(SEED)
    res: dict = {"tier": "EXPLORE", "window": f"{START}..{CUT}", "cut_asserted": True, "horizons_weeks": HORIZONS,
                 "added_after_first_look": ADDED_AFTER_FIRST_LOOK,
                 "bootstrap": {"kind": "moving block over Fridays", "block_weeks": BLOCK, "resamples": NBOOT,
                               "seed": SEED},
                 "supersedes": "2026-11-17_ic_decay_halflife.md (cumulative returns; withdrawn as a decay measure)"}
    res["rule4_anchor"] = anchor()
    print("anchor ok:", res["rule4_anchor"]["reproduced"])

    C, CRS, SLP, mem = weekly_panel()
    elig = eligibility(C, mem)
    res["universe"] = {"rule": "PIT Nifty-500 at each Friday", "median_cross_section": int(elig.sum(axis=1).median()),
                       "fridays": int(len(elig)), "min_names": MIN_NAMES}
    res["rankers"] = {}
    H4 = [h for h in HORIZONS if h >= 4]
    for name, R in (("crs_dist (live swing ranker, 0094)", CRS), ("sma200_slope_63 (momentum ranker, 0001)", SLP)):
        t = ic_tables(C, R, elig)
        m4_pooled = pd.DataFrame({h: pd.concat(list(t["marginal_4w"][h].values())).sort_index() for h in H4})
        res["rankers"][name] = {
            "cumulative_NOT_A_DECAY_MEASURE": summarise(t["cumulative"], rng),
            "marginal": summarise(t["marginal"], rng, fit=True),
            "marginal_4w_nonoverlapping": summarise(m4_pooled, rng, hs=H4, fit=True),
            "marginal_4w_offsets": {h: {o: round(float(s.mean()), 4) for o, s in t["marginal_4w"][h].items()} for h in H4},
        }
        print(name, "marginal:", [(r["h_weeks"], r["mean_ic"]) for r in res["rankers"][name]["marginal"]["per_horizon"]])

    OUT_JSON.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print("wrote", OUT_JSON.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
