/**
 * SignalsV2 — Signals page.
 *
 * Sections render in strict ACTION order (not data order):
 *   1. Sell now       — EXIT_REQUIRED / terminal status (HIT_TARGET / HIT_STOP / EXPIRED)
 *   2. Buy today      — tier=signal, actionability=BUY_OPEN, signal_date is today
 *   3. Buy window closing — actionability=BUY_OPEN, signal_date is NOT today (days 2-3)
 *   4. Holding        — held by user (Kite holdings / nq_positions / status ACTIVE with hold)
 *   5. Brewing        — watchlist; sorted by ml_score desc; top-5 default, expand toggle
 *   6. Closed & missed — BUY_CLOSED / resolved; collapsed by default
 *
 * Architecture:
 *   - Data loaded via useSignals() (react-query, 5-min stale)
 *   - Broker state via useKiteMargins / useKiteHoldings (react-query, 30s stale)
 *   - Order placement via useOrderPlacement (chains Kite + nq_orders + WS)
 *   - Copy/compliance strings from @/lib/signalCopy
 */
import React, { useContext, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { RefreshCcw, AlertCircle, Clock, ChevronDown, ChevronUp, Radar } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { RegimeHeader } from '@/components/shared/RegimeHeader';
import { SignalCard } from '@/components/shared/SignalCard';
import { SignalDetailDrawer } from '@/components/shared/SignalDetailDrawer';
import { OrderPad } from '@/components/shared/OrderPad';
import { CommandBar } from '@/components/shared/CommandBar';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyState } from '@/components/shared/EmptyState';
import { SellGuidanceBanner } from '@/components/shared/SellGuidanceBanner';
import { useSignals } from '@/hooks/queries/useSignals';
import { useSignalHistory } from '@/hooks/queries/useSignalHistory';
import { useKiteHoldings, useKiteMargins } from '@/hooks/queries/useKiteState';
import { useNQPositions } from '@/hooks/queries/useNQPositions';
import { useWatchlist } from '@/hooks/queries/useWatchlist';
import { useOrderPlacement } from '@/hooks/useOrderPlacement';
import { pageEnter } from '@/lib/motion';
import { KiteContext } from '@/App';
import { fmtRelTime } from '@/lib/format';
import { tradeableState } from '@/lib/signalState';
import { ConvictionGauge } from '@/components/shared/ConvictionGauge';
import { SECTIONS, STATES, DISCLAIMER } from '@/lib/signalCopy';

// Entry gate constants — mirrored in models/v1/config.json. The 0.92 gate is
// LOCKED for 90 days (per CLAUDE.md, validated in diagnostics/tier_validation.md).
const ENTRY_GATE_CONF = 0.92;
const ENTRY_GATE_RET_PCT = 8.0;

// Watchlist default top-N before expand toggle.
const WATCH_TOP_N = 5;

const today = () => new Date().toISOString().slice(0, 10);

// ── Section predicates (applied to merged signal list) ────────────────────────

function isSellNow(sig) {
  const a = sig.actionability;
  const s = (sig.status || '').toUpperCase();
  return (
    a === 'EXIT_REQUIRED' ||
    s === 'HIT_TARGET' ||
    s === 'HIT_STOP' ||
    s === 'EXPIRED'
  );
}

function isBuyToday(sig) {
  const a = sig.actionability;
  const isSignalTier = sig.tier === 'signal' || !sig.tier; // default to signal if unset
  return (
    isSignalTier &&
    (a === 'BUY_OPEN' || !a) &&
    sig.signal_date === today()
  );
}

function isBuyWindowClosing(sig) {
  const a = sig.actionability;
  return a === 'BUY_OPEN' && sig.signal_date !== today();
}

