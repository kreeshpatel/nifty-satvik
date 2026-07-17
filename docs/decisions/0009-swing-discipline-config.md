# ADR 0009 — Adopt the owner's discipline config on the live weekly-swing book

**Date:** 2026-07-16
**Status:** ACCEPTED (owner override on risk appetite)
**Supersedes:** nothing. **Extends:** ADR 0008 (swing exit change / P2 exit).

## Context

The owner reviewed the live book's trades against TradingView charts and objected that the book was
"badly traded" regardless of return:

> *"i dont care even if it gave good returns, then our book is badly traded. we have be according to
> rules or else we will suffer later max 20 percent is fine, if more than 10 percent then our R is
> distorted and that can create big positions and big profits as well as big losses and longer holding
> period"*

The concrete complaints were reproducible: median R of 13.7% means a −2R exit is a −27% move; mean holds
ran 19 weeks; and fills routinely landed 20-40% above the 44w SMA (KNRCON filled at +40.1% extension off
a 43.8%-range candle).

## Decision

Add three cfg-gated levers to the live cron (`scripts/run_bhanushali_cron.py`, `LIVE_DISCIPLINE`):

| lever | value | effect |
|---|---|---|
| `ext_cap` | 0.20 | skip any fill priced >20% above the signal-week 44w SMA. **Pure selection — the stop is untouched.** The rule-faithful half. |
| `max_risk_pct` | 0.10 | stop = `max(signal-week low, entry × 0.90)`. **Deviates from the taught rule** (stop = the week's low) by explicit owner instruction. |
| `max_notional_pct` | 0.20 | no name exceeds 20% of sizing equity. **Guardrail, not a performance lever.** |

Model version `weekly-swing-0094-rank-p2exit` → **`weekly-swing-0094-rank-p2exit-disc`**.

## Evidence — measured on the A-ONLY book that actually trades

Pre-registered in `research/preregistry_owner_discipline.md` **before** the run (R4); trial 115→116.
Parity-checked against the recorded A-only live figures (1.004 Sharpe / 171 trades): **PASS**.

| metric | BASE (prior live) | **DISC (new live)** | Δ |
|---|---|---|---|
| Sharpe | 1.004 | **1.055** | +0.05 |
| **2022-26 slice** | **1.17** | **1.04** | **−0.13** ← the one negative |
| CAGR | 20.9% | 20.2% | −0.64pp |
| **MaxDD** | −36.4% | **−31.2%** | **+5.2pp** |
| trades | 171 | 184 | +13 |
| **median R** | 13.7% | **9.1%** | −4.6pp |
| **mean hold** | 19.1wk | **12.4wk** | −6.7wk |
| win rate | 54.4% | 50.5% | −3.8pp |

## Basis and honesty

**This is NOT an edge claim.** It is **return-neutral**: +0.05 Sharpe full-sample against −0.13 on the
2022-26 slice — opposite signs, the signature of noise. This book is known chaotic under fill
perturbation (G1 alone 0.47, G2 alone 0.42, G1+G2 together 0.97). At cumulative trial **122**, **no DSR
gate passes a +0.05 in-sample delta**, and none is claimed. It **fails no gate because it was never
submitted as an improvement.**

What it buys is what the owner asked for, and those parts are structural rather than statistical:
R capped at 9.1%, holds cut by a third, and a 5.2pp better drawdown.

Same adoption route as ADR 0008 (P2 exit), and a strictly better trade: 0008 gave up 0.10 Sharpe for
−8pp DD; this gives up nothing measurable for −5.2pp DD.

## Recorded caveats

1. **The owner's stated mechanism was inverted.** *"R … can create big positions"* — notional is
   `risk% ÷ R%`, so a **wide** stop makes positions **small**. Capping R made the book **more**
   concentrated (14% → 22% per name). `max_notional_pct=0.20` was added to bound it.
2. **Concentration turned out to be a FEATURE.** `FINDING_more_slots` (trial 120→122) measured the
   dose-response: 4-5 names **1.21** > 7 names **0.97** > 10 names **0.81** on the 22-26 slice, walking
   toward the random null (0.74). An earlier draft of `FINDING_owner_discipline` called the 22%
   concentration "the real cost of the R cap" — **that was wrong and is corrected**. The cap is a
   guardrail against single-name blowup, not a diversification benefit.
3. **`max_risk_pct` breaks the rule it enforces.** The taught rule is stop = the signal week's low; the
   R cap lifts it to an arbitrary −10% line. `ext_cap` is the rule-faithful half. The owner chose both
   with the trade-off stated.

## Consequences

- The frozen 0094 research run stays **byte-identical (1.132/255)** — all three levers default OFF.
- Full suite: **120 passed**.
- Live cards will show tighter stops (~9% vs ~14%) and shorter holds; fewer extended-entry buys.
- **Reversible in one line:** delete `**LIVE_DISCIPLINE` from the two `backtest()` call sites.

## Alternatives rejected

- **Forward wall first** — the owner is the sole capital at risk and declined the wait (consistent with
  ADR 0008).
- **`max_risk_pct=0.05`** — KILLED: 0.64 on the 22-26 slice, MaxDD −54.5% (notional → 40%/name).
- **Small-candle selection instead of an R cap** — KILLED at 0.37 (`FINDING_small_candle`).
- **Lower risk to widen the book** — KILLED (`FINDING_more_slots`): dilutes toward the null.
