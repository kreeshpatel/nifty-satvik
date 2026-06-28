# NiftyQuant — Long-Horizon Operating Model

*Last updated: 2026-06-27. Ground truth: `src/runners/long_horizon_cron.py`,
`.github/workflows/cron-scanner.yml`, `long_horizon/STRATEGY_FULL.md`
(§13 production architecture, §16 operating procedures),
`models/long_horizon/config.json`, `long_horizon/audit/wiring_report.md`,
`long_horizon/audit/PHASE1_FIXES.md`.*

---

## 1. Role and persona

You are the **senior quant maintainer** of a live, paid signal service (~10 users).
The strategy has never traded a real rupee. Every output carries the compliance
framing: **model-generated research signal / decision-support output** — not advice
and not a guarantee of any outcome.

The operator mindset in one sentence: **a reversed result is a finding, not a
failure.** Run the harness, record the verdict, and move on — never relitigate a
killed experiment without genuinely new evidence.

Priorities (from `CLAUDE.md`):

```
correctness > reproducibility > maintainability > risk control > documentation
```

The live-path corollary: **never hand-edit a live file.** `models/long_horizon/config.json`
(frozen cfg) is modified only by re-running the offline derivation + walk-forward and
committing both the new JSON and the updated `long_horizon/config.py` constants in one
PR. `results/signals_today.json` is written only by the cron. A one-off edit to a
results file is the same class of error as a one-off edit to a model pickle.

---

## 2. Daily cycle — the 4:15 PM IST scan

### 2.1 Trigger

GitHub Actions `.github/workflows/cron-scanner.yml`, schedule `"45 10 * * 1-5"`
(10:45 UTC = 4:15 PM IST). Runs from `main` only; feature branches require
`workflow_dispatch`. Render was decommissioned 2026-06-25 — it is not involved.

### 2.2 Pipeline (what the runner actually does)

`python -m src.runners.long_horizon_cron`

**Stage 1 — OHLCV acquisition**

The runner calls `data.ohlcv_incremental.download_recent_data` with a 600-calendar-day
window. On a warm run (normal) this is a 5-day incremental pull merged into the
committed cache at `results/ohlcv_cache_lh.json` (495 names, last-bar 2026-06-25 as of
the audit). The cache is whitelisted in `.gitignore` (`!results/ohlcv_cache_lh.json`,
closed W-08) so a `git clean` cannot trigger a cold-start. A cold-start takes ~3–5 min
(600-day full pull from yfinance for ~500 names). The runner records
`download_coverage_status` (`ok / degraded / failure`) in `cron_health.json`; a thin
fetch while the merged cache still has full coverage prints a `WARN` but continues on
cached prices.

**Stage 2 — Features**

`DataStore.compute_all_features(persist=False)` computes features fresh from the clean
OHLCV. `persist=False` means `data/features.pkl` is NOT overwritten — the research cache
is protected (AUD-018). The long-horizon path consumes 9 columns
(`close`, `sma200_slope_63`, `atr_pct_63`, `adv_rupees_20d`, `trend_rank`,
`debt_equity`, `sector`, `ticker`, `date`) from the 89-column output; the remaining ~80
columns are unused overhead but correct.

**Stage 3 — Universe filters**

Applied in order:

| Filter | Mechanism | Rationale |
|---|---|---|
| PIT index-membership mask | `index_membership.filter_features_dict` per-date against `data/nifty500_membership.csv` | Prevents pre-inclusion-ramp lookahead (P1 survivorship bug, fixed 2026-06-25) |
| Large + mid only | `restrict_to_large_mid`: trailing rolling-median 20d rupee ADV ≥ ₹5 crore | Spike-robust liquidity floor; removes small-cap mirage |
| Solvent low-debt | `0 ≤ D/E < 1.5` from `data/fundamentals_pit_screener.pkl` (~90-day PIT lag, content-freshness gated) | Removes leverage-amplified momentum-crash tail; the single quality lever |
| Demerger quarantine | W-01: names whose RAW close has a ≥50% non-reverting single-session drop within 263 bars are excluded from **new entries** (held positions are not touched) | Prevents a fabricated post-spin-off split-adjusted slope from producing a false BUY — confirmed VEDL 2026-06-27 |

