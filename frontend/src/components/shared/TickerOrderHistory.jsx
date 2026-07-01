/**
 * TickerOrderHistory — user's nq_orders rows for a single ticker.
 *
 * Why this matters on the stock detail page:
 *   "What's my track record on this name?" is a question every retail-pro
 *   trader asks before re-entering a position. Showing your last 5-10
 *   orders for THIS ticker — with side, qty, price, P&L if exited —
 *   surfaces patterns: did you get stopped out twice in a row? did you
 *   keep buying tops? are you familiar with this name's rhythm?
 *
 * Source: GET /api/nq-orders?ticker=RELIANCE — already supported by the
 * backend's existing nq_orders router.
 *
 * Renders a vertical list (not a table — too narrow). Each row:
 *   side dot · date · "BUY 35 @ ₹2,850" · status chip · P&L if matched
 *
 * Edge states:
 *   - Loading: 4 row skeletons
 *   - Empty (no orders for this ticker): muted "no history" message
 *   - Error: simple error text + retry hint
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useNQOrders } from '@/hooks/queries/useNQOrders';
import { StatusChip } from './StatusChip';
import { fmtPrice, fmtINR, fmtRelTime } from '@/lib/format';

export function TickerOrderHistory({ ticker, height = 320 }) {
  const symbol = (ticker || '').toUpperCase();
  // useNQOrders supports a ticker filter that maps to ?ticker=… on the
  // backend. Result is sorted server-side by placed_at desc.
  const ordersQuery = useNQOrders(symbol ? { ticker: symbol } : {}, {
    enabled: !!symbol,
  });

  const orders = ordersQuery.data ?? [];

  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        boxShadow: 'var(--shadow-sm)',
        height,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <header
        style={{
          padding: '12px 14px',
          borderBottom: '1px solid var(--edge-1)',
          flexShrink: 0,
        }}
      >
        <div className="flex items-center justify-between">
          <h3 className="t-ui-headline" style={{ margin: 0, color: 'var(--text-1)' }}>
            Your history
          </h3>
          {orders.length > 0 && (
            <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>
              {orders.length} order{orders.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 2 }}>
          {symbol ? `Trades you placed on ${symbol}` : 'Trades you placed via NiftyQuant'}
        </div>
      </header>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {ordersQuery.isLoading ? (
          <Skeleton />
        ) : ordersQuery.error ? (
          <Centered>
            <div className="t-ui-body" style={{ color: 'var(--text-2)' }}>Couldn't load history</div>
            <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 4 }}>
              {ordersQuery.error?.message || 'Try refreshing.'}
            </div>
          </Centered>
        ) : orders.length === 0 ? (
          <Centered>
            <div className="t-ui-body" style={{ color: 'var(--text-2)', textAlign: 'center' }}>
              No history on {symbol}
            </div>
            <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 6, textAlign: 'center', maxWidth: 220 }}>
              When you Buy or Sell {symbol} through NiftyQuant, your past orders will appear here.
            </div>
          </Centered>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {orders.slice(0, 12).map((o) => (
              <OrderRow key={o.id} order={o} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function OrderRow({ order }) {
  const isBuy = order.action === 'BUY';
  const fillPrice = order.fill_price ?? order.placed_price ?? 0;
  const status = String(order.status || '').toUpperCase();
  const tone =
    status === 'COMPLETE' ? 'bull'
    : status === 'REJECTED' || status === 'CANCELLED' ? 'bear'
    : 'muted';

  return (
    <li
      style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--edge-1)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}
    >
      {/* Side dot */}
      <span
        aria-hidden="true"
        style={{
          width: 8,
          height: 8,
          borderRadius: 9999,
          background: isBuy ? 'var(--bull)' : 'var(--bear)',
          flexShrink: 0,
        }}
      />

      <div className="min-w-0 flex-1">
        <div
          className="t-num-body"
          style={{ color: 'var(--text-1)', fontSize: 13, lineHeight: 1.3 }}
        >
          <span style={{ color: isBuy ? 'var(--bull)' : 'var(--bear)', fontWeight: 600 }}>
            {order.action}
          </span>{' '}
          {order.qty} @ {fmtPrice(fillPrice)}
        </div>
        <div
          className="t-ui-footnote"
          style={{ color: 'var(--text-3)', marginTop: 2, display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}
        >
          <span>{order.placed_at ? fmtRelTime(new Date(order.placed_at)) : '—'}</span>
          {order.signal_id && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <Link
                to="/journal"
                title={`Signal ${order.signal_id}`}
                style={{ color: 'var(--text-3)', textDecoration: 'none', fontFamily: 'var(--font-mono)' }}
              >
                signal
              </Link>
            </>
          )}
          {order.net_amount != null && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>net {fmtINR(Math.abs(order.net_amount))}</span>
            </>
          )}
        </div>
      </div>

      <StatusChip tone={tone}>{status || 'PENDING'}</StatusChip>
    </li>
  );
}

function Centered({ children }) {
  return (
    <div
      className="flex flex-col items-center justify-center"
      style={{ height: '100%', padding: 24 }}
    >
      {children}
    </div>
  );
}

function Skeleton() {
  return (
    <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
      {Array.from({ length: 4 }).map((_, i) => (
        <li
          key={i}
          style={{
            padding: '12px 14px',
            borderBottom: '1px solid var(--edge-1)',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            animation: 'tohSkelPulse 1.8s ease-in-out infinite',
          }}
        >
          <div style={{ width: 8, height: 8, borderRadius: 9999, background: 'var(--surface-2)', flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ height: 14, width: '60%', background: 'var(--surface-2)', borderRadius: 4 }} />
            <div style={{ height: 11, width: '40%', background: 'var(--surface-2)', borderRadius: 4, marginTop: 6 }} />
          </div>
          <div style={{ height: 18, width: 60, background: 'var(--surface-2)', borderRadius: 4 }} />
        </li>
      ))}
      <style>{`@keyframes tohSkelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </ul>
  );
}

export default TickerOrderHistory;
