---
name: kite-execution
description: >
  Kite (Zerodha) auth, fill realism, and execution edge cases for the
  NiftyQuant long-horizon strategy. Use when the topic involves "kite",
  "zerodha", "broker", "fill", "slippage", "order", or "execution".
triggers:
  - kite
  - zerodha
  - broker
  - fill
  - slippage
  - order
  - execution
---

# Kite Execution Skill

## 0. Critical separation of concerns — Kite is NOT on the price path

**The signal scanner does not touch Kite for any price data.**

A grep of `src/runners/long_horizon_cron.py` returns zero matches for "kite" or
"zerodha". The sole OHLCV source for the scanner is yfinance via
`data/ohlcv_incremental.py`. Kite's `/quote` LTP endpoint is used by the
dashboard (real-time display) and is referenced as a potential second-source
cross-check in the audit (W-19, open/not yet wired), but as of 2026-06-27
it has zero wiring into the scan path.

**Do not add Kite to the scanner's OHLCV or feature pipeline without an
explicit decision and a golden-master regeneration.** Routing the scanner
through Kite would couple it to session expiry (daily at 6 AM IST), introduce
a paid-subscription dependency on the live signal, and break the clean
yfinance-only reproducibility of the backtest.

Kite powers three dashboard functions only:
- **Holdings** — `useKiteHoldings` (live portfolio display)
- **Margin** — `useKiteMargins` (OrderPad sizing)
- **Order placement** — `useOrderPlacement` / `POST /api/kite/orders/regular`

---

## 1. OAuth flow and daily session lifecycle

### OAuth flow

The Zerodha developer console must have its redirect URL set to
`<origin>/auth/callback` (e.g. `https://niftyquant.vercel.app/auth/callback`
in production). The frontend also passes this explicitly in `connectKite` so
the redirect is deterministic across Vercel preview / production / localhost.

```
User clicks Connect Kite (Header / Settings / any V2 page)
  -> window.location -> kite.zerodha.com/connect/login?api_key=...&redirect_url=.../auth/callback
  -> User approves on Kite
  -> Kite redirects to /auth/callback?request_token=xyz&action=login&status=success
  -> pages/AuthCallback.jsx reads token, calls kiteExchangeToken
     -> POST /api/kite/session/token  (backend stores access_token in KiteSession table)
  -> Toast "Kite connected as <user_id>", navigate to /dashboard
  -> ProtectedAppLayout mount effect refreshes KiteContext via /api/kite/session/status
```

### Session expiry — 6 AM IST daily, no refresh-token flow

Kite access tokens expire every morning at 6 AM IST. There is no silent
refresh; re-auth requires a new OAuth round-trip or a credential-based
programmatic login.

**Detection:** `services/api.js` wraps every Kite endpoint with
`detectKiteSessionExpired`. Any response containing `session_expired` /
`token is invalid` / `access_token is invalid` dispatches a
`kite-session-expired` window event. The listener in `App.js`
`ProtectedAppLayout` flips `KiteContext.connected -> false` and toasts
"Kite session expired — Reconnect". Throttled to once per 30 s to avoid
spam when multiple gated queries fail simultaneously.

**Automated refresh — OPEN OPS ITEM (W-16, audit 2026-06-27):**
`dashboard/backend/refresh_kite_session.py` exists and is wired correctly
(Zerodha credential + TOTP + KiteConnect exchange). It was previously run as
a Render cron at 6:15 AM IST weekdays. The file exists; the GitHub Actions
workflow `cron-kite-refresh.yml` does **not** exist (confirmed: `ls
.github/workflows/` shows no such file). Render was decommissioned 2026-06-25.
The dashboard Kite session therefore expires each morning with no scheduled
refresh. Manual re-auth is the current workaround. Fix: port
`refresh_kite_session.py` to a new GitHub Actions workflow at schedule
`"45 0 * * 1-5"` (6:15 AM IST) with the required secrets
(`ZERODHA_USER_ID`, `ZERODHA_PASSWORD`, `ZERODHA_TOTP_SECRET`,
`KITE_API_KEY`, `KITE_API_SECRET`, `ENCRYPTION_KEY`, `DATABASE_URL`).

---

