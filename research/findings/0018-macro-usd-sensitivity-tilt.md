# 0018 — USD/INR-sensitivity as a rank-component tilt (0082): the feature is real but loses as a selection tilt — IC ≠ portfolio Sharpe, again. KILL.

- **Status:** **KILL** (both λ arms, both windows; ΔSharpe point ≤ 0). The cross-asset branch closes **in-sample** — no forward-wall routing (that is earned only by a positive signal).
- **Date:** 2026-07-02. Pre-registration: [`diagnostics/research/preregistry/0082-macro-usd-sensitivity-tilt.md`](../../diagnostics/research/preregistry/0082-macro-usd-sensitivity-tilt.md).
- **Type:** TRIAL (2 arms; cumulative_n_trials 98 → 100). Anchor: pinned `baseline_v1`. Script `scripts/run_macro_feature.py`; raw `research/exports/macro_feature_0082.json`.

## Hypothesis
Tilting the momentum ranker AWAY from high-USD/INR-sensitivity names (the confirmed NEGATIVE cross-sectional
IC, finding 0017) raises the risk-adjusted return of the top-15 book vs momentum alone. Construction (fixed,
sign taken from the IC not fit): `trend_rank ← pctile(trend_rank + λ·(1 − usd_beta_rank))`, λ∈{0.15,0.25},
`usd_beta` = trailing-126d beta of stock return on the clean `usd_trend` factor. Panel re-ordering only.

## Result
**PRIMARY window 2019-2026** (base Sharpe 0.965 / Sortino 1.243 / CAGR 25.4 / DD −46.9 / Calmar 0.540):
| λ | Sharpe | Sortino | CAGR | DD | Calmar | ΔSharpe [CI] | DSR | ΔCalmar | 2022-26 ΔCAGR | fold | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.15 | 0.900 | 1.121 | 21.9 | −39.5 | 0.550 | −0.065 [−0.41,+0.26] | 0.37 | +0.010 | **−0.29** | 0.25 | KILL |
| 0.25 | 0.960 | 1.190 | 24.1 | −38.7 | 0.620 | −0.006 [−0.38,+0.31] | 0.49 | +0.080 | **−1.23** | 0.62 | KILL |

**Context window 2017-2026** (base 0.667 / 0.836 / 15.5 / −46.3 — reproduces `baseline_v1` exactly ✓):
| λ | ΔSharpe [CI] | DD | 2022-26 ΔCAGR | fold | verdict |
|---|---|---|---|---|---|
| 0.15 | −0.048 [−0.46,+0.33] | −51.6 | +3.88 | 0.62 | KILL |
| 0.25 | −0.001 [−0.42,+0.40] | −49.9 | +1.53 | 0.75 | KILL |

Every arm's ΔSharpe **point estimate is ≤ 0** (−0.065, −0.006, −0.048, −0.001), CI straddling 0; DSR 0.16–0.49
(≪ 0.95). Per the pre-committed rule (KILL if ΔSharpe point ≤ 0 or 2022-26 ΔCAGR ≤ 0), **all four arms KILL.**

## Root-cause readout (REQUIRED)
The USD/INR-sensitivity signal **is real** — it survived the PIT gate with an independently-rebuilt clean IC
(0017: −0.0295, IC-IR −0.28). But a real cross-sectional IC of ~0.03 does **not** convert into a portfolio
Sharpe lift when added as a rank component — the **exact same IC ≠ portfolio-Sharpe gap** that killed the
52-week-high in 0079 (IC +0.068, still loses as a ranker). Mechanically: tilting toward low-USD-beta names
re-sorts the book toward lower-vol, more-domestic names — in the PRIMARY window that **trims the drawdown**
(−46.9 → −38.7) and nudges Calmar up (+0.08), but it also **trims the return engine** (CAGR 25.4 → 24.1),
leaving Sharpe flat-to-down. Critically, the DD relief is a **pre-2022 artifact**: the continuous-slice
2022-26 sub-period CAGR gets *worse* (−1.23pp at λ=0.25), so the hedge does not hold in the live regime — and
the sign of the 2022-26 effect even flips between the 2019 (negative) and 2017 (positive) windows, i.e. the
effect is unstable. A half-strength orthogonal IC blended into a strong ranker mostly dilutes the ranker; the
diversification it buys (a little less DD) costs more Sharpe than it saves. This is not underpowered noise —
the point estimate is negative — it is a genuine KILL of the *tilt formulation*.

## What this closes / what it does not
- **Closes:** USD/INR-sensitivity as a **rank-component selection tilt** on the single momentum sleeve. Do not
  relitigate this formulation. Crude was already dropped in 0017 (lookahead artifact). VIX-sensitivity is dead.
- **Does NOT trigger Step 3** (forward-wall routing) — that was pre-committed to a PROMOTE / strong-UNDERPOWERED
  only. A negative-ΔSharpe KILL earns no watch slot; the wall is for signals that *added*.
- **Still true (from 0017):** USD/INR-sensitivity is the first PIT-clean orthogonal, mechanism-backed *feature*
  the program found. It just doesn't monetize as a top-15 selection tilt. The only place it could still matter
  is a *different application altogether* — a genuinely multi-sleeve book where a low-USD-beta sleeve is
  combined at the portfolio level (the 0081 ERC mechanism), not blended into the ranker. That is the low-vol
  multi-sleeve fork's territory (owner decision, forward wall), **not** a new single-sleeve in-sample trial.

## Verdict
**KILL.** The cross-asset arc delivered exactly what a disciplined gate should: it found the one real
orthogonal signal, proved it PIT-clean (0017), then honestly showed it does not lift the portfolio as a tilt
(0018). The in-sample program stays closed; the forward wall stays the only certifier.
