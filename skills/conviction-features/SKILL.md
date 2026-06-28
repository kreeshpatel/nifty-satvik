---
name: conviction-features
description: >
  How to add a candidate feature to the Phase-5 per-trade conviction model — the
  within-top-15 quality score (0-1) that distinguishes higher-quality from lower-quality
  setups among names that all clear the cross-sectional rank gate.
  Trigger phrases: "conviction feature", "ranking model", "per-trade quality",
  "PIT-safe feature", "within-portfolio quality", "conviction score", "conviction quintile".
---

# Phase-5 Conviction Features

## What this is

The long-horizon strategy selects the **top-15 names by `sma200_slope_63`** from a
filtered universe each day. Every name that clears the cross-sectional rank gate has
already passed the same entry bar. The Phase-5 conviction model asks a finer question:
**among those 15 slots, which setups are higher-quality?**

The output is a per-signal `conviction_score` in [0, 1] and its ordinal bucketing
`conviction_quintile` in {Q1..Q5}. The score does **not** change position sizing in
the base strategy (sizing is risk-budget-only, per §7 of `long_horizon/STRATEGY_FULL.md`)
but it feeds:
- The S3 and R1/R2 sell/replace rules (see `skills/sell-replace-logic/SKILL.md`)
- The dashboard grade display (currently driven by `trend_rank_pct` alone; Phase 5
  replaces it with the richer score)
- Forward-wall research tracking (does high-conviction actually predict better outcomes?)

The strategy's core signal is frozen. This score sits **on top** of it, not in place of it.

---

## 1. The contract — PIT safety is non-negotiable

Every feature in the conviction model MUST satisfy all three conditions:

### 1a. Computed only from data available at signal time

No future data whatsoever. The computation for a signal generated on day `t` may only
use OHLCV data through close of day `t`, and fundamentals data published on or before
day `t` (the Screener PIT store carries a ~90-day publication lag — respect it).

A feature that reads tomorrow's open, uses a contemporaneous label, or implicitly
conditions on whether the trade worked is an **automatic REJECT** — not a "test and see".
The feature-contract discipline from `src/.claude/rules/src.md` applies here without
exception: lookahead bias in a financial feature does not show up as a bug, it shows up
as inflated backtest performance that collapses live.

### 1b. Backward-only rolling windows

Every indicator must be computed from a window that closes at or before signal date `t`.
The same restriction the strategy's core signal follows:
```
sma200_slope_63(t) = SMA200(t) / SMA200(t-63) - 1   # backward-only, PIT-clean
```
Any new feature must follow the same pattern. Use `df['col'].rolling(N).func()` on
date-ordered data with no `min_periods` tricks that implicitly look forward.

### 1c. Identical computation offline and live

The single biggest source of live/backtest divergence in the v1 engine was features
computed one way in the training pipeline and a slightly different way in the live
scanner. **The conviction model must have one code path**, not a "backtest version"
and a "live version". The canonical pattern in this codebase (from
`data/feature_enrichment.py` and `data/data_store.py`) is: one function, one module,
imported by both paths. Follow it. Any feature that cannot be computed from the same
code with the same inputs at signal time as at training time is rejected.

**Test this explicitly:** after implementing a feature, compare its value for 10 random
(ticker, date) pairs between the offline training dataset and a live-mode run on those
same dates. If any value differs: REJECT and diagnose before proceeding.

---

## 2. Candidate feature families

Each entry is a **hypothesis**, not a confirmed edge. None has been validated against
the Phase-5 harness. Pre-register before testing (follow `diagnostics/research/preregistry/`
discipline and increment `n_trials.json`).

### F1 — Signal strength / gap above the #15 threshold

**Hypothesis:** Among the top 15, a name ranked #1–#5 with a large gap above the
marginal #15 name is in a qualitatively stronger trend. Cross-sectional rank alone
ignores the gap.

**Feature:** `rank_gap_15 = sma200_slope_63(i) - sma200_slope_63(rank_15)`, where
`rank_15` is the 15th-ranked name's slope value on that day's eligible universe. This
is a positive float for any name inside the top 15.

