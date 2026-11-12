/**
 * TickerStrip — the operational strip under the header (docs/DESIGN_BRIEF_V5.md §11).
 * Real data only: index levels + intraday sparklines from the public
 * GET /api/yahoo/index-sparklines, and the model's own schedule (weekly re-score Saturday
 * 18:00 IST) with a live countdown. When the index feed is unavailable the strip says so
 * rather than showing placeholder prices.
 */
import { useEffect, useState } from 'react';
import Spark from '@/components/charts/Spark';

const ORDER = ['NIFTY 50', 'SENSEX', 'BANK NIFTY', 'FIN NIFTY', 'INDIA VIX', 'USD/INR'];
const MINUS = '−';

/** Saturday 18:00 IST = Saturday 12:30 UTC. Returns {last, next} as Date. */
export function rescoreTimes(now = new Date()) {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 12, 30));
  const back = (d.getUTCDay() - 6 + 7) % 7;            // days since Saturday
  const last = new Date(d.getTime() - back * 864e5);
  if (last > now) last.setTime(last.getTime() - 7 * 864e5);
  const next = new Date(last.getTime() + 7 * 864e5);
  return { last, next };
}
const fmtIST = (dt) => dt.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false });
const countdown = (ms) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  const d = Math.floor(s / 86400); const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60); const sec = s % 60;
  const p = (v) => String(v).padStart(2, '0');
  return `${d}d ${p(h)}:${p(m)}:${p(sec)}`;
};

export default function TickerStrip({ className = '' }) {
  const [idx, setIdx] = useState(null);
  const [failed, setFailed] = useState(false);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    let alive = true;
    fetch('/api/yahoo/index-sparklines')
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => { if (alive) setIdx(d && typeof d === 'object' ? d : {}); })
      .catch(() => { if (alive) setFailed(true); });
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const { last, next } = rescoreTimes(now);
  const items = idx ? ORDER.filter((k) => idx[k] && idx[k].ltp != null).map((k) => ({ k, ...idx[k] })) : [];

  return (
    <div className={`tk ${className}`} role="region" aria-label="Market and model status">
      <div className="tk-in">
        <span className="tk-cell tk-status"><i className="tk-live" aria-hidden />Model <b>weekly swing</b></span>
        <span className="tk-cell">Last re-score <b>{fmtIST(last)} IST</b></span>
        <span className="tk-cell">Next in <b className="tk-clock" aria-live="off">{countdown(next - now)}</b></span>
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
        {!idx && !failed && <span className="tk-cell tk-muted">Loading index levels…</span>}
        {(failed || (idx && items.length === 0)) && <span className="tk-cell tk-muted">Index levels unavailable</span>}
        <span className="tk-cell tk-muted tk-end">Prices: last session · delayed</span>
      </div>
    </div>
  );
}
