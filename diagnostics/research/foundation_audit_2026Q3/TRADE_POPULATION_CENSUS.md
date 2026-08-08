# Trade-population census — what one signal actually pays

**Date:** 2026-08-06 · **Class: MEASUREMENT.** Zero trials, zero screens, no rule proposed, no
hypothesis generated. **Counts frozen: screens 15 · sealed opens 1 · n_trials 138.**
Fishing guard applies: anything noticed and not asked for is stated and parked, never analysed.

**Deliverable status: binder input.**

> **The framing, stated first because it governs how every number below should be read.** The
> signal-level statistics in §1 rest on **6,245 observations**. The portfolio figure the programme
> quotes — Sharpe 1.132 — rests on **255**, and those 255 are **one path** through the population,
> selected by a cash machine. Where the two disagree, the population is the more robust evidence,
> and §2 shows the selection is not neutral.

Producer: `scripts/diag_trade_population_census.py` · evidence:
`trade_population_census.json`, `trade_population.parquet`.

---

## 0. Which population — two wrong answers rejected first

**Not the substrate.** `research/substrate/trades.parquet` is built with `**P2_EXIT`
(`no_time_cap`, 20-week trail, blow-off arm) — the LIVE Phase-2 exit. The run of record uses the
frozen ladder with the 13-week time cap. A funded-vs-unfunded comparison across those two would
attribute an **exit-regime** difference to the cash machine.

**Not the engine's own uncapped run either.** `backtest(uncapped=True)` removes the cash test but
still enforces **one open position per ticker**, so a signal on a name it already holds is never
activated. Measured: **81 of the capped book's 255 trades do not appear in the uncapped run at
all**, and in **all 81** cases the ticker was open in the uncapped book at that moment. (The capped
book entered TATASPONGE on 2018-04-16; the uncapped book was still holding a 2018-04-09 entry.) It
is not a superset of the funded set — "population minus funded" against it would have been wrong by
a third of the funded trades, and it would have looked fine.

**What is used.** The holdings rule is portfolio construction, not signal. Every entry window is
simulated **independently, overlaps included**, by a simulator that re-implements the frozen exit
ladder.

**The simulator is hard-validated before any statistic is published.** It must reproduce all
**3,045** rows of the engine's own uncapped ledger exactly. It does:

| field | entry | exit price | exit date | reason | weeks held | R | net P&L |
|---|---|---|---|---|---|---|---|
| mismatches / 3,045 | **0** | **0** | **0** | **0** | **0** | **0** | **0** |

Max absolute difference on every numeric field: **0.0**. The script asserts this and refuses to emit
anything if it fails. It further asserts that all **255** funded trades are present in the
population — the check that caught the uncapped run's failure.

**The funnel.**

| stage | count |
|---|---:|
| entry windows created | 8,518 |
| **population** — in index at activation **and** printed an open inside `(lo, hi)` during its week | **6,245** |
| funded by the ₹10L book | **255** (**4.08%** of the population) |
| cash rejections logged by the capped run | 19,504 |

The 2,273 windows that drop out either failed the index-membership test at activation or never
printed a qualifying open; this census did not separate those two causes.

---

## 1. Full population — what one signal pays

### Headline

| | Full period 2017–2026 | From 2019 |
|---|---:|---:|
| **N** | **6,245** | **5,357** |
| Win rate | 47.14% | 48.67% |
| Average win | +2.65 R | +2.74 R |
| Average loss | −1.60 R | −1.67 R |
| **Payoff ratio** | **1.660** | **1.639** |
| **Expectancy** | **+0.405 R** | **+0.475 R** |
| **Expectancy, net %** | **+2.08%** | **+2.70%** |
| Median R | −0.317 | −0.149 |
| Median net % | −2.50% | −1.52% |
| Sum R | +2,530.6 | +2,541.8 |

**The median trade loses.** Expectancy is positive and the median is negative in both periods — the
population is carried by its right tail, not by a majority of winners. Fewer than half of all
signals close green.

Note also that the full period's sum R (+2,530.6) is *below* the 2019+ sum (+2,541.8): 2017–2018
contributes −11.2 R net across 888 signals.

### Distribution of R (deciles)

| p10 | p20 | p30 | p40 | **p50** | p60 | p70 | p80 | p90 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| −1.81 | −1.40 | −1.19 | −1.02 | **−0.32** | +0.71 | +1.45 | +2.15 | +3.21 |

