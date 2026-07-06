/* signals.jsx — Nifty Satvik Signals page (action-first, desktop split-pane)
 * Self-contained: own helpers + data, loaded via <script type="text/babel">.
 * Instrument chart uses TradingView Lightweight Charts (per design system).
 *
 * Pattern: desktop = master-detail SPLIT-PANE (list left, chart+detail right).
 * Mobile (≤900px) = tap a card to PUSH a full-screen detail view (not a drawer).
 * Lead with the ACTION and the RISK; never surface raw model internals.
 *
 * NOTE on fonts: the Nifty Satvik design system retired Reckless/Berkeley/Untitled
 * in favour of DM Sans only (tokens --font-display/-mono/-sans). Numbers keep
 * tabular-nums via the mono token. This is intentional, per the live token set.
 */

// ─────────────────────────────────────────────────────────────────────
// signalCopy — all client-facing section/conviction strings live here.
// Compliance: no "guarantee / will / sure / sure-shot" anywhere in the bundle.
// ─────────────────────────────────────────────────────────────────────
const SECTIONS = {
  SELL:    { id: 'sell-now', title: 'Sell now',           sub: 'Model has exited — sell on next open.' },
  BUY:     { id: 'buy-today', title: 'Buy today',         sub: "Today's high-conviction signals." },
  CLOSING: { id: 'closing',  title: 'Buy window closing', sub: 'Still actionable, window closing.' },
  HOLD:    { id: 'holding',  title: 'Holding',            sub: 'Tracking — no action needed.' },
  WATCH:   { id: 'brewing',  title: 'Brewing',            sub: 'Watching for a trigger.' },
  CLOSED:  { id: 'closed',   title: 'Closed & missed',    sub: 'Resolved or past the window.' },
};
const SECTION_ORDER = [SECTIONS.SELL, SECTIONS.BUY, SECTIONS.CLOSING, SECTIONS.HOLD, SECTIONS.WATCH, SECTIONS.CLOSED];

const CONVICTION = { HIGH: 'High conviction', MED: 'Moderate conviction', LOW: 'Low — watchlist only' };

const DISCLAIMER =
  'Research and decision-support output, not investment advice. Model and backtested ' +
  'results are not indicative of future returns. All trading carries risk of loss; ' +
  'you are responsible for your own decisions.';

const REGIME = 'BULL · VIX 14.2 · breadth +0.34 · Last scan 4:15 PM IST · Next 4:15 PM IST tomorrow';

const PORTFOLIO_CAPITAL = 330000; // ₹ — used for "% of your portfolio risked"
const RISK_BUDGET = 5000;         // ₹ risk per trade for suggested sizing

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────
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

const Icon = {
  Search:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>,
  Bell:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>,
  Arrow:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>,
  ArrDown: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>,
  Back:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>,
  Layers:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="m12 2 10 5-10 5L2 7l10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>,
  Check:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>,
  Bolt:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>,
  Clock:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>,
  Info:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/></svg>,
  Alert:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>,
};

const TICKER_DOMAINS = {
  RELIANCE: 'ril.com', TCS: 'tcs.com', BAJFINANCE: 'bajajfinserv.in', INFY: 'infosys.com',
  HDFCBANK: 'hdfcbank.com', ICICIBANK: 'icicibank.com', BHARTIARTL: 'airtel.in',
  LT: 'larsentoubro.com', MARUTI: 'marutisuzuki.com', KOTAKBANK: 'kotak.com',
  ADANIENT: 'adanienterprises.com', SBIN: 'sbi.co.in', AXISBANK: 'axisbank.com',
  TATAPOWER: 'tatapower.com', POLYCAB: 'polycab.com', VOLTAS: 'voltas.com',
  CUMMINSIND: 'cummins.com', TITAN: 'titancompany.com', SUNPHARMA: 'sunpharma.com',
  DIVISLAB: 'divislabs.com', PERSISTENT: 'persistent.com', WIPRO: 'wipro.com',
};

function tickerBg(sym) {
  let h = 0;
  for (const ch of sym) h = (h + ch.charCodeAt(0) * 13) % 360;
  return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`;
}

function Logo({ sym, size = 32, radius = 9 }) {
  const domain = TICKER_DOMAINS[sym];
  const sources = domain
    ? [`https://icons.duckduckgo.com/ip3/${domain}.ico`, `https://www.google.com/s2/favicons?domain=${domain}&sz=128`]
    : [];
  const [idx, setIdx] = React.useState(0);
  React.useEffect(() => { setIdx(0); }, [sym]);
  if (idx >= sources.length) {
    return <div className="logo-tile logo-mono" style={{ width: size, height: size, borderRadius: radius, background: tickerBg(sym), fontSize: Math.round(size * 0.34) }}>{sym.slice(0, 2)}</div>;
  }
  return <div className="logo-tile" style={{ width: size, height: size, borderRadius: radius }}><img src={sources[idx]} alt={sym} onError={() => setIdx((i) => i + 1)} /></div>;
}

// secondary model-state chip (kept alongside the action chip). No amber here.
const STATUS = {
  fresh:    { label: 'Fresh',          cls: 'c-info',  live: true },
  'in-zone':{ label: 'In zone',        cls: 'c-brand' },
  extended: { label: 'Extended',       cls: 'c-info' },
  target:   { label: 'Target reached', cls: 'c-bull' },
  stopped:  { label: 'Stop hit',       cls: 'c-bear' },
  active:   { label: 'Active',         cls: 'c-bull' },
  'hit-target': { label: 'Hit target', cls: 'c-bull' },
  'hit-stop':   { label: 'Hit stop',   cls: 'c-bear' },
  expired:  { label: 'Expired',        cls: 'c-muted' },
};

