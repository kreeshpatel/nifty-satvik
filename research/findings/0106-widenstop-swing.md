# Finding 0106 — Widening the stop KILLs the book: the 0094 stop is a robust optimum

**Verdict:** **KILL** — keep the candle-low stop. Pre-reg [0106](../../diagnostics/research/preregistry/0106-widenstop-swing.md);
engine `scripts/run_bhanushali_weekly_rank.py` (cfg-gated `stop_widen_pct`). n_trials 133→134.

## Result (frozen 0094, corrected universe 2017-2026)
| | Sharpe | CAGR | MaxDD | trades | win | stops | time-exits |
|---|---|---|---|---|---|---|---|
| stop = candle low (0094) | +1.132 | 24.7% | −42.4% | 255 | 59% | 66 | 164 |
| **stop widened +20%** | **+0.785** | **15.5%** | −41.4% | 284 | 55% | 69 | 197 |
| Δ | **−0.347** [−0.72,+0.11] | −9.2pp | +0.9pp | +29 | −4pp | +3 | +33 |

Pre-committed bar **4/4 FAIL**. Baseline byte-identical.

## Root cause
The frozen 0094 stop is the signal-week low, already ~14% below entry — **already wide.** Widening to ~17%
barely changed the stop-out count (66→69) so there was no recovery benefit; instead it **pushed the +2R
target further away** (needs a bigger move to fire — 0094's exit mix is already sma_break/time-heavy),
**shrank position sizes** (wider stop → smaller size → capped upside), and let **33 more marginal trades
limp to the time cap** (164→197). expR collapsed +0.48→+0.30, CAGR halved for +0.9pp of DD.

## The exit is a robust optimum — the lever avenue is closed
Both directions KILL: tighten the FILL (hard_stop, 0105) destroys the intra-week recoveries that ARE the
edge; widen the LEVEL (0106) recedes the target and shrinks size. The 0094 stop cannot be moved either way.
With the entry side also exhausted (body-frac null; ext_cap-tighten KILL 0104), **every perturbation of the
frozen 0094 now deflates** — confirmation the book is well-tuned and the ~1.13 in-sample Sharpe is fixed.
The remaining value is operational (decision memo, risk gate, barbell sizing) + forward certification, not
another backtest lever.
