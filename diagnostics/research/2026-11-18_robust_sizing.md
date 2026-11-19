# Robustness gates and drawdown-based sizing — 2026-11-18

**Class: MEASUREMENT + documentation.** Owner request 2026-11-18, branch `research/robust-sizing`. No live rule,
no trial counter, no sealed read. **Standing counts: screens 24 · sealed opens 4 · n_trials 3** (read from
`diagnostics/research/label_screen_ledger.md` and `n_trials.json` via `tests/test_standing_counts.py`; unchanged).
The research freeze until the 2027-01-01 review is set aside by the owner's explicit request for this study;
nothing here is adopted.

**Mission line.** The −25% worst-drawdown bar binds the combined book. This measures whether the 70/30 blend at
its 15% vol target clears it on the mission's 3-year horizon, what vol target would, and how robust the two
components' adopted parameters are, before any of it touches capital.

**Anchors, reproduced in-run before any result** (rule 4): live swing 2019-01-01..2024-06-28 Sharpe **1.025** /
MaxDD **−40.1%**; 0001 **21.73% / 1.130**; blend daily worst drawdown **−22.85%** (the frozen band's
`worst_backtest_drawdown_pct`). All three matched; each script aborts on a mismatch.

---

## Part 1 — parameter sensitivity ("spike") gate

**Method.** `pipelines/diagnostics/explore_param_sensitivity.py`. Each numeric parameter nudged −20/−10/+10/+20%,
one at a time, over the 20-path ensemble (`nq.lab.ensemble.draw_perturbations(20, DEFAULT_SEED)`: cost ±10 bp per
side, start in the first ~20 sessions). Sharpe = mean/std of daily NAV returns × √252 (`nq/lab/ensemble.py::
slice_metrics`; momentum the same formula on the engine curve). Swing window 2019-03-01..2024-06-28 (prices cut
2024-06-30); momentum each path's start..2026-06-30. Integers rounded. Paths share one history, so the 20 paths are
a noise band around one path, not 20 independent samples.

**"Sharpe change" for a standalone strategy — fixed before any result, both reported:** vs the mission benchmark
(Nifty Midcap150 Momentum 50 TRI, Sharpe **1.608** over the swing window, **1.179** over 0001's) and vs cash (the
Sharpe itself). Plus the paired change against the unnudged book on the same path (descriptive).

**Result.**

| book | parameters gated | SPIKE vs cash | FAIL vs benchmark | not nudgeable |
|---|---|---|---|---|
| live swing | 15 | **0** | **15 of 15 — at base** (median 1.253 < 1.608) | tp2_frac = 0, runner_sma_buffer = 0, tp2_r inert |
| 0001 momentum | 4 | **0** | **4 of 4 — at base** (median 1.129; median change vs the path-matched TRI −0.02) | cadence (categorical: the engine has W/2W/M/Q only) |

Swing medians, base **1.253**; paired change at −20 / −10 / +10 / +20%:

| parameter | base | −20% | −10% | +10% | +20% |
|---|---|---|---|---|---|
| sma_len (44 wk) | 44 | +0.060 | **+0.409** | +0.237 | +0.309 |
| touch_band | 0.07 | +0.116 | +0.041 | +0.104 | +0.226 |
| slope_min | 0.03 | −0.080 | −0.092 | −0.003 | −0.111 |
| slope_lookback | 13 | −0.040 | +0.016 | −0.172 | −0.109 |
| crs_len | 40 | +0.239 | +0.042 | +0.061 | −0.026 |
| grade_top_n | 5 | +0.102 (4) | = −20% | −0.002 (6) | = +10% |
| risk_pct | 0.02 | +0.250 | +0.223 | 0.000 | 0.000 |
| ext_cap | 0.20 | +0.003 | +0.130 | +0.137 | −0.024 |
| max_risk_pct | 0.10 | +0.114 | −0.015 | −0.024 | +0.039 |
| max_notional_pct | 0.20 | +0.283 | +0.047 | +0.121 | +0.198 |
| stale_absent_days | 10 | 0.000 | 0.000 | 0.000 | 0.000 |
| tp1_r | 2.0 | +0.018 | +0.098 | +0.039 | +0.126 |
| tp1_frac | 0.40 | −0.165 | +0.040 | +0.088 | −0.083 |
| pattern_frac | 0.40 | +0.032 | +0.033 | +0.044 | +0.070 |
| pattern_arm_r | 2.5 | +0.058 | +0.015 | +0.044 | +0.106 |

