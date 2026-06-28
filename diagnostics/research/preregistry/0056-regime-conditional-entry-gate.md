# Pre-registration 0056 — Regime-conditional entry gate (B2)

**Date:** 2026-06-19
**Track:** B (model-internal) — CPCV-backtestable
**Status:** PRE-REGISTERED (bars frozen below BEFORE any run); awaiting owner sign-off + cloud dispatch
**Holdout type:** paired CPCV on the locked honest base (de-leaked 744 universe, REPRODUCIBLE_MODE=1)
**n_trials:** increments by 1 (ONE arm) — bump `n_trials.json` BEFORE the run.

## Hypothesis (economic, pre-stated — NOT fit to localization data)
The 0.92 confidence bar is uniform across regimes; only exits are regime-aware. In a **CHOPPY**
(range-bound) regime, momentum entries are most prone to whipsaw, so the model's lower-conviction
signals there should be disproportionately negative-EV. Demanding **near-A-grade conviction in CHOPPY
only** should cut those whipsaw trades and lift risk-adjusted return — IF they are genuinely negative-EV.

## ⚠️ Honest skeptical prior (stated up front)
This lever **fights the program's just-validated finding** (RS-01 0048 KILL): the binding constraint is
**signal scarcity + under-deployment** (~27% deployed), not trade quality. Raising ANY entry bar REDUCES
trades, worsening deployment. B2 helps ONLY if the CHOPPY sub-0.94 trades are negative-EV by *more* than
the lost deployment costs. Combined with the program's ±0.3 Sharpe noise floor (which swallowed 0013/0014),
**KILL is the expected, acceptable outcome.** We run it because (a) it is cheap given the kernel is already
wired, (b) it is the one regime-gate variant consistent with the kill record (BEAR already hard-blocked;
loosening BULL would re-admit the KILLed 0.88–0.92 band), and (c) a clean null is itself informative.

## The rule (FROZEN — implemented, golden-master byte-identical when off)
Per-regime SIGNAL confidence bar via `GateConfig.regime_entry_min_conf` (label→float) in the shared
`_admission_kernel.py` (live↔backtest parity). Frozen arm:

| Regime | conf bar | rationale |
|---|---|---|
| BEAR | unchanged (hard-block live) | 0013 + prior reports: BEAR already handled; do NOT touch (C2.3) |
| **CHOPPY** | **0.92 → 0.94** | whipsaw-prone; demand near-A-grade (A=0.95, B=0.90); +0.02 shrunk toward global |
| BULL | unchanged (0.92 global) | momentum works in trends; loosening re-admits the KILLed 0.88–0.92 band |

**ONE free parameter** (CHOPPY = 0.94). No grid search. `regime_entry_min_conf=None` (default) ⇒
byte-identical to today. The return bar (8.0) is NOT varied (keeps the arm count at 1).

## Primary metric (ONE) + frozen decision rule
**Primary:** paired CPCV **portfolio Sharpe** uplift of the CHOPPY-0.94 arm vs the locked base (same
models, same folds; the run_cpcv pattern's LdP-path portfolio metric, identical to 0051).

**PROMOTE iff ALL:**
- paired Sharpe uplift **CI-low > 0** (bootstrap across CPCV paths), AND
- uplift **> the 0.041 trade-IR / ~0.3 portfolio-Sharpe noise floor** (must clear noise, not just be positive), AND
- **DSR > 0.95** at cumulative n_trials, AND
- **per-fold/per-group robustness floor** (no single CPCV group blows up — the 0051 rule), AND
- live trade count not cut so far it starves the book (report CHOPPY trades dropped; a >~15% total-book
  cut is disqualifying — it would trade the deployment problem for a marginal quality gain), AND
- **skeptic-agent clearance** (overfit-skeptic + backtest-validator).

**Else → KILL** (record the null). Live untouched until PROMOTE → shadow → reversible flip.

## What ships now (pre-run)
- `src/strategies/_admission_kernel.py` — `regime_entry_min_conf` override + `effective_min_conf` (default
  off, golden-master byte-identical) + `tests/test_regime_entry_gate.py` (5).
- CPCV A/B runner (`diagnostics/run_cpcv_regime_gate.py`) + workflow — **built only after sign-off** to
  avoid wasting work if the skeptical prior redirects the lever.

## Kill risks (pre-stated)
- Within the ±0.3 Sharpe noise floor (most likely).
- CHOPPY loss may be a signal problem no gate fixes (the plan's own caveat).
- Cutting trades worsens the binding under-deployment constraint (the RS-01 tension).
