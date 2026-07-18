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
 *   - useSignals()       → the MODEL's book: open/hold/exit signals + regime + cron_health
 *   - useWatchlist()     → brewing/watchlist signals
 *   - useQuoteBatch()    → live LTP / day-change overlay
 *   (Kite / personal-position mapping removed 2026-07-13 — this page is model-centric.)
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
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { GlassTabs } from '@/components/shared/GlassTabs';
import { CONVICTION, DISCLAIMER, STATES, DISCIPLINE, LESSONS } from '@/lib/signalCopy';
import { EmptyState } from '@/components/shared/EmptyState';
import TradeCardModal from '@/components/shared/TradeCardModal';
import ExecutionCaptureModal from '@/components/shared/ExecutionCaptureModal';
import DisciplineCard from '@/components/shared/DisciplineCard';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { sizePortfolio, SIZER_STATUS } from '@/lib/sizing';
import { useHoldings, useMarkBought, useUnmarkBought } from '@/hooks/queries/useHoldings';
import { useJourney } from '@/hooks/queries/useJourney';
import { useSizerConfig, useSizingPrefs, useUpdateSizingPrefs } from '@/hooks/queries/useSizingPrefs';
import '@/styles/signals-v3.css';
import '@/styles/research-insights.css';

// signal_id = "{TICKER}__{signal_date}" — the shared canonical key the per-user
// ephemeral-holdings layer binds a "bought" mark to (matches NQOrder.signal_id).
const signalIdOf = (s) => {
  const t = String(s?.sym || s?.ticker || '').toUpperCase();
  return s?.signal_id || (t && s?.signal_date ? `${t}__${s.signal_date}` : null);
};

// ── Formatters ────────────────────────────────────────────────────────
const fmtNum  = (n) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtNum0 = (n) => n == null ? '—' : Math.round(Number(n)).toLocaleString('en-IN');
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

// ── Action derivation (deterministic, MODEL-centric) ──────────────────
// open/hold/exit are read from the signal envelope written by the paper-book cron — no Kite / no
// personal positions. EXIT = the model says close it; HOLD = the model holds it; the rest is OPEN.
function deriveAction(sig) {
  const status = (sig.status || '').toUpperCase();
  const actionability = (sig.actionability || '').toUpperCase();

  // EXIT — a held position the model has flagged to close (weekly close hit target/stop/trail/cap).
  if (actionability === 'EXIT_REQUIRED' || status === 'HIT_TARGET' || status === 'HIT_STOP' || status === 'EXPIRED') {
    return { action: 'sell-now', sellReason: status === 'HIT_TARGET' ? 'target' : 'stop' };
  }
  // HOLD — the model holds this position (bought, still active), no action this week.
  if (sig.bought_date || (status === 'ACTIVE' && sig.nq_position_id)) {
    return { action: 'holding' };
  }
  // OPEN — a fresh buy signal, buyable inside its window.
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
  if (actionability === 'BUY_CLOSED' || ['CLOSED', 'RESOLVED', 'CANCELLED'].includes(status)) return { action: 'closed' };
  if (actionability === 'WATCHLIST' || sig.tier === 'watchlist') return { action: 'brewing' };
  if (status === 'ACTIVE') return { action: 'closing' };
  return { action: 'closed' };
}

