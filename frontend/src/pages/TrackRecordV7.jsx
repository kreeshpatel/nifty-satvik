/**
 * Track record — design v7 (docs/DESIGN_BRIEF_V5.md §10–§12), dashboard register (d7-*).
 * Wired to GET /api/backtest/bhanushali (useBhanushaliBacktest): headline, meta (certification,
 * window, note), equity_curve, cum_r_curve, yearly, exit_reasons, recent_trades, best/worst.
 * Everything the endpoint returns is shown; nothing is invented. The certification caveat is the
 * first thing under the title — this is an in-sample backtest, not a track record of real money.
 */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useBhanushaliBacktest } from '@/hooks/queries/useBacktest';
import LwChart from '@/components/charts/LwChart';
import Spark from '@/components/charts/Spark';
import { DISCLAIMER } from '@/lib/signalCopy';
import { FALLBACK } from '@/lib/landingContent';
import '@/styles/dashboard-v5.css';

const MINUS = '−';
const n = (v) => (v == null || Number.isNaN(Number(v)) ? null : Number(v));
const fmt = (v, dp = 2) => { const x = n(v); if (x == null) return '—'; const s = Math.abs(x).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp }); return `${x < 0 ? MINUS : ''}${s}`; };
const sgn = (v, dp = 2) => { const x = n(v); if (x == null) return '—'; return `${x > 0 ? '+' : x < 0 ? MINUS : ''}${Math.abs(x).toFixed(dp)}`; };
const tone = (v) => (n(v) == null || n(v) === 0 ? '' : n(v) > 0 ? 'up' : 'down');
const REASON = { time: 'Time exit', trail: 'Trailing stop', stop: 'Stop loss', target: 'Target', eos: 'End of sample' };
const dmy = (d) => (d ? new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' }) : '—');

/** lightweight-charts needs strictly ascending, unique times — keep the last value per day. */
const series = (rows, key) => {
  const m = new Map();
  (rows || []).forEach((r) => { if (r && r.date && n(r[key]) != null) m.set(String(r.date).slice(0, 10), Number(r[key])); });
  return [...m.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map(([time, value]) => ({ time, value }));
};

function Panel({ id, title, meta, children, className = '' }) {
  return (
    <section className={`d7-panel ${className}`} aria-labelledby={`${id}-h`}>
      <header className="d7-panel-head"><h2 id={`${id}-h`}>{title}</h2>{meta && <span className="d7-panel-meta">{meta}</span>}</header>
      {children}
    </section>
  );
}

export default function TrackRecordV7() {
  const { data, isLoading, error, dataUpdatedAt } = useBhanushaliBacktest();
  const h = data?.headline ?? {};
  const meta = data?.meta ?? {};

  // Portfolio growth curve: the committed 0094 simulation (8.11x, matches the 24.7% anchor), served by
  // /api/landing-stats. NOT data.equity_curve — that is an R-compounded illustration that overstates
  // the result (10.1x) by treating overlapping trades as sequential (docs/DATA_MAP.md §3).
  const lsQ = useQuery({ queryKey: ['landing-stats'], queryFn: () => fetch('/api/landing-stats').then((r) => (r.ok ? r.json() : null)), staleTime: 60 * 60 * 1000 });
  const growth = (lsQ.data?.equity_bt && lsQ.data.equity_bt.length ? lsQ.data.equity_bt : FALLBACK.equity_bt);
  const toTime = (t) => { const v = String(t); return v.length === 7 ? `${v}-01` : v.slice(0, 10); };
  const nav = useMemo(() => growth.filter((d) => d.s != null).map((d) => ({ time: toTime(d.t), value: Number(d.s) })), [growth]);
  const bench = useMemo(() => growth.filter((d) => d.b != null).map((d) => ({ time: toTime(d.t), value: Number(d.b) })), [growth]);
  const cumR = useMemo(() => series(data?.cum_r_curve, 'cum_r'), [data?.cum_r_curve]);
  const dd = useMemo(() => { let pk = -Infinity; return nav.map((p) => { pk = Math.max(pk, p.value); return (p.value / pk - 1) * 100; }); }, [nav]);
  const navChart = useMemo(() => [
    { type: 'area', data: nav, color: '#20C4A0', title: 'Strategy' },
    { type: 'line', data: bench, color: '#7A8494', width: 1, dashed: true, title: 'Nifty 500' },
  ], [nav, bench]);
  const rChart = useMemo(() => [{ type: 'line', data: cumR, color: '#F0B429', title: 'Cum R' }], [cumR]);
  const inrFormat = useMemo(() => ({ type: 'custom', formatter: (v) => `₹${v.toFixed(0)}`, minMove: 1 }), []);

  const reasons = useMemo(() => {
    const c = data?.exit_reasons ?? {};
    const total = Object.values(c).reduce((s, v) => s + v, 0) || 1;
    return Object.entries(c).map(([k, v]) => ({ k, label: REASON[k] || k, v, pct: (v / total) * 100 })).sort((a, b) => b.v - a.v);
  }, [data?.exit_reasons]);
  const yearly = data?.yearly ?? [];
  const trades = data?.recent_trades ?? [];
  const best = data?.best_trade; const worst = data?.worst_trade;
  const start = nav[0]?.value; const end = nav[nav.length - 1]?.value;

  return (
    <div className="d7">
      <header className="d7-head">
        <div>
          <h1>Track record</h1>
          <p className="d7-sub">Weekly-swing model {meta.model_version ? `· ${meta.model_version}` : ''} · backtest {meta.window || '—'} · in-sample</p>
        </div>
        <p className="d7-fresh warn"><span className="d7-dot" aria-hidden />{meta.status ? meta.status.replace(/_/g, ' ').toLowerCase() : 'status —'}</p>
      </header>

      <div className="d7-alert" role="note">
        <b>Not a certified or forward-verified track record.</b>
        <span>{meta.certification || 'In-sample simulation; below the certification bar.'} {meta.note || ''}</span>
      </div>

      {isLoading && <div className="d7-panel"><div className="d7-skel" /><div className="d7-skel" /><div className="d7-skel" /></div>}
      {error && <div className="d7-panel"><p className="d7-empty">Couldn’t load the backtest ({error.message || 'request failed'}). Use Refresh in the strip above to retry.</p></div>}

      {data && !isLoading && (
        <>
          <dl className="d7-stats d7-stats-6" aria-label="Headline statistics">
            <div><dt>Net CAGR</dt><dd data-num className="up">{sgn(h.net_cagr_pct, 1)}%</dd><Spark data={nav.map((p) => p.value)} width={88} height={20} label="Equity curve" /></div>
            <div><dt>Net Sharpe</dt><dd data-num>{fmt(h.net_sharpe)}</dd><span className="d7-sub2">CI low {fmt(h.ci_low)}</span></div>
            <div><dt>Max drawdown</dt><dd data-num className="down">{fmt(h.max_dd_pct, 1)}%</dd><Spark data={dd} width={88} height={20} tone="down" label="Drawdown from peak" /></div>
            <div><dt>Win rate</dt><dd data-num>{fmt(h.win_rate_pct, 1)}%</dd><span className="d7-sub2">of {fmt(h.total_trades, 0)} trades</span></div>
            <div><dt>Cumulative R</dt><dd data-num className={tone(cumR[cumR.length - 1]?.value)}>{sgn(cumR[cumR.length - 1]?.value, 1)}R</dd><Spark data={cumR.map((p) => p.value)} width={88} height={20} label="Cumulative R" /></div>
            <div><dt>DSR</dt><dd data-num className="acc">{fmt(h.dsr, 3)}</dd><span className="d7-sub2">certification bar 0.95</span></div>
          </dl>

          <div className="d7-grid">
            <div className="d7-main">
              <Panel id="nav" title="Growth of ₹100" meta={`₹${fmt(start, 0)} → ₹${fmt(end, 0)} (${fmt(end / start, 2)}×) vs Nifty 500 · portfolio simulation, net of costs, before STCG`}>
                <div className="d7-chart"><LwChart series={navChart} height={280} priceFormat={inrFormat} label="Backtest growth of 100, strategy versus Nifty 500" /></div>
              </Panel>
              <div className="d7-two">
                <Panel id="cumr" title="Cumulative R" meta="sum of R-multiples, trade by trade">
                  <div className="d7-chart"><LwChart series={rChart} height={200} label="Cumulative R-multiple" /></div>
                </Panel>
                <Panel id="years" title="By year" meta="* partial years">
                  <div className="d7-tw"><table className="d7-t">
                    <thead><tr><th scope="col">Year</th><th scope="col" className="r">Trades</th><th scope="col" className="r">Win</th><th scope="col" className="r">Total R</th><th scope="col" className="r">Avg R</th></tr></thead>
                    <tbody>{yearly.map((y) => (
                      <tr key={y.year} className="d7-static"><th scope="row">{y.year}</th>
                        <td className="r" data-num>{y.trades}</td><td className="r" data-num>{fmt(y.win_rate, 0)}%</td>
                        <td className={`r ${tone(y.total_r)}`} data-num>{sgn(y.total_r, 1)}</td><td className={`r ${tone(y.avg_r)}`} data-num>{sgn(y.avg_r, 2)}</td></tr>
                    ))}</tbody>
                  </table></div>
                </Panel>
              </div>
              <Panel id="trades" title="Recent trades" meta={`last ${trades.length} exits · newest first`}>
                <div className="d7-tw"><table className="d7-t">
                  <thead><tr><th scope="col">Symbol</th><th scope="col">Entry</th><th scope="col" className="r">Price</th><th scope="col">Exit</th><th scope="col" className="r">Price</th><th scope="col">Reason</th><th scope="col" className="r">Weeks</th><th scope="col" className="r">R</th></tr></thead>
                  <tbody>{trades.map((t, i) => (
                    <tr key={`${t.ticker}-${t.entry_date}-${i}`} className="d7-static">
                      <th scope="row"><Link to={`/stock/${encodeURIComponent(t.ticker)}`}>{t.ticker}</Link></th>
                      <td className="d7-muted" data-num>{dmy(t.entry_date)}</td><td className="r" data-num>{fmt(t.entry)}</td>
                      <td className="d7-muted" data-num>{dmy(t.exit_date)}</td><td className="r" data-num>{fmt(t.exit_price)}</td>
                      <td><span className={`d7-tag ${t.reason === 'stop' ? 'down' : ''}`}>{REASON[t.reason] || t.reason}</span></td>
                      <td className="r d7-muted" data-num>{t.held_weeks}</td>
                      <td className={`r ${tone(t.r_multiple)}`} data-num>{sgn(t.r_multiple, 2)}</td>
                    </tr>
                  ))}</tbody>
                </table></div>
              </Panel>
            </div>

            <aside className="d7-side" aria-label="Exit mix and extremes">
              <Panel id="exits" title="How trades ended" meta={`${fmt(h.total_trades, 0)} trades`}>
                <table className="d7-t d7-t-compact"><tbody>{reasons.map((r) => (
                  <tr key={r.k} className="d7-static">
                    <th scope="row">{r.label}<span className="d7-bar" aria-hidden><span className={r.k === 'stop' ? 'down' : ''} style={{ width: `${r.pct}%` }} /></span></th>
                    <td className="r" data-num>{r.v}<span className="d7-qty">{r.pct.toFixed(0)}%</span></td>
                  </tr>
                ))}</tbody></table>
              </Panel>
              {[['Best trade', best], ['Worst trade', worst]].map(([label, t]) => t && (
                <Panel key={label} id={label.replace(' ', '-').toLowerCase()} title={label}>
                  <dl className="d7-kv">
                    <div><dt>Symbol</dt><dd data-num>{t.ticker}</dd></div>
                    <div><dt>Held</dt><dd data-num>{dmy(t.entry_date)} → {dmy(t.exit_date)}</dd></div>
                    <div><dt>Entry → exit</dt><dd data-num>{fmt(t.entry)} → {fmt(t.exit_price)}</dd></div>
                    <div><dt>Result</dt><dd data-num className={tone(t.r_multiple)}>{sgn(t.r_multiple, 2)}R · {REASON[t.reason] || t.reason}</dd></div>
                  </dl>
                </Panel>
              ))}
              <Panel id="prov" title="Provenance">
                <p className="d7-note">{meta.provenance || '—'}</p>
                <p className="d7-note">Strategy {meta.strategy || '—'}. Data loaded {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }) : '—'}; the backtest changes only when the model is re-run.</p>
              </Panel>
            </aside>
          </div>
        </>
      )}

      <footer className="d7-disc">{DISCLAIMER} Not SEBI-registered. Charts by TradingView Lightweight Charts™.</footer>
    </div>
  );
}
