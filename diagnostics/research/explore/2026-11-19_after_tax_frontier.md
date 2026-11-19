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
