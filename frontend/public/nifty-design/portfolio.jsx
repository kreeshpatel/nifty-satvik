/* portfolio.jsx — NiftyQuant Portfolio page
 * Self-contained React app loaded via <script type="text/babel">.
 * Portfolio-style charts use hand-rolled SVG with system tokens (per the
 * design system: TradingView is reserved for single-instrument price charts).
 */

// ── helpers ──
const fmtINR  = (n) => '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtNum  = (n) => n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct  = (n) => (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
const fmtPct1 = (n) => (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%';
const fmtLakh = (n) => {
  const sign = n < 0 ? '−' : '';
  const a = Math.abs(n);
  if (a >= 1e7) return sign + '₹' + (a / 1e7).toFixed(2) + 'Cr';
  if (a >= 1e5) return sign + '₹' + (a / 1e5).toFixed(2) + 'L';
  return sign + '₹' + Math.round(a).toLocaleString('en-IN');
};
const fmtSignedINR = (n) => (n >= 0 ? '+' : '−') + '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN');

const Icon = {
  Search:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>,
  Bell:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>,
  Arrow:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>,
  ArrDown: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>,
  Layers:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="m12 2 10 5-10 5L2 7l10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>,
  Alert:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>,
  Download:(p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>,
};

const TICKER_DOMAINS = {
  ICICIBANK: 'icicibank.com', HDFCBANK: 'hdfcbank.com', POLYCAB: 'polycab.com',
  MARUTI: 'marutisuzuki.com', CUMMINSIND: 'cummins.com', DIVISLAB: 'divislabs.com',
  BHARTIARTL: 'airtel.in', LT: 'larsentoubro.com', TATAPOWER: 'tatapower.com', VOLTAS: 'voltas.com',
};
function tickerBg(sym) { let h = 0; for (const ch of sym) h = (h + ch.charCodeAt(0) * 13) % 360; return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`; }
function Logo({ sym, size = 32, radius = 9 }) {
  const domain = TICKER_DOMAINS[sym];
  const sources = domain ? [`https://icons.duckduckgo.com/ip3/${domain}.ico`, `https://www.google.com/s2/favicons?domain=${domain}&sz=128`] : [];
  const [idx, setIdx] = React.useState(0);
  if (idx >= sources.length) return <div className="logo-tile logo-mono" style={{ width: size, height: size, borderRadius: radius, background: tickerBg(sym), fontSize: Math.round(size * 0.34) }}>{sym.slice(0, 2)}</div>;
  return <div className="logo-tile" style={{ width: size, height: size, borderRadius: radius }}><img src={sources[idx]} alt={sym} onError={() => setIdx((i) => i + 1)} /></div>;
}

// ── positions (coherent with the Signals page) ──
const RAW_POSITIONS = [
  { sym: 'ICICIBANK', name: 'ICICI Bank', sector: 'Financials', qty: 80, avg: 1194.20, ltp: 1281.40, day: 1.05, flag: 'sell', flagReason: 'Target reached', held: '3d' },
  { sym: 'DIVISLAB', name: "Divi's Laboratories", sector: 'Pharma', qty: 22, avg: 5842.00, ltp: 5708.00, day: -0.84, flag: 'sell', flagReason: 'Stop hit', held: '4d' },
  { sym: 'POLYCAB', name: 'Polycab India', sector: 'Capital Goods', qty: 14, avg: 6850.00, ltp: 7048.00, day: 0.72, flag: 'hold', held: '5d' },
  { sym: 'HDFCBANK', name: 'HDFC Bank', sector: 'Financials', qty: 30, avg: 1686.00, ltp: 1742.60, day: 1.05, flag: 'hold', held: '3d' },
  { sym: 'MARUTI', name: 'Maruti Suzuki', sector: 'Auto', qty: 4, avg: 12095.00, ltp: 12410.00, day: -0.42, flag: 'hold', held: '7d' },
  { sym: 'CUMMINSIND', name: 'Cummins India', sector: 'Capital Goods', qty: 26, avg: 3748.00, ltp: 3848.00, day: 0.64, flag: 'hold', held: '9d' },
];

const POSITIONS = RAW_POSITIONS.map((p) => {
  const value = p.qty * p.ltp;
  const cost = p.qty * p.avg;
  const pnl = value - cost;
  const pnlPct = (pnl / cost) * 100;
  const dayPnl = value * (p.day / 100);
  return { ...p, value, cost, pnl, pnlPct, dayPnl };
});

const INVESTED = POSITIONS.reduce((a, p) => a + p.value, 0);
const COST_BASIS = POSITIONS.reduce((a, p) => a + p.cost, 0);
const OPEN_PNL = INVESTED - COST_BASIS;
const OPEN_PNL_PCT = (OPEN_PNL / COST_BASIS) * 100;
const DAY_PNL = POSITIONS.reduce((a, p) => a + p.dayPnl, 0);
const CASH = 171274;
const EQUITY = INVESTED + CASH;
const DAY_PNL_PCT = (DAY_PNL / (EQUITY - DAY_PNL)) * 100;
const REALISED_MTD = 6088; // BHARTIARTL +6942, LT +3304, VOLTAS −2178, TATAPOWER −1980
const WINNERS = POSITIONS.filter((p) => p.pnl >= 0).length;
const LOSERS = POSITIONS.length - WINNERS;

// performance stats (proof) + recently closed (ties to realised MTD)
const PERF_STATS = [
  { l: '1-yr return', v: '+34.2%', tone: 'bull' },
  { l: 'Max drawdown', v: '−6.2%', tone: 'bear' },
  { l: 'Sharpe ratio', v: '1.84', tone: '' },
  { l: '90-day win rate', v: '68.4%', tone: '' },
  { l: 'Avg hold', v: '4.2 days', tone: '' },
];
const CLOSED_MTD = [
  { sym: 'BHARTIARTL', name: 'Bharti Airtel', reason: 'Target', pnl: 6942, pct: 7.7, won: true },
  { sym: 'LT', name: 'Larsen & Toubro', reason: 'Target', pnl: 3304, pct: 6.9, won: true },
  { sym: 'VOLTAS', name: 'Voltas', reason: 'Stop', pnl: -2178, pct: -4.3, won: false },
  { sym: 'TATAPOWER', name: 'Tata Power', reason: 'Stop', pnl: -1980, pct: -3.9, won: false },
];

const KPI_SPARK = {
  equity:   [0, 1.1, 0.7, 2.0, 3.3, 2.8, 4.4, 5.1, 6.6, 7.2, 8.0, 9.4],
  invested: [4.9, 5.0, 4.95, 5.1, 5.05, 5.18, 5.12, 5.22, 5.2, 5.26, 5.24, 5.29],
  openpnl:  [0.2, 0.5, 0.3, 0.8, 1.1, 0.9, 1.4, 1.2, 1.7, 1.9, 2.1, 2.4],
  realised: [0, 0, 1.2, 1.2, 1.2, 3.4, 3.4, 5.2, 5.2, 5.2, 6.1, 6.1],
};

// sector allocation (incl. cash) as % of equity
const SECTOR_COLORS = { 'Capital Goods': '#5BC7FF', 'Financials': '#4F8CFF', 'Pharma': '#3FDD8A', 'Auto': '#FFB454', 'Cash': '#5A6488' };
const ALLOC = (() => {
  const bySector = {};
  POSITIONS.forEach((p) => { bySector[p.sector] = (bySector[p.sector] || 0) + p.value; });
  const rows = Object.entries(bySector).map(([label, value]) => ({ label, value, pct: (value / EQUITY) * 100 }));
  rows.push({ label: 'Cash', value: CASH, pct: (CASH / EQUITY) * 100 });
  return rows.sort((a, b) => b.value - a.value);
})();

// equity-curve series per timeframe: % return path points + benchmark
const SERIES = {
  '3M': { you: 9.4,  nifty: 4.2, pts: [0, 1.2, 0.6, 2.1, 3.4, 2.8, 4.6, 5.2, 6.8, 7.4, 8.1, 9.4], bench: [0, 0.8, 1.2, 1.0, 1.8, 2.2, 2.0, 2.8, 3.2, 3.6, 3.9, 4.2] },
  '6M': { you: 18.4, nifty: 12.1, pts: [0, 2.1, 1.6, 3.8, 5.2, 7.1, 6.4, 9.8, 11.2, 13.6, 15.8, 18.4], bench: [0, 1.4, 2.2, 3.1, 4.0, 5.2, 6.4, 7.8, 8.9, 9.8, 11.1, 12.1] },
  '1Y':  { you: 34.2, nifty: 16.8, pts: [0, 3.2, 5.1, 4.2, 8.4, 11.2, 9.8, 15.4, 19.2, 24.1, 29.6, 34.2], bench: [0, 2.1, 3.8, 5.2, 6.9, 8.4, 9.1, 11.2, 12.8, 14.1, 15.6, 16.8] },
  'All': { you: 47.2, nifty: 19.4, pts: [0, 4.1, 7.2, 6.1, 11.8, 16.2, 14.1, 22.4, 28.1, 35.6, 41.2, 47.2], bench: [0, 2.4, 4.1, 6.2, 8.1, 9.8, 11.2, 13.4, 15.1, 16.8, 18.2, 19.4] },
};
const TF_AXIS = {
  '3M': ['MAR', 'APR', 'MAY'], '6M': ['MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG'],
  '1Y': ['JUN', 'AUG', 'OCT', 'DEC', 'FEB', 'APR'], 'All': ['2024', '', '2025', '', '2026', ''],
};

// ── chrome ──
function Topbar() {
  return (
    <header className="topbar">
      <a className="brand" href="Landing.html" style={{ textDecoration: 'none' }}>
        <div className="brand-mark"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19V8l5 6 4-9 4 11 3-5v8"/></svg></div>
        <div className="brand-text">NiftyQuant</div>
      </a>
      <div className="search"><Icon.Search width="14" height="14" /><input placeholder="Search holdings, sector, or ticker…" /><kbd>⌘K</kbd></div>
      <nav className="tabs">
        <a className="tab" href="Dashboard.html">Dashboard</a>
        <a className="tab" href="Signals.html">Signals</a>
        <a className="tab active" href="Portfolio.html">Portfolio</a>
        <a className="tab" href="Signals.html">Backtest</a>
        <a className="tab" href="Signals.html">Track record</a>
      </nav>
      <div className="top-actions">
        <button className="icon-btn"><Icon.Layers width="16" height="16" /></button>
        <button className="icon-btn"><Icon.Bell width="16" height="16" /><span className="bell-dot" /></button>
        <div className="user"><div className="hello"><div className="hello-l">Welcome back</div><div className="hello-n">Kreesh P.</div></div><div className="avatar">KP</div><Icon.ArrDown width="14" height="14" /></div>
      </div>
    </header>
  );
}

// ── KPI tiles ──
function KpiSpark({ data, tone }) {
  const w = 88, h = 32, min = Math.min(...data), max = Math.max(...data), r = (max - min) || 1;
  const pts = data.map((v, i) => [2 + (i * (w - 4)) / (data.length - 1), 3 + (h - 6) * (1 - (v - min) / r)]);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const area = `${d} L${w - 2},${h} L2,${h} Z`;
  const stroke = tone === 'bull' ? 'var(--bull)' : tone === 'bear' ? 'var(--bear)' : 'var(--brand-hi)';
  const fill = tone === 'bull' ? 'rgba(63,221,138,0.14)' : tone === 'bear' ? 'rgba(255,92,122,0.14)' : 'rgba(79,140,255,0.14)';
  return (
    <svg className="kpi-spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <path d={area} fill={fill} />
      <path d={d} fill="none" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2" fill={stroke} />
    </svg>
  );
}

function Kpi({ micro, value, valueClass, spark, sparkTone, children }) {
  return (
    <div className="pf-kpi">
      <div className="pf-kpi-micro">{micro}</div>
      <div className="pf-kpi-row">
        <div className={`pf-kpi-v ${valueClass || ''}`}>{value}</div>
        {spark && <KpiSpark data={spark} tone={sparkTone} />}
      </div>
      <div className="pf-kpi-ctx">{children}</div>
    </div>
  );
}

// ── equity curve (hand-rolled SVG, brand chart style) ──
function EquityCurve({ tf, setTf }) {
  const W = 700, H = 260, padTop = 16, padBot = 30;
  const s = SERIES[tf];
  const all = [...s.pts, ...s.bench];
  const max = Math.max(...all), min = Math.min(0, ...all);
  const range = (max - min) || 1;
  const x = (i, arr) => (i * W) / (arr.length - 1);
  const y = (v) => padTop + (H - padTop - padBot) * (1 - (v - min) / range);
  const toPath = (arr) => arr.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i, arr).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const linePort = toPath(s.pts);
  const lineBench = toPath(s.bench);
  const areaPort = `${linePort} L${W},${H - padBot} L0,${H - padBot} Z`;
  const lastY = y(s.pts[s.pts.length - 1]);
  // gridlines at 0 and rounded steps
  const step = max > 30 ? 20 : max > 15 ? 10 : 5;
  const grids = [];
  for (let g = 0; g <= max + 0.01; g += step) grids.push(g);

  return (
    <div className="pf-panel pf-equity">
      <div className="pf-panel-head">
        <div>
          <div className="pf-panel-title">Portfolio value · vs Nifty 500</div>
          <div className="pf-panel-sub">You <span className="v num-bull">{fmtPct1(s.you)}</span> · Nifty 500 <span className="v">{fmtPct1(s.nifty)}</span></div>
        </div>
        <div className="pf-tf">
          {['3M', '6M', '1Y', 'All'].map((k) => (
            <button key={k} className={tf === k ? 'active' : ''} onClick={() => setTf(k)}>{k}</button>
          ))}
        </div>
      </div>

      <svg className="pf-chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="pf-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4F8CFF" stopOpacity="0.30" />
            <stop offset="100%" stopColor="#4F8CFF" stopOpacity="0" />
          </linearGradient>
        </defs>
        {grids.map((g) => (
          <g key={g}>
            <line className="pf-gl" x1="0" y1={y(g)} x2={W} y2={y(g)} />
            <text className="pf-axis" x={W - 6} y={y(g) - 4} textAnchor="end">{g === 0 ? '0%' : fmtPct1(g).replace('.0', '')}</text>
          </g>
        ))}
        <path className="pf-area" d={areaPort} fill="url(#pf-area)" />
        <path className="pf-bench" d={lineBench} />
        <path className="pf-line" d={linePort} />
        <circle cx={W} cy={lastY} r="4" fill="var(--brand-hi)" style={{ filter: 'drop-shadow(0 0 8px rgba(79,140,255,0.7))' }} />
        {TF_AXIS[tf].map((lbl, i) => lbl && (
          <text key={i} className="pf-axis" x={(i * W) / (TF_AXIS[tf].length - 1)} y={H - 8}
                textAnchor={i === 0 ? 'start' : i === TF_AXIS[tf].length - 1 ? 'end' : 'middle'}>{lbl}</text>
        ))}
      </svg>

      <div className="pf-legend">
        <span className="item"><span className="sw" style={{ background: 'var(--brand-hi)' }} />Portfolio</span>
        <span className="item"><span className="sw bench" />Nifty 500</span>
        <span className="sep">·</span>
        <span>Daily close · since {tf === 'All' ? 'inception' : tf + ' ago'}</span>
      </div>
    </div>
  );
}

