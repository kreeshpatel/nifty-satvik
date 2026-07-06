/**
 * TrackRecordV2 — Phase 7 redesign of the public-facing track record page.
 *
 * This is the "shareable proof" view — the merged live + backtest timeline,
 * not a single tab. Big editorial header, KPIs split per period, hero live
 * equity curve, monthly heatmap, recent-trades preview, and a clearly
 * labeled "Backtest period" section beneath the live one.
 *
 * Pulls from `/api/backtest/live` (cron-backed) and `/api/backtest/historical`
 * (regenerated monthly). React-query dedupes when the user opens BacktestV2
 * in the same session.
 *
 * 2026-05-20 redesign pass — colorize + layout + typeset + polish:
 *   - LIVE section dot is bull (green), BACKTEST is info (soft blue).
 *     Same dot-prefix grammar as SignalsV2 / AnalyticsV2 so the page
 *     reads like the same product.
 *   - KPI tones split: Total Return → bull/bear, Win Rate → brand,
 *     Trades Closed → muted, Days Live → muted.
 *   - Currency line "as of <rel ago>" + "Ensemble v2.0" lineage line in
 *     t-ui-micro near the hero so the user sees data lineage immediately.
 *   - EmptyCard warn/info variants replace gray EmptyState reflex.
 *   - Historical section only renders if /backtest/historical loads
 *     (404 = not regenerated → page collapses cleanly to live-only).
 */
import React, { useMemo } from 'react';
import { TrendingUp, AlertCircle, Share2 } from 'lucide-react';
import { toast } from 'sonner';
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
import { fmtPct, fmtPrice, fmtINR, fmtRelTime } from '@/lib/format';

// Tone → dot/halo. Same map used by SignalsV2 + AnalyticsV2 so the
// visual grammar stays consistent across pages.
const TONE = {
  brand: { dot: 'var(--brand)', halo: 'var(--brand-soft)' },
  bull:  { dot: 'var(--bull)',  halo: 'var(--bull-soft)'  },
  bear:  { dot: 'var(--bear)',  halo: 'var(--bear-soft)'  },
  info:  { dot: 'var(--info)',  halo: 'var(--info-soft)'  },
  warn:  { dot: 'var(--warn)',  halo: 'var(--warn-soft)'  },
  muted: { dot: 'var(--text-4)', halo: 'var(--edge-2)'    },
};

