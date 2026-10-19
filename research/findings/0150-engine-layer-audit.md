# 0150 — Engine layer audit: the Grade-A rank adds about nothing, and the live A-set wastes seats

**Class:** measurement, one pre-registered family, screen ledger row 23. **No trial.** Standing counts:
**screens 23 · sealed opens 3 · n_trials 2.** Pre-registration:
`diagnostics/research/preregistry/0150-engine-layer-audit.md` (committed `a6a5868`, before the diagnostic
existed). Reproduce: `python pipelines/diagnostics/diag_engine_layer_audit_0150.py` →
`diagnostics/research/engine_layer_audit/result.json`. Owner question: "is our A-grade rating on point?"

**Window:** train 2019-01-01..2024-06-30, prices cut before the engine saw them (last bar 2024-06-28),
the live configuration **with point-in-time index membership**.

## Answer

**No, not as configured.** Two separate things are true, and the red-team separated them:

1. **The CRS rank adds about nothing.** Read as a rating of tradeable signals, it does not order their
   outcomes, and a Grade-A book built from tradeable names performs about like random top-5 picks.
2. **The live Grade-A set also wastes seats.** It ranks *all* signals, so roughly a quarter of its top-5
   slots go to names the book cannot buy (non-members, degenerate bands), which are refused at fill.
   Ranking only buyable names recovers about **+0.25 Sharpe**.

## Part 1 — the rank as a rating (uncapped, every filled signal, 1,367 trades, 238 weeks)

| statistic | value | 95% CI (week-clustered) |
|---|---|---|
| within-week rank IC | **−0.004** | −0.08 … +0.07 |
| ranks 1–5 minus the rest | **+0.08R** | −1.03 … +0.66 |
| mean R by rank | 1–5 **+1.29**, 6–10 **+1.56**, 11+ **+1.15** | not monotone |
| 2R hit rate vs first-passage null | top-5 40.5% vs 35.7%; rest 35.8% vs 35.6% | gap not significant |

Sub-periods disagree in sign (2019–21 edge −1.41R, 2022–24H1 +1.04R; both CIs span zero). **Reading as
pre-committed: NOT DISTINGUISHABLE FROM NOISE.** Corrections from the red-team, folded in:

- Ranking is among *filled* trades, grouped by fill week. That is the rank of **tradeable** signals, not
  the live Grade-A rank, which ranks every signal including ones the book cannot buy. This part measures
  CRS's ordering power, not the live A-set.
- 16% of trades are open at the cut and carried at their mark; heavy-tailed runners dominate the means and
  widen the CI. The honest reading is **underpowered**, not "proven flat".

## Part 2 — layers (live capped ₹10L book, Sharpe 1.025)

| arm | Sharpe | note |
|---|---|---|
| live | **1.025** | control |
| Grade A ranked after dropping unbuyable names (red-team run) | **1.275** | the seat-waste fix |
| no Grade-A gate (all grades compete) | 1.266 | |
| random top-5 per week, 20 seeds | mean **1.30**, max 1.72 | live at the 15th percentile (3 of 20 below) |
| no extension cap | +0.22 vs live | single-path difference |
| base exit instead of scaled | −0.06 vs live | noise |

What the numbers support, after the red-team:

- **The seat waste is real and has a mechanism.** 72.9% of live Grade-A picks are index members on their
  date, against 77.7% of all signals. Filter-before-rank (`grade_a_entries(..., filter_before_rank=True)`,
  decision D6, gated off) lifts the book from 1.025 to 1.275, level with the no-gate book.
- **CRS ≈ random, not worse than random.** With seats no longer wasted, the book sits near the random mean.
  The "15th percentile" rests on 20 seeds and is soft (binomial range roughly 3–35%).
- **The extension-cap and exit differences are single-path numbers** with no noise estimate, below the
  path-noise scale typical here. They are not layer findings.
- A plausible second cause of waste, untested: CRS favours the most-extended names (CRS_DISSECTED:
  "relative strength is extension"), and the 20% extension cap refuses some of them at fill.

Every Δ here is inside the ≈ 0.59 ΔSharpe half-width (n_eff ≈ 37).

## Why this differs from CRS_DISSECTED

CRS_DISSECTED placed the CRS portfolio at the 99–100th percentile of random draws.

**CORRECTION 2026-10-19.** The first version of this paragraph said CRS_DISSECTED ran with no index
membership. That was asserted, not checked, and it is wrong: `diag_crs_dissect.py` passes
`load_membership()` (lines 57, 66, 77 in its last committed version). The differences that do hold are
the exit (the older P2 exit, not the live scaled exit P), the window (2017 to 2026, which includes the
2017–18 years this programme does not trust and runs into the sealed 2024H2+ slice), and its own split
(skill inside the noise in 2017–21, beating every draw in 2022–26). Which of those explains the gap to this
study is **not established**. The two results should be read as disagreeing under different exits and
windows, not as one being superseded by a membership fix.

## What this licenses, and what it does not

- **Nothing changes live from this study.**
- **Strongest concrete candidate found:** rank only buyable names (D6, filter-before-rank). It has a clear
  mechanism and a +0.25 Sharpe train-window difference, but it changes which trades the book takes in every
  historical week, so it is a live-rule change: a **pre-registered trial for the 2027-01-01 review**, judged
  once on the sealed slice, not adopted from this train-window number.
- **For the rating question:** treat Grade A as a seat-allocation rule, not a quality score. A card's
  "Grade A" label should not be read as "this trade is better".
- Below the resolution floor, and not proposed: removing the extension cap, changing the exit.
