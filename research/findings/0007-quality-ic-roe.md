# 0007 — Quality/value predictor IC (ROE, earnings-yield, book-yield): KILL (leak + regime)

- Status: **KILL** — no robust, leak-free, regime-stable fundamental predictor. Orthogonal-predictor
  component CLOSED for lock (with gross-profitability still data-gated/untested — LOCK_PLAN Step 4).
- Date: 2026-07-01 (autonomous). Type: MEASUREMENT (rank-IC, 0 trials). Pinned baseline_v1.

## Method
Rank-IC (Spearman) of available PIT fundamentals at trade entry vs realised per-trade return_pct, over
the 1279 base trades, with the **block-permutation null** (block=38 ≈ trades/63d-window). Stress-tested
two ways: a conservative **90-day announcement lag** (period_end + 90d ≤ entry — earnings aren't
observable at quarter-end) and a **2017-21 vs 2022-26 regime split**.

## Result
| factor | full IC (p) | with 90d lag | 2017-21 | 2022-26 (live) |
|---|---|---|---|---|
| **ROE** | +0.078 (0.015) | +0.063 (0.053) | +0.118 (0.022) | **+0.042 (0.32)** |
| earnings-yield (eps/price) | +0.046 (0.21) | — | — | — |
| book-yield (bvps/price) | +0.004 (0.91) | — | — | — |

## Conclusion — KILL
ROE looked significant full-period (IC 0.078, p 0.015 — higher than the conviction blend, which diluted
it). But it fails BOTH honest checks: **(1) leakage** — a 90-day announcement lag drops it to p 0.053
(part of the "signal" was using quarter-end ROE before it was announced); **(2) regime** — even at lag 0
it's a 2017-21 bull artifact (2022-26 p 0.32). With both corrections ROE IC ≈ +0.037 (p 0.38) ≈ ZERO.
Value (ep/bp) is dead as expected (0017). **No fundamental earns a place.**

**Process flag (data integrity):** the fundamentals store keys on `period_end` (quarter-end) with NO
announcement lag → a latent ~45-90d lookahead in any fundamental join (backtest-rigor §A3). IMMATERIAL
to the base (fundamentals only feed the slow D/E solvency screen, robust to a quarter's lag) but MUST be
fixed before fundamentals ever drive selection/sizing/conviction. Lock-gate note.
