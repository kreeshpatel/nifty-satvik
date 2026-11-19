# Blend gross-to-net decomposition: where the 70/30 blend's return goes between gross and after-tax

**Class:** MEASUREMENT. No rule tested, no trial, no sealed read, no live change.

**Standing counts:** screens 24 · sealed opens 4 · n_trials 3 (unchanged).

**Goal link.** The blend loses 7.6pp a year between gross and after-tax, against 2.5pp for the static 65/35
fallback. Knowing which part of that loss is signal and which is implementation decides whether any
implementation-only fix could close the gap to the fallback.

**Reproduce:**

```
python pipelines/diagnostics/explore_blend_cost_tax.py
```

It writes `diagnostics/research/explore/2026-11-19_blend_cost_tax.json`. The output is byte-identical under
PYTHONHASHSEED 0 and 7. Step 0 and the anchor decision are in `2026-11-19_blend_cost_tax_step0.md`.

## Method (stated before results)

**Simulator.** The lot-level engine of `explore_after_tax_comparison.py`, imported unchanged.
`explore_blend_cost_tax.py:91` subclasses `AT.Book` for logging only. The tax and cost arithmetic stay AT's:
- settle: `explore_after_tax_comparison.py:160`
- sell: `:124`
- pass-through: `:148`

**Window and universe.** 2019-03-05..2024-06-28, ₹20,00,000, FY 2026-27 rates applied throughout:
- STCG 20%
- LTCG 12.5% above ₹1.25L
- liquid fund at a 30% slab (assumed)

Two books feed the blend:
- 0001 run of record, 1,952 trades exiting in the window
- live swing book, 66 trades exiting in the window; 10 still open at the cut are excluded from pass-through

**Anchors.** Every committed value reproduced:

| anchor | value |
|---|---|
| blend after-tax CAGR / p95 drawdown | 19.26 / 26.46 |
| static 65/35 after-tax CAGR / p95 drawdown | 23.02 / 24.81 |
| wrapper trading costs | 1.59pp (1.58 in the committed JSON; rounding of the unrounded difference) |
| tax | 4.54pp |
| 0001 full run | 21.73% / 1.130 |
| inline swing replay terminal NAV vs cached | gap 0.0 |

**Formulas.**

*CAGR* = liquidation value ^ (365.25 / days) − 1 (`explore_blend_cost_tax.py:299`).

*Holding days* = calendar days from entry to exit. A pass-through uses the book trade's own dates; a unit sale uses
the age of the unit lot.

*Class:* more than 365 days is long-term, which is AT's rule. The 5 exits at exactly 365 days are short-term and are
counted inside the "365+" bucket.

*Tax per bucket.* Each tax period's ST tax (or LT tax) is allocated across that period's buckets in proportion to
each bucket's positive net gain. This is a convention, and bucket tax is not unique; the class totals are exact. The
event-log recomputation of every period's tax equals the simulator's `tax_paid` to the rupee:

| book | tax |
|---|---|
| blend | ₹7,82,900 |
| 0001 alone | ₹17,28,891 |
| swing alone | ₹3,91,253 |

*Step 2 size* = |instrument-day trade value| / NAV before trading. The first-close purchase and the terminal
liquidation are excluded: 3,660 trades, ₹2,31,580 of the run's ₹2,40,115 cost.

*Step 3 order* = gross → engine costs → expense ratios → wrapper trading costs → tax. Each step is a separate full run.
Gross books are the engines re-run with their costs off: 0001 with `cost_mult=0`, swing with `cost_off=True`. The
exposure series e_t is always the one computed from the net books.

*Step 4 turnover* = sell notional in the window / mean NAV / years. For 0001, sell notional is qty × exit for each
trade row. For swing, it is the daily share decreases in the position log × mark price.

**Dependence.** One path, one window. Exits overlap in time and share tax periods, so set-off makes bucket tax depend
on the other buckets in the same period. No sampling inference is drawn.

## Step 3 — waterfall (pp of CAGR) [measured]

| book | gross | − engine costs | − expense ratios | − wrapper trading | − tax | = after-tax |
|---|---|---|---|---|---|---|
| blend 70/30 at 11% | 26.89 | 1.45 | 0.05 | 1.59 | 4.54 | **19.26** |
| 0001 alone | 45.59 | 2.83 | 0.00 | 0.05 | 6.78 | **35.92** |
| swing alone | 21.79 | 1.07 | 0.00 | 0.05 | 1.86 | **18.82** |
| static 65/35 | 25.55 | 0.00 | 0.31 | 0.00 | 2.22 | **23.02** |
| index fund at 11% | 25.80 | 0.00 | 0.32 | 0.04 | 5.04 | **20.41** |

