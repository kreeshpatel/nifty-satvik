# 0144 — Daily-resolution descent: activation bound

**Class:** ACTIVATION BOUND (verdict-machine Gate 3). **No trial.** Screen ledger row **#20**, appended
**before** this runs. Standing counts at registration: **screens 19 → 20 · sealed opens 2 · n_trials 2**.
**Registered:** 2026-09-25, before the diagnostic exists.
**Plan:** Satvik Brain Phase 1, study B2.

## The owner's hypothesis

> "When the stock is extensively down on the daily charts, the trade goes to SL."

## What is already answered, and what is therefore NOT being re-asked

**0127 measured this on WEEKLY bars and closed both responses.** Its frozen cohort — a decline of
≥4 weeks carrying the name ≥20% off its trailing 13-week peak into the touch — is **descriptively real**:
meanR **+0.062 against +0.494**, win **40.6% against 48.1%**, 16.2% of touches. And:

- **(a) Excluding it costs 1.92 R/yr.** The cohort earns +14.3R — 2.4% of book R from 16.2% of trades:
  "a *nothing* engine, not a loss engine."
- **(b) Managing it differently gains 0.0 R/yr, in all 8 years**, with perfect hindsight over the frozen
  set {as-is, TP@2R, TP@3R, stop@−0.5R}: the optimum treatment does not move.

0127's closing clause is in force: *"not a different descent window, not a different depth threshold,
not velocity instead of depth, not a per-name variant."* Related closures cited and not re-opened:
**0126** (line-hugger, all three legs KILL), **0104** (ext_cap tighten, KILL), **0105 / 0106 / 0109**
(the stop axis, closed in both directions), and **program-laws I** (entry quality is not visible
pre-entry on this funnel, in five instruments).

## What this brings that is new

Exactly one thing: **resolution**. Every measurement above is computed on completed **weekly** bars
against the 44-week line. The owner said *daily*. A daily-resolution descent is a different instrument,
and the question it can answer that 0127 cannot is:

> **Does the daily view SPLIT 0127's weekly cohort** — that is, within the weekly HEG-class trades, does
> a daily measure separate the ones worth treating differently from the ones that are not?

Exclusion and conditional management are re-run **only so the numbers are directly comparable** to
0127's, on the same frozen management set. They are not a new sweep and no new management is added.

**Prior expectation, stated before the run:** `dist_52wh_pct` already carries the daily-ish version of
this gradient (STAGE2_ml quintile win% 39 → 46 → 50 → 54 → 55) and 0127 corroborated its direction, so
the expected result is a bound **below the ±10 R/yr floor**. Recording that expectation now so a null is
read as a null and not as a disappointment.

## Frozen definitions (§1 — no sweep anywhere)

All computed on **daily** bars from `corrected_universe()`, strictly **before** the entry date (the fill
is at that session's open, so the decision bar is the previous session):

- `peak63` = maximum daily **High** over the 63 sessions ending the session before entry.
- **`dd63`** = `100 × (peak63 − close_prev) / peak63`, where `close_prev` is the last close before entry.
- `sessions_since_peak63` = sessions from the peak bar to the decision bar.
- `days_below_50dma` = sessions in that trailing 63 whose close is below their own 50-session SMA.
- `daily_velocity` = `dd63 / sessions_since_peak63`.

**PRIMARY cohort: `dd63 ≥ 20%`.** Robustness reported, never used to choose: `dd63 ≥ 15%`, `dd63 ≥ 25%`,
and `dd63 ≥ 20% AND days_below_50dma ≥ 32` (half the window).

## Population (§2)

`research/substrate/trades.parquet`, `setup == "touch44"`, **`entry_date` in [2019-01-01, 2024-06-30]** —
**train only**. The sealed 2024H2+ slice is not read; `nq.brain.io.assert_unsealed` guards the selection.

**Noted, not acted on:** `pipelines/diagnostics/diag_hegclass_bound_0127.py` filters only
`entry_date >= 2019` with no upper bound, so 0127's published population appears to span 2019-01..2026-06
including the sealed window, while its finding states the sealed slice was not read (it names
`context_windows.parquet`). This study does **not** edit 0127. It recomputes 0127's weekly cohort on
**this** train-only window so the two are comparable, and the discrepancy is raised for the owner.

The population is **uncapped** (the Stage-1 substrate, not the funded book), which inflates both bounds
— the friendliest ground for a bound whose purpose is to fail.

## Bounds and the gate (§3)

1. **(a) Exclusion** — R/yr the cohort earns (refusing it costs that), plus the clairvoyant
   refuse-only-losers ceiling, reported and **set aside as unreachable** (0127's template).
2. **(b) Conditional management** — the clairvoyant gain of conditioning on cohort membership over the
   best single management for everyone, on 0127's frozen set {as-is, TP@2R, TP@3R, stop@−0.5R}. The
   same excursion-order approximation, which inflates every ceiling.
3. **(c) THE NEW LEG — does daily split weekly?** The 2×2 of weekly-HEG-class × daily-cohort, and the
   clairvoyant conditional-management gain of the daily split **computed within the weekly cohort only**.

**Gate, fixed now:** a bound **below ±10 R/yr** (the 0109/0117 path-noise floor), or **wrong-signed**, is
recorded as a bound and **earns no trial**. Per-year sign consistency is reported for every bound.

## What this may never become

Nothing here authorises an entry filter, a sizing rule, a different stop, or a different exit. Those are
live rule changes and need a pre-registration, a trial, and the quarterly review. Law III is explicit
that a cohort being worse is not a reason to refuse it (0121: removing event trades cost −20.96 R/yr).

## Do not re-test unless

Forward **habit-ledger** rows carrying the descent fields exist, **and** the question asked of them is
neither exclusion nor conditional management over the frozen set. A different daily window, a different
depth threshold, or velocity instead of depth is **relitigation** and is refused.
