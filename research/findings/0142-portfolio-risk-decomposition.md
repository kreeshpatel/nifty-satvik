# 0142 — How much of the book is the market? Beta, correlation and effective bets

**Type:** MEASUREMENT — no trial, no screen row, nothing adopted.
**Standing counts:** screens 19 · sealed opens 2 · n_trials 2 (unchanged by this study).
**Date:** 2026-09-24 · **Plan:** Satvik Brain, Phase 1 / Track P1.
**Spec:** [`diagnostics/research/portfolio_risk/SPEC.md`](../../diagnostics/research/portfolio_risk/SPEC.md),
committed before the code, with amendments A1 (the corporate-action hold is live-only) and A2 (after the
red-team read).
**Record:** `diagnostics/research/portfolio_risk/2026-09-24/{summary.json, daily.csv.gz}`.
**Reproduce:** `python scripts/diag_portfolio_risk.py --live-end 2026-09-23 --run-date 2026-09-24`.

## The question

Owner observation 2: "the Nifty has been in a big downtrend and we have been in stocks that made our
portfolio worse." Finding 0141 sharpened it — the book's +2R hit rate matches same-day stocks of similar
volatility, so the market sets the outcome more than selection does. How much of this book *is* the
market, and is its diversification real?

## Populations

- **A — historical, live configuration** on prices 2019-01-01..2024-06-30 (the window stops before the
  sealed slice). 71 trades, 1,352 sessions, mean 7.3 seats.
- **B — the live forward book**, NAV 2026-07-07..2026-09-15, 50 sessions, 11 weekly snapshots. Below
  every informative bar; reported, not interpreted.

## Result

| | sessions | mean seats | avg pairwise corr | effective bets | beta | R² | book/day |
|---|---|---|---|---|---|---|---|
| calm | 1,115 | 7.35 | 0.148 | 4.09 | 0.698 | 0.249 | **+0.166%** |
| index ≥10% off high (all) | 171 | 7.06 | 0.259 | 3.06 | 0.704 | 0.675 | −0.008% |
| — COVID, 2020-03-06..07-20 | 90 | 7.54 | **0.348** | 2.65 | 0.682 | 0.707 | **+0.118%** |
| — 2022-05-31..07-21 | 38 | 5.53 | 0.120 | 3.59 | 0.648 | 0.407 | −0.005% |
| **drawdowns excluding COVID** | 81 | 6.52 | **0.160** | 3.52 | 0.817 | 0.583 | **−0.149%** |

Whole window: beta **0.702**, block-bootstrap CI [0.590, 0.771], R² 0.367. Beta on the held names
themselves is 0.771, implying the book is about 91% invested on average; the rest is cash drag.

Exit families (cluster-bootstrapped on ticker):

| exit | n | mean R | 95% CI | median | skew | total R |
|---|---|---|---|---|---|---|
| 44-week-SMA runner | 37 | **+4.82** | [+2.41, +7.98] | +2.28 | +2.62 | **+178.2R** |
| stop | 29 | −1.62 | [−2.11, −1.27] | −1.29 | −3.02 | −47.0R |
| stop_part | 4 | −0.24 | [−1.62, +0.99] | −0.08 | −0.36 | −0.9R |
| stale | 1 | +2.04 | — | — | — | +2.0R |

## What it says

1. **The book carries about 0.70 of the index, and depends on it far more when the index falls.**
   The index explains a quarter of daily variance in calm markets and **58–68%** in drawdowns. Beta is
   significantly below 1, so this is not a closet index fund — but in a falling market most of what
   happens to the book is the market. That is the measured half of owner observation 2.
   **Limit:** the drawdown side rests on **two episodes** (2020, 2022). Two episodes is not a sample.
2. **Diversification does NOT thin when it matters — the first read of that was one crash.**
   Average correlation rises to 0.348 in COVID, but drawdowns excluding COVID sit at **0.160 against
   0.148 in calm**: indistinguishable. The fall in effective bets (4.09 → 3.52) is then mostly the book
   holding **fewer names** (7.35 → 6.52), because `N_eff` scales with the seat count, not evidence that
   the names moved together. **No regime claim is made on correlation.**
