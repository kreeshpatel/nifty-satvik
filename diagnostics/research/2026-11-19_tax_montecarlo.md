# Joint sensitivity + Monte Carlo on the India after-tax analysis — 2026-11-19

**Analysis, not tax advice.** Base rates come from `config/tax_india_fy2627.yaml` (CONFIRM WITH CA). The distributions
come from `config/tax_montecarlo.yaml`.

**Class:** MEASUREMENT. Branch `research/tax-montecarlo`, stacked on #212. There are no live changes, no sealed reads,
and no trials.

**Standing counts:** screens 24 · sealed opens 4 · n_trials 3 (unchanged).

> **Correction 1 (amendment 2026-11-19, PR #214): arbitrage vs liquid.** The statement "arbitrage vs liquid is a coin
> flip, P 0.52" is **superseded**. It rested on an arbitrage-spread range (−1.5% to +0.3%) that the real data lies
> outside of.
>
> | measure | value |
> |---|---|
> | real spread, Kotak + ICICI arbitrage vs SBI + HDFC liquid (Direct-Growth NAVs, 2019-03 to 2024-06) | **+0.69pp a year** |
> | real spread, all 18 arbitrage vs 31 liquid funds | +0.50pp a year |
> | P(S1 > S0), re-drawn on −0.19% to +1.66% (the by-year range ±0.3pp) | **0.9995** |
> | median gain, re-drawn | **+₹75k** |
>
> All four rows are [measured].

> **Correction 2 (amendment 2026-11-19): company route.** "No break-even up to ₹500 crore under every law" held only
> at the owner surcharge the original draws assumed (0). With the owner at 15% or 25% surcharge, the company breaks
> even in 100% of draws at a median of **₹13.6 crore** (p5 ₹6.9 cr, p95 ₹25.1 cr), **without the final dividend
> only** [measured].

> **Correction 3: #212's harvest figure is not reproducible to the rupee.** #212 explained the replica gap on the
> S1→S2 step as a lot-ordering convention. **The real cause is Python hash-seed nondeterminism** in the #212 simulator.
>
> - `Taxpayer.retarget` iterates over a `set`, and that order sets the order in which the index and arbitrage
>   funds are harvested.
> - #212's deterministic S1→S2 is **+₹13,460 under PYTHONHASHSEED 0, 2 and 3, and +₹11,564 under 1** [measured].
> - In the Monte Carlo, this changes per-draw harvest gains by up to ₹25k. Over 400 draws × 2 seeds, it changes
>   **no** P(gain > 0); the median of the pre-31-March group moved between ₹31.5k and ₹33.6k [measured].
> - S0, S1 and S4 are unaffected.
> - The fix (sorting the set) belongs in #212's script, which this PR may not edit (owner decision 5).

**Mission line.** This tests whether the after-tax vehicle ranking from #212 holds up against uncertain law,
parameters and return paths before any of it is acted on.

## Method (stated before results)

The code is `pipelines/diagnostics/explore_tax_montecarlo.py`; its docstring holds every formula. Output is in
`diagnostics/research/explore/2026-11-19_tax_montecarlo.json`.

**Simulator.**
- It imports #212's `simulate`, `scenarios`, `context`, `cash_prices`, `index_price`, `break_even` and `load_cfg`
  unchanged.
- It builds only the inputs: a config with one joint draw written into it, and a price context with the index path
  replaced.
- Two runtime mechanisms are scoped to a single draw and restored afterwards:
  - **Harvest offset.** The module's `pd.Timestamp(year, 3, 15)` is shifted by the drawn offset.
  - **Law C.** The arbitrage fund is removed from the simulator's equity set, so it is taxed at slab and not harvested.

**Paths.**
- A stationary bootstrap of the daily index-TRI returns, mean block 20 sessions, on the real 2019-03-05..2024-06-28
  calendar. Financial-year boundaries, the 365-day test and harvest dates therefore stay real.
- The same resampled indices are applied to the blend's returns.
- The index drift is re-centred on g ~ U(6%, 16%) while keeping the volatility.
- **This measures path uncertainty on one 2019–24 history plus a drift shift, not regime uncertainty.**
- The cash legs accrue a constant rate under the #212 proxy, so for them the resampling does nothing.
- The blend is not tax-simulated. Its pass-through gains are the books' historical trade ledger, which means nothing on
  a resampled path.

**Draws.**
- Latin hypercube (seed 20261119) over 15 dimensions, with one fresh path per draw.
- The same draws are used for every law scenario.
- 2,000 draws failed the convergence rule, so a second independent hypercube of 2,000 (seed 20261120) was added
  once, as the spec allows. **N = 4,000.**

**Scenarios.**
- S3 is three PANs, two of them at slab 0%.
- S4 is the company, shown with and without the final dividend.
- Law D (family split fails) sets S3 = S2, because clubbing taxes the whole household as the owner.

## Anchors (step 0) — reproduced [measured]

**#212's deterministic pipeline** reproduces exactly:

| step | value |
|---|---|
| S0 → S1 | +₹48,122 |
| S1 → S2 | +₹13,460 |
| S2 → S3 | +₹2,38,886 |
| S2 → S4 | −₹8,47,439 |
| best scenario | 22.86% |

**This file's context builder**, run on the identity path (no resampling, no drift, base parameters), reproduces S0..S4
to the rupee: ₹56,74,731 / 57,22,853 / 57,36,313 / 59,75,199 / 48,88,874.

## Terminal after-tax value, law E (base) [measured]

₹20L invested 2019-03 to 2024-06, liquidated at the end.

These levels sit near **₹30L**, against **₹57L** on the historical path. The drift draws, 6–16% a year, are far below
the historical index's ~34% a year.

**60/40**

| | p5 | p50 | p95 |
|---|---|---|---|
| S0 | 26.18L | 29.75L | 33.84L |
| S1 | 26.12L | 29.78L | 33.84L |
| S2 | 26.33L | 30.07L | 34.28L |
| S3 | 26.76L | 30.89L | 35.44L |
| S4 | 20.55L | 24.64L | 29.29L |
| S4 + dividend | 13.17L | 15.80L | 18.78L |

65/35 is similar and slightly higher; p25 and p75 are in the JSON.

## Step gains and P(gain > 0) [measured]

Rupee gain over the whole window, 60/40 book. 65/35 is within a few % on every row and is in the JSON.

| law | S0→S1 (arbitrage) | S1→S2 (harvest) | S2→S3 (3 PANs) | S2→S4 (company) |
|---|---|---|---|---|
| **E base** | p50 +2.2k (p5 −49k, p95 +57k); P 0.52 *(superseded: amendment item 3D)* | +26.7k (−0.6k / +84k); P 0.82 all offsets; **fixed pre-31-March date: P 0.83** (amendment item 1) | +81.1k (+15.6k / +145k); **P 0.989, conditional on the split being legally valid** | −5.40L (−7.85L / −3.14L); **P 0.000** |
| A exemption removed | +0.3k; P 0.51 | +0.0k; **P 0.52** | +1.00L; P 1.000 | −4.87L; P 0.000 |
| B STCG 30% | +2.2k; P 0.52 | +22.4k; P 0.80 | +82.0k; P 0.990 | −5.38L; P 0.000 |
| C arbitrage at slab | **−28.3k; P 0.17** | +17.0k; P 0.74 | +99.8k; P 1.000 | −5.27L; P 0.000 |
| D family split fails | +2.2k; P 0.52 | +26.7k; P 0.82 | **0; P 0.000** | −5.40L; P 0.000 |

With the dividend, S2 → S4 is p50 −14.2L, and P = 0 under every law.

## Rank-order stability, 60/40 [measured]

| law | P(S3>S2>S1>S0>S4) | P(S1>S0) | P(S2>S1) | P(S3>S2) | P(S2>S4) |
|---|---|---|---|---|---|
| E base | 0.425 | 0.522 | 0.903 | 0.989 | 1.000 |
| A | 0.257 | 0.505 | 0.793 | 1.000 | 1.000 |
| B | 0.415 | 0.522 | 0.885 | 0.990 | 1.000 |
| C | **0.122** | **0.167** | 0.825 | 1.000 | 1.000 |
| D | **0.000** | 0.522 | 0.903 | **0.000** | 1.000 |

The full order holds in only 42% of base draws. Almost all of the failure is S0 vs S1, which is a coin flip. The
ordering between S1 and S4 that #212 relied on holds in 100% of draws under every law.

## Sensitivity attribution — PRCC, law E, 60/40 [measured]

Partial rank correlation coefficient of each step's gain against each parameter; the full tornado is in the JSON
(`prcc`).

| step | top 3 drivers (PRCC) |
|---|---|
| S0 → S1 | arbitrage spread vs liquid **+0.98** · owner slab +0.88 · liquid yield +0.76 |
| S1 → S2 | LTCG exemption **+0.75** · LTCG rate +0.22 · index drift +0.17 |
| S2 → S3 | index drift **+0.75** · LTCG exemption −0.67 · LTCG rate +0.52 |
| S2 → S4 | compliance cost **−0.97** · LTCG exemption −0.72 · index drift −0.59 |

65/35 has the same top 3 in the same order.

## Company break-even [measured]

*Superseded by Correction 2 and amendment item 2.* At owner surcharge 0 (the original draws), no capital up to ₹500 crore makes S4 ≥ S2. Every company rate sits above the individual's.

## Parameters vs return path [measured]

Standard deviation of each step's gain, 60/40.

| step | full | paths only (base parameters) | parameters only (historical path) |
|---|---|---|---|
| S0 → S1 | 32.3k | 8.7k | 33.2k |
| S1 → S2 | 29.7k | 13.8k | 28.0k |
| S2 → S3 | 38.8k | 67.8k | 33.8k |
| S2 → S4 | 148k | 151k | 155k |

**Reading:**
- S0 → S1 and S1 → S2 spread comes from the **parameters**.
- S2 → S3 and S2 → S4 spread grows with the return level.

**The modes are not like-for-like in growth.** "Paths only" keeps the historical ~34% a year index growth (base
parameters means no re-centring). "Parameters only" applies the drawn drift. That is why the paths-only spread for
S2 → S3 exceeds the full run's.

## Convergence [measured]

Each step's p50 and P(gain>0) are compared between the first 2,000 draws and all 4,000.

| step | 60/40 p50 change | 65/35 p50 change |
|---|---|---|
| S2 → S3 | 0.9% | 0.2% |
| S2 → S4 | 0.6% | 0.7% |
| S1 → S2 | **2.0%** | **1.7%** |
| S0 → S1 | **16%** | **10%** |

- **S2 → S3 and S2 → S4 pass.**
- **S1 → S2 and S0 → S1 fail the 1% p50 rule even after the one permitted doubling.**
- The S0 → S1 median is about ₹2k, close to zero, so a relative test can't settle. The absolute moves are a few
  hundred rupees.
- Every P(gain>0) moved by less than 0.006.
- Those two p50s are reported as **not converged to 1%**.

## Verification (rule 3) [measured]

A fresh `blind-replica`, working from the spec only, ran 300 draws with its own seed:

| S3 − S2, law E, 60/40 | replica, 300 draws | this run, 4,000 draws | 90% band for any 300 of these draws |
|---|---|---|---|
| p5 | 17,675 | 15,589 | 10,106 – 23,035 |
| p50 | 78,646 | 81,143 | 75,772 – 85,341 |
| p95 | 147,859 | 145,296 | 137,513 – 151,240 |
| P(S3 > S2) | 0.977 | 0.989 | 0.980 – 0.997 |

- **p5:** 13% off relative, which is above the 5% flag. It lies inside the 300-draw sampling band, so it reads as
  noise.
- **p50, p95 and P:** within 5% (3.1%, 1.8% and 1.2%).
- **P(S3 > S2):** sits 0.003 below the band.
- **No disagreement beyond sampling noise.**

## Artifact check (rule 2)

1. **Path count and block length.**
   - 4,000 paths, mean block 20 sessions.
   - Cross-correlation of index vs blend returns is preserved: 0.813 on resampled paths (p5 0.775, p95 0.848) against
     0.808 originally.
   - Ruled in.
2. **One history.** Every path is assembled from 2019–24 days. Regime uncertainty is not measured. Not ruled out.
3. **Drift range.** At 6–16%, the drift is far below the window's realised ~34%. Absolute rupee steps scale with it,
   and the S2→S3 PRCC reflects that. The ranking, not the levels, is the robust output.
4. **Harvest after 31 March.**
   - Offsets above +16 days (22.5% of draws) put the harvest in April, inside the next FY.
   - In those draws S1→S2 has a median of +19.8k, against +29.3k otherwise.
   - This is the spec's range applied literally; the replica flagged it independently.
5. **Arbitrage proxy.** The S0→S1 sign is set by the drawn spread (PRCC 0.98), which is an assumption, not data. The
   Nifty 50 Arbitrage TRI is still unfetched.
6. **Surcharge held at 0.** The only route to a company break-even (individual surcharge at high income) is outside
   these draws, as in #212.
7. **Two p50s not converged** (above).

## Mapping drivers to #212's ten CA questions [inferred]

| driver or law | CA question |
|---|---|
| arbitrage spread; law C | **Q6**: arbitrage-fund equity status after the April 2026 STT change |
| owner slab and liquid yield (S0→S1) | **Q7**: liquid fund taxed at slab; **Q9**: owner's surcharge and total income |
| LTCG exemption (harvest; S2→S3; S2→S4) | **Q1**: whether the exemption applies to a company. The exemption level itself is statute, not a CA question |
| harvest timing, buy-back | **Q5**: same-day buy-back, GAAR |
| law D, the family split | **Q3**: unexhausted basic exemption against gains; **Q4**: clubbing and gifts |
| compliance cost (S2→S4) | **Q8**: company compliance cost, deductibility and dividend |

## Amendment 2026-11-19 (items 1–7 and owner additions A–E)

Code:
- `pipelines/diagnostics/explore_tax_mc_amendments.py` (items 1, 3, 4, 5)
- `explore_tax_mc_surcharge.py` (item 2)
- `explore_tax_mc_arbitrage_real.py` (A, B, D)

Outputs: `diagnostics/research/explore/2026-11-19_tax_mc_{amendments,surcharge,arbitrage_real}.json`.

There are no new simulations of the original 4,000 draws for item 1. Items 2 and D reuse their seeds and paths;
path regeneration reproduces the cached S1 exactly, a difference of ₹0.00 over 20 draws [measured].

### 1. Harvest timing as a decision [measured]

S1→S2 gain, base law, 4,000 draws.

| group | share of draws | 60/40 p5 / p50 / p95 | P(gain>0) | 65/35 P(gain>0) |
|---|---|---|---|---|
| **fixed pre-31-March date** (offset ≤ +15) | 75.8% | −53 / **+29.9k** / +86.3k | **0.832** | 0.824 |
| on or after 31 March (offset > +15) | 24.2% | −4.4k / +18.2k / +72.3k | 0.772 | 0.766 |

60/40 by 5-day offset bin:

| offset (days) | p50 | P |
|---|---|---|
| −30..−26 | 24.1k | 0.75 |
| −25..−21 | 26.3k | 0.81 |
| −20..−16 | 29.7k | 0.84 |
| −15..−11 | 32.1k | 0.82 |
| −10..−6 | 32.7k | 0.89 |
| −5..−1 | 28.4k | 0.83 |
| 0..+4 | 33.5k | 0.86 |
| +5..+9 | 31.8k | 0.82 |
| +10..+14 | 30.5k | 0.84 |
| +15..+19 | 26.6k | 0.80 |
| +20..+24 | 17.6k | 0.77 |
| +25..+30 | 16.8k | 0.76 |

The gain falls once the harvest slips past 31 March. The fixed pre-31-March figure is the headline. Per Correction 3,
the per-draw amounts carry about ±₹1–2k of median hash-seed noise; the probabilities do not.

### 2. Owner surcharge as a dimension [measured]

The owner surcharge s ∈ {0, 10%, 15%, 25%} on interest and slab income, with capital gains capped at 15%, is
**CONFIRM WITH CA**. The dividend is taxed at slab × (1+s) × (1+cess), which is [assumed]; the statutory surcharge on
dividends may be capped at 15%.

- 2,000 draws, with the same seeds and paths as the original first pass, each evaluated at all four levels.
- **Anchor:** #212's maximum-surcharge break-even of ₹5.52 cr reproduced exactly, 0.0% difference.

| s | P(S4>S2) at ₹20L, laws E/A/B/C | median S4−S2 (E) | break-even, no dividend: share / p5 / p50 / p95 (₹ cr) | break-even with dividend |
|---|---|---|---|---|
| 0 | 0 / 0 / 0 / 0 | −₹5.38L | none up to ₹500 cr | none |
| 10% | 0 / 0 / 0 / 0 | −₹5.29L | none | none |
| 15% | 0 / 0 / 0 / 0 | −₹5.23L | **100% / 6.9 / 13.6 / 25.1** | none |
| 25% | 0 / 0 / 0 / 0 | −₹5.23L | **100% / 6.9 / 13.6 / 25.1** | none |

- 15% and 25% are identical under laws E, A and B. With an arbitrage cash leg, all of the owner's gains are equity, so
  the 15% capital-gains cap binds.
- They differ only under law C, where arbitrage is taxed at slab.

### 3. Real arbitrage and liquid data (with owner additions A–C) [measured]

**Source.** The Nifty 50 Arbitrage TRI endpoint on niftyindices returned HTML for 4 spellings of the index name, so
the TRI is not retrieved. The exact file still needed is that index's daily TRI, 2019-03 to 2024-06.

Daily NAVs come from api.mfapi.in, which mirrors AMFI. They were cross-checked against AMFI's own NAV-history file on
3 dates: **12/12 equal**.

**A. Plans and expenses.**
- All four funds are **Direct Plan, Growth**:
  - Kotak Arbitrage (119771)
  - ICICI Pru Arbitrage (120364)
  - SBI Liquid (119800)
  - HDFC Liquid (119091)
- NAVs are net of expenses. In the simulator the TER enters only the proxy price build and a reported tally that is
  never deducted. With real NAVs, the S0→S1 step is **+₹1,34,129 with the TER left in and +₹1,34,129 with it zeroed**
  (60/40), so nothing is double-counted.

**B. Spreads by year and fund selection.** The selection rule: the two arbitrage funds the owner named as largest, plus
two widely held liquid funds. **AUM is not in AMFI's NAV files, so "largest" is not verified at either the start or
the end of the window** [assumed].

| arbitrage minus liquid (pp a year) | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 H1 | overall |
|---|---|---|---|---|---|---|---|
| Kotak − liquid average | 0.30 | 0.67 | 1.22 | 0.29 | 0.97 | 1.58 | 0.79 |
| ICICI − liquid average | 0.24 | 0.61 | 1.06 | −0.07 | 0.73 | 1.13 | 0.58 |
| pair − liquid average (headline) | 0.27 | 0.64 | 1.14 | 0.11 | 0.85 | 1.36 | **0.69** |
| pair − proxy liquid (6.34% net) | 0.40 | −1.47 | −1.85 | −1.36 | 1.59 | 2.58 | −0.29 |
| **all arbitrage − all liquid, equal weight** | 0.21 | 0.48 | 0.83 | −0.08 | 0.68 | 1.19 | **0.50** |

Fund-by-liquid-fund pairs are in the JSON.

Category counts, Direct-Growth, excluding fund-of-funds, ETFs and overnight funds:

| category | schemes at start | schemes at end | present throughout, used |
|---|---|---|---|
| arbitrage | 23 | 27 | 18 |
| liquid | 40 | 39 | 31 |

One liquid fund (Navi Liquid) was dropped because its NAV was rebased, which is not a return. That cleaning rule was
**added after first look**.

**C. Step value with real data, 60/40.**

| S0 → S1 | value |
|---|---|
| proxy liquid, proxy arbitrage (#212) | +₹48,122 |
| proxy liquid, real arbitrage | +₹71,389 |
| real liquid, real arbitrage | **+₹1,34,129** |

65/35: +₹42,649, +₹64,546 and +₹1,22,037.

How the step grows:
- **Most of the increase (+₹62.7k of +₹86.0k) comes from the liquid proxy overstating liquid yield**: 6.34% net
  against 5.36% real.
- The other +₹23.3k is not a level difference, since the proxy arbitrage rate (6.04%) nearly equals the real 6.05%.
  It comes from the real arbitrage series' timing, with higher yields late in the window.

**D. Where the real spread sits, and the re-run.**
- Against the real liquid funds, the real spread (+0.69pp) lies **outside** the drawn range of −1.5% to +0.3%. Against
  the proxy liquid rate it is −0.29pp, inside the range at its 67th percentile.
- Re-run on the existing 4,000 paths and parameters, mapping each draw's spread onto [0.11 − 0.3, 1.36 + 0.3] =
  **[−0.19%, +1.66%]**:

| | P(S1 > S0) | p50 | p5 / p95 |
|---|---|---|---|
| 60/40 | **0.9995** | **+₹75.5k** | +21.2k / +136.6k |
| 65/35 | 0.9992 | +₹66.9k | — |

- **The old P 0.52 / +₹2.2k is superseded.**
- Law C (arbitrage taxed at slab) was not re-run on the new range; its P 0.17 rests on the old range.

### 4. Convergence, restated [measured]

Steps with a median below ₹10k in absolute value are tested on an absolute tolerance of ₹1,000; the rest stay at 1%
relative.

| step | rule | 60/40 p50 change | 65/35 p50 change | converged? |
|---|---|---|---|---|
| S0→S1 | absolute | ₹357 | ₹215 | **yes** |
| S1→S2 | relative | 2.0% | 1.7% | **no** |
| S2→S3 | relative | 0.9% | 0.2% | yes |
| S2→S4 | relative | 0.6% | 0.7% | yes |

Every P(gain>0) moved by less than 0.006, so all probabilities converged. The S1→S2 p50 also carries the hash-seed
noise from Correction 3.

### 5. Level comparability [measured]

Base law, 60/40, step medians:

| step | MC median (growth 6–16%) | paths-only median (historical ~34% growth) | #212 deterministic |
|---|---|---|---|
| S0→S1 | +2.2k | +53.0k | +48.1k |
| S1→S2 | +26.7k | +32.7k | +13.5k |
| S2→S3 | +81.1k | +2.70L | +2.39L |
| S2→S4 | −5.40L | −7.94L | −8.47L |

The paths-only medians sit near #212's levels. The MC levels are lower because the drift draws are far below the
window's growth. **The result is the ranking, not the rupee levels.**

### 6. Wording of the 3-PAN result

The 3-PAN probability (P 0.989, median +₹81k) is **conditional on the split being legally valid**. That is scenario E;
under D the gain is 0.

- It covers **adult children and parents only**: a spouse or a son's wife is excluded by s.64 clubbing.
- It treats the gift as **irrevocable**.
- It is not described as near-certain without those conditions.

### 7. Verification (rule 3) [measured]

A fresh `blind-replica` worked from the spec and raw files. It was compared only after it finished.

**Item 1 groups.** Identical to this study on all six rows: P 0.8318 / 0.7715 (60/40) and 0.8236 / 0.7663 (65/35).

**Item 2, break-even at 15%, draws 0..39.**

| | value |
|---|---|
| replica median, no dividend | ₹13.62 cr |
| this study, same draws | ₹13.64 cr |
| largest per-draw difference | 0.37% |
| draws differing by more than 5% | 0 of 40 |
| with dividend | none on 40/40, both |

The replica also found the hash-seed defect (Correction 3). It noted that the cache is in completion order and must be
keyed by `i`.

## Owner decisions

1. **Family split (S3).** The largest gain, median +₹81k and P 0.989, **if the split is legally valid**. It falls to 0
   if clubbing applies. CA questions 3 and 4 decide it.
2. **Cash leg (S0→S1).** On real NAVs, the arbitrage fund beats the liquid fund: P 0.9995, median +₹75k; deterministic
   +₹1.34L (60/40).
   - This holds only while arbitrage funds stay taxed as equity (CA Q6). Under law C the sign rests on the spread.
   - Options:
     - adopt arbitrage as the cash leg in the fallback design;
     - wait for Q6;
     - fetch the index TRI to confirm.
3. **Harvest date.** Fix it before 31 March: P 0.83 and median +₹29.9k, against 0.77 and +₹18.2k when it slips into
   April.
4. **Company route (S4).**
   - At ₹20L it loses under every surcharge and every law.
   - It is worth revisiting only if CA Q9 puts the owner at 15% surcharge or more **and** capital reaches about
     ₹7–25 cr (median ₹13.6 cr), with no dividend ever paid.
   - With a dividend, never.
5. **Simulator fix.** Sort `Taxpayer.retarget`'s set iteration in #212's script (Correction 3), then re-run #212's
   deterministic numbers under a fixed order. This is a change to #212, so it needs the owner's word.
