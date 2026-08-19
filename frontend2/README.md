# frontend2 — Nifty Satvik Terminal (parallel frontend)

A **buildless** (no npm, no toolchain) parallel rebuild of the dashboard as a Webull-style
dark trading terminal. It is deliberately separate from the current live frontend so nothing
existing is distorted; the plan is to run it in parallel, verify, then cut over.

## What it is
Plain HTML/CSS/JS — `index.html` + `styles.css` + `app.js` + `config.js`. No framework, no build.
Open the file (via a static server) and it runs.

- **Candlestick chart** (weekly) with MA10/20/44 overlays, a volume pane, and a toggleable
  RSI(14, 75/35 bands) / MACD(12,26,9) sub-pane, a crosshair with an OHLC/indicator readout,
  and dashed entry / stop / target price lines.
- **Watchlist** (fresh buys + holdings), **order / position** panel, **take-profit** tier,
  **portfolio equity** spark, and a dense **positions** table. Click any ticker (watchlist or
  positions) to switch the chart + panels.

## Data — it wires to the existing backend
`app.js` fetches the live API and **falls back to bundled sample data** on any failure, so it
always renders. The top-right badge shows **LIVE** vs **SAMPLE**. Endpoints used (all `/api`,
same `nq_access` cookie):

| Feature | Endpoint |
|---|---|
| Candles (OHLCV) | `GET /api/yahoo/historical/{sym}?interval=1wk&period=2y&exchange=NSE` (array of `[date,o,h,l,c,v]`) |
| Fresh buys + regime + portfolio | `GET /api/signals` |
| Holdings + P&L + sell_guidance | `GET /api/positions/nq` |
| Take-profit / trim tier | `GET /api/signals/sell-guidance` |
| Portfolio equity curve | `GET /api/portfolio/nav-history?days=365` (`{history:[{date,value}]}`) |
| Index strip | `GET /api/yahoo/index-sparklines` |

MA / RSI / MACD are computed **client-side** from the candles — no new backend needed.

## Run locally
```bash
cd frontend2
python -m http.server 8778
# open http://127.0.0.1:8778/
```
With no backend reachable it shows the **SAMPLE** badge and bundled data — correct, not an error.

## Point it at the backend (`config.js`)
- **Same origin** (backend serves this folder): keep `apiBase: "/api"` — cookies just work.
- **Separate static deploy** (e.g. Vercel): set `apiBase` to the backend origin, e.g.
  `"https://nifty-satvik-api.fly.dev/api"`, and add that frontend origin to the backend's
  CORS allow-list **with credentials** so the `nq_access` cookie is sent.

## Deploy options
1. **Static on Vercel** — deploy this folder as a static project (no build command). Set
   `apiBase` to the backend origin + CORS.
2. **Served by the FastAPI backend** — mount `frontend2/` as static files at a route such as
   `/terminal`; same-origin means cookies and `/api` work with zero CORS config.

## Cutover plan
1. Deploy in parallel at a distinct route (e.g. `/terminal`) — the current app is untouched.
2. Verify LIVE data side-by-side with the existing dashboard.
3. Flip the default/nav link to the terminal; keep the old pages as fallback.
4. Retire the old pages once the terminal is trusted.