Typical post-filter universe: ~150–200 names. Banks and lending NBFCs largely absent
(D/E NaN from Screener's Borrowings/net-worth derivation for deposit-takers); 26
financials with clean D/E — insurers, AMCs, exchanges — do survive (W-04: documented,
not fixed, live == backtest so not a parity bug).

**Stage 4 — Cross-sectional rank and slot fill**

`cross_sectional_rank` computes `trend_rank` = cross-sectional percentile by
`sma200_slope_63`, descending (1.0 = best). The top-ranked names not currently held
fill the `free_slots = max(0, max_positions − len(held))` openings, up to max 15
positions. A name that exited the same day is ineligible for same-day re-entry.
Names that floor to 0 shares (price > 15% of the ₹10L book) are skipped (W-18 guard).

**Stage 5 — Frozen config: entry / stop / target / size**

Every operating value is loaded from `models/long_horizon/config.json → cfg` via
`load_frozen_cfg()` (which drops `live_overlays`; research baselines unaffected).
Validation runs first (`validate_frozen_cfg`); a corrupt config aborts before the
expensive download.

| Parameter | Value |
|---|---|
| `stop_atr_mult` | 3.67 |
| `target_pct` | 22.52% |
| `trailing_activate_pct` | 4.0% |
| `trailing_pct` | 4.27% |
| `min_hold_days` | 10 |
| `max_hold_days` | 63 |
| `risk_per_trade_pct` | 3.0% of equity |
| `max_position_pct` | 15.0% of equity |
| `max_adv_participation_pct` | 5.0% of 20d ADV |
| `max_positions` | 15 |

For each new signal: `entry = close × (1 + slippage_tier)`, `stop = entry × (1 −
stop_atr_mult × atr_pct / 100)`, `target = entry × (1 + target_pct / 100)`.
Sizing via `base_risk_qty` (shared with backtest; 15% position cap binds on ~494/495
names — sizing is nearly inert, the effective knob is `max_position_pct`).

**Stage 6 — Portfolio vol-target overlay (0068, PAPER only)**

The `live_overlays` block from `config.json` (NOT the frozen `cfg`) applies a
de-gross scalar `vol_scalar ∈ [0.40, 1.0]` to the sizing equity:

```
vol_scalar = max(0.40, min(1.0, 0.15 / realized_42d_book_vol))
```

Reads `results/portfolio_history.csv` (prior-close paper NAV) — lookahead-clean.
Uses the SHARED `portfolio.vol_target_scalar` so live and backtest use identical math.
Shipped to paper 2026-06-26 (pre-reg 0068 arm V2: CAGR-neutral, ~−45 → −39 DD
in-backtest). Research baselines and the golden master are byte-identical (they call
`load_frozen_cfg()` which drops `live_overlays`). Set `vol_target_annual = 0` to
disable.

**Stage 7 — Track and exit open positions**

`trading.signal_tracker.track_signals` runs the exit logic on every open position
using today's OHLCV. Exit decisions delegate to `engine.exit_logic.decide_exit` — the
**same function** the backtest's `portfolio.simulate` calls (exit-parity unification,
2026-06-26; W-05 and W-11 closed in Phase 1). Four exit conditions:

| Exit | Rule |
|---|---|
| Stop loss | Close below `entry − 3.67 × ATR(63)`, close-only; gap-down fills at `min(open, stop)` |
| Profit target | Intraday high reaches `+22.52%`; fills conservatively at the target, not higher |
| Trailing stop | After +4%, trails 4.27% below the running close-based peak |
| Time cap | Hard exit at 63 trading days — no extension |

Min-hold = 10 trading days (profit-taking exits suppressed below this; the hard stop
is **never** suppressed). Aging uses the fill day `(signal_date + 1)`, not the signal
date, so the 63d cap and 10d min-hold fire on the same session as the backtest (W-11).
Exit distribution in the canonical backtest: trailing ~57% · stop ~20% · target ~19% ·
time ~3%.

**Stage 8 — Paper broker and kill gate**

Paper equity curve always runs (`trading.paper_equity.update_equity_curve` →
`results/portfolio_history.csv`). Capital-constrained paper broker runs when
`NIFTYQUANT_PAPER_BROKER=1` (set in the workflow); it opens a ₹10L book, buys at
T+1 open, marks daily, applies costs.

The kill-criteria safety gate reads `portfolio_history.csv` and `signals_history.json`
and runs in **observe** mode (`KILL_CRITERIA_MODE=observe` in the workflow). It
computes and logs a verdict to `results/kill_log.jsonl` but never blocks entries.
Flip to `enforce` only after the observe period is reviewed.

**Stage 9 — Write result files (atomic)**

All writes use `utils.atomic_io.atomic_write_json` (temp → fsync → `os.replace` —
crash-safe). Files written each run:

| File | Contents |
|---|---|
| `results/signals_today.json` | Today's actionable set: held + new + closed-today. Envelope includes regime, vol-target scalar, frozen config snapshot. |
| `results/signals_history.json` | Full lifecycle history: every signal ever, with ACTIVE/HIT_TARGET/HIT_STOP/EXPIRED status and close price/P&L when closed. |
| `results/signal_analytics.json` | Aggregate analytics: win rate, avg P&L, hold distribution. |
| `results/portfolio_history.csv` | Daily paper NAV (used by vol-target scalar + kill gate). |
| `results/paper_portfolio.json` | Live paper ledger (positions, cash, unrealised P&L). |
| `results/paper_trades.json` | Closed paper trades with fills and costs. |
| `results/paper_ledger_history.csv` | Full paper trade history. |
| `results/kill_state.json` | Kill-criteria state machine (deployment start, triggered metrics). |
| `results/kill_log.jsonl` | Observe-period verdict audit trail (pushed since W-06). |
| `results/cron_health.json` | Monitoring heartbeat: status, last_run_at, universe_size, kill_criteria_mode, data-foundation sub-statuses. |

**Stage 10 — Push to GitHub**

`data.github_push.push_results` commits all result files to the repo via the GitHub
REST API (`LH_PUSH=1`; uses the built-in `GITHUB_TOKEN`). The commit message is
`long-horizon signals YYYY-MM-DD (N new, M held)`. The FastAPI backend then reads from
`results/` locally (or from the GitHub API fallback via `github_data.py`) and the
React dashboard serves the data.

