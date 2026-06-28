# 0034 — partial-exit parity: does live's hidden 40% partial help or hurt? (AUD-029 gate)

- **ID:** 0034. Registered 2026-06-12, BEFORE the 0.4 arm runs.
- **Type:** correctness-fix gate (adopt-if-not-worse, the two-bar principle's second bar —
  with the not-worse arm ACTUALLY RUN, the 0011 lesson). Counted **+1 trial conservatively**
  (n_trials 44 → 45), 0026 precedent.

## Question

Live `signal_tracker` silently takes a **40% partial exit** at +6.5% (its internal default)
because the cron wire dict never stamped the config exit params — while `models/v1/config.json`
says `partial_exit_qty: 0.0` and every validated backtest ran 0.0. AUD-029's fix (stamp config
onto signals — currently HELD on `main` via the consolidation holdback commit 229442f) would
change live behavior from 0.4 → 0.0. **The divergence, not the value, is the defect**; this
experiment decides WHICH value config should mandate.

## Method (within-run A/B, de-leaked pinned-744 cache)

- **Arm 0.0 (config intent):** the committed de-leaked 14d walk-forward `0032_dl14_armA`
  (REPRODUCIBLE_MODE, chunked, embargo-45, bear-block) — partials OFF, already run.
- **Arm 0.4 (current live behavior):** identical run with `partial_exit_qty=0.4` +
  `partial_exit_pct=6.5` (signal_tracker's live defaults) via the new generic
  `--config-override` harness arg. Same cache (`NIFTYQUANT_FEATURES_PATH=features_deleaked.pkl`),
  same code, same folds → only the partial policy differs. AUD-033's partial-P&L accounting fix
  is in, so partials are honestly booked.

## Frozen decision rule

Let Δ = pooled ≥2019 paired per-fold Sharpe (0.0 − 0.4), bootstrap CI (seed 42, n=2000):

- **CI-low(Δ) > −0.15** → 0.0 is not-worse → **ADOPT the AUD-029 stamping** (PR-2 reverts the
  holdback; live stops taking the hidden partial; config is authoritative).
- **Else** → 0.4 is materially better → **set `partial_exit_qty: 0.4` explicitly in
  models/v1/config.json** AND still ship the stamping (config authoritative either way; live
  behavior then unchanged).
- Secondary (reported, not gating): CAGR delta, WR delta, per-fold table, fold-level worst Δ.
- Either branch CLOSES AUD-029. No third option; thresholds frozen now.

## Result

**Status: COMPLETE (2026-06-12). VERDICT: ADOPT 0.0 — ship the AUD-029 stamping.**

| pooled ≥2019 | qty=0.0 (config) | qty=0.4 (live behavior) |
|---|---|---|
| mean Sharpe | **+0.864** | +0.739 |
| mean CAGR | **+22.1%** | +19.4% |

Paired per-fold ΔSharpe(0.0−0.4) = **+0.125, CI95 [−0.066, +0.350]** → CI-low −0.066 clears
the frozen −0.15 bar (and the point estimate favors 0.0). Per-fold: 0.0 wins 6/10 (2018 +0.13,
2019 +0.20, 2021 +0.10, 2022 +0.28, 2023 +0.05, 2026 +0.81); 0.4 wins 2017/2020/2024/2025
(−0.06 to −0.27). Mechanism: the hidden 40% partial at +6.5% clips winners before the
target/trailing harvest — costing ~2.7pp CAGR pooled. Override applied verbatim
(`[OVERRIDE] simulation cfg partial_exit_qty = 0.4` in fold logs); models byte-identical across
arms (sim-config-only override). Evidence: `0034_pq04.{md,json}`, `0034_gate_score.json`.

**Action:** the AUD-029 holdback is reverted on `fix/0034-partial-exit` (PR-2) — the cron now
stamps config exit params; live exits stop the unintended partial on signals generated after
the merge. AUD-029 → FIXED on merge. Forward-wall watch: live exit behavior on the first
post-merge signals.
