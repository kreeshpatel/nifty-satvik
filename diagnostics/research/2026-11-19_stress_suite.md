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

---

## Amendment 1 — 2026-11-19, lead quant — amended before first look

Made before any N1/N2/N3 result existed. The control runs were stopped before writing any output (no N cache file
had been produced), and they are re-run under this amendment. The original Step 0 text above stands as written. It is
superseded only where stated here.

**Withdrawn.** Both readings of the original N1/N2 rule ("mean within 2 SE of 0, p95 < 0.3") are withdrawn: the raw
Sharpe reading and my appraisal-ratio interpretation. The reason given: the rule ignores market beta and cost drag on a
long-only book.

**New harness-bias test (N1, N2) — the only pass/fail for the controls.**
- **Beta baseline, per seed.** The equal-weight eligible PIT universe, held at the same daily exposure as that seed's
  placebo, with cash earning nothing as in the engines:
  - baseline_t = x_{t−1} · EW_t − c_t
  - x_{t−1} is the placebo's invested fraction at the prior close: Σ notional / equity for swing, and
    (equity − cash) / equity for 0001.
  - EW_t is the equal-weight close-to-close return of the universe the placebo samples from:
    - swing: PIT Nifty-500 members with a bar (the engine applies no ADV filter of its own);
    - 0001: rows with `eligible` and the size band. `eligible` carries the book's liquidity filter.
  - c_t is the placebo's own daily cost drag, defined as (return with costs on) − (return with costs off) on the same
    seed. "Same costs."
  - Blend baseline: the 70/30 blend at 11%, applied to the two legs' baselines.
- **Test.** For each seed k, d_k = Sharpe(placebo_k) − Sharpe(baseline_k). Pass if |mean d| ≤ 2 · sd(d)/√100.
  Sharpe is the harness Sharpe vs cash: mean/std × √252, no risk-free rate.
- **Cost drag, reported separately.** N1 and N2 are each run twice per seed, with costs on and with costs off. The
  median Sharpe gap is reported for each.
  - swing costs off = the engine's `cost_off=True` (path cost jitter not applied);
  - 0001 costs off = `cost_mult = 0`.

**New result (not pass/fail).** The permutation p-value of the strategy against each placebo: the share of the 100
placebo seeds whose Sharpe is ≥ the strategy's. The strategy's Sharpe is the median of its 20 unshocked paths.

**Unchanged.** N3 must be clearly below base, as defined in Step 0 (raw-Sharpe reading; the appraisal reading is
dropped together with the withdrawn rule).

**Overall verdict.** **The suite FAILS overall only if N1 or N2 breaks the beta-baseline test, for any book.** The
consequences of an N3 failure, and of the appraisal metric, are withdrawn. An N3 failure is still reported, as a
finding.

**Step 0b (added by the same amendment).** The unshocked base for swing, 0001 and the blend is run under
PYTHONHASHSEED 0 and 7, and the outputs must be byte-identical: a sha256 over every path's NAV bytes, and the blend
built from them.

---

## Results — controls first (Step 0 / Amendment 1)

### Step 0b — determinism: PASS [measured]

The unshocked 20-path base was re-run under PYTHONHASHSEED 0 and 7. The sha256 over every path's NAV, and over the
blend built from them, is **byte-identical** across both seeds and the original run:

| book | sha256 prefix |
|---|---|
| swing | `912f4c0d68d2a4a1` |
| 0001 | `d73ac2c7584d770c` |
| blend at 11% | `baed734ac7a9a294` |

### Anchors — PASS [measured]

| anchor | result |
|---|---|
| swing | 1.025 / −40.1% |
| 0001 | 21.73% / 1.130 |
| blend at 15%, worst daily DD | −22.85% |
| patched swing engine, hooks off, path 0 | 1.348913 (reproduced) |
| patched rebalance copy, hooks off | reproduces 0001's NAV exactly |

### Negative controls — **SUITE FAILED** under Amendment 1 [measured, `explore/2026-11-19_stress_suite_controls.json`]

Columns:
- **placebo Sharpe** — mean and p95 over 100 seeds;
- **beta baseline** — mean Sharpe;
- **paired d** — mean of placebo − baseline, with its SE and z;
- **test** — the beta-baseline test (|mean d| ≤ 2 SE);
- **cost drag** — median Sharpe with costs off minus with costs on;
- **perm. p** — share of placebo seeds ≥ the strategy's median Sharpe.

