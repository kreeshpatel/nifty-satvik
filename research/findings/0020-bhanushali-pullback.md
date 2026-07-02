# 0020 — The Bhanushali 6-step swing setup, systematized & tested "all together": a real but trivial entry edge, KILLED by costs

- **Status:** **MEASUREMENT / standalone candidate** (NOT a baseline_v1 overlay — different strategy and horizon; no n_trials cost). Owner-requested test of an external YouTube strategy (Siddharth Bhanushali, "6-Step Swing Trading Strategy"), tested *combined* per the owner's "let's try these all together."
- **Date:** 2026-07-03. Script `scripts/diag_bhanushali_pullback.py` (event-driven, standalone).

## What was tested (the systematizable core — steps 3 + 5; steps 1/4/6 are discretionary psychology)
Rising-44-SMA **pullback** + green-candle-at-support trigger → enter above the green candle's high; stop below
its low (floored at 4% so 2-3% noise doesn't shake us out — the owner's point); target R:R 1:2; hold 3-10 days;
exit ONLY on stop/target/time (never a red day). 1% risk/trade, ≤15 concurrent, 0.25% round-trip cost.

## Result
| | value |
|---|---|
| trades | 1,889 |
| win-rate | 41.4% |
| avg R / expectancy | **+0.02R** (≈ zero gross) |
| CAGR | **−16.3%** |
| Sharpe | **−0.714** |
| MaxDD | **−83.8%** |

**Implementation-independent entry check** (forward return after a signal vs the universe, removes exit/sizing
from the verdict): signal +0.59% / +1.02% (5d/10d) vs universe +0.44% / +0.89% → **edge +0.13–0.15pp**,
win-rate **51% vs 50%**. A real but negligible whisper — far below the ~0.25% round-trip cost.

## Root-cause readout (REQUIRED)
The mechanical entry (buy pullbacks to a rising 44-SMA on a green candle) has a **tiny real edge** (+0.15pp,
~1pp win-rate over a coin flip) — Bhanushali is not teaching nonsense — but it is **an order of magnitude too
small to survive transaction costs.** The −0.71 Sharpe is not primarily an implementation artifact: the
entry-edge check confirms the entry itself is near-edgeless, so no exit/RR/sizing tweak can rescue it (a
flat-expectancy entry can't be saved by better exits; the wide stop, correctly baked in, didn't help). The
short-horizon pullback's failure mode is buying dips that keep falling in the 2020/2022 drawdowns (41% WR).
Where the strategy *does* work is exactly what a backtest can't capture: **discretionary judgment** (which
pullback, which stock, cutting bad ones early) + the **psychology/discipline** steps (mindset, patience,
checklist). That is real education for a *manual* trader; it is not a *systematic* edge after costs.

Consistency with the program: this whisper (+0.15pp, IC ≈ 0.01–0.02) is far weaker than the base
`sma200_slope_63` (IC 0.062) — the same lesson as the 0079 technical zoo and 0004 chart-structure KILL: a
mechanical technical/price-action entry carries ~0 exploitable edge; the base's 63d momentum is genuinely
stronger. Combining several individually-weak/killed components ("all together") did not resurrect them.

## Addendum (2026-07-03) — the RSI variant (Bhanushali ch.6 checklist), same autopsy
Systematized the RSI checklist too (weekly-44MA-uptrend ≈ rising 220d SMA + daily RSI<35 uptick + green
candle; `scripts/diag_rsi_pullback.py`, Wilder RSI(14)). Implementation-independent entry-edge (forward return
after signal vs universe, 24,229 signals): **5d −0.02pp / 10d −0.24pp / 20d −0.33pp** — the signal
**UNDERPERFORMS** the universe (win-rate 52% vs 51% but lower mean = mean-reversion catching falling knives).
Worse than the 44-SMA pullback (+0.15pp). Confirms the RSI §11 KILL (0079) on this exact oversold-in-uptrend
formulation. Trendlines/breakouts: the systematic form is Donchian-channel breakout = `donchian_pos_126`,
already tested tie-or-lose in the C4 horse-race; visual chart-pattern "imagination" is the 0004 chart-structure
KILL (numeric) or a lookahead/PIT-impossible vision layer — the chart *is* the price, so pattern-reading adds
no information the price doesn't already carry.

## Verdict
**KILL** as a systematic strategy (both the 44-SMA-pullback and RSI-oversold variants). Recorded so the 44-SMA-pullback / candlestick-trigger class is not
re-proposed. The transferable, *true* piece — wide stops / don't-exit-on-noise / hold for target-or-stop — is
already consistent with the base's exit geometry; it is good risk discipline, not an alpha source.
