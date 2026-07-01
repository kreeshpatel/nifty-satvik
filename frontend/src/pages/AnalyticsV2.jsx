/**
 * AnalyticsV2 — Phase 6 redesign of the P&L / Analytics page (route /pnl).
 *
 * Drops all imports from `data/analyticsData.js` (legacy mock). Everything
 * here is computed live from /api/trades + /api/trades/stats + /api/overview.
 *
 * Layout (per plan §7 Secondary):
 *   Page title (Reckless title-1) + "Updated <rel>" currency line
 *   ────────────────────────────────────────
 *   Period chip rail (1W / 1M / 3M / 1Y / All)
 *   ────────────────────────────────────────
 *   KPI strip — Period Return (bull/bear), Max DD (bear),
 *               Win Rate (brand), Avg W/L (muted)
 *   ────────────────────────────────────────
 *   Equity curve  (hero — 360px, semantic dot section header)
 *   ────────────────────────────────────────
 *   Monthly returns heatmap (full width, info-toned header)
 *   ────────────────────────────────────────
 *   By Sector + By Day-of-Week (6/6 horizontal bar lists)
 *
 * 2026-05-20 redesign pass — colorize + layout + typeset + polish:
 *   - Section dot prefixes per .impeccable.md (no side-stripes, no gradient text)
 *   - KPI tones split: brand on Win Rate, bear on Max DD, bull/bear on Period
 *   - EmptyCard with info variant replaces gray EmptyState reflex
 *   - Currency line uses fmtRelTime so "Updated 2m ago" reads obvious
 */
import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, AlertCircle } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { KPICard } from '@/components/shared/KPICard';
import { ChartCard } from '@/components/shared/ChartCard';
import { EquityCurveChart } from '@/components/shared/EquityCurveChart';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { StatusChip } from '@/components/shared/StatusChip';
import { useOverview } from '@/hooks/queries/useOverview';
import { useTrades, useTradeStats, flattenTrades } from '@/hooks/queries/useTrades';
import { fmtINR, fmtPct, fmtRelTime } from '@/lib/format';

const PERIODS = [
  { label: '1W',  value: '1W',  days: 7 },
  { label: '1M',  value: '1M',  days: 30 },
  { label: '3M',  value: '3M',  days: 90 },
  { label: '1Y',  value: '1Y',  days: 365 },
  { label: 'All', value: 'All', days: null },
];

// Tone → dot/halo color map. Mirrors SignalsV2 SectionFrame for visual
// consistency across pages — same dot system, same halo intensity.
const TONE = {
  brand: { dot: 'var(--brand)', halo: 'var(--brand-soft)' },
  bull:  { dot: 'var(--bull)',  halo: 'var(--bull-soft)'  },
  bear:  { dot: 'var(--bear)',  halo: 'var(--bear-soft)'  },
  info:  { dot: 'var(--info)',  halo: 'var(--info-soft)'  },
  warn:  { dot: 'var(--warn)',  halo: 'var(--warn-soft)'  },
  muted: { dot: 'var(--text-4)', halo: 'var(--edge-2)'    },
};

