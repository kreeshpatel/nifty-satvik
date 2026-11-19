# Joint sensitivity + Monte Carlo on the India after-tax analysis — 2026-11-19

**Analysis, not tax advice.** Base rates come from `config/tax_india_fy2627.yaml` (CONFIRM WITH CA). The distributions
come from `config/tax_montecarlo.yaml`.

**Class:** MEASUREMENT. Branch `research/tax-montecarlo`, stacked on #212. There are no live changes, no sealed reads,
and no trials.

**Standing counts:** screens 24 · sealed opens 4 · n_trials 3 (unchanged).

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
| **E base** | p50 +2.2k (p5 −49k, p95 +57k); **P 0.52** | +26.7k (−0.6k / +84k); **P 0.82** | +81.1k (+15.6k / +145k); **P 0.989** | −5.40L (−7.85L / −3.14L); **P 0.000** |
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

No draw breaks even: across 4,000 draws, no capital up to ₹500 crore makes S4 ≥ S2, with or without the dividend.

Every company rate in the draws sits above the matching individual rate, and the individual's own surcharge is held
at 0, as in the config.

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

## Owner decisions

1. **The family split (S3)** is the only step that is both large and near-certain under the base law: median +₹81k,
   P 0.989.
   - It goes to zero if the split fails (law D).
   - Decide whether to take CA questions 3 and 4 before anything else.
2. **Arbitrage fund vs liquid fund (S0→S1)** is a coin flip, P 0.52. It turns negative (P 0.17) if arbitrage funds are
   taxed at slab.
   - It hinges on the real arbitrage-vs-liquid spread and on Q6.
   - Options:
     - fetch the Nifty 50 Arbitrage TRI to replace the proxy;
     - stay on the liquid fund until Q6 is answered.
3. **Harvesting (S1→S2)** gains in 82% of draws. It is worth nothing if the LTCG exemption is removed (law A).
   - It costs little to run.
   - Decide whether to fix the harvest date before 31 March.
4. **The company route (S4)** loses in 100% of draws under every law, and never breaks even up to ₹500 crore at
   surcharge 0. No further work proposed unless Q9 places the owner at the maximum surcharge.
