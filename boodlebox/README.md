# BoodleBox briefing — Nifty Satvik research system (state as of 2026-10-23)

This folder is a reading pack for an outside reviewer. It summarises what the system is, what was done between
2026-10-13 and 2026-10-23, what was found, and what is still open. Every claim links to the file in this
repository that produced it. Numbers are reproduced from committed scripts, not from chat.

## 1. What the system is

- **The live book:** a weekly swing strategy on NSE Nifty-500 stocks. A stock signals when it touches its
  **44-week simple moving average** and closes back above it. The **top 5 signals by a relative-strength score
  (CRS)** each week are "Grade A" and are bought, with about **₹10 lakh** of paper capital, roughly 5 positions,
  an extension cap (no buys more than 20% above the SMA), a 20% maximum position size, and a scaled exit (40% at
  +2R, 40% on a blow-off top, 20% runner on the SMA).
- **Engine:** [`scripts/run_bhanushali_weekly_rank.py`](../scripts/run_bhanushali_weekly_rank.py) (signals, Grade A,
  backtest). **Live weekly run:** [`scripts/run_bhanushali_cron.py`](../scripts/run_bhanushali_cron.py), scheduled
  in [`.github/workflows/cron-bhanushali-scanner.yml`](../.github/workflows/cron-bhanushali-scanner.yml).
- **Map of the live system:** [`skills/repo-map/SKILL.md`](../skills/repo-map/SKILL.md).
- **Research rules:** [`skills/program-laws/SKILL.md`](../skills/program-laws/SKILL.md) (standing verdicts) and
  [`docs/PROCESS_TIERS.md`](../docs/PROCESS_TIERS.md) (how much ceremony each kind of work needs).
- **Discipline in one line:** ideas are cheap and evidence is expensive. Anything that would change real money
  is pre-registered with thresholds fixed in advance and judged once on a sealed 2024H2–2026H1 slice; everything
  else is exploration on 2019–2024H1 and is labelled exploratory.
- **Standing counts:** screens 23 · sealed opens 3 · n_trials 2 (from
  [`diagnostics/research/n_trials.json`](../diagnostics/research/n_trials.json) and the screen ledger).

## 2. Honest scorecard (live configuration)

| aspect | finding | source |
|---|---|---|
| forward paper book | about −2.6% since 2026-07-04, ahead of the Nifty (about −7.9%), but negative; the kill gate is surfaced | weekly cron artifacts |
| the Grade-A rank | ranking by CRS does not order outcomes among buyable signals (rank IC −0.004); about as good as random | [0150](../research/findings/0150-engine-layer-audit.md) |
| seat waste | the live top-5 ranks names the book cannot buy, wasting about a quarter of seats; ranking only buyable names lifts train Sharpe 1.025 → 1.275 | [0150](../research/findings/0150-engine-layer-audit.md) |
| sizing | every fill is capped at 20% notional; the 2% risk rule never binds; the live cap setting is the lowest of 8 grid cells | [batch](../diagnostics/research/engine_assumptions/2026-10-20_batch.md) |
| drawdowns | in falling markets the book's beta is about 1 and its holdings move together | [0142, corrected](../research/findings/0142-portfolio-risk-decomposition.md) |
| exits | every exit tweak tried was a wash on the live book | [0148](../research/findings/0148-giveback-ratchet-bound.md) |
| allocation | the fixed 60/40 swing / low-vol split beat every standard allocation rule on Sharpe | [0149](../research/findings/0149-sleeve-allocation-bound.md) |

**Live-book benchmark (train 2019-01-01..2024-06-30):** Sharpe 1.025, CAGR 20.5%, MaxDD −40.1%, 77 trades.
Turning off five live-only layers together reads 1.503 / 35.9% on the same data — not yet attributed layer by
layer ([anchor and bridge](../diagnostics/research/engine_assumptions/2026-10-20_cluster_and_anchor.md)).

## 3. What was explored on 2026-10-20 (all exploratory, train window only)

| idea | result | file |
|---|---|---|
| frog-in-the-pan (smooth momentum) as the seat key | noise | [fip and live diff](../diagnostics/research/engine_assumptions/2026-10-20_fip_and_live_diff.md) |
| rank by touch depth (closeness to the SMA) | loses as a pure key; a deep-first hybrid cuts drawdown 7pp but splits by sub-period | [touch depth and breadth](../diagnostics/research/explore/2026-10-20_touch_depth_and_breadth.md) |
| our own weekly touch count as a market gauge | no predictive value | same file |
| correlation-cluster de-duplication | low value: clustering in drawdowns is the market, not selection | [anchor and cluster](../diagnostics/research/engine_assumptions/2026-10-20_cluster_and_anchor.md) |
| drawdown-switched Nifty hedge sized to beta | cuts drawdown, lowers Sharpe in every variant; perfect timing would be worth a lot, the causal trigger captures none of it | open PR #156 (not yet merged) |
| breakout setups as their own capital sleeve | breakouts almost never fire pre-extension; one combined sleeve looks good but rests on 24–28 trades | open PR #156 |
| path robustness | one replay's noise is about 0.2 Sharpe (+50bp of cost raised CAGR 4.6pp), so single-run deltas below that are unreliable | [batch](../diagnostics/research/engine_assumptions/2026-10-20_batch.md) |

Other inputs: the [ideas memo](../diagnostics/research/ideas/2026-10-20_llm_calc_dataflow.md) (LLM vs calculation
model vs data flow), the first weekly [research-scout digest](../research/scout/2026-10-20.md), and the
[repository audit supplement](REPO_AUDIT_delta_public.md) in this folder.

## 4. Open now

1. **Saturday 2026-10-24 scan:** first live run of last week's fixes (newly scanned names can no longer rewrite
   past weeks; the informed judge runs as its own workflow; a history-drift tripwire and a calendar-expiry check).
2. **A −389.8R trade** in an uncapped research replay (near-zero initial risk) is being traced; it does not reach
   the capital book but distorts uncapped averages in findings 0148 and 0150.
3. **Queued:** a one-layer-at-a-time ablation of the five live-only layers, then an ensemble tool that gives every
   config a noise band.
4. **Waiting on the owner:** pre-registering "rank only buyable names" (D6) for the 2027-01-01 review.

## 5. What a reviewer could most usefully challenge

- Whether the live layers (Grade-A gate, extension cap, position caps, scaled exit) earn their keep, given the
  bridge result above and Law VII (robustness is bought with return).
- Whether the 5-seat book can ever express a per-trade edge (Law II), or whether the real lever is book shape.
- Whether any of the findings above rests on a flawed harness: two did this month (0148 measured a book without
  the live membership gate; four older findings were re-run and corrected).

Not included here, by design: the sealed judge log, credentials, and personal data.
