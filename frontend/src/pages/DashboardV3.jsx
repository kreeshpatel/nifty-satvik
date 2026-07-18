/**
 * DashboardV3 — Production dashboard page.
 *
 * Ported directly from the design prototype (design-proto/nq-research-dashboard.html,
 * the "v-dash" section) — markup structure and CSS values are taken verbatim from that
 * file (see styles/dashboard-proto.css), wired to real data instead of the prototype's
 * mock numbers. The watchlist rail is NOT part of this port — it stays our own build
 * (two lists + Signals/Held tabs), a deliberate superset of the prototype's simpler rail.
 *
 * Data sources (unchanged from the pre-port version):
 *   useSignals({model:'bhanushali'}) — signals + regime + cron_health (live book)
 *   useWatchlist({model:'bhanushali'}) — brewing/below-gate candidates
 *   useOverview() — paper portfolio + performance metrics
 *   (per-user broker state removed per ADR 0011 — holdings panel shows its empty state)
 *   useIndexSparklines() — NIFTY/SENSEX/VIX/... ticker values
 *   useQuoteBatch() — live day-change for held symbols
 *
 * Compliance: no "guarantee", "will", "sure", "sure-shot" in client-facing strings.
 * DISCLAIMER footer sourced from @/lib/signalCopy.
 */

import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSignals } from '@/hooks/queries/useSignals';
import { useWatchlist } from '@/hooks/queries/useWatchlist';
import { useOverview } from '@/hooks/queries/useOverview';
import { useIndexSparklines } from '@/hooks/queries/useIndexSparklines';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { useExecutionPositions } from '@/hooks/queries/useExecution';
import { DISCLAIMER } from '@/lib/signalCopy';
import TradeCardModal from '@/components/shared/TradeCardModal';
import '@/styles/dashboard-proto.css';

// ─────────────────────────────────────────────────────────────────────
// Formatters
// ─────────────────────────────────────────────────────────────────────
const fmtINR = (n) =>
  n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (n, plus = true) =>
  n == null ? '—' : (n >= 0 && plus ? '+' : '') + Number(n).toFixed(2) + '%';
const fmtPct1 = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%';

