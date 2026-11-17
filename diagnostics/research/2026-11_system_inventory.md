# 2026-11 — System inventory and common scorecard (redesign study, Phase 1–2)

**Tier:** MEASURE. Analysis only. No live config, engine or trial-counter change, nothing tuned, and no new read of the
sealed slice B (2024-07-01..2026-06-30) for the swing books.
**Reproduce:** `INVENTORY_CACHE=<dir> python pipelines/diagnostics/diag_system_inventory_2026_11.py` →
`2026-11_system_inventory.json` (every table below). Benchmark histories are committed in
`diagnostics/research/benchmarks/tri/`.

**Conventions, the same for every strategy, blend and benchmark**
- Capital ₹10L. CAGR by calendar time (ADR-0014). Sharpe and Sortino on daily returns × √252, risk-free 0.
- Every window is a continuous slice of one full run, re-based at the window start.
- Costs are each engine's own coded stack: brokerage, STT on both legs and tiered slippage, all from the same config
  constants. **No capital-gains tax is deducted from any strategy.** Index benchmarks are net of a 0.4% expense ratio.
- Each strategy runs exactly as its spec defines it. Specification notes are listed under Step 1.

## 1. Strategy inventory

| name | engine / entry point | spec | status | last validation | holds / exits | universe | cadence | forward record | open defects and restatements since validation |
|---|---|---|---|---|---|---|---|---|---|
| **Live swing, Grade A** (weekly-swing 0094 rank, exit config P) | `scripts/run_bhanushali_weekly_rank.py` via `scripts/run_bhanushali_cron.py` | `forward/prereg_swing.md`, `models/bhanushali_weekly/config.json` | **live** (paper capital per §3; the owner trades from its cards) | trial 0094, 2026-07-06; certification pinned 2026-08-09 | up to 5 Grade-A 44-week-SMA pullbacks a week. Exit: 40% at +2R, 40% on a blow-off week, 20% runner to a weekly close under the 44-week SMA; stop on the weekly close | PIT Nifty-500 | weekly scan (Saturday) | `results/signals_history_weekly.json`, `paper_portfolio_weekly.json`, `portfolio_history_weekly.csv`, from 2026-07-06 | Exit changed to config P and three caps added 2026-07-15/16, after 0094. PIT membership gate added 2026-10-13. 7 approved history restatements (retroactive entrants 10-19; holiday-dated entries 11-09). h5-30 KILL (0151, 2026-11-13), which also recorded the live book at median Sharpe −0.41 on sealed B |
| **Base-swing, all grades** | same engine, grade gate off | `forward/prereg_swing.md` §2, §4 | watched | none of its own (comparator for §4) | as above, all grades, strongest CRS first | PIT Nifty-500 | weekly | `results/base_swing_forward.json`, from 2026-07-04 | Held identical positions to Grade A on every session so far (§12), so §4 cannot yet separate them |
| **Cross-sectional momentum** (pre-reg 0001) | `nq/engine/rebalance_book.py` via `pipelines/research/run_0001_xsec_momentum.py` | `research/0001-xsec-momentum/prereg.md`, `docs/MOMENTUM_ENGINE_DESIGN.md` | watched, not capital | run 4, 2026-08-07 (all 7 primary gates pass) | top 30 mid-band names by NSE normalised momentum score, equal weight, 5% cap. Exit only by falling past rank 45; no stop, no target | PIT Nifty-500, turnover rank 101–250 | monthly, last session | **none** | Corrected 2026-08-10: the "1.5× cost" line had been the same run reported twice; re-measured at −1.04pp CAGR. CAGR restated 22.17% → 21.73% (ADR-0014). PBO 0.452 is close to a coin flip; planning drawdown −59.3% (Monte Carlo p99); DSR was read at a counter of 2. No independent second implementation of the engine. Forward wall never logged it (audit 2026-08-11/12). ENG-01 no-trade band tested and not adopted |
| **Long-horizon trend** (baseline_v1; low-debt trend momentum) | `nq/engine/portfolio.py::simulate` via `nq.runner.research.run_backtest` | `long_horizon/STRATEGY.md`, `models/long_horizon/config.json` | paper (forward-wall base arm); replaced as the live product by the swing in July 2026 | baseline_v1 pinned 2026-07-01 | top 15 by 200-day trend slope, 0 ≤ D/E < 1.5. Exit on ATR stop, profit target, trailing stop or 63-day cap; minimum hold 10 days | PIT Nifty-500, ADV ≥ ₹5 cr, solvent | daily | `results/forward_wall.csv` (base, veto, drift arms) from 2026-08-12; `results/paper_portfolio.json` | baseline_v0 (26.1% / 1.02) → v1 (15.46% / 0.667): data vintage. Calendar correction 2026-08-06 → 14.88% / 0.647, recorded, not re-anchored. Survivorship backfill and re-anchor still pending. Excludes financials (solvency screen) |
| ↳ veto-0.1 and drift-degross arms | same, wall arms | `forward/prereg.md` | watched | — | base book with a factor-residual veto, or a drift-based de-gross | same | daily | `results/forward_wall.csv` | Veto arm needs factor data that stopped the wall until 2026-08-12 |
| **Low-vol sleeve** (0081) and **blend-hybrid 60/40** (0107) | same engine with an inverse-63-day-volatility rank; `scripts/run_blend_paper.py` | `forward/prereg_swing.md` amendments 2026-07-26 and 2026-08-14; finding 0107 | watched (observational, no capital) | 0107, 2026-07-26, in-sample only (0081 DSR 0.315) | top 15 lowest-volatility names, same exits as long-horizon; blend = 0.60 swing / 0.40 low-vol | as long-horizon | daily; blend weight fixed | `results/blend_hybrid_paper.json`, from 2026-07-04 | Logger crashed for about 7 weeks (n_points 0) until 2026-09-28. Muhurat date mismatch 2026-11-08, fixed in #177 |
| **Breadth-50 watched book** (EW / SW / SW-accum) | `nq/research/breadth50.py` | breadth-50 proposal §4 | watched | none: its spec forbids an in-sample performance evaluation | 50 names from the weekly CRS breadth list, equal or strength weighted | PIT Nifty-500 | weekly | `results/breadth50_forward.json`, from 2026-08-16 | — |
| Zoo shadow book (0131) | `results/zoo_shadow_book.json` | pre-reg 0131 | observational | — | swing plus pattern-zoo entries, traded by nobody | — | weekly | next substantive read 2027-04-01 | never a Sharpe race, by its own spec |
| Shadow breakeven exit | `scripts/run_bhanushali_cron.py` | `2026-11-03_giveback_solution_map.md` | observational | — | live swing with the stop moved to entry at +1R | — | weekly | `results/shadow_exit_forward.json`, from 2026-11-09 | — |
| Weak-market mean-reversion sleeve | none yet | `forward/drafts/2026-11-13_amendment_mr_sleeve_DRAFT.md` | **draft, unsigned, never run** | — | — | — | — | none | — |
| v1 14-day ML ensemble | deleted | `docs/survivorship_fix.md` era | **killed / retired** 2026-06-25 | — | — | — | — | — | survivorship fix declined 2026-04-21; replaced by long-horizon |
| 0013 exposure overlay · 0014 mean-reversion sleeve · 0016 portfolio optimizer | on the v1 model | `diagnostics/research/preregistry/0012`–`0016` | **killed** 2026-06-06 / 06-07 / 06-08 | — | — | — | — | — | all measured on the retired v1 book, not on any current one |
| h5-30 (swing, caps relaxed) | swing engine | pre-reg 0151 | **killed** 2026-11-13 | sealed read S4 | — | — | — | — | — |

