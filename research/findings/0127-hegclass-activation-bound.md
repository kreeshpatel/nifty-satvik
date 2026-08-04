# 0127 — HEG-class approach: the cohort is real and materially worse, and BOTH activation bounds fail — conditional management fails by *identity*

- **Status:** **ACTIVATION BOUND** (ledger row **#14**). **Verdict: FAIL both alternatives → no screen #14.**
- **0 trials. The 0116/0117 sealed slice was never read. Judge log unread. No engine change.**
- **Standing counts: screens 14 · sealed opens 1 · n_trials 138.**
- **Date:** 2026-07-31. Pre-reg
  [`0127-hegclass-activation-bound.md`](../../diagnostics/research/preregistry/0127-hegclass-activation-bound.md)
  — committed, and the ledger row appended, **before the run**.
- **Script:** `scripts/diag_hegclass_bound_0127.py` →
  `diagnostics/research/hegclass_bound_0127.{md,json}`. Deterministic on re-run.

## The archetype, reproduced from a committed script

The owner's pattern: a name makes a high, declines for 4+ weeks, and that decline carries it back to
the 44-week SMA where the signal fires. Frozen as `descent_duration ≥ 4wk` **and**
`descent_depth ≥ 20%` off the trailing-13-week peak.

**Population:** 1,415 uncapped `touch44` trades, ≥2019, 7.46 years, 600.6R total (**80.6 R/yr**).

| threshold | N | share of touches |
|---|---:|---:|
| **≥4wk & ≥20% (PRIMARY)** | **229** | **16.2%** |
| ≥4wk & ≥15% | 406 | 28.7% |
| ≥6wk & ≥20% | 203 | 14.3% |

Descent quartiles: duration **4 / 7 / 11** weeks · depth **5.1 / 10.6 / 17.0%** · velocity
**0.7 / 1.6 / 2.9 %/wk**. *(The 2026-07-31 ad-hoc table reproduces; it now informs something.)*

## The instinct is descriptively RIGHT

| | N | meanR | win% |
|---|---:|---:|---:|
| **HEG-class** | 229 | **+0.062** | 40.6 |
| everything else | 1,186 | **+0.494** | 48.1 |

**A 0.43R per-trade gap and 7.5pp of win rate.** The owner saw something real: these approaches are
materially worse trades, and the funnel has been taking them at 16% of volume the whole time.

**And it does not matter, for two independent reasons.**

## Bound (a) — EXCLUSION: 1.92 R/yr. FAIL.

**Refusing the entire cohort costs 1.92 R/yr** — the cohort is a *nothing* engine, not a loss engine.
229 trades over 7.5 years produce **+14.3R total**, which is **2.4% of book R** from **16.2% of
trades**. Marginally positive-EV, and therefore Law III bites exactly as written: *"Identifying a
below-average cohort does not license removing it."*

1.92 R/yr against a **±10 R/yr** floor is not close. Per-year the cohort's own R is negative in 5 of
8 years — consistent, and consistently trivial.

**The clairvoyant leg is reported and then set aside honestly.** Refusing only the cohort's *losers*
is worth **26.22 R/yr**, which does clear the floor on magnitude. It is not a pass and I am not
treating it as one:

- its sign test is **a tautology, not evidence** — removing negatives is positive by construction in
  every year, so "sign consistency" measures nothing there;
- it is **unreachable by construction** — picking the losers in advance is precisely the pre-entry
  wall (bar-level ML, loser forensics, path shape, formulas, perception; five independent nulls);
- and **0121 showed redeployment is the dominant term** anyway — the refused slot is not free.

I flag this leg explicitly because 26 R/yr above a 10 R/yr floor is exactly the number a future
session would quote out of context.

## Bound (b) — CONDITIONAL MANAGEMENT: 0.0 R/yr. FAIL, by identity.

This was the owner's actual claim — *not* "exclude them", but "handle them differently". Total R
under each frozen management:

| management | whole book | HEG-class | everything else |
|---|---:|---:|---:|
| as-is | 600.6 | 14.3 | 586.3 |
| TP @ +2R | 418.8 | −2.7 | 421.5 |
| **TP @ +3R** | **678.1** | **37.7** | **640.4** |
| stop @ −0.5R | 212.0 | −33.9 | 245.9 |

**Best for the cohort: TP@3R. Best for everything else: TP@3R. Best single management for all:
TP@3R.** The same column wins all three times.

**Clairvoyant conditional gain = −0.0 R total = 0.0 R/yr, and exactly 0.0 in all 8 years.**

This is the strongest form a null can take. It is not "the gain was small" or "the CI straddled" —
**with perfect hindsight over the frozen management set, the HEG-class cohort wants the identical
treatment to everything else.** There is no different handling to discover, because the optimum
does not move.

**One number here must not be misread.** TP@3R appearing to beat as-is on the whole book (678.1 vs
600.6) is **an artifact of the pre-registered excursion-order approximation**, not a finding about
exits. The model assumes a favourable excursion was reachable when we only know it occurred; real
path order is unknown. That optimism was deliberate — it inflates every ceiling, which is the
conservative direction for a bound meant to fail — but it means **nothing in this table is evidence
that TP@3R is a better exit.** Exit geometry remains closed unconditionally (0105 / 0106 / 0109).

## Root-cause readout (the mechanism, not the metric)

**The cohort is worse per-trade and irrelevant per-book, because being worse is not the same as
being separable in a way the book can spend.** 16.2% of trades carrying 2.4% of R means the cohort
is where the book's *marginal* trades live — near-zero expectancy, high variance, and already priced
into every aggregate we have. Removing them recovers almost nothing; managing them differently
recovers exactly nothing.

**This is Law II in its purest observed form.** A real population gradient (+0.062 vs +0.494 is not
subtle) that carries no decision-margin value at all. The programme has now seen this five times —
IC ≠ Sharpe (0079), pool ≠ book (0112), screen ≠ slot (0119), screen ≠ entry decision (0121),
perception ≠ outcome (0123) — and this is the sixth: **cohort ≠ playbook.**

**Why the instinct felt so strong:** a 0.43R per-trade gap is genuinely large and genuinely visible
when you watch individual names. What is invisible while watching is that the cohort nets to
break-even rather than to a loss, and that the optimum management does not move. Both facts are
arithmetic, not intuition, which is why the bound exists.

## The named failure modes (pre-reg §4), scored

| adverse prior | how it landed |
|---|---|
| **0116's sealed flip** on the nearest family | Not engaged — there was no train-clean effect to flip. The bound died on magnitude, upstream of any sealed question. |
| **`dist_52wh`'s gradient points against the cohort** (39→46→50→54→55 win% toward the 52w high) | **Corroborated.** HEG-class win rate 40.6% vs 48.1% — the cohort sits where that gradient predicted, and the two independent measurements agree. |
| **Exit geometry closed unconditionally** (0105/0106/0109) | **Reinforced.** Bound (b) says the optimum does not move even when you are allowed to condition on cohort membership with hindsight. |
| **Law V — post-entry is hindsight-only** | **Reinforced, and this is the sharpest instance yet.** Bound (b) *gave* the rule hindsight and it still bought nothing. |

## Doors — the pre-committed FAIL branch, taken

Per pre-reg §3: **no screen #14.** HEG-class names stay fully tradeable and **identically managed**.
Nothing proposed, nothing shipped, no cfg lever, no band relabel, no card change.

### The closing clause, now in force

**This was the FINAL reformulation of the line-hugger instinct this quarter.** It has been given a
base-rate test (0126, null on three legs) and a kinematics test (0127, both bounds fail). **The
thread is closed until genuinely new data — habit-ledger labels — exists.** No further phrasings:
not a different descent window, not a different depth threshold, not velocity instead of depth, not
a per-name variant.

## What was banked anyway (outcome-independent)

`descent_duration`, `descent_depth`, `descent_velocity` are added to the habit-ledger schema §1.2
entry-context block. They are **not** banked because they predict anything — this finding says they
do not. They are banked because they are cheap, PIT-safe, and describe a real 16% cohort, so the
next question about approach kinematics does not have to re-derive them from raw bars the way this
one did. That is the ledger's whole purpose.

## Do NOT re-test unless

The habit ledger has accrued **forward** rows carrying `descent_*`, and the question asked of them is
one this bound could not answer — i.e. **not** exclusion and **not** conditional management over the
frozen M set, both of which are now measured at 1.92 and 0.0 R/yr respectively.

**Explicitly refused as relitigation:** widening the management set M post-hoc (the set was frozen
precisely so this could not happen), a different descent threshold, or re-running on the capped book
— the uncapped population was chosen because it *inflates* both bounds, so the capped book can only
be worse.

## Next setup

Nothing here opens a door. The durable result is the sixth instance of Law II, and it is worth
stating in the general form the programme can reuse: **a cohort being measurably worse is not a
reason to treat it differently — the test is whether the optimum treatment moves.** Bound (b) is a
cheap, general instrument for that question and can be pointed at any future cohort proposal.

## Reproduce

    python scripts/diag_hegclass_bound_0127.py
