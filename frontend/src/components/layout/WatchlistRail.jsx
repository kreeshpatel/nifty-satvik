import React, { useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KiteContext } from '@/App';
import { searchStocks } from '@/services/kiteStock';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { useKiteQuote } from '@/hooks/queries/useKiteQuote';
import { useSignals } from '@/hooks/queries/useSignals';
import {
  useUserWatchlist, useAddToWatchlist, useRemoveFromWatchlist, useReorderWatchlist,
} from '@/hooks/queries/useUserWatchlist';
import StockLogo from '@/components/shared/StockLogo';
import TradeCardModal from '@/components/shared/TradeCardModal';
import '@/styles/watchlist-rail.css';

/**
 * WatchlistRail — the per-user left rail (collapsible, global, hidden on mobile).
 * Membership from useUserWatchlist; live prices from the shared useQuoteBatch.
 * Hover actions navigate into the real StockDetail page (which already has the
 * chart, top-5 depth, and the Buy/Sell order pad via ?action=).
 */
const COLLAPSE_KEY = 'nq_rail_collapsed';
const LIST_KEY = 'nq_rail_list';
const VIEW_KEY = 'nq_rail_view';
// 'held' (Kite holdings) removed 2026-07-13 — research-only product; users track holdings on their broker.
const VIEWS = ['watchlist', 'signals'];

const fmtPrice = (n) =>
  n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const bookmarkSvg = <svg viewBox="0 0 24 24"><path d="M6 3h12a1 1 0 011 1v17l-7-4-7 4V4a1 1 0 011-1z" /></svg>;

function arrayMove(arr, from, to) {
  const a = arr.slice();
  const [it] = a.splice(from, 1);
  a.splice(to, 0, it);
  return a;
}

