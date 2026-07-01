import React, { useState, useEffect, useRef, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, Plus, Plug, Loader2, LogOut, X,
  Activity, Briefcase, ListChecks, BarChart3, Settings as SettingsIcon,
} from 'lucide-react';
import { searchStocks } from '@/services/kiteStock';
import { KiteContext } from '@/App';
import { AuthContext } from '@/context/AuthContext';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export const Header = () => {
  const navigate = useNavigate();
  const kite = useContext(KiteContext);
  const { user, logout } = useContext(AuthContext);
  const firstName = user?.name?.split(' ')[0] || 'there';
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const wrapperRef = useRef(null);
  const mobileInputRef = useRef(null);

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
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Auto-focus mobile search input when opened
  useEffect(() => {
    if (mobileSearchOpen && mobileInputRef.current) {
      mobileInputRef.current.focus();
    }
  }, [mobileSearchOpen]);

  const handleSelect = (symbol) => {
    setQuery(''); setOpen(false); setResults([]);
    setMobileSearchOpen(false);
    navigate(`/stock/${symbol}`);
  };

  const handleKeyDown = (e) => {
    if (!open || !results.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, results.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); handleSelect(results[selectedIdx].symbol); }
    else if (e.key === 'Escape') { setOpen(false); setMobileSearchOpen(false); }
  };

  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  const dateStr = now.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });

  return (
    <header
      className="mb-4"
      style={{
        paddingTop: 'env(safe-area-inset-top)',
        paddingLeft: 'env(safe-area-inset-left)',
        paddingRight: 'env(safe-area-inset-right)',
      }}
    >
      {/* Single compact row: branding left, actions right */}
      <div className="flex items-center justify-between gap-2 sm:gap-4">
        {/* Left: label + greeting + market info */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <h1 className="font-heading font-bold text-base sm:text-lg tracking-tight text-white truncate">Hi {firstName}</h1>
          <span className="w-px h-3 bg-white/[0.08] shrink-0 hidden md:block" />
          <span className="text-[11px] text-nq-text-muted hidden md:block shrink-0">{dateStr}</span>
          <span className="font-mono text-[11px] text-nq-text-muted tabular-nums hidden md:block shrink-0">{timeStr}</span>
          <span className="w-px h-3 bg-white/[0.08] shrink-0 hidden lg:block" />
          <span className="flex items-center gap-1.5 text-[10px] font-mono text-nq-emerald shrink-0 hidden lg:flex">
            <span className="w-1.5 h-1.5 rounded-full bg-nq-emerald animate-pulse" />
            MARKET OPEN
          </span>
        </div>

        {/* Right: search + actions */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Mobile Search Button */}
          <button
            onClick={() => setMobileSearchOpen(true)}
            className="flex md:hidden h-8 w-8 items-center justify-center rounded-lg bg-white/[0.04] border border-white/[0.08] transition-colors hover:bg-white/[0.08]"
          >
            <Search className="h-3.5 w-3.5 text-nq-text-muted" />
          </button>

          {/* Desktop Search — V2 styling, header-only refresh (locked 2026-04-27).
              Visual changes vs the legacy glass-card / blue-chip design:
                - input uses --surface-3 + --edge-1 hairline (no glass-thin)
                - dropdown is --surface-1 with --edge-1 border + --shadow-lg
                - active row gets --brand-soft + brand-edge ring (was rgba white)
                - exchange chip uses --surface-3 + --text-3 (was iOS blue)
                - widened to 320px so company names don't truncate as aggressively
                - dropped the surrounding quotes on company names */}
          <div className="relative hidden md:block" ref={wrapperRef}>
            <Search
              size={14}
              strokeWidth={1.75}
              style={{
                position: 'absolute',
                left: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-3)',
                pointerEvents: 'none',
              }}
            />
            <input
              type="text"
              placeholder="Search stocks…"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
              onFocus={() => query.length > 0 && setOpen(true)}
              onKeyDown={handleKeyDown}
              className="t-ui-callout"
              style={{
                height: 32,
                width: 200,
                paddingLeft: 30,
                paddingRight: 12,
                background: 'var(--surface-3)',
                color: 'var(--text-1)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
                outline: 'none',
                fontFamily: 'var(--font-sans)',
                fontSize: 13,
              }}
            />

            {/* Results dropdown */}
            {open && results.length > 0 && (
              <div
                role="listbox"
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  left: 0,
                  width: 320,
                  zIndex: 50,
                  background: 'var(--surface-1)',
                  border: '1px solid var(--edge-1)',
                  borderRadius: 'var(--r-card)',
                  boxShadow: 'var(--shadow-lg)',
                  padding: 4,
                }}
              >
                {results.map((stock, i) => {
                  const active = i === selectedIdx;
                  return (
                    <button
                      key={stock.symbol}
                      type="button"
                      role="option"
                      aria-selected={active}
                      onClick={() => handleSelect(stock.symbol)}
                      onMouseEnter={() => setSelectedIdx(i)}
                      style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 10,
                        padding: '8px 10px',
                        textAlign: 'left',
                        background: active ? 'var(--brand-soft)' : 'transparent',
                        border: `1px solid ${active ? 'var(--brand-edge)' : 'transparent'}`,
                        borderRadius: 'var(--r-chip)',
                        cursor: 'pointer',
                        transition: 'background var(--dur-hover) var(--ease-out-cubic)',
                      }}
                    >
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div
                          className="t-ui-subhead"
                          style={{ color: 'var(--text-1)', lineHeight: 1.2 }}
                        >
                          {stock.symbol}
                        </div>
                        {stock.name && (
                          <div
                            className="t-ui-footnote truncate"
                            style={{ color: 'var(--text-3)', marginTop: 2 }}
                          >
                            {stock.name}
                          </div>
                        )}
                      </div>
                      <span
                        className="t-num-small"
                        style={{
                          flexShrink: 0,
                          padding: '2px 7px',
                          background: 'var(--surface-3)',
                          color: 'var(--text-3)',
                          border: '1px solid var(--edge-1)',
                          borderRadius: 'var(--r-chip)',
                          fontSize: 10,
                          letterSpacing: '0.04em',
                        }}
                      >
                        {stock.exchange}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Empty state — same shell, friendlier copy */}
            {open && query.length > 0 && results.length === 0 && (
              <div
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  left: 0,
                  width: 320,
                  zIndex: 50,
                  background: 'var(--surface-1)',
                  border: '1px solid var(--edge-1)',
                  borderRadius: 'var(--r-card)',
                  boxShadow: 'var(--shadow-lg)',
                  padding: '14px 16px',
                  textAlign: 'center',
                }}
              >
                <p
                  className="t-ui-body"
                  style={{ color: 'var(--text-2)', margin: 0 }}
                >
                  No matches for "{query}"
                </p>
                <p
                  className="t-ui-footnote"
                  style={{ color: 'var(--text-3)', margin: '4px 0 0' }}
                >
                  Try the full ticker or company name.
                </p>
              </div>
            )}
          </div>

          {/* Kite */}
          {kite.connected ? (
            <div className="hidden sm:flex items-center gap-1.5 h-8 px-2.5 rounded-lg"
              style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <span className="h-1.5 w-1.5 rounded-full bg-nq-emerald" />
              <span className="text-[10px] font-mono tracking-wide text-nq-emerald">
                Kite {kite.userId ? `(${kite.userId})` : ''}
              </span>
              <button onClick={kite.disconnect} className="ml-0.5 p-0.5 rounded text-nq-text-muted hover:text-nq-red hover:bg-nq-red/10 transition-colors" title="Disconnect">
                <LogOut className="h-3 w-3" />
              </button>
            </div>
          ) : (
            <button onClick={kite.connect} disabled={kite.connecting}
              className="hidden sm:flex items-center gap-1.5 h-8 px-3 rounded-lg text-[10px] font-mono tracking-wide transition-colors"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444' }}>
              {kite.connecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plug className="h-3 w-3" />}
              {kite.connecting ? 'Connecting...' : 'Connect Kite'}
            </button>
          )}

          {/* Quick actions — navigation shortcuts to the most-used pages.
              Replaces the previous decorative "Take Action" button which
              had no onClick handler. */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="hidden sm:flex items-center gap-1.5 h-8 px-3.5 rounded-full text-xs font-medium text-white transition-all hover:-translate-y-0.5"
                style={{
                  background: 'var(--brand-grad)',
                  boxShadow: '0 4px 16px rgba(79, 140, 255, 0.25)',
                }}
              >
                Quick actions
                <Plus className="h-3 w-3" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[200px]">
              <DropdownMenuLabel>Jump to</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => navigate('/premove')}>
                <Activity className="h-4 w-4 mr-2" /> View Signals
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => navigate('/portfolio')}>
                <Briefcase className="h-4 w-4 mr-2" /> View Portfolio
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => navigate('/orders')}>
                <ListChecks className="h-4 w-4 mr-2" /> View Orders
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => navigate('/backtest')}>
                <BarChart3 className="h-4 w-4 mr-2" /> Run Backtest
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Avatar — opens dropdown with name/email + Settings + Logout. */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex h-8 w-8 items-center justify-center rounded-full text-[10px] font-semibold text-white shrink-0 transition-transform hover:scale-105"
                style={{
                  background: 'var(--brand-grad)',
                  boxShadow: '0 2px 8px rgba(79, 140, 255, 0.2)',
                }}
                aria-label="Account menu"
              >
                {firstName.charAt(0).toUpperCase()}{(user?.name?.split(' ')[1] || '').charAt(0).toUpperCase() || ''}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[220px]">
              <DropdownMenuLabel className="flex flex-col gap-0.5">
                <span className="text-xs font-semibold text-nq-text">{user?.name || 'Signed in'}</span>
                {user?.email && (
                  <span className="text-[10px] font-mono text-nq-text-muted truncate">{user.email}</span>
                )}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => navigate('/settings')}>
                <SettingsIcon className="h-4 w-4 mr-2" /> Settings
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={async () => {
                  try { await logout?.(); } finally { navigate('/login'); }
                }}
              >
                <LogOut className="h-4 w-4 mr-2" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* ─── Mobile Search Overlay ─── */}
      {mobileSearchOpen && (
        <div className="fixed inset-0 z-[60] md:hidden" style={{ background: 'rgba(6,6,10,0.97)' }}>
          <div className="flex items-center gap-3 px-4 pt-4 pb-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-nq-text-muted" />
              <input
                ref={mobileInputRef}
                type="text"
                placeholder="Search stocks..."
                value={query}
                onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
                onKeyDown={handleKeyDown}
                className="w-full h-10 pl-10 pr-4 text-sm text-white rounded-xl outline-none"
                style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
              />
            </div>
            <button
              onClick={() => { setMobileSearchOpen(false); setQuery(''); setResults([]); }}
              className="flex h-10 w-10 items-center justify-center rounded-xl shrink-0"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              <X className="h-4 w-4 text-nq-text-muted" />
            </button>
          </div>
          {/* Results */}
          <div className="px-4 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 80px)' }}>
            {results.map((stock, i) => (
              <button
                key={stock.symbol}
                onClick={() => handleSelect(stock.symbol)}
                className="w-full flex items-center justify-between px-3 py-3 text-left transition-colors rounded-xl mb-1"
                style={{ background: i === selectedIdx ? 'rgba(255,255,255,0.06)' : 'transparent' }}
              >
                <div>
                  <p className="text-sm font-semibold text-white">{stock.symbol}</p>
                  <p className="text-xs text-nq-text-muted truncate" style={{ maxWidth: 200 }}>{stock.name}</p>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(59, 130, 246,0.15)', color: '#BFDBFE' }}>
                  {stock.exchange}
                </span>
              </button>
            ))}
            {query.length > 0 && results.length === 0 && (
              <p className="text-sm text-nq-text-muted text-center py-8">No stocks found</p>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
