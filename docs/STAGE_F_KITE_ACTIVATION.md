# Stage F — Kite (Zerodha KiteConnect) live activation

> How the live-trading integration is wired, what is code-complete, and the exact steps only the
> **owner** can perform to switch it on. NiftyQuant uses **KiteConnect directly** (not OpenAlgo).
> Hard rule (see the `kite-execution` skill §0): **Kite is never on the scanner/backtest price
> path** — it powers only the dashboard's holdings, margins, quotes, and order placement.

## 1. What is code-complete (no owner action)

| Layer | Wired |
|---|---|
| **Frontend** | `KiteContext` (in `App.js`) · `connectKite` OAuth redirect · `AuthCallback.jsx` (token exchange) · `useKiteHoldings`/`useKiteMargins`/`useKiteOrders`/`useOrderPlacement` · session-expiry detection (`kite-session-expired` event) |
| **Backend** | `routers/kite.py`: `/session/token`·`/session/status`·`/session/logout`, `/holdings`·`/positions`·`/margins`, `/orders` (GET/POST `{variety}`/PUT/DELETE), `/quote`·`/ltp`·`/historical`; per-user encrypted `KiteSession`; owner-token powers market data for all users; **`KITE_PROXY_URL` static-IP tunnel** on every Kite REST call |
| **Auto-refresh** | `refresh_kite_session.py` (TOTP web-login → token exchange → encrypted upsert → daily NAV snapshot). **Now proxy-aware** (2026-07-02): the login *and* the token exchange tunnel through `KITE_PROXY_URL`, so it works from the droplet, a GitHub-Actions runner, or the admin "Refresh Kite" button on Fly — not only from the whitelisted host. |
| **Refresh cron** | `.github/workflows/cron-kite-refresh.yml` (06:15 IST weekdays, proxy-tunneled, **inert until secrets are set**) — closes audit item **W-16**. |

## 2. Owner-gated steps (only you can do these)

These involve credentials, funded accounts, or infrastructure you own — Claude will not perform them.

1. **Kite Connect app** — in the [Zerodha developer console](https://developers.kite.trade), note the
   app's **API key + secret**, and set the **redirect URL** to `<origin>/auth/callback`
   (e.g. `https://niftyquant.vercel.app/auth/callback`).
2. **Static-IP droplet** — provision/keep the DigitalOcean droplet with the SEBI-whitelisted static
   IP, register that IP in the Zerodha console, and run the forward proxy (tinyproxy) it exposes as
   `KITE_PROXY_URL`. (Required because Zerodha enforces a static Indian IP for login + REST.)
3. **Secrets** — set these on **Fly** (`fly secrets set`) *and*, to enable the refresh cron, as
   **GitHub Actions repo secrets**. `ENCRYPTION_KEY` **must be byte-identical** everywhere or stored
   tokens become undecryptable:
   `KITE_API_KEY`, `KITE_API_SECRET`, `ZERODHA_USER_ID`, `ZERODHA_PASSWORD`, `ZERODHA_TOTP_SECRET`,
   `ENCRYPTION_KEY`, `DATABASE_URL`, `KITE_PROXY_URL`. Frontend build env: `REACT_APP_KITE_API_KEY`.
4. **First OAuth consent** — sign in once via `kite.zerodha.com/connect/login` (the "Connect Kite"
   button) to seed the first admin `KiteSession`. After that the cron keeps it fresh.
5. **First live order** — place one real order end-to-end on a funded account to confirm the path.
   No code can authorize this; it is yours to do.

## 3. Turn-on checklist

- [ ] Kite app redirect URL = `<origin>/auth/callback`; `REACT_APP_KITE_API_KEY` in the Vercel build env.
- [ ] Droplet up, static IP whitelisted in the Zerodha console, tinyproxy reachable as `KITE_PROXY_URL`.
- [ ] All secrets (§2.3) set on Fly **and** GitHub Actions; `ENCRYPTION_KEY` identical across both + droplet.
- [ ] `fly deploy` (picks up the proxy-aware `refresh_kite_session.py`).
- [ ] Owner clicks **Connect Kite** once → toast "Kite connected".
- [ ] Verify: `/orders`, `/funds`, Dashboard holdings populate; `POST /api/admin/refresh-kite` (admin
      "Refresh Kite" button) now succeeds from Fly via the proxy.
- [ ] Trigger `cron-kite-refresh.yml` once manually (Actions → Run workflow) to confirm the tunneled
      login works; then leave the 06:15 IST schedule on.
- [ ] Place one live order to close Stage F.

## 4. Audit items addressed here (code side)

- **W-16** (no auto-refresh cron) → `cron-kite-refresh.yml` added (proxy-tunneled; inert until secrets).
- **K-PROXY-REFRESH** (`refresh_kite_session.py` had no proxy → the Fly "Refresh Kite" button was
  IP-blocked) → login + token exchange now route through `KITE_PROXY_URL`.
- **K-ENV-EXAMPLE** (`.env.example` missing the Zerodha/proxy vars, stale Render note) → corrected.
- **K-AUTH-DEADHOOK** (`useKiteAuth.js` read a non-existent `logged_in` field) → reads `connected`
  (dead code, but correct if ever wired).

## 5. Still open (owner decisions, not code)

- **K-OWNER-SPOF** — market data for *all* users depends on the single owner Kite session. If it
  expires, everyone's quotes 503. Acceptable for a ~10-client private tool; a Yahoo-fallback for the
  quote endpoints is the mitigation if you want redundancy (the `yahoo_finance` router already exists).
- Whether to keep the droplet crontab **and** the GitHub cron, or retire the crontab now that the
  repo-tracked cron exists (the GH cron is enforced/visible; the crontab is hand-provisioned).

*Grounded in the 2026-07-02 Kite wiring scan + the `kite-execution` skill. Prohibited actions
(placing trades, entering credentials, setting secrets, standing up the droplet) remain the owner's.*
