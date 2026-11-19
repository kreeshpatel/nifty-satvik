# Stress suite with negative controls — swing, 0001 and the 70/30 blend at 11% — 2026-11-19

**Class: MEASUREMENT.** Owner request ("prompt 2"), built on `research/robust-sizing` (prompt 1). No live rule, no trial
counter, no sealed read, nothing adoptable: every scenario damages or nulls an already-adopted book. **Standing counts:
screens 24 · sealed opens 4 · n_trials 3** (from `diagnostics/research/n_trials.json` and
`diagnostics/research/label_screen_ledger.md`; unchanged).

**Mission line.** The mission demands a book that keeps its risk-adjusted edge and its −25% drawdown bar under
real-world execution damage. This measures how much of the swing, 0001 and 11%-blend Sharpe survives seven execution and
path shocks, and first checks with negative controls that the harness cannot manufacture edge from noise.

---

## Step 0 — pass criteria, written and committed before any shocked or control run

These are fixed here and not revisited after results. Interpretations I had to make are marked **(interp.)** with the
reason, so the owner can overrule them; they were made before any shock or control was run.

**Shocks (S1–S7), each on all three books, 20 paths.**
- The 20 paths are `nq.lab.ensemble.draw_perturbations(20, DEFAULT_SEED)` (cost ±10 bp per side, start in the first ~20
  sessions), the same draws as prompt 1. Each shock is applied on top of every path, so shocked and unshocked books are
  paired path by path.
- **A shock is PASSED for a book if the median Sharpe over the 20 shocked paths is ≥ 50% of the unshocked median
  Sharpe.** "Sharpe" here is the harness's Sharpe vs cash (mean/std of daily NAV returns × √252, no risk-free rate,
  `nq/lab/ensemble.py::slice_metrics`).
- **For the blend, a shock is PASSED only if, in addition, the 156-week bootstrap p95 drawdown is ≤ 25%.** That is the
  median, over the 20 paths, of each path's p95. Each path's p95 comes from a stationary bootstrap of Friday-to-Friday
  returns with mean block 8 weeks and 10,000 draws (`explore_blend_drawdown_sizing.boot_dd`, the most conservative block
  in prompt 1).
- The Sharpe minus the Nifty Midcap150 Momentum 50 TRI Sharpe over the same window is reported for every cell. It is
  descriptive and carries no pass mark, because Step 0 of the request defines none.
- **Worst shock per book** = the shock with the lowest ratio of shocked to unshocked median Sharpe.

**Negative controls (N1–N3), 100 seeds each, same engine, costs and universe.**
- Seed k uses perturbation draw k of `draw_perturbations(100, DEFAULT_SEED)` and a label/ranker RNG seeded by k.
- **N1 and N2 pass** if the mean over 100 seeds is within 2 standard errors of 0 (SE = sd/√100) **and** the 95th
  percentile is below 0.3.
- **(interp.) The metric for "shows edge" is the beta-neutral appraisal ratio, not the raw Sharpe.** It is computed
  per seed as α/σ(ε)·√252 from an OLS regression of the control's daily returns on the equal-weight daily return of the
  universe the control samples from:
  - swing: PIT Nifty-500 members with a bar;
  - 0001: eligible names in the midcap size band.

  Why: a long-only book of random Indian mid/large caps over 2019–2026 earns the market's Sharpe (around 1) from beta
  alone. Under the raw-Sharpe reading, N1 and N2 would fail by construction, and that failure would say nothing about a
  harness bias. **The literal raw-Sharpe test is also reported for every control**, and if the two readings disagree it
  is listed as an owner decision.
- **N3 passes** ("clearly below base") if its median Sharpe, raw and appraisal alike, is below the 5th percentile of
  the unshocked 20-path base on that metric.
- **The suite is FAILED overall if any N1/N2 control fails on the appraisal ratio for any book, or any N3 is not clearly
  below base.** Controls run **first**. If they fail, the shocks are not interpreted, and the report stops at the
  controls.

**Anchors, reproduced before any result (rule 4)** — the script aborts on any mismatch:
- live swing Sharpe 1.025 / MaxDD −40.1%;
- 0001 21.73% / 1.130;
- blend at 15%, daily worst drawdown −22.85%;
- the patched swing engine with every shock off reproduces prompt 1's path-0 Sharpe 1.348913.

## Method — how each scenario is built (fixed with Step 0, before results)

Script: `pipelines/diagnostics/explore_stress_suite.py`. The harness files are not edited: `nq/lab/ensemble.py`,
`explore_param_sensitivity.py`, `explore_stops_are_requests.py` and `explore_blend_drawdown_sizing.py` are imported and
reused. Shocks that must act inside an engine run on a **source-patched copy** of that engine, the same technique prompt 1
used for `sma_len`. Every patched literal is asserted to occur exactly once, and with all hooks off the copy must
reproduce the unpatched path exactly.

