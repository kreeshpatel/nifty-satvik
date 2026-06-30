# 0006 — Let winners run (0071): removing the profit target IMPROVES the 63d strategy (SHADOW)

- Status: **SHADOW** (positive but UNDERPOWERED — log, watch the forward wall, do NOT promote to cfg).
- Date: 2026-07-01 (autonomous). Pre-reg: 0071 (carried, re-run on baseline_v1, mechanized bar).
- Type: TRIAL (sunk — already in n_trials). Cloud run 28481282947 (== local --quick, pinned).

## Hypothesis
The +22.52% profit target clips momentum winners that would run further over the 63-day hold; removing
the target (and/or trailing) lets winners run, improving risk-adjusted return.

## Result (mechanized 7-gate bar, pinned baseline_v1)
| Arm | Sharpe (base 0.667) | ΔSharpe [CI] | ΔCalmar | 2022-26 ΔCAGR | fold-pass | DSR | after-tax CAGR (base 12.76%) | verdict |
|---|---|---|---|---|---|---|---|---|
| **B stop_only** (no target, no trailing) | 0.781 | **+0.114** [−0.16, 0.36] | +0.05 ✓ | +9.6% ✓ | 75% ✓ | 0.35 | 14.87% | **UNDERPOWERED** |
| **D no_target** (no target, keep trailing) | 0.805 | **+0.138** [−0.14, 0.41] | +0.06 ✓ | +7.0% ✓ | 75% ✓ | 0.27 | **16.76%** | **UNDERPOWERED** |
| C no_trailing (keep target, no trailing) | 0.631 | −0.036 | −0.01 | −2.3% | 50% | 0.18 | 10.73% | KILL |

## Conclusion
Removing the **profit target** (B & D) improves Sharpe (→0.78/0.81), Calmar, the 2022-26 sub-period,
and fold-pass (75%) — clearing **4 of the hard gates** — and lifts **after-tax CAGR materially**
(D: 12.76→16.76%, +4pp), because winners run longer → fewer taxable realizations → less STCG churn.
Removing only the **trailing** (C) HURTS — the trailing stop is doing useful work; it's the fixed
**target** that's the drag. Both winning arms are **UNDERPOWERED** (ΔSharpe CI straddles 0, DSR<0.95):
at ~34 effective windows we can't *certify* a +0.11–0.14 ΔSharpe, so this cannot be promoted to the
frozen cfg.

**This is the first non-KILL lead of the arc**, and it **vindicates the do-not-transfer rule**: the v1
14d result (0047: trailing-off lowered IR; 0022: let-winners-run dead) does NOT carry to the 63d
strategy — here removing the target is clearly positive. The research edge is **exit structure**, not
conviction/sizing (both dead).

## Disposition + next (autonomous)
**SHADOW** the let-winners-run family; flag for the forward wall (the only thing that can power it up).
DIG DEEPER (overnight): **target sweep** target_pct ∈ {15, 22.52, 30, 40, OFF} to map the give-back
curve — momentum decays hyperbolically (external #6), so a higher FINITE target may dominate OFF
(capturing most of the right tail while still banking some). If a finite target Pareto-dominates the
base on Sharpe+Calmar+after-tax, that's a stronger, possibly-promotable candidate than pure no-target.
