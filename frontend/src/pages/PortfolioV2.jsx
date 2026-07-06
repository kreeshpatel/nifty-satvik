/**
 * PortfolioV2 — Portfolio page.
 *
 * Architecture:
 *   - Headline data via useOverview   (60s stale — shared with Dashboard)
 *   - Holdings from useKiteHoldings   (30s stale + WS patch) with
 *     usePaperPositions as the Kite-off fallback
 *   - Orders from useKiteOrders       (30s stale + WS patch)
 *   - Trade history from useTrades    (infinite query, 15min stale)
 *
 * Layout (per plan §7 Flagship #2):
 *   KPI ROW  (Total Capital | Today's P&L | Deployed % | Cash Available)
 *   ──────────────────────────────────────────────────────
 *   EQUITY CURVE  (320px, period switch)
 *   ──────────────────────────────────────────────────────
 *   TABS  (Holdings · Orders · Trades)
 *   DataTable (per tab)
 *
 * No AddTradeModal — trading happens from Signals/StockDetail only, per plan.
 * No mock data — portfolioData.js is not imported anywhere in this file.
 */
import React, { useContext, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowDown, AlertCircle, Plug, Inbox, ReceiptText, RefreshCcw, Target } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { KPICard } from '@/components/shared/KPICard';
import { ChartCard } from '@/components/shared/ChartCard';
import { DataTable } from '@/components/shared/DataTable';
import { EquityCurveChart } from '@/components/shared/EquityCurveChart';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { StatusChip } from '@/components/shared/StatusChip';
import { PositionCard } from '@/components/shared/PositionCard';
import { useOverview } from '@/hooks/queries/useOverview';
import { useKiteHoldings, useKiteMargins } from '@/hooks/queries/useKiteState';
import { useKiteOrders } from '@/hooks/queries/useKiteOrders';
import { usePaperPositions } from '@/hooks/queries/usePaperPositions';
import { useNQPositions } from '@/hooks/queries/useNQPositions';
import { useExternalHoldings } from '@/hooks/queries/useExternalHoldings';
import { useNavHistory } from '@/hooks/queries/useNavHistory';
import { useTrades, flattenTrades } from '@/hooks/queries/useTrades';
import { KiteContext } from '@/App';
import { fmtINR, fmtPrice, fmtPct, fmtRelTime } from '@/lib/format';

const PERIOD_OPTIONS = [
  { label: '1M',  value: '1M', days: 30 },
  { label: '3M',  value: '3M', days: 90 },
  { label: '6M',  value: '6M', days: 180 },
  { label: '1Y',  value: '1Y', days: 365 },
  { label: 'All', value: 'All', days: null },
];

const TABS = [
  { value: 'holdings', label: 'Holdings' },
  { value: 'orders',   label: 'Orders' },
  { value: 'trades',   label: 'Trades' },
];

// Section tone palette — matches SignalsV2 conventions so the dashboard
// reads chromatically the same way across pages.
const TONE_COLORS = {
  brand: { dot: 'var(--brand)', halo: 'var(--brand-soft)', count: 'var(--brand)' },
  bull:  { dot: 'var(--bull)',  halo: 'var(--bull-soft)',  count: 'var(--bull)' },
  info:  { dot: 'var(--info)',  halo: 'var(--info-soft)',  count: 'var(--info)' },
  warn:  { dot: 'var(--warn)',  halo: 'var(--warn-soft)',  count: 'var(--warn)' },
  bear:  { dot: 'var(--bear)',  halo: 'var(--bear-soft)',  count: 'var(--bear)' },
  muted: { dot: 'var(--text-4)', halo: 'var(--edge-2)',    count: 'var(--text-3)' },
};

