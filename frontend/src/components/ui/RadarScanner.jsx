/**
 * RadarScanner — NiftyQuant's signature visual.
 * A circular sonar sweep that "scans" for pre-move signals.
 * Pure SVG + CSS animation. No canvas, no JS timers.
 */
export default function RadarScanner({
  size = 400,
  dotCount = 40,
  sweepDuration = 4,
  className = "",
}) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.42; // Main radar radius

  // Deterministic dot positions (seeded by index)
  const dots = Array.from({ length: dotCount }, (_, i) => {
    const seed = (i * 2654435761) >>> 0; // Knuth hash for deterministic scatter
    const angle = ((seed % 3600) / 3600) * Math.PI * 2;
    const dist = 0.15 + ((seed >> 12) % 1000) / 1000 * 0.80; // 15-95% of radius
    const isSignal = i % 4 === 0; // Every 4th dot is a "signal"
    const dotAngleDeg = (angle * 180) / Math.PI;
    // Delay = how long into the sweep cycle before this dot lights up
    const delay = ((dotAngleDeg % 360) / 360) * sweepDuration;
    return {
      x: cx + Math.cos(angle) * r * dist,
      y: cy + Math.sin(angle) * r * dist,
      isSignal,
      delay,
      size: isSignal ? 3 : 1.5 + (i % 3) * 0.5,
    };
  });

  const rings = [0.25, 0.55, 0.85]; // Concentric ring radii as fraction of r

  return (
    <div className={`relative ${className}`} style={{ width: size, height: size }}>
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        className="block"
      >
        {/* Concentric rings */}
        {rings.map((frac, i) => (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={r * frac}
            fill="none"
            stroke="rgba(255,255,255,0.04)"
            strokeWidth="1"
          />
        ))}

        {/* Crosshair lines */}
        <line x1={cx - r} y1={cy} x2={cx + r} y2={cy} stroke="rgba(255,255,255,0.03)" strokeWidth="0.5" />
        <line x1={cx} y1={cy - r} x2={cx} y2={cy + r} stroke="rgba(255,255,255,0.03)" strokeWidth="0.5" />

        {/* Outer ring */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1.5" />

        {/* Stock dots */}
        {dots.map((dot, i) => (
          <circle
            key={i}
            cx={dot.x}
            cy={dot.y}
            r={dot.size}
            fill={dot.isSignal ? "#10b981" : "rgba(255,255,255,0.12)"}
            className={dot.isSignal ? "radar-signal-dot" : ""}
            style={dot.isSignal ? {
              animationDelay: `${dot.delay}s`,
              animationDuration: `${sweepDuration}s`,
            } : undefined}
          />
        ))}

        {/* Center dot */}
        <circle cx={cx} cy={cy} r="3" fill="rgba(79,140,255,0.6)" />
        <circle cx={cx} cy={cy} r="6" fill="none" stroke="rgba(79,140,255,0.3)" strokeWidth="1" />

        {/* Center label */}
        <text
          x={cx}
          y={cy + 20}
          textAnchor="middle"
          fontSize="10"
          fontFamily="'DM Sans', ui-sans-serif, sans-serif"
          fill="rgba(255,255,255,0.15)"
          letterSpacing="0.15em"
        >
          SCANNING
        </text>
      </svg>

      {/* Sweep beam — rotates via CSS */}
      <div
        className="radar-sweep absolute top-0 left-0"
        style={{
          width: size,
          height: size,
          animationDuration: `${sweepDuration}s`,
        }}
      >
        <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
          <defs>
            <linearGradient id="sweepGrad" gradientTransform="rotate(0)">
              <stop offset="0%" stopColor="rgba(79,140,255,0)" />
              <stop offset="70%" stopColor="rgba(79,140,255,0.15)" />
              <stop offset="100%" stopColor="rgba(79,140,255,0.4)" />
            </linearGradient>
          </defs>
          {/* Sweep wedge — a thin triangle from center to edge */}
          <path
            d={`M ${cx} ${cy} L ${cx + r} ${cy} A ${r} ${r} 0 0 1 ${cx + r * Math.cos(Math.PI / 6)} ${cy + r * Math.sin(Math.PI / 6)} Z`}
            fill="url(#sweepGrad)"
            opacity="0.8"
          />
          {/* Leading edge line */}
          <line
            x1={cx}
            y1={cy}
            x2={cx + r}
            y2={cy}
            stroke="rgba(79,140,255,0.6)"
            strokeWidth="1.5"
          />
        </svg>
      </div>
    </div>
  );
}
