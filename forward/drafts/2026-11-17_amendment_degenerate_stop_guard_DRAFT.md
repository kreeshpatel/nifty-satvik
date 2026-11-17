# DRAFT — degenerate-stop guard for the live weekly-swing scan, for the owner to review, edit and sign

**Status: DRAFT. Not in force, and nothing in the live path has been changed.** It takes effect only when the owner
signs §7 and the wiring ships in the same commit as this file's signed copy. Owner request 2026-11-17.

**Mission line.** A signal whose stop sits a few paise below the entry is a data error, not a trade: it reports a
−389.8R loss on ₹8,041 of money, poisons every total-R figure it touches, and would size a live position off a
meaningless risk basis. Blocking it protects the forward record the whole programme is judged on.

**Class: data-integrity fix, not a strategy change** — but it changes what the live scan will and will not take, so
it needs the owner's signature.

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

## 7. Owner sign-off (required before any wiring)

- [ ] Block live signals whose initial stop is inside **0.5%** of entry, as a data error.
- [ ] Flag them **red** in the health report and list ticker, entry, stop, stop distance, signal date and signal-week low.
- [ ] The research path and the published historical anchors are **unchanged** by this amendment.

Signed: ______________________  Date: ____________