### 2.3 What the operator reads

After each run the three primary files to check are:

**`results/signals_today.json`** — open the envelope:
- `trading_day`: confirm it matches today (if stale, the cron failed).
- `regime`: BULL / CHOPPY / BEAR (breadth-based, display only — not a gate).
- `n_new / n_held`: typical is 0–3 new entries and 10–15 held.
- `vol_target.scalar`: if < 1.0, sizing is being de-grossed (the vol overlay fired).
- `signals[*]`: for each new entry — `grade` (A/B/C), `entry`, `stop_pct`, `target_pct`,
  `rr`, `buy_window_until` (T+3 limit), `debt_equity`, `sector`.

**`results/cron_health.json`** — check `status` (`ok / degraded / failure`) and
`last_run_at` (should be within the past 24h on a trading day). The `kill_criteria_mode`
field tells you whether the gate is in observe or enforce. On `degraded`, the `message`
field names the cause (stale cache, thin fetch, stale fundamentals, membership drift,
structural OHLCV corruption, or as_of alignment below 70%).

**`results/portfolio_history.csv`** — the paper NAV curve. Watch for drawdown relative
to the ~−40% research baseline. If the 30-day trailing Sharpe turns negative for a
sustained stretch, that is the first rollback trigger to review (see §6).

---

## 3. Weekly and research cycle

The strategy's parameters are **frozen**. The weekly cycle is therefore primarily
monitoring, not tuning. Research work follows a strict protocol.

### 3.1 Weekly monitoring checklist (each Monday or after a missed run)

1. Check `cron_health.json` for every run since last Monday — any `degraded` or
   `failure`? If `failure` on a trading day and no alert fired, the `DRIFT_ALERT_SLACK_WEBHOOK`
   secret may not be configured (see §4.2).
2. Scan `signals_history.json` for any signal closed in the last week: were exits via
   trailing stop (expected ~57%), stop (expected ~20%), or target (expected ~19%)? A
   persistent stop-heavy week in a trending market deserves a note in the trade journal.
3. Check `cron_health.json` for `fundamentals_status`: if `degraded`, the Screener
   fundamentals snapshot needs a manual refresh (the store's latest `period_end` has
   gone > 200 days behind the current date).
4. Check `membership_only_current` in the latest `cron_health.json`: should be ~48
   (known AUD-007 gap, below the 75-name alert). A jump above 75 means
   `config.NIFTY_500` has gone dangerously stale and needs a refresh from the NSE list.
5. Check `demerger_suspect` in the printed cron log: any new names appearing? A newly
   suspected name may need verification against the corporate-actions calendar.

### 3.2 Research hypothesis → harness → registry → ADR → (maybe) promote

Any proposed change to the live strategy — a new feature, an overlay, a parameter
adjustment — runs through this protocol:

```
1. PROPOSE  — one-sentence mechanism. Why now? What new evidence?
2. PRE-REGISTER  — write a pre-reg in diagnostics/research/preregistry/.
                   State the exact gate (e.g. "promote if post-tax post-cost
                   ΔSharpe ≥ +0.10 AND ΔCalmar ≥ +0.05") BEFORE running.
3. HARNESS  — run on the research backtest (cloud cpcv-research.yml on the
              corrected 682-name universe). Never trust a local-only run for
              a promotion verdict (survivor-only live cache ≠ backtest dataset).
4. RECORD   — write the verdict (PROMOTE-CANDIDATE / UNDERPOWERED / KILL)
              and the root cause in the pre-reg file. KILL means killed forever
              unless genuinely new evidence emerges.
5. ADR      — if PROMOTE-CANDIDATE: write a decision record (docs/decisions/),
              update the golden master in the SAME PR (never separately).
6. PROMOTE  — only if ALL bars in §3.3 clear. Shadow first if 4–5 hold.
```

Do NOT run this cycle on the live paper book. The paper book's job is to accumulate
a track record, not to evaluate hypotheses.

### 3.3 The promotion bar (mandatory for any overlay)

Promote only if **all** of:

| Gate | Threshold |
|---|---|
| Post-tax post-cost ΔSharpe | ≥ +0.10 |
| ΔCalmar | ≥ +0.05 |
| 2022–2026 sub-period | positive ΔCAGR |
| Walk-forward fold-pass | ≥ 60% |
| Bootstrap 95% CI on ΔSharpe | excludes 0 |
| Turnover increase | ≤ 30% |
| Mechanism | explainable in one sentence |

Shadow (flag-gated, no live trade) if 4–5 hold. Reject otherwise. This bar exists
because every tested overlay that looked good in-sample was killed by honest
out-of-sample validation (§11 of `STRATEGY_FULL.md`). The bar is what the vol-target
overlay (0068) cleared before shipping to paper.

### 3.4 What not to re-test

These were tested and killed (`STRATEGY_FULL.md §11`, `long_horizon/brain.md`).
Do not relitigate without genuinely new evidence:

