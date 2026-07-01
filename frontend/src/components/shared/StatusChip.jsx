import React from 'react';
import { cn } from '@/lib/utils';

/**
 * StatusChip — 6px-radius pill marker for signal + order lifecycle state.
 *
 * Semantic colors driven by tone prop, not hard-coded — flipping the theme
 * propagates without grepping components. 10px uppercase text with tracking
 * matches the .t-ui-micro scale token. NOT rounded-full (pill looks
 * gamified). NOT border-left-stripe (impeccable absolute ban).
 *
 * Tones map to semantic tokens defined in styles/tokens.css:
 *   info  → FRESH signals, informational banners
 *   brand → IN_ZONE, user-selected, active filter
 *   warn  → CHASE, near-stop, session-expired
 *   bull  → FILLED, HIT_TARGET, positive outcome
 *   bear  → REJECTED, HIT_STOP, negative outcome
 *   muted → EXPIRED, CANCELLED, resting
 */
const TONE_STYLES = {
  info:  { bg: 'var(--info-soft)',  fg: 'var(--info)',  edge: 'rgba(91, 199, 255, 0.36)' },
  brand: { bg: 'var(--brand-soft)', fg: 'var(--brand-hi)', edge: 'var(--brand-edge)' },
  warn:  { bg: 'var(--warn-soft)',  fg: 'var(--warn)',  edge: 'rgba(255, 180, 84, 0.32)' },
  bull:  { bg: 'var(--bull-soft)',  fg: 'var(--bull)',  edge: 'rgba(63, 221, 138, 0.36)' },
  bear:  { bg: 'var(--bear-soft)',  fg: 'var(--bear)',  edge: 'rgba(255, 92, 122, 0.32)' },
  muted: { bg: 'var(--surface-3)',  fg: 'var(--text-3)', edge: 'var(--edge-1)' },
};

export function StatusChip({ tone = 'muted', children, className, as: Tag = 'span' }) {
  const t = TONE_STYLES[tone] ?? TONE_STYLES.muted;
  return (
    <Tag
      className={cn('t-ui-micro inline-flex items-center', className)}
      style={{
        background: t.bg,
        color: t.fg,
        border: `1px solid ${t.edge}`,
        borderRadius: 'var(--r-chip)',
        padding: '3px 8px',
        letterSpacing: '0.06em',
      }}
    >
      {children}
    </Tag>
  );
}

export default StatusChip;
