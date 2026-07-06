/* dashboard.jsx — main React app for Nifty Satvik trading desk
 * Loaded via <script type="text/babel" src="dashboard.jsx"> from Dashboard.html
 * Tweaks: brand color, density, sparkline style, hero copy variant
 */

// ─────────────────────────────────────────────────────────────────────
// Mock data — Nifty 500 universe (real tickers, fabricated numbers).
// ─────────────────────────────────────────────────────────────────────
const FRESH = [
  {
    sym: 'RELIANCE', name: 'Reliance Industries', sector: 'Energy',
    grade: 'A', winRate: 72.4, edge: '+2.18%',
    entry: 2948.20, stop: 2872.50, target: 3122.80,
    spark: [44, 46, 45, 49, 53, 51, 56, 59, 57, 62, 65, 64, 69, 73, 76],
    dir: 'up',
  },
  {
    sym: 'TCS', name: 'Tata Consultancy', sector: 'IT',
    grade: 'A−', winRate: 68.1, edge: '+1.62%',
    entry: 4128.50, stop: 4022.00, target: 4348.10,
    spark: [62, 60, 58, 60, 57, 53, 51, 54, 52, 50, 53, 56, 58, 62, 66],
    dir: 'up',
  },
  {
    sym: 'BAJFINANCE', name: 'Bajaj Finance', sector: 'Financials',
    grade: 'B+', winRate: 64.2, edge: '+1.04%',
    entry: 7218.40, stop: 7042.10, target: 7588.00,
    spark: [55, 58, 60, 57, 53, 49, 47, 50, 48, 45, 42, 44, 42, 40, 38],
    dir: 'down',
  },
];

// `perf` is a 12-day series of daily % returns (real-feel, deterministic).
// PerfSquares colors by sign, sizes by magnitude — convey real data per
// the design system rule “no decorative sparklines”.
const TABLE_ROWS = [
  { sym: 'INFY',      name: 'Infosys Ltd.',                  high: 1942.00, low: 1788.40, prev: 1842.10, chg: -14.20, gain: -0.77, perf: [+0.4,+1.2,-0.3,+0.8,-0.5,+1.6,+0.9,-1.1,+0.6,+1.4,-0.2,-0.77] },
  { sym: 'HDFCBANK',  name: 'HDFC Bank Ltd.',                high: 1812.50, low: 1684.00, prev: 1748.20, chg:  18.40, gain: +1.05, perf: [+0.6,+0.9,+1.2,-0.4,+0.7,+1.4,+0.8,+1.1,-0.3,+0.9,+1.3,+1.05] },
  { sym: 'ICICIBANK', name: 'ICICI Bank Ltd.',               high: 1284.20, low: 1142.50, prev: 1218.60, chg:  12.80, gain: +1.05, perf: [+0.8,+1.4,-0.6,+1.2,+0.9,+1.6,-0.4,+1.1,+0.7,-0.3,+1.0,+1.05] },
  { sym: 'BHARTIARTL',name: 'Bharti Airtel Ltd.',            high: 1672.10, low: 1488.00, prev: 1568.40, chg:  -4.20, gain: -0.27, perf: [+0.4,-0.8,+0.6,+1.2,-1.4,-0.9,+0.5,-1.2,+0.7,+0.4,-1.1,-0.27] },
  { sym: 'LT',        name: 'Larsen & Toubro Ltd.',          high: 3742.50, low: 3402.80, prev: 3608.20, chg:  22.40, gain: +0.62, perf: [+0.5,+0.8,+1.2,-0.4,+0.6,+1.4,-0.3,+0.9,+1.1,+0.7,-0.2,+0.62] },
  { sym: 'MARUTI',    name: 'Maruti Suzuki India Ltd.',      high: 13120.00, low: 11842.00, prev: 12420.40, chg: -86.20, gain: -0.69, perf: [-0.4,+0.6,+0.8,-1.2,+0.5,-0.9,+0.4,-1.1,-0.6,+0.7,+1.0,-0.69] },
  { sym: 'KOTAKBANK', name: 'Kotak Mahindra Bank Ltd.',      high: 1942.40, low: 1742.00, prev: 1842.60, chg:  14.80, gain: +0.80, perf: [+0.6,+0.9,-0.2,+0.7,+1.1,-0.4,+0.8,+1.2,-0.3,+0.6,+0.9,+0.80] },
  { sym: 'ADANIENT',  name: 'Adani Enterprises Ltd.',        high: 3284.00, low: 2742.00, prev: 2942.40, chg:  42.80, gain: +1.45, perf: [+1.2,-0.6,+0.9,+1.4,+1.8,-0.4,+0.7,+1.6,+1.2,-0.3,+0.9,+1.45] },
];

