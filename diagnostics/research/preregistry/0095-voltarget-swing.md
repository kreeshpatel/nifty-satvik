# Pre-registration 0095 — Vol-target sizing ported to the weekly-swing book

**Status:** PRE-REGISTERED (written before any run; params fixed here and not retunable).
**Date:** 2026-07-09. **Owner-selected lever** (L1 of `research/RESEARCH_PLAN_swing.md`).
**n_trials cost:** +1 (single arm, fixed params) → cumulative 112 → 113, incremented before the run.

## Overlay
Port the PROMOTED base overlay **O-009 vol-target de-gross** (pre-reg 0068 arm V2) to the live
`weekly-swing-0094-rank` book, which currently sizes at flat 2% risk per fill. The single shared
formula `nq.engine.portfolio.vol_target_scalar` is reused verbatim:

```
scalar = clip( target_annual / realised_vol,  floor,  1.0 )      # de-gross only, never levers
realised_vol = std(last `window` book daily returns) × √252
```

Applied as: `sizing_equity = eq × scalar`, then `sh = sizing_equity × RISK / (entry − stop)`.
When `scalar < 1` (trailing book vol above target) every fill is smaller → lower gross → lower DD.

## Params — FIXED (reused from the promoted O-009 V2; NOT tuned here)
- `target_annual = 0.15`
- `window = 42`
- `floor = 0.40`

Reusing the promoted base params is deliberate: inventing new swing-specific values would be a
tuning knob (a hidden second trial). If this port needs different params to work, that is itself a
finding (the mechanism doesn't transfer at the promoted setting), not a reason to retune.

## Hypothesis
De-grossing the swing book's sizing equity in high-realised-vol windows shrinks positions exactly
when the book's own volatility (and thus tail-loss risk) is elevated, cutting the −42.4% max
drawdown at roughly neutral CAGR/Sharpe — the same signature O-009 showed on the momentum base
(CAGR-neutral, DD −45%→−39%).

## Predicted direction (before seeing results)
- **ΔMaxDD:** better (less negative) — the intended effect.
- **ΔSharpe:** ≈ 0 to slightly positive (vol-target is Sharpe-neutral by construction).
- **ΔCAGR:** ≈ 0 to slightly negative (de-grossing gives up some upside in high-vol recoveries).

## Failure modes (≥2, named before running)
1. **De-grossing through a V-bottom.** High vol often precedes the sharpest recoveries; sizing down
   into them caps the rebound so the CAGR give-up exceeds the DD benefit → net worse.
2. **The overlay barely binds.** The swing book is frequently cash-constrained (fills stop when
   cash runs out), so scaling sizing equity may change little → a near-no-op / UNDERPOWERED result.

## Pre-committed verdict bar (DD-overlay appropriate — fixed here)
Vol-target is Sharpe-neutral **by design**, so the generic overlay bar (ΔSharpe ≥ +0.10) would
wrongly reject a successful DD overlay. This trial is judged as a drawdown overlay:

- **SHADOW (route to the forward wall)** iff ALL hold on the corrected universe, continuous-slice:
  1. **ΔMaxDD ≥ +3.0 pp** (absolute drawdown reduction),
  2. **ΔSharpe ≥ −0.05** (full-sample; not materially worse),
  3. **≥2022 continuous-slice Sharpe** not worse by more than 0.05 (deciding regime),
  4. **ΔCAGR ≥ −2.0 pp** (bounded give-up).
- **PROMOTE to live sizing:** NOT available on in-sample evidence alone — the book is already
  UNDERPOWERED (DSR 0.894 < 0.95). Live promotion is forward-wall only.
- **KILL / UNDERPOWERED** otherwise. No retune, no re-run, no rounding a near-miss into a pass
  (the 0025 lesson: a 0.003 miss is a miss).

## Method
- cfg-gated: `backtest(..., vol_target=(0.15,42,0.40))` on; `vol_target=None` (default) off. The off
  path must be **byte-identical** to the 0094 run of record (the engine invariant; verified by
  running both and diffing the baseline metrics + trade count).
- Universe: corrected (pinned + backfill + aliases), 2017–2026 — the same as the 0094 backtest.
- Sub-periods via `_slices` (continuous-slice of one run, never fresh-capital).
- Report: full-sample + 3 slices, ΔMaxDD/ΔSharpe/ΔCAGR, block-bootstrap ΔSharpe CI, sample
  adequacy (n_independent ≈ 34 sixty-three-day windows).
- vibe-trading is NOT used here (no PIT-NSE); our harness is canonical.

## Registry cross-check (done before writing this)
O-009 vol-target is PROMOTED for the momentum base only; it has **never** been applied to the
weekly-swing book (flat 2% risk). This is a *new formulation* (same mechanism, new book), which
the KILL ledger does not cover. Not a relitigation.
