/**
 * StockDetailV2 — per-stock drill-in optimized for "should I trade this right now".
 *
 * Layout:
 *   Ticker hero  — symbol + LTP + delta + Buy/Sell CTAs
 *   Active signal strip  (if NQ has a signal for this ticker)
 *   Position strip  (if user holds it)
 *   ────────────────────────────────────────────────────────────────────
 *   Price chart  — full width, period switcher, reference lines for active signal
 *   ────────────────────────────────────────────────────────────────────
 *   Decision row  (3 cols)
 *     │ Order Book L2 │ Volume Profile │ Your history on this ticker │
 *   ────────────────────────────────────────────────────────────────────
 *   Tabs: Overview · Fundamentals · News · Peers
 *
 * Data sources:
 *   - useStockData (existing) — price ticks, candles, holdings, indicators.
 *     Candles come back as arrays: [timestamp, open, high, low, close, volume].
 *   - useKiteQuote — top-5 depth + volume for OrderBookL2.
 *   - useSignalHistory — find an active NQ signal for this ticker.
 *   - yahooFundamentals/News/Peers — tab content.
 */
import React, { useContext, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, AlertCircle, ExternalLink } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { ChartCard } from '@/components/shared/ChartCard';
import { PriceChart } from '@/components/shared/PriceChart';
import { DecisionBand } from '@/components/shared/DecisionBand';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { OrderPad } from '@/components/shared/OrderPad';
import { OrderBookL2 } from '@/components/shared/OrderBookL2';
import { VolumeProfile } from '@/components/shared/VolumeProfile';
import { TickerOrderHistory } from '@/components/shared/TickerOrderHistory';
import { ActiveSignalStrip } from '@/components/shared/ActiveSignalStrip';
import { SignalDetailDrawer } from '@/components/shared/SignalDetailDrawer';
import { useStockData } from '@/hooks/useStockData';
import { useOrderPlacement } from '@/hooks/useOrderPlacement';
import { useSignalHistory } from '@/hooks/queries/useSignalHistory';
import {
  yahooFundamentals, yahooNews, yahooPeers,
} from '@/services/api';
import { KiteContext } from '@/App';
import { fmtINR, fmtPrice, fmtVolume } from '@/lib/format';
import { normCandle } from '@/lib/candles';

const PERIODS = ['1D', '1W', '1M', '3M', '6M', '1Y', '5Y', 'ALL'];

// ── Small queries for fundamentals / news / peers ──
//
// These wrap yfinance on the backend and are slow (news up to 50s,
// fundamentals can hang past 60s on cold yfinance). Firing all three on
// page mount made the page feel frozen even when the chart loaded fast.
//
// Strategy: only fundamentals runs eagerly because the default Overview
// tab consumes its data. News and Peers stay disabled until the user
// actually clicks those tabs. Saves two slow concurrent requests on
// every initial page view.
//
// `_timed` wraps the queryFn with performance marks so the console shows
// the actual wall time per endpoint — useful for spotting which yfinance
// call is the current bottleneck without DevTools Network gymnastics.
function _timed(label, fn) {
  return async (...args) => {
    const start = performance.now();
    try {
      const result = await fn(...args);
      const ms = Math.round(performance.now() - start);

      console.info(`[stock] ${label} ✓ ${ms}ms`);
      return result;
    } catch (err) {
      const ms = Math.round(performance.now() - start);

      console.warn(`[stock] ${label} ✗ ${ms}ms`, err?.message || err);
      throw err;
    }
  };
}
function useFundamentals(symbol, active) {
  return useQuery({
    queryKey: ['yahoo', 'fundamentals', symbol],
    queryFn: _timed('fundamentals', () => yahooFundamentals(symbol)),
    staleTime: 60 * 60 * 1000,
    enabled: !!symbol && !!active,
  });
}
function useNews(symbol, active) {
  return useQuery({
    queryKey: ['yahoo', 'news', symbol],
    queryFn: _timed('news', () => yahooNews(symbol)),
    staleTime: 30 * 60 * 1000,
    enabled: !!symbol && !!active,
  });
}
function usePeers(symbol, active) {
  return useQuery({
    queryKey: ['yahoo', 'peers', symbol],
    queryFn: _timed('peers', () => yahooPeers(symbol)),
    staleTime: 60 * 60 * 1000,
    enabled: !!symbol && !!active,
  });
}

