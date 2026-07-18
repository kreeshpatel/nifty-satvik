# Finding — the lock-in ratchet (the HEG giveback fix) truncates the discipline book's runners — KILL

*Pre-registered `research/preregistry_lockin_live.md`, frozen before the run (R4). n_trials 123->124.*

## Motivation

HEG 2025-12-29 @ 562.40 (1R=34.05) spiked to 672 = **+3.22R / +19.5%** in week 1 then round-tripped to a
−1.24R stop. It didn't sell because the 2R half books on the weekly CLOSE (619.7 = +1.68R < 2R) and the
blow-off exit needs a lower-third close on a NEW high (wk1 closed upper-half; wk2 closed lower-third but
not a new high). The owner asked for a rule that protects a large intraweek gain.

The literal ask (sell at the high / a fixed %) is `tp_on_high` — KILLED (0.709 / −49.7%). The lock-in
ratchet was the tested alternative that RAISES the stop instead of capping the target: `lockin_mfe=2.5`
→ stop to `entry+1.5R`. Per-trade it saves HEG (arm at 3.22R, stop → 613.5, exit wk2 ~+2.2% vs −7.5%).

## Result — KILL

| arm | tr | Sharpe | CAGR | MaxDD | 22-26 | win | meanR |
|---|---|---|---|---|---|---|---|
| LIVE (A-only + discipline + P2) | 184 | **1.055** | 20.2% | −31.2% | 1.04 | 51% | +0.61 |
| LIVE + lockin(2.5, 1.5) | 186 | **0.940** | 17.5% | −33.0% | 1.04 | 50% | +0.54 |
| Δ | +2 | **−0.115** | −2.7pp | −1.8pp | +0.01 | −1pp | −0.07 |

## Root cause — same fat-tail truncation, confirmed by the exit mix

```
                 stop  blowoff_half  trail  stop_half
  LIVE            87        47         33        0
  + lockin        95        40         22       13
```

The ratchet converts **runners** (blowoff_half 47→40, trail 33→22) into **early ratchet-outs** (stop_half
0→13). On a fat-tail winner that dips then recovers, raising the stop to +1.5R kicks it out on the first
pullback. CAGR −2.7pp is those cut runners. Pre-declared skeptical prior confirmed: on the R-capped
discipline book a 2.5R arm is a ~25% move (rare), and when it fires it truncates the already-shorter runs.

## The HEG case did NOT get "fixed"

Under lockin, HEG 2025-12-29 is **not in the ledger at all** — the ratchet changed which trades held cash,
so a different name took the slot and the HEG trade never occurred. This is the book's known
chaos-under-fill-perturbation, not a fix. The lever reshuffles the book; it does not surgically save the
one trade. Reading a single-trade rescue off it would be selection-on-outcome.

## Why this differs from the base-book result

The ratchet was ~+0.04 Sharpe on the base/all-grades book (below the +0.10 bar, forward-wall candidate).
It flips **negative** here because the discipline book already runs tighter — R capped at 10% shortens the
runs, so removing more of the top hurts proportionally more. **A lever's sign is book-specific; a positive
result on the base book does not transfer to the discipline book.**

## Verdict

**KILL.** R11 — nothing ships. Live config unchanged (`lockin_mfe` stays 0). Exit-truncation levers are
now **0-for-4** (tp_on_high, fixed-R targets, small-candle, lockin-on-live).

## The standing answer to the giveback question

HEG's +19.5% → −7.5% round-trip is real and it stings, but it is the **cost side of the fat tail**, not a
fixable leak. Every rule that would have caught it (fixed target, tighter trail, profit-protect ratchet)
removes more from the winners than it saves on the givebacks — measured four ways now. The book keeps
**50% of winners' MFE** (winners reach 4.92R, keep 2.44R) precisely by NOT protecting the giveback; the
unprotected runs are where the other 50% lives. The only exit that survives is the one already shipped
(P2: blow-off + 20-week trail, no fixed target).
