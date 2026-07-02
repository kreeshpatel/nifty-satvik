# 0021 — Volume-confirmed momentum-pullback (the Bhanushali-distilled hybrid): real & stable, but UNDERPOWERED at the program's search burden

- **Status:** **UNDERPOWERED** (DSR 0.60 < 0.95). A real, sub-period-stable positive-Sharpe strategy that is
  **not certifiable in-sample** — the same wall as every overlay. Do NOT put in the frozen cfg. Candidate for
  a **forward-wall watched sleeve** (owner decision), lower priority than low-vol.
- **Date:** 2026-07-03. Pre-registration: [`diagnostics/research/preregistry/0083-hybrid-momentum-pullback.md`](../../diagnostics/research/preregistry/0083-hybrid-momentum-pullback.md).
- **Type:** TRIAL (1 frozen config; cumulative_n_trials 100 → 101). Standalone event-driven strategy (NOT a
  baseline_v1 overlay), ρ 0.57 to base. Scripts `scripts/run_hybrid_cert.py` + `scripts/diag_ma44_pullback.py`.

## What was certified (frozen config, no retuning)
The recipe distilled from a full session of testing Siddharth Bhanushali's swing methods (captured in
[`research/bhanushali_swing_rules.md`](../bhanushali_swing_rules.md)): **visible 44-SMA uptrend** (rising on
22/44/66d + price>MA + ≥8% slope) → **pullback to the MA + green candle + HVC volume >1.5×20d avg** → buy above
the high, **2.5×ATR stop**, **1:3 target / 40-day hold**, 2% risk. It is a **momentum-continuation** strategy.

## Result
| metric | value |
|---|---|
| trades | 427 |
| win-rate | 47.8% |
| CAGR | +22.8% |
| MaxDD | −31.1% |
| full daily-Sharpe | **+1.091** |
| bootstrap 95% CI | **[+0.40, +1.78]** — excludes 0 |
| 2017-21 / 2022-26 Sharpe (continuous-slice) | **+1.18 / +1.00** — stable both halves |
| **DSR @ n_trials=101** | **0.602** — FAILS the >0.95 gate |

Gates: CI-low>0 ✓, both sub-periods>0 ✓, **DSR>0.95 ✗** → **UNDERPOWERED**.

## Root-cause readout (REQUIRED)
The strategy is **genuinely real in-sample** — the bootstrap CI excludes zero and the Sharpe is impressively
*stable* across 2017-21 (+1.18) and 2022-26 (+1.00), which overfit strategies usually don't manage. But the
+1.09 Sharpe is the **max over a multi-parameter search** (trend-definition × stop-mode × R:R × hold ×
volume-threshold), and the **Deflated Sharpe Ratio at the program's cumulative 101-trial burden deflates it to
0.60** — below the 0.95 certification bar. In plain terms: at the number of configurations the program has
tried, a Sharpe of ~1.0 on ~430 trades is not statistically distinguishable from the best of many attempts.
This is the identical wall every overlay hits here (low-vol 0081 DSR 0.32, momentum×low-vol ERC 0.32, the whole
in-sample program). **The discipline worked exactly as designed:** it caught a great-looking backtest before it
became false confidence.

## What we actually learned (durable)
Bhanushali's momentum-continuation *principles*, systematized rigorously, **do** produce a real edge on our
data — and the session validated the specific levers: a **visible/sustained** trend beats a marginal tick
(doubled the entry edge), **volume/HVC confirmation** adds (doubled it again), and **wide ATR stops + letting
winners run** flip the risk geometry from losing to winning (matching our own 0047/0071 findings). His
mean-reversion levers (RSI<35, Bollinger lower-band) do not. But — the core program truth stands: **at ~34
independent windows / 101 trials, in-sample cannot certify a ~1.0 Sharpe momentum variant.** The forward wall
is the only judge.

## Next setup (disposition)
- **NOT the frozen cfg** (UNDERPOWERED; no in-sample promotion — the pre-reg's DSR gate failed).
- **Forward-wall watch candidate**, like the low-vol sleeve — an **owner decision at a quarterly review**, not
  an in-sample promote. **Lower priority than low-vol (0081):** this is ρ 0.57 *momentum* (a partial diversifier
  of the *same* factor the base already trades), whereas low-vol (ρ 0.54) diversifies a *different* factor and
  is the stronger multi-sleeve candidate. The forward wall's 2-shadow cap means one slot; low-vol has the prior
  claim.
- **The transferable, already-owned pieces:** wide-stop / let-winners-run is already in the base exit config;
  the liquidity filter is already the base universe rule. The one genuinely-new, not-yet-owned lever is
  **volume/HVC confirmation** — a candidate conviction feature for the Phase-5 model (judged forward, per the
  learning-bot plan), if pursued.
