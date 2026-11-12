/**
 * Dashboard — the daily command center, design v7 "Institutional" (docs/DESIGN_BRIEF_V5.md §10).
 * Order follows docs/FRONTEND_SPEC.md: Act now → Fresh buys → Model book. Dense ruled tables
 * (TradingView / IBKR register), mono figures, 1px dividers, colour only for signal.
 * Data: the same hooks as before — no new endpoint.
 * Compliance: Nifty Satvik is NOT SEBI-registered; DISCLAIMER from @/lib/signalCopy.
 */
import { useContext, useMemo, useState } from 'react';
import { AuthContext } from '@/context/AuthContext';
import { Link } from 'react-router-dom';
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
const fmt = (v, dp = 2) => {
  const x = n(v); if (x == null) return '—';
  const s = Math.abs(x).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp });
  return `${x < 0 ? MINUS : ''}${s}`;
};
const pct = (v, dp = 1) => {
  const x = n(v); if (x == null) return '—';
  return `${x < 0 ? '▼ ' + MINUS : x > 0 ? '▲ +' : ''}${Math.abs(x).toFixed(dp)}%`;
};
const tone = (v) => (n(v) == null || n(v) === 0 ? '' : n(v) > 0 ? 'up' : 'down');
const ago = (iso) => {
  if (!iso) return null;
  const t = new Date(iso).getTime(); if (Number.isNaN(t)) return null;
  const m = Math.round((Date.now() - t) / 60000);
  if (m < 60) return `${Math.max(m, 1)}m ago`;
  const h = Math.round(m / 60); if (h < 48) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
};
const sym = (s) => (s?.ticker || s?.symbol || s?.sym || '').toUpperCase();

/* stop → target rail: entry tick and last-price dot, to scale */
function Rail({ entry, stop, target, price }) {
  const e = n(entry), st = n(stop), t = n(target), p = n(price);
  if (e == null || st == null || t == null || t <= st) return <span className="d7-muted">—</span>;
  const span = t - st;
  const ePos = ((e - st) / span) * 100;
  const pPos = p == null ? null : Math.max(0, Math.min(100, ((p - st) / span) * 100));
  return (
    <span className="d7-rail" role="img" aria-label={`Stop ${fmt(st)}, entry ${fmt(e)}, target ${fmt(t)}${p != null ? `, last ${fmt(p)}` : ''}`}>
      <span className="d7-rail-risk" style={{ width: `${ePos}%` }} />
      <span className="d7-rail-rew" />
      <span className="d7-rail-entry" style={{ left: `${ePos}%` }} />
      {pPos != null && <span className={`d7-rail-now ${p >= e ? 'up' : 'down'}`} style={{ left: `${pPos}%` }} />}
    </span>
  );
}

function Panel({ id, title, count, meta, action, children }) {
  return (
    <section className="d7-panel" aria-labelledby={`${id}-h`}>
      <header className="d7-panel-head">
        <h2 id={`${id}-h`}>{title}</h2>
        {count != null && <span className="d7-count" data-num>{count}</span>}
        {meta && <span className="d7-panel-meta">{meta}</span>}
        {action && <span className="d7-panel-act">{action}</span>}
      </header>
      {children}
    </section>
  );
}

function Empty({ children }) { return <p className="d7-empty">{children}</p>; }
function Loading({ rows = 3 }) { return <div aria-busy="true">{Array.from({ length: rows }).map((_, i) => <div key={i} className="d7-skel" />)}</div>; }

