# 0014 — Mean-reversion sleeve (Phase 2)

- **ID** — 0014
- **Registered** — 2026-06-06
- **Hypothesis** — A rules-based mean-reversion (MR) sleeve that fires ONLY in
  CHOPPY regimes (where momentum whipsaws) adds trades and positive expectancy
  in exactly the periods momentum fails — the non-BEAR bad years (2022/2023/2025)
  that Phase 0/1 showed the momentum book + exposure overlay cannot fix. Merged
  with the momentum book it raises aggregate trades/yr toward 120 and lifts the
  weak-fold returns, while holding merged-book WR ≥ baseline − 3pp. Predicted:
  +trades in 2022/23/25, those folds' Sharpe up, mean Sharpe not regressed, MR
  trades weakly/negatively correlated with momentum trades (the diversification
  claim).
- **Holdout** — `unseen-universe` (per-trade generalization of the MR rule) →
  `forward-wall`. Walk-forward dev folds generate/tune; holdout confirms.
- **Primary metric** — balanced composite of the MERGED book (momentum + MR) vs
  the momentum-only baseline. The trade-count and weak-fold-return axes carry the
  thesis.
- **Decision rule** — PROMOTE iff: (a) `evaluate_candidate` floors hold on the
  merged book (incl. WR within 5pp, mean Sharpe ≤10% regression, trade-count ≥
  baseline); (b) drawdown floor holds; (c) composite > 0; (d) DSR > 0.95 at
  n_trials; (e) the MR sleeve's STANDALONE fold expectancy is positive AND its
  trade-level correlation to the momentum sleeve is low (|ρ| < ~0.3) — if MR
  isn't actually uncorrelated it's noise, not diversification → KILL; (f) the
  gain is spread across ≥2 chop/bad folds, not one. Else KILL.
- **n_trials (cumulative)** — **19** (18 after 0013 + 1 MR variant). If MR
  parameter variants are swept, increment per variant (run serially).
- **Status** — PENDING

## Sleeve design (rules-based, NOT a trained model)

Reuses `engine/dip_detector.py` thresholds + an inverted `momentum_filter` gate.
Emits `Prediction` objects that merge into the backtest's candidate list.

- **Regime gate:** emit ONLY when `market_regime == 1` (CHOPPY). BULL is
  momentum's domain; BEAR is falling-knife + already handled by the live block.
- **Entry (oversold bounce, uptrend intact, not freefall):**
  - oversold: `rsi_14 < 35` OR `bb_pct < 0.05`
  - longer-term uptrend intact: `ema_21_above_50 == 1`
  - not freefall: `return_5d > -15`
  - HIGH conviction only (≥2 oversold conditions) → stays selective + clears gate
- **Prediction fields:** `confidence = 0.93` (HIGH; clears the 0.92 gate),
  `predicted_return_pct = 5.0` (≥ min_predicted_return; MR revert target),
  `predicted_days = 7` (MR reverts fast), `predicted_stop =
  round_stop_price(close, close − 1.5·atr)`, target = close·1.05. Tagged
  `factors=["mean_reversion"]`.
- **Merge:** `merge_predictions(momentum, mr)` dedupes by (ticker, date) with
  **momentum winning ties** (drop the MR dupe). Sizing: same `risk_per_trade` as
  momentum for v1 (separate MR budget deferred).

## Method

Extend the backtest path: `make_backtest_fn(..., apply_mr_sleeve=True)` computes
MR predictions on the same test slice and merges them into the model's
predictions before `_simulate`. Validate via the sweep/walk-forward on the merged
book vs the momentum-only baseline; report the MR sleeve's standalone fold stats
+ MR↔momentum correlation. Live wiring (a `MeanReversionStrategy(Strategy)` merged
in `cron_runner.score_stocks`) only after the backtest clears — research-only
until the coordinated rollout.

## Result

