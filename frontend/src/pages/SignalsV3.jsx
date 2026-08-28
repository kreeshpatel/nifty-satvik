/**
 * SignalsV3 — the Research page (/premove).
 *
 * ONE QUESTION: why is this name on the book, and what does the plan expect of it. What to
 * actually DO today is /this-week; where to place the order is your broker.
 *
 * Rebuilt 2026-08-27 into three tables, because the weekly envelope carries three card shapes:
 * a 30-field FRESH entry case, an 18-field ACTIVE position, and a closed card with a `why`. One
 * row component could only render their intersection, which is what made the old board six thin
 * columns and a lot of dashes.
 *
 * Data:
 *   - useSignals()            → the MODEL's book: open/hold/exit signals + regime + cron_health
 *   - useQuoteBatch()         → live LTP / day-change overlay
 *   - useExecutionPositions() → the user's OWN durable ledger, the single source of "held"
 *   (Kite / personal-position mapping removed 2026-07-13 — this page is model-centric.)
 *
 * The position sizer moved to /this-week (2026-08-27), where the book is actually sized and
 * taken; Research reads the case for a name and does not also price it. The brewing-watchlist
 * merge went with it — its endpoint had no producer for the live book. The chart and order pad
 * were removed earlier (2026-07-07); levels live on /stock/:sym.
 *
 * Compliance: client-facing section strings sourced from @/lib/signalCopy. No
 * "guarantee/will/sure" language. The exit_plan `do` strings are printed verbatim.
 */

import React, { useState, useEffect, useMemo, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '@/context/AuthContext';
import { useSignals } from '@/hooks/queries/useSignals';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { GlassTabs } from '@/components/shared/GlassTabs';
import { DISCLAIMER, STATES, COLD_START, LESSONS } from '@/lib/signalCopy';
import { EmptyState } from '@/components/shared/EmptyState';
import TradeCardModal from '@/components/shared/TradeCardModal';
import ExecutionCaptureModal from '@/components/shared/ExecutionCaptureModal';
import DisciplineCard from '@/components/shared/DisciplineCard';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useExecutionPositions } from '@/hooks/queries/useExecution';
import { useJourney } from '@/hooks/queries/useJourney';
import { nseToday, parseCalendarDate, positionR, toTargetPct, holdWeek } from '@/lib/cards';
import '@/styles/signals-v3.css';
import '@/styles/research-insights.css';
import '@/styles/research.css';

// signal_id = "{TICKER}__{signal_date}" — the shared canonical key the per-user
// ephemeral-holdings layer binds a "bought" mark to (matches NQOrder.signal_id).
const signalIdOf = (s) => {
  const t = String(s?.sym || s?.ticker || '').toUpperCase();
  return s?.signal_id || (t && s?.signal_date ? `${t}__${s.signal_date}` : null);
};

// ── Formatters ────────────────────────────────────────────────────────
const fmtNum  = (n) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct1 = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%';

