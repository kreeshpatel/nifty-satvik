# Learning Bot — Master Plan (Part 0: the arc)

> Living, hierarchical plan. This file = the top-level parts. Each part gets its own drill-down file
> (`01_part1_data.md`, …) with sub-parts, and those get sub-sub-part plans, until each leaf is a
> buildable, pre-registerable unit. We build in parts; nothing ships until it clears the bar (below).

## What we are building (corrected + honest)

A **Phase-5 conviction learner**: a low-capacity, interpretable model that scores setup **quality**
(0–1) *within* the momentum book's top-15 — "among the 15 names that already cleared the entry gate,
which setups are better?" It sits **on top of** the frozen `sma200_slope_63` signal, never replaces it.
The thing that makes it worth building is **new information** the price doesn't already contain
(fundamentals-depth first). It is judged on out-of-sample + the forward wall, **never in-sample fit**.

This is the disciplined form of "a bot that learns from data." It reuses everything we already built:
`conviction-features`, `leakage-audit`, CPCV, DSR, the overlay harness, the forward wall.

## Two corrections the repo's own contracts force (vs. what the external chats — and my first take — said)

1. **Model = regularized logistic regression on triple-barrier labels — NOT XGBoost/LightGBM.**
   `conviction-features` §3 *explicitly disallows* tree ensembles and neural nets at the conviction
   layer: their feature importance is post-hoc and non-linear interactions across 15-name cross-sections
   can't be audited for lookahead; with only ~1,000–1,500 effective trades they overfit. The sanctioned
   learner is **Form C: `LogisticRegression(C=0.1)` on the 63-day triple-barrier label**, trained strictly
   pre-2017. (XGBoost/LightGBM live only in a *deferred* Phase-6 selection ranker — which already **failed
   once**: 0046 LTR ranker KILLED. We do not restart there.) The `xgboost-lightgbm` skill is still useful —
   for the *feature-importance audit* (gain/permutation/SHAP), not as the live model.

2. **First new data = fundamentals-depth — NOT news/NLP.**
   `conviction-features` *permanently excludes* news-sentiment from the backtest: it is forward-only by
   construction (no PIT news archive to reconstruct history without lookahead — the LLM-lookahead research
   confirms). Fundamentals-depth is **PIT-clean** (Screener store, `period_end` + 90-day availability lag)
   and is already a candidate family (F5). News/NLP can only ever be a *live-only forward-wall overlay*,
   so it is Part 7 (optional, shadow), never the backtested core.

## Verification (2026-07-03) — yes, it is a genuine learner

Checked before committing to the plan: (1) the **training + validation harness already exists and has run**
— `nq/validation/cpcv.py` (combinatorial purged CV), `nq/validation/dsr.py` (deflated Sharpe), prior 682-name
CPCV results in `long_horizon/results/`. (2) `sklearn 1.7.0` / `lightgbm` / `xgboost` **all import and run**
locally — the "ML-banned" rule is a *CI-golden-master reproducibility* guard, not a block on training research
models; the conviction score is a **sidecar** (cfg-gated) so the frozen engine stays byte-identical. (3) The
learner genuinely learns: logistic regression **fits its coefficients** from the triple-barrier win/loss labels
by maximizing likelihood — real training, deliberately low-capacity (the anti-overfit dial, turnable up as
forward evidence grows). "Watch the charts" is honored numerically (features F1–F4 read price/volume action,
PIT-clean) plus a shadow chart-vision assistant (Part 7); pixel pattern→signal stays out (0004 KILL + lookahead).

## The arc — the parts