0001 paired change: mr12 lookback (231 d) −0.011…+0.021; mr6 (105 d) +0.019 / −0.017 / −0.037 / **−0.146**;
top_n (30) −0.006…−0.037; buffer (1.5) +0.023…−0.039.

**Reading (facts only).** No adopted parameter is a spike against cash. Both books fail the benchmark comparator at
the unnudged value, so under that comparator the gate cannot distinguish "spike" from "no edge over the index in
this window". The swing's live values sit **below** most of their neighbours (paired change positive in 39 of 60 cells, zero in 6, negative in 15);
0001 sits on a flat plateau. risk_pct above 2% and stale_absent_days change nothing (the notional cap binds;
no name went stale).

**Re-derivation (rule 3).** A fresh `blind-replica`, from the spec and the harness API only, re-ran
max_notional_pct over the same 20 paths: medians base **1.253**, 0.16 **1.493**, 0.24 **1.461**, paired +0.283 /
+0.198 — identical. It flagged that both ±20% moves *raise* Sharpe and asked whether an explicit override takes a
different code path; tested: path 0 with no override and with `max_notional_pct=0.20` set explicitly both give
1.348913 — **ruled out**. The non-monotone response is the book's (which names get seats), not the harness's.

**Artifacts.** (1) *In-sample neighbourhood*: the "better" neighbours are measured on the same 2019–2024 window the
parameters were chosen on — not checked, and a reason not to read them as improvements. (2) *Single path*: the 20
paths are perturbations of one history — disclosed. (3) *Cap binding*: risk_pct's flat upside is the notional cap,
not insensitivity of the edge — ruled in by the zero change. (4) *Integer rounding*: grade_top_n's ±10% and ±20%
collapse to 4 and 6 — disclosed. (5) *Engine copy for sma_len*: the 44-week SMA is a literal, so its nudges ran on a
source-patched engine copy; the copy at 44 reproduces the base median 1.2529 exactly — ruled out.

## Part 2 — drawdown-based sizing for the blend

**Method.** `pipelines/diagnostics/explore_blend_drawdown_sizing.py`. Blend = `core.vol_target_blend` (70/30 daily,
exposure = min(1, target / lagged 20-session vol), cash at 6%), 2019-03-01..2024-06-28. Stationary bootstrap of the
278 Friday-to-Friday returns, mean block 8/13/26, 10,000 draws, seed 20261118; depth = max(1 − NAV/peak) from 1.0.
CAGR and Sharpe of the daily blend over the window.

**1. Blend at 15%, bootstrap drawdown depth (p50 / p95 / p99, %)**

| block | 52 wk | 104 wk | **156 wk** |
|---|---|---|---|
| 8 | 11.0 / 23.2 / 30.1 | 13.8 / 27.2 / 34.4 | **16.7 / 29.3 / 36.2** |
| 13 | 11.3 / 22.2 / 28.7 | 14.6 / 27.1 / 34.0 | 17.4 / 28.7 / 35.2 |
| 26 | 11.5 / 21.1 / 27.1 | 15.6 / 24.7 / 31.4 | 17.8 / 27.0 / 32.9 |

At the current 15% target the 156-week p95 is **27.0–29.3%**, past the −25% bar at every block length.

**2. Why the frozen band's 52-week p95 (22.85) equals the backtest worst (22.85).** It is a **coincidence**, not
clipping, not "wider of the two", and not the ensemble repeating one episode:
- the two are different quantities: the band's worst is the **daily**-NAV drawdown (−22.8533%); the bootstrap runs
  on **weekly** returns, whose own worst is only **21.09%** (COVID, 2020-02-21 → 2020-04-03, 6 weeks);
