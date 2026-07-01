import React, { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

/**
 * ExitReasonsDonut — small pie of why trades closed.
 *
 * Input:
 *   data: [{ reason: string, value: number, count: number, color?: string }]
 *
 * If `color` is missing on an item we map by reason name to our semantic
 * tokens — Target Hit → bull, Stop Hit → bear, Expired → text-3, etc.
 *
 * The center of the donut shows the total trade count in the editorial
 * serif; reading it as the centerpiece is more useful than reading slice
 * labels around the perimeter.
 */
function defaultColor(reason) {
  const r = (reason || '').toLowerCase();
  if (r.includes('target')) return 'var(--bull)';
  if (r.includes('stop'))   return 'var(--bear)';
  if (r.includes('expired') || r.includes('time')) return 'var(--text-3)';
  if (r.includes('cancel')) return 'var(--text-4)';
  if (r.includes('partial') || r.includes('trail')) return 'var(--brand)';
  return 'var(--info)';
}

export function ExitReasonsDonut({ data, height = 260 }) {
  const items = useMemo(
    () =>
      (data ?? []).map((d) => ({
        ...d,
        fill: d.color && d.color.startsWith('#') ? d.color : defaultColor(d.reason),
      })),
    [data],
  );
  const total = useMemo(
    () => items.reduce((sum, i) => sum + (Number(i.count) || 0), 0),
    [items],
  );

  if (!items.length) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-3)',
          fontFamily: 'var(--font-sans)',
        }}
      >
        No exits yet
      </div>
    );
  }

  return (
    /* Outer wrapper has natural height — only the donut sub-wrapper is
       constrained to `height` so the legend can flow naturally below
       without overflowing the parent ChartCard. */
    <div>
      <div style={{ position: 'relative', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={items}
              dataKey="value"
              nameKey="reason"
              innerRadius="62%"
              outerRadius="92%"
              paddingAngle={2}
              stroke="none"
              isAnimationActive={false}
            >
              {items.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 32,
              lineHeight: 1.1,
              color: 'var(--text-1)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {total}
          </div>
          <div
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--text-3)',
              marginTop: 4,
            }}
          >
            Total Exits
          </div>
        </div>
      </div>

      {/* Legend below — read each slice with count + share */}
      <ul
        style={{
          listStyle: 'none',
          margin: 0,
          padding: 0,
          marginTop: 16,
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: 6,
        }}
      >
        {items.map((it, i) => (
          <li
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8,
              fontFamily: 'var(--font-sans)',
              fontSize: 12,
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--text-2)' }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 2,
                  background: it.fill,
                  flexShrink: 0,
                }}
              />
              {it.reason}
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
                color: 'var(--text-1)',
              }}
            >
              {it.count}{typeof it.value === 'number' ? ` · ${it.value.toFixed(0)}%` : ''}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ExitReasonsDonut;
