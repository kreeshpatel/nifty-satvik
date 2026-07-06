/**
 * JournalV2 — Phase 7 redesign of the Trading Journal.
 *
 * Per product decision (locked 2026-04-24): Journal is auto-populated from
 * orders placed through Nifty Satvik Buy/Sell buttons (`nq_orders` table).
 * External Kite trades are NOT shown — Journal is for trades the user
 * actively chose through our signal flow.
 *
 * Layout:
 *   Page title + summary chip
 *   ────────────────────────────────────────
 *   • Performance — KPI cards: Win rate · Avg P&L · Discipline · Open
 *   ────────────────────────────────────────
 *   Filter pills: All · With notes · Wins · Losses · Open
 *   ────────────────────────────────────────
 *   • Entries — Trade entries grid with rationale affordance
 *
 * Lifecycle:
 *   - Each completed nq_orders row becomes a TradeEntry card
 *   - Click "Add notes" / "Edit notes" → drawer with textarea
 *   - Saving fires PATCH /api/nq-orders/:id/notes
 */
import React, { useMemo, useState } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { BookOpen, X, Edit3, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { PageShell } from '@/components/shared/PageShell';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { useNQOrders, useUpdateNQOrderNotes } from '@/hooks/queries/useNQOrders';
import { fmtPrice, fmtINR, fmtRelTime } from '@/lib/format';

const FILTERS = [
  { value: 'ALL',        label: 'All',        tone: 'muted' },
  { value: 'WITH_NOTES', label: 'With notes', tone: 'brand' },
  { value: 'WINS',       label: 'Wins',       tone: 'bull' },
  { value: 'LOSSES',     label: 'Losses',     tone: 'bear' },
  { value: 'OPEN',       label: 'Open',       tone: 'info' },
];

// Section header tone map — mirrors the SignalsV2 SectionFrame palette so the
// dashboard reads chromatically across pages. Each section gets a colored
// dot + halo + count tint; bodies stay quiet.
const SECTION_TONES = {
  brand: { dot: 'var(--brand)', halo: 'var(--brand-soft)', count: 'var(--brand)' },
  bull:  { dot: 'var(--bull)',  halo: 'var(--bull-soft)',  count: 'var(--bull)' },
  info:  { dot: 'var(--info)',  halo: 'var(--info-soft)',  count: 'var(--info)' },
  warn:  { dot: 'var(--warn)',  halo: 'var(--warn-soft)',  count: 'var(--warn)' },
  bear:  { dot: 'var(--bear)',  halo: 'var(--bear-soft)',  count: 'var(--bear)' },
  muted: { dot: 'var(--text-4)', halo: 'var(--edge-2)',    count: 'var(--text-3)' },
};

// Pair buys with sells per ticker (FIFO) so we can compute realised P&L
// on each SELL row. Returns a map order_id → { matched_buy_price, pnl }.
function computeRealised(orders) {
  const buysByTicker = {};
  const result = {};
  // Process chronologically (placed_at asc) so FIFO matching is correct.
  const chrono = [...orders].sort(
    (a, b) => new Date(a.placed_at).getTime() - new Date(b.placed_at).getTime(),
  );
  for (const o of chrono) {
    if (o.action === 'BUY') {
      buysByTicker[o.ticker] = buysByTicker[o.ticker] || [];
      buysByTicker[o.ticker].push({ ...o, remaining: o.qty });
      continue;
    }
    if (o.action === 'SELL' && o.status === 'COMPLETE') {
      let remaining = o.qty;
      let totalCost = 0;
      let qtyMatched = 0;
      const queue = buysByTicker[o.ticker] || [];
      while (remaining > 0 && queue.length > 0) {
        const b = queue[0];
        const m = Math.min(remaining, b.remaining);
        totalCost += m * (b.fill_price || b.placed_price || 0);
        b.remaining -= m;
        remaining -= m;
        qtyMatched += m;
        if (b.remaining <= 0) queue.shift();
      }
      const sellRev = qtyMatched * (o.fill_price || o.placed_price || 0);
      const pnl = sellRev - totalCost;
      result[o.id] = {
        pnl,
        avgBuyPrice: qtyMatched > 0 ? totalCost / qtyMatched : null,
      };
    }
  }
  return result;
}

export default function JournalV2() {
  const ordersQuery = useNQOrders();
  // Stable ref for downstream useMemo dependencies.
  const orders = useMemo(() => ordersQuery.data ?? [], [ordersQuery.data]);
  const realised = useMemo(() => computeRealised(orders), [orders]);

  const [filter, setFilter] = useState('ALL');
  const [editingOrder, setEditingOrder] = useState(null);

  // Aggregate stats — always against the FULL list, not the filtered view.
  const stats = useMemo(() => {
    const completed = orders.filter((o) => o.status === 'COMPLETE');
    const sells = completed.filter((o) => o.action === 'SELL');
    const wins = sells.filter((o) => (realised[o.id]?.pnl || 0) > 0).length;
    const losses = sells.filter((o) => (realised[o.id]?.pnl || 0) < 0).length;
    const totalPnl = sells.reduce((sum, o) => sum + (realised[o.id]?.pnl || 0), 0);
    const open = orders.filter((o) => o.action === 'BUY' && o.status === 'COMPLETE');
    const noted = completed.filter((o) => o.notes && o.notes.trim()).length;
    const winRate = sells.length > 0 ? (wins / sells.length) * 100 : 0;
    const avgPnl = sells.length > 0 ? totalPnl / sells.length : 0;
    const discipline = completed.length > 0 ? (noted / completed.length) * 100 : 0;
    return {
      total: completed.length,
      wins,
      losses,
      sells: sells.length,
      open: open.length,
      totalPnl,
      winRate,
      avgPnl,
      discipline,
      noted,
    };
  }, [orders, realised]);

  const filtered = useMemo(() => {
    return orders.filter((o) => {
      if (filter === 'WITH_NOTES') return o.notes && o.notes.trim();
      if (filter === 'WINS') return o.action === 'SELL' && (realised[o.id]?.pnl || 0) > 0;
      if (filter === 'LOSSES') return o.action === 'SELL' && (realised[o.id]?.pnl || 0) < 0;
      if (filter === 'OPEN') return o.action === 'BUY' && o.status === 'COMPLETE';
      return true;
    });
  }, [orders, filter, realised]);

  const hasAnyTrades = stats.total > 0;

  // Mock data fallback if no orders
  const displayOrders = filtered.length > 0 ? filtered : [
    {
      id: 'mock-1',
      ticker: 'RELIANCE',
      action: 'SELL',
      qty: 5,
      placed_price: 2948.20,
      fill_price: 2999.50,
      placed_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      status: 'COMPLETE',
      notes: 'Textbook breakout, volume confirmed. Sized correctly per signal. Sold half at +5%, trailed remainder.',
    },
    {
      id: 'mock-2',
      ticker: 'ASIANPAINT',
      action: 'SELL',
      qty: 6,
      placed_price: 2950.00,
      fill_price: 2820.00,
      placed_at: new Date(Date.now() - 12 * 24 * 60 * 60 * 1000),
      status: 'COMPLETE',
      notes: 'Rating cut overnight. Lesson: macro × sector dissent → size down 30%.',
    },
  ];

  return (
    <PageShell title="Journal" heroTone="warn">
      {/* HEADER — title left, "+ New entry" CTA right */}
      <header style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 28, fontWeight: 600, color: 'var(--text-1)', fontFamily: 'var(--font-display)', letterSpacing: '-0.018em' }}>Journal</h1>
        <button
          onClick={() => setEditingOrder({ ticker: '', action: 'BUY', qty: 0, placed_price: 0, status: 'DRAFT', notes: '' })}
          style={{
            background: 'var(--brand-grad)',
            color: '#fff',
            border: 'none',
            padding: '9px 18px',
            borderRadius: 999,
            fontSize: 13,
            fontWeight: 600,
            boxShadow: '0 6px 18px rgba(79,140,255,0.4)',
            cursor: 'pointer',
          }}
        >
          + New entry
        </button>
      </header>

      {/* ─── PERFORMANCE (conditionally shown) ─── */}
      {hasAnyTrades && (
        <>
          <SectionHead
            tone="brand"
            title="Performance"
            count={stats.sells}
            subtitle={`${stats.sells} closed trade${stats.sells !== 1 ? 's' : ''} matched, ${stats.open} still open.`}
          />
          <section
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 12,
              marginBottom: 28,
            }}
          >
            <StatTile
              label="Win rate"
              value={`${stats.winRate.toFixed(0)}%`}
              sub={`${stats.wins}W · ${stats.losses}L`}
              tone={stats.winRate >= 60 ? 'bull' : stats.winRate >= 40 ? 'muted' : 'bear'}
            />
            <StatTile
              label="Avg P&L"
              value={`${stats.avgPnl >= 0 ? '+' : ''}${fmtINR(stats.avgPnl)}`}
              sub="per closed trade"
              tone={stats.avgPnl >= 0 ? 'bull' : 'bear'}
            />
            <StatTile
              label="Discipline"
              value={`${stats.discipline.toFixed(0)}%`}
              sub={`${stats.noted}/${stats.total} entries noted`}
              tone={stats.discipline >= 70 ? 'bull' : stats.discipline >= 40 ? 'brand' : 'warn'}
            />
            <StatTile
              label="Open"
              value={String(stats.open)}
              sub="positions still in play"
              tone="info"
            />
          </section>
        </>
      )}

      {/* ─── ENTRIES (kit-style) ─── */}
      {ordersQuery.isLoading ? (
        <EntriesSkeleton />
      ) : ordersQuery.error ? (
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={16} strokeWidth={1.75} />}
          title="Couldn't load journal"
          body={ordersQuery.error?.message || 'Try refreshing.'}
        />
      ) : filtered.length === 0 && filter === 'ALL' ? (
        <EmptyCard
          variant="info"
          icon={<BookOpen size={16} strokeWidth={1.75} />}
          title="Your journal is empty"
          body="Only orders placed through Nifty Satvik Buy/Sell appear here. External Kite trades are tracked separately on Portfolio."
          action={
            <Link
              to="/premove"
              className="t-ui-callout"
              style={{
                padding: '10px 18px',
                background: 'var(--brand)',
                color: 'var(--brand-fg)',
                border: '1px solid var(--brand)',
                borderRadius: 'var(--r-chip)',
                textDecoration: 'none',
                fontWeight: 600,
                display: 'inline-block',
              }}
            >
              Browse signals →
            </Link>
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyCard
          variant="muted"
          icon={<BookOpen size={16} strokeWidth={1.75} />}
          title={`No ${FILTERS.find((f) => f.value === filter)?.label.toLowerCase()} yet`}
          body='Switch to "All" to see every entry, or place more trades to populate this view.'
        />
      ) : (
        <section style={{ display: 'grid', gap: 12 }}>
          {displayOrders.map((o) => (
            <TradeEntryCard
              key={o.id}
              order={o}
              realised={realised[o.id]}
              onEdit={() => setEditingOrder(o)}
            />
          ))}
        </section>
      )}

      {/* NOTES EDITOR */}
      <NotesEditor
        order={editingOrder}
        open={!!editingOrder}
        onOpenChange={(open) => !open && setEditingOrder(null)}
      />
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// SECTION HEADER (tier-toned, mirrors SignalsV2 SectionFrame)
// ══════════════════════════════════════════════════════════════

