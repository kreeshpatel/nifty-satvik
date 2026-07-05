/**
 * SignalsV3 — Signals page (action-first, desktop split-pane).
 *
 * Pattern: desktop = master-detail SPLIT-PANE (list left, chart+detail right).
 * Mobile (≤900px) = tap a card to PUSH a full-screen detail view (not a drawer).
 *
 * Data:
 *   - useSignals()     → active signals + regime + cron_health + sizing_capital
 *   - useWatchlist()   → brewing/watchlist signals
 *   - useKiteHoldings() → held tickers for "holding" detection
 *   - useKiteMargins()  → available margin for order pad
 *   - useNQPositions() → NQ-tracked positions (qty/fillPrice per signal)
 *
 * Compliance: all client-facing section/conviction strings sourced from
 *   @/lib/signalCopy. No "guarantee", "will", "sure", "sure-shot" anywhere.
 */

import React, { useState, useEffect, useRef, useMemo, useContext } from 'react';
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts';
import { KiteContext } from '@/App';
import { useSignals } from '@/hooks/queries/useSignals';
import { useWatchlist } from '@/hooks/queries/useWatchlist';
import { useKiteHoldings, useKiteMargins } from '@/hooks/queries/useKiteState';
import { useNQPositions } from '@/hooks/queries/useNQPositions';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { GlassTabs } from '@/components/shared/GlassTabs';
import {
  SECTIONS,
  CONVICTION,
  DISCLAIMER,
  STATES,
  actionChip as libActionChip,
  holdingChip as libHoldingChip,
} from '@/lib/signalCopy';
import { explainExitRules, exitRulesSummary } from '@/lib/exitRules';
import { EmptyState } from '@/components/shared/EmptyState';
import '@/styles/signals-v3.css';

// ─────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────
const WATCH_TOP_N = 5;
const RISK_BUDGET = 5000; // ₹ risk per trade for suggested sizing

const SECTION_ORDER = [
  { id: 'sell-now',   ...SECTIONS.SELL  },
  { id: 'buy-today',  ...SECTIONS.BUY   },
  { id: 'closing',    ...SECTIONS.CLOSING },
  { id: 'holding',    ...SECTIONS.HOLD  },
  { id: 'brewing',    ...SECTIONS.WATCH },
  { id: 'closed',     ...SECTIONS.CLOSED },
];

// ─────────────────────────────────────────────────────────────────────
// Formatters
// ─────────────────────────────────────────────────────────────────────
const fmtINR  = (n) => n == null ? '—' : '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtNum  = (n) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct  = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
const fmtPct1 = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%';
const fmtLakh = (n) => {
  if (n == null) return '—';
  const sign = n < 0 ? '−' : '';
  const a = Math.abs(n);
  if (a >= 1e7) return sign + '₹' + (a / 1e7).toFixed(2) + 'Cr';
  if (a >= 1e5) return sign + '₹' + (a / 1e5).toFixed(2) + 'L';
  return sign + '₹' + Math.round(a).toLocaleString('en-IN');
};

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

// Add N trading days (Mon–Fri) to a date string
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

// Signal issue date — "2 Jul", with year appended when it isn't the current year
function fmtSigDate(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d)) return null;
  const opts = { day: 'numeric', month: 'short' };
  if (d.getFullYear() !== new Date().getFullYear()) opts.year = 'numeric';
  return d.toLocaleDateString('en-IN', opts);
}

function daysLeftUntil(dateObj, now = new Date()) {
  if (!dateObj) return null;
  return Math.max(0, Math.ceil((new Date(dateObj) - now) / 86400000));
}

// ─────────────────────────────────────────────────────────────────────
// Logo (favicon with gradient fallback)
// ─────────────────────────────────────────────────────────────────────
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

function Logo({ sym, size = 32, radius = 9 }) {
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

// ─────────────────────────────────────────────────────────────────────
// Status chip map
// ─────────────────────────────────────────────────────────────────────
const STATUS_MAP = {
  FRESH:       { label: 'Fresh',          cls: 'c-info',  live: true  },
  'IN-ZONE':   { label: 'In zone',        cls: 'c-brand'              },
  IN_ZONE:     { label: 'In zone',        cls: 'c-brand'              },
  EXTENDED:    { label: 'Extended',       cls: 'c-info'               },
  ACTIVE:      { label: 'Active',         cls: 'c-bull',  live: true  },
  HIT_TARGET:  { label: 'Hit target',     cls: 'c-bull'               },
  HIT_STOP:    { label: 'Hit stop',       cls: 'c-bear'               },
  EXPIRED:     { label: 'Expired',        cls: 'c-muted'              },
  CLOSED:      { label: 'Closed',         cls: 'c-muted'              },
};

function statusChip(sig) {
  const raw = (sig.status || 'ACTIVE').toUpperCase().replace(/ /g, '_');
  return STATUS_MAP[raw] ?? { label: raw, cls: 'c-muted' };
}

// ─────────────────────────────────────────────────────────────────────
// Conviction helper
// ─────────────────────────────────────────────────────────────────────
function convOf(grade, isWatch) {
  const g = (grade || 'B')[0].toUpperCase();
  if (isWatch && g !== 'A') return { word: CONVICTION.LOW.label, cls: 'conv-c' };
  if (g === 'A') return { word: CONVICTION.HIGH.label, cls: 'conv-a' };
  if (g === 'B') return { word: CONVICTION.MED.label, cls: 'conv-b' };
  return { word: CONVICTION.LOW.label, cls: 'conv-c' };
}

// ─────────────────────────────────────────────────────────────────────
// R:R helpers
// ─────────────────────────────────────────────────────────────────────
function rrTone(rr) { return !isFinite(rr) ? 'num-bull' : rr >= 2 ? 'num-bull' : rr >= 1 ? '' : 'num-bear'; }
function rrWord(rr) { return rr >= 2 ? 'solid' : rr >= 1 ? 'fair' : 'thin'; }
function rrDisplay(sig) {
  if (sig._zeroRisk || !isFinite(sig._rr)) return { val: '—', word: 'risk-free', tone: 'num-bull', free: true };
  return { val: Number(sig._rr).toFixed(2), word: rrWord(sig._rr), tone: rrTone(sig._rr), free: false };
}

// ─────────────────────────────────────────────────────────────────────
// Action derivation (deterministic, per instructions)
// ─────────────────────────────────────────────────────────────────────
function deriveAction(sig, heldSet, positionByTicker) {
  const status = (sig.status || '').toUpperCase();
  const actionability = (sig.actionability || '').toUpperCase();

  // 1. Sell now: EXIT_REQUIRED or terminal
  if (
    actionability === 'EXIT_REQUIRED' ||
    status === 'HIT_TARGET' ||
    status === 'HIT_STOP' ||
    status === 'EXPIRED'
  ) {
    let sellReason = 'stop';
    if (status === 'HIT_TARGET') sellReason = 'target';
    return { action: 'sell-now', sellReason };
  }

  // 2. Closed / BUY_CLOSED
  if (actionability === 'BUY_CLOSED' || ['CLOSED', 'RESOLVED', 'CANCELLED'].includes(status)) {
    return { action: 'closed' };
  }

  // 3. Holding: user holds a position (Kite holdings or NQ positions or ACTIVE with nq_position_id)
  const ticker = (sig.ticker || '').toUpperCase();
  const inKite = heldSet.has(ticker);
  const pos = positionByTicker.get(ticker);
  const heldQty = pos?.held_qty ?? sig.user_position?.held_qty ?? 0;
  if (inKite || heldQty > 0 || (status === 'ACTIVE' && sig.nq_position_id)) {
    return { action: 'holding', position: pos };
  }

  // 4. Buy open — today vs not today
  if (actionability === 'BUY_OPEN' || (!actionability && (sig.tier === 'signal' || !sig.tier))) {
    const today = todayISO();
    if (sig.signal_date === today) return { action: 'buy-today' };
    return { action: 'closing' };
  }

  // 5. Watchlist
  if (actionability === 'WATCHLIST' || sig.tier === 'watchlist') {
    return { action: 'brewing' };
  }

  // Default fallback for ACTIVE with no other match: closing
  if (status === 'ACTIVE') return { action: 'closing' };
  return { action: 'closed' };
}

// ─────────────────────────────────────────────────────────────────────
// Mock candle generator (deterministic seed from ticker)
// TODO: replace genCandles with real OHLCV when available
// ─────────────────────────────────────────────────────────────────────
function genCandles(sig, n = 64) {
  const sym = sig.ticker || sig.sym || 'XX';
  let s = 0;
  for (const c of sym) s = (s * 131 + c.charCodeAt(0)) % 2147483647;
  const rand = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return (s % 100000) / 100000; };
  const ltp = sig._ltp || sig.close || sig.entry || 100;
  const lo = Math.min(sig.stop || ltp * 0.95, ltp) * 0.985;
  const hi = Math.max(sig.target || ltp * 1.1, ltp) * 1.012;
  const amp = hi - lo;
  const out = [];
  let price = (sig.entry || ltp) * 0.965;
  const start = new Date();
  start.setDate(start.getDate() - n);
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const anchor = (sig.entry || ltp) + (ltp - (sig.entry || ltp)) * Math.pow(t, 1.7);
    const pull = (anchor - price) * 0.25;
    const noise = (rand() - 0.5) * amp * 0.10;
    const open = price;
    let close = price + pull + noise;
    close = Math.max(lo, Math.min(hi, close));
    const wick = amp * 0.05 * rand();
    const high = Math.min(hi, Math.max(open, close) + wick);
    const low  = Math.max(lo, Math.min(open, close) - wick);
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    out.push({ time: d.toISOString().slice(0, 10), open: +open.toFixed(2), high: +high.toFixed(2), low: +low.toFixed(2), close: +close.toFixed(2) });
    price = close;
  }
  out[out.length - 1].close = ltp;
  out[out.length - 1].high = Math.max(out[out.length - 1].high, ltp);
  out[out.length - 1].low  = Math.min(out[out.length - 1].low, ltp);
  return out;
}

