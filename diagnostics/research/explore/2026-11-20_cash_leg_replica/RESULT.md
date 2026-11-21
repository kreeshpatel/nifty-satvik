# Blind replica result — 60/40 with Kotak Arbitrage, and index-fund tracking difference (2026-11-20)

Written from `SPEC.md` (this folder) and `../2026-11-19_static_long_window_alpha_replica/SPEC.md` only. None of the
files on the do-not-read list were opened. `replica.py` imports nothing from `nq/` or `pipelines/`.
Run: `.venv/Scripts/python.exe diagnostics/research/explore/2026-11-20_cash_leg_replica/replica.py`.

Inputs as pinned: TRI csv (last row 2026-11-13), mfapi NAV snapshots `nav_20261120/119771.json`,
`nav_20261120/150738.json`.

## Part A — static 60/40 after tax, 2017-01-02..2026-06-30

| quantity | replica |
|---|---|
| sessions | 2,351 (2017-01-02..2026-06-30), 3,466 calendar days |
| index_px end (start 100) | 664.957 |
| arbitrage_px end (start 100) | 181.004 |
| tax days | 2017-03-31, 2018-03-28, 2019-03-29, 2020-03-31, 2021-03-31, 2022-03-31, 2023-03-31, 2024-03-28, 2025-03-28, 2026-03-30 |
| final cash after liquidation and final tax | ₹79,58,693.77 |
| total tax paid | ₹7,63,399.07 |
| **after-tax CAGR** | **15.667%** |
| **p95 156-week drawdown** | **23.968%** (T = 495 weekly returns) |

## Part B — Tata Nifty Midcap150 Momentum 50 Index Fund (150738) vs TRI vs model (TRI − 0.30%/252 daily)

Common dates 2022-10-31..2026-11-13 (992 dates, 1,474 days). 8 fund NAV dates are not TRI dates and 11 TRI dates
after the fund's start have no fund NAV; both are dropped by the intersection.

| year | start | end | fund % | TRI % | model % | fund−TRI pp | fund−model pp |
|---|---|---|---|---|---|---|---|
| 2022 | 2022-10-31 | 2022-12-30 | −5.201 | −4.618 | −4.667 | −0.583 | −0.534 |
| 2023 | 2022-12-30 | 2023-12-29 | 49.842 | 52.480 | 52.035 | −2.639 | −2.193 |
| 2024 | 2023-12-29 | 2024-12-31 | 30.894 | 32.298 | 31.907 | −1.404 | −1.013 |
| 2025 | 2024-12-31 | 2025-12-31 | −4.202 | −3.462 | −3.748 | −0.740 | −0.455 |
| 2026 | 2025-12-31 | 2026-11-13 | 3.148 | 3.788 | 3.523 | −0.641 | −0.375 |

Annualised over the span: fund **16.268%**, TRI **17.664%**, model **17.317%**;
fund−TRI **−1.395 pp**, fund−model **−1.048 pp**.

## Ambiguities and the reading taken

| # | ambiguity | reading taken | sensitivity |
|---|---|---|---|
| A1 | Arbitrage return: computed on the session-sampled ffilled NAV, or on the union calendar and then sampled (which would drop returns that land on 3 NAV-only dates in the window)? | Sample on sessions, then pct change (spec wording "then sampled on sessions"; this preserves the NAV level ratio exactly). | Alternative: CAGR 15.666%, p95 23.969% (≈0.001 pp). |
| A2 | Buy cost: does the 0.005% come out of the target amount or on top of it? "cash is the residual" | Buy units worth exactly (target − held value); cost paid on top from cash, so cash can go slightly negative (≈ −₹100 at start). Sell proceeds credited net of 0.001%. | Not tested; order of ₹100 per rebalance. |
| A3 | Is the taxable gain net of the sell cost? Spec sets lot cost = price (buy cost not in basis) but does not define gain. | Gross gain = units × (sale price − lot price); neither cost enters the gain. | Net-of-sell-cost gain: CAGR 15.6668% vs 15.6668%, tax ₹7,63,386 vs ₹7,63,399 — immaterial. |
| A4 | TRI daily return for Part A: pct change on full history or within window? | Full history, first session forced to 0 (identical either way). | None. |
| A5 | Weekly series in p95: weeks with no session? | `resample('W-FRI').last().dropna()`. | Not tested; no empty weeks expected beyond holidays. |
| A6 | Tax rules applied uniformly 2017–2026 (20% STCG, 12.5% LTCG over ₹1.25L, both instruments equity), although actual Indian rates/exemptions changed in 2018 and 2024. | Followed spec literally. | Spec-defined, not an ambiguity in implementation, but a modelling assumption worth stating. |
| A7 | Part B model base: first TRI row. | Model = 1.0 on the first TRI row (no return, no fee); only ratios are used, so irrelevant. | None. |
| A8 | Part B year boundaries: "last common date before Y" for the first year uses the first common date (2022-10-31), so the 2022 row is a 2-month stub. Final year 2026 ends at TRI's last date 2026-11-13 (fund has NAVs to 2026-11-20 but they are not common). | As written. | — |
| A9 | Fractional unit residuals at liquidation (float). | Sell loop stops when lots exhausted. | None. |

No coin-flip readings materially move any reported number: the two tested alternatives (A1, A3) move CAGR by ≤ 0.001 pp
and p95 by ≤ 0.001 pp.
