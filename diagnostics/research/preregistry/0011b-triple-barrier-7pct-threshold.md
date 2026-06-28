# 0011b — Triple-barrier win threshold raised to +7%

- **ID:** 0011b
- **Registered:** 2026-06-04
- **Holdout:** unseen-universe → forward-wall. Retrain-gated.
- **n_trials (cumulative):** ~57.
- **Status:** COMPLETE — **KILL (gate-starvation)** (2026-06-04). +7% bar cut the
  candidate to n=12 trades through the 0.92 gate → statistically meaningless.
  Confirms +4% (0011) is the right threshold; don't raise it. See Result.

## Motivation

0011 isolates *path-awareness* at the live +4% bar. This sibling isolates the
*win threshold*. The current win label fires at +4%, but the entry gate requires
predicted return **≥8%** — so we reward a +4% pop even though we'd never enter a
trade expecting only 4%. Raising the win bar to **+7%** aligns "what counts as a
win" with "what we required to enter" (just under the 8% gate). The threshold is
chosen *because it ties to the gate*, NOT by sweeping for the best backtest —
that distinction is what keeps it from being an overfit knob.

## Hypothesis

Training the confidence head on `tb_hit_14d` = "+7% touched **before** the 2×ATR
stop within 14d" lifts after-cost per-trade expectancy on the unseen universe vs
the live baseline (`hit_4pct_14d`, path-blind +4%), because a higher, gate-aligned
win bar makes the classifier select for setups that deliver the move we actually
trade for.

## Design

Identical to 0011 (same runner, inline training, return head unchanged on
`fwd_max_14d`, same window 2010-2024, same features, same live 0.92/8% gate)
**except** the upper barrier is +7% instead of +4%. Lower barrier = 2×ATR,
vertical = 14d, same-day-both → stop-first, time-barrier → 0.

## Primary metric

Delta in mean after-cost per-trade return (%) on the unseen universe, candidate
(path-aware +7%) vs the **same live baseline** (`hit_4pct_14d`) as 0011, 95%
bootstrap CI.

## Attribution note (threshold vs path-awareness)

0011b's candidate differs from the live baseline in TWO ways (threshold AND
path-awareness). Both 0011 and 0011b run against the **same** live baseline, so
the *pure threshold effect* is recoverable as:
`(0011b delta vs baseline) − (0011 delta vs baseline)`.

## Decision rule (fixed in advance)

- **SUPPORT:** candidate per-trade CI lower bound ≥ baseline point estimate AND
  candidate n ≥ 30 AND WR not down >3pp AND DSR>0.95 → forward wall.
- **KILL:** candidate per-trade ≤ baseline OR n < 30 (a +7% bar is too strict for
  the 0.92 gate — itself a finding).
- **INCONCLUSIVE:** overlapping CIs.

## Priors

The gate-alignment argument is sound, but the **trade-count starvation risk is
real and higher than 0011's**: a +7%-before-stop win is rare, so few setups may
clear 0.92. Realized OOS averages ~+4%/trade, so a +7% win bar labels most
profitable trades as losses — the classifier becomes very selective. Could
sharpen quality OR starve the gate. `n` is the number to watch; n<30 → the bar
is too high for the current gate.

## Result (2026-06-04)

Same harness as 0011, upper barrier +7%. `diagnostics/data/0011b_triple_barrier_7pct.json`.

| metric | baseline (`hit_4pct` +4%) | candidate (`tb_hit` **+7%**) |
|---|---|---|
| label divergence vs live | — | **36.0%** (vs 6.2% at +4%) |
| positive rate | 64.7% | 41.6% |
| OOS trades (n) | 342 | **12** |
| per-trade | +3.68% | +10.5% (n=12 — mirage) |
| win rate | 65.8% | 100% (n=12) |
| Sharpe | 2.42 | 1.09 (lumpy) |

**Verdict — KILL (gate-starvation).** The +7%-before-stop win is rare (positive
rate 41.6%), so the confidence classifier almost never reaches 0.92 → only **12
trades** cleared the live gate. The +10.5%/100%-WR is a small-sample artifact
(Sharpe actually *fell*). n=12 ≪ 30 → no decision possible, and the mechanism
(starve the gate) is now confirmed.

**The point of the experiment was the threshold, and it's settled:** raising the
win bar +4%→+7% does NOT sharpen selection — it stops trading. Combined with 0011
(+4% path-aware = the strongest near-miss, 266 trades), **+4% is the right,
principled threshold** (it's also the live target). We do NOT raise it. This is
why threshold-by-backtest is a trap: +7% *looks* spectacular (+10.5%/trade!) until
you see n=12. The pre-registered n≥30 floor caught it.

**Decision:** +4% path-aware (`tb_hit_14d`/`tb_hit_30d`) is adopted as the
production win label (wired into `data_store` + the 3 train configs). Promotion
remains gated by the `retrain_ensemble` walk-forward.
