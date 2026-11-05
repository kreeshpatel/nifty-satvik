/**
 * DashboardV5 — the daily command center, design v5 "Ledger".
 * Layout follows docs/FRONTEND_SPEC.md §1/§3: it answers, in order,
 *   1. Is there anything to sell or trim right now?   (Act now)
 *   2. What is fresh to buy this week, and how good?  (Fresh buys)
 *   3. How are the holds doing vs stop and target?    (Model book)
 * Data: the same hooks DashboardV3 used — no new endpoint.
 * Compliance: no "guarantee/will/sure" wording; Nifty Satvik is NOT SEBI-registered (the V3 footer
 * said "SEBI Research Analyst" — removed); DISCLAIMER from @/lib/signalCopy.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, AlertTriangle, Clock, LineChart, TrendingUp, CircleDot, Inbox, Activity, Gauge, Sparkles } from 'lucide-react';
import { useSignals } from '@/hooks/queries/useSignals';
import { useOverview } from '@/hooks/queries/useOverview';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { useExecutionPositions, useOutstandingActions } from '@/hooks/queries/useExecution';
import { costBasisOf } from '@/lib/cards';
import { DISCLAIMER } from '@/lib/signalCopy';
import TradeCardModal from '@/components/shared/TradeCardModal';
import '@/styles/dashboard-v5.css';

const MINUS = '−';
const n = (v) => (v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
const inr = (v, dp = 2) => {
  const x = n(v); if (x == null) return '—';
  const s = Math.abs(x).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp });
  return `${x < 0 ? MINUS : ''}₹${s}`;
};
const pct = (v, dp = 1, sign = true) => {
  const x = n(v); if (x == null) return '—';
  const s = Math.abs(x).toFixed(dp);
  return `${x < 0 ? MINUS : sign && x > 0 ? '+' : ''}${s}%`;
};
const tone = (v) => (n(v) == null || n(v) === 0 ? '' : n(v) > 0 ? 'up' : 'down');
/* Direction is never colour-only (WCAG 1.4.1): a small fixed-size arrow precedes every signed move. */
const arrow = (v) => (n(v) == null || n(v) === 0 ? null : <span className="d5-arr" aria-hidden>{n(v) > 0 ? '▲' : '▼'}</span>);
const ago = (iso) => {
  if (!iso) return null;
  const t = new Date(iso).getTime(); if (Number.isNaN(t)) return null;
  const m = Math.round((Date.now() - t) / 60000);
  if (m < 60) return `${Math.max(m, 1)} min ago`;
  const h = Math.round(m / 60); if (h < 48) return `${h} h ago`;
  return `${Math.round(h / 24)} days ago`;
};
const sym = (s) => (s?.ticker || s?.symbol || s?.sym || '').toUpperCase();

/* ── small parts ─────────────────────────────────────────────────── */

function Tile({ sym: s }) {
  return <span className="d5-tile" aria-hidden>{s.slice(0, 2)}</span>;
}

function RRBar({ entry, stop, target, price }) {
  const e = n(entry), st = n(stop), t = n(target);
  if (e == null || st == null || t == null || t <= st) return null;
  const span = t - st;
  const ePos = ((e - st) / span) * 100;
  const p = n(price);
  const pPos = p == null ? null : Math.max(0, Math.min(100, ((p - st) / span) * 100));
  return (
    <div className="d5-rr" role="img" aria-label={`Stop ${inr(st)}, entry ${inr(e)}, target ${inr(t)}${p != null ? `, last ${inr(p)}` : ''}`}>
      <span className="d5-rr-risk" style={{ width: `${ePos}%` }} />
      <span className="d5-rr-rew" style={{ width: `${100 - ePos}%` }} />
      <span className="d5-rr-entry" style={{ left: `${ePos}%` }} />
      {pPos != null && <span className={`d5-rr-now ${p >= e ? 'up' : 'down'}`} style={{ left: `${pPos}%` }} />}
    </div>
  );
}