| control | book | placebo Sharpe (mean / p95) | beta baseline | paired d (SE, z) | test | cost drag | perm. p |
|---|---|---|---|---|---|---|---|
| N1 label shuffle | swing | 0.870 / 1.295 | 1.660 | −0.789 (0.042, z −19.0) | **FAIL** | 0.406 | 0.09 |
| N1 | 0001 | 0.491 / 0.631 | 0.977 | −0.487 (0.012, z −40.3) | **FAIL** | 0.211 | 0.00 |
| N1 | blend | 1.263 / 1.504 | 1.900 | −0.637 (0.019, z −33.1) | **FAIL** | 0.273 | 0.00 |
| N2 random ranker | swing | 0.885 / 1.377 | 1.626 | −0.741 (0.043, z −17.1) | **FAIL** | 0.350 | 0.13 |
| N2 | 0001 | 0.605 / 0.744 | 0.853 | −0.248 (0.009, z −27.1) | **FAIL** | 0.093 | 0.00 |
| N2 | blend | 1.384 / 1.628 | 1.792 | −0.408 (0.018, z −22.2) | **FAIL** | 0.184 | 0.00 |

| control | book | N3 median Sharpe | base p5 | clearly below base |
|---|---|---|---|---|
| N3 reversed sign | swing | 0.911 | 1.031 | yes |
| N3 | 0001 | 0.232 | 1.110 | yes |
| N3 | blend | 1.100 | 1.932 | yes |

Strategy medians (20 paths): swing 1.253, 0001 1.129, blend 1.981.

Turnover matching:
- **0001 N2:** 7.98 exits per rebalance, against 7.94 for the base. Matched by the one calibration step (q = 0.263).
- **0001 N1:** 20.8 exits per rebalance. Not turnover-matched, by design.
- **Swing placebos:** 277 trades on average, against 67 for the base. Random names hit stops and SMA breaks far
  sooner, and the engine re-fills the seats.

**Verdict, as the amendment states it:** the suite FAILS overall because N1 and N2 break the beta-baseline test, on all
three books. **Per Step 0, the shocks (S1–S7) are not interpreted.** All shock runs are complete and cached under
`.cache/stress_suite/`; the shock table is withheld until the owner rules on the failure.

**Direction.** Every placebo sits **below** its beta baseline, by 0.25 to 0.79 Sharpe. The failure is not the harness
creating edge out of noise. The placebo earns less than the passive equal-weight universe held at the same exposure,
net of its own explicit costs.

### What could explain the gap — hypotheses, NOT tested [inferred]

1. **The baseline has a daily-rebalancing premium.** EW_t is the mean of close-to-close returns of every member,
   rebalanced daily. That collects a volatility/rebalancing bonus and bid-ask bounce that no held book earns. The
   placebo holds names for weeks (swing) or a month (0001). Cheapest test: rebuild the baseline as a
   monthly-rebalanced, or buy-and-hold, equal-weight universe and re-run the paired test. The placebo runs are already
   cached, so this takes minutes.
2. **The engine's exit rules on random names cost return beyond the explicit costs.** On random entries the swing's
   10% stop and SMA-break exits whipsaw: 277 trades against the base's 67. The cost-off twin removes explicit costs
   only, not the path loss from cutting and re-entering. That is the strategy's own exit behaviour, not a harness
   bias, but the baseline as specified does not net it out.
3. **Membership and coverage.** The baseline averages every PIT member with a bar. The placebo draws from members with
   a bar on the entry date and a usable signal-week range. These differ at the margin. Expected to be small; not
   checked.

### Permutation p-values (a result, not pass/fail)

| book | vs N1 | vs N2 |
|---|---|---|
| 0001 | 0.00 | 0.00 |
| blend | 0.00 | 0.00 |
| **swing** | **0.09** | **0.13** |

0001's and the blend's Sharpe lie beyond every placebo seed. **The swing book's Sharpe of 1.253 is exceeded by 9% of
label-shuffled and 13% of random-ranker placebos**, so on this window its edge over random entries with its own exits
is not distinguishable at 5%.

### Independent re-derivation (rule 3) [measured]

A `blind-replica` worked from the spec alone. Spec, code and results are in `explore/2026-11-19_stress_suite_replica/`.

