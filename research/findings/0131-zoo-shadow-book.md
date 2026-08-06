# Finding 0131 — the zoo's population edge is real, and structurally unbankable in a cash-constrained book

**Date:** 2026-08-06 · **Class: MEASUREMENT / evidence-generation.** Not a trial.
**Counts frozen: screens 16 · sealed opens 1 · n_trials 138.**
Pre-registration [`0131`](../../diagnostics/research/preregistry/0131-zoo-shadow-book.md) — **CLOSED,
falsifier fired.** Producer [`scripts/run_zoo_shadow_book.py`](../../scripts/run_zoo_shadow_book.py) ·
artifact `results/zoo_shadow_book.json` · mechanism evidence
`diagnostics/research/foundation_audit_2026Q3/zoo_mechanism.json`.

**Status: STOOD DOWN 2026-08-06 by owner decision.** Unwired from the Saturday cron; the script, its
artifact and its guard tests are retained so the result stays reproducible on demand.

---

## THE ANSWER — complete, not inconclusive

> **The zoo's population advantage is real. It is also structurally unbankable in a cash-constrained
> book.** Both halves are measured, and the second half has a named arithmetic cause rather than a
> description. **Both escape routes from that cause were already closed before this study ran.**

This is a terminal result, not a failure to resolve. What follows is why.

---

## 1. The advantage is real

At population level, with CIs excluding zero **in both units**
([`ZOO_TWO_LENS.md`](../../diagnostics/research/ZOO_TWO_LENS.md)):

| setup | N | ΔR vs touch44 | Δ% of equity |
|---|---:|---:|---:|
| cup_handle | 195 | **+0.365** | **+0.758pp** |
| box | 543 | **+0.287** | **+0.574pp** |
| double_bottom | 502 | **+0.266** | **+0.509pp** |

And the rejection that had stood against them was never resolved: STAGE4's standalone line
(touch 1.29 vs cup 1.02 / box 1.00 / dbl 0.94) **carried no CI at all**, and its gaps of
0.27 / 0.29 / 0.35 sit inside the measured ±0.302 band — conservatively, since it is a sub-slice on
smaller books ([`POWER_READJUDICATION.md`](../../diagnostics/research/POWER_READJUDICATION.md)).

## 2. It is unbankable — and here is the arithmetic

The shadow book put the elected pool through the **same CRS priority and the same frozen ladder**,
changing only the candidate pool. Both pre-committed falsifier legs fired at the first observation:

| | live | shadow | |
|---|---:|---:|---|
| closed trades | 255 | **491** | **+92.6%** vs a 25% threshold |
| **% of equity per trade** *(arbiter)* | +2.782 | +0.841 | **−1.941pp, CI [−3.598, −0.264]** |
| mean R per trade | +0.481 | +0.205 | −0.276, CI [−0.486, −0.067] |
| touch44 fills | 255 | **29** | displaced, not supplemented |
| shared fills | — | **19** of 255/491 | the two books are nearly disjoint |

### The mechanism, link by link, each one measured

**stop width → notional → seat count → dilution**

| link | measurement |
|---|---|
| **1. The zoo's stops are far wider** | median stop width: touch44 **7.00%** · cup **17.29%** · box **19.33%** · double_bottom **24.87%** — 2.5× to 3.6× wider |
| **2. So its positions are far cheaper** | under `shares = equity × 2% ÷ stop`, median position: touch44 **28.58%** of equity · cup **11.56%** · box **10.35%** · dbl **8.04%** — roughly **3× cheaper** |
| **3. So the same cash buys many more seats** | mean concurrent positions **5.64 → 12.15** (max 10 → 20); median position size **15.21% → 7.03%** of equity |
| **4. And seat count is a measured dilution axis** | `FINDING_more_slots` (**trial-priced**, `n_trials` 120→122): 4–5 seats **1.21** → 7 seats **0.97** → 10 seats **0.81**, against a random null of **0.74**. **The shadow book runs at 12.15 mean seats — past the worst point that study measured.** |

This is the first time the population-vs-portfolio gap has an **arithmetic** cause on this book
rather than a description. It is not that the zoo signals are secretly bad; it is that *wide stops
are cheap*, cheapness buys seats, and seats are already known to dilute.

### One correction to the chain as originally framed

The mechanism was put to this session as ending in *"walks the CRS queue down."* **The data do not
support that phrasing and it is not used.** The shadow book's funded fills have a *higher* mean
`crs_dist` (+0.4216) than the live book's (+0.1403). The reason is that `crs_dist` is **not
comparable across detectors** — breakout setups sit further above their own RS line by construction:

| setup | median `crs_dist` |
|---|---:|
| touch44 | +0.046 |
| cup_handle | +0.183 |
| box | +0.202 |
| double_bottom | +0.206 |

So a cross-setup CRS comparison measures the detector, not queue depth. The fourth link is **seat
count → dilution**, and it rests on a trial-priced dose-response rather than on a CRS statistic —
which makes it stronger evidence, not weaker.

## 3. Both escape routes were already closed — this is what makes it final

A structural cause is only terminal if the ways around it are shut. Both are, and both were shut
*before* this study ran:

