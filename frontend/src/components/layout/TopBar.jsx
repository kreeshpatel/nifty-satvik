import React, { useState, useEffect, useRef, useContext } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Search, Bell, User, LogOut, Plug, Loader2, Menu, X,
  LayoutDashboard, LineChart, Briefcase, Layers, ListOrdered,
  Wallet, BarChart3, BookOpen, Trophy, FlaskConical, Calculator,
  Settings as SettingsIcon, Shield, Minus, Plus,
} from 'lucide-react';
import { toast } from 'sonner';
import { searchStocks } from '@/services/kiteStock';
import { KiteContext } from '@/App';
import { AuthContext } from '@/context/AuthContext';
import BrandLogo from './BrandLogo';
import KiteChip from './KiteChip';
import HeaderTicker from './HeaderTicker';
import { useIsMobile } from '@/hooks/useIsMobile';
import { useUiScale } from '@/hooks/useUiScale';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

/**
 * TopBar — glass topbar nav per design system kit (2026-05-21).
 *
 * Layout: logo · primary pill tabs · spacer · search · notifications · user pill
 * Replaces left Sidebar entirely. Secondary routes accessed via "More" dropdown
 * on the right side of the primary tab row.
 */

// Primary nav — every visible pill tab in the topbar. Per design system kit
// v2 (2026-05-21), no "More" dropdown — all routes get top-level visibility.
// Primary top-nav pills — kept lean. Reports/Journal/Track/Backtest/Ledger/
// Settings live under the account (avatar) menu instead (see ACCOUNT_LINKS).
const PRIMARY_TABS = [
  { to: '/dashboard',    label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/premove',      label: 'Research',   icon: LineChart },
  { to: '/positions',    label: 'Positions',  icon: Layers },
  { to: '/portfolio',    label: 'Portfolio',  icon: Briefcase },
];

// Secondary pages, tucked into the account dropdown with clearer names.
// Orders + Funds moved here (2026-07-07) so the top nav mirrors the
// prototype's Dashboard · Research · Positions · Portfolio set.
const ACCOUNT_LINKS = [
  { to: '/orders',       label: 'Orders',         icon: ListOrdered },
  { to: '/funds',        label: 'Funds',          icon: Wallet },
  { to: '/pnl',          label: 'Reports',        icon: BarChart3 },
  { to: '/track-record', label: 'Track record',   icon: Trophy },
  { to: '/journal',      label: 'Journal',        icon: BookOpen },
  { to: '/backtest',     label: 'Backtest',       icon: FlaskConical },
  { to: '/accounting',   label: 'Ledger & charges', icon: Calculator },
];

export function TopBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const kite = useContext(KiteContext);
  const { user, logout } = useContext(AuthContext);
  const isMobile = useIsMobile();

  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const searchWrapRef = useRef(null);

  const isAdmin = !!user?.is_admin;
  const uiScale = useUiScale();

  // Display-size control for the account menu — a "zoom that doesn't reflow".
  // Plain buttons (not menu items) so clicking them doesn't close the menu.
  const scaleBtn = (label, onClick, enabled) => (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={!enabled}
      style={{
        width: 24, height: 24, display: 'grid', placeItems: 'center',
        borderRadius: 6, border: '1px solid var(--edge-1)', background: 'var(--surface-1)',
        color: 'var(--text-2)', cursor: enabled ? 'pointer' : 'not-allowed', opacity: enabled ? 1 : 0.4,
      }}
    >
      {label === 'Zoom out' ? <Minus size={13} /> : <Plus size={13} />}
    </button>
  );
  const scaleRow = (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px', fontSize: 13, color: 'var(--text-2)' }}>
      <span>Display size</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {scaleBtn('Zoom out', uiScale.dec, uiScale.canDec)}
        <span style={{ minWidth: 42, textAlign: 'center', fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>{uiScale.pct}%</span>
        {scaleBtn('Zoom in', uiScale.inc, uiScale.canInc)}
      </div>
    </div>
  );

  // Close mobile menu on route change so tap-to-navigate dismisses the drawer.
  useEffect(() => {
    setMobileMenuOpen(false);
    setMobileSearchOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (query.length < 1) { setResults([]); return; }
    let cancelled = false;
    const timer = setTimeout(async () => {
      const res = await searchStocks(query, 8);
      if (!cancelled) { setResults(res); setSelectedIdx(0); }
    }, 150);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query]);

  useEffect(() => {
    const handler = (e) => {
      if (searchWrapRef.current && !searchWrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelect = (symbol) => {
    setQuery(''); setOpen(false); setResults([]);
    navigate(`/stock/${symbol}`);
  };

  const handleKeyDown = (e) => {
    if (!open || !results.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, results.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); handleSelect(results[selectedIdx].symbol); }
    else if (e.key === 'Escape') { setOpen(false); }
  };

  const isActive = (path) => {
    if (path === '/dashboard') return location.pathname === '/' || location.pathname.startsWith('/dashboard');
    return location.pathname.startsWith(path);
  };

  // Mobile gets a different chrome:
  //   [hamburger]  [logo]  [search-icon]  [user-avatar]
  // Desktop keeps the full pill-tab layout. Drawer (full-screen sheet) lists
  // every route + Kite controls + sign-out — same affordances as desktop,
  // just stacked vertically.
  if (isMobile) {
    return (
      <>
        <header
          className="nq-topbar"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 50,
            height: 56,
            display: 'grid',
            gridTemplateColumns: 'auto 1fr auto auto',
            alignItems: 'center',
            gap: 8,
            padding: '0 12px',
            background: 'rgba(10, 14, 34, 0.72)',
            backdropFilter: 'blur(28px) saturate(160%)',
            WebkitBackdropFilter: 'blur(28px) saturate(160%)',
            borderBottom: '1px solid var(--edge-1)',
          }}
        >
          <button
            type="button"
            aria-label="Open menu"
            onClick={() => setMobileMenuOpen(true)}
            style={{
              width: 44, height: 44,
              display: 'grid', placeItems: 'center',
              background: 'transparent', border: 'none',
              color: 'var(--text-1)', cursor: 'pointer',
            }}
          >
            <Menu size={20} />
          </button>
          <BrandLogo to="/dashboard" size={26} wordSize={15} />
          <button
            type="button"
            aria-label="Search"
            onClick={() => setMobileSearchOpen((v) => !v)}
            style={{
              width: 40, height: 40,
              display: 'grid', placeItems: 'center',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--edge-1)',
              borderRadius: '50%',
              color: 'var(--text-2)', cursor: 'pointer',
            }}
          >
            <Search size={16} />
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                aria-label="Account menu"
                style={{
                  width: 40, height: 40, borderRadius: '50%',
                  background: 'var(--brand-grad)',
                  display: 'grid', placeItems: 'center',
                  border: 'none', cursor: 'pointer', color: '#fff',
                }}
              >
                <User size={16} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={8} className="min-w-[220px]">
              <DropdownMenuLabel className="font-normal">
                <div style={{ fontSize: 13, color: 'var(--text-1)' }}>{user?.name || 'You'}</div>
                <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>{user?.email}</div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              {!kite?.connected ? (
                <DropdownMenuItem onSelect={() => kite?.connect?.()} className="gap-2 cursor-pointer">
                  {kite?.connecting ? <Loader2 size={14} className="animate-spin" /> : <Plug size={14} />}
                  Connect Kite
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem onSelect={() => kite?.disconnect?.()} className="gap-2 cursor-pointer">
                  <Plug size={14} />
                  Kite · {kite.userId}
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              {ACCOUNT_LINKS.map((l) => {
                const LIcon = l.icon;
                return (
                  <DropdownMenuItem key={l.to} onSelect={() => navigate(l.to)} className="gap-2 cursor-pointer">
                    <LIcon size={14} />
                    {l.label}
                  </DropdownMenuItem>
                );
              })}
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => navigate('/settings')} className="gap-2 cursor-pointer">
                <SettingsIcon size={14} />
                Settings
              </DropdownMenuItem>
              {isAdmin && (
                <DropdownMenuItem onSelect={() => navigate('/admin')} className="gap-2 cursor-pointer">
                  <Shield size={14} />
                  Admin console
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              {scaleRow}
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => logout()} className="gap-2 cursor-pointer">
                <LogOut size={14} />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* Mobile search drawer — slides down under topbar when search icon tapped */}
        {mobileSearchOpen && (
          <div
            ref={searchWrapRef}
            style={{
              position: 'sticky', top: 56, zIndex: 49,
              padding: 12,
              background: 'rgba(10, 14, 34, 0.92)',
              borderBottom: '1px solid var(--edge-1)',
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
            }}
          >
            <div
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                height: 44, padding: '0 14px',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid var(--edge-2)',
                borderRadius: 999,
              }}
            >
              <Search size={16} style={{ color: 'var(--text-3)' }} />
              <input
                value={query}
                onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
                onKeyDown={handleKeyDown}
                placeholder="Search tickers, place orders…"
                autoFocus
                className="bg-transparent outline-none border-none flex-1"
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: 16,
                  color: 'var(--text-1)',
                  minWidth: 0,
                  width: '100%',
                }}
              />
              {query && (
                <button
                  onClick={() => { setQuery(''); setResults([]); }}
                  style={{ background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer' }}
                  aria-label="Clear search"
                >
                  <X size={16} />
                </button>
              )}
            </div>
            {open && results.length > 0 && (
              <div
                style={{
                  marginTop: 8,
                  background: 'var(--surface-modal)',
                  border: '1px solid var(--edge-2)',
                  borderRadius: 12,
                  padding: 6,
                  maxHeight: 320,
                  overflowY: 'auto',
                }}
              >
                {results.map((r, i) => (
                  <button
                    key={r.symbol}
                    onClick={() => handleSelect(r.symbol)}
                    style={{
                      width: '100%',
                      display: 'grid',
                      gridTemplateColumns: '1fr auto',
                      gap: 8,
                      padding: '12px 10px',
                      borderRadius: 8,
                      background: i === selectedIdx ? 'rgba(79,140,255,0.14)' : 'transparent',
                      border: 'none',
                      color: 'var(--text-1)',
                      fontSize: 14,
                      textAlign: 'left',
                      cursor: 'pointer',
                    }}
                  >
                    <span style={{ color: 'var(--text-1)', fontWeight: 500 }}>{r.symbol}</span>
                    <span style={{ color: 'var(--text-3)', fontSize: 11 }}>{r.exchange || 'NSE'}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Mobile menu drawer — full-screen sheet listing every route */}
        {mobileMenuOpen && (
          <>
            <div
              onClick={() => setMobileMenuOpen(false)}
              style={{
                position: 'fixed', inset: 0, zIndex: 90,
                background: 'rgba(0,0,0,0.5)',
                backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)',
              }}
            />
            <aside
              style={{
                position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 91,
                width: 'min(85vw, 320px)',
                background: 'var(--surface-modal, rgba(20,26,64,0.98))',
                borderRight: '1px solid var(--edge-1)',
                display: 'flex', flexDirection: 'column',
                paddingTop: 'env(safe-area-inset-top, 0px)',
                paddingBottom: 'env(safe-area-inset-bottom, 0px)',
                overflowY: 'auto',
              }}
            >
              <div
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '14px 16px',
                  borderBottom: '1px solid var(--edge-1)',
                }}
              >
                <BrandLogo to="/dashboard" size={24} wordSize={15} onClick={() => setMobileMenuOpen(false)} />
                <button
                  type="button"
                  aria-label="Close menu"
                  onClick={() => setMobileMenuOpen(false)}
                  style={{
                    width: 40, height: 40,
                    display: 'grid', placeItems: 'center',
                    background: 'transparent', border: 'none',
                    color: 'var(--text-2)', cursor: 'pointer',
                  }}
                >
                  <X size={20} />
                </button>
              </div>
              <nav style={{ padding: 8, display: 'flex', flexDirection: 'column', gap: 2 }}>
                {PRIMARY_TABS.map((t) => {
                  const active = isActive(t.to);
                  const Icon = t.icon;
                  return (
                    <Link
                      key={t.to}
                      to={t.to}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '12px 14px',
                        borderRadius: 10,
                        fontSize: 14,
                        fontWeight: active ? 600 : 500,
                        textDecoration: 'none',
                        background: active ? 'rgba(79,140,255,0.18)' : 'transparent',
                        color: active ? 'var(--text-1)' : 'var(--text-2)',
                        minHeight: 44,
                      }}
                    >
                      <Icon size={18} />
                      {t.label}
                    </Link>
                  );
                })}
              </nav>
            </aside>
          </>
        )}
      </>
    );
  }

  return (
    <header
      className="nq-topbar"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        height: 64,
        display: 'grid',
        gridTemplateColumns: 'auto auto 1fr auto auto auto',
        alignItems: 'center',
        gap: 14,
        padding: '0 20px',
        background: 'rgba(10, 14, 34, 0.55)',
        backdropFilter: 'blur(28px) saturate(160%)',
        WebkitBackdropFilter: 'blur(28px) saturate(160%)',
        borderBottom: '1px solid var(--edge-1)',
      }}
    >
      {/* Logo lockup */}
      <BrandLogo to="/dashboard" size={30} wordSize={16} />

      {/* Primary pill tabs */}
      <nav
        className="scrollbar-hide"
        style={{
          display: 'inline-flex',
          gap: 2,
          padding: 4,
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid var(--edge-1)',
          borderRadius: 999,
          overflowX: 'auto',
          maxWidth: '100%',
        }}
      >
        {PRIMARY_TABS.map((t) => {
          const active = isActive(t.to);
          const Icon = t.icon;
          return (
            <Link
              key={t.to}
              to={t.to}
              className="nq-tab"
              style={{
                padding: '6px 14px',
                height: 30,
                borderRadius: 999,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                fontFamily: 'var(--font-sans)',
                fontSize: 12.5,
                fontWeight: 500,
                textDecoration: 'none',
                background: active ? 'rgba(79,140,255,0.18)' : 'transparent',
                color: active ? 'var(--text-1)' : 'var(--text-3)',
                boxShadow: active
                  ? '0 4px 12px rgba(79,140,255,0.18), inset 0 0 0 1px rgba(79,140,255,0.36)'
                  : 'none',
                transition: 'all 200ms',
              }}
            >
              <Icon size={13} />
              {t.label}
            </Link>
          );
        })}
      </nav>

      {/* Live index ticker — inline in the bar (prototype layout). min-width:0
          lets the marquee shrink into the flexible column instead of blowing
          out the grid. */}
      <div style={{ minWidth: 0, overflow: 'hidden' }}>
        <HeaderTicker />
      </div>

      {/* Kite integration status — connect / live / disconnect. Global stock
          search lives in the watchlist rail (top-bar search removed). */}
      <KiteChip />

      {/* Notifications — placeholder until in-app inbox lands. Bell currently
          surfaces the Kite session status (the only ambient signal) and
          points users at the live signal scan time. */}
      <button
        title="Notifications"
        type="button"
        onClick={() => {
          const scanLabel = '16:15 IST every weekday';
          if (kite?.connected) {
            toast.info(`Kite connected · ${kite.userId || 'session live'}`, {
              description: `Next signal scan: ${scanLabel}. Inbox view ships with v3.`,
            });
          } else {
            toast.warning('Kite session disconnected', {
              description: 'Reconnect from the user menu to place orders. Daily expiry: 6 AM IST.',
              action: { label: 'Reconnect', onClick: () => kite?.connect?.() },
            });
          }
        }}
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid var(--edge-1)',
          color: 'var(--text-2)',
          display: 'grid',
          placeItems: 'center',
          cursor: 'pointer',
          position: 'relative',
          transition: 'all 200ms',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(79,140,255,0.18)';
          e.currentTarget.style.borderColor = 'rgba(79,140,255,0.36)';
          e.currentTarget.style.color = 'var(--text-1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
          e.currentTarget.style.borderColor = 'var(--edge-1)';
          e.currentTarget.style.color = 'var(--text-2)';
        }}
      >
        <Bell size={16} />
        {kite?.connected && (
          <span
            style={{
              position: 'absolute',
              top: 7,
              right: 7,
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: 'var(--bull)',
              border: '2px solid #07091c',
            }}
          />
        )}
      </button>

      {/* User pill / Kite status */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              padding: '4px 14px 4px 4px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--edge-1)',
              borderRadius: 999,
              color: 'var(--text-1)',
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
              transition: 'all 200ms',
            }}
          >
            <span
              style={{
                width: 30,
                height: 30,
                borderRadius: '50%',
                background: 'var(--brand-grad)',
                display: 'grid',
                placeItems: 'center',
                color: '#fff',
              }}
            >
              <User size={14} />
            </span>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontSize: 13, color: 'var(--text-1)', fontWeight: 500, lineHeight: 1.1 }}>
                {user?.name?.split(' ')[0] || 'You'}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 2 }}>
                {isAdmin ? 'Admin' : 'Member'} · Pro
              </div>
            </div>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" sideOffset={8} className="min-w-[200px]">
          <DropdownMenuLabel className="font-normal">
            <div style={{ fontSize: 13, color: 'var(--text-1)' }}>{user?.name || 'You'}</div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>{user?.email}</div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {!kite?.connected ? (
            <DropdownMenuItem onSelect={() => kite?.connect?.()} className="gap-2 cursor-pointer">
              {kite?.connecting ? <Loader2 size={14} className="animate-spin" /> : <Plug size={14} />}
              Connect Kite
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onSelect={() => kite?.disconnect?.()} className="gap-2 cursor-pointer">
              <Plug size={14} />
              Kite · {kite.userId}
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          {ACCOUNT_LINKS.map((l) => {
            const LIcon = l.icon;
            return (
              <DropdownMenuItem key={l.to} onSelect={() => navigate(l.to)} className="gap-2 cursor-pointer">
                <LIcon size={14} />
                {l.label}
              </DropdownMenuItem>
            );
          })}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => navigate('/settings')} className="gap-2 cursor-pointer">
            <SettingsIcon size={14} />
            Settings
          </DropdownMenuItem>
          {isAdmin && (
            <DropdownMenuItem onSelect={() => navigate('/admin')} className="gap-2 cursor-pointer">
              <Shield size={14} />
              Admin console
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          {scaleRow}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => logout()} className="gap-2 cursor-pointer">
            <LogOut size={14} />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}

export default TopBar;
