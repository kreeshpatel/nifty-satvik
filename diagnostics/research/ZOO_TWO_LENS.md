# The zoo question — STAGE1 in both units, with power

**Date:** 2026-08-06 · **Class: MEASUREMENT.** Zero trials, zero screens.
**Counts frozen: screens 16 · sealed opens 1 · n_trials 138.**
Producer: [`scripts/diag_zoo_two_lens.py`](../../scripts/diag_zoo_two_lens.py) ·
evidence: `foundation_audit_2026Q3/zoo_two_lens.json`.

> **NO PROPOSAL IS MADE HERE.** This delivers numbers and confounds. Nothing is recommended,
> nothing is authorised, and the collision rules in `program-laws` are untouched.

**Why it could only be done now:** the substrate carried `R` but not `net_pnl` / `stt_paid` /
`half_px`, so this table could only ever be read in R. Those columns are now carried
(`build_substrate.py`, 2026-08-06; determinism guard re-passed at 1.1319 / 255).

---

## READ THE CONFOUNDS FIRST

1. **The substrate runs `P2_EXIT`, not the frozen ladder.** `no_time_cap=True`,
   `wk20_trail_pct=0.04`, `blowoff_arm_r=2.5`. The run of record uses the **13-week time cap** and
   the default ladder. **These numbers are not the record's engine**, and a per-origin ranking under
   one exit does not transfer to the other.
2. **The substrate's `box` / `sr_pivot` are a different construction from E10's ad-hoc run.**
   Comparing these figures to E10's is comparing two different detectors.
3. **Origins are assigned by masking priority, not independently.** The zoo detectors are additive
   with `& ~wsig`: `touch44` has first claim on every name-week and each later origin sees only what
   the earlier ones left. **The cohorts are not exchangeable**, so a difference between them is
   partly a difference in what was still available to detect.
4. **This is the UNCAPPED per-signal population**, and the portfolio-level version of exactly this
   question has already been answered twice at **trial cost**: STAGE4 found **no sleeve
   configuration beats touch-only** under the cap, and ROUTER found per-branch exits **lose**
   (0.71 vs 1.29 on the 2022-26 slice). A population gap is not a portfolio gap, and the programme
   has paid to learn that on this exact question.

---

## The table — both lenses, bootstrap CIs on the mean (10,000 draws, seed 20260806)

| setup | N | mean R | R 95% CI | mean equity % | equity % 95% CI | ΔR vs touch44 | ΔR excl. 0 | Δequity% | Δeq% excl. 0 | **both** |
|---|---:|---:|---|---:|---|---:|---|---:|---|---|
| **cup_handle** | 195 | 0.696 | [0.446, 0.950] | **1.492** | [0.964, 2.038] | **+0.365** | **yes** | **+0.758** | **yes** | **✔** |
| ascending_base | 106 | 0.626 | [0.325, 0.927] | 1.378 | [0.731, 2.011] | +0.295 | no | +0.644 | no | ✘ |
| sr_pivot | 57 | 0.557 | [0.038, 1.083] | 1.329 | [0.212, 2.491] | +0.226 | no | +0.596 | no | ✘ |
| **box** | 543 | 0.619 | [0.480, 0.757] | **1.308** | [1.015, 1.604] | **+0.287** | **yes** | **+0.574** | **yes** | **✔** |
| **double_bottom** | 502 | 0.598 | [0.473, 0.723] | **1.243** | [0.986, 1.504] | **+0.266** | **yes** | **+0.509** | **yes** | **✔** |
| trend_pullback | 1,167 | 0.338 | [0.168, 0.501] | 0.818 | [0.459, 1.173] | +0.007 | no | +0.085 | no | ✘ |
| **touch44** *(base)* | 1,720 | 0.331 | [0.214, 0.450] | 0.733 | [0.476, 0.988] | — | — | — | — | — |
| flag | 16 | — | *N < 20, not bootstrapped* | | | | | | | |
| vcp | 15 | — | *N < 20, not bootstrapped* | | | | | | | |

---

## The answer to the question as asked

**Do cup / box / double_bottom / ascending_base beat touch44 at population level, with adequate
power, in both lenses?**

- **cup_handle — YES.** ΔR +0.365 and Δequity +0.758pp, both CIs exclude zero.
- **box — YES.** ΔR +0.287, Δequity +0.574pp, both exclude zero.
- **double_bottom — YES.** ΔR +0.266, Δequity +0.509pp, both exclude zero.
- **ascending_base — NO.** Point estimates are comparable (+0.295 / +0.644) but **N = 106 and both
  CIs straddle zero.** Underpowered, not disconfirmed — the same distinction
  [`POWER_READJUDICATION.md`](POWER_READJUDICATION.md) draws.

**Three of four clear both lenses with power.** Ranked by the equity lens: **cup_handle > box >
double_bottom.**

### The two lenses agree, which is itself a result

The ordering by mean R and the ordering by mean % of equity are **identical across all seven
bootstrapped setups**, and every Δ that excludes zero in one lens excludes it in the other. This is
what [`UNIT_RESOLUTION.md`](UNIT_RESOLUTION.md) predicts: on a risk-parity sizer, equity return
= R × 2% exactly, so the two lenses cannot disagree except through cost drag and the half-credit.
The zoo table is a live confirmation of that identity on a different exit regime and a different
population.

---

## What this is not

- **Not evidence of a portfolio-level edge.** Confound 4 is not a caveat, it is a measured result:
  STAGE4 and ROUTER both tested this at portfolio level and both lost. Whatever is true of these
  cohorts per signal has already failed to survive the cap twice.
- **Not comparable to the run of record**, which uses a different exit (confound 1).
- **Not a clean cohort comparison**, because origin assignment is priority-masked (confound 3).
- **Not a proposal.** Per the standing instruction, if the owner elects to pursue this it becomes a
  **single ranked candidate** requiring a **fresh, population-primary pre-registration** that must
  pass Gate 0 registry confrontation like anything else — and that confrontation will have to
  address STAGE4 and ROUTER head-on, because they are trial-priced and adjacent.

## Cross-references

`research/substrate/STAGE1*` · `research/substrate/STAGE4_sleeves.md` ·
`research/substrate/ROUTER_RESULT.md` · `UNIT_RESOLUTION.md` · `POWER_READJUDICATION.md`
