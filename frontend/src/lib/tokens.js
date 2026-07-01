/**
 * Token storage for the bearer-token auth flow.
 *
 * Stores the access + refresh JWTs in localStorage so they can be attached
 * as `Authorization: Bearer <token>` on every /api/* request. Replaces the
 * HttpOnly cookie flow that broke across mobile Safari ITP, Chrome incognito
 * third-party-cookie blocking, and Vercel-proxy edge cases.
 *
 * Trade-off acknowledged: localStorage is readable from any JS on the page
 * (HttpOnly cookies were not). Mitigated by our strict CSP (script-src
 * 'self' + 'unsafe-inline'; no third-party CDN loads). XSS-stolen access
 * tokens are bounded to the 4h access-token TTL; refresh-token-reuse
 * detection on the backend kills the chain if the refresh is replayed
 * from elsewhere.
 *
 * Centralizing read/write/clear here so a future migration to a more
 * secure store (e.g. encrypted IndexedDB) is a one-file change.
 */

const ACCESS_KEY = 'nq_access_token';
const REFRESH_KEY = 'nq_refresh_token';

const safe = (op) => {
  try {
    return op();
  } catch {
    return null;
  }
};

export function getAccessToken() {
  return safe(() => window.localStorage.getItem(ACCESS_KEY));
}

export function getRefreshToken() {
  return safe(() => window.localStorage.getItem(REFRESH_KEY));
}

export function setTokens({ access_token, refresh_token }) {
  safe(() => {
    if (access_token) window.localStorage.setItem(ACCESS_KEY, access_token);
    if (refresh_token) window.localStorage.setItem(REFRESH_KEY, refresh_token);
  });
}

export function clearTokens() {
  safe(() => {
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  });
}

export function hasAccessToken() {
  return !!getAccessToken();
}