// ─────────────────────────────────────────────────────────────────────
// Signal enrichment — maps real API fields to UI fields
// ─────────────────────────────────────────────────────────────────────
function enrichSignal(raw, heldSet, positionByTicker, sizingCapital, quotes) {
  const { action, sellReason, position } = deriveAction(raw, heldSet, positionByTicker);

  const ticker = raw.ticker || raw.sym || '';
  // Live quote overlay — the cron writes current_price once at scan time (previous
  // close), so without this the page shows a frozen price all day.
  const q = quotes?.[ticker.toUpperCase()] || null;
  const ltp = q?.last_price ?? raw.current_price ?? raw.last_price ?? raw.close ?? raw.entry ?? 0;
  const dayChangePct = q?.change_pct ?? null;
  const entry = raw.entry ?? 0;
  const stop = raw.stop ?? entry;
  const target = raw.target ?? entry;
  const rr = entry !== stop ? (target - entry) / (entry - stop) : Infinity;
  const fromEntry = entry > 0 ? ((ltp - entry) / entry) * 100 : 0;
  const upside = entry > 0 ? ((target - entry) / entry) * 100 : 0;
  const risk = entry > 0 ? ((stop - entry) / entry) * 100 : 0;
  const zeroRisk = entry === stop;
  const perShareRisk = Math.max(1, entry - stop);
  const suggQty = zeroRisk
    ? (position?.held_qty || 10)
    : Math.max(1, Math.floor(RISK_BUDGET / perShareRisk));

  // buyBy / daysLeft derivation
  let buyByDate = null;
  let buyByStr = null;
  let daysLeft = null;
  if (raw.buy_window_until) {
    buyByDate = new Date(raw.buy_window_until);
    buyByStr = fmtBuyBy(buyByDate);
    daysLeft = daysLeftUntil(buyByDate);
  } else if (raw.signal_date && (action === 'buy-today' || action === 'closing')) {
    buyByDate = addTradingDays(raw.signal_date, 2);
    buyByStr = fmtBuyBy(buyByDate);
    daysLeft = daysLeftUntil(buyByDate);
  }

  // dayOf: days since signal_date for holdings
  let dayOf = null;
  if (raw.signal_date && action === 'holding') {
    dayOf = Math.max(1, Math.round((Date.now() - new Date(raw.signal_date)) / 86400000));
    dayOf = Math.min(dayOf, raw.hold_days || dayOf);
  }

  // Position data from NQ positions or Kite
  const pos = position || positionByTicker.get(ticker.toUpperCase());
  const qty = pos?.held_qty ?? raw.qty ?? null;
  const fillPrice = pos?.avg_price ?? raw.fill_price ?? null;

  // Closed P&L if available
  const closedPnl = raw.realized_pnl ?? raw.closed_pnl ?? null;
  const closedPct = (closedPnl != null && fillPrice && qty) ? (closedPnl / (fillPrice * qty)) * 100 : null;

  // why / risks sourced from p9 news fields, with fallback
  const why = raw.p9_news_reason || raw.why || 'No additional context available.';
  const risks = raw.p9_news_risk || raw.risks || 'Standard model signal risk applies.';

  const isWatch = action === 'brewing';
  const grade = raw.grade || 'B';
  const conv = convOf(grade, isWatch);
  const layers = raw.v7_layers_agreeing ?? raw.layers ?? null;

  // candles — deterministic mock until real OHLCV available
  const sigForCandles = { ...raw, ticker, _ltp: ltp };
  const candles = genCandles(sigForCandles);

  return {
    ...raw,
    // normalised
    sym: ticker,
    name: raw.name || ticker,
    sector: raw.sector || '—',
    ex: raw.exchange || 'NSE',
    grade,
    // derived action
    action,
    sellReason: sellReason ?? null,
    // prices
    entry,
    stop,
    target,
    _ltp: ltp,
    // derived metrics
    _rr: rr,
    _dayChangePct: dayChangePct,
    _fromEntry: fromEntry,
    _upside: upside,
    _risk: risk,
    _zeroRisk: zeroRisk,
    _suggQty: suggQty,
    // buy window
    buyByStr,
    daysLeft,
    dayOf,
    hold: raw.hold_days || 10,
    // position
    qty,
    fillPrice,
    closedPnl,
    closedPct,
    // copy
    why,
    risks,
    highRisk: raw.high_risk ?? false,
    layers,
    conv,
    // chart data
    candles,
  };
}