const SECTOR_BREADTH = [
  { name: 'Banking',     pct: 72, up: 38, total: 52, tone: 'bull', size: 132, top: 6,   left: 8   },
  { name: 'Pharma',      pct: 64, up: 21, total: 33, tone: 'bull', size: 114, top: 16,  left: 162 },
  { name: 'IT services', pct: 58, up: 24, total: 41, tone: 'bull', size: 106, top: 148, left: 6   },
  { name: 'Auto',        pct: 41, up: 12, total: 29, tone: 'warn', size: 94,  top: 150, left: 122 },
  { name: 'Energy',      pct: 36, up: 8,  total: 22, tone: 'bear', size: 82,  top: 172, left: 222 },
];

const HERO_COPY = {
  signals:   { eyebrow: 'TODAY · 16:15 IST SCAN', label: 'Top fresh signals', sub: '3 of 441 stocks scored above conviction threshold' },
  trending:  { eyebrow: 'THIS WEEK · WALK-FORWARD', label: 'Top trending signals', sub: 'Ranked by 90-day reward rate · paper-traded' },
  conviction:{ eyebrow: 'BACKTEST VALIDATED · 90D', label: 'Highest conviction',  sub: 'A-grade entries with explicit stop and target' },
};

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────
const fmtINR = (n) => '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (n) => (n >= 0 ? '+' : '') + n.toFixed(2) + '%';

