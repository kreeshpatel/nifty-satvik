# 0143 — The live book's losses are smaller in money and larger in R: the denominator

**Type:** MEASUREMENT — no trial, no screen row, nothing adopted.
**Standing counts:** screens 19 · sealed opens 2 · n_trials 2 (unchanged by this study).
**Date:** 2026-09-25 · **Plan:** Satvik Brain Phase 1, study B1.
**Spec:** [`diagnostics/research/stop_width/SPEC.md`](../../diagnostics/research/stop_width/SPEC.md),
committed before the code, with amendment A1 (after the red-team read).
**Record:** `diagnostics/research/stop_width/2026-09-25/{summary.json, trades.csv}`.
**Reproduce:** `python scripts/diag_stop_width.py --run-date 2026-09-25`.

## The question

The live book's 11 closed trades total **−17.18R**, which reads like a disaster. R is a ratio whose
denominator is the stop width, and the attribution ledger (PR #106) showed the live stops are unusually
tight. So: **is the book losing more money per trade than the research book, or the same money measured
in smaller units?**

## Populations

- **A — historical, live configuration**, prices 2019-01-01..2024-06-30 (the window stops before the
  sealed slice), the corporate-action hold off (0142 A1). 71 trades, **37 losses**.
- **B — the live book**, all 11 closed trades from `results/attribution_ledger.csv`. Every row is
  `provenance = reconstructed`: this is the live book's history rebuilt from the write-once archives,
  **not forward evidence**. Forward accrual starts with the next scan.

Stop width is taken on the **engine basis** — `return% / R`, the denominator R was actually measured
against — for both populations (A1.1; see *Defects* below).

## Result (losses)

| | historical (37) | live (11) | difference [95% CI] |
|---|---|---|---|
| median stop width | 8.85% | **3.76%** | **−2.58pp [−4.24, −0.83]** ✔ excludes 0 |
| median price move | −9.52% | **−6.19%** | **+3.72pp [+0.95, +6.55]** ✔ excludes 0 |
| median R | −1.24 | −1.46 | −0.14 [−0.68, +0.40] ✘ not established |

Differences are two-sample cluster bootstraps on ticker (2,000 draws), computed by the diagnostic —
not two intervals compared by eye.

Across **all** trades the same gap holds: median stop width 8.95% (A) against 3.76% (B).

**Arithmetic re-expression.** The live losses' *unchanged price moves* divided by A's median loss stop
width: **−17.18R becomes −8.74R**, median −1.46R becomes −0.70R. A unit conversion, **not** a
wider-stop simulation — 0106 measured widening and killed it (ΔSharpe −0.347).

## What it says

1. **The live book's stops are materially tighter** — about 2.6 percentage points at the mean, with a
   confidence interval that excludes zero. Its own signal weeks simply had closer lows; nothing in the
   rule changed. Note A's width is itself censored *upward*: 12 of its 37 losses sit exactly at the
   `max_risk_pct = 0.10` cap, so uncapped the gap would be wider still.
2. **The losses are smaller in money and no larger in R.** Price damage is 3.7 percentage points
   *better* on the live book, with the interval excluding zero; the R difference does not clear its own
   interval. Same or less money, measured in smaller units.
3. **Roughly half the −17.18R headline is the yardstick.** At the research book's denominator the same
   price moves are −8.74R.
4. **Nothing follows for the stop rule.** The axis is closed in both directions — 0105 tighten
   −0.477 Sharpe, 0106 widen −0.347, 0109 floor −0.071 — and `FINDING_hard_stop` showed capping each
   loss made portfolio risk *worse* (DD −34.8% → −55.4%), because 48% of stopped names recover above
   entry within 12 weeks. This finding is about the unit, not the rule.

## Withdrawn after the red-team read

- **The Oct-1 consequence.** An earlier draft said the review's promote/kill gate is written in
  expectancy R and so reads the wrong unit. **Wrong gate.** `>+0.10R` is `forward/prereg.md` §10
  v1.5(2), governing the **unactivated Path-B practitioner sleeve** (Engine B, 4×ATR chandelier stop).
  The live weekly-swing book's pre-committed rule is `forward/prereg_swing.md` §4 — forward **MaxDD and
  Calmar**, no R term — and 2026-10-01 is registered there as **a first read only**. The residual true
  statement: if the Path-B sleeve is ever activated, its R-denominated gate must be read with its own
  stop geometry attached (`FINDING_R_cap`).
- **"Gap-through rises as stops tighten."** The data says the opposite: A's gap-through rate by width
  band runs 0.33 (`<3%`) / 0.78 (`3–6%`) / 0.62 (`6–10%`) / 0.83 (at the cap). The supporting share
  gradient rested on a single trade (RNAVAL, −6.0R at 2.60% width). No statement is made in either
  direction.

## Defects found and fixed

- **The ledger mixed two sources for one ratio.** `stop` came from the archived card and `r_multiple`
  from the engine's history. For **3 of 11** closed trades the implied widths disagree by more than 5%
  — CCL's card says 1.52% where the engine measured 2.46%, HINDZINC 5.65% against 2.66%, 3MINDIA 2.23%
  against 3.04% — and entries disagree for 6 of 11. **The exhibit that motivated this study was wrong**:
  CCL's −2.18R was measured against 2.46%, not 1.52%. The ledger now carries both bases plus
  `width_gap_pct`, flags any gap over 5%, and this study uses the engine basis.
  `nq.brain.attribution.stop_agreement` could not have caught it: it compares stop *prices*, and CCL's
  prices agree to 0.97% while its denominator is off by 38%.
- **The `≥10%` band was not a band** — 12 A-losses pinned at the 10% risk cap, split across the edge by
  float noise. Capped trades are now their own cell.
- **The study compared two intervals by eye.** `cluster_bootstrap_two_sample` was added; every
  between-population statement now carries its own difference interval.

## Limits

- **n = 11.** With 11 trades on 11 distinct tickers the cluster bootstrap degenerates to an ordinary
  percentile bootstrap and is anti-conservative.
- **The live closed set is loss-only by construction** — its winners are still open at 12 weeks, while
  a 2R touch takes a median ~19 sessions. Checked: in A, tighter stops do resolve faster
  (Spearman +0.31), but restricting A's losses to those closed within 12 weeks leaves the median width
  unchanged at 8.85%, so the comparison of *losses* is not distorted.
- **Population B is a reconstruction**, not accrued forward evidence.
- The live window is **one** 12-week period. Across 41 overlapping 12-week windows in A no window
  median falls below 5.74%, but those windows are roughly 8–12 independent quarters and the live book
  is one of them.

## What it points to

"Our losses are terrible" is, in the measured part, **not true in money**: the losing trades fell less
than the research book's typically did. What changed is the yardstick. The open question from 0141 and
0142 — selection — is untouched by this, and the attribution ledger is now accruing the per-trade
context it needs.
