import React from 'react';
import { cn } from '@/lib/utils';

/**
 * SellGuidanceBanner — inline notice attached to a NQ position when
 * the system has detected an exit trigger (target / stop / time).
 *
 * Tone follows the V2 semantic palette:
 *   target  → bull (green)  — congratulatory exit, celebrate the gain
 *   stop    → bear (red)    — urgent, exit at market
 *   time    → warn (coral)  — informational, no urgency
 *
 * Props
 * -----
 * guidance:  { reason, tone, headline, suggested_exit_price, urgency } | null
 * lastPrice: optional — current LTP, used to render "vs current ₹X" footer
 * onSell:    callback when the user clicks the SELL button. Wires through
 *            to the existing OrderPad pre-filled with side='SELL' and the
 *            held qty (caller is responsible for that wiring).
 *
 * Renders nothing when guidance is null — safe to drop into any card.
 */
const TONE_BG = {
  bull: { bg: 'var(--bull-soft)', fg: 'var(--bull)', edge: 'oklch(72% 0.19 145 / 0.45)' },
  bear: { bg: 'var(--bear-soft)', fg: 'var(--bear)', edge: 'oklch(66% 0.21 25 / 0.45)' },
  warn: { bg: 'var(--warn-soft)', fg: 'var(--warn)', edge: 'oklch(68% 0.18 40 / 0.45)' },
};

const fmtRupees = (n) =>
  n == null ? '—' : `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

export function SellGuidanceBanner({ guidance, lastPrice, onSell, className }) {
  if (!guidance) return null;
  const tone = TONE_BG[guidance.tone] ?? TONE_BG.warn;
  const isUrgent = guidance.urgency === 'high';

  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 px-3 py-2',
        className
      )}
      style={{
        background: tone.bg,
        color: tone.fg,
        border: `1px solid ${tone.edge}`,
        borderRadius: 'var(--r-chip)',
      }}
    >
      <div className="min-w-0 flex-1">
        <div className="t-ui text-[13px] font-medium leading-tight" style={{ color: tone.fg }}>
          {guidance.headline}
        </div>
        {(guidance.suggested_exit_price != null || lastPrice != null) && (
          <div
            className="t-ui-micro mt-0.5 opacity-80"
            style={{ color: tone.fg }}
          >
            Suggested exit {fmtRupees(guidance.suggested_exit_price)}
            {lastPrice != null && (
              <span className="ml-2 opacity-70">· current {fmtRupees(lastPrice)}</span>
            )}
          </div>
        )}
      </div>
      {onSell && (
        <button
          type="button"
          onClick={onSell}
          className={cn(
            't-ui-micro shrink-0 rounded-[var(--r-chip)] px-3 py-1.5 transition-colors',
            'border focus-visible:outline-none focus-visible:ring-2',
            isUrgent ? 'animate-pulse' : ''
          )}
          style={{
            background: tone.fg,
            color: 'var(--surface-0)',
            borderColor: tone.fg,
            letterSpacing: '0.06em',
          }}
        >
          SELL NOW
        </button>
      )}
    </div>
  );
}

export default SellGuidanceBanner;
