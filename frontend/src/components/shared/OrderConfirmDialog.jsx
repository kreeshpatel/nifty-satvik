/**
 * OrderConfirmDialog — final "are you sure?" gate before a real-money
 * order is routed to Zerodha Kite.
 *
 * Built on Radix AlertDialog (focus-trapped, no overlay-dismiss) — chosen
 * over plain Dialog because this is a confirmation flow, not a generic
 * modal. Cancel is the safer default.
 *
 * Props:
 *   open         — boolean, controlled by parent
 *   onOpenChange — (next) => void, controlled
 *   payload      — the OrderPad PlaceOrderRequest about to fire
 *   signal       — source signal (used to surface stop/target context)
 *   submitting   — boolean, disables Confirm while in-flight
 *   error        — string | null, inline error from a previous attempt
 *   onConfirm    — async () => void, fires the actual mutation
 */
import React from 'react';
import * as AlertDialogPrimitive from '@radix-ui/react-alert-dialog';
import { ShieldAlert } from 'lucide-react';
import { fmtPrice, fmtINR } from '@/lib/format';

const PRODUCT_HINT = {
  CNC:  'Delivery',
  MIS:  'Intraday',
  NRML: 'F&O carry',
};

const ORDER_TYPE_LABEL = {
  LIMIT:  'Limit',
  MARKET: 'Market',
  SL:     'SL',
  'SL-M': 'SL-Market',
};

