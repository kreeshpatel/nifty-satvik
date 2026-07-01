import React from 'react';
import { cn } from '@/lib/utils';

/**
 * EmptyState — what shows when a page has nothing to render.
 *
 * The default admin-dashboard pattern is a cartoon illustration + "No data
 * yet" + a vague CTA. That's a bored-looking empty state. This one is the
 * opposite: Reckless headline in the editorial serif, a concrete one-line
 * explanation, and a blue CTA only if there's a meaningful action.
 *
 * The icon is optional and rendered at 48px with text-3 color so it reads
 * as a quiet anchor, not a mascot.
 *
 * Usage
 *   <EmptyState
 *     icon={<Radar />}
 *     title="No signals yet today"
 *     body="Next scan at 4:15 PM IST. Signals drop after market close."
 *     cta={<Button onClick={...}>Refresh</Button>}
 *   />
 */
export function EmptyState({ icon, title, body, cta, className, align = 'center' }) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4',
        align === 'center' ? 'items-center text-center' : 'items-start text-left',
        className
      )}
      style={{ padding: '48px 24px' }}
    >
      {icon && (
        <div
          aria-hidden="true"
          style={{ color: 'var(--text-3)', width: 48, height: 48 }}
          className="flex items-center justify-center"
        >
          {/* Children icons inherit currentColor via the wrapping div */}
          {React.isValidElement(icon)
            ? React.cloneElement(icon, { size: 48, strokeWidth: 1.25, ...(icon.props || {}) })
            : icon}
        </div>
      )}
      {title && (
        <h2 className="t-title-2" style={{ maxWidth: '48ch' }}>
          {title}
        </h2>
      )}
      {body && (
        <p className="t-ui-body t-prose" style={{ color: 'var(--text-2)' }}>
          {body}
        </p>
      )}
      {cta && <div style={{ marginTop: 8 }}>{cta}</div>}
    </div>
  );
}

export default EmptyState;
