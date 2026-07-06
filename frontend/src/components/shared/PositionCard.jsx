import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { GlassCard } from '@/components/shared/GlassCard';
import { StatusChip } from '@/components/shared/StatusChip';
import { SellGuidanceBanner } from '@/components/shared/SellGuidanceBanner';
import { reconcileDrift } from '@/services/api';
import { NQ_POSITIONS_KEY } from '@/hooks/queries/useNQPositions';
import { EXTERNAL_HOLDINGS_KEY } from '@/hooks/queries/useExternalHoldings';
import { NQ_ORDERS_KEY } from '@/hooks/useOrderPlacement';
import { cn } from '@/lib/utils';

/**
 * PositionCard — a single NQ-tracked position rendered with the
 * originating signal's frame of reference (entry/stop/target/days).
 *
 * Used by the PortfolioV2 "Nifty Satvik Positions" section. NOT used for
 * external Kite holdings (those go through the existing DataTable in
 * the "Other Kite Holdings" section, since they have no signal context
 * to display).
 *
 * Visual hierarchy:
 *   ┌─────────────────────────────────────────────────────┐
 *   │ TICKER · status_for_user chip          P&L %        │
 *   │ qty × avg ₹ → current ₹  ·  ₹ pnl                   │
 *   │ ───── entry ─── stop ─── target ───── days_left ──  │
 *   │ [optional: SellGuidanceBanner]                       │
 *   └─────────────────────────────────────────────────────┘
 *
 * Drift handling: when held_qty < kite_qty_for_ticker (user externally
 * sold some), shows a yellow drift chip "NQ N · Kite M" so the
 * discrepancy is visible without forcing a separate UI state.
 */

