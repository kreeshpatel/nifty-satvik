# §4 breadth-50 watched-pair amendment ask

**The proposal (breadth_feasibility_census.md §3, verbatim):**
> "**Two watched variants — the comparison IS the experiment:** (a) **EW**: equal-weight 2%/name, the
> no-information baseline; (b) **SW**: same names, weights tilted by the banked signals — dlv_med21
> percentile (up-weight) and known-event-within-14cd (down-weight), tilt bounded to 0.5×-2× of equal
> weight, definitions frozen from 0118/0120 verbatim. The EW-vs-SW forward spread isolates the
> signals' portfolio-expressed value with zero in-sample fitting — forward evidence by construction."

**Machinery (built cold, wired nowhere):** `nq/research/breadth50.py` + `scripts/dry_run_breadth50.py`
— dry-run validated 2026-07-29 (50 names, both weight vectors sum to 1.000000, tilt bounds asserted,
PIT joins lagged >= 0 with the 10d staleness cap, all event flags pre-announced).

**PROVENANCE.** The dry run reads three mortal vendor artifacts, now pinned in
[`dataset-pin-20260729`](https://github.com/kreeshpatel/nifty-satvik/releases/tag/dataset-pin-20260729):
`options_oi_pit.parquet` (`d675a451…`), `_delivery_raw.parquet` (`7a20ec8f…`), `_earnings_raw.parquet`
(`a2825cd7…`). Fetch commands and full hashes: [§1 provenance block](01_reanchor.md). Do not trust
local `data/` — fetch and `sha256sum` first.

**EVIDENCE (September fills):**
- [ ] owner sign-off / decline at the Oct-1 amendment slot
- [ ] if signed: logging wiring + inception date

---

## Audit note (2026-07-31, verification audit 2026Q3) — name your rebalance anchor and vol lookback

Finding 0115's blend headline could not be mechanically replicated because the ERC **vol lookback was
never stated**; the audit recovered it (126d) and committed
`scripts/build_two_sleeve_blend.py` as the producer of record. The reproducible figure is
**Sharpe 1.237 / MaxDD −33.04% / worst year +5.62%** (published 1.22 / −33% / +5.6% retained as
as-measured-then).

**This spec inherits the question.** Before the EW/SW pair is logged, §4 must state explicitly:
(a) the **rebalance anchor** (which calendar boundary, and whether results are anchor-robust), and
(b) any **estimation lookback** the weighting uses. The audit's anchor sweep found the two-sleeve
blend stable across 0–6 week offsets (Sharpe spread 0.023) — breadth-50 should be able to say the
same, or say why not.
