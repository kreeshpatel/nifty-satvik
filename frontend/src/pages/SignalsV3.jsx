/**
 * SignalsV3 — the Research page (/premove).
 *
 * Rebuilt 2026-07-07 to the "Research Insights" layout: a graded calls table
 * plus a right rail (Morning commentary · Signal stats · How calls are made).
 * The position sizer, chart and order pad were intentionally removed from this
 * page — sizing + order entry live on the stock detail page (reached via each
 * row's Buy/Sell action, which deep-links /stock/:sym?action=...).
 *
 * Data (unchanged from the previous split-pane version):
 *   - useSignals()      → active signals + regime + cron_health
 *   - useWatchlist()    → brewing/watchlist signals
 *   - useKiteHoldings() → held tickers for "holding" detection
 *   - useNQPositions()  → NQ-tracked positions (qty/fill per signal)
 *   - useQuoteBatch()   → live LTP / day-change overlay
 *
 * Compliance: client-facing conviction/section strings sourced from
 *   @/lib/signalCopy. No "guarantee/will/sure" language.
 */

import React, { useState, useEffect, useMemo, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { KiteContext } from '@/App';
import { AuthContext } from '@/context/AuthContext';
import { useSignals } from '@/hooks/queries/useSignals';
import { useWatchlist } from '@/hooks/queries/useWatchlist';
import { useKiteHoldings } from '@/hooks/queries/useKiteState';
import { useNQPositions } from '@/hooks/queries/useNQPositions';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { GlassTabs } from '@/components/shared/GlassTabs';
import { CONVICTION, DISCLAIMER, STATES } from '@/lib/signalCopy';
import { EmptyState } from '@/components/shared/EmptyState';
import PickOfWeek from '@/components/shared/PickOfWeek';
import TradeCardModal from '@/components/shared/TradeCardModal';
import '@/styles/signals-v3.css';
import '@/styles/research-insights.css';

const RISK_BUDGET = 5000; // ₹ risk per trade for suggested sizing

// ── Formatters ────────────────────────────────────────────────────────
const fmtNum  = (n) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct1 = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%';

function todayISO() { return new Date().toISOString().slice(0, 10); }

function addTradingDays(dateStr, n) {
  const d = new Date(dateStr);
  let added = 0;
  while (added < n) {
    d.setDate(d.getDate() + 1);
    const dow = d.getDay();
    if (dow !== 0 && dow !== 6) added++;
  }
  return d;
}
function fmtBuyBy(date) {
  if (!date) return null;
  return new Date(date).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
}
function daysLeftUntil(dateObj, now = new Date()) {
  if (!dateObj) return null;
  return Math.max(0, Math.ceil((new Date(dateObj) - now) / 86400000));
}

// ── Logo (favicon with gradient fallback) ─────────────────────────────
const TICKER_DOMAINS = {
  RELIANCE: 'ril.com', TCS: 'tcs.com', BAJFINANCE: 'bajajfinserv.in', INFY: 'infosys.com',
  HDFCBANK: 'hdfcbank.com', ICICIBANK: 'icicibank.com', BHARTIARTL: 'airtel.in',
  LT: 'larsentoubro.com', MARUTI: 'marutisuzuki.com', KOTAKBANK: 'kotak.com',
  ADANIENT: 'adanienterprises.com', SBIN: 'sbi.co.in', AXISBANK: 'axisbank.com',
  TATAPOWER: 'tatapower.com', POLYCAB: 'polycab.com', VOLTAS: 'voltas.com',
  CUMMINSIND: 'cummins.com', TITAN: 'titancompany.com', SUNPHARMA: 'sunpharma.com',
  DIVISLAB: 'divislabs.com', PERSISTENT: 'persistent.com', WIPRO: 'wipro.com',
};
function tickerBg(sym) {
  let h = 0;
  for (const ch of (sym || '')) h = (h + ch.charCodeAt(0) * 13) % 360;
  return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`;
}
function Logo({ sym, size = 34, radius = 10 }) {
  const domain = TICKER_DOMAINS[(sym || '').toUpperCase()];
  const sources = domain
    ? [`https://icons.duckduckgo.com/ip3/${domain}.ico`, `https://www.google.com/s2/favicons?domain=${domain}&sz=128`]
    : [];
  const [idx, setIdx] = useState(0);
  useEffect(() => { setIdx(0); }, [sym]);
  if (idx >= sources.length) {
    return (
      <div className="logo-tile logo-mono" style={{ width: size, height: size, borderRadius: radius, background: tickerBg(sym), fontSize: Math.round(size * 0.34) }}>
        {(sym || '??').slice(0, 2)}
      </div>
    );
  }
  return (
    <div className="logo-tile" style={{ width: size, height: size, borderRadius: radius }}>
      <img src={sources[idx]} alt={sym} onError={() => setIdx((i) => i + 1)} />
    </div>
  );
}

function convOf(grade, isWatch) {
  const g = (grade || 'B')[0].toUpperCase();
  if (isWatch && g !== 'A') return { word: CONVICTION.LOW.label, cls: 'conv-c' };
  if (g === 'A') return { word: CONVICTION.HIGH.label, cls: 'conv-a' };
  if (g === 'B') return { word: CONVICTION.MED.label, cls: 'conv-b' };
  return { word: CONVICTION.LOW.label, cls: 'conv-c' };
}

// ── Action derivation (deterministic) ─────────────────────────────────
function deriveAction(sig, heldSet, positionByTicker) {
  const status = (sig.status || '').toUpperCase();
  const actionability = (sig.actionability || '').toUpperCase();

  if (actionability === 'EXIT_REQUIRED' || status === 'HIT_TARGET' || status === 'HIT_STOP' || status === 'EXPIRED') {
    return { action: 'sell-now', sellReason: status === 'HIT_TARGET' ? 'target' : 'stop' };
  }
  if (actionability === 'BUY_CLOSED' || ['CLOSED', 'RESOLVED', 'CANCELLED'].includes(status)) {
    return { action: 'closed' };
  }
  const ticker = (sig.ticker || '').toUpperCase();
  const inKite = heldSet.has(ticker);
  const pos = positionByTicker.get(ticker);
  const heldQty = pos?.held_qty ?? sig.user_position?.held_qty ?? 0;
  if (inKite || heldQty > 0 || (status === 'ACTIVE' && sig.nq_position_id)) {
    return { action: 'holding', position: pos };
  }
  if (actionability === 'BUY_OPEN' || (!actionability && (sig.tier === 'signal' || !sig.tier))) {
    const today = todayISO();
    if (sig.buy_window_until) {
      if (today < sig.buy_window_until) return { action: 'buy-today' };
      if (today === sig.buy_window_until) return { action: 'closing' };
      return { action: 'closed' };
    }
    if (sig.signal_date === today) return { action: 'buy-today' };
    return { action: 'closing' };
  }
  if (actionability === 'WATCHLIST' || sig.tier === 'watchlist') return { action: 'brewing' };
  if (status === 'ACTIVE') return { action: 'closing' };
  return { action: 'closed' };
}

// ── Signal enrichment — maps real API fields to UI fields ─────────────
function enrichSignal(raw, heldSet, positionByTicker, quotes) {
  const { action, sellReason, position } = deriveAction(raw, heldSet, positionByTicker);
  const ticker = raw.ticker || raw.sym || '';
  const q = quotes?.[ticker.toUpperCase()] || null;
  const ltp = q?.last_price ?? raw.current_price ?? raw.last_price ?? raw.close ?? raw.entry ?? 0;
  const dayChangePct = q?.change_pct ?? null;
  const entry = raw.entry ?? 0;
  const stop = raw.stop ?? entry;
  const target = raw.target ?? entry;
  const rr = entry !== stop ? (target - entry) / (entry - stop) : Infinity;
  const fromEntry = entry > 0 ? ((ltp - entry) / entry) * 100 : 0;
  const upside = entry > 0 ? ((target - entry) / entry) * 100 : 0;
  const zeroRisk = entry === stop;
  const perShareRisk = Math.max(1, entry - stop);
  const suggQty = zeroRisk ? (position?.held_qty || 10) : Math.max(1, Math.floor(RISK_BUDGET / perShareRisk));

  let buyByStr = null, daysLeft = null;
  if (raw.buy_window_until) {
    const d = new Date(raw.buy_window_until);
    buyByStr = fmtBuyBy(d); daysLeft = daysLeftUntil(d);
  } else if (raw.signal_date && (action === 'buy-today' || action === 'closing')) {
    const d = addTradingDays(raw.signal_date, 2);
    buyByStr = fmtBuyBy(d); daysLeft = daysLeftUntil(d);
  }

  let dayOf = null;
  if (raw.signal_date && action === 'holding') {
    dayOf = Math.max(1, Math.round((Date.now() - new Date(raw.signal_date)) / 86400000));
    dayOf = Math.min(dayOf, raw.hold_days || dayOf);
  }

  const isWatch = action === 'brewing';
  const grade = raw.grade || 'B';

  return {
    ...raw,
    sym: ticker,
    name: raw.name || ticker,
    sector: raw.sector || '—',
    ex: raw.exchange || 'NSE',
    grade,
    action,
    sellReason: sellReason ?? null,
    entry, stop, target,
    _ltp: ltp,
    _rr: rr,
    _dayChangePct: dayChangePct,
    _fromEntry: fromEntry,
    _upside: upside,
    _zeroRisk: zeroRisk,
    _suggQty: suggQty,
    buyByStr, daysLeft, dayOf,
    hold: raw.hold_days || 10,
    conv: convOf(grade, isWatch),
    isFreshToday: raw.signal_date === todayISO(),
  };
}

// ── Row helpers ───────────────────────────────────────────────────────
// Display order: actionable first, closed last.
const ACTION_RANK = { 'sell-now': 0, 'buy-today': 1, closing: 2, holding: 3, brewing: 4, closed: 5 };

function rowAction(s) {
  switch (s.action) {
    case 'buy-today':
    case 'closing':  return { label: 'Buy',   cls: 'buy',   suffix: '?action=buy' };
    case 'sell-now': return { label: 'Sell',  cls: 'sell',  suffix: '?action=sell' };
    case 'holding':  return { label: 'Hold',  cls: 'hold',  suffix: '' };
    case 'brewing':  return { label: 'Watch', cls: 'watch', suffix: '' };
    default:         return { label: 'View',  cls: 'view',  suffix: '' };
  }
}

function potentialCell(s) {
  if (s.action === 'brewing') {
    const dist = s._ltp > 0 ? ((s.entry - s._ltp) / s._ltp) * 100 : null;
    return { main: 'below gate', sub: dist != null ? `${fmtPct1(dist)} to enter` : '', tone: 'warn' };
  }
  if (s.action === 'holding' || s.action === 'sell-now') {
    return { main: fmtPct1(s._fromEntry), sub: s.dayOf ? `${s.dayOf}/${s.hold}d held` : '', tone: s._fromEntry >= 0 ? 'bull' : 'bear' };
  }
  const horizon = s.daysLeft != null ? `~${s.daysLeft} days` : `~${s.hold} days`;
  return { main: fmtPct1(s._upside), sub: horizon, tone: 'bull' };
}

// ── Daily-monitor event chip (weekly book) ────────────────────────────
// Surfaces the intra-week event the daily monitor cron flagged on this card
// (results/weekly_monitor.json → backend overlay → sig.monitor), without ever
// touching the frozen entry/stop/target. Only high-signal states show a chip.
function monitorChip(s) {
  const m = s.monitor;
  if (!m) return null;
  if (m.stop_breached) return { label: '⚠ Stop hit', cls: 'mon-bear' };
  if (m.target_reached) return { label: '✓ +2R', cls: 'mon-bull' };
  if (m.kind === 'hold' && m.dist_to_stop_pct != null && m.dist_to_stop_pct <= 2)
    return { label: 'Near stop', cls: 'mon-warn' };
  if (m.kind === 'buy' && m.buy_window_open && m.filled_today === false)
    return { label: 'Gapped — wait', cls: 'mon-warn' };
  return null;
}

// ── Forward-review scorecard tile (weekly book — Oct-1 promote/kill machinery) ──
function ReviewCard({ card }) {
  if (!card) return null;
  const status = card.status || 'ACCRUING';
  const tone = /PROMOTE/.test(status) ? 'bull' : /(KILL|HALT)/.test(status) ? 'bear' : 'warn';
  const rd = card.gates?.readiness || {};
  const nClosed = rd.n_closed ?? 0;
  const quarters = rd.quarters_elapsed ?? 0;
  const closedPct = Math.min(100, Math.round((nClosed / 40) * 100));
  return (
    <div className="ri-card">
      <div className="ri-card-h">FORWARD REVIEW</div>
      <div className="rev-statusrow">
        <span className={`rev-badge rev-${tone}`}>{status}</span>
        {card.next_review && (
          <span className="rev-when">{card.next_review} · {card.days_to_review}d</span>
        )}
      </div>
      <div className="rev-prog">
        <div className="rev-prog-l"><span>Closed trades</span><span className="tnum">{nClosed}/40</span></div>
        <div className="rev-bar"><span className="rev-bar-fill" style={{ width: `${closedPct}%` }} /></div>
        <div className="rev-prog-l"><span>Quarters elapsed</span><span className="tnum">{quarters}/4</span></div>
      </div>
      <div className="rev-note">
        Promote/kill is decided only at the {card.next_review || 'quarterly'} review — never between dates.
        Forward-watch paper, not live capital.
      </div>
    </div>
  );
}

// ── Regime → commentary ───────────────────────────────────────────────
function regimeInfo(regime) {
  const rs = (regime?.status || '').toUpperCase();
  if (rs.includes('BULL')) return { label: 'Bullish', tone: 'bull', line: 'Trend and breadth favour longs.' };
  if (rs.includes('BEAR')) return { label: 'Bearish', tone: 'bear', line: 'Defensive — trend and breadth are against longs.' };
  return { label: 'Choppy', tone: 'warn', line: 'Mixed tape — no clear trend. Stay selective.' };
}

// ── Right-rail cards ──────────────────────────────────────────────────
function CommentaryCard({ regime, model, freshCount }) {
  const r = regimeInfo(regime);
  const vix = regime?.vix != null ? Number(regime.vix).toFixed(1) : '—';
  const breadth = regime?.breadth != null ? (regime.breadth > 0 ? `+${regime.breadth}` : `${regime.breadth}`) : '—';
  const book = model === 'momentum' ? 'momentum' : 'systematic';
  return (
    <div className="ri-card">
      <div className="ri-card-h">MARKET NOW</div>
      <div className="ri-comm-title">
        The market is <span className={`num-${r.tone}`}>{r.label}.</span> {r.line}
      </div>
      <div className="ri-comm-body">
        Breadth {breadth} adv–dec · India VIX {vix}. {freshCount} fresh {book} name{freshCount === 1 ? '' : 's'} cleared
        the conviction gate at today's scan. The calls post themselves — no manual action.
      </div>
    </div>
  );
}

function StatBar({ label, value, total }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="ri-statrow">
      <span className="ri-stat-l">{label}</span>
      <span className="ri-bar"><span className="ri-bar-fill" style={{ width: `${pct}%` }} /></span>
      <span className="ri-stat-v tnum">{value}</span>
    </div>
  );
}

