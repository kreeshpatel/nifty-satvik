# ADR-0006 — LOCK the model: adopt baseline_v1, accept the ~−39% DD via the vol-target, ship to paper

**Status:** Accepted
**Date:** 2026-07-01
**Deciders:** Owner (D1 = accept ~−39% DD via vol-target + ship to paper)
**Related:** ADR-0003 (universe), ADR-0004 (hold-live-until-conviction), ADR-0005 (baseline_v0),
`research/baseline_v1.json`, `docs/LOCK_PLAN.md`, `research/OVERNIGHT_LOG.md`, findings 0002-0009,
`config.json → live_overlays` (vol-target O-009 / pre-reg 0068).

---

## Context

Stages A→C are complete. The base is **validated and certified** but at its **ceiling**, and every
enhancement lever has been tested through the hardened harness and **failed the bar**:

- **Base validated:** `sma200_slope_63` selection beats a random top-15 from the same universe/exits
  (finding 0008 — doubles random's CAGR); PSR(>0) = **0.974**, MinTRL 6.2y < our ~9.5y (finding 0005) —
  the 0.667 Sharpe is statistically real. But it is a **moderate, bull-concentrated** edge: 3 years
  (2020/2021/2023) drive the entire return; 5/9 tradeable years positive (finding 0009).
- **Every lever failed:** conviction sizing KILL (0004), conviction signal INCONCLUSIVE under the
  corrected null (0002), regime gate KILL (A5), let-winners-run/target-loosening regime-dependent (0006),
  ROE/value KILL (leak + regime, 0007). The randomized-entry null explains why (0008): a moderate edge
  + a large already-captured structural return (universe + exit discipline) leaves no headroom.
- **The binding constraint is the −46% drawdown, and it is STRUCTURAL** — pre-reg 0070 proved
  sizing/exposure overlays plateau at ~−38% (the COVID-2020 systematic floor); the only lever to a
  dependable −30% is the deferred Stage-G tail hedge. It is NOT an alpha problem.
- **Rigor hardened:** effective-N + block-permutation null + PSR/MinTRL + the mechanized 7-gate bar
  (findings 0005; LOCK_PLAN Step 1). The `docs/LOCK_PLAN.md` STOP rule ("when the remaining leads all
  return KILL/INCONCLUSIVE/SHADOW → the base IS the model") is satisfied.

Continuing to mine alpha is −EV (every lever dead) and inflates the DSR bar. The model is complete.

## Decision

**LOCK the long-horizon model.** Specifically:

1. **The model = `baseline_v1` (pinned `dataset-pin-20260701`, sha `f8625a8f…`) + the carried frozen
   cfg.** `baseline_v1.json` is the official anchor, **superseding baseline_v0** (per ADR-0005 §6).
   - Gross: **15.46% CAGR / 0.667 Sharpe / −46.26% maxDD / Calmar 0.33**.
   - After-tax (STCG 20%): **~12.76%**; **all-in net (after tax + ~3.5 bps/leg micro-costs) ≈ 12.2% CAGR**.
2. **D1 (DD risk profile) — ACCEPT ~−39% operational DD via the vol-target.** The O-009 vol-target
   (`config.json → live_overlays`: vol_target_annual 0.15 / window 42 / floor 0.40; pre-reg 0068 V2) is
   applied at the **paper/live layer only** (NOT the frozen cfg → research baselines + golden untouched).
   It cuts the operational DD ~−46 → ~−39 CAGR-neutrally. **Do NOT block the lock on Stage-G.**
3. **D2 (universe / cfg) — KEEP the carried frozen cfg** (do NOT re-derive now). Justification: the base
   is validated; the target sweep (0006) showed the carried `target_pct` 22.52 holds up in the
   live-relevant 2022-26 regime (a walk-forward re-derivation is optional polish, deferrable, not a
   blocker). The cfg is unchanged ⇒ the golden master stays byte-identical (no regen, no baseline_v2 —
   baseline_v1 IS the locked research baseline).
4. **Alpha research is CLOSED.** No promotable overlay exists. Default is LOCKED; re-opening any
   component requires a new owner-signed ADR (not merely stopping).

## Consequences

### Honest, client-facing framing (load-bearing)
The number quoted to the ~10 fee-paying clients is **~12% net CAGR** (after tax + all costs), **NOT 15%**,
and it is **lumpy** — delivered in bursts (2020/21/23) with multi-year flat/negative stretches
(2018-19, 2022, 2024-25) and a **−46% research drawdown / ~−39% operational** (with the vol-target).
This is inherent momentum convexity, not a defect. Set expectations to **~12% net / lumpy / ~−39% DD**.
All figures are **research backtest results, never traded live, decision-support only** (compliance framing unchanged).

### What happens next — Stage E (paper), then F (live)
"Ship to paper" is the Stage-E build (currently NOT built in the clean rebuild):
1. Implement the vol-target (shared `portfolio.vol_target_scalar`, trailing 42d realized book vol) in
   the clean engine's **live/paper sizing path** — the one overlay that ships (golden byte-identical off).
2. Build the paper book (paper broker + equity/NAV tracking + the T+1 fill model) + the cron scanner
   (incremental yfinance → `signals_today.json`).
3. Accumulate **≥30 paper trades over ~2 months**; flip kill-criteria observe→enforce; then Stage F (live).

### Stage-G is the SCALING gate, not a launch blocker
The defined-risk tail hedge (→ dependable −30% DD) is built **in parallel** and gates *scaling up*
real capital — the base ships to paper/live first with the vol-target + kill-switch managing the DD.

### Flagged (non-blocking)
- **D2 re-derivation** deferrable; revisit only if a forward-wall shift or a business need warrants the heavy path.
- **Fundamentals announcement-lag** (finding 0007): the store keys on quarter-end with no lag → a latent
  ~quarter lookahead. Immaterial to the base (solvency screen only) but MUST be fixed before any
  fundamental-driven feature.
- The base is **in-sample / not live-validated** — the forward wall (post-2026-05-30, HOLDOUT.md) is the
  real test; every current number is PROVISIONAL until the paper/forward record confirms it.

## Alternatives considered
- **Block lock on Stage-G (dependable −30% first).** Rejected as the *launch* posture: it delays the
  first paper trade by months for a DD improvement (−39→−30) that is a *scaling* concern, not a
  *viability* one — the vol-target + kill-switch make −39% operationally manageable. Stage-G proceeds in
  parallel as the scaling gate.
- **Re-derive the cfg on the corrected+financials universe before locking (D2 heavy path).** Rejected as
  a blocker: the base is validated and the carried cfg holds up in 2022-26; re-derivation is optional
  polish that would delay shipping. Deferred, revisitable.
- **Keep mining alpha (one more overlay).** Rejected: every lever has failed; more is −EV and inflates
  the DSR bar against any future winner. The STOP rule is satisfied.

## Cross-references
| Reference | What it specifies |
|---|---|
| `research/baseline_v1.json` | The locked anchor (pinned, certified) |
| `research/findings/0002-0009` | The full lever-by-lever kill record + base validation |
| `docs/LOCK_PLAN.md` | The component map + LOCK gate + STOP rule this ADR closes |
| `research/OVERNIGHT_LOG.md` | The autonomous research session that converged to LOCK |
| `config.json → live_overlays` | The vol-target (O-009), applied at the paper/live layer for D1 |
| ADR-0005 | baseline_v0 (superseded by baseline_v1 here, per its §6) |
| ADR-0004 | Hold-live-until-conviction — conviction tested + does not earn a place; base ships on its own |
