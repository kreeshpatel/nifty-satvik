# 0137 — Weekly bars + pivot family (SUPERSEDED HEADLINE — see §0)

## §0 CORRECTION (2026-08-06, same day) — the 19.28% was a bug artifact, RETRACTED

A pivot-alignment defect was found during the polish pass and fixed. `resample(freq).shift(1)
.reindex(idx, method="ffill")` **double-shifts**: period-END labels sort after the dates they should
govern, so the ffill reindex picks the previous label whose value is already shifted. The level in
force was **two periods stale** for the whole period (NaN for the first). Verified on a synthetic
quarter: Q3 dates received Q1's pivot instead of Q2's. Conservative — no lookahead — but not the
rule. Fixed by mapping each date to its own period and reading that period's shifted value
(`period_pivot` in `diag_swing_strategy_survey.py`, with the note inline).

**Everything in §2-§4 below was computed with the bug. Corrected results:**

| cell (FULL window) | buggy | **corrected** |
|---|---|---|
| monthly P | 13.23% / 0.778 | **15.77% / 0.850** |
| monthly R1 | 12.60% / 0.779 | **15.08% / 0.805** |
| quarterly P | 6.26% / 0.458 | 7.99% / 0.535 |
| **quarterly R1** | **19.28% / 1.129** | **9.15% / 0.546** |

**The headline claim — that weekly+quarterly-R1 clears passive ownership — is WITHDRAWN.** It was
the highest cell only because of the defect; corrected, it is the second-worst.

**What the corrected family says instead, and it is a better-behaved result:**

- **Period matters, level does not.** Monthly ≈ 15.1-15.8% regardless of P or R1; quarterly ≈
  8.0-9.2% regardless. The 13pp P-vs-R1 swing reported in §5(2) as evidence of a chaotic
  neighbourhood **was the bug**. After the fix the level axis is a plateau and the period axis
  carries a clean, consistent signal: **monthly > quarterly on both levels.**
- **The best cell is the original incumbent** — weekly bars + monthly central pivot:
  **15.77% CAGR / Sharpe 0.850 / MaxDD −27.0%**, vs equal-weight passive ~15.5% / 0.85-0.95 /
  −52.8 to −56.6%. That is passive's return and Sharpe at **roughly half the drawdown** — a genuine
  Law VII improvement, not alpha.
- **Family mean is still 12.00%**, below passive. The monthly sub-family averages 15.4%, level with it.

**Corrected weekly trend-filter family (FULL):** D daily 8.61%/0.544 · W1 EMA200w **13.78%/0.770** ·
W2 EMA40w 5.63%/0.379 · W3 daily-stop 12.04%/0.688. W2 fell 6pp and W1 rose 3.7pp from the same
correctness fix — the magnitude of that reshuffle is itself evidence that this book is dominated by
which trades get funded rather than by the signal.

## §0b SECOND DEFECT — the sub-window numbers are fresh-capital re-runs

W2's corrected FULL (5.63%) sits **below both** its TRAIN (23.36%) and HOLDOUT (7.31%), which is
only possible because TRAIN and HOLDOUT are independent re-runs each starting from a clean ₹10L and
an empty book. `program-laws` VIII forbids exactly this: *sub-period gates use a continuous slice of
one full run, never a fresh-capital re-run* — it resets the equity peak and reseasons the boundary,
and it has manufactured a false KILL in this programme before.

Every TRAIN/HOLDOUT figure in this session is the fresh-capital kind. Consequences:
- **Relative** comparisons survive — every cell got identical treatment, so the 0133 survey ranking
  and the random-control calibration still stand.
- **Absolute** sub-period claims do not. "Holdout +12.80%" and similar are re-run artifacts, not
  what the book would have done. **The FULL continuous column is the honest number throughout.**

Fixing the harness to slice one continuous run is queued as polish item 1b.

---

# (original text follows, computed with the pivot defect — retained for the record)

# 0137 — Weekly bars + quarterly R1: the first cell to clear passive, and why that isn't a promotion

**Date:** 2026-08-06 · **Class:** measurement (specification family). **`n_trials` unchanged 138.**
**Standing counts:** screens 19 · sealed opens 1 · n_trials 138.
**Verdict:** **NOT PROMOTABLE, route to forward evidence.** One cell (weekly signal, quarterly R1
pivot) beats the passive benchmark on the full window — the only thing all session to do so — but
the family it belongs to does not, adjacent specs differ by 13pp, and every window is spent.

---

## 1. What changed

Owner proposals, tested as families rather than single cells (0133 §4):

**(a) weekly bars instead of daily.** Signals on completed weekly bars; entry at the first daily
open after the week closes; stop/target then managed on **daily** bars (a weekly bar can contain
both stop and target, so any intrabar ordering rule would be fiction).

**(b) pivot timeframe/level.** From a TradingView Pivots panel: Traditional, **Quarterly**, "use
daily-based values". Priced as a 2×2: {monthly, quarterly} × {P, R1}, with quarterly H/L/C
aggregated from **daily** bars per the panel setting.

## 2. Weekly vs daily (trend-filter family)

