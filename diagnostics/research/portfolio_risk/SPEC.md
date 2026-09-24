# Portfolio risk decomposition — SPEC (written before any result)

**Class:** MEASUREMENT. No trial, no screen row, nothing adopted.
Standing counts at writing, read from the ledgers: **screens 19 · sealed opens 2 · n_trials 2.**
**Plan:** Satvik Brain, Phase 1 / Track P1. It answers owner observation 2 — "the Nifty has been in a
big downtrend and we have been in stocks that made our portfolio worse" — and the question finding
0141 left open: if the 2R hit rate is set by the market rather than by selection, how much of this
book *is* the market?
**Written:** 2026-09-24, committed before the diagnostic exists. Definitions and interpretation rules
are fixed now and are not revisited after the numbers come in.

## Prior art — cited, not repeated

- **0141** (this plan's item 1): +2R is reached about as often as for same-day stocks with the same
  volatility and stop distance. The market, not selection, sets the rate.
- **`FINDING_more_slots`**: concentration is load-bearing on this book — 4–5 seats scored Sharpe
  **1.21**, 7 seats 0.97, 10 seats 0.81, against a random null of 0.74. **A low effective bet count
  is therefore not automatically a defect here**, and no interpretation rule below treats it as one.
- **0095 / TRANSFERABILITY_REGISTER**: the vol-target de-gross was promoted on the momentum book and
  **killed on this one at ΔSharpe −0.398**. Any de-gross or exposure rule suggested by these numbers
  is a live sizing change: pre-registration, trial, quarterly review. Nothing here authorises one.
- **0107 / 0115**: the swing × low-vol blend is the standing portfolio-level structure (Track P3).

## Populations

- **A — historical, live configuration.** `run_bhanushali_weekly_rank.backtest` with the live dicts
  (`LIVE_DISCIPLINE`, `LIVE_EXIT`, `LIVE_STALENESS`, `LIVE_PREP`, demerger events) on
  `corrected_universe()`, **2019-01-01 .. 2024-06-30**, capped ₹10L paper book. Gives a daily NAV and
  a trade ledger with entry/exit dates.
  **The window stops at 2024-06-30 so the sealed validation slice (2024-07-01..2026-06-30) stays
  shut.** Outcomes inside it are sealed (open S2 already spent); this study does not read them.
- **B — the live forward book.** Daily NAV `results/portfolio_history_weekly.csv`, weekly holdings and
  weights from the archived snapshots `results/archive/*/paper_portfolio_weekly.json`, closed trades
  from `results/signals_history_weekly.json`. Forward-wall: description only, and every cell carries n.
- **Market:** Nifty-50 close (`run_bhanushali_weekly_crs.NIFTY50_CSV`), the book's own CRS denominator.

## Measures

1. **Market exposure.** OLS of the book's daily returns on the Nifty's: **beta, alpha, R²**, and the
   split of realised return into `beta x market` and residual. Both populations.
2. **Concurrency and correlation.** For each session, the set of names held that day (population A
   from the ledger's entry/exit dates; population B from the snapshots). **Average pairwise
   correlation** of their daily returns over the **trailing 63 sessions, using only data up to that
   day** (point-in-time).
3. **Effective number of bets.** `N_eff = N / (1 + (N − 1) · rho_bar)`, the equal-weight expression —
   reported beside the seat count N. Equal weight is an approximation for population A and is
   labelled as such; population B also reports it on **actual weights** from the snapshots.
4. **Diversification ratio.** `DR = (sum_i w_i sigma_i) / sigma_portfolio`, trailing 63 sessions.
   DR near 1 means the names move as one.
5. **Regime split.** Measures 1–4 computed separately when the Nifty is **≥10% below its trailing
   252-session high** and when it is not. The question is whether correlation rises exactly when
   diversification is supposed to help.
6. **Variance shares (population B only, actual weights).** Each holding's share of book variance,
   own term `w_i^2 sigma_i^2` and covariance terms separately.
7. **R by exit reason, with skew** (the external doc's test 1, on the right book): per exit reason —
   n, mean R, median R, skew, and the share of book R. Population A's ledger and population B's
   closed trades.
8. **Volatility at exit versus entry** (the doc's test 6, reframed for a weekly-close stop): for each
   closed trade, `sigma_63(exit) / sigma_63(entry)`, split by exit reason. Tests whether stops fire
   when volatility expands rather than when the trend fails.

## Uncertainty

- Time-series statistics: **block bootstrap, 63-session blocks, 2,000 draws, seed 20260924**.
- Trade statistics: **cluster bootstrap on ticker**, same draws and seed.
- Flags: a time-series cell below **100 sessions**, or a trade cell below **30 trades**, is marked
  *uninformative* and no rule reads it.

## Integrity

- Prices carry the known unadjusted splits of the raw swing path, so the same exclusions as 0141
  apply to per-name return series: a registered demerger, or a single-session move ≤ −45% or ≥ +90%,
  drops that name-day pair from correlation estimation (counted and reported).
- `nq.brain.io.assert_unsealed` guards any substrate read. This study reads no substrate labels.

## DATA-BLOCKED, stated rather than approximated

**Sector concentration is not measured.** The repo has no committed point-in-time ticker→sector map
(`data/sector_intelligence.pkl` holds sector aggregates, not membership). Rather than label sectors
from a live vendor lookup — which is neither point-in-time nor reproducible — the study reports
**correlation clusters** (average correlation, effective bets, and the largest eigenvalue's share of
total variance), which answer the same question without labels. Sector labels stay DATA-BLOCKED until
a PIT map is built.

## Interpretation rules (fixed before the numbers)

1. **Beta near or above 1 with a residual indistinguishable from zero:** the book's return is market
   exposure. That is an exposure finding for the quarterly review, and it explains a drawdown that
   coincides with the index — it does **not** by itself authorise any de-gross or hedge rule (0095).
2. **Beta well below 1 and a positive residual:** the drawdown is not mainly the index, and the
   selection question stands where 0141 left it.
3. **`N_eff` far below the seat count, and rising correlation in the ≥10% regime:** the book is closer
   to one bet than its seat count suggests, and most so when it matters. Recorded as a risk
   description. Per `FINDING_more_slots` this is **not** read as "hold more names".
4. **Exit-reason skew:** if the stop family carries most of the left tail while a single exit family
   carries the right tail, that is a description of where R comes from — it is not a licence to retune
   an exit, which is a live rule change (pre-registration, trial, review).
5. Any cell flagged uninformative is reported and not interpreted.

**Whatever the result, nothing is adopted.** These numbers describe exposure and outcomes;
program-laws I says they are not features for choosing entries.
