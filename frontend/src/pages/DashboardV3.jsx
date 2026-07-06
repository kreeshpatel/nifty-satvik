/**
 * DashboardV3 — Production dashboard page.
 *
 * Converted from frontend/public/nifty-design/dashboard.jsx (Babel-in-browser artifact).
 * Pattern follows SignalsV3: ES imports, real hooks, graceful fallbacks, compliance strings.
 *
 * Sections:
 *   RegimeStrip  — useSignals().regime + useIndexSparklines()["NIFTY 50"]
 *   TrendingCards (3) — top 3 signals from useSignals()
 *   BacktestCTA  — static, link to /backtest
 *   KiteStrip    — hidden if kite.connected, else shows connect prompt
 *   StocksTable  — useKiteHoldings() with deterministic 12-day perf fallback
 *   SectorBreadth — derived from useSignals().signals grouped by sector
 *   BalanceCard  — useKiteMargins() + useOverview().portfolio
 *
 * Compliance: no "guarantee", "will", "sure", "sure-shot" in client-facing strings.
 * DISCLAIMER footer sourced from @/lib/signalCopy.
 */

import React, { useContext, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { KiteContext } from '@/App';
import { useSignals } from '@/hooks/queries/useSignals';
import { useWatchlist } from '@/hooks/queries/useWatchlist';
import { useOverview } from '@/hooks/queries/useOverview';
import { useKiteHoldings, useKiteMargins } from '@/hooks/queries/useKiteState';
import { useIndexSparklines } from '@/hooks/queries/useIndexSparklines';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/dashboard-v3.css';

// ─────────────────────────────────────────────────────────────────────
// Formatters
// ─────────────────────────────────────────────────────────────────────
const fmtINR = (n) =>
  n == null ? '—' : '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (n, plus = true) =>
  n == null ? '—' : (n >= 0 && plus ? '+' : '') + Number(n).toFixed(2) + '%';
const fmtLakh = (n) => {
  if (n == null) return '—';
  const sign = n < 0 ? '−' : '';
  const a = Math.abs(n);
  if (a >= 1e7) return sign + '₹' + (a / 1e7).toFixed(2) + 'Cr';
  if (a >= 1e5) return sign + '₹' + (a / 1e5).toFixed(2) + 'L';
  return sign + '₹' + Math.round(a).toLocaleString('en-IN');
};

// ─────────────────────────────────────────────────────────────────────
// Ticker domain map for brand logos
// ─────────────────────────────────────────────────────────────────────
const TICKER_DOMAINS = {
  RELIANCE: 'ril.com', TCS: 'tcs.com', BAJFINANCE: 'bajajfinserv.in',
  INFY: 'infosys.com', HDFCBANK: 'hdfcbank.com', ICICIBANK: 'icicibank.com',
  BHARTIARTL: 'airtel.in', LT: 'larsentoubro.com', MARUTI: 'marutisuzuki.com',
  KOTAKBANK: 'kotak.com', ADANIENT: 'adanienterprises.com', SBIN: 'sbi.co.in',
  AXISBANK: 'axisbank.com', TATAPOWER: 'tatapower.com', POLYCAB: 'polycab.com',
  VOLTAS: 'voltas.com', CUMMINSIND: 'cummins.com', TITAN: 'titancompany.com',
  SUNPHARMA: 'sunpharma.com', DIVISLAB: 'divislabs.com', PERSISTENT: 'persistent.com',
  WIPRO: 'wipro.com', HINDUNILVR: 'hul.co.in', NESTLEIND: 'nestle.in',
  // Energy / PSU / commodities
  ONGC: 'ongcindia.com', NTPC: 'ntpc.co.in', POWERGRID: 'powergrid.in',
  COALINDIA: 'coalindia.in', IOC: 'iocl.com', BPCL: 'bharatpetroleum.in',
  GAIL: 'gailonline.com', ADANIGREEN: 'adanigreenenergy.com', TATASTEEL: 'tatasteel.com',
  JSWSTEEL: 'jsw.in', HINDALCO: 'hindalco.com', VEDL: 'vedantalimited.com',
  // Financials
  SBICARD: 'sbicard.com', BAJAJFINSV: 'bajajfinserv.in', HDFCLIFE: 'hdfclife.com',
  SBILIFE: 'sbilife.co.in', ICICIPRULI: 'iciciprulife.com', INDUSINDBK: 'indusind.com',
  PNB: 'pnbindia.in', BANKBARODA: 'bankofbaroda.in', CHOLAFIN: 'cholamandalam.com',
  // IT / Media
  HCLTECH: 'hcltech.com', TECHM: 'techmahindra.com', LTIM: 'ltimindtree.com',
  COFORGE: 'coforge.com', MPHASIS: 'mphasis.com', NETWORK18: 'network18online.com',
  ZEEL: 'zee.com', PVRINOX: 'pvrinox.com',
  // Auto
  TATAMOTORS: 'tatamotors.com', MM: 'mahindra.com', BAJAJ_AUTO: 'bajajauto.com',
  EICHERMOT: 'eichermotors.com', HEROMOTOCO: 'heromotocorp.com', TVSMOTOR: 'tvsmotor.com',
  ASHOKLEY: 'ashokleyland.com', BOSCHLTD: 'bosch.in',
  // Pharma / Healthcare
  DRREDDY: 'drreddys.com', CIPLA: 'cipla.com', APOLLOHOSP: 'apollohospitals.com',
  AUROPHARMA: 'aurobindo.com', LUPIN: 'lupin.com', BIOCON: 'biocon.com',
  // FMCG / Consumer
  ITC: 'itcportal.com', BRITANNIA: 'britannia.co.in', DABUR: 'dabur.com',
  GODREJCP: 'godrejcp.com', TATACONSUM: 'tataconsumer.com', ASIANPAINT: 'asianpaints.com',
  PIDILITIND: 'pidilite.com', DMART: 'dmartindia.com', TRENT: 'trentlimited.com',
  // Industrials / Infra / Cement
  ULTRACEMCO: 'ultratechcement.com', GRASIM: 'grasim.com', SHREECEM: 'shreecement.com',
  AMBUJACEM: 'ambujacement.com', ACC: 'acclimited.com', SIEMENS: 'siemens.co.in',
  ABB: 'abb.com', HAVELLS: 'havells.com', BEL: 'bel-india.in', BHEL: 'bhel.com',
};

function tickerBg(sym) {
  let h = 0;
  for (const ch of (sym || '')) h = (h + ch.charCodeAt(0) * 13) % 360;
  return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`;
}

// Company logo with graceful fallback: brand logo → favicon → monogram
function Logo({ sym, size = 32, radius = 9 }) {
  const domain = TICKER_DOMAINS[(sym || '').toUpperCase()];
  const sources = domain
    ? [`https://icons.duckduckgo.com/ip3/${domain}.ico`,
       `https://www.google.com/s2/favicons?domain=${domain}&sz=128`]
    : [];
  const [idx, setIdx] = React.useState(0);
  React.useEffect(() => { setIdx(0); }, [sym]);

  if (idx >= sources.length) {
    return (
      <div
        className="dv3-logo-tile logo-mono"
        style={{ width: size, height: size, borderRadius: radius, background: tickerBg(sym) }}
      >
        {(sym || '??').slice(0, 2)}
      </div>
    );
  }
  return (
    <div className="dv3-logo-tile" style={{ width: size, height: size, borderRadius: radius }}>
      <img src={sources[idx]} alt={sym} onError={() => setIdx((i) => i + 1)} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Sparkline (inline SVG) — used in TrendingCards
// dir: 'up' | 'down'
// ─────────────────────────────────────────────────────────────────────
function Spark({ data, dir, width = 280, height = 48 }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stroke = dir === 'up' ? 'var(--bull)' : 'var(--bear)';
  const fill   = dir === 'up' ? 'rgba(63,221,138,0.20)' : 'rgba(255,92,122,0.20)';
  const padX = 8, padY = 10;
  const xs = data.map((_, i) => padX + (i * (width - 2 * padX)) / (data.length - 1));
  const ys = data.map((v) => padY + (height - 2 * padY) * (1 - (v - min) / range));
  const last = { x: xs[xs.length - 1], y: ys[ys.length - 1] };
  const peakIdx = data.indexOf(dir === 'up' ? max : min);
  const path = xs.map((x, i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(' ');
  const areaPath = `${path} L ${xs[xs.length - 1]} ${height - padY} L ${xs[0]} ${height - padY} Z`;

  return (
    <svg width={width} height={height} className="dv3-spark" aria-hidden="true">
      <path d={areaPath} fill={fill} />
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ filter: dir === 'up' ? 'drop-shadow(0 2px 6px rgba(63,221,138,0.5))' : 'drop-shadow(0 2px 6px rgba(255,92,122,0.5))' }}
      />
      <circle cx={xs[peakIdx]} cy={ys[peakIdx]} r="2.6" fill={stroke} opacity="0.7" />
      <circle cx={last.x} cy={last.y} r="3" fill={stroke} />
      <circle cx={last.x} cy={last.y} r="6.5" fill={stroke} opacity="0.18" />
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Deterministic sparkline generator seeded from ticker
// TODO: replace with real per-stock sparkline when endpoint available
// ─────────────────────────────────────────────────────────────────────
function genSpark(sym, n = 15) {
  let s = 0;
  for (const c of (sym || 'XX')) s = (s * 131 + c.charCodeAt(0)) % 2147483647;
  const rand = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return (s % 100000) / 100000; };
  const pts = [];
  let v = 50 + rand() * 20;
  for (let i = 0; i < n; i++) {
    v = Math.max(10, Math.min(90, v + (rand() - 0.46) * 10));
    pts.push(v);
  }
  return pts;
}

// ─────────────────────────────────────────────────────────────────────
// Icons (inline SVG, Lucide-style)
// ─────────────────────────────────────────────────────────────────────
const Icon = {
  Arrow: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 17 17 7"/><path d="M7 7h10v10"/>
    </svg>
  ),
  ArrDown: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m6 9 6 6 6-6"/>
    </svg>
  ),
  Bolt: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>
    </svg>
  ),
  Chart: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4v16h16"/><path d="M4 16l5-5 4 4 7-7"/>
    </svg>
  ),
  Wallet: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><path d="M16 3h-4a2 2 0 0 0-2 2v2h8V5a2 2 0 0 0-2-2z"/><path d="M18 14h.01"/>
    </svg>
  ),
};