*(2019+: −1.85 / −1.42 / −1.19 / −1.00 / **−0.15** / +0.87 / +1.57 / +2.25 / +3.34.)*

Four of the ten deciles sit between −1.0 and −1.9 R — the stop-out band — and the p40–p60 span
crosses from −1.02 to +0.71, so there is almost no mass near zero. Outcomes are close to bimodal:
stopped, or held to something.

### Distribution of net % per trade

| p10 | p30 | **p50** | p70 | p90 |
|---:|---:|---:|---:|---:|
| −12.84% | −7.53% | **−2.50%** | +9.04% | +21.40% |

*(2019+: −12.71 / −7.34 / **−1.52** / +9.97 / +22.33.)*

### Hold time

| p10 | **median** | p90 | mean | max |
|---:|---:|---:|---:|---:|
| 2 wk | **9 wk** | 13 wk | 8.4 wk | 14 wk |

The 13-week cap binds hard: the p90 *is* the cap.

### Exit-reason mix

| reason | full period | from 2019 |
|---|---:|---:|
| `stop` | 2,820 | 2,353 |
| `time` | 2,316 | 2,005 |
| `trail` | 853 | 764 |
| `eos` | 177 | 177 |
| `stop_half` | 79 | 58 |

**45.2% of all signals close at the stop** (46.4% counting `stop_half`). Only **13.7%** reach the
trail, which requires the +2R half to have booked first.

### Per year

| Year | N | Win rate | Expectancy R | Expectancy % | Funded N | Funded exp R |
|---|---:|---:|---:|---:|---:|---:|
| 2017 | 31 | 64.5% | +1.361 | +8.54% | 13 | +1.153 |
| 2018 | 857 | 37.0% | −0.062 | −2.03% | 30 | +0.279 |
| 2019 | 565 | 55.7% | −0.281 | +3.31% | 19 | +0.902 |
| 2020 | 469 | 53.1% | +0.557 | +5.24% | 36 | +0.255 |
| 2021 | 280 | 47.9% | +0.253 | +3.22% | 30 | +0.417 |
| 2022 | 984 | 39.6% | −0.037 | −0.28% | 28 | +0.693 |
| 2023 | 860 | 69.0% | +1.712 | +8.57% | 25 | +0.935 |
| 2024 | 788 | 36.3% | −0.207 | −0.31% | 32 | +0.051 |
| 2025 | 840 | 40.7% | +0.745 | +0.02% | 27 | −0.041 |
| 2026 | 571 | 52.2% | +0.822 | +4.14% | 15 | +1.149 |

**Four of ten years are negative in R at population level** (2018, 2019, 2022, 2024), and 2019 is
negative in R while positive in %. Signal counts swing 280 → 984 year to year, and the funded
count is nearly flat at 15–36 regardless: **the book's throughput is set by its capital, not by how
many signals the market offers.** 2019 is the sharpest instance of R and % disagreeing in sign;
§2's stop-width finding is the mechanism, and it is not analysed further here.

---

## 2. Funded vs unfunded — the core question

### The answer

**The funded set is not a representative sample. It is systematically selected, on every dimension
tested, at overwhelming significance.**

| | Funded | Unfunded | Δ | Mann-Whitney p |
|---|---:|---:|---:|---:|
| N | 255 | 5,990 | | |
| Win rate | **59.2%** | **46.6%** | +12.6pp | |
| Payoff ratio | 1.546 | 1.677 | −0.131 | |
| Expectancy R | **+0.500** | **+0.401** | +0.099 | **0.00063** |
| Expectancy net % | **+5.36%** | **+1.94%** | +3.42pp | **0.037** |
| Stop width (% of entry) | **13.73%** | **6.79%** | **+6.94pp** | **1.1e-89** |
| Extension over signal-week SMA | **18.50%** | **9.10%** | +9.40pp | **1.9e-84** |
| CRS rank (`crs_dist`) | **0.140** | **0.070** | +0.071 | **1.0e-38** |
| Signals arriving that ISO week | **16.1** | **29.7** | −13.5 | **7.6e-39** |
| Hold time (weeks) | 10.87 | 8.29 | +2.58 | **8.3e-19** |
| Entry price (₹) | 1,595 | 2,025 | −429 | **0.00013** |

*(2019+ only: funded N=212, win 59.4%, expR +0.491, exp% +5.81; unfunded N=5,145, win 48.2%,
expR +0.474, exp% +2.57.)*

### The mechanism — it is arithmetic, not judgement