3. **About 7 seats have always behaved like 4 bets.** Average correlation 0.148 and a diversification
   ratio of 1.96 are *structural*, not regime-driven. Per `FINDING_more_slots` (4–5 seats Sharpe 1.21
   against 10 seats 0.81) this is **not** a defect and **not** an argument for more names.
4. **R lives in one exit family.** The 44-week-SMA runner produced **+178.2R across 37 exits**, mean
   +4.82R with a CI that clears zero comfortably, right-skewed. Everything else is a cost. This is a
   description of where R comes from, not a licence to retune an exit (that is a live rule change).
5. **The stop family is below the study's own bar and is not interpreted.** n = 29 against a
   pre-registered floor of 30. Its −1.62R mean is reported; two trades (RNAVAL −6.0R, JSL −5.4R) carry
   it, the median is −1.29R, and gap-through beyond −1R is structural for a weekly-close stop filled at
   the next open. **The study makes no statement about whether stops fire on volatility expansion** —
   that cell (n = 29) is under the same bar.
6. **The live book cannot be read yet.** 50 sessions: beta 0.708 with a standard error of 0.22 (its
   interval contains 1.0) and alpha t = 0.29. Nothing can be concluded about whether it lost more or
   less than its beta implied. Three of six names carry 76% of current book variance (MCX 31%,
   IndusInd 23%, Cholafin 22%).

**Where this leaves the programme:** the market-exposure half of owner observation 2 is real and
measured; the "our stocks made it worse" half is not established. Combined with 0141 — entries reach
their target about as often as matched random stocks — the open question is **selection**, and the next
Phase-1 items (attribution ledger, the Saturday post-mortem) are where it gets measured.

**Nothing here authorises a de-gross, a hedge or a seat-count change.** The one de-gross measured on
this book inverted (0095, ΔSharpe −0.398).

## What the reconstruction is, and is not

- The book's CAGR 39.4% / Sharpe 1.666 / DD −34.8% are a **fresh-capital sub-window run**, not gate
  numbers: the equity peak resets at 2019-01-01, and CLAUDE.md requires sub-period gates to be a
  continuous slice of one full run.
- On the same window frozen-0094 defaults give 30.3% / 1.225. The lift decomposes as A-only 33.0/1.318
  → discipline caps 24.0/1.153 → **config-P runner exit 39.4/1.666**. It is the owner-adopted fat-tail
  exit, not a new variant, so the "beats 1.13 in-sample is a defect signal" anchor does not bite.
- The corporate-action hold (Phase 0) is **off** in the reconstruction. With it on, four positions froze
  permanently on circuit-limit crash days and the book read 52.8% CAGR. They were **winners** the runner
  could no longer sell (VBL, JSL, IIFL, SWANENERGY) — the guard is live-only, where a human resolves it
  within a day. Its measured firing rate is ~0.7/year on a 5–7 seat book.

## Corrections this study made to itself

Found by the `red-team` read, all fixed before this finding:
- the regime claim was one episode (A2.1) — episodes are now reported separately and no claim may rest
  on the largest one;
- `share_of_total_R` inverted sign on a losing book: the live stop family, −16.3R, printed **+94.5%**
  of R (A2.2). The share is now undefined when total R is not positive;
- trade cells shipped without the cluster-bootstrap CI the SPEC promised (A2.3);
- the live window was labelled by the price fetch (2026-09-23) rather than the NAV (2026-09-15) (A2.4);
- A1's stated mechanism was wrong — the hold inflated by freezing winners, not by hiding losses (A2.5).

## Limits

- Population A is the research engine's capped book on a survivorship-corrected universe, reconstructed
  from prices; it is not the live book's realised history.
- Correlations are equal-weight for population A. Measured against actual weights the diversification
  ratio is 1.84 against 1.92, correlation 0.93 — the notional cap binds on every entry, so equal weight
  is close.
- Sector concentration is **DATA-BLOCKED**: no committed point-in-time ticker→sector map. Correlation
  clustering is reported instead.
- Two drawdown episodes, 11 live snapshots, 50 live sessions. Most cells here are descriptions with
  their n attached, not evidence.