- Market-regime / dual-momentum gate (cuts DD but kills CAGR; whipsaws 2022)
- Residual / beta-stripped momentum
- Frog-in-the-pan / path-smoothness momentum
- Sector-residual momentum + sector overlays (IC ≈ 0, hurt lean years)
- Reversal signals (RSI / MACD / ROC / Donchian — Sharpe < 0.5, DD −60 to −81%)
- Signal-level low-volatility blending
- Heavier quality screens (earnings + ROE) on top of the debt filter (over-filters)
- `min_hold = 20` — the worst point in the hold sweep (~22% CAGR / 0.86 Sharpe)

---

## 4. Monitoring

### 4.1 `cron_health.json`

Written every run to `results/cron_health.json` (pushed to GitHub). Structure:

```json
{
  "last_run_at": "2026-06-27T10:47:12Z",
  "status": "ok | degraded | failure",
  "message": "3 new + 12 held",
  "strategy": "LONG_HORIZON",
  "trading_day": "2026-06-27",
  "signals_count": 15,
  "universe_size": 172,
  "n_new": 3,
  "n_held": 12,
  "regime": "BULL",
  "download_requested": 500,
  "download_returned": 497,
  "used_pickle_fallback": false,
  "cache_freshness": "ok",
  "fundamentals_status": "ok",
  "solvency_coverage_frac": 0.84,
  "membership_divergence": 48,
  "kill_criteria_mode": "observe",
  ...
}
```

Degradation triggers (any one → `"status": "degraded"`):

| Condition | Threshold |
|---|---|
| Fresh fetch returned | < 50 usable names (hard floor; pickle fallback) |
| OHLCV cache stale | Panel lags wall-clock IST today by > 3 trading days |
| Split-heal backlog | > 10 names deferred |
| Fundamentals stale | Latest `period_end` > 200 days behind today |
| Membership divergence | config vs current index > 75 names |
| As-of alignment | Rankable cross-section < 70% of recent norm |
| Structural OHLCV corruption | > 3 names with High < Low / NaN close / bad dates |

A `"status": "failure"` means the runner exited non-zero (empty universe, missing
required column, corrupt frozen config) — no signals were written.

### 4.2 Alerts (`_alert` / `monitoring.alert_publisher`)

Alert calls exist throughout the cron (`_alert("degraded", ...)` on any data-health
degradation; `_alert("failure", ...)` on any hard exit; `_alert("degraded", ...)` on
a failed GitHub push). They are no-ops until the owner configures the
`DRIFT_ALERT_SLACK_WEBHOOK` secret in the repository settings.

**To activate:** set `DRIFT_ALERT_SLACK_WEBHOOK` as a repository secret in
GitHub → Settings → Secrets → Actions. The workflow already wires it via
`DRIFT_ALERT_SLACK_WEBHOOK: ${{ secrets.DRIFT_ALERT_SLACK_WEBHOOK }}` (W-03, shipped
2026-06-27). A Slack incoming-webhook URL is the simplest integration.

Until the secret is set: monitor by polling `results/cron_health.json`
`last_run_at` staleness manually. A run that does not appear in the repo within 30
minutes of 4:15 PM IST on a trading day is a missed scan.

### 4.3 Kill-criteria gate (observe mode)

The gate reads the paper equity curve (`portfolio_history.csv`) and signal history
(`signals_history.json`). In `observe` mode it logs the verdict to `kill_log.jsonl`
and prints to the cron log, but never blocks entries or resizes positions.

The gate is in observe mode until the owner reviews ≥ 30 paper trades / ~2 months of
paper data and explicitly flips `KILL_CRITERIA_MODE` to `enforce` in the workflow env.
Thresholds are calibrated for the long-horizon DD profile in `configs/kill_criteria.yaml`.

Check `kill_log.jsonl` after each week: if `triggered_metrics` is non-empty in the
verdict log, investigate the cause before the gate is in enforce mode.

### 4.4 Forward-wall decay monitor

The headline is a research backtest: **GROSS 26.1% CAGR / 1.02 Sharpe / −41.9% DD; AFTER-TAX 23.1% / 0.83** on the
canonical 682-name corrected universe (frozen cfg, 397 solvent names, 2017–2026, exit-parity unified; previously reported optimistic-exit 30.26% / 1.15, superseded by baseline_v0.json 2026-06-27).
Walk-forward ≥ 2019 figures are pending re-confirmation on the honest baseline. It has never traded a live rupee.

The paper book is the forward wall. Watch:

- **Win rate** vs expected 63% — a sustained < 50% over 20+ paper trades warrants review.
- **Per-trade avg P&L** vs expected ~2.9% (gross) — compression signals cost or fill
  realism issues.
- **Drawdown path** vs the −40% research baseline — the paper book may never hit −40%
  in a 2-month window, but a rapid −15% to −20% in the first 2 months is a yellow flag.
- **Sub-period**: 2022–2026 (the "harder regime") printed ~21.5% CAGR / 0.84 Sharpe in
  the backtest — noticeably below the full-period headline. Expect live to land somewhere
  in this range, not at the full-period ~30%.

---

## 5. Incident response

### 5.1 Degraded scan (cron ran but `status: degraded`)

1. Read `cron_health.json` `message` for the specific cause.
2. For a stale OHLCV cache (cache_freshness = degraded): signals were ranked on prices
   that may be 1–3 days old. The paper book is still correct (it uses the same stale
   data consistently). No action needed unless staleness persists beyond 3 consecutive
   trading days.
