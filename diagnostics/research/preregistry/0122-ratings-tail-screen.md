# Pre-registration 0122 — Credit-rating tail screen (census #4; the disaster-veto question)

**Status:** PRE-REGISTERED (before any feature-label join). **Date:** 2026-07-28. MEASUREMENT — 0
trials; n_trials stays 138. Ledger row #11 (running count 11; sealed opens 1). This is the session's
ONE authorized screen. Step-0 gate PASSED (292 train disasters at the frozen R ≤ −1.5 line), with the
mechanism flag carried honestly: the full disaster list is dominated by market-gap events
(COVID/2022 crash weeks on blue chips) which a ratings mechanism cannot precede.

## Data & PIT
NSE structured credit-rating filings (`harvest_ratings.py`): Symbol, RatingAction, Outlook, prior
rating, **BroadcastDateTime (publication — the PIT layer)** + DateofCR. **Archive regime starts
2023-02** (probed: zero records before; 12 in 2023-02; full volume by 2023-06).

## The coverage hole, stated up front (the invalidation discussion, not dodged)
The covered era excludes the COVID-2020 and 2022 disaster clusters — outcome-correlated missingness in
the raw sense. The screen is therefore ERA-RESTRICTED by construction: universe = train disasters with
entry ≥ 2023-02-01 (~65 events) vs era-matched non-disaster controls. Internally valid within the era;
generalization to crash-era disasters is EXPLICITLY out of scope (and mechanistically hopeless anyway —
ratings do not precede index gaps). The covered era's disasters are the idiosyncratic class the
mechanism targets — the honest test bed.

## Frozen definitions (no scanning)
- Disaster: R ≤ −1.5 (Step-0 frozen line). Controls: same-era trades with R > −1.5, ext-band ×
  CRS-tercile cell-matched.
- Negative rating signal: a filing for the trade's symbol with **RatingAction containing "Downgrade"
  OR Outlook containing "Negative"**, with **BroadcastDateTime ≤ the trade's signal-week Friday**,
  within the trailing **180 calendar days**. One definition, one lookback, one run.

## The pre-committed TAIL question & bar
Fraction of era-disasters preceded by a PIT-knowable negative rating signal vs the matched-control
fraction. **PASS bar:** disaster-preceded fraction exceeds the control fraction with a bootstrap 95%
CI excluding zero AND the preceded fraction is ≥ 15% (below that, a rare-fire veto's ceiling is
negligible regardless of significance — the activation-bound logic applied in advance). Raw counts
reported alongside every rate.
**The honest alternative, stated up front (owner's clause):** if the answer is strong, the usage shape
is a RARE-FIRE VETO whose certification is owner-judgment (0109-class operational insurance), NOT an
n_trials gauntlet — machinery built for means must not be forced onto insurance.

## Named failure modes
1. Mechanism mismatch (the Step-0 flag): era-disasters may still be market/momentum events, not
   credit events → preceded-fraction ≈ base rate → clean KILL, census #4 closes.
2. Coverage bias within the era (audit gate checks per-symbol filing presence vs universe).
3. Tiny-n fragility: ~65 disasters; CIs will be wide; the 15%-floor leg protects against
   significance-without-substance.
4. The 0116 flip precedent applies to any later sealed-era check.
