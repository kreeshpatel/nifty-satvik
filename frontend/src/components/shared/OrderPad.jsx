import React, { useContext, useEffect, useMemo, useState } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X, Minus, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { fmtPrice, fmtINR } from '@/lib/format';
import { StatusChip } from './StatusChip';
import { OrderConfirmDialog } from './OrderConfirmDialog';
import { KiteContext } from '@/App';
import { useIsMobile } from '@/hooks/useIsMobile';

/**
 * OrderPad — the 400px right-side order entry drawer.
 *
 * Prefills qty from risk-per-trade sizing:
 *   qty = floor((risk_per_trade_pct * capital) / (entry - stop))
 * capped at (max_position_pct * capital) / entry.
 *
 * Shows live-computed position size, risk in ₹, reward in ₹, and R:R
 * as the user adjusts qty / price. This is the bit that earns the page
 * — a retail-pro trader wants to SEE the sizing math, not guess.
 *
 * Side effects are OUT of scope: the `onPlace` prop receives the full
 * composed order payload; the parent wires it to /api/kite/orders/:variety
 * and /api/nq-orders. The OrderPad is a controlled form primitive.
 *
 * Controlled props
 * ----------------
 * open, onOpenChange — Radix Dialog control
 * signal             — source signal for defaults (entry, stop, target, ticker)
 * side               — 'BUY' | 'SELL' (default 'BUY')
 * capital            — user's capital (for sizing calculations)
 * riskPerTrade       — fraction (default 0.035)
 * maxPositionPct     — fraction (default 0.12)
 * marginAvailable    — live margin from /kite/margins
 * onPlace            — fn({exchange, tradingsymbol, transaction_type, quantity, product, order_type, price, trigger_price, validity, signalId}) => Promise
 * submitting         — boolean — disables submit while in-flight
 */
const ORDER_TYPES = [
  { value: 'LIMIT',  label: 'Limit' },
  { value: 'MARKET', label: 'Market' },
  { value: 'SL',     label: 'SL' },
  { value: 'SL-M',   label: 'SL-M' },
];

const PRODUCTS = [
  { value: 'CNC',  label: 'CNC',  hint: 'Delivery' },
  { value: 'MIS',  label: 'MIS',  hint: 'Intraday' },
  { value: 'NRML', label: 'NRML', hint: 'F&O carry' },
];

