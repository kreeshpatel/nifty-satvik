# Pre-registration 0104 — Tighten the live ext_cap 0.20 → 0.15 on the weekly-swing book

**Status:** PRE-REGISTERED (written before the run; the 0.15 value is fixed here, not retunable).
**Date:** 2026-07-26. Motivated by a chart-forensic (owner): the FACT 2024-12-04 loser filled at ~+20%
above the 44w SMA — the worst extension bucket — squeaking past the live `ext_cap=0.20` by ₹1. The
matched-control gradient on the 0094 ledger confirms extension grades outcomes: **<10% ext = 88% win /
+1.01R (16 trades); 10-20% = 59% / +0.42R (121); >20% = 51% / +0.34R (86).** FACT lived in the worst
bucket. Question: does moving the cap to 0.15 (cutting the +15-20% fills where FACT lived) lift the
portfolio, or just starve a cash-constrained book?

## Overlay
On the **live book config** — A-grade-only (`grade_a_entries`), `max_risk_pct=0.10`,
`max_notional_pct=0.20`, config-P scaled exit — change **only** `ext_cap`:
- **baseline:** `ext_cap = 0.20` (the current live discipline).
- **candidate:** `ext_cap = 0.15`.
Everything else identical → the delta is purely the ext_cap change. Re-run (not ledger-filter) so the
freed cash redeploys honestly (the 0095 lesson: filtering understates a cash-constrained book's response).

## Params — FIXED
- `ext_cap = 0.15` (single arm). `ext_cap_touch_only = False` (cap all fills, as live).
- No other change. If 0.15 needs a different value to work, that is itself the finding — no retune.

## Hypothesis
Cutting fills >15% above the SMA removes the lowest-quality (0.34-0.42R) extended entries, raising
per-trade quality and possibly cutting drawdown — but because low-ext fills are rare (16/223 ≈ 7%) and
can't be manufactured, the freed cash likely redeploys into other extended names, so total return may fall
(the engine is the extended fills — 207/223 are >10% ext). Net effect uncertain — that's why we test.

## Predicted direction (before results)
- **Trades:** fewer. **Per-trade expR:** higher. **ΔCAGR:** negative-to-flat (engine give-up).
- **ΔMaxDD:** flat-to-better. **ΔSharpe:** ambiguous (quality up, count down) — likely ≈ 0 / slightly ±.

## Failure modes (≥2)
1. **Starves the book** — removes trades without a matching quality lift once cash redeploys into other
   extended names; CAGR falls, Sharpe flat/worse (the O-022 lesson: entry filters cut winners too).
2. **Overfits to FACT** — improves by trimming a handful of >15% losers the sample happens to contain,
   with a non-monotone / spiky response (the §C1b overfit tell) that won't generalize.

## Pre-committed verdict bar (fixed here)
**ADOPT-candidate → forward-wall watch** iff ALL, continuous-slice on the corrected universe:
1. **ΔSharpe ≥ +0.05** (full sample),
2. **ΔMaxDD ≥ 0 pp** (not worse),
3. **2022-26 slice Sharpe** not worse by >0.05,
4. **ΔCAGR ≥ −3.0 pp** (bounded engine give-up).
**PROMOTE to live cfg:** forward-wall only (book UNDERPOWERED). **KILL / UNDERPOWERED** otherwise — no
retune of 0.15, no rounding a near-miss (the 0025 rule). Report block-bootstrap ΔSharpe CI + DSR @132.

## Method
- `run_bhanushali_weekly_rank.backtest` on the corrected universe (2017-2026); baseline vs candidate
  identical except ext_cap; A-grade set from `grade_a_entries(P)`. Continuous-slice `_slices`.
- Reproducible from the committed pipeline; engine untouched (only a cfg param varies).

## Registry cross-check
- ext_cap is an existing live lever (LIVE_DISCIPLINE 0.20; measured DD −36→−31 return-neutral). This is a
  **new value** of a live param on the live config, motivated by a per-trade forensic + matched controls —
  a legitimate single-arm trial, not a relitigation. Related: O-022 (entry arc, near-SMA is the worst
  quintile / extension is the engine) — this tests the *cap threshold*, not a near-SMA entry preference.
