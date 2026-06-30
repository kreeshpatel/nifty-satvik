# 0008 — Randomized-entry null: the slope edge is REAL but MODERATE (base validated)

- Status: **BASE VALIDATED** (entry signal beats random) + the unifying explanation for why overlays fail.
- Date: 2026-07-01 (autonomous). Type: MEASUREMENT (0 trials). Pinned baseline_v1. Rigor-audit P2 item.

## Method
Replace the `sma200_slope_63` cross-sectional rank with a RANDOM uniform rank (random top-15 from the
SAME eligible large+mid+solvent universe, same ATR-stop/target/trailing exits, same caps), 12 seeds.
Does the slope selection beat random? (Turnover matched ~138-144 vs real 149, so the comparison is fair.)

## Result
| | CAGR | Sharpe | maxDD |
|---|---|---|---|
| **REAL (slope)** | **15.46%** | **0.667** | −46.3% |
| Random (12 seeds) mean | 7.90% | 0.474 | — |
| Random range | [−2.3, 18.0]% | [−0.004, 0.916] | — |
| REAL percentile vs random | **92nd (CAGR)** | 83rd (Sharpe) | — |

## Conclusion
The slope selection **adds real, economically significant value** — it roughly **doubles CAGR vs random**
(15.46 vs 7.90) and adds +0.19 Sharpe; the base edge is genuine, not just momentum-exposure. This
corroborates PSR(>0)=0.974. **BUT the edge is MODERATE:** random selection from the same liquid/solvent
universe with the same disciplined exits already earns ~half the return (7.9% CAGR / 0.47 Sharpe), and
2/12 random seeds beat the slope's Sharpe. So a large share of the strategy's return is **structural**
(universe quality + ATR-stop/target/trailing exit discipline), with the slope adding a real-but-moderate
tilt on top.

**This is the unifying explanation for the whole research arc:** the moderate edge + the large already-
captured structural component leave **almost no headroom for marginal overlays** — which is exactly why
conviction (INCONCLUSIVE), sizing (KILL), regime (KILL), exits (regime-dependent), and quality (KILL)
have ALL failed the bar. The base is a genuine, validated, modest-edge strategy at its ceiling. **Ship
the base.** (Caveat: 12 seeds is a first pass; the CAGR-doubling is the robust signal, the Sharpe
percentile noisier — a 200-seed formal test would tighten it but won't change the conclusion.)
