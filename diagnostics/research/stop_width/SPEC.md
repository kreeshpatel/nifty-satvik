# Stop width and the R denominator — SPEC (written before any result)

**Class:** MEASUREMENT. No trial, no screen row, nothing adopted.
Standing counts at writing, read from the ledgers: **screens 19 · sealed opens 2 · n_trials 2.**
**Plan:** Satvik Brain Phase 1, study B1.
**Written:** 2026-09-25, committed before the diagnostic exists. Definitions and interpretation rules
are fixed now and are not revisited after the numbers come in.

## The question

The live book's 11 closed trades total **−17.18R**, which reads like a disaster. But the attribution
ledger (PR #106) shows the stops are unusually tight: median **5.6%**, minimum **1.52%**. CCL fell 5.4%
and that was **−2.18R**; LINDEINDIA fell 4.5% for **−2.32R**.

**R is a ratio, and its denominator is the stop width.** So:

> Is the live book losing more money per trade than the research book — or the same money, measured in
> smaller units?

This matters beyond bookkeeping: the Oct-1 review's promote/kill gate is written in **expectancy R**
(`>+0.10R`), and `FINDING_R_cap` already established that **R-multiples are not comparable across stop
geometries** (a 5% stop "sits inside the 7.83% median weekly ATR — it harvests noise, not information").
If the live book's R is measured against a systematically smaller denominator, the gate is reading a
different unit from the one its threshold was set in.

## Prior art — cited, not repeated

- **`FINDING_R_cap`**: capping risk at 5% raised mean R (+0.616 → +0.846) while *lowering* Sharpe
  (1.03 → 0.67) and CAGR (21.2% → 12.6%) — R went up as the book got worse. The mechanism this study
  measures, already named.
- **0106 widen the stop: KILL** (ΔSharpe −0.347). **0105 tighten: KILL** (−0.477). **0109 disaster
  floor: KILL** (−0.071). **This study does not propose moving the stop in either direction** and
  nothing in it may be read as re-opening that axis.
- **0130**: median stop width 13.10% on the actual risk-parity book; the sizer's bias toward wider
  stops is a **saving**, not a leak.
- **`DEFINITIONS_REGISTER §2`**: "median R" in older notes meant stop WIDTH, not an R-multiple.

## Populations

- **A — historical, live configuration**: the same reconstruction as finding 0142 — live dicts on
  `corrected_universe()`, **2019-01-01..2024-06-30** (the window stops before the sealed slice), the
  corporate-action hold OFF (0142 amendment A1). Stop width per trade = `(entry − stop0) / entry`.
- **B — the live forward book**: `results/attribution_ledger.csv`, all closed trades since inception
  2026-07-04. n = 11: **below every informative bar**, reported with CIs and flagged.

## Measures (fixed)

1. **Stop-width distribution** per population: n, median, IQR, min, max — all trades, and losses only.
2. **The same loss in three units**, per population, losses only: median **R**, median **price move %**,
   and median **stop width %**. The identity being tested is `R ≈ return% / stop_width%`.
3. **Beyond-stop share by stop-width band** (`<3%`, `3–6%`, `6–10%`, `≥10%`): what fraction of the
   loss R is fill past the stop rather than the designed −1R.
4. **Re-expression (arithmetic, not a proposal):** the live losses restated at population A's median
   stop width. This is a unit conversion to show how much of the −17.18R is denominator. **It is not a
   simulation of a wider stop and must never be quoted as one** — 0106 measured that and killed it.

## Uncertainty

Cluster bootstrap on ticker (`nq.brain.portfolio.cluster_bootstrap_mean`), 2,000 draws, seed 20260925.
A cell below **30 trades** is flagged *uninformative*; the live book is such a cell by construction.

## Interpretation rules (fixed before the numbers)

1. **Live median price damage ≈ historical, but live median R materially larger:** the losses are the
   same size in money and larger only in R. The finding is then about the **unit**, and its consequence
   is that the Oct-1 expectancy-R gate must be read with stop width attached.
2. **Live median price damage also materially worse:** genuine deterioration — a selection or regime
   finding, and the R story is secondary.
3. **Neither, or the CIs swamp it:** report as uninformative and carry it to the next review. With
   n = 11 this is the most likely outcome and is a complete result.
4. **Gap-through rising as stop width falls** is mechanically expected; it is reported, and no rule
   follows from it (0105/0106/0109 are closed).

**Whatever the result, nothing is adopted.** No stop change, no sizing change, no gate change: the gate
is `forward/prereg.md` §10.2 and only the quarterly review may touch it.
