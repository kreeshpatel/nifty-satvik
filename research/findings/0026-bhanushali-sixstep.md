# 0026 — The owner's "six-step" Bhanushali variant: exit geometry rescues the killed entry, net +0.48 Sharpe, UNDERPOWERED

- **Status:** TRIAL (pre-reg [0084](../../diagnostics/research/preregistry/0084-bhanushali-sixstep.md),
  n_trials 101→102, params frozen before the run). **Verdict: UNDERPOWERED.**
- **Date:** 2026-07-03. Script `scripts/run_bhanushali_sixstep.py`; ledger
  `research/exports/bhanushali_sixstep_0084_trades.csv` (476 trades). **Corrected backfilled universe**
  (788 names, pinned + backfill + aliases), PIT membership, ADV-tiered real costs, window 2017–2026.

## What was tested (the owner's reconstruction, frozen in 0084)
Two-stage funnel: weekend bucket (weekly close > 44-WEEK SMA, SMA rising) → daily 44-SMA rising + pullback
touch (±2% band) → green candle at/above the MA within 10 sessions → buy-stop at the candle high (lives 3
sessions), initial stop = candle low. Exits: half at +2R, rest at +3R, stop, or 3 consecutive closes below
the 44-DMA (next-open). **No time cap, no rotation, no position/notional caps** — cash is the only
constraint. 2% equity risk per fill.

## Result

| cell | trades | win | expR | hold med/p90 | CAGR | Sharpe | MaxDD |
|---|---|---|---|---|---|---|---|
| corrected GROSS | 492 (52/yr) | 39.2% | +0.20 | 22/54d | +18.3% | **+0.838** | −39.4% |
| **corrected NET (primary)** | 476 (50/yr) | 38.7% | +0.18 | 22/55d | +8.6% | **+0.477** | −37.2% |
| survivor-only NET (ref) | 440 | 38.6% | +0.16 | 23/57d | +6.3% | +0.394 | −43.7% |
| erratum-dropped NET (sensitivity) | 494 | 39.7% | +0.19 | 20/55d | +9.3% | +0.502 | −34.6% |

Slices (continuous, one curve): 2017-18* +0.05 | 2019-21 +0.94 | 2022-26 +0.33. Bootstrap 95% CI
[−0.219, +1.177]; **DSR@102 = 0.085**. Gates: slices PASS, CI-low FAIL, DSR FAIL → **UNDERPOWERED**
(not a KILL: Sharpe > 0, no negative slice; per the 0084 pre-committed rule).

## Root-cause readout (REQUIRED)
1. **The exit geometry is the whole story.** Same funnel family as 0022 Engine-B (killed at Sharpe −1.6
   net); swapping its 1:2/3–10d/stop-churn exits for {half@2R, rest@3R, 3-close MA-breach, no time cap}
   turns the SAME entry into +0.48 net. Exit mix shows the mechanism: the MA-breach trail is the dominant
   loser-cutter (207 of 476 exits) and it exits at ~−0.1..−0.7R *before* the candle-low stop is reached
   (only 165 stop-outs vs 0022's 763), while targets bank 99 winners at blended +2.5R. Median hold 22d vs
   0022's forced ≤10d — the trend actually gets room. This confirms 0025's thesis (exit geometry is the
   live lever) via a *different* geometry: candle-low stop retained, trail carried by the MA-breach rule.
2. **Costs still halve the edge** (gross 0.838 → net 0.477; CAGR 18.3 → 8.6): 50 trades/yr with partial
   exits ≈ 2.5 legs/trade. The strategy is cost-viable (unlike 0022's 260/yr) but not cost-light.
3. **Survivorship correction HELPED here** (+0.394 survivor → +0.477 corrected) — opposite of the usual
   direction: the backfilled/aliased names add profitable 2017-21 signals, and the MA-breach exit truncates
   the delisted losers' left tail. The headline is on the corrected universe regardless (the honest cell).
4. **Capacity binds hard:** 79k cash-skip retries — with no rotation and 2%-risk sizing the book is fully
   invested almost always, so realized performance is also a *selection* among signals (first-triggered
   wins). Realized risk = 2.000% on every fill (0022's cap under-sizing bug provably absent).
5. **Where it sits:** above the 0025 atr4 sleeve point estimate (+0.477 vs +0.397, different geometry,
   same universe/costs) but inside noise; below baseline_v1 (0.667) and far below its own CI width. At
   ~50 trades/yr no in-sample run can certify it — same wall as 0076/0081/0083.

## Verdict & next setup
**UNDERPOWERED — recorded, not relitigated.** No cfg change. Disposition: this variant joins the Path-B
swing-sleeve discussion at the **2026-10-01 quarterly review** (it is the third exit-geometry datapoint:
0022 taught exits KILL, 0025 atr4 +0.397, 0084 scaled+MA-breach +0.477 — a consistent story that the
44-SMA funnel carries a real but small edge whose expression is exit-determined). If the owner wants it
watched before then, the forward wall's watched-book cap (2) is full — an owner decision, not a default.
Do NOT tune the frozen params toward a pass; any new variant is a new pre-reg with a genuinely new lever.
