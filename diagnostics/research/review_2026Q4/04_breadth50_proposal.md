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

**Amendment 2026-08-16 — owner adds a third watched arm, SW-accum.** Following finding **0139**
(delivery's temporal *accumulation* composite is the real signal, IC t=6 on the broad universe, with
this breadth-50 book named as its home), the owner elected to add a third arm rather than change the
frozen SW. `nq/research/breadth50.build_books(..., accum=)` now emits `w_sw_accum`, tilted by the same
frozen shape (0.5 + 1.5·pctile, ×0.5 on the event flag, clipped) but ranked by the 0139 accumulation
composite (definition frozen from `pipelines/diagnostics/diag_delivery_accumulation.py`) instead of
the 0118 dlv_med21 level. The watched comparison is now **EW vs SW vs SW-accum**; the EW-vs-SW-accum
spread forward-tests 0139 directly, zero in-sample fitting. Construction validated (3-arm weights sum
to 1, event names down-weighted, golden master byte-identical, module still wired nowhere).

**Frozen params (per the audit note): rebalance anchor = weekly (W-FRI, top-50 by weekly CRS);
estimation lookbacks = dlv_med21's 21d (SW) and the 0139 composite's trailing windows (SW-accum,
52/21/8-week per its z-components). Stated before logging; a forward book is not anchor-swept.**

**Forward logger BUILT (2026-08-16).** `scripts/run_breadth50_paper.py` logs the three arms' realized
weekly NAVs from a fixed inception FORWARD only (empty until post-inception bars accrue, like the swing
paper book), and — per the book's stricter discipline — **reports no spread and no arm comparison**
(the verdict is the wall/review's to read, never the logger's, never in-sample). Structurally validated
(`--validate`: 78 weeks, weight-integrity True every week, returns finite, 3 arms present; no
performance emitted). Still wired into NO cron: activation = the two boxes below.

**ACTIVATED — owner started the forward clock 2026-08-16 (the §4 amendment taken early).** The 3-arm
watched book (EW / SW / SW-accum) is registered with a **fixed inception of 2026-08-16**, frozen and
forward-only: `run_breadth50_paper.py` appends only W-FRI weeks ≥ the inception that already have a
following realized return, so no past week can enter the record (no backfill by construction). The
inception is pinned in the logger and here; it does not move. Owner's rationale: the design is frozen
and validated, so an earlier start buys more forward evidence by the review at no fitting cost.

**EVIDENCE:**
- [x] owner sign-off — **signed 2026-08-16**, 3-arm ask (EW / SW / SW-accum), clock started early
- [x] inception date fixed — **2026-08-16** (registered here + in `run_breadth50_paper.py`)
- [ ] weekly cron hook + the pinned vendor artifacts (delivery / earnings / options-OI) fetched on the
      runner — the operational plumbing (same class as the wall's factor build); until wired, the log
      accrues from the first weekly run that has the data

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