// Compact sizer for the right rail — sizes today's top pick against a
// user-entered capital amount, using the same fixed risk-per-trade budget
// (RISK_BUDGET) the rest of the page's suggested-qty figures already use, so
// this card's number always agrees with what a call's own card implies.
function SizerCard({ pick, navigate }) {
  const [cash, setCash] = useState('');
  if (!pick) return null;

  const entry = pick.entry ?? 0;
  const stop = pick.stop ?? entry;
  const perShareRisk = Math.max(1, entry - stop);
  const cashNum = Number(cash) || 0;

  const byRisk = Math.floor(RISK_BUDGET / perShareRisk);
  const byCash = entry > 0 ? Math.floor(cashNum / entry) : 0;
  const qty = cashNum > 0 ? Math.max(0, Math.min(byRisk, byCash)) : byRisk;
  const cost = qty * entry;
  const riskAmt = qty * perShareRisk;

  return (
    <div className="ri-card">
      <div className="ri-card-h">POSITION SIZER</div>
      <div className="ri-sizer-sym">{pick.sym} <span className="ri-sizer-entry tnum">@ {fmtNum(entry)}</span></div>
      <label className="ri-sizer-label" htmlFor="ri-sizer-cash">Capital available</label>
      <input
        id="ri-sizer-cash"
        className="ri-sizer-input"
        type="number"
        inputMode="decimal"
        placeholder="e.g. 100000"
        value={cash}
        onChange={(e) => setCash(e.target.value)}
      />
      <div className="ri-kv"><span>Suggested qty</span><b className="tnum">{qty > 0 ? qty : '—'}</b></div>
      <div className="ri-kv"><span>Cost</span><b className="tnum">{qty > 0 ? `₹${fmtNum(cost)}` : '—'}</b></div>
      <div className="ri-kv"><span>Risk at stop</span><b className="num-bear tnum">{qty > 0 ? `₹${fmtNum(riskAmt)}` : '—'}</b></div>
      <div className="ri-sizer-note">Capped at ₹{RISK_BUDGET.toLocaleString('en-IN')} risk/trade{cashNum > 0 ? ' or your capital, whichever is lower.' : '.'}</div>
      <button type="button" className="ri-sizer-btn" onClick={() => navigate(`/stock/${encodeURIComponent(pick.sym)}?action=buy`)}>
        Buy {pick.sym} →
      </button>
    </div>
  );
}

