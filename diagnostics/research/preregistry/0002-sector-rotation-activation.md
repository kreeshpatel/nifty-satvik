# 0002 — Activate dynamic sector-rotation features (retrain) + test generalization

- **ID:** 0002
- **Registered:** 2026-05-30
- **Holdout:** unseen-universe (Holdout #2) for confirmation; forward-wall (Holdout #1) for ongoing
- **n_trials (cumulative):** 2
- **Status:** PENDING

## Motivation

The 2026-05-30 sector audit found that **6 of 10 sector features are hardcoded
constants** in both the training pickle and live: `feature_enrichment.py`
`SECTOR_COMPUTED_COLS` only populates `sector_monthly_avg`, `sector_monthly_wr`,
`is_strong_month`, `seasonal_score`. The **dynamic** rotation features —
`sector_momentum_20d` (0), `sector_acceleration` (0), `sector_rank_20d` (5) — are
computed by `sector_intelligence.get_features()` but defaulted out, so the model
has **no signal for which sector is leading or crashing right now** (e.g. a current
chemical-sector drawdown is invisible). `seasonal_score`/`is_strong_month` are
computed but measured **<1% importance** — effectively ignored.

## Hypothesis

Activating the three dynamic rotation features (`sector_momentum_20d`,
`sector_acceleration`, `sector_rank_20d`) — computing real values in BOTH the
training-feature build and the live inference path, then **retraining** — improves
risk-adjusted after-cost performance and lets the model down-weight stocks in
currently-weak sectors instead of being blind to current sector regime.

**Skeptical prior (stated up front):** seasonal/calendar sector features already
measured <1% importance, and the archived sector-month / stock-month seasonality
sweeps (`archive/path-b-research-20260529`) were **not** promoted. The base rate for
"sector features help" is low. This experiment exists to **kill the idea cheaply**
or find a real, generalizing signal — not to confirm a belief.

## Scope (exactly one candidate)

ONE candidate config: the three dynamic rotation features activated (real values,
train + inference). **No sweep** over feature subsets — that would inflate
`n_trials`. If this single candidate fails, the idea is rejected for now; if it
supports, a follow-up (`0003`) may explore a richer current-sector-regime feature.

## Selection step (dev / generation — walk-forward)

Build a candidate model:
1. Add the three features to `SECTOR_COMPUTED_COLS` so `enrich_row` +
   `enrich_with_layers` populate real values in both paths.
2. Rebuild `features.pkl` (`compute_all_features` + `enrich_with_layers`) on the
   training universe.
3. Retrain via `train.py` — same hyperparams, same 2010-2024 window, same gate —
   into an **isolated** dir `models/v1_sector_candidate/` (never overwrite
   `models/v1/`).

Run the existing retrain gate (`src/runners/_retrain_gate.py`) candidate-vs-baseline
on the standard walk-forward folds. Candidate must clear the existing gate:
**≥70% per-fold Sharpe-wins** AND the regression checks (mean Sharpe ≥ −10%,
CAGR ≥ −10%, WR ≥ −5pp, trade count ≥ 50% of baseline).

- FAILS gate → **KILL** (dynamic sector features don't help even in-sample).
- PASSES gate → proceed to confirmation. The walk-forward is **generation only**;
  passing is necessary, not sufficient.

## Confirmation step (holdout — decisive)

If the candidate passes selection, run BOTH the candidate and the current baseline
through the unseen-universe OOS harness (`run_oos_unseen_universe.py`, same tickers
+ period as `0001`).

**Primary metric:** Δ(mean after-cost per-trade return %) = candidate − baseline on
the unseen universe, with 95% bootstrap CI on the paired difference.
Plus: Deflated Sharpe Ratio of the candidate's unseen-universe Sharpe at
`n_trials = 2` (`overfitting.deflated_sharpe_ratio`).

## Decision rule (fixed in advance)

- **SUPPORT (weak):** PASSES walk-forward gate **AND** unseen-universe Δ per-trade
  CI lower bound ≥ 0 (candidate no worse on unseen stocks) **AND** candidate
  DSR > 0.95. → eligible to begin forward-wall confirmation; **NOT** auto-promoted.
- **KILL:** FAILS walk-forward gate, **OR** unseen-universe Δ per-trade CI upper
  bound < 0 (candidate worse on unseen stocks).
- **INCONCLUSIVE:** passes gate but unseen-universe Δ CI straddles 0, or unseen
  trade count < 30. → needs forward-wall (paper) evidence before any promotion.

A SUPPORT result does **not** promote the model — promotion still requires
forward-wall (Holdout #1) confirmation per `../HOLDOUT.md`. This experiment can only
kill the idea or advance it to forward testing.

## Run params (fixed before execution)

- Features activated: `sector_momentum_20d`, `sector_acceleration`,
  `sector_rank_20d` (real values, both pipeline paths).
- Train window 2010-01-01 .. 2024-12-31, v1 default hyperparams (both unchanged).
- Candidate artifacts isolated in `models/v1_sector_candidate/`; `features.pkl` /
  `ohlcv.pkl` backed up + restored (same isolation discipline as `0001`).
- Seed via `src/repro/seeds.py`.

## Result — SCREEN (2026-05-30)

Importance screen via `diagnostics/run_0002_sector_candidate.py`: rebuilt
full-history `sector_intelligence` (bypassing the 500-day truncation in-process),
**computed** the 3 dynamic features from sector daily returns (key finding:
`enrich_with_layers` has NO code to compute momentum/rank/acceleration — they were
*unimplemented*, not merely toggled off; `data_store.py:787-799` only assigns the 4
monthly cols), retrained a candidate, read feature importance. Caches isolated +
restored.

**Activation confirmed real** (max distinct over 50 tickers: momentum 3652,
acceleration 3652, rank 18).

**Candidate importance (3 activated features):**

| Feature | return head | confidence head |
|---|---|---|
| sector_momentum_20d | 3.37% (rank 12/72) | **4.01% (rank 9/72)** |
| sector_rank_20d | 1.95% (rank 15) | 1.45% (rank 17) |
| sector_acceleration | 1.23% (rank 23) | 1.67% (rank 16) |

**Verdict: INCONCLUSIVE — promising but CONFOUNDED.**

- The naive KILL **prior is overturned**: when fed REAL values the model uses these
  features (momentum reaches rank 9 in the confidence head). The historical
  "<1% importance" was a *constant-feature artifact* (a constant gets 0 splits) —
  never evidence of uselessness.
- **Confound (do not trust the magnitude):** the local `data/features.pkl` (Apr 21)
  PREDATES Phase A, so 7 per-stock pre-move features (atr_compression_ratio,
  bb_width_pct_30, consolidation_score_20d, mtf_alignment_score, obv_trend_30d, ...)
  were MISSING → candidate trained on **72 features, not 79**. With 7 signal-carriers
  absent, sector features face less split competition → importance likely inflated.
- Importance ≠ profit regardless.

**Clean test still owed (selection step not yet validly run):** full
`compute_all_features` rebuild (regenerate the 7 Phase-A per-stock features) +
sector activation + retrain → clean importance screen vs all 79 → if it survives,
the pre-registered walk-forward gate → OOS confirm. n_trials still = 1 (this screen
is diagnostic, not the pre-registered selection run).

### Clean re-screen — confound removed (2026-05-30, `--full-rebuild`)

Full `compute_all_features` rebuild (regenerated the 7 Phase-A per-stock features) +
activate 3 + retrain → candidate trained on the full **79 features**. Importance vs
all 79:

| Feature | return head | confidence head |
|---|---|---|
| sector_momentum_20d | 3.51% (rank 11/79) | 3.55% (rank 10/79) |
| sector_acceleration | 0.97% (rank 28) | 1.73% (rank 15) |
| sector_rank_20d | 1.56% (rank 21) | 1.31% (rank 21) |

**Signal SURVIVES de-confounding.** sector_momentum_20d holds rank ~10-11/79 with
Phase-A back competing (was 9/72 at 4.0% confounded → 10/79 at 3.55% clean). Its
importance was NOT a missing-features artifact; it genuinely earns splits against
the full set. The KILL prior is decisively overturned.

**Tempering: importance != profit, and the fit barely moved.** Candidate
return_corr 0.535 vs baseline 0.532; conf_AUC 0.729 vs 0.725 — noise-level in-sample.
The model uses the feature but is nearly identical overall, so the gate may show
marginal/no after-cost gain.

**Pre-registered selection still owed (decisive step):** walk-forward gate, candidate
(sector active) vs a baseline retrained on the SAME local rebuild with the 3 sector
cols left constant — ≥70% Sharpe-wins + regression checks → OOS confirm. Multi-hour.
Status: **ESCALATE (de-confounded); gate pending.** n_trials = 1.

## Existence proof (2026-06-03) — a real sector-MOMENTUM signal exists

Upstream of "does the feature help the model": does sector-level predictability
exist at all? Study (`diagnostics/sector_pattern_study.py`, 496 tickers, 18
sectors, 2011-2026, equal-weight sector returns):

- **Sector MOMENTUM persists**: rank sectors by trailing 3-month return, hold 1
  month — mean rank-IC **0.0896** (positive in 66.9% of 178 months); top-3 minus
  bottom-3 sectors next month = **+1.05%/month, t=2.75** (significant).
- **Sector SEASONALITY is ~noise**: split-half month-ranking corr 0.075 (positive
  58% of months).

**The model has it backwards:** the DEAD constant features
(`sector_momentum_20d`, `sector_rank_20d`, `sector_acceleration`) are exactly the
ones that would capture the REAL momentum signal; the LIVE features
(`sector_monthly_avg/wr`, `seasonal_score`) capture only the weak seasonality.
This is an existence proof that there is genuine, significant, un-captured
sector-momentum edge — it strengthens the case for the owed walk-forward gate.

Caveat: sector-level long-short result, survivorship-biased universe, local
history — it proves the SIGNAL exists, not that wiring it into the per-stock model
lifts after-cost expectancy (that is still the owed gate + OOS). But unlike the
prior "likely marginal" read, the underlying signal is now confirmed real.
Status: **ESCALATE — existence-confirmed; walk-forward gate + OOS warranted.**

## Decisive OOS (2026-06-03) — INCONCLUSIVE/KILL as a per-stock feature

Reused the existing sector-active candidate (`models/v1_sector_candidate`, 79f,
real sector_momentum/rank/accel) vs the live sector-constant model, on the 145
unseen tickers, single-model both sides, sector signals computed from
full-history training-universe sector returns (`run_0002_oos.py`):

| | trades | per-trade | WR | Sharpe |
|---|---|---|---|---|
| baseline (sector-constant) | 355 | +4.22% [3.00, 5.46] | 69.6% | 2.86 |
| candidate (sector-active) | 245 | +4.35% [2.66, 6.12] | 62.9% | 2.34 |

Delta +0.14%/trade — noise (CIs overlap); WR and Sharpe both DROPPED. **KILL as a
per-stock feature.** The existence proof stands (sector momentum is real, t=2.75),
but it's a sector-ROTATION/allocation edge, not a stock-SELECTION feature — the
per-stock momentum + `rs_rank` features already capture what's useful for picking
individual names, so the sector-level signal is redundant as a model input. To
capture the +1.05%/month would require a sector-rotation OVERLAY (portfolio tilt
toward top-momentum sectors) — a separate strategy with its own risk budget, not
a feature retrain. 0002-as-feature is closed; 0002-as-overlay is a new, motivated
(but skeptical-prior) future direction. Status: **COMPLETE — KILL (feature); the
real edge needs an allocation overlay, not the model.**
