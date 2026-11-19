# Live stop conformance (audit) and the "why did it fall" discriminator — 2026-11-19

**Class: MEASUREMENT.** Owner queue, 2026-11-19. 0 trials, no sealed read, no rule proposed, no live change, no merge.
**Standing counts: screens 24 · sealed opens 4 · n_trials 3** (unchanged).

**Classification note, for the owner.** Part 2 is run in the exploration tier on the owner's instruction, so the counts
stay unchanged. Under `skills/verdict-machine` a feature-vs-label read on the banked 0116/0117 labels would normally be
priced as a screen, which would be screen #25. Whether it should be counted is listed as an owner decision.

**Kill-rule wording.** Per the 2026-08-08 amendment, no path is killed without a pre-registered run. "The domain stays
closed" is therefore read as **"no candidate for the January exploration lane; the path keeps its current priority"**.
It is a bound, not a KILL.

**Goal link.** Part 1 checks that live stops are the stops that were backtested, so the paper record measures the frozen
strategy. Part 2 bounds whether a stopped trade's cause of fall is knowable at stop time.

## Part 1 — live stop conformance (read-only engineering audit). Method stated before any result.

**Population.** Every swing entry in `results/attribution_ledger.csv` (69 rows: 48 reconstructed, 21 forward), joined
to `results/cards_archive.jsonl` (the card's `entry`, `entry_low` = signal-week low, `entry_high` = signal-week high,
`stop`) on ticker and signal_date. Only committed artifacts are read; no engine run touches post-cut prices.

**Live stop.** The ledger `stop`, produced at `scripts/run_bhanushali_cron.py:596`:
`stop = round(_record_stop(entry, lo), 2)`, with `_record_stop` at `:332`, i.e. max(week_low, entry × (1 − 0.10)).

**Frozen 0094 engine stop for the same signal.**
- `scripts/run_bhanushali_weekly_rank.py:1330`: `st = o_["lo"]`, the signal-week low (`_stop_arr = wlow`, `:394`;
  the live config has touch origin only).
- `:1344-1345`: lifted to entry × 0.90 by `max_risk_pct`.
- The engine's entry is the fill (the next-week open inside the band), so engine stop = max(week_low, fill × 0.90),
  and engine width = (fill − engine stop) / fill.

**Width gap per trade.** live width − engine width, in pp. The ledger carries both widths for closed rows
(`stop_width_pct_card`, `stop_width_pct_engine`); for open rows the engine width is recomputed from the card
`entry_low` and the ledger's fill price.

**Root cause of 3.76% vs 8.85% (finding 0143).** Width when the cap does not bind = (entry − week_low)/entry
= [(hi − lo)/entry] × [(entry − lo)/(hi − lo)], that is, signal-week range × entry position in the band.

The decomposition compares:
- **historical:** the unperturbed swing ledger 2019-01..2024-06 (`explore_blend_drawdown_sizing.navs()`), with each
  trade's band (lo, hi) read from the cut panel `ctx.P[t]["entry_win"]`;
- **live:** the card bands.

It reports the median of each factor and the share of trades at the 10% cap.

**Fills beyond the stop.** For ledger rows with `exit_reason` in {stop, stop_part}:
- slippage % = (close_price − stop) / stop;
- slippage in R = `beyond_stop_r` (the ledger's own decomposition);
- `gap_through`.

The stop order type and trigger basis are read from the code. The weekly-close trigger is at
`run_bhanushali_weekly_rank.py:1118`, `if wc <= p["stop"]`: a pending full exit filled at the next session's open
(`:868`). No broker stop order exists in the code base [to be confirmed by grep in the run].

**Output.** Fix options listed with what each changes. No rule is proposed.

## Part 2 — "why did it fall" discriminator. Method and kill rule stated before any result.

**Data.**
- `research/substrate/context_windows.parquet` (the banked 0116/0117 dataset that `diag_postentry_stage1.py` reads),
  train only: entry_date 2019-01-01..2024-06-30. Cohorts: `noise_stop` (391) and `false_touch` (314).
- **Additional sealed-safety cut:** the stop time must also be ≤ 2024-06-30. Rows whose stop falls after the cut are
  dropped and counted, so no 2024H2 bar is read.

**Stop time.** The last session strictly before `exit_date`: the weekly close that triggered the exit, which then
filled at the next open. **Firewall: every feature uses only bars ≤ the stop time.** Prices come from
`corrected_universe()` (adjusted OHLCV), cut at the stop time.

**Drawdown leg.** From the session of the highest close in [entry_date, stop time] to the stop time. If the peak is the
stop day itself, the leg is the entry → stop window.

**Features:**
- **(a) Market-adjusted leg return.** r_stock,leg − β · r_M150,leg, where M150 is the Nifty Midcap 150 TRI
  (`diagnostics/research/benchmarks/tri/nifty_midcap_150_tri.csv`). β is the OLS slope of daily stock returns on
  daily M150 returns over the 126 sessions before entry_date.
- **(b) Sector-adjusted leg return.** The same, with a sector index: the equal-weight daily return of the
  `corrected_universe()` names sharing the ticker's `config.SECTOR_MAP` label, excluding the ticker itself.
  `Others` and sectors with fewer than 5 names fall back to M150.
  **FLAG: SECTOR_MAP is a present-day map, not point-in-time**, and membership is survivorship-coloured.
- **(c) Market share of the leg.** 1 − var(ε)/var(r_stock) over the leg's daily returns, with ε = r_stock − β·r_M150
  and the pre-entry β. Clipped to [−1, 1]. Legs shorter than 5 sessions are NaN.
- **(d) Delivery on the breakdown day.** `deliv_pct` on the stop day, divided by its median over the 60 sessions
  before the stop day (`data/_delivery_raw.parquet`, release `dataset-pin-20260729`, series EQ).
- **(e) Results in the 5 sessions before the stop.** Whether a financial-results board meeting
  (`data/_earnings_raw.parquet`, purpose contains "Financial Results") has its `event_date` within the 5 sessions up to
  and including the stop time. **[assumed]** The NSE `ann_ts` timestamps the intimation, not the results release, so
  the meeting date is used as the results day. Disclosed.

**Statistics.**
- Per feature: mean(false_touch) − mean(noise_stop), with a two-sample cluster bootstrap on ticker
  (`nq.brain.portfolio.cluster_bootstrap_two_sample`, 2,000 draws), giving a 95% CI.
- Feature (e) is a share, so its difference is a difference in proportions with the same bootstrap.

**Kill rule (fixed now).** If every feature's 95% CI straddles zero, the domain gets no exploration-lane candidate (a
bound, as above). If any CI excludes zero, that feature is reported as a **candidate for the January exploration
lane**. No book backtest is run either way.

**Hindsight bound.** The rule is "keep the stop only when (a) is within ±1 SD of zero", with the SD pooled over both
cohorts. Stops with |a| > 1 SD are skipped and held. The R recoverable is the sum over the skipped trades of
`post_ret21` × exit_px / (entry − stop): the 21-session post-exit move in R, which is `diag_postentry_stage1`'s
giveback unit. It is reported for each cohort, net, and per year.
- It is hindsight in two ways: the cohort labels and `post_ret21` both look past the stop.
- It is an upper bound for this rule, not a backtest.
- The post-exit window for a stop near 2024-06-30 runs past the cut, but `post_ret21` is a banked column, not a new
  read. It is used as stored.

**Blind replica.** Re-derives feature (a) for both cohorts from a written spec.