## 2. Fill realism — what the backtest models

Understanding the fill model prevents misreading backtest vs live divergence.

### Entry

Signal is generated at close(t). Fill is modelled at **open(t+1)** — the next
session's open — with a tiered slippage based on liquidity:

| Liquidity tier | Trailing-median 20d rupee ADV | Base slippage | Notes |
|---|---|---|---|
| Large | >= ~₹500 cr (top-tier liquid) | **0.05%** | RELIANCE/HDFCBANK class |
| Mid | >= ₹5 cr (the universe floor) | **0.22%** | The majority of holdings |
| Small | < ₹5 cr (does not normally enter) | **0.40%** | Below the ADV filter |

Plus a **market-impact surcharge of 0.1%** when the order exceeds **0.5% of the
name's 20-day rupee ADV** (capacity cap also applies: position is capped at 5%
of ADV in shares). Source: `long_horizon/backtest/portfolio.py`, `_slip`.

### Costs — both legs

| Cost | Rate | Applied |
|---|---|---|
| Brokerage | **0.03%** per leg | Both buy and sell |
| STT (Securities Transaction Tax) | **0.10%** | Both legs (long-horizon equity trades; confirmed in `config.py` — note the v1 CLAUDE.md comment that previously misstated brokerage as 0.10% was corrected; brokerage is 0.03%) |

**Total round-trip friction at minimum (large-cap):** 0.03 + 0.05 + 0.05 + 0.03 + 0.10 + 0.10 = ~0.36%.
At mid-cap tier: ~0.70%. The average trade ~2.9% mean return (research backtest) comfortably
exceeds round-trip costs; the 2x-cost stress test still shows 26.5% CAGR / 1.01 Sharpe
(STRATEGY_FULL.md §10.3).

### Exit fills

Exit fills in the backtest (post exit-parity unification, 2026-06-26):

- **Stop loss:** conservative fill at `min(open(t+1), close(t))` when the close crosses
  below the stop. On a gap-down open below the stop, fill is at the open (the worse
  of open and stop), not optimistically at the stop level. This is what the live signal
  tracker was failing to do before the W-05 fix (see §4 below).
- **Profit target:** fill at exactly the target level (conservative — not at the
  intraday high).
- **Trailing stop / time cap:** fill at the close of the exit session.

The live scanner and the backtest now share the same exit-logic function
`src/engine/exit_logic.decide_exit` — they produce byte-identical exit
decisions by construction (exit-parity unification, commit b653f52).

---

## 3. Indicative entry — why the published price is not the fill price

Every new signal is stamped `entry_is_indicative = true`. The indicative entry
is `close(t) * (1 + base_slippage)`. It is **not** the actual fill.

Reasons:
1. The scanner runs at 4:15 PM IST (close of the NSE session). It does not
   know tomorrow's open.
2. The risk-based position size is computed from the indicative entry and the
   ATR stop, but the actual shares bought depend on T+1 open.
3. The dashboard shows `max_entry = indicative * 1.01` as the limit price the
   owner should use when placing the order.

The paper broker (`src/trading/paper_broker.py`) re-prices entry to the
**actual open(t+1)** when the next day's data arrives, so the paper P&L is
filled at the real open, not the indicative close-based estimate.

The buy window is **T+1 to T+3** (3 trading sessions). Signals older than T+3
are stale — the entry opportunity has passed. This is stored as
`buy_window_until` on each signal.

---

## 4. Edge cases — what can go wrong in live execution

### W-05: Gap-down stop exits — FIXED (Phase 1, 2026-06-27)

**What was wrong:** the live signal tracker passed no `open` price to
`decide_exit`. When a position gapped down through the stop on open, the live
system recorded the exit at exactly the stop level (optimistic), while the
backtest correctly filled at `min(open, stop)`.

**Scale:** 297 / 1453 stop exits (20.4%) are gap-throughs where the live paper
P&L was optimistic, with an average gap of -17% below the stop and 199 exits
worse than -15%. This affected the win-rate and P&L statistics in
`signals_history.json` — which is the exact input to the kill-criteria rollback
triggers.

