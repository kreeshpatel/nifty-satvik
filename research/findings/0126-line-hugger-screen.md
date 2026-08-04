# 0126 — The line-hugger hypothesis: null on all three legs, and the refinement question's point estimate runs BACKWARDS (screen #13; 0 trials)

- **Status:** **LABEL SCREEN** (ledger row **#13**). **Verdict: KILL.**
- **0 trials. Sealed set untouched. Judge log unread. No engine change.**
- **Standing counts: screens 13 · sealed opens 1 · n_trials 138.**
- **Date:** 2026-07-31. Pre-reg
  [`0126-line-hugger-screen.md`](../../diagnostics/research/preregistry/0126-line-hugger-screen.md)
  — committed, and the ledger row appended, **before any label contact**.
- **Script:** `scripts/diag_hug_index_screen_0126.py` →
  `diagnostics/research/hug_index_screen_0126.{md,json}`.
- **Instrument:** the banked 0116/0117 label dataset (`research/substrate/context_windows.parquet`).
  No new adjudicator was built.

## What was tested

The instinct: some names sit on their 44-week line for months and fire the touch signal repeatedly
("choppers"); others touch rarely. Does that **name-level base rate** carry information the funnel
does not already have?

Frozen before any join (pre-reg §1): **`hug_index`** = share of the trailing **52 completed weeks**
with |close/sma44 − 1| < 5%, PIT (week *k* never in its own window), ≥40/52 weeks of coverage
required. Secondaries: `median_abs_ext`, `touch_count`. Rare vs chronic = **median split**, not a
swept threshold. Cooldown N = **8 weeks**, frozen.

**Population:** 1,619 train trades (2,365 non-train rows dropped at read time before any statistic;
41 excluded on the coverage rule). `hug_index` quartiles 0.039 / 0.135 / 0.250 — the feature has real
spread, so the null is not a degenerate-feature artifact.

## Q1 — discrimination: NULL

| | N | meanR | medR | win% |
|---|---:|---:|---:|---:|
| chronic hugger | 754 | +0.437 | +0.325 | 52.3 |
| rare toucher | 865 | +0.476 | +0.334 | 52.4 |

**Conditional on ext-band × CRS cells: +0.022 R, CI [−0.192, +0.243]** — straddles zero.
`false_touch` rate **−0.4pp [−3.8, +3.0]**; `noise_stop` **−2.0pp [−5.5, +1.5]** — both straddle.
Per-year sign 2/4. **ADV-tercile robustness confirms the null rather than rescuing it:** low +0.026
[−0.42,+0.53] · mid −0.052 [−0.36,+0.26] · high +0.023 [−0.29,+0.34].

## Q2 — the refinement question: NULL, and the point estimate is WRONG-SIGNED

The `<5%` ext band's core, split by hug index within the band:

| | N | meanR | medR | win% | 95% CI on the arm's own mean |
|---|---:|---:|---:|---:|---|
| band total | 122 | **+0.681** | +1.315 | 55.7 | — |
| **rare** touch | 62 | **+0.418** | +1.263 | 58.1 | [−0.237, +1.034] |
| **chronic** hugger | 60 | **+0.954** | +1.419 | 53.3 | [+0.324, +1.646] |

**Delta (rare − chronic) = −0.536, CI [−1.493, +0.334]** — straddles zero.
Conditional within-band on CRS: +0.572 [−0.333, +1.454] — straddles. Per-year 2/3.

**The hypothesis was that the deep-band edge concentrates in RARE touches. The point estimate says
the opposite** — chronic huggers carry the higher mean — **and the difference is not significant in
either direction.** So this is not a reversed finding; it is a null whose sign removes the
"directionally promising, just needs more data" escape.

**One reading to head off explicitly:** the chronic arm's CI excludes zero, the rare arm's does not.
That is **not** a separation — it is each arm's own mean being measured against zero, on thin N. The
separation test is the **delta**, and the delta straddles. Reading the two arm-CIs as a discovery
would be exactly the error the matched-cell discipline exists to prevent.

## Q3 — the cooldown formulation: DEAD NULL

Re-touches within 8 weeks of a stop-out on the same name, vs that name's cold touches:

| | N | meanR | medR | win% |
|---|---:|---:|---:|---:|
| hot re-touch (≤8wk after a stop) | 136 | +0.446 | +1.239 | 54.4 |
| cold touch | 1,483 | +0.459 | +0.267 | 52.1 |

**Delta −0.013, CI [−0.843, +0.617]. Conditional +0.094 [−0.734, +0.713]. Activation 8.4%.**
Per-year 3/4, but around a delta of essentially zero.

**"Stop trading the chopper for a while" has no support on this funnel.** A name that just stopped
you out performs indistinguishably from one that did not, and 8.4% activation means even a real
effect of this size could not have moved the book.

## §4 failure-mode checks — none of them explains the result, because there is nothing to explain

| named confound | measured | read |
|---|---|---|
| hug ≈ inverse-CRS | `corr(hug, rank_crs)` = **−0.181** | mild, right-signed, **not dominant** — the ranker is not secretly the whole feature |
| hug ≈ low-vol proxy | `corr(hug, atr_pct)` = **−0.274** | mild, right-signed, not dominant |
| feature validity | `corr(hug, touch_count)` = **+0.762**, `corr(hug, median_abs_ext)` = −0.63 | the primary and its secondaries agree — the instrument measures what it claims |

This matters: the pre-registered KILL conditions were "the cells absorb it" and "it vanishes under
ATR stratification". **Neither fired.** The feature is not a redundant re-encoding of CRS or of
low-vol — it is a genuine, independent, well-measured name-level property that **simply does not
separate outcomes.** That is a stronger null than a confound-explained one.

## Root-cause readout (the mechanism, not the metric)

**The funnel has already conditioned on everything hug index knows.** A name only enters the label
set by *firing the signal* — a rising 44w SMA, a touch inside the band, a quality green week, an RS
gate. Conditional on having cleared all of that, how often the name *usually* sits near its line is
history the entry has already priced. Hug index is a statement about the name's past relationship to
its line; the signal is a statement about its present one, and the present one is the binding
constraint.

**This is Law I again, from a new angle.** Four walls tested *what the approach looked like*
(bar-level statics, path shape, formulas, perception). This tested *what the name is usually like* —
a property of the ticker rather than the setup — and it lands in the same place. **The wall is not
about the window you look at; it is about the funnel having already spent the information.**

**Why the instinct felt true anyway:** a chopper that stops you out three times is memorable, and the
cold touch that worked is not. Q3 puts a number on the availability bias — the hot re-touch cohort
exists (136 trades, 8.4%) and performs **exactly like everything else**.

## Doors — the pre-committed KILL branch, taken

Per pre-reg §5: **KILL** → this finding, an `overlay_registry.md` row, ledger row #13 closed.

- **HEG-class names stay fully tradeable.** No gate, no non-tradeable list, no band relabel, no
  sizing change. Nothing shipped, nothing proposed.
- **The activation bound is NOT run** — it was pre-committed to run only on a PASS. Running it on a
  null would be spending a measurement to price a rule nobody may propose.
- **The line-hugger instinct is retired with receipts.**

## Honest limitations (stated because they bound the claim, not to soften it)

1. **The train window is 4 years, not 6.** `split == "train"` in this substrate is STAGE1's 2019-22
   split, and the pre-reg intersected it with `entry_date ≤ 2024-06-30`. The result is a window
   **stricter than the sealed boundary required** — I left power on the table. The pre-registered
   "≥5/6 train years" leg was therefore **unattainable by construction**; the achievable bar was 4/4,
   and that is how the per-year figures should be read.
2. **Q2 is thin and should be called UNDERPOWERED, not merely null.** N=122 (62/60). The delta CI
   spans ~1.8R — it excludes neither a +0.5R nor a −0.5R effect. What Q2 establishes is that **the
   deep-band edge does not obviously fractionate by hug index**, not that it provably doesn't.
3. **No sealed validation, by design.** Sealed opens stay at **1**. Given 0116 — CI-clean, 5/6 years,
   then sign-flipped on the sealed set — a *positive* result here would have needed one. A null does
   not: there is nothing to validate.

## Do NOT re-test unless

A future proposal may not re-run the line-hugger family unless it brings **at least one** of:

1. **New data** — a train window materially longer than 4 years (e.g. a re-banked label set spanning
   2019-2024H1, which the substrate's own split does not currently offer), such that Q2's band split
   reaches N per arm where a ±0.5R effect is detectable;
2. **A new formulation** whose object is genuinely different — hug index as a *sizing* input rather
   than a discriminator would still be a usage claim and would owe an activation bound first;
3. **A different funnel** — the base rate of a name against a line it is *not* selected on.

**Explicitly refused as relitigation:** a different hug band (3%, 7%), a different window (26w,
104w), a different split point, or a tercile instead of a median split. The feature has real spread,
its secondaries agree with it, and all three legs are null with the confound checks clear — the
failure is not a knob failure.

## Next setup

Nothing here opens a door. The one thing worth carrying: **the `<5%` band's core survives this
test intact** — 122 train trades at **+0.681R**, consistent with the census's +0.717R on the fuller
population, and it does **not** fractionate by how often the name visits its line. The band remains
a single, undifferentiated cohort, which is what the unshipped sizing question will have to size.

## Reproduce

    python scripts/diag_hug_index_screen_0126.py