function tickerBg(sym) {
  let h = 0;
  for (const ch of (sym || '')) h = (h + ch.charCodeAt(0) * 13) % 360;
  return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`;
}

// Colored 2-letter monogram — the prototype's `.logo` tile (no favicon fetch;
// every card in the prototype uses a flat colour tile, not a brand logo).
// `tint={false}` skips the inline background so an ancestor CSS rule (e.g.
// `.pick .nm .logo`) can supply a different treatment — inline style would
// otherwise out-rank that descendant selector.
function ProtoLogo({ sym, tint = true, style }) {
  return (
    <div className="logo" style={{ ...(tint ? { background: tickerBg(sym) } : {}), ...style }}>
      {(sym || '??').slice(0, 2).toUpperCase()}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Regime — prototype .regime
// ─────────────────────────────────────────────────────────────────────
function RegimeCard({ regime, indexData, heldCount }) {
  const status = (regime?.status || '').toLowerCase();
  // A missing status means the regime hasn't loaded yet — NOT a choppy market. Previously this fell
  // through to "The market is Choppy. Mixed tape — no clear trend. Stay selective." while every
  // number still showed "—", i.e. an authoritative market call fabricated from empty data.
  const known = Boolean(status);
  const isBull = status.includes('bull');
  const isBear = status.includes('bear');
  const label = isBull ? 'Bullish' : isBear ? 'Bearish' : 'Choppy';
  const tone  = !known ? 'muted' : isBull ? 'bull' : isBear ? 'bear' : 'warn';
  const line  = isBull
    ? 'Trend and breadth favour longs.'
    : isBear
      ? 'Trend and breadth are against longs — stay defensive.'
      : 'Mixed tape — no clear trend. Stay selective.';

  // Strength: backend sends 0 as its "not computed" sentinel — treat 0/absent
  // as unknown rather than fabricating a midpoint.
  const strengthRaw = Number(regime?.strength);
  const strength = Number.isFinite(strengthRaw) && strengthRaw > 0
    ? Math.max(0, Math.min(100, Math.round(strengthRaw))) : null;

  const vixData = indexData?.['INDIA VIX'] ?? indexData?.['INDIAVIX'] ?? null;
  const vixRaw  = Number(regime?.vix) || Number(vixData?.ltp) || Number(vixData?.last) || Number(vixData?.value) || null;
  const vix     = vixRaw != null && isFinite(vixRaw) && vixRaw > 0 ? vixRaw : null;
  const vixWord = vix == null ? '—' : vix < 15 ? 'calm' : vix <= 20 ? 'normal' : 'elevated';
  const vixTone = vix == null ? 'muted' : vix < 20 ? 'bull' : 'warn';

  const breadthRaw = Number(regime?.breadth);
  const breadth = Number.isFinite(breadthRaw) && breadthRaw !== 0 ? breadthRaw : null;

  const updated = regime?.updated_at || regime?.as_of || regime?.timestamp || null;
  const updatedLabel = updated
    ? new Date(updated).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <div className={`regime tone-${tone}`}>
      <div className="regime-main">
        <div className="regime-eyebrow"><span className="dot" /><span className="micro">Market regime{updatedLabel ? ` · updated ${updatedLabel}` : ''}</span></div>
        <div className="regime-statement" aria-live="polite">
          {known
            ? <>The market is <b>{label}.</b> {line}</>
            : <span style={{ color: 'var(--text-3)' }}>Reading today&rsquo;s market&hellip;</span>}
        </div>
        <div className="strength">
          <div className="micro">10-day strength{strength == null ? '' : ` · ${strength}/100`}</div>
          <div className="strength-track"><div className="strength-fill" style={{ width: `${strength ?? 0}%` }} /></div>
        </div>
      </div>
      <div className="regime-stats">
        <div className="rstat"><div className="k">India VIX</div><div className="v tnum">{vix == null ? '—' : vix.toFixed(1)}</div><div className={`d ${vixTone}`}>{vixWord}</div></div>
        <div className="rstat"><div className="k">Breadth</div><div className={`v tnum ${breadth != null ? (breadth >= 0 ? 'bull' : 'bear') : ''}`}>{breadth == null ? '—' : (breadth >= 0 ? '+' : '') + breadth}</div><div className="d muted">adv−dec</div></div>
        <div className="rstat"><div className="k">Held</div><div className="v tnum">{heldCount != null ? `${Math.min(heldCount, 15)}/15` : '—/15'}</div><div className="d muted">slots</div></div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Research-call card — prototype .sig
// ─────────────────────────────────────────────────────────────────────
function SigCard({ sig, brewing, onOpen }) {
  const sym    = sig.ticker || sig.sym || sig.symbol || '??';
  const name   = sig.name || sym;
  const sector = sig.sector || '—';
  const grade  = (sig.grade || 'B')[0].toUpperCase();
  const entry  = sig.entry ?? 0;
  const stop   = sig.stop_loss ?? sig.stop ?? entry;
  const target = sig.target ?? entry;
  const ltp    = sig.current_price ?? sig.close ?? entry;

  const upsidePct = entry > 0 && target > 0 ? ((target - entry) / entry) * 100 : null;
  const expReturn = sig.predicted_return_pct != null ? sig.predicted_return_pct : upsidePct;

  // Reward:risk is genuinely per-stock and derived from this card's own levels. It replaces a
  // model-WIDE win rate that was printed identically on every card as if it described that name.
  const risk = entry > 0 && stop > 0 && entry > stop ? entry - stop : null;
  const rr = risk && target > entry ? (target - entry) / risk : null;

  const toGate = brewing && ltp > 0 ? ((entry - ltp) / ltp) * 100 : null;

  return (
    <div
      className={`sig${!brewing ? ' up' : ''}`}
      onClick={() => onOpen?.(sig)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onOpen?.(sig); }}
      style={{ cursor: 'pointer' }}
    >
      <span className={`sig-tag pill ${brewing ? 'brew' : 'fresh'}`}>{brewing ? '● BREW' : '● FRESH'}</span>
      <div className="sig-head">
        <ProtoLogo sym={sym} />
        <div><div className="sig-sym">{sym}</div><div className="sig-name">{name !== sym ? name : sector}</div></div>
        <span className={`grade${grade === 'A' ? ' a' : ''}`}>{grade}</span>
      </div>
      <div className="sig-metrics">
        <div className="m"><div className="k">Reward : risk</div><div className="v tnum">{rr != null ? `${rr.toFixed(1)} : 1` : '—'}</div></div>
        {brewing ? (
          <div className="m"><div className="k">To gate</div><div className="v warn tnum">{toGate != null ? fmtPct1(toGate) : '—'}</div></div>
        ) : (
          <div className="m"><div className="k">Exp. return</div><div className="v tnum">{expReturn != null ? fmtPct1(expReturn) : '—'}</div></div>
        )}
      </div>
      <div className="sig-foot">
        <div className="lvl"><div className="k">Entry</div><div className="v tnum">{fmtINR(entry)}</div></div>
        <div className="lvl"><div className="k">Stop</div><div className="v bear tnum">{fmtINR(stop)}</div></div>
        <div className="lvl"><div className="k">Target</div><div className="v bull tnum">{fmtINR(target)}</div></div>
      </div>
    </div>
  );
}

function SigCardSkeleton() {
  return (
    <>
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="sig skeleton-card" style={{ minHeight: 190 }} aria-hidden="true" />
      ))}
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Holdings table — prototype .thead/.trow
// ─────────────────────────────────────────────────────────────────────
function HoldingsPanel({ holdings, quoteData, isLoading }) {
  const rows = useMemo(() => {
    if (!holdings?.length) return [];
    return holdings.slice(0, 8).map((h) => {
      const sym = (h.tradingsymbol || h.symbol || '').toUpperCase();
      const ltp = h.last_price ?? 0;
      const qty = h.quantity ?? 0;
      const avgP = h.average_price ?? 0;
      const dayChg = h.day_change ?? null;
      const gainPct = ltp > 0 && dayChg != null ? (dayChg / ltp) * 100 : h.day_change_percentage ?? null;
      const pnl = (ltp > 0 && avgP > 0 && qty > 0) ? (ltp - avgP) * qty : null;
      return { sym, sector: quoteData?.[sym]?.sector || 'NSE', ltp, qty, avgP, gainPct, pnl };
    });
  }, [holdings, quoteData]);

  const [tab, setTab] = useState('all');
  const gainers = rows.filter((r) => (r.gainPct ?? 0) > 0).length;
  const losers = rows.filter((r) => (r.gainPct ?? 0) < 0).length;
  const filtered = tab === 'gainers' ? rows.filter((r) => (r.gainPct ?? 0) > 0)
    : tab === 'losers' ? rows.filter((r) => (r.gainPct ?? 0) < 0) : rows;

  return (
    <div className="card panel" style={{ paddingBottom: 6 }}>
      <div className="panel-head" style={{ marginBottom: 10 }}>
        <h3>Your holdings</h3>
        <div className="tabs">
          <button className={tab === 'all' ? 'on' : ''} onClick={() => setTab('all')}>All {rows.length}</button>
          <button className={tab === 'gainers' ? 'on' : ''} onClick={() => setTab('gainers')}>Gainers {gainers}</button>
          <button className={tab === 'losers' ? 'on' : ''} onClick={() => setTab('losers')}>Losers {losers}</button>
        </div>
      </div>
      <div className="thead"><span>Company</span><span>Qty</span><span>Avg</span><span>LTP</span><span>Chg</span><span>Unreal. P&amp;L</span></div>
      {isLoading ? (
        <div style={{ padding: '16px 8px', color: 'var(--text-3)', fontSize: 13 }}>Loading…</div>
      ) : filtered.length === 0 ? (
        <div style={{ padding: '16px 8px', color: 'var(--text-3)', fontSize: 13 }}>
          {rows.length === 0 ? 'No holdings yet — record a buy from Research and it shows up here.' : `No ${tab} right now.`}
        </div>
      ) : filtered.map((r) => (
        <div className="trow" key={r.sym}>
          <div className="co"><ProtoLogo sym={r.sym} /><div><div className="nm">{r.sym}</div><div className="ex">NSE · {r.sector}</div></div></div>
          <div className="td tnum">{r.qty || '—'}</div>
          <div className="td tnum">{r.avgP ? fmtINR(r.avgP) : '—'}</div>
          <div className="td tnum">{r.ltp ? fmtINR(r.ltp) : '—'}</div>
          <div><span className={`chgpill tnum ${(r.gainPct ?? 0) >= 0 ? 'up' : 'dn'}`}>{r.gainPct != null ? fmtPct(r.gainPct) : '—'}</span></div>
          <div className={`td tnum ${r.pnl == null ? '' : r.pnl >= 0 ? 'bull' : 'bear'}`}>{r.pnl != null ? `${r.pnl >= 0 ? '+' : '−'}${fmtINR(Math.abs(r.pnl))}` : '—'}</div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Global indices strip — prototype .gidx/.gi
// ─────────────────────────────────────────────────────────────────────
const INDEX_LABELS = {
  NIFTY: 'NIFTY 50', NIFTY50: 'NIFTY 50', SENSEX: 'SENSEX',
  BANKNIFTY: 'BANK NIFTY', NIFTYBANK: 'BANK NIFTY', INDIAVIX: 'INDIA VIX',
  VIX: 'INDIA VIX', USDINR: 'USD/INR', NIFTYMIDCAP: 'NIFTY MIDCAP', NIFTYIT: 'NIFTY IT',
};
function GlobalIndices({ indexData }) {
  const items = useMemo(() => {
    if (!indexData || typeof indexData !== 'object') return [];
    return Object.keys(indexData).map((k) => {
      const d = indexData[k] || {};
      const val = d.last ?? d.ltp ?? d.value;
      const chg = d.changePct ?? d.change_pct ?? d.change;
      if (typeof val !== 'number' || !isFinite(val)) return null;
      return { key: k, label: INDEX_LABELS[k] || k, val, chg: typeof chg === 'number' ? chg : 0 };
    }).filter(Boolean).slice(0, 4);
  }, [indexData]);
  if (!items.length) return null;
  return (
    <>
      <div className="row-head" style={{ marginBottom: 0 }}><span className="sec-title">Global indices</span></div>
      <div className="gidx">
        {items.map((it) => {
          const up = it.chg >= 0;
          return (
            <div className="gi" key={it.key}>
              <div className="n">{it.label}</div>
              <div className="v tnum">{it.val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
              <div className={`c tnum ${up ? 'bull' : 'bear'}`}>{up ? '▲' : '▼'} {Math.abs(it.chg).toFixed(2)}%</div>
            </div>
          );
        })}
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Action tiles — prototype .grid3/.qa
// ─────────────────────────────────────────────────────────────────────
function ActionTiles() {
  const tiles = [
    { cls: 'qa-teal', to: '/premove', title: 'Position sizer', desc: "Size today's top-15 to your own capital & E-margin.", go: 'Size positions →',
      path: 'M12 3v18M5 8l7-5 7 5M5 8v9l7 4 7-4V8' },
    { cls: 'qa-violet', to: '/track-record', title: 'Track record', desc: 'Live paper equity, closed-trade log & forward-wall.', go: 'View record →',
      path: 'M3 3v18h18M7 13l4-4 3 3 5-6' },
  ];
  return (
    <>
      <div className="row-head" style={{ margin: '4px 0 0' }}><span className="sec-title">What you can do</span></div>
      <div className="grid3" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
        {tiles.map((t) => (
          <Link key={t.title} to={t.to} className={`qa ${t.cls}`}>
            <div className="deco" />
            <div className="icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={t.path} /></svg></div>
            <h4>{t.title}</h4>
            <p>{t.desc}</p>
            <span className="go">{t.go}</span>
          </Link>
        ))}
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Right rail — Pick of the week (prototype .pick)
// ─────────────────────────────────────────────────────────────────────
function PickCard({ sig }) {
  if (!sig) return null;
  const sym = sig.ticker || sig.sym || sig.symbol || '';
  const name = sig.name || sig.company || '';
  const num = (n) => (n == null ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 }));
  const reco = sig.entry ?? sig.reco_price ?? null;
  const target = sig.target ?? null;
  const upside = sig.predicted_return_pct ?? sig.expected_return
    ?? (reco > 0 && target > 0 ? ((target - reco) / reco) * 100 : null);
  return (
    <div className="pick">
      <span className="badge">★ Pick of the week</span>
      <div className="nm"><ProtoLogo sym={sym} tint={false} /><h4>{sym}{name ? ` · ${name}` : ''}</h4></div>
      <div className="pick-metrics">
        <div><div className="k">Reco</div><div className="v tnum">{num(reco)}</div></div>
        <div><div className="k">Target</div><div className="v tnum">{num(target)}</div></div>
        <div><div className="k">Upside</div><div className="v tnum">{upside == null ? '—' : fmtPct1(upside)}</div></div>
      </div>
      <Link className="pick-btn" to="/premove">Size &amp; view →</Link>
      <div className="pick-dots"><i className="on" /><i /><i /><i /></div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Right rail — Your tools (prototype .rcard .opps)
// ─────────────────────────────────────────────────────────────────────
const TOOL_ICONS = {
  sizer:   'M12 3v18M5 8l7-5 7 5',
  record:  'M3 3v18h18M7 13l4-4 3 3 5-6',
  report:  'M4 5h16v14H4zM4 10h16',
  log:     'M3 12h18M3 6h18M3 18h18',
  journal: 'M4 4h16v16H4zM8 4v16',
  method:  'M12 2a10 10 0 100 20 10 10 0 000-20zM2 12h20',
};
function ToolsCard() {
  // Only routes that actually EXIST. Three of the previous six pointed at stripped routes and
  // silently bounced the user somewhere unrelated (/pnl and /orders -> Research, /journal ->
  // Portfolio), and "Methodology" pointed at Research, which is not a methodology page — Research
  // already carries the "How calls are made" card. Portfolio was missing entirely despite being
  // the page where the user's own holdings and realized P&L live.
  const tools = [
    { to: '/premove', label: 'Position sizer', icon: 'sizer' },
    { to: '/portfolio', label: 'Your portfolio', icon: 'report' },
    { to: '/track-record', label: 'Track record', icon: 'record' },
  ];
  return (
    <div className="card rcard">
      <h4>Your tools</h4>
      <div className="opps">
        {tools.map((t) => (
          <Link key={t.label} to={t.to} className="opp">
            {t.tag && <span className="tag">{t.tag}</span>}
            <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={TOOL_ICONS[t.icon]} /></svg></div>
            <div className="lbl">{t.label}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Right rail — Morning commentary (prototype .commentary)
// ─────────────────────────────────────────────────────────────────────
function CommentaryCard({ regime, signalsCount, generatedAt }) {
  const raw = (regime?.status || '').toLowerCase();
  if (!raw) return null;
  const label = raw.includes('bull') ? 'Bullish' : raw.includes('bear') ? 'Bearish' : 'Choppy';
  const breadth = regime?.breadth;
  const dateLabel = generatedAt
    ? new Date(generatedAt).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
    : null;
  return (
    <div className="commentary">
      <div className="tag">Model note{dateLabel ? ` · ${dateLabel}` : ''}</div>
      <h4>The market is {label} today.</h4>
      <p>
        {breadth != null ? `Breadth ${breadth >= 0 ? '+' : ''}${breadth} adv−dec. ` : ''}
        {signalsCount > 0 ? `${signalsCount} names cleared the conviction gate this scan.` : 'No fresh buys cleared the gate this scan.'}
        {' '}No manual action — the book posts itself.
      </p>
      <div className="date">◷ Systematic book</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Right rail — Model health (prototype .rcard .statline/.mini-bar)
// ─────────────────────────────────────────────────────────────────────
function ModelHealthCard({ cronHealth, metrics, portfolio }) {
  const ranToday = cronHealth?.last_run_today;
  const winRate  = metrics?.win_rate ?? null;
  const sharpe   = metrics?.sharpe_ratio ?? null;
  const drawdown = portfolio?.drawdown_pct ?? null;
  const trades   = metrics?.total_trades ?? null;
  const gatePct  = trades != null ? Math.min(100, Math.round((trades / 30) * 100)) : null;

  return (
    <div className="card rcard">
      <h4>Model health · today</h4>
      <div className="statline"><span className="k">Daily cron</span><span className={`v ${ranToday ? 'bull' : 'warn'}`}>{ranToday ? '● Ran today' : 'Pending'}</span></div>
      <div className="statline"><span className="k">Win rate</span><span className="v tnum">{winRate != null ? `${Number(winRate).toFixed(1)}%` : '—'}</span></div>
      <div className="statline"><span className="k">Sharpe (paper)</span><span className="v tnum">{sharpe != null ? Number(sharpe).toFixed(2) : '—'}</span></div>
      <div className="statline"><span className="k">Max drawdown</span><span className="v bear tnum">{drawdown != null ? fmtPct(-Math.abs(drawdown)) : '—'}</span></div>
      {gatePct != null && (
        <div className="statline"><span className="k">{trades} of 30 paper gate</span><span className="v"><div className="mini-bar"><i style={{ width: `${gatePct}%` }} /></div></span></div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Right rail — Sector breadth (prototype .rcard .bubble-stage)
// ─────────────────────────────────────────────────────────────────────
const SECTOR_LAYOUT = [
  { top: 6,   left: 8,   size: 74 },
  { top: 16,  left: 162, size: 60 },
  { top: 118, left: 6,   size: 52 },
  { top: 116, left: 122, size: 46 },
  { top: 138, left: 216, size: 40 },
];
const BUBBLE_TONES = ['bub-bull', 'bub-info', 'bub-violet', 'bub-warn', 'bub-info'];
// config.SECTOR_MAP uses underscore compounds (e.g. "Finance_NBFC") for the
// data layer; render as "Finance/NBFC" so the bubble label reads naturally.
const formatSectorLabel = (name) => name.replace(/_/g, '/');

function SectorCard({ signals }) {
  const derived = useMemo(() => {
    if (!signals?.length) return [];
    const map = new Map();
    for (const s of signals) map.set(s.sector || 'Other', (map.get(s.sector || 'Other') || 0) + 1);
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5)
      .map(([name, count], i) => ({ name, count, ...(SECTOR_LAYOUT[i] || { top: 100 + i * 30, left: 50, size: 40 }), tone: BUBBLE_TONES[i] }));
  }, [signals]);

  return (
    <div className="card rcard">
      <h4>Sector breadth</h4>
      {derived.length === 0 ? (
        <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>No candidates yet — the book is rebuilt at the Saturday 6:00 PM IST scan.</div>
      ) : (
        <div className="bubble-stage">
          {derived.map((s) => {
            // Sector names range from "IT" to "Infrastructure" — scale the
            // label font down for smaller bubbles and cap its width so it
            // wraps within the circle instead of overflowing into whatever
            // bubble sits next to it.
            const labelSize = Math.max(6.5, Math.min(8.5, s.size * 0.16));
            return (
              <div key={s.name} className={`bubble ${s.tone}`} style={{ width: s.size, height: s.size, left: s.left, top: s.top }} title={`${formatSectorLabel(s.name)} · ${s.count}`}>
                <div style={{ maxWidth: Math.max(s.size - 12, 24) }}>
                  <div className="n">{s.count}</div>
                  <div className="l" style={{ fontSize: labelSize }}>{formatSectorLabel(s.name)}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Scan status ribbon — prototype .scan-status
// ─────────────────────────────────────────────────────────────────────
function ScanStatus({ cronHealth, signalsCount }) {
  return (
    <div className="scan-status">
      <span className="dot" />
      <div>
        <div className="ss-head">{cronHealth?.last_run_today ? "Latest scan ran on schedule" : 'Next scan Saturday 6:00 PM IST'}{signalsCount ? ` · ${signalsCount} signals` : ''}</div>
        <div className="ss-sub">Cron {cronHealth?.last_run_today ? 'healthy' : 'pending'} · book rebuilt Saturday 6:00 PM IST, open positions re-checked each trading day — no manual scan.</div>
      </div>
      <Link className="link" to="/premove">See all calls →</Link>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// DashboardV3 — main page export
// ─────────────────────────────────────────────────────────────────────
export default function DashboardV3() {
  const [tradeCard, setTradeCard] = useState(null);
  // The live book is Bhanushali (weekly-swing) — momentum is suspended
  // (2026-07-06) — so the dashboard queries 'bhanushali', same as Research.
  const signalsQuery   = useSignals({ model: 'bhanushali' });
  const watchlistQuery = useWatchlist({ model: 'bhanushali' });
  const overviewQuery  = useOverview();
  const indexQuery     = useIndexSparklines();

  // Holdings = the user's OWN self-reported positions from the execution ledger (ADR 0011 — there is
  // no broker link). Mapped to the panel's existing row shape and priced with owner quotes, exactly
  // like the Portfolio page, so the dashboard and /portfolio never disagree.
  const execQuery = useExecutionPositions();
  const openPositions = useMemo(
    () => (execQuery.data ?? []).filter((p) => (Number(p.remaining_qty) || 0) > 0),
    [execQuery.data]);
  const heldSymbols = useMemo(
    () => [...new Set(openPositions.map((p) => (p.ticker || '').toUpperCase()).filter(Boolean))].slice(0, 8),
    [openPositions]);
  const quotesQuery = useQuoteBatch(heldSymbols, { enabled: heldSymbols.length > 0 });
  const holdingsQuery = useMemo(() => ({
    isLoading: execQuery.isLoading,
    data: openPositions.slice(0, 8).map((p) => {
      const q = quotesQuery.data?.[(p.ticker || '').toUpperCase()] || null;
      const avg = Number(p.avg_buy_price) || 0;
      return {
        tradingsymbol: p.ticker,
        quantity: Number(p.remaining_qty) || 0,
        average_price: avg,
        last_price: q?.last_price != null ? Number(q.last_price) : avg,  // fall back to cost, never 0
        day_change_percentage: q?.change_pct ?? null,
      };
    }),
  }), [openPositions, quotesQuery.data, execQuery.isLoading]);

  const signals    = useMemo(() => signalsQuery.data?.signals ?? [], [signalsQuery.data]);
  const watchlist  = useMemo(() => watchlistQuery.data?.signals ?? [], [watchlistQuery.data]);
  const regime     = useMemo(() => signalsQuery.data?.regime ?? {}, [signalsQuery.data]);
  const cronHealth = useMemo(() => signalsQuery.data?.cron_health ?? {}, [signalsQuery.data]);
  const portfolio  = useMemo(() => overviewQuery.data?.portfolio ?? {}, [overviewQuery.data]);
  const metrics    = useMemo(() => overviewQuery.data?.metrics ?? {}, [overviewQuery.data]);

  const rankByGrade = (list) => [...list].sort((a, b) => {
    const ga = (a.grade || 'B')[0]; const gb = (b.grade || 'B')[0];
    if (ga !== gb) return ga < gb ? -1 : 1;
    return (b.confidence ?? b.ml_score ?? 0) - (a.confidence ?? a.ml_score ?? 0);
  });

  const top4 = useMemo(() => (signals.length ? rankByGrade(signals).slice(0, 4) : []), [signals]);
  const brewing4 = useMemo(
    () => (!signals.length && watchlist.length ? rankByGrade(watchlist).slice(0, 4) : []),
    [signals, watchlist]
  );
  const showingBrewing = top4.length === 0 && brewing4.length > 0;
  const displayCards = top4.length ? top4 : brewing4;
  const breadthSource = signals.length ? signals : watchlist;
  const indexData = indexQuery.data ?? {};
  const sigLoading = signalsQuery.isLoading || watchlistQuery.isLoading;
  // From the execution ledger, not Kite. This was gated on kite?.connected, which is permanently
  // false (ADR 0011 — no per-user broker connection), so it rendered "—/15" forever while the
  // holdings table directly below it listed the very positions it claimed not to know about.
  const heldCount = execQuery.isLoading ? null : openPositions.length;
  const scanNote = cronHealth?.last_run_today ? 'Last scan: Sat 6:00 PM IST' : 'Next scan: Sat 6:00 PM IST';

  return (
    <div className="dv3-proto" style={{ maxWidth: 1760, margin: '0 auto', padding: '18px 22px 60px' }}>
      <div className="dash-grid">
        {/* CENTER */}
        <div className="stack">
          {/* My equity net-worth removed 2026-07-13 — research-only product; users
              see their net worth on their broker, not here. */}
          <RegimeCard regime={regime} indexData={indexData} heldCount={heldCount} />

          <ScanStatus cronHealth={cronHealth} signalsCount={signals.length} />

          <div className="card panel">
            <div className="panel-head">
              <h3>{showingBrewing ? 'Brewing watchlist' : 'Research calls'}</h3>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div className="seg"><button className="on">Systematic</button></div>
                <Link className="chip-drop" to="/premove?filter=today">Fresh today ▾</Link>
              </div>
            </div>
            {!sigLoading && (
              <div className="micro" style={{ marginBottom: 10, textTransform: 'none', letterSpacing: 0, fontWeight: 500, color: 'var(--text-3)' }}>
                {signals.length > 0
                  ? `${signals.length} name${signals.length === 1 ? '' : 's'} scored above the conviction threshold · ${scanNote}`
                  : showingBrewing
                    ? `No fresh buys — ${watchlist.length} names brewing below the entry gate · ${scanNote}`
                    : `No signals from the latest scan · ${scanNote}`}
              </div>
            )}
            <div className="callgrid">
              {sigLoading ? (
                <SigCardSkeleton />
              ) : displayCards.length === 0 ? (
                <div style={{ gridColumn: '1 / -1', padding: '24px 8px', color: 'var(--text-3)', fontSize: 13 }}>
                  No high-conviction names in the current book. It is rebuilt at the Saturday 6:00 PM IST scan.
                </div>
              ) : (
                displayCards.map((sig, i) => (
                  <SigCard key={sig.ticker || sig.sym || sig.symbol} sig={sig} brewing={showingBrewing} onOpen={setTradeCard} />
                ))
              )}
            </div>
          </div>

          <HoldingsPanel holdings={holdingsQuery.data ?? []} quoteData={quotesQuery.data ?? {}} isLoading={holdingsQuery.isLoading} />

          <GlobalIndices indexData={indexData} />

          <ActionTiles />
        </div>

        {/* RIGHT RAIL */}
        <div className="rrail">
          <PickCard sig={displayCards[0]} />
          <ToolsCard />
          <CommentaryCard regime={regime} signalsCount={signals.length} generatedAt={signalsQuery.data?.generated_at} />
          <ModelHealthCard cronHealth={cronHealth} metrics={metrics} portfolio={portfolio} />
          <SectorCard signals={breadthSource} />
        </div>
      </div>

      <div className="disc">{DISCLAIMER}<br />SEBI Research Analyst · Model-generated signals · NSE data delayed 15 min · v2026.07</div>

      <TradeCardModal sig={tradeCard} open={!!tradeCard} onOpenChange={(o) => !o && setTradeCard(null)} />
    </div>
  );
}
