# Pre-registration 0066 — v2_long: a PARALLEL long-horizon (20–63d) position model

**Date:** 2026-06-24
**Track:** New parallel model (NOT a variant of the frozen 14d live model) — CPCV-backtestable.
**Status:** PRE-REGISTERED (frozen below). Research-only; live `models/v1` + ensemble siblings + golden master UNTOUCHED. Owner already approved the build direction (plan `sorted-fluttering-hopper`); this freezes the design before the billed cloud run.
**Holdout type:** paired CPCV portfolio metric (Sharpe + CAGR per LdP path) vs the locked 14d honest base, `REPRODUCIBLE_MODE=1`, embargoed at the 63d horizon.
**n_trials:** **+1** (the long model at its single pre-registered operating gate = ONE trade-bearing config) → **57 → 58**. Bump BEFORE the run; log in `n_trials.json::_increment_log` + add a `families` entry.

---

## 0. One-line summary

The live model is a 14-day-horizon learner whose 79 features are all ≤50-day-window momentum derivatives — it is at its information ceiling for that horizon, and every short-horizon tweak has KILLed. This trial builds a **separate, parallel position model at a 20–63 trading-day hold** with a **lean (25), horizon-matched feature set** (12-1 & 6-month momentum, 200d trend, 126d Donchian + RS, 63d vol) and asks one question: **does a horizon-matched ~3-month model beat the 14d base on paired CPCV portfolio Sharpe?** The honest prior is ~30% (Phase 1, OHLCV+macro only), and the dominant expected failure mode is *underpowered* (a true-but-small positive that 7 LdP paths of 63-day holds cannot resolve) — which the runner reports explicitly as distinct from a true null.

---

## 1. Hypothesis (precise) + exact arms

**Motivating measurements (not assumptions):**
- Every base feature is short-horizon (RSI-14, EMA9/21, ATR-14, 20d momentum, 5–10d ROC; inventory in `data_store._compute_stock_features`). Re-horizoning only the *label/exit* on those features (the cancelled dial runs) cannot fairly test a position model.
- Intermediate-term momentum (3–12mo) is a far more robust anomaly than 2-week prediction (Jegadeesh–Titman), and the repo's own crude 30d sibling (V1 features, no matching) was the first direction to land net-positive after honest validation (+0.187 mean Sharpe, 7/11 folds; `multihorizon_ensemble_report.md`).
- The single most valuable *new* data for this horizon — value/quality — has **measured IC that grows with horizon** (0017: earnings-yield IC-IR 0.10@14d → 0.20@63d → 0.25@126d). That is the Phase-2 prize; **Phase 1 (this trial) is price/trend features only** (no fundamentals → no ToS exposure).

**H1 (directional):** A 63d-horizon two-head LightGBM on `V2_LONG_FEATURES` (25), traded with a 20–63d flexible-exit policy (first stop/target, √t-scaled stop, hard 63d cap), beats the locked 14d base on paired CPCV portfolio Sharpe (CI-low > 0, point > 0.3) and clears the empirical-skew DSR at the cumulative n_trials.

**H0 (null we must reject to PROMOTE):** the long model is ≤ the 14d base on the paired portfolio metric, OR any positive point estimate is below the minimum-detectable-effect (underpowered, not a real edge), OR it is degenerate / blow-up-driven / single-group-load-bearing.

### Arms (FROZEN) — both trained ONCE per split (no frozen pickle → no leak)

| arm | model | features | return head | conf head | entry gate | exits | role |
|---|---|---|---|---|---|---|---|
| **BASE** | 14d | V1 (79) | fwd_max_14d | hit_4pct_14d | 0.92 / 8.0 (`models/v1/config.json`) | native 14d hybrid | locked yardstick |
| **LONG** | 63d | `V2_LONG_FEATURES` (25) | fwd_max_63d | tb_hit_63d (√t barrier) | **0.50 / 10.0** (frozen `LONG_GATE`) | min-hold 20d / hard-max 63d, √t-scaled ATR stop (4.24×), first SL/target | the candidate |