export default function AnalyticsV2() {
  const [period, setPeriod] = useState('1M');
  const overviewQuery = useOverview();
  const statsQuery = useTradeStats();
  const tradesQuery = useTrades({ perPage: 200 });

  const overview = overviewQuery.data;
  const stats = statsQuery.data;
  const allTrades = useMemo(() => flattenTrades(tradesQuery.data), [tradesQuery.data]);

  // Equity curve sliced to chosen period
  const equityCurve = useMemo(() => {
    const all = overview?.equity_curve ?? [];
    const days = PERIODS.find((p) => p.value === period)?.days;
    if (!days || all.length <= days) return all.map((p) => ({ date: p.date, value: p.value }));
    return all.slice(-days).map((p) => ({ date: p.date, value: p.value }));
  }, [overview?.equity_curve, period]);

  // Period KPIs computed from sliced equity curve.
  const periodKPI = useMemo(() => {
    if (equityCurve.length < 2) return { return_pct: 0, abs: 0, dd: 0 };
    const first = equityCurve[0].value;
    const last = equityCurve[equityCurve.length - 1].value;
    const ret = first > 0 ? ((last - first) / first) * 100 : 0;
    let peak = first;
    let dd = 0;
    for (const p of equityCurve) {
      if (p.value > peak) peak = p.value;
      const drop = peak > 0 ? ((p.value - peak) / peak) * 100 : 0;
      if (drop < dd) dd = drop;
    }
    return { return_pct: ret, abs: last - first, dd };
  }, [equityCurve]);

  // Monthly returns heatmap from closed trades — group by year/month and
  // accumulate return_pct (compounding ignored for simplicity, additive
  // approximation matches the live Backtest endpoint's output).
  const monthlyReturns = useMemo(() => {
    const out = {};
    for (const t of allTrades) {
      if (!t.exit_date || typeof t.return_pct !== 'number') continue;
      const d = new Date(t.exit_date);
      if (isNaN(d.getTime())) continue;
      const y = String(d.getFullYear());
      const m = d.getMonth();
      if (!out[y]) out[y] = Array(12).fill(null);
      out[y][m] = (out[y][m] || 0) + t.return_pct;
    }
    return out;
  }, [allTrades]);

  // Day-of-week breakdown from closed trades.
  const dowBreakdown = useMemo(() => {
    const dow = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
    const out = dow.map((label) => ({ label, count: 0, total_pct: 0, win: 0 }));
    for (const t of allTrades) {
      if (!t.exit_date || typeof t.return_pct !== 'number') continue;
      const d = new Date(t.exit_date);
      const idx = d.getDay() - 1;            // Mon=0
      if (idx < 0 || idx > 4) continue;
      out[idx].count++;
      out[idx].total_pct += t.return_pct;
      if (t.return_pct > 0) out[idx].win++;
    }
    return out.map((r) => ({
      ...r,
      avg_pct: r.count > 0 ? r.total_pct / r.count : 0,
      win_rate: r.count > 0 ? (r.win / r.count) * 100 : 0,
    }));
  }, [allTrades]);

  const sectorBreakdown = stats?.sector_stats ?? [];
  const isLoading = overviewQuery.isLoading || statsQuery.isLoading || tradesQuery.isLoading;
  const isError = overviewQuery.isError || statsQuery.isError || tradesQuery.isError;
  const hasAnyTrades = (stats?.total_trades ?? allTrades.length) > 0;

  if (isLoading) {
    return (
      <PageShell title="Analytics" heroTone="info" disclaimer>
        <PageHeader updatedAt={null} totalTrades={0} winRate={0} />
        <PageSkeleton />
      </PageShell>
    );
  }

  if (isError) {
    return (
      <PageShell title="Analytics" heroTone="info" disclaimer>
        <PageHeader updatedAt={null} totalTrades={0} winRate={0} />
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={18} strokeWidth={1.75} />}
          title="Couldn't load analytics"
          body="The /api/overview or /api/trades endpoint failed. Refresh, or check the Render dashboard."
          height={320}
        />
      </PageShell>
    );
  }

  // Cold-start: no trades closed yet. Don't lie with empty zeros — show an
  // info card pointing the user at /backtest as the obvious next step.
  if (!hasAnyTrades && (overview?.equity_curve ?? []).length === 0) {
    return (
      <PageShell title="Analytics" heroTone="info" disclaimer>
        <PageHeader
          updatedAt={overviewQuery.dataUpdatedAt}
          totalTrades={0}
          winRate={0}
        />
        <EmptyCard
          variant="info"
          icon={<TrendingUp size={18} strokeWidth={1.75} />}
          title="No trades closed yet"
          body="Analytics fills in as signals close. In the meantime, check the 2020–2025 backtest for what to expect."
          action={
            <Link
              to="/backtest"
              className="t-ui-callout"
              style={{
                display: 'inline-flex',
                padding: '8px 14px',
                background: 'var(--info-soft)',
                color: 'var(--info)',
                border: '1px solid var(--info-edge)',
                borderRadius: 'var(--r-chip)',
                textDecoration: 'none',
                fontWeight: 600,
              }}
            >
              Open backtest →
            </Link>
          }
          height={320}
        />
      </PageShell>
    );
  }

  return (
    <PageShell title="Analytics" heroTone="info" disclaimer>
      <PageHeader
        updatedAt={overviewQuery.dataUpdatedAt}
        totalTrades={stats?.total_trades ?? allTrades.length}
        winRate={stats?.win_rate ?? 0}
      />

      {/* PERIOD CHIP RAIL */}
      <section
        className="flex items-center"
        style={{ marginBottom: 20, gap: 6 }}
        aria-label="Period selector"
      >
        {PERIODS.map((p) => {
          const active = p.value === period;
          return (
            <button
              key={p.value}
              type="button"
              onClick={() => setPeriod(p.value)}
              aria-pressed={active}
              className="t-ui-callout"
              style={{
                padding: '6px 14px',
                background: active ? 'var(--brand-soft)' : 'transparent',
                color: active ? 'var(--brand-hi)' : 'var(--text-2)',
                border: `1px solid ${active ? 'var(--brand-edge)' : 'var(--edge-1)'}`,
                borderRadius: 'var(--r-chip)',
                cursor: 'pointer',
                fontWeight: active ? 600 : 500,
                fontFamily: 'var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
                transition: 'border-color var(--dur-hover) var(--ease-out-cubic), background var(--dur-hover) var(--ease-out-cubic)',
              }}
            >
              {p.label}
            </button>
          );
        })}
      </section>

      {/* KPI STRIP — 4 cards, kit v2 style (padding 18px, gap 14, glass card) */}
      <section
        className="grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: 14,
          marginBottom: 18,
        }}
      >
        <div
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            padding: 18,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}
        >
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9.5px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-3)', fontWeight: 600, marginBottom: 8 }}>
            Win Rate
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums', fontSize: 26, color: 'var(--bull)', fontWeight: 500 }}>
            {(stats?.win_rate ?? 0).toFixed(1)}%
          </div>
        </div>

        <div
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            padding: 18,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}
        >
          {/* Was mislabeled "CAGR" — the value is periodKPI.return_pct, the raw
              return over the selected window (1W/1M/3M/1Y/All), NOT annualized.
              "Return" is accurate; the period chip rail shows which window. */}
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9.5px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-3)', fontWeight: 600, marginBottom: 8 }}>
            Return
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums', fontSize: 26, color: 'var(--text-1)', fontWeight: 500 }}>
            {fmtPct(periodKPI.return_pct, 1)}
          </div>
        </div>

        <div
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            padding: 18,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}
        >
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9.5px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-3)', fontWeight: 600, marginBottom: 8 }}>
            Sharpe
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums', fontSize: 26, color: 'var(--text-1)', fontWeight: 500 }}>
            {(overview?.metrics?.sharpe_ratio ?? 0).toFixed(2)}
          </div>
        </div>

        <div
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            padding: 18,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}
        >
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9.5px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-3)', fontWeight: 600, marginBottom: 8 }}>
            Max DD
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums', fontSize: 26, color: 'var(--bear)', fontWeight: 500 }}>
            {fmtPct(periodKPI.dd, 1)}
          </div>
        </div>
      </section>

      {/* EQUITY CURVE — hero (brand-toned section dot) */}
      <SectionHeader
        tone="brand"
        title="Equity curve"
        subtitle={`Portfolio value over the ${period === 'All' ? 'full live period' : period.toLowerCase()} window.`}
      />
      <section style={{ marginBottom: 32 }}>
        <ChartCard
          badge={<StatusChip tone={periodKPI.return_pct >= 0 ? 'bull' : 'bear'}>{period}</StatusChip>}
          height={360}
          footer={
            overview?.metrics && (
              <>
                <Meta label="Sharpe" value={(overview.metrics.sharpe_ratio || 0).toFixed(2)} />
                <Meta label="Profit factor" value={(overview.metrics.profit_factor || 0).toFixed(2)} />
                <Meta label="Avg hold" value={`${(overview.metrics.avg_hold_days || 0).toFixed(1)}d`} />
              </>
            )
          }
        >
          {equityCurve.length === 0 ? (
            <EmptyCard
              variant="info"
              icon={<TrendingUp size={18} strokeWidth={1.75} />}
              title="No equity history yet"
              body="Once trades start closing, your equity curve fills in here."
              height={300}
            />
          ) : (
            <EquityCurveChart data={equityCurve} height={360} tone="auto" />
          )}
        </ChartCard>
      </section>

      {/* MONTHLY RETURNS CHART — kit v2 style (SVG bar chart) */}
      <section style={{ marginBottom: 32 }}>
        <div
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            padding: 22,
          }}
        >
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 600, color: 'var(--text-1)', marginBottom: 4 }}>
            Monthly returns · last 24 months
          </div>
          {/* CORRECTNESS: this chart previously rendered a hardcoded `mockMonths`
              array (both the "X of 24 positive" count and the bars) — fabricated
              data on a paid analytics surface, contradicting this page's own
              "everything computed live" contract. Replaced with an honest empty
              state. Wiring a REAL monthly-return series (from closed trades or the
              backend `monthly_returns` blob) is a tracked follow-up — deliberately
              not faked with a quick client-side calc that could itself mislead. */}
          <div style={{ marginBottom: 4 }} />
          <EmptyCard
            variant="info"
            title="Monthly returns will populate from your closed trades"
            height={180}
          />
        </div>
      </section>

      {/* SECTOR + DOW — muted (neutral breakdowns) */}
      <SectionHeader
        tone="muted"
        title="Where the edge comes from"
        subtitle="Win rate by sector (left) and weekday (right). Bar length is trade count, color is win-rate tier."
      />
      <section
        className="grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))',
          gap: 16,
        }}
      >
        <ChartCard title="By sector" height="auto">
          <div style={{ paddingTop: 8 }}>
            {sectorBreakdown.length === 0 ? (
              <EmptyCard
                variant="muted"
                title="No sector data yet"
                body="Once trades close, win-rate by sector will show up here."
                height={180}
              />
            ) : (
              <BreakdownTable
                rows={sectorBreakdown.slice(0, 12).map((s) => ({
                  label: s.sector,
                  count: s.trades,
                  rate: s.win_rate,
                }))}
              />
            )}
          </div>
        </ChartCard>

        <ChartCard title="By day of week" height="auto">
          <div style={{ paddingTop: 8 }}>
            {dowBreakdown.every((d) => d.count === 0) ? (
              <EmptyCard
                variant="muted"
                title="No day-of-week data yet"
                body="Once enough trades close, weekday performance shows here."
                height={180}
              />
            ) : (
              <BreakdownTable
                rows={dowBreakdown.map((d) => ({
                  label: d.label,
                  count: d.count,
                  rate: d.win_rate,
                  avg: d.avg_pct,
                }))}
                showAvg
              />
            )}
          </div>
        </ChartCard>
      </section>
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// SUB-COMPONENTS
// ══════════════════════════════════════════════════════════════

