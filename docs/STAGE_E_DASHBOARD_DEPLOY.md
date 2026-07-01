# Stage-E Dashboard Deploy — MONO-REPO (Fly.io backend + Vercel frontend, both from nifty-satvik)

> Owner chose "stand up the full dashboard" (2026-07-01), then **consolidated the product into a
> mono-repo** (2026-07-01): the niftyquant React frontend + FastAPI backend + Fly/deploy config were
> moved INTO `nifty-satvik`, so one repo holds the engine, the paper book, and the product. Deploy the
> backend (Fly) and the frontend (Vercel) both from `nifty-satvik`. Render is dead; replaced by Fly.io
> (backend) + Supabase (DB) + GitHub Actions (crons) + Vercel (frontend). The old `niftyquant` repo is
> retired for the product role (PR #194 there — the cross-repo re-point — is now superseded).

## Architecture (mono-repo)
```
nifty-satvik (ONE repo)
  nq/ scripts/ config.py            the quant engine + frozen cfg
  cron-scanner.yml ──push──▶ results/*.json      the paper book (daily cron commits state)
  dashboard/backend/  ──build──▶ FastAPI on Fly.io (niftyquant-api.fly.dev)
       └ reads results/* from GitHub (contents API, GITHUB_TOKEN) — the image is frozen, the cron
         pushes fresh results/ to the repo, the backend fetches the latest
  frontend/           ──build──▶ React on Vercel (Root Directory = frontend)
       └ vercel.json rewrites /api/* + wss → niftyquant-api.fly.dev (Fly app name unchanged)
  Supabase Postgres (auth/kite/nav)  project slyxryfbhvjgvvtffjjb
```

## What was done

### A. Data-contract alignment — **DONE (code)**
nifty-satvik's `PaperBook` emits exactly the shapes the backend routers read. Persistence is split:
`paper_state.json` = engine RESUME state (cash/peak/pending/positions/trades/equity_curve);
`dashboard_files()` derives the backend-contract exports:
- `paper_portfolio.json` → `{cash, peak_value, total_value, total_trades, n_positions,
  positions:{tkr:{entry_price, shares, atr_stop, current_price, current_value, unrealised_pnl(_pct),
  entry_date, days_held, target}}}` (overview + positions routers).
- `paper_trades.json` → each trade gets `net_pct`/`net_pnl`/`hold_days` aliases (overview KPIs + trades).
- `portfolio_history.csv` + `paper_ledger_history.csv` → `total_value` column.
- `signals_today.json` (from `run_paper_cron`) → envelope `{generated_at, signals[...], regime, kill_state}`.
`load()` has a one-time legacy migration; the live book (10 positions, ₹941K NAV) carried forward.
Files nifty-satvik does NOT emit (`signals_history.json`, `backtest_data.json`, `trade_log.csv`,
`production_strategy.json`, `tearsheet.html`) degrade gracefully to empty. Committed `39863ca` + `d8ddf4b`.

### A2. Mono-repo consolidation — **DONE (code)**
Moved `frontend/`, `dashboard/backend/`, `deploy/`, `fly.toml`, `.dockerignore`, `.mcp.json` into
nifty-satvik. Two boot-crash fixes were required for the backend to run against the clean engine:
1. `dashboard/backend/routers/backtest.py` did a module-level `from trading.signal_tracker import
   compute_signal_analytics` (a retired-v1 `src/` module absent from nifty-satvik) → **guarded** so it
   degrades to an empty-analytics stub instead of crashing uvicorn (that page reads `signals_history.json`,
   which the LH cron doesn't emit, so it's empty regardless).
2. `dashboard/backend/config.py` bootstraps by exec'ing the root `config.py`. nifty-satvik's lean root
   config supplies most names but NOT `INITIAL_CAPITAL`; the old all-or-nothing fallback only ran when the
   root import FAILED, so a *successful* lean import left `INITIAL_CAPITAL` undefined → `from config import
   INITIAL_CAPITAL` crashed at boot. Rewrote it to **always backfill** any missing router-required name.
Repo hygiene: `.gitignore` gains `node_modules/`, `frontend/{node_modules,build,.eslintcache}`,
`.pytest_cache/`, `dashboard/backend/.env`; `pyproject.toml` adds `--ignore=dashboard` so the engine's
`pytest -q` never collects the backend's fastapi/sqlalchemy tests; `.dockerignore` trims engine-only dirs.

### B. Fly.io backend deploy — **YOU DO (account)** — deploy from the nifty-satvik repo root
`fly.toml` (repo root) builds `deploy/Dockerfile` with context = repo root. One-time:
```
curl -L https://fly.io/install.sh | sh   # install flyctl
fly auth login                            # YOUR Fly account
fly apps create niftyquant-api            # keeps the app name (frontend vercel.json points here)
fly secrets set \
  DATABASE_URL="postgresql://postgres.slyxryfbhvjgvvtffjjb:<DB-PASSWORD>@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres" \
  JWT_SECRET="$(openssl rand -hex 32)" \
  ENCRYPTION_KEY="$(openssl rand -hex 32)" \
  KITE_API_KEY="<zerodha app key>" KITE_API_SECRET="<zerodha app secret>" \
  GITHUB_TOKEN="<PAT with contents:read on nifty-satvik>" \
  CRON_SERVICE_TOKEN="$(openssl rand -hex 24)"
fly deploy                                # from the nifty-satvik repo root; boots on sin (Singapore)
```
**`GITHUB_TOKEN` is functionally required, not optional:** `results/*` and `models/long_horizon/config.json`
are excluded from the image (`.dockerignore`) and served via the GitHub contents API on a PRIVATE repo —
without the token every results endpoint returns empty (boot still succeeds; the dashboard is DOA on data).
DB password: Supabase → Connect → **Session pooler** (port 5432, NOT 6543). *(A Fly deploy token lets me
run `fly deploy`; auth + secrets stay yours. No Fly MCP is connected to my session — CLI/token only.)*

Pre-deploy smoke (optional, catches the boot-crash class): `docker build -f deploy/Dockerfile -t nqapi .`
then `docker run --rm -e ... nqapi python -c "import main"` — must import with no ModuleNotFoundError.

### C. Supabase — **DONE (verified, no migrations)** — project `slyxryfbhvjgvvtffjjb`
All 8 backend tables exist and every column matches the SQLAlchemy models exactly (`users` incl. mfa_*,
`kite_sessions`, `nq_orders`, `nav_history`, `audit_logs`, `access_requests`, `refresh_tokens`,
`password_reset_tokens`). `init_db` create_all is a no-op. Security advisor: 8× "RLS enabled, no policy"
are INFO + EXPECTED (backend uses the privileged Postgres conn; PostgREST anon is denied — do NOT add
permissive policies). 1 WARN: `audit_logs_protect` mutable search_path → optional
`ALTER FUNCTION public.audit_logs_protect() SET search_path=''` (not applied; owner call).

## Vercel — **YOU DO (dashboard settings)**
`frontend/vercel.json` already targets `niftyquant-api.fly.dev` (`/api/*` rewrite + `wss://` + CSP) and
needs NO code change (the Fly app name is unchanged by the repo move). In the Vercel dashboard:
- **Settings → Git:** connect the project to **`kreeshpatel/nifty-satvik`**, Production Branch = `main`.
- **Settings → General → Root Directory = `frontend`** (build config lives under `frontend/`; also scopes
  the `ignoreCommand` git-diff to frontend/ so backend-only commits don't rebuild the site).
- **Env:** leave `REACT_APP_API_URL` UNSET for Production (same-origin + rewrite); set
  `REACT_APP_KITE_API_KEY` if Kite is used. `REACT_APP_WS_URL`/`GENERATE_SOURCEMAP` come from vercel.json.

## Sequencing
1. **A / A2 / C (me):** DONE — product consolidated into nifty-satvik, backend boots against the engine,
   Supabase verified.
2. **B (you):** `fly auth` + `fly secrets set` (incl. `GITHUB_TOKEN`) + `fly deploy` from the repo root.
3. **Vercel (you):** connect to nifty-satvik, Root Directory = frontend.
4. Smoke: `curl https://niftyquant-api.fly.dev/health`; load the Vercel site; confirm the paper
   NAV/positions/signals render.

## Deferred to Stage F (live) — NOT needed to monitor paper
Live Kite order placement (`routers/kite.py`, `nq_orders`), the kite-refresh cron
(`cron-kite-refresh.yml` — needs Zerodha TOTP secrets), and enforce-mode kill-switch. The paper
dashboard is read-only (auth + display); Kite trading is the live gate.
