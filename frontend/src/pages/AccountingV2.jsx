/**
 * AccountingV2 — Phase 7 redesign of the Accounting page (FY P&L + tax view).
 *
 * Per product decision (locked 2026-04-24): only orders placed through
 * Nifty Satvik (`nq_orders` table) appear here. External Kite trades are
 * intentionally invisible — Accounting is a record of what the user
 * executed via our signal flow.
 *
 * Layout:
 *   Page title + intro
 *   ────────────────────────────────────────
 *   Period switcher chips (tone follows active period)
 *   ────────────────────────────────────────
 *   • P&L — KPI row: Realised · STCG · LTCG · Matched pairs
 *   • Tax costs — KPI row: Brokerage · STT
 *   ────────────────────────────────────────
 *   • Filed orders — DataTable + CSV download (text link, not primary CTA)
 *
 * Tax matching is FIFO and computed server-side (/api/nq-orders/stats).
 * The page just visualizes the response.
 */
import React, { useMemo, useState } from 'react';
import { Download, FileText, AlertCircle } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { KPICard } from '@/components/shared/KPICard';
import { DataTable } from '@/components/shared/DataTable';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { useNQOrders, useNQOrderStats } from '@/hooks/queries/useNQOrders';
import { fmtINR, fmtPrice, fmtRelTime } from '@/lib/format';

const PERIODS = [
  { label: 'FY',   value: 'fy',  description: 'Apr 1 → Mar 31' },
  { label: 'YTD',  value: 'ytd', description: 'Jan 1 → today' },
  { label: '30D',  value: '30d', description: 'Last 30 days' },
  { label: 'All',  value: 'all', description: 'Lifetime' },
];

const SECTION_TONES = {
  brand: { dot: 'var(--brand)', halo: 'var(--brand-soft)', count: 'var(--brand)' },
  bull:  { dot: 'var(--bull)',  halo: 'var(--bull-soft)',  count: 'var(--bull)' },
  info:  { dot: 'var(--info)',  halo: 'var(--info-soft)',  count: 'var(--info)' },
  warn:  { dot: 'var(--warn)',  halo: 'var(--warn-soft)',  count: 'var(--warn)' },
  bear:  { dot: 'var(--bear)',  halo: 'var(--bear-soft)',  count: 'var(--bear)' },
  muted: { dot: 'var(--text-4)', halo: 'var(--edge-2)',    count: 'var(--text-3)' },
};

