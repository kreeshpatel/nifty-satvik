/**
 * OrderBookL2 — Level 2 market depth (top 5 bid + top 5 ask).
 *
 * Reads from useKiteQuote(symbol) which polls /api/kite/quote every 2s.
 * Renders the bid + ask ladders side-by-side, with quantity-weighted
 * background fill so the eye reads volume without a second column.
 *
 * Why this matters on the stock detail page:
 *   - Tells the trader the actual spread (often wider than LTP suggests)
 *   - Shows where the next ₹1L of liquidity sits
 *   - Bid/ask volume imbalance is a short-horizon directional signal
 *
 * Layout:
 *   Header: spread + total volume + last trade time
 *   Two columns: BID (left, green tint) | ASK (right, red tint)
 *     Each row: price · qty · orders (collapse on narrow widths)
 *   Quantity bars are normalized to the max qty in the visible book.
 *
 * Empty state: shown when symbol is null OR backend returned no depth
 * (some illiquid stocks have no L2 in Kite). Loading uses a skeleton
 * matched to the final layout.
 */
import React from 'react';
import { fmtPrice, fmtVolume } from '@/lib/format';
import { useKiteQuote } from '@/hooks/queries/useKiteQuote';

/**
 * @param {object|null} [tick] — pre-fetched quote (incl. .depth). When the
 *   parent already polls /api/kite/quote for this symbol (e.g. StockDetailV2
 *   via useStockData), pass that tick in so we don't fire a duplicate query.
 *   Without this prop we fall back to our own useKiteQuote — costs an extra
 *   cold-backend request but keeps standalone usage working.
 */
export function OrderBookL2({ symbol, exchange = 'NSE', height = 320, tick = null }) {
  const externalTickProvided = tick != null;
  const q = useKiteQuote(symbol, { exchange, enabled: !externalTickProvided });
  // Prefer the externally-supplied tick (avoids the second-fetch cold start).
  const data = externalTickProvided ? tick : q.data;
  const isFetching = externalTickProvided ? false : q.isFetching;
  const isLoading = externalTickProvided ? false : q.isLoading;

  if (isLoading && !data) return <Skeleton height={height} />;

  // Array.isArray guards — Kite occasionally returns malformed depth shapes
  // for illiquid tickers (e.g. `depth: null`, `depth: {}`, or even
  // `depth: { buy: null }` when there are no resting orders). The previous
  // `?? []` only handles undefined/null but not non-array primitives, which
  // would crash `.slice()` on the next line. Defensive guard matches the
  // post-audit pattern used elsewhere in the page.
  const buy = Array.isArray(data?.depth?.buy)
    ? data.depth.buy.slice(0, 5)
    : [];
  const sell = Array.isArray(data?.depth?.sell)
    ? data.depth.sell.slice(0, 5)
    : [];
  const lastPrice = data?.last_price;
  const volume = data?.volume;
  const lastTradeTime = data?.last_trade_time;

  const bestBid = buy[0]?.price;
  const bestAsk = sell[0]?.price;
  const spread = bestAsk && bestBid ? bestAsk - bestBid : null;
  const spreadPct = spread && lastPrice ? (spread / lastPrice) * 100 : null;

  // Normalize bar widths against the larger of best-5 bid + best-5 ask.
  const maxQty = Math.max(
    ...buy.map((r) => Number(r.quantity) || 0),
    ...sell.map((r) => Number(r.quantity) || 0),
    1,
  );

  if (buy.length === 0 && sell.length === 0) {
    return (
      <Wrapper height={height}>
        <Header symbol={symbol} note="No depth available" />
        <div
          className="flex items-center justify-center"
          style={{ flex: 1, color: 'var(--text-3)', fontSize: 12 }}
        >
          Order book unavailable for {symbol}
        </div>
      </Wrapper>
    );
  }

  return (
    <Wrapper height={height}>
      <Header
        symbol={symbol}
        spread={spread}
        spreadPct={spreadPct}
        volume={volume}
        lastTradeTime={lastTradeTime}
        loading={isFetching}
      />

      {/* Column heads */}
      <div
        className="grid"
        style={{
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
          padding: '6px 12px 4px',
          borderBottom: '1px solid var(--edge-1)',
          background: 'var(--surface-2)',
        }}
      >
        <span className="t-ui-micro" style={{ color: 'var(--bull)' }}>BID · QTY</span>
        <span className="t-ui-micro" style={{ color: 'var(--bear)', textAlign: 'right' }}>ASK · QTY</span>
      </div>

      {/* Ladders */}
      <div
        className="grid"
        style={{
          gridTemplateColumns: '1fr 1fr',
          gap: 0,
          flex: 1,
          overflowY: 'auto',
        }}
      >
        <div style={{ borderRight: '1px solid var(--edge-1)' }}>
          {buy.map((row, i) => (
            <DepthRow key={`b-${i}`} row={row} maxQty={maxQty} side="buy" />
          ))}
        </div>
        <div>
          {sell.map((row, i) => (
            <DepthRow key={`s-${i}`} row={row} maxQty={maxQty} side="sell" />
          ))}
        </div>
      </div>
    </Wrapper>
  );
}