export default function TrackRecordV2() {
  const liveQuery = useBacktestLive();
  const histQuery = useBacktestHistorical();
  const data = liveQuery.data;
  const histData = histQuery.data;
  const historicalAvailable = !histQuery.isError && !!histData;

  const equity = useMemo(
    () =>
      (data?.equity_curve ?? []).map((p) => ({
        date: p.date || p.month,
        value: p.strategy ?? p.value,
      })),
    [data?.equity_curve],
  );

  const stats = data?.stats ?? {};

  // Compute CAGR, Alpha, Win Rate, Max DD, Sharpe from API or use kit defaults
  const firstEquity = equity[0]?.value ?? 0;
  const lastEquity = equity[equity.length - 1]?.value ?? 0;
  const totalReturnPct =
    firstEquity > 0 ? ((lastEquity - firstEquity) / firstEquity) * 100 : 0;

  // Max DD computation
  const maxDD = useMemo(() => {
    if (equity.length < 2) return 0;
    let peak = equity[0].value;
    let dd = 0;
    for (const p of equity) {
      if (p.value > peak) peak = p.value;
      const drop = peak > 0 ? ((p.value - peak) / peak) * 100 : 0;
      if (drop < dd) dd = drop;
    }
    return dd;
  }, [equity]);

  // COMPLIANCE/CORRECTNESS: never fabricate performance figures. The
  // /api/backtest/live `stats` blob does NOT contain cagr / alpha / sharpe /
  // max_drawdown, so any hardcoded "?? <number>" fallback ALWAYS renders to
  // paying users as if real — a fabricated track record. Use null and show
  // an em-dash when a figure isn't available. (win_rate IS provided; maxDD is
  // computed from the equity curve above.)
  const kpiValues = {
    cagr: stats.cagr ?? null,
    alpha: stats.alpha ?? null,
    winRate: stats.win_rate ?? null,
    maxDD: maxDD !== 0 ? maxDD : (stats.max_drawdown ?? null),
    sharpe: stats.sharpe ?? null,
  };

  const handleShare = async () => {
    const url = window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'Nifty Satvik — Live Track Record',
          text: `Nifty Satvik has returned ${fmtPct(totalReturnPct, 1)} live since ${data?.start_date} with a ${(stats.win_rate ?? 0).toFixed(1)}% win rate.`,
          url,
        });
      } else {
        await navigator.clipboard.writeText(url);
        toast.success('Link copied to clipboard');
      }
    } catch (_) {
      // user cancelled
    }
  };

  // Compose model-version + currency line. Data lineage is what defends
  // the page against the user's "outdated data" complaint — they need to
  // see when the cron last wrote signals, not just a number.
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
    if (data?.as_of) {
      parts.push(`AS OF ${fmtRelTime(new Date(data.as_of)).toUpperCase()}`);
    } else if (liveQuery.dataUpdatedAt) {
      parts.push(`UPDATED ${fmtRelTime(new Date(liveQuery.dataUpdatedAt)).toUpperCase()}`);
    }
    if (data?.start_date) {
      parts.push(`LIVE SINCE ${data.start_date.toUpperCase()}`);
    }
    return parts.join(' · ');
  }, [data?.as_of, data?.start_date, liveQuery.dataUpdatedAt]);

  return (
    <PageShell title="Track Record" heroTone="bull" disclaimer>
      {/* HERO */}
      <header style={{ paddingTop: 32, paddingBottom: 28 }}>
        <div className="flex items-start justify-between flex-wrap" style={{ gap: 16 }}>
          <div className="min-w-0">
            <div
              className="t-ui-micro flex items-center"
              style={{ color: 'var(--bull)', marginBottom: 8, gap: 8, letterSpacing: '0.08em' }}
            >
              <span
                aria-hidden="true"
                style={{
                  display: 'inline-block',
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: 'var(--bull)',
                  boxShadow: `0 0 0 3px var(--bull-soft)`,
                }}
              />
              LIVE · NOT SIMULATED
            </div>
            <h1
              className="t-display"
              style={{ margin: 0, color: 'var(--text-1)', fontSize: 'clamp(36px, 5vw, 56px)', lineHeight: 1.05 }}
            >
              The numbers, in public.
            </h1>
            <p
              className="t-prose"
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 18,
                lineHeight: 1.5,
                fontStyle: 'italic',
                color: 'var(--text-2)',
                margin: '14px 0 0',
                maxWidth: '60ch',
              }}
            >
              Every signal Nifty Satvik has fired since {data?.start_date || 'launch'},
              tracked live. Wins counted. Losses counted. No cherry-picking.
            </p>
            <div
              className="t-ui-micro"
              style={{ color: 'var(--text-3)', marginTop: 12, letterSpacing: '0.06em' }}
            >
              {lineage}
            </div>
          </div>
          <button
            type="button"
            onClick={handleShare}
            className="t-ui-callout"
            style={{
              padding: '10px 18px',
              background: 'transparent',
              color: 'var(--brand-hi)',
              border: '1px solid var(--brand-edge)',
              borderRadius: 'var(--r-chip)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              fontWeight: 600,
            }}
          >
            <Share2 size={14} strokeWidth={1.75} />
            Share
          </button>
        </div>
      </header>

      {liveQuery.isLoading ? (
        <PageSkeleton />
      ) : liveQuery.error ? (
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={18} strokeWidth={1.75} />}
          title="Couldn't load track record"
          body={liveQuery.error?.message || 'The /api/backtest/live endpoint failed. Try refreshing the page.'}
          height={320}
        />
      ) : !data ? null : (
        <>
          {/* HERO STATS CARD — Kit pattern (lines 469-480 of design-system-ref-v2) */}
          <section
            style={{
              background: 'var(--surface-1)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-panel)',
              padding: 26,
              marginBottom: 32,
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
            }}
          >
            {/* STATS ROW — 5 columns on desktop, wraps 2+3 on mobile */}
            <div
              className="grid"
              style={{
                gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                gap: '16px 0',
                marginBottom: 22,
              }}
            >
              {[
                { label: '5Y CAGR', value: kpiValues.cagr != null ? `${kpiValues.cagr.toFixed(1)}%` : '—', color: 'var(--bull)' },
                { label: 'ALPHA', value: kpiValues.alpha != null ? `+${kpiValues.alpha.toFixed(1)}%` : '—', color: 'var(--text-1)' },
                { label: 'WIN RATE', value: kpiValues.winRate != null ? `${kpiValues.winRate.toFixed(1)}%` : '—', color: 'var(--text-1)' },
                { label: 'MAX DD', value: kpiValues.maxDD != null ? `${kpiValues.maxDD.toFixed(1)}%` : '—', color: 'var(--bear)' },
                { label: 'SHARPE', value: kpiValues.sharpe != null ? kpiValues.sharpe.toFixed(2) : '—', color: 'var(--text-1)' },
              ].map((kpi, i, arr) => (
                <div
                  key={kpi.label}
                  style={{
                    padding: '0 18px',
                    borderRight: i < arr.length - 1 ? '1px solid var(--edge-1)' : 'none',
                  }}
                >
                  <div className="t-ui-micro" style={{ color: 'var(--text-3)', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 8 }}>
                    {kpi.label}
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontVariantNumeric: 'tabular-nums', color: kpi.color, lineHeight: 1 }}>
                    {kpi.value}
                  </div>
                </div>
              ))}
            </div>

            {/* COMPLIANCE/CORRECTNESS: render the REAL live equity curve, not a
                hardcoded decorative SVG. The previous fixed `d="M0,220 ... L800,40"`
                path drew a fabricated always-up curve (plus a fake benchmark) in
                the public hero regardless of actual performance. Use the shared
                chart fed by the computed `equity`, with an honest empty state. */}
            {equity.length < 2 ? (
              <EmptyCard
                variant="info"
                title="Live equity curve appears once signals close"
                height={260}
              />
            ) : (
              <EquityCurveChart
                data={equity}
                height={260}
                tone={totalReturnPct >= 0 ? 'bull' : 'bear'}
              />
            )}
          </section>

          {/* LIVE SECTION HEADER */}
          <SectionHeader
            tone="bull"
            title="Live track record"
            subtitle={`Since ${data.start_date}. Every signal closed in production — counted toward the numbers below.`}
          />

          {/* LIVE KPI ROW — secondary metrics */}
          <section
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 16,
              marginBottom: 24,
            }}
          >
            <KPICard
              label="TOTAL RETURN"
              value={fmtPct(totalReturnPct, 1)}
              tone={totalReturnPct >= 0 ? 'bull' : 'bear'}
              context={firstEquity > 0 ? `${fmtINR(firstEquity)} → ${fmtINR(lastEquity)}` : 'no equity yet'}
            />
            <KPICard
              label="WIN RATE"
              value={`${(stats.win_rate ?? 0).toFixed(1)}%`}
              tone="brand"
              context={`${stats.hit_target ?? 0} target hits · ${stats.hit_stop ?? 0} stops`}
            />
            <KPICard
              label="TRADES CLOSED"
              value={String(stats.closed_signals ?? 0)}
              tone="neutral"
              context={`${stats.active_signals ?? 0} still in play · ${stats.total_signals ?? 0} total`}
            />
            <KPICard
              label="DAYS LIVE"
              value={String(stats.days_live ?? 0)}
              tone="neutral"
              context={`Since ${data.start_date}`}
            />
          </section>

          {/* LIVE EQUITY CURVE — hero */}
          <section style={{ marginBottom: 32 }}>
            <ChartCard
              title="Equity curve"
              badge={<StatusChip tone="bull">LIVE</StatusChip>}
              height={400}
              footer={
                <>
                  <Meta label="Avg / trade" value={fmtPct(stats.avg_return_pct ?? 0, 2)} />
                  <Meta label="Open P&L" value={fmtPct(stats.avg_open_pnl_pct ?? 0, 2)} />
                  <Meta label="Closed" value={`${stats.closed_signals ?? 0}`} />
                </>
              }
            >
              {equity.length === 0 ? (
                <EmptyCard
                  variant="info"
                  icon={<TrendingUp size={18} strokeWidth={1.75} />}
                  title="No equity data yet"
                  body="Once trades start closing, the curve fills in here."
                  height={340}
                />
              ) : (
                <EquityCurveChart data={equity} height={400} tone={totalReturnPct >= 0 ? 'bull' : 'bear'} />
              )}
            </ChartCard>
          </section>

          {/* MONTHLY HEATMAP + EXIT REASONS — stacks on mobile */}
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
                  <EmptyCard
                    variant="muted"
                    title="No monthly data yet"
                    body="Fills in as months close."
                    height={200}
                  />
                ) : (
                  <MonthlyHeatmap data={data.monthly_returns ?? {}} />
                )}
              </div>
            </ChartCard>
            <ChartCard title="How trades closed" height="auto">
              <div style={{ paddingTop: 8 }}>
                {(data.exit_reasons ?? []).length === 0 ? (
                  <EmptyCard
                    variant="muted"
                    title="No exits yet"
                    body="Donut shows once signals close."
                    height={200}
                  />
                ) : (
                  <ExitReasonsDonut data={data.exit_reasons ?? []} height={240} />
                )}
              </div>
            </ChartCard>
          </section>

          {/* LIVE RECENT TRADES */}
          <section style={{ marginBottom: 40 }}>
            <SectionHeader
              tone="bull"
              title="Recent closed trades"
              subtitle="Most recent 30 signals from the live cron, sorted by exit date."
            />
            <DataTable
              rows={(data.recent_closed ?? []).slice(0, 30).map((t, i) => ({
                id: t.id ?? i,
                ...t,
              }))}
              initialSort={{ key: 'date', dir: 'desc' }}
              emptyState={
                <EmptyCard
                  variant="info"
                  icon={<TrendingUp size={18} strokeWidth={1.75} />}
                  title="No closed trades yet"
                  body="As soon as a signal closes (target / stop / time), it lands here."
                  height={200}
                />
              }
              columns={tradeColumns()}
            />
          </section>

          {/* HISTORICAL BACKTEST SECTION */}
          {historicalAvailable && <HistoricalSection histData={histData} />}
        </>
      )}
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// HISTORICAL SECTION — backtest period KPIs + heatmap + table
// ══════════════════════════════════════════════════════════════

