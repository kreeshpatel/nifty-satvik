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

### A. Data-contract alignment  — **I DO (code)**  — the real integration work
The Fly backend (`niftyquant/dashboard/backend/github_data.py`) reads `results/*.json` from
`kreeshpatel/niftyquant` and its routers (`signals`, `positions`, `overview`, `trades`,
`landing_stats`) expect that repo's OLD shapes. nifty-satvik's cron emits DIFFERENT (leaner) shapes.
Fix = make the two match:
1. Re-point `github_data.py`: `kreeshpatel/niftyquant` → `kreeshpatel/nifty-satvik` (GITHUB_RAW + API).
2. Compare the OLD contract (niftyquant `results/signals_today.json`, `portfolio_history.csv`, paper
   files + what each router reads) to nifty-satvik's output, and **make nifty-satvik's cron emit the
   OLD shapes** (adapt `scripts/run_paper_cron.py` — cheaper + keeps the validated frontend/backend
   untouched) OR adapt the routers. Prefer adapting nifty-satvik's output.
3. Verify each dashboard page's data need is satisfied by a nifty-satvik file.

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