| number | replica | pipeline | gap |
|---|---|---|---|
| S1 swing median Sharpe (20 paths) | 1.0838 | 1.0838 | 0, identical path by path |
| S1 0001 median Sharpe | 1.1218 | 1.1266 | 0.43% |
| N1 swing raw Sharpe mean (100 seeds) | 0.878 | 0.870 | 0.9% |
| N1 0001 raw Sharpe mean | 0.482 | 0.491 | 1.8% |

The 0001 S1 gap comes from one reading of the spec: the replica shifts ranks by panel date, the pipeline by the
ticker's own previous row. The N1 gaps come from the replica's shuffle details: signals before 2019 left out, and a
different draw order. All gaps are under 5%.

The replica was specified before Amendment 1, so it reported the withdrawn raw and appraisal tests. It did not compute
the beta baseline, and **the beta-baseline verdict has not been independently re-derived**.

### Artifact check

1. **Daily-rebalanced EW baseline.** Hypothesis 1 above. **Not ruled out**; the most likely source of the failure.
2. **Overlapping seeds on one history.** The 100 seeds share one market path, so SE measures seed noise, not sampling
   uncertainty. Any systematic baseline mismatch therefore produces an enormous z. **Disclosed.**
3. **The cost drag is approximated.** c_t = r_on − r_off compares two different paths, because the fills differ.
   **Not ruled out**, but it cannot explain a gap that persists after costs are stripped out.
4. **N3 inverts the CRS ranker only, not the setup.** Long-only cannot short the setup. **Disclosed.**
5. **Interpreting the S5 shock on swing.** Moot while the shocks are withheld.

---

## Owner decisions recorded, 2026-11-19

- **Fallback 60/40 recorded.**
- **Swing goes to the January review as an item.** No live change.

## Amendment 2 — 2026-11-19, lead quant — **post-hoc spec correction** (made after the Amendment 1 result)

Recorded verbatim:

> Amendment 1 compared Sharpe ratios. That was a spec error: random selection preserves EXPECTED RETURN, not Sharpe; a
> 5-seat or 0001-sized random book carries idiosyncratic volatility the 500-name universe does not, and the
> daily-rebalanced baseline adds a rebalancing bonus. Withdraw the Sharpe comparison.
> New harness-bias test, from the cached cost-OFF twins only (no new engine runs):
>  - For N1 and N2 on each book: mean daily arithmetic return of the placebo vs the mean daily arithmetic return of the
>    equal-weight eligible universe over the SAME invested days, scaled by the placebo's exposure fraction on each day.
>    Report the difference (annualised), its z across the 100 seeds, and the placebo-to-baseline volatility ratio.
>  - Pass if |z| < 3 on every book (two controls x three books = 6 tests; state the multiplicity).
>  - Also report the Sharpe gap that the volatility ratio alone predicts, beside the observed Sharpe gap, so the
>    Amendment 1 failure is explained or not.
> If Amendment 2 PASSES: release the shock table in the same message (Sharpe vs cash, vs the Midcap150 Momentum 50 TRI,
> blend p95 156-week drawdown; pass/fail per the Step 0 shock criteria; worst shock per book). Report S6's held-name
> 1st-percentile gap beside the all-pairs -4.23%.
> If it FAILS: stop and report; do not release shocks.

**Multiplicity.** This is the second harness-check specification on the same cached placebo runs, written after the
first one failed. It is a harness check, not a trial: **n_trials is unchanged at 3**. The controls family now counts
**2 specifications × 6 tests = 12 tests**, of which **Amendment 2's 6 are binding**. Their |z| < 3 bar is the
pre-stated bar, and it is not adjusted further here.

**Implementation, fixed before computing** (`explore_stress_suite.py controls_a2`):
- **Inputs.** Each seed's cost-OFF twin (N1off, N2off). Daily returns over the book's window: swing 2019-03-01..2024-06-28;
  0001 path start..2026-06-30.
- **Exposure** x_{t−1}: the twin's invested fraction at the prior close.
- **Baseline** b_t = x_{t−1} · EW_t, with EW_t as in Amendment 1.
- **Invested days:** t with x_{t−1} > 0.
- **Difference** d_k = (mean of r_t − mean of b_t over invested days) × 252. z = mean(d) / (sd(d)/√100).
- **Volatility ratio:** sd(r)/sd(b) over invested days, averaged over seeds.
- **Sharpe gap the volatility ratio alone predicts:** Sharpe(b) · (1/vr − 1), per seed, averaged. It is reported beside
  the observed gap, Sharpe(r) − Sharpe(b).
