/* portfolio2.jsx — Nifty Satvik Portfolio.
 * Speaks the Dashboard's design language (glass cards, mono values, glowing
 * sparklines, regime strip, eyebrow→title→footnote rhythm, one gradient
 * accent) — but with a portfolio-native composition: a fused equity hero
 * (number + curve in one panel), a perf ribbon, a risk ribbon, holdings,
 * a stacked allocation bar, recently closed. Not a clone of the dashboard.
 */
const fmtINR  = (n) => '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtNum  = (n) => n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct  = (n) => (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
const fmtPct1 = (n) => (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%';
const fmtLakh = (n) => { const s = n < 0 ? '−' : '', a = Math.abs(n); if (a >= 1e7) return s + '₹' + (a / 1e7).toFixed(2) + 'Cr'; if (a >= 1e5) return s + '₹' + (a / 1e5).toFixed(2) + 'L'; return s + '₹' + Math.round(a).toLocaleString('en-IN'); };
const fmtSignedINR = (n) => (n >= 0 ? '+' : '−') + '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN');

const Icon = {
  Search:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>,
  Bell:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>,
  ArrDown: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>,
  Arrow:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>,
  Layers:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="m12 2 10 5-10 5L2 7l10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>,
};
const TICKER_DOMAINS = { ICICIBANK: 'icicibank.com', HDFCBANK: 'hdfcbank.com', POLYCAB: 'polycab.com', MARUTI: 'marutisuzuki.com', CUMMINSIND: 'cummins.com', DIVISLAB: 'divislabs.com', BHARTIARTL: 'airtel.in', LT: 'larsentoubro.com', TATAPOWER: 'tatapower.com', VOLTAS: 'voltas.com', SBIN: 'sbi.co.in', TITAN: 'titancompany.com' };
function tickerBg(sym) { let h = 0; for (const ch of sym) h = (h + ch.charCodeAt(0) * 13) % 360; return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`; }
function Logo({ sym, size = 30, radius = 8 }) {
  const domain = TICKER_DOMAINS[sym];
  const sources = domain ? [`https://icons.duckduckgo.com/ip3/${domain}.ico`, `https://www.google.com/s2/favicons?domain=${domain}&sz=128`] : [];
  const [idx, setIdx] = React.useState(0);
  if (idx >= sources.length) return <div className="logo-tile logo-mono" style={{ width: size, height: size, borderRadius: radius, background: tickerBg(sym), fontSize: Math.round(size * 0.34) }}>{sym.slice(0, 2)}</div>;
  return <div className="logo-tile" style={{ width: size, height: size, borderRadius: radius }}><img src={sources[idx]} alt={sym} onError={() => setIdx((i) => i + 1)} /></div>;
}

