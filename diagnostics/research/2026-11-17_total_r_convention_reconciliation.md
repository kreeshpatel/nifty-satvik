# 2026-11-17 — Reconciling the 650.2R anchor with the 260.44R replay

**Correction, first.** Two claims made earlier today about this gap were wrong and are withdrawn here, not edited
away:

- The independent re-derivation reconstructed the gap as *"650.2 = realised R plus mark-to-market on 84 open
  runners"*. **It is not.** Both ledgers mark the same 84 positions at the cut, identically.
- The artifact audit (`2026-11-17_artifact_audit.md`) filed this under *"open trades counted at the cutoff — inside
  the 650.2R anchor itself"*. Open trades **are** inside the anchor, and that is still worth stating, but **they are
  not the source of this gap.**

**The whole 389.751R gap is one trade.** `VMART`, entered 2019-05-06, whose initial stop sat ₹0.05 below the entry.

Owner request 2026-11-17, taken as the priority. Analysis only: no live change, no trial, no screen row, no sealed
read. Reproduce: `python pipelines/diagnostics/reconcile_total_r_conventions.py` →
`2026-11-17_total_r_convention_reconciliation.json`.

## The two ledgers

| | A — the path that produced 650.2R | B — the raw engine ledger |
|---|---|---|
| entry point | `diag_loss_diagnosis_2026_11.build_A().run(uncapped=True)` | `nq.lab.runs.replay({"start": "2019-01-01", "uncapped": True})["ledger"]` |
| extra filter | **`(entry − stop0) / entry >= 0.005`** — `pipelines/diagnostics/diag_loss_diagnosis_2026_11.py:204` | none |
| trades | 525 (441 closed, 84 `eos`) | 526 (442 closed, 84 `eos`) |
| engine, window, membership, exit blocks | identical | identical |

Join: outer, on `(ticker, entry_date)`, no duplicate keys — **525 in both, 1 only in B, 0 only in A**.

## Every trade differing by more than 0.05R

Exactly one, at tolerance 0.05R:

| ticker | entry date | in A | in B | A: exit date / price / reason / R | B: exit date / price / reason / R | ΔR |
|---|---|---|---|---|---|---|
| VMART | 2019-05-06 | **absent** | present | — | 2019-05-13 / 644.24 / `stop_part` / **−389.751** | **+389.751** |

Its initial risk was **₹0.05 per share**, 0.0074% of the ₹676.74 entry (stop 676.69). The position lost **₹8,040.72**
— an ordinary small loss in rupees — but dividing it by a ₹0.05 risk basis reports it as **−389.8R**. A's filter
exists to drop exactly this, and dropping it is why A's total is higher.

## The gap, grouped by cause

| cause | trades | ΔR |
|---|---|---|
| degenerate risk basis: initial stop inside 0.5% of entry, dropped by A's filter | 1 | **+389.751** |
| open at the cut, valued differently | 0 | 0.000 |
| same trade, different exit rule fired | 0 | 0.000 |
| same trade, same exit rule, different R | 0 | 0.000 |
| present only in A | 0 | 0.000 |
| **explained** | **1** | **+389.751** |
| **residual** | | **0.000** (exact; the script asserts it) |

650.191 − 260.440 = 389.751. The buckets add up exactly because there is only one of them.

## Open positions are valued the same way in both, and the same way live does it

- **Engine:** every position still open at the last bar is force-closed at that bar's close and booked with reason
  `eos` — `scripts/run_bhanushali_weekly_rank.py:1464-1479`. This runs in **both** ledgers, which is why both report
  84 `eos` trades. The published "84 open" in the loss diagnosis is a **label** (`reason == "eos"`), not a different
  valuation.
- **Live:** `scripts/run_bhanushali_cron.py:1213-1226` (`_trade_r`) books closed trades at their booked R and marks
  open positions at the last close as `realized_r + frac_left × (cur − entry) / risk0`.
- **Therefore:** **mark-at-cut is what live does.** On this question the two methods do not differ, and neither is
  "more live" than the other.
- On the *other* difference, the 0.5% filter: **live applies none.** There is no minimum stop-distance guard in
  `scripts/run_bhanushali_cron.py` (the only `0.005` there is `ADJ_JUMP` at :834, a corporate-action detector), so
  the live tracker would book a VMART-like trade and would report its R as −389.8 as well. The filter is a
  **research convention**, defensible because an R computed on a ₹0.05 basis is not a risk-adjusted anything — but it
  is a convention, and it was never stated beside the anchor.

## Both conventions, both populations — the numbers to quote from now on

| ledger | population | trades | closed | marked `eos` | **total R, closed-only** | **total R, marked-at-cut** | net P&L closed-only | net P&L marked-at-cut |
|---|---|---|---|---|---|---|---|---|
| A | filtered (stop ≥ 0.5%) | 525 | 441 | 84 | **+273.929** | **+650.191** | ₹46,89,601 | ₹1,02,88,985 |
| B | unfiltered | 526 | 442 | 84 | **−115.822** | **+260.440** | ₹46,81,561 | ₹1,02,80,944 |

Read the rupee columns beside the R columns: the two populations differ by **₹8,041** of P&L and by **390R**. That is
the whole case for saying that **total R is not a safe headline on this book** — one trade with a degenerate risk
basis moves it by more than half the published anchor, while moving the money by 0.08%.

## What changes because of this

1. **`docs/references/plausibility_anchors.md` now states the convention of every anchor** (done in this change).
2. **Every total-R figure is reported both ways from now on** — closed-only and marked-at-cut — per the owner's
   instruction, with the population filter named.
3. **Rule 3:** a fresh sub-agent re-derives the closed-only totals from the specification alone; both sets of numbers
   are reported in the PR.
4. The audit entry that filed this gap under "open trades at the cutoff" is corrected above. The *separate* fact that
   84 of 525 trades are marked at the cut inside the 650.2R anchor still stands, and the table above now gives the
   closed-only figure for anyone who wants it without the marks.

## Limitations

One window (2019-01-01..2024-06-28). The reconciliation is exact for these two paths; other diagnostics in the repo
may use yet other conventions (capped vs uncapped, different filters), and this file does not survey them. The
conventions table above covers the uncapped book only — the capped ₹10L book is a separate population again.
