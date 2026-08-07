# ADR-0014 — Annualise by calendar time, and re-anchor every pinned CAGR

**Date:** 2026-08-07 · **Status:** ACCEPTED · **Decider:** owner
**Class:** MEASUREMENT. Zero trials, zero screens. Counts unchanged: screens 19 · sealed opens 1 ·
n_trials 2.

## Context

`nq.engine.portfolio.compute_metrics` computed the length of a backtest as

    years = n_sessions / TRADING_DAYS        # TRADING_DAYS = 252

which declares a year to be exactly 252 sessions. The panels this programme runs on do not supply
252 sessions a year. Measured on the pre-registration 0001 window, they supply **247.5**, so its
2,348 sessions were counted as **9.32 years where 9.49 had elapsed**. A denominator shorter than the
truth inflates any compound rate, and this one fed four published figures: `cagr_pct`, `calmar`,
`turnover_per_year`, and the reported `years` itself.

The overstatement is **0.44pp of CAGR** on that window. It is not a rounding artefact and it is not
confined to one experiment — it applied to every CAGR the programme has ever published, including
the pinned anchor `baseline_v1` and the Stage-2 golden master.

It was found while reconciling a separate defect. `_after_tax_cagr` annualised by calendar days
while gross CAGR annualised by sessions/252, so the two figures sat on different denominators and
their difference — nominally "the tax cost" — carried a 0.43pp artefact of the mismatch, an error the
same size as the effects being measured. Aligning them forced the question of which convention was
correct.

A *compound annual* growth rate is a rate per year. 252 is a convention for counting trading
sessions, not a definition of a year, and the two only coincide if the data actually supplies 252
sessions per year. It does not.

## Decision

**Annualise by calendar time.** `nq.engine.portfolio.elapsed_years` measures the span between the
first and last dates of the equity curve and divides by 365.25, falling back to the session count
only when the curve has no usable dates or spans under a day — which keeps degenerate and synthetic
fixtures behaving as before rather than dividing by zero.

**Sharpe is deliberately unchanged.** It continues to scale by `sqrt(TRADING_DAYS)`. Scaling a
per-period Sharpe by the square root of periods-per-year is the standard convention, and it is a
separate question from how long the sample lasted. Bundling the two would have turned one clean fix
into two entangled ones, and would have moved a figure this change has no business moving.

## Consequences

**The change is provably free of behavioural effect**, which is what makes it MEASUREMENT rather
than ENGINE. On the Stage-2 golden master:

| | before | after |
|---|---|---|
| `GOLDEN_LEDGER_HASH` | `dbc94a1856681195` | **`dbc94a1856681195`** — unchanged |
| n_trades, exit_reasons | 140, {stop 28, trailing 87, target 10, time 15} | unchanged |
| final_equity, total_return_pct | 1,641,679.2 / 64.17% | unchanged |
| sharpe, sortino, max_drawdown_pct | 1.464 / 2.297 / −13.06% | unchanged |
| win_rate, profit_factor, avg_* | — | unchanged |
| **cagr_pct** | 18.47% | **18.02%** |
| **calmar** | 1.41 | **1.38** |
| **turnover_per_year** | 47.9 | **46.8** |
| **years** | 2.92 | **2.99** |

Not one trade moved. Exactly the four figures derived from `years` changed, all downward.

`tests/test_r94_golden.py` is unaffected — it pins final equity, Sharpe, max drawdown, expectancy and
win rate, none of which depend on the sample's length.

**Pins re-anchored** (each carries a dated migration note at its site):

- `tests/test_stage2_golden.py` — `GOLDEN_METRICS`
- `research/0001-xsec-momentum/` — CAGR 22.17% → **21.73%**, Calmar 0.60 → 0.58, turnover 316.7 →
  311.1. Sharpe 1.130, MaxDD −37.17%, 2,951 trades, PBO 0.452 and the Monte-Carlo block all
  unchanged; all seven primary gates still pass.
- `research/baseline_v1.json` — **NOT re-anchored. Blocked, and deliberately left alone.** See below.

**A second instance was found during the re-anchor and fixed with it.**
`pipelines/research/run_0001_xsec_momentum.py::passive_equal_weight` computed `len(eq) / 252.0`
independently of the engine, so when the engine moved to calendar time the benchmark silently did
not. That would have left the pre-registration's *"must clear equal-weight passive ownership"* gate
comparing two different conventions, with the benchmark flattered by ~0.4pp relative to the
candidate it is meant to challenge. Any future duplicate of this arithmetic is the same hazard;
`elapsed_years` is the single source of truth and should be called rather than reimplemented.

**Historical records are not rewritten.** 79 findings and 103 pre-registrations quote CAGRs computed
under the old convention. They are append-only records of what was measured at the time, and
back-editing them would defeat the purpose of keeping them. The convention change is recorded here,
once, centrally; a reader comparing an old finding against a new one must apply it.

**Every historical CAGR in this programme is therefore ~0.4pp lower than published.** The direction
is unflattering, which is the direction that suggests the correction is real. It also narrows the
gap between this programme's headline numbers and the literature band they always sat slightly above.

`tests/test_stage2_golden.py` now pins the convention as a property — `elapsed_years` must track
calendar span — so a future revert fails with a clear cause instead of surfacing as four
mysteriously drifted metrics.

## `baseline_v1` could not be re-anchored, and the reason is a separate defect

The intent was to regenerate `research/baseline_v1.json` from its designated producer,
`scripts/run_corrected_anchor.py`, rather than adjust it arithmetically. Running it full-window
produced, for LH base on the corrected universe:

| | `baseline_v1.json` (pinned) | producer output, 2026-08-07 |
|---|---|---|
| Sharpe | **0.667** | **0.647** |
| CAGR | 15.46% | 14.88% |
| MaxDD | −46.26% | −46.3% |

**The Sharpe disagreement cannot be caused by this ADR.** `run_corrected_anchor.py` carries its own
private `metrics()` function which never calls `compute_metrics`; it computes Sharpe and CAGR
directly, on bar-years, with `pandas.Series.std()` (ddof=1) where the engine uses NumPy's ddof=0.
Nothing in this change touches any of that. The 0.667 → 0.647 gap therefore **predates today** and
was already present the last time anyone looked.

Two possibilities, and this ADR does not choose between them: either the pinned block was produced
by a different path than the one `provenance.producer` names, or the producer has drifted from the
pin since the 2026-08-05 audit closeout recorded it as reproducing.

**So the pin is left untouched.** Overwriting a governance anchor with numbers from a harness that
does not reproduce it would fold an unexplained pre-existing discrepancy into a cleanly-scoped
measurement change, and the resulting figure would be attributable to neither. `baseline_v1` remains
on the old annualisation convention, is now **knowingly ~0.4pp high on CAGR** for that reason alone,
and needs its own investigation — which is a reproduce-before-trust question about the anchor's
provenance, not an annualisation question.

Arithmetically the calendar-time value would be ~**15.16%** (from 15.46% over the same 9.32 → 9.49
year correction), but that number is recorded here as an expectation to check against, **not** as a
re-anchor, precisely because a chat-derived figure is not a reproducible one.