**PIT check:** derived entirely from the current-day cross-sectional ranking. Clean.

**Caution:** the gap is a function of the universe composition that day, which itself
depends on who passes the solvency filter — stable enough for cross-sectional use, but
noisy if the filtered universe is small (<100 names on a given day).

### F2 — Trend persistence (rank stability)

**Hypothesis:** A name that has been in the top 15 for N of the last M trading sessions
is exhibiting persistent strength, not a one-day spike into the selection window.

**Feature:** `rank_stability_20 = fraction of the last 20 trading days on which the
ticker would have ranked in the top-quartile of the eligible universe`. Requires storing
or re-computing daily rank history for the recent window.

**PIT check:** uses only data through day `t`. Clean if computed from lagged data.

**Caution:** computationally expensive in the live cron (requires re-ranking historical
days). Consider pre-computing on the rolling panel rather than re-running the full
universe each day. Also: persistence is partly implied by `sma200_slope_63` itself
(the 200-day SMA doesn't flip in a day); marginal IC may be low.

### F3 — Volatility regime / ATR percentile

**Hypothesis:** The strategy's stop is `3.67 × ATR(63)`. A low-ATR entry means a
tighter stop in price distance, a smaller position (risk budget / stop distance), and
a smoother ride. High-ATR names are more volatile and the fixed stop can be triggered
by noise alone.

**Feature:** `atr_pct_63_rank` — the cross-sectional percentile of `atr_pct_63` among
the top-15 universe on that day (lower = less volatile = higher conviction for this
feature). Equivalently, `atr_z = (atr_pct_63(i) - mean(top15_atr)) / std(top15_atr)`,
with a negative z-score meaning lower-vol-than-average.

**PIT check:** `atr_pct_63` is already computed in `data/data_store.py` as a
backward-only indicator. Clean.

**Caution:** §11 of `STRATEGY_FULL.md` records that signal-level low-volatility blending
was tested and killed. That was at the *selection* level (mixing a low-vol signal into
the ranking). This feature is at the *conviction* level (within already-selected names).
These are distinct hypotheses, but the burden of proof is elevated — the prior
evidence is negative. Pre-register clearly and validate against the `2022-2026`
sub-period specifically (where volatility regimes differ from the bull years).

### F4 — Drawdown from 52-week high

**Hypothesis:** A name that is near its 52-week high is in a healthier trend state
than one that has corrected 20%+ and is bouncing. The former is in uncharted territory
(lower overhead resistance); the latter may face supply from trapped buyers.

**Feature:** `drawdown_from_52w = (close - high_252) / high_252`, where `high_252` is
the rolling 252-day closing high (exactly one trading year). A value close to 0.0 means
near the high; a value of −0.20 means 20% off the high.

**PIT check:** `rolling(252).max()` on the close, applied to data through day `t`. Clean.

**Caution:** The 200-day SMA slope already captures multi-month trend direction; the
52-week high drawdown is correlated. Marginal IC vs the main signal may be low. That
said, a name can have a rising 200-day SMA while being well off its recent high (e.g.,
after a sharp correction in a longer uptrend) — the two can diverge, which is where
this feature adds information.

### F5 — Earnings momentum from PIT fundamentals

**Hypothesis:** A name whose most recent reported EPS or revenue growth (on the PIT
Screener store) is accelerating is a higher-quality trend name — the earnings drift
provides a fundamental anchor for the price momentum.

**Feature candidates:** YoY revenue growth (latest vs prior quarter in the PIT store),
or QoQ EPS acceleration sign. Use only the `fundamentals_pit_screener.pkl` store with
strict publication-lag discipline (use `period_end` + 90-day lag, never the filing date
directly — it may post-date the fiscal period by weeks).

**PIT check:** the Screener store is already keyed by `period_end` and the cron
applies a ~90-day publication lag. As long as you query the most-recent period that was
published on or before `t − 90d`, this is PIT-clean.

**Caution:** §11 records that `earnings + ROE` screens on top of the debt filter
over-filtered and hurt performance. That was at the *selection* level (gates that cut
the universe). As a *scoring* feature inside already-selected names, the over-filter
risk is absent — but the evidence for earnings momentum adding information at a 63-day
horizon is mixed. Low sample size per-stock (4 data points/year). The Screener store
refresh lag means data can be stale in a fast-moving quarter. Treat this as high
prior-uncertainty.

### F6 — Sector momentum (restricted use)

**Hypothesis:** A name whose sector peers are also in strong uptrends is exhibiting
sector-aided momentum, which is more durable than isolated idiosyncratic momentum.

**Feature:** `sector_slope_median_63` — the median `sma200_slope_63` among all large+mid
names in the same sector on day `t`. High = sector tailwind.

**PIT check:** computed from the same daily cross-section as the main signal. Clean.

**STRONG CAUTION:** §11 records sector overlays tested and **hurt** the strategy's lean
years (sector momentum IC ≈ 0 from the June 2026 audit). The `brain.md` and
`STRATEGY_FULL.md` §8 both explicitly note sector-exposure caps and sector overlays are
deliberately absent. This feature carries a high rejection prior. If you test it:
- Pre-register separately, with a specific hypothesis about *why* sector momentum
  would add information at the within-top-15 conviction level when it fails at the
  selection level.
- Require the 2022–2026 sub-period to show positive ΔConviction-Accuracy — if the
  sub-period disagrees with the full history, **reject**.

### F7 — Market regime / breadth context

**Hypothesis:** A signal generated when broad market breadth is strong (many stocks above
their 200-DMA) is in a more supportive environment than one generated in a narrow or
deteriorating breadth regime.

**Feature:** `market_breadth_score` — the fraction of the eligible Nifty-500 universe
with close > SMA200 on day `t`, computed from the same daily OHLCV panel.

**PIT check:** computed from current-day cross-section. Clean.

**STRONG CAUTION:** §11 records the market-regime gate was tested in 4 arms and killed:
"cuts drawdown but kills CAGR (sidelines the best trending years)". `brain.md` records
"REGIME GATE = KILL (full universe, 682 names): all 4 arms HURT." The **gate** is
definitely dead. The conviction-scoring use is a weaker formulation (it tilts within
selected names, doesn't exclude entries), and the prior evidence is still negative.
Pre-register with the specific claim that breadth *tilts* within-top-15 outcomes, not
that it gates the strategy.

---

## 3. Model forms allowed

The conviction model must remain interpretable. The strategy's edge is documented as
rule-based clarity (`long_horizon/STRATEGY_FULL.md` §2 and `long_horizon/charter.md`).
A black-box ranker inside an already-interpretable strategy creates an unexplainable
stratum — which is exactly the failure mode the v1 experience cautioned against.

### Allowed — use these in preference order

**Form A: Equal-weight z-score blend (baseline)**
```python
# For each feature f in [F1, F2, ...], z-score cross-sectionally among the top-15 names:
z_f = (f_i - mean_top15(f)) / std_top15(f)
conviction_score = sigmoid( sum(w_f * z_f) )   # w_f = 1/N for equal-weight
```
Start here. No training required, always explainable, minimal overfit risk given ~15
in-portfolio names per day.

**Form B: Ranked feature composite with manually set weights**
```python
# Rank each feature within the top-15, normalize to [0,1], then sum with chosen weights
rank_f = argsort_pct(f, ascending=best_direction)
conviction_score = sum(w_f * rank_f_i)
```
Use if features have different directions (e.g., high rank_gap is good, low ATR is good).
Weights must be chosen before seeing the backtest outcome (pre-committed), not tuned to
maximize backtested conviction-accuracy.

**Form C: Logistic regression on triple-barrier labels**
```python
# Label each entry with a 63-day triple-barrier outcome:
#   1 = hit target before stop, 0 = hit stop or time-out first
# Features = the PIT-clean f-vector at entry date
# Train on pre-2017 data only (the same training slice as the frozen cfg)
# Test on 2017+ holdout (use cpcv from validation/cpcv.py, not a single split)
logit = LogisticRegression(C=0.1, max_iter=500)   # regularized; NOT a deep model
conviction_score = logit.predict_proba(X)[:, 1]
```
Allowed because it is low-capacity, interpretable (sign and magnitude of coefficients
are meaningful), and directly calibrated to the triple-barrier label that defines the
strategy's win condition. The training split MUST be strictly pre-2017; the same
walk-forward discipline used for the main cfg derivation applies here.

### Not allowed

- LightGBM, XGBoost, random forest, or any tree ensemble — the feature importance is
  post-hoc and non-linear interactions among 15-name cross-sections are nearly impossible
  to audit for lookahead.
- Neural networks of any kind.
- Any model with more parameters than training examples. With ~150 trades/year and
  pre-2017 training, the effective sample is ~1000-1500 trades. Regularize aggressively
  and prefer fewer, more certain features over many uncertain ones.
- Any model trained on post-2017 data. That is the test set; it must not be touched
  during model selection or weight tuning.

---

## 4. Validation — the conviction-ranked selection test

The validation question is: **does a conviction-ranked selection improve outcomes
compared to rank-ranked selection?**

Two specific comparisons must be computed:

### Test A: Conviction-top-15 vs Rank-top-15 (same portfolio size)

- Run the base strategy as the baseline (rank-top-15 by `sma200_slope_63`).
- Build the alternative: select the top-15 by **conviction_score**, where the eligible
  pool is the top-30 by `sma200_slope_63` (i.e., loosen the rank gate to 30, then
  re-rank by conviction within that set). This tests whether the conviction score
  identifies better positions among plausible candidates.
- Report: ΔCAGR, ΔSharpe, ΔCalmar, ΔMaxDD, ΔWin-rate, ΔTurnover, 2017-2021 vs
  2022-2026 sub-periods separately, and walk-forward fold-pass rate.

### Test B: Conviction-top-10 vs Rank-top-15 (fewer, higher-conviction positions)

- Run the alternative: select only the top-10 names by conviction_score from the
  top-20 by rank. Fewer positions, higher conviction cut.
- This tests whether the score identifies 10 sufficiently better names that the
  reduced breadth (and therefore lower expected drawdown from fewer positions) is
  worth the concentration increase.
- **Watch for:** lower CAGR as a result of fewer positions. The conviction score must
  compensate — a conviction-10 that is simply a lower-breadth version of rank-15 without
  a quality lift is not a useful model.

### Harness

Use the overlay-testing harness described in `skills/overlay-testing/SKILL.md`. The
conviction model is an overlay on the base strategy, not a replacement for it — it must
clear the **promotion bar** defined there:

| Bar | Threshold |
|---|---|
| Post-tax post-cost ΔSharpe | ≥ +0.10 |
| Post-tax post-cost ΔCalmar | ≥ +0.05 |
| 2022–2026 sub-period ΔCAGR | Positive |
| Walk-forward fold-pass rate | ≥ 60% |
| Bootstrap 95% CI on ΔSharpe | Excludes zero |
| Turnover increase | ≤ 30% |
| Mechanism explainable in one sentence | Required |

**SHADOW** (log conviction score alongside each signal, do not act on it in sizing or
selection) if 4-5 of the above hold. **REJECT** otherwise. Log the verdict in
`long_horizon/research/overlay_registry.md`.

### Forward-wall test (mandatory before any live use)

Because the training slice is small (pre-2017, ~500-700 qualifying trades depending on
universe) and the conviction model has free parameters, a forward wall observation period
is required even after the backtest passes:

- Generate conviction scores on the live paper-trading signals (2026-07 onward) without
  acting on them.
- After ≥ 50 paper-trade closures, compute the within-portfolio conviction-quartile
  win-rate split. Q5 should outperform Q1 at ≥ 5pp WR advantage to be consistent with
  the training signal.
- If the forward wall disagrees with the backtest, **REJECT** and diagnose.

---

## 5. Output contract — what goes into signals_today.json

Once a conviction model is validated and promoted, each signal entry in
`results/signals_today.json` (and `results/signals_history.json`) must carry these
additional fields, added by `long_horizon_cron.py::_wire()`:

```json
{
  "conviction_score": 0.78,
  "conviction_quintile": "Q4",
  "conviction_features": {
    "rank_gap_15":      0.71,
    "atr_pct_63_rank":  0.61,
    "drawdown_52w":     0.82,
    "sector_slope":     null
  }
}
```

**Schema rules:**
- `conviction_score`: float in [0, 1], rounded to 2 decimal places. Higher = stronger
  per-trade quality. MUST be derivable purely from data at `signal_date` (same PIT
  constraint as every other field in the signal).
- `conviction_quintile`: string in {"Q1", "Q2", "Q3", "Q4", "Q5"}. Q5 is highest
  conviction. Computed daily cross-sectionally among the current top-15 held + new
  entries — not relative to the full eligible universe.
- `conviction_features`: dict mapping each contributing feature name to its normalised
  contribution (z-score or rank-pct) in [0, 1], or `null` if that feature had no data
  on that signal date. Every feature listed here must correspond to one of the validated
  candidates above — no mystery inputs.
- The existing `grade` / `conviction` fields (currently derived from `trend_rank_pct`
  in `_grade()` at `long_horizon_cron.py:178`) remain for backward compatibility with
  the dashboard until the Phase-5 model is promoted. After promotion, `grade` and
  `conviction` are re-derived from `conviction_quintile` (Q5/Q4 → HIGH, Q3 → MEDIUM,
  Q1/Q2 → LOW) and the old percentile-only mapping is removed.

**The `conviction_score` field must never appear in the signal before the model is
validated.** Publish a stub-`null` field during the SHADOW phase:
```json
{ "conviction_score": null, "conviction_quintile": null, "conviction_features": {} }
```
This lets the dashboard handle the field gracefully before promotion without implying
the model is live.

---

## How this fits the program

The Phase-5 conviction model is deferred until the forward wall from paper trading
accumulates (≥ 30 closed trades, ~2 months, per the gate in `STRATEGY_FULL.md` §14).
The development sequence is:

1. **Shadow phase** (now through paper-trading gate): add `conviction_score: null` to
   each signal so the schema is established; start recording the raw feature values that
   would feed the model without acting on them.
2. **Model development** (once ≥ 30 paper trades closed): pre-register the specific
   feature set and model form; run Tests A and B through the overlay harness; check the
   forward wall.
3. **Promotion** (if the harness passes): update `_wire()` to populate the score; update
   the dashboard `SignalCard`/`SignalDetailDrawer` to display it; retire the rank-pct-only
   `_grade()` mapping.

**Do not skip the shadow phase.** The temptation to compute a score and immediately
use it for sell/replace decisions (S3, R1/R2 in `skills/sell-replace-logic/SKILL.md`)
is real, but the conviction model itself must accrue a forward-wall track record before
those rules can trust it. A sell rule that fires on a conviction score that has not been
validated is not a conviction rule — it is an untested rule dressed up as one.

---

## What is NOT part of this phase

- **ML-based selection rankers** (LightGBM on LONG_HORIZON_FEATURES): a separate Phase-6
  item in `long_horizon/charter.md`, deferred until the rule-based strategy has a forward-
  wall track record.
- **News sentiment / AI sector-regime features**: forward-only by construction (cannot
  be PIT-reconstructed), permanently excluded from the backtest. May be wired as
  live-only overlays on the forward wall, but they are not part of the conviction model.
- **Changes to position sizing**: the base strategy sizes purely on risk-budget (§7 of
  `STRATEGY_FULL.md`). A conviction multiplier on sizing (`conviction_score × base_size`)
  would be a separate pre-registered experiment, not a consequence of building the model.
  The frozen config already explicitly notes "No conviction / quality multiplier on size."
