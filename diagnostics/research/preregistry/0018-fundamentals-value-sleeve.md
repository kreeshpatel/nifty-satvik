# 0018 — Fundamentals value sleeve (ep, 60/126d hold) — breadth Sleeve 2

- **ID:** 0018 (breadth program Sleeve 2; first orthogonal-signal sleeve after the
  honest base was LOCKED — see `diagnostics/research/locked_honest_base.md`)
- **Registered:** 2026-06-08 (BEFORE the Step-2 walk-forward; Step-1 IC is
  hypothesis-generation and is allowed to precede the pre-reg)
- **Holdout:** walk-forward vs the LOCKED honest base → unseen-universe → forward wall.
  Reproducible-only verdicts (`REPRODUCIBLE_MODE=1`). DSR-gated.
- **n_trials (cumulative):** 17 at lock → this experiment adds up to 4 arms
  ({raw-ep, sector-neutral-ep} × {60d, 126d}); the primary arm is pre-committed from
  the Step-1 IC (ep @ 126d) so DSR deflation counts the arms actually evaluated.
- **Status:** Step-1 IC **DONE → SUPPORT** (see Result). Step-2 (the sleeve
  walk-forward) is gated on building the sleeve + the generic runner.

## Context

The honest base is locked (single-model reproducible+embargoed Sharpe 0.81 / CAGR 15.4%,
2019+; live ensemble ~0.45 typical → 1.0 mean). The momentum model is at its price/volume
ceiling (17 kills). Improvement now comes from **breadth** — orthogonal thin edges. The
one orthogonal lever with a *measured* real IC is **value (earnings yield)**: 0017 + the
2026-06-08 Step-1 re-run both find **ep IC-IR ≈ 0.25 (t≈2.6) at 126 days**, ≈0 at 14 days.
It is structurally orthogonal to a 14-day momentum picker (a cheapness signal the price
model cannot see), and it expresses at a horizon ~9× the model — so it is a **separate
low-turnover sleeve**, NOT a 14-day feature (the 0017 verdict).

## Hypothesis

A monthly-rebalanced, **ep-top-decile, long-only** value sleeve held ~126 days (primary;
60 days secondary) earns a **modest positive after-cost expectancy** that is **orthogonal**
(daily-return corr < 0.30) to the 14-day momentum sleeve, so adding it as a breadth sleeve
improves the portfolio's risk-adjusted return without merely levering momentum.

## Critical correctness guard — LOOKAHEAD

Every factor read goes through `fundamentals_pit.point_in_time_value(frame, field, as_of)`
which returns the latest row with **`available_date < as_of`** (strict). For the Screener
annual store, `available_date = period_end + 90d` (`ANNUAL_REPORTING_LAG_DAYS`, conservative
SEBI-LODR lag; over-lagging is safe, under-lagging leaks). The sleeve never touches
reporting dates directly. Forward returns appear ONLY in the IC diagnostic
(`close.shift(-h)`), never in signal construction. Walk-forward folds carry
`embargo_days = ceil(126*7/5) ≈ 177` (resp. 84 for 60d) to purge the long-horizon label
across the train/test boundary — the single biggest self-deception risk at this horizon.

## Design

- **Factor: ep only.** Exclude `low_debt` (IC negative — the Indian leverage/junk-rally
  premium) and `roe` (null); `bp` is too weak (t=1.5 < 2) → excluded. `LONG_FACTORS=("ep",)`
  is a named constant so the exclusions are auditable, not silent.