**Specification notes**
- **Swing start date.** The swing spec has no fixed backtest start; the documented default of 2019-01-01 is used.
- **Long-horizon universe.** The corrected universe is used as-is. The anchor producer documents it as identical to
  the pinned data for this book.
- **Momentum in the design charter vs the pre-registration.** The charter mentions a top-60 exit buffer and plain
  12-1 momentum. The pre-registration fixes rank 45 and the NSE normalised score. The pre-registration is used.
- **Killed strategies** are listed but not run.

## 2. Common scorecard

**Common window: 2019-03-01 to 2024-06-28.** It is the longest window every runnable strategy supports. The swing books start in January 2019 (their documented start; the 20-path tool reports from March 2019), and their prices are cut at 2024-06-30 so that sealed slice B is not read. Every figure is a continuous slice of one full run, re-based to ₹10L.

| strategy | CAGR | Sharpe | Sortino | worst DD | longest DD (weeks) | Calmar | turnover (× equity / yr) | avg positions |
|---|---|---|---|---|---|---|---|---|
| Live swing (Grade A) | 20.59% | 1.025 | 1.308 | -40.11% | 79.9 | 0.51 | 2.5 | 7.1 |
| Base-swing (all grades) | 26.01% | 1.272 | 1.633 | -40.11% | 62.7 | 0.65 | 2.7 | 8.2 |
| Cross-sectional momentum (0001) | 43.07% | 1.85 | 2.022 | -37.17% | 33.9 | 1.16 | 3.58 | 31.2 |
| Long-horizon trend (baseline_v1) | 33.95% | 1.209 | 1.449 | -39.16% | 77.1 | 0.87 | 10.77 | 12.8 |
| Low-vol sleeve (0081) | 12.9% | 0.91 | 1.12 | -29.68% | 120.9 | 0.43 | 7.4 | 13.8 |
| Blend-hybrid 60/40 swing/low-vol (0107) | 17.86% | 1.096 | 1.284 | -35.8% | 79.9 | 0.5 | — | — |

