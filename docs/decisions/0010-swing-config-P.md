# ADR 0010 — Ship config P (pattern-exit) as the live weekly-swing book + surface pattern/exit on cards

**Date:** 2026-07-16
**Status:** ACCEPTED (owner override, against the research recommendation)
**Extends:** ADR 0008 (P2 exit), ADR 0009 (discipline config).

## Context

The owner elected to ship **config P** — the three-tranche pattern exit — as the live book, and to build
the product (per-user memory, Research UI, guidance) around it. This ADR records the config swap
(Phase A of the product build) and its honest basis.

## Decision

`scripts/run_bhanushali_cron.py`: the live book now runs `P_EXIT` (replacing `P2_EXIT`) alongside the
existing `LIVE_DISCIPLINE`:

```
P_EXIT = scaled_exit(tp1_r=2.0, tp1_frac=0.40, tp2_frac=0.0,
                     pattern_frac=0.40, pattern_arm_r=2.5, runner_sma_buffer=0.0)
```

- **40%** books at **+2R** (intraweek resting limit).
- **40%** books on the **blow-off exhaustion pattern** (a new-high week closing in its lower third, armed
  at +2.5R MFE — the one validated pattern exit; the zoo entry detectors are IC~0, finding 0079).
- **20%** runner held until a **weekly close below the 44-week SMA**.

Model version `weekly-swing-0094-rank-p2exit-disc` → **`weekly-swing-0094-rank-P`**.

Every signal card now carries `pattern` (entry structure), `exit_plan` (the three tranches with price
levels + plain-English "do this"), and `exit_stage` (which tranches have booked). The held-card exit
messages are P-aware (pattern tranche, sma_break, stop).

## Evidence (all in-sample, A-only traded book)

| | LIVE (prior) | **P (new)** |
|---|---|---|
| full Sharpe | 1.055 | **1.227** |
| CAGR | 20.2% | **27.2%** |
| MaxDD | −31.2% | **−39.5%** |
| **2022-26 slice (gate)** | **1.04** | **0.91** |
| max winner | 16.7R | **40.8R** |
| trades | 184 | 130 |

## Honest basis — this is an owner override, NOT a certified edge

**The research recommendation was to keep the prior LIVE book.** P is adopted against it, on the owner's
call as sole capital-at-risk. Three independent results say P is inferior:

1. **Fails the pre-registered 2022-26 gate** (0.91 vs 1.04); its full-sample lift is entirely 2017-21 bull
   (`FINDING_pattern_exit.md`).
2. **−39.5% drawdown** — directly against the owner's own stated drawdown priority.
3. **Worse from a cold start** — the rolling cold-start distribution (`COLD_START_DIST.md`) showed P's
   median forward return is LOWER and more dispersed than LIVE (1yr median +9% vs +17%), because P's edge
   is lumpy/tail-dependent and a real start often misses the monster year.

P's appeal is the amplified fat tail (maxR 40.8, in-sample CAGR 27%). The owner accepts the drawdown and
regime risk for that upside. It is in-sample at cumulative trial 129; no DSR gate passes it.

## Consequences

- Frozen 0094 research run stays **byte-identical (1.132/255)** — `backtest()` defaults OFF;
  `test_stage2_golden` 3 passed.
- The `results/` envelope now exposes pattern + exit_plan + exit_stage for the UI (Phase C/D).
- Cron smoke-tested offline: 4 open / held cards carry exit_stage, EXIT_REQUIRED cards give plain-English
  instructions, exit 0.
- **Reversible in one line:** swap `**P_EXIT` back to `**P2_EXIT` at the two `backtest()` call sites and
  revert `model_version`.
- The weekly review scorecard keeps showing the true gate status, so the product does not hide P's
  underperformance from the record.

## Alternatives rejected (by the owner)

- Keep LIVE shipped, build product on it (research recommendation).
- Run P and LIVE side by side as two visible books (more work; owner chose a single config).
