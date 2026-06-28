---
name: portfolio-simulation
description: >
  Real-world portfolio simulation — the backtest-to-real-capital bridge for the
  long-horizon strategy. Use before touching any paper-trading ledger, NAV file,
  kill-switch, or execution fill model. Covers the pre-committed paper gate
  (>=30 closed trades / ~2 months), fill realism, live-vs-backtest divergences
  (gap-down stop fills, day-aging, two equity curves), kill-switch triggers,
  and what to verify before committing any real rupee.

  Trigger words: paper trading, portfolio sim, realistic fills, paper gate,
  before real capital, track record, paper broker, paper equity, kill criteria,
  kill switch, NAV, equity curve, drawdown gate, paper portfolio.

triggers:
  - paper trading
  - portfolio sim
  - realistic fills
  - paper gate
  - before real capital
  - track record
  - paper broker
  - paper equity
  - kill criteria
  - kill switch
  - NAV
  - equity curve
  - drawdown gate
  - paper portfolio
---

# Portfolio Simulation — Backtest-to-Real-Capital Bridge

This skill governs everything between "the backtest looks good" and "real money
is deployed." It is the Stage E→F protocol in the NiftyQuant Roadmap. Nothing
in this skill requires research judgment — it is an operational checklist.

**Why it matters.** A backtest fills at ideal prices with unlimited capital.
Real trading fills at the next open (or worse), has cash limits, costs money on
both sides of every trade, and can gap through a stop overnight. The paper
simulation is the only honest way to measure how much of the research edge
survives contact with the market. The pre-committed gate exists precisely so
this measurement happens before any real rupee is at risk.

Cross-references:
- Backtest integrity → `skills/backtest-rigor/SKILL.md`
- NSE micro-costs, STT, T+1 settlement → `skills/indian-market-execution/SKILL.md`
- Kite order flow, session expiry → `skills/kite-execution/SKILL.md`

---

## 1. What "paper simulation" means in this codebase

There are two parallel equity series. They serve different purposes and must
not be confused.

### 1a. Kill-criteria equity curve (`paper_equity.py` → `results/portfolio_history.csv`)

Purpose: feed the kill-gate circuit-breaker. NOT a cash ledger.

Formula (from `src/trading/paper_equity.py`):

```
total_value = INITIAL_CAPITAL
            + cumulative_realized_pnl          # persisted anchor
            + Σ_active (pnl_pct/100 × position_value)   # unrealized
```

- `cumulative_realized_pnl` is a persisted accumulator so pruned trades
  (the cron drops CLOSED entries older than 60 days) never create an
  artificial cliff in the equity series.
- `pnl_pct` on open positions is refreshed by `track_signals` on each
  4:15 PM cron run from live close prices.
- The cron calls `paper_equity.update_equity_curve(...)` in Step 2a. This
  function is the single entry point — do not call sub-functions individually.
- Known gap (W-12, wiring audit): this curve books entry at close(t) rather
  than open(t+1), making it ~1.4% optimistic vs the paper broker. Acceptable
  for the kill gate; fix alongside W-05 when you resolve the stop-booking gap.

### 1b. Capital-constrained paper ledger (`paper_broker.py` → `results/paper_portfolio.json`)

Purpose: simulate the auto-executor's actual trades against a real ₹10L cash
book. This is what builds the track record you compare against the backtest.

Key outputs (all in `results/`):
- `paper_portfolio.json` — live ledger (cash + positions)
- `paper_broker_state.json` — broker bookkeeping (pending buys/sells, id sets)
- `paper_trades.json` — append-only audit log of closed round-trips
- `paper_ledger_history.csv` — realistic daily equity series (distinct from
  the kill curve above)

The paper broker is called by the cron after `track_signals` completes so
every signal already carries today's `current_price`, `current_open`, and
`pnl_pct`.

---

## 2. Fill model — what the paper broker actually does

