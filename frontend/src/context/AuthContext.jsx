import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { queryClient } from '@/lib/queryClient';
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  hasAccessToken,
} from '@/lib/tokens';

const API = process.env.REACT_APP_API_URL ?? '';

// ── Dev-only preview-mode auth bypass ──────────────────────────────────
//
// Set REACT_APP_PREVIEW_NO_AUTH=true in frontend/.env.development.local
// to skip the /api/auth/me check and seed a stub user on mount. Used by
// Claude Preview / screenshot review so every authenticated route renders
// without manual sign-in. Protected backend endpoints still 401; pages
// surface their EmptyCard warn variant (which is itself part of the
// design review).
//
// CRITICAL: hard guard refuses to start in production even if the env
// var leaked into a production build. The env file is gitignored
// (.env.development.local on line 17 of frontend/.gitignore) so it
// cannot ship via the repo, but the guard catches a misconfigured CI
// or stray Vercel env override.
const PREVIEW_NO_AUTH = process.env.REACT_APP_PREVIEW_NO_AUTH === 'true';
if (process.env.NODE_ENV === 'production' && PREVIEW_NO_AUTH) {
  throw new Error(
    'AUTH BYPASS IS DEV-ONLY — REACT_APP_PREVIEW_NO_AUTH must never be set ' +
    'in production builds. Unset it in your build env immediately.'
  );
}

const PREVIEW_STUB_USER = {
  id: 'preview',
  email: 'preview@local',
  name: 'Preview',
  role: 'user',
  mfa_enabled: false,
};

// Session window for a paid trading app — a stolen laptop can place real
// Kite orders. 15 min idle + 60s warning gives a safety margin without
// being annoying mid-session. Backend refresh-token TTL drops 7d → 3d
// in the same change (see dashboard/backend/auth.py).
const IDLE_LOGOUT_MS = 15 * 60 * 1000;       // hard logout after 15 min idle
const IDLE_WARNING_MS = 14 * 60 * 1000;      // show warning toast at 14 min
const WARNING_TOAST_ID = 'nq-idle-warning';
const LOGOUT_BROADCAST = 'nq-auth';

export const AuthContext = createContext({
  user: null,
  loading: true,
  login: async () => ({}),
  loginMfa: async () => null,
  logout: async () => {},
  refreshAuth: async () => {},
});

// Optimistic user-state persistence — prevents "kicked to /login after
// Kite OAuth" bug where the /api/auth/me check on remount times out
// (Render cold start can exceed the 5s budget). With localStorage hydration
// the AuthContext seeds user state synchronously, so ProtectedAppLayout
// renders the dashboard immediately. The background /api/auth/me still
// runs to revalidate; a 401 clears the cached user.
//
// Stored value is just the public user object (id/email/name/is_admin),
// not the session token. The HttpOnly cookie remains the only authority
// for actual API access; localStorage is purely a UI-hydration hint.
const USER_CACHE_KEY = 'nq_user_cache';