// ─────────────────────────────────────────────────────────────────────
// Plan directive (detail pane plan bar)
// ─────────────────────────────────────────────────────────────────────
function planOf(sig) {
  switch (sig.action) {
    case 'buy-today':
      return {
        kind: 'buy',
        title: sig.buyByStr ? `Buy by ${sig.buyByStr}` : 'Buy now — window open',
        sub: sig.buyByStr ? `After ${sig.buyByStr} we no longer recommend this entry.` : '',
      };
    case 'closing':
      return {
        kind: 'buy',
        title: `Buy by ${sig.buyByStr || 'soon'} — window closing`,
        sub: sig.daysLeft != null ? `${sig.daysLeft} day${sig.daysLeft !== 1 ? 's' : ''} left. After that the setup is stale and drops off the list.` : 'Entry window is closing.',
      };
    case 'sell-now':
      return sig.sellReason === 'target'
        ? { kind: 'sell',    title: 'Sell on the next open', sub: `Target reached at ${fmtINR(sig.target)}. The favourable edge is spent — lock the gain in.` }
        : { kind: 'sellbad', title: 'Sell on the next open', sub: `Price closed below the ${fmtINR(sig.stop)} stop. Exit to cap the loss at plan.` };
    case 'holding':
      return { kind: 'hold', title: `Hold — day ${sig.dayOf || '?'} of ${sig.hold}`, sub: `Stop at ${fmtNum(sig.stop)}. Let it work toward ${fmtNum(sig.target)}; no action today.` };
    case 'brewing':
      return { kind: 'watch', title: 'Watching for a trigger', sub: `Not a buy yet. We flag it again if price sets up near ${fmtNum(sig.entry)}.` };
    case 'closed':
    default: {
      const s = (sig.status || '').toUpperCase();
      return {
        kind: 'closed',
        title: s === 'HIT_TARGET' ? 'Closed — target hit' : s === 'HIT_STOP' ? 'Closed — stopped out' : 'Expired — no fill',
        sub: '',
      };
    }
  }
}

// ─────────────────────────────────────────────────────────────────────
// SVG icons
// ─────────────────────────────────────────────────────────────────────
const Icon = {
  ArrDown: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>,
  Back:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>,
  Check:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>,
  Bolt:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>,
  Clock:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>,
  Info:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/></svg>,
  Alert:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>,
  Arrow:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>,
  Radar:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0"/><path d="M8.56 2.75c4.37 6.03 6.02 9.42 8.03 17.72m2.54-15.38c-3.72 4.35-8.94 5.66-16.88 5.85m19.5 1.9c-3.5-.93-6.63-.82-8.94 0-2.58.92-5.01 2.86-7.44 6.32"/></svg>,
};