export default function StockDetailV2() {
  const { symbol: rawSymbol } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const symbol = (rawSymbol || '').toUpperCase();
  const kite = useContext(KiteContext);

  const [orderSide, setOrderSide] = useState(null);
  const [signalDetailOpen, setSignalDetailOpen] = useState(false);
  const [chartType, setChartType] = useState('candle');
  // Panels stack vertically (no tabs) so all four sections render at once.
  // Fundamentals / News / Peers wrap slow yfinance calls — gate their
  // queries behind a deferred flag that flips ~1s after mount so the
  // chart paints first and the slow sections backfill in the background.
  const [panelsDeferred, setPanelsDeferred] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setPanelsDeferred(true), 800);
    return () => clearTimeout(t);
  }, []);

  const data = useStockData(symbol);
  // All three context-tab queries are strictly tab-gated. Even though the
  // Overview panel reads P/E / Market Cap / Dividend Yield / EPS from
  // fundamentals, we defer fundamentals to its own tab to keep page mount
  // light. Overview still shows Sector / Industry (from useStockData.info)
  // and 52W high/low (from data.price) — so it's not gutted, just less
  // dense until the user clicks Fundamentals. Once fetched, the data is
  // session-cached for an hour, so subsequent tab clicks are instant.
  const fundamentalsQuery = useFundamentals(symbol, panelsDeferred);
  const newsQuery = useNews(symbol, panelsDeferred);
  const peersQuery = usePeers(symbol, panelsDeferred);
  const historyQuery = useSignalHistory();
  const { placeOrder, isPending: placingOrder } = useOrderPlacement();

  // Pre-fill state for SELL flows initiated from the Portfolio page.
  // PortfolioV2 navigates here with `?action=sell&qty=N&signal_id=...`
  // when the user clicks SELL on a NQ position card.
  const presetAction = (searchParams.get('action') || '').toUpperCase();
  const presetQty = Number(searchParams.get('qty')) || null;
  const presetSignalId = searchParams.get('signal_id') || null;

  // Auto-open the OrderPad if we arrived via a sell intent. Use a one-shot
  // effect so back-navigation that strips the params doesn't re-open it.
  const [autoOpenedOnce, setAutoOpenedOnce] = useState(false);
  useEffect(() => {
    if (autoOpenedOnce) return;
    if (!kite?.connected) return;
    if (presetAction === 'SELL' || presetAction === 'BUY') {
      setOrderSide(presetAction);
      setAutoOpenedOnce(true);
    }
  }, [presetAction, kite?.connected, autoOpenedOnce]);

  const ltp = data.tick?.last_price ?? data.price?.last_price ?? null;
  const change = data.tick?.change ?? data.price?.change ?? 0;
  const changePct = data.tick?.change_pct ?? data.price?.change_pct ?? 0;
  const tone = change > 0 ? 'bull' : change < 0 ? 'bear' : 'muted';

  const userPosition = useMemo(() => {
    const list = data.holdings ?? [];
    return list.find((h) => (h.tradingsymbol || h.symbol || '').toUpperCase() === symbol);
  }, [data.holdings, symbol]);

  // Find the most recent NQ signal for THIS ticker that's still in play.
  //
  // The Vercel history endpoint returns:
  //   { today, history, analytics, source }
  //
  // `today` is the RAW signals_today.json envelope `{generated_at, signals: [...]}`
  // — an OBJECT, not an array. Spreading it with `[...]` throws
  // "is not iterable" (the bug the user just reported). `history` is
  // always an array AND already covers today's signals (the function
  // enriches every tracked signal into the same list), so we use it
  // exclusively here. Defensive Array.isArray guard for any future shape
  // drift / fallback responses.
  const activeSignal = useMemo(() => {
    const raw = historyQuery.data?.history;
    const histRows = Array.isArray(raw) ? raw : [];
    const upper = symbol;
    const matches = histRows.filter(
      (s) => s && (s.ticker || '').toUpperCase() === upper && s.entry > 0 && s.grade !== 'REJECT',
    );
    if (matches.length === 0) return null;
    // Sort newest first by signal_date string (YYYY-MM-DD sorts lexicographically)
    matches.sort((a, b) => String(b.signal_date || '').localeCompare(String(a.signal_date || '')));
    return matches[0];
  }, [historyQuery.data, symbol]);

  // Normalize candles once (Kite returns arrays, Yahoo returns objects).
  // Array.isArray guard catches the same iterable-on-non-array failure mode
  // we hit earlier with `historyQuery.data.today`. useStockData defaults to
  // [] so `??` would also work, but defense-in-depth across all response
  // shapes is cheap and matches the post-audit pattern.
  const candles = useMemo(
    () =>
      (Array.isArray(data.candles) ? data.candles : [])
        .map(normCandle)
        .filter((c) => c && c.value > 0),
    [data.candles],
  );

  // Volume profile uses recent daily candles. Picks the last ~20 if more
  // are available; gracefully handles fewer if interval was intraday.
  const volumeHistory = useMemo(
    () =>
      candles
        .slice(-20)
        .map((c) => ({ date: c.date, volume: c.volume })),
    [candles],
  );

  // Today's volume — last candle's volume, or live tick volume if available.
  const todayVolume = useMemo(() => {
    const tickVol = data.tick?.volume ?? data.price?.volume;
    if (typeof tickVol === 'number' && tickVol > 0) return tickVol;
    return candles.length > 0 ? candles[candles.length - 1].volume : null;
  }, [data.tick, data.price, candles]);

  const handleOpenOrder = (side) => {
    if (!kite?.connected) return;
    setOrderSide(side);
  };

  const handlePlaceOrder = async (payload) => {
    // Don't swallow — OrderPad's confirm dialog needs the rejection to display
    // the inline error and stay open. Error toasts still fire from the hook's
    // onError. Drawer close on success is handled by OrderPad via onOpenChange.
    //
    // If we arrived via ?action=sell&signal_id=... (from PortfolioV2), preserve
    // the original signal_id so the SELL row is FIFO-matched to the right
    // entry — that's what makes realised P&L correct on the Accounting page
    // and flips the position to CLOSED in /api/positions/nq.
    const signal = presetSignalId
      ? (() => {
          const [tk, sd] = presetSignalId.split('__');
          return { ticker: tk || symbol, signal_date: sd || new Date().toISOString().slice(0, 10) };
        })()
      : { ticker: symbol, signal_date: new Date().toISOString().slice(0, 10) };

    await placeOrder({ payload, signal, variety: 'regular' });
  };

  // Build a synthetic signal payload so OrderPad's risk-sizing math works.
  // We don't have a real entry/stop/target — use LTP for entry, ±2% as
  // sensible placeholders. The user can override in the OrderPad form.
  const orderPadSignal = useMemo(() => {
    if (!ltp) return null;
    return {
      ticker: symbol,
      entry: ltp,
      stop: ltp * 0.98,
      target: ltp * 1.04,
      signal_date: new Date().toISOString().slice(0, 10),
    };
  }, [symbol, ltp]);

  return (
    <PageShell title={`${symbol} — Stock Detail`} disclaimer>
      {/* BACK link */}
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="t-ui-callout"
        style={{
          background: 'transparent',
          border: 'none',
          color: 'var(--text-3)',
          padding: 0,
          cursor: 'pointer',
          marginTop: 16,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <ArrowLeft size={14} strokeWidth={1.75} /> Back
      </button>

      {/* WARMING-UP BANNER — surfaces when initial data hasn't landed in 2s.
          Render free-tier sleeps after ~15min idle, then takes 15-30s to wake.
          Showing this banner instead of a silent spinner converts "broken?"
          into "warming up" — preserves trust and lets the user wait without
          tab-switching. Auto-clears the moment price or candles arrive. */}
      {data.warmingUp && (
        <div
          role="status"
          style={{
            margin: '8px 0 12px',
            padding: '10px 14px',
            background: 'var(--info-soft)',
            border: '1px solid var(--info-edge)',
            borderRadius: 'var(--r-chip)',
            color: 'var(--info)',
            fontSize: 13,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <span
            aria-hidden
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: 'var(--info)',
              animation: 'spDot 1.2s ease-in-out infinite',
            }}
          />
          Backend warming up — first request after idle takes ~15s. Live data lands automatically.
          <style>{`@keyframes spDot { 0%,100% { opacity: 0.45 } 50% { opacity: 1 } }`}</style>
        </div>
      )}

      {/* HERO BAND — DecisionBand + ActiveSignalStrip + PositionStrip
          live together inside one wrapper. When NQ has an active call,
          the wrapper takes a brand-soft tint that visually says "this
          is a decision moment" without changing the structure. The
          --brand-edge border is the chromatic differentiator. */}
      <div
        style={{
          marginInline: 'calc(-1 * var(--space-5))',
          marginTop: 8,
          marginBottom: 16,
          paddingInline: 'var(--space-5)',
          paddingBlock: activeSignal ? 'var(--space-3)' : 0,
          background: activeSignal ? 'var(--brand-soft)' : 'transparent',
          borderTop: activeSignal ? '1px solid var(--brand-edge)' : 'none',
          borderBottom: activeSignal ? '1px solid var(--brand-edge)' : 'none',
          transition: 'background var(--dur-panel) ease',
        }}
      >
        {/* DECISION BAND — identity + price only. Buy/Sell live in the
            sticky bottom action bar so the primary action is always one
            tap away during scroll (Robinhood-pro pattern). */}
        <DecisionBand
          symbol={symbol}
          exchange={data.info?.exchange}
          name={data.info?.name}
          sector={data.info?.sector}
          ltp={ltp}
          change={change}
          changePct={changePct}
          tone={tone}
          isHolding={!!userPosition}
          kiteConnected={!!kite?.connected}
        />

        {/* ACTIVE NQ SIGNAL strip — turns the page into a decision tool */}
        <ActiveSignalStrip
          signal={activeSignal}
          currentPrice={ltp}
          kiteConnected={!!kite?.connected}
          onWhy={() => setSignalDetailOpen(true)}
          onBuy={() => handleOpenOrder('BUY')}
        />

        {/* USER POSITION strip if holding */}
        {userPosition && (
          <PositionStrip position={userPosition} ltp={ltp} />
        )}
      </div>

      {/* ─────────────────────────────────────────────────────────────
          CONTENT SURFACE — one continuous --surface-1 panel that wraps
          every block from the chart down through the stacked context
          sections. Replaces the previous "floating cards on black"
          pattern. Sections internally are separated by --edge-1
          hairlines, not black gutters.

          The Robinhood-pro pattern: the page IS the surface, not a
          dashboard of widgets. Visual rhythm comes from typography
          and section headings, not card borders.
      ───────────────────────────────────────────────────────────── */}
      <section
        className="dq-content-surface"
        style={{
          background: 'var(--surface-1)',
          border: '1px solid var(--edge-1)',
          borderRadius: 'var(--r-card)',
          boxShadow: 'var(--shadow-sm)',
          overflow: 'hidden',
          marginBottom: 24,
        }}
      >
        {/* PRICE CHART — taller (480px desktop) since it's the page hero. */}
        <div className="dq-cs-section dq-cs-chart">
          <ChartCard
            title="Price"
            badge={
              <div className="flex items-center" style={{ gap: 8 }}>
                <ChartTypeToggle value={chartType} onChange={setChartType} />
                {data.tick ? <StatusChip tone="bull">LIVE</StatusChip> : null}
              </div>
            }
            periods={PERIODS.map((p) => ({ label: p, value: p, active: p === data.period }))}
            onPeriodChange={(v) => data.changePeriod(v)}
            height={400}
            // No more rightRail tabs — tabs are stacked sections below.
            footer={
              data.price && (
                <>
                  <Meta label="Open"  value={fmtPrice(data.price?.open)} />
                  <Meta label="High"  value={fmtPrice(data.price?.high)} />
                  <Meta label="Low"   value={fmtPrice(data.price?.low)} />
                  <Meta label="Volume" value={fmtVolume(data.price?.volume)} />
                  <Meta label="52W H" value={fmtPrice(data.price?.fifty_two_week_high)} dim />
                  <Meta label="52W L" value={fmtPrice(data.price?.fifty_two_week_low)} dim />
                </>
              )
            }
          >
            {data.loading ? (
              <ChartSkeleton />
            ) : data.error || candles.length === 0 ? (
              data.errorKind === 'network' ? (
                <EmptyCard
                  variant="warn"
                  icon={<AlertCircle size={16} strokeWidth={1.75} />}
                  title="Backend warming up"
                  body="The pricing server is unreachable. It usually returns within 30 seconds — reload the page once it's back."
                  height={400}
                />
              ) : (
                <EmptyCard
                  variant="muted"
                  icon={<AlertCircle size={16} strokeWidth={1.75} />}
                  title="No price data"
                  body={`Couldn't fetch ${data.period} candles for ${symbol}. Try a different period or check the symbol.`}
                  height={400}
                />
              )
            ) : (
              <PriceChart
                candles={candles}
                height={400}
                chartType={chartType}
                showVolume={true}
                signal={activeSignal && {
                  entry:  Number(activeSignal.entry),
                  stop:   Number(activeSignal.stop),
                  target: Number(activeSignal.target),
                }}
                ltp={ltp}
                tone={tone}
                ariaLabel={`Price chart for ${symbol}, ${data.period}`}
                // intraday auto-detected from candle timestamps.
              />
            )}
          </ChartCard>
        </div>

        {/* DEPTH ROW — order book · volume profile · your history.
            Tagged bull because these are the action-near widgets — what
            the price IS doing right now and whether you've traded it. */}
        <StackedSection label="Depth · Volume · Your history" tone="bull">
          <div
            className="dq-decision-row"
            style={{ display: 'grid', gap: 16, gridTemplateColumns: '1fr' }}
          >
            <OrderBookL2 symbol={symbol} height={340} tick={data.tick} />
            <VolumeProfile todayVolume={todayVolume} history={volumeHistory} height={340} />
            <TickerOrderHistory ticker={symbol} height={340} />
            <style>{`
              @media (min-width: 1024px) {
                .dq-decision-row { grid-template-columns: 5fr 4fr 3fr; }
              }
            `}</style>
          </div>
        </StackedSection>

        {/* STACKED CONTEXT SECTIONS — replaces the old tab strip.
            Each section gets a tone so the page reads with chromatic
            rhythm instead of all-muted-gray labels. */}
        <StackedSection label="Overview" tone="muted">
          <OverviewPanel
            info={data.info}
            price={data.price}
            indicators={data.indicators}
            fundamentals={fundamentalsQuery.data}
          />
        </StackedSection>

        <StackedSection label="Fundamentals" tone="info">
          <FundamentalsPanel query={fundamentalsQuery} />
        </StackedSection>

        <StackedSection label="News" tone="warn">
          <NewsPanel query={newsQuery} />
        </StackedSection>

        <StackedSection label="Peers" tone="brand" last>
          <PeersPanel query={peersQuery} symbol={symbol} />
        </StackedSection>
      </section>

      {/* ORDER PAD */}
      <OrderPad
        open={!!orderSide}
        onOpenChange={(open) => !open && setOrderSide(null)}
        // Use the active NQ signal's entry/stop/target for sizing if present;
        // otherwise the synthetic ±2% scaffold from the orderPadSignal memo.
        signal={activeSignal || orderPadSignal}
        side={orderSide}
        capital={1000000}
        submitting={placingOrder}
        onPlace={handlePlaceOrder}
      />

      {/* SIGNAL DETAIL DRAWER — opened from ActiveSignalStrip "Why?" button */}
      {activeSignal && (
        <SignalDetailDrawer
          signal={activeSignal}
          open={signalDetailOpen}
          onOpenChange={setSignalDetailOpen}
          onOpenOrderPad={kite?.connected ? () => {
            setSignalDetailOpen(false);
            setTimeout(() => handleOpenOrder('BUY'), 220);
          } : undefined}
        />
      )}

      {/* STICKY DECISION FOOTER — primary action always one tap away.
          Robinhood-pro pattern: Buy/Sell live here, NOT in the DecisionBand.
          Visible whether or not Kite is connected — disabled state shows
          "Connect Kite to trade" so the affordance is always present and
          the user sees the path to enabling it. */}
      <div
        style={{
          position: 'sticky',
          bottom: 16,
          zIndex: 10,
          marginTop: 24,
          padding: '12px 16px',
          background: 'var(--surface-modal)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: '1px solid var(--edge-2)',
          borderRadius: 'var(--r-card)',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <div className="t-ui-footnote" style={{ color: 'var(--text-3)', flex: 1, minWidth: 200 }}>
          <span className="t-num-body" style={{ color: 'var(--text-1)', fontSize: 13, marginRight: 6 }}>
            {symbol}
          </span>
          {ltp != null ? (
            <>
              LTP {fmtPrice(ltp)}
              <span
                style={{
                  color: tone === 'bull' ? 'var(--bull)' : tone === 'bear' ? 'var(--bear)' : 'var(--text-3)',
                  marginLeft: 6,
                }}
              >
                {Number(changePct || 0).toFixed(2)}%
              </span>
            </>
          ) : (
            <span style={{ color: 'var(--text-3)' }}>Loading…</span>
          )}
        </div>
        <button
          type="button"
          disabled={!kite?.connected}
          onClick={() => handleOpenOrder('BUY')}
          className="t-ui-callout"
          style={{
            padding: '10px 22px',
            background: kite?.connected ? 'var(--brand)' : 'var(--surface-3)',
            color: kite?.connected ? 'var(--brand-fg)' : 'var(--text-3)',
            border: `1px solid ${kite?.connected ? 'var(--brand)' : 'var(--edge-1)'}`,
            borderRadius: 'var(--r-chip)',
            cursor: kite?.connected ? 'pointer' : 'not-allowed',
            fontWeight: 600,
            minWidth: 100,
          }}
          title={kite?.connected ? '' : 'Connect Kite to trade'}
        >
          {kite?.connected ? 'Buy at LTP' : 'Buy'}
        </button>
        <button
          type="button"
          disabled={!kite?.connected}
          onClick={() => handleOpenOrder('SELL')}
          className="t-ui-callout"
          style={{
            padding: '10px 22px',
            background: 'transparent',
            color: kite?.connected ? 'var(--bear)' : 'var(--text-3)',
            border: `1px solid ${kite?.connected ? 'var(--bear)' : 'var(--edge-1)'}`,
            borderRadius: 'var(--r-chip)',
            cursor: kite?.connected ? 'pointer' : 'not-allowed',
            fontWeight: 600,
            minWidth: 100,
          }}
          title={kite?.connected ? '' : 'Connect Kite to trade'}
        >
          {kite?.connected ? 'Sell at LTP' : 'Sell'}
        </button>
      </div>
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// STACKED SECTION
// ══════════════════════════════════════════════════════════════

// StackedSection — a labelled region inside the page's contiguous
// content surface. Replaces the previous floating-card-with-gap pattern.
// Each section sits below the one above it with a --edge-1 hairline
// dividing them. The label is uppercase --text-3 micro caps with an
// 8px semantic-coloured dot prefix that anchors the eye and gives the
// page chromatic rhythm.
//
// `tone` maps to the semantic palette:
//   'bull'  — actionable / market-near data (depth, volume, your history)
//   'brand' — Nifty Satvik-signature content (peers preview, related stocks)
//   'info'  — descriptive / fundamentals
//   'warn'  — news / events
//   'muted' — neutral context (default)
//
// `last` skips the bottom-flush adjustment for the final section.
function StackedSection({ label, children, tone = 'muted', last }) {
  const dotColor =
    tone === 'bull'  ? 'var(--bull)' :
    tone === 'bear'  ? 'var(--bear)' :
    tone === 'brand' ? 'var(--brand)' :
    tone === 'info'  ? 'var(--info)' :
    tone === 'warn'  ? 'var(--warn)' :
    'var(--text-4)';
  const haloColor =
    tone === 'bull'  ? 'var(--bull-soft)' :
    tone === 'bear'  ? 'var(--bear-soft)' :
    tone === 'brand' ? 'var(--brand-soft)' :
    tone === 'info'  ? 'var(--info-soft)' :
    tone === 'warn'  ? 'var(--warn-soft)' :
    'var(--edge-2)';
  // Strong-color variant for the inline label — gives each section a
  // chromatic anchor without painting the whole header strip.
  const labelColor =
    tone === 'bull'  ? 'var(--bull)' :
    tone === 'bear'  ? 'var(--bear)' :
    tone === 'brand' ? 'var(--brand-hi)' :
    tone === 'info'  ? 'var(--info)' :
    tone === 'warn'  ? 'var(--warn)' :
    'var(--text-2)';
  return (
    <section
      style={{
        padding: last ? 'var(--space-5) var(--space-5) var(--space-5)' : 'var(--space-5)',
        borderTop: '1px solid var(--edge-1)',
      }}
    >
      <div
        className="flex items-center"
        style={{
          gap: 10,
          marginBottom: 14,
          paddingBottom: 10,
          borderBottom: '1px solid var(--edge-1)',
        }}
      >
        <span
          aria-hidden="true"
          style={{
            display: 'inline-block',
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: dotColor,
            // Soft halo using the *-soft variant — gives the dot a glow
            // that reads as a tint marker rather than a hard dot.
            boxShadow: `0 0 0 3px ${haloColor}`,
            flexShrink: 0,
            marginLeft: 3, // visually centre the dot within its halo
          }}
        />
        <div
          className="t-ui-micro"
          style={{
            color: labelColor,
            letterSpacing: '0.10em',
            textTransform: 'uppercase',
            fontWeight: 600,
          }}
        >
          {label}
        </div>
      </div>
      {children}
    </section>
  );
}

// ══════════════════════════════════════════════════════════════
// CHART
// ══════════════════════════════════════════════════════════════

function ChartTypeToggle({ value, onChange }) {
  const opts = [
    { value: 'candle', label: 'Candle' },
    { value: 'area',   label: 'Area' },
  ];
  return (
    <div
      role="tablist"
      aria-label="Chart type"
      className="inline-flex items-center"
      style={{
        background: 'var(--surface-3)',
        borderRadius: 'var(--r-chip)',
        padding: 2,
        border: '1px solid var(--edge-1)',
      }}
    >
      {opts.map((o) => {
        const active = value === o.value;
        return (
          <button
            key={o.value}
            role="tab"
            aria-selected={active}
            type="button"
            onClick={() => onChange(o.value)}
            className="t-ui-callout transition-all"
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              background: active ? 'var(--surface-1)' : 'transparent',
              color: active ? 'var(--text-1)' : 'var(--text-3)',
              boxShadow: active ? 'var(--shadow-sm)' : 'none',
              fontWeight: active ? 600 : 500,
              border: 'none',
              cursor: 'pointer',
              minWidth: 52,
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div
      style={{
        height: 360,
        display: 'flex',
        alignItems: 'flex-end',
        gap: 4,
        padding: '12px 0',
        animation: 'skelPulse 1.8s ease-in-out infinite',
      }}
    >
      {Array.from({ length: 60 }).map((_, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            height: `${20 + Math.sin(i * 0.4) * 25 + (i / 4)}%`,
            background: 'var(--surface-2)',
            borderRadius: 2,
          }}
        />
      ))}
      <style>{`
        @keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }
        @media (prefers-reduced-motion: reduce) {
          [style*="skelPulse"] { animation: none !important; opacity: 0.85 !important; }
        }
      `}</style>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// HOLDING STRIP
// ══════════════════════════════════════════════════════════════

function PositionStrip({ position, ltp }) {
  const qty = Number(position.quantity) || 0;
  const avg = Number(position.average_price) || 0;
  const value = (ltp || avg) * qty;
  const pnl = ((ltp || avg) - avg) * qty;
  const pnlPct = avg > 0 ? (((ltp || avg) - avg) / avg) * 100 : 0;
  return (
    <section
      className="grid items-center"
      style={{
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: 14,
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: '14px 18px',
        marginBottom: 24,
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <Stat label="QTY HELD" value={qty} mono />
      <Stat label="AVG" value={fmtPrice(avg)} mono />
      <Stat label="VALUE" value={fmtINR(value)} mono />
      <Stat label="P&L" value={fmtINR(pnl)} mono tone={pnl >= 0 ? 'bull' : 'bear'} />
      <Stat label="P&L %" value={`${Number(pnlPct || 0).toFixed(2)}%`} mono tone={pnlPct >= 0 ? 'bull' : 'bear'} />
    </section>
  );
}

// ══════════════════════════════════════════════════════════════
// TAB PANELS
// ══════════════════════════════════════════════════════════════

function OverviewPanel({ info, price, indicators, fundamentals }) {
  // Overview now shows ONLY metrics that arrive with the primary fetch.
  // Fundamentals-only fields (P/E, Market Cap, Dividend Yield, EPS) live
  // in the Fundamentals tab so the Overview panel is fully populated on
  // first paint instead of showing 5+ "—" placeholders while waiting.
  //
  // Per spec: no `—` while loading — replace with a subtle "Loading…"
  // placeholder when the upstream source hasn't returned yet.
  const ph = price ? null : 'Loading…';
  const dayRange = price?.high && price?.low
    ? `${fmtPrice(price.low)} – ${fmtPrice(price.high)}`
    : ph || '—';
  // Sector / Industry / 52W range come from the Yahoo fundamentals payload —
  // the Kite `info` record only carries symbol/name/token, and the Kite live
  // quote has no 52-week range. Fall back to whatever info/price happen to hold.
  const fund = fundamentals || null;
  const sector = fund?.sector ?? info?.sector ?? null;
  const industry = fund?.industry ?? info?.industry ?? null;
  const week52High = price?.fifty_two_week_high ?? fund?.fifty_two_week_high ?? null;
  const week52Low = price?.fifty_two_week_low ?? fund?.fifty_two_week_low ?? null;
  const fundPh = fund ? '—' : 'Loading…';
  const items = [
    { label: 'Sector',         value: sector ?? fundPh },
    { label: 'Industry',       value: industry ?? fundPh },
    { label: 'Today Open',     value: price?.open ? fmtPrice(price.open) : (ph || '—') },
    { label: 'Day Range',      value: dayRange },
    { label: 'Previous Close', value: price?.close ? fmtPrice(price.close) : (ph || '—') },
    { label: 'Volume',         value: price?.volume ? fmtVolume(price.volume) : (ph || '—') },
    { label: '52W High',       value: week52High ? fmtPrice(week52High) : fundPh },
    { label: '52W Low',        value: week52Low ? fmtPrice(week52Low) : fundPh },
  ];
  // Technicals are gated by indicator availability. The fetch is deferred
  // (see useStockData's second effect) so this card fades in a beat after
  // the chart loads instead of blocking first paint with six "—" cells.
  const techItems = indicators
    ? [
        { label: 'RSI 14',     value: indicators.rsi_14 != null ? indicators.rsi_14.toFixed(1) : '—' },
        { label: 'ADX 14',     value: indicators.adx_14 != null ? indicators.adx_14.toFixed(1) : '—' },
        { label: 'EMA 21',     value: indicators.ema_21 ? fmtPrice(indicators.ema_21) : '—' },
        { label: 'EMA 50',     value: indicators.ema_50 ? fmtPrice(indicators.ema_50) : '—' },
        { label: 'ATR',        value: indicators.atr ? fmtPrice(indicators.atr) : '—' },
        { label: 'Volume avg', value: indicators.volume_avg ? fmtVolume(indicators.volume_avg) : '—' },
      ]
    : [
        { label: 'RSI 14',     value: 'Loading…' },
        { label: 'ADX 14',     value: 'Loading…' },
        { label: 'EMA 21',     value: 'Loading…' },
        { label: 'EMA 50',     value: 'Loading…' },
        { label: 'ATR',        value: 'Loading…' },
        { label: 'Volume avg', value: 'Loading…' },
      ];
  return (
    <div
      className="grid"
      style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: 16 }}
    >
      <DefinitionCard title="Profile" rows={items} />
      <DefinitionCard title="Technicals" rows={techItems} />
    </div>
  );
}

function FundamentalsPanel({ query }) {
  if (query.isLoading) return <PanelSkeleton />;
  if (query.error || !query.data) {
    return (
      <EmptyCard
        variant="muted"
        icon={<AlertCircle size={16} strokeWidth={1.75} />}
        title="No fundamentals available"
        body={query.error?.message || 'Yahoo data unavailable for this ticker right now.'}
        height={160}
      />
    );
  }
  const f = query.data;
  const rows = [
    { label: 'Market cap',    value: f.market_cap ? fmtINR(f.market_cap) : '—' },
    { label: 'Enterprise val',value: f.enterprise_value ? fmtINR(f.enterprise_value) : '—' },
    { label: 'P/E',           value: f.pe_ratio?.toFixed(2) ?? '—' },
    { label: 'Forward P/E',   value: f.forward_pe?.toFixed(2) ?? '—' },
    { label: 'PEG',           value: f.peg_ratio?.toFixed(2) ?? '—' },
    { label: 'Price/Book',    value: f.price_to_book?.toFixed(2) ?? '—' },
    { label: 'EPS',           value: f.eps != null ? f.eps.toFixed(2) : '—' },
    { label: 'Dividend yield',value: f.dividend_yield ? `${f.dividend_yield.toFixed(2)}%` : '—' },
    { label: 'Beta',          value: f.beta?.toFixed(2) ?? '—' },
    { label: 'Profit margin', value: f.profit_margin ? `${(f.profit_margin * 100).toFixed(2)}%` : '—' },
    { label: 'ROE',           value: f.roe ? `${(f.roe * 100).toFixed(2)}%` : '—' },
    { label: 'ROA',           value: f.roa ? `${(f.roa * 100).toFixed(2)}%` : '—' },
  ];
  return <DefinitionCard title="Yahoo Finance · cached 1h" rows={rows} columns={2} />;
}

function NewsPanel({ query }) {
  if (query.isLoading) return <PanelSkeleton />;
  const items = query.data?.news ?? query.data ?? [];
  if (!Array.isArray(items) || items.length === 0) {
    return (
      <EmptyCard
        variant="muted"
        title="No recent news"
        body="No news headlines available for this ticker right now."
        height={140}
      />
    );
  }
  return (
    <div
      className="flex flex-col"
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {items.slice(0, 10).map((n, i) => (
        <a
          key={i}
          href={n.link || n.url}
          target="_blank"
          rel="noreferrer"
          className="flex items-start"
          style={{
            padding: '14px 16px',
            borderBottom: i === Math.min(items.length, 10) - 1 ? 'none' : '1px solid var(--edge-1)',
            gap: 12,
            color: 'var(--text-1)',
            textDecoration: 'none',
            transition: 'background var(--dur-hover) var(--ease-out-cubic)',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-2)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
        >
          <div className="flex-1 min-w-0">
            <div className="t-ui-subhead" style={{ color: 'var(--text-1)' }}>
              {n.title}
            </div>
            <div
              className="t-ui-footnote"
              style={{ color: 'var(--text-3)', marginTop: 4, display: 'flex', gap: 8, alignItems: 'center' }}
            >
              {n.publisher && <span>{n.publisher}</span>}
              {(() => {
                // Backend returns .published as Unix epoch seconds (yahoo_finance.py:164).
                // Some sources may return .published_at as ISO string — handle both.
                const ts =
                  typeof n.published === 'number'
                    ? n.published * 1000
                    : n.published_at
                      ? new Date(n.published_at).getTime()
                      : null;
                if (!ts) return null;
                return (
                  <>
                    <span style={{ color: 'var(--text-4)' }}>·</span>
                    <span>{new Date(ts).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
                  </>
                );
              })()}
            </div>
          </div>
          <ExternalLink size={14} strokeWidth={1.75} style={{ color: 'var(--text-3)', flexShrink: 0, marginTop: 4 }} />
        </a>
      ))}
    </div>
  );
}

function PeersPanel({ query, symbol }) {
  if (query.isLoading) return <PanelSkeleton />;
  const peers = query.data?.peers ?? query.data ?? [];
  if (!Array.isArray(peers) || peers.length === 0) {
    return (
      <EmptyCard
        variant="muted"
        title="No peer data"
        body="Peer comparison isn't available for this ticker."
        height={140}
      />
    );
  }
  return (
    <div
      className="grid"
      style={{
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: 12,
      }}
    >
      {peers.map((p, i) => {
        const sym = (p.symbol || p.ticker || '').toUpperCase();
        const change = Number(p.change_pct ?? p.changePct ?? 0);
        // Backend returns .ltp (yahoo_finance.py:230). Tolerate .last_price
        // for forward-compat in case the schema is ever normalised.
        const price = p.ltp ?? p.last_price ?? null;
        return (
          <Link
            key={`${sym}-${i}`}
            to={`/stock/${sym}`}
            style={{
              background: 'var(--surface-1)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-card)',
              padding: 16,
              textDecoration: 'none',
              boxShadow: 'var(--shadow-sm)',
              transition: 'transform var(--dur-hover) var(--ease-out-cubic), box-shadow var(--dur-hover) var(--ease-out-cubic)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = 'var(--shadow-md)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
            }}
          >
            <div className="t-ui-subhead" style={{ color: 'var(--text-1)' }}>{sym}</div>
            {p.name && p.name !== sym && (
              <div
                className="t-ui-footnote truncate"
                style={{ color: 'var(--text-3)', marginTop: 2 }}
              >
                {p.name}
              </div>
            )}
            <div className="t-num-large" style={{ color: 'var(--text-1)', marginTop: 6 }}>
              {price != null ? fmtPrice(price) : '—'}
            </div>
            <div
              className="t-num-small"
              style={{ color: change > 0 ? 'var(--bull)' : change < 0 ? 'var(--bear)' : 'var(--text-3)', marginTop: 4 }}
            >
              {Number(change || 0).toFixed(2)}%
            </div>
          </Link>
        );
      })}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// SHARED INTERNAL PIECES
// ══════════════════════════════════════════════════════════════

function DefinitionCard({ title, rows, columns = 1 }) {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 'var(--pad-card)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <h3
        className="t-ui-subhead"
        style={{
          margin: 0,
          marginBottom: 12,
          color: 'var(--text-2)',
          letterSpacing: '0.04em',
        }}
      >
        {title}
      </h3>
      <div
        className="grid"
        style={{
          gridTemplateColumns: columns > 1 ? `repeat(${columns}, minmax(0, 1fr))` : '1fr',
          gap: '0 24px',
        }}
      >
        {rows.map((r, i) => {
          const isLoading = r.value === 'Loading…';
          const valColor = isLoading ? 'var(--text-3)' : 'var(--text-1)';
          return (
            <div
              key={`${r.label}-${i}`}
              className="flex items-baseline justify-between"
              style={{
                padding: '10px 0',
                borderBottom: '1px solid var(--edge-1)',
                gap: 12,
              }}
            >
              <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>{r.label}</span>
              <span
                className={isLoading ? 't-ui-body' : 't-num-body'}
                style={{
                  color: valColor,
                  fontStyle: isLoading ? 'italic' : 'normal',
                }}
              >
                {r.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Meta({ label, value, dim = false }) {
  return (
    <span className="flex items-baseline" style={{ gap: 6 }}>
      <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>{label}</span>
      <span
        className="t-num-small"
        style={{ color: dim ? 'var(--text-3)' : 'var(--text-1)' }}
      >
        {value ?? '—'}
      </span>
    </span>
  );
}

function Stat({ label, value, mono = false, tone }) {
  const color =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    'var(--text-1)';
  return (
    <div>
      <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 4 }}>{label}</div>
      <div
        className={mono ? 't-num-body' : 't-ui-body'}
        style={{ color, fontSize: 14 }}
      >
        {value}
      </div>
    </div>
  );
}

function PanelSkeleton() {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 'var(--pad-card)',
        minHeight: 200,
        animation: 'skelPulse 1.8s ease-in-out infinite',
      }}
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 16,
            marginBottom: 14,
            background: 'var(--surface-2)',
            borderRadius: 4,
            width: `${60 + (i % 3) * 12}%`,
          }}
        />
      ))}
      <style>{`
        @keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }
        @media (prefers-reduced-motion: reduce) {
          [style*="skelPulse"] { animation: none !important; opacity: 0.85 !important; }
        }
      `}</style>
    </div>
  );
}
