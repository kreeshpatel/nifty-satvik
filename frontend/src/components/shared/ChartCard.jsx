import React from 'react';
import { cn } from '@/lib/utils';

/**
 * ChartCard — canonical wrapper for every Recharts/D3 visualization.
 *
 * Retail-pro rules baked in:
 *   - 280-420px hero height (chart IS the page, not a footnote)
 *   - Period pills rendered inline with the title, not stacked
 *   - No icon-above-heading pattern (impeccable ban)
 *   - Solid surface, NOT glass (data legibility > visual effect)
 *   - Footer row for metadata (legend, timestamp, source) lives below
 *     chart on a hairline, never overlaid
 *
 * The component is presentation-only — the actual chart (a Recharts
 * ResponsiveContainer + series) renders as children. Caller owns:
 *   - tooltip formatter
 *   - axis config (we recommend hairline axis, no vertical grid)
 *   - series color (use --bull, --bear, --brand, --info)
 *
 * Props
 * -----
 * title:     string | ReactNode    main heading
 * badge:     ReactNode             optional inline chip (e.g. "Live", StatusChip)
 * periods:   [{ label, value, active }]   pill toggle row rendered right of title
 * onPeriodChange: (value) => void
 * height:    number                chart area pixel height (default 320)
 * footer:    ReactNode             below-chart strip (legend, disclaimer, timestamp)
 * rightRail: ReactNode             optional companion column at ≥1280px (e.g. tab strip
 *                                  for the chart's stock detail context). Below 1280px
 *                                  it renders inline above the footer so it stays
 *                                  accessible without crowding the chart canvas.
 * railWidth: number                width of the right rail in px at desktop (default 240)
 */
export function ChartCard({
  title,
  badge,
  periods,
  onPeriodChange,
  height = 320,
  footer,
  rightRail,
  railWidth = 240,
  className,
  children,
}) {
  return (
    <div
      className={cn('relative flex flex-col dq-chart-card', className)}
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 'var(--pad-card)',
        boxShadow: 'var(--shadow-sm)',
        // expose railWidth for the scoped CSS below
        '--dq-rail-width': `${railWidth}px`,
      }}
    >
      {(title || periods) && (
        <div
          className="flex items-center justify-between flex-wrap"
          style={{ gap: 12, marginBottom: 16 }}
        >
          <div className="flex items-center" style={{ gap: 10, minWidth: 0 }}>
            {title && (
              <h3 className="t-title-2" style={{ color: 'var(--text-1)' }}>
                {title}
              </h3>
            )}
            {badge && <div className="flex-shrink-0">{badge}</div>}
          </div>
          {periods && periods.length > 0 && (
            <div
              role="tablist"
              aria-label="Time range"
              className="inline-flex items-center"
              style={{
                background: 'var(--surface-3)',
                borderRadius: 'var(--r-chip)',
                padding: 2,
                border: '1px solid var(--edge-1)',
              }}
            >
              {periods.map((p) => {
                const active = !!p.active;
                return (
                  <button
                    key={p.value ?? p.label}
                    role="tab"
                    aria-selected={active}
                    onClick={() => onPeriodChange?.(p.value ?? p.label)}
                    className="t-ui-callout transition-all"
                    style={{
                      padding: '4px 10px',
                      borderRadius: 4,
                      background: active ? 'var(--surface-1)' : 'transparent',
                      color: active ? 'var(--text-1)' : 'var(--text-3)',
                      boxShadow: active ? 'var(--shadow-sm)' : 'none',
                      fontWeight: active ? 600 : 500,
                      border: 'none',
                      cursor: 'pointer',
                      minWidth: 36,
                    }}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div className="dq-chart-card-body">
        <div style={{ height, width: '100%' }}>
          {children}
        </div>
        {rightRail && (
          <div className="dq-chart-card-rail">
            {rightRail}
          </div>
        )}
      </div>

      {footer && (
        <div
          className="mt-4 pt-3 flex items-center flex-wrap"
          style={{ borderTop: '1px solid var(--edge-1)', gap: 12 }}
        >
          {footer}
        </div>
      )}

      {/* Layout: stack at <1280px (mobile + smaller desktops), side-by-side
          ≥1280px so chart canvas keeps the bulk of width. The rail column
          shows a hairline to its left only when desktop. */}
      <style>{`
        .dq-chart-card-body {
          display: flex;
          flex-direction: column;
          gap: 16px;
          width: 100%;
          min-width: 0;
        }
        @media (min-width: 1280px) {
          .dq-chart-card .dq-chart-card-body {
            flex-direction: row;
            gap: 0;
          }
          .dq-chart-card .dq-chart-card-body > div:first-child {
            flex: 1 1 0;
            min-width: 0;
          }
          .dq-chart-card .dq-chart-card-rail {
            flex: 0 0 var(--dq-rail-width);
            border-left: 1px solid var(--edge-1);
            margin-left: 16px;
            padding-left: 16px;
            overflow-y: auto;
          }
        }
      `}</style>
    </div>
  );
}

export default ChartCard;
