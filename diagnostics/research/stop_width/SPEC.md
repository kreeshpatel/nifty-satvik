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

---

## Amendment A1 — 2026-09-25, after the red-team read

The read reproduced population A end to end from the committed pipeline (n=71, 37 losses, median width
8.948% — exact match), re-derived every band cell by hand, and verified the golden master byte-identical.
It then overturned two claims, corrected the motivating exhibit, and found a defect in the ledger this
study reads. All of it is folded in here **before** the finding is written.

**A1.1 — the live book's stop width must be taken on the ENGINE basis, not the card.** The attribution
ledger joins `stop` from the archived card and `r_multiple` from the engine's history. They are
different objects: for **3 of 11** closed trades the implied widths disagree by more than 5%
(CCL card 1.52% against an engine basis of 2.46%; HINDZINC 5.65% against 2.66%; 3MINDIA 2.23% against
3.04%), and the entries disagree for 6 of 11. `stop_agreement` compares stop PRICES and is too blunt
here — CCL's prices agree to 0.97% while its denominator is off by 38%.
**Consequence: the SPEC's motivating exhibit was wrong.** CCL's −2.18R was measured against 2.46%, not
1.52%. The ledger now carries `stop_width_pct_card`, `stop_width_pct_engine`, `width_gap_pct` and
`stop_width_basis`, flags any gap above 5%, and this study uses the engine basis for both populations.

**A1.2 — the study must compute the DIFFERENCE, not compare two intervals by eye.** Overlapping
intervals are not a null result. `nq.brain.portfolio.cluster_bootstrap_two_sample` is added and every
between-population statement now carries its own difference interval.

**A1.3 — the `≥10%` band is not a band.** 12 of A's 37 losses sit at 9.989–10.004%, pinned by
`max_risk_pct = 0.10` and split across the 10% edge by float noise. The capped trades are now reported
as their own cell (`at the 10% cap`) and the remaining bands cover genuinely uncapped widths.

**A1.4 — WITHDRAWN: the Oct-1 consequence.** The `>+0.10R` expectancy bar is `forward/prereg.md` §10
v1.5(2) and governs the **unactivated Path-B practitioner sleeve** (Engine B, 4×ATR chandelier stop).
The live weekly-swing book's pre-committed rule is `forward/prereg_swing.md` §4 — forward **MaxDD and
Calmar**, no R term — and 2026-10-01 is registered there as **a first read only**. The residual, true
statement: *if* the Path-B sleeve is ever activated, its R-denominated gate must be read with its own
stop geometry attached. This study touches neither book that gate compares.

**A1.5 — WITHDRAWN: "gap-through rises as stops tighten."** A's gap-through rate by band runs
0.33 / 0.78 / 0.65 / 1.00 — the tightest band is the *lowest* and the widest the *highest*, the opposite
of the claim. The beyond-stop share gradient rests on one trade (RNAVAL, −6.0R at 2.60% width); without
it A's `<3%` cell is n=2 and its share collapses to about zero. Interpretation rule 4 is struck: no
statement is made about gap-through and stop width in either direction.

**A1.6 — population B is a second reconstruction, not forward evidence.** All 46 ledger rows are
`provenance = reconstructed` (the earliest archive is 2026-07-24, and 9 of the 11 closed trades were
first seen there). The SPEC called B "the live forward book"; it is the live book's history rebuilt from
archives. Forward accrual starts with the next scan.

**A1.7 — the live cluster bootstrap is not a cluster correction.** 11 trades on 11 distinct tickers
makes it an ordinary percentile bootstrap at n=11, which is anti-conservative. Stated wherever a live
interval is quoted.