function convOf(grade, watch) {
  const g = grade[0];
  if (watch && g !== 'A') return { word: CONVICTION.LOW, cls: 'conv-c' };
  if (g === 'A') return { word: CONVICTION.HIGH, cls: 'conv-a' };
  if (g === 'B') return { word: CONVICTION.MED, cls: 'conv-b' };
  return { word: CONVICTION.LOW, cls: 'conv-c' };
}
function rrTone(rr) { return !isFinite(rr) ? 'num-bull' : rr >= 2 ? 'num-bull' : rr >= 1 ? '' : 'num-bear'; }
function rrWord(rr) { return rr >= 2 ? 'solid' : rr >= 1 ? 'fair' : 'thin'; }
// breakeven stop (entry === stop) means zero risk → R:R is undefined, show "risk-free"
function rrDisplay(sig) {
  if (sig.zeroRisk || !isFinite(sig.rr)) return { val: '—', word: 'risk-free', tone: 'num-bull', free: true };
  return { val: sig.rr.toFixed(2), word: rrWord(sig.rr), tone: rrTone(sig.rr), free: false };
}

// ─────────────────────────────────────────────────────────────────────
// Mock data — 22 signals across all six sections. `today` = Tue 2 Jun 2026.
// ─────────────────────────────────────────────────────────────────────
const RAW_SIGNALS = [
  // ── SELL NOW (2) ──
  { sym: 'ICICIBANK', name: 'ICICI Bank', sector: 'Financials', ex: 'NSE', grade: 'A', status: 'target', action: 'sell-now', sellReason: 'target',
    entry: 1192.00, stop: 1156.00, target: 1278.00, ltp: 1281.40, hold: 11, scanned: '3d ago', layers: 6, qty: 80, fillPrice: 1194.20,
    why: 'Banking leadership carried the trade to its objective three sessions after entry, tagging ₹1,278 on strong volume.',
    risks: 'Holding past target gives back gains if the index rolls over. The favourable edge in this signal is now spent.' },
  { sym: 'DIVISLAB', name: "Divi's Laboratories", sector: 'Pharma', ex: 'NSE', grade: 'B+', status: 'stopped', action: 'sell-now', sellReason: 'stop', highRisk: true,
    entry: 5840.00, stop: 5720.00, target: 6180.00, ltp: 5708.00, hold: 9, scanned: '4d ago', layers: 4, qty: 22, fillPrice: 5842.00,
    why: 'Pharma momentum setup at entry, but follow-through faded after two sessions.',
    risks: 'A daily close below the stop voids the thesis. Selling now caps the loss at the one unit of risk that was budgeted.' },

  // ── BUY TODAY (3) ──
  { sym: 'RELIANCE', name: 'Reliance Industries', sector: 'Energy', ex: 'NSE', grade: 'A', status: 'fresh', action: 'buy-today', layers: 6,
    entry: 2948.20, stop: 2872.50, target: 3122.80, ltp: 2951.40, hold: 12, scanned: '2h ago', buyWindow: 'Tue 2 – Thu 4 Jun', buyBy: 'Thu 4 Jun', daysLeft: 2,
    why: 'Breakout above the 50-day high on 1.8× average volume, with energy-sector breadth expanding and relative strength at a 3-month high.',
    risks: 'A daily close back under ₹2,872 voids the breakout. Crude-oil swings or block-deal supply could cap the move before target.' },
  { sym: 'TCS', name: 'Tata Consultancy', sector: 'IT', ex: 'NSE', grade: 'A−', status: 'in-zone', action: 'buy-today', layers: 5,
    entry: 4128.50, stop: 4022.00, target: 4348.10, ltp: 4135.80, hold: 10, scanned: '2h ago', buyWindow: 'Tue 2 – Thu 4 Jun', buyBy: 'Thu 4 Jun', daysLeft: 2,
    why: 'Pullback into a rising 20-day average with a bullish engulfing candle as IT-sector breadth turns up after three weak sessions.',
    risks: 'Quarterly results are nine sessions away — a pre-earnings drift lower is possible. A weak US tech tape could weigh on the basket.' },
  { sym: 'SBIN', name: 'State Bank of India', sector: 'Financials', ex: 'NSE', grade: 'A', status: 'fresh', action: 'buy-today', layers: 6,
    entry: 768.40, stop: 742.00, target: 832.00, ltp: 770.10, hold: 12, scanned: '2h ago', buyWindow: 'Tue 2 – Thu 4 Jun', buyBy: 'Thu 4 Jun', daysLeft: 2,
    why: 'Reclaim of the 50-day average on heavy volume, with PSU-bank breadth at a multi-week high.',
    risks: 'A broad financials pullback could stall it before target. Size the position with the stop in mind, not the upside.' },

  // ── BUY WINDOW CLOSING (2) ──
  { sym: 'TITAN', name: 'Titan Company', sector: 'Consumer', ex: 'NSE', grade: 'A−', status: 'fresh', action: 'closing', layers: 5,
    entry: 3642.00, stop: 3548.00, target: 3858.00, ltp: 3651.50, hold: 14, scanned: 'Yesterday', buyWindow: 'Mon 1 – Wed 3 Jun', buyBy: 'Wed 3 Jun', daysLeft: 1,
    why: 'Cup-and-handle completion on the weekly chart with a festive-demand tailwind and relative strength at a 6-month high.',
    risks: 'A gold-price spike compresses jewellery margins. Chasing above ₹3,700 meaningfully worsens your reward-to-risk.' },
  { sym: 'AXISBANK', name: 'Axis Bank', sector: 'Financials', ex: 'NSE', grade: 'A−', status: 'fresh', action: 'closing', layers: 5,
    entry: 1124.00, stop: 1086.00, target: 1212.00, ltp: 1129.80, hold: 12, scanned: 'Yesterday', buyWindow: 'Mon 1 – Wed 3 Jun', buyBy: 'Wed 3 Jun', daysLeft: 1,
    why: 'Higher-low base break with improving credit-growth commentary and a firm banking tape.',
    risks: 'Late in the buy window. A gap-up open leaves a poor entry and a wider-than-ideal stop.' },

  // ── HOLDING (4) ──
  { sym: 'POLYCAB', name: 'Polycab India', sector: 'Capital Goods', ex: 'NSE', grade: 'A−', status: 'active', action: 'holding', layers: 5,
    entry: 6842.00, stop: 6842.00, target: 7320.00, ltp: 7048.00, hold: 13, dayOf: 5, scanned: '5d ago', qty: 14, fillPrice: 6850.00,
    why: 'Order-book strength and a clean ascending channel. The stop is trailed to breakeven, so the position now carries no risk.',
    risks: 'A channel break or a capital-goods wobble could stall the move. No action needed unless ₹6,850 gives way.' },
  { sym: 'HDFCBANK', name: 'HDFC Bank', sector: 'Financials', ex: 'NSE', grade: 'A', status: 'active', action: 'holding', layers: 6,
    entry: 1684.00, stop: 1648.00, target: 1812.00, ltp: 1742.60, hold: 12, dayOf: 3, scanned: '3d ago', qty: 30, fillPrice: 1686.00,
    why: 'Leadership reasserted after index-rebalancing flows settled, with price holding above a rising 20-day average.',
    risks: 'A rate-decision surprise could spike volatility. The trailing stop protects most of the open gain.' },
  { sym: 'MARUTI', name: 'Maruti Suzuki', sector: 'Auto', ex: 'NSE', grade: 'A−', status: 'active', action: 'holding', layers: 5,
    entry: 12080.00, stop: 11720.00, target: 12980.00, ltp: 12410.00, hold: 14, dayOf: 7, scanned: '7d ago', qty: 4, fillPrice: 12095.00,
    why: 'Volume-backed move off support as monthly auto-sales momentum improves.',
    risks: 'Input-cost or demand softness could cap the upside. Trail the stop higher as the trade advances.' },
  { sym: 'CUMMINSIND', name: 'Cummins India', sector: 'Capital Goods', ex: 'NSE', grade: 'A−', status: 'active', action: 'holding', layers: 5,
    entry: 3742.00, stop: 3610.00, target: 4060.00, ltp: 3848.00, hold: 13, dayOf: 9, scanned: '9d ago', qty: 26, fillPrice: 3748.00,
    why: 'Capital-goods strength and a steady uptrend channel; the position is comfortably in profit.',
    risks: 'A sharp market pullback could test the stop. Let the trend carry it toward target.' },

  // ── BREWING / WATCHLIST (5) ──
  { sym: 'SUNPHARMA', name: 'Sun Pharmaceutical', sector: 'Pharma', ex: 'NSE', grade: 'B+', status: 'extended', action: 'brewing', watch: true, highRisk: true, layers: 4,
    entry: 1742.00, stop: 1688.00, target: 1862.00, ltp: 1789.30, hold: 9, scanned: '2h ago',
    why: 'Momentum thrust above resistance with improving pharma-sector breadth.',
    risks: 'Price has run 2.7% past entry. Buying here means a wider stop and worse reward-to-risk. Wait for a pullback toward ₹1,742.' },
  { sym: 'ADANIENT', name: 'Adani Enterprises', sector: 'Conglomerate', ex: 'NSE', grade: 'B', status: 'extended', action: 'brewing', watch: true, highRisk: true, layers: 4,
    entry: 2942.00, stop: 2820.00, target: 3220.00, ltp: 2988.00, hold: 10, scanned: '2h ago',
    why: 'Volatile base-building near a major level, with volume starting to expand.',
    risks: 'Headline-driven swings make timing hard. Watchlist only until a clean trigger forms.' },
  { sym: 'KOTAKBANK', name: 'Kotak Mahindra Bank', sector: 'Financials', ex: 'NSE', grade: 'A−', status: 'in-zone', action: 'brewing', watch: true, layers: 5,
    entry: 1842.00, stop: 1788.00, target: 1968.00, ltp: 1836.00, hold: 12, scanned: '2h ago',
    why: 'Coiling under resistance with rising relative strength versus the banking index.',
    risks: 'No trigger yet. A failed breakout could trap early buyers — hold off until it clears.' },
  { sym: 'BAJFINANCE', name: 'Bajaj Finance', sector: 'Financials', ex: 'NSE', grade: 'A−', status: 'in-zone', action: 'brewing', watch: true, layers: 5,
    entry: 7218.00, stop: 7020.00, target: 7640.00, ltp: 7180.00, hold: 11, scanned: '2h ago',
    why: 'Bull-flag forming after a strong leg up, with the broader NBFC space firming.',
    risks: 'A rich valuation leaves little room for an earnings miss. Await confirmation of the breakout.' },
  { sym: 'INFY', name: 'Infosys', sector: 'IT', ex: 'NSE', grade: 'B+', status: 'extended', action: 'brewing', watch: true, highRisk: true, layers: 4,
    entry: 1842.00, stop: 1788.00, target: 1962.00, ltp: 1828.00, hold: 9, scanned: '2h ago',
    why: 'Basing above the 200-day average as IT sentiment steadies.',
    risks: 'A weak guidance read could undo the base. Watchlist only for now.' },

  // ── CLOSED & MISSED (6) ──
  { sym: 'BHARTIARTL', name: 'Bharti Airtel', sector: 'Telecom', ex: 'NSE', grade: 'A', status: 'hit-target', action: 'closed', layers: 6,
    entry: 1488.00, stop: 1442.00, target: 1604.00, ltp: 1606.20, hold: 8, scanned: '8d ago', qty: 60, fillPrice: 1489.50, closedPnl: 6942.0, closedPct: 7.7,
    why: 'The ARPU re-rating thesis played out cleanly; target tagged on day 8.',
    risks: 'Resolved at target — nothing to action.' },
  { sym: 'LT', name: 'Larsen & Toubro', sector: 'Capital Goods', ex: 'NSE', grade: 'A', status: 'hit-target', action: 'closed', layers: 6,
    entry: 3402.00, stop: 3308.00, target: 3640.00, ltp: 3642.00, hold: 10, scanned: '12d ago', qty: 14, fillPrice: 3406.00, closedPnl: 3304.0, closedPct: 6.9,
    why: 'Order-inflow strength drove a clean trend to target on day 6.',
    risks: 'Resolved at target — closed for a gain.' },
  { sym: 'VOLTAS', name: 'Voltas Ltd', sector: 'Consumer', ex: 'NSE', grade: 'B+', status: 'hit-stop', action: 'closed', highRisk: true, layers: 4,
    entry: 1684.00, stop: 1612.00, target: 1812.00, ltp: 1609.40, hold: 9, scanned: '11d ago', qty: 30, fillPrice: 1682.00, closedPnl: -2178.0, closedPct: -4.3,
    why: 'Breakout setup with improving discretionary breadth at entry.',
    risks: 'A discretionary selloff took the stop on day 4. The loss was capped at one unit of risk, as designed.' },
  { sym: 'TATAPOWER', name: 'Tata Power', sector: 'Energy', ex: 'NSE', grade: 'B+', status: 'hit-stop', action: 'closed', highRisk: true, layers: 4,
    entry: 462.00, stop: 446.00, target: 502.00, ltp: 444.80, hold: 9, scanned: '14d ago', qty: 110, fillPrice: 463.00, closedPnl: -1980.0, closedPct: -3.9,
    why: 'Momentum setup that failed on a sector rotation away from power names.',
    risks: 'Stopped on day 3. The capped loss did its job — no outsized drawdown.' },
  { sym: 'PERSISTENT', name: 'Persistent Systems', sector: 'IT', ex: 'NSE', grade: 'B+', status: 'expired', action: 'closed', layers: 4,
    entry: 5420.00, stop: 5260.00, target: 5760.00, ltp: 5388.00, hold: 7, scanned: '9d ago',
    why: 'A constructive base, but the entry trigger was on the soft side.',
    risks: 'Entry never reclaimed inside the 7-day window. No fill — no capital at risk.' },
  { sym: 'WIPRO', name: 'Wipro Ltd', sector: 'IT', ex: 'NSE', grade: 'B', status: 'expired', action: 'closed', layers: 4,
    entry: 552.00, stop: 536.00, target: 588.00, ltp: 548.00, hold: 7, scanned: '10d ago',
    why: 'A base attempt that lacked a clean trigger.',
    risks: 'The window lapsed without a fill; capital was never committed.' },
];

