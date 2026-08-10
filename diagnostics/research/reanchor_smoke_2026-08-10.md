# Re-anchor harness, smoke run — 2026-08-10 (PREPARATION, not the record)

**MEASUREMENT, no trial.** Standing counts: read them from `diagnostics/research/n_trials.json` and
`diagnostics/research/label_screen_ledger.md`, never from this line.

## Why this was run

The 2026-10-01 review has the corrected-universe re-anchor on its agenda, and
`scripts/run_corrected_anchor.py` says in its own docstring that the **full** run is September's
memo of record. Producing a competing full-window number in August would just create two artifacts
to reconcile. What is worth doing early is proving the harness still executes — this branch changed
engine code (`cost_mult` in `nq/engine/rebalance_book.py`), and a review that discovers its input
script is broken *on the day* has lost the quarter.

    python scripts/run_corrected_anchor.py --smoke

It ran clean. The Oct-1 input is producible.

## What the smoke window showed

Window **2019-01-01 .. 2021-12-31** — truncated, three years, explicitly **NOT** the record. Universes:
pinned 710 names, corrected 814 (**+104 recovered**).

| book | universe | Sharpe | CAGR % | MaxDD % | after-tax CAGR % |
|---|---|--:|--:|--:|--:|
| LH base | pinned | 1.374 | 38.38 | −35.8 | 30.63 |
| LH base | corrected | 1.374 | 38.38 | −35.8 | 30.63 |
| **swing base** | **pinned** | **1.256** | **28.88** | **−36.3** | **22.91** |
| **swing base** | **corrected** | **1.031** | **25.19** | **−42.3** | **19.99** |

Two things stand out, and they point in opposite directions.

**The LH book does not move at all** — identical to three decimal places on every metric. The 104
recovered names never enter it in this window.

**The swing book — the destination book — moves a lot.** Correcting survivorship costs it **0.225
Sharpe, 3.69pp of CAGR, and 6.0pp of additional drawdown**, and 2.92pp after tax. The direction is
the expected one (survivorship flatters, and finding 0025 measured that the bias scales with holding
period), but the magnitude on this window is larger than "a rounding correction". Trade counts move
too: 77 → 86, with 29 trades appearing only in the corrected arm and 20 only in the pinned one.

## How much weight this carries

Not much on its own, and it must not be quoted as a result:

- **Three years, not nine.** 2019-2021 contains COVID and the recovery, and excludes 2018 and 2022 —
  two of the three years the swing book loses money in. A survivorship correction measured across a
  window that omits most of the book's bad years is not a sample of its bad years.
- **The smoke path is a plumbing proof.** The script's own label is `SMOKE (truncated — NOT the
  record)`, and the September run is what the review reads.
- The 104 recovered names are the same backfill the daily pin already carries; this measures what
  they do to the book, not whether the backfill itself is right.

What it does establish is that the September run is **worth budgeting real attention for**, rather
than treating as a formality. If the full-window effect on the swing book is anything like this one,
the destination book's headline numbers move down, and they move down after this session already
took them from a pre-tax headline to 22.04% after tax at the 2025-12-31 stop.

## Not to be confused with the other re-anchor on the same agenda

`research/0001-xsec-momentum/result.md` records the producer printing Sharpe **0.647** against the
pinned **0.667**. That delta comes from the **M10 holiday fix** (commit `78f6f26`, three mis-listed
2026 NSE holidays that were deleting 2,130 real sessions), not from the corrected universe. Two
different corrections, both dated to 2026-10-01, and they must not be netted against each other.

Reproduce: `python scripts/run_corrected_anchor.py --smoke`
