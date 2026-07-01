/**
 * EmptyCard — single empty/error/loading state primitive with semantic
 * variants. Replaces the page's gray-on-gray "no data" reflex.
 *
 * The audit screenshot showed every widget on a backend-down page reading
 * the same — gray icon, gray "No data found" copy — regardless of whether
 * the cause was a transient outage, a Kite session expiry, or a genuine
 * empty result. EmptyCard makes the variant the carrier of meaning so a
 * broken backend reads warn-coral and a quiet ticker reads muted-gray.
 *
 * Variants:
 *
 * - `muted`  — default. genuine "no data yet" (e.g. user has no order
 *              history on this ticker). Uses --text-3 + --surface-2.
 *              The page is healthy; this widget is just empty.
 *
 * - `warn`   — something failed. backend timing out, Kite session expired,
 *              fetch returned an error. Uses --warn + --warn-soft. Coral,
 *              not red — bear-red is reserved for P&L semantics so backend
 *              outages don't accidentally read as a stock crashing.
 *
 * - `info`   — first-time / cold-start / "this will populate soon".
 *              Uses --info + --info-soft. Soft blue, no urgency.
 *
 * Per .impeccable.md: no icons-above-heading admin pattern, no glass.
 * Icon (when provided) sits inline with the title on a single row, not
 * stacked above. Body copy below in --text-3.
 */
import React from 'react';
import { cn } from '@/lib/utils';

const VARIANTS = {
  muted: {
    body: 'var(--surface-2)',
    border: 'var(--edge-1)',
    iconColor: 'var(--text-3)',
    titleColor: 'var(--text-2)',
  },
  warn: {
    body: 'var(--warn-soft)',
    border: 'var(--warn)',
    iconColor: 'var(--warn)',
    titleColor: 'var(--warn)',
  },
  info: {
    body: 'var(--info-soft)',
    border: 'var(--info)',
    iconColor: 'var(--info)',
    titleColor: 'var(--info)',
  },
};

export function EmptyCard({
  variant = 'muted',
  icon,                  // ReactNode — small lucide icon, optional
  title,                 // string — short label, e.g. "No order history yet"
  body,                  // string — one sentence explaining what's happening, optional
  action,                // ReactNode — optional CTA (e.g. "Reconnect Kite" button)
  height,                // number — match sibling height for grid alignment
  className,
  children,              // alternative to title/body when caller wants full control
}) {
  const v = VARIANTS[variant] || VARIANTS.muted;
  return (
    <div
      role="status"
      className={cn('flex flex-col items-center justify-center', className)}
      style={{
        background: v.body,
        border: `1px solid ${v.border}`,
        borderRadius: 'var(--r-card)',
        padding: '24px 20px',
        textAlign: 'center',
        gap: 8,
        height: height ? `${height}px` : 'auto',
        minHeight: 120,
      }}
    >
      {children || (
        <>
          {(icon || title) && (
            <div
              className="flex items-center"
              style={{ gap: 8, color: v.titleColor }}
            >
              {icon && (
                <span style={{ display: 'inline-flex', color: v.iconColor }}>
                  {icon}
                </span>
              )}
              {title && (
                <div
                  className="t-ui-subhead"
                  style={{ color: v.titleColor, fontWeight: 600 }}
                >
                  {title}
                </div>
              )}
            </div>
          )}
          {body && (
            <p
              className="t-ui-footnote"
              style={{
                color: 'var(--text-3)',
                margin: 0,
                maxWidth: '40ch',
                lineHeight: 1.5,
              }}
            >
              {body}
            </p>
          )}
          {action && <div style={{ marginTop: 4 }}>{action}</div>}
        </>
      )}
    </div>
  );
}

export default EmptyCard;
