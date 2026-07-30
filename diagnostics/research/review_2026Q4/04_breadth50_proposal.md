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