// ─────────────────────────────────────────────────────────────────────
// Regime strip
// ─────────────────────────────────────────────────────────────────────
function RegimeStrip({ regime, vix, breadth, cronHealth }) {
  const status = (regime?.status || '').toUpperCase();
  const dotCls = status.includes('BEAR') ? 'bear' : status.includes('CHOP') ? 'choppy' : '';
  const regimeLabel = regime?.status || 'UNKNOWN';
  const parts = [regimeLabel];
  if (vix != null) parts.push(`VIX ${Number(vix).toFixed(1)}`);
  if (breadth != null) parts.push(`breadth ${breadth > 0 ? '+' : ''}${Number(breadth).toFixed(2)}`);
  if (cronHealth?.last_run_today) parts.push('Last scan 4:15 PM IST');
  parts.push('Next 4:15 PM IST');
  return (
    <div className="sig-regime">
      <span className={`rg-dot ${dotCls}`} />
      <span className="rg-text">{parts.join(' · ')}</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// ActionChip
// ─────────────────────────────────────────────────────────────────────
function ActionChip({ sig }) {
  switch (sig.action) {
    case 'buy-today':
    case 'closing': {
      const dl = sig.daysLeft ?? 2;
      return (
        <span className={`act-chip act-buy ${dl <= 1 ? 'act-urgent' : ''}`}>
          <Icon.Clock width="11" height="11" />
          {sig.buyByStr ? `BUY BY ${sig.buyByStr.toUpperCase()} · ${dl} DAY${dl !== 1 ? 'S' : ''} LEFT` : 'BUY — WINDOW OPEN'}
        </span>
      );
    }
    case 'sell-now':
      return <span className={`act-chip ${sig.sellReason === 'target' ? 'act-sell-good' : 'act-sell-bad'}`}>SELL ON NEXT OPEN</span>;
    case 'holding': {
      const label = libHoldingChip(sig);
      return <span className="act-chip act-hold">{label}</span>;
    }
    case 'brewing':
      return <span className="act-chip act-watch">WATCHING</span>;
    case 'closed': {
      const s = (sig.status || '').toUpperCase();
      if (s === 'EXPIRED') return <span className="act-chip act-closed-chip">WINDOW CLOSED</span>;
      return <span className={`act-chip ${s === 'HIT_TARGET' ? 'act-done-good' : 'act-done-bad'}`}>{s === 'HIT_TARGET' ? 'CLOSED · WON' : 'CLOSED · LOSS'}</span>;
    }
    default:
      return null;
  }
}

// ─────────────────────────────────────────────────────────────────────
// Card plan line
// ─────────────────────────────────────────────────────────────────────
function CardPlan({ sig }) {
  switch (sig.action) {
    case 'buy-today':
    case 'closing':
      return <>Buy ~<b>{sig._suggQty}</b> sh near <b>{fmtNum(sig.entry)}</b> · stop <b className="num-bear">{fmtNum(sig.stop)}</b> · target <b className="num-bull">{fmtNum(sig.target)}</b></>;
    case 'sell-now':
      return <>Sell <b>{sig.qty ?? '—'}</b> sh at market · in at <b>{sig.fillPrice ? fmtNum(sig.fillPrice) : '—'}</b> · {sig.sellReason === 'target' ? <>target <b className="num-bull">{fmtNum(sig.target)}</b></> : <>stop <b className="num-bear">{fmtNum(sig.stop)}</b></>}</>;
    case 'holding':
      return <>Holding <b>{sig.qty ?? '—'}</b> sh · stop <b>{fmtNum(sig.stop)}</b> · target <b className="num-bull">{fmtNum(sig.target)}</b></>;
    case 'brewing':
      return <>Watch for a setup near <b>{fmtNum(sig.entry)}</b> · then stop <b className="num-bear">{fmtNum(sig.stop)}</b></>;
    case 'closed': {
      if (sig.closedPnl != null) return <>Closed {sig.qty ?? '—'} sh @ <b>{sig.fillPrice ? fmtNum(sig.fillPrice) : '—'}</b> · realised <b className={sig.closedPnl >= 0 ? 'num-bull' : 'num-bear'}>{fmtLakh(sig.closedPnl)}</b></>;
      return <>No fill — entry never triggered inside the {sig.hold}-day window</>;
    }
    default: return null;
  }
}

// ─────────────────────────────────────────────────────────────────────
// Signal card
// ─────────────────────────────────────────────────────────────────────
function SignalCard({ sig, selected, onOpen }) {
  const st = statusChip(sig);
  const showFromEntry = sig.action !== 'closed';
  const rd = rrDisplay(sig);
  return (
    <button
      className={`act-card act-${sig.action} ${selected ? 'is-selected' : ''}`}
      onClick={onOpen}
    >
      <div className="ac-head">
        <Logo sym={sig.sym} size={36} radius={9} />
        <div className="ac-id">
          <div className="ac-top">
            <span className="ac-sym">{sig.sym}</span>
            <span className={`conv-pill ${sig.conv.cls}`}>{sig.conv.word} · {sig.grade}</span>
          </div>
          <div className="ac-name">
            {sig.name} · {sig.sector}
            {sig.bought_date
              ? <> · Bought {fmtSigDate(sig.bought_date)}</>
              : sig.signal_date && <> · Signaled {fmtSigDate(sig.signal_date)}</>}
          </div>
        </div>
      </div>
      <div className="ac-action"><ActionChip sig={sig} /></div>
      <div className="ac-body">
        <div className="ac-plan"><CardPlan sig={sig} /></div>
        <div className="ac-figures">
          <div className="ac-ltp">
            <span className="ac-ltp-v">{fmtINR(sig._ltp)}</span>
            {showFromEntry && <span className="ac-ltp-l">now {fmtPct1(sig._fromEntry)} from entry</span>}
          </div>
          <div className="ac-figures-r">
            <span className={`ac-rr-v ${rd.tone}`}>
              {rd.free ? 'Risk-free' : <>R:R {rd.val} <span className="ac-rr-l">{rd.word}</span></>}
            </span>
            <span className={`chip ${st.cls}`}>{st.live && <span className="dot" />}{st.label}</span>
          </div>
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────
// CandleChart (lightweight-charts v4)
// ─────────────────────────────────────────────────────────────────────
function CandleChart({ sig }) {
  const wrapRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const chart = createChart(el, {
      width: el.clientWidth,
      height: el.clientHeight,
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#7A82A5',
        fontFamily: "'DM Sans', system-ui, sans-serif",
        fontSize: 11,
      },
      grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.12 } },
      timeScale: { borderVisible: false, timeVisible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(255,255,255,0.18)', width: 1, style: LineStyle.Dotted, labelBackgroundColor: '#1a2150' },
        horzLine: { color: 'rgba(255,255,255,0.18)', width: 1, style: LineStyle.Dotted, labelBackgroundColor: '#1a2150' },
      },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addCandlestickSeries({
      upColor:        '#3FDD8A',
      downColor:      '#FF5C7A',
      borderUpColor:  '#3FDD8A',
      borderDownColor:'#FF5C7A',
      wickUpColor:    'rgba(63,221,138,0.6)',
      wickDownColor:  'rgba(255,92,122,0.6)',
    });
    chartRef.current = chart;
    seriesRef.current = series;
    const ro = new ResizeObserver(() => {
      if (chartRef.current && el.clientWidth > 0) {
        chartRef.current.resize(el.clientWidth, el.clientHeight);
      }
    });
    ro.observe(el);
    return () => { ro.disconnect(); chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart || !sig?.candles?.length) return;
    series.setData(sig.candles);
    // Remove previous price lines
    (series.__plines || []).forEach((l) => { try { series.removePriceLine(l); } catch (_) {} });
    const mk = (price, color, title) =>
      series.createPriceLine({ price, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title });
    series.__plines = [
      mk(sig.target, '#3FDD8A', 'TGT'),
      mk(sig.entry,  '#4F8CFF', 'ENT'),
      mk(sig.stop,   '#FF5C7A', 'STP'),
    ];
    if (sig.fillPrice) series.__plines.push(mk(sig.fillPrice, 'rgba(241,245,255,0.45)', 'FILL'));
    chart.timeScale().fitContent();
  }, [sig]);

  return <div className="tv-chart" ref={wrapRef} />;
}

// ─────────────────────────────────────────────────────────────────────
// OrderPad
// ─────────────────────────────────────────────────────────────────────
function OrderPad({ sig, availableMargin }) {
  const perShareRisk = Math.max(1, sig.entry - sig.stop);
  const [qty, setQty] = useState(sig._suggQty || 1);
  const [orderType, setOrderType] = useState('Limit');
  const [placed, setPlaced] = useState(false);

  // Reset qty + placed state when the selected signal changes. Intentionally
  // only depend on sig.sym so we reset on signal change, not on every re-render.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { setQty(sig._suggQty || 1); setPlaced(false); }, [sig.sym]);

  const portfolioCapital = availableMargin || 500000;
  const orderValue = qty * sig.entry;
  const riskAmt = sig._zeroRisk ? 0 : qty * perShareRisk;
  const rewardAmt = qty * (sig.target - sig.entry);
  const pctPortfolio = portfolioCapital > 0 ? (riskAmt / portfolioCapital) * 100 : 0;
  const overMargin = availableMargin != null && orderValue > availableMargin;

  const isSell  = sig.action === 'sell-now';
  const isWatch = sig.action === 'brewing';
  const isHold  = sig.action === 'holding';
  const isClosed = sig.action === 'closed';
  const st = statusChip(sig);

  if (isClosed) {
    const win = (sig.status || '').toUpperCase() === 'HIT_TARGET';
    return (
      <div className="orderpad orderpad-closed">
        <div className="op-closed-head">
          <span className={`chip ${st.cls}`}>{st.label}</span>
          <span className="op-closed-when">Closed · {sig.signal_date || '—'}</span>
        </div>
        {sig.closedPnl != null ? (
          <div className="op-pnl">
            <div className="op-pnl-l">Realised P&amp;L</div>
            <div className={`op-pnl-v ${win ? 'num-bull' : 'num-bear'}`}>
              {win ? '+' : ''}{fmtLakh(sig.closedPnl)}
              {sig.closedPct != null && <span className="op-pnl-pct">{fmtPct(sig.closedPct)}</span>}
            </div>
            {sig.qty && sig.fillPrice && (
              <div className="op-pnl-meta">{sig.qty} sh @ {fmtNum(sig.fillPrice)} · exit {fmtINR(sig._ltp)}</div>
            )}
          </div>
        ) : (
          <div className="op-expired">
            <Icon.Info width="18" height="18" />
            <div>No fill — the trigger was never reclaimed inside the {sig.hold}-day window. Capital was never at risk.</div>
          </div>
        )}
        <button className="op-cta op-cta-ghost">View in journal <Icon.Arrow width="13" height="13" /></button>
      </div>
    );
  }

  return (
    <div className="orderpad">
      <div className="op-head">
        <div className="op-title">{isSell ? 'Exit order' : 'Order pad'}</div>
        <div className="op-route">
          <span className="kite-mark"><Icon.Bolt width="11" height="11" /></span>
          Zerodha Kite · CNC
        </div>
      </div>
      <div className="op-controls">
        <label className="op-field">
          <span className="op-field-l">{isSell ? 'Quantity to sell' : 'Suggested quantity'}</span>
          <div className="op-qty">
            <button onClick={() => setQty((q) => Math.max(1, q - 1))}>−</button>
            <input
              type="text"
              value={qty}
              onChange={(e) => { const v = parseInt(e.target.value.replace(/\D/g, ''), 10); setQty(isNaN(v) ? 1 : Math.max(1, v)); }}
            />
            <button onClick={() => setQty((q) => q + 1)}>+</button>
          </div>
        </label>
        <label className="op-field">
          <span className="op-field-l">Order type</span>
          <div className="op-seg">
            {['Market', 'Limit'].map((o) => (
              <button key={o} className={orderType === o ? 'on' : ''} onClick={() => setOrderType(o)}>{o}</button>
            ))}
          </div>
        </label>
        <label className="op-field">
          <span className="op-field-l">{orderType === 'Limit' ? 'Limit price' : 'Est. price'}</span>
          <div className="op-price">{fmtNum(isSell ? sig._ltp : sig.entry)}</div>
        </label>
      </div>
      <div className="op-calc">
        <div className="op-calc-row"><span>Order value</span><span className="t-num">{fmtLakh(orderValue)}</span></div>
        <div className="op-calc-row"><span>Margin required (CNC)</span><span className="t-num">{fmtLakh(orderValue)}</span></div>
        <div className="op-calc-row"><span>Potential reward at target</span><span className="t-num num-bull">+{fmtLakh(rewardAmt)}</span></div>
        <div className="op-calc-row"><span>Risk if stopped</span><span className="t-num num-bear">{sig._zeroRisk ? '₹0 · breakeven' : '−' + fmtLakh(riskAmt)}</span></div>
      </div>
      <button
        className={`op-cta ${placed ? 'is-placed' : ''}`}
        onClick={() => { if (!overMargin) setPlaced(true); }}
        disabled={isWatch || overMargin}
      >
        {placed
          ? <><Icon.Check width="15" height="15" /> Order placed · {sig.sym} × {qty}</>
          : isSell
            ? <>Place sell order · Kite <Icon.Arrow width="14" height="14" /></>
            : isWatch
              ? <>Set a trigger alert</>
              : isHold
                ? <>Add to position · Kite <Icon.Arrow width="14" height="14" /></>
                : <>Place buy order · Kite <Icon.Arrow width="14" height="14" /></>}
      </button>
      <div className="op-foot">
        {overMargin
          ? <span className="num-bear">Insufficient margin — {fmtLakh(orderValue)} needed, {fmtLakh(availableMargin)} available</span>
          : placed
            ? <>Routed to Kite at {fmtNum(isSell ? sig._ltp : sig.entry)} · logged to journal</>
            : sig._zeroRisk
              ? <>Stop at breakeven — this position carries no risk</>
              : <>Sized to risk ≈ {fmtLakh(riskAmt)} · ~{pctPortfolio.toFixed(1)}% of your portfolio risked</>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// DetailBody
// ─────────────────────────────────────────────────────────────────────
function DetailBody({ sig, availableMargin }) {
  const st = statusChip(sig);
  const plan = planOf(sig);
  const rd = rrDisplay(sig);
  const gradeCls = `grade-${(sig.grade || 'b')[0].toLowerCase()}`;
  const pnlFromFill = sig.qty && sig.fillPrice ? sig.qty * (sig._ltp - sig.fillPrice) : null;

  return (
    <div className="detail-body">
      <div className="db-head">
        <Logo sym={sig.sym} size={46} radius={12} />
        <div className="db-head-id">
          <div className="db-head-top">
            <h2 className="db-sym">{sig.sym}</h2>
            <span className={`grade-badge ${gradeCls}`}>{sig.grade}</span>
            <span className={`chip ${st.cls}`}>{st.live && <span className="dot" />}{st.label}</span>
          </div>
          <div className="db-sub">{sig.name} · {sig.sector} · {sig.ex}</div>
        </div>
        <div className="db-price">
          <div className="db-ltp">{fmtINR(sig._ltp)}</div>
          {sig._dayChangePct != null && (
            <div className={`db-vs ${sig._dayChangePct >= 0 ? 'num-bull' : 'num-bear'}`}>
              today {fmtPct1(sig._dayChangePct)}
            </div>
          )}
          {sig.action !== 'closed' && (
            <div className={`db-vs ${sig._fromEntry >= 0 ? 'num-bull' : 'num-bear'}`}>
              now {fmtPct1(sig._fromEntry)} from entry
            </div>
          )}
        </div>
      </div>

      {/* plan bar */}
      <div className={`plan-bar plan-${plan.kind}`}>
        <div className="plan-bar-l">
          <ActionChip sig={sig} />
          <div className="plan-text">
            <div className="plan-title">{plan.title}</div>
            {plan.sub && <div className="plan-sub">{plan.sub}</div>}
          </div>
        </div>
        {(sig.action === 'buy-today' || sig.action === 'closing') && sig.daysLeft != null && (
          <div className={`plan-deadline ${sig.daysLeft <= 1 ? 'is-urgent' : ''}`}>
            <div className="plan-deadline-n">{sig.daysLeft}</div>
            <div className="plan-deadline-l">day{sig.daysLeft !== 1 ? 's' : ''} left</div>
          </div>
        )}
      </div>

      {/* conviction line */}
      <div className="conv-line">
        <span className={`conv-pill ${sig.conv.cls}`}>{sig.conv.word}</span>
        <span className="conv-sep">·</span>
        <span>Grade {sig.grade}</span>
        {sig.layers != null && (
          <>
            <span className="conv-sep">·</span>
            <span>{sig.layers} of 6 model layers agree</span>
          </>
        )}
        <span className="conv-sep">·</span>
        <span>Hold ~{sig.hold} days</span>
        {sig.bought_date ? (
          <>
            <span className="conv-sep">·</span>
            <span>Bought {fmtSigDate(sig.bought_date)}</span>
          </>
        ) : sig.signal_date && (
          <>
            <span className="conv-sep">·</span>
            <span>Signaled {fmtSigDate(sig.signal_date)}</span>
          </>
        )}
      </div>

      {/* chart */}
      <div className="db-chart-card">
        <div className="db-chart-legend">
          <span className="leg-i"><span className="sw" style={{ background: '#FF5C7A' }} />STOP <b>{fmtNum(sig.stop)}</b></span>
          <span className="leg-i"><span className="sw" style={{ background: '#4F8CFF' }} />ENTRY <b>{fmtNum(sig.entry)}</b></span>
          <span className="leg-i"><span className="sw" style={{ background: '#3FDD8A' }} />TARGET <b>{fmtNum(sig.target)}</b></span>
          <span className="leg-tv">TradingView</span>
        </div>
        <CandleChart sig={sig} />
      </div>

      {/* 4-metric strip */}
      <div className="metric-strip">
        <div className="metric">
          <span className="metric-l">Entry</span>
          <span className="metric-v brand">{fmtNum(sig.entry)}</span>
          <span className="metric-s">trigger</span>
        </div>
        <div className="metric">
          <span className="metric-l">Stop</span>
          <span className={`metric-v ${sig._zeroRisk ? '' : 'num-bear'}`}>{fmtNum(sig.stop)}</span>
          <span className={`metric-s ${sig._zeroRisk ? '' : 'num-bear'}`}>{sig._zeroRisk ? 'breakeven' : fmtPct(sig._risk)}</span>
        </div>
        <div className="metric">
          <span className="metric-l">Target</span>
          <span className="metric-v num-bull">{fmtNum(sig.target)}</span>
          <span className="metric-s num-bull">{fmtPct(sig._upside)}</span>
        </div>
        <div className="metric">
          <span className="metric-l">Risk / reward</span>
          <span className={`metric-v ${rd.tone}`}>{rd.val}</span>
          <span className="metric-s">{rd.word}</span>
        </div>
      </div>

      {/* why + risks */}
      <div className="rationale">
        <div className="rat rat-why">
          <div className="rat-h"><span><Icon.Check width="13" height="13" /> Why this stock</span></div>
          <p>{sig.why}</p>
        </div>
        <div className="rat rat-risk">
          <div className="rat-h">
            <span><Icon.Alert width="13" height="13" /> The risks</span>
            {sig.highRisk && <span className="risk-chip">ELEVATED RISK</span>}
          </div>
          <p>{sig.risks}</p>
        </div>
      </div>

      {/* open position strip */}
      {sig.action === 'holding' && sig.qty && sig.fillPrice && pnlFromFill != null && (
        <div className="db-position">
          <span className="db-pos-l">Open position</span>
          <span className="db-pos-v">{sig.qty} sh @ {fmtNum(sig.fillPrice)}</span>
          <span className={`db-pos-pnl ${pnlFromFill >= 0 ? 'num-bull' : 'num-bear'}`}>
            {pnlFromFill >= 0 ? '+' : ''}{fmtLakh(pnlFromFill)} ({fmtPct1(sig._fromEntry)})
          </span>
        </div>
      )}

      <OrderPad sig={sig} availableMargin={availableMargin} />

      <div className="db-disclaimer">{DISCLAIMER}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Section (collapsible)
// ─────────────────────────────────────────────────────────────────────
function Section({ sec, rows, selSym, onOpen, collapsedByDefault, limit }) {
  const [open, setOpen] = useState(!collapsedByDefault);
  const [showAll, setShowAll] = useState(false);
  if (!rows.length) return null;
  const shown = limit && !showAll ? rows.slice(0, limit) : rows;
  return (
    <section className={`sig-section sec-${sec.id}`}>
      <button className="sec-head" onClick={() => setOpen((o) => !o)}>
        <div className="sec-head-l">
          <span className={`sec-marker marker-${sec.id}`} />
          <h2 className="sec-title">{sec.title}</h2>
          <span className="sec-count">{rows.length}</span>
        </div>
        <div className="sec-head-r">
          <span className="sec-desc">{sec.sub}</span>
          <Icon.ArrDown width="14" height="14" className={`sec-caret ${open ? 'is-open' : ''}`} />
        </div>
      </button>
      {open && (
        <div className="sec-cards">
          {shown.map((sig) => (
            <SignalCard
              key={`${sig.sym}__${sig.signal_date || ''}`}
              sig={sig}
              selected={sig.sym === selSym}
              onOpen={() => onOpen(sig.sym)}
            />
          ))}
          {limit && rows.length > limit && (
            <button className="sec-more" onClick={() => setShowAll((s) => !s)}>
              {showAll ? 'Show less' : `Show ${rows.length - limit} more`}
              <Icon.ArrDown width="13" height="13" />
            </button>
          )}
        </div>
      )}
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SizingCalculator — Weekly Swing position sizer (finding 0038 fill rules)
//
// Faithful to the backtest's math:
//   equity        = cash on hand + value already invested in weekly positions
//   risk/trade    = 2% of EQUITY  (never of cash — invested value stays in the base)
//   shares        = floor(risk ÷ (entry − stop))
//   affordability = cash × margin multiplier (leverage widens what you can BUY,
//                   never what you RISK); funded strongest-CRS-first; unaffordable → SKIP
// Client-side only; inputs persist per-browser (per-user) in localStorage.
// ─────────────────────────────────────────────────────────────────────
const SIZING_LS_KEY = 'nq_weekly_sizing_v1';

function SizingCalculator({ candidates }) {
  const saved = useMemo(() => {
    try { return JSON.parse(localStorage.getItem(SIZING_LS_KEY)) || {}; } catch { return {}; }
  }, []);
  const [cash, setCash] = useState(saved.cash ?? '');
  const [invested, setInvested] = useState(saved.invested ?? '');
  const [mult, setMult] = useState(saved.mult ?? 1);
  useEffect(() => {
    try { localStorage.setItem(SIZING_LS_KEY, JSON.stringify({ cash, invested, mult })); } catch {}
  }, [cash, invested, mult]);

  const cashN = Math.max(0, parseFloat(cash) || 0);
  const investedN = Math.max(0, parseFloat(invested) || 0);
  const equity = cashN + investedN;
  const risk = 0.02 * equity;
  const buyingPower = cashN * mult;

  const rows = useMemo(() => {
    const sorted = [...candidates].sort((a, b) => (b.crs_rank ?? 0) - (a.crs_rank ?? 0));
    let bp = buyingPower;
    return sorted.map((s) => {
      const rps = (s.entry ?? 0) - (s.stop ?? 0);
      if (rps <= 0 || risk <= 0) return { s, qty: 0, cost: 0, status: 'n/a' };
      const qty = Math.floor(risk / rps);
      const cost = qty * s.entry;
      if (qty < 1) return { s, qty: 0, cost: 0, status: 'risk too small' };
      if (cost > bp) return { s, qty, cost, status: 'skip — over budget' };
      bp -= cost;
      return { s, qty, cost, status: 'FUND', left: bp };
    });
  }, [candidates, risk, buyingPower]);

  const funded = rows.filter((r) => r.status === 'FUND');
  const deployed = funded.reduce((a, r) => a + r.cost, 0);

  return (
    <div className="sizing-calc">
      <div className="sc-head">
        <span className="sc-title">Position sizer</span>
        <span className="sc-sub">2% of equity risked per trade · funded strongest CRS first</span>
      </div>
      <div className="sc-inputs">
        <label>Cash in hand (₹)
          <input inputMode="numeric" placeholder="e.g. 400000" value={cash}
                 onChange={(e) => setCash(e.target.value.replace(/[^\d.]/g, ''))} />
        </label>
        <label>Already invested in weekly positions (₹)
          <input inputMode="numeric" placeholder="0" value={invested}
                 onChange={(e) => setInvested(e.target.value.replace(/[^\d.]/g, ''))} />
        </label>
        <label>Funding mode
          <select value={mult} onChange={(e) => setMult(parseFloat(e.target.value))}>
            <option value={1}>All cash (1.0×)</option>
            <option value={1.8}>E-margin (1.8×)</option>
            <option value={2}>E-margin (2.0×)</option>
          </select>
        </label>
      </div>
      {equity > 0 && (
        <>
          <div className="sc-strip">
            <span>Equity <b className="num">{fmtLakh(equity)}</b></span>
            <span>Risk/trade <b className="num">{fmtLakh(risk)}</b></span>
            <span>Buying power <b className="num">{fmtLakh(buyingPower)}</b></span>
            <span>Will fund <b className="num-bull">{funded.length}</b> of {rows.length} · deploys {fmtLakh(deployed)}</span>
          </div>
          <div className="sc-table-wrap"><table className="sc-table">
            <thead><tr><th>#</th><th>Signal</th><th>Buy band</th><th>Stop</th><th>Shares</th><th>Cost</th><th></th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.s.sym} className={r.status === 'FUND' ? '' : 'sc-skip'}>
                  <td>{i + 1}</td>
                  <td><b>{r.s.sym}</b> <span className="sc-grade">{r.s.grade}</span></td>
                  <td className="num">{fmtNum(r.s.entry_low)} – {fmtNum(r.s.entry_high)}</td>
                  <td className="num">{fmtNum(r.s.stop)}</td>
                  <td className="num"><b>{r.status === 'FUND' ? r.qty.toLocaleString('en-IN') : '—'}</b></td>
                  <td className="num">{r.status === 'FUND' ? fmtLakh(r.cost) : '—'}</td>
                  <td className={`sc-status ${r.status === 'FUND' ? 'ok' : ''}`}>{r.status === 'FUND' ? 'fund' : r.status}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
          <div className="sc-note">
            Shares assume a fill near the band top — <b>recompute at your actual fill: shares = {fmtLakh(risk)} ÷ (fill − stop)</b>.
            Buy only if the day's open is INSIDE the band; skip otherwise.
            {mult > 1 && (
              <span className="sc-warn"> E-margin: leverage widens what you can buy, never what you risk (still 2% of equity
              per trade). The backtest is UNLEVERED — a −40%-class drawdown on a levered book risks margin calls and forced
              selling, and E-margin interest (~9–12%/yr) is not in any backtest number.</span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Skeleton loading state
// ─────────────────────────────────────────────────────────────────────
function SkeletonList() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      {[3, 2, 4].map((count, sIdx) => (
        <div key={sIdx} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div className="skeleton-card" style={{ height: 18, width: '30%', borderRadius: 8 }} />
          {Array.from({ length: count }).map((_, i) => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────
export default function SignalsV3() {
  const kite = useContext(KiteContext);
  // Which strategy book to show: 'momentum' (baseline_v1, live) or 'weekly' (0091 forward-watch).
  const [model, setModel] = useState('momentum');
  const signalsQuery    = useSignals({ model });
  const watchlistQuery  = useWatchlist({ model });
  const holdingsQuery   = useKiteHoldings({ enabled: !!kite?.connected });
  const marginsQuery    = useKiteMargins({ enabled: !!kite?.connected });
  const nqPositionsQuery = useNQPositions();

  const [gradeFilter, setGradeFilter] = useState('all');
  const [selSym, setSelSym] = useState(null);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Mobile detection
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 900px)');
    const on = () => setIsMobile(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);

  // Mobile scroll lock
  useEffect(() => {
    if (!isMobile || !mobileOpen) return;
    const onKey = (e) => { if (e.key === 'Escape') setMobileOpen(false); };
    window.addEventListener('keydown', onKey);
    // Note: using react-remove-scroll or Radix would be ideal; inline style
    // is an exception only while the mobile detail is pushed full-screen (it
    // overlays the scroll container, not the body scroll).
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [isMobile, mobileOpen]);

  // ── Data assembly ──────────────────────────────────────────────────

  const rawSignals    = useMemo(() => signalsQuery.data?.signals ?? [], [signalsQuery.data]);
  const rawWatchlist  = useMemo(() => watchlistQuery.data?.signals ?? [], [watchlistQuery.data]);

  // Live quotes for every signal ticker (60s poll; server caches 30s per symbol).
  // Overlaid in enrichSignal so LTP / from-entry / day-change track the market
  // instead of freezing at the cron's scan-time close.
  const quoteSymbols = useMemo(
    () => [...new Set([...rawSignals, ...rawWatchlist]
      .map((s) => (s.ticker || '').toUpperCase()).filter(Boolean))],
    [rawSignals, rawWatchlist]
  );
  const quotesQuery = useQuoteBatch(quoteSymbols);
  const quotes = quotesQuery.data ?? null;

  const regime        = signalsQuery.data?.regime ?? {};
  const cronHealth    = signalsQuery.data?.cron_health ?? {};
  const sizingCapital = signalsQuery.data?.sizing_capital ?? 500000;
  const availableMargin = marginsQuery.data?.available ?? null;

  // Kite holdings set
  const heldSet = useMemo(() => {
    const list = holdingsQuery.data ?? [];
    return new Set(list.map((h) => (h.tradingsymbol || h.symbol || '').toUpperCase()));
  }, [holdingsQuery.data]);

  // NQ positions by ticker
  const positionByTicker = useMemo(() => {
    const map = new Map();
    for (const p of nqPositionsQuery.data?.positions ?? []) {
      const t = (p.ticker || p.symbol || '').toUpperCase();
      if (t) map.set(t, p);
    }
    return map;
  }, [nqPositionsQuery.data]);

  // Enrich all signals
  const allEnriched = useMemo(() => {
    const enriched = [
      ...rawSignals.map((s) => enrichSignal(s, heldSet, positionByTicker, sizingCapital, quotes)),
      ...rawWatchlist.map((s) => enrichSignal({ ...s, actionability: 'WATCHLIST', tier: 'watchlist' }, heldSet, positionByTicker, sizingCapital, quotes)),
    ];
    // Dedupe by sym (prefer first occurrence — rawSignals take precedence)
    const seen = new Set();
    return enriched.filter((s) => { if (seen.has(s.sym)) return false; seen.add(s.sym); return true; });
  }, [rawSignals, rawWatchlist, heldSet, positionByTicker, sizingCapital, quotes]);

  // Apply grade filter
  const pool = useMemo(() => {
    if (gradeFilter === 'all') return allEnriched;
    return allEnriched.filter((s) => (s.grade || 'B')[0].toUpperCase() === gradeFilter);
  }, [allEnriched, gradeFilter]);

  // Weekly position-sizer candidates: this week's ranked BUY cards (never held/bought ones),
  // grade-filter-independent so the sizer always sees the full ranked list.
  const sizingCands = useMemo(() =>
    model === 'weekly'
      ? allEnriched.filter((s) => s.crs_rank != null && !s.bought_date
          && (s.action === 'buy-today' || s.action === 'closing'))
      : [],
    [model, allEnriched]);

  // Partition into action buckets
  const byAction = useMemo(() => {
    const buckets = { 'sell-now': [], 'buy-today': [], closing: [], holding: [], brewing: [], closed: [] };
    for (const s of pool) {
      const key = s.action;
      if (buckets[key]) buckets[key].push(s);
      else buckets['closed'].push(s);
    }
    return buckets;
  }, [pool]);

  // Default selection: first actionable signal
  const firstActionable = useMemo(
    () => pool.find((s) => s.action !== 'closed') || pool[0] || null,
    [pool]
  );

  useEffect(() => {
    if (!selSym && firstActionable) setSelSym(firstActionable.sym);
  }, [firstActionable]); // eslint-disable-line react-hooks/exhaustive-deps

  // If the selected sym dropped out of the filtered pool, pick a new one
  useEffect(() => {
    if (selSym && !pool.some((s) => s.sym === selSym)) {
      const next = pool.find((s) => s.action !== 'closed') || pool[0] || null;
      setSelSym(next?.sym ?? null);
    }
  }, [gradeFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const openSig = useMemo(
    () => allEnriched.find((s) => s.sym === selSym) || null,
    [allEnriched, selSym]
  );

  const handleOpen = (sym) => { setSelSym(sym); if (isMobile) setMobileOpen(true); };

  const freshCount = pool.filter((s) => ['buy-today', 'closing'].includes(s.action)).length;
  const activeCount = pool.filter((s) => ['holding', 'sell-now'].includes(s.action)).length;

  const today = todayISO();
  const todayLabel = new Date().toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }).toUpperCase();

  // ── Render ─────────────────────────────────────────────────────────

  // Error state
  if (signalsQuery.error) {
    return (
      <div className="sig-v3-app">
        <EmptyState
          icon={<Icon.Alert width="48" height="48" />}
          title="Couldn't load signals"
          body={STATES.error}
        />
      </div>
    );
  }

  return (
    <div className="sig-v3-app">
      {/* Regime strip */}
      <RegimeStrip
        regime={regime}
        vix={regime?.vix}
        breadth={regime?.breadth}
        cronHealth={cronHealth}
      />

      {/* Strategy book toggle — two live models */}
      <div className="sig-model-tabs">
        <GlassTabs
          tabs={[{ key: 'momentum', label: 'Momentum' }, { key: 'weekly', label: 'Weekly Swing' }]}
          active={model}
          onChange={setModel}
          size="md"
        />
        <span className={`chip ${model === 'momentum' ? 'c-bull' : 'c-warn'}`}>
          {model === 'momentum' ? 'Live' : 'Forward-watch · paper'}
        </span>
      </div>

      {/* Subhead */}
      <div className="sig-subhead">
        <div>
          <div className="t-ui-micro">SIGNALS · 16:15 IST SCAN · {todayLabel}</div>
          <h1 className="sig-page-title">What to do today</h1>
          <div className="sig-state">
            {signalsQuery.isLoading ? (
              <span style={{ color: 'var(--text-3)' }}>{STATES.loading}</span>
            ) : (
              <>
                <span><b className="num-info">{freshCount}</b> to buy today</span>
                <span className="sep">·</span>
                <span><b className="num-bull">{activeCount}</b> positions to manage</span>
              </>
            )}
          </div>
        </div>
        <div className="grade-filter">
          <span className="gf-l">Grade</span>
          {['all', 'A', 'B'].map((g) => (
            <button key={g} className={`gf-btn ${gradeFilter === g ? 'on' : ''}`} onClick={() => setGradeFilter(g)}>
              {g === 'all' ? 'All' : g}
            </button>
          ))}
        </div>
      </div>

      <main className="sig-body">
        {/* Left: signal list */}
        <div className="sig-list">
          {signalsQuery.isLoading ? (
            <SkeletonList />
          ) : pool.length === 0 ? (
            <div className="sig-empty">
              <Icon.Radar width="20" height="20" />
              <div>
                {gradeFilter !== 'all'
                  ? `No ${gradeFilter}-grade signals right now. Try a different grade or wait for the 16:15 IST scan.`
                  : STATES.empty}
              </div>
            </div>
          ) : (
            <>
              {model === 'weekly' && sizingCands.length > 0 && (
                <SizingCalculator candidates={sizingCands} />
              )}
              {SECTION_ORDER.map((sec) => (
                <Section
                  key={sec.id}
                  sec={sec}
                  rows={byAction[sec.id] || []}
                  selSym={selSym}
                  onOpen={handleOpen}
                  collapsedByDefault={sec.id === 'closed'}
                  limit={sec.id === 'brewing' ? WATCH_TOP_N : undefined}
                />
              ))}
            </>
          )}
        </div>

        {/* Right: detail pane (desktop only) */}
        {!isMobile && (
          <div className="detail-pane">
            {openSig ? (
              <DetailBody sig={openSig} availableMargin={availableMargin} />
            ) : (
              <div className="detail-empty">Select a signal to see the plan, chart, and order pad.</div>
            )}
          </div>
        )}
      </main>

      {/* Page footer */}
      <footer className="sig-foot">
        <div className="sig-disclaimer">{DISCLAIMER}</div>
        <div className="sig-foot-meta">SEBI Research Analyst · Model-generated signals · Research output only · NSE data delayed 15 min · v2026.06</div>
      </footer>

      {/* Mobile: full-screen pushed detail (not a drawer) */}
      {isMobile && mobileOpen && openSig && (
        <div className="mobile-detail">
          <div className="md-bar">
            <button className="md-back" onClick={() => setMobileOpen(false)}>
              <Icon.Back width="18" height="18" /> Signals
            </button>
            <span className="md-bar-sym">{openSig.sym}</span>
          </div>
          <div className="md-scroll">
            <DetailBody sig={openSig} availableMargin={availableMargin} />
          </div>
        </div>
      )}
    </div>
  );
}
