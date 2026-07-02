# 0015 — Momentum + low-vol ERC (0081): the multi-sleeve combination lifts every risk-adjusted axis at flat CAGR — uncertifiable, so it goes to the forward wall

- **Status:** **UNDERPOWERED** (the diversification is real and large in-sample; uncertifiable at the
  sample). Routes the low-vol sleeve to the **forward wall** as a watched sleeve — do NOT change the cfg.
- **Date:** 2026-07-02. Pre-registration: [`diagnostics/research/preregistry/0081-momentum-lowvol-erc.md`](../../diagnostics/research/preregistry/0081-momentum-lowvol-erc.md).
- **Type:** TRIAL (1 arm; cumulative_n_trials 97 → 98).
- **Anchor:** pinned `baseline_v1`. Script `scripts/run_erc_combo.py`; raw `research/exports/erc_combo_0081.json`.

## Hypothesis
Combining the frozen momentum book with a low-vol sleeve (rank by inverse realized-63d vol, O-016) at
equal-risk-contribution (quarterly inverse-vol weights) raises the blended Sharpe vs momentum-alone and cuts
the drawdown, driven by their low return correlation. This is a **portfolio-level combination of two books**
— NOT O-006 (low-vol blended into the score) NOR O-016 (low-vol as a sole replacement ranker).

## Result
| book | Sharpe | Sortino | CAGR | MaxDD | Calmar | 2022-26 Sharpe |
|---|---|---|---|---|---|---|
| momentum (base) | 0.667 | 0.835 | 15.5 | −46.3 | 0.33 | 0.582 |
| low-vol sleeve | 1.059 | 1.396 | 14.5 | −32.6 | 0.45 | 1.344 |
| **COMBINED (ERC)** | **0.942** | **1.131** | **15.0** | **−36.1** | **0.42** | **1.066** |

**corr(momentum, low-vol) = 0.54** (< 0.7 → real diversification). Combined vs momentum: **ΔSharpe +0.275
[−0.10, +0.70]**, ΔSortino +0.296 [−0.16, +0.91], **DSR 0.32**.

## Verdict
**UNDERPOWERED.** The combination improves Sharpe (0.67→0.94), Sortino, MaxDD (−46→−36), Calmar (0.33→0.42),
and the 2022-26 Sharpe (0.58→1.07) — **while preserving CAGR** (15.5→15.0). But ΔSharpe CI straddles 0 and DSR
is 0.32 ≪ 0.95 — uncertifiable at ~34 windows, the same wall as everything.

## Root-cause readout (REQUIRED)
The lift is the **diversification mechanism working as advertised**: two positive-Sharpe sleeves with a return
correlation of only 0.54, combined at inverse-vol risk-parity, produce a book with a higher Sharpe than either
weighted-average would suggest — and because low-vol carries its own return, CAGR barely moves. This is the one
Sharpe-lift that does *not* route through the spent single-sleeve trial budget: the combining math is near-
deterministic given the two return series. **Why still UNDERPOWERED:** the entire benefit rests on the low-vol
leg being a *real* edge, and low-vol is uncertifiable in-sample (O-016: Sharpe 1.06 but ΔSharpe CI straddles 0,
DSR 0.35). A combination of {certain momentum edge} + {uncertain low-vol edge} inherits the uncertainty. So
in-sample this is strong-but-unprovable — exactly as pre-registered.

## Next setup
- **Route the low-vol sleeve to the forward wall** (the only certifier). The operational robot (Part A / finding
  fd2982c) already logs base + veto + drift daily; adding low-vol is a `forward/prereg.md` §7 shadow swap (drop
  `drift`, add the low-vol book) + a §10 amendment — an **owner decision at the quarterly review**, not an
  in-sample cfg edit. Once watched, ~18 months of forward data on the *combined* book vs momentum-alone (the §6
  promotion criteria) is what proves or kills the multi-sleeve thesis.
- The combination is the *reason* to watch low-vol forward; 0080 (trend×low-vol filter) is *how* to build a
  momentum-quality variant of its leg later.
- Do NOT retune the weighting or promote to cfg in-sample. The weighting is fixed; the wall decides.
