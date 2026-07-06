import React, { useMemo } from 'react';
import useIndexSparklines from '@/hooks/queries/useIndexSparklines';
import '@/styles/header-ticker.css';

/**
 * HeaderTicker — a live, infinitely-scrolling marquee of market indices for the
 * app top bar. Data comes from the shared useIndexSparklines query (owner-side
 * quote feed, cached). Pauses on hover; respects prefers-reduced-motion.
 *
 * Defensive on shape: the endpoint has been seen returning both
 * { last, changePct } and { ltp, change_pct }, so we read either.
 */
const LABELS = {
  NIFTY: 'NIFTY 50', NIFTY50: 'NIFTY 50', SENSEX: 'SENSEX',
  BANKNIFTY: 'BANK NIFTY', NIFTYBANK: 'BANK NIFTY',
  INDIAVIX: 'INDIA VIX', VIX: 'INDIA VIX', USDINR: 'USD/INR',
  NIFTYMIDCAP: 'NIFTY MIDCAP', NIFTYIT: 'NIFTY IT', NIFTYAUTO: 'NIFTY AUTO',
};
const ORDER = ['NIFTY', 'NIFTY50', 'SENSEX', 'BANKNIFTY', 'NIFTYBANK', 'INDIAVIX', 'VIX', 'USDINR', 'NIFTYMIDCAP', 'NIFTYIT', 'NIFTYAUTO'];

const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const pick = (o, keys) => {
  for (const k of keys) if (o && o[k] != null) return o[k];
  return null;
};

export default function HeaderTicker() {
  const { data } = useIndexSparklines();

  const items = useMemo(() => {
    if (!data || typeof data !== 'object') return [];
    const keys = Object.keys(data).sort((a, b) => {
      const ia = ORDER.indexOf(a); const ib = ORDER.indexOf(b);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
    return keys
      .map((k) => {
        const d = data[k] || {};
        const val = pick(d, ['last', 'ltp', 'value']);
        const chg = pick(d, ['changePct', 'change_pct', 'change']);
        if (!isNum(val)) return null;
        return { key: k, label: LABELS[k] || k, val, chg: isNum(chg) ? chg : 0 };
      })
      .filter(Boolean);
  }, [data]);

  // Keep the grid column occupied while loading / if the feed is unavailable.
  if (!items.length) return <span aria-hidden />;

  const row = items.concat(items); // duplicate → seamless -50% loop

  return (
    <div className="hticker" aria-label="Live market indices">
      <div className="hticker-track">
        {row.map((it, i) => (
          <span className="hticker-item" key={`${it.key}-${i}`}>
            <span className="hticker-name">{it.label}</span>
            <span className="hticker-val tabular-nums">
              {it.val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className={`hticker-chg tabular-nums ${it.chg >= 0 ? 'num-bull' : 'num-bear'}`}>
              {it.chg >= 0 ? '▲' : '▼'}{Math.abs(it.chg).toFixed(2)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