**`V2_LONG_FEATURES` (frozen, 25 = 13 kept + 12 new)** — the exact list is asserted in `src/pillars/feature_lists.py` (`assert len(V2_LONG_FEATURES) == 25`):
- KEEP (horizon-agnostic): `position_in_52w`, `dist_from_52w_high`, `dist_from_52w_low`, `new_high_52w`, `rs_rank_universe_20d`, `rs_rank_sector_20d`, `rs_rank_acceleration`, `adx_14`, `nifty_rsi`, `india_vix`, `vix_trend`, `market_regime`, `global_risk_score`.
- NEW (horizon-matched, all lookahead-safe, computed in the shared kernels): `mom_252_21`, `mom_126`, `mom_63`, `dist_from_200dma`, `above_200dma`, `sma200_slope_63`, `donchian_pos_126`, `donchian_breakout_126`, `rs_rank_universe_126`, `rs_rank_sector_126`, `atr_pct_63`, `vol_126`.

**Labels (FROZEN):**
- Return head `fwd_max_63d` = best intraday excursion over `[i+1, i+63]` (matches the trade-to-target system; `fwd_return_63d` kept diagnostic only).
- Confidence head `tb_hit_63d` = path-aware triple barrier, **both barriers √t-scaled** off the validated 14d anchor (target 4%→8.49%, stop 2×ATR→4.24×ATR(63)), first-touch, time-barrier→0. √t scaling holds each barrier's random-touch probability horizon-invariant so the label does not saturate.

**Exit policy (FROZEN, `V2_LONG_CONFIG`):** `min_hold_days=20` (suppress target/time/trailing below day 20; the hard STOP is NEVER suppressed — risk control), `time_stop_hard_max_days=63` (clean hard cap, extension disabled), `stop_mult=4.24` (√t-matched to the label), trailing protective at +12.7%/5%. Mirrors the owner's "min 20 / max 63 / first SL or target" spec.

