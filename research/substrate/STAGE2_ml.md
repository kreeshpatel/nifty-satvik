# Stage 2 (free half) — ML: does any entry-time feature predict outcome OOS? (measurement, no trial)

**Run 2026-07-16.** LightGBM on the 4,391-trade substrate, ONLY entry-time PIT-safe features (strict
leakage guard — no MAE/MFE/held/reason/R). Trained 2019-22, judged on the 2023-26 holdout. Reproduce:
`python scripts/diag_substrate_ml.py`.

## Result — a WEAK but real OOS signal

- **Holdout AUC 0.536** (continuous) / 0.531 (+setup identity). Train AUC 0.82 = overfit, ignored.
  → entry features only *weakly* separate winners from losers (confirms the forensic's "early heat of
  a survivor and a stop-out look similar"), but the signal is **not zero**.
- **Predicted-good quintile realizes a genuine OOS edge**: Q5 win 53.4% / meanR +0.50 / medR +0.23 vs
  Q1-Q2 win 43-47% / medR −0.6 to −0.95. ~6pp win-rate and ~0.8R median spread top-vs-bottom.

## The OOS-honest discriminators (permutation importance + monotonic win% gradients)

| feature | holdout win% by quintile (lo→hi) | reads as |
|---|---|---|
| dist_52wh_pct | 39 → 46 → 50 → 54 → 55 | **buy near the 52-week high** (O'Neil) |
| vol_ratio | 43 → 45 → 50 → 54 → 52 | **breakout volume confirmation** (Bhanushali) |
| atr_pct | 54 → 51 → 49 → 46 → 43 | **lower volatility wins** (low-vol edge, cf O-016) |
| ext_vs_sma | 45 → 48 → 48 → 48 → 55 | extension (setup-confounded) |
| rank_crs | (top-8 importance) | relative-strength rank |
| roe / bp / low_debt | flat | fundamentals do NOT discriminate entry quality |

## Implication

A **Phase-5 conviction score** (Stage 5 / L3) from {near-52wh, volume-ratio, low-ATR, CRS} is
**feasible but modest** — a real ~6pp/0.8R gradient, the weak-but-real class the forward wall exists
to certify, NOT an in-sample slam dunk. Do not oversell AUC 0.536. Fundamentals are not entry-quality
signal here. These three features are the leading candidates to carry into the pre-registered L3 test.

## Caveat

Weak AUC is partly regime (2023-26 holdout differs from 2019-22 train). The per-quintile realized
meanR is the practically meaningful readout, not AUC alone. Still per-trade — Stage 4 re-tests under
the cap.

---

# Stage 2 (paid half) — blind AI-vision forensic (299 charts, tiered Haiku→Sonnet→Opus)

**Run 2026-07-16** as a Workflow (342 agents, ~11.7M subagent tokens — more than estimated; the cost
is per-agent harness overhead, not image tokens). Full taxonomy: `research/substrate/failure_taxonomy.md`.

## Headline — entry quality is NOT visible at entry (third independent confirmation)

- **Blind mean setup-grade: winners 2.72 vs losers 2.75** (losers grade *marginally higher*; A-grade
  6.7% both). A blind analyst **cannot separate survivor from stop-out from the entry chart.**
- This is now confirmed **three independent ways**: the prior 8-agent forensic, the ML holdout
  AUC 0.536, and this 300-chart blind vision grade-gap ≈ 0. The "survivor and stop-out look the same
  at entry" wall is real and robust.
- Counterintuitive directional tag: winners skew *moderately extended* (+8.2), losers skew *at/near
  the SMA* (−5.7) — echoes the 5-10% deep-near-SMA **trap band**, cuts against a naive near-SMA thesis.
- Failure taxonomy (graded-C/D tail only): climax_reversal 38%, overhead_supply 28%, no_base_whipsaw
  25%, bought_extended 10% — ~90% screenable, **but only in the bad tail; the median loser = median winner.**

## 3 PIT-safe candidates → forward wall (Stage 5)
`overhead_supply_8pct`, `falling_knife_vel`, `dd_from_recent_high`. Each trims losers AND winners;
same family as already-killed ext-cap/near-SMA (O-019/0079) → forward-wall only, never in-sample.

## Plan pivot forced by Stage 2 (the loop adapts to the finding)

The entry-**filtering** avenue is confirmed exhausted — you cannot fix bad trades by screening the
touch entry, because the median loser is indistinguishable from a winner at entry. The real leverage
is therefore NOT better entry filters. It is:
1. **The wide net itself** — the zoo patterns (cup/double-bottom/ascending-base, Stage 1) ARE
   genuinely higher-quality *entries* per-trade (medR +0.5 to +0.8 vs touch −0.94). The entry edge is
   choosing a better *setup family*, not filtering the touch.
2. **Exit (Stage 3) + sizing (Stage 4)** — since entries can't be pre-sorted at the median, capture
   more from the winner tail (exit) and size to survive the unavoidable losers (sizing/sleeves).
3. The 3 tail-failure features → forward wall (Stage 5), held to the same bar.

Stage 3 (exit co-optimization per setup family) and Stage 4 (sizing sleeves for the zoo patterns) are
now the highest-leverage remaining stages.