**Fixed:** `signal_tracker.py` (commit b653f52) now passes `open:
current_open` into `decide_exit` and books `sig['close_price'] =
decision.exit_price` (the real gap fill), not the stop level. Regression tests
in `tests/test_lh_live_exit_parity.py`.

### Circuit lock on a held name

If a held name hits an NSE circuit breaker (upper or lower circuit), there is
no fill at that session's open or close — only a matching price with no
counterpart volume. The strategy's close-only stop evaluation means the exit
signal fires at the circuit price, but the order may not execute.

**Current handling:** no circuit-lock-specific logic exists in the signal
tracker. The recorded exit price will be the circuit limit (usually at or near
the stop). This is realistic for lower-circuit events (the stop fires at the
circuit price, and the order queues there). For upper circuits (target or
trailing stop fires but cannot sell), the position continues holding. The
63-day hard cap eventually forces an exit.

**Operational note:** names restricted to F&O-only (no circuit limits) would
eliminate this risk. That is listed as an open decision in STRATEGY_FULL.md
§17 but gated on PIT F&O membership data.

### Suspension or delisting

If a held name is suspended (NSE action) or delisted, yfinance will stop
returning OHLCV rows for it. The incremental updater (`ohlcv_incremental.py`)
will not find a last-bar for it, and the signal tracker will age it silently
until the 63-day hard cap fires. No stop will fire (no close data). The paper
ledger will last-value-carry the position.

**Mitigation:** the universe definition already reduces this risk — large+mid
by trailing ADV, solvent low-debt. Names approaching suspension typically
violate the solvency filter before they are suspended. But the tracking gap
is real and there is no emergency-exit mechanism currently.

### VEDL-class demerger quarantine (W-01, Phase 1 fix)

Corporate demergers are not splits. When a company spins off a subsidiary
(e.g. VEDL Vedanta, 2026-04-29: -64.9% on the ex-date), yfinance
back-adjusts the raw close as if it were a stock split. This fabricates a
soaring `sma200_slope_63` — VEDL's slope inflated from +2.16 to +24.94,
giving it rank 3/495. The only reason it did not enter the paper book was
a coincidental solvency fail (D/E = 2.22).

**Fix (commit b653f52):** `long_horizon_cron.py` now detects any name with a
raw close drop >= 50% in a single session within the last 263 bars
(`_demerger_suspect_names`) and quarantines it from new entries. Held
positions are not affected (if a demerger occurs on a held name, the stop
logic fires normally on the post-event price). Regression tests:
`tests/test_lh_demerger_guard.py` (17 tests; VEDL confirmed flagged, RELIANCE
confirmed clean).

**The root fix (not yet shipped):** `clean_ohlcv_for_features` should
distinguish confirmed splits (yfinance `Ticker.actions` returns a split
ratio) from demerger-class events and NOT back-adjust the latter. This changes
feature values and requires a golden-master regeneration + cloud re-derivation.
Deferred to the cloud backtest gate.

### 0-share guard (W-18, Phase 1 fix)

If a name's closing price exceeds 15% of the paper book (currently ₹10L → any
name above ~₹1.5L per share), the risk-budget sizing rounds down to 0 shares.
Previously this published a non-actionable 0-share BUY card and wasted a
portfolio slot. MRF (₹1,29,550 as of 2026-06-26) is the near-term trigger.

**Fix (commit b653f52):** entry loop skips any name where `_size_position`
returns fewer than 1 share; the slot stays free for the next-ranked name.

### Financials sector silently excluded (W-04, open)

The D/E solvency filter (`0 <= D/E < 1.5`) drops 78-79 large+mid names per
scan. 62 of those are banks and NBFCs (HDFCBANK, ICICIBANK, SBIN,
BAJFINANCE) whose D/E is `NaN` in `fundamentals_pit_screener.pkl` because
Screener derives D/E from Borrowings/net-worth, which is undefined for
deposit-taking institutions.

This is not a Kite wiring bug — live and backtest behave identically (both
drop the same names). It IS a universe-spec gap: the stated spec says "solvent
low-debt" but the practical effect is "solvent low-debt AND not a bank or
lending NBFC". Insurers and AMCs that have clean D/E (e.g. exchanges, asset
managers) do survive the filter.

