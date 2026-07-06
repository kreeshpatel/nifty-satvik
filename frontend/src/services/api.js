// API Service Layer - Nifty Satvik
// Connects Frontend to FastAPI Backend via Authorization: Bearer JWT.
// Migrated from HttpOnly cookies → bearer tokens on 2026-05-26 because
// cookie-based auth was unreliable across mobile Safari, Chrome incognito,
// and Vercel-proxy edge cases. See lib/tokens.js for storage.

import { getAccessToken, getRefreshToken, setTokens } from '@/lib/tokens';

// API base: empty in production (same-origin via Vercel proxy to Render).
// In local dev, set REACT_APP_API_URL=http://localhost:8000 in .env.local.
const API = process.env.REACT_APP_API_URL ?? '';

// WebSocket connects directly to Render (Vercel doesn't proxy WebSocket).
// In local dev, derived from REACT_APP_API_URL automatically.
const WS_URL = process.env.REACT_APP_WS_URL
  || (API ? API.replace(/^http/, 'ws') : '');

// ── Authenticated fetch helper ──────────────────────
//
// Attaches `Authorization: Bearer <access_token>` from localStorage on every
// request. `credentials: 'include'` is retained for the backward-compat
// window (~7 days) so users still mid-migration with valid cookies don't
// get bounced — backend's get_current_user accepts either header or cookie
// during that window. Once the cookie fallback is removed in a follow-up,
// `credentials: 'include'` can be dropped from this file too.

const authFetch = (url, options = {}) => {
  const token = getAccessToken();
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return fetch(url, {
    ...options,
    credentials: 'include',
    headers,
  });
};

// Read response as text first then parse, avoids "body stream already read"
// errors. Always returns a parsed body or {} — never throws on parse failure.
// HTTP status is the caller's responsibility (see authJson / authPost).
const safeJson = async (res) => {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    return {};
  }
};

/**
 * ApiError — thrown by authJson/authPost on non-2xx HTTP status. Preserves
 * the parsed response body and HTTP status so consumers (toast handlers,
 * error UI) can read backend's `detail` field for a useful message.
 *
 * Pre-2026-04-29 the request layer silently returned the error body as if it
 * were a success response. That hid every Kite/auth/proxy failure behind a
 * react-query "success with empty data" — which surfaced as widespread
 * `Total ₹0` and "not refreshing" symptoms across Funds, Portfolio, and
 * Dashboard. Throwing on non-2xx makes react-query's isError fire so
 * consumers render real error states.
 */
export class ApiError extends Error {
  constructor(message, { status, body, url }) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
    this.url = url;
  }
}

const buildApiError = (res, body, url) => {
  const message =
    body?.detail ||
    body?.error ||
    body?.message ||
    `HTTP ${res.status} ${res.statusText || ''}`.trim();
  return new ApiError(message, { status: res.status, body, url });
};

// ── Reactive 401 → refresh + retry ───────────────────
//
// Access tokens expire after 4 hours (auth.py:ACCESS_TOKEN_EXPIRE_MINUTES).
// AuthContext runs a 3.5h proactive refresh, but if a request fires after
// expiry — or the tab was backgrounded long enough that the interval
// drifted — the request 401s and the user sees "Not authenticated" banners
// with no auto-recovery until they manually log out + back in.
//
// This wrapper transparently calls /api/auth/refresh on a 401 and retries
// the original request once. Single-flight: if many parallel requests all
// 401 simultaneously, only one refresh fires; the rest wait on the same
// promise. The refresh response carries new access + refresh tokens in
// JSON — we stash both via lib/tokens.setTokens so the retry picks up the
// new access token.

let _refreshInFlight = null;

