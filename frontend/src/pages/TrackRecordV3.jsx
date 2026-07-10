/**
 * TrackRecordV3 — Bhanushali (live weekly-swing model)'s own 2017-2026 backtest.
 *
 * Pulls a single consolidated blob from GET /api/backtest/bhanushali (see
 * routers/backtest.py). This is the deployed model's own lineage (pre-reg
 * 0093/0094) — NOT the letter-faithful taught-Bhanushali test in research/
 * findings/0022, which was KILLED. This one is real but UNDERPOWERED
 * (DSR < 0.95) and explicitly in-sample — never presented as a certified
 * or forward-verified track record. The framing banner below carries that
 * distinction through from the API's `meta` block.
 */
import React, { useMemo } from 'react';
import { TrendingUp, AlertCircle, ShieldAlert } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { KPICard } from '@/components/shared/KPICard';
import { ChartCard } from '@/components/shared/ChartCard';
import { DataTable } from '@/components/shared/DataTable';
import { EquityCurveChart } from '@/components/shared/EquityCurveChart';
import { ExitReasonsDonut } from '@/components/shared/ExitReasonsDonut';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { useBhanushaliBacktest } from '@/hooks/queries/useBacktest';
import { fmtPct, fmtPrice } from '@/lib/format';

const EXIT_REASON_LABEL = {
  HALF_TARGET: 'Half at Target',
  TRAIL_STOP: 'Trailing Stop',
  STOP: 'Stop Loss',
  TIME: 'Time Exit',
};

export default function TrackRecordV3() {
  const { data, isLoading, error } = useBhanushaliBacktest();

  const equity = useMemo(
    () => (data?.equity_curve ?? []).map((p) => ({ date: p.date, value: p.nav })),
    [data?.equity_curve],
  );

  const exitReasons = useMemo(() => {
    const counts = data?.exit_reasons ?? {};
    const total = Object.values(counts).reduce((s, n) => s + n, 0);
    if (!total) return [];
    return Object.entries(counts)
      .map(([reason, count]) => ({
        reason: EXIT_REASON_LABEL[reason] || reason,
        count,
        value: Math.round((count / total) * 1000) / 10,
      }))
      .sort((a, b) => b.count - a.count);
  }, [data?.exit_reasons]);

  const h = data?.headline ?? {};
  const meta = data?.meta ?? {};

  return (
    <PageShell title="Track Record" heroTone="info" disclaimer>
      <header style={{ paddingTop: 32, paddingBottom: 20 }}>
        <div
          className="t-ui-micro flex items-center"
          style={{ color: 'var(--info)', marginBottom: 8, gap: 8, letterSpacing: '0.08em' }}
        >
          <span
            aria-hidden="true"
            style={{
              display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
              background: 'var(--info)', boxShadow: '0 0 0 3px var(--info-soft)',
            }}
          />
          {meta.window || '2017 — 2026'} · IN-SAMPLE BACKTEST
        </div>
        <h1
          className="t-display"
          style={{ margin: 0, color: 'var(--text-1)', fontSize: 'clamp(32px, 4.6vw, 48px)', lineHeight: 1.05 }}
        >
          The systematic model, ten years back.
        </h1>
        <p className="t-prose" style={{ color: 'var(--text-2)', margin: '12px 0 0', maxWidth: '70ch' }}>
          The live weekly-swing model's own backtest — trend-ranked entries, staged exits, run across
          Nifty 500 large/mid caps since 2017. This is the model that trades today, tested on the years
          before it.
        </p>
      </header>

      {/* Certification banner — the one thing this page must never let the user miss */}
      <div
        className="flex items-start"
        style={{
          gap: 12, padding: '14px 16px', marginBottom: 28,
          background: 'var(--warn-soft)', border: '1px solid rgba(255,180,84,0.32)',
          borderRadius: 'var(--r-card)',
        }}
      >
        <ShieldAlert size={18} strokeWidth={1.75} style={{ color: 'var(--warn)', flexShrink: 0, marginTop: 1 }} />
        <div>
          <div className="t-ui-callout" style={{ color: 'var(--text-1)', fontWeight: 600 }}>
            Not a certified or forward-verified track record
          </div>
          <p className="t-ui-footnote" style={{ color: 'var(--text-2)', margin: '4px 0 0' }}>
            {meta.certification ||
              'In-sample simulation. DSR below the 0.95 certification bar. Not indicative of future results.'}
            {' '}Forward performance is tracked separately and is the only certifier of real edge.
          </p>
        </div>
      </div>

      {isLoading ? (
        <PageSkeleton />
      ) : error ? (
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={18} strokeWidth={1.75} />}
          title="Couldn't load backtest data"
          body={error?.message || 'The backtest data failed to load. Try refreshing the page.'}
          height={320}
        />
      ) : !data ? null : (
        <>
          <section
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, marginBottom: 24 }}
          >
            <KPICard
              label="NET SHARPE"
              value={h.net_sharpe != null ? h.net_sharpe.toFixed(2) : '—'}
              tone="brand"
              context={h.dsr != null ? `DSR ${h.dsr.toFixed(3)}` : undefined}
            />
            <KPICard
              label="NET CAGR"
              value={h.net_cagr_pct != null ? fmtPct(h.net_cagr_pct, 1) : '—'}
              tone={h.net_cagr_pct >= 0 ? 'bull' : 'bear'}
            />
            <KPICard
              label="MAX DRAWDOWN"
              value={h.max_dd_pct != null ? fmtPct(h.max_dd_pct, 1) : '—'}
              tone="bear"
              context="peak-to-trough"
            />
            <KPICard
              label="WIN RATE"
              value={h.win_rate_pct != null ? `${h.win_rate_pct.toFixed(1)}%` : '—'}
              tone="neutral"
              context={`${h.total_trades ?? 0} trades`}
            />
            <KPICard
              label="CI LOW (95%)"
              value={h.ci_low != null ? h.ci_low.toFixed(2) : '—'}
              tone="neutral"
              context="Sharpe lower bound"
            />
          </section>

          <section style={{ marginBottom: 32 }}>
            <ChartCard
              title="Illustrative equity curve"
              badge={<StatusChip tone="info">IN-SAMPLE</StatusChip>}
              height={380}
              footer={
                <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
                  NAV compounds trade-by-trade at exit date, risking a fixed % of NAV per trade — a
                  standard R-multiple convention, not a claim about literal concurrent capital use.
                </span>
              }
            >
              {equity.length < 2 ? (
                <EmptyCard variant="muted" title="No equity data" height={320} />
              ) : (
                <EquityCurveChart data={equity} height={380} tone="info" />
              )}
            </ChartCard>
          </section>

          <section
            className="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]"
            style={{ gap: 16, marginBottom: 32 }}
          >
            <ChartCard title="Yearly breakdown" height="auto">
              <div style={{ paddingTop: 8 }}>
                {(data.yearly ?? []).length === 0 ? (
                  <EmptyCard variant="muted" title="No yearly data" height={200} />
                ) : (
                  <YearlyTable rows={data.yearly} />
                )}
              </div>
            </ChartCard>
            <ChartCard title="How trades closed" height="auto">
              <div style={{ paddingTop: 8 }}>
                {exitReasons.length === 0 ? (
                  <EmptyCard variant="muted" title="No exits yet" height={200} />
                ) : (
                  <ExitReasonsDonut data={exitReasons} height={220} />
                )}
              </div>
            </ChartCard>
          </section>

          <section style={{ marginBottom: 24 }}>
            <h2 className="t-title-2" style={{ margin: '0 0 12px', color: 'var(--text-1)' }}>
              Recent trades
            </h2>
            <DataTable
              rows={(data.recent_trades ?? []).map((t, i) => ({ id: i, ...t }))}
              initialSort={{ key: 'exit_date', dir: 'desc' }}
              emptyState={
                <EmptyCard
                  variant="info"
                  icon={<TrendingUp size={18} strokeWidth={1.75} />}
                  title="No trades yet"
                  height={200}
                />
              }
              columns={tradeColumns()}
            />
          </section>

          <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 8 }}>
            {meta.provenance && <>Provenance: {meta.provenance}. </>}
            {meta.status && <>Status: {meta.status}.</>}
          </div>
        </>
      )}
    </PageShell>
  );
}