// Sparkline component — supports line, area, candle styles
function Spark({ data, dir, style = 'line', width = 280, height = 96 }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stroke = dir === 'up' ? 'var(--bull)' : 'var(--bear)';
  const fill   = dir === 'up' ? 'rgba(63,221,138,0.20)' : 'rgba(255,92,122,0.20)';
  const padX = 8, padY = 10;
  const xs = data.map((_, i) => padX + (i * (width - 2 * padX)) / (data.length - 1));
  const ys = data.map((v) => padY + (height - 2 * padY) * (1 - (v - min) / range));
  const last = { x: xs[xs.length - 1], y: ys[ys.length - 1] };
  const peak = data.indexOf(dir === 'up' ? max : min);

  if (style === 'candle') {
    // simulated candles from same series — group every 2 ticks into a candle
    const candles = [];
    for (let i = 0; i < data.length - 1; i += 2) {
      const o = data[i], c = data[i + 1];
      // deterministic wick extents so candles don't jitter on re-render
      const j = ((i * 2654435761) % 100) / 100; // 0..1 pseudo from index
      const h = Math.max(o, c) + j * 2;
      const l = Math.min(o, c) - (1 - j) * 2;
      candles.push({ o, c, h, l });
    }
    const cw = (width - 2 * padX) / candles.length;
    return (
      <svg width={width} height={height} className="spark">
        {candles.map((cd, i) => {
          const x = padX + i * cw + cw * 0.5;
          const yO = padY + (height - 2 * padY) * (1 - (cd.o - min) / range);
          const yC = padY + (height - 2 * padY) * (1 - (cd.c - min) / range);
          const yH = padY + (height - 2 * padY) * (1 - (cd.h - min) / range);
          const yL = padY + (height - 2 * padY) * (1 - (cd.l - min) / range);
          const bull = cd.c >= cd.o;
          return (
            <g key={i}>
              <line x1={x} x2={x} y1={yH} y2={yL} stroke={bull ? 'var(--bull)' : 'var(--bear)'} strokeWidth="1" opacity="0.6" />
              <rect x={x - cw * 0.32} y={Math.min(yO, yC)} width={cw * 0.64} height={Math.max(2, Math.abs(yC - yO))}
                    fill={bull ? 'var(--bull)' : 'var(--bear)'} opacity="0.85" />
            </g>
          );
        })}
      </svg>
    );
  }

  const path = xs.map((x, i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(' ');
  const areaPath = `${path} L ${xs[xs.length - 1]} ${height - padY} L ${xs[0]} ${height - padY} Z`;

  return (
    <svg width={width} height={height} className="spark">
      {style === 'area' && <path d={areaPath} fill={fill} />}
      <path d={path} fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={{ filter: dir === 'up' ? 'drop-shadow(0 2px 6px rgba(63,221,138,0.5))' : 'drop-shadow(0 2px 6px rgba(255,92,122,0.5))' }}/>
      {/* peak marker — subtle dot, no vertical rule (keeps the compact band clean) */}
      <circle cx={xs[peak]} cy={ys[peak]} r="2.6" fill={stroke} opacity="0.7" />
      {/* end marker */}
      <circle cx={last.x} cy={last.y} r="3" fill={stroke} />
      <circle cx={last.x} cy={last.y} r="6.5" fill={stroke} opacity="0.18" />
    </svg>
  );
}

// 12-day perf squares — color by sign, height by |daily % change|.
function PerfSquares({ perf }) {
  const maxAbs = Math.max(0.5, ...perf.map((v) => Math.abs(v)));
  return (
    <div className="perf-squares" aria-label="12-day daily returns">
      {perf.slice(0, 12).map((v, i) => {
        // Height: 6px floor, 22px cap, scaled by absolute return.
        const h = 6 + (Math.abs(v) / maxAbs) * 16;
        return (
          <span key={i}
                className={`pf ${v >= 0 ? 'up' : 'dn'}`}
                title={`${v >= 0 ? '+' : ''}${v.toFixed(2)}%`}
                style={{ height: h }} />
        );
      })}
    </div>
  );
}

// Icon helpers (Lucide-style inline SVGs)
const Icon = {
  Bell:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>,
  Search:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>,
  Settings:(p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1.08 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>,
  Arrow:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>,
  ArrDown: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>,
  Sparkle: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></svg>,
  Refresh: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/></svg>,
  Layers:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="m12 2 10 5-10 5L2 7l10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>,
};

// ─────────────────────────────────────────────────────────────────────
// Pieces
// ─────────────────────────────────────────────────────────────────────
function Topbar({ density }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 19V8l5 6 4-9 4 11 3-5v8"/>
          </svg>
        </div>
        <div className="brand-text">Nifty Satvik</div>
      </div>

      <div className="search">
        <Icon.Search width="14" height="14" />
        <input placeholder="Search by ticker, sector, or signal grade…" />
        <kbd>⌘K</kbd>
      </div>

      <nav className="tabs">
        <a className="tab active" href="Dashboard.html">Dashboard</a>
        <a className="tab" href="Signals.html">Signals</a>
        <a className="tab" href="Signals.html">Portfolio</a>
        <a className="tab" href="Signals.html">Backtest</a>
        <a className="tab" href="Signals.html">Track record</a>
      </nav>

      <div className="top-actions">
        <button className="icon-btn"><Icon.Layers width="16" height="16" /></button>
        <button className="icon-btn">
          <Icon.Bell width="16" height="16" />
          <span className="bell-dot" />
        </button>
        <div className="user">
          <div className="hello">
            <div className="hello-l">Welcome back</div>
            <div className="hello-n">Kreesh P.</div>
          </div>
          <div className="avatar">KP</div>
          <Icon.ArrDown width="14" height="14" />
        </div>
      </div>
    </header>
  );
}

function RegimeStrip() {
  return (
    <div className="regime-strip">
      <div className="regime-left">
        <span className="live-dot" />
        <span className="regime-eyebrow">MARKET REGIME</span>
        <span className="regime-statement">
          The market is <em>Bullish</em>
          <span className="sep">·</span>
          <span className="t-num-small">NIFTY 24,182.40</span>
          <span className="num-bull t-num-small">+162.30 (0.68%)</span>
          <span className="sep">·</span>
          <span>VIX 12.8</span>
          <span className="sep">·</span>
          <span>Breadth 75</span>
        </span>
      </div>
      <div className="regime-right">
        <span className="strength-label">10-DAY STRENGTH</span>
        <div className="strength-bar"><span style={{ width: '75%' }} /></div>
        <span className="t-num-small num-bull">75</span>
      </div>
    </div>
  );
}

function TrendingCard({ row, sparkStyle }) {
  return (
    <div className={`trending-card ${row.dir === 'down' ? 'is-down' : 'is-up'}`}>
      <div className="tc-head">
        <Logo sym={row.sym} size={30} radius={8} />
        <div className="tc-id">
          <div className="tc-sym">
            {row.sym}
            <span className="tc-grade">{row.grade}</span>
          </div>
          <div className="tc-name">{row.name} · {row.sector}</div>
        </div>
        <span className="tc-fresh">FRESH</span>
      </div>

      <div className="tc-metrics">
        <div className="tc-metric">
          <span className="tc-metric-label">90-day win rate</span>
          <div className="tc-metric-row">
            <span className="tc-metric-val">{row.winRate.toFixed(1)}<small>%</small></span>
            <div className={`tc-stat-pill ${row.dir === 'up' ? 'bull' : 'bear'}`}>
              <Icon.Arrow width="9" height="9" style={{ transform: row.dir === 'down' ? 'rotate(90deg)' : 'none' }} />
              <span>{row.edge}</span>
            </div>
          </div>
        </div>
        <div className="tc-metric tc-metric-r">
          <span className="tc-metric-label">R-multiple</span>
          <div className="tc-metric-row">
            <span className={`tc-metric-val ${row.dir === 'up' ? 'num-bull' : 'num-bear'}`}>
              {row.dir === 'up' ? '+' : '−'}{rMultiple(row).toFixed(2)}<small>R</small>
            </span>
          </div>
        </div>
      </div>

      <div className="tc-spark">
        <Spark data={row.spark} dir={row.dir} style={sparkStyle} width={280} height={48} />
      </div>

      <div className="tc-foot">
        <div className="tc-level">
          <span className="micro">ENTRY</span>
          <span className="t-num-small">{fmtINR(row.entry)}</span>
        </div>
        <div className="tc-level">
          <span className="micro">STOP</span>
          <span className="t-num-small num-bear">{fmtINR(row.stop)}</span>
        </div>
        <div className="tc-level">
          <span className="micro">TARGET</span>
          <span className="t-num-small num-bull">{fmtINR(row.target)}</span>
        </div>
      </div>
    </div>
  );
}

function rMultiple(row) {
  // R = (current − entry) / (entry − stop). We don't have a live last price,
  // so derive a sensible 'current' from the spark's last value scaled to
  // hover above entry on bullish rows, below entry on bearish.
  const lastSpark = row.spark[row.spark.length - 1];
  const firstSpark = row.spark[0];
  const sparkRange = Math.max(1, Math.max(...row.spark) - Math.min(...row.spark));
  const sparkProgress = (lastSpark - firstSpark) / sparkRange; // -1..+1
  const dollarsPerR = row.entry - row.stop;
  return Math.abs(sparkProgress * 1.4);
}

function tickerBg(sym) {
  // deterministic hue per ticker, used for the avatar circle on cards/rows
  let h = 0;
  for (const ch of sym) h = (h + ch.charCodeAt(0) * 13) % 360;
  return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`;
}

// Map NSE tickers → corporate domains so we can pull real brand logos.
const TICKER_DOMAINS = {
  RELIANCE: 'ril.com',           TCS: 'tcs.com',              BAJFINANCE: 'bajajfinserv.in',
  INFY: 'infosys.com',           HDFCBANK: 'hdfcbank.com',    ICICIBANK: 'icicibank.com',
  BHARTIARTL: 'airtel.in',       LT: 'larsentoubro.com',      MARUTI: 'marutisuzuki.com',
  KOTAKBANK: 'kotak.com',        ADANIENT: 'adanienterprises.com', SBIN: 'sbi.co.in',
  AXISBANK: 'axisbank.com',      TATAPOWER: 'tatapower.com',  POLYCAB: 'polycab.com',
  VOLTAS: 'voltas.com',          CUMMINSIND: 'cummins.com',   JUBLFOOD: 'jubilantfoodworks.com',
  CRAFTSMAN: 'craftsmanautomation.com', JBCHEPHARM: 'jbpharma.com', CDSL: 'cdslindia.com',
  BLUEDART: 'bluedart.com',      IIFL: 'iifl.com',            HINDUNILVR: 'hul.co.in',
  NESTLEIND: 'nestle.in',
};

// Company logo with graceful fallback: brand logo → favicon → colored monogram.
function Logo({ sym, size = 32, radius = 9 }) {
  const domain = TICKER_DOMAINS[sym];
  const sources = domain
    ? [`https://icons.duckduckgo.com/ip3/${domain}.ico`,
       `https://www.google.com/s2/favicons?domain=${domain}&sz=128`]
    : [];
  const [idx, setIdx] = React.useState(0);

  if (idx >= sources.length) {
    return (
      <div className="logo-tile logo-mono" style={{ width: size, height: size, borderRadius: radius, background: tickerBg(sym), fontSize: Math.round(size * 0.34) }}>
        {sym.slice(0, 2)}
      </div>
    );
  }
  return (
    <div className="logo-tile" style={{ width: size, height: size, borderRadius: radius }}>
      <img src={sources[idx]} alt={sym} onError={() => setIdx((i) => i + 1)} />
    </div>
  );
}

function BacktestCTA() {
  return (
    <div className="bt-cta">
      <div className="bt-cta-glow" />
      <div className="bt-cta-bg">
        <svg viewBox="0 0 320 220" preserveAspectRatio="none" width="100%" height="100%">
          <defs>
            <linearGradient id="bt-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#4F8CFF" stopOpacity="0.45"/>
              <stop offset="100%" stopColor="#4F8CFF" stopOpacity="0"/>
            </linearGradient>
            <linearGradient id="bt-bar" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#7B5BFF"/>
              <stop offset="100%" stopColor="#2C5BFF"/>
            </linearGradient>
          </defs>
          {/* bars */}
          {[0,1,2,3,4,5,6,7,8,9].map((i) => {
            const x = 18 + i * 28;
            const h = 30 + Math.abs(Math.sin(i * 0.8)) * 110 + i * 4;
            return <rect key={i} x={x} y={200 - h} width="18" height={h} rx="3" fill="url(#bt-bar)" opacity={0.75 + i * 0.02}/>;
          })}
          {/* equity arrow over bars */}
          <path d="M14 180 L60 155 L100 138 L150 110 L210 75 L290 32" fill="none"
                stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"
                style={{ filter: 'drop-shadow(0 4px 12px rgba(255,255,255,0.5))' }}/>
          <circle cx="290" cy="32" r="5" fill="#fff" />
          <circle cx="290" cy="32" r="12" fill="#fff" opacity="0.18" />
        </svg>
      </div>
      <div className="bt-cta-body">
        <div className="bt-cta-eyebrow">BACKTEST WORKBENCH</div>
        <div className="bt-cta-h">Build a strategy. <br/>Walk it forward.</div>
        <div className="bt-cta-sub">Score any rule set against 8 years of Nifty 500 bars · 441 stocks · ₹0 in capital.</div>
        <button className="bt-cta-btn">
          Open backtest
          <Icon.Arrow width="14" height="14" />
        </button>
      </div>
    </div>
  );
}

function KiteStrip() {
  return (
    <div className="kite-strip">
      <div className="kite-l">
        <div className="kite-eyebrow">CONNECT BROKER</div>
        <div className="kite-headline">Place orders straight from a signal.</div>
        <div className="kite-sub">Zerodha Kite is the only execution venue. One-click routing, OAuth-secured.</div>
      </div>
      <div className="kite-r">
        <div className="kite-broker">
          <div className="kite-broker-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round">
              <path d="M4 4v16h16"/>
              <path d="M4 16l5-5 4 4 7-7"/>
            </svg>
          </div>
          <div className="kite-broker-text">
            <div className="t-ui-subhead">Zerodha · Kite Connect</div>
            <div className="t-ui-footnote">Session active · last sync 14s ago</div>
          </div>
          <div className="kite-status">
            <span className="live-dot" /> LIVE
          </div>
        </div>
        <button className="kite-cta">Manage connection <Icon.Arrow width="13" height="13" /></button>
      </div>
    </div>
  );
}

function StocksTable({ rows, density }) {
  const cellPad = density === 'compact' ? '10px 16px' : density === 'comfy' ? '20px 18px' : '14px 18px';
  return (
    <div className="stocks-table">
      <div className="stocks-table-head">
        <div className="stocks-table-title">
          <div>
            <div className="t-ui-headline">Nifty 500 movers</div>
            <div className="t-ui-footnote">Refreshed 14s ago · 16:15 IST scan window in 02h 31m</div>
          </div>
        </div>
        <div className="stocks-table-tabs">
          <button className="ttab active">All</button>
          <button className="ttab">Gainers</button>
          <button className="ttab">Losers</button>
          <button className="ttab">My watchlist</button>
        </div>
      </div>

      <div className="stocks-table-grid">
        <div className="th">Company</div>
        <div className="th th-r">High</div>
        <div className="th th-r">Low</div>
        <div className="th th-r">Prev close</div>
        <div className="th th-r">Change</div>
        <div className="th th-r">Gain</div>
        <div className="th">5-day perf</div>

        {rows.map((r, i) => (
          <React.Fragment key={r.sym}>
            <div className="td td-name" style={{ padding: cellPad }}>
              <Logo sym={r.sym} size={32} radius={8} />
              <div>
                <div className="td-name-sym">{r.sym}</div>
                <div className="td-name-full">{r.name}</div>
              </div>
            </div>
            <div className="td td-r tabular-nums" style={{ padding: cellPad }}>{fmtINR(r.high)}</div>
            <div className="td td-r tabular-nums" style={{ padding: cellPad }}>{fmtINR(r.low)}</div>
            <div className="td td-r tabular-nums" style={{ padding: cellPad }}>{fmtINR(r.prev)}</div>
            <div className="td td-r tabular-nums" style={{ padding: cellPad, color: r.chg >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
              {r.chg >= 0 ? '+' : ''}{r.chg.toFixed(2)}
            </div>
            <div className="td td-r tabular-nums" style={{ padding: cellPad, color: r.gain >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
              {fmtPct(r.gain)}
            </div>
            <div className="td" style={{ padding: cellPad }}>
              <PerfSquares perf={r.perf} />
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function SectorBreadth() {
  const advancing = SECTOR_BREADTH.filter((s) => s.pct >= 50).length;
  return (
    <div className="card sector-breadth">
      <div className="card-head">
        <div>
          <div className="t-ui-headline">Sector breadth</div>
          <div className="t-ui-footnote">% of stocks above 50-day MA</div>
        </div>
        <button className="card-link">Today <Icon.ArrDown width="12" height="12" /></button>
      </div>

      <div className="bubble-stage">
        {SECTOR_BREADTH.map((s) => (
          <div key={s.name} className={`bubble bubble-${s.tone}`}
               style={{ top: s.top, left: s.left, width: s.size, height: s.size }}
               title={`${s.name} · ${s.up} of ${s.total} above 50-DMA`}>
            <div className="bubble-pct">{s.pct}<span>%</span></div>
            <div className="bubble-name">{s.name}</div>
            <div className="bubble-count">{s.up}/{s.total}</div>
          </div>
        ))}
      </div>

      <div className="bubble-legend">
        <span className="leg"><span className="leg-dot leg-bull" /> Bullish</span>
        <span className="leg"><span className="leg-dot leg-warn" /> Neutral</span>
        <span className="leg"><span className="leg-dot leg-bear" /> Bearish</span>
        <span className="leg-summary"><span className="num-bull">{advancing}</span>/{SECTOR_BREADTH.length} sectors bullish</span>
      </div>
    </div>
  );
}

function BalanceCard() {
  return (
    <div className="balance-card">
      <div className="balance-glow" />
      <div className="card-head">
        <div>
          <div className="t-ui-headline" style={{ color: '#fff' }}>Subscription</div>
          <div className="t-ui-footnote" style={{ color: 'rgba(255,255,255,0.7)' }}>Renews 12 Dec · ₹2,499/mo</div>
        </div>
        <span className="plan-chip">PRO</span>
      </div>
      <div className="balance-rows">
        <div className="balance-row">
          <span>Signals received</span>
          <span className="t-num-small" style={{ color: '#fff' }}>142 / 200</span>
        </div>
        <div className="balance-row">
          <span>Backtests this month</span>
          <span className="t-num-small" style={{ color: '#fff' }}>24 / 50</span>
        </div>
        <div className="balance-row">
          <span>Track-record window</span>
          <span className="t-num-small" style={{ color: '#fff' }}>Lifetime</span>
        </div>
      </div>
      <button className="balance-cta">Manage plan <Icon.Arrow width="13" height="13" /></button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────────────
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "brandColor":   "#4F8CFF",
  "density":      "regular",
  "sparkStyle":   "line",
  "heroCopy":     "signals"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const hero = HERO_COPY[t.heroCopy] || HERO_COPY.signals;

  // Apply brand color override to CSS vars
  React.useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--brand', t.brandColor);
    // derive hi / lo by lightening / darkening — keep simple
    const c = t.brandColor;
    root.style.setProperty('--brand-hi', c);
    root.style.setProperty('--brand-lo', c);
    root.style.setProperty('--brand-soft', hexToRgba(c, 0.14));
    root.style.setProperty('--brand-edge', hexToRgba(c, 0.40));
  }, [t.brandColor]);

  return (
    <div className={`app density-${t.density}`}>
      <Topbar density={t.density} />
      <RegimeStrip />

      <main className="work">
        <section className="row row-trending">
          <div className="row-head">
            <div>
              <div className="t-ui-micro">{hero.eyebrow}</div>
              <h2 className="row-title">{hero.label}</h2>
              <div className="t-ui-footnote">{hero.sub}</div>
            </div>
            <div className="row-controls">
              <div className="seg">
                <button className="seg-btn active">Today</button>
                <button className="seg-btn">Week</button>
                <button className="seg-btn">Month</button>
              </div>
            </div>
          </div>

          <div className="trending-grid">
            {FRESH.map((row) => <TrendingCard key={row.sym} row={row} sparkStyle={t.sparkStyle} />)}
            <BacktestCTA />
          </div>

          <KiteStrip />
        </section>

        <section className="row row-data">
          <StocksTable rows={TABLE_ROWS} density={t.density} />
          <aside className="right-rail">
            <SectorBreadth />
            <BalanceCard />
          </aside>
        </section>

        <footer className="work-foot">
          <div className="t-ui-footnote">
            Members see live tickers · this preview is anonymized · NSE data delayed by 15 min for non-members
          </div>
          <div className="t-ui-footnote">v2026.05 · build 1f4a2c</div>
        </footer>
      </main>

      <TweaksPanel>
        <TweakSection label="Brand color" />
        <TweakColor label="Primary" value={t.brandColor}
          options={['#4F8CFF', '#7B5BFF', '#3FDD8A', '#FFB454']}
          onChange={(v) => setTweak('brandColor', v)} />
        <TweakSection label="Layout" />
        <TweakRadio label="Density" value={t.density}
          options={['compact', 'regular', 'comfy']}
          onChange={(v) => setTweak('density', v)} />
        <TweakSection label="Sparklines" />
        <TweakRadio label="Style" value={t.sparkStyle}
          options={['line', 'area', 'candle']}
          onChange={(v) => setTweak('sparkStyle', v)} />
        <TweakSection label="Headline copy" />
        <TweakSelect label="Variant" value={t.heroCopy}
          options={['signals', 'trending', 'conviction']}
          onChange={(v) => setTweak('heroCopy', v)} />
      </TweaksPanel>
    </div>
  );
}

function hexToRgba(hex, a) {
  const m = hex.replace('#', '');
  const r = parseInt(m.substring(0, 2), 16);
  const g = parseInt(m.substring(2, 4), 16);
  const b = parseInt(m.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
