# 0028 — Comparative-RS entry gate on the six-step book: fixes 2025, breaks the book (ΔSharpe −0.14), UNDERPOWERED/WEAK

- **Status:** TRIAL (pre-reg [0086](../../diagnostics/research/preregistry/0086-bhanushali-sixstep-rs-gate.md),
  n_trials 103→104, params frozen before the run). **Verdict: UNDERPOWERED/WEAK — non-improvement.**
- **Date:** 2026-07-04. Script `scripts/run_bhanushali_sixstep_rs.py`; ledger
  `research/exports/bhanushali_sixstep_rs_0086_trades.csv` (458 trades). Same cell as 0084/0085.

## What was tested
The 0085 runner-trail book unchanged, plus an entry gate: signal candle valid only when the stock's RS
line vs the pinned Nifty-500 TRI (`close/tri_close`) is above its own 100-day EMA. Entry-side only;
TRI warmup (pre-2018-02) passes through. Owner hypothesis from the 0027 diagnostic: 2025's −26.8% was
signal failure in the Jan–Feb breadth collapse — require structural outperformance before entering.

## Result (corrected universe, real tiered costs)

| | trades | win | expR | CAGR | Sharpe | MaxDD | 2025 net P&L |
|---|---|---|---|---|---|---|---|
| **0086 RS-gated** | 458 | 40.2% | +0.18 | +8.3% | **+0.444** | **−40.8%** | **−₹0.97L** |
| 0085 ungated | 432 | 39.6% | +0.23 | +11.5% | +0.587 | −37.5% | −₹6.09L |

Slices +0.22/+0.63/+0.41; CI [−0.198, +1.007]; DSR@104 = 0.138. ΔSharpe vs 0085 **−0.143**.

## Root-cause readout (REQUIRED)
1. **The gate wins its own battle and loses the war.** 2025 improves by ₹5.1L — precisely the designed
   effect (stale-bullish weekly buckets no longer buy pullbacks in names underperforming the index).
   But 2024 flips to −₹4.2L and 2022 worsens to −₹5.0L; MaxDD deepens 3.3pp. Net: CAGR −3.2pp.
2. **Why: RS > EMA100 is a LATE confirmation on an EARLY-entry funnel.** The 44-SMA pullback fires near
   trend beginnings; a 100-day RS EMA crosses months into an outperformance run. The gate systematically
   removes the earliest (best) entries and admits mature trends closer to exhaustion — the same
   "IC ≠ portfolio Sharpe" shape as O-019 and the 52-week-high (0079).
3. **Cash-constrained amplification.** Only 14% of signal candles were gated, but in a no-rotation,
   fully-invested book every removed entry re-sequences all later fills — the realized book diverges far
   more than 14%: it is a different portfolio, not the 0085 portfolio minus its 2025 losers.
4. **Fifth entry-side gate to fail program-wide** (O-001 regime gate, 0056 regime-conditional entry,
   O-019 USD tilt, 0079 rankers; now per-stock RS on the swing funnel). The registry pattern is now
   strong: on momentum entries, filters that veto at entry time destroy more edge than the tail risk
   they remove. Exit-side geometry (0025/0084/0085) is where this funnel improves; entry-side gates are
   not.

## Verdict & next setup
**UNDERPOWERED/WEAK, recorded as a non-improvement — 0085 remains the family's best book.** Do not
sweep the RS EMA span, and do not re-propose RS as a rank tilt (O-019 killed that shape on the base)
without a genuinely new formulation. If 2025-style regimes are the concern, the registered avenue is
portfolio-level (the O-018 ERC multi-sleeve / vol-target mechanics), not another entry veto. 0085 (not
0086) goes to the 2026-10-01 review packet.
