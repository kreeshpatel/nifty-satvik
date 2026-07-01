# Stage-E Dashboard Deploy — Fly.io backend + Vercel frontend, re-pointed at nifty-satvik

> Owner chose "stand up the full dashboard" (2026-07-01). This finishes the carried
> `niftyquant/MIGRATION_RENDER_TO_SUPABASE.md` runbook, re-pointed from the old system onto the clean
> nifty-satvik engine. **Two repos stay separate:** `nifty-satvik` = the quant/paper ENGINE (commits
> `results/*.json`); `niftyquant` = the PRODUCT (React frontend + FastAPI backend). Render is dead;
> replaced by Fly.io (backend) + Supabase (DB) + GitHub Actions (crons) + Vercel (frontend).

## Architecture (target)
```
nifty-satvik (engine)          niftyquant (product)                       user-facing
  cron-scanner.yml  ──push──▶  FastAPI on Fly.io ──reads results/──┐
  results/*.json (paper book)    (niftyquant-api.fly.dev)           │
                                 Supabase Postgres (auth/kite/nav) ◀┘──▶ React on Vercel
                                 (slyxryfbhvjgvvtffjjb)                   (niftyquant.vercel.app)
```
Frontend `vercel.json` ALREADY points `/api/*` + WS at `niftyquant-api.fly.dev` — so once the Fly
backend is up + re-pointed, the frontend works with no frontend changes.

## The 3 workstreams

### A. Data-contract alignment  — **DONE (code, 2026-07-01)**  — the real integration work
The Fly backend (`niftyquant/dashboard/backend/github_data.py`) reads `results/*.json` from
`kreeshpatel/niftyquant` and its routers (`signals`, `positions`, `overview`, `trades`,
`landing_stats`) expect that repo's OLD shapes. nifty-satvik's cron emitted DIFFERENT (leaner) shapes.
What was done:
1. **Re-pointed the backend** (in the niftyquant repo — separate push): `github_data.py` **and**
   `routers/signals.py` both carried hardcoded `kreeshpatel/niftyquant` GITHUB_RAW + API-contents
   URLs → both flipped to `kreeshpatel/nifty-satvik`. (The docs' `git clone niftyquant` lines stay —
   they point at the product repo, not the results data source.)
2. **Adapted nifty-satvik's output to the backend contract** (chose this over touching the validated
   routers). `PaperBook` now splits persistence: `paper_state.json` = the engine RESUME state
   (cash/peak/pending/positions/trades/equity_curve — internal shape), and `dashboard_files()` derives
   the backend-shaped exports:
   - `paper_portfolio.json` → `{cash, peak_value, total_value, total_trades, n_positions,
     positions:{tkr:{entry_price, shares, atr_stop, current_price, current_value, unrealised_pnl(_pct),
     entry_date, days_held, target}}}` (matches `overview._paper_payload` + `positions.py`).
   - `paper_trades.json` → each trade gets `net_pct`/`net_pnl`/`hold_days` aliases (overview KPIs + trades router).
   - `portfolio_history.csv` **and** `paper_ledger_history.csv` → `total_value` column (equity curve +
     the overview Sharpe/MDD read).
   - `signals_today.json` (written by `run_paper_cron`) → the backend envelope `{generated_at, signals:[…
     ticker/indicative_close/indicative_entry/stop/target/buy_window], regime, kill_state}`.
   `load()` has a one-time legacy-migration fallback (reads the pre-split internal `paper_portfolio.json`
   + siblings) so the LIVE book (10 positions, ₹941K NAV) carried forward without a reset; the committed
   `results/` were migrated in place. `paper_state.json` whitelisted in `.gitignore` so the cloud cron resumes.
3. **Coverage:** overview/positions/trades/signals/landing-stats satisfied. Files nifty-satvik does NOT
   emit — `signals_history.json`, `backtest_data.json`, `trade_log.csv`, `production_strategy.json`,
   `tearsheet.html` — all degrade gracefully (`or []`/`or {}`) to empty states, no crash.

### B. Fly.io backend deploy  — **YOU DO (account)**  + I prep the config
`fly.toml` + `deploy/Dockerfile` are staged in niftyquant. Steps (one-time):
```
curl -L https://fly.io/install.sh | sh   # install flyctl
fly auth login                            # YOUR Fly account
fly apps create niftyquant-api            # or `fly launch --no-deploy --copy-config`
fly secrets set \
  DATABASE_URL="postgresql://postgres.slyxryfbhvjgvvtffjjb:<DB-PASSWORD>@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres" \
  JWT_SECRET="$(openssl rand -hex 32)" \
  ENCRYPTION_KEY="$(openssl rand -hex 32)" \
  KITE_API_KEY="<zerodha app key>" KITE_API_SECRET="<zerodha app secret>" \
  GITHUB_TOKEN="<PAT with repo:read on nifty-satvik>" \
  CRON_SERVICE_TOKEN="$(openssl rand -hex 24)"
fly deploy                                # builds deploy/Dockerfile, boots on sin (Singapore)
```
Secret inventory (fly.toml header): `DATABASE_URL, JWT_SECRET, ENCRYPTION_KEY, KITE_API_KEY,
KITE_API_SECRET, GITHUB_TOKEN, CRON_SERVICE_TOKEN`. DB password: Supabase → Connect → **Session
pooler** (port 5432, NOT 6543). *(If you give me a Fly deploy token I can run `fly deploy`; auth +
secrets stay yours.)*

### C. Supabase  — **I DO (via MCP)**  — reuse project `slyxryfbhvjgvvtffjjb`
Do NOT create a new project. It's healthy + has the schema (users, kite_sessions, nav_history,
nq_orders, audit_logs, refresh_tokens + 1 user / real data). I verify the schema matches the backend's
`init_db()` and apply any missing migrations via the MCP. The backend's `init_db` also self-migrates on
boot against `DATABASE_URL`.

## Vercel  — mostly DONE
`vercel.json` already targets `niftyquant-api.fly.dev` (`/api/*` rewrite + `wss://` + CSP `connect-src`).
Remaining: confirm the Vercel project builds from the niftyquant repo + set any `REACT_APP_*` /
Supabase env in the Vercel dashboard. No Render references remain in config.

## Sequencing
1. **A (me):** re-point github_data + align nifty-satvik's cron output to the backend contract (code).
2. **C (me):** verify/apply Supabase migrations.
3. **B (you):** fly auth + secrets + `fly deploy` (or hand me a deploy token).
4. Smoke-test: `curl https://niftyquant-api.fly.dev/health`; load the Vercel site; confirm the paper
   NAV/positions/signals render from nifty-satvik's data.

## Deferred to Stage F (live) — NOT needed to monitor paper
Live Kite order placement (`routers/kite.py`, `nq_orders`), the kite-refresh cron
(`cron-kite-refresh.yml` — needs Zerodha TOTP secrets), and enforce-mode kill-switch. The paper
dashboard is read-only (auth + display); Kite trading is the live gate.
