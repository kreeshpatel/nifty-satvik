# 0006 — Earnings-proximity gate

- **ID:** 0006
- **Registered:** 2026-06-02
- **Holdout:** unseen-universe → forward-wall. Dev for generation only.
- **n_trials (cumulative):** ~52.
- **Status:** PENDING

## Hypothesis

Signals fired within N trading days of a scheduled earnings date have higher
variance and lower risk-adjusted expectancy than "clear" signals; gating them
out (or down-sizing) improves the strategy's Sharpe without collapsing trade
count. Data already exists — `src/data/earnings_calendar.get_days_to_earnings`
(`data/earnings_calendar.json`); this is a no-retrain GATE, not a feature.

## Primary metric

**Sharpe** (risk-adjusted, since the thesis is variance) of the gated strategy
vs ungated, on the unseen universe, with a 95% bootstrap CI on the difference.
Secondary: per-trade expectancy + variance of near-earnings (≤5d) vs clear
signals; trade-count retention.

## Decision rule (fixed in advance)

- **SUPPORT:** near-earnings signals show materially worse risk-adjusted
  expectancy AND gating lifts Sharpe with ≥80% trade-count retained AND DSR>0.95.
- **KILL:** no expectancy/variance difference between near-earnings and clear,
  OR gating needs to drop >20% of trades to help.
- **INCONCLUSIVE:** overlapping CIs.

## Priors / note

B1 (2026-06-02) showed the 0.92 gate is already well-calibrated on
*which names* (95.5% realized) — so a which-names gate is **lower-value than
target calibration (0007)**. Run after 0007. Moderate prior; earnings variance
is real but the gate is already strong.

## Result (2026-06-02) — DATA-LIMITED / no support; do not gate

Tagged the 412 unseen-universe backtest trades (live ensemble) by
days-to-nearest-earnings via `yf.earnings_dates`.

- **Coverage 37.4%** (154/412 trades had a known earnings date within 90d) —
  yfinance historical earnings only covers ~recent years, as flagged. Cannot
  conclude robustly (the DATA caveat in the pre-reg).
- On the covered subset, **near-earnings (≤5d) did slightly BETTER, not worse**:
  +5.56%/trade, 71% WR, std 11.5 vs clear +3.68%, 66% WR, std 11.1 — the OPPOSITE
  of the gating hypothesis, with similar variance.

**Verdict: no support for an earnings gate** (and the limited evidence runs
against it — near-earnings signals are fine, so gating would drop good trades).
Consistent with B1 (name-selection already well-calibrated). A rigorous test
needs proper historical earnings data; defer with delivery% (0010) if pursued.

Fourth disciplined edge experiment (0004, 0005, 0007, 0006) to find no
improvement over the current model — the model is well-tuned w.r.t. the
information it has; the only un-tested edge lever left is genuinely orthogonal
NEW data (delivery% / options).

_(pre-registration above this Result section is immutable)_
