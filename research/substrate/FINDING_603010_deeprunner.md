# Finding — 60/30/10 deep runner: a small runner fraction CANNOT carry the fat tail (blended-R arithmetic) — KILL

*Pre-registered `research/preregistry_603010_deeprunner.md`, frozen before the run (R4). n_trials 127->128.
Guards: golden byte-identical 1.1319/255 with the new runner knobs off.*

## The rule (owner)

> *"keep 2R at 60 percent and 3R at 30 percent, if not 3r then sell at 2R and for the remaining 10 percent
> runners till 6R or 15 percent below the 44SMA"*

`scaled_exit(tp1_r=2, tp1_frac=0.60, tp2_r=3, tp2_frac=0.30, runner_cap_r=6, runner_sma_buffer=0.15)`.
New engine knobs (default-off, golden byte-identical): `runner_cap_r` (book remainder at 6R) and
`runner_sma_buffer` (runner exits at wsma*(1-buffer), i.e. 15% below the 44w SMA — ride THROUGH SMA
touches). Owner's fix for the 70/30 bleed (which sold AT the SMA ~14% below entry).

## Result — KILL, fails the gate

| | tr | full Sh | CAGR | MaxDD | 17-21 | **22-26** | maxR | R>=3 | R>=6 | hold |
|---|---|---|---|---|---|---|---|---|---|---|
| LIVE (P2 trend) | 184 | 1.055 | 20.2% | -31.2% | 1.07 | **1.04** | 16.7 | 23 | 2 | 12wk |
| B (60/40, no runner) | 250 | 1.161 | 22.1% | -31.5% | 1.28 | 1.03 | 2.4 | 0 | 0 | 10wk |
| **D (60/30/10 deep)** | 224 | 1.011 | 19.1% | **-30.0%** | 1.07 | **0.95** | **2.7** | 0 | 0 | 18wk |

D has the **best drawdown** (-30.0%) but **fails the gate** (0.95 vs 1.04, -0.09) and full Sharpe is
slightly worse (-0.044).

## Root cause — blended-R arithmetic caps the trade at 2.7R regardless of the runner

maxR = **2.7**, and NO trade reached even 3R blended. Because the trade's R is the position-weighted blend:

```
0.60 * 2R  +  0.30 * 3R  +  0.10 * (up to 6R)  =  1.2 + 0.9 + 0.6  =  2.7R   (max)
```

Even on a stock that runs 20R, the 10% runner contributes only 0.10 * 20 = +2R to the blend. **A small
runner fraction cannot carry the fat tail — it is arithmetically negligible.** The 6R cap made it worse,
but even uncapped, 10% is too small to matter. This is why D looks like B (tail gone) despite "keeping a
runner."

## The exit axis is now closed — the fundamental law

Six exit variants tested (tp_on_high, 60/40, 60/30/10-close, 70/30, lockin, this). They collapse to one
tradeoff:

- **Keep the fat tail** => need a LARGE fraction running (LIVE runs 50%).
- **A large fraction running bleeds** unless the trail is TIGHT (70/30 proved a loose 44w-SMA trail bleeds
  the tail back: 0.29).
- **Therefore the only tail-preserving exit is a LARGE runner on a TIGHT trail** = the live P2 exit
  (50% runner on the 20-week SMA + blow-off @2.5R). Everything else either caps the tail (B, D:
  maxR 2.4-2.7) or bleeds it (70/30: DD -42.8%).

The owner has independently rediscovered the live exit's design. It is the optimum of this family.

## The two survivors

- **LIVE (shipped):** large runner, tight trail. Keeps the tail (maxR 16.7), passes the gate (1.04).
- **B (forward-wall fork):** all capped ~2.4R, smooth, higher aggregate Sharpe in-sample, gate-flat,
  tail-less. A philosophy choice (smooth-vs-lumpy), not an improvement — decided only out-of-sample.

## Verdict

**KILL.** R11 — nothing ships. Live P2 exit unchanged. Exit restructuring is **0-for-6**; the axis is
exhausted with a clean mechanism for every failure.

## Next setup

Stop probing the exit — six variants, one law, no ship. The two open items are unchanged: the B fork
(forward wall, owner's smooth-vs-lumpy call) and the untested near-SMA-fire entry variant. Further exit
trials only deflate the DSR bar (now trial 128) against a settled question.