function readCachedUser() {
  try {
    const raw = window.localStorage.getItem(USER_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object' && parsed.id) return parsed;
  } catch (_) {}
  return null;
}

function writeCachedUser(u) {
  try {
    if (u) window.localStorage.setItem(USER_CACHE_KEY, JSON.stringify(u));
    else window.localStorage.removeItem(USER_CACHE_KEY);
  } catch (_) {}
}

export function AuthProvider({ children }) {
  const cached = typeof window !== 'undefined' ? readCachedUser() : null;
  const [user, setUserState] = useState(cached);
  // If we have a cached user, we're not "loading" from the user's perspective —
  // the dashboard can render immediately while /api/auth/me revalidates.
  const [loading, setLoading] = useState(!cached);

  // Login-generation counter — bumped on every successful login/loginMfa.
  // The on-mount /api/auth/me check captures the generation when it FIRES;
  // if the generation has advanced by the time the response settles, the
  // response is stale (a login happened mid-flight) and we DON'T apply
  // setUser(null) on a 401 — that would wipe the just-established session.
  // This race was the root cause of "logged out within 0.5s in incognito":
  // /me fires with no cookies on mount, takes 1-3s on Render cold start, by
  // which time the user has logged in and cookies are valid, but the stale
  // 401 from the original /me call comes back and nukes the user state.
  const loginGenRef = useRef(0);

  // setUser wrapper that also writes through to localStorage
  const setUser = useCallback((u) => {
    setUserState(u);
    writeCachedUser(u);
  }, []);

  const idleLogoutTimer = useRef(null);
  const idleWarningTimer = useRef(null);
  const broadcastRef = useRef(null);

  // ── Logout (defined first so it can be referenced by inactivity timer) ──
  //
  // `broadcast=true` (default) tells other tabs to log out via BroadcastChannel.
  // Receivers pass `broadcast=false` to avoid a feedback loop.

  const logout = useCallback(async (broadcast = true) => {
    // Send the refresh token so the backend can revoke its DB row. We do
    // this BEFORE clearing local tokens because the request needs the
    // access token in the Authorization header.
    const refreshToken = getRefreshToken();
    try {
      await fetch(`${API}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
        },
        credentials: 'include',  // legacy cookie fallback during compat window
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Best-effort — local cleanup happens regardless
    }
    // Clear bearer tokens from localStorage. Order matters: do this AFTER
    // the logout POST so the request had a valid Authorization header.
    clearTokens();
    if (broadcast && broadcastRef.current) {
      try { broadcastRef.current.postMessage({ type: 'logout' }); } catch {}
    }
    // Clear React Query cache so a different user logging in next doesn't
    // see the previous user's cached portfolio / orders / signals.
    queryClient.clear();
    setUser(null);
    if (idleLogoutTimer.current) clearTimeout(idleLogoutTimer.current);
    if (idleWarningTimer.current) clearTimeout(idleWarningTimer.current);
    toast.dismiss(WARNING_TOAST_ID);
  }, [setUser]);

  // ── Inactivity auto-logout (15 min) with 60s warning at 14 min ─────

  const resetInactivityTimer = useCallback(() => {
    if (idleLogoutTimer.current) clearTimeout(idleLogoutTimer.current);
    if (idleWarningTimer.current) clearTimeout(idleWarningTimer.current);
    toast.dismiss(WARNING_TOAST_ID);

    idleWarningTimer.current = setTimeout(() => {
      toast.warning('You’ll be signed out in 60 seconds', {
        id: WARNING_TOAST_ID,
        description: 'Click below to stay signed in.',
        duration: 60_000,
        action: {
          label: 'Stay signed in',
          onClick: () => resetInactivityTimer(),
        },
      });
    }, IDLE_WARNING_MS);

    idleLogoutTimer.current = setTimeout(() => {
      logout();
    }, IDLE_LOGOUT_MS);
  }, [logout]);

  useEffect(() => {
    if (!user) return;

    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach(e => window.addEventListener(e, resetInactivityTimer));
    resetInactivityTimer();

    return () => {
      events.forEach(e => window.removeEventListener(e, resetInactivityTimer));
      if (idleLogoutTimer.current) clearTimeout(idleLogoutTimer.current);
      if (idleWarningTimer.current) clearTimeout(idleWarningTimer.current);
    };
  }, [user, resetInactivityTimer]);

  // ── Cross-tab logout sync (BroadcastChannel) ───────
  //
  // Logout in Tab A should immediately clear Tab B too — otherwise B keeps
  // its React Query cache and stale UI until its own idle timer fires.

  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return;
    const bc = new BroadcastChannel(LOGOUT_BROADCAST);
    broadcastRef.current = bc;
    bc.onmessage = (ev) => {
      if (ev?.data?.type === 'logout') {
        // Receiver path — don't re-broadcast or hit /auth/logout again
        // (the originating tab already did that). But DO clear our local
        // tokens so this tab can't keep firing authenticated requests
        // after the other tab logged us out.
        clearTokens();
        queryClient.clear();
        setUser(null);
        writeCachedUser(null);
        if (idleLogoutTimer.current) clearTimeout(idleLogoutTimer.current);
        if (idleWarningTimer.current) clearTimeout(idleWarningTimer.current);
        toast.dismiss(WARNING_TOAST_ID);
      }
    };
    return () => {
      bc.close();
      broadcastRef.current = null;
    };
  }, [setUser]);

  // ── Token refresh (every 3.5 hours for 4-hour tokens) ──
  //
  // Backend's ACCESS_TOKEN_EXPIRE_MINUTES is 240 (4 hours). We refresh
  // 30 min before that so a slow Render cold-start can't catch us
  // mid-window. Earlier this was 12 min for a 15-min token TTL — the
  // shorter cadence wasn't buying anything on a solo-admin app and was
  // racing transient backend hiccups into spurious logouts.

  useEffect(() => {
    if (!user) return;

    const interval = setInterval(async () => {
      try {
        const refreshToken = getRefreshToken();
        if (!refreshToken) return;  // no token, nothing to refresh
        const res = await fetch(`${API}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (res.ok) {
          const data = await res.json();
          if (data?.access_token) {
            setTokens({
              access_token: data.access_token,
              refresh_token: data.refresh_token,
            });
          }
        } else {
          setUser(null);
        }
      } catch {
        // Network error — don't logout, retry next cycle
      }
    }, 3.5 * 60 * 60 * 1000); // 3.5 hours

    return () => clearInterval(interval);
  }, [user, setUser]);

  // ── Tab-focus session re-validation ────────────────
  //
  // When the user comes back to the tab after >60s away, verify the
  // session is still alive. Catches "session expired in another tab",
  // "admin deactivated me while I was away", or "refresh-token reuse
  // killed the chain because I copied the cookie elsewhere". Cheap —
  // /auth/me is a single indexed lookup. Throttled so rapid alt-tabs
  // don't hammer the backend.

  const lastFocusCheckRef = useRef(0);

  useEffect(() => {
    if (!user) return;
    const onVisibility = async () => {
      if (document.visibilityState !== 'visible') return;
      const now = Date.now();
      if (now - lastFocusCheckRef.current < 60_000) return;
      lastFocusCheckRef.current = now;
      try {
        const token = getAccessToken();
        const res = await fetch(`${API}/api/auth/me`, {
          credentials: 'include',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.status === 401) {
          window.dispatchEvent(new Event('auth-session-expired'));
        }
      } catch {
        // Network error — leave it. The next user action will surface it
        // via authFetch's 401 handler in services/api.js.
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, [user]);

  // ── Reactive session-expired listener ──────────────
  //
  // Currently the only dispatcher is the tab-focus /api/auth/me check above.
  // That's the "user came back to the tab after >60s and the session is now
  // genuinely dead" case (admin deactivated them, refresh-token-reuse killed
  // the chain, or session was logged out in another tab). On that signal we
  // clear the cached user, dump React Query, and toast — without this the
  // localStorage hydration would mask the dead session on next remount.
  //
  // We do NOT auto-dispatch on /api/* 401s anymore — see services/api.js
  // for the history of why (immediate-logout-loop right after login).

  useEffect(() => {
    const handler = () => {
      if (!user) return;  // already logged out, ignore
      setUser(null);
      queryClient.clear();
      toast.error('Session expired — please sign in again', {
        id: 'nq-session-expired',
        duration: 8_000,
      });
    };
    window.addEventListener('auth-session-expired', handler);
    return () => window.removeEventListener('auth-session-expired', handler);
  }, [user, setUser]);

  // ── Check session on mount ──────────────────────────
  //
  // CRITICAL: must complete (success or fail) within ~5s. Without a timeout,
  // a slow-starting Render backend (free tier wakes from sleep in 30+s) leaves
  // `loading=true` forever, which makes LoginGuard render `null` — i.e. a
  // completely black page that locks users out of signing in. AbortController
  // ensures `finally` always fires, so `loading` flips to `false` and the
  // login UI renders even if the backend is unreachable.

  useEffect(() => {
    // Preview-mode bypass — see PREVIEW_NO_AUTH constant at the top of this
    // file. Skip the network call entirely, seed the stub user, render.
    if (PREVIEW_NO_AUTH) {
      // eslint-disable-next-line no-console
      console.info(
        '[AuthContext] preview-mode auth bypass active (dev only). ' +
        'Backend endpoints will still 401; pages render their warn empty states.'
      );
      setUser(PREVIEW_STUB_USER);
      setLoading(false);
      return;
    }

    // Skip the network round-trip entirely if there's no access token to
    // validate. Saves a cold-start delay for every fresh-device visit to
    // /login (the most common entry point for new users). The cached-user
    // hydration path still works: if both localStorage `nq_user_cache` and
    // `nq_access_token` exist, hydration sets user state synchronously and
    // we fall through to the network revalidation below.
    if (!hasAccessToken()) {
      // No token → guaranteed unauthenticated. Clear any stale cached user
      // (the inconsistent state the bearer-token migration prevents) and
      // surface the /login UI immediately. setUser(null) is a no-op when
      // user is already null.
      setUser(null);
      setLoading(false);
      return;
    }

    const ctrl = new AbortController();
    // 15s budget — Render free-tier cold start can exceed 5s. The longer
    // budget is safe because cached-user hydration means the dashboard
    // renders immediately while this runs in the background.
    const timeoutId = setTimeout(() => ctrl.abort(), 15000);

    // Snapshot the login-generation at fire time. If a login mutates this
    // before the request settles, the response is stale — see comment on
    // loginGenRef above.
    const startGen = loginGenRef.current;

    (async () => {
      try {
        const token = getAccessToken();
        const res = await fetch(`${API}/api/auth/me`, {
          credentials: 'include',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: ctrl.signal,
        });
        // Stale-response guard: a login happened while this was in flight,
        // ignore the result entirely. The login() handler already set user
        // with the authoritative response.
        if (loginGenRef.current !== startGen) return;
        if (res.ok) {
          const data = await res.json();
          setUser(data);
        } else if (res.status === 401) {
          // Definitive: cookie missing or invalid. Clear cached user so the
          // login redirect fires. Anything else (5xx, network blip) leaves
          // the cached user in place — a transient backend hiccup must NOT
          // sign the user out.
          setUser(null);
        }
      } catch (err) {
        // AbortError (timeout) or network error: keep cached user. The next
        // user action will surface a real 401 via authFetch's retry layer.
        if (err?.name !== 'AbortError') {
          // eslint-disable-next-line no-console
          console.debug('[auth] /me check failed transiently, keeping cached user');
        }
      } finally {
        clearTimeout(timeoutId);
        setLoading(false);
      }
    })();

    return () => {
      clearTimeout(timeoutId);
      ctrl.abort();
    };
  }, [setUser]);

  // ── Login ───────────────────────────────────────────
  //
  // Returns one of:
  //   { user: {...} }                          — fully signed in, MFA off
  //   { mfaRequired: true, mfaPendingToken }   — caller must collect TOTP
  //                                              and call loginMfa()
  // Throws on bad credentials / lockout / network.

  const login = useCallback(async (email, password) => {
    const res = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });

    // Read as text first to avoid "body stream already read" errors
    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      throw new Error(`Server error (${res.status})`);
    }

    if (!res.ok) {
      throw new Error(data.detail || `Login failed (${res.status})`);
    }

    if (data.mfa_required) {
      return { mfaRequired: true, mfaPendingToken: data.mfa_pending_token };
    }

    // Store bearer tokens BEFORE setUser so any immediate /api/* call that
    // setUser indirectly triggers (e.g. via a query that re-runs when user
    // state flips) can attach the new access token to its Authorization
    // header. Also bump login-gen BEFORE setUser so the in-flight on-mount
    // /api/auth/me is stale-guarded out of clobbering our new session.
    if (data.access_token) {
      setTokens({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });
    }
    loginGenRef.current += 1;
    setUser(data.user);
    return { user: data.user };
  }, [setUser]);

  const loginMfa = useCallback(async (mfaPendingToken, code) => {
    const res = await fetch(`${API}/api/auth/login/mfa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ mfa_pending_token: mfaPendingToken, code }),
    });
    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      throw new Error(`Server error (${res.status})`);
    }
    if (!res.ok) {
      throw new Error(data.detail || `MFA verification failed (${res.status})`);
    }
    if (data.access_token) {
      setTokens({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });
    }
    loginGenRef.current += 1;
    setUser(data.user);
    return data.user;
  }, [setUser]);

  // ── Refresh ─────────────────────────────────────────

  const refreshAuth = useCallback(async () => {
    try {
      const refreshToken = getRefreshToken();
      const res = await fetch(`${API}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data?.access_token) {
          setTokens({
            access_token: data.access_token,
            refresh_token: data.refresh_token,
          });
        }
        setUser(data.user);
      } else {
        clearTokens();
        setUser(null);
      }
    } catch {
      setUser(null);
    }
  }, [setUser]);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginMfa, logout, refreshAuth }}>
      {children}
    </AuthContext.Provider>
  );
}
