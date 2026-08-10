# Intraday store — feasibility, measured 2026-08-10

> ## ⚠ CORRECTED later the same day
>
> The conclusion below — "not startable, treat it as a data-source decision" — was reached against
> **yfinance only** and generalised too far. Kite Connect's documented limits are **per-request page
> sizes on history it actually holds**, not ceilings on available history. The store is buildable,
> the fetch is under an hour, and the depth covers the regimes that matter. The yfinance
> measurements stand; the conclusion drawn from them does not. See the corrected finding at the end.

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

---

# Corrected finding — Kite Connect makes this buildable

## The limits are PER REQUEST, not total

[Kite Connect historical candle docs](https://kite.trade/docs/connect/v3/historical/) and the
developer forum give maximum lookback **per request**:

| interval | days per request |
|---|--:|
| 1–2 minute | 60 |
| 3–10 minute | 100 |
| **15–30 minute** | **200** |
| 60 minute – 4 hour | 400 |
| day / week | 2000 |

You paginate. That is the distinction missed above: yfinance's 60/730-day caps are hard ceilings on
*available history*; Kite's are page sizes on history it holds.

## Depth reaches the regimes we need

A forum report of minute data for RELIANCE from **2015-01-01**
([discussion](https://kite.trade/forum/discussion/9129/how-many-past-days-historical-data-can-be-fetched-for-minute-candle))
puts depth well before our 2017 start. That matters more than the interval: it spans **2018, COVID,
2022 and 2025** — the four regimes the daily panel's 37 windows cover. **The regime-diversity
objection raised above does not apply to a Kite-sourced store**, and that objection was the
load-bearing half of the argument against building.

## Cost of acquisition, computed

2017-01-01 → 2026-06-30 is ~3,468 days. At the documented 3 requests/second:

| interval | pages/instrument | 200 names | 561 names (MID ever-traded) |
|---|--:|--:|--:|
| 15-minute | 18 | ~20 min | ~56 min |
| 60-minute | 9 | ~10 min | ~28 min |

**Under an hour for the full history.** Historical data is now included in the base Kite Connect
subscription rather than a separate add-on
([announcement](https://kite.trade/forum/discussion/14806/historical-data-is-now-free-with-base-kite-connect-subscription)).

## The hard parts are NOT the fetching

Three unverified risks, and they are the real project:

1. **Survivorship, possibly worse than the daily pin.** Kite's instrument list is *current*. A name
   delisted in 2019 may have no retrievable endpoint at all. The daily store already carries 103/813
   missing members and needed a bhavcopy backfill; an intraday store could be structurally unable to
   reconstruct the delisted tail — survivor-only **by construction**, flattering in precisely the
   direction this programme has been burned by.
2. **Corporate-action convention** — adjusted or unadjusted, and how splits behave across a
   paginated fetch. The split-vs-demerger distinction (the VEDL lesson) must hold in the new store.
3. **Instrument-token stability** across nine years of symbol changes.

## Other sources, for comparison

- [TickData](https://www.tickdata.com/equity-data/national-stock-exchange-of-india) — NSE intraday
  since 2012-01-02, pre-built 1-minute OHLCV. Commercial and properly licensed; would sidestep the
  survivorship problem *if* their history includes delisted names.
- [Breeze API, ICICI Direct](https://www.icicidirect.com/futures-and-options/api/breeze) — 1-second
  and 1-minute, ~3 years for F&O, free.
- [INDstocks API](https://api-docs.indstocks.com/historicalData/) — claims 15 years of OHLCV.
- [ShabbirHasan1/NSE-Data](https://github.com/ShabbirHasan1/NSE-Data) — free minute data for Nifty
  50, Next 100 midcaps and 9 indices, 2017-01-01 → 2020-12-31. Right universe shape, but unknown
  provenance and no corporate-action contract: a **cross-check** against a Kite fetch, never the
  store of record.

## Revised recommendation — probe, don't build

Sequence, per the `skills/verdict-machine` rung order where coverage is audited before anything is
built on a stream:

1. Confirm Kite Connect access and that historical is enabled on the owner's app.
2. **Probe five known-delisted names** — DHFL, JETAIRWAYS, ALBK, LAKSHVILAS, INFRATEL — for intraday
   availability.
3. Only if that passes: scope the universe (F&O per the reset rationale, not all of Nifty 500) and
   build, with the coverage/PIT audit as the first deliverable rather than the last.

The probe is minutes of work and decides whether the project is worth an hour or is dead on arrival.
