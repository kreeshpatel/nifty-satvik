# Finding 0129 — Event-proximity SIZING: the bound fails; the effect does not reach the funding margin

**Status: GATE FAIL → NO TRIAL.** Ledger row **#15**. **Standing counts: screens 15 · sealed opens 1
· n_trials 138 (UNTOUCHED).** Sealed set never read. Judge log never read. No engine change.
Pre-reg [0129](../../diagnostics/research/preregistry/0129-eventsize-activation-bound.md);
artifacts `diagnostics/research/eventsize_bound_0129.{json,md}`;
reproduce `python scripts/diag_eventsize_bound_0129.py`.

**Relitigation basis (declared in the pre-reg before the run):** NEW FORMULATION only. 0121 killed
DEFERRAL; this priced SIZING. The event definition (`known_event_within_14cd`) and N=14cd were
imported verbatim from 0120/0121 and nothing was re-tuned. The proposal's family placement was
declared in advance: O-009 vol-target (scale to known forthcoming variance), **not** C3/0073
conviction sizing (scale to predicted return).

---

## The headline: the effect is real on the population and absent at the funding margin

The frozen rule reproduced 0120 **exactly** on 0120's own population — 275 activations, gap
**−0.383R** — which validates the imported definition. Then it evaporated where capital is actually
committed.

| | uncapped substrate (0121's population) | **capped train book (the funding margin)** |
|---|---|---|
| trades | 2,648 | **156** |
| activations | 275 (10.4%, **50/yr**) | **12 (7.7%, 2.2/yr)** |
| cohort mean R | +0.419 | **+0.679** |
| peer mean R | +0.802 | **+0.604** |
| **measured gap** | **−0.383** (replicates 0120) | **+0.076 — WRONG-SIGNED** |

At the funding margin the activated cohort is **better** than its peers, not worse. With N=12 that
point estimate is itself noise — which is the finding, not a caveat: **2.2 activations a year cannot
carry a rule, and cannot even measure one.** This is 0119's mode exactly (a real population gradient
that inverts at the decision margin), and it makes the activation-bound gate **4/4** (0117 rotation,
0119 tiebreak, 0121 deferral, 0129 sizing).

## Both arms, both grid points, against the ±10 R/yr floor

Capped book (**PRIMARY**). The book earns ≈17.3 R/yr in total, so the floor is ~58% of its entire
annual output — registered in the pre-reg *before* the run, not produced afterwards as an excuse.

| arm | f=0.50 | f=0.75 | gate |
|---|---|---|---|
| (a) freed capital in **cash** | **−0.74 R/yr** (4/5 yrs negative) | −0.37 R/yr | FAIL — and cannot pass alone by construction |
| (b) **redeploy**, realistic peer replacement | **−0.08 R/yr** | −0.04 R/yr | FAIL |
| (b) **redeploy, CLAIRVOYANT** best same-week alternative | **+0.78 R/yr** | +0.39 R/yr | **FAIL — 13× below the floor even with perfect foresight** |

The clairvoyant leg is the decisive one: hand the rule perfect knowledge of which replacement to buy
and it is still worth **0.78 R/yr against a ±10 R/yr floor**. No real rule reaches a ceiling, and
this ceiling is already two orders of magnitude short of certifiable.

**Cross-check on 0121's population** (inflated ~6×, reported for direct comparability): arm (b)
realistic reaches **+9.57 R/yr at f=0.50, 5/6 years positive** — the best any usage of this calendar
has produced (0121's deferral was −15.72, pure skip −20.96) — and it *still* sits under the floor.
Recorded because it is the honest best case, and because it shows sizing genuinely dominates
deferral as a shape: half-sizing keeps the +0.51R the cohort earns instead of throwing it away.

## The disaster-class leg: the mechanism's target is not in the cohort

The stated target was the CANFINHOME class. It is not there.

| | activated | non-activated |
|---|---|---|
| n | 12 | 144 |
| **disaster (R ≤ −1.5)** | **0** | 8 (5.6%) |
| worst R | **−0.89** | — |

**Tail relief = 0.00 R/yr at both f.** All eight of the capped book's disaster trades are
*non-activated*; half-sizing on event proximity would have cut exactly none of them. Enrichment is
**−5.6pp** — the activated cohort is *depleted* of disasters, not enriched.

On the uncapped population the tail signal does exist but is mild (12.4% vs 10.0%, **+2.4pp**), and
its relief at f=0.50 is **8.98 R/yr on a book making 367 R/yr** — 2.4% of output, still under the
floor. **Per the pre-reg this is stated and routed to the owner's door, not weighed here and not
self-authorized.** The honest summary for that door: there is no tail case at the funding margin,
and a sub-floor one on the population.

## Root-cause readout — the rule looks the wrong way in time

The mechanism is visible in a descriptive statistic (no outcome contrast attached, no multiplicity
spent). Calendar linkage is **96.2%** on the capped book, so these are facts, not coverage holes:

| | entry is **upstream** of an event (forward 14cd) | entry is **downstream** of one (trailing 14cd) |
|---|---|---|
| capped book | 8.0% | **26.7%** |
| uncapped | 10.5% | 16.2% |

At the funding margin an entry is **3.3× more likely to sit just *after* a results event than just
before one.** That is the funnel working as designed: the event gaps the price down onto the 44-week
line, and the touch fires *because* of it. A rule that de-risks the 14 days *ahead* of an event is
pointed away from where the events actually are.

**The owner's four named tickers, checked against the banked calendar (illustration, not evidence —
and reported as it came out): none of the four was activated.** All four link cleanly (~30 events
each), so these are true negatives:

| ticker | entry | R | nearest known results event | position |
|---|---|---|---|---|
| **CANFINHOME** | 2020-01-27 | **−2.037** | **2020-01-20** (announced 2020-01-01) | **7 days BEFORE entry** |
| **LINDEINDIA** | 2024-03-18 | +2.632 | 2024-02-05 | 6 weeks before entry |
| **LINDEINDIA** | 2019-05-20 | −1.368 | 2019-05-13 | 1 week before entry |
| **GLENMARK** | 2024-02-19 | +1.663 | — | no event in window |
| **NATCOPHARM** | 2020-04-13 | +2.467 | — | no event in window |

CANFINHOME — the disaster the mechanism was named for — had already reported a week before the
trade was entered. Half-sizing on forthcoming-event risk would not have touched it.

## What this closes, and the do-not-re-test clause

**Event-proximity as a SIZING lever is closed.** Combined with 0121 (deferral) and 0120's own
dismissal of the exit-side form, the earnings calendar is now **banked, screen-real, and
decision-point-negative in every usage shape tested**: skip, deferral, and now sizing.

**Do not re-test unless** one of these specifically changes: (i) the book's shape changes such that
event-window entries exceed ~10/yr at the funding margin (a second sleeve, or a materially larger
slot count — the binding constraint here is activation count, not effect size); or (ii) a
*downstream*-of-event formulation is proposed, which is a **different hypothesis** with a different
sign and has never been screened — and which would need its own pre-registration, its own ledger
row, and Law III's bookend before anything else. A different N, a different size grid, a different
multiplier schedule, or a bigger sample on the same forward-looking question is **relitigation and
is refused** — the ceiling failed with clairvoyance, so no re-parameterisation can rescue it.

**Banked outcome-independently:** the activation harness (`scripts/diag_eventsize_bound_0129.py`)
prices any per-trade cohort's sizing bound on both populations with both arms; the next sizing
question does not rebuild it.
