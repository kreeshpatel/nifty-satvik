/**
 * OrdersV2 — Phase 6 redesign of the Orders page.
 *
 * Lists today's Kite orders with filter pills (All / Open / Complete /
 * Cancelled / Rejected), inline cancel action on still-open orders, and
 * WS-patched live status updates via the shared queryClient invalidation
 * triggered by ws_manager order_update broadcasts.
 *
 * Layout:
 *   Page title + Kite chip
 *   ────────────────────────────────────────
 *   Filter pills + summary + refresh
 *   ────────────────────────────────────────
 *   DataTable bound to /kite/orders
 *
 * No-Kite users see an empty state with Connect CTA.
 */
import React, { useContext, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plug, RefreshCcw, Inbox, X } from 'lucide-react';
import { toast } from 'sonner';
import { PageShell } from '@/components/shared/PageShell';
import { DataTable } from '@/components/shared/DataTable';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { useKiteOrders, KITE_ORDERS_KEY } from '@/hooks/queries/useKiteOrders';
import { cancelOrder } from '@/services/api';
import { KiteContext } from '@/App';
import { fmtPrice, fmtRelTime } from '@/lib/format';

// Each filter carries its own semantic tone so the pills read chromatically
// when active (Open → info-blue, Complete → bull-green, etc.) instead of
// every active pill defaulting to brand-amber.
const FILTER_PILLS = [
  { value: 'ALL',       label: 'All',       tone: 'brand' },
  { value: 'OPEN',      label: 'Open',      tone: 'info' },
  { value: 'COMPLETE',  label: 'Complete',  tone: 'bull' },
  { value: 'CANCELLED', label: 'Cancelled', tone: 'muted' },
  { value: 'REJECTED',  label: 'Rejected',  tone: 'bear' },
];

// Tone → palette mapping. The `soft` / `edge` / `text` triple drives the
// active pill background, border, and text color in a single lookup so the
// JSX stays readable.
const PILL_TONE = {
  brand: { soft: 'var(--brand-soft)', edge: 'var(--brand-edge)',           text: 'var(--brand-hi)', dot: 'var(--brand)', halo: 'var(--brand-soft)' },
  info:  { soft: 'var(--info-soft)',  edge: 'oklch(78% 0.11 230 / 0.32)',  text: 'var(--info)',     dot: 'var(--info)',  halo: 'var(--info-soft)' },
  bull:  { soft: 'var(--bull-soft)',  edge: 'oklch(72% 0.19 145 / 0.32)',  text: 'var(--bull)',     dot: 'var(--bull)',  halo: 'var(--bull-soft)' },
  warn:  { soft: 'var(--warn-soft)',  edge: 'oklch(68% 0.18 40 / 0.32)',   text: 'var(--warn)',     dot: 'var(--warn)',  halo: 'var(--warn-soft)' },
  bear:  { soft: 'var(--bear-soft)',  edge: 'oklch(66% 0.21 25 / 0.32)',   text: 'var(--bear)',     dot: 'var(--bear)',  halo: 'var(--bear-soft)' },
  muted: { soft: 'var(--surface-2)',  edge: 'var(--edge-2)',                text: 'var(--text-2)',   dot: 'var(--text-4)', halo: 'var(--edge-2)' },
};

function statusToFilter(s) {
  const u = String(s || '').toUpperCase();
  if (u === 'COMPLETE' || u === 'COMPLETED') return 'COMPLETE';
  if (u === 'CANCELLED' || u === 'CANCELLED AMO') return 'CANCELLED';
  if (u === 'REJECTED') return 'REJECTED';
  return 'OPEN';   // OPEN, TRIGGER PENDING, MODIFIED, etc.
}

function statusToTone(s) {
  const u = String(s || '').toUpperCase();
  if (u === 'COMPLETE' || u === 'COMPLETED') return 'bull';
  if (u === 'REJECTED') return 'bear';
  if (u === 'CANCELLED') return 'muted';
  if (u === 'OPEN' || u === 'TRIGGER PENDING') return 'info';
  return 'muted';
}