// Inline top-5 market depth, mounted only while a row is expanded (so the
// 3s useKiteQuote poll runs for at most one symbol at a time). Uses the
// shared owner-Kite quote — works regardless of the user's own Kite link.
function RailDepth({ sym }) {
  const { data } = useKiteQuote(sym);
  const buy = Array.isArray(data?.depth?.buy) ? data.depth.buy.slice(0, 5) : [];
  const sell = Array.isArray(data?.depth?.sell) ? data.depth.sell.slice(0, 5) : [];
  if (!buy.length && !sell.length) {
    return <div className="wlr-depth"><div className="wlr-depth-empty">Depth unavailable</div></div>;
  }
  return (
    <div className="wlr-depth">
      <div className="wlr-depth-h"><span>Qty</span><span>Bid</span><span>Ask</span><span>Qty</span></div>
      {[0, 1, 2, 3, 4].map((i) => {
        const b = buy[i]; const s = sell[i];
        return (
          <div className="wlr-depth-r" key={i}>
            <span className="q">{b ? b.quantity.toLocaleString('en-IN') : ''}</span>
            <span className="bp tnum">{b ? fmtPrice(b.price) : ''}</span>
            <span className="sp tnum">{s ? fmtPrice(s.price) : ''}</span>
            <span className="q r">{s ? s.quantity.toLocaleString('en-IN') : ''}</span>
          </div>
        );
      })}
    </div>
  );
}

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

  // Two independent lists: 1 = seeded core (never blank on first look),
  // 2 = the user's own blank list. Remembered across mounts.
  const [activeList, setActiveList] = useState(() => {
    try { return localStorage.getItem(LIST_KEY) === '2' ? 2 : 1; } catch { return 1; }
  });
  const selectList = (n) => {
    setActiveList(n);
    try { localStorage.setItem(LIST_KEY, String(n)); } catch {}
  };

  // Top-level rail view: your Watchlist, the model's Signals, or your Held
  // positions (prototype's Watchlist · Signals · Held tabs).
  const [view, setView] = useState(() => {
    try { const v = localStorage.getItem(VIEW_KEY); return VIEWS.includes(v) ? v : 'watchlist'; } catch { return 'watchlist'; }
  });
  const selectView = (v) => {
    setView(v);
    try { localStorage.setItem(VIEW_KEY, v); } catch {}
  };

  const wlQuery = useUserWatchlist(activeList);
  const tickers = wlQuery.data ?? [];
  const add = useAddToWatchlist(activeList);
  const remove = useRemoveFromWatchlist(activeList);

  const quotesQuery = useQuoteBatch(tickers, { enabled: tickers.length > 0 });
  const quotes = quotesQuery.data ?? {};

  // ── model context: flag watched names that are held or have a live signal ──
  const kite = useContext(KiteContext);
  const signalsQuery = useSignals();
  // No per-user broker holdings (ADR 0011) — the rail no longer badges held names from Kite.
  const holdingsQuery = { data: [] };

  const heldSet = useMemo(() => {
    const s = new Set();
    (holdingsQuery.data ?? []).forEach((h) => {
      const t = (h.tradingsymbol || '').toUpperCase();
      if (t) s.add(t);
    });
    return s;
  }, [holdingsQuery.data]);

  const signalSet = useMemo(() => {
    const s = new Set();
    (signalsQuery.data?.signals ?? []).forEach((sg) => {
      const t = (sg.ticker || sg.symbol || sg.sym || '').toUpperCase();
      if (t) s.add(t);
    });
    return s;
  }, [signalsQuery.data]);

  const flagFor = (sym) => {
    if (heldSet.has(sym)) return { color: 'var(--bull)', label: 'held' };
    if (signalSet.has(sym)) return { color: 'var(--info)', label: 'signal' };
    return { color: null, label: 'NSE' };
  };

  // Rows for the Signals + Held views (read-only lists, wired to real data).
  const signalRows = useMemo(() => (signalsQuery.data?.signals ?? [])
    .map((s) => ({
      ...s,
      sym: (s.ticker || s.symbol || s.sym || '').toUpperCase(),
      reco: s.entry ?? s.reco_price ?? null,
      grade: (s.grade || 'B')[0].toUpperCase(),
    }))
    .filter((r) => r.sym), [signalsQuery.data]);

  // ── inline depth (one row at a time) ────────────────────────────
  const [expanded, setExpanded] = useState(null);
  const [tradeCard, setTradeCard] = useState(null);

  // ── drag-to-reorder (native HTML5 DnD; no library) ──────────────
  const reorder = useReorderWatchlist(activeList);
  const [localOrder, setLocalOrder] = useState(tickers);
  const tickersKey = tickers.join(',');
  useEffect(() => {
    setLocalOrder(tickers);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickersKey]);
  const orderRef = useRef(localOrder);
  orderRef.current = localOrder;
  const dragIdx = useRef(null);
  const dragged = useRef(false);
  const onDragStart = (i) => (e) => {
    dragIdx.current = i; dragged.current = false;
    try { e.dataTransfer.effectAllowed = 'move'; } catch {}
  };
  const onDragEnter = (i) => () => {
    const from = dragIdx.current;
    if (from == null || from === i) return;
    dragged.current = true;
    setLocalOrder((o) => arrayMove(o, from, i));
    dragIdx.current = i;
  };
  const onDragEnd = () => {
    if (dragged.current) reorder.mutate(orderRef.current);
    dragIdx.current = null; dragged.current = false;
  };

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
    <>
    <aside className="wlr" aria-label="Watchlist">
      <div className="wlr-head">
        <div className="wlr-viewtabs" role="tablist" aria-label="Rail views">
          {[['watchlist', 'Watchlist'], ['signals', 'Signals']].map(([k, lbl]) => (
            <button
              key={k}
              role="tab"
              aria-selected={view === k}
              className={`wlr-vtab${view === k ? ' on' : ''}`}
              onClick={() => selectView(k)}
            >
              {lbl}
            </button>
          ))}
        </div>
        <button className="wlr-collapse" onClick={toggle} title="Collapse" aria-label="Collapse watchlist">«</button>
      </div>

      {/* ── SIGNALS view — the model's current signal stocks (read-only) ── */}
      {view === 'signals' && (
        <div className="wlr-list">
          {signalsQuery.isLoading ? (
            <div className="wlr-empty">Loading…</div>
          ) : signalRows.length === 0 ? (
            <div className="wlr-empty">No signals right now.<span>The scan posts fresh calls at 4:15 PM IST.</span></div>
          ) : signalRows.map((r) => (
            <div className="wlr-row" key={r.sym} onClick={() => setTradeCard(r)}>
              <StockLogo sym={r.sym} size={27} mono />
              <div className="wlr-l">
                <div className="wlr-s">{r.sym}<span className="wlr-flag" style={{ background: 'var(--info)' }} /></div>
                <div className="wlr-e">signal · {r.grade}</div>
              </div>
              <div className="wlr-r">
                <div className="wlr-p tnum">{fmtPrice(r.reco)}</div>
                <div className="wlr-c" style={{ color: 'var(--text-3)' }}>reco</div>
              </div>
              <div className="wlr-actions" onClick={(e) => e.stopPropagation()}>
                <button className={`wlr-bm${inWatch(r.sym) ? ' on' : ''}`} title={inWatch(r.sym) ? 'In watchlist' : 'Add to watchlist'}
                  onClick={() => (inWatch(r.sym) ? remove.mutate(r.sym) : add.mutate(r.sym))}>{bookmarkSvg}</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {view === 'watchlist' && (<>
      <div className="wlr-tabs" role="tablist" aria-label="Watchlists">
        {[1, 2].map((n) => (
          <button
            key={n}
            role="tab"
            aria-selected={activeList === n}
            aria-label={`Watchlist ${n}`}
            className={`wlr-tab${activeList === n ? ' on' : ''}`}
            onClick={() => selectList(n)}
          >
            {n}
          </button>
        ))}
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
                <StockLogo sym={r.symbol} size={26} mono />
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
            This list is empty.
            <span>Search above to add stocks you want to track.</span>
          </div>
        ) : localOrder.map((sym, i) => {
          const qd = quotes[sym] || {};
          const chg = qd.change_pct;
          const pos = (chg ?? 0) >= 0;
          const flag = flagFor(sym);
          return (
            <React.Fragment key={sym}>
              <div
                className="wlr-row"
                draggable
                onClick={() => { if (dragged.current) return; openStock(sym); }}
                onDragStart={onDragStart(i)}
                onDragEnter={onDragEnter(i)}
                onDragOver={(e) => e.preventDefault()}
                onDragEnd={onDragEnd}
              >
                <StockLogo sym={sym} size={27} mono />
                <div className="wlr-l">
                  <div className="wlr-s">
                    {sym}
                    {flag.color && <span className="wlr-flag" style={{ background: flag.color }} />}
                  </div>
                  <div className="wlr-e">{flag.label}</div>
                </div>
                <div className="wlr-r">
                  <div className="wlr-p tnum">{fmtPrice(qd.last_price)}</div>
                  <div className={`wlr-c tnum ${pos ? 'num-bull' : 'num-bear'}`}>
                    {chg == null ? '—' : (pos ? '+' : '−') + Math.abs(chg).toFixed(2) + '%'}
                  </div>
                </div>
                <div className="wlr-actions" onClick={(e) => e.stopPropagation()}>
                  <button
                    className={`wla${expanded === sym ? ' on' : ''}`}
                    title="Market depth"
                    onClick={() => setExpanded((x) => (x === sym ? null : sym))}
                  >
                    <svg viewBox="0 0 24 24"><path d="M3 6h14M3 10h9M3 14h16M3 18h7" /></svg>
                  </button>
                  <button className="wla" title="Open chart" onClick={() => openStock(sym)}>
                    <svg viewBox="0 0 24 24"><path d="M3 17l5-5 4 3 6-7" /><path d="M3 21h18" /></svg>
                  </button>
                  <button className="wla" title="Remove from watchlist" onClick={() => remove.mutate(sym)}>
                    <svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13" /></svg>
                  </button>
                </div>
              </div>
              {expanded === sym && <RailDepth sym={sym} />}
            </React.Fragment>
          );
        })}
      </div>
      </>)}
    </aside>
    <TradeCardModal sig={tradeCard} open={!!tradeCard} onOpenChange={(o) => !o && setTradeCard(null)} />
    </>
  );
}
