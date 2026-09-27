# 0147 — Beyond-stop slippage is 37% of the loss on a book that holds no money

**Status:** MEASUREMENT — **no trial, no screen row, no sealed open, nothing adopted. This finding
proposes no rule, and in particular no stop-placement rule.**
**Standing counts:** screens **20** · sealed opens **3** · n_trials **2** — unchanged by this study.
**Date:** 2026-09-26 · **Plan:** the 2026-09-25 development plan, Phase 0 item **A2**.
**Record:** `diagnostics/research/trade_forensics/2026-09-04/summary.json` (the original run) and
`diagnostics/research/trade_forensics/2026-09-26/summary.json` (the same snapshot with three legs
added).
**Reproduce:**
`python scripts/diag_trade_forensics.py --as-of 2026-09-04 --end 2026-09-08 --offline --out-date 2026-09-26`

**No pre-registration, and none is written retrospectively.** The measurement was run on 2026-09-04 by
`scripts/diag_trade_forensics.py`, committed, and then never written up or referenced anywhere. Writing
a SPEC for a run that has already reported would be theatre; the honest record is that this finding
publishes an existing, reproducible computation, and that the three legs added here were chosen **after**
seeing the original numbers. What protects the reading is that none of the three can flatter the result:
each one makes the headline smaller.

## The original measurement, reproduced

Recomputed read-only from the archived snapshot with the same functions, writing nothing: the stop
decomposition, **every per-trade row**, and the recorded-vs-implied stop agreement all reproduce
**exactly**.

| | |
|---|---|
| closed trades in the 2026-09-04 snapshot | **9** |
| realised | **−14.37R** |
| designed (−1R per trade) | **−9.00R** |
| **beyond the designed stop** | **−5.37R — 37.4% of realised** |
| filled past the stop | **6 of 9** |
| recorded-vs-implied stop, max gap | 0.28% |

And a market control, from the original run (prices pulled 2026-09-15): over their own holding windows
the **stopped** names sat at the **11th percentile** of the universe (median excess −4.05%, 8 of 9
underperforming) while the **open** ones sat at the **68th** (median excess +3.82%).

## The correction that matters: this is the uncapped tracker, not the book

Finding **0146** established that `signals_history_weekly.json` describes the **uncapped** signal
tracker — cash never runs out there — while the ₹10L capital book has funded 7 names and closed **one**.
The forensics above is computed over that closed-trade history, so it is a decomposition of the
tracker's loss. Splitting the same 9 trades by whether the capital book ever actually held the name:

| cohort | n | realised | **beyond the designed stop** |
|---|---|---|---|
| **funded — the book that holds money** | **1** (DELHIVERY) | **−1.05R** | **−0.05R** |
| never funded — the tracker only | 8 | −13.32R | **−5.32R** |
| undetermined | 0 | — | — |

**99% of the beyond-stop slippage is on trades no rupee was ever exposed to.** On the funded book,
beyond-stop slippage is **−0.05R, on one trade** — about five paise in the rupee of one position's risk.

The same caveat applies to the market control: the 11th-vs-68th percentile split compares stopped
*tracker* names against open *capital-book* positions, so part of that gap is the funding margin itself
rather than a statement about how stopped names behave. It is not evidence that selection is picking
losers.

**Consequence for the development plan.** Phase 0's framing — *"half the R-pain is denominator, a third
is gap-through fills"* — was built on this figure plus 0143's. The denominator half stands (0143 measured
stop widths on the live cards). The gap-through third **does not describe the funded book**, and the plan's
Phase-2 note that a stop-geometry rule "needs its own pre-registration" should now read: on current
evidence there is no funded-book quantity for such a rule to improve.

## Two committed artifacts decompose the same trades differently

Neither says it is making a convention choice:

| convention | designed | beyond-stop | source |
|---|---|---|---|
| nets favourable fills | −9.00R | **−5.37R** | `nq/brain/attribution.py::ClosedTrade.beyond_stop_r` (`r + 1` unconditionally) |
| adverse overshoot only | −8.45R | **−5.92R** | `nq/brain/ledger.py::decompose_r` (a shallower loss is a shallower *designed* loss) |

The **0.55R** difference is the favourable overshoots — three trades that lost *less* than their stop
distance (GLENMARK +0.07, NATCOPHARM +0.05, 3MINDIA +0.43). One convention credits them against genuine
overshoot; the other does not treat them as overshoot at all. Both are defensible. The problem is that a
reader of either number cannot tell which was used, and the two differ by a tenth of the quantity.