**Status (W-04, open):** the Phase-1 fix added observability (cron logs
`solvency_dropped_financials` in `cron_health`). The policy decision —
special-case banking D/E vs keep dropping banks — is deferred. Until it is
resolved, never claim the strategy has "exposure to Nifty Bank" or uses a
purely leverage-based solvency screen.

### AUD-007 — 48 invisible current index members (W-02, open)

The scanner downloads from `config.NIFTY_500` (the 2025-07-20 official list).
Current index members that joined after that snapshot (ATHERENERG, GROWW-class
new entrants — 48 names as of 2026-06-27) are **never downloaded and are
invisible to the scan**.

These 48 are exactly the class of newly-promoted, high-momentum names the
slope signal would target. The universe-union fix (set download universe =
current_members ∪ config.NIFTY_500) is not applied yet because 0 of the 48
have coverage in `fundamentals_pit_screener.pkl` — they would all be dropped
by the solvency filter anyway. The fix ships with the Task-8 data work.

Divergence is recorded in `cron_health` every run (`membership_divergence`,
`membership_current_count`) and printed as `AUD-007: 48 current index
member(s) absent from config.NIFTY_500 (invisible to the live scan)`.

---

## 5. Kite API key hygiene

The Kite API key was rotated 2026-06-05 after the old value was found
committed in `vercel.json` + git history. Hard rules:

- **Never hardcode** the Kite API key. Pull from
  `process.env.REACT_APP_KITE_API_KEY` in the frontend and from the
  `KITE_API_KEY` env var on the backend.
- Set the key as a **Vercel dashboard Environment Variable** (Production +
  Preview), NOT in `vercel.json` (which is committed to a public repo).
- For local dev, use `frontend/.env.local` (gitignored).
- `kiteJson` / `kitePost` wrappers in `services/api.js` must always be used
  for Kite endpoint calls — bypassing them disables session-expired detection.
- **Rotating the API key** (generating a new Kite app) requires updating the
  Zerodha developer console redirect URL, which requires the new app's
  subscription and one-time user consent. Rotating only the `KITE_API_SECRET`
  (same app, same key) is simpler if the key value itself has not leaked.

---

## 6. Quick ops reference

| Task | Location | Notes |
|---|---|---|
| Connect Kite for a user | `/settings` or Header | OAuth round-trip; sets `KiteSession` DB row |
| Check session status | `/api/kite/session/status` | Returns `connected`, `kite_user_id` |
| Automated session refresh | `dashboard/backend/refresh_kite_session.py` | **No cron yet** — W-16 open; run manually or schedule via new GH Actions workflow |
| Place an order | OrderPad -> `useOrderPlacement` | POST `/api/kite/orders/regular`; also writes to `nq_orders` table |
| Detect session expiry | `services/api.js::detectKiteSessionExpired` | Fires `kite-session-expired` window event on stale-token response |
| View today's orders | `/orders` (OrdersV2) | `useKiteOrders` hook; requires live Kite session |
| Real-time quotes | `/api/yahoo-finance/prices` (primary) / Kite `/quote` (Paid tier, owner's key) | Kite quotes require an active session; Yahoo Finance is the fallback |

---

## 7. What is deliberately NOT wired to Kite

Per the product decision (CLAUDE.md):

- **External Kite trades** (orders placed directly on Zerodha outside NiftyQuant)
  are invisible to Journal and Accounting — only NiftyQuant Buy/Sell button orders
  are tracked in `nq_orders`.
- **The signal scanner** — yfinance only. No Kite dependency on the price path.
- **The backtest** — no Kite dependency. Backtest fill model uses the tiered
  slippage + cost model above, not live order routing.
- **The AI sector-regime shadow analyst** — runs on shadow only, reads no Kite data.

---

*Skill grounded in: CLAUDE.md (Kite section), long_horizon/audit/wiring_report.md,
long_horizon/audit/wiring_issues.md, long_horizon/audit/PHASE1_FIXES.md,
long_horizon/STRATEGY_FULL.md §5/§7/§10.3, models/long_horizon/config.json,
src/runners/long_horizon_cron.py (grep: zero kite refs), .github/workflows/cron-scanner.yml,
dashboard/backend/refresh_kite_session.py. Last verified: 2026-06-27 Phase-1 audit.*