function Empty({ icon: Icon = Inbox, title, children }) {
  return (
    <div className="d5-empty">
      <Icon size={18} aria-hidden />
      <div><p className="d5-empty-t">{title}</p>{children && <p className="d5-empty-s">{children}</p>}</div>
    </div>
  );
}

function Skeleton({ rows = 3, h = 120 }) {
  return <div className="d5-skel-grid">{Array.from({ length: rows }).map((_, i) => <div key={i} className="d5-skel" style={{ height: h }} />)}</div>;
}

function Section({ title, count, hint, action, children, id }) {
  return (
    <section className="d5-sec" aria-labelledby={`${id}-h`}>
      <header className="d5-sec-head">
        <h2 id={`${id}-h`}>{title}{count != null && <span className="d5-count" data-num>{count}</span>}</h2>
        {hint && <p className="d5-sec-hint">{hint}</p>}
        {action && <div className="d5-sec-act">{action}</div>}
      </header>
      {children}
    </section>
  );
}

/* ── tiers ───────────────────────────────────────────────────────── */

function SellCard({ s, onOpen }) {
  const g = s.sell_guidance || {};
  const trim = n(g.partial_pct) != null;
  const kind = g.reason === 'stop' ? 'down' : g.tone === 'warn' ? 'warn' : 'up';
  return (
    <button type="button" className={`d5-card d5-stripe-${kind}`} onClick={() => onOpen(s)}>
      <div className="d5-card-top">
        <Tile sym={sym(s)} />
        <div className="d5-card-id"><span className="d5-sym">{sym(s)}</span><span className="d5-meta">Model holding</span></div>
        <span className={`d5-chip d5-chip-${kind}`}>{trim ? `Trim ${g.partial_pct}%` : g.reason === 'stop' ? 'Exit · stop' : 'Exit'}</span>
      </div>
      <p className="d5-sell-head">{g.headline || 'Exit recommended'}</p>
      <dl className="d5-kv">
        <div><dt>Suggested exit</dt><dd data-num>{inr(g.suggested_exit_price ?? s.current_price)}</dd></div>
        <div><dt>Entry</dt><dd data-num>{inr(s.entry)}</dd></div>
        <div><dt>Since entry</dt><dd data-num className={tone(s.current_price - s.entry)}>{n(s.entry) ? pct(((s.current_price - s.entry) / s.entry) * 100) : '—'}</dd></div>
      </dl>
      {g.note && <p className="d5-note">{g.note}</p>}
    </button>
  );
}

function BuyCard({ s, onOpen }) {
  const e = n(s.entry), st = n(s.stop), t = n(s.target);
  const up = e && t ? ((t - e) / e) * 100 : null;
  const rr = e && st && t && e > st ? (t - e) / (e - st) : null;
  const low = s.signal_conviction === 'low';
  return (
    <button type="button" className={`d5-card d5-stripe-${low ? 'warn' : 'brand'}`} onClick={() => onOpen(s)}>
      <div className="d5-card-top">
        <Tile sym={sym(s)} />
        <div className="d5-card-id"><span className="d5-sym">{sym(s)}</span><span className="d5-meta">{low ? <span className="warn">Low conviction</span> : (s.sector || 'NSE')}</span></div>
        <span className="d5-chips">
          <span className="d5-chip d5-chip-up" title="Grade">Grade {(s.grade || 'A')[0]}</span>
        </span>
      </div>
      <div className="d5-buy-mid">
        <div><p className="d5-lbl">To target</p><p className="d5-big up" data-num>{up != null ? <>{arrow(up)}{pct(up)}</> : '—'}</p></div>
        <div className="d5-right"><p className="d5-lbl">Reward : risk</p><p className="d5-big" data-num>{rr != null ? `${rr.toFixed(1)}R` : '—'}</p></div>
      </div>
      <RRBar entry={e} stop={st} target={t} price={s.current_price} />
      <dl className="d5-kv d5-kv3">
        <div><dt>Stop</dt><dd data-num className="down">{inr(st)}</dd></div>
        <div><dt>Entry</dt><dd data-num>{inr(e)}</dd></div>
        <div><dt>Target</dt><dd data-num className="up">{inr(t)}</dd></div>
      </dl>
      {s.buy_window_until && <p className="d5-note"><Clock size={12} aria-hidden /> Buy window through {s.buy_window_until}</p>}
    </button>
  );
}