function HistoricalSection({ histData }) {
  const stats = histData?.stats ?? {};
  const equity = useMemo(
    () =>
      (histData?.equity_curve ?? []).map((p) => ({
        date: p.date || p.month,
        value: p.strategy ?? p.value,
      })),
    [histData?.equity_curve],
  );
  const first = equity[0]?.value ?? 0;
  const last = equity[equity.length - 1]?.value ?? 0;
  const totalReturn = first > 0 ? ((last - first) / first) * 100 : 0;

  // Compute max DD from the equity curve (same logic as BacktestV2 since
  // /backtest/historical doesn't ship a precomputed max_drawdown field).
  const maxDD = useMemo(() => {
    if (equity.length < 2) return null;
    let peak = equity[0].value;
    let dd = 0;
    for (const p of equity) {
      if (p.value > peak) peak = p.value;
      const drop = peak > 0 ? ((p.value - peak) / peak) * 100 : 0;
      if (drop < dd) dd = drop;
    }
    return dd;
  }, [equity]);

  return (
    <>
      <SectionHeader
        tone="info"
        title="Backtest period (2020 — 2025)"
        subtitle="The full walk-forward backtest run on historical data. Same model, same gate, same exit logic — applied to 5 years of Nifty 500 closes."
      />

      <section
        className="grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16,
          marginBottom: 24,
        }}
      >
        <KPICard
          label="TOTAL RETURN"
          value={fmtPct(totalReturn, 1)}
          tone={totalReturn >= 0 ? 'bull' : 'bear'}
          context={first > 0 ? `${fmtINR(first)} → ${fmtINR(last)}` : 'no equity'}
        />
        <KPICard
          label="WIN RATE"
          value={`${(stats.win_rate ?? 0).toFixed(1)}%`}
          tone="brand"
          context={`${stats.total_signals ?? 0} trades over 5y`}
        />
        <KPICard
          label="MAX DRAWDOWN"
          value={maxDD != null ? fmtPct(maxDD, 1) : '—'}
          tone="bear"
          context="peak-to-trough"
        />
        <KPICard
          label="AVG / TRADE"
          value={fmtPct(stats.avg_return_pct ?? 0, 2)}
          tone={(stats.avg_return_pct ?? 0) >= 0 ? 'bull' : 'bear'}
          context="per closed trade"
        />
      </section>

      <section style={{ marginBottom: 32 }}>
        <ChartCard
          title="Backtest equity curve"
          badge={<StatusChip tone="info">2020 — 2025</StatusChip>}
          height={360}
        >
          {equity.length === 0 ? (
            <EmptyCard variant="muted" title="No backtest equity data" height={300} />
          ) : (
            <EquityCurveChart data={equity} height={360} tone={totalReturn >= 0 ? 'bull' : 'bear'} />
          )}
        </ChartCard>
      </section>

      <section
        className="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]"
        style={{
          gap: 16,
          marginBottom: 32,
        }}
      >
        <ChartCard title="Monthly returns (backtest)" height="auto">
          <div style={{ paddingTop: 8 }}>
            {Object.keys(histData.monthly_returns ?? {}).length === 0 ? (
              <EmptyCard variant="muted" title="No monthly data" height={200} />
            ) : (
              <MonthlyHeatmap data={histData.monthly_returns ?? {}} />
            )}
          </div>
        </ChartCard>
        <ChartCard title="Exit reasons (backtest)" height="auto">
          <div style={{ paddingTop: 8 }}>
            {(histData.exit_reasons ?? []).length === 0 ? (
              <EmptyCard variant="muted" title="No exit data" height={200} />
            ) : (
              <ExitReasonsDonut data={histData.exit_reasons ?? []} height={240} />
            )}
          </div>
        </ChartCard>
      </section>
    </>
  );
}

// ══════════════════════════════════════════════════════════════
// SUB-COMPONENTS
// ══════════════════════════════════════════════════════════════

function SectionHeader({ tone = 'muted', title, subtitle }) {
  const t = TONE[tone] || TONE.muted;
  return (
    <div style={{ marginBottom: 16 }}>
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

// Centralized column spec so the live + historical tables stay in sync.
function tradeColumns() {
  return [
    { key: 'date',   header: 'Closed',  sortable: true, width: '110px' },
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
    { key: 'entry', header: 'Entry', sortable: true, align: 'right', render: (v) => fmtPrice(v) },
    { key: 'exit',  header: 'Exit',  sortable: true, align: 'right', render: (v) => fmtPrice(v) },
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
  ];
}

function PageSkeleton() {
  return (
    <div>
      <div
        className="grid grid-cols-2 sm:grid-cols-4"
        style={{
          gap: 16,
          marginBottom: 32,
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
          minHeight: 420,
          animation: 'skelPulse 1.8s ease-in-out infinite',
        }}
      />
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}
