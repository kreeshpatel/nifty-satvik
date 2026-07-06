import React from 'react';
import { Link } from 'react-router-dom';
import StockLogo from '@/components/shared/StockLogo';

/**
 * PickOfWeek — the prototype's magenta "pick of the week" banner, driven by the
 * top-ranked signal of the day. Self-contained (inline styles) so it renders on
 * any page without a page stylesheet. Null-safe.
 */
const wrap = {
  position: 'relative', overflow: 'hidden', padding: '18px 22px', borderRadius: 20,
  background: 'linear-gradient(135deg, #8E1E63 0%, #B12A6E 45%, #6E2CC0 100%)',
  boxShadow: '0 14px 40px rgba(150,30,110,0.35), inset 0 1px 0 rgba(255,255,255,0.14)',
};

function Metric({ k, v }) {
  return (
    <div>
      <div style={{ fontSize: 9.5, color: 'rgba(255,255,255,0.72)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>{k}</div>
      <div style={{ fontSize: 15, fontWeight: 700, color: '#fff', marginTop: 3, fontVariantNumeric: 'tabular-nums' }}>{v}</div>
    </div>
  );
}

export default function PickOfWeek({ sig, to = '/premove', ctaLabel = 'Size & view →' }) {
  if (!sig) return null;
  const sym = sig.ticker || sig.sym || sig.symbol || '';
  const name = sig.name || sig.company || '';
  const grade = (sig.grade || '')[0] || '';
  const num = (n) => (n == null ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 }));
  const reco = sig.entry ?? sig.reco_price ?? null;
  const target = sig.target ?? null;
  let upside = sig.predicted_return_pct ?? sig.expected_return ?? null;
  if (upside == null && reco && target) upside = ((target - reco) / reco) * 100;
  const horizon = sig.hold ? `~${sig.hold}d` : (sig.horizon || '10–63d');

  return (
    <div style={wrap}>
      <div style={{ position: 'absolute', right: -40, top: -40, width: 220, height: 220, borderRadius: '50%', background: 'radial-gradient(circle, rgba(255,255,255,0.22), transparent 68%)' }} />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#fff', opacity: 0.92 }}>★ Pick of the week</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10 }}>
          <StockLogo sym={sym} size={32} radius={9} />
          <h3 style={{ fontSize: 18, fontWeight: 700, color: '#fff', letterSpacing: '-0.01em', margin: 0 }}>
            {sym}{name ? ` · ${name}` : ''}{grade ? ` — Grade ${grade}` : ''}
          </h3>
        </div>
        <div style={{ display: 'flex', gap: 26, marginTop: 16, flexWrap: 'wrap' }}>
          <Metric k="Reco" v={num(reco)} />
          <Metric k="Target" v={num(target)} />
          <Metric k="Upside" v={upside == null ? '—' : (upside >= 0 ? '+' : '') + upside.toFixed(1) + '%'} />
          <Metric k="Horizon" v={horizon} />
        </div>
        <Link to={to} style={{ display: 'inline-block', marginTop: 16, padding: '9px 20px', borderRadius: 9, background: '#fff', color: '#7a1a55', fontSize: 13, fontWeight: 700, textDecoration: 'none' }}>
          {ctaLabel}
        </Link>
      </div>
    </div>
  );
}