3. For a thin fresh fetch (`download_returned` much lower than `download_requested`):
   yfinance rate-limiting. The merged cache carries the universe, so signals are still
   published. No action needed for a single day; if it persists for 3 days, investigate
   yfinance API status or add a retry delay.
4. For stale fundamentals (`fundamentals_status: degraded`): manually refresh
   `data/fundamentals_pit_screener.pkl` from the Screener PIT source. The solvency filter
   is running on stale D/E — risk is low (D/E changes slowly), but the refresh is overdue.
5. For a split-heal backlog > 10: aged corporate-action events that the incremental
   heal cannot address. Review the names in the printed log; if any are in the held book,
   check their slope values manually against a clean source.

### 5.2 Failed scan (cron exited non-zero, `status: failure`)

1. Check the GitHub Actions run log for the error. Common causes:
   - **Empty universe after filters** — the membership/liquidity/solvency pipeline yielded
     0 names. Check `fundamentals_status` and `download_returned` in `cron_health.json`.
     If `used_pickle_fallback: true` AND the universe is still empty, the fundamentals
     pickle may be corrupt — restore from the last committed version.
   - **Missing required column** — a future pipeline change dropped one of
     `sma200_slope_63`, `atr_pct_63`, `adv_rupees_20d`, or `close` from the feature
     output. This fails loud with an `ERROR:` line identifying the missing column.
     Fix the feature pipeline before the next scan.
   - **Corrupt frozen config** — `validate_frozen_cfg` found a missing or non-numeric
     value in `models/long_horizon/config.json`. Restore the last committed JSON.
2. `signals_today.json` was not updated. The dashboard serves the previous day's data
   (signals from yesterday are still valid; the held positions just have no updated exit
   checks for today).
3. If the failure recurs on the next day, declare an incident: pause new entries manually
   (post to the user channel), investigate, fix, and run `workflow_dispatch` to force a
   catch-up scan after the fix lands on `main`.

### 5.3 Stale OHLCV cache (cold-start risk)

The cache at `results/ohlcv_cache_lh.json` is a git-tracked, committed file (whitelisted
in `.gitignore`). It is NOT in danger of being lost by a normal `git clean -fd`.

Risk scenario: someone does `git rm --cached results/ohlcv_cache_lh.json` and pushes.
The next cron run performs a 600-calendar-day cold-start (~3–5 minutes, ~500 yfinance
calls). This is slow and yfinance-rate-limit-risky but not data-destructive — the cache
rebuilds itself. To avoid: never run `git rm --cached` on `results/ohlcv_cache_lh.json`.
If the cold-start happens, the first run will take longer and may partially fail on
rate-limits; re-run via `workflow_dispatch` the following day.

### 5.4 Demerger-suspect name appearing in the held book

The W-01 quarantine guard (`_demerger_suspect`) blocks a demerger-suspect name from
**new entries** but does not force-exit an already-held position. If a held name
undergoes a spin-off demerger after it was entered:

1. The cron prints a `W-01 demerger quarantine:` line naming the suspect.
2. Its `sma200_slope_63` may be fabricated (split-adjusted). Do NOT use the slope or
   rank for any decision on this name.
3. The stop, target, and trailing values were set at entry on clean data and remain valid
   as exit triggers.
4. The position will exit naturally via its stop, target, trailing, or time cap.
   No manual intervention is required unless the fundamentals also changed materially (a
   spin-off changing D/E substantially warrants manual review).
5. Log the name in the trade journal with a note: "Corporate action during hold; slope
   unreliable from [date]; exits on contract terms."

### 5.5 Rollback

There is no env-var rollback for the long-horizon strategy (v1 was deleted entirely on
2026-06-25). To revert to the v1 LightGBM scanner, restore the v1 files from git history
before commit `c0fbd1d` and re-point the workflow. This is a full code rollback, not a
config flip.

To disable the vol-target overlay (the only live-param that can be toggled without a
code change): set `vol_target_annual = 0` in `models/long_horizon/config.json →
live_overlays` and push. The next cron run will use `vol_scalar = 1.0` (no de-gross).

---

## 6. Gate to real capital (pre-committed)

The paper book must accrue **≥ 30 closed paper trades / ~2 months** and the owner must
review the live-vs-backtest behaviour (fill realism, hit rates, drawdown path) before
any real capital is committed. The strategy is paper-trade-ready; it is **not**
real-capital-ready. This gate is pre-committed and cannot be waived by any single-session
decision.

Observable kill triggers (any one fires → pause and review before real capital):

| Trigger | Threshold | Source |
|---|---|---|
| Win rate collapse | < 45% on any rolling 20 closed paper trades | `signals_history.json` outcomes |
| Realized avg P&L | < 0% over 20 closed trades | `signal_analytics.json` |
| 30d paper Sharpe | Negative while all-time paper Sharpe ≥ 0 | `portfolio_history.csv` |
| Drawdown pace | > −15% peak-to-trough within the first 60 paper days | `portfolio_history.csv` |
| 0 new entries | 5+ consecutive trading days with `n_new = 0` | `cron_health.json` |