// The NSE calendar day, not the UTC one — see lib/cards.js. `new Date().toISOString()` is
// 5h30m behind IST, so it returned yesterday for the whole 00:00–05:30 IST window, and this
// value decides whether a buy window is open, closing or closed.
const todayISO = () => nseToday();

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
  const d = date instanceof Date ? date : parseCalendarDate(date);
  return d ? d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }) : null;
}
/** "Mon 24 Aug" — the compact form the monitor chips use. */
function fmtDayMon(v) {
  const d = parseCalendarDate(v);
  return d ? d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }) : '—';
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
function enrichSignal(raw, quotes, posBySignal) {
  const { action, sellReason } = deriveAction(raw);
  const ticker = raw.ticker || raw.sym || '';
  const q = quotes?.[ticker.toUpperCase()] || null;
  const ltp = q?.last_price ?? raw.current_price ?? raw.last_price ?? raw.close ?? raw.entry ?? 0;
  const dayChangePct = q?.change_pct ?? null;
  const entry = raw.entry ?? 0;
  const stop = raw.stop ?? entry;
  const target = raw.target ?? entry;
  // Buy band. `buy_zone_low/high` is the band the record actually buys inside; `entry_low/high`
  // is the whole SIGNAL WEEK's candle, whose low IS the stop. Reading the candle as the buy band
  // therefore quoted a range starting AT the stop (JSWSTEEL: "1,250.40-1,310.60" when the record
  // buys 1,293.70-1,310.60) and dragged the mid down with it, inflating the printed potential to
  // +7.8% against a true +6.0%. The zone wins wherever the cron writes it; the candle stays as
  // the fallback for older cards that predate the field.
  const buyLow = raw.buy_zone_low ?? raw.entry_low ?? entry;
  const buyHigh = raw.buy_zone_high ?? raw.entry_high ?? entry;
  const buyMid = ((buyLow + buyHigh) / 2) || entry;
  const rr = entry !== stop ? (target - entry) / (entry - stop) : Infinity;
  const fromEntry = entry > 0 ? ((ltp - entry) / entry) * 100 : 0;
  const upside = entry > 0 ? ((target - entry) / entry) * 100 : 0;
  // Potential to target — from the ACTUAL fill once the monitor knows it, from the band's mid
  // only while it does not. See lib/cards.js.
  const toTarget = toTargetPct({ target, filledPrice: raw.monitor?.filled_price,
                                 buyLow, buyHigh, entry }) ?? upside;
  // For a name already held, the potential that still matters is the upside REMAINING from where the
  // price is NOW to the target — a live number distinct from P&L (the gain since the Monday-open
  // entry). Without this the Potential column just echoed the P&L for held rows.
  const toTargetNow = ltp > 0 && target > 0 ? ((target - ltp) / ltp) * 100 : null;
  const zeroRisk = entry === stop;

  let buyByStr = null, daysLeft = null;
  if (raw.buy_window_until) {
    const d = parseCalendarDate(raw.buy_window_until);
    buyByStr = fmtBuyBy(d); daysLeft = daysLeftUntil(d);
  } else if (raw.signal_date && (action === 'buy-today' || action === 'closing')) {
    const d = addTradingDays(raw.signal_date, 2);
    buyByStr = fmtBuyBy(d); daysLeft = daysLeftUntil(d);
  }

  // Hold age runs from the day the position OPENED — the fill — not from the signal date. See
  // lib/cards.js; counting from the signal ages every position up to three days early.
  const isFilledUnbooked = !!(raw.monitor?.window_filled && !raw.bought_date);
  const weekOf = (action === 'holding' || action === 'sell-now' || isFilledUnbooked)
    ? holdWeek({ filledOn: raw.monitor?.filled_on, boughtDate: raw.bought_date,
                 signalDate: raw.signal_date })
    : null;

  const grade = raw.grade || 'B';

  // The user's OWN position from the durable execution ledger (self-reported buy price + qty), keyed
  // by the same signal_id. P&L is derived here from the live LTP against the recorded average buy —
  // NOT the model's signal entry — so a held row shows the owner's real, daily-updated gain/loss.
  const sid = signalIdOf({ sym: ticker, signal_date: raw.signal_date, signal_id: raw.signal_id });
  const pos = posBySignal?.get(sid) || null;
  const recordedBuy = pos && pos.avg_buy_price ? Number(pos.avg_buy_price) : null;
  const myQty = pos ? Number(pos.remaining_qty || 0) : 0;
  // The reference buy price: the user's real recorded fill if they marked one, otherwise the MODELLED
  // fill — the Monday open of the entry week — so every recommendation shows a tracked P&L from that
  // open even if the user never bought it. Fresh signals carry it as `entry_week_open`; picks the
  // model is already tracking as positions carry the same Monday open as `fill_price` (a fractional
  // qty marks them modelled, not a real fill). Either way it is the forward book's assumed entry.
  // A card whose window filled MID-WEEK has no bought_date yet — the Saturday scan books it —
  // but the monitor already knows the price it filled at, and that is the reference the reader's
  // position is actually running from. It wins over the modelled Monday open for exactly the
  // period between the fill and the book.
  const modelBuy = typeof raw.monitor?.filled_price === 'number' ? raw.monitor.filled_price
    : typeof raw.entry_week_open === 'number' ? raw.entry_week_open
    : typeof raw.fill_price === 'number' ? raw.fill_price
    : null;
  const myBuy = recordedBuy ?? modelBuy;
  const pnlIsModeled = recordedBuy == null && modelBuy != null;
  const myPnlPct = myBuy && myBuy > 0 ? (ltp / myBuy - 1) * 100 : null;
  // Rupee P&L needs a real quantity; a modelled fill has none, so it shows the % only.
  const myPnl = recordedBuy && myQty > 0 ? (ltp - recordedBuy) * myQty : null;

  // ── The entry case, computed once here so no row component does arithmetic ──
  // Risk is quoted off the ENTRY, not the current price: it is the number the position was
  // sized on, and the one the R multiple below divides by.
  const riskPct = entry > 0 && entry !== stop ? ((entry - stop) / entry) * 100 : null;
  // Extension over the 44-week SMA — the book's own entry engine, and the single strongest
  // per-trade discriminator we have measured. Banded against the config's OWN cap
  // (`ext_cap_pct`), never a hardcoded number, so a cap change re-colours the board for free.
  const ext = typeof raw.ext_pct_over_sma44 === 'number' ? raw.ext_pct_over_sma44 : null;
  const extCap = typeof raw.ext_cap_pct === 'number' ? raw.ext_cap_pct : 20;
  const extTone = ext == null ? null
    : (raw.record_would_skip_as_extended || ext >= extCap) ? 'over'
    : ext < 5 ? 'deep' : ext < 10 ? 'mid' : 'far';

  // The next tranche the plan expects, read off exit_stage rather than inferred from price:
  // the record's own booking flags are the authority on what has already been taken.
  const stage = raw.exit_stage || {};
  const tranches = raw.exit_plan?.tranches ?? [];
  const trancheDone = (t) => (t.type === 'target' ? !!stage.target_40_booked
    : t.type === 'pattern' ? !!stage.pattern_40_booked
    : t.type === 'runner' ? stage.runner_20_open === false : false);
  const nextTranche = tranches.find((t) => !trancheDone(t)) || null;

  return {
    ...raw,
    sym: ticker,
    _riskPct: riskPct,
    _ext: ext, _extCap: extCap, _extTone: extTone,
    _tranches: tranches, _trancheDone: trancheDone, _nextTranche: nextTranche,
    _fracLeft: typeof stage.fraction_remaining === 'number' ? stage.fraction_remaining : null,
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
    _upside: upside,
    _signalId: sid,
    _myBuy: myBuy, _myQty: myQty, _myPnl: myPnl, _myPnlPct: myPnlPct, _pnlIsModeled: pnlIsModeled,
    buyByStr, daysLeft, weekOf, isFilledUnbooked,
    hold: raw.hold_days || 10,
    isFreshToday: raw.signal_date === todayISO(),
  };
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
  // A filled window OUTRANKS today's price, and it has to. `filled_today` is recomputed against
  // the last bar every run, so by Thursday it says nothing about Monday -- and the old rule read
  // that as "Gapped — wait" on JSWSTEEL, which had opened 1,298.00 inside its band on Monday and
  // then run to 1,351. The trade was taken; the surface called it pending.
  if (m.kind === 'buy' && m.window_filled)
    return { label: `Filled ${fmtDayMon(m.filled_on)}`, cls: 'mon-bull' };
  if (m.kind === 'buy' && m.buy_window_open && m.filled_today === false)
    return { label: 'No open in band yet', cls: 'mon-warn' };
  return null;
}

