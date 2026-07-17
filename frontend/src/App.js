import React, { useState, useEffect, useLayoutEffect, useContext, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { toast } from 'sonner';

// Local toast helpers — kept inline so the ProtectedAppLayout's Kite
// callback handler can surface failures without re-importing sonner.
const toastSuccess = (msg, opts) => toast.success(msg, opts);
const toastError = (msg, opts) => toast.error(msg, opts);
import { queryClient } from '@/lib/queryClient';
import { TopBar } from '@/components/layout/TopBar';
import WatchlistRail from '@/components/layout/WatchlistRail';

// Phase 8 polish: every page is code-split via React.lazy so the initial
// bundle only carries the shell + auth + sidebar. Each route fetches its
// own JS chunk on first navigation. Recharts (~150KB gz) loads only on
// pages that actually render charts.
//
// Login + Landing stay eager — they're the entry points and any lazy
// Suspense flicker on first paint reads as broken.
import Login from '@/pages/Login';
import LandingV2 from '@/pages/LandingV2';
import InfoPage from '@/pages/InfoPage';
// NOTE: the legacy `Landing` page (/landing-v1) was retired 2026-07-02 — it carried fabricated
// stats and a pricing block that contradicted the live invite-only positioning. The route now
// redirects to `/`. Landing.jsx stays on disk; roll back by reverting this commit.

const DashboardV2     = React.lazy(() => import('@/pages/DashboardV2'));
const DashboardV3     = React.lazy(() => import('@/pages/DashboardV3'));
const SignalsV2       = React.lazy(() => import('@/pages/SignalsV2'));
const SignalsV3       = React.lazy(() => import('@/pages/SignalsV3'));
const JournalV2       = React.lazy(() => import('@/pages/JournalV2'));
const BacktestV2      = React.lazy(() => import('@/pages/BacktestV2'));
const StockDetailV2   = React.lazy(() => import('@/pages/StockDetailV2'));
// AdminV2 is the canonical admin console (4-tab layout). The legacy Admin
// page is retained behind the /admin route only as a temporary fallback
// until V2 is soaked; the route below points at AdminV2.
const Admin           = React.lazy(() => import('@/pages/Admin'));
const AdminV2         = React.lazy(() => import('@/pages/AdminV2'));
const TrackRecordV2   = React.lazy(() => import('@/pages/TrackRecordV2'));
const TrackRecordV3   = React.lazy(() => import('@/pages/TrackRecordV3'));
const SettingsV2      = React.lazy(() => import('@/pages/SettingsV2'));
const PrimitivesShowcase = React.lazy(() => import('@/pages/_internal/Primitives'));
const PreviewDashboard   = React.lazy(() => import('@/pages/_internal/PreviewDashboard'));

// Kite OAuth callback page — eagerly imported so the redirect bounce is
// instant. Outside ProtectedAppLayout so no chrome flashes during exchange.
const AuthCallback = React.lazy(() => import('@/pages/AuthCallback'));
const ForgotPassword = React.lazy(() => import('@/pages/ForgotPassword'));
const ResetPassword  = React.lazy(() => import('@/pages/ResetPassword'));
import PageTransition from '@/components/PageTransition';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';
import { cn } from '@/lib/utils';
import { TooltipProvider } from '@/components/ui/tooltip';
import { AuthProvider, AuthContext } from '@/context/AuthContext';
import { useOrderUpdates } from '@/hooks/useOrderUpdates';

// One-time cleanup of the dead V1/V2 redesign feature flag. Earlier builds
// gated the V2 amber design behind localStorage.nq_redesign_v2; the legacy
// design is now deleted, so any lingering '0' value would be dead state.
if (typeof window !== 'undefined') {
  try { window.localStorage.removeItem('nq_redesign_v2'); } catch (_) {}
}

// Kite context shared across the app
export const KiteContext = React.createContext({
  connected: false,
  userId: null,
  connecting: false,
  connect: () => {},
  disconnect: () => {},
});


/**
 * Layout for all authenticated app routes (dashboard, signals, etc.).
 * Wraps children with sidebar + KiteContext, redirects to /login if not auth'd.
 */
function ProtectedAppLayout() {
  const { user, loading } = useContext(AuthContext);

  // One-shot WS subscription: invalidate order/holdings/stats queries on
  // every backend-broadcast `order_update` frame. Mounted at layout level
  // because useWebSocket uses a module-level singleton — page-level mounts
  // would close/reopen the socket on every navigation.
  useOrderUpdates();

  // Defensive scroll-lock cleanup — runs on every navigation within the
  // authenticated app, not just on mount. Lenis (only active on /) leaks
  // `lenis-*` classes onto <html> that apply `overflow: clip`, and
  // IntroChoreography historically locked body overflow. We force-restore
  // a known-good native-scroll state on every render so dashboard scroll
  // never gets stuck.
  //
  // useLayoutEffect runs synchronously before paint so users never see
  // the broken (locked-scroll) state.
  const location = useLocation();
  useLayoutEffect(() => {
    if (typeof document === 'undefined') return;
    const html = document.documentElement;
    const body = document.body;
    // Strip leaked Lenis classes from html AND body
    [html, body].forEach((el) => {
      Array.from(el.classList)
        .filter((c) => c.startsWith('lenis'))
        .forEach((c) => el.classList.remove(c));
    });
    // Clear inline overflow leaked by Lenis or any modal that forgot cleanup
    html.style.overflow = '';
    html.style.height = '';
    body.style.overflow = '';
    body.style.height = '';
    body.style.position = '';
    // Strip leaked landing body class (safety net)
    body.classList.remove('landing-page-active');
    // Remove orphaned custom cursor elements if cursor feature returns
    document.querySelectorAll('.custom-cursor-dot, .custom-cursor-ring')
      .forEach((el) => el.remove());
  }, [location.pathname]);

  // No per-user broker connection (ADR 0011). KiteContext is permanently disconnected;
  // consumers gate every per-user Kite query on `connected` (always false) and degrade to the
  // not-connected state. Owner market-data quotes are a separate path and unaffected.
  const kiteValue = { connected: false, userId: null, connecting: false, connect: () => {}, disconnect: () => {} };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <KiteContext.Provider value={kiteValue}>
      <div data-page-ctx="dashboard" className="min-h-screen flex flex-col">
        <TopBar />
        <div className="flex flex-1 min-w-0">
          <WatchlistRail />
          <main className="flex-1 min-w-0 overflow-x-hidden relative z-10">
            <Outlet />
          </main>
        </div>
      </div>
    </KiteContext.Provider>
  );
}