- **Blend:** placebo = the blend rule applied to the two legs' cost-off twins. Baseline = the blend rule applied to the
  two legs' baselines. Invested days = every day.

## Correction — Amendment 1 baseline sign (found while computing Amendment 2)

**Correction:** the Amendment 1 beta baseline was implemented as x·EW − c_t with c_t = r_on − r_off, which is the text
of the amendment. The text is sign-inconsistent: costs make r_on < r_off, so c_t is negative, and subtracting it
**added** the placebo's cost drag to the baseline instead of charging it.

Every Amendment 1 baseline Sharpe in the controls table above (`explore/2026-11-19_stress_suite_controls.json`,
commit 5be24a9) is therefore inflated by roughly the cost drag. For example, the swing N1 baseline reads 1.660, against
1.318 with costs excluded under Amendment 2.

The Amendment 1 FAIL is overstated, but it is moot: Amendment 1's Sharpe comparison is withdrawn by Amendment 2 in any
case. Amendment 2 uses cost-off twins only and has no c_t term, so this error does not reach it.

## Amendment 2 result — **FAILS on 3 of 6 tests**

Source: [measured, `explore/2026-11-19_stress_suite_controls_a2.json`; cost-off twins, 100 seeds]. Column key:
- **diff** — placebo − baseline mean return, annualised, with its SE;
- **vol ratio** — placebo-to-baseline volatility;
- **Sharpe gap** — observed and predicted by the vol ratio alone.

| control | book | placebo mean / yr | baseline mean / yr | diff (SE) | z | \|z\| < 3 | vol ratio | Sharpe gap: observed / predicted |
|---|---|---|---|---|---|---|---|---|
| N1 | swing | 24.60% | 21.98% | **+2.62pp** (0.58) | **+4.53** | **FAIL** | 1.186 | −0.076 / −0.204 |
| N1 | 0001 | 15.15% | 15.59% | −0.43pp (0.19) | −2.33 | pass | 1.037 | −0.050 / −0.029 |
| N1 | blend | 19.43% | 19.64% | −0.20pp (0.16) | −1.25 | pass | 1.008 | −0.029 / −0.013 |
| N2 | swing | 24.82% | 22.47% | **+2.35pp** (0.61) | **+3.85** | **FAIL** | 1.180 | −0.084 / −0.199 |
| N2 | 0001 | 14.96% | 15.54% | **−0.58pp** (0.17) | **−3.39** | **FAIL** | 1.034 | −0.055 / −0.026 |
| N2 | blend | 19.58% | 19.61% | −0.03pp (0.18) | −0.15 | pass | 1.006 | −0.011 / −0.009 |

Multiplicity: 6 binding tests, out of 12 run across the two specifications.

**Verdict: Amendment 2 FAILS** on swing N1, swing N2 and 0001 N2. **Per the amendment, stop: the shock table is not
released**, and neither is the S6 held-name gap, which belongs to that release.

**Is the Amendment 1 failure explained?** Mostly. With costs off and no sign error, the observed Sharpe gaps are small
(−0.01 to −0.08). The volatility ratio alone predicts gaps of a similar size, and larger for swing (−0.20). So the
Amendment 1 gaps of −0.25 to −0.79 came from the cost-sign error plus idiosyncratic volatility, and **not** from a
return shortfall. The return test is now the binding one, and it fails in two different directions:
- **Swing placebos earn more than their baseline**, by +2.3 to +2.6pp a year. This is the direction in which a harness
  would create edge.
- **0001's N2 placebo earns less**, by −0.58pp a year (z −3.39). N1 0001 is −0.43pp (z −2.33, within the bar).

**Hypotheses, NOT tested** [inferred]:
1. **Swing timing mismatch between fills and the baseline.** The placebo fills at the open and exits at the open. The
   baseline uses exposure at the prior close times the close-to-close return. So on an entry day the placebo earns
   open→close on the new position while the baseline credits nothing, and on an exit day the reverse happens. With 277
   trades a year against the base's 67, any systematic overnight-versus-intraday difference in Indian midcaps lands
   in d.
   - Cheapest test: rebuild the baseline at the placebo's own fill timing, or measure the open→close vs close→open
     split in the universe. Both work from the cached runs.
