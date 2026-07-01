/**
 * DecisionBand — single horizontal hero strip on the stock detail page.
 *
 * Replaces the old split layout where ticker + name lived on the left and
 * LTP + Buy/Sell lived on the right as two competing hero-scale elements.
 * The decision band consolidates them into one balanced row reading
 * left-to-right: identity → price → action.
 *
 * Layout (≥1024px):
 *   ┌──────────────────────────┬──────────────────┬──────────────┐
 *   │ TICKER · NSE  [holding]  │  ₹2,485.30       │ [Buy] [Sell] │
 *   │ Reliance Industries · En │  +12.50  +0.50%  │              │
 *   └──────────────────────────┴──────────────────┴──────────────┘
 *
 * Below 1024px it stacks: identity → price → buttons full-width.
 *
 * Design notes (per .impeccable.md):
 * - Ticker is t-title-2, not t-title-1, so it doesn't compete with LTP.
 * - LTP is t-num-hero, the highest-value number on the page.
 * - Sub-name is t-ui-footnote with no quote marks (those were a content-source
 *   artifact, not a typographic device).
 * - Exchange chip dropped — `· NSE` inline next to ticker reads cleaner and
 *   avoids the chip-on-everything admin tell.
 * - Buy is the only solid amber CTA on the page; Sell is outlined.
 * - No side-stripe borders, no rounded-2xl, no gradient text.
 */
import React from 'react';
import { StatusChip } from './StatusChip';
import { fmtPrice } from '@/lib/format';

export function DecisionBand({
  symbol,
  exchange,
  name,
  sector,
  ltp,
  change = 0,
  changePct = 0,
  tone = 'muted',          // 'bull' | 'bear' | 'muted' — colours the delta line
  isHolding = false,
  kiteConnected = true,
  onBuy,
  onSell,
  // When `false` (new default for the redesign), the inline Buy/Sell
  // buttons are hidden — actions live in the sticky bottom bar instead,
  // following the Robinhood-pro "primary action always one tap away"
  // pattern. Callers that still want inline actions pass true.
  showActions = false,
}) {
  const deltaColor =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    'var(--text-3)';
  const changeAbs = Math.abs(Number(change) || 0);
  const changeSign = Number(change) < 0 ? '-' : Number(change) > 0 ? '+' : '';

  const subline = [name, sector].filter(Boolean).join(' · ');

  return (
    <header className="dq-decision-band">
      {/* IDENTITY */}
      <div className="dq-db-identity">
        <div className="flex items-baseline" style={{ gap: 10, flexWrap: 'wrap' }}>
          <h1 className="t-title-2" style={{ margin: 0, color: 'var(--text-1)' }}>
            {symbol}
          </h1>
          {exchange && (
            <span className="t-ui-callout" style={{ color: 'var(--text-3)' }}>
              · {exchange}
            </span>
          )}
          {isHolding && <StatusChip tone="bull">HOLDING</StatusChip>}
        </div>
        {subline && (
          <p
            className="t-ui-footnote"
            style={{
              margin: '4px 0 0',
              color: 'var(--text-3)',
              maxWidth: '52ch',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {subline}
          </p>
        )}
      </div>

      {/* PRICE — LTP itself takes a tone when the day's move is non-trivial
          (>0.3% in either direction). Subtle but signals direction at a
          glance without an extra chip. Below threshold we keep neutral
          --text-1 to avoid colouring random rounding noise. */}
      <div className="dq-db-price">
        <div
          className="t-num-hero"
          style={{
            color:
              Math.abs(Number(changePct) || 0) > 0.3
                ? deltaColor
                : 'var(--text-1)',
            lineHeight: 1.05,
            fontVariantNumeric: 'tabular-nums',
            transition: 'color var(--dur-tick) ease',
          }}
        >
          {ltp != null ? fmtPrice(ltp) : '—'}
        </div>
        <div
          className="t-num-body flex items-baseline"
          style={{
            color: deltaColor,
            gap: 8,
            marginTop: 6,
            fontVariantNumeric: 'tabular-nums',
            justifyContent: 'flex-end',
          }}
        >
          <span>{changeSign}₹{changeAbs.toFixed(2)}</span>
          <span className="t-num-small">{Number(changePct || 0).toFixed(2)}%</span>
        </div>
      </div>

      {/* ACTIONS — optional. In the redesigned stock detail page these
          buttons live in the sticky bottom bar instead; the band is
          identity + price only. */}
      {showActions && (
        <div className="dq-db-actions flex" style={{ gap: 8 }}>
          <button
            type="button"
            disabled={!kiteConnected}
            onClick={onBuy}
            className="t-ui-headline"
            style={{
              padding: '10px 22px',
              background: kiteConnected ? 'var(--brand)' : 'var(--surface-3)',
              color: kiteConnected ? 'var(--brand-fg)' : 'var(--text-3)',
              border: `1px solid ${kiteConnected ? 'var(--brand)' : 'var(--edge-1)'}`,
              borderRadius: 'var(--r-chip)',
              cursor: kiteConnected ? 'pointer' : 'not-allowed',
              fontWeight: 600,
              minWidth: 88,
            }}
          >
            Buy
          </button>
          <button
            type="button"
            disabled={!kiteConnected}
            onClick={onSell}
            className="t-ui-headline"
            style={{
              padding: '10px 22px',
              background: 'transparent',
              color: kiteConnected ? 'var(--bear)' : 'var(--text-3)',
              border: `1px solid ${kiteConnected ? 'var(--bear)' : 'var(--edge-1)'}`,
              borderRadius: 'var(--r-chip)',
              cursor: kiteConnected ? 'pointer' : 'not-allowed',
              fontWeight: 600,
              minWidth: 88,
            }}
          >
            Sell
          </button>
        </div>
      )}

      {/* Layout via plain CSS so we can use a media query without pulling in
          a CSS-in-JS dep. Scoped via the .dq-decision-band class. */}
      <style>{`
        .dq-decision-band {
          display: grid;
          grid-template-columns: ${showActions ? 'minmax(0, 1fr) auto auto' : 'minmax(0, 1fr) auto'};
          align-items: center;
          gap: 24px;
          padding: 16px 0 20px;
        }
        .dq-db-identity { min-width: 0; }
        .dq-db-price { text-align: right; }
        .dq-db-actions { flex-shrink: 0; }

        /* Buy button — solid amber, hover lifts to brand-hi */
        .dq-db-actions > button:first-child:not([disabled]):hover {
          background: var(--brand-hi) !important;
          border-color: var(--brand-hi) !important;
        }
        .dq-db-actions > button:first-child:not([disabled]):active {
          background: var(--brand-lo) !important;
          border-color: var(--brand-lo) !important;
        }
        /* Sell button — outlined bear, hover fills with bear-soft */
        .dq-db-actions > button:nth-child(2):not([disabled]):hover {
          background: var(--bear-soft) !important;
        }

        @media (max-width: 768px) {
          .dq-decision-band {
            grid-template-columns: 1fr;
            gap: 16px;
          }
          .dq-db-price { text-align: left; }
          .dq-db-price > div:nth-child(2) {
            justify-content: flex-start !important;
          }
          .dq-db-actions > button { flex: 1; }
        }
      `}</style>
    </header>
  );
}

export default DecisionBand;
