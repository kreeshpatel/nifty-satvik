# Owner chart review (2026-07-16) — 5 observations, 2 new guards, both KILLED

The owner reviewed the worst trades on TradingView against the taught rule. **All five observations were
factually correct.** Three map to already-KILLED tests; two were genuinely new and were tested here.

## The observations, adjudicated

| # | Observation | Verdict |
|---|---|---|
| 1 | "rule is to enter only if the setup candle closes above the previous candle near the SMA" / no confirmation | **Deliberate, already tested.** Pre-reg **0088** tested the taught buy-stop at the signal week's HIGH → **KILLED**: Sharpe +0.215 (Δ −0.372), CAGR **+2.3%** (Δ −9.2pp), because entry→stop width doubles to **12.8%** (vs 7%). **0089** introduced the in-range fill *specifically to fix 0088* and became family-best. We deviate from the teaching **because the teaching measured worse.** |
| 2 | RAINBOW "never had a green candle that closed above the candle near the SMA" | **Correct + NEW.** Signal week closed **1444.8 vs prior 1454.3** — green (close>open) but BELOW the prior close. `qgreen` never requires progress. → tested as **G2**. |
| 3 | SOBHA "next candle did not have a body" | Requires waiting for the entry candle to close = 0088's confirmation by another name. |
| 4 | RAIN "not in a proper visible uptrend" | **Correct in spirit** (slope floor is a weak 3%/13wk; the repo's own appendix found a *strong* sustained filter doubles the edge) — but the visibly-rising-MA tightening was tested as **0092 → KILL** ("the definitive backtest > your eyes"). |
| 5 | KENNAMET "already under the 44SMA" | **Correct + NEW.** Fill landed **−1.5%** below the SMA (NAVA −1.8%). The signal requires close>SMA but the 0089 in-range fill can land below the line. → tested as **G1**. |

## The two new guards — both KILLED (`scripts/diag_owner_guards.py`)

| config | trades | Sharpe | CAGR | DD | Calmar | **22-26** |
|---|---|---|---|---|---|---|
| BASE (live rule) | 168 | 1.03 | 21.2% | −34.8% | 0.61 | **1.29** |
| **G1** fill must be above the SMA (`ext_floor=0.0`) | 169 | 0.64 | 11.7% | −45.2% | 0.26 | **0.47** |
| **G2** signal close > prior close (95% of windows pass) | 173 | 0.76 | 14.1% | −42.7% | 0.33 | **0.42** |
| **G3** both | 165 | 1.03 | 21.0% | **−32.2%** | **0.65** | **0.97** |

Per R11: FINDINGS, no retune. New engine lever `ext_floor` (default None ⇒ byte-identical).

## The finding that matters — this is CHAOS, not information

**G1 changes the trade count by ONE (168→169) and the 22-26 slice collapses 1.29 → 0.47** — *below the
random-selection null (0.74)*. Skipping a few below-SMA fills frees cash, a different name fills, and the
portfolio cascades.

**And the proof:** G1 alone **0.47**, G2 alone **0.42**, but **G1+G2 = 0.97**. If either filter carried
signal, combining them would COMPOUND. Instead they partially **cancel**. That is the signature of
**chaotic reshuffling**, not a systematic effect — two "obviously correct" fixes behaving as coin-flips.

**Implication for the forward number:** if the book is this sensitive to a one-trade perturbation, then its
**1.29 is itself substantially a lucky cascade**. This independently reinforces the Monte-Carlo conclusion:
**plan against the null (0.67-0.74), not 1.29.**

## Standing lesson (3rd sighting)

Pool filter → broke CRS. 14-EMA gate on B → deleted the deep pullbacks. Now G1/G2 → chaotic cascade.
**Every filter applied to this book removes the deep entries that carry the tail, and every fill
perturbation regresses toward the null. Do not filter this book.**