/**
 * PageHeader — Reckless title-1 with currency line below. The "Updated
 * <rel>" footnote is the user-visible signal that the page is fed from
 * /api/overview (not stale stub data); a paid product can't ship without
 * this on the analytics view.
 */
function PageHeader({ updatedAt, totalTrades, winRate }) {
  return (
    <header style={{ paddingTop: 24, paddingBottom: 20 }}>
      <h1 className="t-title-1" style={{ margin: 0, color: 'var(--text-1)' }}>
        Analytics
      </h1>
      <div
        className="t-ui-micro flex items-center flex-wrap"
        style={{ color: 'var(--text-3)', marginTop: 8, gap: 8, letterSpacing: '0.06em' }}
      >
        <span>
          {totalTrades} CLOSED · {winRate.toFixed(1)}% LIFETIME WIN RATE
        </span>
        {updatedAt && (
          <>
            <span style={{ color: 'var(--text-4)' }}>·</span>
            <span>UPDATED {fmtRelTime(new Date(updatedAt)).toUpperCase()}</span>
          </>
        )}
      </div>
    </header>
  );
}

/**
 * SectionHeader — dot prefix + tone halo + title + optional subtitle.
 *
 * Same visual grammar as SignalsV2's SectionFrame so the analytics page
 * reads like the same product instead of a separate one. Halo is the
 * 4-6% wash around the dot; never a side-stripe (banned).
 */