Single unperturbed path each. Turnover = cost basis of all lots opened per year, as a multiple of mean equity.

**20-path ensemble (median [5th, 95th]).** `nq/lab/ensemble.py` supports the swing engine only; the momentum and long-horizon engines have no path-perturbation harness, so their rows above are single paths.

| strategy | CAGR | Sharpe | worst DD |
|---|---|---|---|
| Live swing (Grade A) | 26.09% [20.70, 32.94] | 1.25 [1.03, 1.41] | -37.48% [-47.67, -33.17] |
| Base-swing (all grades) | 28.57% [25.51, 33.09] | 1.36 [1.23, 1.55] | -32.66% [-40.01, -31.17] |

**Annual returns, % (2019 from March, 2024 to June):**

| strategy | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|
| Live swing (Grade A) | +1.3 | +25.4 | +39.9 | -3.9 | +30.7 | +21.5 |
| Base-swing (all grades) | +1.3 | +35.3 | +25.7 | +3.9 | +67.1 | +14.6 |
| Cross-sectional momentum (0001) | +11.7 | +52.1 | +90.4 | +4.3 | +53.5 | +30.1 |
| Long-horizon trend (baseline_v1) | +11.3 | +28.6 | +65.2 | -3.5 | +72.2 | +20.8 |
| Low-vol sleeve (0081) | -1.9 | +34.2 | +10.9 | -13.1 | +25.9 | +19.5 |
| Blend-hybrid 60/40 swing/low-vol (0107) | +0.2 | +29.5 | +28.1 | -7.4 | +29.0 | +20.9 |

### Extended window 2019-03-01 to 2026-06-29 (books whose own validation already read 2024-07..2026-06)

The momentum (0001, window to 2026-06-30), long-horizon (baseline_v1, to 2026-06-30) and low-vol (0107, to 2026-06) validations each already covered this period, so re-running them reads nothing new. The swing books are excluded.

| strategy | CAGR | Sharpe | Sortino | worst DD | longest DD (weeks) | Calmar | 2024 | 2025 | 2026 H1 |
|---|---|---|---|---|---|---|---|---|---|
| Cross-sectional momentum (0001) | 31.4% | 1.443 | 1.647 | -37.17% | 77.4 | 0.84 | +40.5 | -0.5 | +2.1 |
| Long-horizon trend (baseline_v1) | 20.5% | 0.824 | 1.039 | -46.26% | 102.4 | 0.44 | +3.5 | +1.6 | -5.1 |
| Low-vol sleeve (0081) | 12.02% | 0.883 | 1.13 | -29.68% | 120.9 | 0.4 | +34.5 | +8.7 | -1.6 |

