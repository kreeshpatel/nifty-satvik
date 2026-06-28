# 0026 — sweep_override parity: measure the live [0.88, 0.92) band's true EV (AUD-017)

- **ID:** 0026. Prompted by AUD-017 (the backtest harness omits the live sweep_override → live
  trades ~12% more signals than every verdict measured, from a band previously measured as
  negative-EV at −0.46%/trade on the survivor cache) + the post-0025 program decision that
  free-EV cleanups run regardless of the meta-labeling verdict.
- **Registered:** 2026-06-10, **BEFORE** the parity arm is run on the corrected universe. The
  decision rule below is committed first; the band's corrected-universe EV has never been measured.
- **Type:** live-parity correctness measurement (NOT an alpha trial) — but conservatively counted
  as 1 arm in `n_trials.json`. Candidate-only; any live config flip is owner-gated.

## Question

Live promotes watchlist signals with conf ∈ [0.88, 0.92) to real trades when `sweep_20d == 1`
(`sweep_override_enabled: true` in `models/v1/config.json`); the backtest gate never simulated
this. **On the corrected 744-universe cache, is the sweep band's expected value positive enough
to justify keeping the live override — or is live silently bleeding EV the backtests never saw?**

## Method

Walk-forward, expanding window, embargo-45, REPRODUCIBLE_MODE=1, `--apply-bear-block`,
single-model `models/v1` (the frozen live recipe), ONE shared expanded-universe cloud cache,
honest window = ≥2019 folds. Two arms:

- **A — base (override OFF):** the locked-yardstick recipe, byte-identical to every prior verdict.
- **B — sweep parity (override ON):** identical run with `--apply-sweep-override` — the engine
  replicates the live promote rule (`backtest_engine._simulate`, `apply_sweep_override=True`;
  regression-pinned in `tests/test_backtest_sweep_override.py`). Swept trades are tagged and
  their per-trade returns exported per fold (`sweep_returns_pct` in the fold JSON).

Training is byte-identical across arms (the sidecar column threads through the TEST-side filter
only), so every B−A difference is attributable to the admitted band trades.

## Pre-registered decision rule (committed before data)

Measured on ≥2019 folds:

1. **Band EV (primary):** pooled per-trade net return of SWEPT trades, bootstrap 95% CI.
2. **Portfolio effect:** paired per-fold (B − A) deltas on Sharpe / CAGR / WR / MaxDD.

**Verdict logic — asymmetric by design** (a false "keep" bleeds real users ~12% extra trades in
a suspect band; a false "disable" forgoes a marginal edge):

- **KEEP the live override** iff BOTH: (a) pooled swept-trade mean return CI **lower bound > 0**,
  AND (b) mean per-fold Sharpe delta (B−A) ≥ 0. Then also adopt `--apply-sweep-override` in all
  future verdict walk-forwards (backtest↔live parity restored in the ON direction) and close
  AUD-017 as "modeled".
- **DISABLE the live override** in every other case — including CI straddling zero ("can't prove
  it helps" = don't take the extra trades): recommend the owner flip
  `sweep_override_enabled: false` in `models/v1/config.json` (config-only, no retrain, takes
  effect next cron). AUD-017 closes as "removed". The ~12% trade-count reduction also cuts
  brokerage/STT/slippage mechanically.
- **No third option.** No threshold tuning, no band-narrowing re-runs. One shot.

DSR is NOT a criterion here (this is a parity measurement with a disable-by-default rule, not an
alpha promotion); the arm still increments the family registry (conservative).

## Skeptical prior (stated before running)

The band was measured at −0.46%/trade, 58% WR on the survivor cache (2026-04-22 tier validation,
which is WHY min_confidence moved 0.88→0.92) — but the sweep_20d conditioning was validated
separately (+9.0% cumulative claim in `diagnostics/sweep_features_v2_spec.md`, pre-audit
methodology). Corrected-universe prior: weakly negative-to-zero band EV → expected verdict is
DISABLE. A robustly positive band EV would be a (welcome) surprise.

## Results (2026-06-10 — cloud run 27285113768, REPRODUCIBLE_MODE=1, embargo-45, bear-block)

One shared expanded-universe cache; ≥2019 folds; scored by `diagnostics/score_0026_gate.py`
→ `diagnostics/research/0026_gate_score.json`.

| arm | meanSh | medSh | negFolds | meanCAGR% | meanWR% | trades | meanMaxDD% |
|---|---|---|---|---|---|---|---|
| A base (override OFF) | +0.777 | +0.804 | 3 | +17.37 | 48.2 | 504 | −17.60 |
| B sweep (override ON) | +1.060 | +0.943 | 2 | +17.68 | 51.9 | 579 | −18.27 |

- Per-fold Sharpe delta B−A: 2019 −0.58, 2020 −0.12, 2021 −0.17, 2022 −0.20, 2023 +0.62,
  2024 +0.84, 2025 +1.45, 2026 +0.42 → mean **+0.28** (positive in every fold since 2023).
- **Swept-trade EV (primary): +0.80%/trade, WR 56.6%, n=106 — but bootstrap CI95
  [−1.23, +2.77] straddles zero.** Swept volume = 21.0% of base admits (live estimate was ~12%;
  the corrected universe + bear-block mix admits proportionally more band trades).
- (Cross-run note: arm A's absolute level differs from 0025's arm A — separate cloud cache
  vintages, the known AUD-021 sensitivity. Within-run A/B is the valid comparison.)

## Verdict — DISABLE the live override (2026-06-10, per the pre-registered rule)

Rule (a) — swept-trade EV CI-low > 0 — **FAILS** (CI [−1.23, +2.77]). Rule (b) — Sharpe delta
≥ 0 — passes (+0.28). KEEP required BOTH → **DISABLE**.

**Honest tension, recorded:** this is the closest call of the program. The band measured mildly
HELPFUL at the portfolio level in this single corrected-universe run (Sharpe +0.28, WR +3.7pp,
neg-folds 3→2, CAGR ~flat, MaxDD −0.7pp worse) — the opposite sign of the 2026-04-22 survivor-cache
measurement (−0.46%/trade) that motivated the 0.92 gate. But 106 swept trades cannot statistically
separate +0.8%/trade from zero, and the rule was committed precisely for this situation: "can't
prove it helps = don't take the extra trades" for ~10 paying users. No re-runs, no band-tuning.

**Recommended action (owner-gated, config-only):** flip `sweep_override_enabled: false` in
`models/v1/config.json` on the live deployment. Effects: live↔backtest gate parity restored in
the OFF direction (AUD-017 → closed as "measured + removed"), ~17–21% fewer live trades with
mechanical brokerage/STT/slippage savings, and the [0.88, 0.92) band returns to watchlist-only.
**Revisit trigger (pre-committed, not a re-roll):** if the forward wall accumulates ≥100 live
watchlist-band observations with positive realized EV, a fresh pre-registration (0026b) may
re-test the band with the power this run lacked.