- the band's bootstrap p95 is **22.8539** — 0.0006 pp from the daily worst. Re-seeding the same bootstrap gives
  22.55, 22.78, 22.94, 22.97;
- 222 of 5,000 draws (4.4%) reproduce the weekly episode intact (depth 21.09) and they sit at ranks 4385–4606,
  **below** the p95 rank of 4750; 395 draws are deeper than any weekly drawdown in the history;
- no clip exists in `core.stationary_bootstrap` / `core._path_stats`, and the bootstrap column already reads 22.85
  before `core.wider` (the ensemble column reads 21.33).
- One real repetition effect does exist: at block 26 the 52-week p95 equals the weekly worst, **21.09**, exactly —
  long blocks copy the COVID crash whole.

**3. Vol target meeting −25% at 156 weeks** (most conservative block = 8, deepest p95 at 15%):

| target | CAGR % | Sharpe raw | Sharpe excess | mean exposure | backtest worst | 156-wk p95 | meets −25% |
|---|---|---|---|---|---|---|---|
| 8% | 20.88 | 2.112 | 1.440 | 0.55 | −13.0% | 17.2 | yes |
| 9% | 22.35 | 2.032 | 1.427 | 0.61 | −14.6% | 19.4 | yes |
| 10% | 23.80 | 1.978 | 1.423 | 0.66 | −16.1% | 21.4 | yes |
| **11%** | **25.14** | **1.932** | **1.417** | **0.71** | **−17.7%** | **23.4** | **yes — highest** |
| 12% | 26.40 | 1.898 | 1.416 | 0.75 | −19.1% | 25.0 | no (by 0.03 pp) |
| 13% | 27.44 | 1.861 | 1.406 | 0.79 | −20.5% | 26.7 | no |
| 14% | 28.46 | 1.833 | 1.399 | 0.82 | −21.7% | 28.2 | no |
| 15% | 29.20 | 1.801 | 1.386 | 0.85 | −22.85% | 29.3 | no |

Sharpe raw = mean/std(ddof 1) of daily returns × √252, rf = 0 (the engine and band convention). Sharpe excess = the
same with a 6.5%/yr risk-free rate compounded daily, (1.065)^(1/252) − 1 a session, subtracted from the mean
(`nq/validation/metrics.py::sharpe_excess`; computed in `pipelines/diagnostics/explore_risk_matched_benchmark.py`,
artifact `diagnostics/research/explore/2026-11-18_risk_matched_benchmark.json` → `q1_part2_both_sharpes`).