Per-trade cross-check against `results/attribution_ledger.csv`: **6 of 9 agree exactly, 3 differ only by
that convention, 0 unexplained.**

## Two join bugs this study made, recorded because both returned confident wrong numbers

- Keying the cross-check on **ticker alone** reported GESHIP as missing from the ledger. It is not: GESHIP
  has **two** rows — the closed trade and a later still-open re-entry — and the ticker-keyed lookup found
  the blank open one.
- Keying on **(ticker, signal_date)** then failed for three trades, because signal dates are **restated
  between snapshots**: 3MINDIA and GESHIP read 2026-07-27 in the as-of-dated forensics and 2026-07-24 in
  the current ledger; CCL reads 2026-08-17 against 2026-08-14. That looks like absent data and is not.

The stable join is *closed rows, by ticker*, with the date disagreement reported rather than silently
failing the match. `tests/test_trade_forensics_legs.py` pins both.

## The 11-vs-9 trade difference, accounted for by date

The current history carries 11 closed trades; this snapshot carries 9. The two absent from it are
**BIOCON** (closed 2026-09-07) and **HINDZINC** (closed 2026-09-14) — both after the snapshot's
2026-09-04 as-of. Nothing was dropped.

## What this does NOT license

**No rule, and specifically no stop-placement rule.** The stop axis is closed in both directions and the
receipts are on the live book's own family: **0105** tighten ΔSharpe −0.477, **0106** widen −0.347,
**0109** disaster floor −0.071 and −1.3pp DD, and `FINDING_hard_stop` — capping each loss made portfolio
risk *worse* (DD −34.8% → −55.4%), with 48% of stop-outs recovering above entry within 12 weeks.

This is a statement about the **composition** of a loss, not a pre-entry discriminator and not a
management proposal. Turning the 11th-vs-68th percentile split into "we are picking bad names" walks
straight into **Law II** (a population effect does not survive to this book's decision points; the
mechanism in 0131 is stop width → notional → seat count → dilution, and the dilution axis is **seats**)
and **Law III** (worse-than-average is still positive-EV; 0121 removed a genuinely worse cohort and it
cost **−20.96 R/yr**).

Any stop-geometry proposal would need a clairvoyant activation bound first, then a pre-registration, then
a trial — and it would be starting from a funded-book quantity of −0.05R.

## Declared limitations

- The **market-control leg was not re-verified**: it needs a price pull (the original used prices fetched
  2026-09-15) and this reproduction ran offline. The stop decomposition and every per-trade row were
  reproduced exactly.
- The funded/never-funded split rests on the weekly snapshot sequence, the same instrument as 0146, and
  inherits its half-open-window rule. No trade here was undetermined.

  **The gap that rule leaves, and why it is closed.** Absence from every snapshot inside a trade's window
  proves the name was not held *on those dates* — not, strictly, that it was never held, since a position
  bought and sold entirely between two weekly snapshots would be invisible. Five of the eight
  never-funded names (GLENMARK, CANFINHOME, NATCOPHARM, LINDEINDIA, 3MINDIA) have only **one** in-window
  snapshot, so the logical hole is real for them. It is closed by arithmetic rather than by assumption:
  any such brief holding would itself have been a **capped closure**, and 0146 established that the
  capital book's closures number **exactly one** — DELHIVERY — corroborated by
  `base_swing_forward.n_closed = 1`. A second funded closure cannot be hiding in the gaps, because the
  count that would have to contain it is 1 and it is already spoken for.

  The pre-archive window (inception 2026-07-04 to the first snapshot 2026-07-24) is closed the same way:
  the uncapped book reports **0** closures at 2026-07-24, and capped closures are a subset of uncapped
  ones, so nothing opened and closed before the archive began.
- n = 9 on the tracker and **n = 1** on the funded book. Nothing inferential rests on either, and the
  ≥30-closed precondition means expectancy is not an informative quantity at this sample.

## Do not re-test unless

The funded book accumulates closed trades — the quantity worth decomposing is the funded cohort, and it
currently has one member. Re-running this diagnostic is cheap and is the right check after each quarter's
closures, or after any change to `nq/brain/attribution.py` or `nq/brain/ledger.py`'s decomposition.