These are not automatic kill-gate enforcement conditions (the code gate uses
`configs/kill_criteria.yaml`). They are owner judgment prompts: see them → investigate →
decide.

---

## 7. Skills and procedures

| Situation | Skill / procedure |
|---|---|
| Propose a new overlay or feature | `diagnostics/research/preregistry/` — write pre-reg first, run harness second |
| Manual backtest run | `python diagnostics/run_long_horizon_tradelog.py` (local, uses cached data) |
| Cloud canonical backtest | `.github/workflows/cpcv-research.yml` via `workflow_dispatch` |
| Force a scan outside schedule | `.github/workflows/cron-scanner.yml` → `workflow_dispatch` |
| Refresh fundamentals pickle | Manual: re-scrape Screener PIT source → commit new `data/fundamentals_pit_screener.pkl` |
| Investigate a specific name | Read its row in `results/signals_history.json`; check raw close in `results/ohlcv_cache_lh.json` |
| Code review before merging to `main` | `/code-review` skill — always before anything that touches `src/runners/long_horizon_cron.py`, `long_horizon/`, or `trading/signal_tracker.py` |
| Verify a fix works | `/verify` skill — run the live scanner locally via `python -m src.runners.long_horizon_cron` (omit `LH_PUSH`); compare `cron_health.json` status |
| Add a new monitoring hook | Extend `_write_cron_health` + `assess_data_health` in `long_horizon_cron.py`; add a seam test |

---

## 8. Open deferred work (what is NOT yet fixed)

Phase 1 closed the safe subset. Items deferred to the cloud backtest gate or Task-8
data work:

| W-id | Title | Gate |
|---|---|---|
| W-01 (root fix) | CA-type-aware cleaner in `data_store.py` (vs the live quarantine guard already shipped) | Golden-master regeneration + cloud re-derive |
| W-02 (universe union) | Add 48 invisible current index members to `ds.stocks` | Task-8 data work (they lack PIT fundamentals; expansion is a no-op today) |
| W-04 | Explicit financials D/E policy (banks/NBFCs as a known exclusion, not silent drop) | Documentation + cron_health observability (no behavior change needed) |
| W-12 | Kill-equity curve books entry at close(t), not open(t+1) | Subsumed by W-05 fix; low priority |
| W-15 | GitHub push partial-success alerting | Ops polish |
| W-16 | Kite session refresh cron | Ops (no signal-path impact) |
| W-17 | Sub-50% demerger monitoring (TRENT/IEX) | Low — currently benign |
| W-19 | yfinance second-source reconciliation against Kite quotes | Medium — nice to have |

The honest headline backtest (26.1% CAGR / 1.02 Sharpe gross; 23.1% / 0.83 after-tax) is **not reproducible locally** —
`data/ohlcv.pkl` and the expanded-universe panel are absent from this repo. The cloud
`cpcv-research.yml` path rehydrates the corrected universe; run it there before building
any new research layer on top of baseline_v0.json (committed 2026-06-27).

---

## 9. Research operating path (2026-06-27 reframe)

*Owner decisions confirmed 2026-06-27. This section maps the destination-ordered
roadmap to the daily operating model — which skills apply at each stage, when to stop
and gate, and how the paper-book clock interacts with the re-derivation work.*

### 9.1 The destination and the honest tradeoffs

**The destination:** a corrected-universe, conviction-layered, fully-validated system
trading real capital for ~10 paying users. Quality before speed.

**Three owner decisions that set the shape of everything below:**

1. **Hold live until the conviction layer is in.** The frozen base does NOT go live on
   its own. Real capital waits on the full research track (Stages A → E).
2. **Model evolution = conviction-within-top-15, only.** The conviction layer operates
   on sizing, exit multipliers, and risk limits — not on adding new signals. The defined-risk
   tail hedge and vol-carry second stream are **deferred** (off the near-term critical path;
   revisit post-live).
3. **Fix the universe BEFORE live.** The corrected/widened universe is rebuilt first;
   the frozen cfg is re-derived on it; the headline may move. We anchor to the honest new
   number, whatever it is.

**Honest tradeoffs (do not hide these):**

| Tradeoff | Detail |
|---|---|
| Path to first real rupee is longer | Foundation re-derivation + conviction model + hybrid layers + a **fresh** ≥30-trade paper window all precede live capital |
| The headline has moved | Re-derived on the corrected universe via baseline_v0.json (2026-06-27): honest gross 26.1% CAGR / 1.02 Sharpe (after-tax 23.1% / 0.83), vs prior optimistic-exit 30.26% / 1.15. This new number is the anchor — not the old one. |
| Paper-gate clock resets at Stage B | The current paper book is on the old base. The ≥30-trade gate clock restarts when the corrected base enters paper. |
| Stages C/D may mostly KILL | The §11 kill history is long. Conviction must earn its place through the same harness. If it cannot clear the bar, the corrected frozen base is still shippable — then revisit decision #1. |

---

### 9.2 Stage A — Trustworthy statistical harness

**Objective:** reproduce the frozen-cfg headline within ≤1pp CAGR and ≤0.05 Sharpe on
the cloud canonical run; lock the harness as the ground truth for all subsequent stages.

**What to build:** `src/research/` statistical harness. **Reuse, do not reinvent:**