// ─────────────────────────────────────────────────────────────────────
// RegimeStrip — driven from useSignals().regime + useIndexSparklines()
// ─────────────────────────────────────────────────────────────────────
function RegimeStrip({ regime, indexData }) {
  const status = (regime?.status || '').toLowerCase();
  const isBull = status.includes('bull');
  const isBear = status.includes('bear');
  const isChop = !isBull && !isBear;

  const regimeLabel = isBull ? 'Bullish' : isBear ? 'Bearish' : 'Choppy';
  const regimeCls   = isBull ? 'num-bull' : isBear ? 'num-bear' : 'num-warn';
  const strength    = regime?.strength ?? 50;

  // NIFTY 50 data from index sparklines
  const nifty    = indexData?.['NIFTY 50'] ?? indexData?.['NIFTY'] ?? null;
  const niftyLtp = nifty?.ltp ?? nifty?.last ?? null;
  const niftyChg = nifty?.change_pct ?? nifty?.changePct ?? null;

  // VIX from index sparklines
  const vixData = indexData?.['INDIA VIX'] ?? indexData?.['INDIAVIX'] ?? null;
  const vix     = regime?.vix ?? vixData?.ltp ?? vixData?.last ?? null;
  const breadth = regime?.breadth;

  return (
    <div className="dv3-regime-strip">
      <div className="dv3-regime-left">
        <span className="dv3-live-dot" />
        <span className="dv3-regime-eyebrow">MARKET REGIME</span>
        <div className="dv3-regime-statement">
          The market is <em className={regimeCls}>{regimeLabel}</em>
          {niftyLtp != null && (
            <>
              <span className="sep">·</span>
              <span className="t-num-small">NIFTY {Number(niftyLtp).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              {niftyChg != null && (
                <span className={`t-num-small ${niftyChg >= 0 ? 'num-bull' : 'num-bear'}`}>
                  {fmtPct(niftyChg)}
                </span>
              )}
            </>
          )}
          {vix != null && (
            <>
              <span className="sep">·</span>
              <span>VIX {Number(vix).toFixed(1)}</span>
            </>
          )}
          {breadth != null && (
            <>
              <span className="sep">·</span>
              <span>Breadth {Number(breadth).toFixed(0)}</span>
            </>
          )}
        </div>
      </div>
      <div className="dv3-regime-right">
        <span className="dv3-strength-label">10-DAY STRENGTH</span>
        <div className="dv3-strength-bar">
          <span style={{ width: `${Math.max(0, Math.min(100, strength))}%` }} />
        </div>
        <span className={`t-num-small ${isBull ? 'num-bull' : isBear ? 'num-bear' : 'num-warn'}`}>
          {Math.round(strength)}
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// TrendingCard — maps a signal to the card layout
// ─────────────────────────────────────────────────────────────────────
function TrendingCard({ sig, modelWinRate, brewing = false }) {
  const sym    = sig.ticker || sig.sym || sig.symbol || '??';
  const name   = sig.name || sym;
  const sector = sig.sector || '—';
  const grade  = sig.grade || 'B';
  const entry  = sig.entry ?? 0;
  const stop   = sig.stop_loss ?? sig.stop ?? entry;
  const target = sig.target ?? entry;
  const dir    = target > entry ? 'up' : 'down';

  // Edge from predicted return, or hide if absent
  const edge = sig.predicted_return_pct != null
    ? fmtPct(sig.predicted_return_pct)
    : null;

  // Win rate: portfolio-level model win rate as proxy (no per-signal WR).
  // Treat 0 / missing as unavailable — a "0.0%" win rate (e.g. no trade
  // history yet) is misleading, so the card falls back to expected return.
  const wrNum = Number(modelWinRate);
  const wr = (modelWinRate != null && Number.isFinite(wrNum) && wrNum > 0)
    ? wrNum.toFixed(1)
    : null;

  // Decorative trend line — seeded from ticker, not real OHLCV.
  // TODO: replace with real per-stock sparkline when a price-history endpoint exists.
  const sparkData = genSpark(sym);

  // Reward-to-risk from the REAL plan levels (not the decorative spark).
  const rr = (entry > stop && target > entry)
    ? (target - entry) / (entry - stop)
    : null;
  const rMult = rr != null ? rr.toFixed(2) : null;

  return (
    <div className={`dv3-trending-card ${dir === 'up' ? 'is-up' : 'is-down'}`}>
      <div className="dv3-tc-head">
        <Logo sym={sym} size={30} radius={8} />
        <div className="dv3-tc-id">
          <div className="dv3-tc-sym">
            {sym}
            <span className="dv3-tc-grade">{grade}</span>
          </div>
          <div className="dv3-tc-name">{name} · {sector}</div>
        </div>
        <span className={`dv3-tc-fresh${brewing ? ' dv3-tc-brewing' : ''}`}>
          {brewing ? 'WATCHLIST' : 'SIGNAL'}
        </span>
      </div>

      <div className="dv3-tc-metrics">
        <div className="dv3-tc-metric">
          <span className="dv3-tc-metric-label">
            {wr != null ? 'Model win rate' : 'Expected return'}
          </span>
          <div className="dv3-tc-metric-row">
            {wr != null ? (
              <>
                <span className="dv3-tc-metric-val">{wr}<small>%</small></span>
                {edge && (
                  <div className={`dv3-stat-pill ${dir === 'up' ? 'bull' : 'bear'}`}>
                    <Icon.Arrow width="9" height="9" style={{ transform: dir === 'down' ? 'rotate(90deg)' : 'none' }} />
                    <span>{edge}</span>
                  </div>
                )}
              </>
            ) : (
              <span className={`dv3-tc-metric-val ${dir === 'up' ? 'num-bull' : 'num-bear'}`}>
                {edge ?? '—'}
              </span>
            )}
          </div>
        </div>
        <div className="dv3-tc-metric">
          <span className="dv3-tc-metric-label">Reward : risk</span>
          <div className="dv3-tc-metric-row">
            <span className={`dv3-tc-metric-val ${rMult != null && rr >= 2 ? 'num-bull' : ''}`}>
              {rMult != null ? <>{rMult}<small>R</small></> : '—'}
            </span>
          </div>
        </div>
      </div>

      <div className="dv3-tc-spark">
        <Spark data={sparkData} dir={dir} width={280} height={48} />
      </div>

      <div className="dv3-tc-foot">
        <div className="dv3-tc-level">
          <span className="micro">ENTRY</span>
          <span className="t-num-small">{fmtINR(entry)}</span>
        </div>
        <div className="dv3-tc-level">
          <span className="micro">STOP</span>
          <span className="t-num-small num-bear">{fmtINR(stop)}</span>
        </div>
        <div className="dv3-tc-level">
          <span className="micro">TARGET</span>
          <span className="t-num-small num-bull">{fmtINR(target)}</span>
        </div>
      </div>
    </div>
  );
}

// Skeleton for trending card area while loading
function TrendingCardSkeleton() {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <div key={i} className="dv3-trending-card dv3-skel" style={{ minHeight: 220 }} aria-hidden="true" />
      ))}
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────
// BacktestCTA — static card, links to /backtest
// ─────────────────────────────────────────────────────────────────────
function BacktestCTA() {
  return (
    <div className="dv3-bt-cta">
      <div className="dv3-bt-cta-glow" />
      <div className="dv3-bt-cta-bg">
        <svg viewBox="0 0 320 220" preserveAspectRatio="none" width="100%" height="100%" aria-hidden="true">
          <defs>
            <linearGradient id="dv3BtBar" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#7B5BFF" />
              <stop offset="100%" stopColor="#2C5BFF" />
            </linearGradient>
          </defs>
          {[0,1,2,3,4,5,6,7,8,9].map((i) => {
            const x = 18 + i * 28;
            const h = 30 + Math.abs(Math.sin(i * 0.8)) * 110 + i * 4;
            return <rect key={i} x={x} y={200 - h} width="18" height={h} rx="3" fill="url(#dv3BtBar)" opacity={0.75 + i * 0.02} />;
          })}
          <path
            d="M14 180 L60 155 L100 138 L150 110 L210 75 L290 32"
            fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"
            style={{ filter: 'drop-shadow(0 4px 12px rgba(255,255,255,0.5))' }}
          />
          <circle cx="290" cy="32" r="5" fill="#fff" />
          <circle cx="290" cy="32" r="12" fill="#fff" opacity="0.18" />
        </svg>
      </div>
      <div className="dv3-bt-cta-body">
        <div className="dv3-bt-cta-eyebrow">BACKTEST WORKBENCH</div>
        <div className="dv3-bt-cta-h">Build a strategy.<br />Walk it forward.</div>
        <div className="dv3-bt-cta-sub">
          Score any rule set against 8 years of Nifty 500 bars · 441 stocks · ₹0 in capital.
        </div>
        <Link to="/backtest" className="dv3-bt-cta-btn">
          Open backtest <Icon.Arrow width="14" height="14" />
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// KiteStrip — hidden when kite.connected is true
// ─────────────────────────────────────────────────────────────────────
function KiteStrip({ onConnect }) {
  return (
    <div className="dv3-kite-strip">
      <div className="dv3-kite-l">
        <div className="dv3-kite-eyebrow">CONNECT BROKER</div>
        <div className="dv3-kite-headline">Place orders straight from a signal.</div>
        <div className="dv3-kite-sub">
          Zerodha Kite is the supported execution venue. OAuth-secured, one-tap routing.
        </div>
      </div>
      <div className="dv3-kite-r">
        <div className="dv3-kite-broker">
          <div className="dv3-kite-broker-logo">
            <Icon.Chart width="18" height="18" style={{ color: '#fff' }} />
          </div>
          <div className="dv3-kite-broker-text">
            <div className="t-ui-subhead">Zerodha · Kite Connect</div>
            <div className="t-ui-footnote">Not connected</div>
          </div>
        </div>
        <button className="dv3-kite-cta" onClick={onConnect}>
          Connect Kite <Icon.Arrow width="13" height="13" />
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// StocksTable — driven from useKiteHoldings() + useQuoteBatch()
// ─────────────────────────────────────────────────────────────────────
function StocksTable({ holdings, quoteData, isLoading }) {
  const rows = useMemo(() => {
    if (!holdings?.length) return [];
    return holdings.slice(0, 8).map((h) => {
      const sym  = (h.tradingsymbol || h.symbol || '').toUpperCase();
      const name = h.product_type || sym; // Kite holdings don't include company name; use sym
      const ltp  = h.last_price ?? 0;
      const qty  = h.quantity ?? 0;
      const avgP = h.average_price ?? 0;
      const dayChg = h.day_change ?? null;
      const gainPct = ltp > 0 && dayChg != null
        ? (dayChg / ltp) * 100
        : h.day_change_percentage ?? null;

      // Quote batch supplies previous_close (Yahoo). High/low are not in the
      // batch payload, so the table shows holdings-native columns (Qty/Avg/LTP)
      // which are always present from Kite rather than market-data columns that
      // would mostly render "—".
      const q = quoteData?.[sym] ?? {};
      const prev = q.previous_close ?? null;
      const mktValue = ltp > 0 && qty > 0 ? ltp * qty : null;

      // Unrealised P&L from real holdings cost basis (no fabricated series).
      const pnl = (ltp > 0 && avgP > 0 && qty > 0) ? (ltp - avgP) * qty : null;
      const pnlPct = (pnl != null && avgP > 0 && qty > 0) ? ((ltp - avgP) / avgP) * 100 : null;

      return { sym, name: sym, prev, mktValue, ltp, avgP, qty, dayChg, gainPct, pnl, pnlPct };
    });
  }, [holdings, quoteData]);

  const [activeTab, setActiveTab] = React.useState('all');

  const filteredRows = useMemo(() => {
    if (activeTab === 'gainers') return rows.filter((r) => (r.gainPct ?? 0) > 0);
    if (activeTab === 'losers')  return rows.filter((r) => (r.gainPct ?? 0) < 0);
    return rows;
  }, [rows, activeTab]);

  return (
    <div className="dv3-stocks-table">
      <div className="dv3-stocks-table-head">
        <div className="dv3-stocks-table-title">
          <div className="t-ui-headline">Holdings</div>
          <div className="t-ui-footnote">
            {isLoading ? 'Loading…' : rows.length ? `${rows.length} positions · Kite data` : 'Connect Kite to see positions'}
          </div>
        </div>
        <div className="dv3-stocks-table-tabs">
          {['all', 'gainers', 'losers'].map((tab) => (
            <button
              key={tab}
              className={`dv3-ttab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="dv3-stocks-table-grid">
        {/* Headers */}
        <div className="dv3-th">Company</div>
        <div className="dv3-th dv3-th-r">Qty</div>
        <div className="dv3-th dv3-th-r">Avg cost</div>
        <div className="dv3-th dv3-th-r">LTP</div>
        <div className="dv3-th dv3-th-r">Change</div>
        <div className="dv3-th dv3-th-r">Unreal. P&amp;L</div>

        {isLoading ? (
          <div className="dv3-holdings-empty" style={{ gridColumn: '1 / -1' }}>
            <div className="dv3-skel" style={{ height: 14, width: '40%', margin: '0 auto', borderRadius: 8 }} />
          </div>
        ) : filteredRows.length === 0 ? (
          <div className="dv3-holdings-empty" style={{ gridColumn: '1 / -1' }}>
            {rows.length === 0
              ? 'Connect Kite to see your holdings here.'
              : `No ${activeTab} right now.`}
          </div>
        ) : (
          filteredRows.map((r) => (
            <React.Fragment key={r.sym}>
              <div className="dv3-td dv3-td-name">
                <Logo sym={r.sym} size={32} radius={8} />
                <div>
                  <div className="dv3-td-name-sym">{r.sym}</div>
                  <div className="dv3-td-name-full">{r.name}</div>
                </div>
              </div>
              <div className="dv3-td dv3-td-r">{r.qty != null ? r.qty : '—'}</div>
              <div className="dv3-td dv3-td-r">{r.avgP ? fmtINR(r.avgP) : '—'}</div>
              <div className="dv3-td dv3-td-r">{r.ltp ? fmtINR(r.ltp) : '—'}</div>
              <div
                className="dv3-td dv3-td-r"
                style={{ color: r.gainPct == null ? 'var(--text-3)' : r.gainPct >= 0 ? 'var(--bull)' : 'var(--bear)' }}
              >
                {r.gainPct != null ? fmtPct(r.gainPct) : '—'}
              </div>
              <div
                className="dv3-td dv3-td-r"
                style={{ color: r.pnl == null ? 'var(--text-3)' : r.pnl >= 0 ? 'var(--bull)' : 'var(--bear)' }}
              >
                {r.pnl != null ? (
                  <span>
                    {r.pnl >= 0 ? '+' : '−'}{fmtINR(Math.abs(r.pnl))}
                    {r.pnlPct != null && (
                      <span className="dv3-pnl-pct"> {r.pnlPct >= 0 ? '+' : '−'}{Math.abs(r.pnlPct).toFixed(1)}%</span>
                    )}
                  </span>
                ) : '—'}
              </div>
            </React.Fragment>
          ))
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SectorBreadth — distribution of today's candidates across sectors.
// NOTE: the model only surfaces bullish candidates, so a "% bullish" per
// sector would be tautologically 100%. Instead we show WHERE today's
// candidates cluster (count per sector) — an honest read of concentration.
// TODO: a dedicated advance/decline breadth endpoint would let us show
// true bullish-vs-bearish proportions.
// ─────────────────────────────────────────────────────────────────────
const SECTOR_LAYOUT = [
  { top: 6,   left: 8   },
  { top: 16,  left: 162 },
  { top: 148, left: 6   },
  { top: 150, left: 122 },
  { top: 172, left: 222 },
];

function SectorBreadth({ signals }) {
  // Group today's candidates by sector, count per sector.
  const { derived, total } = useMemo(() => {
    if (!signals?.length) return { derived: [], total: 0 };
    const map = new Map();
    for (const s of signals) {
      const sec = s.sector || 'Other';
      map.set(sec, (map.get(sec) || 0) + 1);
    }
    const sorted = Array.from(map.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    const maxCount = sorted.length ? sorted[0][1] : 1;
    const list = sorted.map(([name, count], i) => {
      const layout = SECTOR_LAYOUT[i] || { top: 100 + i * 30, left: 50 };
      const size = 80 + Math.round((count / maxCount) * 56);
      return { name, count, size, top: layout.top, left: layout.left };
    });
    return { derived: list, total: signals.length };
  }, [signals]);

  return (
    <div className="dv3-card">
      <div className="dv3-card-head">
        <div>
          <div className="t-ui-headline">Signal distribution</div>
          <div className="t-ui-footnote">Where today's candidates cluster</div>
        </div>
      </div>

      {derived.length === 0 ? (
        <div className="dv3-no-breadth">No candidates yet — the model runs at 4:15 PM IST on trading days.</div>
      ) : (
        <>
          <div className="dv3-bubble-stage">
            {derived.map((s) => (
              <div
                key={s.name}
                className="dv3-bubble dv3-bubble-bull"
                style={{ top: s.top, left: s.left, width: s.size, height: s.size }}
                title={`${s.name} · ${s.count} candidate${s.count === 1 ? '' : 's'}`}
              >
                <div className="dv3-bubble-pct">{s.count}</div>
                <div className="dv3-bubble-name">{s.name}</div>
              </div>
            ))}
          </div>
          <div className="dv3-bubble-legend">
            <span className="dv3-leg-summary">
              <span className="num-bull">{total}</span> candidate{total === 1 ? '' : 's'} across {derived.length} sector{derived.length === 1 ? '' : 's'}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// BalanceCard — useKiteMargins() + useOverview().portfolio
// Falls back to paper-portfolio from overview when Kite not connected.
// ─────────────────────────────────────────────────────────────────────
function BalanceCard({ margins, portfolio, holdings, kiteConnected }) {
  // When Kite-connected, derive everything from REAL account data — never
  // the paper portfolio (which would mislabel the ₹10L paper capital as a
  // live Kite balance). Holdings value + cost come from the holdings rows;
  // cash from margins.available.
  const kite = useMemo(() => {
    if (!kiteConnected) return null;
    const rows = holdings ?? [];
    let mktValue = 0, cost = 0;
    for (const h of rows) {
      const qty = h.quantity ?? 0;
      const ltp = h.last_price ?? 0;
      const avg = h.average_price ?? 0;
      if (qty > 0 && ltp > 0) mktValue += qty * ltp;
      if (qty > 0 && avg > 0) cost += qty * avg;
    }
    const cash = margins?.available ?? null;
    const pnl = cost > 0 ? mktValue - cost : null;
    return {
      total: cash != null ? mktValue + cash : (mktValue || null),
      cash,
      invested: mktValue || null,
      returnPct: cost > 0 ? (pnl / cost) * 100 : null,
      nPositions: rows.length || null,
    };
  }, [kiteConnected, holdings, margins]);

  const totalValue = kite ? kite.total      : (portfolio?.total_value ?? null);
  const available  = kite ? kite.cash        : (portfolio?.cash ?? null);
  const used       = kite ? kite.invested    : (portfolio?.invested ?? null);
  const returnPct  = kite ? kite.returnPct   : (portfolio?.total_return_pct ?? null);
  const nPositions = kite ? kite.nPositions  : (portfolio?.n_positions ?? null);
  const investedLabel = kite ? 'Holdings value' : 'Invested';

  return (
    <div className="dv3-balance-card">
      <div className="dv3-balance-glow" />
      <div className="dv3-balance-head">
        <div>
          <div className="card-head-title">Portfolio</div>
          <div className="card-head-sub">
            {kiteConnected ? 'Kite · live balance' : 'Paper portfolio'}
          </div>
        </div>
        <span className="dv3-plan-chip">
          {returnPct != null
            ? <span className={returnPct >= 0 ? 'num-bull' : 'num-bear'}>{fmtPct(returnPct)}</span>
            : 'PRO'}
        </span>
      </div>

      <div className="dv3-balance-stat">{totalValue != null ? fmtLakh(totalValue) : '—'}</div>
      <div className="dv3-balance-stat-label">TOTAL VALUE</div>

      <div className="dv3-balance-rows">
        <div className="dv3-balance-row">
          <span>Available cash</span>
          <span className="dv3-balance-val">{available != null ? fmtLakh(available) : '—'}</span>
        </div>
        <div className="dv3-balance-row">
          <span>{investedLabel}</span>
          <span className="dv3-balance-val">{used != null ? fmtLakh(used) : '—'}</span>
        </div>
        {nPositions != null && (
          <div className="dv3-balance-row">
            <span>Open positions</span>
            <span className="dv3-balance-val">{nPositions}</span>
          </div>
        )}
      </div>

      <Link to="/portfolio" className="dv3-balance-cta">
        View portfolio <Icon.Arrow width="13" height="13" />
      </Link>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// EquityNetWorth — top-of-page net-worth bar (prototype). Same derivation
// as BalanceCard: real Kite holdings + margins when connected, else the
// paper portfolio from overview. Additive; never fabricates numbers.
// ─────────────────────────────────────────────────────────────────────
function EquityNetWorth({ margins, portfolio, holdings, kiteConnected }) {
  const kite = useMemo(() => {
    if (!kiteConnected) return null;
    const rows = holdings ?? [];
    let mktValue = 0, cost = 0;
    for (const h of rows) {
      const qty = h.quantity ?? 0, ltp = h.last_price ?? 0, avg = h.average_price ?? 0;
      if (qty > 0 && ltp > 0) mktValue += qty * ltp;
      if (qty > 0 && avg > 0) cost += qty * avg;
    }
    const pnl = cost > 0 ? mktValue - cost : null;
    return {
      current: mktValue || null,
      invested: cost || null,
      pnl,
      pnlPct: cost > 0 ? (pnl / cost) * 100 : null,
    };
  }, [kiteConnected, holdings]);

  const current  = kite ? kite.current  : (portfolio?.total_value ?? null);
  const invested = kite ? kite.invested : (portfolio?.invested ?? null);
  const pnl      = kite ? kite.pnl
    : (portfolio?.total_pnl ?? ((current != null && invested != null) ? current - invested : null));
  const pnlPct   = kite ? kite.pnlPct   : (portfolio?.total_return_pct ?? null);
  const dayPnl   = portfolio?.day_pnl ?? null;
  const dayPct   = portfolio?.day_return_pct ?? null;

  return (
    <div className="dv3-networth">
      <div className="dv3-nw-head">
        <div>
          <span className="card-head-title">My equity net-worth</span>
          <span className="card-head-sub">{kiteConnected ? 'Kite · live' : 'Paper portfolio'}</span>
        </div>
        <Link to="/portfolio" className="dv3-nw-link">View details <Icon.Arrow width="12" height="12" /></Link>
      </div>
      <div className="dv3-nw-body">
        <div className="dv3-nw-item">
          <div className="dv3-nw-k">Current value</div>
          <div className="dv3-nw-v">{current != null ? fmtLakh(current) : '—'}</div>
        </div>
        <div className="dv3-nw-item">
          <div className="dv3-nw-k">Invested</div>
          <div className="dv3-nw-v">{invested != null ? fmtLakh(invested) : '—'}</div>
        </div>
        <div className="dv3-nw-item">
          <div className="dv3-nw-k">Total P&amp;L</div>
          <div className={`dv3-nw-v ${pnl != null ? (pnl >= 0 ? 'num-bull' : 'num-bear') : ''}`}>
            {pnl != null ? fmtLakh(pnl) : '—'}
            {pnlPct != null && <small> ({fmtPct(pnlPct)})</small>}
          </div>
        </div>
        {dayPnl != null && (
          <div className="dv3-nw-item dv3-nw-day">
            <div className="dv3-nw-k">Today's P&amp;L</div>
            <div className={`dv3-nw-v ${dayPnl >= 0 ? 'num-bull' : 'num-bear'}`}>
              {fmtLakh(dayPnl)}{dayPct != null ? ` (${fmtPct(dayPct)})` : ''}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// ActionTiles — the prototype's vibrant "what you can do" gradient cards.
// Real routes only (no fake broker actions); crons are scheduled so there
// is no manual-scan tile.
// ─────────────────────────────────────────────────────────────────────
function ActionTiles() {
  const tiles = [
    { cls: 'dv3-qa-teal',   to: '/premove',      title: 'Position sizer', desc: "Size today's top names to your capital & E-margin." },
    { cls: 'dv3-qa-violet', to: '/track-record', title: 'Track record',   desc: 'Live paper equity curve & closed-trade log.' },
    { cls: 'dv3-qa-blue',   to: '/pnl',          title: 'Analytics',      desc: 'Performance, attribution & signal stats.' },
  ];
  return (
    <section className="dv3-row">
      <div className="dv3-actions">
        {tiles.map((t) => (
          <Link key={t.to} to={t.to} className={`dv3-qa ${t.cls}`}>
            <span className="dv3-qa-deco" />
            <h4>{t.title}</h4>
            <p>{t.desc}</p>
            <span className="dv3-qa-go">Open <Icon.Arrow width="12" height="12" /></span>
          </Link>
        ))}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────
// ModelHealth — prototype right-rail card. Shows the model is running and
// its headline stats, from cron_health (useSignals) + metrics/portfolio
// (useOverview). Same formatting conventions as PortfolioV3's PerfRibbon.
// ─────────────────────────────────────────────────────────────────────
function ModelHealth({ cronHealth, metrics, portfolio }) {
  const ranToday = cronHealth?.last_run_today;
  const winRate  = metrics?.win_rate ?? null;
  const sharpe   = metrics?.sharpe_ratio ?? null;
  const drawdown = portfolio?.drawdown_pct ?? null;
  const trades   = metrics?.total_trades ?? null;

  const rows = [
    ['Daily scan', ranToday
      ? <span className="num-bull">● Ran today</span>
      : <span className="num-warn">Pending</span>],
    ['Win rate', winRate != null ? `${Number(winRate).toFixed(1)}%` : '—'],
    ['Sharpe ratio', sharpe != null ? Number(sharpe).toFixed(2) : '—'],
    ['Max drawdown', drawdown != null
      ? <span className="num-bear">{fmtPct(-Math.abs(drawdown))}</span>
      : '—'],
    ['Closed trades', trades != null ? `${trades}` : '—'],
  ];

  return (
    <div className="dv3-card dv3-model-health">
      <div className="dv3-card-head">
        <div>
          <div className="t-ui-headline">Model health</div>
          <div className="t-ui-footnote">Momentum book · paper</div>
        </div>
      </div>
      {rows.map(([k, v]) => (
        <div className="dv3-mh-row" key={k}>
          <span className="dv3-mh-k">{k}</span>
          <span className="dv3-mh-v">{v}</span>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// PickOfWeek — the prototype's magenta "pick of the week" card, driven by
// the top-ranked signal of the day. Null-safe (renders nothing if no signal).
// ─────────────────────────────────────────────────────────────────────
function PickOfWeek({ sig }) {
  if (!sig) return null;
  const sym = sig.ticker || sig.sym || sig.symbol || '';
  const name = sig.name || sig.company || '';
  const num = (n) => (n == null ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 }));
  const reco = sig.entry ?? sig.reco_price ?? null;
  const target = sig.target ?? null;
  const upside = sig.predicted_return_pct ?? sig.expected_return ?? null;
  return (
    <div className="dv3-pick">
      <span className="dv3-pick-badge">★ Pick of the week</span>
      <div className="dv3-pick-nm">
        <Logo sym={sym} size={30} radius={8} />
        <h4>{sym}{name ? ` · ${name}` : ''}</h4>
      </div>
      <div className="dv3-pick-metrics">
        <div><div className="k">Reco</div><div className="v">{num(reco)}</div></div>
        <div><div className="k">Target</div><div className="v">{num(target)}</div></div>
        <div><div className="k">Upside</div><div className="v">{upside == null ? '—' : fmtPct(upside)}</div></div>
      </div>
      <Link to="/premove" className="dv3-pick-btn">Size &amp; view →</Link>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// ToolsGrid — the prototype's "Your tools" grid; links to real routes only.
// ─────────────────────────────────────────────────────────────────────
function ToolsGrid() {
  const tools = [
    { to: '/premove', label: 'Position sizer' },
    { to: '/track-record', label: 'Track record' },
    { to: '/pnl', label: 'P&L report' },
    { to: '/orders', label: 'Trade log' },
    { to: '/journal', label: 'Journal' },
    { to: '/backtest', label: 'Backtest' },
  ];
  return (
    <div className="dv3-card dv3-tools-card">
      <div className="dv3-card-head"><div className="t-ui-headline">Your tools</div></div>
      <div className="dv3-tools">
        {tools.map((t) => (
          <Link key={t.to} to={t.to} className="dv3-tool">
            <span className="dv3-tool-ic"><Icon.Arrow width="14" height="14" /></span>
            <span className="dv3-tool-lbl">{t.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// MarketIndices — the prototype's index strip, from useIndexSparklines().
// Defensive on the payload shape ({last,changePct} or {ltp,change_pct}).
// ─────────────────────────────────────────────────────────────────────
const INDEX_LABELS = {
  NIFTY: 'NIFTY 50', NIFTY50: 'NIFTY 50', SENSEX: 'SENSEX',
  BANKNIFTY: 'BANK NIFTY', NIFTYBANK: 'BANK NIFTY', INDIAVIX: 'INDIA VIX',
  VIX: 'INDIA VIX', USDINR: 'USD/INR', NIFTYMIDCAP: 'NIFTY MIDCAP', NIFTYIT: 'NIFTY IT',
};
function MarketIndices({ indexData }) {
  const items = useMemo(() => {
    if (!indexData || typeof indexData !== 'object') return [];
    return Object.keys(indexData).map((k) => {
      const d = indexData[k] || {};
      const val = d.last ?? d.ltp ?? d.value;
      const chg = d.changePct ?? d.change_pct ?? d.change;
      if (typeof val !== 'number' || !isFinite(val)) return null;
      return { key: k, label: INDEX_LABELS[k] || k, val, chg: (typeof chg === 'number' ? chg : 0) };
    }).filter(Boolean).slice(0, 6);
  }, [indexData]);
  if (!items.length) return null;
  return (
    <section className="dv3-row">
      <div className="dv3-row-head"><div><h2 className="dv3-row-title" style={{ fontSize: 16 }}>Market indices</h2></div></div>
      <div className="dv3-indices">
        {items.map((it) => (
          <div className="dv3-idx" key={it.key}>
            <div className="dv3-idx-n">{it.label}</div>
            <div className="dv3-idx-v tnum">{it.val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
            <div className={`dv3-idx-c tnum ${it.chg >= 0 ? 'num-bull' : 'num-bear'}`}>
              {it.chg >= 0 ? '▲' : '▼'}{Math.abs(it.chg).toFixed(2)}%
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────
// MorningCommentary — the prototype's amber note, derived from real regime
// + breadth + today's signal count (no fabricated text).
// ─────────────────────────────────────────────────────────────────────
function MorningCommentary({ regime, signalsCount }) {
  const status = regime?.status || regime?.label;
  if (!status) return null;
  const label = String(status).charAt(0).toUpperCase() + String(status).slice(1);
  const breadth = regime?.breadth;
  return (
    <div className="dv3-commentary">
      <div className="dv3-comm-tag">Model note</div>
      <h4>The market is {label} today.</h4>
      <p>
        {breadth != null ? `Breadth ${breadth >= 0 ? '+' : ''}${breadth} adv−dec. ` : ''}
        {signalsCount > 0
          ? `${signalsCount} names cleared the conviction gate this scan.`
          : 'No fresh buys cleared the gate this scan.'}
        {' '}No manual action — the book posts itself.
      </p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// DashboardV3 — main page export
// ─────────────────────────────────────────────────────────────────────
export default function DashboardV3() {
  const kite          = useContext(KiteContext);
  const signalsQuery  = useSignals();
  const watchlistQuery = useWatchlist();
  const overviewQuery = useOverview();
  const holdingsQuery = useKiteHoldings({ enabled: !!kite?.connected });
  const marginsQuery  = useKiteMargins({ enabled: !!kite?.connected });
  const indexQuery    = useIndexSparklines();

  // Quote batch for holdings — request high/low/prev for held symbols
  const heldSymbols = useMemo(() => {
    const list = holdingsQuery.data ?? [];
    return list.slice(0, 8).map((h) => (h.tradingsymbol || '').toUpperCase()).filter(Boolean);
  }, [holdingsQuery.data]);
  const quotesQuery = useQuoteBatch(heldSymbols, {
    enabled: kite?.connected && heldSymbols.length > 0,
  });

  // ── Data derivation ──────────────────────────────────────────────
  // Memoized so downstream useMemo dependencies remain stable across renders.
  const signals    = useMemo(() => signalsQuery.data?.signals ?? [], [signalsQuery.data]);
  const watchlist  = useMemo(() => watchlistQuery.data?.signals ?? [], [watchlistQuery.data]);
  const regime     = useMemo(() => signalsQuery.data?.regime  ?? {}, [signalsQuery.data]);
  const cronHealth = useMemo(() => signalsQuery.data?.cron_health ?? {}, [signalsQuery.data]);
  const portfolio  = useMemo(() => overviewQuery.data?.portfolio ?? {}, [overviewQuery.data]);
  const metrics    = useMemo(() => overviewQuery.data?.metrics ?? {}, [overviewQuery.data]);
  const winRate    = metrics?.win_rate ?? null; // used as proxy for per-signal model win rate

  // Rank helper: A-grade first, then confidence desc.
  const rankByGrade = (list) => [...list].sort((a, b) => {
    const ga = (a.grade || 'B')[0]; const gb = (b.grade || 'B')[0];
    if (ga !== gb) return ga < gb ? -1 : 1;
    return (b.confidence ?? b.ml_score ?? 0) - (a.confidence ?? a.ml_score ?? 0);
  });

  // Top 3 fresh signals; if today's scan produced none, fall back to the
  // brewing watchlist so the section is never an empty placeholder.
  const top3 = useMemo(() => (signals.length ? rankByGrade(signals).slice(0, 3) : []), [signals]);
  const brewing3 = useMemo(
    () => (!signals.length && watchlist.length ? rankByGrade(watchlist).slice(0, 3) : []),
    [signals, watchlist]
  );
  const showingBrewing = top3.length === 0 && brewing3.length > 0;
  const displayCards = top3.length ? top3 : brewing3;

  // Sector breadth: prefer today's signals, fall back to the watchlist so
  // a zero-signal day (e.g. choppy regime) still populates the panel.
  const breadthSource = signals.length ? signals : watchlist;

  const indexData = indexQuery.data ?? {};
  const sigLoading = signalsQuery.isLoading || watchlistQuery.isLoading;

  // Connect Kite handler — delegates to existing KiteContext
  const handleConnectKite = () => {
    if (kite?.connect) kite.connect();
  };

  // Build a timestamp label for the regime strip scan notice
  const scanNote = cronHealth?.last_run_today
    ? 'Last scan: 4:15 PM IST'
    : 'Next scan: 4:15 PM IST';

  return (
    <div className="dv3-page density-regular">
      {/* ── Equity net-worth bar ─────────────────────────────────── */}
      <EquityNetWorth
        margins={marginsQuery.data}
        portfolio={portfolio}
        holdings={holdingsQuery.data ?? []}
        kiteConnected={!!kite?.connected}
      />

      {/* ── Main grid: content column + full-height right rail (prototype) ── */}
      <div className="dv3-main-grid">
        <div className="dv3-main-col">
          {/* RegimeStrip */}
          <RegimeStrip regime={regime} indexData={indexData} />

          {/* Scan-status ribbon */}
          <div className="dv3-scan-status">
            <span className="dv3-live-dot" />
            <div className="dv3-scan-txt">
              <div className="dv3-scan-head">
                {cronHealth?.last_run_today ? "Today's scan ran on schedule" : 'Next scan at 4:15 PM IST'}
                {signals.length ? ` · ${signals.length} signals` : ''}
              </div>
              <div className="dv3-scan-sub">
                Cron {cronHealth?.last_run_today ? 'healthy' : 'pending'} · runs 4:15 PM IST on trading days — the calls post themselves, no manual scan.
              </div>
            </div>
            <Link to="/premove" className="dv3-scan-link">See all calls →</Link>
          </div>

          {/* Research calls */}
          <section className="dv3-row">
            <div className="dv3-row-head">
              <div>
                <div className="dv3-row-eyebrow">
                  {showingBrewing ? 'BREWING · BELOW ENTRY GATE' : 'TODAY · 16:15 IST SCAN'}
                </div>
                <h2 className="dv3-row-title">
                  {showingBrewing ? 'Brewing watchlist' : 'Research calls'}
                </h2>
                <div className="dv3-row-sub">
                  {sigLoading
                    ? 'Loading…'
                    : signals.length > 0
                      ? `${signals.length} of 441 stocks scored above conviction threshold · ${scanNote}`
                      : showingBrewing
                        ? `No fresh buys today — ${watchlist.length} names brewing below the entry gate · ${scanNote}`
                        : `No signals from today's scan · ${scanNote}`}
                </div>
              </div>
            </div>

            <div className="dv3-trending-grid">
              {sigLoading ? (
                <TrendingCardSkeleton />
              ) : displayCards.length === 0 ? (
                <div className="dv3-no-signals">
                  No high-conviction signals from today's scan. The model runs at 4:15 PM IST on trading days.
                </div>
              ) : (
                displayCards.map((sig) => (
                  <TrendingCard
                    key={sig.ticker || sig.sym || sig.symbol}
                    sig={sig}
                    modelWinRate={winRate}
                    brewing={showingBrewing}
                  />
                ))
              )}
              <BacktestCTA />
            </div>

            {!kite?.connected && <KiteStrip onConnect={handleConnectKite} />}
          </section>

          {/* Holdings table */}
          <StocksTable
            holdings={holdingsQuery.data ?? []}
            quoteData={quotesQuery.data ?? {}}
            isLoading={holdingsQuery.isLoading}
          />

          {/* Market indices strip */}
          <MarketIndices indexData={indexData} />

          {/* Action tiles */}
          <ActionTiles />
        </div>

        {/* Right rail — Pick of the week, tools, commentary, model health, breadth, balance */}
        <aside className="dv3-right-rail">
          <PickOfWeek sig={displayCards[0]} />
          <ToolsGrid />
          <MorningCommentary regime={regime} signalsCount={signals.length} />
          <ModelHealth cronHealth={cronHealth} metrics={metrics} portfolio={portfolio} />
          <SectorBreadth signals={breadthSource} />
          <BalanceCard
            margins={marginsQuery.data}
            portfolio={portfolio}
            holdings={holdingsQuery.data ?? []}
            kiteConnected={!!kite?.connected}
          />
        </aside>
      </div>

      {/* ── Footer ──────────────────────────────────────────────── */}
      <footer className="dv3-foot">
        <div className="dv3-disclaimer">{DISCLAIMER}</div>
        <div className="dv3-foot-meta">
          SEBI Research Analyst · Model-generated signals · NSE data delayed 15 min · v2026.06
        </div>
      </footer>
    </div>
  );
}
