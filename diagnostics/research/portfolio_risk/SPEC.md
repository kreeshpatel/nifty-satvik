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

---

## Amendment A1 — 2026-09-24, before the reported run: the corporate-action hold is live-only

The first run of population A used the full live configuration, **including the corporate-action hold**
(`LIVE_CA_HOLD`, the Phase-0 guard). That guard freezes a held position after an unregistered ≥15%
single-session drop **until the owner resolves it**. Live, resolution takes a day. In a 5.5-year
reconstruction there is no owner, so a frozen position never exits and its loss is never realised.

Measured on 2019-01-01..2024-06-30:

| live config | trades | CAGR | Sharpe | frozen at the end |
|---|---|---|---|---|
| with the hold | 52 | **52.8%** | 1.86 | 4 |
| without the hold | 71 | **39.4%** | 1.67 | 0 |

The four freezes are circuit-limit crash days, not corporate actions: VBL −20.0% and JSL −17.0%
(March 2020), IIFL −20.0% and SWANENERGY −18.5% (March 2024).

**Population A therefore runs WITHOUT the hold.** Registered demerger events (B′) stay on: those are
historical facts, not an operational review. The hold is an operational mechanism for a book with a
human attached, and it does not belong in any historical reconstruction.

Two things this also records, outside this study's scope:
- the guard's real-world firing rate on the live book is about **0.7 a year** on a 5-seat book (4 in
  5.5 years), which matches the 1–3 a year estimated when it was built;
- whether a live hold should **auto-release** after N sessions with no corporate action found is a live
  rule change — pre-registration, trial, quarterly review. It is noted, not proposed here.

Nothing else in the SPEC changes.

## Amendment A2 — 2026-09-24, after the red-team read

The read confirmed the pipeline (an independent re-run reproduced population A field for field, and
three days of `rho_bar` / `div_ratio` were recomputed from raw closes and matched exactly), and
rejected two readings and two statistics.

**A2.1 — the regime claim was one episode.** 90 of the 171 index-drawdown sessions are the COVID crash
(2020-03..2020-07). Excluding it, drawdown `rho_bar` is **0.160 against 0.148 in calm** — nothing. The
fall in effective bets is then mostly *fewer names held* (6.5 vs 7.8), not more-correlated names, since
`N_eff` scales with N. The stitched 171-session mask also breaks the 63-session block bootstrap
(~2.7 blocks per replicate, blocks straddling episode boundaries), so that CI is not a CI.
**Added:** every contiguous drawdown episode of ≥30 sessions is reported separately, plus a
drawdown-excluding-the-largest-episode cell, plus `mean_n_held` per cell. **No regime claim is made
unless it survives excluding the largest episode.**

**A2.2 — `share_of_total_R` inverts when the book loses.** The live cell shipped
`stop: sum_R −16.32, share +0.945` — a family that lost 16R reading as +94.5% of R. The share is now
**undefined (None) whenever total R is not positive**, and `sum_R` in R units is the reported number.

**A2.3 — trade cells now carry the CI the SPEC promised.** §Uncertainty specified a cluster bootstrap
on ticker for trade statistics; the first implementation computed none.
`nq.brain.portfolio.cluster_bootstrap_mean` is wired into every exit-reason cell.

**A2.4 — the live window is labelled by its data.** The summary said `end: 2026-09-23` (the price
fetch) while the NAV ends **2026-09-15**; the 50-session window is 2026-07-07..2026-09-15. Now reported
as `nav_window_end` and `prices_fetched_to`.

**A2.5 — A1's stated mechanism was wrong; its decision stands.** A1 said a frozen position's "loss is
never realised". In fact all four frozen names ended far UP (VBL 647.97 against an entry of 47.04; JSL
815.85 against 38.89; SWANENERGY 586.90 against 305.00; IIFL 513.80 against 332.72). The hold inflated
the book by freezing **winners the runner exit could never sell**, not by hiding losses. Turning it off
still moves the book down (52.8% → 39.4% CAGR), so the decision is not result-shopping — but the reason
is corrected here rather than left to be cited again.

**A2.6 — interpretation rule 5 binds harder than the first write-up did.** The stop cell (n=29) and the
volatility-at-exit cell are **below the 30-trade bar**. They are reported and **not interpreted** — in
particular, the study makes **no statement** about whether stops fire on volatility expansion.

Also recorded, not claimed: the notional cap binds on every entry (risk 2% ÷ a stop distance capped at
10% is always ≥ 20% of sizing equity), so equal-weight is a close approximation for population A —
actual-weight DR 1.84 against 1.92 equal-weight, correlation 0.93.
