import React from 'react';

/**
 * SectionHeader — unified header grammar for container primitives.
 *
 * Replaces three current treatments scattered across primitives:
 *   - KPICard / MetricCard:  t-ui-micro UPPERCASE
 *   - ChartCard / SignalCard: t-title-2 (no uppercase, no letter-spacing)
 *   - DataTable:              t-ui-subhead weight 600
 *
 * After this primitive lands, each consumer's header gets refactored to
 * use it, so the dashboard reads with one consistent label rhythm.
 *
 * Props
 * -----
 * label:   string                                  required
 * tone:    'brand'|'bull'|'bear'|'info'|'warn'|'muted'   default 'muted'
 *                                                  drives the leading dot color
 * meta:    ReactNode                               right-side meta (count, time, etc.)
 * action:  ReactNode                               far-right action (text link, chip)
 * size:    'sm' | 'md'                             default 'sm' (11px); 'md' is 13.5px for hero cards
 * className: string                                extends class on the root row
 * style:   object                                  extends root row style
 *
 * Visual: 28px tall row, dot (6×6) + label, optional meta + action on the right.
 * No background, no border — sits ON TOP of the container's surface, the
 * container owns the chrome.
 */

const TONE = {
  brand:  'var(--brand)',
  bull:   'var(--bull)',
  bear:   'var(--bear)',
  info:   'var(--info)',
  warn:   'var(--warn)',
  muted:  'var(--text-3)',
};

export function SectionHeader({
  label,
  tone = 'muted',
  meta,
  action,
  size = 'sm',
  className,
  style,
}) {
  const dotColor = TONE[tone] || TONE.muted;
  const fontSize = size === 'md' ? 13 : 11;
  const letterSpacing = size === 'md' ? '0.04em' : '0.06em';

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        minHeight: 28,
        ...style,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <span
          aria-hidden="true"
          style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: dotColor,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize,
            lineHeight: 1.2,
            fontWeight: 600,
            letterSpacing,
            textTransform: 'uppercase',
            color: 'var(--text-3)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {label}
        </span>
      </div>

      {(meta || action) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          {meta && (
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--text-3)',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {meta}
            </span>
          )}
          {action}
        </div>
      )}
    </div>
  );
}

export default SectionHeader;
