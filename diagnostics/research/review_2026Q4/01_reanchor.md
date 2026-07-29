# §1 Corrected-universe re-anchor

**Pre-committed criterion (CLAUDE.md, the 0025 data-debt clause, verbatim):**
> "Finding 0025 measured the bias: **it scales with holding period** (−0.04 Sharpe tight-stop vs −0.18
> wide-stop swing configs) → the 63d-hold **baseline_v1 0.667 is exposed in the same direction; its
> corrected re-run is unblocked but re-anchors the pin → owner/governance decision (quarterly-review
> class)."

**Machinery:** `scripts/run_corrected_anchor.py` (full window, September). Smoke-proof 2026-07-29;
the harness's pinned arm reproduces `baseline_v1` (0.667 / 15.47 / −46.3), so it is validated against
the anchor of record.

**RESOLVED TO A POINT ESTIMATE 2026-07-29 (owner-approved remediation + harvest executed).**
The bounds below are RETIRED. On the re-run with the backfill flowing through the REAL gate (no
waiver anywhere) — `run_corrected_anchor.py --resolved`, report `lh_anchor_resolved.json`:

| arm (full window, real gate) | Sharpe | CAGR % | MaxDD % | after-tax % |
|---|---|---|---|---|
| pinned (`baseline_v1`) | 0.667 | 15.47 | −46.3 | 12.34 |
| corrected AS-IS | 0.667 | 15.47 | −46.3 | 12.34 |
| corrected + alias-aware | 0.662 | 15.14 | −45.2 | 11.93 |
| **corrected + alias + backfill** | **0.737** | **17.11** | **−49.6** | **13.49** |

**POINT ESTIMATE: ΔSharpe +0.070 · ΔCAGR +1.64pp · ΔMaxDD −3.3pp** (retired bounds: +0.202 naive,
+0.024 dedup). The correction is **mixed, not one-signed**: Sharpe and CAGR improve, drawdown gets
**worse** (−46.3 → −49.6). A re-anchor would move the headline up and the risk number up too.

The gate is now doing real work: **67 of 104** recovered names have D/E after resolution; **21 passed
into the book**, **46 had data and were REJECTED** — the levered failures are being excluded on their
balance sheets rather than on absence, which is exactly what the flag asked for. Note the alias-aware
arm alone is *slightly negative* (0.662): admitting the 13 renamed-but-alive companies on real data
does not help by itself, so "more names" was never the mechanism.

**Residual coverage limit (must be stated in the memo):** 37 of 104 still have no vendor data (20 no
page, 12 empty pages, plus non-harvest targets) and remain gate-excluded. The point estimate is
therefore conditioned on 67/104 coverage, not a complete correction.

---

**Original flag, for the record — it did NOT close on the bracket:** The LH-identical observation
was real and is a data-coverage artifact, not a no-op: only 2 of the 104 recovered names carry any
fundamentals rows and only 1 a non-null D/E, so the solvency gate drops all of them for want of data
rather than on economics. The pre-committed bracket (`--bracket`, full window,
`lh_solvency_bracket.json`): **(a) corrected AS-IS 0.667 == pinned exactly; (b) gate-waived 0.869
(ΔSharpe +0.202, 197/1,373 trades, 788 name-weeks); (c) gate-waived after removing duplicate entities
0.691 (ΔSharpe +0.024)**. Both readings sit outside the ±0.02 close-the-flag band and the book-entry
count is far from trivial → **work order issued:
[lh_fundamentals_backfill_work_order.md](../lh_fundamentals_backfill_work_order.md)**, awaiting owner
sign-off for an August harvest feeding this memo.

One thing September must carry from that diagnostic:
- **Direction is not what 0025 predicts on Sharpe.** The correction moves Sharpe/CAGR *up* because
  the recovered set mixes failures with PSU-bank amalgamations and ordinary M&A/rename exits —
  delisting is not a synonym for failure. It moves **drawdown the way 0025 predicts** (worse). Any
  memo sentence claiming the correction "reduces" or "inflates" the record uniformly is wrong.

**RETRACTED (2026-07-29):** an earlier readout in this stub claimed the corrected universe
double-counts 16 companies and that `delisted_alias_map.json` held only 2 entries. **Both were
wrong.** The map holds **17** entries (the earlier count read the container, `_readme` + `aliases`).
The byte-identical pairs are those 17 aliases materialized deliberately (old symbol → successor's
series). `diag_alias_census.py` settles it: a constant-ratio scan finds **17 pairs, 17 known, ZERO
novel** (map complete), and PIT membership windows are **disjoint for 17/17**, so one company can
never occupy two slots. No double-counting exists; no re-cut was performed. The +0.178 previously
attributed to "contamination" was the same data-coverage conflation applied to renamed-but-alive
companies, and is now handled properly by the alias-aware fundamentals join.

## Swing-record alias census (Phase 2, 2026-07-29) — no decision item found

Read-only check of whether the certified 0094 record was damaged by the alias materialization
(`diag_swing_alias_census.py`, report `swing_alias_census.json`):
- The record **reproduces exactly: 1.132 Sharpe / 255 trades.**
- **Zero concurrent holdings** of any alias pair. Only ESSELPACK/EPL ever both traded, at different
  times. The record never held one company in two slots.
- A naive re-cut (dropping alias old-symbols) would **cost −0.158 Sharpe** (1.132 → 0.973) by
  deleting legitimate PIT history under the old name. **The re-cut was therefore not performed** —
  it would destroy real exposure to fix a problem that does not exist.

No re-certification, no golden-master change, no live change. Nothing here escalates to September
beyond the record that it was checked and came back clean.

**EVIDENCE (September fills — memo-of-record numbers are September's FRESH runs; the above is
methodology evidence):**
- [ ] full-window anchor table re-run fresh (pinned vs corrected vs corrected+backfill)
- [ ] trade diff + recovered-name attribution
- [ ] **owner decision: re-anchor the pin to 0.737/−49.6, or keep 0.667/−46.3 with a stated caveat**
- [ ] decide whether the alias-aware fundamentals join graduates from harness-side composition into
      `nq/**` (it currently lives in `run_corrected_anchor.resolved_store`; making it the engine's
      behaviour is an engine change and needs its own golden-master check)
- [ ] backfill artifact: `data/fundamentals_pit_backfill_20260729.pkl` is under the repo's `/data/*`
      ignore (cloud-only data convention) — regenerate via `harvest_fundamentals_backfill.py` or
      attach to the dataset release before the memo run
