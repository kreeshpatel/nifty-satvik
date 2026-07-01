/**
 * ActiveSignalStrip — surfaces an NQ signal for the current ticker.
 *
 * The killer feature of StockDetailV2: when a trader lands on /stock/RELIANCE
 * and there's an active NiftyQuant signal for RELIANCE, this strip turns the
 * page from "stock info dump" into a decision tool. Hero info: signal status,
 * entry / stop / target / R:R, and a Why? button that opens the existing
 * SignalDetailDrawer with the full v7 breakdown.
 *
 * Renders nothing if there's no signal — caller should still render the
 * component and let it self-hide. Don't add conditionals at the call site.
 */
import React from 'react';
import { Zap } from 'lucide-react';
import { StatusChip } from './StatusChip';
import { GradeBadge } from './GradeBadge';
import { fmtPrice, fmtPct } from '@/lib/format';

function statusTone(status) {
  switch ((status || '').toUpperCase()) {
    case 'FRESH':       return 'info';
    case 'IN_ZONE':
    case 'IN ZONE':     return 'brand';
    case 'CHASE':
    case 'NEAR_TARGET': return 'warn';
    case 'HIT_TARGET':
    case 'FILLED':      return 'bull';
    case 'HIT_STOP':
    case 'REJECTED':    return 'bear';
    default:            return 'muted';
  }
}

export function ActiveSignalStrip({ signal, currentPrice, onWhy, onBuy, onSell, kiteConnected = true }) {
  if (!signal) return null;

  const tone = statusTone(signal.status);
  const label = String(signal.status || 'PENDING').replace(/_/g, ' ').toUpperCase();
  const entry = Number(signal.entry) || 0;
  const stop = Number(signal.stop) || 0;
  const target = Number(signal.target) || 0;

  // Prefer explicit pcts, fall back to computed.
  const stopPct = typeof signal.stop_pct === 'number'
    ? signal.stop_pct
    : entry > 0 ? ((stop - entry) / entry) * 100 : null;
  const targetPct = typeof signal.target_pct === 'number'
    ? signal.target_pct
    : entry > 0 ? ((target - entry) / entry) * 100 : null;

  // Entry zone proximity — if currentPrice is within ±0.5% of entry, the
  // user is in the live entry zone. Show that more prominently.
  const inZone =
    typeof currentPrice === 'number' && entry > 0
      ? Math.abs((currentPrice - entry) / entry) <= 0.005
      : false;

  return (
    <section
      style={{
        background: 'var(--brand-soft)',
        border: '1px solid var(--brand-edge)',
        borderRadius: 'var(--r-card)',
        padding: '14px 18px',
        boxShadow: 'var(--shadow-sm), 0 0 0 1px var(--brand-soft)',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        flexWrap: 'wrap',
        marginBottom: 20,
      }}
    >
      <div className="flex items-center" style={{ gap: 10, minWidth: 0 }}>
        <Zap size={18} strokeWidth={1.75} style={{ color: 'var(--brand-hi)' }} />
        <div className="min-w-0">
          <div className="flex items-center" style={{ gap: 8 }}>
            <span className="t-ui-headline" style={{ color: 'var(--text-1)' }}>
              NQ Signal
            </span>
            <StatusChip tone={tone}>{label}</StatusChip>
            {inZone && <StatusChip tone="brand">IN ENTRY ZONE</StatusChip>}
            {(signal.grade || signal.v7_score != null || signal.ml_score != null) && (
              <GradeBadge
                grade={signal.grade}
                v7_score={signal.v7_score}
                ml_score={signal.ml_score}
                size="sm"
              />
            )}
          </div>
          <div
            className="t-ui-footnote"
            style={{ color: 'var(--text-3)', marginTop: 2 }}
          >
            Scanned {signal.signal_date}
            {signal.hold_days && ` · hold ≤${signal.hold_days}d`}
            {typeof signal.v7_layers_agreeing === 'number' &&
              ` · ${signal.v7_layers_agreeing}/6 pillars`}
          </div>
        </div>
      </div>

      {/* Entry / stop / target trio */}
      <div
        className="flex items-center"
        style={{ gap: 14, marginLeft: 'auto', flexWrap: 'wrap' }}
      >
        <Anchor label="ENTRY" value={fmtPrice(entry)} sub={signal.rr ? `R:R ${signal.rr.toFixed(2)}` : null} />
        <Anchor
          label="STOP"
          value={fmtPrice(stop)}
          sub={stopPct != null ? fmtPct(stopPct) : null}
          tone="bear"
        />
        <Anchor
          label="TARGET"
          value={fmtPrice(target)}
          sub={targetPct != null ? fmtPct(targetPct) : null}
          tone="bull"
        />
      </div>

      <div className="flex items-center" style={{ gap: 8 }}>
        <button
          type="button"
          onClick={onWhy}
          className="t-ui-callout"
          style={{
            padding: '8px 14px',
            background: 'transparent',
            color: 'var(--text-1)',
            border: '1px solid var(--edge-2)',
            borderRadius: 'var(--r-chip)',
            cursor: 'pointer',
            fontWeight: 500,
          }}
        >
          Why?
        </button>
        {kiteConnected && onBuy && (
          <button
            type="button"
            onClick={onBuy}
            className="t-ui-callout"
            style={{
              padding: '8px 18px',
              background: 'var(--brand)',
              color: 'var(--brand-fg)',
              border: '1px solid var(--brand)',
              borderRadius: 'var(--r-chip)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Buy
          </button>
        )}
      </div>
    </section>
  );
}

function Anchor({ label, value, sub, tone = 'neutral' }) {
  const subColor =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    'var(--text-3)';
  return (
    <div>
      <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 2 }}>
        {label}
      </div>
      <div
        className="t-num-body"
        style={{ color: 'var(--text-1)', fontSize: 14, lineHeight: 1.1 }}
      >
        {value}
      </div>
      {sub && (
        <div className="t-num-small" style={{ color: subColor, marginTop: 2 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

export default ActiveSignalStrip;