**Model capacity (FROZEN, `V2_LONG_LGBM`):** the LONG arm trains LightGBM at REDUCED capacity — `max_depth=4`, `num_leaves=15`, `min_child_samples=100`, `n_estimators=200` — vs the V1 dense-label defaults (depth 8 / 500 trees). A 63d hold yields ~4 non-overlapping obs/stock/yr, so the V1 capacity is high per-effective-observation and would overfit on the axis the lean 25-feature set does NOT address (tree capacity, not feature count — the overfit-skeptic's pre-run requirement). The BASE arm keeps the V1 defaults (it is the locked yardstick and must reproduce the base). Pre-committed before the run.

---

## 2. Harness + window (FROZEN)

- CPCV: **`N_GROUPS=8`, `N_TEST_GROUPS=2`** → C(8,2)=28 splits, `n_backtest_paths(8,2)` = **7 LdP paths**. NOT the base 10 groups — `EMBARGO_OBS=63` would erase a 10-group partition.
- Purge + embargo: **`HORIZON_OBS=63`, `EMBARGO_OBS=63`** (≥ the 63d label → full two-sided purge; no train/test label leak). Window **2015-01-01 → 2024-12-31**.
- Per split: train `pm_base` (14d, V1) and `pm_long` (63d, `active_features=V2_LONG_FEATURES`) ONCE on the purged train rows under `REPRODUCIBLE_MODE=1`; `filter_to_v2_long` drops the ~252-bar warm-up NaN rows (else `train()` fillna(0)s them into fake-zero momentum). Then `engine.run(...)` per test group per arm; store `daily_returns_from_equity_curve(res.equity_curve)`.
- LONG predictions force confidence=0 on warm-up-incomplete rows (any NaN in the 25 features) → those stocks are never traded (no fake-zero-feature entries).
- Path assembly: each of the 7 paths stitches one OOS daily series covering all 8 groups once; per-path `sharpe(ser)` + `_cagr(ser)`; paired (LONG − BASE) deltas across the 7 paths.
- Runner: `diagnostics/run_cpcv_long.py`; output `diagnostics/cpcv_long.json` (atomic write per split). Workflow: `cpcv-research.yml --ref feat/v2-long-horizon -f runner=run_cpcv_long`. No live/engine file changes; golden master untouched (the only engine touch — `min_hold_days` — is a default-0 no-op verified byte-identical).

---

## 3. The statistical-power problem (the honest core — pre-stated)

A 63-day hold yields **~4 non-overlapping trades per stock per year**, so this model is **harder to prove than a 14d one, not easier**: fewer independent observations → wider CIs, a bigger embargo (63 vs 14) eating the timeline, and the SAME DSR bar on thinner evidence. The academic robustness of intermediate momentum raises the *prior* that an edge exists; it does **not** lower the *evidentiary* bar.

**Pre-committed:** the runner computes and reports `min_detectable_effect(dispersion_of_paired_dSharpe, n_paths)` — the smallest paired dSharpe this 7-path design can resolve. A result is classified into THREE outcomes, not two:
- **PROMOTE-CANDIDATE** — all §4 gates pass.
- **UNDERPOWERED** — paired dSharpe point > 0 but < the min-detectable-effect (and/or DSR ≤ 0.95): a real-but-unresolvable positive. Reported AS underpowered; **NOT promoted**, NOT recorded as a null. This is the dominant expected outcome and is honest grounds for a Phase-2 (fundamentals) or more-data revisit — never grounds to ship.
- **KILL** — point ≤ 0, or degenerate/blow-up/group-load-bearing.

Effective sample size (≈4 non-overlapping holds/stock/yr; 7 independent paths) is reported in the headline — NOT the raw row count (which over-states confidence). The runner also emits the LONG **train-fit** (conf-AUC / return-corr per split) so a high-train/weak-OOS overfit is visible, and **trades/year** so the ≥150 non-degeneracy floor is never mistaken for the statistical denominator (= n_paths).

---

## 4. Pre-committed PASS/KILL gate (ALL must hold to PROMOTE-CANDIDATE)

Scored vs the locked 14d honest base on the FROZEN harness. PROMOTE-CANDIDATE only if ALL hold:

1. **Portfolio Sharpe lift, real:** paired (LONG − BASE) **dSharpe CI-low > 0 AND point > 0.3** (NOISE_FLOOR), CI over the 7 LdP paths. [primary]
2. **DSR:** `deflated_sharpe_ratio(LONG)` **> 0.95**, EMPIRICAL skew/kurtosis of LONG's pooled daily returns (NOT normal 0/3), `n_observations`=7 paths, at `cumulative_n_trials` (=58).
3. **Non-degenerate:** LONG total trades across paths **≥ 150** AND every path traded (> 0). (A 63d model SHOULD trade far less than the 14d base — so this is an absolute floor, NOT the 14d fill-ratio bar.)
4. **No per-group blow-up:** no group where LONG group-CAGR is > 15pp below BASE with a negative LONG Sharpe.
5. **Drop-best-group robust:** the WORST jackknife of the paired dSharpe point estimate — over both **single-group AND adjacent-group-PAIR** drops — stays **> 0** (no single calendar group, and no 2-adjacent-group bull cluster e.g. a 2020∪2021 run split across groups, is load-bearing).

**KILL / UNDERPOWERED on any miss** (per §3 classification). Record the full readout regardless (arm Sharpe/CAGR/trades, paired CI, DSR, MDE, jackknife, per-group). **Skeptic-agent clearance** (overfit-skeptic + backtest-validator + flaw-hunter) is a pre-run precondition; a PASS that the skeptic overturns does not promote.

**What a PROMOTE-CANDIDATE authorizes:** a research finding → a separate, flag-gated, golden-master-safe wiring change → a forward-wall shadow period. NEVER a direct live change. The live 14d model is untouched throughout.

---

## 5. Interpretation guide (pre-stated)

- **All gates pass:** horizon-matching broke the 14d ceiling on price/trend features alone → proceed to skeptic clearance + owner sign-off + shadow; and Phase 2 (value/quality overlay, the 0017 126d IC) becomes the high-prior follow-on.
- **Underpowered positive (the modal prior):** a real-but-small edge the data can't yet resolve → do NOT ship; the legitimate next moves are Phase-2 fundamentals (orthogonal signal that the 0017 IC says grows to this horizon) and forward-wall accrual — NOT re-rolling the backtest.
- **KILL (point ≤ 0):** the long horizon does not help with horizon-matched price/trend features → the ceiling is not horizon, it is the trailing-momentum information class; the only remaining lever is genuinely orthogonal data (Phase 2), evaluated on its own pre-registration.
- **Degenerate / blow-up / one-group:** the operating gate or a single bull group is doing the work → re-registered gate or KILL, never ship.

---

## 6. Governance (isolation + compliance-safe)

- **Zero live risk by construction.** `models/v2_long/` is never auto-loaded (live single-model uses `models/v1`; ensemble is hardwired to (14,7,30)); `V1_FEATURES` is frozen (its `assert len==79` stays green); the golden master loads only `models/v1` and the lone engine touch (`min_hold_days`, default 0) is byte-identical (verified: `tests/integration/test_golden_master.py` green). Rollback = delete the branch.
- **Phase 2 (fundamentals value/quality + delivery-%) is a SEPARATE pre-registration** and requires explicit owner go-ahead (the Screener scrape is ToS-sensitive). It is NOT consumed or pre-empted by this trial.
- **Compliance-safe framing:** this evaluates a candidate model-generated, decision-support strategy. It makes no claim about and offers no guarantee of live outcomes; it authorizes a research measurement only. Nothing served to the ~10 paying users changes until a PROMOTE-CANDIDATE clears skeptic review, owner sign-off, golden-master safety, and a forward-wall shadow.

---

## 7. Provenance / cross-references

- **Plan:** `~/.claude/plans/sorted-fluttering-hopper.md` (owner-approved). Design doc grounding in `diagnostics/research/swing_feature_research_2026_06_24.md`.
- **Template:** `diagnostics/run_cpcv_7d_2x2.py` (0058 — paired CPCV portfolio Sharpe, empirical-skew DSR, per-group robustness). Pre-reg `0058-7d-horizon-clean-2x2.md`.
- **Prior art / priors:** 30d sibling MARGINAL (`multihorizon_ensemble_report.md`); value-IC-vs-horizon `0017-pit-fundamentals-value-quality.md`; short-horizon ceiling KILLs (0004/0005/0010); the cancelled dial runs (superseded by this trial — they tested exit-only re-horizoning on fixed short features).
- **Machinery:** `src/validation/cpcv.py`, `src/validation/composition.py` (`sharpe`, `daily_returns_from_equity_curve`), `src/validation/overfitting.py` (`deflated_sharpe_ratio`, `cumulative_n_trials`), `src/validation/power.py` (`min_detectable_effect`, `inv_norm_cdf`).
- **New artifacts (all on `feat/v2-long-horizon`):** `feature_lists.V2_LONG_FEATURES`; the 10 long-window features + `fwd_max_63d`/`tb_hit_63d` in `data_store`; the 126d RS legs in `cross_sectional_features`; `min_hold_days` in `exit_logic`; `train_v2_long.py`; `run_cpcv_long.py`; tests `test_v2_long_features.py` + `test_min_hold_exit.py`.

---

## 8. Skeptic's dissent (filed against this trial, pre-committed)

*The standing objection the trial must answer; it cannot be softened post-hoc.*

1. **It is still trailing-momentum.** The 25 features are price/trend derivatives re-expressed at longer windows; the kill-record says this information class is ceilinged. Re-windowing 14d→200d does not manufacture *new* information — it relocates the same momentum signal to the horizon where it is most robust. The genuinely orthogonal lever (value/quality) is deferred to Phase 2, so Phase 1's prior of beating the base on price features alone is **low (~20–25%)**, and a KILL here should be read as "the ceiling is the information class, not the horizon," not "longer holds are bad."
2. **The modal outcome is underpowered, and underpowered must not soft-promote.** 7 paths × 63-day holds is thin; a +0.2-class paired dSharpe will likely have a CI straddling 0 and/or DSR < 0.95. The §3 three-way classification exists precisely so this is reported as *underpowered*, not massaged into a PROMOTE — and underpowered authorizes Phase-2 / more-data, never a ship.
3. **The operating gate is a guess.** `LONG_GATE = 0.50 / 10.0` was set a priori (the return floor does the selecting; confidence is a low bar). If it proves degenerate (gate 3 fails) the answer is a *re-registered* gate, not a sweep mined for the best cell. The non-degeneracy floor (≥150 trades, every path > 0) is the guard.
4. **CAGR is not the judge.** A 63d model will mechanically show different turnover/CAGR; the primary is **risk-adjusted (Sharpe)**, paired, with the drop-best-group jackknife guarding against a single bull group (2020/2021 analogue) carrying the lift. A CAGR-up/Sharpe-flat result is NOT a promote.
5. **Bottom line:** proceed as a *measurement*. The disciplined expected outcome is UNDERPOWERED or KILL, which still pays — it tells us whether ~3 months is worth the Phase-2 data investment. PROMOTE only on all five gates + skeptic clearance; never on the CAGR or the point estimate alone.

**Result:** _TBD — pending the cloud CPCV run._
