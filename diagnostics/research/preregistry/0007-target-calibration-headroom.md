# 0007 — Target-calibration headroom

- **ID:** 0007
- **Registered:** 2026-06-02
- **Holdout:** unseen-universe → forward-wall. No retrain (changes the target
  level / exit, not the model).
- **n_trials (cumulative):** ~53.
- **Status:** PENDING

## Motivation

B2 (2026-06-02): the model's return head predicts `fwd_max_14d` (the *max*),
which averages +8.26% vs a +1.20% realized 14-day hold — a 7pp optimism gap.
Targets built from that prediction sit too high → **time-exits dominate** (seen
in the client ledger). The live system already applies `shrink_target`
(`engine/target_calibration.py`, fit 2020-2025), which shrinks the target toward
an achievable level. Question: **is the existing shrink aggressive enough, or is
there headroom** to convert time-exits into target-hits and lift realized
per-trade return / capture?

## Hypothesis

A more aggressively calibrated target (or a different shrink curve) produces a
higher **realized after-cost per-trade return** on the unseen universe than the
current live calibration, by raising the target-hit share without raising the
stop-out rate. Allowed to fail — over-shrinking caps winners (HFCL-type runners)
and could *lower* expectancy.

## Primary metric

**Realized after-cost per-trade return (%)** on the unseen universe under the
candidate calibration vs the live calibration, 95% bootstrap CI on the paired
difference. Secondary: exit-reason mix (target vs stop vs time) shift; capture
of the large (+20%/30d) movers (must not collapse — the over-shrink risk).

## Decision rule (fixed in advance)

- **SUPPORT:** candidate per-trade CI lower bound ≥ live point estimate AND
  target-hit share up AND large-mover capture not down >X% AND DSR>0.95.
- **KILL:** candidate expectancy ≤ live, OR large-mover capture collapses
  (over-shrink caps the runners that carry the edge).
- **INCONCLUSIVE:** overlapping CIs → the live calibration is already near-optimal.

## Procedure

1. Measure the CURRENT shrink_target effect: backtest with `target_calibration`
   ON vs OFF — quantify the exit-mix + expectancy delta the live calibration
   already buys. (Headroom baseline.)
2. Sweep a small set of shrink curves (more/less aggressive); pick the best on
   the unseen universe; confirm large-mover capture is intact; DSR-correct.

## Priors / note

This targets the soft spot B1+B2 isolated (target-setting, not name-selection).
But the live `shrink_target` already does much of this, so the headroom may be
small (INCONCLUSIVE is a likely outcome). Highest-value Tier-C item per the
audit synthesis; run before 0006.

## Result (2026-06-02) — INCONCLUSIVE/KILL: live calibration is already optimal

Shrink-aggressiveness sweep on the unseen universe (same ensemble/costs;
per-trade after cost, top-decile mean = big-runner-capture proxy):

| shrink | per-trade | WR | Sharpe | target-hit% | top-10% |
|---|---|---|---|---|---|
| raw (none) | +4.07% | 68.5 | 2.76 | 27 | 29.0 |
| ×0.70 | +3.82% | 68.0 | 2.88 | 52 | 23.3 |
| ×0.85 | +3.99% | 68.5 | 2.91 | 43 | 24.5 |
| **live** | **+4.20%** | 68.4 | 2.90 | 36 | 26.9 |
| ×1.15 | +3.95% | 67.9 | 2.70 | 28 | 28.5 |
| ×1.30 | +4.01% | 67.0 | 2.69 | 23 | 30.5 |

**Live is the best per-trade of all six.** It's a clean trade-off: shrinking
harder converts time/trailing-exits into target-hits (52% at ×0.70) but **caps
the runners** (top-decile 29→23) → lower per-trade; loosening catches more
runners but fewer hits → also lower. The existing `shrink_target` (k from
`models/v1/target_calibration.json`) is tuned to the optimum. No headroom →
do not change. The B2 max-label optimism is REAL but already correctly handled
by the live calibration; the soft spot is closed, not open.

Note: this is the THIRD disciplined test (after 0004, 0005) to conclude the
current system is already well-tuned and the obvious lever doesn't beat it.
The model + its calibration sit at a local optimum that reuses of the existing
price/volume information cannot improve. Remaining real odds are in genuinely
ORTHOGONAL data (delivery%, options) or the A3 stale-data correctness fix —
not in re-exploiting what the model already sees.

_(pre-registration above this Result section is immutable)_