// ── Signal enrichment — maps real API fields to UI fields ─────────────
function enrichSignal(raw, quotes) {
  const { action, sellReason } = deriveAction(raw);
  const ticker = raw.ticker || raw.sym || '';
  const q = quotes?.[ticker.toUpperCase()] || null;
  const ltp = q?.last_price ?? raw.current_price ?? raw.last_price ?? raw.close ?? raw.entry ?? 0;
  const dayChangePct = q?.change_pct ?? null;
  const entry = raw.entry ?? 0;
  const stop = raw.stop ?? entry;
  const target = raw.target ?? entry;
  // Buy range = the signal week's candle [low, high]; you buy inside this band at the open.
  const buyLow = raw.entry_low ?? entry;
  const buyHigh = raw.entry_high ?? entry;
  const buyMid = ((buyLow + buyHigh) / 2) || entry;
  const rr = entry !== stop ? (target - entry) / (entry - stop) : Infinity;
  const fromEntry = entry > 0 ? ((ltp - entry) / entry) * 100 : 0;
  const upside = entry > 0 ? ((target - entry) / entry) * 100 : 0;
  // Potential return = % to the +2R target from the MIDDLE of the buy range (fill-dependent).
  const toTarget = buyMid > 0 ? ((target - buyMid) / buyMid) * 100 : upside;
  const zeroRisk = entry === stop;

  let buyByStr = null, daysLeft = null;
  if (raw.buy_window_until) {
    const d = new Date(raw.buy_window_until);
    buyByStr = fmtBuyBy(d); daysLeft = daysLeftUntil(d);
  } else if (raw.signal_date && (action === 'buy-today' || action === 'closing')) {
    const d = addTradingDays(raw.signal_date, 2);
    buyByStr = fmtBuyBy(d); daysLeft = daysLeftUntil(d);
  }

  let dayOf = null, weekOf = null;
  if (raw.signal_date && action === 'holding') {
    const calDays = Math.max(1, Math.round((Date.now() - new Date(raw.signal_date)) / 86400000));
    dayOf = Math.min(calDays, raw.hold_days || calDays);
    // The book's cap is 13 WEEKS; dayOf above is calendar days (unit mismatch, fault F9), so express
    // hold progress in weeks against the real 13-week cap.
    weekOf = Math.min(13, Math.max(1, Math.ceil(calDays / 7)));
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
    _buyLow: buyLow, _buyHigh: buyHigh, _toTarget: toTarget,
    _ltp: ltp,
    _rr: rr,
    _dayChangePct: dayChangePct,
    _fromEntry: fromEntry,
    _upside: upside,
    _zeroRisk: zeroRisk,
    _signalId: signalIdOf({ sym: ticker, signal_date: raw.signal_date, signal_id: raw.signal_id }),
    buyByStr, daysLeft, dayOf, weekOf,
    hold: raw.hold_days || 10,
    conv: convOf(grade, isWatch),
    isFreshToday: raw.signal_date === todayISO(),
  };
}

// ── Row helpers ───────────────────────────────────────────────────────
// Display order: actionable first, closed last.
const ACTION_RANK = { 'sell-now': 0, 'buy-today': 1, closing: 2, holding: 3, brewing: 4, closed: 5 };

// Research-only (2026-07-13): no in-app order pad. Every action opens the stock's
// levels/chart page (/stock/:sym); the user places the order on their broker.
function rowAction(s) {
  switch (s.action) {
    case 'buy-today':
    case 'closing':  return { label: 'Levels', cls: 'buy',   suffix: '' };
    case 'sell-now': return { label: 'Levels', cls: 'sell',  suffix: '' };
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
    // A held trade counts days UP from entry toward the ~13-week (65d) exit.
    return { main: fmtPct1(s._fromEntry), sub: s.weekOf ? `week ${s.weekOf} of 13` : '', tone: s._fromEntry >= 0 ? 'bull' : 'bear' };
  }
  if (s.action === 'closed') {
    // Buy window elapsed and it was never bought — not a live trade, so no day count.
    return { main: '—', sub: 'buy window closed', tone: 'warn' };
  }
  // OPEN buy: potential return = % to the +2R target (from the middle of the buy range).
  return { main: fmtPct1(s._toTarget), sub: `to target ${fmtNum(s.target)}`, tone: 'bull' };
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
  // No status yet = NOT LOADED, which is not the same as "choppy". Previously an empty regime fell
  // through to a definitive "The market is Choppy. Mixed tape — stay selective." while breadth and
  // VIX both still rendered "—" — an authoritative market call generated from no data.
  if (!rs) return { known: false, label: null, tone: 'muted', line: '' };
  if (rs.includes('BULL')) return { known: true, label: 'Bullish', tone: 'bull', line: 'Trend and breadth favour longs.' };
  if (rs.includes('BEAR')) return { known: true, label: 'Bearish', tone: 'bear', line: 'Defensive — trend and breadth are against longs.' };
  return { known: true, label: 'Choppy', tone: 'warn', line: 'Mixed tape — no clear trend. Stay selective.' };
}

