# Finding 0120 — Earnings screen: KNOWN event proximity at entry costs ~0.3R (Q2 PASS, PIT-legal); Q1's big number is a duration confound, dismissed

**Status: SCREEN PASS on Q2 at the pre-registered bar — STOPPED at the PASS door.** Ledger row #9
(running count 9; sealed opens 1). n_trials untouched at 138. Pre-reg
[0120](../../diagnostics/research/preregistry/0120-earnings-calendar-screen.md); audit gate PASSED
(coverage 97.7-99.5%/yr, 251 delisted-in-window symbols, lag median 8d with only 0.3% ≤0d — the PIT
layer is sane; SEBI's ≥5-day intimation rule visible at p10=6d).

## The honest Q1 dismissal FIRST (the biggest number in the readout is a confound)
Raw "holding through a results event" shows +1.58R [+1.37,+1.82] — and it is NOT a causal event
benefit: exposure is proportional to HOLDING TIME, and duration is mechanically confounded with
outcome on this book (losers stop out early and short; survivors live long enough to meet a quarterly
event; 76% base exposure). The number is duration survivorship and is DISMISSED, not claimed. (The
pre-reg named the frequency trap; the duration form of it surfaced here and is recorded as the
governing caveat for any label-side exposure contrast on this dataset.)

## What survives
- **Q2 (feature-side, PIT, the actionable result): PASS.** `known_event_within_14cd` — at the
  signal-week Friday, a results event already ANNOUNCED and dated within 14cd of the entry-week
  Monday — activates on 275 train trades (10%, ~50/yr) and costs **dR −0.383 [−0.680,−0.121] raw,
  −0.294 conditional (ext×CRS)**, sign-consistent **5/6 years**, ADV-tercile deltas all-negative
  [−0.13,−0.44,−0.81]. Clears every leg of the bar. Mechanism: entering INTO a known imminent binary
  event buys the event gap with a fresh (wide) stop — the risk is knowable at decision time and is
  currently ignored by the funnel.
- **Q1 sub-result (cohort-matched, CI-clean): false_touches are MORE event-struck than noise_stops
  (63% vs 54%, +9.8pp [+2.6,+17.2])** — both cohorts are stop-outs of similar duration, so the
  duration confound largely cancels; events are disproportionately present in the UNRECOVERABLE
  stops. Supports the same mechanism from the label side.
- **Q3: null** (exit-too-early is not about selling before favorable events).

## Registry consequence
**S5 ("earnings event de-risking", OPEN since the sell-replace skill) is now RESOLVED-POSITIVE AT THE
SCREEN LEVEL** — the PIT calendar exists, and the entry-proximity form of the hypothesis is confirmed
on train years. S5's exit-side form remains untested (and post-entry conditional territory is closed
by 0117 — any usage lives at ENTRY/DEFERRAL, not exit).

## Usage sketch (one paragraph, per the door; confronts both mandated territories up front)
The mechanism-matched shape is a **DEFERRAL, not a skip** (0104/0108 territory confronted first: a
skip is a trade-count filter and dies by idle-cash redeployment; deferral is not — the signal's entry
window SHIFTS to the first post-event week, entering only if the setup still qualifies, so the trade
usually still happens and the slot re-opens within days). **The activation-bound law binds next
(confronted second):** before any trial ask, the zero-trial clairvoyant bound must be run — the raw
material is promising (275 activations, ~50/yr — 18x the tiebreak's; naive ceiling ~+19R/yr if every
deferred entry recovered the full −0.38R gap, well above the ±10R floor) but the honest bound must
mechanically simulate deferral (some setups lapse, some re-enter at worse prices) and THAT number
decides whether a trial is ever pre-registered. Nothing proceeds without the owner's sign-off.
