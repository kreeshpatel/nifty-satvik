# Book identity — which book produced which number (SPEC, written before any result)

**Class:** MEASUREMENT. **No trial. No screen row. No sealed open.** Nothing is adopted, and no rule is
proposed. Standing counts at writing, read from the ledgers:
**screens 20 · sealed opens 3 · n_trials 2.**
**Plan:** the 2026-09-25 development plan, Phase 0 item **A1**.
**Written:** 2026-09-25, before the diagnostic exists. Definitions and reading rules are fixed now.

## Why this exists

The weekly scan runs **three** books off one engine (`scripts/run_bhanushali_cron.py`):

| book | call | what it is |
|---|---|---|
| **capped A-only** | `out_paper` — `a_grade=a_set`, ₹10L cash gate | the book that would hold real positions |
| **uncapped A-only** | `out_all` — `uncapped=True` | every A signal tracked, cash never runs out |
| **capped all-grades** | `out_base` — no `a_grade` filter | `prereg_swing.md` §4's comparator |

`build_envelopes` is fed `out_all`/`led_all` (line 1090), so the signals page and
`signal_analytics_weekly.json` describe the **uncapped** book, while `paper_portfolio_weekly.json` and
`portfolio_history_weekly.csv` describe the **capped** one. Nothing states this at the point of use, and
the Oct-1 scorecard reads both without saying so.

This study asserts nothing about whether the strategy works. It answers one question: **for every number
the 2026-10-01 review will read, which book produced it?**

## Population

Committed artifacts only — no re-run, no network, no engine call. The local OHLCV cache is stale
(`data/ohlcv.pkl`, 2026-07-01, pre-inception), so an offline replay **cannot** reproduce the live NAV and
is not attempted; that limitation is declared rather than worked around.

Read: `results/{signals_history_weekly,signal_analytics_weekly,paper_portfolio_weekly,base_swing_forward,
weekly_review_scorecard}.json`, `results/portfolio_history_weekly.csv`, `results/attribution_ledger.csv`,
and the dated snapshots under `results/archive/*/`. All live entries are ≥ 2026-07-04, so the sealed
2024-07-01..2026-06-30 slice is untouched.

## What is measured

1. **Provenance map.** For each metric in the Oct-1 readout — `n_closed`, expectancy, win rate, Sharpe,
   MaxDD, NAV, `a_only_closed`, `base_swing_closed` — the artifact it is read from, the backtest call that
   produced that artifact, and therefore which of the three books it describes. Each mapping is
   **verified by value**, not asserted from the code: e.g. the scorecard's `n_closed` must equal
   `signal_analytics_weekly.total_closed`, and its `maxdd_pct` must be reproducible from
   `portfolio_history_weekly.csv`.

2. **Curve identity.** The capped A-only NAV series against the capped all-grades series, point by point
   over the common dates. If they agree everywhere, grading does not change what the cash gate funds, and
   §4's MaxDD/Calmar test — which is the only thing §4 decides on — cannot separate the arms.

3. **The capped book's own position history**, from the snapshot sequence: names entering and leaving each
   week, the union of names ever held, and the count of positions that left. **Declared limitation:**
   snapshots are weekly, so a position opened and closed between two snapshots is invisible; the count is
   a **lower bound**, and it is reported as one. `base_swing_forward.n_closed` is an independent
   corroborating source for the all-grades capped book.

4. **NAV reconciliation.** Within the latest snapshot, `cash + Σ current_value == total_value`. Then
   `implied_realised = total_value − 1,000,000 − Σ unrealised_pnl`, reported as a **derived** quantity —
   the capped book's per-position realised P&L is published nowhere, so it is solved for, not sourced, and
   it is labelled that way.

5. **Gate-book mismatch.** For each gate the review applies — readiness (`≥40 closed OR 4 quarters`),
   `KILL_SHARPE < 0`, and §4's `≥20 closed per book` floor — which book each of its inputs comes from, and
   whether the inputs of a single gate come from the same book.

## Reading rules, fixed now

- This is description. **No rule is proposed and no gate is re-specified.** If a gate turns out to read two
  books, the finding says so and stops; changing a gate is a review decision and would need its own
  pre-registration.
- A number that cannot be sourced to an artifact is reported as **derived** or as a **hole**, never
  estimated silently.
- Nothing here restates the book's performance as better or worse. "The capital book's realised P&L is
  positive" is a statement about *which* book, not a claim that the strategy is working: one closed trade
  is not evidence of anything, and the finding must say so in those words.
- The `≥30 closed` precondition applies: expectancy and win rate are not to be read as informative.

## What this may never become

Nothing here authorises a config change, a grading change, a gate change, or a restatement of the
published record. The published artifacts stay as they are; what changes is only what the review is told
each number means.