How to read the table:
- The blend starts with the **highest gross return of the three fallback books**: 26.89, against 25.55 for 65/35 and
  25.80 for the index fund. It loses 7.63pp on the way to after-tax; 65/35 loses 2.53pp.
- 0001's in-window 43.1% NAV CAGR is a property of this window. Its full 2017–2026 run is 21.73%, with 2017–19 at
  −6.1% and 2024–26 at +4.8% [measured].
- For the standalone books, "wrapper" is only the tax-funding and terminal sales.

## Step 1 — tax by source [measured, `step1_tax_by_source`]

**Blend at 11%.** Total tax ₹7,82,900.

| source | short-term gain | short-term tax | long-term gain | long-term tax | share of tax |
|---|---|---|---|---|---|
| sleeve trades (pass-through) | ₹24,58,788 | ₹4,04,665 | ₹6,21,046 | ₹20,137 | 54.3% |
| wrapper unit sales (exposure moves, 70/30 rebalance, tax funding) | ₹6,18,686 | ₹2,53,738 | — | — | 32.4% |
| terminal liquidation | ₹1,00,164 | ₹12,237 | — | — | 1.6% |
| liquid fund (slab 30%) | ₹3,07,078 gain | ₹92,123 | — | — | 11.8% |

**Blend, by holding days.**

| days | sleeve-trade exits | gain | tax | wrapper-sale exits | gain | tax |
|---|---|---|---|---|---|---|
| 0-30 | 389 | ₹48,163 | ₹24,451 | 91 (+13 terminal) | −₹80,114 (+₹3,023) | ₹216 (+₹609) |
| 31-90 | 677 | ₹3,43,538 | ₹57,413 | 1,537 (+21 terminal) | ₹1,66,154 (+₹97,141) | ₹1,38,186 (+₹11,628) |
| 91-180 | 550 | ₹8,50,795 | ₹1,43,959 | 756 | ₹95,966 | ₹33,535 |
| 181-330 | 302 | ₹9,84,666 | ₹1,48,552 | 208 | ₹4,36,680 | ₹81,801 |
| 331-364 | 30 | ₹1,54,795 | ₹18,778 | 0 | — | — |
| 365+ (5 short-term at exactly 365) | 70 | ₹6,97,877 | ₹31,649 | 0 | — | — |

A bucket's tax can exceed 20% of its window-total gain. The 0-30 sleeve row and the 31-90 wrapper row both do this:
each is positive in high-tax periods and negative in others, and losses only reduce tax within their own period
(allocation convention, above).

**0001 alone.** Total tax ₹17,28,891.
- Short-term: 1,896 exits, ₹74.96L gain, ₹14.99L tax.
- Long-term: 63 exits, ₹24.82L gain, ₹2.30L tax. Of that, the terminal liquidation is ₹15.40L gain and ₹1.77L tax.
- 331-364 days: 28 exits, ₹2.54L gain.

**Swing alone.** Total tax ₹3,91,253.
- Short-term trades net −₹10.44L.
  - 0-180 days: −₹21.1L.
  - 181-364 days: +₹10.65L.
- Long-term: ₹44.49L gain.
  - Trades of 365+ days: ₹22.49L.
  - Terminal liquidation of the 10 open positions: ₹21.62L, ₹2.55L tax.

**331-364 ceiling.** This is arithmetic on existing P&L, **not an achievable saving**. Holding 1–34 more days changes
the P&L, and stops are requests: a stopped trade cannot be held. Each figure is the tax saved if the same gains had
been long-term, with every period recomputed including set-off:

