# Data map — where every number on the site comes from (audit, 2026-11-12)

Purpose: answer three questions for every page — **which data**, **whose data** (shared vs per
user), and **is the math right** — so the redesign wires pages to the right source instead of
re-deriving numbers in 1,700-line components. Companion to `docs/DESIGN_BRIEF_V5.md` §12 (refresh).

## 1. Whose data: the per-user model (already enforced by the backend)

ADR 0011 removed per-user broker links. Since then there are exactly three kinds of data, and
`dashboard/backend/tests/test_tenant_isolation.py` enforces the split:

| Kind | What | Endpoints | Who sees it |
|---|---|---|---|
| **Shared model output** | weekly-swing signals, regime, sell guidance, backtest, website stats | `/api/signals*`, `/api/backtest/bhanushali`, `/api/landing-stats`, `/api/yahoo/*` | every signed-in user (the last two are public) |
| **Owner's paper book** | the model's paper portfolio: NAV, positions, trade log, performance metrics | `/api/overview*`, `/api/positions`, `/api/portfolio/nav-history`, `/api/trades*` | **admin only** — members get an empty, zeroed payload by design |
| **Per user** | the user's own self-reported fills (the execution ledger) → their holdings, realised P&L, reconciliation vs the model; watchlist; sizing prefs; onboarding flags | `/api/execution/*`, `/api/watchlist*`, `/api/journey*`, sizing prefs | only that user (`user_id` on every row) |

**Rule for the redesign:** a page never mixes the three without labelling them. "Your" numbers
come only from the ledger; "the model's" numbers come from signals/paper book; a member must not
see an admin-only panel rendered as an empty-looking real figure — hide it or say "owner only".

**Per-user prices.** A user's holdings are priced with the *owner's* daily-close quotes
(`useQuoteBatch`), never a user broker feed. No cash/NAV is invented for a user: value =
Σ(remaining shares × last close).

## 2. Page by page

| Page | Shows | Source | Kind | Refresh |
|---|---|---|---|---|
| Website | backtest headline, growth chart, calendar years | `/api/landing-stats` — **hardcoded constants** in `routers/landing_stats.py` | shared | static |
| Website | ticker | `/api/yahoo/index-sparklines` | shared | 5 min while NSE open |
| Dashboard | regime, breadth, VIX, Act now, Fresh buys, Model book | `/api/signals?model=bhanushali` | shared | publish-aware (§12) |
| Dashboard | Your positions | `/api/execution/positions` + daily-close quotes | per user | focus |
| Dashboard | Model health (win rate, max DD) | `/api/overview` metrics | **admin only** — members see "—" | publish-aware |
| This week | buys open, exits due, sizing | signals + ledger + `/api/execution/reconciliation` + sizing prefs | shared + per user | focus |
| Research | the book, closed this cycle | `/api/signals` | shared | publish-aware |
| Track record | headline, equity, cum R, years, exits, trades | `/api/backtest/bhanushali` — **computed from** `research/exports/bhanushali_weekly_rank_0094_trades.csv` | shared | static |
| Portfolio · Yours | holdings, realised P&L, actions | ledger + quotes + reconciliation | per user | focus |
| Portfolio · Paper | NAV, curve, metrics, positions, trades | overview / nav-history / positions / trades | **admin only** | publish-aware |
| Research (merged with History, 2026-11-12) | every issued call and its return since issue | `/api/signals/history` | shared | 15 min stale + focus |

## 3. Math findings

**Fixed**
- **Re-entry average cost (backend, `services/execution_ledger.py`).** After a full exit and a
  re-entry (buy 10@100, sell 10@110, buy 10@200) the open position reported avg 150 / cost basis
  1,500 instead of 200 / 2,000, mispricing unrealised P&L on every re-entered position. Fixed to
  average-cost over shares still held; regression test added. Commit `f8a3712`.

**Resolved 2026-11-12 (owner: "re-run the numbers, hide owner-only panels")** — measurement only,
no trial spent; method per `/plausibility-check` against the frozen-0094 anchor
(`docs/references/plausibility_anchors.md` §6: CAGR 24.7%, MaxDD −42.4%, Sharpe ~1.132).

