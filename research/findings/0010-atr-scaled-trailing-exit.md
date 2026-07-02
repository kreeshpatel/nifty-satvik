# 0010 — Uncapped target + ATR-proportionate trailing (0076): a real, regime-robust exit edge that is UNDERPOWERED

- **Status:** **UNDERPOWERED** (directional edge real + regime-robust; statistically uncertifiable at n_trials=86). Do NOT change the frozen exit cfg off this run.
- **Date:** 2026-07-02. Pre-registration: [`diagnostics/research/preregistry/0076-atr-scaled-trailing.md`](../../diagnostics/research/preregistry/0076-atr-scaled-trailing.md) (written BEFORE the run).
- **Type:** TRIAL (4 grid arms; cumulative_n_trials 82 → 86, incremented before the run).
- **Anchor:** pinned `baseline_v1` (`dataset-pin-20260701`), frozen cfg, corrected universe, 2017-01-01..2026-06-30.

## Hypothesis
Removing the +22.52% target un-truncates the momentum right tail, and replacing the flat 4.27%
trailing stop with an ATR-proportionate width (`trail_atr_mult × atr_pct_63`) protects open profit in
proportion to each name's volatility — lifting Sortino/Calmar and cutting the drawdown, while
surviving the correctly-sliced 2022-26 gate that killed 0071's flat-trail variants.

## Method
Uncapped target (`target_pct`=999) × `trail_atr_mult ∈ {2.0, 2.5, 3.0, 3.5}`, flag-gated in
`exits.decide_exit` + `portfolio.simulate` (golden byte-identical when off — `test_stage2_golden.py`
3 passed). Each arm vs frozen base via `evaluate_overlay` (paired 63-day block bootstrap n=5000,
DSR at n_trials=86, continuous-slice 2022-26 gate, ≥2019 fold-pass) + a paired block-bootstrap
ΔSortino. Script: `scripts/run_atr_trail_overlay.py`; raw JSON `research/exports/atr_trail_0076_results.json`.

## Result (base: Sharpe 0.667, Sortino 0.836, DD −46.3, Calmar 0.33, after-tax CAGR 12.76%)
| mult | cand Sharpe | ΔSharpe [CI] | ΔSortino [CI] | DSR | ΔCalmar | 22-26 ΔCAGR | fold | turn Δ | DD | after-tax CAGR | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0 | 0.780 | +0.113 [−0.18, +0.40] | +0.182 [−0.20, +0.58] | 0.26 | +0.08 | +6.5% | 0.88 | −30% | −46.4 | 16.24% | UNDERPOWERED |
| **2.5** | **0.808** | **+0.141 [−0.13, +0.40]** | **+0.225 [−0.15, +0.60]** | 0.30 | +0.12 | +2.4% | 0.88 | −38% | −44.1 | **16.30%** | **UNDERPOWERED** |
| 3.0 | 0.742 | +0.075 [−0.18, +0.32] | +0.123 [−0.22, +0.45] | 0.26 | 0.00 | +8.7% | 0.62 | −45% | −53.6 | 14.68% | UNDERPOWERED |
| 3.5 | 0.775 | +0.108 [−0.18, +0.40] | +0.160 [−0.22, +0.56] | 0.24 | +0.10 | +2.8% | 0.75 | −49% | −43.1 | 15.52% | UNDERPOWERED |

Best arm **2.5** clears **5 of 7 gates** (ΔCalmar +0.12 ✓, 2022-26 ΔCAGR +2.4% ✓, fold-pass 0.88 ✓,
turnover −38% ✓, mechanism ✓) and FAILS the two certification gates: **ΔSharpe CI-low ≤ 0** (−0.13)
and **DSR ≤ 0.95** (0.30).

## Root-cause readout (REQUIRED)
**Why the point estimate improves:** removing the target un-truncates the right tail (base clips 17.7%
of trades at exactly +22.5%; uncapped surfaces trades to +125%) and letting winners ride cuts turnover
~30–49% → lower cost + fewer taxable realizations → **after-tax CAGR +3.5pp** (12.76→16.30%); the
ATR-scaled trail lifts Sortino 0.84→1.06 and Calmar 0.33→0.45. **Why UNDERPOWERED:** at ~34
non-overlapping 63-day windows the ΔSharpe standard error is large — a +0.14 point estimate sits well
inside its [−0.13, +0.40] CI, and the DSR deflated at 86 trials is 0.30 (bar 0.95). The edge is
real-but-small relative to the book's ~27% vol. **The mult surface is spiky** (3.0 dips between 2.5 and
3.5, and blows the DD out to −53.6 via right-tail give-back) → the specific multiple is not robustly
identifiable in-sample — the same overfitting tell 0071 flagged for the target, and the reason ATR
scaling (not a fitted flat %) was the right formulation to test even though it did not rescue certifiability.

**Correction to 0071 (important):** 0071's WEAK-SHADOW "bull artifact" downgrade used a **fresh-capital
per-half re-run** (phantom base 2022-26 Sharpe 0.762 / DD −40.0). On the correct **continuous-slice**
gate (base 0.570 / −46.3), the exit-loosening family PASSES the 2022-26 sub-period on every arm
(subperiod_2022_positive=True) with fold-pass 0.88 — it is **directionally real AND regime-robust**, not
a bull artifact. The correct status is UNDERPOWERED (0071's top-table verdict), not WEAK-SHADOW. See
[[subperiod-gate-continuous-slice]].

## Next setup
This exit-loosening family (0071 + 0076) is the **strongest, most regime-robust, best after-tax lead in
the program — but sample-limited, not promotable in-sample.** The defensible path is NOT an in-sample
mult pick; it is (a) a **forward-wall OOS watch** (post-2026-05-30 paper accrual), and/or (b) a
**walk-forward re-derivation** of the whole exit block on the corrected vintage (LOCK Plan D2), mult
chosen per-fold. To tighten the CI, a pre-registered stack with the already-shipped vol-target (0068)
or a faster-recycling horizon could raise effective sample — a new pre-reg, not this one.
