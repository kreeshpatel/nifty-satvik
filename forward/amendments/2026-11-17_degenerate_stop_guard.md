# Amendment 2026-11-17 — degenerate-stop guard for the live weekly-swing scan

**Status: SIGNED by the owner on 2026-11-17 and IN FORCE from the scan of 2026-11-21.** The owner signed §7 as
drafted, at the 0.5% threshold, in session on 2026-11-17, with wiring conditional on the two checks in §8 — both of
which passed. The draft this was signed from is `forward/drafts/2026-11-17_amendment_degenerate_stop_guard_DRAFT.md`.

**Change-control class: DATA-INTEGRITY EXEMPTION** (`skills/strategy-lifecycle` §6, exemption class added
2026-11-17). It alters no decision on any historical or live signal except signals classified as data errors by a
rule stated in advance. **Signals affected: 1 historical (VMART 2019-05-06), 0 live.**

---

## 1. The rule

At card-build time, for every candidate signal, compute `stop_distance = (entry − stop) / entry`.

If `stop_distance < 0.005` (the stop is within **0.5% of entry**), the signal is:

1. **Not taken.** It is excluded from the fill candidates — no card, no buy window, no position.
2. **Flagged red in the health report**, as a data-integrity failure, not a market event. Red, not amber: a
   sub-0.5% stop on a weekly-swing signal means the signal week's low is effectively the entry, which only happens
   when the price history is wrong (a bad tick, a mis-adjusted corporate action, a stale or duplicated bar).
3. **Listed explicitly**, with **ticker, entry and stop** — and, because they cost nothing to add and make the
   triage a one-minute job: the stop distance in percent, the signal date, and the signal week's low.

It fires on `stop_distance` **below** 0.5%; exactly 0.5% passes. A non-positive or missing stop (`stop >= entry`, or
`stop` absent) is the same failure and is caught by the same rule.

## 2. Why 0.5%, and why the threshold is not load-bearing

| | value |
|---|---|
| the one historical trade it catches | stop distance **0.0074%** |
| the next-smallest stop distance in 5.5 years | **1.161%** |
| smallest live stop distance in 107 cards | **1.518%** |

**Nothing in the programme's history sits between 0.0074% and 1.161%.** Any threshold from about 0.01% to about 1.1%
catches exactly the same single signal, so the number is not a fitted parameter. 0.5% is chosen because it is the
value already used as a research filter (`pipelines/diagnostics/diag_loss_diagnosis_2026_11.py:204`), which keeps the
live rule and the research convention identical rather than introducing a second number.

## 3. How many signals it would have caught

**Historical, 2019-01-01..2024-06-28, uncapped book (every Grade-A signal taken): 1 of 526 — 0.19%.**

| ticker | signal / entry date | entry | stop | stop distance | R as booked | money |
|---|---|---|---|---|---|---|
| VMART | 2019-05-06 | ₹676.74 | ₹676.69 | **0.0074%** (₹0.05) | **−389.751R** | −₹8,040.72 |

**Live, 2026-07-06..2026-11-13, 107 archived cards: 0.** Smallest stop distance 1.518%, 5th percentile 2.683%,
median 6.551%. Also zero in the 0.5%–1.0% band, historically and live.

**So the rule is a no-op on every signal the live book has ever produced, and would have removed exactly one trade
in 5.5 years of history.** That is the point: it is a guard against a failure mode that has happened once and would
be invisible until it corrupted a number, not a filter that reshapes the book.

## 4. What it changes, measured both ways (per the owner's reporting rule)

Dataset A, uncapped, 2019-01-01..2024-06-28:

| | trades / closed / marked | closed-only | marked-at-cut | share of total R from trades open at the cutoff |
|---|---|---|---|---|
| without the guard | 526 / 442 / 84 | **−115.822R** | **+260.440R** | 144.5% |
| **with the guard** | 525 / 441 / 84 | **+273.929R** | **+650.191R** | 57.9% |

Money changes by **₹8,041** (0.08% of P&L). R changes by **389.751**. Every Sharpe, CAGR and drawdown figure is
**unchanged** to the precision reported, because those price the book rather than the per-trade R basis — the 2%
risk sizing on a ₹0.05 basis was already bounded by the 20% notional cap, which is why the money moved so little.
Source: [`diagnostics/research/2026-11-17_total_r_convention_reconciliation.md`](../../diagnostics/research/2026-11-17_total_r_convention_reconciliation.md).

## 5. Where it would be wired (not wired yet)

| piece | file |
|---|---|
| the guard, at card build, before fill selection | `scripts/run_bhanushali_cron.py` (card assembly), one predicate plus an exclusion list |
| the red flag and the listing | the health-report section of the same scan output, beside the existing data-integrity checks |
| regression test | a new `tests/test_degenerate_stop_guard.py`: a fixture signal at 0.4% is excluded and listed; one at 0.6% is untouched; the live golden masters stay byte-identical because no historical live signal is affected |

