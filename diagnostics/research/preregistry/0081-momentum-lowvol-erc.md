# 0081 — Momentum + low-vol at equal-risk-contribution: does the portfolio-level combination beat momentum alone?

- **ID:** 0081 (the multi-sleeve thesis — `forward/prereg.md` §9; the one genuinely-new experiment of the
  Part-C backlog). Owner-approved 2026-07-02.
- **Registered:** 2026-07-02, BEFORE the run. **TRIAL, 1 arm** → cumulative_n_trials 97 → 98.
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`), frozen cfg, corrected universe, 2017-2026.

## Why this is new (not a relitigation)
The IC screen + 0079/0080/O-016 triply-signpost **low-vol** as the one real lever. Prior low-vol tests are
distinct from this: **O-006** blended low-vol INTO the trend *score* (KILL); **O-016** ranked by low-vol as a
*sole replacement* ranker (uncertifiable). This is a **portfolio-level combination of two separate books** —
the momentum book (frozen) + a standalone low-vol book — at risk-parity. Untested. It is the one Sharpe-lift
that does not route through the spent single-sleeve trial budget: combining two low-correlation positive-edge
sleeves *mechanically* raises Sharpe.

## Hypothesis
Combining the frozen momentum book (`r_mom`) with a low-vol sleeve (`r_lv`, ranked by inverse realized-63d
vol — O-016's ranker) at **equal-risk-contribution** raises the blended Sharpe vs momentum-alone and cuts the
drawdown, driven by their low return correlation. Falsifier: combined Sharpe ≤ momentum-alone, OR the low-vol
sleeve is not actually low-correlation (ρ > 0.7), OR the ΔSharpe point estimate ≤ 0.

## Candidate (fixed, no sweep)
Two books over 2017-2026: `r_mom` = base (`sma200_slope_63`); `r_lv` = a `simulate` with
`trend_rank = pctile(−realized_63d_vol)`, same universe/exits/caps. Each **quarter-start**, weights from
trailing-63d realized vol: `w_i = (1/σ_i) / Σ(1/σ_j)` (the 2-asset risk-parity/inverse-vol solution), held
the quarter. Combined daily return `r_c = w_mom·r_mom + w_lv·r_lv`.

## Method
`scripts/run_erc_combo.py`: paired 63d block bootstrap (n=5000) of ΔSharpe & ΔSortino (`r_c` − `r_mom`), DSR
at n_trials=98, continuous-slice 2022-26, plus the return correlation ρ(r_mom, r_lv) and each book's
standalone Sharpe/DD. Report gross Sharpe/Sortino/MaxDD/Calmar/CAGR of the combined vs momentum-alone.
(After-tax for the combined book needs per-book trade-log STCG then a weighted merge — reported approximate
/ deferred; the gross Sharpe/DD *shape* is the diversification test and is what the bar keys on here.)

## Decision rule (pre-committed) — the promotion bar
PROMOTE only if ALL: combined ΔSharpe CI-low > 0 AND point > 0.10, DSR > 0.95, ΔCalmar ≥ +0.05, 2022-26
combined Sharpe > base, ρ(r_mom, r_lv) < 0.7 (real diversification), mechanism one sentence. Positive-but-CI-
straddles-0 → UNDERPOWERED. Else KILL. **A PROMOTE routes the low-vol sleeve to the FORWARD WALL as a watched
sleeve** (a §7 shadow swap) — never to the frozen cfg on this in-sample run.

## Skeptical prior
The combination *should* raise Sharpe (diversification of two low-correlation sleeves) — that part is near-
mechanical. BUT the benefit rests on the low-vol sleeve's edge being **real**, which is uncertifiable in-sample
(O-016: Sharpe 1.06 but ΔSharpe CI straddles 0, DSR 0.35). So the most likely honest outcome is a positive
combined-Sharpe point estimate with a ΔSharpe CI that straddles 0 → **UNDERPOWERED** → the low-vol sleeve goes
on the forward wall as the real test. This experiment's value is *deciding whether to watch low-vol forward*,
not certifying it in-sample. Do NOT retune the weighting toward a pass.
