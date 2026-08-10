# 07 — ADR-0013's acceptance expires five weeks before the thing it accepts

**Prepared 2026-08-10 for the 2026-10-01 review. Owner decision required — this memo recommends, it
does not decide.** Class: governance. Zero trials, zero screens.

## The finding

ADR-0013 accepted running the live book on a known-wrong TRENT input until **2026-10-01**. Its third
stated reason for deferring was that the defect **self-resolves on 2026-11-06**, when the seam leaves
the engine's trailing 44-week window.

Those two dates are five weeks apart, and the gap is not benign. The acceptance is enforced in code
by `nq.data.adjustment_guard._accepted`, which parses the date and returns `False` past it. From
2026-10-02 the seam is *in-window and no longer accepted*, which is precisely the escalation
condition at `adjustment_guard.py:322`. `assert_no_live_escalation` then raises, and it is called at
`scripts/run_bhanushali_cron.py:594` — outside the download `try`, deliberately, so nothing swallows
it.

**So the acceptance lapses five weeks before the condition it accepts goes away, and the weekly scan
halts for exactly that gap unless a decision is taken on 2026-10-01.**

Computed, not estimated:

| as_of | window opens | seam in window | accepted | escalates |
|---|---|:--:|:--:|:--:|
| 2026-10-01 | 2025-11-27 | yes | yes | **no** |
| 2026-10-02 | 2025-11-28 | yes | **no** | **YES** |
| 2026-11-05 | 2026-01-01 | yes | no | **YES** |
| 2026-11-06 | 2026-01-02 | **no** | no | **no** |

Halt window **2026-10-02 → 2026-11-05**. The scanner runs `30 12 * * 6`, so the scans lost are
**2026-10-03, 10-10, 10-17, 10-24 and 10-31 — five of them**.

Scope of the halt, bounded: only `cron-bhanushali-scanner.yml` invokes `run_bhanushali_cron.py`. The
weekday monitor (`cron-bhanushali-monitor.yml`) does not, so daily re-pricing of held positions is
unaffected. What stops is new signal generation and every artifact that run writes.

## Why the halt is more expensive than it looks

The obvious cost is five weeks of no new entries. The less obvious one is worse.

That same run writes **`results/base_swing_forward.json`** — the `prereg_swing.md` §4 comparator,
which only began logging on 2026-08-08 because §2 had registered it as reconstructable from a ledger
that turned out to be Grade-A filtered. §3 forbids backfilling. So five halted scans are five more
weeks permanently absent from a comparison window that is already truncated on the left, on the one
book §4 defaults to. The §4 decision is due 2027-07-01 and needs ≥20 closed trades **per book**.

A halt taken to protect the integrity of one suppressed candidate would therefore damage the
evidence base for the grading decision the same programme has pre-committed to.

## Options

**A — extend the acceptance to 2026-11-06 (recommended).** A new dated ADR moving `owner_status` to
`ACCEPTED_UNTIL_2026-11-06`, on the same scope ADR-0013 accepted: one suppressed candidate, no open
position. This is what ADR-0013's own reason 3 implies; setting the expiry to the review date rather
than the self-resolution date reads as an oversight, not a judgement. Cost: five more weeks of TRENT
suppressed as a candidate — exactly the cost already accepted, for the reason already accepted.
Note ADR-0013 says *"do not edit `owner_status`"* to get a red scan green; doing it through a dated
ADR at a review date is the sanctioned route, and the distinction is the whole point of that
sentence.

**B — repair the seam via a vendor override.** ADR-0013 reason 4 argued against this and nothing has
changed: the discontinuity is upstream and vendor-reproduced, so a repair is a new permanently
maintained divergence from the data source, not the removal of a local error. It also covers only
part of the class — two of the seven F-1 seams are rights issues whose factors were measured rather
than derived, and two `OPEN-undiagnosed` seams have no known factor at all.

**C — accept the halt.** Defensible only if the owner wants the book to stop rather than run on a
known-wrong input for one name. But note the asymmetry: the input has been knowingly wrong since
2026-08-06 under an explicit acceptance, and nothing about it changes on 10-02 except the calendar.
Stopping then is a change of posture triggered by a date, not by evidence.

**D — remove TRENT from the live universe until 2026-11-06.** Achieves today's net effect (the
candidate stays suppressed) without an override and without a halt, but it introduces a hand-maintained
universe exclusion, which is a worse precedent than a dated acceptance.

## Recommendation

**A.** It is the only option whose cost is one already-accepted cost, and it is what the original
decision's own reasoning points to. Whichever is chosen, the decision must be taken **on 2026-10-01**:
this is the one item on the review agenda with a mechanical consequence for not deciding.

## Verify

```
python -c "import pandas as pd; seam=pd.Timestamp('2026-01-01'); w=pd.Timedelta(weeks=44); until=pd.Timestamp('2026-10-01'); [print(d, (pd.Timestamp(d)-w).date()<=seam.date()<=pd.Timestamp(d).date(), pd.Timestamp(d)<=until) for d in ('2026-10-01','2026-10-02','2026-11-05','2026-11-06')]"
```

Anchors: `nq/data/adjustment_guard.py:278-288, 322` · `scripts/run_bhanushali_cron.py:594` ·
`docs/decisions/0013-defer-live-seam-repair.md:68-72` · `.github/workflows/cron-bhanushali-scanner.yml:15`
