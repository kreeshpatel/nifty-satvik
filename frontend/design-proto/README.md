# Research Dashboard — design prototype

A self-contained, clickable HTML prototype of the enriched trading dashboard and the
new **Research** surface, built in the app's real v3 design tokens (`frontend/src/styles/tokens.css`:
navy-glass ground, blue→violet brand, DM Sans, semantic bull/bear).

This is a **design reference only** — not wired into the React app and not shipped to users.
It exists to lock the visual direction and interaction model before implementation.

## Open it

It is fully static (single file, no build). Open directly in a browser, or serve the folder:

```
python -m http.server 4599 --directory frontend/design-proto
# then visit http://localhost:4599/nq-research-dashboard.html
```

## What it demonstrates

- **Dense terminal layout** — persistent left watchlist rail, main column, right rail.
- **Live scrolling ticker** (25 indices + signal stocks) with a 2-second price simulation;
  research picks stay fixed (they are model levels, not live quotes).
- **Research tab** — analyst-style model calls, graded, with a Pick of the Week and commentary.
- **Stock detail page** — candlestick chart (canvas mock; production uses TradingView
  `lightweight-charts` fed by our own Kite OHLCV), timeframes, market-depth modal, order pad.
- **Per-user watchlist** — search + add/remove, hover actions (Buy / Sell / Depth / Chart / Delete),
  inline depth. Prototype persists to `localStorage`; production is a `user_watchlist` table
  (`user_id, symbol, added_at`) behind `GET/POST/DELETE /api/watchlist`, scoped by auth.
- **Portfolio** (Overview + Asset allocation → Equity holdings) and **Positions** (open model trades).
- Per-symbol logo badges driven by one central colour function.

## Not in scope here

Market/stock data stays centralised on the owner Kite app token (cached); only account-style
data (watchlist, holdings) is per-user. Broker-only surfaces (F&O, MTF, Fixed Income) are shown
as dimmed labels — the strategy is long-only delivery momentum.