**Books and windows.**
- **Swing:** the live book (`nq.lab.runs` config `{}`, PIT membership, prices cut 2024-06-30). Reporting window
  2019-03-01..2024-06-28, taken as a continuous slice.
- **0001:** the run of record (`run_0001_xsec_momentum.BOOK`). Each path runs from its own start to 2026-06-30. The path
  cost jitter maps to `cost_mult = 1 + δ/0.0035`, as in prompt 1.
- **Blend:** `pipelines/lifecycle/core.py::vol_target_blend` at target **0.11**: 70/30 legs, 20-session lookback, cash at
  6%. Path k pairs swing path k with 0001 path k, and both legs are windowed to 2019-03-01..2024-06-28. Under every
  shock, both legs carry the shock.

**Shocks.** Each shock is applied alone, on top of each path's cost/start draw.

| id | swing | 0001 |
|---|---|---|
| S1 latency | Entry window shifted one session later: the in-range test and the fill both use the open one session later. Every signal-driven exit (weekly-close stop, pattern tranche, SMA break, time) fills one session later than the next open. Resting limit tranches (+2R) are standing orders and are unchanged. | Ranks are read one session after each month-end rebalance date, using the month-end values, so targets fill at the open two sessions after month-end instead of one. Entries and exits alike. |
| S2 liquidity miss | Each fill candidate is dropped with p = 0.10, decided by a hash of (seed, ticker, date). A dropped order is cancelled (the entry is missed, not retried). | Each new entry (held qty 0 → >0) is dropped with p = 0.10 per (seed, ticker, rebalance). The slot stays in cash until the next rebalance. |
| S3 adversarial stop fills | Every stop exit (`stop`, `stop_part`) fills at the **low** of its fill session instead of the open. The live book's stop triggers at the weekly close and fills at the next session, so "the day it triggers intraday" is that fill session. | **N/A: 0001 has no stops.** Reported equal to base. |
| S4 costs ×3 | Every cost leg ×3 (brokerage, STT, slippage, impact), then the path jitter is added. | `cost_mult` ×3. |
| S5 ADV caps ×0.5 | **(interp.)** The swing engine has no ADV participation cap. Its only ADV-participation term is the impact adder above 0.5% of ADV, so that threshold is halved to 0.25%. | `max_adv_participation` ×0.5. |
| S6 gap shock | Applied to both books. Let G = 2 × the empirical 1st-percentile open/previous-close gap over all names in the corrected universe, 2019-03-01..2024-06-28. Each (held name, day) pair, with the name held at the prior close, is hit with p = 0.01 (RNG seed per path). A hit subtracts w × \|G\| from that day's book return, where w is the name's prior-close weight (swing: from the position log; 0001: (equity − cash)/equity/n_positions). Returns compound, so the hit is permanent and scales with current equity, as in `apply_cash_scaled`. | same |
| S7 calendar permutation | Applied to every book. The path's daily returns over its window are cut into calendar-year blocks, and as many years as the window holds are drawn i.i.d. with replacement (mean block = one year), RNG seeded per path. The TRI comparison uses the same year draws, and the blend resamples the blend's own daily returns. | same |

**Negative controls.**

| id | swing | 0001 |
|---|---|---|
| N1 label shuffle | For each setup week, every real signal is re-assigned to a uniformly random **different** ticker that is a PIT member with a bar on the entry day, without replacement within the week. The new ticker gets its own signal-week low (stop) and high (band), its own 44-week SMA, and the original's CRS value and origin. Grade A (top 5 by CRS per week) and fill order are then recomputed on the relabelled set. | On each date, the rank values are permuted across the rows that have a rank. |
| N2 random ranker | Signal weeks are drawn at random. For each calendar year, as many signals as the real book had are placed on uniformly random (member ticker, week) pairs, with uniform random CRS values. The engine, exits and Grade-A rule are unchanged. Turnover is matched on activations per year, and realised trades per year are reported. | Each name gets a persistent U(0,1) score that is redrawn with probability q at each month-end. q is the base book's measured entry rate per rebalance divided by top_n, so turnover is matched. Realised turnover is reported. |
| N3 reversed sign | The CRS rank is negated, so Grade A becomes the bottom 5 per week and the fill order is weakest first. The setup itself has no sign, and a long-only book cannot short it. | rank = −NMS. |

**Metrics.**
- Sharpe: per path, mean/std of daily returns × √252 over the window.
- Sharpe vs TRI: path Sharpe minus the TRI Sharpe over the same dates.
- Appraisal ratio: see Step 0.
- Blend p95: see Step 0.
- Dependence: the 20 paths, and the 100 seeds, all share one market history. They are a noise band around one path,
  not independent samples. The 2·SE test on the controls is therefore a test against this history's null, not the
  population's.