function SignalStatsCard({ buyPool }) {
  const fresh = buyPool.filter((s) => s.isFreshToday).length;
  const gradeA = buyPool.filter((s) => (s.grade || 'B')[0].toUpperCase() === 'A').length;
  const gradeB = buyPool.filter((s) => (s.grade || 'B')[0].toUpperCase() === 'B').length;
  const avgPot = buyPool.length ? buyPool.reduce((a, s) => a + (s._upside || 0), 0) / buyPool.length : null;
  const avgHz  = buyPool.length ? Math.round(buyPool.reduce((a, s) => a + (s.hold || 0), 0) / buyPool.length) : null;
  const denom = Math.max(gradeA, gradeB, 1);
  return (
    <div className="ri-card">
      <div className="ri-card-h">SIGNAL STATS · TODAY</div>
      <div className="ri-kv"><span>Fresh entries</span><b className="num-info tnum">{fresh}</b></div>
      <StatBar label="Grade A" value={gradeA} total={denom} />
      <StatBar label="Grade B" value={gradeB} total={denom} />
      <div className="ri-kv"><span>Avg potential</span><b className="num-bull tnum">{avgPot == null ? '—' : fmtPct1(avgPot)}</b></div>
      <div className="ri-kv"><span>Avg horizon</span><b className="tnum">{avgHz == null ? '—' : `${avgHz} days`}</b></div>
    </div>
  );
}

