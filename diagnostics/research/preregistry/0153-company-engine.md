# 0153 — Company engine: slow core, fast timing

**Status: DRAFT. To be signed by the owner at the January 2027 review. Nothing in this file may be run as a screen
or trial before that signature.**

**Written:** 2026-11-20, before any candidate signal for this engine has been computed or evaluated. The Phase 0
work that accompanies this file (data panels, holdout guard, calibrated gate harness) computes no candidate signal.

**Standing counts at registration:** screens 24 · sealed opens 4 · n_trials 3. These were read from
`diagnostics/research/label_screen_ledger.md` and `diagnostics/research/n_trials.json`. The task brief that ordered
this file quoted screens as 25; the ledger says 24, and the ledger is the authority. Nothing in this file increments
any counter. Increments happen at the January review, in their own commits, before each run (§e).

## a) Thesis

The engine predicts **what drives prices**, not prices themselves. Those drivers are earnings, earnings surprise and
stock-specific crash risk.

Its shape is **"slow core, fast timing"**:

- **The core ranks on slow information and holds for months.**
  - L1, an earnings-trend forecast, serves as fundamental momentum and quality.
  - L5, stock-specific crash risk, serves as an exclusion.
- **Fast earnings information only times trades into names the core already wants.**
  - The fast layers are L2 (earnings surprise) and L3 (earnings seasonality).
  - They can delay a sale.
  - They never create extra trades.
- **L4 comes last.** L4 is spill-over from early reporters to their peers. It is tested only if the other layers pass
  and the peer clusters are stable.

## b) Layers and kill rules

Every bar below is fixed now and is not revisited after any result is seen.

**L1, earnings-trend forecast.**
- It must beat the seasonal random walk by at least 5% in mean absolute scaled error, out of sample.
- The seasonal random walk is the same quarter last year, with drift.
- L1 is price-free. Its forecast accuracy may therefore be evaluated through 2026, including 2024-07-01..2026-06-30.
  No return statistic on that window is allowed.

**L5, stock-specific crash risk.**
- **Target:** a stock-specific drawdown of 25% or more within 63 sessions. Stock-specific means the stock minus beta
  times the market.
- **Evaluation:** clustered by date, out of sample.
- **Bars, all of which must hold:**
  - AUC of at least 0.65.
  - Calibration slope within 0.8–1.2.
  - Excluding the top-risk decile lowers the universe's p95 156-week drawdown, without cutting its return by more than
    1pp a year.

**L2 (earnings surprise) and L3 (earnings seasonality).**
- Gross alpha against a beta-matched static mix must reach t ≥ 2.6. The t is Holm-adjusted across the 6 registered
  layers (L1–L6).
- It must hold with an execution delay of anywhere from 0 to 5 sessions.
- It must hold in the tradable slice, where ADV is at least ₹5 cr.
- It must show no significant decline across years, by a slope test on yearly alpha.
- Its correlation to the 0001 ranker must be below 0.3.
- The low-momentum tercile must not straddle zero. This is the failure that ended 0128.

**Every layer must pass the friction test.**
- Friction = signal turnover × 2 × event-day cost + short-term capital-gains tax drag at 20% plus cess.
- Friction must be below the layer's gross alpha.

**L6, conformal bands.** The bands must hold their stated coverage out of sample.

## c) Book (fixed now)

- **Holdings:** 25 names, equal weight.
- **Entry and exit:** a name enters when it ranks in the top 25 and exits when it ranks below 40. The gap is
  hysteresis.
- **Timing:** scan weekly, rebalance monthly.
- **Resizing:** a holding is resized only if its weight drifts more than 1.5pp from target.
- **Sale order:** losses first, then long-term lots.
- **Equity share (static, no vol-targeting):**
  - The equity share is the largest share, rounded down to 5pp, whose p95 156-week drawdown is at most 25%.
  - That drawdown is measured by stationary bootstrap: mean block 8 weeks, 10,000 draws, training window only.
  - The rest of the capital goes into the arbitrage fund.

## d) Evidence and holdout

- **Training window:** ends 2024-06-30.
- **Sealed holdout:** 2024-07-01..2026-06-30, for every return-based test.
  - It is labelled **"regime known"**: it can confirm, but it cannot prove.
  - The holdout is enforced in code by `nq/research/holdout.py`. Any return series past 2024-06-30 raises an error
    unless an owner unseal token is passed.
- **Deciding test:** 26 weeks of forward paper trading against 60/40 index/arbitrage, after tax.

## e) Accounting

- **Screens:** each layer is one screen (L1–L6, so 6 screens).
- **Trial:** the combined book is one trial.
- **No other degrees of freedom:** everything in (c) is fixed.

## f) Success

The engine succeeds only if, after tax, at a p95 drawdown of at most 25%, it beats 60/40 in the holdout **and** over
26 weeks of paper trading. Otherwise core capital stays in 60/40.

## Owner signature

_Unsigned — January 2027 review._

## Amendment note, 2026-11-20 (owner decision on PR #218): known limits

No threshold changes.

**Known limits.**

- On the training window, the layer-gate harness passes the 0001 momentum ranker: gross alpha t 3.51
  (`diagnostics/research/explore/2026-11-20_phase0_calibration.json`).
- 0001 has no full-run alpha. The training window favours momentum, so a gate pass on this window is not, by itself,
  evidence of an edge.
- The rule that a layer's correlation to the 0001 ranker must be below 0.3 guards against momentum-like signals
  passing for this reason.
- The sealed holdout (2024-07-01..2026-06-30) and the 26-week paper test decide the rest.

## Amendment note, 2026-11-20 (owner decision on PR #219): debt/equity cannot be a core L5 input

No threshold changes.

- In the results XBRL, balance-sheet tags (borrowings and total equity) first appear in the Sep-2022 half-year
  filings. Total equity is present on about 97% of half-year filings from then on, and on about 0% before
  (`diagnostics/research/2026-11_phase0_closeout.md`, section C).
- `de_ratio` therefore exists for under 2 years of the training window, which ends 2024-06-30.
- It cannot be a core input to the L5 crash-risk layer. It may be tested only as an add-on to a core L5 built
  without it.

## Amendment note, 2026-11-20 (owner decision on PR #221): results gaps and financials

- **Financials** are excluded from L1 entirely. They are excluded from L5's fundamental inputs only; L5's price
  features keep them.
- The **425 member-quarters before a company's first filed quarter are not gaps**: there is no history to fill.
- The **remaining interior gaps stay NaN and are never interpolated.** The L1 study must report the number of forecast
  points lost to them.
- If more history is needed later, a **browser-based BSE fetch** is the fallback. Scripted calls to api.bseindia.com
  returned 403 on 2026-11-20 (`diagnostics/research/explore/2026-11-20_bse_gap_fill_attempt.json`).
- Gap profile: `diagnostics/replica/phase0/missing_gap_clusters.json`.
