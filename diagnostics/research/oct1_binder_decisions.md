# Oct-1 binder — decision section (owner doors)

Companion to [system_constitution.md](system_constitution.md). Everything here is **written up, not
acted on**: each item is an owner decision, and every fix is a mid-quarter system change. Remediated
constitution rows are cited with their fix commits in the constitution itself.

Standing counts (unchanged by the audit and the remediation): **screens 11, sealed opens 1,
n_trials 138.** No trials or screens were spent; no forward-wall log was read.

---

## 0. Governance change already landed — gates must read SNAPSHOTS

Constitution **D2** (the record recomputes from inception every Saturday and can silently rewrite
its own past) is now **measured**: `scripts/archive_weekly_snapshot.py` runs in the Saturday cron
after the scorecard and writes a dated, **write-once** snapshot to `results/archive/<as_of>/` —
book, NAV series, closed-trade history, analytics, plus an input fingerprint (OHLCV cache sha256,
membership sha256, index-CSV sha256, engine config) — then diffs against the previous snapshot and
appends a row to `results/archive/drift_log.jsonl` recording **restated / vanished / appeared**
closed trades and the NAV delta.

**Frozen baseline artifact:** `results/archive/2026-07-24/` (flagged `is_baseline: true`) — the
state of the record at remediation time.

**The decision this forces (for the Oct-1 review):** the §10.2 promote/kill gates and the §4 halt
must be evaluated against a **named snapshot**, not the mutable working copy. Recommended wording
for the review: *"the gate reads `results/archive/<first-trading-day-of-October>/`; if that
snapshot's `drift_vs_prev.json` is not clean, the restatements must be attributed before the gate
is read."* `scripts/bhanushali_review_scorecard.py` still reads the working copy — pointing it at a
snapshot is a one-line change deliberately **not** made mid-quarter.

What this does **not** do: it does not make yfinance immutable. That was never the goal — the goal
is that drift is attributable rather than silent.

---

## 1. D1 — universe snapshot refresh policy *(couples to the re-anchor decision)*

**State.** Live trades `config.NIFTY_500`, a hard-coded snapshot dated **2025-07-20**, intersected
with `data/nifty500_membership.csv` (last written 2026-06-29, 500 rows active, sentinel
`to_date = 2030-12-31`). The certified 0094 run used the *corrected* universe (pinned + backfill +
delisted aliases). Post-snapshot index entrants can never signal live; index exits keep trading.

**Why it is loaded.** Finding 0025 measured survivorship bias scaling with holding period, and this
book has **no time cap** (item 2 below) — the maximum-exposure configuration. D1 and B-2's substance
compound.

**Freshly relevant:** the September semi-annual NSE rebalance lands **before** the Oct-1 review.
M7 below quantifies today's gap.

**Doors:** (a) refresh the snapshot + membership on a fixed cadence tied to NSE rebalances;
(b) switch the live universe to `build_universe("union")` so current members are included without
touching the historical file; (c) leave as-is and accept a widening gap. Couples to the pending
baseline re-anchor (CLAUDE.md data-debt note), so it is a quarterly-review-class decision either way.

## 2. B-2 substance — the missing time cap *(docstring half already fixed)*

**State.** Under config P the weekly branch decides stop / blow-off / 44w-SMA runner and returns
**before** any cap check: neither the 13-week cap nor the 52-week backstop the P2 exit carried is
reachable. Holds are unbounded above. The docstring that claimed otherwise was corrected in
`d3b4d5e`-series work; the **behaviour** is untouched, by design.

**Exposure.** Unbounded holds are exactly the configuration where D1's stale-universe survivorship
bias is largest (0025). M2 below reports the realised hold-age distribution.

**Doors:** (a) reinstate the 52-week backstop that silently vanished with the P swap (restores the
documented intent, smallest change); (b) adopt an explicit no-cap policy and delete the card's
`HOLD_DAYS_DISPLAY` fiction; (c) route a cap variant to the forward wall rather than deciding
in-sample. **Recommendation: (a)** — it re-establishes what the decision record already claimed,
without a new lever.

## 3. D3 — the live config is not the certified config *(owner's recorded override)*

**State, restated for the review.** The 0094 run of record (Sharpe 1.132 / 255 trades, DSR 0.89 —
UNDERPOWERED, not certified) is **all-defaults**. Live runs `LIVE_DISCIPLINE` (ext_cap 0.20,
max_risk_pct 0.10, max_notional_pct 0.20; docs/decisions/0009) **and** config-P `LIVE_EXIT`
(docs/decisions/0010), which the code itself records as failing the 2022-26 continuous slice at
**0.91** with a **−39.5%** drawdown, adopted on owner call with sole capital at risk.

No action requested — this is your override and it stands. It is restated so the review does not
read 1.132/255 as this book's pedigree. The golden master now pins both configurations separately,
so the distinction is mechanically enforced rather than remembered.

## 4. Low-rank divergences — one line each

| ID | What | Recommended disposition |
|----|------|------------------------|
| **D6** | Two Grade-A top-5 sets: `grade_a_entries` ranks all signals; the card pipeline filters membership/degenerate bands **first**. At the margin the book reserves a slot it cannot fill while the card promotes a name the book will never hold. | **Fix next quarter** — apply the membership/`entry>stop` filter before ranking, so one A-set exists. Small, but it is the only remaining card-vs-book set mismatch now that D5 is closed. |
| **D7** | Fractional shares: sizing is a float, the owner buys integers. Backtest and paper share the fiction. | **Accept + document.** Flooring would change every historical fill for a bounded, direction-known error (it slightly flatters the record). Revisit only if real capital is deployed. |
| **D8** | A missed/failed Saturday is healed with modeled fills the owner never saw. | **Fix cheaply** — have the archive mark a snapshot whose predecessor is >8 days old as `backfilled`, so gates can exclude weeks the owner could not have traded. Archive infrastructure now exists; wiring is one condition. |
| **D9** | Monitor flags fills on an inclusive band (`lo <= open <= hi`); the engine fills strictly (`lo < open < hi`). | **Fix next quarter** — make the monitor strict. One character; currently a boundary-tick card/book split. |
| **B-3** | The non-member-in-top-5 case inside `grade_a_entries` — the mechanism behind D6. | Resolved by the D6 fix; no separate action. |
| **B-4** | Monitor's `window_open` compares against the **data** as-of date, not today, so a stale feed shows an expired buy window as open. | **Fix next quarter** — compare against today; bounded today by the daily refresh. |

## 5. Menu items surfaced by this remediation (not run)

* **M1 — done.** R94 golden master exists (`tests/test_r94_golden.py`), pinning the frozen 0094 cell,
  the live cell, the B-1 fix diff, and the card arithmetic.
* **M5** (post-tp1 giveback: the stop never moves under config P) and **M11** (mark-to-market
  compounding of the 2% risk base) remain unexamined and are the two highest-value free diagnostics
  left; both are column arithmetic on the existing ledger.
* **M9 / M13 / M14** unchanged from the constitution's ranking.
* **M10** — `NSE_HOLIDAYS` ends 2026-12-25, so the 2027 Jan/Apr review dates cannot be computed
  correctly. **Add the 2027 list at the Oct-1 review** (zero-compute, but it blocks the review-date
  machinery next year).
