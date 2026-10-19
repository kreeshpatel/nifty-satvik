# Process tiers — how much ceremony a piece of work actually needs

**Owner decision, 2026-10-19.** The full verdict-machine method (registry confrontation → coverage/PIT
audit → screen row → activation bound → pre-registration → trial) is the right cost for a result that
will change what is traded. It is the wrong cost for most of the work that gets there. Professional
research shops separate *exploration*, which is cheap, fast and labelled, from *confirmation*, which is
expensive and rare. This page is that separation. `skills/session-router` points here at Step 0.

Two standing beliefs underlie it:

- **Our own findings can be wrong.** In one week, 0148 measured a book without the live membership gate;
  0150 asserted, unchecked, that an earlier study had the same defect, when it had not; four findings rest
  on scripts that skip the gate. A prior verdict is a prior, quoted with its epoch, book and test strength.
  It is never a reason to refuse to look.
- **Never answer "no" flatly.** When something looks closed, the answer is the cheapest test that would
  change our mind, not a refusal.

## The tiers

| tier | what it is | ceremony | output may say |
|---|---|---|---|
| **0 · EXPLORE** | any question, any config, in the Strategy Lab (`nq/lab`) or a scratch script, on the **train window** (to 2024-06-30) | **none.** No pre-registration, no screen row, no ledger. Every lab run is logged automatically by the multiplicity meter, and its Sharpe is shown deflated by the number of configs tried. | "exploratory", "suggests", "worth testing". Never "works", never a threshold, never a live change. |
| **1 · MEASURE / RE-RUN** | a descriptive measurement that adopts nothing, or a re-run of an already-registered question under a corrected harness (e.g. adding the membership gate) | a short dated note or an appended `CORRECTION` section; no new screen row; standing counts unchanged | the measured number, with n, CI and which book it is on |
| **2 · SCREEN / BOUND** | a candidate rule's activation bound, to rank what to confirm | one screen-ledger row appended **before** the run; train only | "bound recorded" or "eligible to propose"; ranks, never closes |
| **3 · CONFIRM** | anything that would change live money: a rule, threshold, grading, cap or universe for the book | the full method: pre-registration committed, `n_trials` incremented, then the run; one sealed read; red-team | "adopt / keep / revert" at a quarterly review |

**Promotion only goes up a tier, never skips one into live.** An exploratory hit becomes a tier-2 bound
or a tier-3 trial before it can touch the book; it does not get adopted on its exploratory number.

## What does not get lighter, and why

Only the guards that protect something that **cannot be undone**:

1. **The sealed data** (validation slice 2024-07-01..2026-06-30, and the sealed judge log). A sealed read is
   spent the moment it happens. Exploration stays on the train window.
2. **The live engine's behaviour.** Golden masters stay byte-identical; a new lever is gated off by default.
   Silent drift here changes real trades.
3. **Thresholds before looking, for tier 3 only.** A decision-grade result whose pass bar is chosen after
   seeing it is not evidence. This applies to confirmation, not to exploration.
4. **Hooks.** `scripts/guard_protected_paths.py` stays as is; it is cheap and it has caught real errors.

Everything else (re-runs, measurements, tooling, lab exploration, documentation, refactors that keep the
goldens) goes at tier 0 or 1.

## Quick test for which tier

*If this came back favourable, would anyone change live money because of it, as-is?*
- **No** → tier 0 or 1. Go.
- **Not yet, but it would decide what to test next** → tier 2.
- **Yes** → tier 3.
