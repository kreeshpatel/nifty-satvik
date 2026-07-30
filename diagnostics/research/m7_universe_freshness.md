# M7 — universe freshness: snapshot vs membership, before the September rebalance

**Date:** 2026-07-29 · **Script:** [scripts/diag_m7_universe_freshness.py](../../scripts/diag_m7_universe_freshness.py)
· **Data:** [m7_universe_freshness.json](m7_universe_freshness.json) · Read-only; the universe was
not modified. **Counts unchanged: screens 11, sealed opens 1, n_trials 138.**

Constitution D1 / B-10: the live scan universe is `config.NIFTY_500`, a hard-coded snapshot dated
**2025-07-20**, intersected at card and entry time with `data/nifty500_membership.csv`. The
September semi-annual NSE rebalance lands **before** the Oct-1 review.

## Headline: a symmetric 48-name gap, in both directions

| Measure | Value |
|---|---|
| Snapshot `config.NIFTY_500` (2025-07-20) | 500 names |
| Membership file active today (mtime **2026-06-28**) | 500 names |
| In snapshot but **not** currently active | **48** — AKUMS, ALIVUS, ALKYLAMINE, ALOKINDS, APLLTD, ASTRAZEN, BASF, CAMPUS, CENTURYPLY, CERA, DBREALTY, FINPIPE, GNFC, GODREJAGRO, GPPL, … |
| Currently active but **not** in the snapshot | **48** — ABDL, ABLBL, ACUTAAS, AEGISVOPAK, ANTHEM, ANURAS, ATHERENERG, BELRISE, BLUEJET, CANHLIFE, CARTRADE, CEMPRO, CHOICEIN, CPPLUS, EMMVEE, … |
| OHLCV cache coverage | 710 names; 5 snapshot names and 1 active name missing |

**Sentinel handling verified** (the check that could have silently emptied the universe): all 500
active rows carry the open-ended `2030-12-31` `to_date`, zero carry a real future date, and
`current_members()` parses them correctly — 500 active, not 0. No sentinel defect.

## Reading

The two 48-name sets are **not** symmetric in consequence:

* **Active-but-not-in-snapshot (48 names) can never produce a live signal**, regardless of what the
  membership file says — the snapshot is the *scan* universe and membership only *masks* it. Roughly
  one index-tenth of today's Nifty-500 is structurally invisible to the live book. These are
  disproportionately recent listings (ATHERENERG, BELRISE, EMMVEE, AEGISVOPAK), i.e. exactly the
  younger names a 44-week-SMA trend book would take time to qualify anyway — which softens, but does
  not remove, the miss.
* **In-snapshot-but-not-active (48 names) are still scanned**, but the membership check at card and
  entry time correctly blocks them, so they cannot enter. The residual risk is a name that exits the
  index *while held*: nothing forces an exit, and with holds now measured up to 201 weeks (see
  [M2](m2_hold_age.md)) a position can outlive several rebalances.

The membership file is one month stale (2026-06-28) and manually refreshed; the snapshot is
**twelve months** stale. A live NSE constituent fetch was not attempted (offline report; the
repo documents the NSE bot-wall). The authoritative pre-review action is to refresh both against the
September rebalance — an owner decision, recorded in the binder as D1, because it couples to the
pending baseline re-anchor.