const STATES = {
  prototype: { tone: 'amber', badge: 'PROTOTYPE', word: 'Prototype', context: 'No live trading · example data', startCap: 550000, equity: 700000, today: 1713, todayPct: 0.25, realized: { MTD: 6088, YTD: 41200, All: 61400 }, cash: 171274, qtyMul: 1, sebi: 'Not registered with SEBI — research prototype', risk: 'Not investment advice. Prototype only — all figures are illustrative example data, not real trades.' },
  paper:     { tone: 'blue', badge: 'PAPER', word: 'Paper', context: 'Day 34 of 90 · simulated execution', startCap: 500000, equity: 534200, today: 980, todayPct: 0.18, realized: { MTD: 3420, YTD: 12880, All: 34200 }, cash: 210400, qtyMul: 0.62, sebi: 'Not registered with SEBI — research prototype', risk: 'Not investment advice. Paper-trading simulation only — positions are not real and no capital is at risk.' },
  earlylive: { tone: 'green', badge: 'LIVE', word: 'Live', context: '2 months · ₹7.0L deployed', startCap: 640000, equity: 742000, today: 2100, todayPct: 0.28, realized: { MTD: 8900, YTD: 22400, All: 22400 }, cash: 120000, qtyMul: 1.06, sebi: 'Not registered with SEBI — single-operator research tool', risk: 'Not investment advice. Live trading carries risk of loss. Two-month track record is too short to be statistically meaningful.' },
  established: { tone: 'green', badge: 'LIVE', word: 'Live', context: '14 months · ₹52.4L deployed', startCap: 4100000, equity: 5243000, today: 24180, todayPct: 0.46, realized: { MTD: 124000, YTD: 680000, All: 1820000 }, cash: 840000, qtyMul: 7.5, sebi: 'Not registered with SEBI — single-operator research tool', risk: 'Not investment advice. Live trading carries risk of loss. Past performance does not indicate future returns. Subject to market risk.' },
};
const KILL = {
  prototype: [ { name: 'Drawdown', value: '−4.1%', status: 'ok', fill: 0.27 }, { name: 'Consec. losses', value: '1', status: 'ok', fill: 0.17 }, { name: 'Rolling-20 WR', value: '64%', status: 'ok', fill: 0.18 }, { name: 'Single-day loss', value: '−1.2%', status: 'ok', fill: 0.24 }, { name: 'Days w/o signal', value: '1', status: 'ok', fill: 0.10 } ],
  paper: [ { name: 'Drawdown', value: '−7.8%', status: 'ok', fill: 0.52 }, { name: 'Consec. losses', value: '3', status: 'ok', fill: 0.50 }, { name: 'Rolling-20 WR', value: '52%', status: 'soft', fill: 0.64 }, { name: 'Single-day loss', value: '−2.4%', status: 'ok', fill: 0.48 }, { name: 'Days w/o signal', value: '4', status: 'ok', fill: 0.40 } ],
  earlylive: [ { name: 'Drawdown', value: '−9.4%', status: 'soft', fill: 0.78 }, { name: 'Consec. losses', value: '4', status: 'soft', fill: 0.80 }, { name: 'Rolling-20 WR', value: '58%', status: 'ok', fill: 0.30 }, { name: 'Single-day loss', value: '−3.1%', status: 'ok', fill: 0.62 }, { name: 'Days w/o signal', value: '2', status: 'ok', fill: 0.20 } ],
  established: [ { name: 'Drawdown', value: '−6.2%', status: 'ok', fill: 0.41 }, { name: 'Consec. losses', value: '2', status: 'ok', fill: 0.33 }, { name: 'Rolling-20 WR', value: '66%', status: 'ok', fill: 0.16 }, { name: 'Single-day loss', value: '−1.8%', status: 'ok', fill: 0.36 }, { name: 'Days w/o signal', value: '1', status: 'ok', fill: 0.10 } ],
};
const KPI_META = { prototype: { won: 8, total: 12 }, paper: { won: 5, total: 11 }, earlylive: { won: 9, total: 14 }, established: { won: 14, total: 22 } };
function perfFor(stKey) {
  const live = (v) => ({ v, src: 'live' }), bt = (v) => ({ v, src: 'backtest' }), paper = (v) => ({ v, src: 'paper' });
  if (stKey === 'prototype') return [{ l: 'Sharpe', ...bt('1.84') }, { l: 'Max drawdown', ...bt('−12.6%') }, { l: 'Win rate', ...bt('63.8%') }, { l: 'Avg win/loss', ...bt('1.92') }];
  if (stKey === 'paper') return [{ l: 'Sharpe', ...bt('1.84') }, { l: 'Max drawdown', ...paper('−7.8%') }, { l: 'Win rate', ...paper('52.0%') }, { l: 'Avg win/loss', ...bt('1.92') }];
  if (stKey === 'earlylive') return [{ l: 'Sharpe', ...bt('1.84') }, { l: 'Max drawdown', ...live('−9.4%') }, { l: 'Win rate', ...live('58.0%') }, { l: 'Avg win/loss', ...bt('1.92') }];
  return [{ l: 'Sharpe', ...live('1.71') }, { l: 'Max drawdown', ...live('−6.2%') }, { l: 'Win rate', ...live('66.1%') }, { l: 'Avg win/loss', ...live('1.78') }];
}
const SRC_TAG = { live: 'LIVE', backtest: 'BACKTEST', paper: 'PAPER' };
const BASE_HOLDINGS = [
  { sym: 'ICICIBANK', name: 'ICICI Bank', sector: 'Financials', qty: 80, avg: 1194.20, ltp: 1281.40, day: 1.05, status: 'sell-target', target: 1278 },
  { sym: 'DIVISLAB', name: "Divi's Laboratories", sector: 'Pharma', qty: 22, avg: 5842.00, ltp: 5708.00, day: -0.84, status: 'sell-stop', target: 6180 },
  { sym: 'POLYCAB', name: 'Polycab India', sector: 'Capital Goods', qty: 14, avg: 6850.00, ltp: 7048.00, day: 0.72, status: 'hold', target: 7320 },
  { sym: 'HDFCBANK', name: 'HDFC Bank', sector: 'Financials', qty: 30, avg: 1686.00, ltp: 1742.60, day: 1.05, status: 'hold', target: 1812 },
  { sym: 'MARUTI', name: 'Maruti Suzuki', sector: 'Auto', qty: 4, avg: 12095.00, ltp: 12410.00, day: -0.42, status: 'hold', target: 12980 },
  { sym: 'CUMMINSIND', name: 'Cummins India', sector: 'Capital Goods', qty: 26, avg: 3748.00, ltp: 3848.00, day: 0.64, status: 'hold', target: 4060 },
];
const SECTOR_HEX = { 'Capital Goods': '#5BC7FF', 'Financials': '#4F8CFF', 'Pharma': '#3FDD8A', 'Auto': '#FFB454', 'Cash': '#5A6488' };
const CLOSED = [
  { sym: 'BHARTIARTL', reason: 'target', pnl: 6942, pct: 7.7, held: 8 }, { sym: 'LT', reason: 'target', pnl: 3304, pct: 6.9, held: 10 },
  { sym: 'TITAN', reason: 'time', pnl: 1180, pct: 1.4, held: 9 }, { sym: 'VOLTAS', reason: 'stop', pnl: -2178, pct: -4.3, held: 4 }, { sym: 'TATAPOWER', reason: 'stop', pnl: -1980, pct: -3.9, held: 3 },
];
const SHAPE = [0, 0.10, 0.22, 0.18, 0.34, 0.46, 0.40, 0.58, 0.72, 0.85, 1.0, 0.93, 0.97];
const BENCH = [0, 0.06, 0.12, 0.14, 0.20, 0.26, 0.24, 0.32, 0.38, 0.44, 0.50, 0.52, 0.55];
const PERIODS = ['1M', '3M', '6M', '1Y', 'All'];
// monthly realised P&L (₹, established scale) — scaled per state
const MONTHLY = [[ 'Jun', 82000], ['Jul', -31000], ['Aug', 124000], ['Sep', 68000], ['Oct', -18000], ['Nov', 156000], ['Dec', 92000], ['Jan', 210000], ['Feb', -44000], ['Mar', 138000], ['Apr', 176000], ['May', 124000]];

