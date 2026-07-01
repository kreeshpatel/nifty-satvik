/**
 * BacktestV2 — Track Record page.
 *
 * User intent: "Prove the system works." Editorial header, tab strip,
 * KPI ledger, hero equity curve, monthly heatmap + exit donut, recent
 * trades. Live tab is sourced entirely from /api/backtest/live; the
 * other tabs are conditionally rendered based on backend data
 * availability — Historical + Compare disappear when
 * results/backtest_data.json is missing, Run Local disappears unless
 * the env flag REACT_APP_RUN_LOCAL_ENABLED is set (the local-run
 * backend isn't wired in production).
 *
 * Layout per plan §7 Flagship #4.
 *
 * 2026-05-20 redesign pass — colorize + layout + typeset + polish:
 *   - Lineage line ("ENSEMBLE v2.0 · AS OF <rel>") under hero, addresses the
 *     "outdated data from previous models" complaint by showing data
 *     freshness immediately. Backend already returns `as_of` — wire it.
 *   - Tab strip: active tab gets brand underline (current behavior) plus
 *     a small brand dot prefix when active. Stale tabs remain muted.
 *   - KPI tones split: Win Rate → brand, Max DD → bear, Total Return →
 *     bull/bear, Avg Return → bull/bear (was all neutral before).
 *   - Dot-prefix section headers per impeccable spec.
 *   - EmptyCard variants replace gray EmptyState reflex (warn on fetch
 *     error, info on cold-start no-trades, muted on per-widget empties).
 */
import React, { useMemo, useState } from 'react';
import {
  ResponsiveContainer, XAxis, YAxis, Tooltip, Line, ComposedChart, Area,
} from 'recharts';
import { TrendingUp, AlertCircle, Play, Loader2 } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { KPICard } from '@/components/shared/KPICard';
import { ChartCard } from '@/components/shared/ChartCard';
import { DataTable } from '@/components/shared/DataTable';
import { EquityCurveChart } from '@/components/shared/EquityCurveChart';
import { MonthlyHeatmap } from '@/components/shared/MonthlyHeatmap';
import { ExitReasonsDonut } from '@/components/shared/ExitReasonsDonut';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { useBacktestLive, useBacktestHistorical } from '@/hooks/queries/useBacktest';
import { fmtPrice, fmtPct, fmtINR, fmtRelTime } from '@/lib/format';

// Env-flag gate for the Run Local tab. Backend's /api/backtest/run
// currently returns a stub error; until that's wired, hide the tab
// entirely instead of advertising a broken affordance.
const RUN_LOCAL_ENABLED = process.env.REACT_APP_RUN_LOCAL_ENABLED === 'true';

// Tone → dot/halo map (matches AnalyticsV2, TrackRecordV2, SignalsV2).
const TONE = {
  brand: { dot: 'var(--brand)', halo: 'var(--brand-soft)' },
  bull:  { dot: 'var(--bull)',  halo: 'var(--bull-soft)'  },
  bear:  { dot: 'var(--bear)',  halo: 'var(--bear-soft)'  },
  info:  { dot: 'var(--info)',  halo: 'var(--info-soft)'  },
  warn:  { dot: 'var(--warn)',  halo: 'var(--warn-soft)'  },
  muted: { dot: 'var(--text-4)', halo: 'var(--edge-2)'    },
};

// Format an ISO date 'YYYY-MM-DD' as 'Jan 13, 2026' for the tab subtitle.
function fmtMonthDay(iso) {
  if (!iso || typeof iso !== 'string') return null;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return null;
  }
}

