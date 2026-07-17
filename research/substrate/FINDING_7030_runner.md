# Finding — 70% @ 2R + 30% runner-to-44wSMA: the tail returns but the 44w SMA is far too loose a trail — KILL

*Pre-registered `research/preregistry_7030_runner.md`, frozen before the run (R4). n_trials 126->127.
Guards: A-only baseline parity 1.004/171 PASS.*

## The rule (owner)

> *"keep 2R and 70 percent but keep 30 percent as runners till its above the 44 weekly SMA"*

`scaled_exit(tp1_r=2.0, tp1_frac=0.70, tp2_frac=0.0)`: 70% books at 2R (intraweek), 30% runs until a
weekly close below the 44w SMA. On the LIVE book (A-only + LIVE_DISCIPLINE).

## Result — KILL, worse than BOTH references

| | tr | full Sh | CAGR | MaxDD | 17-21 | **22-26** | maxR | R>=3 | hold |
|---|---|---|---|---|---|---|---|---|---|
| LIVE (P2 trend) | 184 | 1.055 | 20.2% | -31.2% | 1.07 | **1.04** | 16.7 | 23 | 12.4wk |
| B (60/40, no runner) | 250 | 1.161 | 22.1% | -31.5% | 1.28 | 1.03 | 2.4 | 0 | 10.1wk |
| **H (70/30 -> 44wSMA)** | 173 | **0.627** | 10.8% | **-42.8%** | 0.94 | **0.29** | **27.8** | 18 | **21.9wk** |

## Root cause — the tail returned, but the runner's trail is ~14% below entry

The mechanism check PASSED in the wrong direction: **maxR rose to 27.8** (the biggest of all three), so the
30% runner DID preserve the fat tail. But the book collapsed to **0.29** on the 2022-26 slice with a
**-42.8%** drawdown.

The 44w SMA sits a median **~14% BELOW the entry** (entries fire ~14% extended). So the 30% runner cannot
exit until price falls all the way back to the line — a -14%+ round-trip from the high. **Holds jumped
21.9 weeks (vs 12.4 LIVE)** — the runner sits for months, and on every trade that tops and rolls over the
30% bleeds most of the way down. Exit mix `sma_break 81`: the runner giving it back.

## The real lesson — the runner's TRAIL rule is the whole game, not target-vs-runner

This is NOT "runners lose." LIVE also keeps a runner — but it trails on the **20-WEEK SMA** (far closer to
price) **plus a blow-off-bar exit @2.5R**, which catch the rollover ~9 weeks earlier. The 44w SMA is the
**loosest possible trail**; the 20wk+blowoff is calibrated. Same 30%-runner intent, opposite outcome,
entirely down to the trail distance:

- 44w SMA trail (H): exits ~14% below the peak -> gives back the tail it caught -> 0.29.
- 20wk SMA + blowoff (LIVE): exits near the rollover -> banks the tail -> 1.04.

The owner's instinct to keep a runner is sound and is ALREADY in the live book; "till the 44w SMA" is just
the wrong stop for it.

## Where this leaves the three exits

- **LIVE (P2):** 50% half @2R + 20wk/blowoff trend trail. Banks the tail via a tight runner exit. **1.04.**
- **B (60/40):** all capped at 2.4R, no tail, smooth, higher aggregate Sharpe but fails the gate (flat
  22-26) and removes the fat tail. Forward-wall fork.
- **H (70/30->44wSMA):** tail preserved but the trail too loose -> worst. **KILLED.**

Exit-truncation / exit-restructuring is now **0-for-5**. The current P2 exit is confirmed as the balance
point: tighter than the 44w runner, tail-preserving unlike B.

## Verdict

**KILL.** R11 — nothing ships. Live config unchanged (P2 exit stays). The one improver remains B, held at
the forward wall (`FINDING_intraweek_rotate`).

## Next setup

If the runner idea is pursued further, the lever is the **trail distance**, not the fraction: a 30% runner
on the 20-week SMA (LIVE's trail) rather than the 44-week. But that is close to the live P2 exit already,
and the exit axis has now been probed five ways with no ship. The genuine open item stays the B fork
(smooth-vs-lumpy, forward wall) and the untested near-SMA-fire entry variant.
