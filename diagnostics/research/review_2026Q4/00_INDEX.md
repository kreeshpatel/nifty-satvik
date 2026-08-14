# Oct-1 2026 Review Binder — skeleton (built 2026-07-29; September fills the evidence slots)

Sections (criteria are VERBATIM transcriptions from the source docs; evidence slots empty by design):
1. 01_reanchor.md — corrected-universe re-anchor (harness: scripts/run_corrected_anchor.py, full run)
2. 02_pathB_swing_grading.md — A-only vs base-swing grading decision (prereg_swing.md §4)
3. 03_forward_wall_audit.md — wall integrity + gates (scripts/audit_forward_wall.py vs live logs)
4. 04_breadth50_proposal.md — the watched-pair amendment ask (feasibility memo §3)
5. 05_capstone_carryforward.md — external-data campaign synthesis (capstone memo)
6. 06_habit_ledger_spec.md — forward memory layer, DESIGN SPEC ONLY (owner approve/decline; build is a separate cfg-gated session)
9. 09_category_a_reexamination.md — the closed-verdict re-examination campaign (Find-Its-Home): 4 of 13 Category-A signals placed (delivery→pre-breakout home; low-vol→live-logging at 0.60; PEAD→closed; zoo→closed (real per-trade edge, worse+redundant book)). Feeds §4 — the homes converge on the second book shape. Zero trials, zero new screens spent.

Standing counts at binder creation: screens 11 · sealed opens 1 · n_trials 138.
Standing counts as of 2026-07-31: **screens 12 · sealed opens 1 · n_trials 138** (0123 moved screens 11->12; 0124 Weinstein spent neither).

