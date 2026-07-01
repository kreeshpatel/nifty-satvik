import React from 'react';

/**
 * ConditionalBanner — full-width alert strip for transient page states.
 *
 * Consolidates inline duplicated banners across:
 *   - SignalsV2:   cron-stale + Kite-disconnect warnings
 *   - PortfolioV2: no-Kite info banner
 *   - OrdersV2 / FundsV2: no-Kite empty notices
 *
 * Sits ABOVE the main page content as a 56-72px horizontal strip with a
 * leading tone dot, label + body inline, and optional action. Renders
 * nothing when `when={false}` so consumers can pass the gating expression
 * directly without wrapping conditionals.
 *
 * Props
 * -----
 * when:    boolean             render gate; falsy → returns null
 * tone:    'warn'|'info'|'muted'   default 'warn'; drives chrome + dot
 * title:   string              short label, weight 600
 * body:    string | ReactNode  one-sentence supporting copy
 * action:  ReactNode           right-side CTA (button, link)
 * compact: boolean             tighter padding for stacking multiple banners
 * className / style:           passthrough
 */

const TONES = {
  warn: {
    bg:     'oklch(68% 0.18 40 / 0.10)',
    border: 'oklch(68% 0.18 40 / 0.32)',
    dot:    'var(--warn)',
    label:  'var(--warn)',
  },
  info: {
    bg:     'oklch(78% 0.11 230 / 0.10)',
    border: 'oklch(78% 0.11 230 / 0.32)',
    dot:    'var(--info)',
    label:  'var(--info)',
  },
  muted: {
    bg:     'var(--surface-2)',
    border: 'var(--edge-1)',
    dot:    'var(--text-3)',
    label:  'var(--text-2)',
  },
};

export function ConditionalBanner({
  when = true,
  tone = 'warn',
  title,
  body,
  action,
  compact = false,
  className,
  style,
}) {
  if (!when) return null;
  const t = TONES[tone] || TONES.warn;
  const pad = compact ? '10px 14px' : '14px 18px';
  return (
    <div
      role={tone === 'warn' ? 'alert' : 'status'}
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        padding: pad,
        background: t.bg,
        border: `1px solid ${t.border}`,
        borderRadius: 'var(--r-card)',
        marginBottom: compact ? 8 : 12,
        ...style,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: t.dot,
          flexShrink: 0,
        }}
      />
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flex: 1, minWidth: 0, flexWrap: 'wrap' }}>
        {title && (
          <span
            className="t-ui-callout"
            style={{ color: t.label, fontWeight: 600, flexShrink: 0 }}
          >
            {title}
          </span>
        )}
        {body && (
          <span
            className="t-ui-body"
            style={{ color: 'var(--text-2)', minWidth: 0 }}
          >
            {body}
          </span>
        )}
      </div>
      {action && (
        <div style={{ flexShrink: 0 }}>
          {action}
        </div>
      )}
    </div>
  );
}

export default ConditionalBanner;
