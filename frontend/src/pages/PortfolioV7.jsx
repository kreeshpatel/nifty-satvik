/**
 * Portfolio — design v7, product definition §13 (docs/DESIGN_BRIEF_V5.md).
 * Job: the user's OWN recorded buys/sells from our calls, priced at the daily close. Optional —
 * an empty ledger is a valid state. Per-user data only (docs/DATA_MAP.md §1):
 *   positions  GET /api/execution/positions   (avg cost, remaining qty, realised P&L — backend math)
 *   prices     useQuoteBatch (owner's daily closes)
 *   our call   /api/signals + /api/signals/history, joined by signal_id (entry / stop / target)
 *   actions    /api/execution/reconciliation (exits due vs the model's plan)
 * A holding with no price yet is shown as "no price yet" and left out of value and P&L — it is
 * never priced at cost (that read as a real 0.0%; DATA_MAP §3). Owners get a link to the model's
 * paper book (/portfolio/paper); members never see or request it.
 */
import { useContext, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthContext } from '@/context/AuthContext';
import { useExecutionPositions, useReconciliation } from '@/hooks/queries/useExecution';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { useSignals } from '@/hooks/queries/useSignals';
import useSignalHistory from '@/hooks/queries/useSignalHistory';
import { costBasisOf } from '@/lib/cards';
import { signalIdOf } from '@/lib/signalId';
import ExecutionCaptureModal from '@/components/shared/ExecutionCaptureModal';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/dashboard-v5.css';

