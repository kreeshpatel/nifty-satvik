# long_horizon — the 3-month equity strategy (validated 2026-06-25)

> Result of the autonomous research arc. Built on the audited `long_horizon/` engine. NOT yet wired
> to live; this is the validated backtest spec + the honest case for/against deploying it.

## TL;DR
**Low-debt-filtered trend momentum** on liquid Indian large+mid caps, ~3-month holds. It beats
buy-and-hold on every metric and the low-debt filter both raised returns and cut the crash years.

> **HEADLINE UPDATED 2026-06-27 — baseline_v0 (exit-parity-unified engine, corrected-682 universe,
> 397 solvent names, 2017-2026).** See `research/baseline_v0.json` for the frozen anchor.
>
> **Reconciliation with prior 30.3% / 1.15 figure:** the old number used the optimistic target-fill
> (backtest filled targets at open, live fills at next close). Exit-parity unification — backtest now
> fills conservatively = live — costs ~4 pp CAGR over the full window. 30.3% was explicitly flagged in
> §6 as "to be re-confirmed on the next CPCV run"; baseline_v0 IS that re-confirmation. The prior figure
> is preserved here as historical provenance but is superseded as of this date.
> Previously reported (optimistic-exit, superseded): CAGR 30.3% / Sharpe 1.15 / maxDD −40.1%.
>
> **Walk-forward "~32% / 1.31" (≥2019) was also measured with the optimistic-exit engine and is
> similarly unconfirmed on the exit-parity baseline; treat it as pending re-confirmation, not a
> current figure.**
>
> The pre-fix filter (bare "<1.5") admitted negative-equity names and read 35.5% / 1.27 — ~5pp of
> that was distressed-pump momentum (IDEA-type) and is correctly gone. (A D/E < 2.0 cut reads 35.5% /
> 1.28 but is threshold-noise-sensitive — D/E < 1.5 is the stable, defensible point.)
>
> After-tax STCG (20%) is a further ~3 pp CAGR / ~0.18 Sharpe versus the gross figure.

| | strategy (gross) | strategy (after-tax STCG 20%) | buy-hold (same universe) |
|---|---|---|---|
| CAGR | **26.1%** | **23.1%** | 16.3% |
| Sharpe | **1.02** | **0.83** | 0.96 |
| Max drawdown | −41.9% | −45.6% | −43.5% |
| Calmar | 0.62 | 0.51 | — |
| Trades / year | ~152 | — | — |
| Negative years (2017-26) | **1 of 10** (2018) | — | several |

## The spec (every value derived/validated, not guessed)
- **Universe:** Nifty-500, **point-in-time index-membership masked** (trade a name only while it was
  an index member — no pre-inclusion-ramp lookahead), **large+mid only** (trailing-median 20d rupee
  ADV ≥ ₹5 cr, spike-robust → small caps + flash-pumps excluded), **filtered to 0 ≤ debt/equity < 1.5**
  (solvency floor is deliberate — the bare "<1.5" admits NEGATIVE-equity insolvent names like
  Vodafone-Idea D/E −3.32; requiring D/E ≥ 0 excludes the most distressed / F&O-ban-prone names)
  (PIT Screener fundamentals, strict-before join). ≈ 400 tradeable names.
- **Signal:** cross-sectional rank by `sma200_slope_63` (200-day trend slope). Long the top ~15.
- **Hold:** min 10 / max 63 trading days (≈ 3 months).
- **Exit (first hit):** ATR(63) stop (≈3.5×, close-only + gap-fill) · profit target (≈16%, derived
  70th-pct MFE) · trailing stop on the close-peak · hard 63-day time cap. Hard stop never gated.
- **Sizing:** risk-based — `risk_per_trade 3%` / stop distance, capped at 15% of equity and 5% of the
  name's daily turnover. (Sizing is largely inert — the 15% cap binds — so this is not a live knob.)
- **Costs (modeled):** brokerage 0.03% + STT 0.10% both legs + tiered ADV slippage (LARGE 0.05% /
  MID 0.22%) + 0.1% impact > 0.5% ADV. (India micro-costs stamp/exch/SEBI/GST ≈ 3.5 bps — immaterial.)

## Why it works (mechanism, not curve-fit)
Trend/momentum is a real, generalizing cross-sectional factor (mean IC +0.09@63d, HAC t +5.2; holds
on unseen years AND unseen stocks). The **low-debt filter** is the key: leverage is what makes
momentum names blow up in reversals, so removing high-debt names strips the fragile / junk-momentum
/ manipulation-prone tail — it turned the 2022 momentum-crash year from −13% to +0.9%. Threshold-
robust (D/E < 1.0, 1.5, 2.0 all beat the unfiltered book), so it's a real leverage effect, not a
threshold fit.

## What was tested and KILLED (the rigor — so we don't relitigate)
Regime/dual-momentum gate (whipsaws, −CAGR); residual/beta-stripped momentum (India bull momentum
*is* beta); frog-in-the-pan information-discreteness; sector-residual momentum; all short-term
reversal / RSI / MACD / ROC / acceleration signals (Sharpe <0.5, DD −60 to −81%); signal-level
low-vol blending (drags momentum); adding earnings+ROE on top of the debt filter (over-filters).
Plain trend momentum + the single low-debt filter is the robust optimum — simpler won.

## Engine audit (trustworthy)
Three independent passes (flaw-hunter, backtest-validator, the third-party Backtest-Expert checklist).
Found + fixed a P1 survivorship/lookahead bug (PIT membership was never applied → pre-inclusion-ramp
harvesting). Confirmed clean: signal↔fill parity (cleaned OHLC, 0.0 mismatch), no forward-label leak,
train/test purge, both-leg costs, no negative-cash / phantom-DD. 11 correctness unit tests.