function genCandles(sig, n = 64) {
  let s = 0;
  for (const c of sig.sym) s = (s * 131 + c.charCodeAt(0)) % 2147483647;
  const rand = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return (s % 100000) / 100000; };
  const lo = Math.min(sig.stop, sig.ltp) * 0.985, hi = Math.max(sig.target, sig.ltp) * 1.012;
  const amp = (hi - lo);
  const out = [];
  let price = sig.entry * 0.965;
  const start = new Date(2026, 2, 2);
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const anchor = sig.entry + (sig.ltp - sig.entry) * Math.pow(t, 1.7);
    const pull = (anchor - price) * 0.25;
    const noise = (rand() - 0.5) * amp * 0.10;
    const open = price;
    let close = price + pull + noise;
    close = Math.max(lo, Math.min(hi, close));
    const wick = amp * 0.05 * rand();
    const high = Math.min(hi, Math.max(open, close) + wick);
    const low  = Math.max(lo, Math.min(open, close) - wick);
    const d = new Date(start); d.setDate(d.getDate() + i);
    out.push({ time: d.toISOString().slice(0, 10), open: +open.toFixed(2), high: +high.toFixed(2), low: +low.toFixed(2), close: +close.toFixed(2) });
    price = close;
  }
  out[out.length - 1].close = sig.ltp;
  out[out.length - 1].high = Math.max(out[out.length - 1].high, sig.ltp);
  out[out.length - 1].low  = Math.min(out[out.length - 1].low, sig.ltp);
  return out;
}

