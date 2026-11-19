# DRAFT — CLAUDE.md mission fallback wording

**Status: DRAFT. Not applied.** Owner request 2026-11-18: propose, don't apply. `CLAUDE.md` is unchanged.

## Proposed diff

```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -7,8 +7,9 @@
 Momentum 50 TRI on risk-adjusted return over rolling 3-year windows, with a worst drawdown no deeper than −25%,
 proven by a forward record rather than a backtest, and needing no more than about 1 hour a week of owner time. The
 target system is the 70/30 momentum/swing blend at a 15% volatility target, with total system capital of
 ₹20,00,000: PILOT ₹2,00,000, SCALE ₹5,00,000, FULL ₹20,00,000. Promotion between stages needs 26 weeks on paper. If
-no strategy meets this goal, core capital goes into the index fund.
+no strategy meets this goal, core capital goes into the index fund plus a liquid fund, at the exposure whose 156-week
+p95 drawdown meets −25%.
```

(The "15% volatility target" in the same paragraph changes only if the separate vol-target amendment,
`forward/drafts/2026-11-18_amendment_blend_vt11_DRAFT.md`, is signed.)

## What "the exposure" is today

Measured in `diagnostics/research/explore/2026-11-18_risk_matched_benchmark.json`, `q3_risk_matched → bench_static_*`:
a fixed share e of the Nifty Midcap150 Momentum 50 TRI, the rest in cash at 6.5% a year, rebalanced daily, with the
156-week stationary-bootstrap p95 drawdown measured at mean block 26 weeks (10,000 draws). The grid is 0.05 wide.

| window | highest e meeting −25% (block 26) | p95 | CAGR | at block 8 |
|---|---|---|---|---|
| 2019-03..2024-06 | 0.70 | 24.5% | 25.9% | 0.60 |
| 2017-01..2026-06 | 0.65 | 23.6% | 17.2% | 0.60 |

An independent replica got the same exposures (0.70 / 0.65; p95 24.4% / 23.5%).

## Points for the owner before signing

1. **Which block length defines "meets".** Block 26 gives 0.65–0.70, and block 8 (the block used to pick the blend's 11%)
   gives 0.60. The wording should name one, or the fallback and the blend are sized by different rules.
2. **Which window.** The longer window is more conservative and includes 2018 and the 2024–26 period. Suggest the
   longest available history, re-measured at each annual review.
3. **Rebalancing.** The figures assume daily rebalancing. A real index fund plus liquid fund split drifts, so the
   wording could add "rebalanced quarterly", which then needs re-measuring under that rule.