> **Correction (2026-11-18, PR #211):** this section first said moving 15% → 11% "*raises* Sharpe by +0.13". That
> is the raw, zero-risk-free Sharpe, and most of it is the cash leg's interest counted as risk-adjusted return. Net of a
> 6.5% risk-free rate the change is **+0.031** (1.386 → 1.417): essentially flat. Replaced by: moving 15% → 11% costs
> **−4.06 pp CAGR** and leaves the excess-return Sharpe **unchanged to within +0.03**. It buys drawdown, not
> risk-adjusted return. Picked by the drawdown rule only.

**4. Components alone (reference), 156-week p95:** momentum 38.6 / 37.5 / 35.1 %; swing 44.9 / 45.2 / 43.9 %
(blocks 8 / 13 / 26). Full tables in the JSON.

**Re-derivation (rule 3).** A fresh `blind-replica` from the spec and the raw NAV CSVs only: daily worst −22.8533%;
156-wk p95 at block 8: 11% **23.45** (mine 23.35), 12% **25.24** (25.03), 15% **29.72** (29.33); Sharpe 1.801 at 15%
(1.801). All within 1.3% relative. The replica also showed that 11% clears at every one of 10 seeds while 12% fails
at every seed by only 0.04–0.6 pp: **the 11/12 boundary is Monte-Carlo-thin.**

**Artifacts.** (1) *One history*: every percentile resamples one 278-week path that contains one crash — not
ruled out; it is the main limit. (2) *Block length*: varied 8/13/26, the conservative one used — ruled in. (3) *Seed*:
shown above to move p95 by ~0.5 pp — disclosed; the 12% boundary sits inside it. (4) *In-sample window*: 2019–2024,
which includes the momentum regime that made the TRI benchmark itself +34% a year — not checked. (5) *Return-fitting*:
the target is chosen by drawdown only, but CAGR/Sharpe were seen in the same table — disclosed.

## Part 3 — stops are requests

**Method.** `pipelines/diagnostics/explore_stops_are_requests.py`. Live overshoot = (exit − card stop) / (entry −
card stop) over the 33 closed live stop exits (2026-07-27..2026-11-09): mean **−0.733R**, median −0.594, p5 −1.914,
min −3.53. These are the forward scan's **modelled** exits on real bars (same weekly-close trigger, next-open fill),
not broker fills, and mostly tracker-only trades (0146/0147). Backtest stop exits in the capped book: 32, mean
**−0.813R**, median −0.442, min −4.37. Re-priced exits change cash by shares × Δprice from the exit date.

**Circuit lock (APPROXIMATE — no NSE price-band data in the repo):** close within 0.15 pp of −5/−10/−20%, close
within 0.1% of the low, range ≤ 2% of prior close; exit moved to the next unlocked session's open. Detected 1,877
locked sessions on 181 names. Trades affected: **dataset A 1 of 441 closed**, capped swing book **0**, 0001 **2 of
2,951**. 0001 has **no stop exits** (rebalance exits/trims and 1 stale), so the stop scenarios leave it unchanged.

| scenario | swing Sharpe / CAGR / 156-wk p95 | momentum | blend at 15% |
|---|---|---|---|
| base | 1.025 / 20.5% / 45.6 | 1.130 / 21.7% / 41.4 | 1.790 / 29.0% / 29.3 |
| live overshoot (200 resamples, median) | 1.016 / 20.1% / 42.2 | unchanged | 1.781 / 28.8% / 28.5 |
| circuit lock (approx.) | unchanged (0 trades) | 1.125 / 21.7% / 41.7 | 1.792 / 29.1% / 29.4 |
| gap-shock 2× live mean | **0.523 / 12.4% / 77.5** (worst −68.0%) | unchanged | **1.576 / 26.3% / 35.3** (worst −25.2%) |
| gap-shock, equity-scaled † | 0.614 / 14.5% / 71.1 (worst −63.9%) | unchanged | 1.625 / 26.8% / 33.6 (worst −24.7%) |

† **Added after first look**, because the fixed-rupee accounting books later losses at the original position size;
each adjustment is scaled by adjusted ÷ base NAV the session before. Counts toward multiplicity as a second look.

The gap-shock adds ~1.47R to every one of 32 stops on top of the backtest's own overshoot (median stop risk 1.6% of
NAV → ~2–3% NAV each; nine fall in Feb–Mar 2020). Live overshoot alone barely moves anything: the live mean
(−0.73R) is close to the backtest's (−0.81R).

**Re-derivation (rule 3).** A fresh `blind-replica`: live overshoot −0.7332R (n 33), backtest −0.8125R (n 32),
gap-shock swing 0.5230 / 12.36% / −68.02% — identical to the figures above.

**Artifacts.** (1) *Sizing feedback ignored*: shown by the equity-scaled row; still a first-order fix, not a
re-simulation. (2) *"Live" is modelled, n = 33, four months*: not ruled out. (3) *Circuit detector approximate*: no
band data; dividend-adjusted closes can miss exact band ratios — not checked. (4) *Blend p95 under the base row*
uses a different seed per resample in the live-overshoot row — ~0.5 pp noise, disclosed.

## Part 4 — walk-forward / CPCV status

**Existing:** none of the three has a walk-forward or CPCV result. Nearest: swing `certify_live_config_A1.md`
(sub-period slices + DSR, no folds); 0001 `research/0001-xsec-momentum/results.json` (CSCV PBO **0.452** over a
9-config top_n × buffer family); blend — only the frozen bands.

