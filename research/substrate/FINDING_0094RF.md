# 0094-RF — the owner rule-faithful variant: KILLED (pre-registered run, 2026-07-16)

Pre-reg: `research/preregistry_owner_variant.md` (params frozen by the owner BEFORE the run).
Reproduce: `python scripts/run_0094rf.py`. Live config untouched. Per R11: a FINDING, **no retune**.

## Result — worse than random

Signal pool 8,518 -> **4,857 windows (57%)** after the three signal-side guards.

| config | trades | Sharpe | CAGR | MaxDD | win | meanR | med-risk | **22-26** |
|---|---|---|---|---|---|---|---|---|
| BASE (live rule) | 168 | 1.03 | 21.2% | −34.8% | 54% | +0.616 | **14.2%** | **1.29** |
| **0094-RF (frozen spec)** | 154 | **0.38** | **5.9%** | −36.9% | **43%** | **+0.202** | 8.2% | **0.35** |

**0.35 vs baseline 1.29 (−0.94), and −1.6 sigma BELOW the random-selection null (0.74).** KILLED.

## Root cause — the ATR stop (my lever) did the damage, for the OPPOSITE reason I argued

| config | risk% | **22-26** |
|---|---|---|
| BASE | 14.2% | **1.29** |
| SIGNAL guards only (C1/C4/C5) | 12.6% | 0.89 |
| FILL changes only (C3/C3b/C5b) | 8.6% | 0.65 |
| 0094-RF (both) | 8.2% | **0.35** |
| **buystop + TAUGHT candle-low stop** | **15.7%** | **0.96** |
| **ATR stop 1.0x only (in-range fill)** | 9.5% | **0.28** ← worst single lever |

**Both halves hurt and they compound.** But the decisive component is the **ATR stop**: alone it scores
**0.28**, while the owner's buy-stop paired with the **taught candle-low stop** scores **0.96** — nearly 3x
better than the "fix" designed to rescue it.

**The reasoning was inverted.** I argued pre-reg 0088 died because entry-at-high + stop-at-low made stops
**too wide** (12.8%), and tightened toward 7.8%. The data says the opposite: **wider stops are protective on
this book** (15.7% -> 0.96; 9.5% -> 0.28). It is consistent with the earlier measurement that **48% of
stop-outs recover above the entry within 12 weeks** — the stops were already too tight, and this tightened
them further. **0088's width diagnosis was measured on a different book (the daily six-step 0085 family)
and does not transfer to the weekly 0094 book.**

## Two calibration errors (mine), recorded

1. Offered "2.5x weekly ATR ~= 7%". Weekly ATR(10) median is **7.83%**, so 2.5x = **19.6%**. Caught before
   freezing; the owner re-chose 1.0x.
2. Calibrated 1.0x against the **uncapped pool's** 7.1% median stop. The **traded** book's median is
   **14.2%** (CRS funds extended names, which carry naturally wider stops). So 1.0x delivered ~8.2% —
   roughly **half** the width the live book actually runs. The lever never tested "preserve the width"; it
   tested "halve the width".

## What the owner's observations are worth (they were all correct)

The five verified chart-review flaws are real: the touch rule cannot distinguish a pullback from a recovery
through the SMA (ZFCVINDIA/RCF), `qgreen` requires no progress (RAINBOW), and the in-range fill can land
below the SMA (KENNAMET/NAVA). **Fixing them still costs 0.40 on the slice** (guards-only 0.89 vs 1.29) —
another instance of the standing law: **every filter removes the deep entries that carry the tail.**

## The one untested residue

**buystop + a WIDER stop** (~1.8x weekly ATR ~= 14.2%, i.e. actually preserving the traded book's width) is
the version my calibration should have produced. It is untested and would be a **NEW pre-registration (K=2)**
— an owner decision, not a retune of this one. Prior: buystop + taught-low (15.7%) already reaches 0.96,
still below 1.29.
