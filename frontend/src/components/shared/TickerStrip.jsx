/**
 * TickerStrip — the operational strip under the header (docs/DESIGN_BRIEF_V5.md §11–§12).
 * Real data only: index levels + intraday sparklines (useIndexSparklines — polls only during
 * NSE hours), the model schedule (last re-score, live countdown to the next publish), and data
 * freshness: when this page's data was last fetched, with a Refresh control that re-fetches
 * every active query now. When the index feed is unavailable the strip says so.
 */
import { useEffect, useState } from 'react';
import { useIsFetching, useQueryClient } from '@tanstack/react-query';
import { RotateCw } from 'lucide-react';
import Spark from '@/components/charts/Spark';
import { useIndexSparklines } from '@/hooks/queries/useIndexSparklines';
import { nextPublish, isMarketOpen, fmtIST } from '@/lib/schedule';

const ORDER = ['NIFTY 50', 'SENSEX', 'BANK NIFTY', 'FIN NIFTY', 'INDIA VIX', 'USD/INR'];
const MINUS = '−';

/** Saturday 18:00 IST = Saturday 12:30 UTC. Returns {last, next} as Date. */
export function rescoreTimes(now = new Date()) {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 12, 30));
  const back = (d.getUTCDay() - 6 + 7) % 7;
  const last = new Date(d.getTime() - back * 864e5);
  if (last > now) last.setTime(last.getTime() - 7 * 864e5);
  return { last, next: new Date(last.getTime() + 7 * 864e5) };
}
const day = (dt) => fmtIST(dt, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
const countdown = (ms) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  const d = Math.floor(s / 86400); const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60); const sec = s % 60;
  const p = (v) => String(v).padStart(2, '0');
  return `${d ? `${d}d ` : ''}${p(h)}:${p(m)}:${p(sec)}`;
};

export default function TickerStrip({ className = '' }) {
  const qc = useQueryClient();
  const idxQ = useIndexSparklines();
  const fetching = useIsFetching();
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);

  const idx = idxQ.data && typeof idxQ.data === 'object' ? idxQ.data : null;
  const items = idx ? ORDER.filter((k) => idx[k] && idx[k].ltp != null).map((k) => ({ k, ...idx[k] })) : [];
  const { last } = rescoreTimes(now);
  const pub = nextPublish(now);
  // Freshness: the newest successful fetch among the queries on this page.
  const fetchedAt = Math.max(0, ...qc.getQueryCache().getAll().map((q) => q.state.dataUpdatedAt || 0));
  const open = isMarketOpen(now);

  return (
    <div className={`tk ${className}`} role="region" aria-label="Market and data status">
      <div className="tk-in">
        <span className="tk-cell tk-status"><i className={`tk-live${open ? '' : ' off'}`} aria-hidden />{open ? 'NSE open' : 'NSE closed'}</span>
        <span className="tk-cell">Last re-score <b>{day(last)} IST</b></span>
        <span className="tk-cell">Next publish <b>{fmtIST(pub, { weekday: 'short', hour: '2-digit', minute: '2-digit' })}</b> <span className="tk-clock">in {countdown(pub - now)}</span></span>
        {items.map((it) => {
          const ch = Number(it.change_pct);
          const up = ch >= 0;
          return (
            <span className="tk-cell" key={it.k}>
              <span className="tk-name">{it.k}</span>
              <b>{Number(it.ltp).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</b>
              <span className={up ? 'tk-up' : 'tk-down'}>{up ? '▲ +' : `▼ ${MINUS}`}{Math.abs(ch).toFixed(2)}%</span>
              <Spark data={it.sparkline} width={48} height={14} tone={up ? 'up' : 'down'} />
            </span>
          );
        })}
        {idxQ.isLoading && <span className="tk-cell tk-muted">Loading index levels…</span>}
        {!idxQ.isLoading && items.length === 0 && <span className="tk-cell tk-muted">Index levels unavailable</span>}
        <span className="tk-cell tk-end">
          {fetchedAt ? <>Updated <b>{fmtIST(fetchedAt)}</b></> : 'Not yet loaded'}
          <button type="button" className="tk-refresh" onClick={() => qc.invalidateQueries()} disabled={fetching > 0}
            aria-label="Refresh data now" title="Refresh data now">
            <RotateCw size={12} aria-hidden className={fetching > 0 ? 'tk-spin' : ''} />{fetching > 0 ? 'Refreshing' : 'Refresh'}
          </button>
        </span>
      </div>
    </div>
  );
}
