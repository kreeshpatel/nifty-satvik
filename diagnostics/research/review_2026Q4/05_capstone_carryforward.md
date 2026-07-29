# §5 External-data campaign carry-forward

**The synthesis (external_data_campaign_capstone.md, verbatim):**
> "**Population/cohort information is real; this book's decision margins — selection, timing, exit —
> cannot express it; worse-than-average is still positive-EV.** Corollaries now standing: the
> activation-bound gate is mandatory before any usage trial; label screens are serialized and priced
> in the ledger; sealed opens are priced like any reuse."
> "What would have to change for the banked assets to find a consumer: a structurally different book
> shape — one whose decision points CAN express population-level quality gradients"

**PROVENANCE.** The banked delivery + earnings datasets are pinned in
[`dataset-pin-20260729`](https://github.com/kreeshpatel/nifty-satvik/releases/tag/dataset-pin-20260729)
(`_delivery_raw.parquet` `7a20ec8f…`, `_earnings_raw.parquet` `a2825cd7…`). The forward accumulator
feeds (`results/bulkblock_forward.csv`, `results/ratings_forward.csv`) are append-only and committed —
cite the commit, not the working copy. Full table: [§1 provenance block](01_reanchor.md).

**EVIDENCE (September fills):**
- [ ] accumulator health (scripts/diag_accumulator_health.py — August's report attached)
- [ ] banked-asset inventory confirmation (delivery, earnings; bulk/block forward-only; ratings raw)
- [ ] the breadth-50 decision (§4) as the named consumer-shape answer