**The research path is deliberately not changed.** `diag_loss_diagnosis_2026_11.py:204` keeps its filter, and the
anchors page keeps publishing both populations, so the historical record stays reproducible exactly as published.

## 6. What would make this wrong

- **It hides a real signal.** If a genuine weekly-swing setup can have a sub-0.5% stop, the guard drops a real trade.
  The evidence says it cannot: no live card and no historical trade except the one data error comes within 1.1%.
- **It masks the underlying data defect instead of fixing it.** True, and intentional — the red flag exists so the
  bad bar gets fixed. If the flag is ignored, the guard quietly absorbs broken data. Mitigation: red, listed, and in
  the health report rather than a log line.
- **The threshold drifts into a tuning knob.** Mitigation: §2 — the 0.0074%-to-1.161% gap means any value in a
  hundred-fold range behaves identically. If a future session wants to move it, that is a new amendment.

## 7. Owner sign-off — SIGNED 2026-11-17

- [x] Block live signals whose initial stop is inside **0.5%** of entry, as a data error.
- [x] Flag them **red** in the health report and list ticker, entry, stop, stop distance, signal date and signal-week low.
- [x] The research path and the published historical anchors are **unchanged** by this amendment.

**Signed: the owner, in session. Date: 2026-11-17.**

## 8. The owner's wiring conditions, and how each was met

The owner's instruction: wire it before Saturday's scan **only if** (a) the full suite passes and (b) a dry run of
the latest scan with and without the guard produces identical published files. If either fails, do not wire.

**(a) Full suite: PASS.** 1,753 tests green, including the new `tests/test_degenerate_stop_guard.py` (14 cases: the
threshold value, that the guard sits above the card-building append, the predicate at 0.4% / 0.5% / 0.6% / the
historical ₹0.05 case / zero distance / stop above entry / an ordinary 10% stop, the health check green with no
file, red with one, amber on an unreadable one, its registration in the runner, and that a clean scan publishes
nothing new).

**(b) Dry run: IDENTICAL, on both legs.**

| leg | what was compared | result |
|---|---|---|
| code path (`pipelines/diagnostics/dryrun_degenerate_stop_guard.py`) | the scan's own path run twice over the same data, guard on and guard off, diffing all five published payloads byte for byte — `signals_today_weekly`, `signals_history_weekly`, `signal_analytics_weekly`, `paper_portfolio_weekly`, `portfolio_history_weekly` | **identical; 0 payloads differ, 0 signals refused** (local cache as-of 2026-06-29) |
| latest published scan (`check_published`) | the guard predicate replayed over the cards the 2026-11-13 scan actually published | **0 of 21 cards would be refused**; smallest stop distance **3.033%** (RBLBANK) |

The second leg exists because the developer cache lags the cron: the code-path leg proves the two code paths agree,
and the published leg proves it on the latest scan's real output. Across the 107 archived live cards the smallest
stop distance is 1.518%, three hundred times the threshold.

**Known, unrelated, and not fixed here:** `scripts/run_bhanushali_cron.py --no-download` crashes with
`KeyError: 'quarantined'` at the pending-restatement step, because the offline path leaves the quarantine record
empty. It predates this amendment and does not affect the cron (which downloads), but it is why the dry run uses
the two legs above rather than two full offline scans.

## 9. What shipped

| piece | where |
|---|---|
| the floor and its reasoning | `scripts/run_bhanushali_cron.py`, `MIN_STOP_DISTANCE = 0.005` |
| the guard, above the card append | `scripts/run_bhanushali_cron.py`, in `build_envelopes` |
| the guard record, written every scan | `results/degenerate_stops.json` — `ran`, `n_candidates`, `n_refused`, `refused[]`; the `degenerate_stops` envelope key is still added only when non-empty, so every published card payload is unchanged by a clean scan |
| the red flag, and the "ran, N refused" line | `scripts/scan_health.py`, check `degenerate-stop`: a line in every health report even at N = 0, and AMBER when the record is absent (no evidence the guard ran) |
| the regression test | `tests/test_degenerate_stop_guard.py` |
| the dry run | `pipelines/diagnostics/dryrun_degenerate_stop_guard.py` |

## 10. Amendment to §9, 2026-11-17 (owner request, same day)

The owner asked that Saturday's health report carry the line **"degenerate-stop guard: ran, N refused"** even when
N = 0, so that the guard can be seen to have run rather than inferred to have been quiet. Two consequences:

1. `results/degenerate_stops.json` is now written on **every** scan, with `ran`, `n_candidates`, `n_refused` and the
   (possibly empty) `refused` list. It is a health record, not one of the five published card payloads, so the
   wiring condition in §8 — that the published files are byte-identical — still holds and was re-verified.
2. An **absent** record is now an AMBER finding (`degenerate-stop:not-run`) rather than green: silence from a check
   that writes unconditionally means no evidence it ran, which is the opposite of a clean scan.