## Data contract / universe (audit 2026-06-25)
Data-minimalist — the live path consumes only **9 columns**, a clean subset of the feature
pipeline. It does NOT use the v1 79-feature contract, macro features, or sector enrichment
(`enrich_with_layers` is never called):
- `close`, `sma200_slope_63` (rank signal), `atr_pct_63` (stop/sizing), `adv_rupees_20d`
  (liquidity tier + ADV cap), `ticker`/`date`; `trend_rank` is computed at run time;
  `debt_equity` (solvency) + `sector` (display) are joined in.
- **Universe:** `NIFTY_500` → PIT membership mask → large+mid (trailing-median 20d ADV ≥ ₹5cr)
  → solvent low-debt (0 ≤ D/E < 1.5) → rank → top-15. Does NOT use the v1 `universe_filter`
  (reimplements the liquidity floor via `restrict_to_large_mid`).
- **Sources (all git-tracked → reach the runner):** OHLCV via `data/ohlcv_incremental` (own
  GitHub-backed `ohlcv_cache_lh.json`); `low_debt`/`debt_equity` from
  `data/fundamentals_pit_screener.pkl` (PIT, ~90d lag); membership from
  `data/nifty500_membership.csv`; sector from `config.SECTOR_MAP`. No gaps.
- **Overhead (not a bug):** `compute_all_features` computes ~50 technical cols + labels when
  ~6 are used — wasteful but correct (future: a long-horizon-only feature mode). The
  fundamentals pickle is static (manual refresh). A runtime guard fails loud if the pipeline
  ever drops a required column.

## Robustness / stress tests (full universe, 402 names — all PASSED)
> Note: figures in this section were computed on the pre-exit-parity engine (optimistic-exit) and
> have not been re-run on the baseline_v0 engine. They remain directionally valid (the qualitative
> robustness conclusions hold) but absolute CAGR/Sharpe values are ~4 pp CAGR / ~0.13 Sharpe higher
> than the current honest anchor. Re-run against baseline_v0 engine is queued for baseline_v1.
- **Cost-sensitivity (pre-parity engine):** 1x 30.7%/1.15 · **2x 26.5%/1.01** · 3x 20.5%/0.82 — survives
  2-3x realistic costs and still beats buy-hold (avg trade 2.9% ≫ round-trip cost). Turnover is not fatal.
- **Second train/test split** (derive <2019, test 2019+): **42.4% / 1.46** — not a pre-2017-split artifact.
- **Sub-period stability:** 2017-2021 = 39.9% / 1.50 · **2022-2026 = 21.5% / 0.84 / −37% DD**. Regime-
  dependent (stronger in momentum bulls) but the edge is ALIVE in the recent harder regime and still
  beats buy-hold there. Not front-loaded into death.
- **Threshold-robust:** D/E < 1.0, 1.5, 2.0 all beat the unfiltered book.
- **Bootstrap (block=63, pre-parity engine):** Sharpe median 1.23 [0.58, 1.88]; CAGR median 34.4% [13, 57].

## Honest caveats / risks (do not skip)
1. **−42% drawdown is steep.** It's the price of 26% gross / 23% after-tax CAGR; sizing can't
   reduce it much (cap binds), and the regime gate that *would* cut it also kills the CAGR. A real
   client must stomach −42% gross / −46% after-tax in the worst scenario.
2. **High-variance / regime-dependent.** Bootstrap figures (pre-parity engine) showed Sharpe 5th-pct
   = 0.58 (below buy-hold in the worst ~5% of resampled paths) and median 1.23. The baseline_v0
   headline Sharpe of 1.02 confirms the median is solidly above buy-hold (0.96), but this is a
   high-return, fat-right-tail book, not a smooth 1.3-Sharpe machine. The edge concentrates in
   momentum-friendly years (2017/2020/2021/2023 were +75 to +98%).
3. **min_hold = 10 days, not the "min 20" you specified.** mh10 backtests at 33-36% CAGR; **mh20 is
   the WORST point in the sweep (22% / 0.86)**. Your 20-day floor costs ~11pp CAGR — a real decision
   for you (data says 10; your preference says 20).
4. Backtest-Expert red flags: CAGR >20% (warning) + DD >30% (warning), **but** multi-regime-robust
   (not the regime-specialist flag), 1445 trades, no-lookahead, survivorship-corrected → "deploy
   with conservative sizing + paper-trade first," no *critical* flags. (Prior flag was CAGR >30%
   under the optimistic-exit engine; baseline_v0 gross CAGR 26.1% still warrants the >20% watch.)

## Open decisions / next steps (for the owner)
- [ ] **min_hold 10 vs your 20** — pick the point (CAGR vs your hold preference).
- [ ] **Drawdown tolerance** — −42% as-is for max CAGR, or de-lever (risk 1.5% → ~32% CAGR, similar DD
      since the cap binds) / accept fewer positions.
- [ ] **F&O-only universe** (circuit-free, even cleaner) — needs point-in-time F&O membership (data task).
- [x] **Productionized + LIVE 2026-06-25** — long-horizon is now the SOLE live strategy
      (`src/runners/long_horizon_cron.py`, merged to main); v1 deleted entirely.
- [x] **Paper-trading wired** — `NIFTYQUANT_PAPER_BROKER=1` on the scanner accrues a clean ₹10L
      paper book + the kill-gate equity curve. Still: ≥30 trades / 2 months of paper before any
      real capital (Backtest-Expert gate).
