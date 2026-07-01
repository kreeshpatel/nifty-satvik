import React, { useMemo } from 'react';
import { fmtPct } from '@/lib/format';

/**
 * MonthlyHeatmap — year-by-year × month grid of monthly returns.
 *
 * Input:
 *   data: { '2024': [2.5, 3.1, -0.8, null, ...], '2025': [...], ... }
 *     - Object keyed by year string
 *     - Each value is a 12-element array (Jan-Dec). null/undefined = no trade
 *
 * Cells are colored by sign + magnitude using OKLCH lightness shifts on
 * --bull / --bear so a +5% month reads stronger than a +0.5% month
 * without resorting to multiple hardcoded hues. Empty cells get a hairline
 * outline only (no fill) so the eye doesn't read missing data as zero.
 *
 * Hover reveals the exact value in a small tooltip pill.
 */
function cellStyle(value) {
  if (value == null || isNaN(value)) {
    return {
      background: 'transparent',
      border: '1px solid var(--edge-1)',
      color: 'var(--text-4)',
    };
  }
  // Exactly-zero months get a muted neutral cell — they're not losses.
  // Magnitude < 0.05 is also rounded to neutral so cells like +0.03% don't
  // claim bull-green for what's effectively a flat month.
  if (Math.abs(value) < 0.05) {
    return {
      background: 'var(--surface-2)',
      border: '1px solid var(--edge-1)',
      color: 'var(--text-3)',
    };
  }
  const pct = Math.min(Math.abs(value), 12) / 12;            // saturation cap @ ±12%
  const alpha = 0.18 + pct * 0.55;                           // 0.18 → 0.73
  if (value > 0) {
    return {
      background: `oklch(72% 0.19 145 / ${alpha.toFixed(2)})`,
      border: '1px solid oklch(72% 0.19 145 / 0.32)',
      color: alpha > 0.5 ? 'oklch(15% 0.05 145)' : 'var(--bull)',
    };
  }
  return {
    background: `oklch(66% 0.21 25 / ${alpha.toFixed(2)})`,
    border: '1px solid oklch(66% 0.21 25 / 0.32)',
    color: alpha > 0.5 ? 'oklch(15% 0.06 25)' : 'var(--bear)',
  };
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function MonthlyHeatmap({ data, className }) {
  const years = useMemo(
    () => Object.keys(data || {}).sort((a, b) => Number(b) - Number(a)),
    [data],
  );

  if (!years.length) {
    return (
      <div
        className={className}
        style={{
          padding: 32,
          textAlign: 'center',
          color: 'var(--text-3)',
          fontFamily: 'var(--font-sans)',
        }}
      >
        No monthly data yet
      </div>
    );
  }

  return (
    <div className={className} style={{ width: '100%', overflowX: 'auto' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'separate',
          borderSpacing: 4,
          fontFamily: 'var(--font-mono)',
        }}
      >
        <thead>
          <tr>
            <th
              style={{
                width: 56,
                textAlign: 'left',
                fontFamily: 'var(--font-sans)',
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: 'var(--text-3)',
                padding: '4px 6px',
              }}
            >
              Year
            </th>
            {MONTHS.map((m) => (
              <th
                key={m}
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: 11,
                  fontWeight: 500,
                  color: 'var(--text-3)',
                  textAlign: 'center',
                  padding: '4px 0',
                }}
              >
                {m}
              </th>
            ))}
            <th
              style={{
                fontFamily: 'var(--font-sans)',
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: 'var(--text-3)',
                textAlign: 'right',
                padding: '4px 6px',
              }}
            >
              YTD
            </th>
          </tr>
        </thead>
        <tbody>
          {years.map((year) => {
            const row = data[year] || [];
            const ytd = row.reduce((sum, v) => sum + (typeof v === 'number' ? v : 0), 0);
            return (
              <tr key={year}>
                <td
                  style={{
                    fontFamily: 'var(--font-sans)',
                    fontSize: 12,
                    fontWeight: 600,
                    color: 'var(--text-2)',
                    padding: '0 6px',
                  }}
                >
                  {year}
                </td>
                {MONTHS.map((_, i) => {
                  const v = row[i];
                  const style = cellStyle(v);
                  const display = typeof v === 'number' ? `${v >= 0 ? '+' : ''}${v.toFixed(1)}` : '';
                  return (
                    <td
                      key={i}
                      title={typeof v === 'number' ? fmtPct(v) : 'No trades'}
                      style={{
                        ...style,
                        height: 32,
                        borderRadius: 4,
                        textAlign: 'center',
                        fontSize: 11,
                        fontVariantNumeric: 'tabular-nums',
                        cursor: 'default',
                      }}
                    >
                      {display}
                    </td>
                  );
                })}
                <td
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 12,
                    fontVariantNumeric: 'tabular-nums',
                    fontWeight: 600,
                    color: ytd > 0 ? 'var(--bull)' : ytd < 0 ? 'var(--bear)' : 'var(--text-3)',
                    textAlign: 'right',
                    padding: '0 6px',
                  }}
                >
                  {fmtPct(ytd, 1)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default MonthlyHeatmap;