export function OrderPad({
  open,
  onOpenChange,
  signal,
  side = 'BUY',
  capital = 1000000,
  riskPerTrade = 0.035,
  maxPositionPct = 0.12,
  marginAvailable,
  onPlace,
  submitting = false,
}) {
  const isBuy = side === 'BUY';
  const {
    ticker = '',
    entry = 0,
    stop = 0,
    target = 0,
  } = signal ?? {};

  // ── Form state ───────────────────────────────────────────────
  const [orderType, setOrderType] = useState('LIMIT');
  const [product, setProduct] = useState('CNC');
  const [price, setPrice] = useState(entry ?? 0);
  const [qty, setQty] = useState(0);
  const [triggerPrice, setTriggerPrice] = useState(0);

  // ── Confirmation dialog state ────────────────────────────────
  // pendingPayload non-null = "user clicked Place, waiting for explicit
  // Confirm before we hit Kite". Decoupled from the OrderPad drawer's open
  // state so the user can keep editing if they cancel the confirmation.
  const [pendingPayload, setPendingPayload] = useState(null);
  const [confirmError, setConfirmError] = useState(null);

  // ── Kite session gate (G4) ───────────────────────────────────
  const kite = useContext(KiteContext);
  const kiteConnected = kite?.connected;

  // ── Mobile bottom-sheet variant ──────────────────────────────
  // On phones the right-side 400px drawer + sticky footer leaves the
  // Place button stranded under the soft keyboard. We slide up from
  // the bottom, cap height at 90dvh, and let the body scroll.
  const isMobile = useIsMobile();

  // Prefill qty from risk sizing when signal changes or drawer opens.
  useEffect(() => {
    if (!open || !signal) return;
    const stopDist = Math.abs((entry ?? 0) - (stop ?? 0));
    if (stopDist <= 0 || !entry) { setQty(0); setPrice(entry ?? 0); return; }
    const maxRisk = capital * riskPerTrade;
    const qtyByRisk = Math.floor(maxRisk / stopDist);
    const qtyByCap = Math.floor((capital * maxPositionPct) / entry);
    const q = Math.max(1, Math.min(qtyByRisk, qtyByCap));
    setQty(q);
    setPrice(entry);
    setTriggerPrice(stop || 0);
  }, [open, signal, entry, stop, capital, riskPerTrade, maxPositionPct]);

  // Percent-of-margin shortcuts snap qty to 25/50/100% of what margin allows.
  const margin = typeof marginAvailable === 'number' ? marginAvailable : capital;
  const setPctOfMargin = (pct) => {
    if (!price || price <= 0) return;
    setQty(Math.max(1, Math.floor((margin * pct) / price)));
  };

  // ── Live computed metrics ────────────────────────────────────
  const { positionValue, riskRupees, rewardRupees, rr } = useMemo(() => {
    const p = Number(price) || 0;
    const q = Number(qty) || 0;
    const positionValue = p * q;
    const stopDist = Math.abs(p - (stop ?? 0));
    const tgtDist = Math.abs((target ?? 0) - p);
    const riskRupees = stopDist * q;
    const rewardRupees = tgtDist * q;
    const rr = stopDist > 0 ? tgtDist / stopDist : 0;
    return { positionValue, riskRupees, rewardRupees, rr };
  }, [price, qty, stop, target]);

  const pctOfMargin = margin > 0 ? (positionValue / margin) * 100 : 0;
  const overMargin = positionValue > margin;

  // Click "Place BUY/SELL" → compose payload + open the confirm dialog.
  // We do NOT call onPlace yet; the actual Kite POST fires only after the
  // user clicks "Confirm & place" inside OrderConfirmDialog.
  const handlePlace = () => {
    if (!onPlace || !kiteConnected) return;
    const payload = {
      exchange: 'NSE',
      tradingsymbol: ticker,
      transaction_type: isBuy ? 'BUY' : 'SELL',
      quantity: Number(qty),
      product,
      order_type: orderType,
      price: orderType === 'MARKET' ? null : Number(price),
      trigger_price: (orderType === 'SL' || orderType === 'SL-M') ? Number(triggerPrice) : null,
      validity: 'DAY',
      signalId: signal?.signal_date ? `${ticker}__${signal.signal_date}` : null,
      signal,
    };
    setConfirmError(null);
    setPendingPayload(payload);
  };

  const handleConfirmedPlace = async () => {
    if (!pendingPayload) return;
    try {
      await onPlace(pendingPayload);
      // Success: close confirm dialog AND OrderPad drawer.
      setPendingPayload(null);
      setConfirmError(null);
      onOpenChange?.(false);
    } catch (err) {
      // Keep confirm dialog open with inline error so user can retry
      // without re-opening the drawer.
      setConfirmError(err?.message || 'Order failed. Please try again.');
    }
  };

  const handleConfirmOpenChange = (next) => {
    if (!next) {
      setPendingPayload(null);
      setConfirmError(null);
    }
  };

  if (!signal) return null;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50"
          style={{ background: 'oklch(0% 0 0 / 0.6)', backdropFilter: 'blur(4px)' }}
        />
        <DialogPrimitive.Content
          className={cn(
            'fixed z-50 flex flex-col',
            isMobile
              ? 'left-0 right-0 bottom-0'
              : 'top-0 right-0 h-full'
          )}
          style={
            isMobile
              ? {
                  width: '100vw',
                  maxHeight: '90dvh',
                  background: 'var(--surface-modal)',
                  backdropFilter: 'blur(24px)',
                  WebkitBackdropFilter: 'blur(24px)',
                  borderTop: '1px solid var(--edge-2)',
                  borderTopLeftRadius: 'var(--r-panel)',
                  borderTopRightRadius: 'var(--r-panel)',
                  boxShadow: 'var(--shadow-lg)',
                  paddingBottom: 'env(safe-area-inset-bottom)',
                }
              : {
                  width: 'min(400px, 100vw)',
                  background: 'var(--surface-modal)',
                  backdropFilter: 'blur(24px)',
                  WebkitBackdropFilter: 'blur(24px)',
                  borderLeft: '1px solid var(--edge-2)',
                  boxShadow: 'var(--shadow-lg)',
                }
          }
          aria-describedby={undefined}
        >
          {/* HEADER with BUY/SELL tone */}
          <header
            style={{
              padding: '20px 24px',
              borderBottom: '1px solid var(--edge-1)',
              flexShrink: 0,
            }}
          >
            <div className="flex items-start justify-between">
              <div className="min-w-0">
                <div
                  className="t-ui-micro"
                  style={{ color: isBuy ? 'var(--bull)' : 'var(--bear)', marginBottom: 6 }}
                >
                  {isBuy ? 'BUY' : 'SELL'}
                </div>
                <DialogPrimitive.Title
                  className="t-title-2"
                  style={{ margin: 0, color: 'var(--text-1)' }}
                >
                  {ticker}
                </DialogPrimitive.Title>
              </div>
              <DialogPrimitive.Close
                aria-label="Close"
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-3)',
                  padding: 4,
                }}
              >
                <X size={18} strokeWidth={1.75} />
              </DialogPrimitive.Close>
            </div>
          </header>

          {/* BODY */}
          <div
            className="flex-1 overflow-y-auto"
            style={{ padding: '20px 24px' }}
          >
            {/* ORDER TYPE — pill group */}
            <FieldGroup label="Order type">
              <PillGroup
                options={ORDER_TYPES}
                value={orderType}
                onChange={setOrderType}
              />
            </FieldGroup>

            {/* PRICE */}
            {orderType !== 'MARKET' && (
              <FieldGroup label="Price">
                <NumberInput
                  value={price}
                  onChange={setPrice}
                  step={0.05}
                  decimals={2}
                  prefix="₹"
                />
              </FieldGroup>
            )}

            {/* TRIGGER PRICE for SL / SL-M */}
            {(orderType === 'SL' || orderType === 'SL-M') && (
              <FieldGroup label="Trigger price">
                <NumberInput
                  value={triggerPrice}
                  onChange={setTriggerPrice}
                  step={0.05}
                  decimals={2}
                  prefix="₹"
                />
              </FieldGroup>
            )}

            {/* QUANTITY with steppers + %-of-margin */}
            <FieldGroup label="Quantity">
              <div className="flex items-center" style={{ gap: 8 }}>
                <StepperButton onClick={() => setQty((q) => Math.max(1, Number(q) - 1))}>
                  <Minus size={14} strokeWidth={2} />
                </StepperButton>
                <input
                  type="number"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={qty}
                  onChange={(e) => setQty(Math.max(0, Math.floor(Number(e.target.value) || 0)))}
                  className="t-num-large"
                  style={{
                    flex: 1,
                    background: 'var(--surface-3)',
                    border: '1px solid var(--edge-1)',
                    borderRadius: 'var(--r-chip)',
                    padding: '8px 12px',
                    color: 'var(--text-1)',
                    textAlign: 'center',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 18,
                  }}
                />
                <StepperButton onClick={() => setQty((q) => Number(q) + 1)}>
                  <Plus size={14} strokeWidth={2} />
                </StepperButton>
              </div>
              <div className="flex" style={{ gap: 6, marginTop: 8 }}>
                {[0.25, 0.5, 1].map((pct) => (
                  <button
                    key={pct}
                    type="button"
                    onClick={() => setPctOfMargin(pct)}
                    className="t-ui-callout flex-1"
                    style={{
                      padding: '6px 10px',
                      background: 'transparent',
                      color: 'var(--text-2)',
                      border: '1px solid var(--edge-1)',
                      borderRadius: 'var(--r-chip)',
                      cursor: 'pointer',
                    }}
                  >
                    {pct * 100}%
                  </button>
                ))}
              </div>
            </FieldGroup>

            {/* PRODUCT */}
            <FieldGroup label="Product">
              <PillGroup
                options={PRODUCTS}
                value={product}
                onChange={setProduct}
                renderHint={(opt) => opt.hint}
              />
            </FieldGroup>

            {/* LIVE SIZING READOUT */}
            <div
              style={{
                marginTop: 24,
                padding: 16,
                background: 'var(--surface-2)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
              }}
            >
              <SizingRow label="Position size" value={fmtINR(positionValue)} />
              <SizingRow
                label="% of margin"
                value={`${pctOfMargin.toFixed(1)}%`}
                tone={overMargin ? 'bear' : 'muted'}
              />
              <SizingRow
                label="Risk"
                value={fmtINR(riskRupees)}
                sub={stop ? `Stop ${fmtPrice(stop)}` : undefined}
                tone="bear"
              />
              <SizingRow
                label="Reward"
                value={fmtINR(rewardRupees)}
                sub={target ? `Target ${fmtPrice(target)}` : undefined}
                tone="bull"
              />
              <SizingRow
                label="R:R"
                value={rr > 0 ? rr.toFixed(2) : '—'}
                tone="neutral"
                last
              />
            </div>

            {overMargin && (
              <div style={{ marginTop: 12 }}>
                <StatusChip tone="bear">INSUFFICIENT MARGIN</StatusChip>
              </div>
            )}
          </div>

          {/* FOOTER — PLACE ORDER CTA */}
          <footer
            style={{
              flexShrink: 0,
              padding: 16,
              borderTop: '1px solid var(--edge-1)',
              background: 'var(--surface-modal)',
            }}
          >
            {(() => {
              const disabled =
                submitting || overMargin || qty <= 0 || !kiteConnected;
              const label = !kiteConnected
                ? 'Connect Kite to place orders'
                : submitting
                  ? 'Placing…'
                  : `Place ${side} ${qty > 0 ? `${qty} ` : ''}${ticker}`;
              return (
                <button
                  type="button"
                  disabled={disabled}
                  onClick={handlePlace}
                  className="t-ui-headline w-full"
                  style={{
                    padding: '14px 16px',
                    background: disabled ? 'var(--surface-3)' : 'var(--brand-grad)',
                    color: disabled ? 'var(--text-3)' : 'var(--brand-fg)',
                    border: `1px solid ${disabled ? 'var(--edge-1)' : 'var(--brand)'}`,
                    borderRadius: 'var(--r-chip)',
                    cursor: disabled ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    transition: 'background var(--dur-press) ease',
                  }}
                >
                  {label}
                </button>
              );
            })()}
          </footer>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>

      <OrderConfirmDialog
        open={pendingPayload !== null}
        onOpenChange={handleConfirmOpenChange}
        payload={pendingPayload}
        signal={signal}
        submitting={submitting}
        error={confirmError}
        onConfirm={handleConfirmedPlace}
      />
    </DialogPrimitive.Root>
  );
}