function isHolding(sig, heldSet, positionBySignalId) {
  // Already classified as exit — don't double-count in hold
  if (isSellNow(sig)) return false;

  const sigId = sig.ticker && sig.signal_date ? `${sig.ticker}__${sig.signal_date}` : null;
  const position = sigId ? positionBySignalId.get(sigId) : null;
  const heldQty = position?.held_qty ?? sig.user_position?.held_qty ?? 0;
  const inKite = heldSet.has((sig.ticker || '').toUpperCase());
  const isActive = (sig.status || '').toUpperCase() === 'ACTIVE';

  return heldQty > 0 || inKite || (isActive && sig.nq_position_id);
}

function isClosed(sig) {
  const a = sig.actionability;
  const s = (sig.status || '').toUpperCase();
  return a === 'BUY_CLOSED' || ['CLOSED', 'RESOLVED', 'CANCELLED'].includes(s);
}

// ── Derive UI status for ConvictionGauge ──────────────────────────────────────

function deriveUiStatus(signal) {
  const raw = signal.status ? String(signal.status).toUpperCase() : null;
  if (raw === 'HIT_TARGET' || raw === 'HIT_STOP' || raw === 'EXPIRED') return raw;

  const t = today();
  if (signal.signal_date === t) return 'FRESH';

  const livePrice = signal.current_price ?? signal.last_price;
  if (livePrice) {
    const { state } = tradeableState(signal, livePrice);
    if (state === 'STOPPED') return 'HIT_STOP';
    return state;
  }
  return raw || 'ACTIVE';
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SignalsV2() {
  const kite = useContext(KiteContext);
  const signalsQuery = useSignals();
  const historyQuery = useSignalHistory();
  const holdingsQuery = useKiteHoldings({ enabled: !!kite?.connected });
  const marginsQuery = useKiteMargins({ enabled: !!kite?.connected });
  const nqPositionsQuery = useNQPositions();
  const watchlistQuery = useWatchlist();
  const { placeOrder, isPending: placingOrder } = useOrderPlacement();

  const [showClosed, setShowClosed] = useState(false);
  const [showAllWatch, setShowAllWatch] = useState(false);
  const [openSig, setOpenSig] = useState(null);
  const [orderSignal, setOrderSignal] = useState(null);
  const [orderSide, setOrderSide] = useState('BUY');
  const [commandOpen, setCommandOpen] = useState(false);

  // ── Data assembly ───────────────────────────────────────────────────────────

  const todaySignals = useMemo(() => signalsQuery.data?.signals ?? [], [signalsQuery.data]);
  const regime = signalsQuery.data?.regime ?? {};
  const modelInfo = signalsQuery.data?.model ?? {};
  const cronHealth = signalsQuery.data?.cron_health ?? {};
  const sizingCapital = signalsQuery.data?.sizing_capital ?? 1000000;

  // Merge today's signals with still-in-play history rows (dedupe by ticker+date).
  const signals = useMemo(() => {
    const fresh = todaySignals;
    const histRows = historyQuery.data?.history ?? [];
    const stillInPlay = histRows.filter((s) => {
      const status = String(s.status || '').toUpperCase();
      return (
        ['ACTIVE', 'NEAR_TARGET', 'IN_ZONE', 'IN ZONE', 'CHASE'].includes(status) &&
        s.entry > 0 &&
        s.grade !== 'REJECT'
      );
    });

    const seen = new Set(fresh.map((s) => `${s.ticker}__${s.signal_date}`));
    const merged = [...fresh];
    for (const h of stillInPlay) {
      const key = `${h.ticker}__${h.signal_date}`;
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(h);
      }
    }
    return merged;
  }, [todaySignals, historyQuery.data]);

  // Kite holdings set for HELD detection.
  const heldSet = useMemo(() => {
    const list = holdingsQuery.data ?? [];
    return new Set(list.map((h) => (h.tradingsymbol || h.symbol || '').toUpperCase()));
  }, [holdingsQuery.data]);

  // Per-signal NQ position lookup.
  const positionBySignalId = useMemo(() => {
    const map = new Map();
    for (const p of nqPositionsQuery.data?.positions ?? []) {
      if (p.signal_id) map.set(p.signal_id, p);
    }
    return map;
  }, [nqPositionsQuery.data]);

  // Annotate each signal with its position and uiStatus, then partition.
  const annotated = useMemo(() => {
    return signals.map((s) => {
      const sigId = s.ticker && s.signal_date ? `${s.ticker}__${s.signal_date}` : null;
      const position = sigId ? positionBySignalId.get(sigId) : null;
      const uiStatus = deriveUiStatus(s);
      return { ...s, _position: position, _uiStatus: uiStatus };
    });
  }, [signals, positionBySignalId]);

  // Partition into 6 action-ordered buckets.
  // Priority: SELL > BUY_TODAY > CLOSING > HOLDING > (watchlist separate) > CLOSED.
  const sections = useMemo(() => {
    const sell = [], buyToday = [], closing = [], holding = [], closed = [];

    for (const s of annotated) {
      if (isSellNow(s)) {
        sell.push(s);
      } else if (isBuyToday(s)) {
        buyToday.push(s);
      } else if (isBuyWindowClosing(s)) {
        closing.push(s);
      } else if (isHolding(s, heldSet, positionBySignalId)) {
        holding.push({ ...s, _heldByUser: true });
      } else if (isClosed(s)) {
        closed.push(s);
      }
      // Remaining signals (no match) fall off — they are either historical
      // rows that are genuinely stale or watchlist (handled separately).
    }

    return { sell, buyToday, closing, holding, closed };
  }, [annotated, heldSet, positionBySignalId]);

  // Watchlist — separate population from signals.
  const watchlistSignals = useMemo(() => {
    const raw = watchlistQuery.data?.signals ?? [];
    // Sort by ml_score desc (tiebreak: confidence)
    return [...raw].sort((a, b) => {
      const sa = Number(a.ml_score ?? a.confidence ?? 0);
      const sb = Number(b.ml_score ?? b.confidence ?? 0);
      return sb - sa;
    });
  }, [watchlistQuery.data]);

  const watchTop = watchlistSignals.slice(0, WATCH_TOP_N);
  const watchRest = watchlistSignals.slice(WATCH_TOP_N);
  const watchCount = watchlistSignals.length;

  // Top candidate for ConvictionGauge — entry signals OR watchlist leader.
  const topCandidate = useMemo(() => {
    const all = [...sections.buyToday, ...watchlistSignals];
    if (all.length === 0) return null;
    return all
      .map((s) => ({ ...s, _score: Number(s.ml_score ?? s.confidence ?? 0) }))
      .sort((a, b) => b._score - a._score)[0];
  }, [sections.buyToday, watchlistSignals]);

  const marginAvailable = marginsQuery.data?.available ?? sizingCapital;

  // ── Edge state flags ────────────────────────────────────────────────────────
  const cronStale = cronHealth?.status && cronHealth.status !== 'OK';
  const signalsError = signalsQuery.error;
  const signalsLoading = signalsQuery.isLoading || historyQuery.isLoading;

  const totalSignals = signals.length;
  const hasAnything = totalSignals > 0 || watchCount > 0;
  const allEmpty =
    !signalsLoading &&
    !signalsError &&
    !hasAnything;

  // ── Handlers ────────────────────────────────────────────────────────────────
  const handleOpenDetail = (sig) => setOpenSig(sig);
  const handleOpenOrderPad = (sig, side = 'BUY') => {
    if (!kite?.connected) return;
    setOrderSide(side);
    setOrderSignal(sig);
  };
  const handlePlaceOrder = async (payload) => {
    await placeOrder({ payload, signal: orderSignal, variety: 'regular' });
  };

  // Scan time label for meta strip
  const scanTimeLabel = signalsQuery.data?.scan_time
    ? fmtRelTime(signalsQuery.data.scan_time)
    : signalsQuery.dataUpdatedAt
      ? fmtRelTime(new Date(signalsQuery.dataUpdatedAt))
      : null;

  return (
    <PageShell title="Signals">
      {/* ── REGIME HEADER ─────────────────────────────────────────────────── */}
      <RegimeHeader
        regime={regime.status ? titleCase(regime.status) : '—'}
        tone={regimeTone(regime.status)}
        strength={typeof regime.strength === 'number' ? Math.round(regime.strength) : undefined}
        vix={typeof regime.vix === 'number' ? regime.vix : undefined}
        breadth={typeof regime.breadth === 'number' ? regime.breadth : undefined}
        scanTime={scanTimeLabel}
      />

      {/* ── META STRIP ────────────────────────────────────────────────────── */}
      <div
        className="t-ui-footnote flex items-center justify-between flex-wrap"
        style={{ color: 'var(--text-3)', marginBottom: 16, gap: 10 }}
      >
        <span>
          {scanTimeLabel
            ? `Last scan ${scanTimeLabel} IST · next 4:15 PM IST`
            : 'Last scan 4:15 PM IST · next 4:15 PM IST tomorrow'}
        </span>
        <div className="flex items-center" style={{ gap: 10 }}>
          {modelInfo.version && (
            <span>
              Model{' '}
              <span style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>
                {modelInfo.version}
              </span>
            </span>
          )}
          {cronHealth?.status === 'OK' && <StatusChip tone="bull">CRON OK</StatusChip>}
          <button
            type="button"
            onClick={() => signalsQuery.refetch()}
            disabled={signalsQuery.isFetching}
            aria-label="Refresh signals"
            style={{
              background: 'transparent',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-chip)',
              padding: 8,
              color: 'var(--text-2)',
              cursor: signalsQuery.isFetching ? 'wait' : 'pointer',
            }}
          >
            <RefreshCcw
              size={14}
              strokeWidth={1.75}
              style={{ animation: signalsQuery.isFetching ? 'spin 1s linear infinite' : 'none' }}
            />
          </button>
        </div>
      </div>

      {/* ── EDGE BANNERS ──────────────────────────────────────────────────── */}
      {cronStale && (
        <Banner tone="warn" icon={<Clock size={16} strokeWidth={1.75} />}>
          <strong style={{ color: 'var(--text-1)' }}>Signal scan stale.</strong>{' '}
          Last status: {cronHealth.status}. Data may be outdated.
        </Banner>
      )}
      {signalsError && !signalsLoading && (
        <Banner tone="warn" icon={<AlertCircle size={16} strokeWidth={1.75} />}>
          <strong style={{ color: 'var(--text-1)' }}>Signal feed offline.</strong>{' '}
          Showing last known data. {String(signalsError.message || signalsError)}
        </Banner>
      )}
      {!kite?.connected && signals.length > 0 && (
        <Banner tone="info" icon={<AlertCircle size={16} strokeWidth={1.75} />}>
          Connect Kite to place trades directly from these signals.{' '}
          <button
            type="button"
            onClick={kite?.connect}
            style={{
              color: 'var(--brand)',
              background: 'none',
              border: 'none',
              padding: 0,
              font: 'inherit',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Connect now →
          </button>
        </Banner>
      )}

      {/* ── CONVICTION GAUGE ─────────────────────────────────────────────── */}
      {!signalsLoading && (
        <ConvictionGauge
          topCandidate={topCandidate}
          cleared={sections.buyToday.length > 0}
          gateConf={ENTRY_GATE_CONF}
          gateRetPct={ENTRY_GATE_RET_PCT}
        />
      )}

      {/* ── SECTIONS ─────────────────────────────────────────────────────── */}
      {signalsLoading ? (
        <SkeletonSections />
      ) : allEmpty ? (
        <EmptyState
          icon={<Radar />}
          title="No signals yet today"
          body={STATES.empty}
        />
      ) : (
        <div className="dq-signals-stack flex flex-col" style={{ gap: 14 }}>

          {/* 1. SELL NOW */}
          {sections.sell.length > 0 && (
            <SectionFrame
              id="section-sell"
              tone="bear"
              title={SECTIONS.SELL.title}
              sub={SECTIONS.SELL.sub}
              count={sections.sell.length}
            >
              <SignalGrid
                signals={sections.sell}
                tier="SELL"
                kiteConnected={!!kite?.connected}
                heldSet={heldSet}
                onOpenDetail={handleOpenDetail}
                onSell={(sig) => handleOpenOrderPad(sig, 'SELL')}
              />
            </SectionFrame>
          )}

          {/* 2. BUY TODAY */}
          {sections.buyToday.length > 0 && (
            <SectionFrame
              id="section-buy-today"
              tone="brand"
              title={SECTIONS.BUY.title}
              sub={SECTIONS.BUY.sub}
              count={sections.buyToday.length}
            >
              <SignalGrid
                signals={sections.buyToday}
                tier="TODAY"
                kiteConnected={!!kite?.connected}
                heldSet={heldSet}
                onOpenDetail={handleOpenDetail}
                onBuy={(sig) => handleOpenOrderPad(sig, 'BUY')}
              />
            </SectionFrame>
          )}

          {/* 3. BUY WINDOW CLOSING */}
          {sections.closing.length > 0 && (
            <SectionFrame
              id="section-closing"
              tone="bull"
              title={SECTIONS.CLOSING.title}
              sub={SECTIONS.CLOSING.sub}
              count={sections.closing.length}
            >
              <SignalGrid
                signals={sections.closing}
                tier="CLOSING"
                kiteConnected={!!kite?.connected}
                heldSet={heldSet}
                onOpenDetail={handleOpenDetail}
                onBuy={(sig) => handleOpenOrderPad(sig, 'BUY')}
              />
            </SectionFrame>
          )}

          {/* 4. HOLDING */}
          {sections.holding.length > 0 && (
            <SectionFrame
              id="section-holding"
              tone="info"
              title={SECTIONS.HOLD.title}
              sub={SECTIONS.HOLD.sub}
              count={sections.holding.length}
            >
              <SignalGrid
                signals={sections.holding}
                tier="HELD"
                kiteConnected={!!kite?.connected}
                heldSet={heldSet}
                onOpenDetail={handleOpenDetail}
                onSell={(sig) => handleOpenOrderPad(sig, 'SELL')}
                heldByUser
              />
            </SectionFrame>
          )}

          {/* 5. BREWING / WATCHLIST */}
          {watchCount > 0 && (
            <SectionFrame
              id="section-brewing"
              tone="warn"
              title={SECTIONS.WATCH.title}
              sub={SECTIONS.WATCH.sub}
              count={watchCount}
              opacity={0.92}
            >
              <SignalGrid
                signals={watchTop}
                tier="WATCHLIST"
                kiteConnected={!!kite?.connected}
                heldSet={heldSet}
                onOpenDetail={handleOpenDetail}
              />
              {watchRest.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <button
                    type="button"
                    onClick={() => setShowAllWatch((v) => !v)}
                    className="t-ui-callout flex items-center"
                    style={{
                      background: 'var(--warn-soft)',
                      border: '1px solid oklch(68% 0.18 40 / 0.32)',
                      borderRadius: 'var(--r-chip)',
                      padding: '7px 12px',
                      color: 'var(--warn)',
                      cursor: 'pointer',
                      gap: 6,
                      fontWeight: 600,
                    }}
                  >
                    {showAllWatch
                      ? <ChevronUp size={14} strokeWidth={2} />
                      : <ChevronDown size={14} strokeWidth={2} />}
                    {showAllWatch
                      ? 'Show fewer'
                      : `Show all (${watchCount})`}
                  </button>
                  {showAllWatch && (
                    <div style={{ marginTop: 16 }}>
                      <SignalGrid
                        signals={watchRest}
                        tier="WATCHLIST"
                        kiteConnected={!!kite?.connected}
                        heldSet={heldSet}
                        onOpenDetail={handleOpenDetail}
                      />
                    </div>
                  )}
                </div>
              )}
            </SectionFrame>
          )}

          {/* 6. CLOSED & MISSED — collapsed by default */}
          {sections.closed.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowClosed((v) => !v)}
                className="t-ui-callout flex items-center"
                style={{
                  background: 'transparent',
                  border: '1px solid var(--edge-1)',
                  borderRadius: 'var(--r-chip)',
                  padding: '7px 12px',
                  color: 'var(--text-3)',
                  cursor: 'pointer',
                  gap: 6,
                }}
              >
                {showClosed
                  ? <ChevronUp size={14} strokeWidth={2} />
                  : <ChevronDown size={14} strokeWidth={2} />}
                {showClosed ? 'Hide' : `Show ${sections.closed.length} closed signal${sections.closed.length !== 1 ? 's' : ''}`}
              </button>
              {showClosed && (
                <div style={{ marginTop: 12 }}>
                  <SectionFrame
                    id="section-closed"
                    tone="muted"
                    title={SECTIONS.CLOSED.title}
                    sub={SECTIONS.CLOSED.sub}
                    count={sections.closed.length}
                  >
                    <SignalGrid
                      signals={sections.closed}
                      tier="MISSED"
                      kiteConnected={!!kite?.connected}
                      heldSet={heldSet}
                      onOpenDetail={handleOpenDetail}
                    />
                  </SectionFrame>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── FOOTER DISCLAIMER ─────────────────────────────────────────────── */}
      <footer
        style={{
          marginTop: 48,
          paddingTop: 16,
          borderTop: '1px solid var(--edge-1)',
        }}
      >
        <p
          className="t-ui-footnote"
          style={{
            color: 'var(--text-3)',
            fontSize: 11,
            fontStyle: 'italic',
            margin: 0,
            maxWidth: '76ch',
          }}
        >
          {DISCLAIMER}
        </p>
        <div
          className="t-ui-footnote flex items-center justify-between flex-wrap"
          style={{ color: 'var(--text-3)', marginTop: 12, gap: 16 }}
        >
          <span>
            <span
              className="t-num-small"
              style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}
            >
              {totalSignals}
            </span>{' '}
            signal{totalSignals !== 1 ? 's' : ''} tracked,{' '}
            {watchCount} on watchlist
          </span>
          {modelInfo.version && (
            <span>
              Model{' '}
              <span style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>
                {modelInfo.version}
              </span>
              {modelInfo.n_features ? (
                <>
                  {' '}·{' '}
                  <span style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>
                    {modelInfo.n_features}
                  </span>{' '}
                  features
                </>
              ) : null}
            </span>
          )}
        </div>
      </footer>

      {/* ── DRAWERS ───────────────────────────────────────────────────────── */}
      <SignalDetailDrawer
        signal={openSig}
        open={!!openSig}
        onOpenChange={(open) => !open && setOpenSig(null)}
        onOpenOrderPad={
          kite?.connected
            ? (s) => { setOpenSig(null); setTimeout(() => handleOpenOrderPad(s, 'BUY'), 220); }
            : undefined
        }
      />
      <OrderPad
        open={!!orderSignal}
        onOpenChange={(open) => !open && setOrderSignal(null)}
        signal={orderSignal}
        side={orderSide}
        capital={sizingCapital}
        marginAvailable={marginAvailable}
        submitting={placingOrder}
        onPlace={handlePlaceOrder}
      />
      <CommandBar
        open={commandOpen}
        onOpenChange={setCommandOpen}
        tickers={signals.map((s) => ({ symbol: s.ticker }))}
        actions={[
          {
            id: 'refresh',
            title: 'Refresh signals',
            subtitle: 'Force pull from server',
            icon: <RefreshCcw />,
            run: () => signalsQuery.refetch(),
          },
        ]}
        onPlaceOrder={(parsed) => {
          const match = signals.find(
            (s) => (s.ticker || '').toUpperCase() === parsed.ticker
          );
          if (match && kite?.connected) handleOpenOrderPad(match, parsed.side);
        }}
      />

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        .dq-signals-stack > .dq-section-frame {
          margin-top: 22px;
        }
        .dq-signals-stack > .dq-section-frame:first-child {
          margin-top: 0;
        }
      `}</style>
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════

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

const TONE_COLORS = {
  brand: { dot: 'var(--brand)',   halo: 'var(--brand-soft)', count: 'var(--brand)' },
  bull:  { dot: 'var(--bull)',    halo: 'var(--bull-soft)',  count: 'var(--bull)' },
  info:  { dot: 'var(--info)',    halo: 'var(--info-soft)',  count: 'var(--info)' },
  warn:  { dot: 'var(--warn)',    halo: 'var(--warn-soft)',  count: 'var(--warn)' },
  bear:  { dot: 'var(--bear)',    halo: 'var(--bear-soft)',  count: 'var(--bear)' },
  muted: { dot: 'var(--text-4)', halo: 'var(--edge-2)',     count: 'var(--text-3)' },
};

/**
 * SectionFrame — section wrapper with title · count · subtitle header.
 *
 * Collapses to nothing when count === 0 (enforced by parent — frame is only
 * rendered when count > 0). Populated sections breathe at 22px via
 * `.dq-section-frame` adjacent-sibling rule.
 */
function SectionFrame({ id, title, sub, count, tone = 'muted', children, opacity }) {
  const t = TONE_COLORS[tone] || TONE_COLORS.muted;

  return (
    <div
      id={id}
      className="dq-section-frame"
      style={opacity != null ? { opacity } : undefined}
    >
      {/* Section header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: 10,
          marginBottom: 14,
          paddingBottom: 10,
          borderBottom: '1px solid var(--edge-1)',
          flexWrap: 'wrap',
        }}
      >
        {/* Colored dot */}
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
            transform: 'translateY(-1px)',
          }}
        />
        {/* Title */}
        <h2
          className="t-title-2"
          style={{ margin: 0, color: 'var(--text-1)', fontSize: '1rem', fontWeight: 600 }}
        >
          {title}
        </h2>
        {/* Count pill */}
        <span
          className="t-num-small"
          style={{
            color: t.count,
            fontFamily: 'var(--font-mono)',
            fontWeight: 500,
            background: t.halo,
            padding: '2px 8px',
            borderRadius: 'var(--r-chip)',
          }}
        >
          {count}
        </span>
        {/* Subtitle */}
        {sub && (
          <span
            className="t-ui-footnote"
            style={{ color: 'var(--text-3)', flex: 1, minWidth: '20ch' }}
          >
            {sub}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

/**
 * SignalGrid — card grid for one section.
 *
 * `tier` is passed through to SignalCard so it can adapt its CTA:
 *   TODAY / CLOSING → buy CTA
 *   HELD / SELL     → sell CTA
 *   WATCHLIST       → research CTA
 *   MISSED          → no CTA
 *
 * `heldByUser` overrides the card to show the holdingChip instead of the
 * buy chip when true (e.g. HELD section or confirmed Kite holding).
 */
function SignalGrid({
  signals,
  tier,
  kiteConnected,
  heldSet,
  onOpenDetail,
  onBuy,
  onSell,
  heldByUser: sectionHeld,
}) {
  if (!signals || signals.length === 0) return null;

  const isWatchlist = tier === 'WATCHLIST';
  const isSell = tier === 'SELL' || tier === 'HELD';

  return (
    <motion.div
      variants={pageEnter}
      initial="hidden"
      animate="visible"
      className="grid"
      style={{
        gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))',
        gap: 16,
      }}
    >
      <AnimatePresence>
        {signals.map((sig, i) => {
          const position = sig._position;
          const sellGuidance = position?.sell_guidance;
          const cardHeld = sectionHeld || sig._heldByUser || heldSet.has((sig.ticker || '').toUpperCase());

          const ctaMode = isWatchlist ? 'research'
            : isSell ? 'sell'
            : 'buy';

          const tierAccent = tier === 'CLOSING' ? 'bull'
            : tier === 'HELD' || tier === 'SELL' ? 'info'
            : tier === 'WATCHLIST' ? 'warn'
            : undefined;

          return (
            <motion.div
              key={`${sig.ticker}-${sig.signal_date}-${tier}`}
              custom={i}
              variants={pageEnter}
              initial="hidden"
              animate="visible"
              layout
              className="flex flex-col"
              style={{ gap: 8 }}
            >
              {sellGuidance && (
                <SellGuidanceBanner
                  guidance={sellGuidance}
                  lastPrice={position?.last_price}
                  onSell={kiteConnected && onSell ? () => onSell(sig) : undefined}
                />
              )}
              <SignalCard
                signal={sig}
                priceSeries={null}
                heldByUser={cardHeld}
                ctaMode={ctaMode}
                tierAccent={tierAccent}
                onOpenDetail={onOpenDetail}
                onOpenOrderPad={
                  isWatchlist
                    ? undefined
                    : kiteConnected
                    ? (s) => {
                        if (isSell && onSell) onSell(s);
                        else if (onBuy) onBuy(s);
                      }
                    : undefined
                }
              />
            </motion.div>
          );
        })}
      </AnimatePresence>
    </motion.div>
  );
}

function Banner({ tone = 'info', icon, children }) {
  const colors = {
    info: { bg: 'var(--info-soft)', edge: 'oklch(78% 0.11 230 / 0.32)', fg: 'var(--info)' },
    warn: { bg: 'var(--warn-soft)', edge: 'oklch(68% 0.18 40 / 0.32)',  fg: 'var(--warn)' },
    bear: { bg: 'var(--bear-soft)', edge: 'oklch(66% 0.21 25 / 0.32)',  fg: 'var(--bear)' },
  }[tone];
  return (
    <div
      role="status"
      className="flex items-center"
      style={{
        marginTop: 16,
        marginBottom: 8,
        padding: '12px 16px',
        background: colors.bg,
        border: `1px solid ${colors.edge}`,
        borderRadius: 'var(--r-chip)',
        gap: 12,
      }}
    >
      <span style={{ color: colors.fg, flexShrink: 0 }}>{icon}</span>
      <p className="t-ui-body" style={{ color: 'var(--text-2)', margin: 0 }}>
        {children}
      </p>
    </div>
  );
}

/**
 * SkeletonSections — loading state: RegimeHeader is already shown above,
 * so just render section-shaped skeletons to avoid layout jump.
 */
function SkeletonSections() {
  return (
    <div className="flex flex-col" style={{ gap: 32 }}>
      {/* Section header skeleton */}
      {[6, 3].map((count, si) => (
        <div key={si}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--surface-2)' }} />
            <div style={{ width: 120, height: 18, background: 'var(--surface-2)', borderRadius: 4 }} />
            <div style={{ width: 28, height: 18, background: 'var(--surface-2)', borderRadius: 'var(--r-chip)' }} />
          </div>
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
                  padding: 'var(--pad-card)',
                  animation: 'skeletonPulse 1.8s ease-in-out infinite',
                  animationDelay: `${i * 0.1}s`,
                }}
              >
                <div style={skelLine(120, 22)} />
                <div style={{ ...skelLine(80, 12), marginTop: 10 }} />
                <div style={{ height: 24, marginTop: 16, background: 'var(--surface-2)', borderRadius: 4 }} />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 16 }}>
                  <div style={skelLine('100%', 56)} />
                  <div style={skelLine('100%', 56)} />
                  <div style={skelLine('100%', 56)} />
                </div>
                <div style={{ ...skelLine('100%', 40), marginTop: 14 }} />
                <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                  <div style={{ flex: 1, height: 36, background: 'var(--surface-2)', borderRadius: 'var(--r-chip)' }} />
                  <div style={{ flex: 1, height: 36, background: 'var(--surface-2)', borderRadius: 'var(--r-chip)' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
      <style>{`
        @keyframes skeletonPulse {
          0%, 100% { opacity: 1; }
          50%      { opacity: 0.65; }
        }
      `}</style>
    </div>
  );
}

function skelLine(w, h) {
  return { width: w, height: h, background: 'var(--surface-2)', borderRadius: 4 };
}
