# G1 Weinstein — GATE-1 census (entry count + ext-at-entry)

**MEASUREMENT — 0 trials, 0 screens spent. No backtest, no capital, no config change,**
**no forward-wall read. Standing counts unchanged: screens 12 · sealed opens 1 · n_trials 138.**

Weekly panel from `corrected_universe()`: 336382 rows / 788 tickers, sha256 `2b5d6592966bf7ef…`. Window from 2017-01-01.
Spec + every ambiguity interpretation frozen in the module docstring; nothing swept.

Reproduce: `python scripts/diag_g1_weinstein_gate1.py`

## (a) Entry-count census

**211 signals** clearing the full spec on PIT members with ADV ≥ ₹5cr over 9.4 years = **22.5 signals/year** (174 distinct names).

| year | all_signals | pit_member | member_and_ADV5cr | distinct_names |
|---|---|---|---|---|
| 2017 | 4 | 3 | 2 | 2 |
| 2018 | 14 | 9 | 9 | 9 |
| 2019 | 30 | 26 | 18 | 18 |
| 2020 | 20 | 16 | 13 | 13 |
| 2021 | 8 | 7 | 7 | 7 |
| 2022 | 22 | 21 | 21 | 21 |
| 2023 | 88 | 64 | 64 | 64 |
| 2024 | 42 | 29 | 29 | 29 |
| 2025 | 43 | 33 | 33 | 33 |
| 2026 | 23 | 15 | 15 | 15 |
| TOTAL | 294 | 223 | 211 | 174 |

### Leg-by-leg attrition (which leg costs what)

| leg | name_weeks | pct_of_universe | survival_vs_prev |
|---|---|---|---|
| universe (weeks with a 30w SMA + a full base window) | 293042 | 100.0 | — |
| + stage-1 base: 30w SMA flat | 54752 | 18.684 | 18.68 |
| + stage-1 base: price range-bound | 20872 | 7.1225 | 38.12 |
| + close > base ceiling (the breakout) | 1084 | 0.3699 | 5.19 |
| + close > 30w SMA | 1084 | 0.3699 | 100.0 |
| + 30w SMA flattened / turning up | 950 | 0.3242 | 87.64 |
| + Mansfield RS >= 0 | 821 | 0.2802 | 86.42 |
| + Mansfield RS rising (4wk) | 800 | 0.273 | 97.44 |
| + volume >= 2x 10wk avg | 325 | 0.1109 | 40.62 |
| + one-signal-per-base cooldown | 294 | 0.1003 | 90.46 |

## (b) Ext-at-entry vs the slow weekly line

Median ext vs the 44w SMA at the modelled breakout close: **17.54%** (mean 18.16%); share below 5%: **0.0%**. Median ext vs Weinstein's own 30w line: 16.85%. Median modelled stop distance (entry → base low): 24.74%; median base range 27.01%.

| band | N | share_pct |
|---|---|---|
| <0 (below wk line) | 0 | 0.0 |
| 0-5% | 0 | 0.0 |
| 5-10% | 7 | 3.3 |
| 10-15% | 59 | 28.0 |
| 15-20% | 77 | 36.5 |
| 20-25% | 47 | 22.3 |
| >25% | 21 | 10.0 |

### Comparison set (median ext vs the 44w SMA, from `ext_band_census.md`)

| funnel | median_ext_pct |
|---|---|
| touch44 (incumbent) | 8.72 |
| trend_pullback | 22.1 |
| cup_handle | 28.48 |
| 0084/0085 six-step | 29.53 |
| double_bottom | 31.64 |
| vcp (zoo) | 33.24 |
| box | 33.78 |
| sr_pivot | 37.87 |

Signal ledger: `research/exports/g1_weinstein_signals.csv` (294 rows, all legs passed).
