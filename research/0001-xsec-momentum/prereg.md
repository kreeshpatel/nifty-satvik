# Pre-registration 0001 — Cross-sectional momentum, Indian midcaps

**Status:** PRE-REGISTERED — written and committed **before** the run
**Date:** 2026-08-07
**Trial count:** `n_trials` 0 → 1, incremented **before** execution
**Design charter:** `docs/MOMENTUM_ENGINE_DESIGN.md`

---

## 1. Hypothesis

> A monthly-rebalanced, equal-weight book of the top-30 midcap names ranked by NSE's Normalized
> Momentum Score earns a positive risk-adjusted return **over and above a random selection drawn
> from the same universe at the same turnover**, net of the full Indian cost and tax stack.

The comparator is deliberately the **random control**, not zero. A long-only book in a rising market
makes money by existing; the only question worth asking is whether the *ranking* contributes
anything. Equal-weight passive ownership is reported alongside as the economic benchmark.

## 2. The book — every parameter fixed here

| | |
|---|---|
| universe | PIT Nifty-500 membership → `MID` size band (turnover rank 101-250) |
| screens | turnover ≥ ₹5cr · history ≥ 252 sessions · price ≥ ₹10 · circuit proxy |
| signal | `MR12 = ret(252, skip 21) / σ_ann`, `MR6 = ret(126, skip 21) / σ_ann` |
| score | `Z12`, `Z6` cross-sectionally → `WAZ = 0.5·Z12 + 0.5·Z6` → `NMS` |
| selection | top **30** by NMS |
| buffer | hold until rank falls past **1.5 × 30 = 45** |
| weight | equal, capped **5%** per name |
| cadence | **monthly**, last session |
| exits | ranking buffer only — **no stop, no target** |
| execution | rank at close T, fill at **T+1 open**, two-pass slippage |
| costs | tiered slippage + ADV impact + brokerage + STT **both legs** |
| window | 2017-01-01 → 2026-06-30, one continuous run |

## 3. Pre-committed gates

**Primary** — via `nq.runner.research.adjudicate` against the random control:

- ΔSharpe CI lower bound > 0 **and** point estimate > the 0.30 noise floor
- DSR > 0.95 at the live `n_trials`
- ΔCalmar ≥ 0.05 · 2022-26 sub-period ΔCAGR > 0 (**sliced**, never re-run) · fold-pass ≥ 60%
- turnover increase ≤ 30% · `n_eff` ≥ 20

**Secondary** — the compendium's Stage-4 additions:

- **PBO < 0.5** across the parameter neighbourhood (lookback × top-N × cadence)
- edge survives **1.5× costs** — *"if the edge disappears under 1.5× costs, it is not deployable"*
- Monte Carlo **block** drawdown p99 reported as the planning number, not the single realised path
- per-regime slices reported: 2018 · 2020 · 2022 · 2024-25
- **must clear equal-weight passive ownership** on Sharpe, or it is not worth running over an index fund

## 4. What each outcome means — decided now, not after seeing the number

| result | reading |
|---|---|
| all primary gates pass **and** PBO < 0.5 **and** beats passive | route to the forward wall as a WATCHED book. **Not** capital. |
| ΔSharpe positive, CI straddles zero | UNDERPOWERED — expected given ~37 independent windows. Not a failure; the data cannot resolve it. |
| PBO ≥ 0.5 with gates passing | the *selection between configurations* is noise even if the family has edge. Do not pick a winner from the sweep. |
| fails 1.5× costs | not deployable at any conviction level. |
| below passive on Sharpe | the book is not worth its complexity. |

## 5. Stated in advance

**Expected outcome: UNDERPOWERED.** Nine years of one market gives roughly 37 independent 63-day
windows and a ΔSharpe confidence half-width near 0.6. That is a property of the sample, not of the
strategy, and it is written here so a wide CI is read as the predicted result rather than a
disappointment.

**Known coverage gaps, carried into every readout:**
1. Size bands are reconstructed from trailing turnover rank — **not** NSE constituent lists.
2. The circuit screen is a returns-based proxy; there is no ASM/GSM or circuit-band feed.
3. Weights are equal rather than NSE's free-float-mcap × NMS tilt — the repo has no free-float
   market cap. Equal-weight with a 5% cap is the documented practitioner default.
4. STCG is applied at 20% inside the compounding; business-income treatment is not modelled.

**No performance expectation is recorded.** The gates decide; the number is whatever it is.

## 6. Refusals

The parameter neighbourhood is swept **only** to compute PBO and to check the baseline sits on a
plateau. No cell from that sweep may be adopted — selecting the best cell is the procedure PBO
exists to measure, and adopting it would make the PBO figure meaningless.