| escape route | why it would work | why it is closed |
|---|---|---|
| **Leave the freed cash idle** — take the zoo trades but don't let cheapness inflate seats | caps seat count at the live book's ~5–6 | **0104 / 0108**: subtractive rules and idle capital are negative on this book. Law III's bookend — the removed trade's slot is not free, and the same-week queue alternative is net negative (0117). |
| **Size by notional instead of risk** — decouple position size from stop width so seats stay fixed | removes link 2 entirely | **0130**: equal-notional sizing on this book is **−10.83% of equity per year**, CI [−26.33, +4.74], 7 of 10 years the same sign. Measured *before* this study, for a different question. |

**With link 2 unavoidable and link 3's consequence already priced, there is no construction inside a
₹10L cash-constrained book that banks the population edge.** That is a complete answer.

## 4. What is NOT closed

**A different book *shape*.** Everything above is about forcing more detectors through the same
five-ish seats under one cash pool. It says nothing about a book that is *designed* for many
equal-weighted names — breadth-50 is the named candidate elsewhere, and this finding neither
supports nor damages it. The distinction is exact: this closes *widening the pool inside the
concentrated book*, not *a different book*.

---

## What could and could not be certified

The ΔSharpe is **−0.2845 — inside the ±0.302 resolution band, and NOT a verdict.** Pre-registration
§4 forbids reading it as one, and this finding does not.

That constraint cuts both ways and is the reason this study was worth running: the same instrument
limit that made the zoo's *rejection* unsafe would have made its *acceptance* unsafe. **What settled
it was not the Sharpe — it was three quantities that do not depend on the underpowered metric:**

1. the **trade count** (255 → 491) — an exact count, not an estimate;
2. the **per-trade quality delta** — a CI excluding zero in the arbiter unit on 491 vs 255 trades;
3. the **displacement** (touch44 255 → 29; 19 shared fills) — structural, not statistical.

---

## H-bis — the drawdown axis, completed 2026-08-06

**Why this was asked, and why it was a real gap.** The first version of this study reported **Sharpe
and nothing else**. `research/losers_analysis/LOCKED_STRATEGY.md:64` records the box/S-R sleeve as a
**drawdown-only option** — *"dilutes Sharpe (0.855 vs 1.034 touch-only); only helps DRAWDOWN
(−32.5 vs −34.8, stable)"* — and `:73` preserves it as *"a live/forward-wall DRAWDOWN option (−2pp DD
at a Sharpe cost)"*. Reporting only the axis that fell, on precisely the family the record keeps for
the axis that did not, left the record incomplete. **Completing it; the stand-down is unaffected and
the falsifier was not re-run** (its fields are byte-unchanged: 255→491, +92.55%, arbiter −1.9406
[−3.5975, −0.2644]).

| | live book | shadow book | Δ |
|---|---:|---:|---:|
| **MaxDD** | **−42.374%** | **−42.928%** | **−0.553pp (deeper)** |
| CAGR | 24.694% | 18.834% | −5.86pp |
| **Calmar** | **0.5828** | **0.4387** | **−0.1440** |
| worst calendar year | 2025, −13.803% | 2018, **−18.867%** | −5.06pp |
| **losing years** | **1** | **4** | **+3** |

**There is no drawdown gain. Every risk measure moves the wrong way.**

- ΔMaxDD of −0.553pp sits inside the measured ±9.05pp band (STAGE4's published ΔMaxDD CI
  [−0.049, +0.132] around +0.088), so on MaxDD *alone* the two books are **not resolvably
  different** — but the direction is worse, not better.
- **Losing years 1 → 4 is an exact count, not an estimate**, and the worst year deepens by 5.06pp.
  Those do not depend on the underpowered metric.

### Why the preserved sleeve option does not appear here — and this is the point

`LOCKED_STRATEGY.md:64` is explicit about its construction: *"Box/S/R sleeve **(with capital)**"* —
a **sleeve with its own budget**, allocated capital of its own. The 0131 shadow book is the opposite
construction: a **shared pool** competing for one cash book's seats. The −2pp DD benefit is a
property of **sleeve allocation**, not of the box/S-R family, and it does not transfer to a shared
pool. That is the same distinction §4 of this finding already draws — *a different book shape is not
closed by this* — arriving from the risk side.

### Nothing routes to the owner

**This is not a Law VII risk-preference dial.** Law VII is *robustness is bought with return* —
a candidate that improves drawdown at a cost in CAGR, which is owner preference territory rather than
a promotion. **Here robustness was not bought at all: both axes moved the same way.** There is no
trade-off to price and therefore no dial to offer. A candidate that is worse on return *and* worse on
risk needs no risk-preference decision.

The DD option `LOCKED_STRATEGY.md:73` preserves for the **sleeve** construction is untouched by this
and remains exactly where it was.

## Root-cause readout

Wide stops make the zoo's positions cheap. Cheap positions multiply seats. Seats dilute, on a
dose-response this programme has already paid a trial to measure. The population edge is real and
every route from it to the book runs through a step that is already closed.

## Next setup

None. The territory is closed, and closed *with* its mechanism.

## Do not re-test unless

A **different book shape** — not a different pool inside the same seats — with its own sizing
construction and its own seat count, judged on forward evidence. Re-running a wider pool through the
concentrated book with a different detector set, a different threshold, or a bigger sample is refused
relitigation: the mechanism is arithmetic and does not depend on which detectors are chosen.