| Part | Name | What it delivers | Start |
|---|---|---|---|
| **1** | **DATA** | Extend the Screener scrape + PIT store beyond the current 5 fields (`eps_ttm/book_value_ps/roe/debt_equity`) to carry **depth**: revenue, revenue/EPS growth (YoY, QoQ), gross-profitability, margins — each `period_end`-keyed with the 90-day availability lag. Truncation-tested. | **NOW** |
| **2** | **FEATURES** ✅ *(offline core)* | `depth_feature_series` — 7 PIT-safe features (rev_yoy/eps_yoy/np_yoy/op_to_assets/op_margin/op_margin_delta/asset_turnover), strict-before join + truncation gate green, dev-validated on cached data. Live-panel wiring deferred to Part 4/5. → [03_part2_features.md](03_part2_features.md) | done |
| **3** | **SHADOW** | Establish the `conviction_score: null` schema in `signals_today.json`; log raw feature values live without acting on them. The sanctioned shadow phase. | **NOW** |
| **4** | **LEARNER (bake-off)** | Train the conviction learner **several ways** on the 63-day triple-barrier label, pre-2017 only: regularized `LogisticRegression(C=0.1)` (sanctioned Form C) → elastic-net → (at the *deferred selection* layer, forward-gated) shallow gradient-boosted. Also vary label (triple-barrier vs forward-return) + feature set. Produce `conviction_score ∈ [0,1]` + `conviction_quintile`. | **GATED** on paper wall |
| **5** | **VALIDATION (pick OOS-best)** | Every bake-off variant scored through the overlay harness: Tests A/B, **CPCV + DSR** (the harness already exists), feature-importance audit (gain→permutation→SHAP, the one legit use of `xgboost-lightgbm`). Keep the variant that wins **out-of-sample**, not the best backtest. Verdict → registry. | **GATED** |
| **6** | **FORWARD CERT** | The only certifier: on ≥50 paper closes, Q5 conviction quartile must beat Q1 by ≥5pp win-rate. Disagreement with the backtest → REJECT. | **GATED** |
| **7** | **LLM / CHART-VISION ASSISTANT** *(parallel, optional)* | LLM as a *research assistant* — extract structured feature scores from filings/earnings-call text, **annotate charts & propose feature ideas**, write the research journal. **Shadow/ops only; never the signal path.** | optional |

## Sequencing / gating (respects the `conviction-features` deferral)

- **Parts 1–3 start now.** Data acquisition, PIT feature engineering, and shadow logging are exactly the
  "shadow phase" the skill sanctions before the paper gate. They spend **zero trials** and no in-sample fit.
- **Parts 4–6 gate on the base book's paper wall** (≥30 closed trades, ~2 months → ~Sept 2026). Program
  discipline: don't build the enhancement layer until the base has a forward track record. Model *fitting*
  and any PROMOTE/KILL decision wait for the gate; the pre-registration is written before the fit.

## Definition of done (non-negotiable — the bar everything answers to)

Promotion bar (post-tax post-cost **ΔSharpe ≥ +0.10**, **ΔCalmar ≥ +0.05**, 2022-26 sub-period positive,
walk-forward fold-pass ≥ 60%, bootstrap 95% CI on ΔSharpe excludes 0, turnover increase ≤ 30%, mechanism
explainable in one sentence) **AND** forward-wall Q5 − Q1 win-rate ≥ +5pp. Golden master byte-identical
when the overlay is off. Judged OOS, never in-sample fit.

## Design considerations — markets / sectors / seasonality / news (owner guidance, 2026-07-03)

How each maps to what the registry actually permits (so Part-2 feature design doesn't walk into a KILL):

- **Market mechanics** — realistic costs, T+1, circuit limits, ADV/liquidity — already modelled
  (`indian-market-execution`, `portfolio-simulation`). Feed the learner only as *context* (e.g. liquidity
  percentile of a setup), never as timing.
- **Sectors** — sector-selection / rotation **as alpha is a §11 KILL** (sector IC ≈ 0; overlays *hurt* the
  lean years). Permitted only as a **within-name conviction *context* feature** (the F6 family) with an
  **elevated burden**: separate pre-reg + a *positive* 2022-26 sub-period, else reject. Never a selection tilt.
- **Seasonality (India)** — Budget / monsoon / RBI cycle / March FY-end / Diwali / earnings-season. As an
  entry-timing signal it is **market-timing + calendar data-mining → KILL-prone**, skeptical prior. Two
  *legit* uses: (a) **data-plumbing** — earnings-season governs *when* new fundamentals post (the 90-day
  availability lag, Part 1); (b) a PIT-clean seasonal *feature* only if it clears the full bar OOS. Default: not alpha.
- **News** — *already in* as **Part 7** (live-only shadow): can't be PIT-backtested (no PIT news archive;
  LLM-lookahead), so it never enters the backtested core — only annotates/forward-overlays.

Net: fundamentals-depth (Part 1) stays the first real lever; sector/seasonality enter — if at all — as
elevated-burden *conviction context*, judged OOS, never as selection or timing.

## What this is NOT (so it isn't re-proposed)

No XGBoost/NN at the conviction layer (disallowed); no news/NLP in the backtest (forward-only); no
LLM-generated signals (lookahead by construction); no conviction multiplier on position size (frozen cfg
forbids it — a separate experiment if ever); no replacing the momentum ranker (that's 0046, KILLED).

## Next step

Drill into **Part 1 (DATA)** → its sub-parts → sub-sub-parts, until each leaf is a buildable unit with a
one-function PIT contract and a truncation test. (`01_part1_data.md`.)