**Reproduction check.** Momentum full window: 21.73% / 1.13 / -37.17%, against the published 21.73% / 1.130 / −37.17%. Long-horizon full window: 14.52% / 0.647 / -46.26%, against the pinned 15.46% / 0.667 / −46.26% and the recorded calendar-corrected 14.88% / 0.647. The Sharpe matches the corrected figure; the CAGR is lower because this report annualises by calendar time (ADR-0014) and the anchor harness does not.

## 3. Forward records

| strategy | record | dates | return | worst DD | trades | backtest, same-length windows: median [5th, 95th] | realised percentile |
|---|---|---|---|---|---|---|---|
| Live swing (Grade A) | paper book | 2026-07-06 → 2026-11-08 | -3.97% | -13.9% | 55 (38 closed) | 7.9% [-16.2, 31.9] over 18 weeks | 22th |
| Base-swing (all grades) | watched | 2026-07-04 → 2026-11-08 | same NAV as Grade A | -13.9% | 7 closed (capped book) | — | — |
| Long-horizon, base arm | forward wall + paper book | 2026-08-12 → 2026-11-13 | -0.73% (veto arm 0.56%, drift arm -0.77%) | -14.33% | 49 (paper book, lifetime) | 6.4% [-20.8, 30.2] over 13 weeks | 33rd |
| Blend-hybrid 60/40 | watched | 2026-07-04 → 2026-11-06 | -5.55% (swing leg -3.9%, low-vol leg -4.76%) | — | — | — | — |
| Breadth-50 watched book | watched, forward-only | 2026-08-16 → 2026-11-13 | EW -2.96%, SW-accum -3.58% | — | 12 weekly points | none: its spec forbids an in-sample evaluation | — |
| Cross-sectional momentum (0001) | **none** | — | — | — | — | — | — |
| ↳ **replay, not a record** | Yahoo prices, fresh ₹10L | 2026-08-07 → 2026-11-13 | -0.22% | -10.87% | 88 | 8.5% [-13.1, 28.5] over 14 weeks | 26th |

- **Momentum has no forward record.** No model-wall log exists for 0001. The wall that would carry it was blocked by the veto arm's factor data (audit 2026-08-11/12). The replay row uses Yahoo auto-adjusted, 481 current PIT Nifty-500 members, fresh ₹10L on 2026-08-07; it averaged 23.7 positions.
- **The swing record is the engine run on live data**, rebuilt every scan, so a dated replay equals it by construction. The comparison shown is against the distribution of same-length windows in each book's backtest.
- **Nifty 50 (price) over 2026-08-07 → latest:** 2.33%.

## 4. Correlation and fixed blends (descriptive)

**All weeks** (278 weeks, common window, weekly returns):

| | swing | base-swing | momentum | long-horizon | low-vol |
|---|---|---|---|---|---|
| swing | 1.00 | 0.82 | 0.70 | 0.60 | 0.63 |
| base-swing | 0.82 | 1.00 | 0.76 | 0.65 | 0.66 |
| momentum | 0.70 | 0.76 | 1.00 | 0.84 | 0.71 |
| long-horizon | 0.60 | 0.65 | 0.84 | 1.00 | 0.59 |
| low-vol | 0.63 | 0.66 | 0.71 | 0.59 | 1.00 |

**Weeks when the Nifty was below its 40-week SMA** (54 weeks, common window, weekly returns):

| | swing | base-swing | momentum | long-horizon | low-vol |
|---|---|---|---|---|---|
| swing | 1.00 | 0.93 | 0.86 | 0.75 | 0.86 |
| base-swing | 0.93 | 1.00 | 0.86 | 0.76 | 0.82 |
| momentum | 0.86 | 0.86 | 1.00 | 0.91 | 0.80 |
| long-horizon | 0.75 | 0.76 | 0.91 | 1.00 | 0.68 |
| low-vol | 0.86 | 0.82 | 0.80 | 0.68 | 1.00 |

A week counts as "below" when the prior Friday's Nifty close was under its 40-week SMA.

**Three fixed blends, no weight search** (common window):

