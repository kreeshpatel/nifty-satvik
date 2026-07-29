# §1 Corrected-universe re-anchor

**Pre-committed criterion (CLAUDE.md, the 0025 data-debt clause, verbatim):**
> "Finding 0025 measured the bias: **it scales with holding period** (−0.04 Sharpe tight-stop vs −0.18
> wide-stop swing configs) → the 63d-hold **baseline_v1 0.667 is exposed in the same direction; its
> corrected re-run is unblocked but re-anchors the pin → owner/governance decision (quarterly-review
> class)."

**Machinery:** `scripts/run_corrected_anchor.py` (full window, September). Smoke-proof 2026-07-29;
the harness's pinned arm reproduces `baseline_v1` (0.667 / 15.47 / −46.3), so it is validated against
the anchor of record.

**FLAG RESOLVED 2026-07-29 — it does NOT close; a backfill is required.** The LH-identical observation
was real and is a data-coverage artifact, not a no-op: only 2 of the 104 recovered names carry any
fundamentals rows and only 1 a non-null D/E, so the solvency gate drops all of them for want of data
rather than on economics. The pre-committed bracket (`--bracket`, full window,
`lh_solvency_bracket.json`): **(a) corrected AS-IS 0.667 == pinned exactly; (b) gate-waived 0.869
(ΔSharpe +0.202, 197/1,373 trades, 788 name-weeks); (c) gate-waived after removing duplicate entities
0.691 (ΔSharpe +0.024)**. Both readings sit outside the ±0.02 close-the-flag band and the book-entry
count is far from trivial → **work order issued:
[lh_fundamentals_backfill_work_order.md](../lh_fundamentals_backfill_work_order.md)**, awaiting owner
sign-off for an August harvest feeding this memo.

Two things September must carry from that diagnostic:
- **Direction is not what 0025 predicts.** Both waiver arms move the LH book *up*, because the
  recovered set mixes failures with PSU-bank amalgamations and ordinary M&A/rename exits. The bound
  is an upper limit (it assumes every recovered name clears D/E < 1.5 — exactly what the levered
  failures would break), never a point estimate.
- **A second defect, decision-shaped, not fixed:** the corrected universe **double-counts 16
  companies** (old symbol + current symbol, byte-identical series; e.g. PGHL=MERCK, ETERNAL=ZOMATO).
  17 of 104 "recovered" tickers are duplicates, 87 genuine, and those 26 duplicate trades carry
  +0.178 of (b)'s +0.202. `delisted_alias_map.json` has only 2 entries. Whether the corrected
  universe is re-cut is a governance call on the pin.

**EVIDENCE (September fills):**
- [ ] full-window anchor table (pinned vs corrected, both books)
- [ ] trade diff + recovered-name attribution
- [ ] owner decision: re-anchor the pin / keep + caveat