// ── allocation donut ──
function Donut() {
  const R = 56, SW = 22, C = 2 * Math.PI * R, cx = 80, cy = 80;
  let offset = 0;
  return (
    <div className="pf-panel pf-alloc">
      <div className="pf-panel-head"><div className="pf-panel-title">Allocation</div><span className="pf-alloc-cash">{fmtLakh(EQUITY)} total</span></div>
      <div className="pf-alloc-body">
        <div className="pf-donut">
          <svg viewBox="0 0 160 160">
            <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={SW} />
            {ALLOC.map((a) => {
              const len = (a.pct / 100) * C;
              const seg = (
                <circle key={a.label} cx={cx} cy={cy} r={R} fill="none" stroke={SECTOR_COLORS[a.label]} strokeWidth={SW}
                        strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-offset}
                        transform={`rotate(-90 ${cx} ${cy})`} strokeLinecap="butt" />
              );
              offset += len;
              return seg;
            })}
            <text x={cx} y={cy - 4} textAnchor="middle" className="donut-c-v">{POSITIONS.length}</text>
            <text x={cx} y={cy + 12} textAnchor="middle" className="donut-c-l">holdings</text>
          </svg>
        </div>
        <div className="pf-alloc-legend">
          {ALLOC.map((a) => (
            <div key={a.label} className="alloc-row">
              <span className="alloc-dot" style={{ background: SECTOR_COLORS[a.label] }} />
              <span className="alloc-label">{a.label}</span>
              <span className="alloc-pct">{a.pct.toFixed(1)}%</span>
              <span className="alloc-val">{fmtLakh(a.value)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── holdings table ──
function Holdings() {
  return (
    <div className="pf-panel pf-holdings">
      <div className="pf-panel-head">
        <div className="pf-panel-title">Holdings <span className="pf-h-count">{POSITIONS.length}</span></div>
        <button className="pf-export"><Icon.Download width="13" height="13" /> Export</button>
      </div>
      <div className="pf-table">
        <div className="pf-thead">
          <div className="th">Instrument</div>
          <div className="th th-r">Qty</div>
          <div className="th th-r">Avg cost</div>
          <div className="th th-r">LTP</div>
          <div className="th th-r">Cur. value</div>
          <div className="th th-r">Day</div>
          <div className="th th-r">P&amp;L</div>
          <div className="th th-r">Alloc</div>
          <div className="th th-r"></div>
        </div>
        {POSITIONS.map((p) => {
          const alloc = (p.value / EQUITY) * 100;
          return (
            <div key={p.sym} className="pf-trow">
              <div className="td td-name">
                <Logo sym={p.sym} size={32} radius={8} />
                <div><div className="td-sym">{p.sym}</div><div className="td-full">{p.name} · {p.sector}</div></div>
              </div>
              <div className="td td-r t-num">{p.qty}</div>
              <div className="td td-r t-num td-dim">{fmtNum(p.avg)}</div>
              <div className="td td-r t-num">{fmtNum(p.ltp)}</div>
              <div className="td td-r t-num">{fmtLakh(p.value)}</div>
              <div className={`td td-r t-num ${p.day >= 0 ? 'num-bull' : 'num-bear'}`}>{fmtPct(p.day)}</div>
              <div className="td td-r">
                <div className={`t-num ${p.pnl >= 0 ? 'num-bull' : 'num-bear'}`}>{fmtSignedINR(p.pnl)}</div>
                <div className={`td-pnl-pct t-num ${p.pnl >= 0 ? 'num-bull' : 'num-bear'}`}>{fmtPct(p.pnlPct)}</div>
              </div>
              <div className="td td-r">
                <div className="alloc-mini"><span style={{ width: Math.min(100, alloc * 3) + '%', background: SECTOR_COLORS[p.sector] }} /></div>
                <div className="t-num td-dim td-alloc-n">{alloc.toFixed(1)}%</div>
              </div>
              <div className="td td-r">
                {p.flag === 'sell'
                  ? <a href="Signals.html" className="td-action sell">Sell <Icon.Arrow width="11" height="11" /></a>
                  : <span className="td-action hold">Hold</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── performance stats bar ──
function StatsBar() {
  return (
    <div className="pf-statsbar">
      {PERF_STATS.map((s) => (
        <div key={s.l} className="pf-stat">
          <div className="pf-stat-l">{s.l}</div>
          <div className={`pf-stat-v ${s.tone === 'bull' ? 'num-bull' : s.tone === 'bear' ? 'num-bear' : ''}`}>{s.v}</div>
        </div>
      ))}
    </div>
  );
}

// ── recently closed (this month) ──
function ClosedPanel() {
  return (
    <div className="pf-panel pf-closed">
      <div className="pf-panel-head">
        <div className="pf-panel-title">Recently closed <span className="pf-h-count">MTD</span></div>
        <span className="pf-closed-total">Realised <b className="num-bull">{fmtSignedINR(REALISED_MTD)}</b></span>
      </div>
      <div className="pf-closed-list">
        {CLOSED_MTD.map((c) => (
          <a key={c.sym} href="Signals.html" className="pf-closed-row">
            <Logo sym={c.sym} size={30} radius={8} />
            <div className="pf-closed-id">
              <div className="pf-closed-sym">{c.sym}</div>
              <div className="pf-closed-name">{c.name}</div>
            </div>
            <span className={`pf-closed-chip ${c.won ? 'won' : 'lost'}`}>{c.won ? 'Target' : 'Stop'}</span>
            <div className="pf-closed-pnl">
              <div className={`t-num ${c.won ? 'num-bull' : 'num-bear'}`}>{fmtSignedINR(c.pnl)}</div>
              <div className={`pf-closed-pct t-num ${c.won ? 'num-bull' : 'num-bear'}`}>{fmtPct(c.pct)}</div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// ── App ──
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "brandColor":  "#4F8CFF",
  "timeframe":   "6M"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tf, setTf] = React.useState(t.timeframe || '6M');
  React.useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--brand', t.brandColor);
    root.style.setProperty('--brand-hi', t.brandColor);
    root.style.setProperty('--brand-soft', hexToRgba(t.brandColor, 0.14));
    root.style.setProperty('--brand-edge', hexToRgba(t.brandColor, 0.40));
  }, [t.brandColor]);
  React.useEffect(() => { setTf(t.timeframe); }, [t.timeframe]);

  const flagged = POSITIONS.filter((p) => p.flag === 'sell');

  return (
    <div className="app pf-app">
      <Topbar />

      <div className="pf-subhead">
        <div>
          <div className="t-ui-micro">PORTFOLIO · LIVE · TUE 2 JUN</div>
          <h1 className="pf-title">Portfolio</h1>
          <div className="pf-state">
            <span><b className="t-num">{POSITIONS.length}</b> open positions</span>
            <span className="sep">·</span>
            <span><b className="num-bull t-num">{WINNERS}</b> winning</span>
            <span className="sep">·</span>
            <span><b className="num-bear t-num">{LOSERS}</b> in drawdown</span>
          </div>
        </div>
        <a href="Signals.html" className="pf-cta">Review signals <Icon.Arrow width="14" height="14" /></a>
      </div>

      {flagged.length > 0 && (
        <a href="Signals.html" className="pf-attention">
          <span className="pf-att-icon"><Icon.Alert width="16" height="16" /></span>
          <span className="pf-att-text">
            <b>{flagged.length} position{flagged.length > 1 ? 's' : ''} flagged to sell</b> — {flagged.map((p) => `${p.sym} (${p.flagReason.toLowerCase()})`).join(' · ')}
          </span>
          <span className="pf-att-go">Review &amp; exit <Icon.Arrow width="13" height="13" /></span>
        </a>
      )}

      <div className="pf-kpis">
        <Kpi micro="Total equity" value={fmtLakh(EQUITY)} spark={KPI_SPARK.equity} sparkTone="brand">
          <span className={`pill ${DAY_PNL >= 0 ? 'pill-bull' : 'pill-bear'}`}>{fmtSignedINR(DAY_PNL)} · {fmtPct(DAY_PNL_PCT)}</span> today
        </Kpi>
        <Kpi micro="Invested" value={fmtLakh(INVESTED)} spark={KPI_SPARK.invested} sparkTone="brand">
          {fmtLakh(CASH)} cash available
        </Kpi>
        <Kpi micro="Open P&L" value={fmtSignedINR(OPEN_PNL)} valueClass={OPEN_PNL >= 0 ? 'num-bull' : 'num-bear'} spark={KPI_SPARK.openpnl} sparkTone={OPEN_PNL >= 0 ? 'bull' : 'bear'}>
          <span className={OPEN_PNL >= 0 ? 'num-bull' : 'num-bear'}>{fmtPct(OPEN_PNL_PCT)}</span> on cost basis
        </Kpi>
        <Kpi micro="Realised · MTD" value={fmtSignedINR(REALISED_MTD)} valueClass={REALISED_MTD >= 0 ? 'num-bull' : 'num-bear'} spark={KPI_SPARK.realised} sparkTone={REALISED_MTD >= 0 ? 'bull' : 'bear'}>
          4 closed · 2 won · 2 lost
        </Kpi>
      </div>

      <StatsBar />

      <div className="pf-grid">
        <EquityCurve tf={tf} setTf={setTf} />
        <Donut />
      </div>

      <div className="pf-lower">
        <Holdings />
        <ClosedPanel />
      </div>

      <footer className="pf-foot">
        <div className="pf-disclaimer">Research and decision-support output, not investment advice. Holdings and P&amp;L reflect your own Kite account. Past performance does not indicate future returns. All trading carries risk of loss.</div>
        <div className="pf-foot-meta">SEBI Research Analyst · INH000012345 · Synced with Zerodha Kite · last sync 14s ago · v2026.05</div>
      </footer>

      <TweaksPanel>
        <TweakSection label="Brand color" />
        <TweakColor label="Primary" value={t.brandColor} options={['#4F8CFF', '#7B5BFF', '#3FDD8A', '#FFB454']} onChange={(v) => setTweak('brandColor', v)} />
        <TweakSection label="Equity curve" />
        <TweakRadio label="Timeframe" value={t.timeframe} options={['3M', '6M', '1Y', 'All']} onChange={(v) => setTweak('timeframe', v)} />
      </TweaksPanel>
    </div>
  );
}

function hexToRgba(hex, a) { const m = hex.replace('#', ''); return `rgba(${parseInt(m.substring(0, 2), 16)},${parseInt(m.substring(2, 4), 16)},${parseInt(m.substring(4, 6), 16)},${a})`; }

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
