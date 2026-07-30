# B-1 impact census — absent-bar holdings (read-only)

**Date:** 2026-07-29 · **Script:** [scripts/diag_b1_absent_bar_census.py](../../scripts/diag_b1_absent_bar_census.py)
· **Machine-readable:** [b1_absent_bar_census.json](b1_absent_bar_census.json)
· Read-only: engine not run, forward-wall books/logs not read, counts unchanged
(screens 11, sealed opens 1, n_trials 138).

## The bug being measured

`run_bhanushali_weekly_rank.backtest` skips **all** exit logic for a held name with no bar on the
current date ([R94:412-414](../../scripts/run_bhanushali_weekly_rank.py), `i is None → continue`),
and the NAV sum marks such a name at its **entry price**
([R94:864](../../scripts/run_bhanushali_weekly_rank.py), `… if d in didx[t] else p["en"]`). A
suspension or delisting mid-hold therefore freezes the position forever *and* carries it at cost —
NAV flattery that feeds the Oct-1 scorecard's Sharpe/MaxDD gates. The momentum engine guards this
with `STALE_ABSENT_DAYS = 10` ([nq/engine/portfolio.py:43](../../nq/engine/portfolio.py)); the swing
engine has no equivalent.

## Verdict: **NO INSTANCE TO DATE. Zero rupees of NAV flattery.**

| Measure | Value |
|---|---|
| Book as-of (committed envelope) | 2026-07-24 |
| Open positions in the ₹10L paper book | 4 — DELHIVERY, INDUSINDBK, NESTLEIND, CUB |
| Open positions affected (bar-less mid-hold) | **0** |
| NAV flattery to date | **₹0.00** (0.0000% of NAV ₹991,807.38) |
| Names in signal history missing from the cache / stale ≥10 sessions | **0** |
| Universe names stale ≥10 sessions | **0** of 710 cached |

Every name the book has ever held or signalled is present in the OHLCV snapshot with bars running
to the snapshot's own frontier. No holding has ever gone bar-less mid-hold, so the freeze path and
the entry-price mark have never been exercised on live capital.

**Caveat on provenance.** The census ran against the local `data/ohlcv.pkl`, verified as the pinned
research blob `f8625a8f…` (frontier 2026-06-29); the live book is computed CI-side against the
Actions-cached copy, which runs ~4 weeks fresher. The check is therefore authoritative for
"has any held//signalled name ever vanished from the series" (a property of the name, not of the
snapshot date) and for the ₹0 flattery conclusion on the four current holdings, all of which are
present and current in the snapshot. A name that suspended *after* 2026-06-29 would not appear
here; nothing in the committed book state suggests one.

*Incidental finding:* the pin is intact — constitution row K6 (a local cron run with downloads
would clobber `data/ohlcv.pkl`, the same path as the pinned blob) has **not** occurred on this
machine. The hazard remains real; the pin is currently clean.

## Reading

B-1 is **latent, not realized**. That is the argument for fixing it now rather than after an
instance: the fix can be landed with a provably zero behavioural diff on the existing record
(nothing to restate, no gate re-evaluation), which would not be true once a suspension has entered
the book. The forward book holds mid/small-caps (CUB, DELHIVERY) where suspension-class events are
not exotic, and positions have **no time cap** (constitution G6), so the exposure window per
position is unbounded.
