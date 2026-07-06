/**
 * DashboardV2 — Dashboard page.
 *
 * User intent: 60-second glance. Am I OK, what needs attention?
 *
 * Layout (per plan §7 Flagship #3):
 *
 *   TickerTape  (NIFTY, BANKNIFTY, VIX, top holdings — live via /yahoo/quote-batch)
 *   ──────────────────────────────────────────────────────
 *   RegimeHeader
 *   ──────────────────────────────────────────────────────
 *   Portfolio snapshot (7 col)  │  Market Pulse (5 col)
 *   ──────────────────────────────────────────────────────
 *   Fresh signals preview  — 3 SignalCard previews
 *   ──────────────────────────────────────────────────────
 *   Top holdings  — compact DataTable, top 5
 *   ──────────────────────────────────────────────────────
 *   Index movers  — 5-card strip with PriceArc intraday sparklines
 *
 * Exit criteria (from plan Phase 4):
 *   - ≤3 unique backend requests on mount (shared cache with Portfolio page)
 *   - Cmd-K command bar reachable
 *
 * Data requests fired on mount:
 *   1. /api/overview           (shared with Portfolio)
 *   2. /api/signals            (shared with Signals)
 *   3. /api/kite/holdings      (shared with Portfolio, gated on Kite conn)
 *   4. /api/yahoo/index-sparklines (public, cached 60s)
 *   5. /api/yahoo/quote-batch  (ticker tape, live, gated on symbols known)
 *
 * All 5 are deduped by react-query so cross-page navigation is a no-op hit.
 */
import React, { useContext, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Activity, RefreshCcw, Clock } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { TickerTape } from '@/components/shared/TickerTape';
import { RegimeHeader } from '@/components/shared/RegimeHeader';
import { KPICard } from '@/components/shared/KPICard';
import { ChartCard } from '@/components/shared/ChartCard';
import { DataTable } from '@/components/shared/DataTable';
import { EquityCurveChart } from '@/components/shared/EquityCurveChart';
import { SignalCard } from '@/components/shared/SignalCard';
import { SignalDetailDrawer } from '@/components/shared/SignalDetailDrawer';
import { OrderPad } from '@/components/shared/OrderPad';
import { CommandBar } from '@/components/shared/CommandBar';
import { PriceArc } from '@/components/shared/PriceArc';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { useSignals } from '@/hooks/queries/useSignals';
import { useOverview } from '@/hooks/queries/useOverview';
import { useKiteHoldings, useKiteMargins } from '@/hooks/queries/useKiteState';
import { useNavHistory } from '@/hooks/queries/useNavHistory';
import { useIndexSparklines } from '@/hooks/queries/useIndexSparklines';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { useOrderPlacement } from '@/hooks/useOrderPlacement';
import { KiteContext } from '@/App';
import { fmtINR, fmtPrice, fmtPct, fmtRelTime } from '@/lib/format';

// Keys must match the backend's YAHOO_INDEX_MAP exactly —
// see dashboard/backend/routers/yahoo_finance.py:466. The backend returns
// human-readable keys like "NIFTY 50" / "INDIA VIX", not the short forms.
// `shortLabel` is the compact label we render in the UI.
const MARKET_INDICES = [
  { key: 'NIFTY 50',    shortLabel: 'NIFTY' },
  { key: 'BANK NIFTY',  shortLabel: 'BANKNIFTY' },
  { key: 'SENSEX',      shortLabel: 'SENSEX' },
  { key: 'INDIA VIX',   shortLabel: 'VIX' },
  { key: 'USD/INR',     shortLabel: 'USDINR' },
];

