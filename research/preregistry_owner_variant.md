# PRE-REGISTRATION — Owner rule-faithful variant ("0094-RF")

**Frozen 2026-07-16, BEFORE the run. Params fixed by the owner; NO retuning under any outcome (R4/R11).**

## The frozen config

```python
P = prep_weekly_rank(ohlcv,
        slope_min=0.06,              # C4  visible uptrend (was 3%/13wk)
        prior_above_n=2,             # C5  >=2 of prior 4 weeks CLOSED ABOVE the SMA
        prior_above_lookback=4,
        require_progress=True)       # C1/C2 signal close > prior week's close
m = backtest(P, mem, start="2017-01-01", eq0=EQ0,
        entry_mode="buystop",        # C3  fill only THROUGH the signal-week high
        stop_atr_mult=1.0,           # C3b stop = entry - 1.0 x weekly ATR (~7.8%, preserves size)
        ext_floor=0.0,               # C5b fill must land ABOVE the SMA
        no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)   # P2 exit unchanged
# grade: ALL-GRADES (no a_grade filter)
```

Exit (P2), sizing (2% risk / Rs10L), universe (corrected, 788), and CRS-rank fill order are **unchanged**.

## What each lever fixes (owner chart review — all 9 observations verified in OWNER_CHART_REVIEW.md)

| lever | value | the trade that motivated it |
|---|---|---|
| `slope_min` | 0.06 | RAIN (+4.1% slope) — "not even in a proper visible uptrend" |
| `prior_above_n=2/4` | 2 of 4 | ZFCVINDIA (6 wks below, one +30% candle), RCF (5 of 6 below) |
| `require_progress` | True | RAINBOW (green, but closed 1444.8 vs prior 1454.3) |
| `entry_mode="buystop"` | on | APOLLOHOSP/SOBHA/TARIL — every reviewed trade filled BELOW the signal high |
| `stop_atr_mult` | 1.0 | neutralises 0088's cause: width ~7.8% vs the taught rule's 12.8% |
| `ext_floor` | 0.0 | KENNAMET (fill −1.5%), NAVA (−1.8%) — filled below the SMA |

## Calibration note (an error found and corrected BEFORE freezing)

I first offered "2.5x weekly ATR ~= 7%". **That was wrong.** Measured weekly ATR(10) median = **7.83%** of
price, so 2.5x = **19.6%** — *worse* than the 12.8% that killed 0088. The repo's 2.5x/4x ATR results are
**DAILY**-ATR multiples (daily ATR ~3.5%) and do not transfer to weekly bars. The owner re-chose **1.0x
(7.8%)**, which delivers the stated intent: preserve the ~7.1% risk width and the position size.

## Pre-declared expectations (so nothing is rationalised after the fact)

- **`entry_mode="buystop"` is 0088's entry**, which was KILLED (Sharpe +0.215, CAGR +2.3%) — but 0088
  paired it with the candle-low stop (12.8% width). `stop_atr_mult=1.0` is the **new formulation**: it
  attacks 0088's measured cause of death. This is the one genuinely untested idea in the spec.
- **`slope_min` tightening resembles 0092** (KILLED) and **`ext_floor`/`require_progress` measured 0.47 /
  0.42 alone** — but the book is **chaotic under fill perturbation** (G1 0.47, G2 0.42, G1+G2 0.97), so
  single-lever numbers are near-noise and are NOT predictions for the coherent spec.
- **Fewer trades are expected** (five conjunctive tightenings + a confirmation trigger). If the count
  collapses, that is itself the finding.

## Gates (pre-committed)

| benchmark | value |
|---|---|
| live all-grades baseline (22-26 slice) | **1.29** |
| A-only traded book | 1.17 |
| **random-selection null** | **0.74** (sigma 0.24) |

Judge on the **2022-26 continuous slice** (R3). Report the **null percentile** too — given the chaos
finding, "beats the baseline" is weaker evidence than "beats the null distribution". Gaps < ~0.2 are inside
selection noise.

**UNDERPOWERED / KILL is a first-class outcome. No retune. Nothing ships in-sample (R11).**
