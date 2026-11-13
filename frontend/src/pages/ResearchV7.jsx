/**
 * Research — product definition §13 (docs/DESIGN_BRIEF_V5.md): ONLY the calls we have issued and
 * how each has done since issue. Shared model data (docs/DATA_MAP.md §1).
 * Source: GET /api/signals/history (useSignalHistory) — real fields, checked against the API:
 *   ticker, signal_date, entry, status (ACTIVE | HIT_STOP), exit_reason (stop | stop_part |
 *   sma_break | null), close_price/close_date, current_price, return_pct, r_multiple, net_pnl,
 *   hold_days, days_since; open rows also carry stop/target.
 * Two returns are shown because they differ: PRICE return (exit or latest price vs entry) and the
 * PLAN result in R (includes partial profit-taking along the way — e.g. a call can exit at -0.4%
 * on price yet +3.1R on the plan). Closed calls skew to losers (stops exit fast, winners run), so
 * open, closed and all-calls figures are always shown side by side.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import useSignalHistory from '@/hooks/queries/useSignalHistory';
import Spark from '@/components/charts/Spark';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/dashboard-v5.css';

const MINUS = '−';
const n = (v) => (v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
const fmt = (v, dp = 2) => { const x = n(v); if (x == null) return '—'; const s = Math.abs(x).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp }); return `${x < 0 ? MINUS : ''}${s}`; };
// |v| below the display precision reads as flat, never as "−0.0%".
const pct = (v, dp = 1) => { const x = n(v); if (x == null) return '—'; if (Math.abs(x) < 0.5 * 10 ** -dp) return `${(0).toFixed(dp)}%`; return `${x > 0 ? '▲ +' : `▼ ${MINUS}`}${Math.abs(x).toFixed(dp)}%`; };
const rr = (v) => { const x = n(v); if (x == null) return '—'; if (Math.abs(x) < 0.005) return '0.00R'; return `${x > 0 ? '+' : MINUS}${Math.abs(x).toFixed(2)}R`; };
const tone = (v) => (n(v) == null || Math.abs(n(v)) < 0.05 ? '' : n(v) > 0 ? 'up' : 'down');
const dmy = (d) => (d ? new Date(d).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', year: '2-digit' }) : '—');
const mean = (a) => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : null);

const OUTCOME = {
  stop: ['Stopped out', 'down'],
  stop_part: ['Partial profit, then stopped', 'warn'],
  sma_break: ['Trend-break exit', ''],
  target: ['Target hit', 'up'],
  time: ['Time exit', ''],
};
const outcomeOf = (r) => (r.status === 'ACTIVE' ? ['Open', 'acc'] : OUTCOME[r.exit_reason] || [r.exit_reason || 'Closed', '']);

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

export default function ResearchV7() {
  const q = useSignalHistory({});
  const [view, setView] = useState('all');
  const [find, setFind] = useState('');
  const rows = useMemo(() => [...(q.data?.history ?? [])].sort((a, b) => String(b.signal_date).localeCompare(String(a.signal_date))), [q.data]);
  const open = rows.filter((r) => r.status === 'ACTIVE');
  const closed = rows.filter((r) => r.status !== 'ACTIVE');
  const ret = (arr) => arr.map((r) => n(r.return_pct)).filter((v) => v != null);
  const allRet = ret(rows);
  const closedR = closed.map((r) => n(r.r_multiple)).filter((v) => v != null);
  const latestWeek = rows[0]?.signal_date;

  const shown = rows.filter((r) => (view === 'open' ? r.status === 'ACTIVE' : view === 'closed' ? r.status !== 'ACTIVE' : true))
    .filter((r) => !find || String(r.ticker).toUpperCase().includes(find.trim().toUpperCase()));
  // chronological price-return series for the strip chart (oldest → newest)
  const series = useMemo(() => [...rows].reverse().map((r) => n(r.return_pct) ?? 0), [rows]);

  return (
    <div className="d7">
      <header className="d7-head">
        <div>
          <h1>Research</h1>
          <p className="d7-sub">Every call we have issued, and how it has done since — open calls at the latest daily close, closed calls at their exit.</p>
        </div>
        <p className="d7-fresh"><span className="d7-dot" aria-hidden />{rows.length ? `${rows.length} calls since ${dmy(rows[rows.length - 1]?.signal_date)}` : 'Loading…'}</p>
      </header>

      {q.error && <div className="d7-panel"><p className="d7-empty">Couldn’t load the call history. Use Refresh in the strip above to retry.</p></div>}

      <dl className="d7-stats d7-stats-6" aria-label="Record of issued calls">
        <div><dt>Calls issued</dt><dd data-num>{q.isLoading ? '—' : rows.length}</dd><span className="d7-sub2">{open.length} open · {closed.length} closed</span></div>
        <div><dt>All calls, avg return</dt><dd data-num className={tone(mean(allRet))}>{pct(mean(allRet))}</dd><Spark data={series} width={88} height={20} bars label="Price return of each call, oldest to newest" /></div>
        <div><dt>Open, avg return</dt><dd data-num className={tone(mean(ret(open)))}>{pct(mean(ret(open)))}</dd><span className="d7-sub2">at the latest close</span></div>
        <div><dt>Closed, avg return</dt><dd data-num className={tone(mean(ret(closed)))}>{pct(mean(ret(closed)))}</dd><span className="d7-sub2">at exit, on price</span></div>
        <div><dt>Closed, plan result</dt><dd data-num className={tone(mean(closedR))}>{rr(mean(closedR))}</dd><span className="d7-sub2">avg, incl. partial exits</span></div>
        <div><dt>Positive now or at exit</dt><dd data-num>{allRet.filter((v) => v > 0).length}<small> / {allRet.length}</small></dd><span className="d7-sub2">on price return</span></div>
      </dl>

      <p className="d7-note d7-note-band">Read the open and closed figures together. Losing calls exit quickly at their stop while winning calls stay open for weeks, so closed calls on their own look worse than the record, and open calls on their own look better. This is a forward paper record, not certified.</p>

      <section className="d7-panel" aria-labelledby="calls-h">
        <header className="d7-panel-head">
          <h2 id="calls-h">Issued calls</h2><span className="d7-count" data-num>{shown.length}</span>
          <span className="d7-panel-act d7-tools">
            <span className="seg" role="tablist" aria-label="Filter calls">
              {[['all', 'All'], ['open', 'Open'], ['closed', 'Closed']].map(([k, l]) => (
                <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? 'on' : ''} onClick={() => setView(k)}>{l}</button>
              ))}
            </span>
            <input className="d7-find" type="search" placeholder="Find a symbol" aria-label="Find a symbol" value={find} onChange={(e) => setFind(e.target.value)} />
          </span>
        </header>
        {q.isLoading ? <div><div className="d7-skel" /><div className="d7-skel" /><div className="d7-skel" /></div> : shown.length === 0 ? <p className="d7-empty">No calls match.</p> : (
          <div className="d7-tw"><table className="d7-t">
            <thead><tr>
              <th scope="col">Symbol</th><th scope="col">Issued</th><th scope="col" className="r">Entry</th>
              <th scope="col" className="r">Exit / last</th><th scope="col" className="r">Days</th>
              <th scope="col" className="r">Price return</th><th scope="col" className="r">Plan result</th>
              <th scope="col">Outcome</th><th scope="col" className="d7-col-rail">Stop → target</th>
            </tr></thead>
            <tbody>{shown.map((r) => {
              const [label, t] = outcomeOf(r);
              const isOpen = r.status === 'ACTIVE';
              return (
                <tr key={`${r.ticker}-${r.signal_date}`} className="d7-static">
                  <th scope="row"><Link to={`/stock/${encodeURIComponent(r.ticker)}`}>{r.ticker}</Link>{r.signal_date === latestWeek && <span className="d7-flag">New</span>}</th>
                  <td className="d7-muted" data-num>{dmy(r.signal_date)}</td>
                  <td className="r" data-num>{fmt(r.entry)}</td>
                  <td className="r" data-num>{fmt(isOpen ? (r.current_price ?? r.close_price) : r.close_price)}<span className="d7-qty">{isOpen ? 'latest close' : dmy(r.close_date)}</span></td>
                  <td className="r d7-muted" data-num>{r.hold_days ?? r.days_since ?? '—'}</td>
                  <td className={`r ${tone(r.return_pct)}`} data-num>{pct(r.return_pct)}</td>
                  <td className={`r ${tone(r.r_multiple)}`} data-num>{isOpen ? <span className="d7-muted">open</span> : rr(r.r_multiple)}</td>
                  <td><span className={`d7-tag ${t}`}>{label}</span></td>
                  <td className="d7-col-rail">{isOpen ? <Rail entry={r.entry} stop={r.stop} target={r.target} price={r.current_price} /> : <span className="d7-muted">closed</span>}</td>
                </tr>
              );
            })}</tbody>
          </table></div>
        )}
      </section>

      <footer className="d7-disc">{DISCLAIMER} Not SEBI-registered. Price return = exit or latest daily close versus entry. Plan result = the call’s own R-multiple, including partial exits. Returns are before costs and taxes unless a fill was recorded.</footer>
    </div>
  );
}
