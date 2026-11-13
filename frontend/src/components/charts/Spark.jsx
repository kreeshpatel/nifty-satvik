/**
 * Spark — a tiny inline sparkline for a REAL series (index closes, an equity curve, yearly
 * returns). Not a decorative squiggle: callers pass data they have, and it renders nothing
 * when there is none. Colour follows direction (first → last) unless `tone` is given.
 */
export default function Spark({ data, width = 64, height = 20, tone, label, bars = false }) {
  const pts = (data || []).map(Number).filter((v) => Number.isFinite(v));
  if (pts.length < 2) return null;
  const min = Math.min(...pts, bars ? 0 : Infinity);
  const max = Math.max(...pts, bars ? 0 : -Infinity);
  const span = max - min || 1;
  const x = (i) => (i / (pts.length - 1)) * (width - 2) + 1;
  const y = (v) => height - 1 - ((v - min) / span) * (height - 2);
  const dir = tone || (pts[pts.length - 1] >= pts[0] ? 'up' : 'down');
  const color = dir === 'up' ? 'var(--up)' : dir === 'down' ? 'var(--down)' : 'var(--ink-3)';
  const a11y = label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true };
  if (bars) {
    const bw = Math.max(1, (width - 2) / pts.length - 1);
    const zero = y(0);
    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} {...a11y} style={{ display: 'block' }}>
        {pts.map((v, i) => (
          <rect key={i} x={1 + i * ((width - 2) / pts.length)} width={bw} y={Math.min(y(v), zero)} height={Math.max(1, Math.abs(zero - y(v)))}
            fill={v >= 0 ? 'var(--up)' : 'var(--down)'} />
        ))}
      </svg>
    );
  }
  const d = pts.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ');
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} {...a11y} style={{ display: 'block' }}>
      <path d={d} fill="none" stroke={color} strokeWidth="1.25" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
