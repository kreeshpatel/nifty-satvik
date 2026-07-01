# Local UI demo / audit harness (dev-only)

Run the whole dashboard locally with **test data in every field** — no backend, no Kite, no login —
so the UI can be screenshotted and audited. Used with the preview/screenshot tooling.

## Run it

```bash
# 1. start the mock API (serves fixtures for every /api/* the pages read)
python frontend/dev/mock-api.py                 # listens on :8899

# 2. one-time: create frontend/.env.development.local  (gitignored — never commit)
#    REACT_APP_PREVIEW_NO_AUTH=true              # AuthContext preview bypass (dev-only; throws in prod)
#    LOCAL_PROXY_TARGET=http://localhost:8899    # setupProxy.js sends /api/* to the mock

# 3. start the frontend
npm --prefix frontend start                     # http://localhost:3000
```

Open http://localhost:3000/portfolio → click **Paper** → the tabs (Overview / Positions / Closed
Trades / Activity) render fully populated. Every route works (the mock reports Kite connected + a
stub user). The only console noise is "Failed to get WebSocket ticket" (no local WS — harmless).

## What it proves
`REACT_APP_PREVIEW_NO_AUTH` (in `AuthContext.jsx`) seeds a stub user so protected routes render; the
mock API fills every field. Verify wiring by reading rendered values (e.g. via the preview tool's
`eval`: `document.querySelectorAll('.pv3-ptbl .pv3-td')`) and comparing to the fixtures in
`mock-api.py`. Edit the fixtures there to test edge values (huge numbers, negatives, empty lists).

## Fixtures → pages (see FRONTEND_DEPENDENCY_MAP.md for the full wiring)
`/api/positions` → Positions tab · `/api/trades` → Closed Trades + Analytics · `/api/overview` →
Overview/KPIs · `/api/signals` → Signals · `/api/kite/*` → Live/Orders/Funds · `/api/nq-orders` →
Journal/Accounting · `/api/backtest/*` → Track/Backtest.