export default function BacktestV2() {
  const [tab, setTab] = useState('live');
  const liveQuery = useBacktestLive();
  const histQuery = useBacktestHistorical({ enabled: tab === 'historical' || tab === 'compare' });

  // First signal date drives both the editorial subtitle and the Live
  // tab's "since X" note. Falls back to a generic phrase while loading.
  const firstSignalDate = liveQuery.data?.first_signal_date || liveQuery.data?.start_date;
  const firstSignalLabel = fmtMonthDay(firstSignalDate);

  // Currency line — model version + as-of timestamp. The user explicitly
  // flagged "outdated data from previous models" so we surface lineage
  // upfront. `as_of` comes from /api/backtest/live (cron-backed); falls
  // back to the react-query dataUpdatedAt if the backend hasn't shipped
  // as_of yet.
  //
  // Label is hardcoded to the live production config: multi-horizon
  // ensemble (7d + 14d + 30d) of LightGBM v2.0 with regime_medium
  // per-row weights. Verified 2026-05-24 against results/signals_today.json
  // `config_fingerprint="strategy=ensemble|model_dir="` and
  // `model_version="v2.0"`. If NIFTYQUANT_STRATEGY env var on Render
  // ever flips back to single-model, OR NIFTYQUANT_ENSEMBLE_WEIGHTS
  // changes scheme, update this string (or wire through
  // /api/backtest/live for auto-tracking).
  const lineage = useMemo(() => {
    const parts = ['ENSEMBLE v2.0'];
    const ts = liveQuery.data?.as_of;
    if (ts) {
      parts.push(`AS OF ${fmtRelTime(new Date(ts)).toUpperCase()}`);
    } else if (liveQuery.dataUpdatedAt) {
      parts.push(`FETCHED ${fmtRelTime(new Date(liveQuery.dataUpdatedAt)).toUpperCase()}`);
    }
    if (firstSignalDate) {
      parts.push(`LIVE SINCE ${firstSignalDate.toUpperCase()}`);
    }
    return parts.join(' · ');
  }, [liveQuery.data?.as_of, liveQuery.dataUpdatedAt, firstSignalDate]);

  // Tab availability — driven by what the backend actually returns:
  //   - Live: always shown (cron-backed; degrades to empty state on its own)
  //   - Historical: hidden if the request errors (404 = backtest_data.json
  //     not regenerated yet)
  //   - Compare: hidden when Historical is hidden (depends on it)
  //   - Run Local: hidden behind env flag until backend supports it
  const historicalAvailable = !histQuery.isError;
  const tabs = useMemo(() => {
    const t = [
      {
        value: 'live',
        label: 'Live',
        note: firstSignalLabel ? `since ${firstSignalLabel}` : 'live track record',
        tone: 'bull',
      },
    ];
    if (historicalAvailable) {
      t.push({ value: 'historical', label: 'Historical', note: '2020 — 2025', tone: 'info' });
      t.push({ value: 'compare',    label: 'Compare',    note: 'overlay',     tone: 'brand' });
    }
    if (RUN_LOCAL_ENABLED) {
      t.push({ value: 'run', label: 'Run Local', note: 'beta', tone: 'warn' });
    }
    return t;
  }, [firstSignalLabel, historicalAvailable]);

  // Auto-fall-back to Live if the user is on a tab that just got hidden.
  React.useEffect(() => {
    if (!tabs.find((t) => t.value === tab)) setTab('live');
  }, [tabs, tab]);

  return (
    <PageShell title="Backtest" heroTone="info" disclaimer>
      {/* EDITORIAL HEADER */}
      <header style={{ paddingTop: 24, paddingBottom: 20 }}>
        <h1 className="t-title-1" style={{ margin: 0, color: 'var(--text-1)' }}>
          Track Record
        </h1>
        <p
          className="t-prose"
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 18,
            lineHeight: 1.45,
            fontStyle: 'italic',
            color: 'var(--text-2)',
            margin: '12px 0 0',
          }}
        >
          {firstSignalLabel
            ? `Live since ${firstSignalLabel}${historicalAvailable ? ' — and the full 2020–2025 backtest, side by side' : ''}.`
            : 'Real signals, real outcomes.'}{' '}
          Every closed signal counts. Nothing cherry-picked.
        </p>
        <div
          className="t-ui-micro"
          style={{ color: 'var(--text-3)', marginTop: 12, letterSpacing: '0.06em' }}
        >
          {lineage}
        </div>
      </header>

      {/* TAB STRIP */}
      <TabStrip tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'live' && <BacktestPanel query={liveQuery} variant="live" />}
      {tab === 'historical' && historicalAvailable && (
        <BacktestPanel query={histQuery} variant="historical" />
      )}
      {tab === 'compare' && historicalAvailable && (
        <ComparePanel liveQuery={liveQuery} histQuery={histQuery} />
      )}
      {tab === 'run' && RUN_LOCAL_ENABLED && <RunLocalPanel />}
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// MAIN PANEL — used by Live + Historical (same shape, different cache)
// ══════════════════════════════════════════════════════════════

