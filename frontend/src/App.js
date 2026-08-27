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
// NOTE: the legacy `Landing` page + its exclusive components were DELETED 2026-07-18. They carried
// fabricated stats, a pricing block contradicting the invite-only positioning, and the RETIRED-v1
// strategy in plain text (Features.jsx named the old LightGBM model / feature count). Unrouted since
// 2026-07-02, but a disclosure landmine one route change away. /landing-v1 still redirects to `/`.

const DashboardV3     = React.lazy(() => import('@/pages/DashboardV3'));
const SignalsV3       = React.lazy(() => import('@/pages/SignalsV3'));
const BacktestV2      = React.lazy(() => import('@/pages/BacktestV2'));
const StockDetailV2   = React.lazy(() => import('@/pages/StockDetailV2'));
// AdminV2 is the canonical admin console (4-tab layout). The legacy Admin page and
// TrackRecordV2 were DELETED 2026-08-27 — both had been unrouted for weeks, kept as
// "emergency rollback", which git already is. An unrouted import is not a rollback, it
// is a second copy of a page nobody maintains that still ships in the bundle graph.
const AdminV2         = React.lazy(() => import('@/pages/AdminV2'));
const TrackRecordV3   = React.lazy(() => import('@/pages/TrackRecordV3'));
const PortfolioV3     = React.lazy(() => import('@/pages/PortfolioV3'));
const ThisWeek        = React.lazy(() => import('@/pages/ThisWeek'));
const RecommendationHistory = React.lazy(() => import('@/pages/RecommendationHistory'));
const SettingsV2      = React.lazy(() => import('@/pages/SettingsV2'));
const PrimitivesShowcase = React.lazy(() => import('@/pages/_internal/Primitives'));
const PreviewDashboard   = React.lazy(() => import('@/pages/_internal/PreviewDashboard'));

const ForgotPassword = React.lazy(() => import('@/pages/ForgotPassword'));
const ResetPassword  = React.lazy(() => import('@/pages/ResetPassword'));
import PageTransition from '@/components/PageTransition';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';
import { cn } from '@/lib/utils';
import { TooltipProvider } from '@/components/ui/tooltip';
import { AuthProvider, AuthContext } from '@/context/AuthContext';

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

  // NO mode="wait" (removed 2026-08-27). AnimatePresence's direct child here is ErrorBoundary,
  // not a motion component, so it never reports an exit completion — and under mode="wait" the
  // INCOMING page then waited forever at PageTransition's `initial` state. Every route that
  // redirects on mount (an unknown slug, /landing-v1, /portfolio-v2) therefore rendered a fully
  // populated DOM stuck at opacity 0: a blank page with 30KB of content behind it. Without
  // mode="wait" the incoming page animates in immediately, which is also what a redirect wants.
  return (
    <AnimatePresence>
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

        {/* Authenticated app — wrapped with sidebar + KiteContext */}
        <Route element={<ProtectedAppLayout />}>
          <Route path="/dashboard" element={<PageTransition><DashboardV3 /></PageTransition>} />
          {/* The single "what to do this week" surface — consolidates the buys (Research),
              the exits (Portfolio's outstanding strip) and the monitor flags into one list. */}
          <Route path="/this-week" element={<PageTransition><ThisWeek /></PageTransition>} />
          <Route path="/premove" element={<PageTransition><SignalsV3 /></PageTransition>} />
          {/* Portfolio RESURRECTED 2026-07-18 (Stage 5): a per-user self-report holdings page
              sourced from the execution ledger + owner quotes (ADR 0011), NOT Kite. Positions
              (the Kite-mirror page) stays stripped. */}
          <Route path="/portfolio" element={<PageTransition><PortfolioV3 /></PageTransition>} />
          <Route path="/portfolio-v2" element={<Navigate to="/portfolio" replace />} />
          {/* The broker-mirror redirects (/positions /orders /funds /pnl /accounting /journal)
              were REMOVED 2026-08-27 with the dead Sidebar that was their only entry point. They
              pointed at /premove, which is not what any of those words mean — a redirect that
              lands somewhere unrelated is worse than the catch-all, which sends an old bookmark
              home instead of to a page the user then has to make sense of. */}
          <Route path="/track-record" element={<PageTransition><TrackRecordV3 /></PageTransition>} />
          {/* Recommendation history: every posted weekly call and how it performed from the entry-week
              Monday open. Exited calls (target/stop/expired) live here, not on the live Research board. */}
          <Route path="/history" element={<PageTransition><RecommendationHistory /></PageTransition>} />
          <Route path="/backtest" element={<PageTransition><BacktestV2 /></PageTransition>} />
          <Route path="/settings" element={<PageTransition><SettingsV2 /></PageTransition>} />
          <Route path="/stock/:symbol" element={<PageTransition><StockDetailV2 /></PageTransition>} />
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
