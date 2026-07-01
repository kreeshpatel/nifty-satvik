/**
 * MetricCard — standardized chrome for any informational card on the
 * stock detail page (and elsewhere) that ISN'T a chart.
 *
 * The decision-row widgets (OrderBookL2, VolumeProfile, TickerOrderHistory)
 * each define their own --surface-1 / --edge-1 / --r-card wrapper. They
 * predate this primitive; new informational cards should use this so the
 * page picks up consistent header treatment without each component
 * inventing its own.
 *
 * Header pattern (per .impeccable.md):
 * - 28px tall row
 * - left: t-ui-micro label (UPPERCASE, --text-3)
 * - right: optional meta chip (small tabular metric, --text-2)
 * - hairline below header to separate from body
 *
 * No icons-above-headings (banned admin tell). No glass surface (data
 * legibility > visual effect). Solid --surface-1, ≤ 16px radius.
 */
import React from 'react';
import { cn } from '@/lib/utils';

export function MetricCard({
  label,                  // string — UPPERCASE ui-micro label, left side of header
  meta,                   // ReactNode — optional right-aligned meta (chip, count, etc.)
  height,                 // number — fixed pixel height (e.g. 340 to align with siblings)
  scroll = true,          // when content overflows, scroll vertically inside the card
  className,
  children,
}) {
  return (
    <div
      className={cn('flex flex-col', className)}
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        boxShadow: 'var(--shadow-sm)',
        height: height ? `${height}px` : 'auto',
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      {(label || meta) && (
        <div
          className="flex items-center justify-between flex-shrink-0"
          style={{
            padding: '8px 14px',
            borderBottom: '1px solid var(--edge-1)',
            minHeight: 28,
            gap: 12,
          }}
        >
          {label && (
            <div
              className="t-ui-micro"
              style={{ color: 'var(--text-3)', letterSpacing: '0.05em', textTransform: 'uppercase' }}
            >
              {label}
            </div>
          )}
          {meta && (
            <div
              className="t-num-small"
              style={{
                color: 'var(--text-2)',
                fontFamily: 'var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
                whiteSpace: 'nowrap',
              }}
            >
              {meta}
            </div>
          )}
        </div>
      )}

      <div
        className="flex-1"
        style={{
          minHeight: 0,
          overflowY: scroll ? 'auto' : 'visible',
          overflowX: 'hidden',
        }}
      >
        {children}
      </div>
    </div>
  );
}

export default MetricCard;
