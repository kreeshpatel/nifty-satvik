# Frontend Dependency & Wiring Map — niftyquant dashboard

> The frontend's **data wiring**: which page reads which React-Query hook, which hook calls which
> `services/api.js` function → `/api/*` endpoint, which backend router serves it, and which
> `results/*` file (written by the nifty-satvik paper cron) or DB table / Kite API it ultimately reads.
> Import-graph tools (trailmark) can't derive the runtime API/data flow, so this is authored from the
> code and kept current by hand. Engine-side map: [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) (the `nq/` graph).
>
> Layers: `frontend/src/pages/*` → `frontend/src/hooks/queries/*` → `frontend/src/services/api.js`
> → `dashboard/backend/routers/*` → `dashboard/backend/github_data.py` → `results/*` (via GitHub API) /
> Supabase / Kite. `run_paper_cron.py` (engine) writes the `results/*` files the read path consumes.

## 1. Paper data flow (Portfolio / Dashboard)

```mermaid
flowchart LR
  subgraph FE["Frontend"]
    PV["PortfolioV3<br/>(Overview/Positions/Closed/Activity)"]
    DV["DashboardV3"]
    PV --> hOv["useOverview"]
    PV --> hPos["usePaperPositions"]
    PV --> hTr["useTrades"]
    PV --> hPap["usePaperHistory"]
    PV --> hKH["useKiteHoldings (Live)"]
    DV --> hOv
  end
  subgraph API["services/api.js  →  /api/*"]
    hOv --> eOv["/api/overview"]
    hPos --> ePos["/api/positions"]
    hTr --> eTr["/api/trades + /api/trades/stats"]
    hPap --> ePap["/api/portfolio/paper-history"]
    hKH --> eKite["/api/kite/holdings"]
  end
  subgraph BE["dashboard/backend/routers"]
    eOv --> rOv["overview.py"]
    ePos --> rPos["positions.py"]
    eTr --> rTr["trades.py"]
    ePap --> rPort["portfolio.py"]
    eKite --> rKite["kite.py"]
  end
  subgraph DATA["results/* (GitHub API via github_data.py)  ·  DB  ·  Kite"]
    rOv --> fPP["paper_portfolio.json"]
    rOv --> fPH["portfolio_history.csv"]
    rOv --> fPT["paper_trades.json"]
    rOv --> fPL["paper_ledger_history.csv"]
    rPos --> fPP
    rTr --> fPT
    rPort --> dbNav[("nav_history / ledger")]
    rKite --> kite(["Zerodha Kite API"])
  end
  CRON["run_paper_cron.py (engine cron)"] -.writes.-> fPP & fPH & fPT & fPL
```

## 2. Signals data flow

```mermaid
flowchart LR
  SV["SignalsV3"] --> hSig["useSignals"] & hSigH["useSignalHistory"] & hNQ["useNQPositions"]
  hSig --> eSig["/api/signals"]
  hSigH --> eSigH["/api/signals/history"]
  hNQ --> eNQ["/api/positions/nq"]
  eSig --> rSig["signals.py"]
  eSigH --> rSig
  eNQ --> rPos2["positions.py + services/nq_positions.py"]
  rSig --> fST["signals_today.json"]
  rSig --> fMdl["models/long_horizon/config.json"]
  rSig --> fSH["signals_history.json (degrades ∅ — not emitted)"]
  rPos2 --> dbOrders[("nq_orders (Supabase)")]
  rPos2 --> kite2(["Kite holdings"])
```

## 3. Hook → endpoint → router → source (lookup table)

| Hook (`hooks/queries/`) | `api.js` fn | Endpoint | Router | Reads |
|---|---|---|---|---|
| `useOverview` | `fetchOverview` | `GET /api/overview` | `overview.py` | paper_portfolio.json, portfolio_history.csv, paper_trades.json, paper_ledger_history.csv |
| `usePaperPositions` | `fetchPositions` | `GET /api/positions` | `positions.py` | paper_portfolio.json |
| `useNQPositions` | `fetchNQPositions` | `GET /api/positions/nq` | `positions.py` + `services/nq_positions.py` | signals_history.json (∅) + `nq_orders` DB + Kite |
| `useTrades` | `fetchTrades` | `GET /api/trades` | `trades.py` | paper_trades.json |
| `useTradeStats` | `fetchTradeStats` | `GET /api/trades/stats` | `trades.py` | paper_trades.json |
| `useSignals` | `fetchSignals` | `GET /api/signals` | `signals.py` | signals_today.json, paper_portfolio.json, models/long_horizon/config.json |
| `useSignalHistory` | `fetchSignalHistory` | `GET /api/signals/history` | `signals.py` | signals_today.json, signals_history.json (∅), signal_analytics.json (∅) |
| `useNavHistory` | `fetchNavHistory` | `GET /api/portfolio/nav-history` | `portfolio.py` | `nav_history` DB (per-user) |
| `usePaperHistory` | `fetchPaperHistory` | `GET /api/portfolio/paper-history` | `portfolio.py` | paper_ledger_history.csv |
| `useKiteHoldings` / `useKiteMargins` / `useKiteState` | `kiteJson(...)` | `GET /api/kite/*` | `kite.py` | Zerodha Kite API (per-user session) |
| `useNQOrders` | `fetchNQOrders` | `GET /api/nq-orders` | `nq_orders.py` | `nq_orders` DB |
| `useOverview().metrics` (landing) | — | `GET /api/landing-stats` | `landing_stats.py` | trade_log.csv (∅), production_strategy.json (∅), portfolio_history.csv |
| `useBacktest*` | `fetchBacktest*` | `GET /api/backtest/*` | `backtest.py` | signals_history.json (∅), backtest_data.json (∅) |

`∅` = nifty-satvik's cron does **not** emit this file; the router degrades to an empty state (`or []`/`{}`).

## 4. Cross-cutting infrastructure
- **`services/api.js`** — all fetches go through `authJson`/`authPost` (adds JWT, auto-refreshes on 401 via
  `/api/auth/refresh`) or `kiteJson`/`kitePost` (Kite-session-expiry detection). Never bypass these wrappers.
- **`context/AuthContext.jsx`** — holds `user`; `App.js::ProtectedAppLayout` redirects to `/login` when `!user`.
- **`context/KiteContext`** — Kite connection state (`connected`), provided by `ProtectedAppLayout`.
- **React Query** (`lib/queryClient.js`) — caches responses (15 min trades, 30 s positions); NOT persisted to
  localStorage, so a full reload refetches.
- **`github_data.py`** — the read layer: results/* are GitHub-first (30 s cache, `GITHUB_TOKEN`) from
  `kreeshpatel/nifty-satvik@main`, then local. models/* are local-first. **Requires `GITHUB_TOKEN`** on Fly.
- **Deploy:** frontend → Vercel (Root Directory `frontend`); backend → Fly (`nifty-satvik-api`, builds
  `deploy/Dockerfile`). See [STAGE_E_DASHBOARD_DEPLOY.md](STAGE_E_DASHBOARD_DEPLOY.md).

## 5. Maintenance
Update this map when you: add/rename a query hook or `api.js` fetch fn, add/rename an `/api/*` endpoint or
router, or change which `results/*` file a router reads. It is the frontend counterpart to
[DEPENDENCY_MAP.md](DEPENDENCY_MAP.md); keep both current (owner memory: regenerate the engine dep-map after
`nq/**` changes; update this by hand after frontend/backend wiring changes).