// ── chrome ──
function Topbar() {
  return (
    <header className="topbar">
      <a className="brand" href="Landing.html" style={{ textDecoration: 'none' }}>
        <div className="brand-mark"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19V8l5 6 4-9 4 11 3-5v8"/></svg></div>
        <div className="brand-text">Nifty Satvik</div>
      </a>
      <div className="search"><Icon.Search width="14" height="14" /><input placeholder="Search holdings, sector, or ticker…" /><kbd>⌘K</kbd></div>
      <nav className="tabs">
        <a className="tab" href="Dashboard.html">Dashboard</a><a className="tab" href="Signals.html">Signals</a>
        <a className="tab active" href="Portfolio.html">Portfolio</a><a className="tab" href="Signals.html">Backtest</a><a className="tab" href="Signals.html">Track record</a>
      </nav>
      <div className="top-actions">
        <button className="icon-btn"><Icon.Layers width="16" height="16" /></button>
        <button className="icon-btn"><Icon.Bell width="16" height="16" /><span className="bell-dot" /></button>
        <div className="op-chip"><span className="op-dot" /> Operator</div>
      </div>
    </header>
  );
}
function StateStrip({ st, killWorst }) {
  const word = killWorst === 'ok' ? 'All kill criteria clear' : killWorst === 'soft' ? 'Soft warning active' : 'HARD KILL';
  return (
    <div className="regime-strip">
      <div className="regime-left">
        <span className={`live-dot ${st.tone === 'amber' ? 'dot-warn' : st.tone === 'blue' ? 'dot-info' : ''}`} />
        <span className="regime-eyebrow">{st.badge}</span>
        <span className="regime-statement">Portfolio is <em>{st.word}</em><span className="sep">·</span><span>{st.context}</span><span className="sep">·</span><span className="t-num-small">NIFTY 24,182.40</span><span className="num-bull t-num-small">+0.68%</span></span>
      </div>
      <div className="regime-right"><span className="strength-label">RISK</span><span className={`kw kw-${killWorst}`}>{word}</span></div>
    </div>
  );
}

