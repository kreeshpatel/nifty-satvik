# 0012 — Residual momentum as a complement (0078): the VETO mechanism is validated, but all arms KILL the pre-committed bar

- **Status:** **KILL** (all 4 arms, by the pre-committed 0078 rule). The **veto construction is validated** (return-preserving, Sortino- and DD-improving); **veto-0.1 is the near-miss** (fails only marginal skew) → forward-wall watch, not a promotion. Do NOT change the frozen cfg.
- **Date:** 2026-07-02. Pre-registration: [`diagnostics/research/preregistry/0078-residual-blend-veto.md`](../../diagnostics/research/preregistry/0078-residual-blend-veto.md).
- **Type:** TRIAL FAMILY (4 fixed-param arms; cumulative_n_trials 87 → 91).
- **Anchor:** pinned `baseline_v1`; FF-India factors (Market + HML). Motivated by the vol-matched diagnostic (`scripts/diag_volmatch_residmom.py`): resid's DD edge is **live-window-only** (vol-matched 2022-26 −33.6 vs base −46.3 survives; full-period −56.8 is worse).

## Hypothesis
Applying residual momentum as a COMPLEMENT — blending it into the rank, or vetoing the worst-scored
names — retains the trend signal's return while buying down the factor-grind drawdown.

## Method
4 arms vs base: BLEND λ∈{0.25,0.50} (`rank=pctile(trend_rank+λ·resid_rank)`), VETO q∈{0.20,0.10}
(exclude bottom-quintile/decile resid_rank names from trend selection). Pre-committed SHADOW rule
(else KILL): (1) LIVE 2022-26 DD ≥ 8pp shallower than base (≤ −38.3), vol-guarded if book vol < 24%;
(2) full-period **gross** CAGR ≥ 13.5%; (3) skew AND Sortino not worse. `scripts/run_residual_blend_veto.py`.

## Result (base: gross CAGR 15.5, after-tax 12.76, Sortino 0.836, skew −0.639, vol 27.1%, LIVE DD −46.3)
| arm | gross CAGR | after-tax | Sortino | skew | vol% | LIVE DD (guard) | dSharpe | c1 DD | c2 CAGR | c3 shape | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| blend-0.25 | 10.9 | 8.13 | 0.716 | −0.571 | 24.0 | −35.3 | −0.115 | ✓ | ✗ | ✗ | KILL |
| blend-0.50 | 12.4 | 9.78 | 0.771 | −0.619 | 24.0 | −34.7 | −0.058 | ✓ | ✗ | ✗ | KILL |
| veto-0.20 | 18.4 | 15.32 | 0.970 | −0.680 | 26.8 | −40.9 | +0.098 | ✗ | ✓ | ✗ | KILL |
| **veto-0.10** | **17.4** | **14.83** | **0.938** | −0.691 | 26.4 | **−37.5** | +0.076 | ✓ | ✓ | **✗ (skew only)** | **KILL** |

## Root-cause readout (REQUIRED)
**BLEND fails as the vol-match predicted:** diluting the trend everywhere improves skew (−0.64 → −0.57/
−0.62) but taxes the paying years — gross CAGR falls to 10.9/12.4% (< the 13.5% floor) and Sortino
drops. Confirmed: you cannot dilute a moderate-edge ranker for a tail benefit without paying return.

**VETO validates the mechanism** — touching only the worst-scored names lifts gross CAGR *above base*
(18.4/17.4 vs 15.5; removing trend picks whose "trend" is pure factor beta is return-accretive),
improves Sortino (0.94/0.97 vs 0.84), cuts the live-window DD, and holds a strong ≥2019 fold-pass
(0.75/0.875). **veto-0.1 clears DD (−37.5, 8.8pp shallower) AND the return floor AND Sortino — it fails
ONLY the marginal skew criterion** (−0.691 vs −0.639). The veto trims the deep left tail (Sortino/DD
improve) but also some right tail (skew marginally worsens): **Sortino and skew disagree.** Two honesty
notes: (a) the DD is **non-monotone in the cutoff** (veto-0.2 −40.9 is *deeper* than veto-0.1 −37.5 —
the more-aggressive veto cut *less* DD), an overfit-surface signal that the specific q is not robustly
identifiable in-sample; (b) per the pre-committed rule this is a **KILL** and is recorded as such — no
goalpost move.

## Verdict
**KILL** all 4 by the pre-committed bar. Blends fail the return floor; vetoes fail on DD magnitude
(q=0.20) or marginal skew (q=0.10). The veto *mechanism* — drop the pure-factor-beta trend picks — is
real (return-accretive, Sortino+DD-improving), but no arm cleared the full pre-committed shape bar.

## Next setup
1. **veto-0.1 → forward-wall watch.** It preserves/improves return AND Sortino AND cuts the live DD;
   only the unbiased forward wall can certify it. NOT a cfg change.
2. **Methodological (for the next pre-reg, not a post-hoc move here):** skew was the *binding*
   constraint while Sortino + DD — the downside metrics the −46% problem is actually about — both
   improved. Reconsider whether skew belongs in the shape bar, or whether Sortino + DD-shape are the
   right axes for a downside overlay.
3. **SMB follow-up (0079):** the veto now justifies the Screener re-scrape — a full-FF3 residual
   (adding size) may improve skew too (the smallcap leg of the 2024-25 unwind the 2-factor residual
   leaves in), potentially converting veto-0.1's near-miss into a pass on all three axes.
4. Do NOT retune q in-sample (non-monotone surface).