const _attemptRefresh = () => {
  if (_refreshInFlight) return _refreshInFlight;
  const refreshToken = getRefreshToken();
  _refreshInFlight = fetch(`${API}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',  // legacy cookie fallback during compat window
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
    .then(async (r) => {
      if (!r.ok) return false;
      try {
        const data = await r.json();
        if (data?.access_token) {
          setTokens({
            access_token: data.access_token,
            refresh_token: data.refresh_token,
          });
          return true;
        }
      } catch {}
      return false;
    })
    .catch(() => false)
    .finally(() => {
      // Reset on next tick so consecutive 401s after a settled refresh
      // don't dogpile on a stale stored promise.
      setTimeout(() => { _refreshInFlight = null; }, 0);
    });
  return _refreshInFlight;
};

// Skip the refresh dance for endpoints that ARE the auth flow itself —
// otherwise a 401 from /auth/me triggers a refresh that 401s, ad infinitum.
const _isAuthEndpoint = (url) => /\/api\/auth\/(login|refresh|logout|me)\b/.test(url);

// Auth-failure policy:
//   - On a non-auth 401: try refresh, retry once.
//   - If refresh succeeds: invisible to the caller, request flows.
//   - If refresh fails: throw the original 401 as ApiError. The user-action-
//     triggered re-fetch (or AuthContext's tab-focus /auth/me check) will
//     surface a genuinely-dead session cleanly.
//
// History note: we tried twice to auto-dispatch a session-expired event on
// this path. Both times it tripped on the "fresh login, dashboard fans out
// 5+ queries, one of them 401s for a few hundred ms while the cookie jar
// settles" race, immediately kicking the user back to /login within ~500ms
// of a successful login — including in incognito where the state is
// guaranteed clean. The grace period is set by the user opening /login
// again. Don't reintroduce this without a per-request "settled-after-login"
// grace window.

const authJson = async (url, options = {}, _retried = false) => {
  const res = await authFetch(url, options);
  if (res.status === 401 && !_retried && !_isAuthEndpoint(url)) {
    const ok = await _attemptRefresh();
    if (ok) return authJson(url, options, true);
    // Refresh failed too — fall through, throw as normal ApiError.
  }
  const body = await safeJson(res);
  if (!res.ok) throw buildApiError(res, body, url);
  return body;
};

const authPost = async (url, body, _retried = false) => {
  const res = await authFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (res.status === 401 && !_retried && !_isAuthEndpoint(url)) {
    const ok = await _attemptRefresh();
    if (ok) return authPost(url, body, true);
  }
  const responseBody = await safeJson(res);
  if (!res.ok) throw buildApiError(res, responseBody, url);
  return responseBody;
};

// ========================================
// Auth APIs
// ========================================

export const authLogin = (email, password) =>
  authPost(`${API}/api/auth/login`, { email, password });

// Logout posts the refresh token in the body so the backend can revoke its
// row in the refresh_tokens table. AuthContext.logout() is responsible for
// clearing localStorage tokens — DO NOT call clearTokens() here, since the
// authPost helper itself relies on the access token for the request. Order:
// AuthContext.logout posts → backend revokes → AuthContext clears local.
export const authLogout = () =>
  authPost(`${API}/api/auth/logout`, { refresh_token: getRefreshToken() });

// ── MFA (TOTP) APIs ──
// Routed through authJson/authPost so the Bearer token is attached and the
// 401→refresh→retry path works. Previously SettingsV2's MfaPanel called these
// with raw fetch() + credentials:include only, which silently broke MFA
// management once auth migrated cookie→bearer (the cookie compat window closed).
export const fetchMfaStatus = () =>
  authJson(`${API}/api/auth/mfa/status`);

export const mfaSetup = () =>
  authPost(`${API}/api/auth/mfa/setup`, {});

export const mfaVerify = (code) =>
  authPost(`${API}/api/auth/mfa/verify`, { code });

export const mfaDisable = (password) =>
  authPost(`${API}/api/auth/mfa/disable`, { password });

export const authMe = () =>
  authJson(`${API}/api/auth/me`);

// authRefresh is rarely called directly — most refresh goes through the
// transparent _attemptRefresh in the 401 retry path. Kept exported in case
// a caller (e.g. AuthContext's 3.5h proactive tick) wants explicit control.
export const authRefresh = async () => {
  const refreshToken = getRefreshToken();
  const res = await fetch(`${API}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const body = await safeJson(res);
  if (res.ok && body?.access_token) {
    setTokens({
      access_token: body.access_token,
      refresh_token: body.refresh_token,
    });
  }
  return body;
};

// ========================================
// Dashboard APIs
// ========================================

export const fetchOverview = () =>
  authJson(`${API}/api/overview`);

export const fetchPositions = () =>
  authJson(`${API}/api/positions`);

// NQ-tracked positions: signals the user actually bought, joined with
// signal context (entry/stop/target/days) and live Kite price. Powers
// PortfolioV2's "Nifty Satvik Positions" section and SignalsV2 "Held"
// tier. Returns { positions, count, kite_connected, updated_at }.
export const fetchNQPositions = () =>
  authJson(`${API}/api/positions/nq`);

// Kite holdings minus NQ-attributed qty — drives PortfolioV2's
// "Other Kite Holdings" section. Same-ticker overlap is handled by
// strict NQ-recorded qty subtraction on the backend.
export const fetchExternalHoldings = () =>
  authJson(`${API}/api/positions/external`);

// Active sell-now recommendations for held positions (target / stop /
// time triggered). Convenience filter over /positions/nq used by the
// SignalsV2 page for the urgency banner.
export const fetchSellGuidance = () =>
  authJson(`${API}/api/signals/sell-guidance`);

// Today's watchlist — borderline candidates (conf 0.75-0.92) the model
// surfaced but didn't clear the entry gate. Used by the SignalsV2
// "Watchlist" tier so users see what the system is monitoring.
export const fetchWatchlist = (model = 'momentum') =>
  authJson(`${API}/api/signals/watchlist?model=${model}`);

// Drift reconciliation: synthesize a SELL nq_order for a position the
// user closed externally on Kite (qty in NQ records exceeds Kite truth).
// Posts to a dedicated endpoint that creates the row already-COMPLETE,
// so FIFO matching reflects the realised P&L immediately.
export const reconcileDrift = ({ signal_id, qty, fill_price, notes }) =>
  authPost(`${API}/api/nq-orders/reconcile`, { signal_id, qty, fill_price, notes });

// Per-user NAV time series for the Equity Curve. Rows are written
// opportunistically by /api/positions/nq (every dashboard load), so
// history starts on the day this shipped and grows organically. No
// backfill — early days will be sparse.
export const fetchNavHistory = (days = 365) =>
  authJson(`${API}/api/portfolio/nav-history?days=${days}`);

// Paper-broker equity curve (the realistic ₹10L ledger written daily by
// src/trading/paper_broker.py). Distinct from nav-history (live Kite NAV)
// and from /overview's equity_curve (the all-signals kill curve). The
// Paper toggle on the Portfolio page reads THIS so it doesn't fall through
// to the live account's NAV.
export const fetchPaperHistory = (days = 365) =>
  authJson(`${API}/api/portfolio/paper-history?days=${days}`);

export const fetchSignals = (model = 'momentum') =>
  authJson(`${API}/api/signals?model=${model}`);

export const runSignalScan = () =>
  // authPost gives the 401→refresh→retry path + a real ApiError(detail) on
  // failure (raw authFetch().then(r.json()) had neither — it silently returned
  // the error body as if it were a success). Keep the always-return-an-object
  // contract the admin scan mutation expects by mapping a thrown ApiError back
  // to { detail }.
  authPost(`${API}/api/signals/scan`, {})
    .catch((err) => ({ detail: err?.message || 'Scan failed — server may be sleeping. Try again.' }));

export const fetchRegime = () =>
  authJson(`${API}/api/signals/regime`);

// Signal history (today + still-in-play prior-day signals + analytics).
// Served by the AUTHENTICATED backend GET /api/signals/history. This replaces
// the retired Vercel `/fn/signals` serverless function, which read the repo's
// public GitHub raw URLs and broke when the repo went private (and exposed the
// paid signals unauthenticated). authJson attaches the bearer token + handles
// session-expiry detection.
export const fetchSignalHistory = async (model = 'momentum') => {
  try {
    const data = await authJson(`${API}/api/signals/history?model=${model}`);
    if (data) return data;
  } catch {}
  // Graceful empty (e.g. transient backend error) — consumers null-tolerate.
  return { today: [], history: [], analytics: {}, source: 'fallback' };
};

// ========================================
// Analytics APIs
// ========================================

export const fetchTrades = (params = {}) =>
  authJson(`${API}/api/trades?${new URLSearchParams(params)}`);

export const fetchTradeStats = () =>
  authJson(`${API}/api/trades/stats`);

// ========================================
// Backtest APIs
// ========================================

export const fetchBacktestHistory = () =>
  authJson(`${API}/api/backtest/history`);

export const runBacktest = async (params) =>
  authPost(`${API}/api/backtest/run`, params);

// Live signal track record (single consolidated blob)
export const fetchBacktestLive = () =>
  authJson(`${API}/api/backtest/live`);

// Historical backtest (single consolidated blob, regenerated monthly)
export const fetchBacktestHistorical = () =>
  authJson(`${API}/api/backtest/historical`);

// ========================================
// Kite (Zerodha) APIs
// ========================================

/**
 * detectKiteSessionExpired — sniffs Kite endpoint responses for the daily
 * 6 AM IST session-expired pattern and dispatches a global event so the
 * KiteContext provider can flip `connected` back to false and toast a
 * "reconnect" CTA. Returns the response unchanged so callers don't need
 * to know this exists.
 *
 * Only fires on TRUE session expiry — Kite emits `error_type: "TokenException"`
 * for these, which our backend's _extract_kite_error wraps into the detail
 * string as "<msg> (TokenException)". That's the canonical signal.
 *
 * Older heuristic patterns kept as a fallback for legacy error shapes
 * (raw Kite errors from before the backend's error-extractor) but only
 * applied to the `detail` / `error_message` top-level fields — NOT a
 * stringify of the whole body. This prevents false-matching on incidental
 * words in nested holdings/orders payloads (the previous broad-stringify
 * approach was producing toast spam after the static-IP proxy rollout
 * because transient error bodies carried matching substrings).
 *
 * NOT treated as expired:
 *   - Transient backend errors (502/504 from proxy, "Cannot reach Kite API")
 *   - Other Kite error types (InputException for T2T, OrderException for
 *     rejection, PermissionException for IP-not-whitelisted, etc.)
 *   - Order rejection reasons like 'insufficient funds'
 *   - 401 from Nifty Satvik auth (handled by auth.js refresh logic)
 */
const KITE_EXPIRED_PATTERNS = /\(TokenException\)|session_expired|token is invalid|access_token is invalid/i;

const detectKiteSessionExpired = (res) => {
  if (!res || typeof res !== 'object') return res;
  // Read only the conventional error fields. Avoid JSON.stringify of the
  // whole body — that was too broad and produced false positives.
  const detail = typeof res.detail === 'string' ? res.detail : '';
  const errorMessage = typeof res.error_message === 'string' ? res.error_message : '';
  const haystack = `${detail} ${errorMessage}`;
  if (haystack && KITE_EXPIRED_PATTERNS.test(haystack)) {
    // CustomEvent (not Event) so we can pass payload for debug tools.
    window.dispatchEvent(new CustomEvent('kite-session-expired', { detail: res }));
  }
  return res;
};

// Wrap a Kite endpoint so 401 / TokenException responses fire the global
// session-expired event before propagating the error to react-query.
//
// Two paths now produce the event:
//   1. Body-pattern match (legacy) — for 200 responses that contain an
//      embedded TokenException string (rare, but documented in earlier
//      Kite proxy migrations).
//   2. ANY 401 from /api/kite/* (new) — covers backend's
//      "Not connected to Kite. Please link your Kite account." which
//      doesn't contain TokenException but is unambiguously a session
//      problem the user must reconnect through.
const dispatchKiteExpired = (payload) => {
  window.dispatchEvent(new CustomEvent('kite-session-expired', { detail: payload }));
};

const isKiteUrl = (url) => typeof url === 'string' && url.includes('/api/kite/');

const kiteJson = async (url, opts) => {
  try {
    const res = await authJson(url, opts);
    return detectKiteSessionExpired(res);
  } catch (err) {
    if (err?.status === 401 && isKiteUrl(err?.url || url)) {
      dispatchKiteExpired(err.body ?? { detail: err.message });
    }
    throw err;
  }
};

const kitePost = async (url, body) => {
  try {
    const res = await authPost(url, body);
    return detectKiteSessionExpired(res);
  } catch (err) {
    if (err?.status === 401 && isKiteUrl(err?.url || url)) {
      dispatchKiteExpired(err.body ?? { detail: err.message });
    }
    throw err;
  }
};

export const kiteSessionStatus = () =>
  kiteJson(`${API}/api/kite/session/status`);

export const kiteExchangeToken = async (requestToken) =>
  kitePost(`${API}/api/kite/session/token`, { request_token: requestToken });

export const kiteLogout = () =>
  authFetch(`${API}/api/kite/session/logout`, { method: 'POST' }).then(r => r.json());

export const kiteHoldings = () =>
  kiteJson(`${API}/api/kite/holdings`);

export const kitePositions = () =>
  kiteJson(`${API}/api/kite/positions`);

export const kiteMargins = () =>
  kiteJson(`${API}/api/kite/margins`);

export const kiteOrders = () =>
  kiteJson(`${API}/api/kite/orders`);

export const kiteLTP = (instruments = []) => {
  const tokens = Array.isArray(instruments) ? instruments.join(',') : instruments;
  return kiteJson(`${API}/api/kite/ltp-via-history?tokens=${tokens}`);
};

export const kiteHistorical = (token, interval, from, to) =>
  kiteJson(`${API}/api/kite/historical/${token}/${interval}?start=${from}&end=${to}`);

export const placeOrder = async (variety, data) =>
  kitePost(`${API}/api/kite/orders/${variety}`, data);

export const cancelOrder = async (variety, orderId) =>
  authFetch(`${API}/api/kite/orders/${variety}/${orderId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(detectKiteSessionExpired);

// ========================================
// NQ Orders — Nifty Satvik-executed orders (Accounting + Journal source)
// ========================================

/**
 * Record an order that was just placed on Kite via our UI. Called immediately
 * after a successful placeOrder(). Only orders tracked through here appear
 * on the Accounting + Journal pages — external Kite trades stay invisible to
 * those pages by design.
 */
export const createNQOrder = ({ kite_order_id, signal_id, ticker, action, qty, placed_price, notes }) =>
  authPost(`${API}/api/nq-orders`, {
    kite_order_id,
    signal_id,
    ticker,
    action,
    qty,
    placed_price,
    notes,
  });

/**
 * List NQ orders with optional filters. Used by both Accounting (year/month)
 * and Journal (status=COMPLETE) pages.
 */
export const listNQOrders = (params = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null && v !== '') qs.set(k, v); });
  const suffix = qs.toString();
  return authJson(`${API}/api/nq-orders${suffix ? `?${suffix}` : ''}`);
};

/** Aggregate FY P&L + tax split. period: 'fy' | 'ytd' | 'all' | '30d' */
export const fetchNQOrderStats = (period = 'fy') =>
  authJson(`${API}/api/nq-orders/stats?period=${encodeURIComponent(period)}`);

/** Journal rationale upsert. */
export const updateNQOrderNotes = (orderId, notes) =>
  authFetch(`${API}/api/nq-orders/${orderId}/notes`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes }),
  }).then(safeJson);

// ========================================
// Watchlist APIs (per-user saved stocks — the left rail)
// Distinct from /signals/watchlist (the model's signal-tier list).
// ========================================

// Each user has two independent lists (list 1 = seeded core, list 2 = blank).
// `listNo` defaults to 1 so any legacy single-list caller keeps working.

/** The authenticated user's saved tickers for a list → { watchlist: [...], list } */
export const getWatchlist = (listNo = 1) =>
  authJson(`${API}/api/watchlist?list=${listNo}`);

/** Add a ticker to a list (idempotent) → { watchlist: [...], list } */
export const addToWatchlist = (ticker, listNo = 1) =>
  authPost(`${API}/api/watchlist`, { ticker, list: listNo });

/** Remove a ticker from a list (204 No Content) */
export const removeFromWatchlist = (ticker, listNo = 1) =>
  authFetch(`${API}/api/watchlist/${encodeURIComponent(ticker)}?list=${listNo}`, { method: 'DELETE' })
    .then(safeJson);

/** Persist a new display order within a list → { watchlist: [...], list } */
export const reorderWatchlist = (order, listNo = 1) =>
  authFetch(`${API}/api/watchlist/reorder`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order, list: listNo }),
  }).then(safeJson);

// ========================================
// Admin APIs (require is_admin=true on the user)
// ========================================

export const adminListUsers = () =>
  authJson(`${API}/api/admin/users`);

// Create a new user. Admin-only on the backend (POST /api/auth/register is
// gated to is_admin). Backend enforces password strength — surfaces a 400
// with a human-readable detail string on failure, which authPost throws as
// an ApiError for the caller to display.
export const adminCreateUser = ({ name, email, password }) =>
  authPost(`${API}/api/auth/register`, { name, email, password });

export const adminUserAction = (userId, action) =>
  authPost(`${API}/api/admin/users/${userId}/${action}`, {});

export const adminAuditLogs = ({ page = 1, perPage = 25, action } = {}) => {
  const qs = new URLSearchParams({ page, per_page: perPage });
  if (action) qs.set('action', action);
  return authJson(`${API}/api/admin/audit-logs?${qs.toString()}`);
};

export const adminKiteStatus = () =>
  authJson(`${API}/api/admin/kite-status`);

export const adminRefreshKite = () =>
  authPost(`${API}/api/admin/refresh-kite`, {});

export const adminSystemHealth = () =>
  authJson(`${API}/api/admin/system-health`);

export const adminListAccessRequests = (status) => {
  const qs = status ? `?status=${encodeURIComponent(status)}&per_page=100` : '?per_page=100';
  return authJson(`${API}/api/admin/access-requests${qs}`);
};

export const adminApproveAccessRequest = (id, payload = {}) =>
  authPost(`${API}/api/admin/access-requests/${id}/approve`, payload);

export const adminRejectAccessRequest = (id) =>
  authPost(`${API}/api/admin/access-requests/${id}/reject`, {});

export const adminDeleteAccessRequest = (id) =>
  authFetch(`${API}/api/admin/access-requests/${id}`, { method: 'DELETE' }).then(safeJson);

export const kiteInstruments = (exchange = 'NSE') =>
  kiteJson(`${API}/api/kite/instruments?exchange=${exchange}`);

export const kiteQuote = (instruments = []) => {
  const q = Array.isArray(instruments) ? instruments.join(',') : instruments;
  return kiteJson(`${API}/api/kite/quote?instruments=${q}`);
};

// ========================================
// Yahoo Finance APIs
// ========================================

export const yahooFundamentals = (symbol) =>
  authJson(`${API}/api/yahoo/fundamentals/${symbol}`);

export const yahooNews = (symbol) =>
  authJson(`${API}/api/yahoo/news/${symbol}`);

export const yahooPeers = (symbol) =>
  authJson(`${API}/api/yahoo/peers/${symbol}`);

export const yahooShareholding = (symbol) =>
  authJson(`${API}/api/yahoo/shareholding/${symbol}`);

export const yahooHistorical = (symbol, interval = '1d', period = '1y') =>
  authJson(`${API}/api/yahoo/historical/${symbol}?interval=${interval}&period=${period}`);

export const yahooQuote = (symbol) =>
  authJson(`${API}/api/yahoo/quote/${symbol}`);

export const yahooQuoteBatch = (symbols = []) => {
  if (!symbols.length) return Promise.resolve({});
  const q = symbols.map(s => encodeURIComponent(s)).join(',');
  return authJson(`${API}/api/yahoo/quote-batch?symbols=${q}`);
};

export const yahooIndexSparklines = () =>
  authJson(`${API}/api/yahoo/index-sparklines`);

// ========================================
// WebSocket Connection (ticket-based auth)
// ========================================

let ws = null;
let wsCallbacks = {};

export const initWebSocket = async ({ onPortfolioUpdate, onTick, onOrderUpdate } = {}) => {
  // Get a short-lived WS ticket from the backend
  try {
    const { ticket } = await authJson(`${API}/api/auth/ws-ticket`);
    if (!ticket) {
      console.error('Failed to get WebSocket ticket');
      return null;
    }

    const wsBase = WS_URL || `ws${window.location.protocol === 'https:' ? 's' : ''}://${window.location.host}`;
    ws = new WebSocket(`${wsBase}/ws?ticket=${ticket}`);

    wsCallbacks = {
      portfolio_update: onPortfolioUpdate,
      tick: onTick,
      order_update: onOrderUpdate,
    };

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const callback = wsCallbacks[data.type];
        if (callback) callback(data);
      } catch (err) {
        console.error('WebSocket message error:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return ws;
  } catch (err) {
    console.error('WebSocket init failed:', err);
    return null;
  }
};

export const subscribeToTicks = (tokens = []) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'subscribe', tokens }));
  }
};