- `src/validation/{cpcv, overfitting, bootstrap, power, factor_metrics, null_test}` —
  already exist; wire them into the harness rather than reimplementing.
- `long_horizon/backtest/portfolio.simulate` — the walk-forward engine that produced the
  headline; the harness calls this.
- The pre-registration framework in `diagnostics/research/preregistry/`.

**Gate:** the harness must reproduce the honest baseline_v0 headline (gross 26.1% CAGR / 1.02 Sharpe, after-tax 23.1% / 0.83) within ≤1pp / ≤0.05 on
the cloud `cpcv-research.yml` run AND must replicate the §11 KILLs (all killed overlays
remain below the promotion bar when re-run through the harness). Persist the equity curve
as `baseline_v0.json` (committed 2026-06-27; this supersedes the prior optimistic-exit 30.26% / 1.15 figure).

**Skills at this stage:** `engineering:testing-strategy` (harness structure),
`backtest-rigor` (reproduction gate), `data:validate-data` (sanity-checking the
rehydrated universe panel).

**Stop-gate discipline:** do not start Stage B until the harness reproduction run is
complete and `baseline_v0.json` is committed. A green number in a local notebook is not
sufficient — the cloud canonical run must pass.

---

### 9.3 Stage B — Corrected universe + re-derived base

**Objective:** widen the universe, fix the known gaps, re-derive the frozen cfg on the
honest dataset, and reset the paper book.

**What to do (in order):**

| Step | Task | Reference |
|---|---|---|
| B1 | CA-type-aware cleaner in `data_store.py`: split vs demerger via yf corporate actions (the VEDL lesson; W-01 root fix) | W-01 in §8 above |
| B2 | Universe union: `current_members ∪ config.NIFTY_500` — adds the ~48 invisible current members (W-02); source PIT fundamentals and delisted OHLCV for the new entrants | W-02 in §8 above |
| B3 | Financials capital-adequacy policy: explicit D/E proxy for banks and lending NBFCs so they are included or excluded by a stated policy, not a silent NaN drop (W-04) | W-04 in §8 above |
| B4 | Re-derive frozen cfg: new pre-registration → walk-forward on the corrected universe → regenerate `models/long_horizon/config.json` → regenerate the golden master → persist `baseline_v1.json` + commit ADR-0003 | docs/LIVE_OVERLAY_PROTOCOL.md |

**After B4: restart the paper book.** The ≥30-trade gate clock (§6 / Stage E) begins
here, not at the original paper-book start. Paper trades on the old base do not count
toward the Stage E gate.

**Gate (ADR-0003):** the corrected-universe walk-forward holds (Sharpe ≥ 0.90 on at
least 60% of folds; 0 negative years in the 2019-onwards slice). The new config values
are whatever the re-derivation produces — do not force them to match the current frozen
params (`stop_atr_mult` 3.67, `target_pct` 22.52, `trailing_activate_pct` 4.0 /
`trailing_pct` 4.27, `min_hold_days` 10, `max_hold_days` 63, `risk_per_trade_pct` 3.0%,
`max_position_pct` 15%, `max_positions` 15). If they move materially, that is a finding,
not an error.

**Skills at this stage:** `data:data-quality` (OHLCV cleaning, universe expansion),
`engineering:testing-strategy` (golden-master regeneration), `backtest-rigor`
(walk-forward re-derivation on the cloud path).

**Stop-gate discipline:** do not start Stage C until `baseline_v1.json` is committed,
the new `config.json` is in place, and the paper book has been reset.

---

### 9.4 Stage C — Conviction model (within top-15)

**Objective:** build a PIT-safe conviction score that separates the top-15 by expected
quality, without adding a new outer signal.

**What to build:** `src/research/conviction.py`. Model form must be **inspectable** —
z-score blend, logistic regression, or a ranked composite. No uninspectable ML (no tree
ensembles, no neural nets) at this layer; the mechanism must be explainable in one
sentence.

Candidate conviction features (all must be PIT-safe at the scan date):
- Trend-strength magnitude and slope-acceleration (derivatives of `sma200_slope_63`)
- Cross-sectional rank stability over a rolling window (rank volatility)
- Liquidity quality (ADV trend, not just the 20d snapshot)
- Solvency margin (D/E distance from the 1.5 cap)

**Validation:** run through the Stage A harness. Compare `conviction-top-15` vs
`rank-only` on `baseline_v1.json`'s universe. The promotion bar from §3.3 applies in
full (post-tax post-cost ΔSharpe ≥ +0.10, ΔCalmar ≥ +0.05, 2022–2026 positive, fold-pass
≥ 60%, bootstrap CI excludes 0, turnover ≤ +30%, mechanism explainable).

**Output (if promoted):** `conviction_score` and `conviction_quintile` (Q1 = lowest,
Q5 = highest) appended to each signal in `signals_today.json`.

**Skills at this stage:** `engineering:architecture` (conviction module design),
`backtest-rigor` (harness validation vs rank-only), `data:statistical-analysis`
(IC/IR of candidate features, PIT sanity checks).

**Stop-gate discipline:** if the conviction model cannot clear the promotion bar, record
the KILL in the pre-reg and stop. Do not proceed to Stage D with a marginal model. The
corrected frozen base (Stage B output) is itself shippable — revisit decision #1 at that
point.