Position size is `shares = equity × 2% ÷ (entry − stop)`. **Notional is therefore inversely
proportional to stop width.** A tight stop buys many shares and needs a large notional; a wide stop
needs a small one. The cash gate is a notional filter, so it is a stop-width filter.

| Stop-width quintile | Median stop | **Median notional** | N | Funded | **Funded rate** | Pop. exp R | Pop. exp % |
|---|---:|---:|---:|---:|---:|---:|---:|
| Q1 tightest | 2.84% | **₹704,900** | 1,249 | **0** | **0.00%** | **+0.972** | +2.16% |
| Q2 | 4.51% | ₹443,681 | 1,249 | 4 | 0.32% | +0.357 | +1.70% |
| Q3 | 6.14% | ₹325,728 | 1,249 | 20 | 1.60% | +0.245 | +1.55% |
| Q4 | 8.35% | ₹239,657 | 1,249 | 38 | 3.04% | +0.228 | +2.00% |
| Q5 widest | 12.62% | **₹158,462** | 1,249 | **193** | **15.45%** | +0.224 | **+2.99%** |

**Not one of the 1,249 tightest-stop signals was ever funded, in nine and a half years.** Their
median notional is ₹704,900 against a ₹1,000,000 book — a single such position consumes 70% of
capital, so it can only be bought from an almost-empty book. Q5's median notional is ₹158,462; six
of those fit at once. **75.7% of all funded trades come from the widest quintile.**

### And the same table read in the other unit reverses the sign

In **R**, the excluded quintile is by far the best (+0.972 against +0.224) — the cash gate looks
like it systematically funds the worst signals. In **net %**, the ordering flips: the widest
quintile is the *best* (+2.99% against +2.16%).

Both are arithmetically correct, and the reason they disagree is already on the binder: **R is not a
comparable unit across cohorts with different stop widths** (binder §7/§8, the R-denominator audit).
A tight stop is a small R denominator, so the same rupee move prints a larger R. The funded/unfunded
R gap of +0.099 and the % gap of +3.42pp are measuring different things, and neither alone
characterises the selection.

### Two opposing selections, separated

| | exp R |
|---|---:|
| Population | +0.405 |
| Widest-stop quintile (where 75.7% of funded live) | +0.224 |
| **Funded** | **+0.500** |

The cash gate pushes the book into the lowest-R quintile; CRS fill-priority then picks well *inside*
it. Within-quintile, funded beats unfunded consistently:

| Quintile | Funded exp R | Unfunded exp R | Δ |
|---|---:|---:|---:|
| Q3 | +1.020 | +0.232 | **+0.788** |
| Q4 | +1.048 | +0.202 | **+0.846** |
| Q5 | +0.365 | +0.198 | +0.167 |

*(Q1 has zero funded trades; Q2 has four and is not read.)*

So the +0.099 R funded-vs-population edge is a **net of two large opposing effects**, not a small
one — an illustrative decomposition puts the mechanical selection at about −0.18 R (population → widest
quintile) against a priority selection of about +0.28 R (widest quintile → funded). The two legs are
approximate, since 24.3% of funded trades sit outside the widest quintile.

### Extension band

Extension and stop width correlate **+0.577** in the population, so the same selection appears here:

| Ext band | N | Funded | **Funded rate** | Pop. exp R | Pop. exp % |
|---|---:|---:|---:|---:|---:|
| `<0%` (below the line) | 93 | 0 | **0.00%** | **+2.977** | +5.10% |
| `0–5%` | 1,104 | 4 | 0.36% | +0.755 | +2.70% |
| `5–10%` | 2,498 | 21 | 0.84% | +0.256 | +1.03% |
| `10–20%` | 2,308 | 133 | 5.76% | +0.308 | +2.50% |
| `>20%` | 242 | 97 | **40.08%** | +0.288 | +4.89% |

**Two in five of the most-extended signals get funded; none of the sub-line ones ever do.** Stated
and parked — this census does not analyse it and proposes nothing.

### What this means for every rejection judged against the portfolio figure

Plainly: **the portfolio Sharpe partly measures the cash machine.** The 255 trades behind 1.132 are
drawn from the population with a funding probability that varies by a factor of **48×** across
stop-width quintiles (0.32% → 15.45%, and 0% at the extreme), and by **111×** across extension bands
(0.36% → 40.08%). An overlay evaluated by its effect on that book is evaluated on a set whose
composition is set as much by notional arithmetic as by signal quality — and any lever that shifts
stop width or extension shifts *which* signals are affordable, before it changes anything about
whether they are good.

