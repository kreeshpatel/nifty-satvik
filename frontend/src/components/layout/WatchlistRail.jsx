import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { searchStocks } from '@/services/kiteStock';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import {
  useUserWatchlist, useAddToWatchlist, useRemoveFromWatchlist,
} from '@/hooks/queries/useUserWatchlist';
import StockLogo from '@/components/shared/StockLogo';
import '@/styles/watchlist-rail.css';

/**
 * WatchlistRail — the per-user left rail (collapsible, global, hidden on mobile).
 * Membership from useUserWatchlist; live prices from the shared useQuoteBatch.
 * Hover actions navigate into the real StockDetail page (which already has the
 * chart, top-5 depth, and the Buy/Sell order pad via ?action=).
 */
const COLLAPSE_KEY = 'nq_rail_collapsed';

const fmtPrice = (n) =>
  n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const bookmarkSvg = <svg viewBox="0 0 24 24"><path d="M6 3h12a1 1 0 011 1v17l-7-4-7 4V4a1 1 0 011-1z" /></svg>;

export default function WatchlistRail() {
  const navigate = useNavigate();

  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(COLLAPSE_KEY) === '1'; } catch { return false; }
  });
  const toggle = () => setCollapsed((c) => {
    const n = !c;
    try { localStorage.setItem(COLLAPSE_KEY, n ? '1' : '0'); } catch {}
    return n;
  });

  const wlQuery = useUserWatchlist();
  const tickers = wlQuery.data ?? [];
  const add = useAddToWatchlist();
  const remove = useRemoveFromWatchlist();

  const quotesQuery = useQuoteBatch(tickers, { enabled: tickers.length > 0 });
  const quotes = quotesQuery.data ?? {};

  // ── search (debounced) ──────────────────────────────────────────
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const seq = useRef(0);
  useEffect(() => {
    const query = q.trim();
    if (!query) { setResults([]); return; }
    const my = ++seq.current;
    const t = setTimeout(async () => {
      try {
        const r = await searchStocks(query, 8);
        if (seq.current === my) setResults(Array.isArray(r) ? r : []);
      } catch {
        if (seq.current === my) setResults([]);
      }
    }, 180);
    return () => clearTimeout(t);
  }, [q]);

  const inWatch = (sym) => tickers.includes((sym || '').toUpperCase());
  const openStock = (sym, suffix = '') => navigate(`/stock/${encodeURIComponent(sym)}${suffix}`);

  if (collapsed) {
    return (
      <aside className="wlr wlr-collapsed">
        <button className="wlr-expand" onClick={toggle} title="Show watchlist" aria-label="Show watchlist">»</button>
      </aside>
    );
  }

  return (
    <aside className="wlr" aria-label="Watchlist">
      <div className="wlr-head">
        <span className="wlr-title">Watchlist</span>
        <button className="wlr-collapse" onClick={toggle} title="Collapse" aria-label="Collapse watchlist">«</button>
      </div>

      <div className="wlr-searchwrap">
        <div className="wlr-search">
          <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></svg>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search & add NSE equity…"
            aria-label="Search stocks"
            autoComplete="off"
          />
          {q && <button className="wlr-clear" onClick={() => setQ('')} aria-label="Clear search">✕</button>}
        </div>
        {q && (
          <div className="wlr-results">
            {results.length === 0 ? (
              <div className="wlr-empty-sm">No match for “{q}”</div>
            ) : results.map((r) => (
              <div key={r.symbol} className="wlr-sr" onClick={() => { openStock(r.symbol); setQ(''); }}>
                <StockLogo sym={r.symbol} size={26} />
                <div className="wlr-sr-l">
                  <div className="wlr-sr-s">{r.symbol}</div>
                  <div className="wlr-sr-e">{(r.exchange || 'NSE')} · {r.name}</div>
                </div>
                <button
                  className={`wlr-bm${inWatch(r.symbol) ? ' on' : ''}`}
                  title={inWatch(r.symbol) ? 'In watchlist' : 'Add to watchlist'}
                  onClick={(e) => { e.stopPropagation(); inWatch(r.symbol) ? remove.mutate(r.symbol) : add.mutate(r.symbol); }}
                >
                  {bookmarkSvg}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="wlr-list">
        {wlQuery.isLoading ? (
          <div className="wlr-empty">Loading…</div>
        ) : tickers.length === 0 ? (
          <div className="wlr-empty">
            Your watchlist is empty.
            <span>Search above to add stocks you want to track.</span>
          </div>
        ) : tickers.map((sym) => {
          const qd = quotes[sym] || {};
          const chg = qd.change_pct;
          const pos = (chg ?? 0) >= 0;
          return (
            <div key={sym} className="wlr-row" onClick={() => openStock(sym)}>
              <StockLogo sym={sym} size={27} />
              <div className="wlr-l">
                <div className="wlr-s">{sym}</div>
                <div className="wlr-e">NSE</div>
              </div>
              <div className="wlr-r">
                <div className="wlr-p tnum">{fmtPrice(qd.last_price)}</div>
                <div className={`wlr-c tnum ${pos ? 'num-bull' : 'num-bear'}`}>
                  {chg == null ? '—' : (pos ? '+' : '−') + Math.abs(chg).toFixed(2) + '%'}
                </div>
              </div>
              <div className="wlr-actions" onClick={(e) => e.stopPropagation()}>
                <button className="wla b" title="Buy" onClick={() => openStock(sym, '?action=buy')}>B</button>
                <button className="wla s" title="Sell" onClick={() => openStock(sym, '?action=sell')}>S</button>
                <button className="wla" title="Chart & depth" onClick={() => openStock(sym)}>
                  <svg viewBox="0 0 24 24"><path d="M3 17l5-5 4 3 6-7" /><path d="M3 21h18" /></svg>
                </button>
                <button className="wla" title="Remove from watchlist" onClick={() => remove.mutate(sym)}>
                  <svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13" /></svg>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