// equity curve svg (shared) — glowing line + area + dashed bench + hover crosshair
function EquityChartSvg({ st, period, setPeriod }) {
  const PER = { '1M': 4, '3M': 6, '6M': 9, '1Y': 12, 'All': 13 };
  const TF = { '1M': ['4w', '2w', 'now'], '3M': ['Mar', 'Apr', 'May'], '6M': ['Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'], '1Y': ['Jun', 'Aug', 'Oct', 'Dec', 'Feb', 'Apr'], 'All': ['2024', '', '2025', '', '2026', ''] };
  const [hi, setHi] = React.useState(null);
  const svgRef = React.useRef(null);
  const n = PER[period], peakCap = st.equity / 0.97, N = Math.max(20, n * 6);
  const densify = (anchors, j) => { const m = anchors.length, out = []; let s = 137; const rnd = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return (s % 1000) / 1000; }; for (let i = 0; i < N; i++) { const t = (i / (N - 1)) * (m - 1), lo = Math.floor(t), hiI = Math.min(m - 1, lo + 1), f = (1 - Math.cos((t - lo) * Math.PI)) / 2; out.push(anchors[lo] * (1 - f) + anchors[hiI] * f + (rnd() - 0.5) * j); } return out; };
  const equity = densify(SHAPE.slice(-n), 0.03).map((s) => st.startCap + (peakCap - st.startCap) * Math.max(0, s));
  const benchV = densify(BENCH.slice(-n), 0.015).map((b) => st.startCap + (peakCap - st.startCap) * b * 0.62);
  const W = 640, H = 250, padL = 4, padR = 56, padT = 16, padB = 22;
  const all = [...equity, ...benchV], dMin = Math.min(...all), dMax = Math.max(...all);
  const step = (() => { const raw = (dMax - dMin) / 3.2, mag = Math.pow(10, Math.floor(Math.log10(raw))), nrm = raw / mag; return (nrm < 1.5 ? 1 : nrm < 3 ? 2 : nrm < 7 ? 5 : 10) * mag; })();
  const min = Math.floor(dMin / step) * step, max = Math.ceil(dMax / step) * step, range = (max - min) || 1;
  const ticks = []; for (let v = min; v <= max + 1e-6; v += step) ticks.push(v);
  const x = (i) => padL + (i * (W - padL - padR)) / (N - 1), y = (v) => padT + (H - padT - padB) * (1 - (v - min) / range);
  const line = (arr) => arr.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const eLine = line(equity), eArea = `${eLine} L${x(N - 1)},${H - padB} L${x(0)},${H - padB} Z`, peak = Math.max(...equity);
  const onMove = (e) => { const r = svgRef.current.getBoundingClientRect(); setHi(Math.max(0, Math.min(N - 1, Math.round(((e.clientX - r.left) / r.width) * (N - 1))))); };
  const hp = hi == null ? null : { i: hi, e: equity[hi], r: ((equity[hi] - st.startCap) / st.startCap) * 100 };
  return (
    <div className="eq-wrap" onMouseLeave={() => setHi(null)}>
      {hp && <div className="eq-tip" style={{ left: `${(x(hp.i) / W) * 100}%` }}><b>{fmtLakh(hp.e)}</b><span className={hp.r >= 0 ? 'num-bull' : 'num-bear'}>{fmtPct1(hp.r)}</span></div>}
      <svg ref={svgRef} className="eq-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" onMouseMove={onMove}>
        <defs><linearGradient id="eqf" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--brand-hi)" stopOpacity="0.24"/><stop offset="100%" stopColor="var(--brand-hi)" stopOpacity="0"/></linearGradient></defs>
        {ticks.map((tv, i) => <g key={i}><line className="eq-grid" x1={padL} y1={y(tv)} x2={W - padR} y2={y(tv)} /><text className="eq-ax" x={W - padR + 6} y={y(tv) + 3}>{fmtLakh(tv).replace('.00', '')}</text></g>)}
        <line className="eq-peak" x1={padL} y1={y(peak)} x2={W - padR} y2={y(peak)} /><text className="eq-peak-l" x={padL + 3} y={y(peak) - 4}>PEAK {fmtLakh(peak)}</text>
        <path d={eArea} fill="url(#eqf)" /><path className="eq-bench" d={line(benchV)} /><path className="eq-line" d={eLine} />
        {hp && <line className="eq-cross" x1={x(hp.i)} y1={padT} x2={x(hp.i)} y2={H - padB} />}
        <circle cx={x(hp ? hp.i : N - 1)} cy={y(hp ? hp.e : equity[N - 1])} r="4" fill="var(--brand-hi)" stroke="#0a0e22" strokeWidth="1.5" />
      </svg>
      <div className="eq-xax">{TF[period].map((l, i) => <span key={i}>{l}</span>)}</div>
    </div>
  );
}