Understanding the fill model is required before comparing paper results to the
backtest. The design goal is: **paper broker fills = backtest fills**.

### Buy fill (T+1)

The paper broker fills at the signal's T+1 `current_open × (1 + slippage)`.

```python
# src/trading/paper_broker.py, _entry_slip()
from long_horizon.backtest.portfolio import _slip
return _slip(_to_float(adv_rupees), 0.0)   # same function the backtest uses
```

`BUY_LAG = 1` (fixed; no human T+2/T+3 randomisation). If the signal closes
before its T+1 buy day, the position is a "missed trade" — none is opened.

Capacity cap: at most `MAX_POSITIONS` (15) concurrent positions. Each new buy
is also constrained by available cash (deducting brokerage + buy-side STT) and
the `MAX_POSITION_PCT` (15%) cap on portfolio equity.

### Sell fill (next trading day after model exit)

When `track_signals` marks a position `HIT_TARGET / HIT_STOP / EXPIRED`, the
broker schedules a sell for the **next trading day** at that day's fetched
price (via `trading.signal_tracker._fetch_prices`). The model's own recorded
`close_price` is a fallback only.

This one-day delay is deliberate: a real user sees the signal close in the
4:15 PM run, then sells the following morning. It matches `ClientExecConfig`
(`sell_lag_days=1`, `sell_fill='open'`) in `src/trading/client_execution.py`.

### Costs (matching the backtest exactly)

Both legs charge `config.delivery_leg_cost(notional)`:
- Brokerage: `BROKERAGE_PCT` (0.03%) per leg
- STT: `STT_PCT` (0.10%) **per leg** — delivery equity charges both sides
  (intraday is sell-only; do not confuse them)

Slippage: `long_horizon.backtest.portfolio._slip(adv_rupees, notional)` with
tiered rates (LARGE 0.05% / MID 0.22% / SMALL 0.40%) plus 0.1% market-impact
surcharge when a position exceeds 0.5% of the name's daily turnover.

---

## 3. Live-vs-backtest divergences (known and pre-committed)

These are not bugs you fix without a gate — they are documented differences
between the live system and the backtest as of the Phase-1 wiring audit.

### W-05: Gap-down stop fills (HIGH severity)

The backtest in `long_horizon/backtest/portfolio.py` has explicit gap-fill
logic: if the session opens below the stop, the exit price is the open, not
the stop.

```python
# portfolio.py ~line 323
if open_price < stop:
    exit_price = open_price   # gap-fill
```

The live `signal_tracker.py` (~line 467, 510) does NOT receive `current_open`
in the stop-exit branch. It records `close_price = stop`, which is optimistic
for the ~20% of stop exits that are gap-throughs (wiring audit: 297/1453 stop
exits, avg −17%, 199 worse than −15%).

Impact: the paper track record understates the average loss on stop exits by
roughly 1–2 pp per stopped trade. This is the highest-priority parity fix
before claiming the paper track record is an honest gate.

Fix path (W-05): pass `today_ohlc={'open': current_open, ...}` into
`track_signals`; book `sig['close_price'] = decision.exit_price` from the
gap-branch; fix alongside W-11 and W-12 in a single parity PR.

### W-11: Day-aging off by one (MEDIUM severity)

The backtest ages a position from the fill day (signal_date + 1). The live
`signal_tracker.py` (~line 399) ages from `signal_date`. This causes the
63-day hard cap and the 10-day min-hold to fire one trading session early in
live vs the backtest.

Impact: slightly more time-stop exits than expected; the min-hold floor
occasionally gates a profitable exit that the backtest would have allowed.

Fix: stamp `assumed_fill_date = signal_date + 1 trading day` and age from it.

### W-12: Kill-equity curve entry basis (MEDIUM severity)

The kill-criteria curve (paper_equity.py) books entry at `close(t)` rather
than the open(t+1) fill price. This makes the kill curve ~1.4% optimistic per
entry leg on the unrealized side.