function BacktestPanel({ query, variant }) {
  if (query.isLoading) return <PanelSkeleton />;
  if (query.error) {
    return (
      <div style={{ marginTop: 20 }}>
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={18} strokeWidth={1.75} />}
          title="Couldn't load track record"
          body={
            query.error?.message ||
            `The /api/backtest/${variant} endpoint failed. Refresh, or regenerate the backtest blob.`
          }
          height={320}
        />
      </div>
    );
  }
  if (!query.data) return null;

  const data = query.data;
  const stats = data.stats ?? {};
  const equity = (data.equity_curve ?? []).map((p) => ({
    date: p.date || p.month,
    value: p.strategy ?? p.value,
    pct: p.strategy_pct,
  }));
  const lastEquity = equity[equity.length - 1]?.value ?? 0;
  const firstEquity = equity[0]?.value ?? 0;
  const totalReturnPct = firstEquity > 0 ? ((lastEquity - firstEquity) / firstEquity) * 100 : 0;

  // Backend's /backtest/live + /backtest/historical don't currently return
  // max_drawdown / sharpe_ratio / profit_factor. We compute max_drawdown
  // client-side from the equity curve (cheap, deterministic). Sharpe and
  // profit_factor would need trade-level data — left to a future backend
  // improvement; the chart footer already null-guards them.
  let computedMaxDrawdown = null;
  if (equity.length > 1) {
    let peak = equity[0].value;
    let dd = 0;
    for (const p of equity) {
      if (p.value > peak) peak = p.value;
      const drop = peak > 0 ? ((p.value - peak) / peak) * 100 : 0;
      if (drop < dd) dd = drop;
    }
    computedMaxDrawdown = dd;
  }
  const maxDrawdown = stats.max_drawdown ?? computedMaxDrawdown;

  const subtitle = variant === 'live'
    ? `Live for ${stats.days_live ?? 0} days · ${stats.total_signals ?? 0} signals · ${stats.closed_signals ?? 0} closed`
    : `2020-2025 backtest · ${stats.total_signals ?? data.recent_closed?.length ?? 0} trades`;

  // Period accent — used on equity curve section halo. Live → bull, hist → info.
  const periodTone = variant === 'live' ? 'bull' : 'info';

  return (
    <div style={{ marginTop: 20 }}>
      {/* Subtitle line */}
      <div
        className="t-ui-footnote"
        style={{ color: 'var(--text-3)', marginBottom: 20 }}
      >
        {subtitle}
        {variant === 'live' && stats.active_signals > 0 && (
          <>
            {' · '}
            <span style={{ color: 'var(--brand-hi)' }}>
              {stats.active_signals} still in play
            </span>
          </>
        )}
      </div>

      {/* KPI ROW — semantic tones per spec */}
      <section
        className="grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16,
          marginBottom: 28,
        }}
      >
        <KPICard
          label="TOTAL RETURN"
          value={fmtPct(totalReturnPct, 1)}
          tone={totalReturnPct >= 0 ? 'bull' : 'bear'}
          context={
            firstEquity > 0
              ? `${fmtINR(firstEquity)} → ${fmtINR(lastEquity)}`
              : undefined
          }
        />
        <KPICard
          label="WIN RATE"
          value={`${(stats.win_rate ?? 0).toFixed(1)}%`}
          tone="brand"
          context={
            stats.hit_target != null
              ? (() => {
                  const closed = stats.closed_signals ?? 0;
                  const target = stats.hit_target ?? 0;
                  const stopGain = stats.stops_at_gain ?? null;
                  const stopLoss = stats.stops_at_loss ?? null;
                  const totalStops = stats.hit_stop ?? 0;
                  const expired = stats.expired ?? 0;
                  // Show breakdown that distinguishes trailing-at-gain
                  // from real losses, plus a sample-size disclosure when
                  // n is small. Win rate of 95% on 21 trades is wildly
                  // different from 95% on 500 — say so.
                  const breakdown = stopGain != null && stopLoss != null
                    ? `${target} target · ${stopGain} trail-at-gain · ${stopLoss} stop-loss · ${expired} expired`
                    : `${target} target hits · ${totalStops} stops · ${expired} expired`;
                  const sample = closed > 0 && closed < 30
                    ? ` · n=${closed} (small sample)`
                    : closed > 0 ? ` · n=${closed}` : '';
                  return breakdown + sample;
                })()
              : undefined
          }
        />
        <KPICard
          label="AVG RETURN"
          value={fmtPct(stats.avg_return_pct ?? 0, 2)}
          tone={(stats.avg_return_pct ?? 0) >= 0 ? 'bull' : 'bear'}
          context="per closed trade"
        />
        <KPICard
          label={variant === 'live' ? 'OPEN P&L' : 'MAX DRAWDOWN'}
          value={
            variant === 'live'
              ? fmtPct(stats.avg_open_pnl_pct ?? 0)
              : maxDrawdown != null ? fmtPct(maxDrawdown, 2) : '—'
          }
          tone={
            variant === 'live'
              ? ((stats.avg_open_pnl_pct ?? 0) >= 0 ? 'bull' : 'bear')
              : 'bear'
          }
          context={
            variant === 'live'
              ? `${stats.active_signals ?? 0} active`
              : maxDrawdown != null ? 'peak-to-trough during period' : 'computed from equity curve'
          }
        />
      </section>

      {/* EQUITY CURVE — hero with dot-prefix section title */}
      <SectionHeader
        tone={periodTone}
        title="Equity curve"
        subtitle={
          variant === 'live'
            ? 'Strategy equity since the cron started writing signals.'
            : 'Walk-forward backtest equity across the 2020–2025 window.'
        }
      />
      <section style={{ marginBottom: 32 }}>
        <ChartCard
          badge={
            variant === 'live'
              ? <StatusChip tone="bull">LIVE</StatusChip>
              : <StatusChip tone="info">BACKTEST</StatusChip>
          }
          height={400}
          footer={
            stats && (
              <>
                {stats.win_rate != null && (
                  <Meta label="WR" value={`${(stats.win_rate || 0).toFixed(1)}%`} />
                )}
                {stats.profit_factor != null && (
                  <Meta label="PF" value={stats.profit_factor.toFixed(2)} />
                )}
                {stats.sharpe_ratio != null && (
                  <Meta label="Sharpe" value={stats.sharpe_ratio.toFixed(2)} />
                )}
              </>
            )
          }
        >
          {equity.length === 0 ? (
            <EmptyCard
              variant="info"
              icon={<TrendingUp size={18} strokeWidth={1.75} />}
              title={variant === 'live' ? 'No equity data yet' : 'No backtest equity data'}
              body={
                variant === 'live'
                  ? 'Once the cron closes its first signal, the curve fills in here.'
                  : 'Regenerate the backtest blob to populate this curve.'
              }
              height={340}
            />
          ) : (
            <EquityCurveChart data={equity} height={400} tone={totalReturnPct >= 0 ? 'bull' : 'bear'} />
          )}
        </ChartCard>
      </section>

      {/* MONTHLY HEATMAP + EXIT DONUT — 8/4 split, stacks on mobile */}
      <SectionHeader
        tone="info"
        title="Returns by month & exit type"
        subtitle="Heatmap sums each month's closed P&L. Donut groups exits by reason."
      />
      <section
        className="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]"
        style={{
          gap: 16,
          marginBottom: 32,
        }}
      >
        <ChartCard title="Monthly returns" height="auto">
          <div style={{ paddingTop: 8 }}>
            {Object.keys(data.monthly_returns ?? {}).length === 0 ? (
              <EmptyCard variant="muted" title="No monthly data yet" height={200} />
            ) : (
              <MonthlyHeatmap data={data.monthly_returns ?? {}} />
            )}
          </div>
        </ChartCard>
        <ChartCard title="Exit reasons" height="auto">
          <div style={{ paddingTop: 8 }}>
            {(data.exit_reasons ?? []).length === 0 ? (
              <EmptyCard variant="muted" title="No exits yet" height={200} />
            ) : (
              <ExitReasonsDonut data={data.exit_reasons ?? []} height={240} />
            )}
          </div>
        </ChartCard>
      </section>

      {/* RECENT CLOSED TRADES */}
      <section>
        <SectionHeader
          tone="muted"
          title="Recent closed trades"
          subtitle={`${(data.recent_closed ?? []).length} shown · sorted by exit date`}
        />
        <DataTable
          rows={(data.recent_closed ?? []).map((t, i) => ({ id: t.id ?? i, ...t }))}
          initialSort={{ key: 'date', dir: 'desc' }}
          emptyState={
            <EmptyCard
              variant="info"
              icon={<TrendingUp size={18} strokeWidth={1.75} />}
              title="No closed trades yet"
              body={
                variant === 'live'
                  ? 'Trades appear here as soon as a signal closes (hit target, hit stop, or time-expired).'
                  : 'No data — try the live tab.'
              }
              height={200}
            />
          }
          columns={[
            { key: 'date',   header: 'Closed',  sortable: true, width: '120px' },
            { key: 'symbol', header: 'Ticker',  sortable: true, width: '130px' },
            {
              key: 'side',
              header: 'Side',
              width: '70px',
              render: (v) => (
                <span
                  style={{
                    color: v === 'LONG' || v === 'BUY' ? 'var(--bull)' : 'var(--bear)',
                    fontWeight: 600,
                    fontSize: 12,
                  }}
                >
                  {v}
                </span>
              ),
            },
            { key: 'entry',  header: 'Entry',   sortable: true, align: 'right', render: (v) => fmtPrice(v) },
            { key: 'exit',   header: 'Exit',    sortable: true, align: 'right', render: (v) => fmtPrice(v) },
            {
              key: 'pnlPct',
              header: 'Return',
              sortable: true,
              align: 'right',
              render: (v) => (
                <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtPct(v)}</span>
              ),
            },
            { key: 'holdDays',   header: 'Days',  sortable: true, align: 'right', width: '70px' },
            {
              key: 'exitReason',
              header: 'Reason',
              render: (v) => (
                <span className="t-ui-footnote" style={{ color: 'var(--text-2)' }}>{v}</span>
              ),
            },
          ]}
        />
      </section>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// COMPARE PANEL — overlay live vs historical equity curves