function SectionHead({ tone = 'muted', title, count, subtitle }) {
  const t = SECTION_TONES[tone] || SECTION_TONES.muted;
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="flex items-baseline" style={{ gap: 10 }}>
        <h2 className="t-title-2 flex items-baseline" style={{ margin: 0, color: 'var(--text-1)' }}>
          <span
            aria-hidden="true"
            style={{
              display: 'inline-block',
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: t.dot,
              boxShadow: `0 0 0 3px ${t.halo}`,
              marginRight: 10,
              marginLeft: 3,
              transform: 'translateY(-2px)',
              flexShrink: 0,
            }}
          />
          {title}
        </h2>
        {count != null && (
          <span
            className="t-num-small"
            style={{
              color: t.count,
              fontFamily: 'var(--font-mono)',
              fontWeight: 500,
            }}
          >
            {count}
          </span>
        )}
      </div>
      {subtitle && (
        <p
          className="t-ui-footnote"
          style={{ color: 'var(--text-2)', margin: '4px 0 0 0', maxWidth: '76ch' }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// CARDS / TILES
// ══════════════════════════════════════════════════════════════

// Compact KPI tile — promoted from old StatPill to use the t-num-hero scale
// + Berkeley Mono numbers. Quiet halo at the bottom carries the tone without
// adding a side stripe (banned). Sub text in --text-3.
function StatTile({ label, value, sub, tone = 'muted' }) {
  const t = SECTION_TONES[tone] || SECTION_TONES.muted;
  const valueColor =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    tone === 'warn' ? 'var(--warn)' :
    tone === 'info' ? 'var(--info)' :
    tone === 'brand' ? 'var(--brand-hi)' :
    'var(--text-1)';
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: '14px 16px',
        boxShadow: 'var(--shadow-sm)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Tone halo — top-right corner glow, no side stripe (banned). */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: -40,
          right: -40,
          width: 100,
          height: 100,
          background: t.halo,
          borderRadius: '50%',
          pointerEvents: 'none',
          opacity: tone === 'muted' ? 0 : 1,
        }}
      />
      <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6, position: 'relative' }}>
        {label}
      </div>
      <div
        className="t-num-hero"
        style={{ color: valueColor, position: 'relative', fontSize: 28, lineHeight: 1.1 }}
      >
        {value}
      </div>
      {sub && (
        <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 4, position: 'relative' }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function TradeEntryCard({ order, realised, onEdit }) {
  const isSell = order.action === 'SELL';
  const fill = order.fill_price ?? order.placed_price;
  const pnl = realised?.pnl ?? null;
  const pnlPct = pnl != null && realised?.avgBuyPrice
    ? ((pnl / (realised.avgBuyPrice * order.qty)) * 100)
    : null;
  const hasRealisedPnl = isSell && pnl != null;

  // Determine result chip tone and label
  let resultTone = 'muted';
  let resultLabel = 'PENDING';
  if (hasRealisedPnl) {
    resultTone = pnl >= 0 ? 'bull' : 'bear';
    resultLabel = `${isSell ? 'EXIT' : order.action} ${pnl >= 0 ? '+' : ''}${pnlPct?.toFixed(1)}%`;
  }

  return (
    <article
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 20,
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Row 1: Title + timestamp on left, result chip on right */}
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <Link
            to={`/stock/${order.ticker}`}
            style={{
              fontSize: 16,
              fontWeight: 500,
              color: 'var(--text-1)',
              textDecoration: 'none',
              fontFamily: 'var(--font-display)',
            }}
          >
            {order.ticker}
            {isSell ? ' exited' : ' entry'}
          </Link>
          <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-3)' }}>
            {order.placed_at ? fmtRelTime(new Date(order.placed_at)) : '—'}
          </span>
        </div>
        {/* Result chip */}
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            padding: '3px 8px',
            background: resultTone === 'bull' ? 'var(--bull-soft)' : resultTone === 'bear' ? 'var(--bear-soft)' : 'var(--surface-2)',
            color: resultTone === 'bull' ? 'var(--bull)' : resultTone === 'bear' ? 'var(--bear)' : 'var(--text-2)',
            borderRadius: 999,
            letterSpacing: '0.06em',
          }}
        >
          {resultLabel}
        </span>
      </div>

      {/* Body text */}
      <div style={{ fontSize: '13.5px', lineHeight: 1.6, color: 'var(--text-2)', marginBottom: 12 }}>
        {order.notes ? (
          <p style={{ margin: 0, display: '-webkit-box', WebkitLineClamp: 4, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {order.notes}
          </p>
        ) : (
          <p style={{ margin: 0, fontStyle: 'italic', color: 'var(--text-4)' }}>
            No rationale yet — {isSell ? 'what was the exit reason?' : 'what was the setup?'}
          </p>
        )}
      </div>

      {/* Edit link */}
      <button
        type="button"
        onClick={onEdit}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'var(--brand-hi)',
          padding: 0,
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          fontWeight: 600,
          fontSize: 12,
        }}
      >
        <Edit3 size={12} strokeWidth={1.75} />
        {order.notes ? 'Edit notes' : 'Add notes'}
      </button>
    </article>
  );
}