export default function DashboardV5() {
  const [card, setCard] = useState(null);
  const sq = useSignals({ model: 'bhanushali' });
  // The paper book's metrics are OWNER-ONLY (docs/DATA_MAP.md §1): members don't request them
  // and don't see the rows.
  const { user } = useContext(AuthContext);
  const isAdmin = !!user?.is_admin;
  const oq = useOverview({ enabled: isAdmin });
  const actions = useOutstandingActions();
  const exec = useExecutionPositions();

  const signals = useMemo(() => sq.data?.signals ?? [], [sq.data]);
  const regime = sq.data?.regime ?? {};
  const cron = sq.data?.cron_health ?? {};
  const metrics = oq.data?.metrics ?? {};

  const sells = useMemo(() => [...signals.filter((s) => s.sell_guidance)]
    .sort((a, b) => (b.sell_guidance?.urgency === 'high') - (a.sell_guidance?.urgency === 'high')), [signals]);
  const buys = useMemo(() => signals.filter((s) => s.status === 'FRESH' && !s.sell_guidance)
    .sort((a, b) => (a.signal_conviction === 'low') - (b.signal_conviction === 'low') || (n(b.crs_rank) ?? 0) - (n(a.crs_rank) ?? 0)), [signals]);
  const holds = useMemo(() => signals.filter((s) => s.status === 'ACTIVE' && !s.sell_guidance), [signals]);

  const mine = useMemo(() => (exec.data ?? []).filter((p) => (Number(p.remaining_qty) || 0) > 0), [exec.data]);
  const mineSyms = useMemo(() => [...new Set(mine.map((p) => (p.ticker || '').toUpperCase()).filter(Boolean))].slice(0, 12), [mine]);
  const quotes = useQuoteBatch(mineSyms, { enabled: mineSyms.length > 0 });

  const status = String(regime.status || '').toUpperCase();
  const regimeTone = status === 'BULL' ? 'up' : status === 'BEAR' ? 'down' : 'warn';
  const gen = sq.data?.generated_at;
  const stale = gen && Date.now() - new Date(gen).getTime() > 8 * 864e5;
  const missed = actions.data?.missed ?? 0;
  const due = actions.data?.exitsDue ?? 0;
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  const strength = Math.max(0, Math.min(100, n(regime.strength) ?? 0));

  return (
    <div className="d7">
      <header className="d7-head">
        <div>
          <h1>Command center</h1>
          <p className="d7-sub">{today} · Weekly recompute Sat 18:00 IST · Daily re-price on trading days</p>
        </div>
        <p className={`d7-fresh${stale ? ' warn' : ''}`} title={gen || ''}>
          <span className="d7-dot" aria-hidden />{sq.isLoading ? 'Loading scan…' : gen ? `Scan ${ago(gen)}${stale ? ' · stale' : ''}` : 'Scan time unavailable'}
        </p>
      </header>

      {(missed > 0 || due > 0) && (
        <Link to="/this-week" className={`d7-alert${missed ? ' down' : ''}`}>
          <b>{missed ? `The model has already sold ${missed} ${missed === 1 ? 'name' : 'names'} you still hold.` : `${due} exit${due === 1 ? '' : 's'} due on your book.`}</b>
          <span>{missed ? 'Sell the remainder at the next open.' : 'From the model’s plan versus your recorded ledger.'}</span>
          <span className="d7-alert-go">Review →</span>
        </Link>
      )}

      <dl className="d7-stats" aria-label="Market and book summary">
        <div>
          <dt>Market regime</dt>
          <dd className={regimeTone}>{status ? status.charAt(0) + status.slice(1).toLowerCase() : '—'}</dd>
          <span className="d7-meter" aria-label={`Strength ${strength} of 100`}><span style={{ width: `${strength}%` }} /></span>
        </div>
        <div><dt>Strength</dt><dd data-num>{n(regime.strength) ?? '—'}<small>/100</small></dd></div>
        <div><dt>Breadth</dt><dd data-num className={tone(regime.breadth)}>{n(regime.breadth) == null ? '—' : `${n(regime.breadth) > 0 ? '+' : ''}${String(regime.breadth).replace('-', MINUS)}`}</dd></div>
        <div><dt>India VIX</dt><dd data-num>{n(regime.vix) ? n(regime.vix).toFixed(2) : '—'}</dd></div>
        <div><dt>Fresh buys</dt><dd data-num>{sq.isLoading ? '—' : buys.length}</dd></div>
        <div><dt>To act</dt><dd data-num className={sells.length ? 'acc' : ''}>{sq.isLoading ? '—' : sells.length}</dd></div>
      </dl>

      <div className="d7-grid">
        <div className="d7-main">
          <Panel id="act" title="Act now" count={sq.isLoading ? null : sells.length} meta="Trims and exits from the model book">
            {sq.isLoading ? <Loading rows={1} /> : sells.length === 0 ? <Empty>Nothing to sell or trim. No position has reached a target, stop or time exit.</Empty> : (
              <div className="d7-tw"><table className="d7-t">
                <thead><tr><th scope="col">Symbol</th><th scope="col">Action</th><th scope="col">Instruction</th><th scope="col" className="r">Suggested exit</th><th scope="col" className="r">Entry</th><th scope="col" className="r">Since entry</th><th scope="col"><span className="sr-only">Open</span></th></tr></thead>
                <tbody>{sells.map((s) => {
                  const g = s.sell_guidance || {};
                  const kind = g.reason === 'stop' ? 'down' : 'up';
                  const since = n(s.entry) ? ((n(s.current_price) - n(s.entry)) / n(s.entry)) * 100 : null;
                  return (
                    <tr key={sym(s)} onClick={() => setCard(s)}>
                      <th scope="row">{sym(s)}</th>
                      <td><span className={`d7-tag ${kind}`}>{n(g.partial_pct) != null ? `Trim ${g.partial_pct}%` : g.reason === 'stop' ? 'Exit · stop' : 'Exit'}</span></td>
                      <td className="d7-text">{g.headline || 'Exit recommended'}</td>
                      <td className="r" data-num>{fmt(g.suggested_exit_price ?? s.current_price)}</td>
                      <td className="r" data-num>{fmt(s.entry)}</td>
                      <td className={`r ${tone(since)}`} data-num>{pct(since)}</td>
                      <td className="r"><button type="button" className="d7-btn" onClick={(e) => { e.stopPropagation(); setCard(s); }}>Plan</button></td>
                    </tr>
                  );
                })}</tbody>
              </table></div>
            )}
          </Panel>

          <Panel id="buys" title="Fresh buys" count={sq.isLoading ? null : buys.length}
            meta={buys[0]?.buy_window_until ? `Buy at the open, through ${new Date(buys[0].buy_window_until).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}` : 'Buy at the open, inside the window'}
            action={<Link to="/premove" className="d7-link">All research →</Link>}>
            {sq.isLoading ? <Loading /> : buys.length === 0 ? <Empty>No fresh setups this week. The model stays silent when nothing clears the bar.</Empty> : (
              <div className="d7-tw"><table className="d7-t">
                <thead><tr>
                  <th scope="col">Symbol</th><th scope="col" className="r">Entry</th><th scope="col" className="r">Stop</th>
                  <th scope="col" className="r">Target</th><th scope="col" className="r">Upside</th><th scope="col" className="r">R:R</th>
                  <th scope="col" className="d7-col-rail">Stop → target</th>
                </tr></thead>
                <tbody>{buys.map((s) => {
                  const e = n(s.entry), st = n(s.stop), t = n(s.target);
                  const up = e && t ? ((t - e) / e) * 100 : null;
                  const rr = e && st && t && e > st ? (t - e) / (e - st) : null;
                  const low = s.signal_conviction === 'low';
                  return (
                    <tr key={sym(s)} onClick={() => setCard(s)}>
                      <th scope="row">{sym(s)}{(s.grade || 'A')[0] !== 'A' && <span className="d7-flag">Grade {(s.grade || '')[0]}</span>}{low && <span className="d7-flag">Low conviction</span>}</th>
                      <td className="r" data-num>{fmt(e)}</td>
                      <td className="r down" data-num>{fmt(st)}</td>
                      <td className="r up" data-num>{fmt(t)}</td>
                      <td className="r up" data-num>{pct(up)}</td>
                      <td className="r" data-num>{rr != null ? `${rr.toFixed(1)}R` : '—'}</td>
                      <td className="d7-col-rail"><Rail entry={e} stop={st} target={t} price={s.current_price} /></td>
                    </tr>
                  );
                })}</tbody>
              </table></div>
            )}
          </Panel>

          <Panel id="book" title="Model book" count={sq.isLoading ? null : holds.length} meta="Open paper positions · dot = last close">
            {sq.isLoading ? <Loading rows={2} /> : holds.length === 0 ? <Empty>The model book is flat.</Empty> : (
              <div className="d7-tw"><table className="d7-t">
                <thead><tr><th scope="col">Symbol</th><th scope="col" className="r">Entry</th><th scope="col" className="r">Last</th><th scope="col" className="r">Since entry</th><th scope="col" className="r">Stop</th><th scope="col" className="r">Target</th><th scope="col" className="d7-col-rail">Position</th></tr></thead>
                <tbody>{holds.map((s) => {
                  const e = n(s.entry), p = n(s.current_price);
                  const ch = e && p ? ((p - e) / e) * 100 : null;
                  return (
                    <tr key={sym(s)} onClick={() => setCard(s)}>
                      <th scope="row">{sym(s)}</th>
                      <td className="r" data-num>{fmt(e)}</td><td className="r" data-num>{fmt(p)}</td>
                      <td className={`r ${tone(ch)}`} data-num>{pct(ch)}</td>
                      <td className="r d7-muted" data-num>{fmt(s.stop)}</td><td className="r d7-muted" data-num>{fmt(s.target)}</td>
                      <td className="d7-col-rail"><Rail entry={s.entry} stop={s.stop} target={s.target} price={p} /></td>
                    </tr>
                  );
                })}</tbody>
              </table></div>
            )}
          </Panel>
        </div>

        <aside className="d7-side" aria-label="Your book and model health">
          <Panel id="mine" title="Your positions" action={<Link to="/portfolio" className="d7-link">Portfolio →</Link>}>
            {exec.isLoading ? <Loading rows={2} /> : mine.length === 0 ? (
              <Empty>Record a fill from any call and it appears here, priced at the daily close.</Empty>
            ) : (
              <table className="d7-t d7-t-compact"><tbody>{mine.slice(0, 10).map((p) => {
                const t = (p.ticker || '').toUpperCase();
                const avg = Number(costBasisOf(p)?.avg) || 0;
                const last = n(quotes.data?.[t]?.last_price) ?? avg;
                const ch = avg ? ((last - avg) / avg) * 100 : null;
                return (
                  <tr key={p.signal_id || t}>
                    <th scope="row"><Link to={`/stock/${t}`}>{t}</Link><span className="d7-qty" data-num>{Number(p.remaining_qty)} @ {fmt(avg)}</span></th>
                    <td className={`r ${tone(ch)}`} data-num>{pct(ch)}</td>
                  </tr>
                );
              })}</tbody></table>
            )}
          </Panel>

          <Panel id="health" title="Model health">
            <dl className="d7-kv">
              <div><dt>Weekly scan</dt><dd className={stale ? 'warn' : 'up'}>{stale ? 'Stale' : gen ? 'Current' : '—'}</dd></div>
              <div><dt>Daily re-price</dt><dd className={cron.last_run_today ? 'up' : 'warn'}>{cron.last_run_today ? 'Ran today' : 'Pending'}</dd></div>
              {isAdmin && <div><dt>Win rate, paper</dt><dd data-num>{n(metrics.win_rate) != null ? `${Number(metrics.win_rate).toFixed(0)}%` : '—'}</dd></div>}
              {isAdmin && <div><dt>Max drawdown, paper</dt><dd data-num className={tone(metrics.max_drawdown)}>{n(metrics.max_drawdown) != null ? `${MINUS}${Math.abs(metrics.max_drawdown).toFixed(1)}%` : '—'}</dd></div>}
            </dl>
            <p className="d7-note">Forward paper record — not certified.</p>
          </Panel>

          <nav className="d7-panel d7-links" aria-label="Shortcuts">
            <Link to="/this-week">This week’s plan</Link>
            <Link to="/history">Recommendation history</Link>
            <Link to="/track-record">Track record</Link>
          </nav>
        </aside>
      </div>

      <footer className="d7-disc">{DISCLAIMER} Charts by TradingView Lightweight Charts™.</footer>
      <TradeCardModal sig={card} open={!!card} onOpenChange={(o) => !o && setCard(null)} />
    </div>
  );
}
