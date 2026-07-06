import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { Search, ArrowRight, Hash } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * CommandBar — Linear-style ⌘K trading palette.
 *
 * Opens on ⌘K / Ctrl-K / `/` anywhere in the app (global keybinding
 * registered here). Fuzzy-searches across three item categories:
 *   1. Actions  — commands with side effects ("Run scan", "Refresh")
 *   2. Pages    — route navigation ("Signals", "Backtest", "Settings")
 *   3. Tickers  — live quick-jump to /stock/:symbol
 *
 * The fuzzy match is intentionally simple: substring-hit scoring with
 * a bonus for prefix matches. This keeps ms latency <10 on 500-ticker
 * lists without shipping fuse.js (+12kb).
 *
 * Natural-language shortcuts (poor-man's parser):
 *   "buy reliance 10"  → prefills OrderPad for RELIANCE, qty 10
 *   "sell infy half"   → prefills OrderPad SELL for INFY (qty=half holding)
 *   "backtest 2023"    → /backtest with year filter
 *
 * Higher-fidelity NLP is Phase 6+. For now we dispatch registered actions.
 *
 * Props
 * -----
 * open, onOpenChange  — Radix Dialog control
 * tickers             — [{ symbol, price?, change? }] universe
 * actions             — [{ id, title, subtitle?, keywords?, shortcut?, run: fn }]
 * pages               — [{ id, title, subtitle?, path, icon?, keywords? }]
 * onPlaceOrder        — optional hook receiving parsed { ticker, side, qtyHint }
 */
const DEFAULT_PAGES = [
  { id: 'dashboard',  title: 'Dashboard',       path: '/dashboard',    keywords: 'home overview' },
  { id: 'signals',    title: 'Signals',         path: '/premove',      keywords: 'trade fresh premove today' },
  { id: 'portfolio',  title: 'Portfolio',       path: '/portfolio',    keywords: 'holdings positions' },
  { id: 'orders',     title: 'Orders',          path: '/orders',       keywords: 'executions open' },
  { id: 'funds',      title: 'Funds',           path: '/funds',        keywords: 'margin cash' },
  { id: 'analytics',  title: 'Analytics',       path: '/pnl',          keywords: 'pnl performance' },
  { id: 'journal',    title: 'Journal',         path: '/journal',      keywords: 'trade diary notes' },
  { id: 'backtest',   title: 'Backtest',        path: '/backtest',     keywords: 'track record history' },
  { id: 'accounting', title: 'Accounting',      path: '/accounting',   keywords: 'tax p&l fy' },
  { id: 'settings',   title: 'Settings',        path: '/settings',     keywords: 'profile broker kite' },
];

function scoreMatch(query, haystack) {
  if (!query) return 1;
  const q = query.toLowerCase();
  const h = (haystack || '').toLowerCase();
  if (h.startsWith(q)) return 3;
  if (h.includes(q)) return 2;
  // Simple subsequence score
  let idx = 0;
  for (const ch of q) {
    const found = h.indexOf(ch, idx);
    if (found === -1) return 0;
    idx = found + 1;
  }
  return 1;
}

// Parses "buy reliance 10" → { side:'BUY', ticker:'RELIANCE', qty:10 }
function parseTradeCommand(input) {
  const m = input.trim().match(/^(buy|sell)\s+([A-Za-z]+)(?:\s+(\d+|half|all))?$/i);
  if (!m) return null;
  const side = m[1].toUpperCase();
  const ticker = m[2].toUpperCase();
  const qtyPart = m[3]?.toLowerCase();
  let qty = null;
  if (qtyPart === 'half') qty = 'half';
  else if (qtyPart === 'all') qty = 'all';
  else if (qtyPart) qty = parseInt(qtyPart, 10);
  return { side, ticker, qty };
}

export function CommandBar({
  open,
  onOpenChange,
  tickers = [],
  actions = [],
  pages = DEFAULT_PAGES,
  onPlaceOrder,
}) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);

  // Register global ⌘K / Ctrl-K / "/" open.
  useEffect(() => {
    function onKey(e) {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onOpenChange?.(true);
      }
      // "/" only when not focused on input
      if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        onOpenChange?.(true);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onOpenChange]);

  // Reset query + focus when opening
  useEffect(() => {
    if (open) { setQuery(''); setSelected(0); }
  }, [open]);

  const results = useMemo(() => {
    const q = query.trim();
    const tradeCmd = parseTradeCommand(q);

    const items = [];

    // 1. Natural-language trade command (if matches shape)
    if (tradeCmd && onPlaceOrder) {
      items.push({
        kind: 'trade',
        id: `trade-${tradeCmd.ticker}`,
        title: `${tradeCmd.side} ${tradeCmd.ticker}${tradeCmd.qty ? ` × ${tradeCmd.qty}` : ''}`,
        subtitle: 'Opens order pad',
        run: () => onPlaceOrder(tradeCmd),
        score: 100,
      });
    }

    // 2. Actions
    for (const a of actions) {
      const hay = `${a.title} ${a.subtitle ?? ''} ${a.keywords ?? ''}`;
      const s = scoreMatch(q, hay);
      if (s > 0 || !q) items.push({ kind: 'action', ...a, score: s });
    }

    // 3. Pages
    for (const p of pages) {
      const hay = `${p.title} ${p.subtitle ?? ''} ${p.keywords ?? ''}`;
      const s = scoreMatch(q, hay);
      if (s > 0 || !q) items.push({ kind: 'page', ...p, score: s });
    }

    // 4. Tickers
    for (const t of tickers) {
      const s = scoreMatch(q, t.symbol);
      if (s > 0) items.push({ kind: 'ticker', ...t, score: s + 0.5 });
    }

    items.sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
    return items.slice(0, 40);
  }, [query, actions, pages, tickers, onPlaceOrder]);

  const runItem = useCallback((item) => {
    if (!item) return;
    if (item.kind === 'action') item.run?.();
    if (item.kind === 'page') navigate(item.path);
    if (item.kind === 'ticker') navigate(`/stock/${item.symbol}`);
    if (item.kind === 'trade') item.run?.();
    onOpenChange?.(false);
  }, [navigate, onOpenChange]);

  const handleKey = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected((i) => Math.min(results.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected((i) => Math.max(0, i - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      runItem(results[selected]);
    }
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50"
          style={{ background: 'oklch(0% 0 0 / 0.65)', backdropFilter: 'blur(4px)' }}
        />
        <DialogPrimitive.Content
          className="fixed z-50 flex flex-col"
          style={{
            top: '15vh',
            left: '50%',
            transform: 'translateX(-50%)',
            width: 'min(620px, calc(100vw - 32px))',
            maxHeight: '70vh',
            background: 'var(--surface-modal)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid var(--edge-2)',
            borderRadius: 'var(--r-panel)',
            boxShadow: 'var(--shadow-lg)',
            overflow: 'hidden',
          }}
          aria-label="Command palette"
          aria-describedby={undefined}
        >
          <DialogPrimitive.Title className="sr-only">Nifty Satvik Command</DialogPrimitive.Title>

          {/* INPUT */}
          <div
            className="flex items-center"
            style={{
              padding: '14px 20px',
              borderBottom: '1px solid var(--edge-1)',
              gap: 10,
            }}
          >
            <Search size={18} strokeWidth={1.75} style={{ color: 'var(--text-3)' }} />
            <input
              autoFocus
              placeholder="Buy RELIANCE 10 · go signals · TCS · run scan…"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setSelected(0); }}
              onKeyDown={handleKey}
              className="t-ui-body"
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--text-1)',
                fontFamily: 'var(--font-sans)',
                fontSize: 15,
                caretColor: 'var(--brand)',
              }}
            />
            <kbd
              className="t-num-small"
              style={{
                background: 'var(--surface-3)',
                border: '1px solid var(--edge-1)',
                borderRadius: 4,
                padding: '2px 6px',
                color: 'var(--text-3)',
                fontSize: 10,
              }}
            >
              ESC
            </kbd>
          </div>

          {/* RESULTS */}
          <div
            role="listbox"
            className="flex-1 overflow-y-auto"
            style={{ padding: 8 }}
          >
            {results.length === 0 ? (
              <div
                className="t-ui-body text-center"
                style={{ padding: 32, color: 'var(--text-3)' }}
              >
                No matches for "{query}"
              </div>
            ) : (
              results.map((item, i) => {
                const active = i === selected;
                const iconColor = item.kind === 'ticker'
                  ? 'var(--brand)'
                  : item.kind === 'trade'
                    ? 'var(--brand-hi)'
                    : 'var(--text-3)';
                return (
                  <button
                    key={`${item.kind}-${item.id ?? item.symbol}`}
                    type="button"
                    role="option"
                    aria-selected={active}
                    onClick={() => runItem(item)}
                    onMouseEnter={() => setSelected(i)}
                    className="flex items-center w-full text-left"
                    style={{
                      gap: 12,
                      padding: '10px 12px',
                      borderRadius: 'var(--r-chip)',
                      background: active ? 'var(--surface-2)' : 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'var(--text-1)',
                    }}
                  >
                    <div
                      className="flex items-center justify-center flex-shrink-0"
                      style={{
                        width: 28, height: 28,
                        borderRadius: 'var(--r-chip)',
                        background: 'var(--surface-3)',
                        border: '1px solid var(--edge-1)',
                        color: iconColor,
                      }}
                    >
                      {item.kind === 'ticker' ? (
                        <Hash size={14} strokeWidth={1.75} />
                      ) : item.icon ? (
                        React.cloneElement(item.icon, { size: 14, strokeWidth: 1.75 })
                      ) : (
                        <ArrowRight size={14} strokeWidth={1.75} />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="t-ui-subhead truncate" style={{ color: 'var(--text-1)' }}>
                        {item.kind === 'ticker' ? item.symbol : item.title}
                      </div>
                      {(item.subtitle || item.kind === 'page' || item.kind === 'ticker') && (
                        <div
                          className="t-ui-footnote truncate"
                          style={{ color: 'var(--text-3)', marginTop: 1 }}
                        >
                          {item.subtitle ??
                            (item.kind === 'page' ? `Go to ${item.path}` :
                             item.kind === 'ticker' ? `Open /stock/${item.symbol}` : '')}
                        </div>
                      )}
                    </div>
                    {item.shortcut && (
                      <kbd
                        className="t-num-small flex-shrink-0"
                        style={{
                          background: 'var(--surface-3)',
                          border: '1px solid var(--edge-1)',
                          borderRadius: 4,
                          padding: '2px 6px',
                          color: 'var(--text-3)',
                          fontSize: 10,
                        }}
                      >
                        {item.shortcut}
                      </kbd>
                    )}
                  </button>
                );
              })
            )}
          </div>

          {/* FOOTER shortcuts */}
          <footer
            className="flex items-center"
            style={{
              padding: '8px 16px',
              borderTop: '1px solid var(--edge-1)',
              background: 'var(--surface-2)',
              gap: 16,
              fontSize: 10,
              color: 'var(--text-3)',
            }}
          >
            <span>
              <kbd style={kbdStyle}>↑</kbd><kbd style={kbdStyle}>↓</kbd> navigate
            </span>
            <span>
              <kbd style={kbdStyle}>↵</kbd> select
            </span>
            <span>
              <kbd style={kbdStyle}>ESC</kbd> close
            </span>
          </footer>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

const kbdStyle = {
  background: 'var(--surface-3)',
  border: '1px solid var(--edge-1)',
  borderRadius: 3,
  padding: '1px 4px',
  marginRight: 4,
  fontFamily: 'var(--font-mono)',
  fontSize: 10,
  color: 'var(--text-2)',
};

export default CommandBar;
