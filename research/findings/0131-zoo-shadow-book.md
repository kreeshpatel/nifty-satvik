# Finding 0131 — the zoo shadow book: elected, built, and falsified by its own first observation

**Date:** 2026-08-06 · **Class: MEASUREMENT / evidence-generation.** Not a trial.
**Counts frozen: screens 16 · sealed opens 1 · n_trials 138 — this spends none of them.**
Pre-registration: [`0131-zoo-shadow-book.md`](../../diagnostics/research/preregistry/0131-zoo-shadow-book.md) ·
producer: [`scripts/run_zoo_shadow_book.py`](../../scripts/run_zoo_shadow_book.py) ·
artifact: `results/zoo_shadow_book.json`.

---

## What was elected, and on what evidence

**Elected:** `cup_handle` + `box` + `double_bottom`, added to `touch44` as one combined candidate
pool, run as a **watched shadow book — observational, traded by nobody.**

The evidence was two-sided and both sides were about *power*, not about performance:

1. **Population level** ([`ZOO_TWO_LENS.md`](../../diagnostics/research/ZOO_TWO_LENS.md)): all three
   beat `touch44` with CIs excluding zero **in both units** — cup ΔR +0.365 / Δequity +0.758pp, box
   +0.287 / +0.574, dbl +0.266 / +0.509. `ascending_base` was *not* elected: N=106, both CIs straddle.
2. **The standalone rejection was never tested.** STAGE4's most-cited line — touch 1.29 vs cup 1.02 /
   box 1.00 / dbl 0.94 — carries **no CI, no bootstrap, no walk-forward**. Its only two intervals are
   for config D vs A. Applying the measured ±0.302 band, gaps of 0.27 / 0.29 / 0.35 are **inside it**
   — and the band is *conservatively* transferred, because these are sub-slice, smaller-N comparisons
   whose true band is wider. The families were **not proven worse**; they were never resolved.

---

## The pre-committed hypothesis, and its immediate falsification

> **H (pre-registered):** the combined funnel improves the **pool**, not the **throughput** — capital
> binds, not signal supply.
>
> **Falsifier (pre-registered):** trade count rising **>25%** over the live book while per-trade
> quality does not rise.

**Both legs fired on the first observation.**

| | live book | shadow book | |
|---|---:|---:|---|
| closed trades | 255 | **491** | **+92.6%** vs a 25% threshold |
| mean R per trade | +0.4812 | +0.2054 | **−0.276**, CI [−0.486, −0.067] |
| **mean % of equity per trade** *(arbiter)* | **+2.7818** | **+0.8412** | **−1.941pp, CI [−3.598, −0.264]** |
| win rate | 59.2% | 54.6% | −4.6pp |

**The arbiter's CI excludes zero.** H is falsified on its own pre-committed terms, in its own
pre-committed unit, before any forward data exists.

### The mechanism — and it is the wall again, seen from a new angle

The two books are **almost disjoint**: 19 shared fills against 236 live-only and 472 shadow-only.
And inside the shadow book, `touch44` fills collapse from **255 to 29**.

| shadow book, by detector | n | mean R | mean % equity |
|---|---:|---:|---:|
| touch44 | 29 | +0.8146 | +1.5774 |
| box | 164 | +0.1699 | +0.8912 |
| double_bottom | 241 | +0.1537 | +0.7745 |
| cup_handle | 57 | +0.2157 | +0.6046 |

Widening the pool did not add trades *alongside* touch44 — it **displaced** it. Three detectors
firing into the same five-ish seats consume the cash that funded the touch book, and the touch trades
that survive are a small residue. This is the per-trade-≠-portfolio wall for the **seventh** time on
this exact question (0112 fill priority, ROUTER per-branch exits, STAGE4 sleeves, E1/E2/E3 entry
levers, `FINDING_more_slots` dilution), and it is also `more_slots` again: nearly doubling throughput
walks the book down the CRS queue.

**Population truth and portfolio truth are both correct and they do not transfer.** Per signal, the
three elected setups genuinely are better than touch44. Pooled into one capped book, they make it
worse. Nothing in this finding contradicts `ZOO_TWO_LENS.md`; it is the cap acting on it.

---

## What cannot be certified in-sample, and why

The ΔSharpe is **−0.2845 — inside the ±0.302 resolution band, and therefore NOT a verdict.**
Pre-registration §4 forbids reading it as one and this finding does not. It is quoted here only with
its band attached.

That constraint is not a formality. The measured band is ±0.302 ΔSharpe against a book whose entire
annual return is 1.617σ, so **the capped book cannot certify any improvement or any degradation of
this size** — which is exactly why the standalone rejection this election was founded on is itself
NOT PROVEN. The same instrument limit that made the zoo's rejection unsafe makes its acceptance
unsafe.

**What IS resolved, and does not depend on the underpowered metric:**
- the **trade count** (255 → 491) is an exact count, not an estimate;
- the **per-trade quality delta** has a CI excluding zero in the arbiter unit on 491 vs 255 trades;
- the **displacement** (touch44 255 → 29, 19 shared fills) is structural, not statistical.

**What remains unresolved:** whether the combined pool would be better under a *different* book
shape — one that does not force three detectors through five seats. Equal-weight in a wider book is
the named candidate elsewhere (breadth-50) and this finding says nothing about it.

---

## What was built

Cold and cfg-gated, beside the existing observational loggers:

- `scripts/run_zoo_shadow_book.py` → `results/zoo_shadow_book.json`, whitelisted, wired into the
  Saturday cron as an **optional** artifact that warns and never fails the scanner.
- Nothing in the live book, the cards, the wall or the traded config is touched. The golden master is
  byte-identical and the determinism guard still reproduces **1.1319 / 255** — asserted inside the
  shadow book's own live arm, which *is* the record.
- `tests/test_zoo_shadow_book.py` (6 tests) pins that it cannot influence the traded book: exactly
  one write, to its own file; no attribute assignment into a shared module; the elected pool frozen
  at cup+box+dbl; **no kwarg anywhere that alters the exit ladder, fill priority or sizing**; not
  imported by any traded path; and the record reproduced before *and* after the wider pool is built.

*Recorded: the first version of those tests scanned raw source text and failed on the module's own
documentation — which names the artifacts it must not touch precisely in order to say it does not
touch them. They now scan the AST. A guard that fires on its own prose is the false-positive class
this programme has twice paid to learn about.*

---

## The Oct-1 ask

**Formalise as a wall book, or stand it down.** The pre-registration set 2026-10-01 as a status check
and 2027-04-01 as the first substantive read. That schedule is now overtaken by the falsification:

- **Stand it down** — the pre-committed falsifier fired on both legs at the first observation, in the
  arbiter unit, with a CI excluding zero. Continuing to log a book whose stated hypothesis is already
  refuted spends cron time for evidence about a question that has been answered.
- **Keep it running** — the falsification is *in-sample*, and in-sample is exactly what this
  programme holds cannot certify. Forward selection-divergence data is unbiased and costs one cron
  step; the displacement mechanism is worth watching live at least once.

**No recommendation is made.** Both readings are stated; the decision is the owner's.

## Do not re-test unless

This finding creates no re-open condition. The elected setups remain **not proven worse standalone**
(a labelling correction, not a revival) and **measured as diluting when pooled into the capped book**
(this finding). A different *book shape* — not a different pool inside the same five seats — is the
only construction this result does not speak to.