| cell | TRAIN | HOLDOUT | FULL | trades | win | meanR | hold | stop |
|---|---|---|---|---|---|---|---|---|
| D daily reference | 14.42% / 0.882 | 4.18% / 0.313 | 9.69% / 0.624 | 996 | 40.6% | +0.20 | 13d | 6.9% |
| W1 EMA200w, weekly stop | 24.11% / 1.365 | 5.14% / 0.368 | 10.04% / 0.639 | 261 | 45.2% | +0.31 | 56d | 15.3% |
| W2 EMA40w, weekly stop | 23.71% / 1.256 | 6.50% / 0.429 | 11.65% / 0.690 | 271 | 45.0% | +0.31 | 56d | 15.8% |
| **W3 EMA40w, DAILY stop** | 24.02% / 1.353 | **−6.78% / −0.307** | 10.72% / 0.691 | **897** | 40.7% | +0.23 | 12d | 7.6% |

**Weekly does reduce whipsaw as hypothesised**: win 40.6%→45.0%, meanR +0.20→+0.31, hold 13d→56d,
4× fewer trades, holdout MaxDD −23.9%→−16.6%.

**W3 is the mechanism cell and it fails: the stop must match the signal's timeframe.** Same weekly
signals with a daily-width stop (7.6% vs 15.8%) blow the trade count from 271 to 897 and the
holdout to −6.78% — weekly-timeframe moves cannot survive daily-noise stops. This generalises
beyond this strategy.

## 3. Pivot timeframe × level

| cell | TRAIN | HOLDOUT | **FULL** | trades | win | meanR |
|---|---|---|---|---|---|---|
| monthly P (incumbent) | 24.16% / 1.314 | 3.15% / 0.262 | 13.23% / 0.778 | 289 | 45.7% | +0.34 |
| monthly R1 | 30.54% / 1.387 | −7.22% / −0.289 | 12.60% / 0.779 | 298 | 46.0% | +0.41 |
| **quarterly P — the literal proposal** | 13.67% / 0.840 | −2.95% / −0.068 | **6.26% / 0.458** | 287 | 43.2% | +0.24 |
| **quarterly R1** | 31.04% / 1.529 | **6.37% / 0.415** | **19.28% / 1.129** | 276 | **50.7%** | **+0.49** |

**The literal proposal (quarterly P) is the WORST of the four.** The best is quarterly **R1** — the
level the Ranade sources actually describe ("entry when the candle closes above the R1 level"),
which 0132 found *losing* on daily bars (−8.42% holdout). Quarterly R1 on weekly bars is a genuinely
different object: quarterly R1 sits far above the prior quarter's range, so a weekly close through
it is a structural breakout rather than a daily noise-cross.

## 4. Quarterly R1 against the binding gate

| | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| **weekly + quarterly R1** | **19.28%** | **1.129** | **−28.3%** |
| equal-weight passive (0136) | ~15.5% | 0.85-0.95 | −52.8 to −56.6% |
| NIFTY-50 buy-and-hold | 11.95% | 0.787 | −38.4% |
| baseline_v1 | 15.46% | 0.667 | −46.26% |

**This is the first configuration in the entire arc to clear passive ownership on every axis** —
higher CAGR, higher Sharpe, roughly half the drawdown.

## 5. Why it is still NOT promotable — four reasons, all pre-existing rules

1. **The family does not clear.** Per 0133 §4 the unit of evidence is the family of faithful
   readings, not the winning cell. Family mean on FULL: (13.23 + 12.60 + 6.26 + 19.28)/4 =
   **12.84%**, below passive's ~15.5%. One cell of four clears; three do not.
2. **Adjacent specs differ by 13pp.** Quarterly P returns 6.26% and quarterly R1 returns 19.28% —
   the same rule, one line different. A robust edge should not hinge on P versus R1. This is the
   chaotic-surface signature from 0133 §3(c), now on a different axis.
3. **Every window is spent.** Train and holdout went to the 0133 survey, 2016-18 to the deep dive,
   and both have since been re-read several times. The train→holdout drop here (31.04% → 6.37%) is
   the same drop the *daily reference* shows (14.42% → 4.18%), i.e. it is the window, not the spec.
4. **Multiplicity.** This is cell 4 of 4 in this family and roughly the 30th configuration of the
   session. Finding one that beats the benchmark is the expected outcome of that many looks.

## 6. What is genuinely banked

- **Weekly reduces whipsaw on this funnel** — win rate, meanR, hold length and drawdown all improve,
  consistently across all three weekly cells. This is a robust directional result, not one cell.
- **Stop width must match signal timeframe** (W3). Mechanical, and transferable.
- **The 10% notional cap binds on every trade**, so the "2% risk" parameter is inert: every position
  is 10% of equity and a −1R loss costs 10% × stop-width. Wider weekly stops therefore did *not*
  shrink positions (seats stayed ~9.4); they raised money-risk per trade from ~0.69% to ~1.54%.
  Weekly is the higher-risk configuration in rupee terms, and part of its higher meanR is
  compensation for that rather than free improvement.

## 7. Next setup

Quarterly-R1-on-weekly is the only candidate this arc has produced that clears the passive gate. It
cannot be certified on this data. The correct destination is the **forward wall**
(`forward/prereg.md`) as a WATCHED book — hash-chained, logged daily, decided at a quarterly review.
That costs nothing but time and is the only instrument left that can produce unbiased evidence.

Any in-sample refinement of it — different R-level, different pivot period, different stop multiple —
is refused: §5(2) shows the neighbourhood is noise, and §5(4) shows the multiplicity is already
spent.

## 8. Reproduction

`scripts/diag_ranade_weekly.py` (trend-filter family) · `scripts/diag_ranade_pivot_tf.py`
(pivot timeframe × level family).