export default function DashboardV2() {
  const kite = useContext(KiteContext);
  const navigate = useNavigate();

  const overviewQuery = useOverview();
  const signalsQuery = useSignals();
  const holdingsQuery = useKiteHoldings({ enabled: !!kite?.connected });
  const marginsQuery = useKiteMargins({ enabled: !!kite?.connected });
  const navHistoryQuery = useNavHistory();
  const indexQuery = useIndexSparklines();

  // Ticker tape pulls live prices for top holdings. We only request after
  // holdings data is available so the initial quote-batch key is stable.
  const topHoldingsSymbols = useMemo(() => {
    const list = holdingsQuery.data ?? [];
    return list
      .slice()
      .sort((a, b) => (b.last_price * b.quantity) - (a.last_price * a.quantity))
      .slice(0, 5)
      .map((h) => (h.tradingsymbol || '').toUpperCase())
      .filter(Boolean);
  }, [holdingsQuery.data]);

  // The ticker tape only needs live quotes for holdings — index prices come
  // from useIndexSparklines. So feed quote-batch only the user's top holdings.
  const quoteQuery = useQuoteBatch(topHoldingsSymbols, {
    enabled: topHoldingsSymbols.length > 0,
  });

  const { placeOrder, isPending: placingOrder } = useOrderPlacement();

  const [detailSignal, setDetailSignal] = useState(null);
  const [orderSignal, setOrderSignal] = useState(null);
  const [commandOpen, setCommandOpen] = useState(false);

  // ── Derived state ──────────────────────────────────────
  const portfolio = overviewQuery.data?.portfolio ?? {};
  const metrics = overviewQuery.data?.metrics ?? {};
  // Equity curve: prefer per-user NAV snapshots (real Kite history),
  // fall back to overview's equity_curve for users with no NAV history
  // yet. NavHistory rows are written by /api/positions/nq dashboard
  // loads — see services/nav_history.snapshot_nav.
  const equityCurve = useMemo(() => {
    const navRows = navHistoryQuery.data?.history ?? [];
    if (navRows.length > 0) return navRows;
    return overviewQuery.data?.equity_curve ?? [];
  }, [navHistoryQuery.data, overviewQuery.data]);
  // Stable refs for downstream useMemo dependencies.
  const signals = useMemo(() => signalsQuery.data?.signals ?? [], [signalsQuery.data]);
  const regime = signalsQuery.data?.regime ?? {};
  const cronHealth = signalsQuery.data?.cron_health ?? {};
  const indices = useMemo(() => indexQuery.data ?? {}, [indexQuery.data]);

  const freshSignals = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    return signals
      .filter((s) => s.signal_date === today || (s.status || '').toUpperCase() === 'FRESH')
      .slice(0, 3);
  }, [signals]);

  const tickerItems = useMemo(() => {
    const items = [];
    // Index rows come from /yahoo/index-sparklines — see backend
    // YAHOO_INDEX_MAP for the exact key shape ("NIFTY 50", "BANK NIFTY",
    // "INDIA VIX", "USD/INR"). Field names: .ltp + .change_pct + .sparkline.
    MARKET_INDICES.forEach(({ key, shortLabel }) => {
      const row = indices[key];
      if (!row) return;
      items.push({
        symbol: shortLabel || key,
        price: row.ltp,
        changePct: row.change_pct,
      });
    });
    const quotes = quoteQuery.data ?? {};
    topHoldingsSymbols.forEach((sym) => {
      const q = quotes[sym];
      if (!q) return;
      items.push({
        symbol: sym,
        price: q.last_price,
        changePct: q.change_pct,
      });
    });
    return items;
  }, [indices, quoteQuery.data, topHoldingsSymbols]);

  const holdings = useMemo(
    () => (kite?.connected ? (holdingsQuery.data ?? []) : []),
    [kite?.connected, holdingsQuery.data],
  );

  // Top 5 holdings by position value (for the compact table).
  const topHoldings = useMemo(
    () =>
      holdings
        .map((h) => ({
          ...h,
          _value: (Number(h.last_price) || 0) * (Number(h.quantity) || 0),
          _pnl: ((Number(h.last_price) || 0) - (Number(h.average_price) || 0)) * (Number(h.quantity) || 0),
          _pnlPct: Number(h.average_price) > 0
            ? ((Number(h.last_price) - Number(h.average_price)) / Number(h.average_price)) * 100
            : 0,
        }))
        .sort((a, b) => b._value - a._value)
        .slice(0, 5),
    [holdings],
  );

  // Today's P&L. Kite's `day_change` field is per-share gain vs yesterday's
  // close — returns 0 for T+1 / freshly-bought holdings since they have no
  // previous-close reference. Fall back to total unrealised P&L when the
  // day-change sum is 0 so a fresh-buy day shows the actual gain instead of
  // "+₹0" (matches Kite Web's behaviour in that case).
  const todayPnL = useMemo(() => {
    const dayChangeSum = holdings.reduce(
      (sum, h) => sum + (Number(h.day_change) || 0) * (Number(h.quantity) || 0),
      0,
    );
    if (dayChangeSum !== 0) return dayChangeSum;
    return holdings.reduce(
      (sum, h) => sum + ((Number(h.last_price) || 0) - (Number(h.average_price) || 0)) * (Number(h.quantity) || 0),
      0,
    );
  }, [holdings]);

  // Holdings market value — needed by `totalCapital` below so we don't miss
  // the value of held positions (Kite's /user/margins endpoint only returns
  // cash + blocked, not holdings).
  const investedValue = useMemo(
    () => holdings.reduce(
      (sum, h) => sum + (Number(h.last_price) || 0) * (Number(h.quantity) || 0),
      0,
    ),
    [holdings],
  );

  // Total capital = cash + blocked + market value of holdings. Earlier this
  // was just margins.total which excluded holdings entirely, causing the KPI
  // to render the user's cash leftover (~₹143) as their full net worth (~₹515).
  const totalCapital = kite?.connected
    ? ((marginsQuery.data?.total ?? 0) + investedValue)
    : (portfolio?.total_value ?? 0);
  const todayPnLPct = totalCapital > 0 ? (todayPnL / totalCapital) * 100 : 0;

  // Featured signal for the brand-gradient hero — prefer top FRESH, fall back to top active.
  const topFreshSignal = useMemo(() => {
    const fresh = signals.find((s) => (s.tier || s.status) === 'FRESH' || s.is_fresh);
    return fresh || signals[0] || null;
  }, [signals]);

  // Holdings KPI summary for the right rail of the hero.
  const winningHoldingsCount = useMemo(
    () => holdings.filter((h) => ((Number(h.last_price) || 0) - (Number(h.average_price) || 0)) * (Number(h.quantity) || 0) > 0).length,
    [holdings],
  );
  const drawdownHoldingsCount = holdings.length - winningHoldingsCount;
  const bestHolding = useMemo(() => {
    if (holdings.length === 0) return null;
    return holdings
      .map((h) => {
        const avg = Number(h.average_price) || 0;
        const ltp = Number(h.last_price) || 0;
        const pct = avg > 0 ? ((ltp - avg) / avg) * 100 : 0;
        return { symbol: (h.tradingsymbol || '').toUpperCase(), pct };
      })
      .sort((a, b) => b.pct - a.pct)[0];
  }, [holdings]);

  // ── Handlers ──────────────────────────────────────────
  const handleOpenOrderPad = (sig) => {
    if (!kite?.connected) return;
    setOrderSignal(sig);
  };
  const handlePlaceOrder = async (payload) => {
    // Don't swallow — OrderPad's confirm dialog needs the rejection to display
    // the inline error and stay open. Error toasts still fire from the hook's
    // onError. Drawer close on success is handled by OrderPad via onOpenChange.
    await placeOrder({ payload, signal: orderSignal, variety: 'regular' });
  };

  return (
    <PageShell title="Dashboard">
      {/* TICKER TAPE — edge-to-edge inside the page shell */}
      {tickerItems.length > 0 && (
        <div style={{ margin: '0 -4px 8px' }}>
          <TickerTape items={tickerItems} />
        </div>
      )}

      {/* FEATURE HERO — brand-gradient focused symbol + capital/positions micros.
          Matches the design system kit (2026-05-21). Featured signal = top
          fresh signal; falls back to top active signal. */}
      <FeatureHero
        signal={topFreshSignal}
        totalCapital={totalCapital}
        todayPnL={todayPnL}
        todayPnLPct={todayPnLPct}
        openPositions={holdings.length}
        bestHolding={bestHolding}
        winningCount={winningHoldingsCount}
        drawdownCount={drawdownHoldingsCount}
        onClick={(s) => navigate(`/stock/${s.symbol}`)}
      />

      {/* REGIME HEADER */}
      <RegimeHeader
        regime={regime.status ? titleCase(regime.status) : 'Loading'}
        tone={regimeTone(regime.status)}
        strength={typeof regime.strength === 'number' ? Math.round(regime.strength) : undefined}
        vix={typeof regime.vix === 'number' ? regime.vix : undefined}
        breadth={typeof regime.breadth === 'number' ? regime.breadth : undefined}
        scanTime={signalsQuery.dataUpdatedAt ? fmtRelTime(new Date(signalsQuery.dataUpdatedAt)) : undefined}
      />

      {/* Cron warning — sticky until recovers */}
      {cronHealth?.status && cronHealth.status !== 'OK' && (
        <Banner tone="warn" icon={<Clock size={16} strokeWidth={1.75} />}>
          <strong style={{ color: 'var(--text-1)' }}>Signal scan stale.</strong>{' '}
          Last successful scan status: {cronHealth.status}.
        </Banner>
      )}

      {/* HERO ROW — portfolio snapshot + market pulse.
          Mobile stacks the snapshot above the market-pulse card.
          Section dot prefix marks this as the brand-primary region. */}
      <SectionLabel
        tone="brand"
        title="Portfolio & pulse"
        subtitle="Today's position value, regime context."
      />
      <section
        className="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]"
        style={{
          gap: 16,
          marginTop: 12,
          marginBottom: 28,
        }}
      >
        {/* Portfolio snapshot (wider) — hero card gets larger padding. */}
        <ChartCard
          title="Portfolio"
          badge={kite?.connected ? <StatusChip tone="bull">KITE</StatusChip> : <StatusChip tone="muted">PAPER</StatusChip>}
          height={300}
          footer={
            overviewQuery.data && (
              <>
                <MetaPair label="Total" value={fmtINR(totalCapital)} />
                <MetaPair
                  label="Today"
                  value={`${todayPnL >= 0 ? '+' : ''}${fmtINR(todayPnL)}  ${fmtPct(todayPnLPct)}`}
                  tone={todayPnL >= 0 ? 'bull' : 'bear'}
                />
                <MetaPair
                  label="Return"
                  value={fmtPct(portfolio?.total_return_pct ?? 0)}
                  tone={(portfolio?.total_return_pct ?? 0) >= 0 ? 'bull' : 'bear'}
                />
                <button
                  type="button"
                  onClick={() => navigate('/portfolio')}
                  className="t-ui-callout"
                  style={{
                    marginLeft: 'auto',
                    padding: '4px 10px',
                    background: 'transparent',
                    color: 'var(--brand-hi)',
                    border: '1px solid var(--brand-edge)',
                    borderRadius: 'var(--r-chip)',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  Open portfolio <ArrowRight size={12} strokeWidth={1.75} />
                </button>
              </>
            )
          }
        >
          {overviewQuery.isLoading || equityCurve.length === 0 ? (
            <ChartSkeleton />
          ) : (
            <EquityCurveChart data={equityCurve.slice(-120)} height={300} tone="auto" />
          )}
        </ChartCard>

        {/* Market pulse (narrower) — uses the page's brand-soft halo wash via
            a thin top border + warm card background to read as the section's
            "first child" without violating the no-side-stripe ban. */}
        <div
          className="flex flex-col"
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            padding: 'var(--pad-card-lg)',
            boxShadow: 'var(--shadow-sm)',
            gap: 14,
            minHeight: 300,
          }}
        >
          <div className="flex items-center justify-between">
            <h3 className="t-title-2" style={{ color: 'var(--text-1)', margin: 0 }}>
              Market pulse
            </h3>
            {cronHealth?.status === 'OK' && <StatusChip tone="bull">LIVE</StatusChip>}
          </div>

          <StatBar
            label="Regime"
            value={titleCase(regime.status) || '—'}
            tone={regimeTone(regime.status)}
          />
          <StatBar
            label="Strength"
            value={typeof regime.strength === 'number' ? `${Math.round(regime.strength)}/100` : '—'}
            barPct={typeof regime.strength === 'number' ? regime.strength : 0}
            tone={regimeTone(regime.status)}
          />
          <StatBar
            label="VIX"
            value={typeof regime.vix === 'number' ? regime.vix.toFixed(1) : '—'}
            tone={typeof regime.vix === 'number' && regime.vix > 20 ? 'warn' : 'neutral'}
          />
          {typeof regime.breadth === 'number' && (
            <StatBar
              label="Breadth"
              value={`${Math.round(regime.breadth)}%`}
              barPct={regime.breadth}
              tone="neutral"
            />
          )}

          <div
            className="t-ui-footnote"
            style={{
              marginTop: 'auto',
              color: 'var(--text-3)',
              paddingTop: 10,
              borderTop: '1px solid var(--edge-1)',
            }}
          >
            {signals.length} signals scanned · {freshSignals.length} fresh today
          </div>
        </div>
      </section>

      {/* FRESH SIGNALS PREVIEW */}
      <section style={{ marginBottom: 28 }}>
        <SectionHeader
          tone="bull"
          title="Fresh signals today"
          subtitle={
            freshSignals.length > 0
              ? `${freshSignals.length} cleared the entry gate, of ${signals.length} scanned.`
              : `0 cleared the gate today, of ${signals.length} scanned.`
          }
          action={
            <button
              type="button"
              onClick={() => navigate('/premove')}
              className="t-ui-callout"
              style={{
                background: 'transparent',
                color: 'var(--brand-hi)',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              View all signals <ArrowRight size={14} strokeWidth={1.75} />
            </button>
          }
        />
        {signalsQuery.isLoading ? (
          <SignalsSkeleton count={3} />
        ) : freshSignals.length === 0 ? (
          <EmptyCard
            variant="info"
            icon={<Activity size={16} strokeWidth={1.75} />}
            title="No fresh signals today"
            body="The scanner runs at 4:15 PM IST after market close. Brewing candidates land on the Signals page."
            height={180}
          />
        ) : (
          <div
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))',
              gap: 16,
            }}
          >
            {freshSignals.map((sig) => (
              <SignalCard
                key={`${sig.ticker}-${sig.signal_date}`}
                signal={sig}
                priceSeries={null}
                onOpenDetail={setDetailSignal}
                onOpenOrderPad={kite?.connected ? handleOpenOrderPad : undefined}
              />
            ))}
          </div>
        )}
      </section>

      {/* TOP HOLDINGS */}
      {kite?.connected && (
        <section style={{ marginBottom: 28 }}>
          <SectionHeader
            tone="info"
            title="Top holdings"
            subtitle={
              holdings.length > 0
                ? `Your ${Math.min(5, holdings.length)} largest positions by value, of ${holdings.length} held.`
                : 'No NQ positions yet.'
            }
            action={
              <button
                type="button"
                onClick={() => navigate('/portfolio')}
                className="t-ui-callout"
                style={{
                  background: 'transparent',
                  color: 'var(--brand-hi)',
                  border: 'none',
                  padding: 0,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                Open portfolio <ArrowRight size={14} strokeWidth={1.75} />
              </button>
            }
          />
          {topHoldings.length === 0 ? (
            <EmptyCard
              variant="muted"
              title="No holdings yet"
              body="Once you place an order through Nifty Satvik, your positions will appear here."
              height={160}
            />
          ) : (
            <DataTable
              rows={topHoldings.map((h) => ({ id: h.tradingsymbol, ...h }))}
              onRowClick={(h) => navigate(`/stock/${h.tradingsymbol}`)}
              initialSort={{ key: '_value', dir: 'desc' }}
              dense
              columns={[
                { key: 'tradingsymbol', header: 'Ticker', width: '140px' },
                { key: 'quantity', header: 'Qty', align: 'right', width: '80px' },
                { key: 'average_price', header: 'Avg', align: 'right', render: (v) => fmtPrice(v) },
                { key: 'last_price', header: 'LTP', align: 'right', render: (v) => fmtPrice(v) },
                { key: '_value', header: 'Value', align: 'right', render: (v) => fmtINR(v) },
                {
                  key: '_pnl',
                  header: 'P&L',
                  align: 'right',
                  render: (v) => (
                    <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
                      {v >= 0 ? '+' : ''}{fmtINR(v)}
                    </span>
                  ),
                },
                {
                  key: '_pnlPct',
                  header: '%',
                  align: 'right',
                  width: '80px',
                  render: (v) => (
                    <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtPct(v)}</span>
                  ),
                },
              ]}
            />
          )}
        </section>
      )}

      {/* INDEX MOVERS — tiny intraday sparkline strip */}
      <section>
        <SectionHeader
          tone="muted"
          title="Market indices"
          subtitle="Intraday move on the five anchors we track."
        />
        <div
          className="grid"
          style={{
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 12,
          }}
        >
          {MARKET_INDICES.map(({ key, shortLabel }) => {
            const row = indices[key];
            if (!row) return <IndexCardSkeleton key={key} />;
            return (
              <IndexCard
                key={key}
                label={shortLabel}
                last={row.ltp}
                changePct={row.change_pct}
                series={row.sparkline ?? []}
              />
            );
          })}
        </div>
      </section>

      {/* DRAWERS / OVERLAYS */}
      <SignalDetailDrawer
        signal={detailSignal}
        open={!!detailSignal}
        onOpenChange={(open) => !open && setDetailSignal(null)}
        onOpenOrderPad={
          kite?.connected
            ? (s) => { setDetailSignal(null); setTimeout(() => setOrderSignal(s), 220); }
            : undefined
        }
      />
      <OrderPad
        open={!!orderSignal}
        onOpenChange={(open) => !open && setOrderSignal(null)}
        signal={orderSignal}
        capital={signalsQuery.data?.sizing_capital ?? totalCapital ?? 1000000}
        marginAvailable={marginsQuery.data?.available}
        submitting={placingOrder}
        onPlace={handlePlaceOrder}
      />
      <CommandBar
        open={commandOpen}
        onOpenChange={setCommandOpen}
        tickers={signals.map((s) => ({ symbol: s.ticker }))}
        actions={[
          {
            id: 'refresh-dashboard',
            title: 'Refresh all data',
            icon: <RefreshCcw />,
            run: () => {
              overviewQuery.refetch();
              signalsQuery.refetch();
              if (kite?.connected) holdingsQuery.refetch();
            },
          },
        ]}
      />
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// SUB-COMPONENTS
// ══════════════════════════════════════════════════════════════

// Tone palette shared by SectionHeader + SectionLabel. Same shape as the
// SignalsV2 TONE_COLORS map so the two pages read consistently.
const SECTION_TONES = {
  brand: { dot: 'var(--brand)', halo: 'var(--brand-soft)' },
  bull:  { dot: 'var(--bull)',  halo: 'var(--bull-soft)'  },
  info:  { dot: 'var(--info)',  halo: 'var(--info-soft)'  },
  warn:  { dot: 'var(--warn)',  halo: 'var(--warn-soft)'  },
  bear:  { dot: 'var(--bear)',  halo: 'var(--bear-soft)'  },
  muted: { dot: 'var(--text-4)', halo: 'var(--edge-2)'    },
};

function SectionDot({ tone = 'muted' }) {
  const t = SECTION_TONES[tone] || SECTION_TONES.muted;
  return (
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
        marginRight: 8,
        transform: 'translateY(-2px)',
      }}
    />
  );
}