// ══════════════════════════════════════════════════════════════

function ComparePanel({ liveQuery, histQuery }) {
  const merged = useMemo(() => {
    if (!liveQuery.data || !histQuery.data) return null;
    // Normalize both to a percent-from-start basis so amounts of capital
    // don't dominate the chart. Then key by ordinal day-since-start so the
    // two periods overlay cleanly even if dates differ by years.
    const live = (liveQuery.data.equity_curve ?? []).map((p, i) => ({
      day: i,
      live_pct: p.strategy_pct ?? 0,
    }));
    const hist = (histQuery.data.equity_curve ?? []).map((p, i) => ({
      day: i,
      historical_pct: p.strategy_pct ?? (p.strategy != null && histQuery.data.equity_curve[0]?.strategy
        ? ((p.strategy / histQuery.data.equity_curve[0].strategy) - 1) * 100
        : 0),
    }));
    const len = Math.max(live.length, hist.length);
    const out = [];
    for (let i = 0; i < len; i++) {
      out.push({
        day: i,
        live_pct: live[i]?.live_pct,
        historical_pct: hist[i]?.historical_pct,
      });
    }
    return out;
  }, [liveQuery.data, histQuery.data]);

  if (liveQuery.isLoading || histQuery.isLoading) return <PanelSkeleton />;
  if (!merged) {
    return (
      <div style={{ marginTop: 20 }}>
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={18} strokeWidth={1.75} />}
          title="Couldn't compare"
          body="Failed to load either live or historical track record."
          height={320}
        />
      </div>
    );
  }

  return (
    <div style={{ marginTop: 20 }}>
      <SectionHeader
        tone="brand"
        title="Live vs Historical"
        subtitle="Both series normalized to % gain from start so amounts of capital don't dominate. Live is amber (filled), historical is dashed soft-blue."
      />
      <ChartCard title="% from start" height={420}>
        <ResponsiveContainer width="100%" height={420}>
          <ComposedChart data={merged} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="day"
              tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.48)', fontFamily: 'var(--font-mono)' }}
              axisLine={{ stroke: 'var(--edge-1)' }}
              tickLine={false}
              minTickGap={40}
              label={{
                value: 'Days since start',
                position: 'insideBottom',
                offset: -2,
                fill: 'rgba(255,255,255,0.4)',
                fontSize: 10,
                fontFamily: 'var(--font-sans)',
              }}
            />
            <YAxis
              tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.48)', fontFamily: 'var(--font-mono)' }}
              axisLine={false}
              tickLine={false}
              width={56}
              tickFormatter={(v) => `${v.toFixed(0)}%`}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--surface-modal)',
                border: '1px solid var(--edge-2)',
                borderRadius: 'var(--r-chip)',
                fontFamily: 'var(--font-sans)',
              }}
              formatter={(v) => `${(v ?? 0).toFixed(2)}%`}
              labelFormatter={(d) => `Day ${d}`}
              cursor={{ stroke: 'var(--edge-3)', strokeWidth: 1, strokeDasharray: '2 3' }}
            />
            <Line
              type="monotone"
              dataKey="historical_pct"
              stroke="var(--info)"
              strokeWidth={1.5}
              strokeDasharray="3 3"
              dot={false}
              isAnimationActive={false}
              name="Historical"
            />
            <Area
              type="monotone"
              dataKey="live_pct"
              stroke="var(--brand)"
              strokeWidth={2}
              fill="var(--brand-soft)"
              isAnimationActive={false}
              name="Live"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// RUN LOCAL — gated behind REACT_APP_RUN_LOCAL_ENABLED env flag.