function SectionHeader({ tone = 'muted', title, subtitle }) {
  const t = TONE[tone] || TONE.muted;
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
              flexShrink: 0,
              marginRight: 10,
              marginLeft: 3,
              transform: 'translateY(-2px)',
            }}
          />
          {title}
        </h2>
      </div>
      {subtitle && (
        <p
          className="t-ui-footnote"
          style={{ color: 'var(--text-2)', margin: '4px 0 0 20px', maxWidth: '76ch' }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <span className="flex items-baseline" style={{ gap: 6 }}>
      <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>{label}</span>
      <span className="t-num-small" style={{ color: 'var(--text-1)' }}>{value}</span>
    </span>
  );
}

/**
 * BreakdownTable — horizontal bar list. Each row's bar fills relative to
 * the row count of the highest-count entry. Win rate is colored by tier:
 *   ≥60% → bull, 40-60% → text-1, <40% → bear.
 */
function BreakdownTable({ rows, showAvg = false }) {
  const maxCount = Math.max(...rows.map((r) => r.count || 0), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {rows.map((r, i) => {
        const rateColor =
          (r.rate ?? 0) >= 60
            ? 'var(--bull)'
            : (r.rate ?? 0) >= 40
              ? 'var(--text-1)'
              : 'var(--bear)';
        const barPct = maxCount > 0 ? (r.count / maxCount) * 100 : 0;
        return (
          <div
            key={`${r.label}-${i}`}
            className="grid items-center"
            style={{
              gridTemplateColumns: '120px 1fr 80px' + (showAvg ? ' 60px' : ''),
              gap: 12,
              padding: '6px 0',
              borderBottom: i === rows.length - 1 ? 'none' : '1px solid var(--edge-1)',
            }}
          >
            <span className="t-ui-body" style={{ color: 'var(--text-2)' }}>{r.label}</span>
            <div
              role="presentation"
              style={{
                position: 'relative',
                height: 6,
                background: 'var(--surface-2)',
                borderRadius: 3,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: '0 auto 0 0',
                  width: `${barPct}%`,
                  background: rateColor,
                  borderRadius: 3,
                  opacity: 0.7,
                }}
              />
            </div>
            <span
              className="t-num-body"
              style={{
                color: rateColor,
                textAlign: 'right',
                fontSize: 13,
              }}
            >
              {(r.rate ?? 0).toFixed(0)}%
              <span className="t-num-small" style={{ color: 'var(--text-3)', marginLeft: 4 }}>
                ({r.count})
              </span>
            </span>
            {showAvg && (
              <span
                className="t-num-small"
                style={{
                  color: (r.avg ?? 0) >= 0 ? 'var(--bull)' : 'var(--bear)',
                  textAlign: 'right',
                }}
              >
                {fmtPct(r.avg ?? 0, 1)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function PageSkeleton() {
  return (
    <div>
      <div
        className="grid grid-cols-2 sm:grid-cols-4"
        style={{
          gap: 16,
          marginBottom: 24,
        }}
      >
        {[0, 1, 2, 3].map((i) => (
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
      </div>
      <div
        style={{
          background: 'var(--surface-1)',
          border: '1px solid var(--edge-1)',
          borderRadius: 'var(--r-card)',
          minHeight: 360,
          animation: 'skelPulse 1.8s ease-in-out infinite',
        }}
      />
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}