// Signal-week candle quality — the wide-band / small-body flag (backend 2026-08-11). A wide-range
// small-body (indecision) week measures +0.03R vs +0.39R for a solid-body week, so it is surfaced
// as a low-conviction chip. Reuses the .ri-mon pill; no new CSS. Flag only — nothing traded changes.
function convictionChip(s) {
  if (s.signal_conviction === 'low') return { label: 'Low conviction', cls: 'mon-warn' };
  if (s.band_is_wide) return { label: 'Wide band', cls: 'mon-info' };
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
// ── The three row shapes ──────────────────────────────────────────────
// One row component could only ever render the INTERSECTION of the three card shapes the
// envelope carries (30-field FRESH, 18-field ACTIVE, 20-field closed). That intersection was
// six columns and a lot of dashes. These are the three unions instead.

function Scrip({ s, chips = [] }) {
  return (
    <div className="rs-scrip">
      <Logo sym={s.sym} size={28} radius={8} />
      <div className="rs-scrip-l">
        <div className="rs-scrip-top">
          <span className="ns-sym">{s.sym}</span>
          <span className="rs-grade">{(s.grade || 'A')[0].toUpperCase()}</span>
          {chips.filter(Boolean).map((c) => <span key={c.label} className={`ri-mon ${c.cls}`}>{c.label}</span>)}
        </div>
        <div className="rs-scrip-sub">{s.sector}{s.isFreshToday ? ' · new this scan' : ''}</div>
      </div>
    </div>
  );
}

/** Value over caption — the only cell shape the tables use, so every column shares a baseline. */
function Cell({ v, c, tone, right = true }) {
  return (
    <div className={right ? 'rs-r' : undefined}>
      <div className={`rs-v${tone ? ` num-${tone}` : ''}`}>{v}</div>
      {c ? <div className="rs-c">{c}</div> : null}
    </div>
  );
}

/** Extension against the config's own cap. See enrichSignal for why this is the coloured column. */
function ExtCell({ s }) {
  if (s._ext == null) return <div className="rs-r"><div className="rs-v">—</div><div className="rs-c">not on this card</div></div>;
  const pct = Math.max(4, Math.min(100, (s._ext / s._extCap) * 100));
  const label = s.record_would_skip_as_extended ? 'over the cap'
    : s._extTone === 'deep' ? 'deep touch' : `cap ${s._extCap}%`;
  return (
    <div className={`rs-r rs-ext rs-ext--${s._extTone}`}>
      <span className="rs-ext-v">{s._ext.toFixed(1)}%</span>
      <span className="rs-ext-bar"><span className="rs-ext-fill" style={{ width: `${pct}%` }} /></span>
      <span className="rs-c">{label}</span>
    </div>
  );
}

function ExpandBtn({ open, onClick, sym }) {
  return (
    <button type="button" className="rs-x" aria-expanded={open} onClick={onClick}
            aria-label={`${open ? 'Hide' : 'Show'} the case for ${sym}`}>
      ▸
    </button>
  );
}

/** The case: the model's own reasoning, printed rather than summarised. */
function CasePanel({ s, onAction, extraAction }) {
  const facts = [
    s._ext != null && ['Extension over the 44-week SMA', `${s._ext.toFixed(2)}% of ${s._extCap}% cap`],
    typeof s.band_width_pct === 'number' && ['Signal-week range', `${s.band_width_pct.toFixed(1)}%${s.band_is_wide ? ' · wide' : ''}`],
    typeof s.body_ratio === 'number' && ['Body ratio', `${(s.body_ratio * 100).toFixed(0)}% of range`],
    typeof s.crs_rank === 'number' && ['Relative-strength score', s.crs_rank.toFixed(4)],
    typeof s.no_chase_above === 'number' && ['Do not chase above', fmtNum(s.no_chase_above)],
    s.hold_days ? ['Horizon', `${s.hold_days} days`] : null,
    s._fracLeft != null && ['Position remaining', `${Math.round(s._fracLeft * 100)}%`],
  ].filter(Boolean);
  return (
    <div className="rs-case">
      <div className="rs-case-grid">
        <div>
          <div className="rs-case-h">The exit plan · {s.pattern || 'entry pattern'}</div>
          <div className="rs-plan">
            {(s._tranches || []).length === 0 && <div className="rs-why">No staged plan on this card.</div>}
            {(s._tranches || []).map((t, i) => {
              const done = s._trancheDone ? s._trancheDone(t) : false;
              return (
                <div className={`rs-plan-row${done ? ' rs-plan-row--done' : ''}`} key={i}>
                  <span className="rs-plan-pct">{done ? '✓' : `${t.pct}%`}</span>
                  {/* The record's own instruction, verbatim. A paraphrase of an instruction is a
                      second instruction, and only one of the two was ever backtested. */}
                  <span>{t.do}</span>
                </div>
              );
            })}
          </div>
        </div>
        <div>
          <div className="rs-case-h">Why it qualified</div>
          <div className="rs-facts">
            {facts.map(([k, v]) => <div className="rs-fact" key={k}><span>{k}</span><b>{v}</b></div>)}
          </div>
          {s.buy_window && <div className="rs-fact-note">{s.buy_window}</div>}
          <div className="rs-case-actions">
            <button type="button" className="ns-btn" onClick={() => onAction(s.sym)}>Levels &amp; chart →</button>
            {extraAction}
          </div>
        </div>
      </div>
    </div>
  );
}

/** §1 New this week — the entry case. Every column here exists only on a FRESH card. */
function FreshRow({ s, rank, open, onToggle, onAction }) {
  const chips = [monitorChip(s), convictionChip(s),
    s.record_would_skip_as_extended ? { label: 'Over ext cap', cls: 'mon-bear' } : null];
  return (
    <>
      <div className="rs-tr">
        <span className={`rs-rank${rank <= 3 ? ' rs-rank--top' : ''}`}
              title={typeof s.crs_rank === 'number' ? `Relative-strength score ${s.crs_rank.toFixed(4)}` : undefined}>
          {rank}
        </span>
        <Scrip s={s} chips={chips} />
        <ExtCell s={s} />
        <Cell v={s._buyLow !== s._buyHigh ? `${fmtNum(s._buyLow)}–${fmtNum(s._buyHigh)}` : fmtNum(s.entry)}
              c={s.no_chase_above ? `no chase > ${fmtNum(s.no_chase_above)}` : 'buy band'} />
        <Cell v={fmtNum(s.stop)} c={s._riskPct != null ? `−${s._riskPct.toFixed(1)}% risk` : 'stop'} />
        <Cell v={fmtNum(s.target)} c={`${fmtPct1(s._toTarget)} · ${Number.isFinite(s._rr) ? `${s._rr.toFixed(1)}R` : '—'}`} />
        <div className="rs-r rs-hide-md">
          <div className="rs-v">{s.buyByStr || '—'}</div>
          <div className="rs-c">{s.daysLeft != null ? `${s.daysLeft}d left` : 'buy window'}</div>
        </div>
        <ExpandBtn open={open} onClick={onToggle} sym={s.sym} />
      </div>
      {open && <CasePanel s={s} onAction={onAction} />}
    </>
  );
}

/** §2 The open book — the position case. No entry diagnostics exist on these cards. */
function OpenRow({ s, open, onToggle, onAction, onToggleBought, held }) {
  const exiting = s.action === 'sell-now';
  const unreal = s._myPnlPct;
  // Gain and risk measured from the SAME fill. Dividing the reader's own gain by the MODEL's
  // risk-per-share flattered every fill above the model entry — a 4% chase read +0.80R when the
  // true figure was +0.37R. See lib/cards.js.
  const rNow = positionR({ ltp: s._ltp, fill: s._myBuy, stop: s.stop });
  const next = s._nextTranche;
  return (
    <>
      <div className={`rs-tr${exiting ? ' ns-row--alarm' : ''}`}>
        <Scrip s={s} chips={[monitorChip(s), exiting ? { label: 'Exit now', cls: 'mon-bear' } : null]} />
        <Cell v={fmtNum(s._myBuy ?? s.entry)}
              c={s.isFilledUnbooked ? 'window fill' : s._pnlIsModeled ? 'model fill' : 'your fill'} />
        <Cell v={fmtNum(s._ltp)} c={s._dayChangePct != null ? fmtPct1(s._dayChangePct) : 'now'}
              tone={s._dayChangePct == null ? null : s._dayChangePct >= 0 ? 'bull' : 'bear'} />
        <Cell v={unreal == null ? '—' : fmtPct1(unreal)}
              c={rNow == null ? 'unrealised' : `${rNow >= 0 ? '+' : '−'}${Math.abs(rNow).toFixed(2)}R`}
              tone={unreal == null ? null : unreal >= 0 ? 'bull' : 'bear'} />
        <div className="rs-hide-md">
          <div className="rs-plan-next">
            {exiting ? (s.why || 'Close the position.')
              : s.isFilledUnbooked ? 'Filled — the Saturday scan books it'
              : next ? `${next.pct}% at ${fmtNum(next.level ?? next.arm)}` : 'Runner — hold'}
          </div>
          <div className="rs-c">
            {exiting ? 'the model is already out'
              : s.isFilledUnbooked ? 'not yet in the weekly record'
              : `next tranche · ${next?.type ?? 'runner'}`}
          </div>
        </div>
        <div className="rs-r rs-hide-md">
          <div className="rs-v">{s.weekOf ? `wk ${s.weekOf}` : '—'}</div>
          <div className="rs-c">of 13</div>
        </div>
        <ExpandBtn open={open} onClick={onToggle} sym={s.sym} />
      </div>
      {open && (
        <CasePanel
          s={s} onAction={onAction}
          extraAction={onToggleBought && (
            <button type="button" className={`ns-btn${exiting ? ' ns-btn--primary' : ''}`}
                    onClick={() => onToggleBought(s)}>
              {held ? 'Record a sell' : 'Record a fill'}
            </button>
          )}
        />
      )}
    </>
  );
}

/** §3 Closed this cycle — why a name left the board. The full record lives on /history. */
function ClosedRow({ s }) {
  // Two different endings share this table, and they are not the same fact. A position the model
  // EXITED has an outcome (target / stop). A buy window that expired with no open inside the band
  // was never a trade at all — reading its `status` gave the outcome "fresh", and the fallback
  // sentence claimed the model had closed a call it never opened.
  const untaken = s.action === 'closed';
  const good = /TARGET/i.test(s.status || '');
  return (
    <div className="rs-tr">
      <Scrip s={s} />
      <Cell v={fmtNum(s._ltp)} c="last price" />
      <Cell v={untaken ? 'not taken' : (s.status || 'closed').replace('HIT_', '').toLowerCase()}
            c="outcome" tone={untaken ? null : good ? 'bull' : 'bear'} />
      <div className="rs-why">
        {untaken
          ? `The buy window closed ${s.buy_window_until ? fmtDayMon(s.buy_window_until) : ''} with no open inside the band — no trade.`
          : (s.why || 'The model closed this call.')}
      </div>
    </div>
  );
}


export default function SignalsV3() {
  const { user } = useContext(AuthContext);
  const isAdmin = !!user?.is_admin;
  const navigate = useNavigate();

  // Bhanushali weekly-swing is the ONLY live model (momentum removed 2026-07-13).
  const [model, setModel] = useState('bhanushali');
  const [tradeCard, setTradeCard] = useState(null);

  const signalsQuery    = useSignals({ model });

  // ONE store for "did you buy this": the durable execution ledger.
  //
  // There used to be two. `/api/holdings` kept an ephemeral "bought" mark that was erased the
  // moment the model completed the trade, while `/api/execution` kept the append-only ledger the
  // reconciliation and the P&L are derived from. Both answered the same question, this page wrote
  // to the ephemeral one and read from it, and a real recorded position whose mark had been pruned
  // read back as "not held". Two stores of one fact is one store too many, and the durable one is
  // the one every other surface already trusts.
  const execQuery = useExecutionPositions();
  const posBySignal = useMemo(
    () => new Map((execQuery.data ?? []).map((p) => [p.signal_id, p])),
    [execQuery.data],
  );

  const rawSignals = useMemo(() => signalsQuery.data?.signals ?? [], [signalsQuery.data]);

  const quoteSymbols = useMemo(
    () => [...new Set(rawSignals.map((s) => (s.ticker || '').toUpperCase()).filter(Boolean))],
    [rawSignals]
  );
  const quotesQuery = useQuoteBatch(quoteSymbols);
  const quotes = quotesQuery.data ?? null;

  const regime = signalsQuery.data?.regime ?? {};
  const monitorAsOf = signalsQuery.data?.monitor_as_of ?? null;
  const monitorStamp = signalsQuery.data?.monitor_generated_ist ?? null;
  const cronHealth = signalsQuery.data?.cron_health ?? null;
  const scanTime = signalsQuery.data?.scan_time ?? null;
  const reviewScorecard = signalsQuery.data?.review_scorecard ?? null;

  // ── The three books ───────────────────────────────────────────────────
  // Model-centric (2026-07-13): open / hold / exit come from the envelope itself (the paper-book
  // cron writes bought_date + status), NOT from Kite/personal positions. Every viewer sees the
  // same model book.
  //
  // Bucketed, not filtered. The previous board DROPPED every closed call and then rendered the
  // survivors through one row shape — which is how a 30-field entry card and an 18-field
  // position card ended up sharing six columns. Each bucket now gets the columns its own card
  // shape actually carries.
  const allEnriched = useMemo(() => {
    // The brewing/watchlist tier was merged in here from GET /api/signals/watchlist. That endpoint
    // returned an empty list unconditionally for the live book -- the weekly model has no watchlist
    // file and `_MODELS["bhanushali"]["watchlist"]` was None -- so the merge could only ever add
    // nothing. It is gone; `deriveAction` still understands a 'brewing' card, so a future watchlist
    // tier only needs its producer back.
    const enriched = rawSignals.map((s) => enrichSignal(s, quotes, posBySignal));
    const seen = new Set();
    return enriched.filter((s) => { if (seen.has(s.sym)) return false; seen.add(s.sym); return true; });
  }, [rawSignals, quotes, posBySignal]);

  // §1 — buyable this week, ranked the way the envelope's own buy_window instructs:
  // "fund strongest CRS rank first". That instruction has been in the payload all along and was
  // never once shown, so the board's order silently disagreed with the book's own rule.
  const freshRows = useMemo(() => allEnriched
    .filter((s) => !s.isFilledUnbooked && (s.action === 'buy-today' || s.action === 'closing'))
    .sort((a, b) => (b.crs_rank ?? -1) - (a.crs_rank ?? -1)), [allEnriched]);

  // §2 — the model's open positions, plus any exit it has issued. An exit sorts to the top:
  // acting late on one costs more than acting late on anything else on this page.
  // A window that FILLED belongs here even before the Saturday scan books it. The envelope still
  // says FRESH and carries no bought_date until the weekend recompute, so these cards used to
  // fall through to "Closed this cycle" — a trade the reader now owns, filed under "already
  // exited", labelled with the outcome "fresh". Every part of that was false.
  const openRows = useMemo(() => allEnriched
    .filter((s) => s.action === 'holding' || s.isFilledUnbooked
      || (s.action === 'sell-now' && s._myQty > 0))
    .sort((a, b) => (a.action === 'sell-now' ? -1 : 0) - (b.action === 'sell-now' ? -1 : 0)), [allEnriched]);

  // §3 — closed in the CURRENT envelope only. The full record is /history; this section exists
  // to answer "where did that name go", which /history answers too slowly to be useful here.
  const closedRows = useMemo(() => allEnriched
    .filter((s) => !s.isFilledUnbooked
      && ((s.action === 'sell-now' && !(s._myQty > 0)) || s.action === 'closed')), [allEnriched]);

  const buyPool = freshRows;
  const freshCount = useMemo(() => allEnriched.filter((s) => s.isFreshToday).length, [allEnriched]);

  // One row open at a time, keyed by signal id: two open case panels turn a scannable table
  // into a stack of documents.
  const [openCase, setOpenCase] = useState(null);
  const toggleCase = (s) => setOpenCase((cur) => (cur === s._signalId ? null : s._signalId));

  const doAction = (sym) => navigate(`/stock/${encodeURIComponent(sym)}`);

  // Self-reported execution capture (Stage 4): { mode:'buy'|'sell', sig, sizerQty, tranche } | null.
  const [capture, setCapture] = useState(null);

  // Stage 6c — onboarding journey: durable per-user memory; lessons unlock off the user's OWN events.
  const journey = useJourney();
  const showColdStart = !journey.isLoading && !journey.seen('cold_start_acked');
  const fireLesson = (key) => {
    const flag = key;                                     // journey flag == LESSONS key
    if (journey.seen(flag) || !LESSONS[flag]) return;
    const l = LESSONS[flag];
    toast.info(l.title, { description: l.body, duration: 12000 });
    journey.mark(flag);
  };

  // Row "Bought" toggle: not-held → open the BUY capture popup; already-held → open the SELL popup.
  const isHeld = (s) => s?._myQty > 0;

  const toggleBought = (s) => {
    const id = s._signalId;
    if (!id) return;
    const sig = { sym: s.sym, signalId: id, entry: s.entry, stop: s.stop,
                  target: s.target, exitLevel: s.exitLevel, current_price: s._ltp ?? s.current_price };
    setCapture(isHeld(s) ? { mode: 'sell', sig, tranche: 'target' } : { mode: 'buy', sig });
  };
  // Recording a fill no longer has to mirror itself into a second store: the ledger mutation
  // invalidates the positions query, and held-ness is derived from that. This function is now only
  // the just-in-time lessons (Stage 6c) — first buy, first +2R partial.
  const onRecorded = (res, { mode: recMode, signalId }) => {
    const pos = res?.position;
    if (!signalId || !pos) return;
    if (recMode === 'buy') fireLesson('lesson_first_buy');
    if (recMode === 'sell' && capture?.tranche === 'target' && (pos.realized_pnl ?? 0) > 0) {
      fireLesson('lesson_first_2r');
    }
  };

  if (signalsQuery.error) {
    return (
      <div className="ns-page ns-page--wide">
        <EmptyState title="Couldn’t load research calls" body={STATES.error} />
      </div>
    );
  }

  const loading = signalsQuery.isLoading;

  return (
    <div className="ns-page ns-page--wide">
      <header className="rs-head">
        <div>
          <div className="ns-kicker">RESEARCH · THE MODEL’S BOOK</div>
          <h1 className="ns-title">Research</h1>
          <p className="ns-sub">
            Why each name is on the book, and what the plan expects of it. Only <b>Grade A</b> —
            the week’s top relative-strength leaders — is traded. What to actually do today is on{' '}
            <Link className="ns-link" to="/this-week" style={{ marginRight: 0 }}>This week</Link>.
          </p>
        </div>
        <div className="rs-head-r">
          <GlassTabs tabs={[{ key: 'bhanushali', label: 'Weekly Swing' }]} active={model}
                     onChange={setModel} size="md" />
          <span className="chip c-warn">Forward-watch · paper</span>
          <Link to="/history" className="ns-link">Past calls →</Link>
          {model === 'bhanushali' && monitorStamp && (
            <span className="rs-fresh" title={`Live re-price as of ${monitorAsOf}`}>
              prices updated {monitorStamp} IST
            </span>
          )}
        </div>
      </header>

      {/* Stale-data banner (fault F8): the weekly scan runs Saturday; if the published board is
          >48h old (STALE) or today's expected run hasn't landed (FAILED_TODAY), say so instead of
          showing an old board as if it were current. */}
      {cronHealth && cronHealth.status && cronHealth.status !== 'OK' && (
        <div className="rs-stale">
          {cronHealth.status === 'STALE'
            ? 'These calls may be stale — the weekly scan hasn’t refreshed in over 48 hours.'
            : 'Today’s scan hasn’t landed yet — showing the most recent published calls.'}
          {scanTime && <span className="ns-num"> Last scan: {String(scanTime).slice(0, 10)}.</span>}
        </div>
      )}

      <div className="rs-grid">
        <div>
          {/* ── §1 NEW THIS WEEK — the entry case ── */}
          <section className="ns-section">
            <div className="ns-section-h">
              <h2>New this week <span className="ns-count">{freshRows.length}</span></h2>
              <span className="ns-section-sub">Ranked by relative strength — the book funds the strongest first</span>
            </div>
            <div className="rs-table rs-table--fresh">
              <div className="rs-th">
                <span>#</span>
                <span>Scrip</span>
                <span className="rs-r">Ext vs 44w</span>
                <span className="rs-r">Buy band</span>
                <span className="rs-r">Stop</span>
                <span className="rs-r">Target</span>
                <span className="rs-r rs-hide-md">Window</span>
                <span />
              </div>
              {loading
                ? Array.from({ length: 3 }).map((_, i) => <div key={i} className="rs-tr" style={{ height: 52 }} />)
                : freshRows.length === 0
                  ? <div className="ns-card ns-prose">{STATES.idle}</div>
                  : freshRows.map((s, i) => (
                      <FreshRow key={s.sym} s={s} rank={i + 1} open={openCase === s._signalId}
                                onToggle={() => toggleCase(s)} onAction={doAction} />
                    ))}
            </div>
          </section>

          {/* ── §2 THE OPEN BOOK — the position case ── */}
          {openRows.length > 0 && (
            <section className="ns-section">
              <div className="ns-section-h">
                <h2>The open book <span className="ns-count">{openRows.length}</span></h2>
                <span className="ns-section-sub">Positions the model holds, and what the plan expects next</span>
              </div>
              <div className="rs-table rs-table--open">
                <div className="rs-th">
                  <span>Scrip</span>
                  <span className="rs-r">Entry</span>
                  <span className="rs-r">Now</span>
                  <span className="rs-r">Unrealised</span>
                  <span className="rs-hide-md">Next</span>
                  <span className="rs-r rs-hide-md">Held</span>
                  <span />
                </div>
                {openRows.map((s) => (
                  <OpenRow key={s.sym} s={s} open={openCase === s._signalId} onToggle={() => toggleCase(s)}
                           onAction={doAction} onToggleBought={toggleBought} held={isHeld(s)} />
                ))}
              </div>
            </section>
          )}

          {/* ── §3 CLOSED THIS CYCLE — where a name went ── */}
          {closedRows.length > 0 && (
            <section className="ns-section">
              <div className="ns-section-h">
                <h2>Closed this cycle <span className="ns-count">{closedRows.length}</span></h2>
                <span className="ns-section-sub">
                  Calls the model has already exited. The full record is on{' '}
                  <Link className="ns-link" to="/history" style={{ marginRight: 0 }}>past calls</Link>.
                </span>
              </div>
              <div className="rs-table rs-table--closed">
                <div className="rs-th">
                  <span>Scrip</span>
                  <span className="rs-r">Last</span>
                  <span className="rs-r">Outcome</span>
                  <span>Why</span>
                </div>
                {closedRows.map((s) => <ClosedRow key={s.sym} s={s} />)}
              </div>
            </section>
          )}
        </div>

        <aside className="rs-rail">
          <DisciplineCard />
          {isAdmin && model === 'bhanushali' && <ReviewCard card={reviewScorecard} />}
          <CommentaryCard regime={regime} model={model} freshCount={freshCount} />
        </aside>
      </div>

      {/* Reference — static context, kept out of the rail so the rail stays actionable and the
          page doesn't leave a tall empty column beside a short call list. */}
      <div className="rs-reference">
        <SignalStatsCard buyPool={buyPool} heldCount={openRows.length} />
        <HowCallsMadeCard />
      </div>

      <footer className="ns-foot">
        <div className="ns-disclaimer">{DISCLAIMER}</div>
        <div className="ns-disclaimer" style={{ marginTop: 'var(--space-2)' }}>
          SEBI Research Analyst · Model-generated signals · Research output only · NSE data delayed 15 min · v2026.08
        </div>
      </footer>

      <TradeCardModal sig={tradeCard} open={!!tradeCard} onOpenChange={(o) => !o && setTradeCard(null)} />
      <ExecutionCaptureModal
        open={!!capture} mode={capture?.mode} sig={capture?.sig}
        sizerQty={capture?.sizerQty} tranche={capture?.tranche}
        onClose={() => setCapture(null)} onRecorded={onRecorded}
      />

      {/* Stage 6c — cold-start onboarding: shown once (durable server-side flag), sets forward-honest
          expectations before the first trade. Dismissable only via the acknowledgement. */}
      <Dialog open={showColdStart} onOpenChange={() => {}}>
        <DialogContent className="border-0 p-0 rsm-dialog" style={{ maxWidth: 460 }}
                     srTitle="Before your first trade — what normal looks like">
          <div className="rsm ecm">
            <div className="rsm-h"><span>{COLD_START.title}</span></div>
            <ul className="ecm-coldstart-points">
              {COLD_START.points.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
            <div className="ecm-actions" style={{ gridTemplateColumns: '1fr' }}>
              <button type="button" className="ri-sizer-btn ecm-confirm"
                      onClick={() => journey.mark('cold_start_acked')}>
                {COLD_START.ack}
              </button>
            </div>
            <div className="rsm-note">{DISCLAIMER}</div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
