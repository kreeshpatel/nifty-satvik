# Finding 0130 — the funding bias is a SAVING of ~10.8% of equity per year, not a cost

**Date:** 2026-08-06 · **Class: MEASUREMENT** — screen-ledger row 16, appended before the run.
**Counts: screens 15 → 16 · sealed opens 1 · n_trials 138 (unchanged).**
Pre-registration: [`0130-sizing-exclusion-bound.md`](../../diagnostics/research/preregistry/0130-sizing-exclusion-bound.md)
(owner sign-off 2026-08-06; amendments A1–A3 written before the run).
Producer: [`scripts/diag_sizing_exclusion_bound_0130.py`](../../scripts/diag_sizing_exclusion_bound_0130.py) ·
evidence: `sizing_exclusion_bound_0130.json`.

---

## The headline — a price, not a verdict

Per amendment A1 this study exists to **price** the funding bias the trade-population census found.
The magnitude is the finding; the gate is a footnote.

> **Replacing the record's risk-parity sizer with an equal-notional one — the change that would let
> the excluded tight-stop signals into the book — earns 10.83% of equity per year LESS.**
>
> **Delta = −10.83% of equity per year. 95% CI [−26.33, +4.74]. 7 of 10 years the same sign.
> P(the bias is a cost) = 0.083.**

**The sign is the finding.** Negative means the funding bias **saves** the book. The census
established that the cash gate excludes the population's best-R signals; this prices that exclusion
and finds it is worth paying for.

*Escalation line (secondary): the magnitude is below the ±20%-of-equity-per-year escalation floor,
so it does not become an owner item on size alone.*

**And this is a positive result about the engine.** The sizer is not throwing away edge — it is
trading risk-efficiency for throughput at a price that is favourable, and the exclusion the census
documented is the mechanism by which it does so, not a defect in it.

---

## The two units disagree in sign — the sharpest instance the programme has measured

| | Arm A — actual (risk-parity) | Arm B — equal-notional, cap 0.20 | difference |
|---|---:|---:|---:|
| trades | 255 (26.9/yr) | 232 (24.5/yr) | −23 |
| **sum R** | **+127.5** | **+167.6** | **Arm B +40.1** |
| **R per year** | **+13.44** | **+17.66** | **Arm B +4.22 R/yr** |
| **% of equity per year** | **+26.55%** | **+15.72%** | **Arm B −10.83pp** |
| win rate | 59.2% | 53.9% | −5.3pp |
| median stop width | 13.10% | 9.49% | −3.61pp |
| median extension | 17.51% | 13.45% | −4.06pp |

**Arm B earns +4.22 R/yr MORE and 10.83% of equity/yr LESS.** Same population, same priority rule,
same span — and the two units reach opposite conclusions about which book is better.

**Mechanism, stated as the root cause.** R is `price outcome ÷ that trade's own stop width`, so a
tight stop is a small denominator and prints a large R for the same rupee move. Equal-notional
sizing puts the *same money* behind every R regardless of that denominator; risk-parity puts **more
money behind the trades whose R is worth more money**, which is precisely what risk-parity is for.
The census's "the book excludes its best-R signals" is true and is not a defect: those signals are
best **in R**, and R over-weights tight stops by construction.

This is `DEFINITIONS_REGISTER` row 1 and binder §6/§8 demonstrated at **book level** for the first
time. Every previous statement of the R-comparability problem was per-cohort; this is a case where
the choice of unit reverses the answer to the question being asked.

---

## The tail leg — equal-notional is also worse where it matters most

| | Arm A | Arm B | clairvoyant |
|---|---:|---:|---:|
| disaster-class trades (R ≤ −1.5) | **14** | **34** | 19 |
| share of trades | 5.49% | **14.66%** | 8.56% |
| total equity lost to disasters | **−58.02%** | **−97.13%** | −44.49% |
| worst single position | −11.12% | −8.51% | −8.51% |

Arm B carries **2.4× the disaster-class trades** and loses **1.7×** as much equity to them. The
mechanism is the one the pre-registration named in advance: a tight stop is more easily gapped
through by a *large multiple of itself*, so the cohort equal-notional sizing makes affordable is
also the cohort most exposed to gap-through. Risk-parity's smaller positions in wide-stop names cap
the single-position damage differently — Arm A's worst single position is larger (−11.12%) while its
aggregate disaster loss is much smaller.

**Both the mean and the tail point the same way.** That is worth stating because the two legs could
easily have disagreed, and a bound whose mean and tail conflict is not decisive.

