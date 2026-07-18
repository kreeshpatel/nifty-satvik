import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import StockLogo from '@/components/shared/StockLogo';
import { CONVICTION } from '@/lib/signalCopy';
import { fmtINR, fmtPct } from '@/lib/format';

/**
 * TradeCardModal — the "click a signal, see the trade card" popup.
 *
 * Opened by clicking a signal's name/row (Dashboard's Research calls,
 * Research Insights' calls table, the watchlist rail's Signals tab) instead
 * of jumping straight to the stock page. Shows the trade at a glance —
 * entry, stop, target, risk — with a Buy action that hands off to the
 * (existing, unchanged for now) stock detail page.
 *
 * Card color follows grade so different picks read as visually distinct
 * "cards" rather than one static template — A-grade warm (matches the
 * Pick-of-the-week treatment), B-grade cool.
 */
const GRADE_THEME = {
  A: 'linear-gradient(135deg, #8E1E63 0%, #B12A6E 45%, #6E2CC0 100%)',
  B: 'linear-gradient(135deg, #1E3A6E 0%, #1F5FA8 55%, #1E8FA8 100%)',
};

function Stat({ k, v, tone }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>{k}</div>
      <div
        style={{
          fontSize: 18, fontWeight: 700, marginTop: 4, fontVariantNumeric: 'tabular-nums',
          color: tone === 'bear' ? '#FF9EB0' : tone === 'bull' ? '#8CF0BE' : '#fff',
        }}
      >
        {v}
      </div>
    </div>
  );
}

export default function TradeCardModal({ sig, open, onOpenChange }) {
  const navigate = useNavigate();
  if (!sig) return null;

  const sym = sig.ticker || sig.sym || sig.symbol || '??';
  const name = sig.name || sym;
  const sector = sig.sector || '—';
  const grade = (sig.grade || 'B')[0].toUpperCase();
  const entry = sig.entry ?? 0;
  const stop = sig.stop_loss ?? sig.stop ?? entry;
  const target = sig.target ?? entry;
  const risk = Math.max(0, entry - stop);
  const upsidePct = entry > 0 && target > 0 ? ((target - entry) / entry) * 100 : null;
  const rr = risk > 0 ? (target - entry) / risk : null;
  const conv = grade === 'A' ? CONVICTION.HIGH : CONVICTION.MED;

  // Research-only (2026-07-13): no in-app order pad. Both CTAs open the stock's
  // levels/chart page; the user places the order on their broker.
  const goDetails = () => {
    onOpenChange(false);
    navigate(`/stock/${encodeURIComponent(sym)}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-0 bg-transparent shadow-none p-0" style={{ maxWidth: 380 }}
                     srTitle={sig ? `${sig.sym || sig.ticker} — trade card` : 'Trade card'}>
        <div
          style={{
            position: 'relative', overflow: 'hidden', borderRadius: 20, padding: '22px 24px 24px',
            background: GRADE_THEME[grade] || GRADE_THEME.B,
            boxShadow: '0 20px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.14)',
          }}
        >
          <div style={{ position: 'absolute', right: -40, top: -40, width: 220, height: 220, borderRadius: '50%', background: 'radial-gradient(circle, rgba(255,255,255,0.22), transparent 68%)' }} />
          <div style={{ position: 'relative', zIndex: 1 }}>
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.85)' }}>
              Trade card
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10 }}>
              <StockLogo sym={sym} size={38} radius={10} />
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <h3 style={{ fontSize: 19, fontWeight: 700, color: '#fff', letterSpacing: '-0.01em', margin: 0 }}>{sym}</h3>
                  <span
                    style={{
                      fontSize: 11, fontWeight: 700, padding: '2px 7px', borderRadius: 6,
                      background: 'rgba(255,255,255,0.18)', color: '#fff',
                    }}
                  >
                    Grade {grade}
                  </span>
                </div>
                <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.78)', marginTop: 2 }}>
                  {name !== sym ? `${name} · ` : ''}{sector}
                </div>
              </div>
            </div>

            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.85)', marginTop: 12 }}>
              {conv.label}{upsidePct != null ? ` · potential ${fmtPct(upsidePct, 1)} to target` : ''}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px 12px', marginTop: 18 }}>
              <Stat k="Entry" v={fmtINR(entry)} />
              <Stat k="Stop" v={fmtINR(stop)} tone="bear" />
              <Stat k="Target" v={fmtINR(target)} tone="bull" />
              <Stat k="Risk / share" v={fmtINR(risk)} />
              <Stat k="Reward : risk" v={rr != null ? `${rr.toFixed(1)}R` : '—'} />
              <Stat k="Upside" v={upsidePct != null ? fmtPct(upsidePct, 1) : '—'} tone="bull" />
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 22 }}>
              <button
                type="button"
                onClick={goDetails}
                style={{
                  flex: 1, padding: '11px 0', borderRadius: 10, border: 'none', cursor: 'pointer',
                  background: '#fff', color: '#1a1a2e', fontSize: 14, fontWeight: 700,
                }}
              >
                View {sym} levels →
              </button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