export default function PortfolioV2() {
  const kite = useContext(KiteContext);
  const navigate = useNavigate();
  const [tab, setTab] = useState('holdings');
  const [period, setPeriod] = useState('3M');

  const overviewQuery = useOverview();
  const marginsQuery = useKiteMargins({ enabled: !!kite?.connected });
  const kiteHoldingsQuery = useKiteHoldings({ enabled: !!kite?.connected });
  const paperPositionsQuery = usePaperPositions({ enabled: !kite?.connected });
  const ordersQuery = useKiteOrders({ enabled: !!kite?.connected });
  const tradesQuery = useTrades({ perPage: 50 });

  // V2 split: NQ-tracked positions and the residual external Kite
  // holdings. Both run regardless of Kite-connected state so a user who
  // has bought NQ signals via paper-mode (when we add that path) still
  // sees them. The hooks short-circuit gracefully when there's no data.
  const nqPositionsQuery = useNQPositions();
  const externalHoldingsQuery = useExternalHoldings({ enabled: !!kite?.connected });
  // Daily NAV snapshots — auto-written by /api/positions/nq, read here
  // for the equity curve. Series starts empty for new users; backend
  // skips zero-NAV rows so a Kite-disconnected day doesn't pollute
  // the chart with a misleading ₹0 dip.
  const navHistoryQuery = useNavHistory();

  // ── Headline numbers ──────────────────────────────────
  // Prefer live Kite state when connected, fall back to the paper portfolio
  // snapshot from /api/overview for users who haven't wired Kite yet.
  const overview = overviewQuery.data;
  const portfolio = overview?.portfolio ?? {};

  const holdings = kite?.connected
    ? (kiteHoldingsQuery.data ?? [])
    : (paperPositionsQuery.data ?? []);

  // Holdings market value — used for both `invested` and `totalCapital`.
  // Computed up-front so the KPI math below has a single source of truth.
  const invested = kite?.connected
    ? holdings.reduce((sum, h) => sum + (Number(h.last_price) || 0) * (Number(h.quantity) || 0), 0)
    : (portfolio?.invested ?? 0);

  // Today's P&L. Kite's `day_change` field is the per-share gain since
  // yesterday's close — accurate for held-overnight positions but returns 0
  // for freshly-bought T+1 holdings (no "previous close" reference yet).
  // When EVERY holding reports day_change=0 we fall back to total unrealised
  // P&L (ltp - avg) × qty so a fresh-buy day shows the actual gain rather
  // than "+₹0" — matches what Kite's web UI shows in that case.
  const todayPnL = useMemo(() => {
    if (kite?.connected) {
      const list = kiteHoldingsQuery.data ?? [];
      const dayChangeSum = list.reduce(
        (sum, h) => sum + (Number(h.day_change) || 0) * (Number(h.quantity) || 0),
        0,
      );
      if (dayChangeSum !== 0) return dayChangeSum;
      // All-zero day_change → fall back to total unrealised P&L.
      return list.reduce(
        (sum, h) => sum + ((Number(h.last_price) || 0) - (Number(h.average_price) || 0)) * (Number(h.quantity) || 0),
        0,
      );
    }
    return (paperPositionsQuery.data ?? []).reduce(
      (sum, p) => sum + (Number(p.unrealised_pnl) || 0),
      0,
    );
  }, [kite?.connected, kiteHoldingsQuery.data, paperPositionsQuery.data]);

  // Total capital = cash + blocked margin + market value of holdings.
  // Kite's /user/margins endpoint only returns cash + blocked (margins.total
  // = available + used) — it has no concept of holdings value, that lives in
  // /portfolio/holdings. So summing margins.total alone misses the entire
  // value of the user's positions and rendered "Total ₹143" when actual net
  // worth was ~₹515. Including `invested` here makes the number match what
  // the user sees on Kite Web's Console.
  const totalCapital = kite?.connected
    ? ((marginsQuery.data?.total ?? 0) + invested)
    : (portfolio?.total_value ?? 0);

  const cash = kite?.connected
    ? (marginsQuery.data?.available ?? portfolio?.cash ?? 0)
    : (portfolio?.cash ?? 0);

  const deployedPct = totalCapital > 0 ? (invested / totalCapital) * 100 : 0;
  const todayPnLPct = totalCapital > 0 ? (todayPnL / totalCapital) * 100 : 0;

  // ── Equity curve data, sliced by period ───────────────
  // Prefer the per-user NAV history written by /api/positions/nq
  // snapshots — that's real Kite NAV over time. Fall back to the
  // overview's equity_curve (paper-portfolio CSV) only if the user has
  // no NAV history yet (new account, or Kite never connected).
  const equityCurve = useMemo(() => {
    const navRows = navHistoryQuery.data?.history ?? [];
    const source = navRows.length > 0
      ? navRows
      : (overview?.equity_curve ?? []);
    const days = PERIOD_OPTIONS.find((p) => p.value === period)?.days;
    if (!days || source.length <= days) {
      return source.map((p) => ({ date: p.date, value: p.value }));
    }
    return source.slice(-days).map((p) => ({ date: p.date, value: p.value }));
  }, [navHistoryQuery.data, overview?.equity_curve, period]);

  const navHistoryCount = navHistoryQuery.data?.count ?? 0;

  const loadingHeadline = overviewQuery.isLoading ||
    (kite?.connected
      ? kiteHoldingsQuery.isLoading || marginsQuery.isLoading
      : paperPositionsQuery.isLoading);

  return (
    <PageShell title="Portfolio" heroTone="info">
      {/* Page title + Kite status */}
      <header style={{ paddingTop: 24, paddingBottom: 16 }}>
        <h1 className="t-title-1" style={{ margin: 0, color: 'var(--text-1)' }}>Portfolio</h1>
        <div
          className="t-ui-footnote flex items-center flex-wrap"
          style={{ color: 'var(--text-3)', marginTop: 6, gap: 10 }}
        >
          {kite?.connected ? (
            <StatusChip tone="bull">KITE CONNECTED</StatusChip>
          ) : (
            <StatusChip tone="muted">PAPER</StatusChip>
          )}
          {overviewQuery.dataUpdatedAt && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>Updated {fmtRelTime(new Date(overviewQuery.dataUpdatedAt))}</span>
            </>
          )}
        </div>
      </header>

      {/* No-Kite banner — info-toned, non-blocking notice */}
      {!kite?.connected && (
        <div
          className="flex items-start"
          style={{
            background: 'var(--info-soft)',
            border: '1px solid oklch(78% 0.11 230 / 0.32)',
            borderRadius: 'var(--r-card)',
            padding: '14px 16px',
            gap: 12,
            marginBottom: 20,
          }}
        >
          <Plug size={16} strokeWidth={1.75} style={{ color: 'var(--info)', marginTop: 3, flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <p className="t-ui-body" style={{ color: 'var(--text-1)', margin: 0 }}>
              <strong>You're viewing paper positions.</strong>{' '}
              <span style={{ color: 'var(--text-2)' }}>
                Connect Kite to see your real holdings, orders, and margins.
              </span>
            </p>
            <button
              type="button"
              onClick={kite?.connect}
              className="t-ui-callout"
              style={{
                marginTop: 10,
                padding: '7px 14px',
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
          </div>
        </div>
      )}

      {/* KPI ROW — semantic tones drive the value color so the page reads
          left-to-right: brand (hero) · bull/bear (today) · neutral · info. */}
      <section
        className="grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16,
          marginBottom: 24,
        }}
      >
        <KPICard
          label="TOTAL CAPITAL"
          value={loadingHeadline ? '—' : fmtINR(totalCapital)}
          tone="brand"
          context={
            portfolio?.peak_value
              ? `Peak ${fmtINR(portfolio.peak_value)} · ${(portfolio?.drawdown_pct || 0).toFixed(2)}% from peak`
              : 'Cash + holdings · live from Kite'
          }
        />
        <KPICard
          label="TODAY'S P&L"
          value={loadingHeadline ? '—' : `${todayPnL >= 0 ? '+' : ''}${fmtINR(todayPnL)}`}
          tone={todayPnL >= 0 ? 'bull' : 'bear'}
          context={
            <span style={{ color: todayPnL >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
              {fmtPct(todayPnLPct)}{' '}
              <span style={{ color: 'var(--text-3)' }}>vs previous close</span>
            </span>
          }
        />
        <KPICard
          label="DEPLOYED"
          value={loadingHeadline ? '—' : `${deployedPct.toFixed(1)}%`}
          tone="neutral"
          context={`${fmtINR(invested)} across ${holdings.length} position${holdings.length !== 1 ? 's' : ''}`}
        />
        <KPICard
          label="CASH AVAILABLE"
          value={loadingHeadline ? '—' : fmtINR(cash)}
          tone="neutral"
          context={
            <span>
              <span style={{ color: 'var(--info)' }}>{(100 - deployedPct).toFixed(1)}%</span>
              <span style={{ color: 'var(--text-3)' }}> of capital · ready to deploy</span>
            </span>
          }
        />
      </section>

      {/* ALLOCATION STRIP — only render when there's something to show. */}
      {invested > 0 && holdings.length > 0 && (
        <AllocationStrip holdings={holdings} invested={invested} />
      )}

      {/* EQUITY CURVE */}
      <section style={{ marginBottom: 24 }}>
        <ChartCard
          title="Equity Curve"
          badge={overview?.metrics?.total_trades ? (
            <StatusChip tone="muted">{overview.metrics.total_trades} trades</StatusChip>
          ) : null}
          periods={PERIOD_OPTIONS.map((p) => ({ ...p, active: p.value === period }))}
          onPeriodChange={setPeriod}
          height={320}
          footer={
            overview?.metrics && (
              <>
                <MetaPair label="Win rate" value={`${(overview.metrics.win_rate || 0).toFixed(1)}%`} />
                <MetaPair label="Sharpe" value={(overview.metrics.sharpe_ratio || 0).toFixed(2)} />
                <MetaPair label="Profit factor" value={(overview.metrics.profit_factor || 0).toFixed(2)} />
                <MetaPair label="Avg hold" value={`${(overview.metrics.avg_hold_days || 0).toFixed(1)}d`} />
              </>
            )
          }
        >
          {overviewQuery.isLoading ? (
            <EquityCurveSkeleton />
          ) : (
            <EquityCurveChart data={equityCurve} height={320} tone="auto" />
          )}
        </ChartCard>
      </section>

      {/* TABS */}
      <section>
        <TabStrip tabs={TABS} active={tab} onChange={setTab} />

        {tab === 'holdings' && (
          kite?.connected ? (
            <HoldingsSplitTab
              nqQuery={nqPositionsQuery}
              externalQuery={externalHoldingsQuery}
              onSell={(position) => {
                // Navigate to StockDetail with sell intent — the OrderPad
                // there is already wired to the order-placement mutation
                // and will be enhanced in PR4 to honour these query params.
                navigate(
                  `/stock/${encodeURIComponent(position.ticker)}?action=sell&qty=${position.held_qty}&signal_id=${encodeURIComponent(position.signal_id)}`,
                );
              }}
            />
          ) : (
            <HoldingsTab
              holdings={holdings}
              isPaper={true}
              isLoading={paperPositionsQuery.isLoading}
              error={paperPositionsQuery.error}
            />
          )
        )}

        {tab === 'orders' && (
          <OrdersTab
            orders={kite?.connected ? (ordersQuery.data ?? []) : []}
            kiteConnected={!!kite?.connected}
            isLoading={kite?.connected && ordersQuery.isLoading}
          />
        )}

        {tab === 'trades' && (
          <TradesTab
            infiniteQuery={tradesQuery}
          />
        )}
      </section>
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// TAB CONTENTS
// ══════════════════════════════════════════════════════════════

/**
 * HoldingsSplitTab — Kite-connected variant of the Holdings tab.
 *
 * Two stacked sections:
 *   1. Nifty Satvik Positions — PositionCard grid with full signal context
 *      and sell guidance. Sourced from /api/positions/nq.
 *   2. Other Kite Holdings — DataTable of Kite holdings minus NQ-attributed
 *      qty. Includes pre-existing positions and external trades.
 *
 * The strict-overlap rule on the backend ensures qty totals never
 * double-count across the two sections.
 */
function HoldingsSplitTab({ nqQuery, externalQuery, onSell }) {
  const nqLoading = nqQuery.isLoading;
  const nqError = nqQuery.error;
  const nqPositions = nqQuery.data?.positions ?? [];

  const externalLoading = externalQuery.isLoading;
  const externalError = externalQuery.error;
  const externalHoldings = externalQuery.data?.holdings ?? [];

  return (
    <div className="flex flex-col gap-8">
      {/* ───── Nifty Satvik Positions ───── */}
      <SectionHeader
        title="Nifty Satvik Positions"
        count={nqPositions.length}
        tone="brand"
        subtitle="Tracked by signal — entry, stop, target, and sell guidance shown."
      />
      {nqLoading ? (
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 360px), 1fr))', gap: 12 }}
        >
          {Array.from({ length: 3 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : nqError ? (
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={16} strokeWidth={1.75} />}
          title="Couldn't load Nifty Satvik positions"
          body={nqError?.message || 'Try refreshing.'}
        />
      ) : nqPositions.length === 0 ? (
        <EmptyCard
          variant="muted"
          icon={<Target size={16} strokeWidth={1.75} />}
          title="No tracked positions yet"
          body="When you buy a signal through Nifty Satvik, it appears here with full lifecycle tracking."
        />
      ) : (
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 360px), 1fr))', gap: 12 }}
        >
          {nqPositions.map((p) => (
            <PositionCard key={p.signal_id} position={p} onSell={onSell} />
          ))}
        </div>
      )}

      {/* ───── Other Kite Holdings ───── */}
      <SectionHeader
        title="Other Kite Holdings"
        count={externalHoldings.length}
        tone="info"
        subtitle="Positions in your Kite account that weren't bought via Nifty Satvik."
      />
      {externalLoading ? (
        <TableSkeleton rows={4} />
      ) : externalError ? (
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={16} strokeWidth={1.75} />}
          title="Couldn't load external holdings"
          body={externalError?.message || 'Try refreshing.'}
        />
      ) : externalHoldings.length === 0 ? (
        <EmptyCard
          variant="muted"
          icon={<Inbox size={16} strokeWidth={1.75} />}
          title="No external holdings"
          body="Every position in your Kite account is tracked by Nifty Satvik."
        />
      ) : (
        <DataTable
          columns={[
            {
              key: 'tradingsymbol',
              header: 'Ticker',
              sortable: true,
              width: '180px',
              render: (v, row) => (
                <span className="flex items-center gap-2">
                  <span>{v}</span>
                  <StatusChip tone="muted">EXTERNAL</StatusChip>
                  {row.nq_attributed_qty > 0 && (
                    <span className="t-ui-micro opacity-70">
                      (+{row.nq_attributed_qty} tracked separately)
                    </span>
                  )}
                </span>
              ),
            },
            { key: 'quantity',      header: 'Qty',   sortable: true, align: 'right', width: '80px' },
            { key: 'average_price', header: 'Avg',   sortable: true, align: 'right', render: (v) => fmtPrice(v || 0) },
            { key: 'last_price',    header: 'LTP',   sortable: true, align: 'right', render: (v) => fmtPrice(v || 0) },
            {
              key: 'value',
              header: 'Value',
              sortable: true,
              align: 'right',
              render: (_, row) => fmtINR((Number(row.last_price) || 0) * (Number(row.quantity) || 0)),
            },
            {
              key: 'pnl',
              header: 'P&L',
              sortable: true,
              align: 'right',
              render: (_, row) => {
                const pnl = ((Number(row.last_price) || 0) - (Number(row.average_price) || 0)) * (Number(row.quantity) || 0);
                return (
                  <span style={{ color: pnl >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
                    {pnl >= 0 ? '+' : ''}{fmtINR(pnl)}
                  </span>
                );
              },
            },
          ]}
          rows={externalHoldings.map((h, i) => ({ id: h.tradingsymbol ?? `ext-${i}`, ...h }))}
          initialSort={{ key: 'value', dir: 'desc' }}
        />
      )}
    </div>
  );
}

function SectionHeader({ title, count, subtitle, tone = 'muted', unit = 'position' }) {
  const t = TONE_COLORS[tone] || TONE_COLORS.muted;
  return (
    <div>
      <div className="flex items-baseline" style={{ gap: 10 }}>
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
              background: t.dot,
              boxShadow: `0 0 0 3px ${t.halo}`,
              flexShrink: 0,
              marginRight: 7,
              marginLeft: 3,
              transform: 'translateY(-2px)',
            }}
          />
          {title}
        </h2>
        <span
          className="t-num-small"
          style={{ color: t.count, fontFamily: 'var(--font-mono)' }}
        >
          {count}
        </span>
        <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>
          {count === 1 ? unit : `${unit}s`}
        </span>
      </div>
      {subtitle && (
        <p
          className="t-ui-footnote"
          style={{ color: 'var(--text-2)', margin: '4px 0 12px 0' }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

/**
 * AllocationStrip — single-row stacked bar showing how invested capital is
 * split across the top 5 positions. Replaces the "decorative pie chart"
 * temptation with a 12px-tall honest bar that reads at a glance:
 *   what % of my deployed cash is in my top 5 names vs the long tail?
 *
 * No sector data on the Kite holdings shape, so we use ticker — which is
 * the data we actually have. Sectors can graduate in once the backend
 * starts returning a sector column on /kite/holdings.
 */
function AllocationStrip({ holdings, invested }) {
  if (!invested || invested <= 0 || !holdings?.length) return null;

  const valued = holdings
    .map((h) => {
      const ticker = h.tradingsymbol || h.ticker;
      const value =
        (Number(h.last_price ?? h.current_price) || 0) *
        (Number(h.quantity ?? h.shares) || 0);
      return { ticker, value };
    })
    .filter((x) => x.value > 0)
    .sort((a, b) => b.value - a.value);

  if (!valued.length) return null;

  const top = valued.slice(0, 5);
  const restValue = valued.slice(5).reduce((s, x) => s + x.value, 0);
  const segments = [...top];
  if (restValue > 0) {
    segments.push({ ticker: `+${valued.length - 5} more`, value: restValue });
  }

  // Pre-defined warm palette — staying within the V2 token harmony. The
  // first 5 ramp through brand → bull → info → warn → bear in soft-saturation
  // form so each segment is distinguishable without competing with the
  // page's semantic P&L colors.
  const palette = [
    '#4F8CFF',   // brand-ish
    '#72C766',  // bull-ish
    '#5BA3FF',  // info-ish
    '#FFB81C',   // warn-ish
    '#FF5555',   // bear-ish
    'var(--text-4)',         // rest = muted
  ];

  return (
    <section style={{ marginBottom: 24 }}>
      <div
        className="flex items-baseline"
        style={{ gap: 10, marginBottom: 10 }}
      >
        <h3
          className="t-ui-subhead flex items-baseline"
          style={{ margin: 0, color: 'var(--text-1)' }}
        >
          <span
            aria-hidden="true"
            style={{
              display: 'inline-block',
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: 'var(--info)',
              boxShadow: '0 0 0 3px var(--info-soft)',
              marginRight: 7,
              marginLeft: 3,
              transform: 'translateY(-1px)',
            }}
          />
          Allocation
        </h3>
        <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>
          TOP {top.length} OF {valued.length} POSITIONS
        </span>
      </div>

      {/* Stacked bar */}
      <div
        style={{
          display: 'flex',
          height: 12,
          width: '100%',
          borderRadius: 'var(--r-chip)',
          overflow: 'hidden',
          border: '1px solid var(--edge-1)',
          background: 'var(--surface-1)',
        }}
      >
        {segments.map((s, i) => {
          const pct = (s.value / invested) * 100;
          return (
            <div
              key={s.ticker}
              title={`${s.ticker} · ${pct.toFixed(1)}%`}
              style={{
                width: `${pct}%`,
                background: palette[i] || 'var(--text-4)',
                borderRight:
                  i < segments.length - 1 ? '1px solid var(--surface-0)' : 'none',
              }}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div
        className="flex items-center flex-wrap"
        style={{ gap: 12, marginTop: 10 }}
      >
        {segments.map((s, i) => {
          const pct = (s.value / invested) * 100;
          return (
            <span
              key={s.ticker}
              className="t-ui-footnote flex items-center"
              style={{ gap: 6, color: 'var(--text-2)' }}
            >
              <span
                aria-hidden="true"
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  borderRadius: 2,
                  background: palette[i] || 'var(--text-4)',
                }}
              />
              <span style={{ color: 'var(--text-1)', fontWeight: 500 }}>
                {s.ticker}
              </span>
              <span
                className="t-num-small"
                style={{ color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}
              >
                {pct.toFixed(1)}%
              </span>
            </span>
          );
        })}
      </div>
    </section>
  );
}

function CardSkeleton() {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 16,
        height: 168,
        animation: 'pulse 1.6s ease-in-out infinite',
      }}
    />
  );
}


function HoldingsTab({ holdings, isPaper, isLoading, error }) {
  if (isLoading) {
    return <TableSkeleton rows={6} />;
  }

  if (error) {
    return (
      <EmptyCard
        variant="warn"
        icon={<AlertCircle size={16} strokeWidth={1.75} />}
        title="Couldn't load holdings"
        body={error?.message || 'Something went wrong. Try refreshing.'}
      />
    );
  }

  if (!holdings || holdings.length === 0) {
    return (
      <EmptyCard
        variant="muted"
        icon={<Inbox size={16} strokeWidth={1.75} />}
        title={isPaper ? 'No paper positions yet' : 'No holdings'}
        body={
          isPaper
            ? 'When you execute a paper trade, it will show up here.'
            : 'Your first position from Kite will appear here. Visit Signals to place a trade.'
        }
      />
    );
  }

  // Normalize Kite vs paper shapes into a single row shape.
  const rows = holdings.map((h, i) => {
    if (isPaper) {
      return {
        id: `paper-${h.ticker}-${i}`,
        ticker: h.ticker,
        qty: h.shares,
        avg: h.entry_price,
        ltp: h.current_price,
        value: h.current_value,
        pnl: h.unrealised_pnl,
        pnlPct: h.unrealised_pnl_pct,
        sector: h.sector,
        holdDays: h.hold_days,
      };
    }
    const qty = Number(h.quantity) || 0;
    const avg = Number(h.average_price) || 0;
    const ltp = Number(h.last_price) || 0;
    const value = ltp * qty;
    const pnl = (ltp - avg) * qty;
    const pnlPct = avg > 0 ? ((ltp - avg) / avg) * 100 : 0;
    return {
      id: h.tradingsymbol ?? `kite-${i}`,
      ticker: h.tradingsymbol,
      qty,
      avg,
      ltp,
      value,
      pnl,
      pnlPct,
      sector: null,
      holdDays: null,
    };
  });

  return (
    <DataTable
      columns={[
        { key: 'ticker', header: 'Ticker', sortable: true, width: '140px' },
        { key: 'qty',    header: 'Qty',    sortable: true, align: 'right', width: '80px' },
        { key: 'avg',    header: 'Avg',    sortable: true, align: 'right', render: (v) => fmtPrice(v) },
        { key: 'ltp',    header: 'LTP',    sortable: true, align: 'right', render: (v) => fmtPrice(v) },
        { key: 'value',  header: 'Value',  sortable: true, align: 'right', render: (v) => fmtINR(v) },
        {
          key: 'pnl',
          header: 'P&L',
          sortable: true,
          align: 'right',
          render: (v) => (
            <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
              {v >= 0 ? '+' : ''}{fmtINR(v)}
            </span>
          ),
        },
        {
          key: 'pnlPct',
          header: 'P&L %',
          sortable: true,
          align: 'right',
          render: (v) => (
            <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtPct(v)}</span>
          ),
        },
      ]}
      rows={rows}
      initialSort={{ key: 'value', dir: 'desc' }}
    />
  );
}

function OrdersTab({ orders, kiteConnected, isLoading }) {
  if (!kiteConnected) {
    return (
      <EmptyCard
        variant="info"
        icon={<Plug size={16} strokeWidth={1.75} />}
        title="Connect Kite to see orders"
        body="Order book is populated from your Zerodha account in real time."
      />
    );
  }
  if (isLoading) return <TableSkeleton rows={4} />;
  if (!orders || orders.length === 0) {
    return (
      <EmptyCard
        variant="muted"
        icon={<Inbox size={16} strokeWidth={1.75} />}
        title="No orders today"
        body="Orders placed through Nifty Satvik or on kite.zerodha.com will appear here."
      />
    );
  }

  return (
    <DataTable
      columns={[
        { key: 'tradingsymbol', header: 'Ticker',  sortable: true,  width: '140px' },
        {
          key: 'transaction_type',
          header: 'Side',
          width: '70px',
          render: (v) => (
            <StatusChip tone={v === 'BUY' ? 'bull' : 'bear'}>{v}</StatusChip>
          ),
        },
        { key: 'quantity',       header: 'Qty',     sortable: true, align: 'right', width: '80px' },
        { key: 'price',          header: 'Price',   sortable: true, align: 'right', render: (v) => fmtPrice(v || 0) },
        { key: 'order_type',     header: 'Type',    width: '80px' },
        { key: 'product',        header: 'Product', width: '80px' },
        {
          key: 'status',
          header: 'Status',
          render: (v) => {
            const s = String(v || '').toUpperCase();
            const tone = s === 'COMPLETE' ? 'bull'
                      : s === 'REJECTED' || s === 'CANCELLED' ? 'bear'
                      : s === 'OPEN' || s === 'TRIGGER PENDING' ? 'info'
                      : 'muted';
            return <StatusChip tone={tone}>{s}</StatusChip>;
          },
        },
      ]}
      rows={orders.map((o, i) => ({ id: o.order_id || i, ...o }))}
    />
  );
}

function TradesTab({ infiniteQuery }) {
  if (infiniteQuery.isLoading) return <TableSkeleton rows={6} />;
  if (infiniteQuery.error) {
    return (
      <EmptyCard
        variant="warn"
        icon={<AlertCircle size={16} strokeWidth={1.75} />}
        title="Couldn't load trade history"
        body={infiniteQuery.error?.message || 'Try refreshing.'}
      />
    );
  }

  const trades = flattenTrades(infiniteQuery.data);
  if (!trades.length) {
    return (
      <EmptyCard
        variant="muted"
        icon={<ReceiptText size={16} strokeWidth={1.75} />}
        title="No closed trades yet"
        body="Once a signal closes, it'll appear here as a completed trade."
      />
    );
  }

  const rows = trades.map((t, i) => ({ id: `${t.ticker}-${t.exit_date}-${i}`, ...t }));
  return (
    <>
      <DataTable
        columns={[
          { key: 'ticker',     header: 'Ticker',      sortable: true, width: '120px' },
          { key: 'entry_date', header: 'Entry',       sortable: true, width: '110px' },
          { key: 'exit_date',  header: 'Exit',        sortable: true, width: '110px' },
          { key: 'entry',      header: 'Entry ₹',     sortable: true, align: 'right', render: (v) => fmtPrice(v) },
          { key: 'exit_price', header: 'Exit ₹',      sortable: true, align: 'right', render: (v) => fmtPrice(v) },
          {
            key: 'return_pct',
            header: 'Return',
            sortable: true,
            align: 'right',
            render: (v) => (
              <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtPct(v)}</span>
            ),
          },
          { key: 'hold_days',   header: 'Days',  sortable: true, align: 'right', width: '70px' },
          { key: 'exit_reason', header: 'Reason', render: (v) => (
              <span className="t-ui-footnote" style={{ color: 'var(--text-2)' }}>{(v || '').replace(/_/g, ' ')}</span>
            ),
          },
        ]}
        rows={rows}
        initialSort={{ key: 'exit_date', dir: 'desc' }}
      />
      {infiniteQuery.hasNextPage && (
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            type="button"
            onClick={() => infiniteQuery.fetchNextPage()}
            disabled={infiniteQuery.isFetchingNextPage}
            className="t-ui-callout"
            style={{
              padding: '10px 20px',
              background: 'transparent',
              color: 'var(--text-2)',
              border: '1px solid var(--edge-2)',
              borderRadius: 'var(--r-chip)',
              cursor: infiniteQuery.isFetchingNextPage ? 'wait' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {infiniteQuery.isFetchingNextPage ? (
              <>
                <RefreshCcw size={14} strokeWidth={1.75} style={{ animation: 'spin 1s linear infinite' }} />
                Loading…
              </>
            ) : (
              <>Load more <ArrowDown size={14} strokeWidth={1.75} /></>
            )}
          </button>
        </div>
      )}
    </>
  );
}

// ══════════════════════════════════════════════════════════════
// PRIMITIVES — scoped to Portfolio, may later promote to shared
// ══════════════════════════════════════════════════════════════

function TabStrip({ tabs, active, onChange }) {
  return (
    <div
      role="tablist"
      className="flex items-center"
      style={{ borderBottom: '1px solid var(--edge-1)', marginBottom: 16, gap: 0 }}
    >
      {tabs.map((t) => {
        const isActive = t.value === active;
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
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

function MetaPair({ label, value }) {
  return (
    <span className="flex items-baseline" style={{ gap: 6 }}>
      <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>{label}</span>
      <span className="t-num-small" style={{ color: 'var(--text-1)' }}>{value}</span>
    </span>
  );
}

function TableSkeleton({ rows = 5 }) {
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
            height: 38,
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: 12,
            alignItems: 'center',
            borderBottom: i === rows - 1 ? 'none' : '1px solid var(--edge-1)',
          }}
        >
          {Array.from({ length: 6 }).map((__, j) => (
            <div key={j} style={{ height: 12, background: 'var(--surface-2)', borderRadius: 4 }} />
          ))}
        </div>
      ))}
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}

function EquityCurveSkeleton() {
  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        alignItems: 'flex-end',
        gap: 4,
        padding: '8px 0',
        animation: 'skelPulse 1.8s ease-in-out infinite',
      }}
    >
      {Array.from({ length: 32 }).map((_, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            height: `${20 + Math.sin(i * 0.7) * 15 + (i / 2)}%`,
            background: 'var(--surface-2)',
            borderRadius: 2,
          }}
        />
      ))}
    </div>
  );
}
