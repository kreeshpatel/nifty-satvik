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

| target | CAGR % | Sharpe | backtest worst | 156-wk p95 | meets −25% |
|---|---|---|---|---|---|
| 8% | 20.88 | 2.112 | −13.0% | 17.2 | yes |
| 9% | 22.35 | 2.032 | −14.6% | 19.4 | yes |
| 10% | 23.80 | 1.978 | −16.1% | 21.4 | yes |
| **11%** | **25.14** | **1.932** | **−17.7%** | **23.4** | **yes — highest** |
| 12% | 26.40 | 1.898 | −19.1% | 25.0 | no (by 0.03 pp) |
| 13% | 27.44 | 1.861 | −20.5% | 26.7 | no |
| 14% | 28.46 | 1.833 | −21.7% | 28.2 | no |
| 15% | 29.20 | 1.801 | −22.85% | 29.3 | no |

Moving 15% → 11% costs **−4.06 pp CAGR** and *raises* Sharpe by +0.13 (cash at 6% is a large, low-variance share at
low targets). Picked by the drawdown rule only.

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
not across strategies — disclosed. (3) *DSR at n_trials 3*: the programme's lifetime count is far larger; DSR at the
certified 114 would be lower — not computed here. (4) *Fold length ~6 months*: wide per-fold noise.