function SectionLabel({ tone = 'muted', title, subtitle }) {
  return (
    <div style={{ marginTop: 8 }}>
      <div className="flex items-baseline">
        <SectionDot tone={tone} />
        <span
          className="t-ui-micro"
          style={{ color: 'var(--text-2)', letterSpacing: '0.10em' }}
        >
          {title}
        </span>
      </div>
      {subtitle && (
        <p
          className="t-ui-footnote"
          style={{ color: 'var(--text-3)', margin: '4px 0 0 15px', maxWidth: '76ch' }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

function SectionHeader({ title, subtitle, action, tone = 'muted' }) {
  return (
    <div
      className="flex items-end justify-between flex-wrap"
      style={{ marginBottom: 12, gap: 12 }}
    >
      <div>
        <h2 className="t-title-2 flex items-baseline" style={{ margin: 0, color: 'var(--text-1)' }}>
          <SectionDot tone={tone} />
          {title}
        </h2>
        {subtitle && (
          <div
            className="t-ui-footnote"
            style={{ color: 'var(--text-3)', marginTop: 4, marginLeft: 15, maxWidth: '76ch' }}
          >
            {subtitle}
          </div>
        )}
      </div>
      {action}
    </div>
  );
}

function StatBar({ label, value, barPct, tone = 'neutral' }) {
  const color =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    tone === 'brand' ? 'var(--brand)' :
    tone === 'warn' ? 'var(--warn)' :
    'var(--text-1)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div className="flex items-baseline justify-between">
        <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>{label}</span>
        <span className="t-num-body" style={{ color }}>{value}</span>
      </div>
      {typeof barPct === 'number' && (
        <div
          style={{
            height: 4,
            background: 'var(--surface-2)',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${Math.max(0, Math.min(100, barPct))}%`,
              height: '100%',
              background: color,
              transition: 'width var(--dur-enter) var(--ease-out-quart)',
            }}
          />
        </div>
      )}
    </div>
  );
}

function MetaPair({ label, value, tone = 'neutral' }) {
  const color =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    'var(--text-1)';
  return (
    <span className="flex items-baseline" style={{ gap: 6 }}>
      <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>{label}</span>
      <span className="t-num-body" style={{ color }}>{value}</span>
    </span>
  );
}

function IndexCard({ label, last, changePct, series }) {
  const tone = changePct > 0 ? 'bull' : changePct < 0 ? 'bear' : 'muted';
  const color =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    'var(--text-3)';
  const chipBg =
    tone === 'bull' ? 'var(--bull-soft)' :
    tone === 'bear' ? 'var(--bear-soft)' :
    'var(--surface-2)';
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 14,
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div className="flex items-center justify-between" style={{ marginBottom: 10 }}>
        <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>{label}</span>
        <span
          className="t-num-small"
          style={{
            color,
            background: chipBg,
            padding: '2px 8px',
            borderRadius: 'var(--r-chip)',
            fontWeight: 600,
          }}
        >
          {(changePct ?? 0) > 0 ? '+' : ''}{fmtPct(changePct ?? 0)}
        </span>
      </div>
      <div className="t-num-large" style={{ color: 'var(--text-1)' }}>
        {typeof last === 'number' ? last.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—'}
      </div>
      <div style={{ marginTop: 10 }}>
        <PriceArc series={series} size="wide" showDot={false} />
      </div>
    </div>
  );
}

function IndexCardSkeleton() {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 14,
        minHeight: 108,
        animation: 'skelPulse 1.8s ease-in-out infinite',
      }}
    >
      <div style={{ height: 10, width: 60, background: 'var(--surface-2)', borderRadius: 3 }} />
      <div style={{ height: 20, width: 90, background: 'var(--surface-2)', borderRadius: 3, marginTop: 10 }} />
      <div style={{ height: 22, width: '100%', background: 'var(--surface-2)', borderRadius: 3, marginTop: 14 }} />
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}

function Banner({ tone = 'warn', icon, children }) {
  const colors = {
    warn: { bg: 'var(--warn-soft)', edge: 'oklch(68% 0.18 40 / 0.32)', fg: 'var(--warn)' },
  }[tone];
  return (
    <div
      className="flex items-center"
      style={{
        marginTop: 16,
        padding: '10px 14px',
        background: colors.bg,
        border: `1px solid ${colors.edge}`,
        borderRadius: 'var(--r-chip)',
        gap: 10,
      }}
    >
      <span style={{ color: colors.fg }}>{icon}</span>
      <p className="t-ui-body" style={{ color: 'var(--text-2)', margin: 0 }}>{children}</p>
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        alignItems: 'flex-end',
        gap: 4,
        padding: '12px 0',
        animation: 'skelPulse 1.8s ease-in-out infinite',
      }}
    >
      {Array.from({ length: 40 }).map((_, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            height: `${15 + ((Math.sin(i * 0.5) + 1) * 30) + (i / 3)}%`,
            background: 'var(--surface-2)',
            borderRadius: 2,
          }}
        />
      ))}
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}

function SignalsSkeleton({ count }) {
  return (
    <div
      className="grid"
      style={{
        gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))',
        gap: 16,
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            minHeight: 280,
            animation: 'skelPulse 1.8s ease-in-out infinite',
          }}
        />
      ))}
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}

function titleCase(s) {
  if (!s) return s;
  return String(s).toLowerCase().replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

function regimeTone(status) {
  if (!status) return 'muted';
  const s = String(status).toUpperCase();
  if (s.includes('BULL') || s === 'TRENDING') return 'bull';
  if (s.includes('BEAR')) return 'bear';
  if (s.includes('CHOP') || s.includes('RANG')) return 'brand';
  return 'muted';
}

/**
 * FeatureHero — brand-gradient focused-symbol hero card + stacked KPI micros
 * on the right. Matches the design system kit (2026-05-21). The card renders
 * the top fresh signal with entry/stop/target levels; the right column shows
 * total capital and open positions.
 */
function FeatureHero({
  signal,
  totalCapital,
  todayPnL,
  todayPnLPct,
  openPositions,
  bestHolding,
  winningCount,
  drawdownCount,
  onClick,
}) {
  const hasSignal = !!signal;
  const dayChange = Number(signal?.day_change_pct ?? signal?.daily_change_pct ?? 0);
  const dayChangeTone = dayChange >= 0 ? 'bull' : 'bear';
  const lastPrice = Number(signal?.last_price ?? signal?.current_price ?? signal?.entry ?? 0);
  const entry = Number(signal?.entry ?? lastPrice);
  const stop = Number(signal?.stop_loss ?? signal?.stop ?? 0);
  const target = Number(signal?.target ?? signal?.target_price ?? 0);
  const stopPct = entry > 0 && stop > 0 ? ((stop - entry) / entry) * 100 : 0;
  const targetPct = entry > 0 && target > 0 ? ((target - entry) / entry) * 100 : 0;
  const rr = stopPct !== 0 ? Math.abs(targetPct / stopPct) : 0;

  return (
    <section
      className="grid"
      style={{
        gridTemplateColumns: 'minmax(0, 1.6fr) minmax(0, 1fr)',
        gap: 16,
        marginBottom: 16,
      }}
    >
      {/* Brand-gradient feature card */}
      <article
        onClick={() => hasSignal && onClick?.(signal)}
        style={{
          background: 'var(--brand-grad)',
          border: '1px solid rgba(255,255,255,0.18)',
          borderRadius: 22,
          padding: 24,
          color: 'white',
          position: 'relative',
          overflow: 'hidden',
          boxShadow: '0 20px 50px rgba(44,91,255,0.32), inset 0 1px 0 rgba(255,255,255,0.12)',
          cursor: hasSignal ? 'pointer' : 'default',
          minHeight: 220,
        }}
      >
        <div
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(circle at 90% 10%, rgba(255,255,255,0.10), transparent 40%)',
            pointerEvents: 'none',
          }}
        />
        <div style={{ position: 'relative', zIndex: 1 }}>
          {/* Head row: ticker + chip */}
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 600, letterSpacing: '-0.012em', color: '#fff' }}>
                {signal?.symbol || 'Awaiting fresh signal'}
              </span>
              {signal?.sector && (
                <span style={{ fontSize: 11, letterSpacing: '0.04em', color: 'rgba(255,255,255,0.7)' }}>
                  NSE · {signal.sector}
                </span>
              )}
            </div>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 10.5,
                padding: '4px 10px',
                background: 'rgba(0,0,0,0.25)',
                border: '1px solid rgba(255,255,255,0.20)',
                borderRadius: 999,
                letterSpacing: '0.06em',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                color: '#fff',
                whiteSpace: 'nowrap',
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: 'var(--bull)',
                  animation: 'fhPulse 2.2s infinite ease-in-out',
                }}
              />
              {hasSignal ? 'Live · FRESH signal' : 'Live · Awaiting scan'}
            </span>
          </div>

          {/* Price hero */}
          <div style={{ marginTop: 18, display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
                fontSize: 44,
                fontWeight: 600,
                lineHeight: 1,
                letterSpacing: '-0.022em',
                color: '#fff',
              }}
            >
              {hasSignal ? `₹${fmtPrice(lastPrice)}` : '—'}
            </span>
            {hasSignal && (
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: 13,
                  padding: '4px 10px',
                  background: dayChangeTone === 'bull' ? 'rgba(63,221,138,0.22)' : 'rgba(255,92,122,0.22)',
                  color: dayChangeTone === 'bull' ? 'var(--bull)' : 'var(--bear)',
                  borderRadius: 999,
                  fontWeight: 500,
                }}
              >
                {dayChange >= 0 ? '▲' : '▼'} {dayChange >= 0 ? '+' : ''}{dayChange.toFixed(2)}%
              </span>
            )}
          </div>

          {/* Levels grid */}
          {hasSignal && entry > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 18 }}>
              <Level label="Entry" value={fmtPrice(entry)} sub={rr > 0 ? `R:R ${rr.toFixed(2)}` : null} subOpacity={0.7} />
              <Level label="Stop" value={stop > 0 ? fmtPrice(stop) : '—'} sub={stop > 0 ? `${stopPct.toFixed(1)}%` : null} subColor="rgba(255,182,196,0.95)" />
              <Level label="Target" value={target > 0 ? fmtPrice(target) : '—'} sub={target > 0 ? `+${targetPct.toFixed(1)}%` : null} subColor="rgba(170,255,210,0.95)" />
            </div>
          )}
        </div>
        <style>{`
          @keyframes fhPulse { 0%, 100% { opacity: 0.5 } 50% { opacity: 1 } }
        `}</style>
      </article>

      {/* Right column — Total Capital + Open positions */}
      <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr', gap: 16 }}>
        <div
          className="glass-card"
          style={{
            padding: 18,
            borderRadius: 18,
          }}
        >
          <div className="t-ui-micro" style={{ color: 'var(--text-3)' }}>Total Capital</div>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontVariantNumeric: 'tabular-nums',
              fontSize: 30,
              color: 'var(--text-1)',
              marginTop: 8,
              lineHeight: 1,
            }}
          >
            {fmtINR(totalCapital)}
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 10 }}>
            <span
              style={{
                padding: '2px 8px',
                background: todayPnL >= 0 ? 'var(--bull-soft)' : 'var(--bear-soft)',
                color: todayPnL >= 0 ? 'var(--bull)' : 'var(--bear)',
                borderRadius: 999,
                fontFamily: 'var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
                fontSize: 11,
                fontWeight: 600,
              }}
            >
              {todayPnL >= 0 ? '+' : ''}{fmtINR(todayPnL)} · {todayPnLPct >= 0 ? '+' : ''}{todayPnLPct.toFixed(2)}%
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-3)' }}>today</span>
          </div>
        </div>

        <div
          className="glass-card"
          style={{
            padding: 18,
            borderRadius: 18,
          }}
        >
          <div className="t-ui-micro" style={{ color: 'var(--text-3)' }}>
            Open positions · today P&amp;L
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginTop: 8 }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
                fontSize: 26,
                color: 'var(--text-1)',
                lineHeight: 1,
              }}
            >
              {openPositions}
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
                fontSize: 22,
                color: todayPnL >= 0 ? 'var(--bull)' : 'var(--bear)',
                lineHeight: 1,
              }}
            >
              {todayPnL >= 0 ? '+' : ''}{fmtINR(todayPnL)}
            </span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 10 }}>
            {openPositions > 0 ? (
              <>
                {winningCount} winning · {drawdownCount} in drawdown
                {bestHolding && (
                  <>
                    {' · '}best{' '}
                    <strong style={{ color: 'var(--text-1)' }}>
                      {bestHolding.symbol} {bestHolding.pct >= 0 ? '+' : ''}{bestHolding.pct.toFixed(1)}%
                    </strong>
                  </>
                )}
              </>
            ) : (
              'No open positions'
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function Level({ label, value, sub, subOpacity, subColor }) {
  return (
    <div
      style={{
        padding: '12px 14px',
        background: 'rgba(0,0,0,0.22)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 12,
      }}
    >
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9.5,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'rgba(255,255,255,0.65)',
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontVariantNumeric: 'tabular-nums',
          fontSize: 18,
          marginTop: 5,
          color: '#fff',
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 10.5,
            marginTop: 2,
            opacity: subOpacity ?? 1,
            color: subColor ?? 'rgba(255,255,255,0.85)',
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}