2. **Swing exit rules on random entries are a trend filter.** Stops and SMA breaks drop falling names and keep rising
   ones, so a random-entry book still holds a momentum tilt. That would be a property of the strategy's exits, not a
   harness bias. The two cannot be separated with these controls.
   - Cheapest test: a placebo that also randomises the exit date while matching holding-period lengths.
3. **0001 N2 (−0.58pp).** The persistent random ranks hold names for months, against a universe re-weighted daily; the
   remaining rebalancing bonus in the baseline is the natural candidate. It is small in size, and the z is driven by
   a tight SE across 100 seeds on one history.

### Amendment 2 — independent re-derivation, swing N2 [measured]

A fresh `blind-replica` worked from the spec and the exported cost-off series only. Spec, code and result are in
`explore/2026-11-19_stress_suite_a2_replica/`.

| quantity | replica | pipeline | gap |
|---|---|---|---|
| diff, % a year | +2.348 | +2.348 | 0 |
| SE | 0.610 | 0.61 | 0 |
| z | 3.85 | 3.85 | 0 |
| vol ratio | 1.180 | 1.18 | 0 |
| Sharpe gap observed / predicted | −0.084 / −0.199 | −0.084 / −0.199 | 0 |
| invested days | 1,313 | 1,313 | 0 |

The replica notes that exposure is never zero (minimum 0.137), so the invested-day filter keeps every day. Both
implementations start on 2019-03-05, the first return after the 2019-03-01 slice start.

---

## Owner decisions, 2026-11-19 (second)

1. **Harness:** run Step A, then Step B, **swing only**, as HARNESS VALIDATION. This is not a verdict on swing.
2. **0001 and swing both go to the January review.** No live change now.

## Post-hoc spec 3 (Harness Step A) — stated before computing; under multiplicity; n_trials unchanged

**What it does.** Recompute the swing N1/N2 baseline with the placebo's own fill convention, exposure-matched by day,
from the cost-off twins. The gap and z are reported under both conventions.

**Pass rule.** If |z| < 3 under matched fills on both N1 and N2, the harness passes for swing and the shock table is
released.

**Multiplicity.** This is the third harness specification on the same placebos: 2 controls on swing, so 14 tests in
total across the specifications.

**Inputs.** The cache holds each seed's NAV and exposure but not its fills. The identical cost-off runs are therefore
regenerated with the engine's position log, event log and trade ledger kept. These are observation-only logs: the
engine documents that they change nothing. **Each regenerated seed is accepted only if its daily NAV equals the cached
NAV exactly;** any mismatch stops the step.

**Matched-fill baseline for day t.** Weights are each position's value at the prior close over equity at the prior
close. Three universe returns are used:
- EW_cc: the equal-weight close-to-close return, as before;
- EW_on: the overnight return, open_t / close_{t−1} − 1;
- EW_id: the intraday return, close_t / open_t − 1.

Each piece of the book is matched to the return it actually experienced:
- **Held through the day:** w · EW_cc.
- **Sold at the open** (full exits whose ledger reason is a queued exit: stop, stop_part, sma_break, time, stale; and
  pattern-tranche sells): w_sold · EW_on.
- **Sold intraday at a resting limit** (the +2R tranche; full exits with reason `targets`): w_sold · EW_cc. This is
  approximate, because the fill is at the level, not the close. Disclosed.
- **Entered at the open:** (shares × fill price / prior-close equity) · EW_id.

b_t is the sum of these terms. d_k = (mean r − mean b) × 252 over the window, and z = mean(d) / (sd(d)/√100). The A2
convention, b_t = x_{t−1} · EW_cc, is recomputed beside it on the same days.

## Harness Step B (N4) — stated before running; only if Step A leaves |z| ≥ 3

**The placebo.** Swing, 100 seeds. Random entries (the N2 generator) **and** random exits. Each trade's holding period is
drawn, by a deterministic hash of (seed, ticker, entry date), from the unperturbed swing ledger's closed-trade holding
periods in calendar days. The position is exited in full at the open of the first session on or after
entry + holding period. Stops, tranches, pattern and SMA exits are all disabled. Same seats and engine; costs off, for
comparability with the Amendment 2 and Step A tests. Implemented on the source-patched engine copy, with the hook off
by default.

**Test.** N4 against the matched-fill baseline (gap, z), with the same |z| < 3 bar.

**Interpretation, fixed now:**
- If N4 passes and N2 fails, swing's exits carry the excess, which is a property of the strategy.
- If N4 also fails, the harness is biased and stays blocked for January.