**Run** (`pipelines/diagnostics/explore_walkforward_status.py`, 2019-01-01..2024-06-28; blend from 2019-03-01;
continuous slices): CPCV with the module defaults (N = 10, k = 2, no purge/embargo) yields 9 paths that are
**identical by construction** on a frozen rule (path-Sharpe spread 0.000), as `nq/runner/research.py` documents —
so the CPCV "distribution" carries no information here. Per-fold OOS Sharpe = each of the 10 contiguous groups.
DSR = the harness path (63-day windows, n_trials = 3 from the ledger). PBO = CSCV, 16 blocks, over the Part 1 nudge
family (fixed before PBO was computed; swing family excludes sma_len).

| book | fold Sharpe (10 folds, in time order) | DSR @ 3 | PBO | base rank in family |
|---|---|---|---|---|
| live swing | 0.22, 0.75, 0.97, 1.33, 2.01, 0.15, 0.57, 0.14, 2.76, 2.61 | 0.890 | 0.310 (55 configs) | 44 of 55 |
| 0001 (slice) | −0.07, 2.36, 0.67, 4.28, 3.36, 1.13, 0.42, 0.26, 4.75, 2.57 | 0.980 | 0.411 (17) | 5 of 17 |
| blend 15% | −0.15, −0.55, 4.85, 3.62, 3.24, −0.68, 2.03, 0.58, 4.15, 2.22 | 0.976 | 0.250 (71) | 44 of 71 |

**Artifacts.** (1) *Degenerate CPCV*: shown. (2) *PBO family = own neighbourhood*: it measures selection within ±20%,
not across strategies — disclosed. (3) *DSR at n_trials 3*: the programme's lifetime count is far larger — now computed;
see follow-up F2: every book falls to 0.21–0.44. (4) *Fold length ~6 months*: wide per-fold noise.


---

## Follow-up 2026-11-18 (b) — owner decisions and corrections

Owner decisions, 2026-11-18:

1. Blend vol target **11%, provisional** until the real-band re-run. The draft amendment
   `forward/drafts/2026-11-18_amendment_blend_vt11_DRAFT.md` is **not applied**.
2. The spike-gate comparator is the benchmark, **risk-matched**.
3. Yes to NSE band data. The owner will supply broker fills.

Standing counts unchanged: **screens 24 · sealed opens 4 · n_trials 3**. Nothing here is a trial.

### F1. Excess-return Sharpe

`nq/validation/metrics.py::sharpe_excess` subtracts a 6.5%/yr risk-free rate, compounded per period (`RF_ANNUAL`,
`rf_per_period`). It is now reported next to the raw Sharpe in:

- `metrics.summary`;
- `nq/lab/ensemble.py::slice_metrics`, as the `sharpe_excess` key and in the ensemble summary.

The raw value and every frozen band are untouched; tests `test_sharpe_excess_*` and
`test_slice_metrics_reports_both_sharpes` cover this. The Part 2 table now carries both columns.

**Correction** at the Part 2 table: 11% vs 15% is +0.131 raw Sharpe but only **+0.031 excess**.

### F2. DSR at the lifetime count

Same harness DSR path as Part 4 (`nq.runner.research._dsr_from_bootstrap`), at three trial counts:

- **3**: the post-reset ledger (`cumulative_n_trials`).
- **141**: the ledger's lifetime count (`lifetime_n_trials`): the pre-reset 138 plus 3.
- **214**: an entry count.
  - What it counts: 109 `diagnostics/research/preregistry/*.md` (excluding README) + 12 `research/preregistry_*.md`
    + 1 `research/*/prereg.md` + 92 numbered `research/findings/*.md`.
  - Files are counted, not IDs, because the two numbering schemes collide on 55 numbers that name different studies.
  - That makes 214 an upper bound: a study can count twice, and measurements count as trials.

| book | DSR @ 3 | @ 141 | @ 214 |
|---|---|---|---|
| live swing (2019-01..2024-06) | 0.890 | 0.249 | 0.205 |
| 0001 (same slice) | 0.980 | 0.436 | 0.370 |
| blend 15% (2019-03..2024-06) | 0.976 | 0.400 | 0.336 |
| blend 11% | 0.984 | 0.445 | 0.376 |