// ══════════════════════════════════════════════════════════════
// INTERNAL SUB-COMPONENTS
// ══════════════════════════════════════════════════════════════

function FieldGroup({ label, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 8 }}>
        {label}
      </div>
      {children}
    </div>
  );
}

function PillGroup({ options, value, onChange, renderHint }) {
  return (
    <div
      role="radiogroup"
      className="inline-flex w-full"
      style={{
        background: 'var(--surface-3)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-chip)',
        padding: 2,
        gap: 2,
      }}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className="t-ui-callout"
            style={{
              flex: 1,
              padding: '6px 10px',
              background: active ? 'var(--surface-1)' : 'transparent',
              color: active ? 'var(--text-1)' : 'var(--text-3)',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: active ? 600 : 500,
              boxShadow: active ? 'var(--shadow-sm)' : 'none',
            }}
          >
            <div>{opt.label}</div>
            {renderHint && (
              <div className="t-num-small" style={{ color: active ? 'var(--text-3)' : 'var(--text-4)', fontSize: 10, marginTop: 2 }}>
                {renderHint(opt)}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}

function NumberInput({ value, onChange, step = 1, decimals = 0, prefix }) {
  return (
    <div
      className="flex items-center"
      style={{
        background: 'var(--surface-3)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-chip)',
        paddingLeft: 12,
      }}
    >
      {prefix && (
        <span
          className="t-num-body"
          style={{ color: 'var(--text-3)', fontSize: 14, marginRight: 4 }}
        >
          {prefix}
        </span>
      )}
      <input
        type="number"
        inputMode="decimal"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
        className="t-num-body"
        style={{
          flex: 1,
          background: 'transparent',
          border: 'none',
          padding: '10px 12px',
          color: 'var(--text-1)',
          outline: 'none',
          fontFamily: 'var(--font-mono)',
          fontSize: 14,
        }}
      />
    </div>
  );
}

function StepperButton({ children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Adjust"
      style={{
        width: 36,
        height: 36,
        background: 'var(--surface-3)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-chip)',
        color: 'var(--text-2)',
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {children}
    </button>
  );
}

function SizingRow({ label, value, sub, tone = 'muted', last = false }) {
  const color =
    tone === 'bull'    ? 'var(--bull)' :
    tone === 'bear'    ? 'var(--bear)' :
    tone === 'neutral' ? 'var(--text-1)' :
                         'var(--text-2)';
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
      <div>
        <div className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
          {label}
        </div>
        {sub && (
          <div className="t-num-small" style={{ color: 'var(--text-4)', marginTop: 2 }}>
            {sub}
          </div>
        )}
      </div>
      <div className="t-num-body" style={{ color, fontSize: 14 }}>
        {value}
      </div>
    </div>
  );
}

export default OrderPad;