| blend | CAGR | Sharpe | Sortino | worst DD | longest DD (weeks) | Calmar | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (i) 70% momentum / 30% swing | 36.28% | 1.716 | 1.864 | -36.63% | 45.4 | 0.99 | +8.6 | +44.0 | +74.2 | +2.1 | +46.5 | +27.6 |
| (ii) 50 / 50 | 31.77% | 1.562 | 1.754 | -36.48% | 72.1 | 0.87 | +6.5 | +38.6 | +63.9 | +0.5 | +41.9 | +25.9 |
| (iii) 70 / 30 with a 15% volatility target | 29.14% | 1.801 | 2.025 | -22.85% | 46.0 | 1.27 | +7.2 | +41.6 | +54.5 | -1.3 | +44.8 | +16.6 |

Rules: fixed weights re-set daily, no cost charged for moving money between sleeves; vol target uses the 20-session realised volatility of the combined book up to the prior session, exposure = min(1, 15% / vol), the rest in cash at 6% a year. Blend (iii) averaged 85% invested, with a minimum of 22%.

## 5. Investable benchmarks (total-return indices)

Source: niftyindices.com total-return index histories, fetched 2026-11-13 and committed under `diagnostics/research/benchmarks/tri/`. An index-fund expense ratio of **0.4% a year** is deducted (the middle of the 0.3–0.5% range). No tracking error or entry/exit cost is modelled.

| benchmark, net of fee | CAGR | Sharpe | Sortino | worst DD | longest DD (weeks) | Calmar | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nifty 50 | 16.99% | 0.94 | 1.083 | -38.31% | 55.4 | 0.44 | +12.9 | +15.7 | +25.1 | +5.3 | +20.8 | +11.1 |
| Nifty 500 | 19.55% | 1.081 | 1.186 | -38.15% | 57.9 | 0.51 | +10.0 | +17.4 | +31.1 | +3.8 | +26.4 | +16.5 |
| Nifty Midcap 150 | 26.6% | 1.36 | 1.458 | -38.48% | 46.9 | 0.69 | +4.6 | +25.1 | +47.6 | +3.5 | +44.0 | +22.1 |
| Nifty Midcap150 Momentum 50 | 33.77% | 1.588 | 1.724 | -36.01% | 46.4 | 0.94 | +7.8 | +26.4 | +77.6 | -0.1 | +51.9 | +28.4 |
| Nifty 200 Momentum 30 | 25.74% | 1.21 | 1.395 | -33.98% | 92.4 | 0.76 | +7.5 | +19.5 | +53.2 | -5.8 | +41.1 | +29.5 |
| Nifty Alpha Low-Volatility 30 | 19.65% | 1.179 | 1.351 | -31.0% | 82.0 | 0.63 | +7.6 | +15.2 | +30.4 | -3.5 | +38.5 | +20.4 |

**Extended window 2019-03-01 to 2026-06-29:**

| benchmark, net of fee | CAGR | Sharpe | worst DD | Calmar | 2024 | 2025 | 2026 H1 |
|---|---|---|---|---|---|---|---|
| Nifty 50 | 12.27% | 0.759 | -38.31% | 0.32 | +9.6 | +11.4 | -8.0 |
| Nifty 500 | 14.33% | 0.87 | -38.15% | 0.38 | +15.8 | +7.3 | -3.4 |
| Nifty Midcap 150 | 20.15% | 1.098 | -38.48% | 0.52 | +24.0 | +5.6 | +1.9 |
| Nifty Midcap150 Momentum 50 | 23.68% | 1.182 | -36.01% | 0.66 | +31.8 | -3.8 | +2.1 |
| Nifty 200 Momentum 30 | 16.11% | 0.838 | -33.98% | 0.47 | +20.8 | -4.9 | -0.5 |
| Nifty Alpha Low-Volatility 30 | 13.09% | 0.871 | -31.0% | 0.42 | +17.4 | -0.1 | -2.8 |

## 6. Execution reality

The app's `execution_events` table holds **0 rows** (read-only query on the production database, 2026-11-13). No real
fill has ever been recorded, so every "live" number in this repo is a model or paper number.

