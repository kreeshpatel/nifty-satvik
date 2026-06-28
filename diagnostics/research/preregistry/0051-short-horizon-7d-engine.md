# 0051 — short-horizon (7d) engine: does faster capital recycling beat the 14d base?

- **ID:** 0051. Registered 2026-06-19, BEFORE the validation run. Cloud-run. **The #1 forward lever**
  (per the 0031 readout) — and the direct answer to the owner's opportunity-cost concern: the book
  runs ~27% deployed, the 30-slot cap never binds, and the system is silent for stretches while real
  movers run. A 7d horizon recycles capital ~2.4× faster → more deployment, faster capture, fewer
  silent days — WITHOUT lowering per-trade quality (the proven trap).
- **Type:** model/horizon trial. Counts **+1** cumulative trial — bump `n_trials.json` (52) BEFORE the run.
- **Skeptic gate:** `overfit-skeptic` + `flaw-hunter` + `backtest-validator` must clear before PROMOTE.

## Prior evidence (0031, GREEN build/no-build gate)
Walk-forward pooled ≥2019: **7d Sharpe +1.10 / CAGR +33.2% vs 14d +0.97 / +26.2%**; 1085 vs 448
trades (**2.42×**); per-trade edge shrank −0.39pp but turnover MORE than compensated → higher CAGR
AND Sharpe (net of costs incl. 5% ADV cap + sqrt impact). 2024 flipped −7.6% → +23% (the 14d held
faders too long). This is the **capital-recycling** lever 0028 located — categorically different from
"trade more lower-quality" (the per-trade-alpha axis that is ceilinged). **0031 proved the DIRECTION
is alive, NOT the magnitude** — it was confounded + fragile + not gate-significant. This trial resolves that.

## The three things 0031 flagged — all resolved here
1. **AUD-041 confound (FIXED):** v1_7d gated on `hit_4pct_14d` (14d touch prob) while exiting at 7d.
   Now: clean `hit_4pct_7d` label added to `data_store` (`fwd_max_7d>=4`), trainer + this engine use it
   → a horizon-consistent 7d model (7d return head `fwd_max_7d` + 7d conf head `hit_4pct_7d`).
2. **Per-fold FRAGILITY:** 0031 won 4 folds / lost ~4 (2018 −6%→−32%), pooled mean carried by 2021
   (+172%) + the 2024 flip; the +0.135 Sharpe delta was NOT DSR-significant + had no CI. → resolved by
   **CPCV** (combinatorial paths test fold-robustness) + a paired CI + DSR + a per-fold/per-path floor.
3. **Turnover cost realism:** 2.42× turnover stresses the impact/ADV model. → capacity-aware costs
   (5% ADV cap + sqrt impact) stay ON; report trades/yr + the per-trade-edge erosion explicitly.

## Method
`diagnostics/run_cpcv_7d.py` (to build) — paired CPCV of the clean 7d engine vs the 14d base on the
SAME 45 splits / 9 LdP paths, models trained PER SPLIT (7d engine: PredictionModel with
`return_label=fwd_max_7d`, `confidence_label=hit_4pct_7d`, `prediction_days=7`, 7d time-stop, gate
conf≥0.88/min-ret≥5.0 per the v1_7d config; 14d = the locked base). **Metric = PORTFOLIO Sharpe + CAGR
per reconstructed path (from the equity curve), NOT per-trade IR** — judging a frequency/recycling
lever on per-trade IR is the LTR (0046) mistake; the whole point is that turnover compensates a smaller
per-trade edge. Report per path: portfolio Sharpe, CAGR, trade count, mean deployment %, paired Δ vs base.

## Frozen decision rule
PROMOTE the 7d engine over the 14d base ONLY IF ALL hold:
1. paired **portfolio-Sharpe** Δ CI-low > 0 **AND** paired **CAGR** Δ CI-low > 0 (95%, over the 9 paths);
2. **DSR > 0.95** at cumulative n_trials (=52);
3. **per-fold robustness:** the 7d engine does NOT catastrophically lose any single bad year
   (e.g. no fold where 7d CAGR < 14d CAGR by more than a pre-set −15pp **and** 7d Sharpe < 0) — i.e.
   the 2018-style −32% blowup must not recur on clean labels;
4. capacity-aware costs ON; turnover (trades/yr) reported + defensible (the EX-E ceiling);
5. `overfit-skeptic` + `flaw-hunter` + `backtest-validator` clear it; golden-master untouched (research only).
Else → **KILL** (record the null — fragility/cost beat the recycling benefit). No partial credit.

## Result
**Status: REGISTERED — clean `hit_4pct_7d` label added (data_store) + trainer fixed (AUD-041); the
CPCV portfolio-metric runner + cloud run PENDING.** Features.pkl must be rebuilt to carry `hit_4pct_7d`.