const SIGNALS = RAW_SIGNALS.map((sig) => {
  const rr = (sig.target - sig.entry) / (sig.entry - sig.stop);
  const fromEntry = ((sig.ltp - sig.entry) / sig.entry) * 100;
  const upside = ((sig.target - sig.entry) / sig.entry) * 100;
  const risk = ((sig.stop - sig.entry) / sig.entry) * 100;
  const suggQty = sig.entry === sig.stop ? (sig.qty || 10) : Math.max(1, Math.floor(RISK_BUDGET / (sig.entry - sig.stop)));
  return { ...sig, rr, fromEntry, upside, risk, suggQty, zeroRisk: sig.entry === sig.stop, conv: convOf(sig.grade, sig.watch), candles: genCandles(sig) };
});

// plan directive — "what do I do, by when"
function planOf(sig) {
  switch (sig.action) {
    case 'buy-today':
      return { kind: 'buy', title: `Buy between ${sig.buyWindow}`, sub: `After ${sig.buyBy} we no longer recommend this entry.` };
    case 'closing':
      return { kind: 'buy', title: `Buy by ${sig.buyBy} — window closing`, sub: `${sig.daysLeft} day left. After that the setup is stale and drops off the list.` };
    case 'sell-now':
      return sig.sellReason === 'target'
        ? { kind: 'sell', title: 'Sell on the next open', sub: `Target reached at ${fmtINR(sig.target)}. The favourable edge is spent — lock the gain in.` }
        : { kind: 'sellbad', title: 'Sell on the next open', sub: `Price closed below the ${fmtINR(sig.stop)} stop. Exit to cap the loss at plan.` };
    case 'holding':
      return { kind: 'hold', title: `Hold — day ${sig.dayOf} of ${sig.hold}`, sub: `Stop at ${fmtNum(sig.stop)}. Let it work toward ${fmtNum(sig.target)}; no action today.` };
    case 'brewing':
      return { kind: 'watch', title: 'Watching for a trigger', sub: `Not a buy yet. We flag it again if price sets up near ${fmtNum(sig.entry)}.` };
    case 'closed':
      return { kind: 'closed',
        title: sig.status === 'hit-target' ? 'Closed — target hit' : sig.status === 'hit-stop' ? 'Closed — stopped out' : 'Expired — no fill', sub: '' };
  }
}

// ─────────────────────────────────────────────────────────────────────
// Chrome
// ─────────────────────────────────────────────────────────────────────
function RegimeHeader() {
  return (
    <div className="sig-regime">
      <span className="rg-dot" />
      <span className="rg-text">{REGIME}</span>
    </div>
  );
}

