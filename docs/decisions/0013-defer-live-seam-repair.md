# ADR-0013 — Defer the live seam repair to the 2026-10-01 review

**Date:** 2026-08-06 · **Status:** ACCEPTED · **Decider:** owner
**Class:** governance. Zero trials, zero screens. Counts unchanged: screens 15 · sealed opens 1 ·
n_trials 138.

## Context

The 2026Q3 foundation audit (`diagnostics/research/foundation_audit_2026Q3/FOUNDATION_AUDIT.md`)
established that the pinned OHLCV series contains 13 adjustment-monotonicity violations — sessions
where the implied adjustment factor `adj(t) = cache(t)/raw(t)` falls as time advances, which no
correct adjustment can do. Each is a price step no market produced.

The audit's addendum then relocated the cause: the seams are **vendor-served**. A fresh single-call
download reproduces all 13 exactly, so the pin is byte-faithful to what the vendor publishes and no
rebuild removes them — including the live cron's monthly clean rebuild, whose stated purpose is to
put the cache on one adjustment basis.

Two options were put to the owner in `LIVE_REPAIR_DECISION.md`, with both readings and no
recommendation: (a) repair the live cache now; (b) wait for the 2026-10-01 quarterly review.

The feasibility question was answered first and is not in dispute: **(a) could have been done
without re-anchoring the pin.** The record path (`run_bhanushali_path1.corrected_universe()`) and
the live path (`run_bhanushali_cron._refresh_ohlcv()`) are different functions reading different
artifacts that share the gitignored filename `data/ohlcv.pkl` — the pinned release
`dataset-pin-20260701` on a research machine, and a monthly-rebuilt `actions/cache` instance on the
runner. They already diverge every week. A repair on the live path would have been invisible to the
record by construction.

## Decision

**Option (b). No live repair before 2026-10-01.**

## Reasoning

1. **The scope is one suppressed candidate.** Only TRENT has a seam inside the engine's trailing
   44-week window. CONCOR, HBLENGINE, UPL and the three 2024-01-01 seams have aged out; MAHLIFE is
   not in the live 500-name universe. Measured: live panel `sma44 3248.73`, `close_above_sma False`;
   seam-corrected `sma44 2809.84`, `close/sma 1.0698`, `True`.

2. **No open position is affected.** DELHIVERY, INDUSINDBK, NESTLEIND, CUB and HEG contain no seam
   name. No entry, stop, target or NAV figure moves under either option. The defect suppresses a
   candidate; it does not misprice anything the book holds.

3. **It self-resolves on 2026-11-06**, when the seam leaves the 44-week window — roughly five weeks
   after the review. Acting now buys about one month of corrected signal on one name.

4. **The fix is a vendor override, not a restoration.** Because the discontinuity is upstream, a
   repair means applying our own arithmetic on top of the vendor's using factors from the NSE
   corporate-action record. That is a new, permanently-maintained divergence from the data source,
   not the removal of a local error. Two of the seven F-1 seams are rights issues whose factors were
   measured rather than derived, and the two `OPEN-undiagnosed` seams have no known factor at all —
   so a repair today would cover part of the class and commit the repo to maintaining the override
   for the rest.

5. **`forward/prereg.md` §9 protects three newly-started forward streams.** The clause — *"Between
   dates: monitoring and logging only — no config changes, no size changes"* — exists precisely to
   make mid-quarter discretion structurally impossible. The three forward books are young; the first
   quarter is when a "just this once, it's obviously right" exception is most corrosive, and the
   measured cost of declining it is now small and precisely known.

6. **It arrives with its siblings.** The seam repair, the demerger convention (binder §7) and the
   0025 survivorship re-anchor all change historical bars and share one re-anchor. Deciding them
   together means one convention and one re-anchor rather than three.

## Consequences

- The live book knowingly runs on a known-wrong input for one name until 2026-10-01. This is
  recorded rather than tolerated silently: the seam is registered in
  `nq.data.adjustment_guard.KNOWN_SEAMS` with `owner_status = "ACCEPTED_UNTIL_2026-10-01 (ADR-0013)"`.
- **The acceptance expires by date, not by memory.** `_accepted()` parses the date, so on
  2026-10-02 the same seam escalates on its own with no edit to any file.
- What is *not* known, and is not claimed: whether TRENT would have won a Grade-A slot in any week.
  That is a counterfactual run — a trial — and none was spent.
- `research/config_CHANGELOG.md` carries the dated entry. **No `forward/prereg.md` §10 amendment is
  filed, deliberately:** the decision is to change nothing, and an amendment recording a non-change
  would dilute the amendment log.

## The pre-committed escalation trigger

The acceptance was granted on the scope in reasons 1–2. It lapses immediately if that scope stops
holding. Implemented as `nq.data.adjustment_guard.assert_no_live_escalation`, evaluated on **every**
cron refresh, and raising — halting the weekly scan — when either condition fires:

| Trigger | Rationale |
|---|---|
| **Any ADDITIONAL live-affecting seam** — a seam inside the 44-week window that the owner has not accepted | The scope was "one name". A second one is a different decision. |
| **Any seam on a name the book HOLDS**, accepted or not | The acceptance was granted for a *suppressed candidate*. An open position on a wrong input is a different question and does not inherit it. |

Raising halts the scan, and that is intended rather than incidental: the pre-commitment is that this
returns to the owner **before the book acts again**, not after. A brand-new unregistered seam already
raises via `assert_no_new_seams`; this adds the case of a *registered* seam becoming live-affecting.

Eight tests pin the trigger, including that the acceptance expires on its own date and that a
malformed `owner_status` fails closed rather than granting immunity.

**Do not** widen `LIVE_WINDOW_WEEKS`, edit `owner_status`, or bypass the check to get a red scan
green. Any of those is the decision being reversed without an ADR.

## Revisit

2026-10-01 quarterly review, jointly with the demerger convention and the 0025 re-anchor.

## References

- `diagnostics/research/foundation_audit_2026Q3/LIVE_REPAIR_DECISION.md` — both readings as put
- `diagnostics/research/foundation_audit_2026Q3/FOUNDATION_AUDIT.md` — the audit and its addendum
- `nq/data/adjustment_guard.py` · `tests/test_adjustment_guard.py`
- `forward/prereg.md` §9 · `diagnostics/research/oct1_binder_decisions.md` §7