export function OrderConfirmDialog({
  open,
  onOpenChange,
  payload,
  signal,
  submitting = false,
  error = null,
  onConfirm,
}) {
  if (!payload) return null;

  const {
    transaction_type: side,
    tradingsymbol: ticker,
    quantity,
    order_type: orderType,
    price,
    trigger_price: triggerPrice,
    product,
    validity,
  } = payload;

  const isBuy = side === 'BUY';
  const tone = isBuy ? 'var(--bull)' : 'var(--bear)';
  const stop = signal?.stop;
  const target = signal?.target;

  // For MARKET orders price is null on the wire — show entry as estimate.
  const displayPrice =
    orderType === 'MARKET'
      ? (signal?.entry ?? null)
      : price;
  const estimatedValue =
    typeof displayPrice === 'number' ? displayPrice * quantity : null;

  const stopPct =
    typeof stop === 'number' && typeof displayPrice === 'number' && displayPrice > 0
      ? ((stop - displayPrice) / displayPrice) * 100
      : null;
  const targetPct =
    typeof target === 'number' && typeof displayPrice === 'number' && displayPrice > 0
      ? ((target - displayPrice) / displayPrice) * 100
      : null;

  const handleConfirm = async (e) => {
    // Prevent the AlertDialogAction default close-on-click — we want the
    // dialog to stay open while the mutation is in flight, and only close
    // on success. The parent handles closing via onOpenChange after success.
    e.preventDefault();
    if (submitting) return;
    await onConfirm?.();
  };

  return (
    <AlertDialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialogPrimitive.Portal>
        <AlertDialogPrimitive.Overlay
          className="fixed inset-0 z-[60]"
          style={{ background: 'oklch(0% 0 0 / 0.7)', backdropFilter: 'blur(6px)' }}
        />
        <AlertDialogPrimitive.Content
          className="fixed left-1/2 top-1/2 z-[60] flex flex-col"
          style={{
            transform: 'translate(-50%, -50%)',
            width: 'min(440px, calc(100vw - 32px))',
            maxHeight: 'calc(100vh - 64px)',
            background: 'var(--surface-modal)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid var(--edge-2)',
            borderRadius: 'var(--r-card)',
            boxShadow: 'var(--shadow-lg)',
            overflow: 'hidden',
          }}
        >
          <header
            style={{
              padding: '20px 24px 16px',
              borderBottom: '1px solid var(--edge-1)',
              flexShrink: 0,
            }}
          >
            <div
              className="t-ui-micro"
              style={{ color: tone, marginBottom: 6, letterSpacing: '0.08em' }}
            >
              {side}
            </div>
            <AlertDialogPrimitive.Title
              className="t-title-2"
              style={{ margin: 0, color: 'var(--text-1)' }}
            >
              Confirm order — {ticker}
            </AlertDialogPrimitive.Title>
            <AlertDialogPrimitive.Description
              className="t-ui-footnote"
              style={{ color: 'var(--text-3)', marginTop: 6 }}
            >
              Review the terms before this is sent to Zerodha.
            </AlertDialogPrimitive.Description>
          </header>

          <div
            className="flex-1 overflow-y-auto"
            style={{ padding: '16px 24px' }}
          >
            <Row label="Action" value={side} valueColor={tone} />
            <Row label="Quantity" value={`${quantity} share${quantity === 1 ? '' : 's'}`} />
            <Row
              label="Order type"
              value={ORDER_TYPE_LABEL[orderType] ?? orderType}
            />
            <Row
              label="Price"
              value={
                orderType === 'MARKET'
                  ? 'Market'
                  : typeof price === 'number'
                    ? fmtPrice(price)
                    : '—'
              }
            />
            {(orderType === 'SL' || orderType === 'SL-M') && (
              <Row
                label="Trigger price"
                value={typeof triggerPrice === 'number' ? fmtPrice(triggerPrice) : '—'}
              />
            )}
            <Row
              label="Product"
              value={
                <span>
                  {product}
                  {PRODUCT_HINT[product] && (
                    <span style={{ color: 'var(--text-3)', marginLeft: 6 }}>
                      · {PRODUCT_HINT[product]}
                    </span>
                  )}
                </span>
              }
            />
            <Row label="Validity" value={validity} />

            <div
              style={{
                marginTop: 16,
                padding: 12,
                background: 'var(--surface-2)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
              }}
            >
              <Row
                label="Estimated value"
                value={
                  typeof estimatedValue === 'number' ? fmtINR(estimatedValue) : '—'
                }
                last
                strong
              />
              {typeof stop === 'number' && (
                <Row
                  label="Stop loss"
                  value={
                    <span style={{ color: 'var(--bear)' }}>
                      {fmtPrice(stop)}
                      {stopPct !== null && (
                        <span style={{ marginLeft: 6, fontSize: 12 }}>
                          ({stopPct >= 0 ? '+' : ''}{stopPct.toFixed(1)}%)
                        </span>
                      )}
                    </span>
                  }
                  last
                />
              )}
              {typeof target === 'number' && (
                <Row
                  label="Target"
                  value={
                    <span style={{ color: 'var(--bull)' }}>
                      {fmtPrice(target)}
                      {targetPct !== null && (
                        <span style={{ marginLeft: 6, fontSize: 12 }}>
                          ({targetPct >= 0 ? '+' : ''}{targetPct.toFixed(1)}%)
                        </span>
                      )}
                    </span>
                  }
                  last
                />
              )}
            </div>

            <div
              role="note"
              style={{
                marginTop: 16,
                padding: 12,
                background: 'var(--warn-soft)',
                border: '1px solid var(--warn)',
                borderRadius: 'var(--r-chip)',
                display: 'flex',
                gap: 10,
                alignItems: 'flex-start',
              }}
            >
              <ShieldAlert
                size={16}
                strokeWidth={1.75}
                style={{ color: 'var(--warn)', flexShrink: 0, marginTop: 2 }}
              />
              <div className="t-ui-footnote" style={{ color: 'var(--text-2)', lineHeight: 1.5 }}>
                This order will be placed directly on <strong>Zerodha Kite</strong> using your
                linked account. Nifty Satvik does not hold funds or settle the trade. By
                confirming, you authorize Zerodha to execute this transaction on your behalf.
                Markets move — fills are not guaranteed at the displayed price.
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="t-ui-footnote"
                style={{
                  marginTop: 12,
                  padding: 10,
                  background: 'var(--bear-soft)',
                  border: '1px solid var(--bear)',
                  borderRadius: 'var(--r-chip)',
                  color: 'var(--bear)',
                }}
              >
                {error}
              </div>
            )}
          </div>

          <footer
            style={{
              flexShrink: 0,
              padding: 16,
              borderTop: '1px solid var(--edge-1)',
              display: 'flex',
              gap: 8,
              background: 'var(--surface-modal)',
            }}
          >
            <AlertDialogPrimitive.Cancel asChild>
              <button
                type="button"
                disabled={submitting}
                className="t-ui-callout"
                style={{
                  flex: 1,
                  padding: '12px 16px',
                  background: 'transparent',
                  color: 'var(--text-2)',
                  border: '1px solid var(--edge-2)',
                  borderRadius: 'var(--r-chip)',
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  fontWeight: 500,
                }}
              >
                Cancel
              </button>
            </AlertDialogPrimitive.Cancel>
            <AlertDialogPrimitive.Action asChild>
              <button
                type="button"
                disabled={submitting}
                onClick={handleConfirm}
                className="t-ui-callout"
                style={{
                  flex: 1.4,
                  padding: '12px 16px',
                  background: submitting ? 'var(--surface-3)' : 'var(--brand)',
                  color: submitting ? 'var(--text-3)' : 'var(--brand-fg)',
                  border: `1px solid ${submitting ? 'var(--edge-1)' : 'var(--brand)'}`,
                  borderRadius: 'var(--r-chip)',
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  transition: 'background var(--dur-press) ease',
                }}
              >
                {submitting ? 'Placing…' : `Confirm & place ${side}`}
              </button>
            </AlertDialogPrimitive.Action>
          </footer>
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Portal>
    </AlertDialogPrimitive.Root>
  );
}

function Row({ label, value, valueColor, last = false, strong = false }) {
  return (
    <div
      className="flex items-baseline justify-between"
      style={{
        paddingTop: 8,
        paddingBottom: 8,
        borderBottom: last ? 'none' : '1px solid var(--edge-1)',
        gap: 12,
      }}
    >
      <div className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
        {label}
      </div>
      <div
        className="t-num-body"
        style={{
          color: valueColor ?? 'var(--text-1)',
          fontSize: 14,
          fontWeight: strong ? 600 : 500,
          textAlign: 'right',
        }}
      >
        {value}
      </div>
    </div>
  );
}

export default OrderConfirmDialog;