---

## The seat check — amendment A2 satisfied, and it strengthens the result

`FINDING_more_slots` (trial-priced, `n_trials` 120→122) established a monotonic dilution as seats
increase: 4–5 names → 1.21, 7 → 0.97, 10 → 0.81, against a random null of 0.74. The pre-registration
bound this study to demonstrating its result **inside** that non-diluting band, or not claiming it.

| | max concurrent | mean concurrent |
|---|---:|---:|
| Arm A (actual) | 10 | 5.64 |
| **Arm B** | **5** | **4.56** |

**Arm B sits inside more_slots' best-performing band (4–5 names) and still loses by 10.8%/yr.** The
result is therefore *not* a rediscovery of dilution — Arm B is not a widened book. It isolates the
**sizing basis** from the seat count, which is exactly the narrowing the pre-registration claimed
and the only thing that made this study legitimate after more_slots.

Noted without analysis: Arm A's own mean concurrency of 5.64 sits slightly *outside* that band,
toward the 7-name figure more_slots measured at 0.97.

---

## The clairvoyant ceiling — the structure is not worthless, its selection rule is

| | equity %/yr | vs Arm A |
|---|---:|---:|
| Arm A actual | +26.55% | — |
| Arm B, CRS priority | +15.72% | **−10.83** |
| Arm B, perfect foresight | +53.86% | **+27.32** |

With perfect foresight over which of the affordable candidates to take, equal-notional beats the
record by **+27.32% of equity per year — above the escalation floor.** So the equal-notional
*structure* does have real headroom; what fails is choosing inside it. CRS priority, which is the
best selection rule the programme has, gives all of that headroom back and 10.8 points more.

This is the same shape as 0117's rotation ceiling: a bound that is large under clairvoyance and
negative under the best real rule tells you the territory is not empty, and that nothing we can
build reaches it.

---

## Per-year

| year | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ equity %/yr | +0.8 | −26.0 | −6.5 | **+6.0** | −28.0 | −20.9 | −17.4 | **+3.3** | −5.7 | −8.2 |

**7 of 10 years negative** (the bias saves). The three positive years are 2017 (31 signals, a stub),
2020 and 2024. No year is close to the +20% escalation floor on the cost side.

---

## What this does NOT establish

- **It is not a backtest.** Affordability is computed at full deployment (5 seats), not by
  simulating the cash carry path. No equity curve, no Sharpe, no CAGR, no MaxDD was produced for any
  arm — per the pre-registration's binding constraint, producing one would have made this
  trial-class and stopped the session.
- **Arm A is priced on a fixed reference equity**, not on the record's mark-to-market compounding
  sizing, so its +26.55%/yr is a fixed-base restatement rather than the published CAGR of 24.69%.
  That convention is what makes the two arms commensurable; it is not a restatement of the record.
- **The CI includes zero** ([−26.33, +4.74]). The direction is consistent (7/10 years, p=0.083) but
  the magnitude is not tightly determined, and this study does not claim it is.
- **It says nothing about a different book shape.** Equal weight in a *wider* book (breadth-50) is a
  different structure with a different seat count, and this result neither supports nor damages it.

## Root-cause readout

The funding bias is **not a leak, it is the sizer working**. Risk-parity allocates money in
proportion to how much money each unit of R is worth, and the signals the cash gate excludes are
precisely those whose R is cheap. Measuring the exclusion in R makes it look like a large loss
(+4.22 R/yr forgone); measuring it in money shows a 10.83%/yr gain. The census was right that the
funded set is not representative; this finding shows that non-representativeness is the mechanism by
which the sizer earns its keep.

## Next setup

None proposed. The territory is closed for the price of one screen row.

## Do not re-test unless

A **different book shape** whose seat count sits inside the non-diluting band while decoupling size
from stop width (breadth-50 equal-weight is the named candidate, and it must be judged on forward
evidence, not here); or **forward evidence**; or a **corrected-universe re-anchor** that changes the
population's stop-width distribution. Re-running this comparison with a different `cap`, a bigger
sample, or a different unit is refused relitigation.

## Consequence for the Structural Defect Map

`SEL-1`, `SEL-2` and `SEL-3` move from **OPEN** to **TRADEOFF** — the funding bias is now a priced
structural property with a measured sign. `SEL-4` (scale-invariance) and `SEL-7` (record vs live
carry different selection biases) are untouched and remain open.