const MINUS = '−';
const n = (v) => (v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
const fmt = (v, dp = 2) => { const x = n(v); if (x == null) return '—'; const s = Math.abs(x).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp }); return `${x < 0 ? MINUS : ''}${s}`; };
const inr = (v, dp = 0) => (n(v) == null ? '—' : `${n(v) < 0 ? MINUS : ''}₹${fmt(Math.abs(n(v)), dp)}`);
const sinr = (v, dp = 0) => (n(v) == null ? '—' : `${n(v) > 0 ? '+' : n(v) < 0 ? MINUS : ''}₹${fmt(Math.abs(n(v)), dp)}`);
const pct = (v, dp = 1) => (n(v) == null ? '—' : `${n(v) > 0 ? '▲ +' : n(v) < 0 ? `▼ ${MINUS}` : ''}${Math.abs(n(v)).toFixed(dp)}%`);
const tone = (v) => (n(v) == null || n(v) === 0 ? '' : n(v) > 0 ? 'up' : 'down');
const dmy = (d) => (d ? new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' }) : '—');

function Rail({ entry, stop, target, price }) {
  const e = n(entry), st = n(stop), t = n(target), p = n(price);
  if (e == null || st == null || t == null || t <= st) return <span className="d7-muted">—</span>;
  const span = t - st; const ePos = ((e - st) / span) * 100;
  const pPos = p == null ? null : Math.max(0, Math.min(100, ((p - st) / span) * 100));
  return (
    <span className="d7-rail" role="img" aria-label={`Stop ${fmt(st)}, entry ${fmt(e)}, target ${fmt(t)}${p != null ? `, last ${fmt(p)}` : ''}`}>
      <span className="d7-rail-risk" style={{ width: `${ePos}%` }} /><span className="d7-rail-rew" />
      <span className="d7-rail-entry" style={{ left: `${ePos}%` }} />
      {pPos != null && <span className={`d7-rail-now ${p >= e ? 'up' : 'down'}`} style={{ left: `${pPos}%` }} />}
    </span>
  );
}

function Panel({ id, title, count, meta, action, children }) {
  return (
    <section className="d7-panel" aria-labelledby={`${id}-h`}>
      <header className="d7-panel-head">
        <h2 id={`${id}-h`}>{title}</h2>{count != null && <span className="d7-count" data-num>{count}</span>}
        {meta && <span className="d7-panel-meta">{meta}</span>}{action && <span className="d7-panel-act">{action}</span>}
      </header>
      {children}
    </section>
  );
}

export default function PortfolioV7() {
  const { user } = useContext(AuthContext);
  const isAdmin = !!user?.is_admin;
  const [capture, setCapture] = useState(null);
  const ex = useExecutionPositions();
  const recon = useReconciliation();
  const sq = useSignals({ model: 'bhanushali' });
  const hq = useSignalHistory({});

  const all = useMemo(() => ex.data ?? [], [ex.data]);
  const open = useMemo(() => all.filter((p) => (Number(p.remaining_qty) || 0) > 0), [all]);
  const closed = useMemo(() => all.filter((p) => p.status === 'CLOSED'), [all]);
  const syms = useMemo(() => [...new Set(open.map((p) => (p.ticker || '').toUpperCase()).filter(Boolean))], [open]);
  const quotes = useQuoteBatch(syms, { enabled: syms.length > 0 });

  // our call for each position, by signal_id (current book first, then history)
  const calls = useMemo(() => {
    const m = new Map();
    // signals carry no signal_id field — derive it the same way the ledger keys fills
    (hq.data?.history ?? []).forEach((s) => { const id = signalIdOf(s); if (id) m.set(id, s); });
    (sq.data?.signals ?? []).forEach((s) => { const id = signalIdOf(s); if (id) m.set(id, s); });
    return m;
  }, [sq.data, hq.data]);

  const rows = useMemo(() => open.map((p) => {
    const t = (p.ticker || '').toUpperCase();
    const avg = n(costBasisOf(p)?.avg) ?? n(p.avg_buy_price);
    const qty = Number(p.remaining_qty) || 0;
    const call = calls.get(p.signal_id) || {};
    // Price: the owner's daily-close quote; else the model's own daily re-price of this call
    // (call.current_price, same close); else null = "no price yet" — never priced at cost.
    const q = n(quotes.data?.[t]?.last_price);
    const last = q ?? n(call.current_price);
    const priceSrc = q != null ? 'quote' : last != null ? 'model' : null;
    const cost = avg != null ? avg * qty : null;
    const value = last != null ? last * qty : null;
    const pnl = value != null && cost != null ? value - cost : null;
    return { p, t, avg, qty, last, priceSrc, cost, value, pnl, pnlPct: pnl != null && cost ? (pnl / cost) * 100 : null, call };
  }), [open, quotes.data, calls]);

  const priced = rows.filter((r) => r.value != null);
  const unpriced = rows.length - priced.length;
  const mv = priced.reduce((s, r) => s + r.value, 0);
  const pricedCost = priced.reduce((s, r) => s + r.cost, 0);
  const invested = rows.reduce((s, r) => s + (r.cost || 0), 0);
  const unreal = priced.length ? mv - pricedCost : null;
  const realised = all.reduce((s, p) => s + (Number(p.realized_pnl) || 0), 0);
  const wins = closed.filter((p) => Number(p.realized_pnl) > 0).length;
  const actions = recon.data?.items ?? [];
  const empty = !ex.isLoading && all.length === 0;

  return (
    <div className="d7">
      <header className="d7-head">
        <div>
          <h1>Portfolio</h1>
          <p className="d7-sub">Your recorded buys and sells from our calls · priced at the daily close · no broker link</p>
        </div>
        <p className="d7-fresh">{isAdmin && <Link to="/portfolio/paper" className="d7-link">Model paper book (owner) →</Link>}</p>
      </header>

      {actions.length > 0 && (
        <Link to="/this-week" className="d7-alert">
          <b>{actions.length} action{actions.length === 1 ? '' : 's'} on your holdings.</b>
          <span>The model’s plan versus what you recorded — exits due or missed.</span><span className="d7-alert-go">Review →</span>
        </Link>
      )}

      <dl className="d7-stats d7-stats-6" aria-label="Your book">
        <div><dt>Market value</dt><dd data-num>{priced.length ? inr(mv) : '—'}</dd><span className="d7-sub2">{unpriced ? `${unpriced} without a price yet` : `${rows.length} holding${rows.length === 1 ? '' : 's'}`}</span></div>
        <div><dt>Invested</dt><dd data-num>{rows.length ? inr(invested) : '—'}</dd><span className="d7-sub2">cost of shares held</span></div>
        <div><dt>Unrealised P&amp;L</dt><dd data-num className={tone(unreal)}>{sinr(unreal)}</dd><span className={`d7-sub2 ${tone(unreal)}`}>{pricedCost ? pct((unreal / pricedCost) * 100) : '—'}</span></div>
        <div><dt>Realised P&amp;L</dt><dd data-num className={tone(realised)}>{all.length ? sinr(realised) : '—'}</dd><span className="d7-sub2">booked on sells</span></div>
        <div><dt>Closed trades</dt><dd data-num>{closed.length}</dd><span className="d7-sub2">{closed.length ? `${wins} won · ${closed.length - wins} lost` : 'none yet'}</span></div>
        <div><dt>Open positions</dt><dd data-num>{rows.length}</dd><span className="d7-sub2">from our calls</span></div>
      </dl>

      {empty ? (
        <section className="d7-panel">
          <div className="d7-onboard">
            <h2>Track what you buy — optional.</h2>
            <p>When you buy one of our calls on your broker, record the fill here and we’ll track it at the daily close: average cost, unrealised and realised P&amp;L, and where it sits between its stop and target. Nothing is linked to your broker.</p>
            <div className="d7-onboard-cta"><Link to="/this-week" className="pf-btn">See this week’s calls</Link><Link to="/premove" className="pf-btn-2">All our calls</Link></div>
          </div>
        </section>
      ) : (
        <div className="d7-main" style={{ gap: 16 }}>
          <Panel id="hold" title="Holdings" count={ex.isLoading ? null : rows.length} meta="priced at the last daily close">
            {ex.isLoading ? <div className="d7-skel" /> : rows.length === 0 ? <p className="d7-empty">No open positions. Closed trades are below.</p> : (
              <div className="d7-tw"><table className="d7-t">
                <thead><tr>
                  <th scope="col">Symbol</th><th scope="col" className="r">Qty</th><th scope="col" className="r">Avg cost</th><th scope="col" className="r">Last close</th>
                  <th scope="col" className="r">Value</th><th scope="col" className="r">P&amp;L</th><th scope="col" className="r">%</th>
                  <th scope="col" className="d7-col-rail">Stop → target</th><th scope="col"><span className="sr-only">Actions</span></th>
                </tr></thead>
                <tbody>{rows.map((r) => (
                  <tr key={r.p.signal_id} className="d7-static">
                    <th scope="row"><Link to={`/stock/${encodeURIComponent(r.t)}`}>{r.t}</Link>{r.p.cost_basis && r.p.cost_basis !== 'none' && <span className="d7-flag" title="Cost re-based for a demerger">re-based</span>}</th>
                    <td className="r" data-num>{r.qty}</td>
                    <td className="r" data-num>{fmt(r.avg)}</td>
                    <td className="r" data-num title={r.priceSrc === 'model' ? 'Daily close from the model re-price' : undefined}>{r.last != null ? fmt(r.last) : <span className="d7-muted">no price yet</span>}</td>
                    <td className="r" data-num>{r.value != null ? inr(r.value) : '—'}</td>
                    <td className={`r ${tone(r.pnl)}`} data-num>{sinr(r.pnl)}</td>
                    <td className={`r ${tone(r.pnlPct)}`} data-num>{pct(r.pnlPct)}</td>
                    <td className="d7-col-rail"><Rail entry={r.call.entry} stop={r.call.stop} target={r.call.target} price={r.last} /></td>
                    <td className="r"><button type="button" className="d7-btn"
                      onClick={() => setCapture({ mode: 'sell', sig: { sym: r.t, signalId: r.p.signal_id, entry: r.call.entry, stop: r.call.stop, target: r.call.target } })}>Record sell</button></td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </Panel>

          <Panel id="closed" title="Closed trades" count={closed.length} meta="realised on your recorded sells">
            {closed.length === 0 ? <p className="d7-empty">No closed trades yet.</p> : (
              <div className="d7-tw"><table className="d7-t">
                <thead><tr><th scope="col">Symbol</th><th scope="col" className="r">Shares</th><th scope="col" className="r">Avg cost</th><th scope="col" className="r">Realised</th><th scope="col" className="r">%</th><th scope="col" className="r">R</th><th scope="col">Last fill</th></tr></thead>
                <tbody>{closed.map((p) => (
                  <tr key={p.signal_id} className="d7-static">
                    <th scope="row"><Link to={`/stock/${encodeURIComponent(p.ticker)}`}>{p.ticker}</Link></th>
                    <td className="r" data-num>{p.total_sold_qty}</td>
                    <td className="r" data-num>{fmt(p.avg_buy_price)}</td>
                    <td className={`r ${tone(p.realized_pnl)}`} data-num>{sinr(p.realized_pnl)}</td>
                    <td className={`r ${tone(p.realized_pnl_pct)}`} data-num>{pct(p.realized_pnl_pct)}</td>
                    <td className={`r ${tone(p.realized_r)}`} data-num>{p.realized_r != null ? `${p.realized_r > 0 ? '+' : ''}${fmt(p.realized_r)}R` : '—'}</td>
                    <td className="d7-muted" data-num>{dmy(p.last_event_at)}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </Panel>

          {priced.length > 1 && (
            <Panel id="alloc" title="Allocation" meta="share of market value">
              <table className="d7-t d7-t-compact"><tbody>{[...priced].sort((a, b) => b.value - a.value).map((r) => (
                <tr key={r.p.signal_id} className="d7-static">
                  <th scope="row">{r.t}<span className="d7-bar" aria-hidden><span style={{ width: `${(r.value / mv) * 100}%` }} /></span></th>
                  <td className="r" data-num>{((r.value / mv) * 100).toFixed(1)}%<span className="d7-qty">{inr(r.value)}</span></td>
                </tr>
              ))}</tbody></table>
            </Panel>
          )}
        </div>
      )}

      <footer className="d7-disc">{DISCLAIMER} Not SEBI-registered. These figures come only from the fills you record; we never connect to your broker.</footer>
      <ExecutionCaptureModal open={!!capture} mode={capture?.mode} sig={capture?.sig} onClose={() => setCapture(null)} />
    </div>
  );
}
