# Finding — the blow-off PATTERN exit preserves & amplifies the tail (CAGR 27%!) but fails the gate and blows the DD

*Pre-registered `research/preregistry_pattern_exit.md`, frozen before the run (R4). n_trials 128->129.
Golden byte-identical 1.1319/255; test_stage2_golden 3 passed.*

## The rule (owner)

> *"40 percent at 2R and 40 percent at pattern and 20 at runner and sell below 44SMA"*

`scaled_exit(tp1_r=2, tp1_frac=0.40, pattern_frac=0.40, pattern_arm_r=2.5, runner_sma_buffer=0.0)`.
40% @ 2R (intraweek) + 40% on the BLOW-OFF exhaustion bar (new high closing in its lower third once
MFE>=2.5R — the one pattern with validated exit value; the zoo entry detectors are IC~0, 0079) + 20%
runner to a weekly close below the 44w SMA. New engine: a partial "part" pending books the mid-position
pattern tranche at next Monday open while keeping the runner open.

## Result

| | tr | full Sh | CAGR | MaxDD | 17-21 | **22-26** | maxR | R>=5 | hold |
|---|---|---|---|---|---|---|---|---|---|
| LIVE (P2 trend) | 184 | 1.055 | 20.2% | -31.2% | 1.07 | **1.04** | 16.7 | 2 | 12wk |
| B (60/40, capped) | 250 | 1.161 | 22.1% | -31.5% | 1.28 | 1.03 | 2.4 | 0 | 10wk |
| **P (40/40/20 pattern)** | 130 | **1.227** | **27.2%** | **-39.5%** | **1.48** | **0.91** | **40.8** | **12** | 27wk |

## The pattern-exit idea WORKED — it preserved and amplified the tail

Unlike every other target scheme (which capped the tail at ~2.4-2.7R), the blow-off pattern tranche let
monsters run: **maxR 40.8** (vs LIVE 16.7), **12 trades >=5R** (vs 2). Highest CAGR (27.2%) and full
Sharpe (1.23) of the entire session. The owner's intuition — use a pattern, not a fixed target, to exit
the runner — is mechanically sound and it genuinely captured more of the fat tail than the live 20wk trail.

## Why it does NOT ship

1. **Fails the pre-registered gate:** 2022-26 slice **0.91** vs LIVE 1.04 (-0.13). The lift is entirely
   2017-21 (1.48). The forward-relevant period is WORSE.
2. **DD blows to -39.5%** (vs -31.2%) — it contradicts the owner's stated first priority (lower drawdown,
   clean trades). The 20% at-SMA runner + long holds (27wk) ride losers deep; the tail-amplification cuts
   both ways.
3. In-sample at trial 129; DSR deeply deflated.

## The session's central result — B and P are MIRROR IMAGES, both fail the gate

Two configs now beat LIVE on full-sample Sharpe AND CAGR in-sample, via OPPOSITE mechanisms:

| | tail | full Sh | CAGR | DD | 2017-21 | 2022-26 (gate) |
|---|---|---|---|---|---|---|
| B | CAPPED (2.4R) | 1.16 | 22% | -31.5% | 1.28 | 1.03 |
| P | AMPLIFIED (40.8R) | 1.23 | 27% | -39.5% | 1.48 | 0.91 |
| LIVE | balanced (16.7R) | 1.06 | 20% | -31.2% | 1.07 | **1.04** |

**Both B and P improve only in the 2017-21 bull and both fail the 2022-26 gate.** Capping the tail and
amplifying the tail both look good on aggregate in-sample, and both evaporate on the forward-relevant
slice. This is strong evidence the aggregate wins are **regime artifacts of the bull run**, and that LIVE
— the only book that holds up on 2022-26 — is the correct ship. You can win in-sample by going either
direction on the tail; neither survives the period that matters.

## The one refinement not spent (owner decision, NOT auto-run)

P's failure is the DD, driven by the loose 20%-at-SMA runner. A pattern tranche paired with a TIGHTER
runner (the 20wk trail or a 7%-below-SMA backstop instead of at-SMA) might keep the tail while controlling
DD. But that is trial 130 on a settled axis, and the gate result (0.91) suggests the recent-period
weakness is structural to the long holds, not just the runner. Flagged, not run.

## Verdict

**Does NOT ship (R11): fails the 2022-26 gate and worsens DD.** Like B, it is a regime-dependent
in-sample aggregate improver, not a certified edge. The pattern-exit mechanism is validated as
tail-preserving but the whole config trades the owner's drawdown priority for return. Live P2 exit
unchanged. Exit axis: 7 variants, LIVE remains the gate-passing optimum.