// Backend's /api/backtest/run currently returns a stub error; this
// panel only renders when the flag is set to 'true' (i.e. you've
// wired the local-run endpoint).
//
// Earlier versions printed hardcoded fake progress lines ('> Loading
// model v1...', '> Walking forward...') before the actual API call —
// removed because the simulated stream read as if a feature was
// almost-working when nothing real was happening.
// ══════════════════════════════════════════════════════════════

function RunLocalPanel() {
  const [running, setRunning] = useState(false);
  const [params, setParams] = useState({ start: '2024-01-01', end: '2024-12-31' });
  const [output, setOutput] = useState([]);

  const handleRun = async () => {
    setRunning(true);
    setOutput([`> Submitting backtest ${params.start} → ${params.end}...`]);
    try {
      const { runBacktest } = await import('@/services/api');
      const result = await runBacktest(params);
      setOutput((prev) => [
        ...prev,
        `> Done. ${result?.summary || JSON.stringify(result).slice(0, 80)}`,
      ]);
    } catch (e) {
      setOutput((prev) => [...prev, `! Run failed: ${e?.message || e}`]);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ marginTop: 20 }}>
      <SectionHeader
        tone="warn"
        title="Run a custom backtest"
        subtitle="Run against any date range. Results don't persist — sandbox for exploring 'what if I'd traded these dates.'"
      />

      <div
        className="grid"
        style={{
          gridTemplateColumns: '1fr 1fr auto',
          gap: 12,
          marginBottom: 16,
          alignItems: 'end',
        }}
      >
        <div>
          <label className="t-ui-micro" style={{ color: 'var(--text-3)', display: 'block', marginBottom: 6 }}>
            START
          </label>
          <input
            type="date"
            value={params.start}
            onChange={(e) => setParams({ ...params, start: e.target.value })}
            className="t-num-body"
            style={{
              width: '100%',
              background: 'var(--surface-3)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-chip)',
              padding: '10px 12px',
              color: 'var(--text-1)',
              outline: 'none',
              fontFamily: 'var(--font-mono)',
              fontSize: 14,
              colorScheme: 'dark',
            }}
          />
        </div>
        <div>
          <label className="t-ui-micro" style={{ color: 'var(--text-3)', display: 'block', marginBottom: 6 }}>
            END
          </label>
          <input
            type="date"
            value={params.end}
            onChange={(e) => setParams({ ...params, end: e.target.value })}
            className="t-num-body"
            style={{
              width: '100%',
              background: 'var(--surface-3)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-chip)',
              padding: '10px 12px',
              color: 'var(--text-1)',
              outline: 'none',
              fontFamily: 'var(--font-mono)',
              fontSize: 14,
              colorScheme: 'dark',
            }}
          />
        </div>
        <button
          type="button"
          onClick={handleRun}
          disabled={running}
          className="t-ui-callout"
          style={{
            padding: '10px 18px',
            background: running ? 'var(--surface-3)' : 'var(--brand)',
            color: running ? 'var(--text-3)' : 'var(--brand-fg)',
            border: `1px solid ${running ? 'var(--edge-1)' : 'var(--brand)'}`,
            borderRadius: 'var(--r-chip)',
            cursor: running ? 'wait' : 'pointer',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          {running ? <Loader2 size={14} strokeWidth={1.75} className="animate-spin" /> : <Play size={14} strokeWidth={1.75} />}
          {running ? 'Running…' : 'Run backtest'}
        </button>
      </div>

      <div
        style={{
          background: 'var(--surface-1)',
          border: '1px solid var(--edge-1)',
          borderRadius: 'var(--r-card)',
          padding: 16,
          minHeight: 200,
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          lineHeight: 1.55,
          color: 'var(--text-2)',
          whiteSpace: 'pre-wrap',
        }}
      >
        {output.length === 0 ? (
          <span style={{ color: 'var(--text-4)' }}>No output yet. Click "Run backtest".</span>
        ) : (
          output.map((line, i) => (
            <div key={i} style={{ color: line.startsWith('!') ? 'var(--bear)' : 'var(--text-2)' }}>
              {line}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// SHARED SUB-COMPONENTS
// ══════════════════════════════════════════════════════════════

/**
 * TabStrip — bottom-border tab list. Active tab gets a brand underline
 * (existing) plus a small brand-colored dot prefix (new) for stronger
 * visual separation between tabs at a glance. Tone metadata on each tab
 * tints the note (the "since X" / "beta" subtext) so each tab gets its
 * own faint chromatic identity.
 */
function TabStrip({ tabs, active, onChange }) {
  return (
    <div
      role="tablist"
      className="flex items-center"
      style={{ borderBottom: '1px solid var(--edge-1)', gap: 0 }}
    >
      {tabs.map((t) => {
        const isActive = t.value === active;
        const toneEntry = TONE[t.tone] || TONE.muted;
        return (
          <button
            key={t.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(t.value)}
            className="t-ui-subhead"
            style={{
              padding: '12px 16px',
              background: 'transparent',
              color: isActive ? 'var(--text-1)' : 'var(--text-3)',
              border: 'none',
              borderBottom: `2px solid ${isActive ? 'var(--brand)' : 'transparent'}`,
              marginBottom: -1,
              cursor: 'pointer',
              fontWeight: isActive ? 600 : 500,
              transition: 'color var(--dur-hover) var(--ease-out-cubic), border-color var(--dur-hover) var(--ease-out-cubic)',
              display: 'inline-flex',
              alignItems: 'baseline',
              gap: 8,
            }}
          >
            {isActive && (
              <span
                aria-hidden="true"
                style={{
                  display: 'inline-block',
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: toneEntry.dot,
                  boxShadow: `0 0 0 3px ${toneEntry.halo}`,
                  transform: 'translateY(-1px)',
                }}
              />
            )}
            {t.label}
            {t.note && (
              <span
                className="t-num-small"
                style={{
                  color: isActive ? 'var(--text-3)' : 'var(--text-4)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                }}
              >
                {t.note}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/**
 * SectionHeader — dot prefix + tone halo + title + optional subtitle.
 * Matches AnalyticsV2 / TrackRecordV2 / SignalsV2 grammar so the three
 * track-record pages read as a single product.
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

function PanelSkeleton() {
  return (
    <div style={{ marginTop: 20 }}>
      <div
        className="grid grid-cols-2 sm:grid-cols-4"
        style={{
          gap: 16,
          marginBottom: 24,
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
