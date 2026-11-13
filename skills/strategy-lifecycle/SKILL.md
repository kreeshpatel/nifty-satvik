---
name: strategy-lifecycle
description: >
  The operating model for every strategy once it leaves research: stages (RESEARCH → PAPER → PILOT → SCALE → FULL),
  weekly GREEN / AMBER / RED status against frozen expectation bands, the 26-week minimum before any forward verdict,
  promotion and retirement rules, change control at quarterly reviews, the benchmark rule and the research freeze.
  Read it BEFORE answering any question about how a strategy is doing live, and before proposing to promote, demote,
  fund, change or kill one.

  Trigger phrases: "is it working", "should we kill", "live results", "forward record", "promote", "allocate capital",
  "go live", "change a rule", "quarterly review", "paper trading", "pilot", "status", "RED", "AMBER", "bands",
  "trailing the benchmark", "retire the strategy", "new research idea".
---

# strategy-lifecycle — how a strategy earns, keeps and loses capital

ADR: [`docs/decisions/0020-strategy-lifecycle-operating-model.md`](../../docs/decisions/0020-strategy-lifecycle-operating-model.md).
Everything this model writes is **append-only and frozen once written** (ADR-0018): bands, forward records, stage
changes and amendments.

**Where the state lives**

| what | file | written by |
|---|---|---|
| each strategy's stage and stage start date | `forward/lifecycle/stages.json` (append-only log of stage changes) | a dated owner decision |
| frozen expectation bands | `forward/bands/<strategy>_bands_<date>.json` (write-once) | `pipelines/lifecycle/build_bands.py` |
| weekly forward record | `forward/records/<strategy>.csv` (append-only) | `pipelines/lifecycle/update_records.py`, in the Saturday scan |
| this week's status | `results/lifecycle_status.json` and the scan's run page | `pipelines/lifecycle/weekly_status.py` |
| ideas parked by the research freeze | `research/BACKLOG.md` | anyone; nothing in it runs without the owner |

**Answer "is it working?" from `results/lifecycle_status.json`, never from a feeling about recent trades.**

## 1. Stages

| stage | capital | entry | exit |
|---|---|---|---|
| **RESEARCH** | none | an idea | a pre-registered validation that passes (`/pre-register`, `/verdict`), frozen bands built, a forward record started → PAPER. A KILL verdict ends it |
| **PAPER** | none (paper record only) | validation passed; bands frozen; record running | promotion to PILOT (§2), or retirement (§4) |
| **PILOT** | 10% of the intended capital | §2 | promotion to SCALE, demotion to PAPER, or retirement |
| **SCALE** | 25% | §2 | promotion to FULL, demotion to PILOT, or retirement |
| **FULL** | 100% | §2 | demotion to SCALE, or retirement |

Moves are one stage at a time, in either direction, and each is a dated line in `forward/lifecycle/stages.json`.

## 2. Promotion

- **PAPER → PILOT:** at least **26 weeks** of paper record, status **AMBER or better at week 26**, and **no RED in the
  last 8 weeks**.
- **PILOT → SCALE** and **SCALE → FULL:** at least **13 weeks** at the current stage, AMBER or better, and **execution
  tracking error under 1% a quarter** (real fills against the model's prices, from the app's execution ledger).
- Promotion is the owner's decision at a quarterly review. Meeting the criteria makes a strategy eligible; it does not
  promote it.

## 3. Weekly status against the frozen bands

Checked every week by `weekly_status.py`, at the band horizon nearest to the weeks on record (13 / 26 / 52 / 104).

| status | condition |
|---|---|
| **GREEN** | cumulative return at or above the band's **25th percentile** for that horizon, **and** drawdown no deeper than the band's 95th-percentile drawdown |
| **AMBER** | cumulative return at or above the 5th percentile and below the 25th; or a return that would be GREEN with a drawdown deeper than the band's 95th percentile |
| **RED** | cumulative return **below the 5th percentile**, **or** drawdown deeper than **1.25 × the backtest's worst drawdown** (the drawdown breaker) |

A return exactly on the 25th percentile is GREEN. A return exactly on the 5th percentile is AMBER.

## 4. RED means a review, not a kill

The review asks three questions, in this order, and writes the answers down:

1. **Is it a data or execution fault?** A split, a holiday bar, a failed scan, fills far from the model's prices.
2. **Is it a market regime the backtest contained, and how did the strategy do there?** Compare like with like.
3. **Has something structural changed?** Costs, liquidity, index rules, the data vendor, the strategy's own code.

Outcomes:
- A strategy **may be demoted one stage** at a review.
- A strategy **may be retired only if** it is RED at **two consecutive monthly checks after the 26-week minimum**, or it
  is RED **on the drawdown breaker**.
- Retirement is a pre-registered verdict under the current harness like any other KILL (CLAUDE.md, owner amendment
  2026-08-08).

## 5. Minimum horizon: no forward verdict before 26 weeks

No verdict of any kind (promote, demote, retire, "it is broken", "it is working") comes from fewer than 26 weeks of
forward data. The only exception is the drawdown breaker.

**Why:** the standard error of an annualised Sharpe estimate is about `1 / sqrt(years)`. Over 3 months that is
`1 / sqrt(0.25) = 2`. A strategy whose true Sharpe is 1 will show a 3-month Sharpe between about −1 and +3 two times in
three, and outside that range the rest of the time. Thirteen weeks of results cannot tell a good strategy from a bad one; 26 weeks only begins to.

Before week 26 the report still shows the status, labelled **provisional**.

## 6. Change control

- Rule changes happen **only at quarterly reviews** (first trading day of January, April, July, October).
- **At most one change per strategy per review**, each with a **dated amendment**.
- The forward record **continues**, with the change date marked. Bands are **recomputed only for the changed version**
  and saved as a new frozen file. The old bands stay.
- A change that needs a trial still goes through `/pre-register` and `/verdict` first.

## 7. Benchmark rule

Every strategy's weekly report shows the **Nifty Midcap150 Momentum 50 total-return index** over the same dates. A
strategy whose risk-adjusted return (return ÷ volatility) trails the benchmark's over the last **52 weeks** is flagged
for the next quarterly review. The flag is an agenda item, not a verdict.

## 8. Research freeze

While any strategy is in **PAPER or PILOT**, a new research idea is **logged to `research/BACKLOG.md` and not run**,
unless the owner approves it. Measurement of what is already running (data checks, the weekly report, a review's three
questions) is not research and is not frozen.

## What this does not replace

- [`portfolio-simulation`](../portfolio-simulation/SKILL.md): fill realism, the paper broker and kill-switch mechanics.
  Its "≥30 closed trades and about 2 months" paper gate and `forward/prereg_swing.md` §3 predate this model. Until
  the owner amends them, **the stricter rule applies**: 26 weeks.
- [`/verdict`](../verdict/SKILL.md), [`/seal`](../seal/SKILL.md), [`/pre-register`](../pre-register/SKILL.md): how a
  validation or a retirement is adjudicated and frozen.
- The mechanical halts in `forward/prereg.md` §4 and `forward/prereg_swing.md` §5 stay in force.
