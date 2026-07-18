import React from 'react';
import { Link } from 'react-router-dom';
import StockLogo from '@/components/shared/StockLogo';

/**
 * PickOfWeek — the featured "pick of the week" banner, driven by the top-ranked signal.
 * Self-contained (inline styles) so it renders on any page without a page stylesheet. Null-safe.
 *
 * Restyled 2026-07-18 (UI audit): was a magenta->purple gradient — the only element in that hue
 * family and the loudest thing on both Research and Dashboard, which read as a stock template
 * dropped into an otherwise disciplined navy/blue terminal. It now speaks the house language:
 * navy glass + a brand-blue wash + a brand accent rule to mark it as FEATURED. Built on design
 * tokens (not hex) so a future theme change carries automatically.
 */
const wrap = {
  position: 'relative', overflow: 'hidden', padding: '18px 22px', borderRadius: 20,
  background:
    'linear-gradient(135deg, rgba(79,140,255,0.16) 0%, rgba(79,140,255,0.06) 42%, var(--surface-1) 100%), var(--surface-solid-1)',
  border: '1px solid var(--brand-edge)',
  boxShadow: '0 14px 40px rgba(4,8,24,0.45), inset 0 1px 0 rgba(255,255,255,0.06)',
};

function Metric({ k, v }) {
  return (
    <div>
      <div style={{ fontSize: 9.5, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>{k}</div>
      <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)', marginTop: 3, fontVariantNumeric: 'tabular-nums' }}>{v}</div>
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
      <div style={{ position: 'absolute', right: -40, top: -40, width: 220, height: 220, borderRadius: '50%', background: 'radial-gradient(circle, rgba(79,140,255,0.20), transparent 70%)' }} />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--brand)' }}>★ Pick of the week</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10 }}>
          <StockLogo sym={sym} size={32} radius={9} />
          <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.01em', margin: 0 }}>
            {sym}{name ? ` · ${name}` : ''}{grade ? ` — Grade ${grade}` : ''}
          </h3>
        </div>
        <div style={{ display: 'flex', gap: 26, marginTop: 16, flexWrap: 'wrap' }}>
          <Metric k="Reco" v={num(reco)} />
          <Metric k="Target" v={num(target)} />
          <Metric k="Upside" v={upside == null ? '—' : (upside >= 0 ? '+' : '') + upside.toFixed(1) + '%'} />
          <Metric k="Horizon" v={horizon} />
        </div>
        <Link to={to} style={{ display: 'inline-block', marginTop: 16, padding: '9px 20px', borderRadius: 9, background: 'var(--brand)', color: 'var(--brand-fg)', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
          {ctaLabel}
        </Link>
      </div>
    </div>
  );
}
