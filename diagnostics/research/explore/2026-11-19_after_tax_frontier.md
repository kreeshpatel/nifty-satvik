# After-tax efficient frontier and the mission's rolling 3-year test — 2026-11-19

**Class: MEASUREMENT.** Owner request ("prompt 3"), built on `research/blend-cost-tax` (PR #215, stacked on #214). No
rule test, no trial, no sealed read, no live change, nothing merged. **Standing counts: screens 24 · sealed opens 4 ·
n_trials 3** (unchanged).

**Goal link.** The mission sends core capital to the index fund unless a strategy beats it after tax over rolling
3-year windows within the −25% drawdown bar. This measures, on one friction model, which design has the most after-tax
return at that bar, and how often the blend wins the mission's own rolling test.

## Method — stated before any frontier result

Script: `pipelines/diagnostics/explore_after_tax_frontier.py`. The lot simulator is `explore_blend_cost_tax.LBook`
(itself `explore_after_tax_comparison.Book`), imported unchanged.

### Friction and tax

The same model as #215:
- **Stock-rate costs on sleeve units:** buy 0.2190%, sell 0.2040%.
- **Mutual-fund costs** (index fund, liquid fund, arbitrage fund): buy 0.005%, sell 0.001%.
- **Index fund:** the TRI less a 0.30% TER.
- **Tax:**
  - STCG 20%.
  - LTCG 12.5% above ₹1.25L. A gain is long-term above 365 days.
  - Liquid-fund gains at a 30% slab [assumed].
  - Set-off and carry-forward as AT.
  - Tax is paid on the last session on or before 31 March.
  - Terminal liquidation at 2024-06-28.
- **Capital and window:** ₹20,00,000, 2019-03-05..2024-06-28 (1,313 sessions).

The one addition: the arbitrage fund is taxed as equity (STCG/LTCG) at mutual-fund cost rates. This is the
`explore_india_tax_practices` rule (`config/tax_india_fy2627.yaml`, equity section).

### Cash leg — real NAVs from #214

Two cash legs are run, each a daily average of two funds' returns, Direct-Growth:
- **Real liquid:** SBI Liquid 119800 + HDFC Liquid 119091.
- **Real arbitrage:** Kotak 119771 + ICICI Prudential 120364.

Both come from api.mfapi.in, cross-checked against AMFI's own file on 3 dates × 4 funds; all 12 match. This is
#214's `daily_avg`. The NAVs are net of TER, so no further TER is applied.

### Designs

Each design is vol-targeted with e_t = min(1, T / σ₂₀,t−1·√252), the 20-session realised vol lagged one session, with
the rest in the cash leg. Positions are re-traded to target every close (AT's rule), for T = 6%..20% in 1pp steps.
- **Blend:** 70/30 sleeve units of 0001 / swing. The vol is that of the 70/30 combined return (`core.vol_target_blend`).
- **0001 alone:** 100% 0001 sleeve units.
- **Swing alone:** 100% swing sleeve units.
- **Index:** the index fund.
- **Static index/cash mixes:** 40/60 to 80/20 in 5pp steps. Bought at the first close, re-weighted at each 31-March
  close after the tax payment, otherwise left to drift (AT's static rule).

### Open positions at the cut (Step 2 fix)

Applied to every frontier design that holds sleeve units. Each position open at 2024-06-28 is passed through on the
last session, before the terminal unit sale, as a realised gain. It is short-term if the position has been held 365
days or less, and long-term otherwise, with the sleeve's unit basis stepped up by the same amount, as for every other
pass-through. The terminal unit sale then taxes only the residual.
- **Swing:** the 10 ledger rows with reason `eos`, using their `net_pnl` and entry dates.
- **0001:** trades with entry ≤ 2024-06-28 < exit. Gain = qty × (close at the cut − entry basis per share).

The old convention taxed open positions by unit-lot age. The blend at 11% is reported under both conventions to bridge
to the #215 anchor.

### Metrics

- **After-tax CAGR:** the liquidation value.
- **p95 drawdown:** the 156-week p95 drawdown of the after-tax mark-to-market NAV. Stationary bootstrap of W-FRI
  returns, mean block 8, 10,000 draws (`explore_blend_drawdown_sizing.boot_dd`).
- **Excess Sharpe:** rf 6.5%.

### Pass and ranking rules

**A point passes the cap if its p95 drawdown is ≤ 25%.** "Best at the cap" is the passing point with the highest
after-tax CAGR, over all designs and both cash legs. The margin is reported against:
- the best passing point of every other design;
- the best passing static mix.

A point is **dominated** if another point has after-tax CAGR ≥ and p95 ≤, with at least one strict.

### Step 4 — vol-target tax layer

Index at 11% against static 65/35, on #215's own price set (proxy liquid), so that its 5.04 − 2.22 = 2.82pp tax
difference is the thing split. Each book's tax pp (pre-tax CAGR − after-tax CAGR) is split by rupee share of tax. Tax
is allocated per tax period and per class, in proportion to each group's positive net gain. The groups are:
- in-run rebalance sales, index fund;
- in-run rebalance sales, liquid fund (slab);
- terminal liquidation, index fund;
- terminal liquidation, liquid fund.

The short-term and long-term shares of realised equity gain are also reported.

### Step 5 — mission test

**Book.** The blend at its cap-passing vol: the highest T whose p95 is ≤ 25%, for each cash leg.

**Benchmarks:**
- **(a)** static 65/35 on the same cash leg;
- **(b)** the Nifty Midcap150 Momentum 50 TRI held as the index fund (TRI less TER) at 100%, through the same simulator.
  Buy-and-hold means no tax until exit.

**Windows.**
- Rolling 3-year windows, starting on the first session of each month from 2019-03, for every start whose 3-year end
  is on or before 2024-06-28.
- Each window is a **continuous slice** of the one full after-tax run (never a fresh-capital re-run; CLAUDE.md).
- The metric is excess Sharpe (rf 6.5%) of the daily after-tax mark-to-market returns in the slice.

**Reported:**
- the share of windows in which the blend's excess Sharpe is greater than the benchmark's;
- the median and worst margin;
- the number of non-overlapping 3-year windows.

**Dependence.** One path. Adjacent windows share 35 of 36 months.

### Anchors

Read from the committed JSON (`2026-11-18_after_tax_comparison.json`, `2026-11-19_blend_cost_tax.json`), reproduced
on #215's proxy price set with the old open-position convention:
- blend at 11%: 19.26 / 26.46;
- static 65/35: 23.02 / 24.81;
- index at 11%: 20.41;
- swing alone: 18.82;
- 0001 alone: 35.92;
- 0001 full run: 21.73 / 1.130.

The script runs under PYTHONHASHSEED 0 and 7, and its output must be byte-identical. It stops only on an unexplained
miss or a miss over 5% relative.

---

## Results

**Reproduce:** `python pipelines/diagnostics/explore_after_tax_frontier.py` →
`2026-11-19_after_tax_frontier.json`. It is byte-identical under PYTHONHASHSEED 0 and 7 (sha256 `d0567d45…`)
[measured].

### Anchors — all exact [measured]

| anchor | committed JSON | reproduced |
|---|---|---|
| blend at 11%, after-tax / p95 | 19.26 / 26.46 | 19.26 / 26.46 |
| static 65/35 | 23.02 / 24.81 | 23.02 / 24.81 |
| index at 11% | 20.41 / 26.34 | 20.41 / 26.34 |
| swing alone | 18.82 | 18.82 |
| 0001 alone | 35.92 | 35.92 |
| 0001 full run | 21.73 / 1.130 | 21.73 / 1.130 |

### Step 2 — the swing after-tax fix [measured, `step2_swing_fix`]

At the cut there are 10 open swing positions, carrying a gain of ₹11.52L at book scale. **6 of them, holding ₹3.90L
of that gain, have been held 365 days or less**, and are now taxed short-term. The other 4 are long-term, by their own
age.

| | old (unit-lot age) | fixed (position age) | change |
|---|---|---|---|
| **swing alone, after-tax CAGR** | 18.82% | **18.57%** | **−0.25pp** |
| swing alone, tax | ₹3,91,253 | ₹4,46,847 | +₹55,594, matching #215's estimate of ≈ ₹55k |
| 0001 alone, same fix | 35.92% | 35.53% | −0.39pp |
| blend at 11%, same fix | 19.26% | 19.37% | +0.11pp |

The blend's figure rises. Its terminal unit lots were all short-term, and the 4 old swing positions are now long-term.

### Step 3 — the frontier [measured, `frontier.points`]

The cash legs over the window: real liquid 5.36%/yr, real arbitrage 6.05%/yr. The arbitrage leg beats the liquid leg
at every point: it earns more pre-tax and is taxed as equity, not at the 30% slab.

**Best passing point (p95 ≤ 25%) of each design, arbitrage cash leg:**

| design | vol / mix | after-tax CAGR | p95 156w DD | excess Sharpe | dominated? |
|---|---|---|---|---|---|
| **static index/arbitrage 65/35** | 65/35 | **23.25** | 24.73 | 1.322 | no |
| 0001 vol-targeted | 10% | 20.20 | 23.27 | 1.087 | yes |
| index vol-targeted | 10% | 19.58 | 24.38 | 1.071 | yes |
| blend 70/30 vol-targeted | 10% | 18.36 | 24.30 | 0.972 | yes |
| swing vol-targeted | 8% | 10.17 | 22.68 | 0.423 | yes |

With the liquid leg the order is the same: 65/35 at 22.79, 0001 at 19.71, index at 19.16, blend at 17.89, swing at 9.53.

**Best at the cap: static 65/35 with the arbitrage leg, at 23.25% after tax.** Its margin over each other design's
best passing point:
- blend: **+4.89pp**
- 0001 alone: +3.05pp
- index vol-targeted: +3.67pp
- swing alone: +13.08pp

**Dominated points.** Every vol-targeted point that passes the cap is dominated by a static index/arbitrage mix, and
so is every liquid-leg point. The only exception is 0001 at 6% (14.20 / 14.1), which no other point dominates.

The undominated set is:
- static/arbitrage 40/60 to 80/20;
- 0001 at 6% and at 16–20%;
- the 100% index fund held to the end, at 31.07 / 37.4.

Every undominated point above 14.1 except the static mixes breaches the cap.

Full grid (after-tax CAGR / p95; * = passes the cap):

| design (arbitrage leg) | 6% | 8% | 10% | 11% | 12% | 15% | 20% |
|---|---|---|---|---|---|---|---|
| blend | 13.33/14.8* | 15.90/20.0* | 18.36/24.3* | 19.53/26.3 | 20.66/28.0 | 23.84/31.6 | 27.03/36.0 |
| 0001 | 14.20/14.1* | 17.33/18.9* | 20.20/23.3* | 21.58/25.1 | 22.95/26.6 | 26.63/30.5 | 31.00/35.6 |
| swing | 9.20/16.4* | 10.17/22.7* | 11.32/28.4 | 11.87/30.8 | 12.32/33.2 | 14.53/37.3 | 16.14/41.4 |
| index | 14.20/15.1* | 17.05/20.1* | 19.58/24.4* | 20.51/26.2 | 21.22/27.9 | 24.09/31.4 | 27.15/35.5 |

| static index/arbitrage | 40/60 | 50/50 | 60/40 | 65/35 | 70/30 | 80/20 |
|---|---|---|---|---|---|---|
| after-tax / p95 | 16.96/14.9* | 19.54/18.9* | 22.03/22.8* | 23.25/24.7* | 24.45/26.6 | 26.77/30.3 |

### Step 4 — the vol-target tax layer [measured, `step4_tax_layer`, #215's proxy price set]

Index at 11% loses 5.036pp to tax; static 65/35 loses 2.221pp. **The difference is 2.815pp**, split as follows:

| component | index at 11% | static 65/35 | difference |
|---|---|---|---|
| **tax on rebalance sales**, index fund | 4.391 | 0.223 | **+4.168** |
| tax on rebalance sales, liquid fund (slab) | 0.472 | 0.026 | +0.446 |
| **tax at exit** (terminal liquidation), index fund | 0.131 | 1.592 | **−1.461** |
| tax at exit, liquid fund | 0.042 | 0.381 | −0.339 |
| total | 5.036 | 2.221 | **+2.815** |

Entry carries no tax in either book. Rebalance sales total **+4.61pp** and the exit **−1.80pp**. The vol target pays
more than all of its gap in rebalance tax, and gets some of it back at exit, because little gain is left in its lots.

**Short- vs long-term realised equity gain:**
- index at 11%: **100% short-term** (₹39.6L short-term, ₹0 long-term). Daily re-trading never lets a lot reach 366
  days.
- static 65/35: **≈ 100% long-term** (₹719 short-term, ₹42.5L long-term).

### Step 5 — the mission test [measured, `step5_mission_test`]

The blend's highest cap-passing vol is **10%** on both cash legs. There are 28 rolling 3-year windows, starting
2019-03 to 2021-06 in monthly steps. **Only 1 non-overlapping 3-year window fits in the 5.3-year sample.**

| blend at 10% vs | cash leg | blend wins | median margin (excess Sharpe) | worst margin (window start) |
|---|---|---|---|---|
| static 65/35 | arbitrage | **0 of 28** | −0.426 | −0.767 (2020-12) |
| static 65/35 | liquid | 0 of 28 | −0.446 | −0.779 (2020-12) |
| TRI held as the index fund, after tax | arbitrage | **0 of 28** | −0.429 | −0.753 (2020-12) |
| TRI held as the index fund, after tax | liquid | 0 of 28 | −0.476 | −0.796 (2020-12) |

The best window for the blend still loses: by −0.143 against 65/35 and −0.089 against the TRI (arbitrage leg).