- **Construction:** at each date, rank ep cross-sectionally over the as-of-eligible universe
  (`cross_sectional_rank`, NaN→0.5 neutral so sparse coverage can't tilt). **Long the top
  decile** (`ep_rank ≥ 0.90`); long-only (the system is long-only — no shorting the
  expensive decile). Confidence = ep_rank; entry gate `min_confidence = 0.90`. The long
  hold (~126d) makes effective turnover monthly-ish via one-open-position-per-ticker.
- **Horizons (the two arms):** 126d primary (where the IC lives), 60d secondary (interacts
  more naturally with the existing exit machinery). Scorecard picks; the other is reported.
- **Sector-neutral variant (2nd dimension):** also test ranking ep *within* `get_sector`
  buckets, to check value isn't just a disguised sector bet. Pre-registered as the 2nd arm.
- **Costs:** honest — brokerage 0.03%/leg + STT 0.1% sell + tier slippage + ADV impact
  (shared `engine._simulate`). A 126d hold trades ~1/9th as often as the 14d sleeve, so cost
  drag is structurally low — but it is charged, or the result is void.
- **Universe:** the corrected/expanded membership (survivorship-corrected). On survivor-only
  data the verdict is INCONCLUSIVE, never PROMOTE (value ranking is especially survivorship-
  sensitive — deleted cheap-and-falling names are the value trap survivor data hides).

## Decision rule (one-shot, fixed BEFORE the run; no tweaking)

- **PROMOTE-to-shadow** iff ALL: (1) `balanced_scorecard` PASS vs the locked base **at the
  sleeve's own horizon**; (2) **DSR > 0.95** at cumulative `n_trials`; (3) daily-return
  **corr < 0.30** with the momentum sleeve (the breadth gate); (4) primary-metric (mean
  after-cost per-trade return) bootstrap **CI-low > 0**; (5) Step-1 ep IC survived on the
  corrected universe. PROMOTE = shadow-track only; live capital needs the forward-wall
  ≥30-closed-trade CI>0 confirmation.
- **KILL** if any fails. No horizon-shopping beyond the two arms, no universe-shopping, no
  re-tuning the decile/target and re-running. A KILL is final for this hypothesis.
- **INCONCLUSIVE** only if the corrected-universe data isn't ready (survivor-only run).

## Honest prior (~40-50%)

The value premium in a large-cap, well-arbitraged universe is real but **modest**
(single-digit annualized, thin Sharpe ~0.2-0.4, lumpy across regimes, fragile to value
drawdowns). We expect a **diversifier**, not an alpha cannon — and the bar is breadth
(orthogonality + a positive standalone edge), not beating momentum head-to-head. Given the
0012/0016 kill-record, a KILL is a very live outcome and a cheap, valid one.

## Result

### Step-1 — IC screen (2026-06-08, `pit_factor_ic_sprint1.json`) — SUPPORT

Deep Screener store, 88-91% coverage every year 2017-2026 (all 110 monthly dates clear the
0.70 floor):

| factor | 14d IC-IR | 63d | 126d |
|---|---|---|---|
| **ep** | +0.095 (t=1.0) | +0.197 (t=2.04) | **+0.254 (t=2.59), hit 59%** |
| bp | +0.01 | +0.11 | +0.15 (t=1.5) |
| roe | +0.02 | −0.05 | −0.12 |
| low_debt | −0.10 | −0.16 | −0.16 |

ep clears the pre-registered gate (IC-IR ≥ 0.20, t ≥ 2.0 at 126d); matches 0017 (not a
one-off). bp too weak (exclude), roe null (exclude), low_debt negative (exclude). →
**Proceed to Step-2: build the ep-only top-decile sleeve at 126d (primary) / 60d
(secondary) and walk-forward it vs the locked base.**

### Step-2 — sleeve walk-forward — LOCAL first read (INCONCLUSIVE, pending cloud)

Built `src/strategies/fundamentals_value_sleeve.py` (PanelSleeve) + the generic
`diagnostics/run_sleeve_walkforward.py` runner (Part 2A.2; reuses
expanding_window_folds / run_walk_forward / `_simulate` / DSR / bootstrap). Ran
`value_ep_126d` over 2019-2025 (7 folds) **on the LOCAL survivor-ish 497-name universe**
(reproducible, `_simulate` costs on; momentum entry filters off — they contradict a value
premise):

| year | Sharpe | CAGR | WR | trades |
|---|---|---|---|---|
| 2019 | +0.48 | +3.7% | 62% | 34 |
| 2020 | +1.14 | +13.0% | 61% | 36 |
| 2021 | +2.11 | +19.2% | 67% | 33 |
| 2022 | +0.58 | +5.2% | 56% | 34 |
| 2023 | **+3.13** | +27.8% | 81% | 36 |
| 2024 | +0.92 | +9.0% | 53% | 32 |
| 2025 | −0.32 | −3.4% | 53% | 30 |

**Aggregate:** mean Sharpe **+1.148** (locked base 0.812), mean CAGR **+10.64%** (base
15.38%), WR 61.78%, 235 trades. **DSR 0.025** (FAIL >0.95 — the 2023 outlier inflates the
skew/kurtosis deflation at n_trials=18), **per-trade +1.025% CI [−0.088, +2.115]**
(CI-low ≤ 0 → FAIL).

**Verdict: INCONCLUSIVE (does NOT cleanly clear the gate; local survivor universe).**
Encouraging — positive 6/7 years, WR ~62%, beats the base on mean Sharpe — but it fails
the strict bars (DSR>0.95, CI-low>0), and per the pre-reg a survivor-only run is
INCONCLUSIVE-never-PROMOTE regardless (value ranking is the most survivorship-sensitive
signal). **Two things gate the authoritative verdict:** (1) the **corrected/expanded
universe** (cloud, like the honest-baseline run) — survivor data disadvantages value and
the local mean is outlier-leaning; (2) the **breadth/correlation gate** (is this daily
return stream actually orthogonal, corr<0.30, to momentum?) — deferred to the composition
stage (Part 2B), which produces the momentum daily-return series. Runner artifacts:
`sleeve_value_ep_126d_local{,_verdict}.json`.

### Step-2 FINAL — CORRECTED universe (run 27144836995) — **KILL**

Authoritative run on the CORRECTED + expanded universe (membership_v2 real exits +
recovered dropped-name OHLCV), reproducible, all 3 pre-registered arms, 2019-2025 (7
folds), vs the locked base (Sharpe 0.812 / CAGR 15.38%):

| arm | mean Sharpe | mean CAGR | WR | trades | DSR | per-trade CI |
|---|---|---|---|---|---|---|
| ep 126d | 1.004 | 7.42% | 54.4% | 240 | **0.052** | +0.66% **[−0.28, +1.57]** |
| ep 126d sector-neutral | 1.007 | 7.55% | 59.9% | 234 | **0.019** | +0.52% **[−0.55, +1.56]** |
| ep 60d | 0.897 | 6.32% | 51.9% | 242 | **0.011** | +0.39% **[−0.53, +1.31]** |

**Verdict: KILL (all 3 arms).** The decision rule fails on TWO independent criteria for
every arm: **DSR ≈ 0.01-0.05 ≪ 0.95**, and the **per-trade bootstrap CI-low < 0** (the
~+0.5%/trade edge is NOT statistically distinguishable from zero on ~240 trades). The mean
Sharpe ~1.0 is misleading (Sharpe-of-fold-means flattered by a couple of strong folds);
the per-trade CI is the honest read and it straddles zero. CAGR ~7% also underperforms the
momentum base (15.4%). As the pre-reg predicted, the corrected universe **lowered** the
value edge vs the survivor-only local read (CAGR 10.6% → 7.4%) — survivor data had flattered
it. The orthogonality/breadth gate is moot (a sleeve must first clear a significant
standalone edge; ep value does not, in this long-only top-decile form).

This is the honest prior realized ("a KILL is a very live outcome"). ep value is real as a
**slow factor IC** (Step-1, t=2.6 @126d) but does NOT survive as a tradeable long-only
top-decile sleeve after costs on the corrected universe. **n_trials → 21** (3 arms added).
Sleeve 2 is CLOSED. Artifacts: `sleeve_value_ep_*_corrected{,_verdict}.json`. Next breadth
candidate: Sleeve 1 (FII/DII flows).