This only matters for the kill trigger thresholds, not the paper_broker ledger
(which is already open-based). Fix together with W-05.

---

## 4. The pre-committed paper gate

This is a hard rule — not a guideline. Real capital cannot be deployed until
the gate clears.

### Gate definition

**Minimum**: 30 closed trades in `results/paper_trades.json` AND approximately
2 months of daily NAV rows in `results/paper_ledger_history.csv`.

Why 30 trades: at the strategy's ~60% expected win rate, a 30-trade sample
gives a ~80% probability of distinguishing genuine edge from noise (binomial).
Below 30, the realized WR is too noisy to act on even directionally. The kill
criteria themselves don't even compute rolling-WR until 20 closed trades exist
(`kill_criteria.MIN_TRADES_FOR_WR_CHECK = 20`).

Why 2 months: the strategy has a 3-month hold cycle. Two months ensures at
least one full cohort of positions has entered and most have exited — you are
measuring real round-trips, not only unrealized marks.

### What to measure at the gate

Run through these items in order. A "pass" requires all items to be in range.

**A. Fill realism**
- Compare paper `entry_price` in `paper_trades.json` to the backtest's
  `open × (1 + slip)`. Drift > 1% average on the buy side means the slippage
  model or T+1 logic is wrong.
- Compare paper `sell_price` to the backtest's exit prices. A consistent
  downward gap on stops confirms the W-05 divergence and must be fixed first
  if it is material (> 1 pp average).

**B. Hit rate**
- Paper win rate should be within ±10 pp of the backtest's 59.7%.
- A WR below 45% over 30 trades is the kill-criteria hard trigger — stop
  immediately, do not wait for the gate date.
- A WR between 45% and 50% over 30 trades: soft warning territory. Do not
  advance to real capital; extend paper for another month.

**C. Drawdown path, not just endpoint**
- Open `results/paper_ledger_history.csv` and plot the equity curve.
- The maximum intraday drawdown should be comparable to the backtest's −41.9%
  gross. A paper drawdown exceeding −35% at any point triggers the hard kill
  regardless of where you are in the gate window.
- More importantly: check whether the drawdown PATH looks like the backtest
  (slow, trend-driven) or like correlated cluster losses (sharp V-shapes in
  days). The latter signals a structural difference the backtest didn't model.

**D. STCG tax drag**
- At 59.7% WR and ~152 trades/yr, roughly 60% of gains are taxable at 20%
  STCG. The after-tax headline from `research/baseline_v0.json` is 23.1% CAGR
  / 0.83 Sharpe. Paper CAGR should not exceed this before claiming the gate
  is valid — if it does, either the cost model is wrong or the paper period
  was unusually favourable. Flag but do not auto-fail.

---

## 5. Kill-switch triggers and the kill criteria system

The kill system (`src/trading/kill_criteria.py`) runs on every cron cycle.
It reads `configs/kill_criteria.yaml` for thresholds. These thresholds were
re-calibrated for the long-horizon strategy's larger drawdown profile on
2026-06-25. Do not edit them outside the quarterly review.

### Hard kill thresholds (any one triggers → new entries stop immediately)

| Metric | Threshold | Source |
|---|---|---|
| Drawdown from peak | 35% | Calibrated to just above the worst backtest fold (2022: −34.8%) |
| Consecutive losses | 6 | Matches worst backtest streak; probability at 60% WR = ~0.22% |
| Rolling-20 WR | ≤ 35% | Tied worst observed fold value (2022, 2024) |
| Single-day NAV loss | ≥ 6% | Tail event not captured in the backtest (gap-through cluster) |
| Days with no signal | ≥ 60 | 2× the expected 30-day inter-signal gap; suggests out-of-distribution universe state |