**Research input (2026-07-31) — the grammar census + finding 0124.** Six real-world grammars were censused as whole systems (Weinstein / Minervini / O'Neil / Turtle / owner multi-timeframe / Darvas-control); Weinstein was run letter-faithful and **KILLed** (finding 0124): capped Sharpe 0.259, 2022-26 slice 0.861 vs the 1.29 bar, 8 of 10 years negative per-trade. Two results matter for this binder: (a) it produced **rho 0.381 / 0.344** to the incumbent swing/lowvol pair - the lowest sleeve correlation ever measured here - and still failed, completing 0115's law from the missing side (orthogonality without edge is worth nothing); (b) the companion ext-band census (`../ext_band_census.md`) measured that **every funnel we own is post-extension** against the weekly 44w line (touch 8.7% is the closest; six-step 29.5%, box 33.8%), and **0.0% of 211 Weinstein signals** land below 5% - so the 0123 pre-extension re-open condition has **no in-house funnel that satisfies it literally**. Path-B and breadth-50 remain the named territories; this is a caution on what they can claim.

---

## Two lines the review must carry (added 2026-07-31)

**(a) 0123's pre-extension re-open condition currently has NO in-house funnel satisfying it literally —
measured, not asserted.** `scripts/diag_ext_band_census.py` →
[`../ext_band_census.md`](../ext_band_census.md) banded every funnel we own against the weekly 44w SMA
from committed ledgers: **touch44 median 8.72%** (the closest to the line), trend_pullback 22.1%,
cup_handle 28.5%, six-step 0084/0085 **29.5%**, double_bottom 31.6%, vcp 33.2%, box 33.8%, sr_pivot 37.9%.
Finding 0124's Gate-1 then measured the newest candidate: **0.0% of 211 Weinstein stage-2 signals land
below 5% ext** (median 17.5%). **Consequence for October: Path-B and the breadth-50 book may NOT claim
the 0123 re-open condition on the grounds that their entries fire pre-extension.** That claim is now a
measurable one, and no funnel we have built passes it. Either may still be promoted on its own merits —
but "it satisfies 0123" is not among them unless and until its own ext-at-entry distribution is measured
and clears. (0123's re-open condition itself is untouched; what changed is that we can no longer assume
which funnels satisfy it.)

**(b) The ρ 0.34–0.38 orthogonal shape — an input to the sleeve discussion.** Finding 0124 KILLed
Weinstein as a system (capped Sharpe 0.259; 2022-26 slice 0.861 vs the 1.29 bar; 8 of 10 years negative
per-trade) — but it produced **ρ 0.381 to swing and 0.344 to lowvol**, against 0.57–0.64 for every 0115
candidate and 0.54 for the incumbent pair with each other. **This is the lowest sleeve correlation the
programme has measured.** The 3-sleeve ERC blend still lost (Sharpe 1.182 → 1.005) and broke the pair's
zero-losing-year property (worst year +3.8% → −2.5%, 0 → 2 losing years).

**0115's law is therefore now proved from both sides:** 0115 killed two candidates that were neither
orthogonal nor strong; 0124 killed one that **was** genuinely orthogonal and had no edge. Structure
without edge is worth nothing. **What this hands the review is a shape, not a sleeve** — a base-breakout
book with its own trend line and its own exit is the first construction to decorrelate from the incumbent
pair. Any future third-leg question should start from that shape and ask what would give it an edge,
rather than re-testing candidates that were never orthogonal to begin with.

---

## 07 — ADR-0013's acceptance expires five weeks before the thing it accepts

**Owner decision required, and it is the only agenda item with a mechanical consequence for not
deciding.** ADR-0013 accepted the TRENT seam until **2026-10-01**, but its own reason 3 is that the
defect self-resolves on **2026-11-06** when the seam leaves the 44-week window. `_accepted()` parses
that date, so from **2026-10-02** the seam is in-window and unaccepted — the escalation condition —
and `assert_no_live_escalation` halts the weekly scan. **Five scans lost: 10-03, 10-10, 10-17, 10-24,
10-31.** Only the Saturday scanner is affected; the weekday monitor does not run that script.

The hidden cost: that run also writes `base_swing_forward.json`, the §4 comparator that only started
accruing on 2026-08-08 and that §3 forbids backfilling. A halt to protect one suppressed candidate
would damage the evidence base for the grading decision the programme has pre-committed to.

Recommended: **extend the acceptance to 2026-11-06 via a dated ADR** — the only option whose cost is
one already-accepted cost, and what ADR-0013's own reasoning implies. Full memo, options and
verification in [07_adr0013_seam_expiry.md](07_adr0013_seam_expiry.md).

---

## 08 — Do we want a faster book? (the intraday-store decision)

**Owner decision, not dated but blocking a build that is otherwise finished.** The intraday store's
whole chain is built and tested and nothing has been fetched, because the reason to fetch turned out
to be narrower than it was described as.

**An intraday store does not certify the swing book.** The ±0.59 ceiling is `n_eff = 37` independent
63-day windows — calendar span divided by holding period. Bar frequency does not enter it. The same
9.5 years at 15-minute resolution gives the same 37 windows, and it does not accelerate the
30-closed-trade paper gate either. Intraday pays only where the HOLDING PERIOD shrinks: a 3-day hold
over the same window has of order 800 independent blocks rather than 37.

So the question is not "should we collect intraday data" but **"do we want a second, faster strategy
family?"** — with its own in-sample work, pre-registration, `n_trials` charge and forward record from
zero. Finding 0133's case is real (11 of 22 surveyed positive strategies are intraday and untested
here purely because no store existed) but it is not a swing-book argument.

Recommendation for the review: **defer the fetch.** With the live book UNCERTIFIED at DSR 0.8096, a
forward record needing a year, and n_trials at 2, opening a second family now competes with the thing
that actually gates real capital. Revisit here as an explicit yes/no.

Census and full reasoning: [`../fo_universe_census_2026-08-11.md`](../fo_universe_census_2026-08-11.md).
It also retires the survivorship worry on a second independent ground: of 151 names that left the F&O
segment, **98 are still trading** — segment exit, not corporate death — and the genuinely-dead tail is
bounded at 53 of 359 (14.8%) and is probably a fraction of that.