function Topbar() {
  return (
    <header className="topbar">
      <a className="brand" href="Landing.html" style={{ textDecoration: 'none' }}>
        <div className="brand-mark">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19V8l5 6 4-9 4 11 3-5v8"/></svg>
        </div>
        <div className="brand-text">Nifty Satvik</div>
      </a>
      <div className="search">
        <Icon.Search width="14" height="14" />
        <input placeholder="Search by ticker, sector, or signal grade…" />
        <kbd>⌘K</kbd>
      </div>
      <nav className="tabs">
        <a className="tab" href="Dashboard.html">Dashboard</a>
        <a className="tab active" href="Signals.html">Signals</a>
        <a className="tab" href="Signals.html">Portfolio</a>
        <a className="tab" href="Signals.html">Backtest</a>
        <a className="tab" href="Signals.html">Track record</a>
      </nav>
      <div className="top-actions">
        <button className="icon-btn"><Icon.Layers width="16" height="16" /></button>
        <button className="icon-btn"><Icon.Bell width="16" height="16" /><span className="bell-dot" /></button>
        <div className="user">
          <div className="hello"><div className="hello-l">Welcome back</div><div className="hello-n">Kreesh P.</div></div>
          <div className="avatar">KP</div>
          <Icon.ArrDown width="14" height="14" />
        </div>
      </div>
    </header>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Action chip — amber ONLY for buy deadlines; one chip per card.
// ─────────────────────────────────────────────────────────────────────
function ActionChip({ sig }) {
  switch (sig.action) {
    case 'buy-today':
    case 'closing':
      return (
        <span className={`act-chip act-buy ${sig.daysLeft <= 1 ? 'act-urgent' : ''}`}>
          <Icon.Clock width="11" height="11" />
          BUY BY {sig.buyBy.toUpperCase()} · {sig.daysLeft} DAY{sig.daysLeft > 1 ? 'S' : ''} LEFT
        </span>
      );
    case 'sell-now':
      return <span className={`act-chip ${sig.sellReason === 'target' ? 'act-sell-good' : 'act-sell-bad'}`}>SELL ON NEXT OPEN</span>;
    case 'holding':
      return <span className="act-chip act-hold">HOLDING · DAY {sig.dayOf} OF {sig.hold}</span>;
    case 'brewing':
      return <span className="act-chip act-watch">WATCHING</span>;
    case 'closed':
      return sig.status === 'expired'
        ? <span className="act-chip act-closed">WINDOW CLOSED</span>
        : <span className={`act-chip ${sig.status === 'hit-target' ? 'act-done-good' : 'act-done-bad'}`}>{sig.status === 'hit-target' ? 'CLOSED · WON' : 'CLOSED · LOSS'}</span>;
  }
}

function cardPlan(sig) {
  switch (sig.action) {
    case 'buy-today':
    case 'closing':
      return <>Buy ~<b>{sig.suggQty}</b> sh near <b>{fmtNum(sig.entry)}</b> · stop <b className="num-bear">{fmtNum(sig.stop)}</b> · target <b className="num-bull">{fmtNum(sig.target)}</b></>;
    case 'sell-now':
      return <>Sell <b>{sig.qty}</b> sh at market · in at <b>{fmtNum(sig.fillPrice)}</b> · {sig.sellReason === 'target' ? <>target <b className="num-bull">{fmtNum(sig.target)}</b></> : <>stop <b className="num-bear">{fmtNum(sig.stop)}</b></>}</>;
    case 'holding':
      return <>Holding <b>{sig.qty}</b> sh · stop <b>{fmtNum(sig.stop)}</b> · target <b className="num-bull">{fmtNum(sig.target)}</b></>;
    case 'brewing':
      return <>Watch for a setup near <b>{fmtNum(sig.entry)}</b> · then stop <b className="num-bear">{fmtNum(sig.stop)}</b></>;
    case 'closed':
      if (sig.closedPnl != null) return <>Closed {sig.qty} sh @ <b>{fmtNum(sig.fillPrice)}</b> · realised <b className={sig.closedPnl >= 0 ? 'num-bull' : 'num-bear'}>{fmtLakh(sig.closedPnl)}</b></>;
      return <>No fill — entry never triggered inside the {sig.hold}-day window</>;
  }
}

function SignalCard({ sig, selected, onOpen }) {
  const st = STATUS[sig.status];
  const showFromEntry = sig.action !== 'closed';
  const rd = rrDisplay(sig);
  return (
    <button className={`act-card act-${sig.action} ${selected ? 'is-selected' : ''}`} onClick={onOpen}>
      <div className="ac-head">
        <Logo sym={sig.sym} size={36} radius={9} />
        <div className="ac-id">
          <div className="ac-top">
            <span className="ac-sym">{sig.sym}</span>
            <span className={`conv-pill ${sig.conv.cls}`}>{sig.conv.word} · {sig.grade}</span>
          </div>
          <div className="ac-name">{sig.name} · {sig.sector}</div>
        </div>
      </div>
      <div className="ac-action"><ActionChip sig={sig} /></div>
      <div className="ac-body">
        <div className="ac-plan">{cardPlan(sig)}</div>
        <div className="ac-figures">
          <div className="ac-ltp">
            <span className="ac-ltp-v">{fmtINR(sig.ltp)}</span>
            {showFromEntry && <span className="ac-ltp-l">now {fmtPct1(sig.fromEntry)} from entry</span>}
          </div>
          <div className="ac-figures-r">
            <span className={`ac-rr-v ${rd.tone}`}>{rd.free ? 'Risk-free' : <>R:R {rd.val} <span className="ac-rr-l">{rd.word}</span></>}</span>
            <span className={`chip ${st.cls}`}>{st.live && <span className="dot" />}{st.label}</span>
          </div>
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────
// TradingView chart
// ─────────────────────────────────────────────────────────────────────
function CandleChart({ sig }) {
  const wrapRef = React.useRef(null);
  const chartRef = React.useRef(null);
  const seriesRef = React.useRef(null);
  React.useEffect(() => {
    if (!window.LightweightCharts || !wrapRef.current) return;
    const el = wrapRef.current;
    const chart = window.LightweightCharts.createChart(el, {
      width: el.clientWidth, height: el.clientHeight,
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#7A82A5', fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11 },
      grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.12 } },
      timeScale: { borderVisible: false, timeVisible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: { mode: 1, vertLine: { color: 'rgba(255,255,255,0.18)', width: 1, style: 3, labelBackgroundColor: '#1a2150' }, horzLine: { color: 'rgba(255,255,255,0.18)', width: 1, style: 3, labelBackgroundColor: '#1a2150' } },
      handleScroll: false, handleScale: false,
    });
    const series = chart.addCandlestickSeries({ upColor: '#3FDD8A', downColor: '#FF5C7A', borderUpColor: '#3FDD8A', borderDownColor: '#FF5C7A', wickUpColor: 'rgba(63,221,138,0.6)', wickDownColor: 'rgba(255,92,122,0.6)' });
    chartRef.current = chart; seriesRef.current = series;
    const ro = new ResizeObserver(() => { if (chartRef.current && el.clientWidth) chartRef.current.resize(el.clientWidth, el.clientHeight); });
    ro.observe(el);
    return () => { ro.disconnect(); chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []);
  React.useEffect(() => {
    const series = seriesRef.current, chart = chartRef.current;
    if (!series || !chart) return;
    series.setData(sig.candles);
    (series.__lines || []).forEach((l) => series.removePriceLine(l));
    const mk = (price, color, title) => series.createPriceLine({ price, color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title });
    series.__lines = [ mk(sig.target, '#3FDD8A', 'TGT'), mk(sig.entry, '#4F8CFF', 'ENT'), mk(sig.stop, '#FF5C7A', 'STP') ];
    if (sig.fillPrice) series.__lines.push(mk(sig.fillPrice, 'rgba(241,245,255,0.45)', 'FILL'));
    chart.timeScale().fitContent();
  }, [sig]);
  return <div className="tv-chart" ref={wrapRef} />;
}

// ─────────────────────────────────────────────────────────────────────
// OrderPad
// ─────────────────────────────────────────────────────────────────────
function OrderPad({ sig }) {
  const perShareRisk = Math.max(1, sig.entry - sig.stop);
  const [qty, setQty] = React.useState(sig.suggQty);
  const [type, setType] = React.useState('Limit');
  const [placed, setPlaced] = React.useState(false);
  React.useEffect(() => { setQty(sig.suggQty); setPlaced(false); }, [sig.sym]);

  const orderValue = qty * sig.entry;
  const riskAmt = sig.zeroRisk ? 0 : qty * perShareRisk;
  const rewardAmt = qty * (sig.target - sig.entry);
  const pctPortfolio = (riskAmt / PORTFOLIO_CAPITAL) * 100;
  const isSell = sig.action === 'sell-now';
  const isWatch = sig.action === 'brewing';
  const isHold = sig.action === 'holding';
  const closed = sig.action === 'closed';

  if (closed) {
    const win = sig.status === 'hit-target';
    return (
      <div className="orderpad orderpad-closed">
        <div className="op-closed-head">
          <span className={`chip ${STATUS[sig.status].cls}`}>{STATUS[sig.status].label}</span>
          <span className="op-closed-when">Closed · {sig.scanned}</span>
        </div>
        {sig.closedPnl != null ? (
          <div className="op-pnl">
            <div className="op-pnl-l">Realised P&amp;L</div>
            <div className={`op-pnl-v ${win ? 'num-bull' : 'num-bear'}`}>{win ? '+' : ''}{fmtLakh(sig.closedPnl)}<span className="op-pnl-pct">{fmtPct(sig.closedPct)}</span></div>
            <div className="op-pnl-meta">{sig.qty} sh @ {fmtNum(sig.fillPrice)} · exit {fmtNum(sig.ltp)}</div>
          </div>
        ) : (
          <div className="op-expired"><Icon.Info width="18" height="18" /><div>No fill — the trigger was never reclaimed inside the {sig.hold}-day window. Capital was never at risk.</div></div>
        )}
        <button className="op-cta op-cta-ghost">View in journal <Icon.Arrow width="13" height="13" /></button>
      </div>
    );
  }

  return (
    <div className="orderpad">
      <div className="op-head">
        <div className="op-title">{isSell ? 'Exit order' : 'Order pad'}</div>
        <div className="op-route"><span className="kite-mark"><Icon.Bolt width="11" height="11" /></span> Zerodha Kite · CNC</div>
      </div>
      <div className="op-controls">
        <label className="op-field">
          <span className="op-field-l">{isSell ? 'Quantity to sell' : 'Suggested quantity'}</span>
          <div className="op-qty">
            <button onClick={() => setQty((q) => Math.max(1, q - 1))}>−</button>
            <input type="text" value={qty} onChange={(e) => { const v = parseInt(e.target.value.replace(/\D/g, ''), 10); setQty(isNaN(v) ? 0 : v); }} />
            <button onClick={() => setQty((q) => q + 1)}>+</button>
          </div>
        </label>
        <label className="op-field">
          <span className="op-field-l">Order type</span>
          <div className="op-seg">{['Market', 'Limit'].map((o) => (<button key={o} className={type === o ? 'on' : ''} onClick={() => setType(o)}>{o}</button>))}</div>
        </label>
        <label className="op-field">
          <span className="op-field-l">{type === 'Limit' ? 'Limit price' : 'Est. price'}</span>
          <div className="op-price">{fmtNum(isSell ? sig.ltp : sig.entry)}</div>
        </label>
      </div>
      <div className="op-calc">
        <div className="op-calc-row"><span>Order value</span><span className="t-num">{fmtLakh(orderValue)}</span></div>
        <div className="op-calc-row"><span>Margin required (CNC)</span><span className="t-num">{fmtLakh(orderValue)}</span></div>
        <div className="op-calc-row"><span>Potential reward at target</span><span className="t-num num-bull">+{fmtLakh(rewardAmt)}</span></div>
        <div className="op-calc-row"><span>Risk if stopped</span><span className="t-num num-bear">{sig.zeroRisk ? '₹0 · breakeven' : '−' + fmtLakh(riskAmt)}</span></div>
      </div>
      <button className={`op-cta ${placed ? 'is-placed' : ''}`} onClick={() => setPlaced(true)} disabled={isWatch}>
        {placed ? <><Icon.Check width="15" height="15" /> Order placed · {sig.sym} × {qty}</>
          : isSell ? <>Place sell order · Kite <Icon.Arrow width="14" height="14" /></>
          : isWatch ? <>Set a trigger alert</>
          : isHold ? <>Add to position · Kite <Icon.Arrow width="14" height="14" /></>
          : <>Place buy order · Kite <Icon.Arrow width="14" height="14" /></>}
      </button>
      <div className="op-foot">
        {placed ? <>Routed to Kite at {fmtNum(isSell ? sig.ltp : sig.entry)} · logged to journal</>
          : sig.zeroRisk ? <>Stop at breakeven — this position carries no risk</>
          : <>Sized to risk ≈ {fmtLakh(riskAmt)} · ~{pctPortfolio.toFixed(1)}% of your portfolio risked</>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Detail body (shared by desktop pane + mobile full-screen)
// ─────────────────────────────────────────────────────────────────────
function DetailBody({ sig }) {
  const st = STATUS[sig.status];
  const plan = planOf(sig);
  const rd = rrDisplay(sig);
  return (
    <div className="detail-body">
      <div className="db-head">
        <Logo sym={sig.sym} size={46} radius={12} />
        <div className="db-head-id">
          <div className="db-head-top">
            <h2 className="db-sym">{sig.sym}</h2>
            <span className={`grade-badge grade-${sig.grade[0].toLowerCase()}`}>{sig.grade}</span>
            <span className={`chip ${st.cls}`}>{st.live && <span className="dot" />}{st.label}</span>
          </div>
          <div className="db-sub">{sig.name} · {sig.sector} · {sig.ex}</div>
        </div>
        <div className="db-price">
          <div className="db-ltp">{fmtINR(sig.ltp)}</div>
          {sig.action !== 'closed' && <div className={`db-vs ${sig.fromEntry >= 0 ? 'num-bull' : 'num-bear'}`}>now {fmtPct1(sig.fromEntry)} from entry</div>}
        </div>
      </div>

      {/* the answer: action + deadline */}
      <div className={`plan-bar plan-${plan.kind}`}>
        <div className="plan-bar-l">
          <ActionChip sig={sig} />
          <div className="plan-text">
            <div className="plan-title">{plan.title}</div>
            {plan.sub && <div className="plan-sub">{plan.sub}</div>}
          </div>
        </div>
        {(sig.action === 'buy-today' || sig.action === 'closing') && (
          <div className={`plan-deadline ${sig.daysLeft <= 1 ? 'is-urgent' : ''}`}>
            <div className="plan-deadline-n">{sig.daysLeft}</div>
            <div className="plan-deadline-l">day{sig.daysLeft > 1 ? 's' : ''} left</div>
          </div>
        )}
      </div>

      {/* worded conviction — no raw ml score / pillar dots */}
      <div className="conv-line">
        <span className={`conv-pill ${sig.conv.cls}`}>{sig.conv.word}</span>
        <span className="conv-sep">·</span>
        <span>Grade {sig.grade}</span>
        <span className="conv-sep">·</span>
        <span>{sig.layers} of 6 model layers agree</span>
        <span className="conv-sep">·</span>
        <span>Hold ~{sig.hold} days</span>
      </div>

      {/* chart */}
      <div className="db-chart-card">
        <div className="db-chart-legend">
          <span className="leg-i"><span className="sw" style={{ background: '#FF5C7A' }} />STOP <b>{fmtNum(sig.stop)}</b></span>
          <span className="leg-i"><span className="sw" style={{ background: '#4F8CFF' }} />ENTRY <b>{fmtNum(sig.entry)}</b></span>
          <span className="leg-i"><span className="sw" style={{ background: '#3FDD8A' }} />TARGET <b>{fmtNum(sig.target)}</b></span>
          <span className="leg-tv">TradingView</span>
        </div>
        <CandleChart sig={sig} />
      </div>

      {/* 4-metric strip — stop red, target green */}
      <div className="metric-strip">
        <div className="metric"><span className="metric-l">Entry</span><span className="metric-v brand">{fmtNum(sig.entry)}</span><span className="metric-s">trigger</span></div>
        <div className="metric"><span className="metric-l">Stop</span><span className={`metric-v ${sig.zeroRisk ? '' : 'num-bear'}`}>{fmtNum(sig.stop)}</span><span className={`metric-s ${sig.zeroRisk ? '' : 'num-bear'}`}>{sig.zeroRisk ? 'breakeven' : fmtPct(sig.risk)}</span></div>
        <div className="metric"><span className="metric-l">Target</span><span className="metric-v num-bull">{fmtNum(sig.target)}</span><span className="metric-s num-bull">{fmtPct(sig.upside)}</span></div>
        <div className="metric"><span className="metric-l">Risk / reward</span><span className={`metric-v ${rd.tone}`}>{rd.val}</span><span className="metric-s">{rd.word}</span></div>
      </div>

      {/* why + risks, equal billing */}
      <div className="rationale">
        <div className="rat rat-why">
          <div className="rat-h"><Icon.Check width="13" height="13" /> Why this stock</div>
          <p>{sig.why}</p>
        </div>
        <div className="rat rat-risk">
          <div className="rat-h">
            <span><Icon.Alert width="13" height="13" /> The risks</span>
            {sig.highRisk && <span className="risk-chip">ELEVATED RISK</span>}
          </div>
          <p>{sig.risks}</p>
        </div>
      </div>

      {sig.action === 'holding' && (
        <div className="db-position">
          <span className="db-pos-l">Open position</span>
          <span className="db-pos-v">{sig.qty} sh @ {fmtNum(sig.fillPrice)}</span>
          <span className="db-pos-pnl num-bull">+{fmtLakh(sig.qty * (sig.ltp - sig.fillPrice))} ({fmtPct1(sig.fromEntry)})</span>
        </div>
      )}

      <OrderPad sig={sig} />

      <div className="db-disclaimer">{DISCLAIMER}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Section (collapsible)
// ─────────────────────────────────────────────────────────────────────
function Section({ sec, rows, selSym, onOpen, collapsedByDefault, limit }) {
  const [open, setOpen] = React.useState(!collapsedByDefault);
  const [showAll, setShowAll] = React.useState(false);
  if (!rows.length) return null;
  const shown = limit && !showAll ? rows.slice(0, limit) : rows;
  return (
    <section className={`sig-section sec-${sec.id}`}>
      <button className="sec-head" onClick={() => setOpen((o) => !o)}>
        <div className="sec-head-l">
          <span className={`sec-marker marker-${sec.id}`} />
          <h2 className="sec-title">{sec.title}</h2>
          <span className="sec-count">{rows.length}</span>
        </div>
        <div className="sec-head-r">
          <span className="sec-desc">{sec.sub}</span>
          <Icon.ArrDown width="14" height="14" className={`sec-caret ${open ? 'is-open' : ''}`} />
        </div>
      </button>
      {open && (
        <div className="sec-cards">
          {shown.map((sig) => <SignalCard key={sig.sym} sig={sig} selected={sig.sym === selSym} onOpen={() => onOpen(sig.sym)} />)}
          {limit && rows.length > limit && (
            <button className="sec-more" onClick={() => setShowAll((s) => !s)}>
              {showAll ? 'Show less' : `Show ${rows.length - limit} more`} <Icon.ArrDown width="13" height="13" />
            </button>
          )}
        </div>
      )}
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────────────
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "brandColor":  "#4F8CFF",
  "listDensity": "regular"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [grade, setGrade] = React.useState('all');
  const [isMobile, setIsMobile] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  React.useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--brand', t.brandColor);
    root.style.setProperty('--brand-hi', t.brandColor);
    root.style.setProperty('--brand-soft', hexToRgba(t.brandColor, 0.14));
    root.style.setProperty('--brand-edge', hexToRgba(t.brandColor, 0.40));
  }, [t.brandColor]);

  React.useEffect(() => {
    const mq = window.matchMedia('(max-width: 900px)');
    const on = () => setIsMobile(mq.matches);
    on(); mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);

  const pool = SIGNALS.filter((s) => grade === 'all' || s.grade[0] === grade);
  const bySection = (id) => pool.filter((s) => s.action === id);

  // default desktop selection = first actionable signal
  const firstActionable = pool.find((s) => s.action !== 'closed') || pool[0];
  const [selSym, setSelSym] = React.useState(firstActionable ? firstActionable.sym : null);
  React.useEffect(() => {
    if (pool.length && !pool.some((s) => s.sym === selSym)) setSelSym((pool.find((s) => s.action !== 'closed') || pool[0]).sym);
  }, [grade]);

  const open = (sym) => { setSelSym(sym); if (isMobile) setMobileOpen(true); };
  const selected = SIGNALS.find((s) => s.sym === selSym) || null;

  const freshCount = SIGNALS.filter((s) => ['buy-today', 'closing'].includes(s.action)).length;
  const activeCount = SIGNALS.filter((s) => ['holding', 'sell-now'].includes(s.action)).length;

  React.useEffect(() => {
    if (!isMobile || !mobileOpen) return;
    const onKey = (e) => { if (e.key === 'Escape') setMobileOpen(false); };
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [isMobile, mobileOpen]);

  return (
    <div className={`app sig-app density-${t.listDensity}`}>
      <Topbar />
      <RegimeHeader />

      <div className="sig-subhead">
        <div>
          <div className="t-ui-micro">SIGNALS · 16:15 IST SCAN · TUE 2 JUN</div>
          <h1 className="sig-page-title">What to do today</h1>
          <div className="sig-state">
            <span><b className="num-info">{freshCount}</b> to buy today</span>
            <span className="sep">·</span>
            <span><b className="num-bull">{activeCount}</b> positions to manage</span>
          </div>
        </div>
        <div className="grade-filter">
          <span className="gf-l">Grade</span>
          {['all', 'A', 'B'].map((g) => (<button key={g} className={`gf-btn ${grade === g ? 'on' : ''}`} onClick={() => setGrade(g)}>{g === 'all' ? 'All' : g}</button>))}
        </div>
      </div>

      <main className="sig-body">
        <div className="sig-list">
          {SECTION_ORDER.map((sec) => (
            <Section key={sec.id} sec={sec} rows={bySection(sec.id)} selSym={selSym} onOpen={open}
              collapsedByDefault={sec.id === 'closed'}
              limit={sec.id === 'brewing' ? 5 : undefined} />
          ))}
          {pool.length === 0 && (
            <div className="sig-empty"><Icon.Info width="20" height="20" /><div>No {grade}-grade signals right now. Try a different grade or wait for the 16:15 IST scan.</div></div>
          )}
        </div>

        {!isMobile && (
          <div className="detail-pane">
            {selected ? <DetailBody sig={selected} /> : <div className="detail-empty">Select a signal to see the plan, chart, and order pad.</div>}
          </div>
        )}
      </main>

      <footer className="sig-foot">
        <div className="sig-disclaimer">{DISCLAIMER}</div>
        <div className="sig-foot-meta">SEBI Research Analyst · INH000012345 · Members see live tickers · this preview is anonymized · NSE data delayed 15 min for non-members · v2026.05</div>
      </footer>

      {/* mobile: full-screen pushed detail (not a drawer) */}
      {isMobile && mobileOpen && selected && (
        <div className="mobile-detail">
          <div className="md-bar">
            <button className="md-back" onClick={() => setMobileOpen(false)}><Icon.Back width="18" height="18" /> Signals</button>
            <span className="md-bar-sym">{selected.sym}</span>
          </div>
          <div className="md-scroll"><DetailBody sig={selected} /></div>
        </div>
      )}

      <TweaksPanel>
        <TweakSection label="Brand color" />
        <TweakColor label="Primary" value={t.brandColor} options={['#4F8CFF', '#7B5BFF', '#3FDD8A', '#FFB454']} onChange={(v) => setTweak('brandColor', v)} />
        <TweakSection label="List density" />
        <TweakRadio label="Rows" value={t.listDensity} options={['compact', 'regular', 'comfy']} onChange={(v) => setTweak('listDensity', v)} />
      </TweaksPanel>
    </div>
  );
}

function hexToRgba(hex, a) {
  const m = hex.replace('#', '');
  return `rgba(${parseInt(m.substring(0, 2), 16)},${parseInt(m.substring(2, 4), 16)},${parseInt(m.substring(4, 6), 16)},${a})`;
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