---

### 9.5 Stage D — Conviction-driven hybrid layers

**Objective:** wire the conviction quintile into sizing, exit multipliers, and risk limits.
Each layer is promoted separately — a layer that does not clear the bar is rejected
independently of the others.

**Four candidate layers (each requires its own pre-reg and harness gate):**

| Layer | Mechanism | Gate notes |
|---|---|---|
| **Sizing** | Quintile-scaled risk budget: Q5 gets a higher allocation, Q1 lower; mean preserved so overall capital deployment is unchanged; 15% position cap continues to bind | Most likely to clear — reduces concentration risk without changing the outer rank signal |
| **Exit multipliers** | Q1 uses tighter stop/trailing (risk is acknowledged lower-quality); Q5 uses wider stop/trailing (let the best trends run longer) | Tricky to gate cleanly — turnover cap at ≤ +30% is strict |
| **Risk limits** | Soft sector/correlation caps at the portfolio level, modulated by conviction distribution (higher cap when Q5 names are spread across sectors, tighter when concentrated) | Mechanism must be fully explainable and PIT-safe |
| **Sell/replace logic** | S1–S7 (sell candidates) and R1–R4 (replacement candidates) policies; conviction informs which held positions are replaced first when a higher-quintile entrant appears | Requires careful treatment of min-hold (10d hard floor is never suppressed) |

**Skills at this stage:** `sell-replace-logic` (S/R policy framework),
`edge-research-pipeline` (pre-reg → harness → gate → ADR cycle),
`backtest-rigor` (each layer validated individually before stacking).

**Stop-gate discipline:** promote each layer independently. A layer that KILLs does not
block the others. Do not stack unvalidated layers — the §11 history demonstrates that
interactions can surprise.

---

### 9.6 Stage E — Paper-revalidate the full conviction system

**Objective:** accumulate ≥ 30 closed paper trades (~2 months) on the re-derived base
with the promoted conviction layers active; flip kill-criteria from observe to enforce.

This is the pre-committed real-capital gate. The clock starts at Stage B (paper book
reset). The same thresholds from §6 apply:

| Trigger | Threshold |
|---|---|
| Win rate | ≥ 45% on any rolling 20 closed paper trades |
| Realized avg P&L | ≥ 0% over 20 closed trades |
| 30d paper Sharpe | Non-negative while all-time paper Sharpe ≥ 0 |
| Drawdown pace | ≤ −15% peak-to-trough within the first 60 paper days |
| Signal continuity | No stretch of 5+ consecutive trading days with `n_new = 0` |

During Stage E: `KILL_CRITERIA_MODE=observe`. After the 30-trade / 2-month review with
no triggers fired: flip to `KILL_CRITERIA_MODE=enforce` and record the ADR.

**Skills at this stage:** `backtest-rigor` (verify live/backtest parity on the paper
fills), `engineering:incident-response` (any triggered kill metric → follow §5 protocol).

---

### 9.7 Stage F — Live capital

After Stage E clears, real capital can be deployed. The pre-committed kill switch from §6
transitions from paper to live — the same thresholds, now on real-money fills.

**Continuous monitoring after live:**

| Monitor | Check | Frequency |
|---|---|---|
| Kill switch | WR < 45% / 20 trades, 30d Sharpe < 0, 5-day zero-signal | Each scan |
| Decay monitor | 90-day rolling IC of `sma200_slope_63` — if IC falls below 0.02 for 10 consecutive weeks, open a pre-reg for the signal's continued relevance | Weekly |
| Data-quality | `cron_health.json` `status` and `fundamentals_status` | Each scan (§4.1) |
| Universe staleness | `membership_divergence` in `cron_health.json` | Weekly (§3.1) |

---

### 9.8 Deferred work (off the critical path)

The following are NOT blocked by the A→F sequence but are deliberately off the
near-term critical path per the 2026-06-27 owner decision:

- **Defined-risk tail hedge** (options overlay) — deferred post-live. Revisit after the
  conviction layers have accumulated forward-wall data.
- **Vol-carry second stream** (options volatility-risk-premium as a structurally
  orthogonal return stream) — deferred post-live. The two-premium portfolio is the
  longer-term architecture; it requires a separate backtester and a fresh paper gate.
- **Swing-trading program** — deferred post paper-gate (Stage E). No overlap with the
  long-horizon book until the real-capital gate clears.

---

### 9.9 Stage-gate summary

```
Stage A  Statistical harness reproduces headline ≤1pp → baseline_v0.json committed
    ↓
Stage B  Corrected universe + re-derived cfg → paper book RESET → baseline_v1.json committed
    ↓
Stage C  Conviction model clears promotion bar → conviction_score in signals_today.json
    ↓
Stage D  Each hybrid layer (sizing/exit/risk/sell-replace) gated independently
    ↓
Stage E  ≥30 paper trades / ~2 months, no kill triggers → kill-criteria flipped to enforce
    ↓
Stage F  Real capital deployed; kill switch + decay monitor active continuously
```

At each arrow: **stop, run the gate, record the ADR, then proceed.** Rushing a gate to
reach the next stage faster is how a §11-class KILL slips into production. The
destination is worth the discipline.
