# Blind-replica spec: 60/40 with a single arbitrage fund, and the index fund's tracking difference (2026-11-20)

Do NOT read `pipelines/diagnostics/explore_cash_leg_reconciliation.py`, `pipelines/diagnostics/explore_static_long_window_alpha.py`,
`pipelines/diagnostics/explore_after_tax_frontier.py`, `pipelines/diagnostics/explore_after_tax_comparison.py`,
`diagnostics/research/explore/2026-11-19_static_long_window_alpha_replica/replica.py`, or any `*.json` result under
`diagnostics/research/explore/` dated 2026-11-19 or 2026-11-20. You MAY read
`diagnostics/research/explore/2026-11-19_static_long_window_alpha_replica/SPEC.md` (the written rules of the
after-tax static-mix book and its p95 drawdown) and follow it exactly, except for the input prices defined below.

## Inputs (raw)
- TRI: `diagnostics/research/benchmarks/tri/nifty_midcap150_momentum_50_tri.csv` (columns date, tri).
- Fund NAVs (mfapi JSON: `data[]` of {date "dd-mm-yyyy", nav}):
  - Kotak Arbitrage 119771: `diagnostics/replica/phase0/nav_20261120/119771.json`
  - Tata Nifty Midcap 150 Momentum 50 Index Fund 150738: `diagnostics/replica/phase0/nav_20261120/150738.json`

## Part A — 60/40 after tax, 2017-01-02..2026-06-30
- Sessions = TRI dates from 2017-01-01 to 2026-06-30 inclusive.
- index_px: start 100 on the first session; each later session multiply by (1 + TRI daily return − 0.0030/252).
  The first session's return is 0.
- arbitrage_px: start 100; each later session multiply by (1 + r), r = the daily return of 119771's NAV after
  forward-filling the NAV onto the session calendar (NAV dates unioned with sessions, forward-filled, then sampled on
  sessions). A missing return is 0.
- Run the static 60/40 book exactly as SPEC.md describes (₹20,00,000, costs, FIFO lots, tax on the last session on or
  before each 31 March, re-weight after the tax payment, terminal liquidation).
- Report: after-tax CAGR (liquidation value) in %, and the p95 156-week drawdown as SPEC.md defines it.

## Part B — index leg tracking difference
- Common dates = dates present in both the TRI file and 150738's NAVs, from 150738's first NAV onward.
- model = cumulative product over the full TRI history of (1 + TRI daily return − 0.0030/252), sampled on common dates.
- For each calendar year Y: start = last common date before Y (or the first common date for the first year); end = last
  common date in Y. Report fund, TRI and model returns, fund−TRI and fund−model in pp.
- Annualised over the span: (last/first)^(365.25/days) − 1 for each series; report the differences in pp.

Write `replica.py` and `RESULT.md` in this folder.