function HoldRow({ s, onOpen }) {
  const e = n(s.entry), p = n(s.current_price);
  const chg = e && p ? ((p - e) / e) * 100 : null;
  return (
    <tr onClick={() => onOpen(s)} tabIndex={0} onKeyDown={(ev) => ev.key === 'Enter' && onOpen(s)}>
      <th scope="row"><span className="d5-row-id"><Tile sym={sym(s)} />{sym(s)}</span></th>
      <td data-num>{inr(e)}</td>
      <td data-num>{inr(p)}</td>
      <td data-num className={tone(chg)}>{chg != null ? <>{arrow(chg)}{pct(chg)}</> : '—'}</td>
      <td className="d5-col-rail"><RRBar entry={s.entry} stop={s.stop} target={s.target} price={p} /></td>
    </tr>
  );
}

/* ── page ────────────────────────────────────────────────────────── */

export default function DashboardV5() {
  const [card, setCard] = useState(null);
  const sq = useSignals({ model: 'bhanushali' });
  const oq = useOverview();
  const actions = useOutstandingActions();
  const exec = useExecutionPositions();

  const signals = useMemo(() => sq.data?.signals ?? [], [sq.data]);
  const regime = sq.data?.regime ?? {};
  const cron = sq.data?.cron_health ?? {};
  const metrics = oq.data?.metrics ?? {};

  const sells = useMemo(() => signals.filter((s) => s.sell_guidance), [signals]);
  const buys = useMemo(() => signals.filter((s) => s.status === 'FRESH' && !s.sell_guidance)
    .sort((a, b) => (a.signal_conviction === 'low') - (b.signal_conviction === 'low') || (n(b.crs_rank) ?? 0) - (n(a.crs_rank) ?? 0)), [signals]);
  const holds = useMemo(() => signals.filter((s) => s.status === 'ACTIVE' && !s.sell_guidance), [signals]);

  const mine = useMemo(() => (exec.data ?? []).filter((p) => (Number(p.remaining_qty) || 0) > 0), [exec.data]);
  const mineSyms = useMemo(() => [...new Set(mine.map((p) => (p.ticker || '').toUpperCase()).filter(Boolean))].slice(0, 12), [mine]);
  const quotes = useQuoteBatch(mineSyms, { enabled: mineSyms.length > 0 });

  const status = String(regime.status || '').toUpperCase();
  const regimeTone = status === 'BULL' ? 'up' : status === 'BEAR' ? 'down' : 'warn';
  const updated = ago(sq.data?.generated_at);
  const stale = sq.data?.generated_at && Date.now() - new Date(sq.data.generated_at).getTime() > 8 * 864e5;
  const missed = actions.data?.missed ?? 0;
  const due = actions.data?.exitsDue ?? 0;
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });

  return (
    <div className="d5">
      <header className="d5-hero">
        <div>
          <p className="d5-date">{today}</p>
          <h1>Command center</h1>
        </div>
        <div className="d5-fresh" title={sq.data?.generated_at || ''}>
          <span className={`d5-dot ${stale ? 'warn' : 'up'}`} aria-hidden />
          {sq.isLoading ? 'Loading scan…' : updated ? `Scan updated ${updated}` : 'Scan time unavailable'}
          {stale && <span className="d5-chip d5-chip-warn">Stale</span>}
        </div>
      </header>

      {(missed > 0 || due > 0) && (
        <Link to="/this-week" className={`d5-alert ${missed ? 'down' : ''}`}>
          <AlertTriangle size={16} aria-hidden />
          <span>
            <b>{missed ? `The model has already sold ${missed} ${missed === 1 ? 'name' : 'names'} you still hold.` : `${due} exit${due === 1 ? '' : 's'} due on your book.`}</b>
            {' '}{missed ? 'Sell the remainder at the next open.' : 'From the model’s plan versus your recorded ledger.'}
          </span>
          <ArrowRight size={16} aria-hidden className="d5-alert-go" />
        </Link>
      )}

      <section className="d5-kpis" aria-label="Market and book summary">
        <div className={`d5-kpi-hero d5-kpi-${regimeTone}`}>
          <div className="d5-kpi-hero-top">
            <p className="d5-lbl">Market regime</p>
            <span className="d5-kpi-badge" data-num>Strength {n(regime.strength) ?? '—'}/100</span>
          </div>
          <p className="d5-kpi-hero-v">{status ? status.charAt(0) + status.slice(1).toLowerCase() : '—'}</p>
          <div className="d5-meter" aria-hidden><span style={{ width: `${Math.max(0, Math.min(100, n(regime.strength) ?? 0))}%` }} /></div>
          <svg viewBox="0 0 300 60" className="d5-kpi-wave" aria-hidden preserveAspectRatio="none">
            <path d="M0 50 C40 46 60 30 100 34 S160 18 200 22 S260 6 300 10 L300 60 L0 60Z" />
          </svg>
        </div>
        <div className="d5-kpi-card">
          <span className="pf-ic cool"><Activity size={19} aria-hidden /></span>
          <div>
            <p className="d5-lbl">Breadth</p>
            <p className={`d5-kpi ${tone(regime.breadth)}`} data-num>{n(regime.breadth) == null ? '—' : <>{arrow(regime.breadth)}{n(regime.breadth) > 0 ? '+' : ''}{String(regime.breadth).replace('-', MINUS)}</>}</p>
            <p className="d5-sub">Advances − declines</p>
          </div>
        </div>
        <div className="d5-kpi-card">
          <span className="pf-ic warm"><Gauge size={19} aria-hidden /></span>
          <div>
            <p className="d5-lbl">India VIX</p>
            <p className="d5-kpi" data-num>{n(regime.vix) ? n(regime.vix).toFixed(1) : '—'}</p>
            <p className="d5-sub">{n(regime.vix) ? (regime.vix < 15 ? 'Calm' : regime.vix < 22 ? 'Normal' : 'Elevated') : 'Unavailable'}</p>
          </div>
        </div>
        <div className="d5-kpi-card">
          <span className="pf-ic up"><Sparkles size={19} aria-hidden /></span>
          <div>
            <p className="d5-lbl">This week</p>
            <p className="d5-kpi" data-num>{sq.isLoading ? '—' : buys.length}<span className="d5-kpi-unit">fresh</span>{sq.isLoading ? '' : sells.length}<span className="d5-kpi-unit">to act</span></p>
            <p className="d5-sub" data-num>{holds.length + sells.length} in the model book</p>
          </div>
        </div>
      </section>

      <div className="d5-grid">
        <div className="d5-main">
          <Section id="act" title="Act now" count={sq.isLoading ? null : sells.length}
            hint="Take-profit tranches and exits from the model book. Most urgent first.">
            {sq.isLoading ? <Skeleton rows={2} h={150} /> : sells.length === 0
              ? <Empty icon={CircleDot} title="Nothing to sell or trim.">No position in the model book has reached a target, stop or time exit.</Empty>
              : <div className="d5-cards">{[...sells].sort((a, b) => (b.sell_guidance?.urgency === 'high') - (a.sell_guidance?.urgency === 'high')).map((s) => <SellCard key={sym(s)} s={s} onOpen={setCard} />)}</div>}
          </Section>

          <Section id="buys" title="Fresh buys" count={sq.isLoading ? null : buys.length}
            hint="Buy at the open, inside the buy window. Every call has an explicit stop and target."
            action={<Link to="/premove" className="d5-link">All research <ArrowUpRight size={14} aria-hidden /></Link>}>
            {sq.isLoading ? <Skeleton rows={3} h={210} /> : buys.length === 0
              ? <Empty title="No fresh setups this week.">The model is designed to stay silent when nothing clears the bar. The weekly scan runs Saturday evening.</Empty>
              : <div className="d5-cards">{buys.map((s) => <BuyCard key={sym(s)} s={s} onOpen={setCard} />)}</div>}
          </Section>

          <Section id="holds" title="Model book" count={sq.isLoading ? null : holds.length}
            hint="Open positions in the model’s paper book. The rail runs stop → target; the dot is the last price.">
            {sq.isLoading ? <Skeleton rows={1} h={160} /> : holds.length === 0
              ? <Empty title="The model book is flat.">Positions appear here after a fresh buy fills.</Empty>
              : (
                <div className="d5-table-wrap">
                  <table className="d5-table">
                    <thead><tr><th scope="col">Symbol</th><th scope="col">Entry</th><th scope="col">Last</th><th scope="col">Since entry</th><th scope="col" className="d5-col-rail">Stop → target</th></tr></thead>
                    <tbody>{holds.map((s) => <HoldRow key={sym(s)} s={s} onOpen={setCard} />)}</tbody>
                  </table>
                </div>
              )}
          </Section>
        </div>

        <aside className="d5-rail" aria-label="Your book and model health">
          <div className="d5-panel">
            <div className="d5-panel-head"><h2>Your positions</h2><Link to="/portfolio" className="d5-link">Portfolio <ArrowUpRight size={14} aria-hidden /></Link></div>
            {exec.isLoading ? <Skeleton rows={1} h={80} /> : mine.length === 0 ? (
              <p className="d5-muted">Record a fill from any call and it appears here, priced at the daily close.</p>
            ) : (
              <ul className="d5-mine">
                {mine.slice(0, 8).map((p) => {
                  const t = (p.ticker || '').toUpperCase();
                  const avg = Number(costBasisOf(p)?.avg) || 0;
                  const last = n(quotes.data?.[t]?.last_price) ?? avg;
                  const ch = avg ? ((last - avg) / avg) * 100 : null;
                  return (
                    <li key={p.signal_id || t}>
                      <Link to={`/stock/${t}`}><span className="d5-sym">{t}</span><span className="d5-meta" data-num>{Number(p.remaining_qty)} × {inr(avg)}</span></Link>
                      <span data-num className={tone(ch)}>{ch != null ? <>{arrow(ch)}{pct(ch)}</> : '—'}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="d5-panel">
            <div className="d5-panel-head"><h2>Model health</h2></div>
            <dl className="d5-health">
              <div><dt>Weekly scan</dt><dd className={stale ? 'warn' : 'up'}>{stale ? 'Stale' : updated ? 'Current' : '—'}</dd></div>
              <div><dt>Daily re-price</dt><dd className={cron.last_run_today ? 'up' : 'warn'}>{cron.last_run_today ? 'Ran today' : 'Pending'}</dd></div>
              <div><dt>Win rate (paper)</dt><dd data-num>{n(metrics.win_rate) != null ? `${Number(metrics.win_rate).toFixed(0)}%` : '—'}</dd></div>
              <div><dt>Max drawdown (paper)</dt><dd data-num className={tone(metrics.max_drawdown)}>{n(metrics.max_drawdown) != null ? pct(metrics.max_drawdown, 1, false) : '—'}</dd></div>
            </dl>
            <p className="d5-muted">Forward paper record — not certified. Weekly recompute Saturday 18:00 IST; daily re-price on trading days.</p>
          </div>

          <nav className="d5-panel d5-quick" aria-label="Shortcuts">
            <Link to="/this-week"><TrendingUp size={16} aria-hidden />This week’s plan</Link>
            <Link to="/history"><Clock size={16} aria-hidden />Recommendation history</Link>
            <Link to="/track-record"><LineChart size={16} aria-hidden />Track record</Link>
          </nav>
        </aside>
      </div>

      <footer className="d5-disc">{DISCLAIMER}</footer>
      <TradeCardModal sig={card} open={!!card} onOpenChange={(o) => !o && setCard(null)} />
    </div>
  );
}