function Wrapper({ height, children }) {
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
      {children}
    </div>
  );
}

function Header({ symbol, spread, spreadPct, volume, lastTradeTime, note, loading }) {
  return (
    <header
      style={{
        padding: '12px 14px',
        borderBottom: '1px solid var(--edge-1)',
        flexShrink: 0,
      }}
    >
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h3 className="t-ui-headline" style={{ margin: 0, color: 'var(--text-1)' }}>
          Order book
        </h3>
        {loading && <span className="t-ui-micro" style={{ color: 'var(--brand-hi)' }}>LIVE</span>}
      </div>
      {note ? (
        <div className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>{note}</div>
      ) : (
        <div
          className="t-ui-footnote flex items-center"
          style={{ color: 'var(--text-3)', gap: 10, flexWrap: 'wrap' }}
        >
          {spread != null && (
            <span>
              Spread <span className="t-num-small" style={{ color: 'var(--text-2)' }}>{fmtPrice(spread)}</span>
              {spreadPct != null && <span className="t-num-small" style={{ color: 'var(--text-3)', marginLeft: 4 }}>({spreadPct.toFixed(2)}%)</span>}
            </span>
          )}
          {volume != null && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>Vol <span className="t-num-small" style={{ color: 'var(--text-2)' }}>{fmtVolume(volume)}</span></span>
            </>
          )}
          {lastTradeTime && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>{formatTradeTime(lastTradeTime)}</span>
            </>
          )}
        </div>
      )}
    </header>
  );
}

function formatTradeTime(s) {
  // Kite returns "YYYY-MM-DD HH:MM:SS"
  if (!s || typeof s !== 'string') return '';
  const m = s.match(/(\d{2}:\d{2}:\d{2})/);
  return m ? m[1] : '';
}

function DepthRow({ row, maxQty, side }) {
  const qty = Number(row.quantity) || 0;
  const widthPct = maxQty > 0 ? Math.min(100, (qty / maxQty) * 100) : 0;
  const tone = side === 'buy' ? 'var(--bull)' : 'var(--bear)';
  const bgTone = side === 'buy' ? 'var(--bull-soft)' : 'var(--bear-soft)';
  return (
    <div
      style={{
        position: 'relative',
        padding: '8px 12px',
        borderBottom: '1px solid var(--edge-1)',
        display: 'flex',
        alignItems: 'baseline',
        justifyContent: side === 'buy' ? 'flex-start' : 'flex-end',
        gap: 6,
        overflow: 'hidden',
      }}
    >
      {/* qty-proportional fill bar — anchored to outer side */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          [side === 'buy' ? 'left' : 'right']: 0,
          width: `${widthPct}%`,
          background: bgTone,
          opacity: 0.55,
          pointerEvents: 'none',
        }}
      />
      <span
        className="t-num-body"
        style={{
          position: 'relative',
          color: tone,
          fontSize: 13,
          fontWeight: 500,
          minWidth: 60,
          textAlign: side === 'buy' ? 'left' : 'right',
        }}
      >
        {fmtPrice(row.price ?? 0)}
      </span>
      <span
        className="t-num-small"
        style={{
          position: 'relative',
          color: 'var(--text-2)',
          fontSize: 11,
        }}
      >
        {fmtVolume(qty)}
      </span>
    </div>
  );
}

function Skeleton({ height }) {
  return (
    <Wrapper height={height}>
      <header
        style={{
          padding: '12px 14px',
          borderBottom: '1px solid var(--edge-1)',
          flexShrink: 0,
        }}
      >
        <div style={{ height: 16, width: 100, background: 'var(--surface-2)', borderRadius: 4 }} />
        <div style={{ height: 12, width: 200, background: 'var(--surface-2)', borderRadius: 4, marginTop: 6 }} />
      </header>
      <div style={{ flex: 1, padding: 14 }}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
              marginBottom: 10,
            }}
          >
            <div style={{ height: 18, background: 'var(--surface-2)', borderRadius: 4 }} />
            <div style={{ height: 18, background: 'var(--surface-2)', borderRadius: 4 }} />
          </div>
        ))}
      </div>
      <style>{`
        @keyframes shimmer { 0% { opacity: 0.55 } 50% { opacity: 1 } 100% { opacity: 0.55 } }
      `}</style>
    </Wrapper>
  );
}

export default OrderBookL2;
