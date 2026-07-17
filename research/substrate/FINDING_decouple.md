# Finding — the touch-then-green lever KILLED, but its MECHANISM CHECK FAILED: the owner's rule is still untested

*Pre-registered `research/preregistry_decouple.md`, frozen before the run (R4). n_trials 118->120.
Guards byte-identical (golden 1.1319/255 · live P2 1.0342/168).*

## Result — KILL both arms

| arm | tr | Sharpe | CAGR | DD | **22-26** | **entry ext (med)** | pool |
|---|---|---|---|---|---|---|---|
| BASE | 168 | 1.03 | 21.2% | −34.8% | **1.29** | +17.4% | 8,518 |
| SPEC (ext20+R10+pos20) | 181 | 1.11 | 21.6% | −33.6% | **1.21** | +13.8% | 8,518 |
| BASE + decouple | 175 | 0.88 | 18.0% | −35.9% | **0.73** | **+18.4%** | 9,562 |
| SPEC + decouple | 182 | 1.05 | 19.9% | −33.2% | **0.86** | **+15.1%** | 9,562 |

## The mechanism check FAILED — this is the finding

The pre-registration declared: *"entry extension should FALL (firing on the first green after the touch,
not the reclaim blow-off)"*. **Extension ROSE** — median +17.4% → +18.4% on base.

**Root cause — the lever does not implement the owner's rule.** The base rule requires the FIRING week to
itself touch (`wlow <= SMA*1.07`). `decouple_touch_green` drops that condition: it arms on a touch, then
fires on the first `qgreen AND close>SMA` week within `green_wait=3` — **with no requirement that the
firing week is still anywhere near the SMA**. After the touch, price runs; the lever fires on a green week
*further* from the line than the base would have.

The owner's stated rule is explicit on this point:

> *"that should be considered the setup week **until its near the 44SMA or touching it actively**"*

The lever has no near-SMA condition on the fire. It armed on the pullback and then fired anywhere.

**This was my error.** The pre-reg transcribed the semantics correctly (`qgreen AND close>SMA AND slope
AND RS`) and I failed to notice the absent touch/near-SMA term before freezing. Two trials were spent on
a mis-specified lever. Recorded so the cost is visible, not buried.

## Honest status

- **These two arms: KILL.** R11 — nothing ships. The numbers stand; no retuning.
- **The owner's hypothesis: UNTESTED.** A KILL of a mis-specified implementation is not evidence against
  the idea it was supposed to encode. This is NOT an excuse to keep tweaking until something passes —
  it is the difference between *falsified* and *never tried*.

The faithful version would keep the arm-on-red-touch behaviour AND require the firing week to still be
near the line (e.g. `wlow <= SMA*(1+band)` on the fire, or an extension ceiling on the signal bar rather
than only on the fill). That is a **new formulation** and needs its own pre-registration and its own
trial count. **Owner's call whether it is worth trial 121** — proposing it here is not the same as
running it.

## Reading this against the rest of the arc

`open_progress` (KILL) removed the pullback and lost 82% of the book's R. This lever *kept* the pullback
but let the fire drift **further** from the line, and also lost. Both point the same way, and it is the
same thing `deep-near-sma-touch-edge` and `POOL_vs_SELECTION` already say: **proximity to the line at the
moment of entry is the edge**, and every mechanism that increases entry extension costs money. The one
config that *reduced* extension (SPEC, med 17.4% → 13.8%) is also the only one that did not lose.

Entry-side changes now **0-for-12**. But note the split: 10 subtractive filters, and 2 timing arms whose
mechanism check failed. The subtractive family is genuinely dead. The timing family has had **no valid
test yet**.

## Next setup

Unchanged and both additive: the **2R-on-close miss** (AEGISLOG reached +2.35R MFE, booked −2.02R) and
the **more-slots** experiment (`FINDING_cash_starvation`). Plus, now, a faithful near-SMA-fire variant of
the owner's sequence — if the owner wants to spend the trial.