function YearlyTable({ rows }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr>
          {['Year', 'Trades', 'Win Rate', 'Total R', 'Avg R'].map((h, i) => (
            <th
              key={h}
              className="t-ui-micro"
              style={{
                textAlign: i === 0 ? 'left' : 'right', color: 'var(--text-3)',
                padding: '8px 6px', borderBottom: '1px solid var(--edge-1)',
              }}
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.year}>
            <td className="t-num-small" style={{ padding: '8px 6px', color: 'var(--text-1)' }}>{r.year}</td>
            <td className="t-num-small" style={{ padding: '8px 6px', textAlign: 'right', color: 'var(--text-2)' }}>{r.trades}</td>
            <td className="t-num-small" style={{ padding: '8px 6px', textAlign: 'right', color: 'var(--text-2)' }}>{r.win_rate.toFixed(1)}%</td>
            <td
              className="t-num-small"
              style={{ padding: '8px 6px', textAlign: 'right', color: r.total_r >= 0 ? 'var(--bull)' : 'var(--bear)' }}
            >
              {r.total_r >= 0 ? '+' : ''}{r.total_r.toFixed(2)}R
            </td>
            <td className="t-num-small" style={{ padding: '8px 6px', textAlign: 'right', color: 'var(--text-2)' }}>{r.avg_r.toFixed(2)}R</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function tradeColumns() {
  return [
    { key: 'exit_date', header: 'Closed', sortable: true, width: '110px' },
    { key: 'ticker', header: 'Ticker', sortable: true, width: '120px' },
    { key: 'entry', header: 'Entry', sortable: true, align: 'right', render: (v) => fmtPrice(v) },
    { key: 'exit_price', header: 'Exit', sortable: true, align: 'right', render: (v) => fmtPrice(v) },
    {
      key: 'r_multiple',
      header: 'R',
      sortable: true,
      align: 'right',
      render: (v) => (
        <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}R
        </span>
      ),
    },
    { key: 'held_weeks', header: 'Weeks', sortable: true, align: 'right', width: '80px' },
    {
      key: 'reason',
      header: 'Reason',
      render: (v) => (
        <span className="t-ui-footnote" style={{ color: 'var(--text-2)' }}>
          {EXIT_REASON_LABEL[v] || v}
        </span>
      ),
    },
  ];
}

function PageSkeleton() {
  return (
    <div>
      <div
        className="grid grid-cols-2 sm:grid-cols-5"
        style={{ gap: 16, marginBottom: 32 }}
      >
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            style={{
              background: 'var(--surface-1)', border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-card)', minHeight: 100,
              animation: 'skelPulse 1.8s ease-in-out infinite',
            }}
          />
        ))}
      </div>
      <div
        style={{
          background: 'var(--surface-1)', border: '1px solid var(--edge-1)',
          borderRadius: 'var(--r-card)', minHeight: 380,
          animation: 'skelPulse 1.8s ease-in-out infinite',
        }}
      />
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}
