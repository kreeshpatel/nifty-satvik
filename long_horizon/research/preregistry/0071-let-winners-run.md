# Pre-registration — 0071 let-winners-run (Stage-D exit machinery)

**Status:** PRE-REGISTERED 2026-06-28. **Type:** TRIAL (3 candidate exit-config arms). n_trials 76 →
**79** (arm-level; counted BEFORE the run). Anchor = baseline_v0 (26.1% gross / 23.1% after-tax;
`research/baseline_v0.json`). **Change class:** FROZEN-cfg exit machinery → a PROMOTE is the
**heavy path** (LIVE_OVERLAY_PROTOCOL §6a: walk-forward re-derive + golden-master regen + owner
sign-off). This experiment produces the EVIDENCE only — it does NOT touch `cfg` or promote anything.

## Origin
Phase-0's clean exit decomposition (ARM C/D, same engine + risk-sizing + 1× cost, only `exit_policy`
differs) found, **in-sample**: `stop_only` 38.5% / 1.381 Sharpe vs `production` (live) 26.9% / 1.046 —
the ATR stop adds (+0.26 Sharpe) but the **+22.5% target + 4.27% trailing SUBTRACT (−0.34 Sharpe /
−11.6pp CAGR)**, capping the fat right tail (STRATEGY_FULL §15 caveat 3). In-sample + cache-noisy →
this pre-reg subjects it to the full OOS promotion bar.

## Mechanism (one sentence)
The 63-day trend-momentum book is a fat-right-tail strategy whose returns concentrate in a few big
winners; the fixed +22.5% target and 4.27% trailing band **cut those winners short**, so removing them
(keep only the risk-control ATR stop + the 63-day hard cap — "let winners run") should lift
risk-adjusted return.

## Design (rank by the CONFIRMED entry `sma200_slope_63`; vary ONLY the exit; paired same-cache)
- **A `production`** (base = live): stop 3.67×ATR + target 22.52% + trailing 4.0/4.27 + min_hold 10.
- **B `stop_only`** (PRIMARY candidate): ATR stop + 63d cap, **no target, no trailing** (parameter-free
  — the C1b-clean "let winners run"; via the `exit_policy` passthrough → engine 0060 arm).
- **C no-trailing**: production with `trailing_activate_pct=9999` (disabled) → isolates: is *trailing*
  the culprit?
- **D no-target**: production with `target_pct=9999` (disabled) → isolates: is the *target* the culprit?

(9999 is an OFF sentinel, not a tuned threshold — no decimal-tuning / peak-vs-plateau overfit. No new
params are introduced; this is structural removal, not re-tuning.) Each arm: full `portfolio.simulate`,
same universe/cache → **paired** deltas (the cache-vintage ±4pp lesson).

## Predicted direction + the SKEPTICAL prior (stated before the run)
The **CAGR** gain is plausibly real (let winners run). The **Sharpe** gain is the one in doubt:
**v1-era 0047** (CPCV, the retired 14d model) found *trailing-off raised raw expectancy but LOWERED
risk-adjusted IR* — the exact illusion to guard against. So the in-sample +0.34 Sharpe must be
confirmed by the **block-bootstrap CI on ΔSharpe excluding 0** AND **≥2019 paired fold-pass ≥60%**
before it is believed. Honest prior: **SHADOW or KILL is as likely as PROMOTE**; a PROMOTE only if the
risk-adjusted gain survives OOS (the 63d structure may genuinely differ from v1's 14d).

## Failure modes (≥2)
1. **0047 illusion** — raw CAGR up, risk-adjusted Sharpe NOT reliably up: bootstrap CI-low(ΔSharpe) ≤ 0
   → KILL despite a higher point CAGR.
2. **Drawdown blow-out** — removing the give-back band deepens DD (Phase-0 `pure_time` was −47.5% vs
   production −43.8%); if Calmar falls, the "improvement" is just leverage on the tail → KILL.

## kill_criteria (a candidate exit config PROMOTES only if it clears ALL 7 gates; default = KILL/SHADOW)
- metric: paired ΔSharpe (vs production)               threshold: < +0.10   verdict: KILL
- metric: block-bootstrap CI-low(ΔSharpe), block=63     threshold: ≤ 0        verdict: KILL
- metric: ΔCalmar                                        threshold: < +0.05   verdict: KILL
- metric: 2022–2026 sub-period ΔCAGR                     threshold: ≤ 0        verdict: KILL
- metric: ≥2019 walk-forward fold-pass                   threshold: < 60%      verdict: KILL
- (turnover: `stop_only` REDUCES trades — the ≤+30% gate is not the binding constraint here)

## Pre-screen
- [x] Mechanism explainable in one sentence
- [x] No decimal-tuned threshold (removal via OFF sentinel, not a re-tuned value)
- [x] Param count 0 new (structural removal)
- [x] Not a §11 KILL (§11 has no exit-widening entry; ROADMAP Stage-D leaves long-horizon exit-widening
      OPEN; the v1 0047 KILL was the 14d model — cited as a skeptical prior, this is the 63d book, a
      genuinely different formulation)
- [x] No lookahead (exits decided on the close, shared `engine.exit_logic`)

## Output
`diagnostics/cpcv_long_horizon_exit_race.json` — per-arm metrics, paired Δ vs production, ≥2019
fold-pass, sub-period, block-bootstrap ΔSharpe CI, DSR@79, turnover — + the verdict per arm and which
of {target, trailing} is the primary culprit. → finding `research/findings/` + `overlay_registry.md`.
A PROMOTE is recorded as a **heavy-path candidate requiring owner sign-off**, never auto-applied.