const fmtRupees = (n, opts = {}) => {
  if (n == null || isNaN(n)) return '—';
  const fixed = opts.compact && Math.abs(n) >= 100000;
  if (fixed) return `₹${(n / 100000).toFixed(2)}L`;
  return `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

const fmtPct = (n) => {
  if (n == null || isNaN(n)) return '—';
  const sign = n > 0 ? '+' : '';
  return `${sign}${Number(n).toFixed(2)}%`;
};

// Map status_for_user → StatusChip tone + label
const STATUS_PRESENTATION = {
  ACTIONABLE_SELL:      { tone: 'bear',  label: 'SELL NOW' },
  HOLDING:              { tone: 'brand', label: 'HOLDING' },
  HOLDING_PARTIAL_SOLD: { tone: 'warn',  label: 'DRIFT' },
  ACTIONABLE_BUY:       { tone: 'info',  label: 'BUY' },
  INFORMATIONAL:        { tone: 'muted', label: 'INFO' },
  MISSED:               { tone: 'muted', label: 'MISSED' },
};

export function PositionCard({ position, onSell, onCardClick, className }) {
  if (!position) return null;
  const {
    ticker,
    held_qty,
    nq_recorded_qty,
    kite_qty_for_ticker,
    avg_fill_price,
    last_price,
    pnl_rupees,
    pnl_pct,
    entry,
    stop,
    original_stop,
    target,
    original_target,
    days_since,
    days_left,
    status_for_user,
    sell_guidance,
  } = position;

  const presentation =
    STATUS_PRESENTATION[status_for_user] ?? STATUS_PRESENTATION.HOLDING;

  const pnlColor =
    pnl_rupees == null || pnl_rupees === 0
      ? 'var(--text-2)'
      : pnl_rupees > 0
      ? 'var(--bull)'
      : 'var(--bear)';

  const stopMoved = original_stop != null && stop != null && Number(original_stop) !== Number(stop);
  const driftDetected = status_for_user === 'HOLDING_PARTIAL_SOLD';

  const handleSell = (e) => {
    e?.stopPropagation?.();
    onSell?.(position);
  };

  return (
    <GlassCard
      tier={1}
      hoverLift={!!onCardClick}
      interactive={!!onCardClick}
      onClick={onCardClick}
      className={cn('p-4 flex flex-col gap-3', className)}
    >
      {/* Row 1: ticker + status + P&L % */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="t-display-card-h1 font-semibold" style={{ color: 'var(--text-1)' }}>
              {ticker}
            </span>
            <StatusChip tone={presentation.tone}>{presentation.label}</StatusChip>
            {driftDetected && (
              <StatusChip tone="warn">
                NQ {nq_recorded_qty} · Kite {kite_qty_for_ticker}
              </StatusChip>
            )}
          </div>
          <div className="t-ui-micro mt-1 opacity-80" style={{ color: 'var(--text-2)' }}>
            {held_qty} × {fmtRupees(avg_fill_price)}
            {last_price != null && (
              <>
                {' → '}
                <span style={{ color: 'var(--text-1)' }}>{fmtRupees(last_price)}</span>
              </>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="t-display-card-h1 font-mono" style={{ color: pnlColor }}>
            {fmtPct(pnl_pct)}
          </div>
          <div className="t-ui-micro font-mono" style={{ color: pnlColor }}>
            {fmtRupees(pnl_rupees, { compact: true })}
          </div>
        </div>
      </div>

      {/* Row 2: signal context (entry · stop · target · days) */}
      <div
        className="grid grid-cols-2 sm:grid-cols-4 gap-2 t-ui-micro"
        style={{ color: 'var(--text-3)' }}
      >
        <div>
          <div className="opacity-70">Entry</div>
          <div style={{ color: 'var(--text-2)' }} className="font-mono">
            {fmtRupees(entry)}
          </div>
        </div>
        <div>
          <div className="opacity-70">Stop</div>
          <div style={{ color: 'var(--text-2)' }} className="font-mono">
            {fmtRupees(stop)}
            {stopMoved && (
              <span className="opacity-60 ml-1">(was {fmtRupees(original_stop)})</span>
            )}
          </div>
        </div>
        <div>
          <div className="opacity-70">Target</div>
          <div style={{ color: 'var(--text-2)' }} className="font-mono">
            {fmtRupees(original_target ?? target)}
          </div>
        </div>
        <div>
          <div className="opacity-70">Days</div>
          <div style={{ color: 'var(--text-2)' }} className="font-mono">
            {days_since ?? '—'}
            {days_left != null && (
              <span className="opacity-60"> / {days_left} left</span>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: optional sell guidance banner */}
      {sell_guidance && (
        <SellGuidanceBanner
          guidance={sell_guidance}
          lastPrice={last_price}
          onSell={onSell ? handleSell : undefined}
        />
      )}

      {/* Row 4: drift reconciliation (only when status_for_user == HOLDING_PARTIAL_SOLD) */}
      {driftDetected && (
        <ReconcileDriftPanel
          signalId={position.signal_id}
          ticker={ticker}
          driftQty={Math.max(0, (nq_recorded_qty ?? 0) - (kite_qty_for_ticker ?? 0))}
          lastPrice={last_price}
        />
      )}
    </GlassCard>
  );
}

/**
 * ReconcileDriftPanel — collapsed by default. When opened, shows two
 * inputs (qty + sell price) and a confirm button that POSTs to
 * /api/nq-orders/reconcile to synthesize a SELL row matching the user's
 * external close.
 *
 * After success the NQ position list refreshes — this card will
 * disappear or flip to HOLDING/CLOSED automatically as the join service
 * picks up the new SELL row.
 */
function ReconcileDriftPanel({ signalId, ticker, driftQty, lastPrice }) {
  const [open, setOpen] = useState(false);
  const [qty, setQty] = useState(driftQty || 0);
  const [price, setPrice] = useState(lastPrice ?? '');
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      reconcileDrift({
        signal_id: signalId,
        qty: Number(qty),
        fill_price: Number(price),
      }),
    onSuccess: () => {
      toast.success(`Reconciled ${qty} ${ticker}`, {
        description: 'Position records now match your Kite holdings.',
      });
      qc.invalidateQueries({ queryKey: NQ_POSITIONS_KEY });
      qc.invalidateQueries({ queryKey: EXTERNAL_HOLDINGS_KEY });
      qc.invalidateQueries({ queryKey: NQ_ORDERS_KEY });
      setOpen(false);
    },
    onError: (err) => {
      toast.error('Reconciliation failed', {
        description: err?.message || 'Try again or check the price.',
      });
    },
  });

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="t-ui-micro"
        style={{
          background: 'transparent',
          border: '1px dashed var(--warn)',
          color: 'var(--warn)',
          borderRadius: 'var(--r-chip)',
          padding: '4px 10px',
          cursor: 'pointer',
          alignSelf: 'flex-start',
          letterSpacing: '0.06em',
        }}
      >
        RECONCILE DRIFT ({driftQty} EXTERNAL)
      </button>
    );
  }

  return (
    <div
      className="flex flex-col"
      style={{
        gap: 8,
        background: 'var(--warn-soft)',
        border: '1px solid oklch(68% 0.18 40 / 0.35)',
        borderRadius: 'var(--r-chip)',
        padding: 10,
      }}
    >
      <div className="t-ui-micro" style={{ color: 'var(--warn)' }}>
        Mark as sold externally — records the SELL at your fill price.
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col" style={{ gap: 2 }}>
          <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>Qty</span>
          <input
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="t-ui-body"
            style={{
              background: 'var(--surface-2)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-chip)',
              padding: '4px 8px',
              color: 'var(--text-1)',
            }}
          />
        </label>
        <label className="flex flex-col" style={{ gap: 2 }}>
          <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>Fill price ₹</span>
          <input
            type="number"
            step="0.01"
            min={0}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="t-ui-body"
            style={{
              background: 'var(--surface-2)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-chip)',
              padding: '4px 8px',
              color: 'var(--text-1)',
            }}
          />
        </label>
      </div>
      <div className="flex" style={{ gap: 8 }}>
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !qty || !price}
          className="t-ui-callout"
          style={{
            background: 'var(--warn)',
            color: 'var(--surface-0)',
            border: '1px solid var(--warn)',
            borderRadius: 'var(--r-chip)',
            padding: '4px 12px',
            cursor: mutation.isPending ? 'wait' : 'pointer',
            fontWeight: 600,
            opacity: mutation.isPending || !qty || !price ? 0.6 : 1,
          }}
        >
          {mutation.isPending ? 'Saving…' : 'Confirm'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          disabled={mutation.isPending}
          className="t-ui-callout"
          style={{
            background: 'transparent',
            color: 'var(--text-2)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-chip)',
            padding: '4px 12px',
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default PositionCard;
