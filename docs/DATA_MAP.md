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
| History | every posted call and its outcome | `/api/signals/history` | shared | 15 min stale + focus |

## 3. Math findings

**Fixed**
- **Re-entry average cost (backend, `services/execution_ledger.py`).** After a full exit and a
  re-entry (buy 10@100, sell 10@110, buy 10@200) the open position reported avg 150 / cost basis
  1,500 instead of 200 / 2,000, mispricing unrealised P&L on every re-entered position. Fixed to
  average-cost over shares still held; regression test added. Commit `f8a3712`.

**Open — need the owner / a reproduction before anything changes** (published figures; the
repo rule is reproduce-before-trust, so these were not edited)
1. **Two different figures for the same backtest.** The website's `WEEKLY_SWING_TRACK` constant
   says ₹10L → ₹81.15L (8.11×, CAGR 24.7%). Track record recomputes NAV from the trade export:
   ₹10.05L → ₹101.7L (10.1×) — which over 2017–2026 implies roughly 28–29% CAGR, not 24.7%. One
   of them is stale or uses different sizing; reproduce from the committed pipeline and publish
   one number.
2. **Website calendar-year returns may belong to a different model.** `YEARLY_RETURNS` in
   `routers/landing_stats.py` is documented as *baseline_v1* returns *after* 20% STCG, but the
   website labels them as the weekly-swing book *before* STCG. Either the data or the label is
   wrong.
3. **Missing price shows as zero P&L.** When a holding has no quote yet, the frontend prices it
   at cost (`ledgerHoldingToRow`, Dashboard "Your positions"), so P&L reads 0.0% as if real. It
   should say "no price yet".
4. **Members see admin-only panels as blanks.** Dashboard "Model health" (win rate, max
   drawdown) and Portfolio "Paper" are admin-only; members see "—". Decide: hide for members, or
   label "owner only".

## 4. How the redesign uses this

Each page is rebuilt against this table: one data source per panel, labelled shared / yours /
owner-only, a freshness line, and no figure derived in the page that the backend already
computes. Open items 1–2 are research/governance decisions for the owner; 3–4 are frontend fixes
that ship with the Portfolio and Dashboard rebuild.
