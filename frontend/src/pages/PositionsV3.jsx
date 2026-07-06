import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { Target, AlertCircle, Layers } from 'lucide-react';
import { KiteContext } from '@/App';
import { useNQPositions } from '@/hooks/queries/useNQPositions';
import { PositionCard } from '@/components/shared/PositionCard';

/**
 * PositionsV3 — the "open model positions" page (top-nav: Positions).
 *
 * Standalone view of every Nifty Satvik-tracked position, each rendered with
 * its originating signal's frame of reference (entry / stop / target / days
 * left) and live Kite P&L via PositionCard — the same card the Portfolio
 * page's "Nifty Satvik Positions" section uses, so both stay in lockstep.
 *
 * Data: useNQPositions (GET /api/positions/nq). Positions only appear once a
 * signal is actually bought through Nifty Satvik, so a fresh account shows the
 * empty state until the first buy fills.
 */
const GRID = { gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 360px), 1fr))', gap: 12 };

export default function PositionsV3() {
  const navigate = useNavigate();
  const kite = useContext(KiteContext);
  const { data, isLoading, error } = useNQPositions();
  const positions = data?.positions ?? [];

  const onSell = (position) =>
    navigate(
      `/stock/${encodeURIComponent(position.ticker)}?action=sell&qty=${position.held_qty}&signal_id=${encodeURIComponent(position.signal_id)}`,
    );

  return (
    <div style={{ padding: 'clamp(16px, 3vw, 28px)', maxWidth: 1440, margin: '0 auto', width: '100%' }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div className="t-ui-micro" style={{ color: 'var(--text-3)', letterSpacing: '0.08em' }}>
          NIFTY SATVIK · OPEN POSITIONS
        </div>
        <h1 style={{ margin: '4px 0 0', fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 26, color: 'var(--text-1)' }}>
          Positions
        </h1>
        <div style={{ marginTop: 6, fontSize: 13.5, color: 'var(--text-2)' }}>
          {positions.length > 0
            ? `${positions.length} tracked ${positions.length === 1 ? 'position' : 'positions'} — entry, stop, target, and sell guidance shown.`
            : 'Everything you buy through a signal is tracked here with full lifecycle context.'}
          {!kite?.connected && (
            <span style={{ color: 'var(--warn)' }}> · Connect Kite for live P&L.</span>
          )}
        </div>
      </div>

      {/* Body */}
      {isLoading ? (
        <div className="grid" style={GRID}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="glass-card"
              style={{ height: 168, borderRadius: 16, background: 'var(--surface-1)', border: '1px solid var(--edge-1)', opacity: 0.5 }}
            />
          ))}
        </div>
      ) : error ? (
        <div
          style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '16px 18px',
            borderRadius: 14, border: '1px solid rgba(255,180,84,0.3)', background: 'rgba(255,180,84,0.08)',
            color: 'var(--text-1)', fontSize: 14,
          }}
        >
          <AlertCircle size={18} style={{ color: 'var(--warn)' }} />
          <div>
            <div style={{ fontWeight: 600 }}>Couldn't load positions</div>
            <div style={{ fontSize: 12.5, color: 'var(--text-2)', marginTop: 2 }}>{error?.message || 'Try refreshing.'}</div>
          </div>
        </div>
      ) : positions.length === 0 ? (
        <div
          style={{
            display: 'grid', placeItems: 'center', gap: 10, padding: '48px 20px', textAlign: 'center',
            borderRadius: 16, border: '1px dashed var(--edge-2)', background: 'var(--surface-1)',
          }}
        >
          <div style={{ width: 44, height: 44, borderRadius: 12, display: 'grid', placeItems: 'center', background: 'var(--surface-2)', color: 'var(--text-3)' }}>
            <Layers size={20} />
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-1)' }}>No open positions yet</div>
          <div style={{ fontSize: 13, color: 'var(--text-2)', maxWidth: 380 }}>
            When you buy a signal through Nifty Satvik, it appears here with entry, stop,
            target and live sell guidance.
          </div>
          <button
            type="button"
            onClick={() => navigate('/premove')}
            style={{
              marginTop: 6, display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 999, border: 'none',
              background: 'var(--brand-grad)', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            <Target size={14} /> Browse research calls
          </button>
        </div>
      ) : (
        <div className="grid" style={GRID}>
          {positions.map((p) => (
            <PositionCard key={p.signal_id} position={p} onSell={onSell} />
          ))}
        </div>
      )}
    </div>
  );
}
