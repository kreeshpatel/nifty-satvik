# 0080 — Trend × low-vol as a FILTER: rank by the slope among lower-vol names only

- **ID:** 0080 (the one genuinely-new hybrid after the 0079 battery + the web-evidence cross-reference).
  Owner-approved 2026-07-02.
- **Registered:** 2026-07-02, BEFORE the run. **TRIAL, 2 fixed-cutoff arms** → cumulative_n_trials 95 → 97.
- **Anchor / data:** pinned `baseline_v1`, frozen cfg, corrected universe, 2017-2026; realized-63d vol
  from OHLCV.

## Why this is new (not a relitigation)
The IC screen (0079) found the ONLY two signals with real 63d edge are the **trend slope** and
**low-vol**. Combining them is the mechanism-backed hybrid ("low-vol momentum" / quality-momentum) the
web evidence also supports (Barroso-adjacent; NSE MQ50 spirit). It is distinct from both prior kills:
- **NOT O-006** (which blended a low-vol factor INTO the trend score — a signal blend).
- **NOT O-016** (low-vol as the SOLE ranker — a different strategy).
This is a **conditional filter**: keep the trend ranker, but restrict the eligible set to the lower-vol
subset each day. One parameter (the vol cutoff), one-sentence mechanism.

## Hypothesis
High realized-vol trend names are disproportionately "junk-rally" momentum that reverses hard in a
rotation; filtering them out before ranking by the slope should improve the shape (Sortino, DD, skew)
at modest CAGR cost, because the removed names are lower-quality trends. Falsifier: the filter does NOT
improve Sortino AND DD vs base, OR fails the continuous-slice 2022-26 gate → KILL.

## Candidates (2 fixed cutoffs, NO sweep)
Each day, drop names whose realized-63d vol is **above** the cross-sectional cutoff quantile, then rank
the remainder by the incumbent `sma200_slope_63` (inject as the eligible-set filter — bottom-vol names
keep their trend_rank; high-vol names → ineligible). Cutoffs: **q=0.50** (keep lower-half vol) and
**q=0.33** (keep lowest-third vol). No other cutoff is run under this trial.

## Method
`scripts/run_lowvol_filter.py`: each arm vs the frozen base, paired 63d block bootstrap ΔSharpe/ΔSortino
+ DSR at n_trials=97, continuous-slice 2022-26 (Sharpe + DD), skew, ≥2019 fold-pass, turnover, after-tax.

## Decision rule (pre-committed) — the 7-gate bar
PROMOTE only if ALL: ΔSharpe CI-low > 0 AND point > 0.30, DSR > 0.95, ΔCalmar ≥ +0.05, 2022-26 (sliced)
ΔCAGR > 0, ≥2019 fold-pass ≥ 60%, turnover ≤ +30%, one-sentence mechanism. Positive-but-CI-straddles-0 →
UNDERPOWERED. Else KILL. **Kill criteria (≥2, pre-committed):** (i) ΔSharpe CI-low ≤ 0 → KILL; (ii)
2022-26 sliced ΔCAGR ≤ 0 → KILL. A frozen-cfg universe-filter change is the heavy path (WF + owner
sign-off); this run is EVIDENCE only.

## Skeptical prior
The low-vol sole-ranker (O-016) was strong-but-uncertifiable; filtering (vs replacing) should retain more
trend CAGR while capturing some of the DD benefit — but the sample can't certify a moderate ΔSharpe at ~34
windows (the whole-session lesson), so the most likely honest outcome is UNDERPOWERED (shape-positive, CI
straddles 0) → a forward-wall watch, not a promotion. KILL if it doesn't even improve the shape. Do NOT
retune the cutoff toward a pass — the two values are fixed above.