function HowCallsMadeCard() {
  return (
    <div className="ri-card">
      <div className="ri-card-h">HOW CALLS ARE MADE</div>
      <div className="ri-how">
        Long-only cross-sectional trend-momentum on Nifty-500 large + mid caps. Ranked by 200-day
        SMA slope over 63 days; top-15 by cross-sectional rank; 10–63 day hold. Fully mechanical —
        the daily cron scans, grades, and posts the calls; there is no discretionary override.
      </div>
    </div>
  );
}

// ── Calls table ───────────────────────────────────────────────────────
function CallRow({ s, onOpen, onAction }) {
  const act = rowAction(s);
  const pot = potentialCell(s);
  const g = (s.grade || 'B')[0].toUpperCase();
  const dayChg = s._dayChangePct;
  const mon = monitorChip(s);
  return (
    <div className="ri-row" onClick={() => onOpen(s)} role="button" tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onOpen(s); }}>
      <div className="ri-scrip">
        <Logo sym={s.sym} size={34} />
        <div className="ri-scrip-l">
          <div className="ri-scrip-top">
            <span className="ri-sym">{s.sym}</span>
            <span className={`ri-grade g-${g}`}>{g}</span>
          </div>
          <div className="ri-scrip-sub">
            {s.sector}{s.isFreshToday && <> · <span className="num-info">fresh</span></>} · {s.ex}
            {mon && <span className={`ri-mon ${mon.cls}`}>{mon.label}</span>}
          </div>
        </div>
      </div>

      <div className="ri-cell ri-ltp">
        <div className="ri-cell-main tnum">{fmtNum(s._ltp)}</div>
        {dayChg != null && (
          <div className={`ri-cell-sub tnum ${dayChg >= 0 ? 'num-bull' : 'num-bear'}`}>{fmtPct1(dayChg)}</div>
        )}
      </div>

      <div className="ri-cell ri-reco">
        <div className="ri-cell-main tnum">{fmtNum(s.entry)}</div>
      </div>

      <div className="ri-cell ri-pot">
        <div className={`ri-cell-main tnum num-${pot.tone}`}>{pot.main}</div>
        {pot.sub && <div className="ri-cell-sub">{pot.sub}</div>}
      </div>

      <div className="ri-act" onClick={(e) => e.stopPropagation()}>
        <button className={`ri-btn ri-btn-${act.cls}`} onClick={() => onAction(s.sym, act.suffix)}>
          {act.label}
        </button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────
