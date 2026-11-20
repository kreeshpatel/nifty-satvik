# DRAFT — amendment: the 70/30 blend's volatility target from 15% to 11%

**Status: DRAFT, owner-approved for signing at the January 2027 review. Not in force until signed.** The owner chose 11% on 2026-11-18, **provisional pending the real-price-band re-run of
the stop stress** (Part 3 of `diagnostics/research/2026-11-18_robust_sizing.md`). It becomes an amendment only when the
owner signs and dates it into `forward/amendments/`, at a quarterly review (`skills/strategy-lifecycle` §6). Nothing
in the repo has been changed by this draft: `pipelines/lifecycle/core.py::vol_target_blend` still defaults to 0.15, the
paper record `forward/records/blend_70_30_vt15.csv` still runs at 15%, and the frozen bands
`forward/bands/blend_70_30_vt15_bands_2026-11-13.json` stand.

---

## Amendment 2027-01-__ — blend volatility target 15% → 11%

**What:** the 70/30 momentum/swing blend's volatility target changes from 15% to 11%. Every other part of the
definition is unchanged: daily fixed 70/30 weights, exposure = min(1, target / 20-session realised volatility lagged
one session), the rest in cash at the record's cash rate. One change for this strategy at this review (§6).

**Why (the drawdown rule, and only the drawdown rule):** the mission bars a drawdown deeper than −25%. On the
2019-03-01..2024-06-28 window, the blend's 156-week stationary-bootstrap p95 drawdown at 15% is 29.3% / 28.7% / 27.0%
at mean blocks 8 / 13 / 26 weeks (`diagnostics/research/explore/2026-11-18_blend_drawdown_sizing.json`). The highest
whole-percent target whose p95 is at or under 25% at the most conservative block (8) is **11%: p95 23.35%**, clearing
at all 10 seeds of the independent replica; 12% (25.03%) misses at every seed by 0.04–0.6pp.

**What it costs** (same window, same file and `2026-11-18_risk_matched_benchmark.json`):

| target | CAGR | Sharpe raw | Sharpe excess of 6.5% | 156w p95 DD (block 8) |
|---|---|---|---|---|
| 15% (now) | 29.20% | 1.801 | 1.386 | 29.33% |
| 11% (proposed) | 25.14% | 1.932 | 1.417 | 23.35% |

−4.06pp CAGR. The excess-return Sharpe is essentially unchanged (+0.03), so this is a drawdown purchase, not a
risk-adjusted improvement.

**What the change does NOT establish:** the risk-matched comparison at 11% on the same window puts the blend level
with the Nifty Midcap150 Momentum 50 TRI run through the identical rule (excess Sharpe 1.417 vs 1.411; paired
difference on common dates −0.002, 5–95% CI −0.53 to +0.46). The mission's "beats the index" is not shown by the
backtest at either target; only the forward record can show it.

**Condition precedent (the reason this is provisional):** the stop-stress re-run with NSE's own band-hitter and
price-band files for 2019–2024H1 must not move the 11% blend's 156-week p95 above 25% at block 8. If it does, this draft
is re-derived at the highest target that clears, by the same rule, before signing.

**Mechanics at signing (§6):**
1. `pipelines/lifecycle/update_records.py` passes `target=0.11` to `vol_target_blend` from the change date.
2. The forward record **continues**; the change date is marked in its `note` column. The file name keeps `vt15` (records
   are append-only, ADR-0018); the stage log `forward/lifecycle/stages.json` gets a dated entry.
3. New frozen bands `forward/bands/blend_70_30_vt11_bands_<date>.json` built by `pipelines/lifecycle/build_bands.py` for
   the changed version; the vt15 bands stay.
4. `CLAUDE.md` mission line: "at a 15% volatility target" → "at an 11% volatility target".
5. The 26-week promotion clock **continues from 2026-11-13** (owner, 2026-11-18). From the change date, status is
   read against the vt11 bands, rescaled so that week 0 is the change date.
6. Capital rule (owner, 2026-11-18): the blend stays a **forward challenger**. It receives capital only if its forward
   record beats the Nifty Midcap150 Momentum 50 TRI **after tax**.

**Owner decision 2026-11-18:** to be signed at the January 2027 review. The condition precedent is met
(real-band p95 23.48% ≤ 25%, `diagnostics/research/explore/2026-11-18_circuit_lock_real_bands.json`).

**Signed:** ____________ **Date:** ____________