Hard kills latch. A metric recovering on its own does NOT un-kill the strategy.
Resume only after `scripts/kill_resume.py` is run AND the resume protocol in
`configs/kill_criteria.yaml` is satisfied (7-day cooling, written diff, 10-fold
walk-forward, written anti-resume memo, second-person review).

### Soft warning thresholds (half-size new entries, write a memo)

| Metric | Threshold |
|---|---|
| Drawdown from peak | 22% |
| Consecutive losses | 4 AND drawdown > 8% (both required) |
| Rolling-20 WR | ≤ 45% |
| Single-day NAV loss | ≥ 4% |
| Days with no signal | ≥ 45 |

Soft warnings clear after 5 consecutive clean checks (anti-whipsaw).

### Mode switch: observe → enforce

The kill system starts in `observe` mode (`KILL_CRITERIA_MODE=observe`). In
observe mode every metric is computed and logged to `results/kill_log.jsonl`
but no action is taken — position sizing is untouched.

Switch to `enforce` only after:
1. The paper gate has cleared (30 trades / 2 months).
2. You have confirmed `results/kill_log.jsonl` is being pushed to GitHub
   (W-06 fix — add it to the push list in `long_horizon_cron.py`).
3. `results/portfolio_history.csv` has at least 20 daily rows (the equity
   data must exist or the system fails CLOSED to a soft warning on startup).

To switch: set `KILL_CRITERIA_MODE=enforce` as a GitHub Actions secret or
environment variable. The cron reads it at runtime — no code change needed.

---

## 6. `client_execution.py` — measuring client-realistic returns

`src/trading/client_execution.py` provides `simulate_client_trade()`: given a
model signal + forward OHLCV, re-price the trade under realistic human
execution (T+1..T+3 buy window, sell next day after signal exit).

Key config (`ClientExecConfig`):
- `buy_window_days=3`, `buy_fill='avg_typical'` (mean of (H+L+C)/3 across the
  window) — the realistic default
- `sell_lag_days=1`, `sell_fill='open'`
- `slippage_tier='SMALL_CAP'` — most conservative (use `MID_CAP` for the
  large+mid-only filtered universe)

This module is research / measurement infrastructure. The paper broker does
NOT call it — the broker's fill model is already T+1 open-based. Use
`simulate_client_trade()` when you want to answer: "what did clients who
followed signals but didn't buy immediately actually make?"

Prior finding (MEMORY: client-execution framework): edge survives realistic
execution — realistic T+1..T+3 avg-typical fill = +4.75% / 68% WR, essentially
equal to the idealized T+1-open fill (+4.75% / 68%); worst-case worst-close
fill = +2.33% / 59%. The edge is robust to execution latency.

---

## 7. Capacity constraints

The strategy's ADV floor (≥ ₹5 cr trailing-median 20d) is the primary guard
against illiquid names. The per-name sizing cap of 5% of daily turnover
(`max_adv_participation = 0.05` in `long_horizon/backtest/portfolio.py`) is
applied in both the backtest (`base_risk_qty`) and the paper broker
(`_entry_slip`).

At ₹10L starting capital with 15 positions at 15% each, the maximum per-name
notional is ₹1.5L. For a name with ₹5 cr ADV (the floor), ₹1.5L = 0.3% of
ADV — well below the 5% cap. Capacity is not a binding constraint at this
capital level. It becomes relevant above ₹30L per position (~₹450L total).

---

## 8. Step-by-step: how to set up a fresh paper run

1. **Verify OHLCV freshness**: check `results/ohlcv_cache_lh.json` is current
   (the incremental fetcher keeps it rolling 600d). A cold-start means a
   495-name yfinance pull — allow 10 min.

2. **Verify fundamentals PIT store**: confirm
   `data/fundamentals_pit_screener.pkl` exists and has a recent scrape date.
   Without it, D/E filter silently returns empty universe. Check W-13: the
   path must be absolute (anchored by `Path(__file__).resolve().parents[2]`),
   not cwd-relative.

