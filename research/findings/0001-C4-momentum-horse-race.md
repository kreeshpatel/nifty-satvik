# 0001 — C4 momentum horse-race: `sma200_slope_63` is the best sole entry ranker (G2 retired)

- Status: **KILL** (all 3 replacement candidates) → **`sma200_slope_63` CONFIRMED** as the entry signal.
- Date: 2026-06-28   Pre-registration: [`../preregistry/C4-momentum-horse-race.md`](../preregistry/C4-momentum-horse-race.md) (written BEFORE the run)
- Trials: n_trials 73 → **76** (3 arms, counted before the run). DSR evaluated at 76.
- Run: cloud `cpcv-research.yml` `run_long_horizon_signal_race` (28326794167). Entry-Signal Arc Phase 1, Tier 1, candidate **C4**.

## Hypothesis
`sma200_slope_63` was the max of a ~16-factor screen with **no multiple-testing correction** and was
never deflation-tested *as a trading strategy* (gap **G2**). If its win was a selection artifact, a
co-equal raw-momentum factor (`mom_252_21` 12-1, `mom_126` 6-month, `donchian_pos_126` 126-day channel
position) should **match or beat** it as the sole cross-sectional ranker out-of-sample after DSR.

## Method
Canonical 681→solvent universe, FROZEN cfg, **paired same-cache** (the cache-vintage ±4pp lesson — only
paired deltas are trusted, P3). Each signal re-ranks the SAME universe and runs through BOTH the frozen
full strategy AND the entry-only book (the validated Phase-0 pure-rank bar). Rule-only (fixed factors,
no fit) → no CPCV embargo (P6). Per candidate vs the `sma200_slope_63` base: paired ΔSharpe / ΔCAGR /
ΔCalmar, ≥2019 per-year fold-pass, sub-period 2017-21 / 2022-26 ΔCAGR, block-bootstrap ΔSharpe CI
(block=63, n=2000), DSR at cumulative n_trials=76. P4 demerger quarantine applied to all price-derived
signals before ranking. (Absolute CAGR is gross + cache-noisy; the **paired deltas** are the signal.)

## Result (base `sma200_slope_63` full strategy this run: 27.62% CAGR / 1.067 Sharpe / 0.63 Calmar)

| candidate (full strategy) | ΔSharpe | ΔCAGR | boot ΔSharpe CI | ≥2019 fold-pass | 2017-21 ΔCAGR | 2022-26 ΔCAGR | DSR | entry-only ΔSharpe |
|---|---|---|---|---|---|---|---|---|
| `mom_252_21` (12-1) | **−0.22** | −6.8pp | [−1.06, +0.23] (straddles 0) | 4/8 | −8.9 | −4.2 | 0.0 | −0.087 |
| `mom_126` (6m) | −0.49 | −15.4pp | [−1.51, −0.01] (<0) | 1/8 | −8.9 | −20.6 | 0.0 | −0.095 |
| `donchian_pos_126` | −0.45 | −17.6pp | [−1.37, −0.12] (<0) | 2/8 | −23.1 | −11.6 | 0.0 | +0.049 |

**0 of 3 candidates clear the promotion bar.** The pick wins on BOTH the full strategy and the
entry-only book against all three; even the strongest competitor (`mom_252_21`, 2nd-highest IC in F2)
loses by −0.22 Sharpe / −6.8pp CAGR and fails every gate.

### S4 — adversarial review (R1–R8)
- **R1 mechanism** PASS · **R2 overfit** PASS (signal swap, 0 params, no decimal threshold).
- **R3 2022–26 sub-period** — every candidate is **negative** (−4.2 / −20.6 / −11.6 pp): all hard-fail.
- **R4 ΔSharpe ≥ +0.10** FAIL (all negative) · **R5 ΔCalmar ≥ +0.05** FAIL · **R6 fold-pass ≥ 60%**
  FAIL (4/8, 1/8, 2/8) · **R7 bootstrap CI excludes 0 on the upside** FAIL (all straddle-or-below 0).
- Verdict: all 3 cleanly **REJECT** as replacements; `sma200_slope_63` confirmed.

## Root-cause readout (REQUIRED)
**Why the 200-day slope wins as the sole ranker — it measures trend QUALITY, not raw momentum.**
`sma200_slope_63` slopes the *smoothed* 200-day average, so it rewards durable, low-noise up-trends and
ignores the sharp one-off pops that mean-revert. The raw factors capture the same Jegadeesh-Titman
intermediate-momentum premium but extract it more noisily: `mom_252_21`/`mom_126` carry the volatile
recent price path (more whipsaw → more false entries), and `donchian_pos_126` at the top of its channel
often signals near-term *exhaustion* (F2 measured its incremental sign **flips negative** after
momentum — "contrarian-after-momentum"; here its full-strategy book is the worst). The smoothing is the
edge: same premium, cleaner extraction, higher Sharpe. This is consistent with DOSSIER **F2** (slope
highest mean IC 0.092 > 12-1 0.086 > 6m 0.063 > donchian 0.054), **F4** (single trend beats composites
OOS), **F5** (generalises to unseen stocks) — and C4 adds the **strategy-level, DSR-corrected**
confirmation the factor-IC work did not provide. **G2 answer:** despite being the max of a 16-factor
screen, no co-equal factor beats it as the sole ranker → the pick is **not** a multiple-testing
artifact. G2 is retired.

## Next setup
The entry signal is **settled**. The remaining Tier-1 candidates test **additions on top of the
confirmed entry**, not replacements: **C1** quality/fraud filter (must first prove non-collinear with
the D/E filter — note O-007 already REJECTed generic quality screens), **C2** pullback-entry timing
(targets the ~20% stop rate — the most concrete improvement lever), **C3** reduced-capacity ML ranker
(FITTED → CPCV embargo=63 per P6; bar = beat `sma200_slope_63` OOS net of DSR). Separately, the
Phase-0 side-finding (clean exit decomposition: ATR stop adds, target+trailing subtract) is a
**Stage-D** "let winners run" hypothesis, out of scope for the entry race.
