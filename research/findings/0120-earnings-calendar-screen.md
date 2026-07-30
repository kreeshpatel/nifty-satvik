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

---

## ADDENDUM (2026-07-28) — 0121 deferral bound: the setup does not survive the event; no trial

Owner-gated bound (`scripts/diag_deferral_bound_0121.py`; ledger row #10, running count 10; sealed
opens 1; n_trials untouched at 138):

- **94% lapse rate (259/275):** after a results event, the engine re-signals the name within 28cd in
  only 16 cases over 5.5 years. The touch setup almost never survives the event — "deferral" is a
  de-facto SKIP on this funnel, and the 0104/0108 territory it was designed to dodge claims it anyway.
- **The activated cohort is worse-than-peers but POSITIVE-EV** (+0.51R mean despite the −0.38R gap vs
  non-event peers) — so removing those trades costs: pure-skip bookend **−20.96 R/yr**. The 16 genuine
  re-entries were excellent (orig −1.02R → deferred +1.80R, delta +2.82R each) but 3/year cannot carry
  a rule. Clairvoyant ceiling +36.9 R/yr (avoid only the losers — requires foresight).
- **THE PROPOSAL NETS −15.72 R/yr** (4/6 years negative-dominant). **GATE FAIL** — wrong-signed, and
  the year pattern (2022 +38, 2023 −77) is regime-swung, not structure.
- Cohort check: the avoided set is mildly false-touch-enriched (16% vs 12% base) — the Q1 sub-result's
  direction confirmed, but the enrichment is far too weak to overcome the foregone positive EV.

**Program consequence:** the earnings calendar is BANKED alongside delivery (both PIT-proven, both
screen-level effects real, both decision-point-negative). S5 stands resolved-positive at the screen
level with its usage priced OUT at the decision point — do not re-propose skip/deferral shapes without
a mechanism that beats "worse-than-average is still positive-EV." The activation-bound law is now 3/3
(0117 rotation, 0119 tiebreak, 0121 deferral): every external-data usage candidate has been killed for
the cost of a measurement, with total trials spent on the entire external-data campaign = ZERO.