No book reaches 0.95 at either lifetime count. Artifact: `2026-11-18_risk_matched_benchmark.json → q2_dsr`.

### F3. Risk-matched benchmark

**Method**, fixed before results (`pipelines/diagnostics/explore_risk_matched_benchmark.py` docstring):

- **Benchmark:** TRI daily returns run through the blend's own rule: 20-session lagged volatility, exposure capped
  at 1.0, the rest in cash at 6.5% compounded daily.
- **Blend cash:** the blend keeps its frozen 6% simple cash rate. A parity row with 6.5% cash is also reported.
- **Windowing:** both series are windowed before the rule, so both start at exposure 1.0 for 20 sessions.
- **Drawdown:** 156-week p95 from the stationary bootstrap, block 26 (owner spec) and block 8, 10,000 draws.
- **Worst 3-year return:** the minimum over every calendar 3-year window. The windows overlap, so this is one number
  from one path.
- **"Beats":** blend excess Sharpe is above the benchmark's at the same target.

**Swing window 2019-03..2024-06:**

| target | book | CAGR | Sharpe excess | p95 DD b26 / b8 | worst 3y (ann.) |
|---|---|---|---|---|---|
| 11% | blend | 25.14 | 1.417 | 21.1 / 23.4 | 19.4% |
| 11% | index | 25.15 | 1.411 | 20.8 / 22.7 | 17.2% |
| 13% | blend | 27.44 | 1.406 | 24.3 / 26.7 | 21.6% |
| 13% | index | 26.79 | 1.364 | 24.2 / 26.2 | 18.4% |
| 15% | blend | 29.20 | 1.386 | 27.0 / 29.3 | 23.1% |
| 15% | index | 28.69 | 1.363 | 26.8 / 29.0 | 20.0% |

Paired excess-Sharpe difference, blend minus index, on common dates (block 63, 5,000 draws):

| target | difference | 5–95% CI |
|---|---|---|
| 11% | −0.002 | −0.53 to +0.46 |
| 13% | +0.033 | −0.48 to +0.48 |
| 15% | +0.019 | −0.49 to +0.45 |

With 6.5% cash (the parity row), the blend at 11% scores excess Sharpe 1.425.

**0001 full window 2017-01..2026-06.** The blend can't be built on this window: swing has no NAV before 2019, and
2024-07 onward is sealed. As the nearest substitute, 0001 alone was run through the same rule. It loses to the index
at every target:

| target | 0001 excess Sharpe | index excess Sharpe | 0001 CAGR | index CAGR |
|---|---|---|---|---|
| 11% | 0.627 | 0.805 | 13.6% | 16.3% |
| 15% | 0.688 | 0.799 | — | — |

**Index alone, at the static exposure that meets −25% (block 26):**

| window | exposure | CAGR | excess Sharpe | exposure at block 8 |
|---|---|---|---|---|
| swing window | 0.70 | 25.9% | 1.299 | 0.60 |
| full window | 0.65 | 17.2% | 0.854 | 0.60 |

**Re-derivation (rule 3).** A fresh `blind-replica`, working from the spec only, got:

- Part 2 sweep: identical. The 11% minus 15% excess Sharpe is +0.032.
- Index at 11%: 24.90 CAGR / 1.395 excess Sharpe, against 25.15 / 1.411 here (1.1% relative). The replica dropped the
  first return day and kept 5 weekend special sessions in the TRI.
- Paired difference at 11%: +0.000, against −0.002 here.
- Static exposures 0.70 / 0.65 and entry count 214: identical.

**Artifacts:**

- *Cash-rate asymmetry (6% vs 6.5%):* ruled out by the parity row, which moves excess Sharpe by +0.008.
- *Date alignment and special sessions:* these move the 11% gap anywhere from +0.022 to −0.002. Not ruled out.
  **The sign at 11% is inside method noise.**
- *One path:* every difference lies inside a ±0.5 bootstrap CI. Not ruled out.
- *Window choice:* the swing window is the TRI's best stretch (+34%/yr unlevered). Not ruled out.