function Cell({ label, value, tone = 'neutral' }) {
  const color =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    'var(--text-1)';
  return (
    <div
      style={{
        background: 'var(--surface-2)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-chip)',
        padding: '8px 10px',
      }}
    >
      <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 4 }}>
        {label}
      </div>
      <div className="t-num-body" style={{ color, fontSize: 13 }}>{value}</div>
    </div>
  );
}

function StatusTone({ status }) {
  const u = String(status || '').toUpperCase();
  const tone =
    u === 'COMPLETE' ? 'bull' :
    u === 'REJECTED' ? 'bear' :
    u === 'CANCELLED' ? 'muted' :
    u === 'OPEN' ? 'info' :
    'muted';
  return <StatusChip tone={tone}>{u || 'PENDING'}</StatusChip>;
}

// ══════════════════════════════════════════════════════════════
// NOTES EDITOR DRAWER
// ══════════════════════════════════════════════════════════════

function NotesEditor({ order, open, onOpenChange }) {
  const [draft, setDraft] = React.useState('');
  const updateNotes = useUpdateNQOrderNotes();

  React.useEffect(() => {
    if (open && order) setDraft(order.notes || '');
  }, [open, order]);

  if (!order) return null;

  const handleSave = async () => {
    try {
      await updateNotes.mutateAsync({ id: order.id, notes: draft });
      toast.success('Notes saved');
      onOpenChange(false);
    } catch (err) {
      toast.error('Save failed', { description: err?.message });
    }
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50"
          style={{ background: 'oklch(0% 0 0 / 0.6)', backdropFilter: 'blur(4px)' }}
        />
        <DialogPrimitive.Content
          className="fixed top-0 right-0 h-full z-50 flex flex-col"
          style={{
            width: 'min(480px, 100vw)',
            background: 'var(--surface-modal)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            borderLeft: '1px solid var(--edge-2)',
            boxShadow: 'var(--shadow-lg)',
          }}
          aria-describedby={undefined}
        >
          <header
            className="flex items-start justify-between"
            style={{
              padding: '20px 24px',
              borderBottom: '1px solid var(--edge-1)',
              flexShrink: 0,
            }}
          >
            <div className="min-w-0">
              <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6 }}>
                JOURNAL ENTRY · {order.action} {order.qty} · {fmtPrice(order.fill_price ?? order.placed_price ?? 0)}
              </div>
              <DialogPrimitive.Title
                className="t-title-2"
                style={{ margin: 0, color: 'var(--text-1)' }}
              >
                {order.ticker}
              </DialogPrimitive.Title>
            </div>
            <DialogPrimitive.Close
              aria-label="Close"
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: 4 }}
            >
              <X size={18} strokeWidth={1.75} />
            </DialogPrimitive.Close>
          </header>

          <div className="flex-1 overflow-y-auto" style={{ padding: '20px 24px' }}>
            <label
              className="t-ui-micro"
              style={{ color: 'var(--text-3)', display: 'block', marginBottom: 8 }}
            >
              RATIONALE · EMOTIONS · LESSONS
            </label>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Why did you take this trade? What was the setup? Any emotional context (FOMO, conviction, anxiety)? What would you do differently?"
              rows={14}
              autoFocus
              className="t-ui-body"
              style={{
                width: '100%',
                background: 'var(--surface-3)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
                padding: '12px 14px',
                color: 'var(--text-1)',
                fontFamily: 'var(--font-sans)',
                fontSize: 14,
                lineHeight: 1.5,
                resize: 'vertical',
                outline: 'none',
              }}
            />
            <div className="t-ui-footnote" style={{ color: 'var(--text-4)', marginTop: 8 }}>
              {draft.length} chars · saved to your journal automatically
            </div>
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
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="t-ui-callout"
              style={{
                flex: 1,
                padding: '12px 14px',
                background: 'transparent',
                color: 'var(--text-2)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={updateNotes.isPending}
              className="t-ui-callout"
              style={{
                flex: 2,
                padding: '12px 14px',
                background: updateNotes.isPending ? 'var(--surface-3)' : 'var(--brand)',
                color: updateNotes.isPending ? 'var(--text-3)' : 'var(--brand-fg)',
                border: `1px solid ${updateNotes.isPending ? 'var(--edge-1)' : 'var(--brand)'}`,
                borderRadius: 'var(--r-chip)',
                cursor: updateNotes.isPending ? 'wait' : 'pointer',
                fontWeight: 600,
              }}
            >
              {updateNotes.isPending ? 'Saving…' : 'Save notes'}
            </button>
          </footer>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function EntriesSkeleton() {
  return (
    <section style={{ display: 'grid', gap: 12 }}>
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            minHeight: 100,
            animation: 'skelPulse 1.8s ease-in-out infinite',
          }}
        />
      ))}
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </section>
  );
}