// ── Right-rail cards ──────────────────────────────────────────────────
function CommentaryCard({ regime, model, freshCount }) {
  const r = regimeInfo(regime);
  const vix = regime?.vix != null ? Number(regime.vix).toFixed(1) : '—';
  const breadth = regime?.breadth != null ? (regime.breadth > 0 ? `+${regime.breadth}` : `${regime.breadth}`) : '—';
  const book = 'weekly-swing';
  return (
    <div className="ri-card">
      <div className="ri-card-h">MARKET NOW</div>
      <div className="ri-comm-title" aria-live="polite">
        {r.known
          ? <>The market is <span className={`num-${r.tone}`}>{r.label}.</span> {r.line}</>
          : <span style={{ color: 'var(--text-3)' }}>Reading today&rsquo;s market&hellip;</span>}
      </div>
      {r.known && (
        <div className="ri-comm-body">
          Breadth {breadth} adv–dec · India VIX {vix}. {freshCount} fresh {book} name{freshCount === 1 ? '' : 's'} cleared
          the conviction gate at today's scan. The calls post themselves — no manual action.
        </div>
      )}
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

// Map an enriched signal → the pure sizer's input shape.
const toSizerSig = (s) => ({
  signalId: s._signalId, sym: s.sym, entry: s.entry, stop: s.stop, buyHigh: s._buyHigh, ltp: s._ltp,
});

// Right-rail sizer — risk-as-%-of-capital tiers (from config), funded strongest-first.
// "Calculate" hands the sized plan up to the SizerResultsModal. Tier + capital persist
// per-user (useSizingPrefs) so the card isn't blank on return.
function SizerCard({ buyPool, heldIds, onCalculate }) {
  const { data: config } = useSizerConfig();
  const { data: prefs } = useSizingPrefs();
  const updatePrefs = useUpdateSizingPrefs();
  const [cash, setCash] = useState('');
  const [tier, setTier] = useState('medium');

  useEffect(() => {
    if (!prefs) return;
    setTier(prefs.risk_tier || 'medium');
    if (prefs.default_capital != null) setCash((c) => (c === '' ? String(prefs.default_capital) : c));
  }, [prefs]);

  const tiers = config?.tiers || { medium: 0.02, high: 0.03 };
  const capPct = config?.position_cap_pct ?? 0.20;
  const tierPct = tiers[tier] ?? 0.02;
  const cashNum = Number(cash) || 0;
  const nOpen = buyPool.length;

  const chooseTier = (t) => { setTier(t); updatePrefs.mutate({ risk_tier: t }); };
  const persistCapital = () => { if (cashNum > 0) updatePrefs.mutate({ default_capital: cashNum }); };
  const calc = () => {
    const plan = sizePortfolio({
      signals: buyPool.map(toSizerSig), heldSignalIds: [...heldIds],
      capital: cashNum, tierPct, capPct,
    });
    onCalculate({ ...plan, capital: cashNum, tier, tierPct, capPct });
  };

  return (
    <div className="ri-card">
      <div className="ri-card-h">POSITION SIZER</div>
      <label className="ri-sizer-label" htmlFor="ri-sizer-cash">Capital available <span className="ri-sizer-hint">(free, for new buys)</span></label>
      <input
        id="ri-sizer-cash" className="ri-sizer-input" type="number" inputMode="decimal"
        placeholder="e.g. 2000000" value={cash}
        onChange={(e) => setCash(e.target.value)} onBlur={persistCapital}
      />
      <div className="ri-sizer-tiers" role="group" aria-label="Risk tier">
        {['medium', 'high'].map((t) => (
          <button
            key={t} type="button"
            className={`ri-tier${tier === t ? ' on' : ''}`}
            onClick={() => chooseTier(t)}
          >
            {t === 'medium' ? 'Medium' : 'High'} · {Math.round((tiers[t] ?? 0) * 100)}%
          </button>
        ))}
      </div>
      <div className="ri-sizer-note">
        {Math.round(tierPct * 100)}% risk/trade · max {Math.round(capPct * 100)}% per name.
        {tier === 'high' && <> <span className="num-bear">High is aggressive — above the validated 2%.</span></>}
      </div>
      <button
        type="button" className="ri-sizer-btn" disabled={nOpen === 0 || cashNum <= 0}
        onClick={calc}
      >
        {cashNum <= 0 ? 'Enter capital to size' : `Size ${nOpen} open A-call${nOpen === 1 ? '' : 's'} →`}
      </button>
    </div>
  );
}

// One row inside the sizer results popup.
function SizerRow({ r, held, onBought }) {
  const s = r.status;
  const badge = s === SIZER_STATUS.OUT_OF_RANGE ? { t: 'chased — above buy range', cls: 'warn' }
    : s === SIZER_STATUS.NOT_FUNDED ? { t: 'no cash left', cls: 'warn' }
    : s === SIZER_STATUS.BOUGHT ? { t: '✓ bought', cls: 'bull' }
    : r.rangeUnknown ? { t: 'range unknown', cls: 'warn' } : null;
  const canBuy = s === SIZER_STATUS.FUNDED && !held;
  return (
    <div className={`rsm-row${held || s === SIZER_STATUS.BOUGHT ? ' is-bought' : ''}`}>
      <div className="rsm-sym">
        <span className="ri-sym">{r.sym}</span>
        {badge && <span className={`rsm-badge num-${badge.cls}`}>{badge.t}</span>}
      </div>
      <div className="rsm-nums tnum">
        <span className="rsm-qty">{r.qty > 0 ? `${r.qty} sh` : '—'}</span>
        <span className="rsm-cost">{r.qty > 0 ? `₹${fmtNum0(r.cost)}` : ''}</span>
        <span className="rsm-risk">{r.risk > 0 ? `risk ₹${fmtNum0(r.risk)}` : ''}</span>
      </div>
      <button
        type="button"
        className={`ri-btn ri-btn-bought${held ? ' on' : ''}`}
        disabled={!canBuy && !held}
        onClick={() => onBought(r)}
      >
        {held ? '✓' : 'Bought'}
      </button>
    </div>
  );
}

// The "Calculate" popup — the sized plan across every open Grade-A call.
function SizerResultsModal({ open, onOpenChange, result, heldIds, onMarkBought }) {
  if (!result) return null;
  const { rows, totals, capital, tier, tierPct } = result;
  // Stage 6 — rank-named skip friction: rows are strongest-first, so the first funded row the user
  // hasn't taken is the highest-ranked skip. Named, costed, never blocking (their capital).
  const fundedUntaken = rows
    .map((r, i) => ({ r, rank: i + 1 }))
    .filter(({ r }) => r.status === SIZER_STATUS.FUNDED && !heldIds.has(r.signalId));
  const topSkip = fundedUntaken.length > 0 && fundedUntaken.length < rows.length
    ? fundedUntaken[0] : null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-0 p-0 rsm-dialog" style={{ maxWidth: 480 }}
                     srTitle="Position plan — take this week's book">
        <div className="rsm">
          <div className="rsm-h">
            <span>Take this week&rsquo;s book ({rows.length})</span>
            <span className="rsm-hsub">{tier} · {Math.round(tierPct * 100)}% risk · ₹{fmtNum0(capital)} free</span>
          </div>
          <div className="rsm-list">
            {rows.map((r) => (
              <SizerRow key={r.signalId || r.sym} r={r} held={heldIds.has(r.signalId)} onBought={onMarkBought} />
            ))}
          </div>
          <div className="rsm-totals">
            <div><span>Deployed</span><b className="tnum">₹{fmtNum0(totals.deployed)}</b></div>
            <div><span>At risk</span><b className="tnum">{totals.atRiskPct.toFixed(1)}%</b></div>
            <div><span>Cash left</span><b className="tnum">₹{fmtNum0(totals.cashLeft)}</b></div>
            <div><span>Funded</span><b className="tnum">{totals.namesFunded}</b></div>
          </div>
          {topSkip && (
            <div className="rsm-friction">
              {DISCIPLINE.skipFriction(topSkip.rank, topSkip.r.sym)}
            </div>
          )}
          <div className="rsm-note">
            Indicative sizing — research output, not advice. Names you already hold are excluded;
            a “Bought” mark is remembered only until the model completes that trade.
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function SignalStatsCard({ buyPool, heldCount }) {
  const fresh = buyPool.filter((s) => s.isFreshToday).length;
  const avgPot = buyPool.length ? buyPool.reduce((a, s) => a + (s._upside || 0), 0) / buyPool.length : null;
  const avgHz  = buyPool.length ? Math.round(buyPool.reduce((a, s) => a + (s.hold || 0), 0) / buyPool.length) : null;
  // A-only book (2026-07-13): every call shown is Grade A, so the old A/B split is gone.
  return (
    <div className="ri-card">
      <div className="ri-card-h">SIGNAL STATS · TODAY</div>
      <div className="ri-kv"><span>Open A-calls</span><b className="num-info tnum">{buyPool.length}</b></div>
      <div className="ri-kv"><span>Fresh entries</span><b className="num-info tnum">{fresh}</b></div>
      <div className="ri-kv"><span>You're holding</span><b className="tnum">{heldCount}</b></div>
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
        Weekly-swing on NSE large + mid caps. A name qualifies when it's in a weekly uptrend
        (above a rising 44-week SMA), pulls back and rebounds off it on a strong green weekly
        candle, and leads the Nifty-50 on relative strength. Only the top-5 by relative-strength
        rank each week are traded (Grade A). Mechanical — the Saturday cron scans and posts the
        calls; no discretionary override.
      </div>
    </div>
  );
}

// ── Calls table ───────────────────────────────────────────────────────
function CallRow({ s, onOpen, onAction, held, onToggleBought }) {
  const act = rowAction(s);
  const pot = potentialCell(s);
  const g = (s.grade || 'B')[0].toUpperCase();
  const dayChg = s._dayChangePct;
  const mon = monitorChip(s);
  return (
    <div className="ri-row" onClick={() => onOpen(s)} role="button" tabIndex={0}
      onKeyDown={(e) => {
        // Native buttons fire on BOTH Enter and Space; a role="button" div must do the same.
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(s); }
      }}>
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
        {(s.action === 'buy-today' || s.action === 'closing') && s._buyLow != null && s._buyHigh != null && s._buyLow !== s._buyHigh ? (
          <>
            <div className="ri-cell-main tnum ri-range">{fmtNum(s._buyLow)}–{fmtNum(s._buyHigh)}</div>
            <div className="ri-cell-sub">buy range</div>
          </>
        ) : (
          <div className="ri-cell-main tnum">{fmtNum(s.entry)}</div>
        )}
      </div>

      <div className="ri-cell ri-pot">
        <div className={`ri-cell-main tnum num-${pot.tone}`}>{pot.main}</div>
        {pot.sub && <div className="ri-cell-sub">{pot.sub}</div>}
      </div>

      <div className="ri-act" onClick={(e) => e.stopPropagation()}>
        {onToggleBought && ['buy-today', 'closing', 'holding'].includes(s.action) && (
          <button
            className={`ri-btn ri-btn-bought${held ? ' on' : ''}`}
            onClick={() => onToggleBought(s)}
            title={held ? 'Marked bought — remembered until the trade completes. Click to unmark.'
                        : 'I bought this — remember it until the trade completes.'}
          >
            {held ? '✓ Bought' : 'Bought'}
          </button>
        )}
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

  // Bhanushali weekly-swing is the ONLY live model (momentum removed 2026-07-13).
  const [model, setModel] = useState('bhanushali');
  const [filter, setFilter] = useState('all');
  const [tradeCard, setTradeCard] = useState(null);
  const [sizerResult, setSizerResult] = useState(null);   // the "Calculate" popup's sized plan

  const signalsQuery    = useSignals({ model });
  const watchlistQuery  = useWatchlist({ model });

  // Per-user ephemeral holdings — merged CLIENT-SIDE (GET /api/signals stays model-only).
  const holdingsQuery = useHoldings();
  const heldIds = useMemo(
    () => new Set((holdingsQuery.data ?? []).map((h) => h.signal_id)),
    [holdingsQuery.data]
  );
  const markBought = useMarkBought();
  const unmarkBought = useUnmarkBought();

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
  const cronHealth = signalsQuery.data?.cron_health ?? null;
  const scanTime = signalsQuery.data?.scan_time ?? null;
  const reviewScorecard = signalsQuery.data?.review_scorecard ?? null;

  // Model-centric (2026-07-13): open / hold / exit come from the envelope itself (the paper-book
  // cron writes bought_date + status), NOT from Kite/personal positions. Every viewer sees the
  // same model book.
  const allEnriched = useMemo(() => {
    const enriched = [
      ...rawSignals.map((s) => enrichSignal(s, quotes)),
      ...rawWatchlist.map((s) => enrichSignal({ ...s, actionability: 'WATCHLIST', tier: 'watchlist' }, quotes)),
    ];
    const seen = new Set();
    return enriched
      .filter((s) => { if (seen.has(s.sym)) return false; seen.add(s.sym); return true; })
      .sort((a, b) => (ACTION_RANK[a.action] ?? 9) - (ACTION_RANK[b.action] ?? 9));
  }, [rawSignals, rawWatchlist, quotes]);

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

  // Track record: every stock the model bought and its outcome (bought -> held -> exited).
  const freshCount = counts.today ?? 0;

  const doAction  = (sym, suffix) => navigate(`/stock/${encodeURIComponent(sym)}${suffix}`);

  // Self-reported execution capture (Stage 4): { mode:'buy'|'sell', sig, sizerQty, tranche } | null.
  const [capture, setCapture] = useState(null);

  // Stage 6c — onboarding journey: durable per-user memory; lessons unlock off the user's OWN events.
  // (The cold-start briefing moved to ColdStartGate in the app layout so it can't be walked past.)
  const journey = useJourney();
  const fireLesson = (key) => {
    const flag = key;                                     // journey flag == LESSONS key
    if (journey.seen(flag) || !LESSONS[flag]) return;
    const l = LESSONS[flag];
    toast.info(l.title, { description: l.body, duration: 12000 });
    journey.mark(flag);
  };

  // Row "Bought" toggle: not-held → open the BUY capture popup; already-held → open the SELL popup.
  const toggleBought = (s) => {
    const id = s._signalId;
    if (!id) return;
    const sig = { sym: s.sym, signalId: id, entry: s.entry, stop: s.stop,
                  target: s.target, exitLevel: s.exitLevel, current_price: s.ltp ?? s.current_price };
    setCapture(heldIds.has(id) ? { mode: 'sell', sig, tranche: 'target' } : { mode: 'buy', sig });
  };
  // Sizer modal "Bought": open the BUY capture popup pre-filled with the sized qty (close the sizer first).
  const markSized = (r) => {
    if (!r?.signalId) return;
    setSizerResult(null);
    setCapture({ mode: 'buy', sizerQty: r.qty || null,
                 sig: { sym: r.sym, signalId: r.signalId, entry: r.entry, stop: r.stop } });
  };
  // After a fill is recorded, keep the ephemeral held-set (row highlighting) in sync with the ledger:
  // a buy or a partial sell means "held"; a full exit (nothing left) clears the mark. Also fires the
  // event-unlocked just-in-time lessons (Stage 6c) — first buy, first +2R partial.
  const onRecorded = (res, { mode: recMode, signalId }) => {
    const pos = res?.position;
    if (!signalId || !pos) return;
    if (pos.remaining_qty > 0) {
      markBought.mutate({ signal_id: signalId, ticker: pos.ticker, qty: pos.remaining_qty });
    } else {
      unmarkBought.mutate(signalId);
    }
    if (recMode === 'buy') fireLesson('lesson_first_buy');
    if (recMode === 'sell' && capture?.tranche === 'target' && (pos.realized_pnl ?? 0) > 0) {
      fireLesson('lesson_first_2r');
    }
  };

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
          <p className="ri-sub">The model's book — open, hold, exit. Only <b>Grade A</b> (the week's top-5 relative-strength leaders) is traded. Mark what you buy; it's remembered until the trade completes. Not advice — your own capital, your own rules.</p>
        </div>
        <div className="ri-head-r">
          <GlassTabs
            tabs={[{ key: 'bhanushali', label: 'Weekly Swing' }]}
            active={model}
            onChange={setModel}
            size="md"
          />
          <span className="chip c-warn">Forward-watch · paper</span>
          {model === 'bhanushali' && monitorStamp && (
            <span className="ri-fresh" title={`Live re-price as of ${monitorAsOf}`}>
              prices updated {monitorStamp} IST
            </span>
          )}
        </div>
      </div>

      {/* Stale-data banner (fault F8): the weekly scan runs Saturday; if the published board is
          >48h old (STALE) or today's expected run hasn't landed (FAILED_TODAY), say so instead of
          showing an old board as if it were current. */}
      {cronHealth && cronHealth.status && cronHealth.status !== 'OK' && (
        <div className="ri-stale-banner">
          <span className="ri-stale-dot" />
          {cronHealth.status === 'STALE'
            ? "These calls may be stale — the weekly scan hasn't refreshed in over 48 hours."
            : "Today's scan hasn't landed yet — showing the most recent published calls."}
          {scanTime && <span className="ri-stale-when"> Last scan: {String(scanTime).slice(0, 10)}.</span>}
        </div>
      )}

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

      {/* Body: table + right rail */}
      <div className="ri-grid">
        <div className="ri-main">
          <div className="ri-table">
            <div className="ri-thead">
              <span>Scrip</span>
              <span className="ri-th-r">LTP</span>
              <span className="ri-th-r">Buy range</span>
              <span className="ri-th-r">Potential</span>
              <span />
            </div>
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => <div key={i} className="ri-row-skel skeleton-card" />)
            ) : rows.length === 0 ? (
              <div className="ri-empty">
                {filter === 'all'
                  ? (buyPool.length === 0 ? STATES.idle : STATES.empty)
                  : 'No calls match this filter right now.'}
              </div>
            ) : (
              rows.map((s) => (
                <CallRow
                  key={s.sym} s={s} onOpen={setTradeCard} onAction={doAction}
                  held={heldIds.has(s._signalId)} onToggleBought={toggleBought}
                />
              ))
            )}
          </div>
        </div>

        <aside className="ri-rail">
          <SizerCard buyPool={buyPool} heldIds={heldIds} onCalculate={setSizerResult} />
          <DisciplineCard />
          {isAdmin && model === 'bhanushali' && <ReviewCard card={reviewScorecard} />}
          <CommentaryCard regime={regime} model={model} freshCount={freshCount} />
        </aside>
      </div>

      {/* Reference — static context, moved out of the rail so the rail stays actionable and the
          page doesn't leave a tall empty column beside a short call list. */}
      <div className="ri-reference">
        <SignalStatsCard buyPool={buyPool} heldCount={heldIds.size} />
        <HowCallsMadeCard />
      </div>

      {/* Footer */}
      <footer className="ri-foot">
        <div className="ri-disclaimer">{DISCLAIMER}</div>
        <div className="ri-foot-meta">SEBI Research Analyst · Model-generated signals · Research output only · NSE data delayed 15 min · v2026.07</div>
      </footer>

      <TradeCardModal sig={tradeCard} open={!!tradeCard} onOpenChange={(o) => !o && setTradeCard(null)} />
      <SizerResultsModal
        open={!!sizerResult} onOpenChange={(o) => !o && setSizerResult(null)}
        result={sizerResult} heldIds={heldIds} onMarkBought={markSized}
      />
      <ExecutionCaptureModal
        open={!!capture} mode={capture?.mode} sig={capture?.sig}
        sizerQty={capture?.sizerQty} tranche={capture?.tranche}
        onClose={() => setCapture(null)} onRecorded={onRecorded}
      />
    </div>
  );
}
