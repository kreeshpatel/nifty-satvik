import React, { useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { fmtINR } from '@/lib/format';

/**
 * EquityCurveChart — the hero chart for Portfolio + Analytics + Backtest.
 *
 * Design rules (from redesign plan §5.5):
 *   - Hairline axis in --edge-1, no vertical grid
 *   - Muted tick labels in Berkeley Mono
 *   - Gradient fill: bull-green if terminal > initial, bear-red if below
 *   - Crosshair tooltip with pill treatment (surface-modal + blur)
 *   - Blue reference marker for "today" or a custom highlight date
 *
 * Props
 * -----
 * data: [{ date: 'YYYY-MM-DD', value: number, nifty?: number }]
 * height:   px (default 320)
 * tone:     'auto' | 'bull' | 'bear' | 'brand' — drives fill color; 'auto'
 *           derives from first vs last value of `data`
 * highlight: 'YYYY-MM-DD' — optional vertical reference line (e.g. cron date)
 * benchmarkKey: data row key for a comparison series (e.g. 'nifty'). Draws
 *               a second thin line in info color.
 */
function ToneForSeries(data) {
  if (!data || data.length < 2) return 'brand';
  const first = Number(data[0]?.value) || 0;
  const last = Number(data[data.length - 1]?.value) || 0;
  if (last > first) return 'bull';
  if (last < first) return 'bear';
  return 'brand';
}

const TONE_COLOR = {
  bull:  'var(--bull)',
  bear:  'var(--bear)',
  brand: 'var(--brand)',
  info:  'var(--info)',
};

function CrosshairTooltip({ active, payload, benchmarkKey }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const primary = payload.find((p) => p.dataKey === 'value');
  const bench = benchmarkKey ? payload.find((p) => p.dataKey === benchmarkKey) : null;
  return (
    <div
      style={{
        background: 'var(--surface-modal)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: '1px solid var(--edge-2)',
        borderRadius: 'var(--r-chip)',
        padding: '10px 12px',
        boxShadow: 'var(--shadow-lg)',
        fontFamily: 'var(--font-sans)',
        minWidth: 160,
      }}
    >
      <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6 }}>
        {d.date}
      </div>
      {primary && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
          <span className="t-ui-footnote" style={{ color: 'var(--text-2)' }}>Portfolio</span>
          <span className="t-num-body" style={{ color: 'var(--text-1)' }}>
            {fmtINR(primary.value)}
          </span>
        </div>
      )}
      {bench && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 4 }}>
          <span className="t-ui-footnote" style={{ color: 'var(--text-2)' }}>Nifty</span>
          <span className="t-num-body" style={{ color: 'var(--info)' }}>
            {Number(bench.value).toLocaleString('en-IN')}
          </span>
        </div>
      )}
    </div>
  );
}

export function EquityCurveChart({
  data,
  height = 320,
  tone = 'auto',
  highlight = null,
  benchmarkKey = null,
}) {
  const resolvedTone = useMemo(
    () => (tone === 'auto' ? ToneForSeries(data) : tone),
    [tone, data]
  );
  const color = TONE_COLOR[resolvedTone] || TONE_COLOR.brand;
  const fillId = useMemo(
    () => `eq-fill-${Math.random().toString(36).slice(2, 9)}`,
    []
  );

  if (!data || data.length === 0) {
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
        No equity history yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.32" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{
            fontSize: 10,
            fill: 'rgba(255,255,255,0.48)',
            fontFamily: 'var(--font-mono)',
          }}
          axisLine={{ stroke: 'var(--edge-1)' }}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          tick={{
            fontSize: 10,
            fill: 'rgba(255,255,255,0.48)',
            fontFamily: 'var(--font-mono)',
          }}
          axisLine={false}
          tickLine={false}
          width={56}
          tickFormatter={(v) => fmtINR(v)}
          domain={['dataMin', 'dataMax']}
        />
        <Tooltip
          content={<CrosshairTooltip benchmarkKey={benchmarkKey} />}
          cursor={{
            stroke: 'var(--edge-3)',
            strokeWidth: 1,
            strokeDasharray: '2 3',
          }}
        />
        {benchmarkKey && (
          <Area
            type="monotone"
            dataKey={benchmarkKey}
            stroke="var(--info)"
            strokeWidth={1}
            strokeDasharray="3 3"
            fill="none"
            isAnimationActive={false}
          />
        )}
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          fill={`url(#${fillId})`}
          isAnimationActive={false}
        />
        {highlight && (
          <ReferenceLine
            x={highlight}
            stroke="var(--brand)"
            strokeDasharray="2 3"
            label={{ value: 'today', position: 'top', fill: 'var(--brand-hi)', fontSize: 10 }}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export default EquityCurveChart;
