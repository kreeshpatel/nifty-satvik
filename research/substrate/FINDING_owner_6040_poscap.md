# Finding — the owner's 60/40 + 20%-per-name cap: the cap *concentrates* the book instead of protecting it

*Run: `scripts/run_owner_6040_poscap.py` (2026-07-16). Guards verified byte-identical first
(golden 1.1319/255 · live P2 1.0342/168). Judged on the 2022-26 continuous slice (R3).
Baseline all-grades **1.29** · random-selection null **0.74** (sd 0.24).*

## The spec as tested

The owner's instruction, read as one conjunction: notional capped at **20% of equity per name**;
**60% off at 2R**; **40% off at 3R** if reached, otherwise that 40% exits on the weekly close below the
44w SMA; **no runners**; R capped at **5%**.

## Result — every arm loses

| arm | tr | Sharpe | CAGR | MaxDD | **22-26** | win | meanR | med R% |
|---|---|---|---|---|---|---|---|---|
| BASE (live P2) | 168 | 1.03 | 21.2% | −34.8% | **1.29** | 54% | +0.62 | 14.2 |
| SPEC 60/40 + Rcap5 + cap20 | 529 | 0.27 | 3.4% | **−54.5%** | **0.64** | 51% | +0.16 | 5.0 |
| …no R cap | 280 | 0.97 | 18.8% | −35.7% | **0.82** | 47% | +0.48 | 13.0 |
| …+ 3 signal guards | 532 | 0.72 | 12.0% | −32.1% | **0.75** | 54% | +0.38 | 5.0 |

The full spec lands **−0.65 vs base** and **−0.4σ *below* the random null** — it is worse than picking
trades at random. This is **sighting #8** of the standing law: every mechanism that tightens, protects,
or imposes structure removes the fat tail and regresses toward (here, past) the null.

## Root cause — the cap is a floor-raiser, not a ceiling

This is exact arithmetic, not an inference. Position size is `sh = eq × risk / (entry − stop)`, so
notional per name is:

```
notional = sh × entry = eq × risk% / R%
```

- **Base**: R% = 14.2 → notional = 2%/14.2% = **14.1% of equity per name**.
- **R capped at 5%**: notional = 2%/5% = **40%** → the 20% cap binds and clips it to **20%**.

So the 20% cap does bind — but it binds at **1.4× MORE concentrated than the base book already was**.
The base never needed a cap; its wide stops self-limited notional to 14%. Capping R forced notional up,
and the "protective" 20% cap merely stopped it going to 40%. **MaxDD −34.8% → −54.5% is the cap doing
its job as specified.** A 20% cap only protects a book whose natural sizing exceeds 20%; this one's
doesn't.

## The mechanics worked — that is what makes this decisive

The targets **did** start firing: exit mix went from `stop 69 / blowoff_half 44 / trail 31 / time 14`
(targets never reached) to `stop 251 / **targets 230** / stop_part 28 / sma_break 14`. The 2R/3R
tranches are now reachable, exactly as the R cap was designed to make them. **The design intent was
achieved and the book still lost.** So this is not a "the targets never fire" failure — it is the
fat-tail removal: 230 trades were cut at 3R that previously ran.

## meanR is again the denominator illusion — read the actual move

meanR falls +0.62 → +0.16, but R% falls 14.2 → 5.0. The honest quantity is `meanR × R%` = the actual
price move captured per trade:

- Base: 0.62 × 14.2% = **+8.8%**
- Spec: 0.16 × 5.0% = **+0.8%**

**11× less actual price movement captured.** meanR's collapse understates the damage; it does not
overstate it.

## The 20% cap alone is the least-bad arm and still loses

Without the R cap (R% 13.0, near-base geometry), the cap barely binds and the book scores 0.97 full /
**0.82** on 22-26 — the closest arm, still −0.47 vs base. The loss there is the **60/40 exit**, not the
cap: `targets 102 / sma_break 101` replaced `blowoff_half 44 / trail 31`, i.e. the no-runners rule sold
the winners that carry the book. This reproduces `FINDING_taught_mechanics.md` (the 2R/3R mechanics cap
the fat tail that *is* the edge) on a second, independent geometry.

## Verdict

**KILL — all three arms.** R11: nothing ships in-sample, and nothing here would want to.
The live config is untouched and stays FROZEN. R4: params were frozen before the run; no retuning.

## What this closes and what it leaves

- **Closed:** the 2R/3R target family at every geometry we can build it (wide stop → targets never fire;
  tight stop → targets fire and the fat tail dies; capped notional → concentration, worse DD). Three
  independent formulations, three kills. Do not re-propose fixed-R targets on this book.
- **Closed:** "cap capital per name" as a drawdown tool for *this* book — its natural 14% sizing is
  already below any cap worth setting. A cap can only bind upward here.
- **Still open (unspent):** the base's own exit is `blowoff_half + trail`, and the fat tail survives
  only because nothing truncates it. The remaining honest levers are **selection** (already at the
  99-100th percentile via CRS) and the **entry**, which Phase-1 exhausted across 8 levers. Which is to
  say: **this book has no in-sample lever left**, which is what the last eight sightings have each said.