1. **8.11× vs 10.1× — reconciled.** The website constant matches the anchor: 24.7% CAGR over the
   export's window (2017-01-30 → 2026-06-29, 9.41 y) compounds to ≈8.0×, consistent with 8.11×.
   The 10.1× was never a competing measurement: `/backtest/bhanushali` builds an R-compounded
   illustration (each trade risks 2% of NAV, trades taken one after another), which overstates
   the result by treating overlapping trades as sequential (implied ≈28.7% CAGR, ~4pp above the
   anchor — "better than the anchor" was the defect signal). Fix: Track record now charts the
   committed 0094 portfolio growth curve (`EQUITY_CURVE_BT`, 8.11×, vs Nifty 500); the endpoint
   labels its curve `equity_curve_method: "r_compounded_sequential"` and keeps it only for API
   compatibility.
2. **Website calendar-year % — not reproducible, withdrawn.** The comment called them baseline_v1
   after-STCG returns; they are not (baseline_v1's `daily_returns.csv` gives 2018 −4.7% vs the
   site's +11.6%). They follow the 0094 curve's shape but differ from it by up to ~7pp and cannot
   be reproduced without the pinned price data, so the website no longer shows them. Both pages
   now show **trades, win rate and total R by exit year**, computed exactly from the committed
   trade export by one shared helper (`yearly_breakdown`); the per-year R sums to the +122.7R
   cumulative figure. `YEARLY_RETURNS` stays in the payload, marked deprecated, for old clients.
3. **Owner-only panels hidden from members.** Portfolio's Paper view and Dashboard's paper win
   rate / drawdown render only for admins, and members no longer request that data. Found on the
   way: Portfolio's performance and risk strips read the paper book's metrics even in the
   **Yours** view, so the model's Sharpe/drawdown appeared labelled as the user's. They now show
   only in the Paper view.

**Still open**
- ~~Missing price shows as zero P&L~~ — fixed 2026-11-12 in the Portfolio rebuild and Dashboard:
  price = owner's daily-close quote, else the model's own daily re-price of that call
  (`current_price`), else "no price yet" and excluded from value and P&L. Never priced at cost.
- **Wiring facts found against the real API** (not visible with mocks): signals carry no
  `signal_id` (derived as `TICKER__signal_date`, `lib/signalId.js`); freshness fields are
  `scan_time` and `monitor_generated_ist`; `regime.vix` is 0 when absent (India VIX now comes
  from the index feed).
- **Exact calendar-year % for 0094**: needs a re-run of `scripts/run_bhanushali_weekly_rank.py`
  on the pinned price data (not in this container) to export the daily equity series.

## 4. How the redesign uses this

Each page is rebuilt against this table: one data source per panel, labelled shared / yours /
owner-only, a freshness line, and no figure derived in the page that the backend already
computes. Open items 1–2 are research/governance decisions for the owner; 3–4 are frontend fixes
that ship with the Portfolio and Dashboard rebuild.

## 5. Research page — what "return since issue" means (2026-11-12)

The history payload carries two different results per call, and they can disagree in sign:
- **Price return** (`return_pct`): exit price — or the latest daily close for an open call — versus
  entry. What a reader means by "return since issue".
- **Plan result** (`r_multiple`, `net_pnl`): the call's own outcome in R, *including* partial
  profit-taking along the way. Example from the live record: BAJAJ-AUTO −0.44% on price but
  +3.12R / +₹17,477 on the plan (it trimmed at higher prices before the final exit).

The backend's `analytics.win_rate` (5.3% on 38 closed) counts plan results (r > 0); on price
return 0 of 38 closed calls are positive. The page shows both, labelled. Closed calls skew to
losers (stops exit within days, winners run for weeks), so the page always shows open, closed and
all-calls figures together (live: all −2.5%, open +8.7%, closed −7.5%, 15 / 55 positive).
`status` is `HIT_STOP` for every closed call whatever the exit, so outcomes are labelled from
`exit_reason` (stop · stop_part · sma_break), not from `status`.