**2026-06-07 — KILL (sub-threshold), but the STRONGEST signal of the program.**
Sweep run 27087535501 (`phase2_mr_v3`, after two no-op gate bugs fixed: MR must
bypass `min_adx`/`min_rsi`/`require_uptrend` [PR #60] AND `min_predicted_return`
[8.0 > MR's 5% target] + `min_confidence` [PR #61]). MR vs the sweep's own `off`:

| metric | off | mr | delta |
|--------|-----|-----|-------|
| mean Sharpe | 1.261 | 1.356 | **+0.094** |
| Sharpe std (consistency) | 1.886 | 1.684 | **−0.20 (better)** |
| total trades | 947 | 1299 | **+352 (+37%, ~130/yr — clears 120 target)** |
| mean WR | 49.9% | 50.6% | +0.8pp |
| worst-fold MaxDD | −29.6% | −32.3% | −2.7pp (slightly worse) |
| **balanced composite** | — | — | **+0.115 (best in program)** |

MR fires exactly where predicted — the chop/bad years — and lifts them:
**2025 Sharpe −1.44→−0.67 (+0.77), WR +9.1pp**; 2023 +0.44/+4.6pp; 2022 +0.26;
2019 +0.23; 2018 +0.11. The thesis is DIRECTIONALLY CONFIRMED.

**Why KILL:** fails `sharpe_wins_per_fold` at **6/10** (needs 7/10). MR trades
CONSISTENCY for upside — it repairs the bad years but DILUTES three good ones
(2017 −0.32, 2020 −0.22, 2024 −0.27) by adding MR trades there too. DSR 0.13 on
the mean-Sharpe level (weak test; the value here is variance reduction + trade
count, not the mean level). Per the pre-registered rule this is a KILL — the gate
will NOT be changed post-hoc (p-hacking).

**Diagnosis + redirect:** the failure is the diversification trade-off, and the
`sharpe_wins≥70%` floor is calibrated for momentum UPGRADES, not variance-reducing
SLEEVES. The signal is one fold short, entirely from good-year dilution. → **0015**
refines MR to fire only where momentum is THIN (so it fills the lean-year gap
without diluting good years), aiming to convert 6/10 into a legitimate 7/10+.
n_trials 19 → 20.

---

**2026-06-07 — FINAL VERDICT: KILL (reproducible). The earlier "strongest signal"
framing is WITHDRAWN — it was favorable model-fit noise.** 0015 showed the
per-fold-wins verdict swung 6/10 (v3) → 8/10 (thin run) on NON-reproducible model
randomness. The decisive REPRODUCIBLE sweep (run 27089473463, `phase2_repro`,
deterministic per-fold models) settles it:

| metric | off | mr | delta |
|--------|-----|-----|-------|
| **Sharpe wins** | — | **5/10** | needs 7 → FAIL |
| mean Sharpe | 1.181 | 1.206 | +0.025 (noise) |
| Sharpe std | 1.795 | 1.723 | −0.07 |
| trades | 947 | 1301 | +354 (+37%) |
| WR | 49.8% | 51.0% | +1.2pp |
| **DSR @21** | — | **0.051** | ≪0.95 |
| composite | — | +0.099 | (driven by trade-count axis only) |

Deterministic per-fold: MR helps 2019 (+0.97), 2023 (+0.83) but HURTS the target
years — **2025 −0.54→−1.11**, 2026 −0.82, 2018 −0.26. **It's "trade more, same
edge"**: +37% trades, mean Sharpe flat, 5/10 folds, DSR 0.05. KILL.

**Two lasting lessons:**
1. **Reproducible-only verdicts.** Non-reproducible walk-forward noise (±2 folds,
   ±0.15 Sharpe) swamps the signal — it nearly promoted a worthless sleeve (the
   lucky 8/10). EVERY promote/kill must use `REPRODUCIBLE_MODE`. The discipline
   caught a false positive.
2. **Both bad-year levers KILLed** (Phase 1 exposure, Phase 2 MR). The 2025-type
   losses are NOT fixable by portfolio construction (resizing or a 2nd price
   signal). Consistent with the repo's pattern — the model's selectivity is
   well-calibrated; more trades ≠ more edge. The only remaining lever is
   genuinely new ORTHOGONAL information (Phase 3).