What logging fills would take (nothing was built):
1. The backend already has the endpoints: `POST /api/execution/buy`, `/sell` and `/correct`, writing an append-only ledger.
2. This Week already has "Record buy" and "Record sell" buttons that call them. They need to be used for each fill, with the real price and quantity.
3. For past trades, enter the 55 live trades' fills once, from broker contract notes.
4. Then a slippage report (model entry vs fill, stop vs exit) becomes a query on that table joined to `signal_snapshots`.

## Facts for the redesign decision

1. **Strongest on risk-adjusted return, common window (2019-03 to 2024-06, single path):** cross-sectional momentum
   0001, with Sharpe 1.85, CAGR 43.1% and worst drawdown −37.2%. Next: base-swing 1.27, long-horizon 1.21, live swing
   1.03 (20-path median 1.25), low-vol 0.91.
2. **Through June 2026**, for the three books whose validations already covered that period: momentum 31.4% / 1.44,
   long-horizon 20.5% / 0.82, low-vol 12.0% / 0.88. Momentum made −0.5% in 2025 and +2.1% in 2026 H1; long-horizon
   +1.6% and −5.1%.
3. **Against the Nifty Midcap150 Momentum 50 index, net of a 0.4% fee** (33.8% / 1.59 / −36.0% on the common window):
   only momentum 0001 is ahead on both CAGR and Sharpe. Long-horizon matches its CAGR (34.0%) at a lower Sharpe (1.21).
   The live swing is below it on both, on the single path (20.6% / 1.03) and at the 20-path median (26.1% / 1.25).
   Through June 2026 the index is 23.7% / 1.18, against momentum's 31.4% / 1.44.
4. **These comparisons are before capital-gains tax on the strategies.** Momentum's own validation puts its full-window
   CAGR at 21.73% gross and 18.16% after 20% STCG. An index fund realises no gains internally.
5. **Best fixed blend:** on Sharpe and drawdown, (iii) 70/30 with the 15% volatility target, at 1.80 / 29.1% /
   −22.9%. On CAGR, (i) 70/30 at 36.3% / 1.72 / −36.6%. Momentum alone (43.1% / 1.85) is above blends (i) and (ii)
   on both measures; only the volatility target lowers the drawdown.
6. **The strategies are not diversifying each other.** Weekly return correlation between swing and momentum is 0.70,
   rising to 0.86 in weeks when the Nifty is below its 40-week SMA. Every pair is between 0.59 and 0.84 overall, and
   between 0.68 and 0.93 in weak weeks.
7. **Forward vs backtest:**

   | book | forward period | realised | backtest median, same-length windows | percentile |
   |---|---|---|---|---|
   | live swing | 18 weeks | −4.0% | +7.9% | 22nd |
   | long-horizon wall | 13 weeks | −0.7% | +6.4% | 33rd |
   | momentum (**replay, not a record**) | 14 weeks | −0.2% | +8.5% | 26th |

   All three are below median and inside their 5th–95th range. The Nifty 50 rose 2.3% from 2026-08-07.
8. **Momentum 0001 has no forward record.** Its open items since validation: PBO 0.452, a planning drawdown of −59.3%,
   no independent second implementation, and a window that contains no 2008-class event.
9. **Only the swing engine has a path-noise ensemble.** The momentum and long-horizon numbers are single paths with no
   noise band. On the swing, single paths have moved by 0.2–0.3 Sharpe between paths.
10. **Zero real fills are recorded.** The common window is also the period every one of these books was developed on.

## Limits

- The common window starts in March 2019 and ends in June 2024, a strong period for Indian midcaps. The Midcap 150
  index itself made 26.6% a year in it.
- Turnover is measured the same way for every engine, but the engines' own "turnover" fields are trades per year, so
  they will not match.
- Blends re-set weights daily at no cost. A real two-sleeve book would pay to rebalance.
- The momentum replay uses Yahoo prices and today's index membership file; it averaged 23.7 positions, against 31 in
  the backtest.
- Index funds are modelled as the total-return index less a flat fee. Tracking error and the funds' launch dates are
  ignored; a fund tracking an index cannot have been held before the fund existed.

Standing counts: screens 24 · sealed opens 4 · n_trials 3 (unchanged).
