import { useMemo } from "react";

/**
 * DashboardMockup — a stylised, CSS-only representation of what the
 * Nifty Satvik dashboard looks like. Lives inside the hero, wrapped in a
 * blue radial glow, perspective-tilted slightly.
 *
 * Composition mirrors the prototype dashboard at /preview-dashboard:
 *   - Top bar (brand + nav + user pill)
 *   - Left rail (nav icons)
 *   - Center: big candle chart (SVG candles, real-looking)
 *   - Right rail: today's signal card + active positions card
 *   - Bottom: mini calendar heatmap strip
 *
 * Everything is SVG / CSS — no real chart library, no real data. Loads
 * instantly, scales cleanly, never breaks. When the real dashboard
 * ships, swap this for an actual screenshot.
 */

// Deterministic OHLC generator so the chart looks lived-in but stays
// the same across renders.
function generateCandles(count) {
  const candles = [];
  let price = 100;
  let seed = 7;
  const rand = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  for (let i = 0; i < count; i++) {
    const open = price;
    const change = (rand() - 0.48) * 4;
    const close = open + change;
    const minOC = Math.min(open, close);
    const maxOC = Math.max(open, close);
    const high = maxOC + rand() * 1.6;
    const low = minOC - rand() * 1.6;
    price = close;
    candles.push({ open, high, low, close, bull: close >= open });
  }
  return candles;
}

export default function DashboardMockup() {
  const candles = useMemo(() => generateCandles(60), []);
  const heatmapCells = useMemo(() => generateHeatmap(), []);

  // Normalize candle prices into the chart viewport
  const allPrices = candles.flatMap((c) => [c.high, c.low]);
  const minP = Math.min(...allPrices);
  const maxP = Math.max(...allPrices);
  const range = Math.max(0.01, maxP - minP);
  const chartW = 620;
  const chartH = 220;
  const slot = chartW / candles.length;
  const bodyW = slot * 0.65;

  const toY = (p) => chartH - ((p - minP) / range) * (chartH - 16) - 8;

  return (
    <div className="mock-root">
      <div className="mock-top">
        <div className="mock-top-brand">
          <span className="mock-top-dot" />
          <span className="mock-top-name">Nifty Satvik</span>
          <span className="mock-top-divider" />
          <span className="mock-top-section">Today</span>
        </div>
        <div className="mock-top-nav">
          {["Signals", "Portfolio", "Journal", "Backtest"].map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
        <div className="mock-top-user">
          <span className="mock-top-pill">Live</span>
          <span className="mock-top-avatar">K</span>
        </div>
      </div>

      <div className="mock-body">
        <aside className="mock-rail">
          {["S", "P", "J", "B", "A"].map((l, i) => (
            <span
              key={i}
              className={`mock-rail-item ${i === 0 ? "active" : ""}`}
            >
              {l}
            </span>
          ))}
        </aside>

        <main className="mock-main">
          <div className="mock-chart-head">
            <div className="mock-chart-title">
              <span className="mock-ticker">RELIANCE</span>
              <span className="mock-sector">Energy · NSE</span>
            </div>
            <div className="mock-chart-meta">
              <span className="mock-price">₹ 2,894.50</span>
              <span className="mock-change mock-change-up">+1.42%</span>
            </div>
          </div>

          <svg
            className="mock-chart"
            viewBox={`0 0 ${chartW} ${chartH}`}
            preserveAspectRatio="none"
          >
            {/* Grid */}
            {[0.2, 0.4, 0.6, 0.8].map((g) => (
              <line
                key={g}
                x1="0"
                y1={chartH * g}
                x2={chartW}
                y2={chartH * g}
                stroke="rgba(255,255,255,0.04)"
                strokeWidth="1"
              />
            ))}

            {/* Candles */}
            {candles.map((c, i) => {
              const cx = i * slot + slot / 2;
              const color = c.bull ? "var(--bull, #3FDD8A)" : "var(--bear, #FF5C7A)";
              const bodyTop = toY(Math.max(c.open, c.close));
              const bodyH = Math.max(1.5, Math.abs(toY(c.open) - toY(c.close)));
              return (
                <g key={i}>
                  <line
                    x1={cx}
                    x2={cx}
                    y1={toY(c.high)}
                    y2={toY(c.low)}
                    stroke={color}
                    strokeWidth="1"
                    opacity="0.75"
                  />
                  <rect
                    x={cx - bodyW / 2}
                    y={bodyTop}
                    width={bodyW}
                    height={bodyH}
                    fill={color}
                    rx="0.5"
                  />
                </g>
              );
            })}

            {/* Signal entry line at the last candle */}
            <line
              x1="0"
              x2={chartW}
              y1={toY(candles[candles.length - 4].close)}
              y2={toY(candles[candles.length - 4].close)}
              stroke="var(--brand, #4F8CFF)"
              strokeWidth="1"
              strokeDasharray="3 4"
            />
            <text
              x={chartW - 4}
              y={toY(candles[candles.length - 4].close) - 4}
              fill="var(--brand, #4F8CFF)"
              fontSize="9"
              textAnchor="end"
              fontFamily="ui-monospace, monospace"
            >
              ENTRY ₹2,872
            </text>
          </svg>

          {/* Mini calendar heatmap strip */}
          <div className="mock-heatmap">
            <div className="mock-heatmap-label">26-week win/loss</div>
            <div className="mock-heatmap-grid">
              {heatmapCells.map((cell, i) => (
                <span
                  key={i}
                  className={`mock-heatmap-cell mock-heatmap-${cell}`}
                />
              ))}
            </div>
          </div>
        </main>

        <aside className="mock-side">
          <div className="mock-card mock-card-primary">
            <div className="mock-card-tag">Today's signal</div>
            <div className="mock-card-ticker">RELIANCE</div>
            <div className="mock-card-row">
              <span>Confidence</span>
              <strong>0.94</strong>
            </div>
            <div className="mock-card-row">
              <span>Entry</span>
              <strong>₹ 2,872</strong>
            </div>
            <div className="mock-card-row">
              <span>Target</span>
              <strong className="up">₹ 3,054</strong>
            </div>
            <div className="mock-card-row">
              <span>Stop</span>
              <strong className="down">₹ 2,791</strong>
            </div>
          </div>

          <div className="mock-card">
            <div className="mock-card-tag">Open positions</div>
            <div className="mock-pos-row">
              <span>TCS</span>
              <span className="up">+2.4%</span>
            </div>
            <div className="mock-pos-row">
              <span>HDFCBANK</span>
              <span className="up">+0.8%</span>
            </div>
            <div className="mock-pos-row">
              <span>INFY</span>
              <span className="down">-1.1%</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function generateHeatmap() {
  // 26 weeks × 5 trading days = 130 cells. ~62% no-signal, ~25% win, ~13% loss.
  let s = 17;
  const r = () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
  return Array.from({ length: 26 * 5 }, () => {
    const x = r();
    if (x < 0.62) return "none";
    if (x < 0.87) return "win";
    return "loss";
  });
}