| book | exits | gain | ceiling saving |
|---|---|---|---|
| blend | 30 | ₹1,54,795 | ₹15,229 (≈ 1.9% of the blend's tax) |
| 0001 alone | 28 | — | ₹31,861 |
| swing alone | 2 | — | ₹0 (absorbed by carried-forward short-term losses) |

## Step 2 — daily rebalance cost by trade size [measured, `step2_rebalance_cost_by_size`]

**Trade size**, % of NAV: p10 0.05 · p50 0.43 · p90 4.15 · p99 17.85.

| trade size (% NAV) | trades | share of cost | share of turnover |
|---|---|---|---|
| < 0.5% | 1,937 | 8.5% | 5.6% |
| 0.5–1% | 505 | 8.1% | 5.9% |
| 1–2% | 482 | 13.0% | 11.0% |
| > 2% | 736 | **70.4%** | **77.4%** |

**Cost by instrument:**
- MOM ₹1,58,644
- SW ₹69,714
- liquid ₹3,221

**Hypothetical no-trade bands.** This is cost only, not a rule test. Drift that would accumulate under a real band is
not simulated, so each "cost of trades below" figure is an upper bound on what a band saves:

| band | trades below | cost of those trades | share of cost | gap left, p50 / p90 / p99 / max (% NAV) |
|---|---|---|---|---|
| 0.5% | 1,937 | ₹19,697 | 8.5% | 0.14 / 0.37 / 0.48 / 0.50 |
| 1% | 2,442 | ₹38,493 | 16.6% | 0.20 / 0.70 / 0.96 / 1.00 |
| 2% | 2,924 | ₹68,635 | 29.6% | 0.27 / 1.28 / 1.92 / 1.99 |

The cost is in the large trades. These are mostly exposure moves of the vol target [inferred from size: a 70/30
drift between two sleeves rarely reaches 2% of NAV in a day]. Even a 2% band reaches at most 30% of the cost.

## Step 4 — by sleeve [measured, `step4_by_sleeve`]

| sleeve | trades | mean / median holding days | one-way turnover a year | pre-tax CAGR | after-tax CAGR | after/pre ratio |
|---|---|---|---|---|---|---|
| 0001 | 1,952 | 112.1 / 83 | 3.89× | 42.70 | 35.92 | 0.841 |
| swing | 66 | 164.6 / 98.5 | 2.43× | 20.68 | 18.82 | 0.910 |

## Step 5 — independent re-derivation

A fresh `blind-replica` agent worked from a written spec and three exported input files only: the daily sleeve NAVs
and exposure, the 0001 trades and the swing ledger. It had no code. Spec, code and result:
`diagnostics/research/explore/2026-11-19_blend_cost_tax_replica/`.

| quantity | replica | pipeline | relative gap |
|---|---|---|---|
| blend after-tax / pre-tax / no-cost CAGR | 19.26 / 23.80 / 25.38 | 19.26 / 23.80 / 25.38 | 0 |
| total tax | ₹7,82,900 | ₹7,82,900 | 0 |
| short-term class: count / gain / tax | 4,579 / ₹31,77,637 / ₹6,70,639 | identical | 0 |
| long-term class: count / gain / tax | 65 / ₹6,21,046 / ₹20,137 | identical | 0 |
| liquid (slab): gain / tax | ₹3,07,078 / ₹92,123 | identical | 0 |
| liquid (slab): exit count | 1,019 | 1,024 | 0.5% |
| every source × bucket count and gain (15 rows) | identical | identical | 0 |
| 331-364 ceiling | ₹15,229 | ₹15,229 | 0 |
| Step 2: n, total cost, p10/p50/p90/p99 | 3,660 · ₹2,31,580 · 0.048/0.431/4.149/17.853 | identical | 0 |
| Step 2: cost shares < 0.5 / 0.5–1 / 1–2 / > 2% | 8.51 / 8.12 / 13.02 / 70.36 | identical | 0 |
| Step 2: band costs, 0.5 / 1 / 2% | ₹19,697 / ₹38,493 / ₹68,635 | identical | 0 |

No difference is over 5% relative. The 5 extra liquid "exits" in the pipeline come from logging zero-unit lot touches
[inferred]. They carry no gain.

**Diagnostic: where the old replica's 19.52% comes from.** It does not block this study. Each variant changes one
thing in the replica's own simulator:

| variant | after-tax CAGR change |
|---|---|
| pass-through booked the next session | −0.003pp |
| tax on 1 April | +0.012pp |
| same-day gains into the current period | +0.034pp |
| no cost on tax-day trades | +0.008pp |
| LIFO | +0.42pp |
| long-term threshold ≥ 365 days | +0.06pp |
| **costs counted in the tax basis** (buy cost added to basis, sell cost netted from proceeds) | **+0.258pp → 19.51%** |

Only the last variant reproduces 19.52%. Its two legs contribute +0.13pp each. **The component is costs:** whether
transaction costs reduce taxable gains. The pipeline taxes gross price gains. Indian rules allow transfer expenses,
such as brokerage, to be deducted, but not STT [assumed; confirm with a CA]. So the true figure likely sits between
19.26% and 19.51% [inferred]. This closes the open reconciliation item in the Step 0 note as **explained**.

The replica's own caveat: its 19.26% match depends on reading the spec's "cost per unit" as the price excluding
costs. That is a reading of the spec, not something the spec settles. The match therefore confirms the arithmetic, not
the choice of cost treatment.

## Biggest sources of the blend's gross-to-after-tax gap

The blend loses 7.63pp in total. The tax pp in this table are split by rupee share [inferred, proportional].

| # | source | pp a year | changes a signal? |
|---|---|---|---|
| 1 | wrapper layer: daily vol-target / 70-30 re-trading costs (1.59 [measured]) plus STCG on wrapper unit sales (≈ 1.53 = 34% × 4.54) | **≈ 3.1** | no: implementation of exposure, not the signals; 70% of its cost is trades over 2% of NAV |
| 2 | STCG on the sleeves' own trades | **≈ 2.4** (52% × 4.54) | yes: holding periods are set by the signals and stops; 331-364 ceiling only ₹15k |
| 3 | engine costs inside the books | **1.45** [measured] | no, as execution (slippage assumptions), but the trade count is signal-driven |
| — | slab tax on the liquid fund | ≈ 0.53 (12% × 4.54) | no: cash-leg instrument choice |
| — | costs not deducted from gains (Step 5) | up to +0.26 back | no: tax-treatment assumption |

## Owner decisions

1. **Whether to test an exposure-implementation change for the blend**, such as a rebalance band or a smoothed or
   stepped exposure.
   - Evidence for: the wrapper layer is the largest addressable source (≈ 3.1pp).
   - Evidence against: a band alone reaches at most 8.5–30% of wrapper cost (₹20k–₹69k of ₹2.3L, upper bounds), and
     the cost sits in large exposure moves. Changing those is a rule change, and it needs a pre-registered trial
     (n_trials 3 → 4).
   - Options: (a) pre-register; (b) do not, and keep the static 65/35 fallback ranking. Even with zero wrapper costs
     and zero wrapper tax, the blend's ≈ 22.4% stays under 65/35's 23.02% [inferred: 19.26 + 1.59 + 1.53].
2. **The cash-leg instrument** (liquid fund vs arbitrage fund). Slab tax is ≈ 0.53pp; the trade-off is in #212/#214.
3. **The tax treatment of transaction costs in the simulators.** Currently costs are not deducted from gains.
   Deducting them is worth +0.26pp on the blend.
   - Options: (a) keep the conservative treatment; (b) after CA confirmation, re-run the after-tax comparison with
     brokerage deducted and STT not deducted. That is a re-anchor of the after-tax figures, not a rule change.

## Artifact check

1. **Waterfall order.** Tax is taken last, on a base that is already net of costs, so a different order would split
   the gap differently.
   - Bounded. Tax on the no-wrapper-cost base is 4.56pp against 4.54pp [measured, Step 0 note].
2. **Pass-through approximation** (from AT's own doc). These items favour the blend.
   - A 0001 top-up keeps its first entry date, which lengthens holding days and understates short-term gains.
   - Swing half-exits are booked at the final exit date.
   - Gains accrued before 2019 are taxed at exit, then offset at the final sale.
   - Not ruled out. Direction: tax understated [assumed from the doc; not measured here].
3. **Terminal liquidation taxed by unit-lot age.** In the standalone books, open positions at the cut are taxed as
   long-term because the unit lots are old.
   - For swing, 34% of the open gain (₹3.90L of ₹11.52L at book scale) sits in positions held 365 days or less
     [measured].
   - The standalone swing tax is therefore understated by roughly ₹55k [inferred: about 1.9 units × ₹3.9L ×
     (20% − 12.5%)].
   - The blend's terminal lots are short-term already, so the blend is not affected.
4. **Bucket tax allocation is a convention.** The class totals are exact; the per-bucket tax is not unique.
   - Ruled out for totals: the recomputation equals the simulator to the rupee. Not ruled out for buckets.
5. **Band costs are static.** No drift accumulation and no re-simulation.
   - The band figures are upper bounds on savings, labelled as such.
6. **Gross books are re-runs with costs off, not the net book plus costs paid.** Equity-based sizing changes the
   trades slightly.
   - Engine costs are therefore "the book without costs" [measured: 0001 full run 23.85% gross vs 21.73% net].
7. **Single path, strong window.** 0001 made 43% a year in-window against 21.7% over its full run. Tax drag scales
   with realised gains, so the absolute pp are window-specific.
   - Not ruled out.
8. **The 30% slab on the liquid fund is assumed.**
   - Not ruled out. It drives the ₹92k liquid row.

## Scope

**Added after first look:**
- The split of terminal-liquidation unit sales from in-run unit sales. Reason: the standalone books' terminal rows
  dominated their long-term tax.
- The check of the swing book's open positions at the cut (artifact 3).

Neither is a new horizon or setting, and no rule was evaluated.