export default function AccountingV2() {
  const [period, setPeriod] = useState('fy');
  const statsQuery = useNQOrderStats(period);
  const ordersQuery = useNQOrders({});

  const stats = statsQuery.data;
  // Stable reference for downstream useMemo deps — see SignalsV2 for the
  // same pattern. Without this, `orders` becomes a fresh `[]` every render
  // while the query is loading and filteredOrders churns needlessly.
  const orders = useMemo(() => ordersQuery.data ?? [], [ordersQuery.data]);

  // For the table: only completed orders, filtered by period date range.
  const filteredOrders = useMemo(() => {
    const completed = orders.filter((o) => o.status === 'COMPLETE');
    const now = new Date();
    let cutoff = null;
    if (period === 'fy') {
      const startYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
      cutoff = new Date(startYear, 3, 1);
    } else if (period === 'ytd') {
      cutoff = new Date(now.getFullYear(), 0, 1);
    } else if (period === '30d') {
      cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    }
    return cutoff
      ? completed.filter((o) => new Date(o.placed_at) >= cutoff)
      : completed;
  }, [orders, period]);

  const activePeriod = PERIODS.find((p) => p.value === period);

  const handleExportCSV = () => {
    const rows = [
      ['Date', 'Ticker', 'Action', 'Qty', 'Placed Price', 'Fill Price', 'Brokerage', 'STT', 'Net Amount', 'Status', 'Signal ID', 'Notes'],
      ...filteredOrders.map((o) => [
        o.placed_at?.slice(0, 10) || '',
        o.ticker,
        o.action,
        o.qty,
        o.placed_price ?? '',
        o.fill_price ?? '',
        o.brokerage ?? 0,
        o.stt ?? 0,
        o.net_amount ?? '',
        o.status,
        o.signal_id || '',
        (o.notes || '').replace(/[\n\r,]/g, ' '),
      ]),
    ];
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `niftyquant-accounting-${period}-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const hasMatchedTrades = stats && stats.trades_matched > 0;
  const realisedTone = !stats ? 'muted' : stats.realised_pnl >= 0 ? 'bull' : 'bear';

  return (
    <PageShell title="Accounting" heroTone="info">
      <header style={{ paddingTop: 24, paddingBottom: 16 }}>
        <h1 className="t-title-1" style={{ margin: 0, color: 'var(--text-1)' }}>Accounting</h1>
        <p
          className="t-prose"
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 16,
            lineHeight: 1.5,
            fontStyle: 'italic',
            color: 'var(--text-2)',
            margin: '10px 0 0',
            maxWidth: '72ch',
          }}
        >
          Tax-year P&L for orders placed through Nifty Satvik. STCG / LTCG matched
          FIFO. External Kite trades aren't tracked here by design — only signals
          you actually executed.
        </p>
      </header>

      {/* PERIOD SWITCHER */}
      <section
        className="flex items-center"
        style={{ gap: 6, marginBottom: 24, flexWrap: 'wrap' }}
        aria-label="Period selector"
      >
        {PERIODS.map((p) => {
          const active = p.value === period;
          const t = SECTION_TONES.brand;
          return (
            <button
              key={p.value}
              type="button"
              onClick={() => setPeriod(p.value)}
              aria-pressed={active}
              title={p.description}
              className="t-ui-callout inline-flex items-center"
              style={{
                gap: 6,
                padding: '6px 14px',
                background: active ? t.halo : 'transparent',
                color: active ? t.count : 'var(--text-2)',
                border: `1px solid ${active ? t.dot : 'var(--edge-1)'}`,
                borderRadius: 'var(--r-chip)',
                cursor: 'pointer',
                fontWeight: active ? 600 : 500,
                transition: 'background var(--dur-hover) ease, color var(--dur-hover) ease, border-color var(--dur-hover) ease',
              }}
            >
              {active && (
                <span
                  aria-hidden="true"
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: t.dot,
                  }}
                />
              )}
              {p.label}
              <span className="t-ui-footnote" style={{ color: active ? t.count : 'var(--text-4)', marginLeft: 4, fontWeight: 400 }}>
                {p.description}
              </span>
            </button>
          );
        })}
      </section>

      {/* ─── P&L ─── */}
      <SectionHead
        tone={realisedTone}
        title="P&L"
        subtitle={
          hasMatchedTrades
            ? `Realised performance across the ${activePeriod?.label || period} window, FIFO-matched.`
            : `No matched trades in the ${activePeriod?.label || period} window yet.`
        }
      />

      {statsQuery.isLoading ? (
        <KPISkeleton />
      ) : statsQuery.error ? (
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={16} strokeWidth={1.75} />}
          title="Couldn't load stats"
          body={statsQuery.error?.message || 'Try refreshing the page.'}
          className="mb-4"
        />
      ) : !hasMatchedTrades ? (
        <EmptyCard
          variant="muted"
          icon={<FileText size={16} strokeWidth={1.75} />}
          title="Tax records appear once you place orders through Nifty Satvik"
          body="The Accounting view fills in once you have completed buy/sell pairs in this period."
          className="mb-4"
        />
      ) : (
        <>
          <section
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 16,
              marginBottom: 24,
            }}
          >
            <KPICard
              label="REALISED P&L"
              value={`${stats.realised_pnl >= 0 ? '+' : ''}${fmtINR(stats.realised_pnl)}`}
              tone={stats.realised_pnl >= 0 ? 'bull' : 'bear'}
              context={`Net of costs: ${stats.net_pnl >= 0 ? '+' : ''}${fmtINR(stats.net_pnl)}`}
            />
            <KPICard
              label="STCG"
              value={`${stats.stcg_pnl >= 0 ? '+' : ''}${fmtINR(stats.stcg_pnl)}`}
              tone={stats.stcg_pnl >= 0 ? 'bull' : 'bear'}
              context="Held < 1 year · taxed as short-term"
            />
            <KPICard
              label="LTCG"
              value={`${stats.ltcg_pnl >= 0 ? '+' : ''}${fmtINR(stats.ltcg_pnl)}`}
              tone={stats.ltcg_pnl >= 0 ? 'bull' : 'bear'}
              context="Held ≥ 1 year · taxed as long-term"
            />
            <KPICard
              label="MATCHED PAIRS"
              value={String(stats.trades_matched)}
              tone="brand"
              context={`${stats.open_positions} position${stats.open_positions !== 1 ? 's' : ''} still open`}
            />
          </section>

          {/* ─── TAX COSTS ─── */}
          <SectionHead
            tone="info"
            title="Tax costs"
            subtitle="What Zerodha and the exchange charged on the matched pairs."
          />
          <section
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 16,
              marginBottom: 28,
            }}
          >
            <KPICard
              label="BROKERAGE"
              value={fmtINR(stats.total_brokerage)}
              tone="neutral"
              context="Zerodha charges across matched trades"
            />
            <KPICard
              label="STT"
              value={fmtINR(stats.total_stt)}
              tone="neutral"
              context="Securities Transaction Tax (sell side)"
            />
          </section>
        </>
      )}

      {/* ─── FILED ORDERS ─── */}
      <SectionHead
        tone="muted"
        title="Filed orders"
        count={filteredOrders.length}
        subtitle={
          <>
            {filteredOrders.length} order{filteredOrders.length !== 1 ? 's' : ''} in this period
            {ordersQuery.dataUpdatedAt && (
              <>
                <span style={{ color: 'var(--text-4)' }}> · </span>
                Updated {fmtRelTime(new Date(ordersQuery.dataUpdatedAt))}
              </>
            )}
          </>
        }
        action={
          filteredOrders.length > 0 && (
            <button
              type="button"
              onClick={handleExportCSV}
              className="t-ui-callout inline-flex items-center"
              style={{
                gap: 6,
                background: 'transparent',
                border: 'none',
                color: 'var(--brand-hi)',
                padding: 0,
                cursor: 'pointer',
                fontWeight: 600,
                textDecoration: 'underline',
                textUnderlineOffset: 3,
                textDecorationColor: 'var(--brand-edge)',
              }}
            >
              <Download size={13} strokeWidth={1.75} />
              Download CSV
            </button>
          )
        }
      />

      <section style={{ marginBottom: 16 }}>
        {ordersQuery.isLoading ? (
          <TableSkeleton />
        ) : filteredOrders.length === 0 ? (
          <EmptyCard
            variant="muted"
            icon={<FileText size={16} strokeWidth={1.75} />}
            title="No orders in this period"
            body="Switch to a wider period or place trades through Nifty Satvik Buy/Sell to populate this table."
          />
        ) : (
          <DataTable
            rows={filteredOrders}
            initialSort={{ key: 'placed_at', dir: 'desc' }}
            columns={[
              {
                key: 'placed_at',
                header: 'Date',
                sortable: true,
                width: '110px',
                render: (v) => (v ? new Date(v).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' }) : '—'),
              },
              { key: 'ticker', header: 'Ticker', sortable: true, width: '130px' },
              {
                key: 'action',
                header: 'Side',
                width: '80px',
                render: (v) => (
                  <StatusChip tone={v === 'BUY' ? 'bull' : 'bear'}>{v}</StatusChip>
                ),
              },
              { key: 'qty', header: 'Qty', sortable: true, align: 'right', width: '70px' },
              { key: 'fill_price', header: 'Fill', sortable: true, align: 'right', render: (v, row) => fmtPrice(v ?? row.placed_price ?? 0) },
              {
                key: 'net_amount',
                header: 'Net amount',
                sortable: true,
                align: 'right',
                render: (v, row) => {
                  if (v == null) return '—';
                  // Tint net amount per side: BUY = bear (money out), SELL = bull (money in).
                  // Subtle (--text-2 brightness) so it doesn't compete with P&L rows.
                  const color = row.action === 'SELL' ? 'var(--bull)' : 'var(--bear)';
                  return <span style={{ color }}>{fmtINR(v)}</span>;
                },
              },
              { key: 'brokerage', header: 'Brk', align: 'right', render: (v) => fmtINR(v || 0) },
              { key: 'stt', header: 'STT', align: 'right', render: (v) => fmtINR(v || 0) },
              {
                key: 'status',
                header: 'Status',
                render: (v) => {
                  const u = String(v || '').toUpperCase();
                  const tone = u === 'COMPLETE' ? 'bull' : u === 'REJECTED' ? 'bear' : u === 'OPEN' ? 'info' : 'muted';
                  return <StatusChip tone={tone}>{u}</StatusChip>;
                },
              },
            ]}
          />
        )}
      </section>
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// SECTION HEADER (tier-toned)
// ══════════════════════════════════════════════════════════════

function SectionHead({ tone = 'muted', title, count, subtitle, action }) {
  const t = SECTION_TONES[tone] || SECTION_TONES.muted;
  return (
    <div style={{ marginBottom: 12, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
      <div style={{ minWidth: 0 }}>
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
          {count != null && count > 0 && (
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
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
    </div>
  );
}

function KPISkeleton() {
  return (
    <section
      className="grid"
      style={{
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: 16,
        marginBottom: 16,
      }}
    >
      {Array.from({ length: 4 }).map((_, i) => (
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

function TableSkeleton() {
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
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 40,
            display: 'grid',
            gridTemplateColumns: 'repeat(8, 1fr)',
            gap: 12,
            alignItems: 'center',
            borderBottom: i === 5 ? 'none' : '1px solid var(--edge-1)',
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