// FUSED EQUITY HERO — big number + KPI stack + curve in one wide glass panel
function EquityHero({ st, stKey, holdings, openPnl }) {
  const [period, setPeriod] = React.useState('All');
  const [rper, setRper] = React.useState('MTD');
  const invested = holdings.reduce((a, h) => a + h.value, 0);
  const deployed = (invested / st.equity) * 100;
  const curRet = ((st.equity / st.startCap) - 1) * 100, benchRet = curRet * 0.36;
  const tr = KPI_META[stKey], upN = holdings.filter((h) => h.pnl >= 0).length;
  return (
    <div className="card eq-hero">
      <div className="eqh-l">
        <div className="t-ui-micro">TOTAL EQUITY · MARK-TO-MARKET</div>
        <div className="eqh-eq">{fmtLakh(st.equity)}</div>
        <div className="eqh-delta"><span className={`tag ${st.today >= 0 ? 'tag-bull' : 'tag-bear'}`}>{fmtSignedINR(st.today)} · {fmtPct(st.todayPct)}</span> today &nbsp;·&nbsp; YOU <b className="num-bull">{fmtPct1(curRet)}</b> &nbsp;NIFTY <b className="dim">{fmtPct1(benchRet)}</b></div>
        <div className="eqh-kpis">
          <div className="eqh-kpi"><span className="ek-l">Open P&amp;L</span><span className={`ek-v ${openPnl >= 0 ? 'num-bull' : 'num-bear'}`}>{fmtSignedINR(openPnl)}</span><span className="ek-s">{upN}/{holdings.length} up</span></div>
          <div className="eqh-kpi"><span className="ek-l">Realized<span className="ek-seg">{['MTD', 'YTD', 'All'].map((p) => <button key={p} className={rper === p ? 'on' : ''} onClick={() => setRper(p)}>{p}</button>)}</span></span><span className={`ek-v ${st.realized[rper] >= 0 ? 'num-bull' : 'num-bear'}`}>{fmtSignedINR(st.realized[rper])}</span><span className="ek-s">{tr.won}/{tr.total} won</span></div>
          <div className="eqh-kpi"><span className="ek-l">Deployed</span><span className="ek-v">{deployed.toFixed(0)}%</span><span className="ek-s">{fmtLakh(invested)}</span></div>
          <div className="eqh-kpi"><span className="ek-l">Cash</span><span className="ek-v">{fmtLakh(st.cash)}</span><span className="ek-s">deployable</span></div>
        </div>
      </div>
      <div className="eqh-r">
        <div className="eqh-r-head"><span className="t-ui-footnote">Equity curve · vs Nifty 500 · since inception</span><div className="seg eqh-seg">{PERIODS.map((p) => <button key={p} className={`seg-btn ${period === p ? 'active' : ''}`} onClick={() => setPeriod(p)}>{p}</button>)}</div></div>
        <EquityChartSvg st={st} period={period} setPeriod={setPeriod} />
      </div>
    </div>
  );
}

