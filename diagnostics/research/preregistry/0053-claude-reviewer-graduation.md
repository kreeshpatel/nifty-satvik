# Pre-registration 0053 — claude_reviewer shadow graduation (A2)

**Date:** 2026-06-19
**Track:** A (AI decision bridge) — forward-validated, NOT backtestable
**Status:** SHADOW (reviewer now wired + accruing verdicts; NO routing change)
**Holdout type:** forward-wall only (no historical Claude-verdict corpus exists)
**n_trials:** not a backtest trial — does not increment `n_trials.json` (no trade decision
against the locked base until the forward gate fires).

## Background / discovery
`claude_reviewer.py` (commit 5a36722, "shadow mode") was built but **never wired into the cron** —
no verdicts were being produced and `diagnostics/evaluate_claude_shadow.py` did not exist, so the shadow
data could never graduate. This pre-reg covers (a) wiring the reviewer into cron Step 5.6 as a default-ON
shadow annotation, and (b) the forward evaluator that decides graduation.

## What ships now (shadow, no routing change)
- Cron **Step 5.6**: `review_signal` runs on every emitted signal (Haiku, daily-capped, fails open to
  TAKE). Verdict stamped on the signal + persisted to live_log (`claude_verdict/_confidence/_reason`).
  Gated by `claude_reviewer_shadow_enabled` (default **true**; set false on Render to silence the call).
- `diagnostics/evaluate_claude_shadow.py` — joins verdicts to realized outcomes; writes
  `results/claude_shadow_scorecard.json`.
- `claude_reviewer_gate_enabled: false` — the routing flag (future; graduation only).
- Golden-master byte-identical (the reviewer touches only the cron annotation path, not the engine).

## Asymmetric graduation ladder
1. **SKIP → hard-block FIRST.** A false block costs one missed trade on a ~27%-deployed book (near-zero
   marginal cost); this is the cheapest AI action to be right about.
2. **DOWNSIZE → 0.5× sizing LATER and SEPARATELY** (touches capital; higher bar; its own follow-on pre-reg).
3. **TAKE is never actioned.**

## Primary metric (ONE) + frozen rule — SKIP graduation
**Primary:** `mean(actual_return | TAKE) − mean(actual_return | SKIP)` over CLOSED signals (two-sample
percentile bootstrap, 10k, seed from `repro.seeds`).

**PROMOTE SKIP→hard-block iff ALL:**
- `n_closed_SKIP ≥ 20` AND `n_closed_TAKE ≥ 20` (power floor), AND
- the bootstrap 95% **CI-low of the (TAKE − SKIP) difference is > 0** (SKIP genuinely avoided losers), AND
- `SKIP_rate ≤ 25%` of closed signals (a SKIP firing more often than this is mis-specified, not a rare
  red-flag filter), AND
- **skeptic-agent clearance** (overfit-skeptic + flaw-hunter): no leakage in the reviewer's inputs, the
  verdicts are not just echoing the model's own confidence, the flagged events are real.

**HOLD** if under the power floor or the CI straddles 0 (keep accruing). **KILL** if after a full forward
year `n_SKIP` never reaches 20 or the CI never clears — honest outcome "the second opinion adds no
actionable safety edge," recorded as such.

## Kill risks (pre-stated)
- **SKIP rate near-zero** on already-0.92-gated signals → never reaches the power floor (most likely).
- **SKIP precision at chance** → the reviewer just echoes model confidence; CI straddles 0.
- **Sample starvation** → months, not weeks.
- **Cost** → mitigated by the daily call cap + the default-OFF kill-switch flag.

## Verification
- Unit tests: live_log verdict round-trip (persist + read back); evaluator gate logic on synthetic
  closed rows (empty → HOLD; clear SKIP-underperformance + low rate → PROMOTE_PENDING_SKEPTIC; high rate
  → HOLD; CI-straddle → HOLD).
- Golden-master byte-identical; cron compiles + imports.
