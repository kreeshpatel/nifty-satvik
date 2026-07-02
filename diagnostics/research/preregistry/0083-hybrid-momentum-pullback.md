# 0083 — Volume-confirmed strong-uptrend momentum-pullback: certification (frozen config, DSR gate)

- **ID:** 0083. **Status: PRE-REGISTERED** (config frozen here BEFORE the certification run; no further tuning).
- **Registered:** 2026-07-03, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 100 → 101.
- **Anchor / data:** local OHLCV cache (~700 NSE names, 2017–2026); standalone event-driven strategy (NOT an
  overlay on baseline_v1). Correlation to baseline_v1 = **ρ 0.57** (partial-diversifier momentum variant,
  finding f364db6). Script `scripts/run_hybrid_cert.py`; strategy engine `scripts/diag_ma44_pullback.py`.

## Why this trial exists
A full session of testing Bhanushali's swing methods converged on one recipe that works in-sample. Every
ingredient was validated separately; this trial **freezes the whole recipe and asks the decisive question the
repo asks of everything: is the in-sample Sharpe real, or a Deflated-Sharpe-inflated artifact of a
multi-parameter search?**

## The FROZEN config (locked — no further search)
- **Regime gate:** 44-day SMA rising on 22/44/66-day horizons AND price > SMA AND ≥8% 66-day MA slope (a
  *visible, sustained* uptrend).
- **Entry:** price pulled back to within 2% of the 44-SMA (support) AND a green candle AND **volume > 1.5× its
  20-day average** (HVC confirmation) → buy above the candle's high next day.
- **Stop:** entry − 2.5×ATR(14) (wide, noise-proof). **Target:** 1:3 R:R. **Max hold:** 40 trading days.
- **Sizing:** 2% risk/trade, 20% notional cap/position, ≤10 concurrent, 0.25% round-trip cost.

## Method
`run_hybrid_cert.py`: one full-period backtest → daily equity curve → daily returns. Reports annualized Sharpe;
**block-bootstrap Sharpe 95% CI** (block=63, n=5000); **Deflated Sharpe Ratio at cumulative n_trials = 101**
(the family-wise multiple-testing penalty — the whole program's search burden); and **continuous-slice**
sub-period Sharpes (2017–21 vs 2022–26, sliced from the ONE full run — never a fresh-capital re-run, per the
phantom-gate rule).

## Decision rule (pre-committed)
**PROMOTE to a forward-wall watched sleeve** iff ALL: DSR > 0.95, block-bootstrap Sharpe CI-low > 0, AND both
continuous-slice sub-periods have Sharpe > 0. Positive-but-CI-straddles-0 or DSR ≤ 0.95 → **UNDERPOWERED**.
Negative sub-period or Sharpe ≤ 0 → **KILL**. A PROMOTE routes it to the forward wall (the multi-sleeve fork),
**never** to the frozen cfg on this in-sample search.

## Skeptical prior (honest)
The in-sample Sharpe (~1.0) is the **max over a multi-parameter search** (trend-def × stop-mode × R:R × hold ×
volume-threshold) on ~200–430 trades. DSR at n_trials=101 is a demanding gate, and the strategy is ρ 0.57
momentum (not clean new alpha). Most likely outcome: **DSR deflates below 0.95 → UNDERPOWERED**, i.e. the +1.0
was search-inflated — which we'd have learned cheaply, before any capital. If it *survives* n_trials=101, that
is a genuinely strong signal worth a forward-wall watch. **No retuning toward a pass; the config is frozen.**
