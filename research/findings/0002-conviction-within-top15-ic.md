# 0002 — Conviction within the top-15: weak-but-real IC on realised per-trade P&L

- Status: **SUPPORT (weak)** — a lead to C3, NOT a tradeable green light.
- Date: 2026-07-01   Pre-registration: [0072-conviction-within-top15.md](../../diagnostics/research/preregistry/0072-conviction-within-top15.md) (written BEFORE the run)
- Type: MEASUREMENT (rank-IC; no trade/PROMOTE decision) → **NOT an n_trials trial** (cf. 0021).

## Hypothesis
Among the names actually traded, a higher 4-factor conviction score (trend / low-vol / liquidity /
quality, equal-weight z-blend within the selectable pool) predicts a higher realised per-trade
return (return_pct, which embeds the +22.52% target / 3.67×ATR stop / trailing convexity).

## Method
Frozen-cfg backtest on the PINNED corrected universe (`dataset-pin-20260701`, sha `f8625a8f…52142`,
2017-01-01..2026-06-30). Each trade's conviction taken at its ENTRY date within that day's pool
(no lookahead). Primary metric = Spearman IC(conviction_at_entry, return_pct) across all trades;
significance = matched-permutation null (n_perm=5000). `scripts/run_conviction_c2.py`.

## Result (cloud run 28473678954 == local, byte-identical on pinned data)
- **IC = 0.0559, p = 0.043** (n = 1279 trades); null band [−0.045, +0.046], null mean ≈ 0.
- Quintile mean return / win-rate (clean monotone WR):

  | Q | n | mean return | WR |
  |---|---|---|---|
  | Q1 (low) | 29 | −3.03% | 51.7% |
  | Q2 | 88 | +1.99% | 58.0% |
  | Q3 | 202 | +0.96% | 58.4% |
  | Q4 | 340 | +1.61% | 59.7% |
  | Q5 (high) | 620 | +2.67% | **62.1%** |

## Conclusion
Conviction carries a **small, statistically-significant, correctly-signed** ability to rank realised
per-trade P&L. This **exceeds the 0021 prior** (≈0 *directional* IC) because conviction ranks the
**convexity / blowup-avoidance** dimension (which trades hit targets cleanly vs get stopped), not raw
direction — exactly the pre-registered mechanism. BUT:
- IC 0.056 is far below the tradeable bar (~0.3–0.5, finding 0021) — a weak lead, not alpha.
- p = 0.043 is borderline; the permutation null treats overlapping/correlated trades as independent,
  so true significance is somewhat weaker than 0.043 suggests.
- The Q-spread is driven heavily by Q1 (−3.0%, small n=29) and the Q5 WR edge; Q2>Q3 breaks strict
  monotonicity on mean return.
- IN-SAMPLE + dev-contaminated — the forward wall is the real test.

**Implication for C3:** the lead justifies a pre-registered conviction-weighted **sizing** trial
(mean-preserved: overweight high-conviction within the 15% cap), but with low expectation of clearing
the 7-criterion promotion bar given the tiny IC. KILL/UNDERPOWERED at C3 remains the honest base case.