**Answer: does the blend beat the risk-matched index at 11%?**

- **Swing window:** nominally yes, 1.417 vs 1.411, but it is a **tie**. The gap is +0.006 on each series' own dates
  and −0.002 to +0.000 on common dates, with a CI of ±0.5.
- **0001 window:** not answerable for the blend, which can't be built there. 0001 alone: **no**.

### F4. Mission fallback wording

Proposed, not applied: `forward/drafts/2026-11-18_mission_fallback_DRAFT.md`, with the diff and the exposure table.

### F5. Circuit lock with NSE's own band data

**Data.** `pipelines/build/fetch_nse_price_bands.py` fetched NSE's public archive into `data/nse_bands/`, with a
manifest and sha256 hashes.

- **Band-hitter lists** (`PRddmmyy.zip → bh*.csv`): all 1,362 sessions from 2019-01-01 to 2024-06-30.
  - 188,312 lower-band rows, of which 14,519 match 471 universe tickers.
  - F&O names have no band, so they never appear.
- **Band files** (`sec_list_DDMMYYYY.csv`): from 2019-12-30 only. 2019 isn't archived (HTTP 404).

**Definitions**, fixed before results:

- *real_lock:* on the lower-band list, and the close is within 0.1% of the low.
- *real_touch:* on the lower-band list at all. This is an upper bound.

An exit on a locked session moves to the open of the next unlocked session. Accounting is as in Part 3.

**Old approximate detector vs real_lock:** precision 0.95, recall **0.18**. The approximation caught about a fifth of
the real locks.

**Trades affected:**

| book | real_lock | real_touch | approximate |
|---|---|---|---|
| dataset A | 4 / 441 | 8 / 441 | 1 / 441 |
| capped swing | 0 / 67 | 2 / 67 | 0 / 67 |
| momentum | 13 / 2,951 | 25 / 2,951 | 2 / 2,951 |

The median move of the real_lock exits is −10.8%.

**Effect** (Sharpe / CAGR / 156-week p95 drawdown at block 8):

| book | base | real_lock | real_touch |
|---|---|---|---|
| momentum | 1.130 / 21.73 / 41.4 | 1.123 / 21.67 / 41.5 | 1.117 / 21.61 / 41.7 |
| blend 15% | 1.790 / 28.97 / 29.33 | 1.782 / 28.86 / 29.52 | 1.779 / 28.84 / 29.56 |
| **blend 11%** | 1.918 / 24.91 / 23.35 | **1.912 / 24.84 / 23.48** | 1.909 / 24.82 / 23.52 |

- The swing book is unchanged under real_lock.
- Equity-scaled accounting matches the fixed-rupee numbers to 0.01.
- **The condition precedent for the 11% draft is met:** 23.48 and 23.52 are both at or under 25.
- Artifact: `2026-11-18_circuit_lock_real_bands.json`.

**Re-derivation (rule 3).** A fresh `blind-replica` working from the spec matched every count:

- 471 tickers and 7,346 real_lock sessions.
- Momentum exits moved: 13 under real_lock, 25 under real_touch. Swing closed trades on a locked session: 0 and 2.
- Momentum after the real_lock adjustment: Sharpe 1.123, CAGR 21.67%.
- Blend 11% p95, base → real_lock: 23.44 → **23.55**, against 23.35 → 23.48 here (0.3% relative).

**Artifacts:**

- *Coverage:* bands cover 2019-01 to 2024-06 only. 0001's exits in 2017–18 and from 2024-07 are not tested. Not
  ruled out. The approximate detector's 2018 BOMDYEING lock falls outside the data.
- *Symbol matching:* renames go through the alias map. An unmatched rename would hide a lock. Not checked name by name.
- *Adjusted OHLCV:* the close-at-low test is invariant to split adjustment. Ruled out.
- *Next-open fill:* a lock can persist into the open; AUBANK's exit moved 9 sessions. Modelled: the search runs to the
  first unlocked session.
- *Sizing feedback:* shown by the equity-scaled row.
