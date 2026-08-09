# Intraday store — feasibility, measured 2026-08-10

**MEASUREMENT, no trial.** Standing counts: screens 19 · sealed opens 1 · n_trials 2.

## Why this was asked

`diagnostics/research/n_trials.json`'s reset rationale names the only way out of the resolution
ceiling, and states the discipline that makes the counter reset honest:

> "A reset counter only means something if the next trials run on data the prior 138 never touched.
> The elected direction is **intraday bars (2h / 15m) for the F&O universe** — genuinely new sample."

Finding 0133 recorded the same gap from the other side: **11 of 22 surveyed positive strategies are
intraday and untested here, because no intraday store exists.**

Every cheap screen on the 2017-2026 daily panel is bounded at n_eff = 37 independent 63-day windows
and a ±0.59 dSharpe half-width, permanently. Building a genuinely new sample is the only action that
moves that number rather than re-spending it. So the direction is right. The question is whether it
is startable.

## First correction: the "intraday scan" is not intraday

`scripts/run_intraday_scan.py:62` calls `yf.download(...)` with **no `interval` argument**, so it
receives daily bars. What it actually does is read *today's partial daily candle* at 14:30 IST and
check whether a watchlist name's setup is forming before the close. That is a useful shadow job and
its own docstring is honest about being observational — but it is **not** an intraday bar source, and
the elected direction has therefore never been started.

## The binding constraint

Measured directly against the live source, `RELIANCE.NS`, with Yahoo's own error text quoted:

| interval | requested | result |
|---|---|---|
| `15m` | 400 days | **EMPTY** — *"The requested range must be within the last **60 days**"* |
| `60m` | 1200 days | **EMPTY** — *"1h data not available … must be within the last **730 days**"* |
| `1h` | 1200 days | **EMPTY** — same 730-day limit |
| `1d` | 1200 days | 813 bars over 1197 days — works |

**The intraday store cannot be built from yfinance.** The ceiling is roughly **2 years of hourly**
and **60 days of 15-minute** data, and neither is retroactively extendable — the history simply is
not served.

## What that means for the n_eff argument, honestly

Two years of hourly bars is about 4,500 bars, which at a 63-bar hold is ~71 non-overlapping windows —
more than the daily panel's 37. **But that is a statistical count, not a regime count.** Those 71
windows all sample the same two calendar years and therefore one market environment. The daily
panel's 37 windows span 2017-2026 and include 2018, COVID, 2022 and 2025.

So an hourly store bought from yfinance would raise the *window count* while lowering the *regime
diversity* — which is the opposite of what the reset rationale was asking for when it said "data the
prior 138 never touched". It would produce narrower confidence intervals around a claim that had
been tested against less of the world.

## The realistic path, and it needs an owner decision

The Kite (Zerodha) historical API serves minute-level data several years back, and the owner already
runs a Kite developer app for market data (it is the repo's existing owner-app arrangement for
quotes). That is the only in-reach source that could support the elected direction.

It is a real acquisition project, not a script: per-instrument rate limits, a PIT-safe store with its
own corporate-action handling, a data-quality gate of its own before any trial is pre-registered, and
a decision about which universe to cover.

**This is therefore not the next engineering task. It is a data-source decision.** Recommended
sequence if it is taken:

1. Owner confirms Kite historical access and its rate limits for the intended universe.
2. Scope the universe deliberately — F&O names, per the reset rationale, not the whole Nifty 500.
3. Build the store with the coverage/PIT audit **first**, on the `skills/verdict-machine` rung order:
   a stream whose coverage audit has not passed may not carry a screen, let alone a trial.
4. Only then does the intraday strategy family become testable.

## What to do instead, in the meantime

Nothing in the daily programme is blocked by this. The remaining Track A items (A2, the narrowed A3)
are small and concrete, and every Track B search runs through screens and bounds that spend no
trials. The ceiling stays at ±0.59 until a genuinely new sample exists, and no amount of daily-panel
work changes that — which is exactly why it should not be discovered halfway through building the
wrong store.

Reproduce the limit check: request `interval="15m"` or `"1h"` over any range longer than 60 or 730
days respectively; Yahoo returns the quoted error rather than truncated data.