export default function OrdersV2() {
  const kite = useContext(KiteContext);
  const ordersQuery = useKiteOrders({ enabled: !!kite?.connected });
  const qc = useQueryClient();
  const [filter, setFilter] = useState('ALL');

  const cancelMutation = useMutation({
    mutationFn: ({ variety, order_id }) => cancelOrder(variety || 'regular', order_id),
    onSuccess: (_data, { ticker }) => {
      toast.success(`Cancellation sent`, { description: ticker });
      qc.invalidateQueries({ queryKey: KITE_ORDERS_KEY });
    },
    onError: (err) => {
      toast.error(`Cancel failed`, { description: err?.message || 'Try again from Kite directly.' });
    },
  });

  const orders = useMemo(() => ordersQuery.data ?? [], [ordersQuery.data]);

  // Counts per filter for the pill badges.
  const counts = useMemo(() => {
    const c = { ALL: orders.length, OPEN: 0, COMPLETE: 0, CANCELLED: 0, REJECTED: 0 };
    for (const o of orders) c[statusToFilter(o.status)]++;
    return c;
  }, [orders]);

  const filtered = useMemo(() => {
    if (filter === 'ALL') return orders;
    return orders.filter((o) => statusToFilter(o.status) === filter);
  }, [orders, filter]);

  return (
    <PageShell title="Orders" heroTone="bull">
      <header style={{ paddingTop: 24, paddingBottom: 16 }}>
        <h1 className="t-title-1" style={{ margin: 0, color: 'var(--text-1)' }}>Orders</h1>
        <div
          className="t-ui-footnote flex items-center flex-wrap"
          style={{ color: 'var(--text-3)', marginTop: 6, gap: 10 }}
        >
          {kite?.connected ? (
            <StatusChip tone="bull">KITE CONNECTED</StatusChip>
          ) : (
            <StatusChip tone="muted">DISCONNECTED</StatusChip>
          )}
          {ordersQuery.dataUpdatedAt && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>Updated {fmtRelTime(new Date(ordersQuery.dataUpdatedAt))}</span>
            </>
          )}
        </div>
      </header>

      {!kite?.connected ? (
        <EmptyCard
          variant="warn"
          icon={<Plug size={16} strokeWidth={1.75} />}
          title="Connect Kite to see your orders"
          body="Order book is populated from Zerodha in real time. Once connected, orders placed through NiftyQuant or directly on kite.zerodha.com appear here."
          action={
            <button
              type="button"
              onClick={kite?.connect}
              className="t-ui-callout"
              style={{
                padding: '10px 18px',
                background: 'var(--brand)',
                color: 'var(--brand-fg)',
                border: '1px solid var(--brand)',
                borderRadius: 'var(--r-chip)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Connect Kite →
            </button>
          }
        />
      ) : (
        <>
          {/* Today's-orders summary line — semantic dot prefix matches the
              SignalsV2 SectionFrame pattern, count tints toward the active
              filter's tone so the heading reads chromatically. */}
          {(() => {
            const activeTone = PILL_TONE[FILTER_PILLS.find((p) => p.value === filter)?.tone] || PILL_TONE.brand;
            return (
              <div
                className="flex items-baseline flex-wrap"
                style={{ gap: 10, marginBottom: 12 }}
              >
                <h2
                  className="t-title-2 flex items-baseline"
                  style={{ margin: 0, color: 'var(--text-1)' }}
                >
                  <span
                    aria-hidden="true"
                    style={{
                      display: 'inline-block',
                      width: 7,
                      height: 7,
                      borderRadius: '50%',
                      background: activeTone.dot,
                      boxShadow: `0 0 0 3px ${activeTone.halo}`,
                      flexShrink: 0,
                      marginRight: 7,
                      marginLeft: 3,
                      transform: 'translateY(-2px)',
                    }}
                  />
                  Today's Orders
                </h2>
                <span
                  className="t-num-small"
                  style={{ color: activeTone.text, fontFamily: 'var(--font-mono)' }}
                >
                  {filter === 'ALL' ? counts.ALL : counts[filter] ?? 0}
                </span>
                <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>
                  {filter === 'ALL' ? 'TOTAL' : filter}
                </span>
              </div>
            );
          })()}

          {/* Filter pills + refresh */}
          <section
            className="flex items-center justify-between flex-wrap"
            style={{ gap: 12, marginBottom: 16 }}
          >
            <div className="flex items-center flex-wrap" style={{ gap: 6 }}>
              {FILTER_PILLS.map((p) => {
                const active = p.value === filter;
                const count = counts[p.value] ?? 0;
                const t = PILL_TONE[p.tone] || PILL_TONE.muted;
                return (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setFilter(p.value)}
                    aria-pressed={active}
                    className="t-ui-callout"
                    style={{
                      padding: '6px 12px',
                      background: active ? t.soft : 'transparent',
                      color: active ? t.text : 'var(--text-2)',
                      border: `1px solid ${active ? t.edge : 'var(--edge-1)'}`,
                      borderRadius: 'var(--r-chip)',
                      cursor: 'pointer',
                      fontWeight: active ? 600 : 500,
                      transition: 'all var(--dur-hover) var(--ease-out-cubic)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    {/* small tone dot — present even when inactive so the
                        viewer can scan the pill row chromatically without
                        having to click through each filter. */}
                    <span
                      aria-hidden="true"
                      style={{
                        display: 'inline-block',
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: t.dot,
                        opacity: active ? 1 : 0.65,
                        flexShrink: 0,
                      }}
                    />
                    {p.label}
                    {count > 0 && (
                      <span
                        className="t-num-small"
                        style={{
                          padding: '0 6px',
                          background: active ? t.text : 'var(--surface-3)',
                          color: active ? 'var(--surface-0)' : 'var(--text-2)',
                          borderRadius: 9999,
                          fontSize: 10,
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            <button
              type="button"
              onClick={() => ordersQuery.refetch()}
              disabled={ordersQuery.isFetching}
              aria-label="Refresh orders"
              style={{
                background: 'transparent',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
                padding: 8,
                color: 'var(--text-2)',
                cursor: ordersQuery.isFetching ? 'wait' : 'pointer',
              }}
            >
              <RefreshCcw
                size={14}
                strokeWidth={1.75}
                style={{
                  animation: ordersQuery.isFetching ? 'spin 1s linear infinite' : 'none',
                }}
              />
            </button>
          </section>

          {/* Table or empty state */}
          {ordersQuery.isLoading ? (
            <TableSkeleton rows={6} />
          ) : filtered.length === 0 ? (
            <EmptyCard
              variant="muted"
              icon={<Inbox size={16} strokeWidth={1.75} />}
              title={
                filter === 'ALL'
                  ? 'No orders today'
                  : `No ${FILTER_PILLS.find((p) => p.value === filter)?.label.toLowerCase()} orders`
              }
              body={
                filter === 'ALL'
                  ? 'Orders placed today through NiftyQuant or kite.zerodha.com will appear here.'
                  : 'Switch the filter to see other orders, or place a new order from Signals.'
              }
            />
          ) : (
            <DataTable
              rows={filtered.map((o, i) => ({ id: o.order_id || i, ...o }))}
              initialSort={{ key: 'order_timestamp', dir: 'desc' }}
              columns={[
                {
                  key: 'order_timestamp',
                  header: 'Time',
                  sortable: true,
                  width: '110px',
                  render: (v) => (
                    <span className="t-ui-footnote" style={{ color: 'var(--text-2)' }}>
                      {v ? new Date(v).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '—'}
                    </span>
                  ),
                },
                { key: 'tradingsymbol', header: 'Ticker', sortable: true, width: '140px' },
                {
                  key: 'transaction_type',
                  header: 'Side',
                  width: '70px',
                  render: (v) => (
                    <StatusChip tone={v === 'BUY' ? 'bull' : 'bear'}>{v}</StatusChip>
                  ),
                },
                { key: 'quantity', header: 'Qty', sortable: true, align: 'right', width: '80px' },
                {
                  key: 'price',
                  header: 'Price',
                  sortable: true,
                  align: 'right',
                  render: (v, row) => fmtPrice(v || row.average_price || 0),
                },
                { key: 'order_type', header: 'Type', width: '80px' },
                { key: 'product', header: 'Product', width: '80px' },
                {
                  key: 'status',
                  header: 'Status',
                  render: (v) => <StatusChip tone={statusToTone(v)}>{String(v || '').toUpperCase()}</StatusChip>,
                },
                {
                  key: '_action',
                  header: '',
                  width: '60px',
                  align: 'right',
                  render: (_, row) => {
                    const cancellable = statusToFilter(row.status) === 'OPEN';
                    if (!cancellable) return null;
                    const isCancelling = cancelMutation.isPending && cancelMutation.variables?.order_id === row.order_id;
                    return (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          cancelMutation.mutate({
                            variety: row.variety || 'regular',
                            order_id: row.order_id,
                            ticker: row.tradingsymbol,
                          });
                        }}
                        disabled={isCancelling}
                        aria-label={`Cancel order for ${row.tradingsymbol}`}
                        title="Cancel order"
                        style={{
                          background: 'transparent',
                          border: '1px solid var(--edge-1)',
                          borderRadius: 'var(--r-chip)',
                          padding: 4,
                          color: 'var(--bear)',
                          cursor: isCancelling ? 'wait' : 'pointer',
                          width: 24,
                          height: 24,
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <X size={12} strokeWidth={2} />
                      </button>
                    );
                  },
                },
              ]}
            />
          )}
        </>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </PageShell>
  );
}

function TableSkeleton({ rows = 6 }) {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 16,
        animation: 'skelPulse 1.8s ease-in-out infinite',
      }}
    >
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 40,
            display: 'grid',
            gridTemplateColumns: 'repeat(8, 1fr)',
            gap: 12,
            alignItems: 'center',
            borderBottom: i === rows - 1 ? 'none' : '1px solid var(--edge-1)',
          }}
        >
          {Array.from({ length: 8 }).map((__, j) => (
            <div key={j} style={{ height: 12, background: 'var(--surface-2)', borderRadius: 4 }} />
          ))}
        </div>
      ))}
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}