const FILTERS = [
  { key: 'today',   label: 'Added today',   test: (s) => s.isFreshToday },
  { key: 'buy',     label: 'Your next buy', test: (s) => s.action === 'buy-today' || s.action === 'closing' },
  { key: 'profit',  label: 'Making profit', test: (s) => s.action === 'holding' && s._fromEntry > 0 },
  { key: 'closing', label: 'Closing soon',  test: (s) => s.action === 'closing' },
];

export default function SignalsV3() {
  const kite = useContext(KiteContext);
  const { user } = useContext(AuthContext);
  const isAdmin = !!user?.is_admin;
  const navigate = useNavigate();

  // MOMENTUM SUSPENDED 2026-07-06 (owner) — cron paused, tab hidden. Flip to
  // false to restore the tab (and re-enable the cron in the same commit).
  const MOMENTUM_SUSPENDED = true;
  const [model, setModel] = useState(MOMENTUM_SUSPENDED ? 'bhanushali' : 'momentum');
  const [filter, setFilter] = useState('all');
  const [tradeCard, setTradeCard] = useState(null);

  const signalsQuery    = useSignals({ model });
  const watchlistQuery  = useWatchlist({ model });
  const holdingsQuery   = useKiteHoldings({ enabled: !!kite?.connected });
  const nqPositionsQuery = useNQPositions();

  const rawSignals   = useMemo(() => signalsQuery.data?.signals ?? [], [signalsQuery.data]);
  const rawWatchlist = useMemo(() => watchlistQuery.data?.signals ?? [], [watchlistQuery.data]);

  const quoteSymbols = useMemo(
    () => [...new Set([...rawSignals, ...rawWatchlist].map((s) => (s.ticker || '').toUpperCase()).filter(Boolean))],
    [rawSignals, rawWatchlist]
  );
  const quotesQuery = useQuoteBatch(quoteSymbols);
  const quotes = quotesQuery.data ?? null;

  const regime = signalsQuery.data?.regime ?? {};
  const monitorAsOf = signalsQuery.data?.monitor_as_of ?? null;
  const monitorStamp = signalsQuery.data?.monitor_generated_ist ?? null;
  const reviewScorecard = signalsQuery.data?.review_scorecard ?? null;

  const heldSet = useMemo(() => {
    const list = holdingsQuery.data ?? [];
    return new Set(list.map((h) => (h.tradingsymbol || h.symbol || '').toUpperCase()));
  }, [holdingsQuery.data]);

  const positionByTicker = useMemo(() => {
    const map = new Map();
    for (const p of nqPositionsQuery.data?.positions ?? []) {
      const t = (p.ticker || p.symbol || '').toUpperCase();
      if (t) map.set(t, p);
    }
    return map;
  }, [nqPositionsQuery.data]);

  const allEnriched = useMemo(() => {
    const enriched = [
      ...rawSignals.map((s) => enrichSignal(s, heldSet, positionByTicker, quotes)),
      ...rawWatchlist.map((s) => enrichSignal({ ...s, actionability: 'WATCHLIST', tier: 'watchlist' }, heldSet, positionByTicker, quotes)),
    ];
    const seen = new Set();
    return enriched
      .filter((s) => { if (seen.has(s.sym)) return false; seen.add(s.sym); return true; })
      .sort((a, b) => (ACTION_RANK[a.action] ?? 9) - (ACTION_RANK[b.action] ?? 9));
  }, [rawSignals, rawWatchlist, heldSet, positionByTicker, quotes]);

  const buyPool = useMemo(
    () => allEnriched.filter((s) => s.action === 'buy-today' || s.action === 'closing'),
    [allEnriched]
  );

  const rows = useMemo(() => {
    if (filter === 'all') return allEnriched;
    const f = FILTERS.find((x) => x.key === filter);
    return f ? allEnriched.filter(f.test) : allEnriched;
  }, [allEnriched, filter]);

  const counts = useMemo(() => {
    const c = {};
    for (const f of FILTERS) c[f.key] = allEnriched.filter(f.test).length;
    return c;
  }, [allEnriched]);

  const topPick = useMemo(
    () => buyPool[0] || allEnriched[0] || null,
    [buyPool, allEnriched]
  );

  const freshCount = counts.today ?? 0;

  const doAction  = (sym, suffix) => navigate(`/stock/${encodeURIComponent(sym)}${suffix}`);

  if (signalsQuery.error) {
    return (
      <div className="ri-app">
        <EmptyState title="Couldn't load research calls" body={STATES.error} />
      </div>
    );
  }

  const loading = signalsQuery.isLoading;

  return (
    <div className="ri-app">
      {/* Header */}
      <div className="ri-head">
        <div className="ri-head-l">
          <h1 className="ri-title">Research Insights</h1>
          <p className="ri-sub">Model-generated calls, graded &amp; level-annotated. Not advice — your own capital, your own rules.</p>
        </div>
        <div className="ri-head-r">
          <GlassTabs
            tabs={MOMENTUM_SUSPENDED
              ? [{ key: 'bhanushali', label: 'Systematic' }]
              : [{ key: 'momentum', label: 'Momentum' }, { key: 'bhanushali', label: 'Systematic' }]}
            active={model}
            onChange={setModel}
            size="md"
          />
          <span className={`chip ${model === 'momentum' ? 'c-bull' : 'c-warn'}`}>
            {model === 'momentum' ? 'Live' : 'Forward-watch · paper'}
          </span>
          {model === 'bhanushali' && monitorStamp && (
            <span className="ri-fresh" title={`Live re-price as of ${monitorAsOf}`}>
              prices updated {monitorStamp} IST
            </span>
          )}
        </div>
      </div>

      {/* Filter chips */}
      <div className="ri-chips">
        <button className={`ri-chip ${filter === 'all' ? 'on' : ''}`} onClick={() => setFilter('all')}>
          All <span className="ri-chip-n">{allEnriched.length}</span>
        </button>
        {FILTERS.map((f) => (
          <button key={f.key} className={`ri-chip ${filter === f.key ? 'on' : ''}`} onClick={() => setFilter(f.key)}>
            {f.label} <span className="ri-chip-n">{counts[f.key] ?? 0}</span>
          </button>
        ))}
      </div>

      {/* Pick of the week */}
      {!loading && topPick && (
        <div className="ri-pick">
          <PickOfWeek sig={topPick} to={`/stock/${encodeURIComponent(topPick.sym || '')}`} ctaLabel="Size & buy →" />
        </div>
      )}

      {/* Body: table + right rail */}
      <div className="ri-grid">
        <div className="ri-main">
          <div className="ri-table">
            <div className="ri-thead">
              <span>Scrip</span>
              <span className="ri-th-r">LTP</span>
              <span className="ri-th-r">Reco</span>
              <span className="ri-th-r">Potential</span>
              <span />
            </div>
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => <div key={i} className="ri-row-skel skeleton-card" />)
            ) : rows.length === 0 ? (
              <div className="ri-empty">
                {filter === 'all' ? STATES.empty : 'No calls match this filter right now.'}
              </div>
            ) : (
              rows.map((s) => <CallRow key={s.sym} s={s} onOpen={setTradeCard} onAction={doAction} />)
            )}
          </div>
        </div>

        <aside className="ri-rail">
          <SizerCard pick={topPick} navigate={navigate} />
          {isAdmin && model === 'bhanushali' && <ReviewCard card={reviewScorecard} />}
          <CommentaryCard regime={regime} model={model} freshCount={freshCount} />
          <SignalStatsCard buyPool={buyPool} />
          <HowCallsMadeCard />
        </aside>
      </div>

      {/* Footer */}
      <footer className="ri-foot">
        <div className="ri-disclaimer">{DISCLAIMER}</div>
        <div className="ri-foot-meta">SEBI Research Analyst · Model-generated signals · Research output only · NSE data delayed 15 min · v2026.07</div>
      </footer>

      <TradeCardModal sig={tradeCard} open={!!tradeCard} onOpenChange={(o) => !o && setTradeCard(null)} />
    </div>
  );
}
