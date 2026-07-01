import React, { useMemo } from 'react';

/**
 * PriceArc — an intraday price path done right.
 *
 * This is NOT a decorative sparkline. It is a meaningful snapshot that
 * tells the user:
 *   - where has the price been since entry (or intraday open)?
 *   - is it currently above, below, or within the entry neutral zone?
 *
 * Color is driven by current price vs entry, not by gain/loss on a
 * generic trend:
 *   - bull (green) if current > entry + tolerance
 *   - bear (red)   if current < entry - tolerance
 *   - brand (blue) if within ±tolerance (still a fresh signal in play)
 *
 * With no entry prop, falls back to "last point vs first point" coloring
 * which is appropriate for holdings rows showing today's path.
 *
 * Size default matches the card spec (80×24). A `size="wide"` mode
 * (160×40) suits StockDetail header and CommandBar recent-tickers preview.
 */
function colorForPath({ series, entry, tolerance }) {
  if (!series || series.length < 2) return 'var(--text-3)';
  const last = series[series.length - 1];
  if (typeof entry === 'number') {
    const diff = last - entry;
    const band = Math.abs(entry) * (tolerance ?? 0.01);
    if (diff > band) return 'var(--bull)';
    if (diff < -band) return 'var(--bear)';
    return 'var(--brand)';
  }
  const first = series[0];
  if (last > first) return 'var(--bull)';
  if (last < first) return 'var(--bear)';
  return 'var(--text-3)';
}

function buildPath({ series, width, height, padY }) {
  if (!series || series.length === 0) return { d: '', areaD: '', dotCx: 0, dotCy: 0 };
  const n = series.length;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const range = max - min || 1;
  const usableH = height - padY * 2;

  const points = series.map((v, i) => {
    const x = n === 1 ? width / 2 : (i / (n - 1)) * width;
    const y = padY + (1 - (v - min) / range) * usableH;
    return [x, y];
  });

  const d = points
    .map(([x, y], i) => (i === 0 ? `M ${x.toFixed(2)} ${y.toFixed(2)}` : `L ${x.toFixed(2)} ${y.toFixed(2)}`))
    .join(' ');

  const first = points[0];
  const last = points[points.length - 1];
  const areaD =
    `M ${first[0].toFixed(2)} ${height} ` +
    points.map(([x, y]) => `L ${x.toFixed(2)} ${y.toFixed(2)}`).join(' ') +
    ` L ${last[0].toFixed(2)} ${height} Z`;

  return { d, areaD, dotCx: last[0], dotCy: last[1] };
}

export function PriceArc({
  series,
  entry = null,
  tolerance = 0.01,
  width: w,
  height: h,
  size = 'sm',
  className,
  showDot = true,
  ariaLabel,
}) {
  const width = w ?? (size === 'wide' ? 160 : 80);
  const height = h ?? (size === 'wide' ? 40 : 24);
  const padY = 2;

  const color = useMemo(() => colorForPath({ series, entry, tolerance }), [series, entry, tolerance]);
  const { d, areaD, dotCx, dotCy } = useMemo(
    () => buildPath({ series, width, height, padY }),
    [series, width, height]
  );

  if (!series || series.length < 2) {
    return (
      <svg width={width} height={height} className={className} aria-hidden="true">
        <line
          x1="0" y1={height / 2} x2={width} y2={height / 2}
          stroke="var(--edge-1)" strokeWidth="1" strokeDasharray="2 3"
        />
      </svg>
    );
  }

  const fillId = `arc-fill-${Math.random().toString(36).slice(2, 9)}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role={ariaLabel ? 'img' : undefined}
      aria-label={ariaLabel}
      aria-hidden={ariaLabel ? undefined : 'true'}
    >
      <defs>
        <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#${fillId})`} />
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      {showDot && (
        <circle cx={dotCx} cy={dotCy} r="2" fill={color} />
      )}
    </svg>
  );
}

export default PriceArc;