3. **Reset the paper broker state**: delete
   `results/paper_broker_state.json` and `results/paper_portfolio.json`.
   On the next cron run, `paper_broker.run_paper_broker()` detects
   `state['initialized'] == False` and starts a clean ₹10L book.
   Do NOT delete `results/paper_equity_state.json` separately — it is
   updated by `paper_equity.update_equity_curve()` and does not need reset
   unless you want to restart the kill curve too.

4. **Confirm kill mode is `observe`**: verify `KILL_CRITERIA_MODE=observe`
   in the GitHub Actions environment. Check `results/kill_log.jsonl` after
   the first run — if the file does not exist, the kill log is not being
   pushed (W-06: add `results/kill_log.jsonl` to the push list in the cron).

5. **Let it run for 2 months / 30 closed trades**. Check weekly:
   - `results/paper_trades.json` (count closed trades)
   - `results/paper_ledger_history.csv` (plot the NAV curve; watch for
     the drawdown path anomalies described in Section 4-C)
   - `results/kill_log.jsonl` (any triggered metrics?)

6. **At the gate review** (see Section 4): run through items A–D. If all
   pass, write the gate memo and commit it. Then switch to `enforce` mode.

7. **Ramp real capital**: start at 10–20% of intended size. Observe for
   another 30 days before full deployment. The ramp is not coded — it is
   an operator decision.

---

## 9. Common mistakes and misreadings

**Mistake: comparing paper WR to the backtest's gross WR directly.**
The paper ledger is after-costs and after realistic fill timing. The backtest's
59.7% WR is gross, before costs, but the cost drag on WR is small (only trades
that barely cleared the exit target become losses after costs). Expect ≤2 pp
difference. A larger gap points to W-05 (stop exits being booked optimistically)
or a stale OHLCV causing wrong stop prices.

**Mistake: reading the kill-criteria equity curve as the paper P&L.**
`results/portfolio_history.csv` (written by `paper_equity.py`) is the
always-on kill signal, not the realized trading P&L. It over-counts positions
it has not actually opened (it uses unrealized pnl_pct × position_value
without checking whether the paper broker actually bought). Use
`results/paper_ledger_history.csv` for the realistic book.

**Mistake: treating an observe-mode soft warning as "no action needed."**
In observe mode the system takes no action, but a soft warning still means
the metric fired. Write the investigation memo anyway — the gate review will
check that triggered metrics were investigated, not just that they were
non-blocking.

**Mistake: switching kill mode to enforce before the equity curve has data.**
If `portfolio_history.csv` is missing or has < 2 rows, both drawdown and
single-day-loss return `None`, and the system immediately enters soft-warning
state (`equity_data_unavailable`). Start the paper run, let the equity curve
accumulate 20+ rows, then switch modes.

**Mistake: relying on the paper broker for real-time intraday exit signals.**
The paper broker runs once per day at 4:15 PM IST (with the cron). Intraday
stop hits are not modeled. This matches the strategy's close-only stop
assumption in the backtest — the strategy does not watch intraday prices.

---

## 10. Checklist: before real capital

Run through this in order. Do not skip items.

- [ ] 30+ closed trades in `results/paper_trades.json`
- [ ] 40+ daily rows in `results/paper_ledger_history.csv`
- [ ] Paper WR within 45–75% (not below 45% hard kill)
- [ ] Paper max drawdown within −35% (not at or beyond hard kill)
- [ ] Average paper buy fill within 1% of backtest's T+1-open × slip
- [ ] Stop exit average loss not materially worse than −17% (W-05 divergence
      at worst 20% of stops; if paper stop losses average > −20%, fix W-05 first)
- [ ] `results/kill_log.jsonl` is being pushed and readable
- [ ] `results/portfolio_history.csv` has been stable for 2+ months
      (no artificial cliffs from the 60-day prune cycle)
