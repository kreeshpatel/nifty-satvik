import React, { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import useSignalHistory from '@/hooks/queries/useSignalHistory';
import { fmtPrice } from '@/lib/format';
import '@/styles/research-insights.css';
import '@/styles/recommendation-history.css';

// Recommendation History (/history) — every weekly call the model has posted and how it actually
// performed, tracked from the entry-week Monday open, WHETHER OR NOT it was bought. This is the
// home for exited calls (target / stop / expired) so the live Research board stays about what to do
// now. Winners and losers both show — the honest record, not a curated highlight reel.

const pct1 = (n) => (n == null || Number.isNaN(n) ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%');
const rmult = (n) => (n == null || Number.isNaN(n) ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + 'R');
const fmtDate = (s) => {
  if (!s) return '—';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' });
};

const CLOSED_STATUS = new Set(['HIT_TARGET', 'HIT_STOP', 'EXPIRED', 'CLOSED', 'RESOLVED']);
const isClosed = (r) => CLOSED_STATUS.has((r.status || '').toUpperCase()) || !!r.close_date;

// The outcome badge. Reason first (target/stop/expired), then fall back to the sign of the return.
function outcomeOf(r) {
  const ret = Number(r.return_pct ?? 0);
  if (!isClosed(r)) return { key: 'running', label: 'Running', cls: 'rh-run' };
  const st = (r.status || '').toUpperCase();
  const why = (r.exit_reason || '').toLowerCase();
  if (st === 'HIT_TARGET' || why === 'target') return { key: 'win', label: 'Target', cls: 'rh-win' };
  if (st === 'HIT_STOP' || why === 'stop' || why === 'sma_break') return { key: 'loss', label: 'Stopped', cls: 'rh-loss' };
  if (st === 'EXPIRED' || why === 'time') return { key: ret >= 0 ? 'win' : 'loss', label: 'Expired', cls: ret >= 0 ? 'rh-win' : 'rh-loss' };
  return { key: ret >= 0 ? 'win' : 'loss', label: ret >= 0 ? 'Win' : 'Loss', cls: ret >= 0 ? 'rh-win' : 'rh-loss' };
}

const FILTERS = [
  { key: 'all', label: 'All', test: () => true },
  { key: 'closed', label: 'Closed', test: (r) => isClosed(r) },
  { key: 'wins', label: 'Winners', test: (r) => isClosed(r) && Number(r.return_pct ?? 0) > 0 },
  { key: 'losses', label: 'Losers', test: (r) => isClosed(r) && Number(r.return_pct ?? 0) <= 0 },
  { key: 'running', label: 'Still running', test: (r) => !isClosed(r) },
];

function Stat({ label, value, tone }) {
  return (
    <div className="rh-stat">
      <div className="rh-stat-label">{label}</div>
      <div className={`rh-stat-value tnum ${tone || ''}`}>{value}</div>
    </div>
  );
}

export default function RecommendationHistory() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState('all');
  const query = useSignalHistory({});
  const history = useMemo(() => query.data?.history ?? [], [query.data]);

  // Newest first: exit date if closed, else the signal date.
  const rows = useMemo(() => {
    const sorted = [...history].sort((a, b) => {
      const da = new Date(a.close_date || a.signal_date || 0).getTime();
      const db = new Date(b.close_date || b.signal_date || 0).getTime();
      return db - da;
    });
    const f = FILTERS.find((x) => x.key === filter) || FILTERS[0];
    return sorted.filter(f.test);
  }, [history, filter]);

  const counts = useMemo(() => {
    const c = {};
    for (const f of FILTERS) c[f.key] = history.filter(f.test).length;
    return c;
  }, [history]);

  // Summary over CLOSED calls only — a running call has no realised outcome to average.
  const stats = useMemo(() => {
    const closed = history.filter(isClosed);
    if (!closed.length) return null;
    const rets = closed.map((r) => Number(r.return_pct ?? 0));
    const wins = rets.filter((v) => v > 0);
    const avg = rets.reduce((s, v) => s + v, 0) / rets.length;
    const rs = closed.map((r) => Number(r.r_multiple)).filter((v) => !Number.isNaN(v));
    const avgR = rs.length ? rs.reduce((s, v) => s + v, 0) / rs.length : null;
    return {
      n: closed.length,
      winRate: (wins.length / closed.length) * 100,
      avg,
      avgR,
      best: Math.max(...rets),
      worst: Math.min(...rets),
    };
  }, [history]);

  const loading = query.isLoading && !history.length;

  return (
    <div className="ri-app rh-scope">
      <div className="ri-head">
        <div>
          <Link to="/premove" className="rh-back"><ArrowLeft size={14} /> Research</Link>
          <h1 className="ri-title">Recommendation History</h1>
          <p className="ri-sub">
            Every weekly call the model has posted, and how it performed from the entry-week Monday
            open — whether or not it was bought. Winners and losers both, tracked to the exit.
          </p>
        </div>
      </div>

      {stats && (
        <div className="rh-stats">
          <Stat label="Closed calls" value={stats.n} />
          <Stat label="Win rate" value={`${stats.winRate.toFixed(0)}%`} tone={stats.winRate >= 50 ? 'num-bull' : 'num-bear'} />
          <Stat label="Avg return" value={pct1(stats.avg)} tone={stats.avg >= 0 ? 'num-bull' : 'num-bear'} />
          <Stat label="Avg R" value={rmult(stats.avgR)} tone={(stats.avgR ?? 0) >= 0 ? 'num-bull' : 'num-bear'} />
          <Stat label="Best" value={pct1(stats.best)} tone="num-bull" />
          <Stat label="Worst" value={pct1(stats.worst)} tone="num-bear" />
        </div>
      )}

      <div className="ri-chips">
        {FILTERS.map((f) => (
          <button key={f.key} className={`ri-chip ${filter === f.key ? 'on' : ''}`} onClick={() => setFilter(f.key)}>
            {f.label}
            <span className="ri-chip-n">{counts[f.key] ?? 0}</span>
          </button>
        ))}
      </div>

      <div className="ri-table">
        <div className="ri-thead">
          <div>Scrip</div>
          <div className="ri-th-r">Signal</div>
          <div className="ri-th-r">Entry</div>
          <div className="ri-th-r">Exit / now</div>
          <div className="ri-th-r">Return</div>
          <div className="ri-th-r">R</div>
          <div className="ri-th-r">Outcome</div>
        </div>

        {loading && [0, 1, 2, 3].map((i) => <div key={i} className="ri-row rh-skel" />)}

        {!loading && rows.length === 0 && (
          <div className="rh-empty">No recommendations in this view yet.</div>
        )}

        {!loading && rows.map((r, i) => {
          const o = outcomeOf(r);
          const ret = Number(r.return_pct ?? 0);
          const exitPrice = isClosed(r) ? r.close_price : (r.current_price ?? r.close_price);
          const sym = r.ticker || r.sym || '';
          return (
            <div key={`${sym}-${r.signal_date}-${i}`} className="ri-row" onClick={() => sym && navigate(`/stock/${encodeURIComponent(sym)}`)}>
              <div className="ri-scrip">
                {r.grade ? <span className={`ri-grade g-${r.grade}`}>{r.grade}</span> : null}
                <div className="ri-scrip-l">
                  <div className="ri-scrip-top"><span className="ri-sym">{sym}</span></div>
                  <div className="ri-scrip-sub">{r.sector || (isClosed(r) ? `held ${r.hold_days ?? '—'}d` : 'open')}</div>
                </div>
              </div>
              <div className="ri-cell"><div className="ri-cell-main tnum">{fmtDate(r.signal_date)}</div></div>
              <div className="ri-cell"><div className="ri-cell-main tnum">{r.entry != null ? fmtPrice(r.entry) : '—'}</div></div>
              <div className="ri-cell">
                <div className="ri-cell-main tnum">{exitPrice != null ? fmtPrice(exitPrice) : '—'}</div>
                <div className="ri-cell-sub">{isClosed(r) ? fmtDate(r.close_date) : 'live'}</div>
              </div>
              <div className="ri-cell"><div className={`ri-cell-main tnum ${ret >= 0 ? 'num-bull' : 'num-bear'}`}>{pct1(ret)}</div></div>
              <div className="ri-cell"><div className={`ri-cell-main tnum ${(r.r_multiple ?? 0) >= 0 ? 'num-bull' : 'num-bear'}`}>{rmult(r.r_multiple)}</div></div>
              <div className="ri-cell"><span className={`rh-badge ${o.cls}`}>{o.label}</span></div>
            </div>
          );
        })}
      </div>

      <p className="rh-foot">
        Research and decision-support output, not investment advice. Model and backtested results are
        not indicative of future returns. Entry is the entry-week Monday open the forward book assumes;
        returns are modelled and do not include costs unless a real fill was recorded.
      </p>
    </div>
  );
}
