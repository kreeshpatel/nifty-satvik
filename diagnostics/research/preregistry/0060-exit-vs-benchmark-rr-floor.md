# 0060 — Exit-vs-benchmark ablation + max-entry R:R-floor validation

**Status:** PRE-REGISTERED (not yet run)
**Date:** 2026-06-22
**Arc:** entry/exit/R:R execution discipline (see `diagnostics/research/entry_exit_rr_research.md`)
**Harness:** cloud backtest (features.pkl absent locally → built in CI), honest leak-free universe, `REPRODUCIBLE_MODE`.

## Motivation
The deep-research methodology review validated our entry/stop/target/R:R design as best-practice on every axis, leaving exactly **one validation gap** and **one open knob**:

- **GAP (H1).** We have never proven the exit machinery (confidence-calibrated target + 2.0×ATR close-only stop + 14d hybrid time-stop + trailing) actually *beats* naive benchmark exits. The literature warns that strong in-sample exits often perform like a **random/benchmark exit out-of-sample** (portfoliooptimizer, buildalpha). If ours doesn't beat random / fixed-hold, the machinery isn't earning its complexity.
- **KNOB (H2).** The shipped max-entry buy-limit floor `MAX_ENTRY_RR_FLOOR = 1.2` is **thin after costs** at our ~53% WR (frictionless breakeven `(1−p)/p ≈ 0.89`; ~1.0–1.05 after Nifty round-trip). The near-cap fills are plausibly the chased/extended names with below-average WR.

## Hypotheses
- **H1 (exit value):** the production exit produces higher **net-of-cost per-trade expectancy AND portfolio Sharpe** than the best naive benchmark exit, on the **same entries**.
- **H2 (floor validity):** trades filling near the R:R=1.2 cap do **not** have materially lower WR / expectancy than the book average. (If they do → raise the floor.)

## Design — exit ablation (H1): identical entries, swap only the exit policy
All arms share IDENTICAL entries (production gate + sizing + indicative→T+1 fill). Only `decide_exit` changes. Honest costs (brokerage + STT + slippage + impact), close-only fills.

| Arm | Exit policy | Isolates |
|---|---|---|
| **A** (production) | calibrated target + 2.0×ATR close-only stop + 14d hybrid time-stop + trailing | — |
| **B** (random) | exit at a uniformly-random day in [10,18] (seeded) | is the *timing* skillful? (null) |
| **C** (stop-only) | 2.0×ATR close-only stop + hard 14d exit, **no target** | the TARGET's contribution |
| **D** (pure time) | exit at day 14, **no stop, no target** | stop + target together |
| **E** (opt.) | target + stop, **no trailing / no time-extend** | the trailing / time machinery |

**Primary metric:** per-trade net expectancy (%, after costs) with stationary-bootstrap CI. **Secondary:** portfolio Sharpe + CAGR + maxDD across the honest walk-forward / CPCV folds.

**Decision rule (PRE-COMMITTED):**
- **KEEP** the production exit IFF **A beats the best of {B,C,D}** on per-trade expectancy with **paired-CI-low > 0**, AND A's portfolio Sharpe ≥ the best benchmark on a **majority of folds**, **drop-2021 robust**.
- If a simpler benchmark (C or D) matches/beats A within noise → **simplify toward it**. Report which component (target / stop / trailing / time) carries the edge via the A−C−D−E decomposition.
- **DSR** at cumulative n_trials; verdict only on the `REPRODUCIBLE_MODE` run.

## Design — R:R-floor validity (H2)
On the production-exit arm, partition trades by fill-proximity to `max_entry`:
- **near-cap** = filled in the top decile of the `[entry, max_entry]` band (effective R:R at fill ∈ [1.2, ~1.3)).
- **rest** = the others.
Compare WR + net expectancy (bootstrap CI), near-cap vs rest.

**Decision rule (PRE-COMMITTED):**
- near-cap WR ≥ ~55% **AND** expectancy CI-low > 0 → **KEEP** `MAX_ENTRY_RR_FLOOR = 1.2`.
- near-cap expectancy CI-low ≤ 0 **OR** WR < ~55% → **RAISE** the floor to the smallest of {1.3, 1.4} at which the retained (≥floor) sub-population's expectancy CI-low > 0. Pre-committed mapping; **not** tuned to a Sharpe spike.
- The floor is a one-line config edit; advisory-only, **no trading-logic / golden-master impact**.

## Robustness / anti-overfit
- **Plateau-not-spike:** report A across stop-mult {1.75, 2.0, 2.25} and floor {1.1, 1.2, 1.3} as a **robustness check, not a selection** (the research's #1 named pitfall: stop/target grid-search spike — ATR-guard configs showed no robust post-cost edge).
- drop-2021 (the known bull-outlier), per-fold, honest costs. Survivorship caveat attached, but this is a **relative exit-vs-exit ablation** so common-mode survivorship cancels.
- **Audit-before-run:** `backtest-validator` on the exit-arm instrumentation (config merge, cost realism, live↔backtest parity) before trusting any metric.

## Not in scope
- A trailing overlay on the right tail (a separate retrain/skeptical-prior experiment per the research) — only *measured* here via the A−E decomposition, not added.