- [ ] Kill mode switched to `enforce`
- [ ] Gate memo written and committed to `research/findings/`
- [ ] Ramp plan documented (start size, review milestone, full-size trigger)

---

## 11. Recommended postmortem fields for the paper track record

*Applies once the paper gate is running and closed trades are accumulating in
`results/paper_trades.json` / `results/signals_history.json`.*

*(Adapted from mphinance/alpha-skills `trader-memory-core` + `signal-postmortem`, MIT.)*

### 11a. MAE / MFE — per-trade excursion fields

Add these two fields to every closed entry in `signals_history.json` and
`paper_trades.json`. Both are computable from the OHLCV cache without a
full backtest rerun — loop the low/high series between fill date and exit date.

| Field | Definition | Formula (close-only proxy) |
|---|---|---|
| `mae_pct` | Maximum Adverse Excursion — the worst intraday trough reached before exit, expressed as % from fill price | `min(low[fill..exit]) / fill_price - 1` |
| `mfe_pct` | Maximum Favorable Excursion — the best intraday peak reached before exit | `max(high[fill..exit]) / fill_price - 1` |

**Why it matters here.** The long-horizon strategy uses a fixed
`stop_atr_mult` and `target_pct` derived from the research backtest.
After ≥ 30 closed paper trades, MAE/MFE distributions tell you:

- If MAE is systematically tighter than the stop (e.g. 80% of stopped
  trades had MAE < half the stop), the stop is too wide — it bleeds
  capital on reversals that never threatened the trade.
- If MFE significantly exceeds `target_pct` on winning trades before the
  target fires, the target is potentially too tight and captures only
  part of the available trend.

These are inputs for the **next** stop/target parameter review, not
actionable in paper-phase. Do not adjust frozen config based on
paper-phase MAE/MFE alone — the sample is too small and the review gate
(`docs/LIVE_OVERLAY_PROTOCOL.md`) requires a full walk-forward.

### 11b. Regime stamp fields

Add to every signal entry (open and closed) in `signals_history.json`:

| Field | Type | Source |
|---|---|---|
| `regime_at_entry` | string: `BULL` / `CHOPPY` / `BEAR` | 3-tier regime value from `results/regime_history.csv` on the signal date |
| `regime_at_exit` | string: same enum, or `null` if still open | regime value on the exit date |

These fields enable regime-stratified WR analysis on the paper track
record without re-running the backtest.

### 11c. REGIME_MISMATCH outcome category

The existing exit-reason taxonomy (`HIT_TARGET`, `HIT_STOP`, `EXPIRED`,
`REPLACED`) does not capture regime causality. Add a derived field:

```json
"postmortem_tag": "REGIME_MISMATCH"
```

Assign `REGIME_MISMATCH` when `regime_at_entry != regime_at_exit` AND
the trade result is a loss (HIT_STOP or EXPIRED below entry). This tags
trades where the regime flipped against the position after entry — a
separate failure mode from "entered a bad name in a stable regime."

**Minimum-sample rule (mirror of our DSR discipline):** do not act on
the REGIME_MISMATCH rate until ≥ 20 closed signals exist in the paper
ledger. With fewer trades, the cell counts by regime are too thin to
distinguish signal from noise. Log the tag from day one; evaluate only
once the sample floor is reached.

**Suggested `signal_analytics.json` rollup:**

```json
"regime_breakdown": {
  "BULL":   { "n": 0, "wr": null, "avg_pnl_pct": null },
  "CHOPPY": { "n": 0, "wr": null, "avg_pnl_pct": null },
  "BEAR":   { "n": 0, "wr": null, "avg_pnl_pct": null },
  "REGIME_MISMATCH_count": 0,
  "min_sample_met": false
}
```

All three additions are **schema / documentation only.** No code change
should be made here — the correct place to wire them is the cron's
postmortem step and the `signal_analytics.json` aggregation pass, both
of which should go through the standard PR + paper-gate review.