This is a restatement of a mechanism the programme already has receipts for — the composition-noise
law, 0112's fill-priority result, and the ±10R/yr floor — measured here for the first time as a
population-versus-funded comparison. **No verdict on the record moves and none is proposed.**

---

## 3. Adherence sensitivity

**Limitation, stated up front.** This is **per-trade random sampling of the signal population**. It
cannot model cash-path effects: which signals a smaller book could actually have funded, the order
they arrive in, or the capital each frees for the next. It answers exactly one question — *if you
took a random k% of these trades, how far can realised expectancy sit from the population's?* — and
nothing about portfolio behaviour.

Sampling is without replacement, so **the mean is invariant by construction**; it is printed only as
an arithmetic check. **The spread is the finding.** 4,000 draws per k, seed 20260806.

**Full period** (population mean +0.4052 R):

| k | n taken | mean of draw means | SD | p05 | p95 |
|---:|---:|---:|---:|---:|---:|
| 50% | 3,122 | +0.4022 | 0.1474 | **+0.168** | **+0.638** |
| 70% | 4,372 | +0.4039 | 0.0953 | +0.246 | +0.567 |
| 90% | 5,620 | +0.4042 | 0.0495 | +0.300 | +0.518 |
| 100% | 6,245 | +0.4052 | 0.0000 | +0.405 | +0.405 |

**From 2019** (population mean +0.4745 R):

| k | n taken | mean of draw means | SD | p05 | p95 | net % p05–p95 |
|---:|---:|---:|---:|---:|---:|---|
| 50% | 2,678 | +0.4701 | 0.1735 | **+0.199** | **+0.744** | +2.35% … +3.03% |
| 70% | 3,750 | +0.4723 | 0.1111 | +0.291 | +0.664 | +2.48% … +2.92% |
| 90% | 4,821 | +0.4739 | 0.0550 | +0.356 | +0.606 | +2.58% … +2.81% |
| 100% | 5,357 | +0.4745 | 0.0000 | +0.475 | +0.475 | +2.70% |

**Reading.** Taking a random half of the signals puts the 5th–95th percentile of realised
expectancy at **+0.17 to +0.64 R** against a population value of +0.41 — a 90% interval spanning
roughly **±58% of the expectancy itself**, produced by nothing but which trades you happened to
take. At 90% adherence the band is still +0.30 to +0.52.

Note the contrast with the % column: the same draws move net expectancy only between +2.35% and
+3.03%. R is the noisier unit here, for the denominator reason in §2.

**What this does not say.** It does not say a 50%-adherence book has this distribution — a real book
at half adherence has a different cash path, different fill order, and different capital
availability. It says only that **per-trade selection noise alone is large relative to the
expectancy being measured**, which bounds from below how much of any observed difference between two
books can be attributed to their rules.

---

## 4. What this census does and does not establish

**Establishes.**
- The signal population's own statistics, in one place, for the first time: N=6,245, win 47.1%,
  payoff 1.66, expectancy +0.405 R / +2.08%, median trade negative, 45% stop out.
- The funded set differs from the population at p < 1e-38 on stop width, extension, CRS rank and
  queue depth, and the mechanism is arithmetic (notional ∝ 1/stop-width), not judgement.
- The funded/unfunded R gap is the net of two large opposing selections, not one small one.
- Per-trade adherence noise alone spans ±58% of expectancy at 50% adherence.
- The 13-week cap binds at the p90 of hold time.

**Does not establish, and is not claimed.**
- That the book *should* fund different signals. No counterfactual book was run; §3 is explicitly
  not one.
- That the excluded tight-stop cohort would have earned +0.972 R *in a book*. It earned that as a
  population of independent, overlap-allowed signals with fixed sizing off ₹1,000,000 — a book
  cannot take them all, and 3.7% of the population would not fit in the book at any one time.
- Anything about whether R or % is the right unit. Both are reported; the binder owns that question.
- Any hypothesis about ext bands, the 2019 sign disagreement, or the year-to-year signal-count
  swing. Noticed, stated, parked.

---

## Cross-references

- `scripts/diag_trade_population_census.py` — producer, with the simulator and its validation gate
- `trade_population_census.json` · `trade_population.parquet` — full evidence, all deciles and tests
- `BLIND_BRIEF_SWING.md` — the exit ladder this census's simulator re-implements, specified
- binder §7 / §8 — the R-denominator audit, which owns the unit question §2 runs into
- `FOUNDATION_AUDIT.md` — the data the whole population is computed from