function LoginGuard() {
  const { user, loading } = useContext(AuthContext);
  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;
  return <Login />;
}

/**
 * RouteFallback — what shows while a lazy-loaded page chunk is downloading.
 * Black background match keeps the transition seamless on slow connections.
 */
function RouteFallback() {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--surface-0, #000)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1,
        pointerEvents: 'none',
      }}
      aria-busy="true"
      aria-live="polite"
    >
      <div
        style={{
          width: 28,
          height: 28,
          border: '2px solid var(--edge-1, rgba(255,255,255,0.08))',
          borderTopColor: 'var(--brand, #4F8CFF)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @media (prefers-reduced-motion: reduce) {
          [aria-busy="true"] > div { animation: none !important; }
        }
      `}</style>
    </div>
  );
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      {/* ErrorBoundary scoped to the route — a crash in one page (e.g.
          StockDetailV2) shows a useful card with the error message + a
          reload button, instead of leaving the user on a fully-black
          page with no information. The boundary's `key` is the pathname
          so navigating to a different route auto-resets the error state. */}
      <ErrorBoundary key={location.pathname}>
      <Suspense fallback={<RouteFallback />}>
      <Routes location={location} key={location.pathname}>
        {/* Public routes — landing page always shown at / */}
        {/* LandingV2 is the single live landing; /landing-v1 (legacy) redirects here — it
            carried fabricated stats + a contradictory pricing block. Roll back via git. */}
        <Route path="/" element={<PageTransition><LandingV2 /></PageTransition>} />
        <Route path="/landing-v1" element={<Navigate to="/" replace />} />
        <Route path="/login" element={<PageTransition><LoginGuard /></PageTransition>} />
        <Route path="/forgot-password" element={<PageTransition><ForgotPassword /></PageTransition>} />
        <Route path="/reset-password" element={<PageTransition><ResetPassword /></PageTransition>} />

        {/* Internal — Phase 1 primitive library QA page. Not linked from nav.
            Unauthenticated so design review doesn't require a login. Remove
            before Phase 2 ship if this becomes a security concern. */}
        <Route path="/_primitives" element={<PageTransition><PrimitivesShowcase /></PageTransition>} />
        {/* fxreplay-inspired dashboard prototype. Public, no auth gate.
            Lives at /preview-dashboard — separate from /dashboard so
            the redesign doesn't affect paying users. */}
        <Route path="/preview-dashboard" element={<PageTransition><PreviewDashboard /></PageTransition>} />

        {/* Kite OAuth callback — Zerodha redirects here with ?request_token=...
            Public route (no ProtectedAppLayout) so the chrome doesn't flash
            during the ~500ms exchange. The component itself requires the NQ
            session cookie to call kiteExchangeToken; if missing it toasts
            "sign in first" and redirects to /login. See pages/AuthCallback.jsx. */}
        <Route path="/auth/callback" element={<AuthCallback />} />

        {/* Authenticated app — wrapped with sidebar + KiteContext */}
        <Route element={<ProtectedAppLayout />}>
          <Route path="/dashboard" element={<PageTransition><DashboardV3 /></PageTransition>} />
          {/* DashboardV2 retained at /dashboard-v2 for rollback */}
          <Route path="/dashboard-v2" element={<PageTransition><DashboardV2 /></PageTransition>} />
          <Route path="/premove" element={<PageTransition><SignalsV3 /></PageTransition>} />
          {/* SignalsV2 retained at /premove-v2 for rollback */}
          <Route path="/premove-v2" element={<PageTransition><SignalsV2 /></PageTransition>} />
          {/* Positions + Portfolio stripped 2026-07-13 (research-only product; users
              track holdings on their broker). Redirect legacy links to Research. */}
          <Route path="/portfolio" element={<Navigate to="/premove" replace />} />
          <Route path="/portfolio-v2" element={<Navigate to="/premove" replace />} />
          <Route path="/positions" element={<Navigate to="/premove" replace />} />
          {/* Broker-mirror pages stripped 2026-07-13 (research-only; track on your broker). */}
          <Route path="/orders" element={<Navigate to="/premove" replace />} />
          <Route path="/funds" element={<Navigate to="/premove" replace />} />
          <Route path="/pnl" element={<Navigate to="/premove" replace />} />
          <Route path="/accounting" element={<Navigate to="/premove" replace />} />
          <Route path="/journal" element={<PageTransition><JournalV2 /></PageTransition>} />
          <Route path="/track-record" element={<PageTransition><TrackRecordV3 /></PageTransition>} />
          <Route path="/backtest" element={<PageTransition><BacktestV2 /></PageTransition>} />
          <Route path="/settings" element={<PageTransition><SettingsV2 /></PageTransition>} />
          <Route path="/stock/:symbol" element={<PageTransition><StockDetailV2 /></PageTransition>} />
          {/* /admin → AdminV2 (4-tab console). Legacy Admin import kept for emergency
              rollback only — not routed. Will be removed after AdminV2 soaks. */}
          <Route path="/admin" element={<PageTransition><AdminV2 /></PageTransition>} />
        </Route>

        {/* Footer info/legal pages (Disclaimer, Privacy, Terms, About, …) — one per slug */}
        <Route path="/:slug" element={<PageTransition><InfoPage /></PageTransition>} />

        {/* Catch-all — redirect unknown routes to landing */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
      </ErrorBoundary>
    </AnimatePresence>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <BrowserRouter>
            <AnimatedRoutes />
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
      )}
    </QueryClientProvider>
  );
}

export default App;
