# 0004 — Conviction-weighted sizing (C3): KILL — it hurts on every axis

- Status: **KILL** (do not promote; the base ships flat-sized). Confirms finding 0003 (Kelly) + 0020.
- Date: 2026-07-01   Pre-registration: [0073-conviction-sizing-c3.md](../../diagnostics/research/preregistry/0073-conviction-sizing-c3.md) (written BEFORE the run; n_trials 79→80).
- Type: TRIAL. Cloud run 28475385642 (== local, byte-identical on pinned data).

## Hypothesis
Redistributing per-trade risk toward higher-conviction names (mean-preserved, 15% cap binding)
improves risk-adjusted return vs flat 3%-risk sizing.

## Method
Paired 63-day block bootstrap (n=5000) of ΔSharpe + DSR(candidate) at n_trials=80 on the pinned
`baseline_v1` (corrected universe, `dataset-pin-20260701`). Candidate = `conviction_size` quintile
multiplier {Q1 0.6 … Q5 1.4} renormalised across each day's new entries to mean 1.0.
`scripts/run_conviction_c3.py`.

## Result — KILL on every axis
| metric | base (flat) | candidate (conviction-sized) |
|---|---|---|
| Sharpe | 0.667 | **0.610** |
| CAGR | 15.46% | **13.48%** |
| maxDD | −46.26% | **−51.0%** (worse) |
| ΔSharpe | — | **−0.057**, 95% CI **[−0.25, +0.14]** (straddles 0) |
| DSR(cand) | — | **0.155** (≪ 0.95 bar) |

It is *not* even a clean sizing tilt: **trade-set overlap 0.345, deployed-notional ratio 0.955.**
The 15% position cap clips the Q5 *up*-scale, so the multiplier mostly *down*-sizes Q1 — freeing
cash that cascades into a different, slightly de-grossed trade set (so it would also fail the
turnover ≤ +30% gate). Governance **Kelly multiple k = 0.407** (within the 0.5 / half-Kelly ceiling).

## Conclusion
Conviction does **not** earn a sizing role. Three reinforcing reasons, all pre-called:
1. **Mechanism (Kelly, 0003):** a mean-preserved tilt cannot lift the mean; the binding 15% cap
   turns it into an asymmetric de-gross that overlaps the already-promoted O-009 vol-target — and
   here it de-grosses into *deeper* drawdown and lower CAGR.
2. **Signal too weak (C2, 0002):** conviction IC 0.056 → sizing IR ≈ 0.20 (overstated by trade
   correlation), structurally incapable of a +0.30 ΔSharpe.
3. **Prior (0020):** the homologous conviction-size multiplier was already +0.000, CI [0,0].

This is a first-class, expected negative (ROADMAP tradeoff 4) — the pinned base ships flat-sized.
**Open lead:** conviction's weak-but-real per-trade signal (C2) might still pay where it can move the
*mean* — conviction-driven EXITS (let high-conviction winners run / tighten low-conviction) — a
distinct, untested formulation (unconditional let-winners-run was KILLed in 0022/0047, but conditioning
on conviction has never been tried). That, or accept the base. Owner decision at the Stage-C gate.