// performance ribbon — thin row of source-tagged stat chips
function PerfRibbon({ stKey }) {
  return (
    <div className="perf-ribbon">
      {perfFor(stKey).map((m) => (
        <div key={m.l} className="prc">
          <span className="prc-l">{m.l}</span>
          <span className="prc-v">{m.v}</span>
          <span className={`prc-src src-${m.src}`}>{SRC_TAG[m.src]}</span>
        </div>
      ))}
      <div className="prc prc-note"><span className="prc-l">Track record</span><span className="prc-v dim">130+ closed trades</span></div>
    </div>
  );
}

// risk ribbon — full-width margin-to-kill cells
function RiskRibbon({ items, killWorst }) {
  const v = killWorst === 'ok' ? 'ALL CLEAR' : killWorst === 'soft' ? 'SOFT WARNING' : 'HARD KILL';
  return (
    <div className="card risk-card">
      <div className="card-head"><div><div className="t-ui-headline">Risk · margin to kill</div><div className="t-ui-footnote">five hard limits monitored every session</div></div><span className={`kw kw-${killWorst}`}>{v}</span></div>
      <div className="risk-cells">
        {items.map((k) => (
          <div key={k.name} className={`rc rc-${k.status} ${k.status !== 'ok' ? 'rc-pulse' : ''}`}>
            <div className="rc-name">{k.name}</div>
            <div className="rc-val">{k.value}</div>
            <div className="rc-bar"><span style={{ width: Math.round(k.fill * 100) + '%' }} /></div>
            <div className="rc-pct">{Math.round(k.fill * 100)}% to kill</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// holdings table
const SP = { hold: ['HOLD', 'sp-hold'], 'sell-target': ['SELL · TGT', 'sp-tgt'], 'sell-stop': ['SELL · STP', 'sp-stp'] };
function HoldingsTable({ holdings, equity }) {
  return (
    <div className="stocks-table">
      <div className="stocks-table-head">
        <div className="stocks-table-title"><div><div className="t-ui-headline">Holdings</div><div className="t-ui-footnote">{holdings.length} open · synced with Kite 14s ago</div></div></div>
        <div className="stocks-table-tabs"><button className="ttab active">All</button><button className="ttab">Winners</button><button className="ttab">To exit</button></div>
      </div>
      <div className="pf-htbl">
        <div className="th">Company</div><div className="th th-r">Qty</div><div className="th th-r">Avg</div><div className="th th-r">LTP</div><div className="th th-r">Value</div><div className="th th-r">Day</div><div className="th th-r">Unreal. P&amp;L</div><div className="th th-r">Alloc</div><div className="th th-r">Status</div>
        {holdings.map((h) => { const al = (h.value / equity) * 100, sp = SP[h.status]; return (
          <React.Fragment key={h.sym}>
            <div className="td td-name"><Logo sym={h.sym} size={32} radius={8} /><div><div className="td-name-sym">{h.sym}</div><div className="td-name-full">{h.sector}</div></div></div>
            <div className="td td-r tabular-nums">{Math.round(h.qty)}</div>
            <div className="td td-r tabular-nums" style={{ color: 'var(--text-3)' }}>{fmtNum(h.avg)}</div>
            <div className="td td-r tabular-nums">{fmtNum(h.ltp)}</div>
            <div className="td td-r tabular-nums">{fmtLakh(h.value)}</div>
            <div className="td td-r tabular-nums" style={{ color: h.day >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtPct(h.day)}</div>
            <div className="td td-r tabular-nums" style={{ color: h.pnl >= 0 ? 'var(--bull)' : 'var(--bear)' }}><div className="pcol"><span className="pf-pnl-v">{fmtSignedINR(h.pnl)}</span><span className="pf-pnl-p">{fmtPct(h.pnlPct)}</span></div></div>
            <div className="td td-r"><div className="acol"><span className="al-mini"><span style={{ width: Math.min(100, al * 2.6) + '%' }} /></span><span className="al-n tabular-nums">{al.toFixed(1)}%</span></div></div>
            <div className="td td-r"><span className={`spill ${sp[1]}`}>{sp[0]}</span></div>
          </React.Fragment>
        ); })}
      </div>
    </div>
  );
}

// allocation — stacked bar + ranked list (NOT bubbles)
function AllocCard({ holdings, cash, equity }) {
  const by = {}; holdings.forEach((h) => { by[h.sector] = (by[h.sector] || 0) + h.value; });
  const rows = Object.entries(by).map(([name, v]) => ({ name, v, pct: (v / equity) * 100 })); rows.push({ name: 'Cash', v: cash, pct: (cash / equity) * 100 });
  rows.sort((a, b) => b.v - a.v);
  return (
    <div className="card">
      <div className="card-head"><div><div className="t-ui-headline">Allocation</div><div className="t-ui-footnote">% of equity · {holdings.length} positions</div></div><span className="t-num-small dim">{fmtLakh(equity)}</span></div>
      <div className="alloc-stack">{rows.map((r) => <span key={r.name} style={{ width: r.pct + '%', background: SECTOR_HEX[r.name] }} title={`${r.name} ${r.pct.toFixed(1)}%`} />)}</div>
      <div className="alloc-list">
        {rows.map((r) => (
          <div key={r.name} className="al-row"><span className="al-dot" style={{ background: SECTOR_HEX[r.name] }} /><span className="al-name">{r.name}</span><span className="al-pct t-num-small">{r.pct.toFixed(1)}%</span><span className="al-val t-num-small dim">{fmtLakh(r.v)}</span></div>
        ))}
      </div>
    </div>
  );
}
const RSN = { target: ['TGT', 'won'], stop: ['STP', 'lost'], time: ['TIME', 'neu'] };
function ClosedCard() {
  const tot = CLOSED.reduce((a, c) => a + c.pnl, 0);
  return (
    <div className="card">
      <div className="card-head"><div><div className="t-ui-headline">Recently closed</div><div className="t-ui-footnote">last 5 trades · this month</div></div><span className="t-num-small num-bull">{fmtSignedINR(tot)}</span></div>
      <div className="closed-list">
        {CLOSED.map((c) => { const r = RSN[c.reason]; return (
          <div key={c.sym} className="cl-row"><Logo sym={c.sym} size={26} radius={6} /><span className="cl-sym">{c.sym}</span><span className={`cl-rsn ${r[1]}`}>{r[0]}</span><span className="cl-held t-num-small dim">{c.held}d</span><span className={`cl-pnl t-num-small ${c.pnl >= 0 ? 'num-bull' : 'num-bear'}`}>{fmtSignedINR(c.pnl)}</span></div>
        ); })}
      </div>
    </div>
  );
}

// monthly realised P&L bar chart
function MonthlyPnl({ st }) {
  const scale = st.equity / 5243000;
  const data = MONTHLY.map(([m, v]) => ({ m, v: v * scale }));
  const maxAbs = Math.max(...data.map((d) => Math.abs(d.v)));
  const pos = data.filter((d) => d.v >= 0).length;
  return (
    <div className="card">
      <div className="card-head"><div><div className="t-ui-headline">Monthly realised P&amp;L</div><div className="t-ui-footnote">closed-trade P&amp;L by month · {pos} of {data.length} months green</div></div></div>
      <div className="mp-chart">
        <div className="mp-baseline" />
        {data.map((d) => { const h = (Math.abs(d.v) / maxAbs) * 48; const up = d.v >= 0; return (
          <div key={d.m} className="mp-col" title={`${d.m} · ${fmtSignedINR(d.v)}`}>
            <div className="mp-bar-wrap">
              <span className={`mp-bar ${up ? 'b-up' : 'b-dn'}`} style={up ? { bottom: '50%', height: h + '%' } : { top: '50%', height: h + '%' }} />
            </div>
            <div className="mp-m">{d.m}</div>
          </div>
        ); })}
      </div>
    </div>
  );
}

// ── App ──
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "previewState": "established",
  "brandColor": "#4F8CFF"
}/*EDITMODE-END*/;
function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [stKey, setStKey] = React.useState(t.previewState || 'established');
  React.useEffect(() => { setStKey(t.previewState); }, [t.previewState]);
  React.useEffect(() => { const r = document.documentElement; r.style.setProperty('--brand', t.brandColor); r.style.setProperty('--brand-hi', t.brandColor); r.style.setProperty('--brand-soft', hexToRgba(t.brandColor, 0.14)); r.style.setProperty('--brand-edge', hexToRgba(t.brandColor, 0.40)); }, [t.brandColor]);
  const st = STATES[stKey];
  const holdings = BASE_HOLDINGS.map((h) => { const qty = h.qty * st.qtyMul, value = qty * h.ltp, cost = qty * h.avg, pnl = value - cost; return { ...h, qty, value, cost, pnl, pnlPct: (pnl / cost) * 100 }; });
  const openPnl = holdings.reduce((a, h) => a + h.pnl, 0);
  const items = KILL[stKey];
  const killWorst = items.some((k) => k.status === 'hard') ? 'hard' : items.some((k) => k.status === 'soft') ? 'soft' : 'ok';
  return (
    <div className="app density-regular">
      <Topbar />
      <StateStrip st={st} killWorst={killWorst} />
      <main className="work">
        <section className="row pf-head-row">
          <div className="row-head">
            <div><div className="t-ui-micro">PORTFOLIO · MONITORING</div><h2 className="row-title">Portfolio</h2><div className="t-ui-footnote">Live mark-to-market · {st.context}</div></div>
            <div className="row-controls"><div className="seg">{[['prototype', 'Prototype'], ['paper', 'Paper'], ['earlylive', 'Live · early'], ['established', 'Live']].map(([k, l]) => <button key={k} className={`seg-btn ${stKey === k ? 'active' : ''}`} onClick={() => setStKey(k)}>{l}</button>)}</div></div>
          </div>
        </section>
        <section className="row"><EquityHero st={st} stKey={stKey} holdings={holdings} openPnl={openPnl} /></section>
        <section className="row"><PerfRibbon stKey={stKey} /></section>
        <section className="row"><RiskRibbon items={items} killWorst={killWorst} /></section>
        <section className="row"><MonthlyPnl st={st} /></section>
        <section className="row row-data">
          <HoldingsTable holdings={holdings} equity={st.equity} />
          <aside className="right-rail"><AllocCard holdings={holdings} cash={st.cash} equity={st.equity} /><ClosedCard /></aside>
        </section>
        <footer className="work-foot">
          <div className="t-ui-footnote pf-disc">{st.sebi} · {st.risk}</div>
          <div className="t-ui-footnote">Synced with Zerodha Kite · v2026.05</div>
        </footer>
      </main>
      <TweaksPanel>
        <TweakSection label="Preview state" />
        <TweakSelect label="Lifecycle" value={t.previewState} options={['prototype', 'paper', 'earlylive', 'established']} onChange={(v) => setTweak('previewState', v)} />
        <TweakSection label="Brand color" />
        <TweakColor label="Primary" value={t.brandColor} options={['#4F8CFF', '#7B5BFF', '#3FDD8A', '#FFB454']} onChange={(v) => setTweak('brandColor', v)} />
      </TweaksPanel>
    </div>
  );
}
function hexToRgba(hex, a) { const m = hex.replace('#', ''); return `rgba(${parseInt(m.substring(0, 2), 16)},${parseInt(m.substring(2, 4), 16)},${parseInt(m.substring(4, 6), 16)},${a})`; }
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