export const unsubscribeFromTicks = (tokens = []) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'unsubscribe', tokens }));
  }
};

export const closeWebSocket = () => {
  if (ws) {
    ws.close();
    ws = null;
  }
};

// ========================================
// Kite Authentication Flow
// ========================================

export const getKiteLoginUrl = (apiKey) =>
  `https://kite.zerodha.com/connect/login?v=3&api_key=${apiKey}`;

export const handleKiteCallback = async () => {
  const params = new URLSearchParams(window.location.search);
  const requestToken = params.get('request_token');

  if (!requestToken) return null;

  try {
    const session = await kiteExchangeToken(requestToken);
    window.history.replaceState({}, document.title, window.location.pathname);
    return session;
  } catch (error) {
    console.error('Kite token exchange failed:', error);
    throw error;
  }
};

// ========================================
// Utility Functions
// ========================================

export const handleApiError = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }
  return response.json();
};

export const checkBackendHealth = async () => {
  try {
    const res = await fetch(`${API}/health`, { timeout: 3000 });
    return res.ok;
  } catch {
    return false;
  }
};

export default {
  // Auth
  authLogin,
  authLogout,
  authMe,
  authRefresh,

  // Dashboard
  fetchOverview,
  fetchPositions,
  fetchSignals,
  fetchSignalHistory,

  // Analytics
  fetchTrades,
  fetchTradeStats,

  // Backtest
  fetchBacktestHistory,
  runBacktest,
  fetchBacktestLive,
  fetchBacktestHistorical,

  // Kite
  kiteSessionStatus,
  kiteExchangeToken,
  kiteLogout,
  kiteHoldings,
  kitePositions,
  kiteMargins,
  kiteOrders,
  kiteLTP,
  kiteHistorical,
  kiteInstruments,
  kiteQuote,
  placeOrder,
  cancelOrder,

  // Yahoo Finance
  yahooFundamentals,
  yahooNews,
  yahooPeers,
  yahooShareholding,
  yahooHistorical,
  yahooQuote,
  yahooQuoteBatch,
  yahooIndexSparklines,

  // WebSocket
  initWebSocket,
  subscribeToTicks,
  unsubscribeFromTicks,
  closeWebSocket,

  // Auth
  getKiteLoginUrl,
  handleKiteCallback,

  // Utils
  handleApiError,
  checkBackendHealth,
};
