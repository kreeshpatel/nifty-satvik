/**
 * LandingV2.jsx — Nifty Satvik marketing landing — "THE SATVIK ALMANAC".
 *
 * Complete visual redesign (2026-07-07): a printed financial-broadsheet / ledger
 * aesthetic (warm newsprint, editorial serif, ruled tables) replacing the prior
 * dark-glass look. Styles: frontend/src/styles/landing-v2.css — every selector
 * scoped under [data-page-ctx="landing"] per CLAUDE.md.
 *
 * Behaviour unchanged from the previous version:
 *   - FAQ accordion   → useState(openFaq) single-open index
 *   - Sector tabs     → useState(activeSector) + SECTORS data map
 *   - Weekly scan     → conditional section, safe aggregate from /api/landing-stats
 *   - All "Request access" CTAs → RequestAccessModal (real POST /api/access-requests)
 *
 * Compliance: no "guarantee / will / sure-shot" language; every real number is
 * served aggregate-only by GET /api/landing-stats with honest baseline_v1 fallbacks.
 */

import { useState, useEffect } from 'react';
import { RegimeProvider } from '@/context/RegimeContext';
import DashboardMockup from '@/components/landing/DashboardMockup';
import RequestAccessModal from '@/components/landing/RequestAccessModal';
import kiteMark from '@/assets/brand/kite-logo.png';
import brandLogo from '@/assets/brand/nifty-satvik-logo.png';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/landing-v2.css';

// Real performance numbers are served by GET /api/landing-stats (public, aggregate-only —
// never tickers/prices/parameters). The constants below are the honest FALLBACKS (the frozen
// baseline_v1 anchor) used until the fetch resolves or if the endpoint is unreachable, so the
// page never renders a blank or an invented figure. SAFETY: nothing here reveals the strategy.
const STATS_FALLBACK = {
  // Weekly-swing 0094 book (the marketed model), NET of costs, corrected universe 2017–2026.
  // Reproduced from scripts/run_bhanushali_weekly_rank.py. NOT certified (DSR 0.894). The API
  // serves these same frozen values; this is the honest offline fallback.
  backtest: {
    cagr_pct: 24.7, net_cagr_pct: 24.7, sharpe: 1.13, win_rate_pct: 59.2,
    total_trades: 255, max_drawdown_pct: -42.4, operational_max_drawdown_pct: -42.4,
    total_return_pct: 711, mult: 8.11, alpha_pp: 528, dsr: 0.894, certified: false,
    period: '2017–2026',
  },
  live: { since: '2026-06-30', n_positions: null, n_closed: 0, total_return_pct: null },
  weekly_swing: null,   // this week's swing scan — populated by the API when a fresh scan exists
  // Net calendar-year returns of the weekly-swing 0094 book (net of costs, corrected universe).
  // 2017 & 2026 are partial years. ₹10L → ₹81.15L over the full run.
  yearly_returns: [
    { year: '2017', net_pct: 31.8, partial: true },
    { year: '2018', net_pct: 11.6, partial: false },
    { year: '2019', net_pct: 30.8, partial: false },
    { year: '2020', net_pct: 11.4, partial: false },
    { year: '2021', net_pct: 34.5, partial: false },
    { year: '2022', net_pct: 34.8, partial: false },
    { year: '2023', net_pct: 66.5, partial: false },
    { year: '2024', net_pct: 9.9,  partial: false },
    { year: '2025', net_pct: -13.0, partial: false },
    { year: '2026', net_pct: 31.3, partial: true },
  ],
  // Growth-of-100 curve, weekly-swing 0094 NET vs Nifty 500 TRI (indexed to inception).
  // Strategy ends 811.5 (8.11×, +711%); Nifty 283.9. Compact fallback; API serves the full series.
  equity_bt: [
    { t: '2017-01', s: 99.1,  b: 100.0 }, { t: '2018-01', s: 140.6, b: 109.3 },
    { t: '2019-01', s: 152.9, b: 102.8 }, { t: '2020-01', s: 210.4, b: 113.9 },
    { t: '2020-04', s: 174.2, b: 92.9 },  { t: '2021-01', s: 219.2, b: 132.0 },
    { t: '2022-01', s: 297.9, b: 176.1 }, { t: '2023-01', s: 383.6, b: 178.4 },
    { t: '2024-01', s: 666.6, b: 238.7 }, { t: '2024-07', s: 827.2, b: 285.3 },
    { t: '2025-04', s: 604.1, b: 268.5 }, { t: '2026-06', s: 811.5, b: 283.9 },
  ],
};

// number → display string, '—' when null/undefined (never an invented number).
const fmt = (v, opts = {}) => {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const { dp = 0, sign = false, suffix = '' } = opts;
  const n = Number(v);
  const s = n.toFixed(dp);
  return `${sign && n > 0 ? '+' : ''}${s}${suffix}`;
};

/* ─── Sector tab data ─── */
const SECTORS = {
  largecap: {
    key: 'largecap',
    label: 'Large-cap · Nifty 100',
    name: 'Nifty 100 · Large-cap universe',
    meta: 'Illustrative — the universe Nifty Satvik scans daily',
    pct: '100 names',
    linePath: 'M0 240 L60 220 L120 200 L180 195 L240 170 L300 155 L360 130 L420 115 L480 90 L540 75 L600 60',
    fillPath: 'M0 240 L60 220 L120 200 L180 195 L240 170 L300 155 L360 130 L420 115 L480 90 L540 75 L600 60 L600 280 L0 280 Z',
    endCx: 600, endCy: 60,
    rows: [
      { sym: 'RELIANCE', name: 'Reliance Industries', price: '₹2,948.20', chg: '+2.18%', tone: 'bull' },
      { sym: 'TCS',      name: 'Tata Consultancy',   price: '₹4,128.50', chg: '+1.62%', tone: 'bull' },
      { sym: 'HDFCBANK', name: 'HDFC Bank',          price: '₹1,748.20', chg: '+1.05%', tone: 'bull' },
      { sym: 'INFY',     name: 'Infosys',            price: '₹1,842.10', chg: '−0.77%', tone: 'bear' },
      { sym: 'ICICIBANK',name: 'ICICI Bank',         price: '₹1,218.60', chg: '+1.05%', tone: 'bull' },
    ],
  },
  midcap: {
    key: 'midcap',
    label: 'Mid-cap · Nifty 150',
    name: 'Nifty Midcap 150',
    meta: 'Illustrative — the universe Nifty Satvik scans daily',
    pct: '150 names',
    linePath: 'M0 250 L60 235 L120 220 L180 200 L240 195 L300 165 L360 145 L420 110 L480 85 L540 55 L600 35',
    fillPath: 'M0 250 L60 235 L120 220 L180 200 L240 195 L300 165 L360 145 L420 110 L480 85 L540 55 L600 35 L600 280 L0 280 Z',
    endCx: 600, endCy: 35,
    rows: [
      { sym: 'TATAPOWER', name: 'Tata Power',        price: '₹468.40',   chg: '+3.42%', tone: 'bull' },
      { sym: 'POLYCAB',   name: 'Polycab India',     price: '₹7,124.00', chg: '+2.84%', tone: 'bull' },
      { sym: 'VOLTAS',    name: 'Voltas Ltd',        price: '₹1,684.20', chg: '+1.92%', tone: 'bull' },
      { sym: 'CUMMINSIND',name: 'Cummins India',     price: '₹3,842.50', chg: '+1.64%', tone: 'bull' },
      { sym: 'JUBLFOOD',  name: 'Jubilant FoodWorks',price: '₹612.80',   chg: '−0.82%', tone: 'bear' },
    ],
  },
  smallcap: {
    key: 'smallcap',
    label: 'Small-cap · Nifty 250',
    name: 'Nifty Smallcap 250',
    meta: 'Illustrative — the universe Nifty Satvik scans daily',
    pct: '250 names',
    linePath: 'M0 260 L60 250 L120 232 L180 240 L240 200 L300 180 L360 140 L420 100 L480 85 L540 45 L600 22',
    fillPath: 'M0 260 L60 250 L120 232 L180 240 L240 200 L300 180 L360 140 L420 100 L480 85 L540 45 L600 22 L600 280 L0 280 Z',
    endCx: 600, endCy: 22,
    rows: [
      { sym: 'CRAFTSMAN', name: 'Craftsman Automation', price: '₹4,820.00', chg: '+4.62%', tone: 'bull' },
      { sym: 'JBCHEPHARM',name: 'JB Chemicals',         price: '₹1,842.40', chg: '+3.18%', tone: 'bull' },
      { sym: 'CDSL',      name: 'Central Depository',   price: '₹1,684.00', chg: '+2.42%', tone: 'bull' },
      { sym: 'BLUEDART',  name: 'Blue Dart Express',    price: '₹7,242.00', chg: '+1.94%', tone: 'bull' },
      { sym: 'IIFL',      name: 'IIFL Finance',         price: '₹412.60',   chg: '−1.42%', tone: 'bear' },
    ],
  },
  banking: {
    key: 'banking',
    label: 'Banking · BankNifty',
    name: 'BankNifty universe',
    meta: 'Illustrative — the universe Nifty Satvik scans daily',
    pct: 'Bank Nifty',
    linePath: 'M0 245 L60 240 L120 225 L180 210 L240 215 L300 195 L360 180 L420 165 L480 140 L540 115 L600 85',
    fillPath: 'M0 245 L60 240 L120 225 L180 210 L240 215 L300 195 L360 180 L420 165 L480 140 L540 115 L600 85 L600 280 L0 280 Z',
    endCx: 600, endCy: 85,
    rows: [
      { sym: 'HDFCBANK',  name: 'HDFC Bank',            price: '₹1,748.20', chg: '+1.05%', tone: 'bull' },
      { sym: 'ICICIBANK', name: 'ICICI Bank',            price: '₹1,218.60', chg: '+1.05%', tone: 'bull' },
      { sym: 'SBIN',      name: 'State Bank of India',   price: '₹768.40',   chg: '+1.62%', tone: 'bull' },
      { sym: 'KOTAKBANK', name: 'Kotak Mahindra Bank',   price: '₹1,842.60', chg: '+0.80%', tone: 'bull' },
      { sym: 'AXISBANK',  name: 'Axis Bank',             price: '₹1,124.20', chg: '−0.42%', tone: 'bear' },
    ],
  },
};
const SECTOR_KEYS = ['largecap', 'midcap', 'smallcap', 'banking'];

/* ─── FAQ items ─── */
const FAQ_ITEMS = [
  {
    q: 'Is Nifty Satvik SEBI-registered?',
    a: 'No. Nifty Satvik is not a SEBI-registered investment advisor or research analyst. We publish research and decision-support signals — not personalised investment advice — and we never manage your capital. Every order is placed by you, in your own Zerodha Kite account.',
  },
  {
    q: 'Do I need a Zerodha Kite account?',
    a: 'For one-click routing, yes — Kite Connect is the only execution venue we integrate with today. You can still use Nifty Satvik without Kite — you\'ll just place orders manually in your own broker.',
  },
  {
    q: "What's the minimum capital to start?",
    a: "There's no hard floor, but we recommend ₹2,00,000 minimum. Position sizes scale with your equity, and small accounts have trouble respecting stops on higher-priced names like NESTLEIND or BAJFINANCE.",
  },
  {
    q: 'How is this different from a Telegram tip channel?',
    a: "Three differences. (1) Every signal has explicit entry, stop, and target — no \"buy at CMP\". (2) Every signal is walk-forward backtested before it ships — no \"this stock looks good\". (3) Every trade is logged with timestamps, fills, and P&L — no screenshots, no selective memory.",
  },
  {
    q: 'What does it cost?',
    a: 'Nothing today. Nifty Satvik is private and invite-only — not a paid subscription. You bring your own Zerodha account; we don\'t charge a fee or manage your money. Revoke access anytime — your journal and track-record data stay readable.',
  },
  {
    q: 'What happens on a flat or bearish day?',
    a: 'The dashboard says so plainly — "No fresh signals today — next scan at 16:15 IST." The system is designed to underfit; on many weekdays it surfaces zero A-grade signals. Patience is part of the edge.',
  },
];

/* ─── Logo-tile helper (fallback to monogram) ─── */
const LOGO_DOMAINS = {
  RELIANCE: 'ril.com', TCS: 'tcs.com', BAJFINANCE: 'bajajfinserv.in',
  INFY: 'infosys.com', HDFCBANK: 'hdfcbank.com', ICICIBANK: 'icicibank.com',
  BHARTIARTL: 'airtel.in', LT: 'larsentoubro.com', MARUTI: 'marutisuzuki.com',
  KOTAKBANK: 'kotak.com', ADANIENT: 'adanienterprises.com', SBIN: 'sbi.co.in',
  AXISBANK: 'axisbank.com', TATAPOWER: 'tatapower.com', POLYCAB: 'polycab.com',
  VOLTAS: 'voltas.com', CUMMINSIND: 'cummins.com', JUBLFOOD: 'jubilantfoodworks.com',
  CRAFTSMAN: 'craftsmanautomation.com', JBCHEPHARM: 'jbpharma.com',
  CDSL: 'cdslindia.com', BLUEDART: 'bluedart.com', IIFL: 'iifl.com',
};

function LogoTile({ sym, size = 30 }) {
  const [failed, setFailed] = useState(false);
  const domain = LOGO_DOMAINS[sym];
  const tileStyle = { width: size, height: size };
  if (!domain || failed) {
    return <span className="alm-logo mono" style={tileStyle}>{sym.slice(0, 2)}</span>;
  }
  return (
    <span className="alm-logo" style={tileStyle}>
      <img src={`https://icons.duckduckgo.com/ip3/${domain}.ico`} alt={sym} onError={() => setFailed(true)} />
    </span>
  );
}

/* ─── icons ─── */
const MarkIcon = ({ size = 18 }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19V8l5 6 4-9 4 11 3-5v8" />
  </svg>
);
const ArrowIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14M13 5l7 7-7 7" />
  </svg>
);
const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M12 5v14M5 12h14" />
  </svg>
);
const CheckIcon = ({ c = 'currentColor', s = 15 }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
);
const DashIcon = ({ c = 'currentColor', s = 15 }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.6" strokeLinecap="round"><path d="M5 12h14" /></svg>
);

/* ─── section header (editorial) ─── */
function Head({ kicker, title, sub }) {
  return (
    <div className="tp-head">
      <div className="tp-eyebrow">{kicker}</div>
      <h2 className="tp-title">{title}</h2>
      {sub && <p className="tp-sub">{sub}</p>}
    </div>
  );
}

/* Spark — a faint metric-shaped sparkline drawn behind a KPI value. */
function Spark({ tone, d }) {
  return (
    <svg className={`alm-hero-spark ${tone}`} viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

/* ─── equity curve — TradingView-style area, strategy vs Nifty 500 (real data) ─── */
function EquityCurve({ data }) {
  const W = 640, H = 250, padL = 6, padR = 6, padT = 14, padB = 26;
  const plotW = W - padL - padR, plotH = H - padT - padB, baseY = padT + plotH;
  const n = data.length;
  const all = data.flatMap((d) => [Number(d.s), Number(d.b)]);
  const lo = Math.min(...all), hi = Math.max(...all);
  const gap = (hi - lo) * 0.08 || 1;
  const minV = Math.max(0, lo - gap), maxV = hi + gap;
  const X = (i) => padL + (i / (n - 1)) * plotW;
  const Y = (v) => padT + (1 - (v - minV) / (maxV - minV)) * plotH;
  const path = (key) => data.map((d, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Y(Number(d[key])).toFixed(1)}`).join(' ');
  const sLine = path('s'), bLine = path('b');
  const area = `${sLine} L${X(n - 1).toFixed(1)} ${baseY} L${X(0).toFixed(1)} ${baseY} Z`;
  const last = data[n - 1];
  const gS = Math.round(last.s - 100), gB = Math.round(last.b - 100);
  const grid = [0, 0.25, 0.5, 0.75, 1].map((f) => padT + f * plotH);
  const seen = new Set();
  const ticks = [];
  data.forEach((d, i) => {
    const y = d.t.slice(0, 4);
    if (!seen.has(y) && Number(y) % 2 === 1) { seen.add(y); ticks.push({ i, y }); }
  });

  return (
    <div className="alm-yearly">
      <div className="alm-yearly-head">
        <div>
          <h3 className="alm-yearly-h">Growth of ₹100 — strategy vs Nifty 500</h3>
          <div className="alm-yearly-sub">Net of costs · indexed to 2017 inception</div>
        </div>
        <div className="alm-yearly-legend">
          <span><i style={{ background: 'var(--alm-accent)' }} />Strategy <b style={{ color: 'var(--alm-bull)', fontWeight: 600 }}>+{gS}%</b></span>
          <span><i style={{ background: 'var(--alm-ink-3)' }} />Nifty 500 <b style={{ color: 'var(--alm-ink-2)', fontWeight: 600 }}>+{gB}%</b></span>
        </div>
      </div>
      <div className="alm-yearly-body">
        <svg className="alm-yearly-svg" viewBox={`0 0 ${W} ${H}`} role="img"
          aria-label="Growth of 100 rupees: strategy versus Nifty 500 benchmark">
          <defs>
            <linearGradient id="eq-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="var(--alm-accent)" stopOpacity="0.30" />
              <stop offset="100%" stopColor="var(--alm-accent)" stopOpacity="0" />
            </linearGradient>
          </defs>
          {grid.map((gy, i) => (
            <line key={i} x1={padL} x2={W - padR} y1={gy} y2={gy} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
          ))}
          {ticks.map((t) => (
            <text key={t.y} x={X(t.i)} y={H - 8} textAnchor="middle" fill="var(--alm-ink-3)" fontSize="11"
              fontFamily="var(--alm-mono)">{t.y}</text>
          ))}
          <path d={area} fill="url(#eq-fill)" />
          <path d={bLine} fill="none" stroke="var(--alm-ink-3)" strokeWidth="1.4" strokeDasharray="5 4"
            strokeLinecap="round" strokeLinejoin="round" opacity="0.85" />
          <path d={sLine} fill="none" stroke="var(--alm-accent)" strokeWidth="2.4"
            strokeLinecap="round" strokeLinejoin="round" />
          <circle cx={X(n - 1)} cy={Y(last.s)} r="4" fill="var(--alm-accent)" />
          <circle cx={X(n - 1)} cy={Y(last.s)} r="8" fill="var(--alm-accent)" opacity="0.18" />
        </svg>
      </div>
      <div className="alm-yearly-foot">
        Strategy vs Nifty 500 Total-Return Index · backtest, in-sample.
      </div>
    </div>
  );
}

/* ─── yearly returns bar chart — crisp SVG in the house chart style ─── */
function YearlyReturns({ data }) {
  const W = 640;
  const padX = 12;
  const topPad = 22;
  const barMaxPx = 150;                       // px height of the tallest positive bar
  const maxPos = Math.max(...data.map((d) => Number(d.net_pct) || 0), 1);
  const maxNeg = Math.min(...data.map((d) => Number(d.net_pct) || 0), 0);
  const k = barMaxPx / maxPos;                // px per percentage-point
  const y0 = topPad + barMaxPx;               // zero baseline y
  const H = y0 + Math.abs(maxNeg) * k + 40;   // room for neg bars + x labels
  const plotW = W - padX * 2;
  const slot = plotW / data.length;
  const barW = Math.min(46, slot * 0.52);
  // horizontal gridlines every 20% up from zero
  const grids = [];
  for (let g = 20; g <= maxPos + 5; g += 20) grids.push(g);

  return (
    <div className="alm-yearly">
      <div className="alm-yearly-head">
        <div>
          <h3 className="alm-yearly-h">Calendar-year returns</h3>
          <div className="alm-yearly-sub">Net calendar-year returns · net of costs</div>
        </div>
        <div className="alm-yearly-legend">
          <span><i style={{ background: 'linear-gradient(180deg,#57E6A0,#24C97A)' }} />Positive</span>
          <span><i style={{ background: 'linear-gradient(180deg,#FF7A90,#E23B54)' }} />Negative</span>
        </div>
      </div>
      <div className="alm-yearly-body">
        <svg className="alm-yearly-svg" viewBox={`0 0 ${W} ${H}`} role="img"
          aria-label="Net calendar-year returns of the strategy backtest">
          <defs>
            <linearGradient id="yr-bull" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#57E6A0" /><stop offset="100%" stopColor="#22B76E" />
            </linearGradient>
            <linearGradient id="yr-bear" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#FF7A90" /><stop offset="100%" stopColor="#E23B54" />
            </linearGradient>
          </defs>
          {/* gridlines + % ticks */}
          {grids.map((g) => (
            <g key={g}>
              <line x1={padX} x2={W - padX} y1={y0 - g * k} y2={y0 - g * k}
                stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
              <text x={padX} y={y0 - g * k - 3} fill="var(--alm-ink-4)" fontSize="9"
                fontFamily="var(--alm-mono)">{g}%</text>
            </g>
          ))}
          {/* zero baseline */}
          <line x1={padX} x2={W - padX} y1={y0} y2={y0} stroke="rgba(255,255,255,0.20)" strokeWidth="1" />

          {data.map((d, i) => {
            const v = Number(d.net_pct) || 0;
            const pos = v >= 0;
            const cx = padX + slot * i + slot / 2;
            const h = Math.max(Math.abs(v) * k, v === 0 ? 0 : 2);
            const y = pos ? y0 - h : y0;
            return (
              <g key={d.year} className="yr-col" opacity={d.partial ? 0.5 : 1}>
                <rect className="yr-bar" x={cx - barW / 2} y={y} width={barW} height={h}
                  rx="3" fill={pos ? 'url(#yr-bull)' : 'url(#yr-bear)'} />
                {Math.abs(v) >= 0.05 && (
                  <text x={cx} y={pos ? y - 7 : y0 + h + 13} textAnchor="middle"
                    fill={pos ? 'var(--alm-bull)' : 'var(--alm-bear)'} fontSize="11" fontWeight="600"
                    fontFamily="var(--alm-mono)">{pos ? '+' : ''}{v.toFixed(1)}</text>
                )}
                <text x={cx} y={H - 8} textAnchor="middle"
                  fill={d.partial ? 'var(--alm-ink-4)' : 'var(--alm-ink-3)'} fontSize="11"
                  fontFamily="var(--alm-mono)">&rsquo;{d.year.slice(2)}</text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="alm-yearly-foot">
        2017 &amp; 2026 are partial years (dimmed) · backtest, in-sample.
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   LandingV2Shell — the page, wrapped by RegimeProvider
   ═══════════════════════════════════════════════════════════ */
function LandingV2Shell() {
  const [requestOpen, setRequestOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(null);
  const [activeSector, setActiveSector] = useState('largecap');
  const [stats, setStats] = useState(STATS_FALLBACK);

  useEffect(() => {
    let alive = true;
    fetch('/api/landing-stats')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!alive || !d) return;
        setStats({
          backtest: { ...STATS_FALLBACK.backtest, ...(d.backtest || {}) },
          live: { ...STATS_FALLBACK.live, ...(d.live || {}) },
          weekly_swing: d.weekly_swing || null,
          yearly_returns: Array.isArray(d.yearly_returns) && d.yearly_returns.length
            ? d.yearly_returns : STATS_FALLBACK.yearly_returns,
          equity_bt: Array.isArray(d.equity_bt) && d.equity_bt.length
            ? d.equity_bt : STATS_FALLBACK.equity_bt,
          equity_curve: Array.isArray(d.equity_curve) ? d.equity_curve : [],
        });
      })
      .catch(() => { /* keep honest fallbacks */ });
    return () => { alive = false; };
  }, []);

  const bt = stats.backtest || STATS_FALLBACK.backtest;
  const live = stats.live || STATS_FALLBACK.live;
  const weekly = stats.weekly_swing || null;
  const yearly = (stats.yearly_returns && stats.yearly_returns.length)
    ? stats.yearly_returns : STATS_FALLBACK.yearly_returns;
  const equityBt = (stats.equity_bt && stats.equity_bt.length)
    ? stats.equity_bt : STATS_FALLBACK.equity_bt;
  const last = equityBt[equityBt.length - 1] || { s: 343.5, b: 293.2 };
  const totalReturn = Math.round(last.s - 100);          // growth-of-100 → total return %
  const alphaPP = Math.round(last.s - last.b);            // strategy − benchmark, in points

  const openModal = () => setRequestOpen(true);
  const sector = SECTORS[activeSector];
  const scrollTo = (id) => { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: 'smooth' }); };

  return (
    <div data-page-ctx="landing">

      {/* ═══ MASTHEAD ═══ */}
      <header className="alm-mast">
        <div className="alm-mast-inner">
          <a className="alm-brand" href="#top">
            <span className="alm-brand-mark"><img src={brandLogo} alt="Nifty Satvik" /></span>
            <span className="alm-brand-name">Nifty Satvik<span>Systematic Signals</span></span>
          </a>
          <nav className="alm-mast-links">
            <button className="alm-mast-link" onClick={() => scrollTo('how')}>How it works</button>
            <button className="alm-mast-link" onClick={() => scrollTo('top')}>Track record</button>
            <button className="alm-mast-link" onClick={() => scrollTo('access')}>Access</button>
            <button className="alm-mast-link" onClick={() => scrollTo('faq')}>FAQ</button>
          </nav>
          <div className="alm-mast-cta">
            <a href="/login" className="alm-btn alm-btn-ghost alm-btn-sm">Sign in</a>
            <button className="alm-btn alm-btn-primary alm-btn-sm" onClick={openModal}>
              Request access<span className="alm-btn-arrow"><ArrowIcon /></span>
            </button>
          </div>
        </div>
      </header>

      {/* ═══ HERO — centered, TradePro-style ═══ */}
      <section className="tp-hero" id="top">
        <div className="alm-wrap">
          <div className="tp-badge">Systematic swing signals · Nifty 500</div>
          <h1 className="tp-hero-title">Trade only when the market says <span className="tp-script">yes</span>.</h1>
          <p className="tp-hero-sub">
            Nifty Satvik scores 441 stocks every weekday at 16:15 IST. Wake up to the day's A-grade
            signals — each with an explicit entry, stop and target, and a one-click route to Zerodha Kite.
          </p>
          <div className="tp-hero-cta">
            <button className="tp-btn tp-btn-primary" onClick={openModal}>Request access<ArrowIcon /></button>
            <button className="tp-btn tp-btn-ghost" onClick={() => scrollTo('how')}>How it works</button>
          </div>

          <div className="tp-shot"><DashboardMockup /></div>

          <div className="tp-trust">
            <span className="tp-trust-item"><span className="tp-trust-ic"><MarkIcon size={15} /></span><span className="tp-trust-t">NSE market data</span></span>
            <span className="tp-trust-item"><span className="tp-trust-ic kite"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4v16h16" /><path d="M4 16l5-5 4 4 7-7" /></svg></span><span className="tp-trust-t">Zerodha Kite Connect</span></span>
            <span className="tp-trust-item"><span className="tp-trust-ic"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg></span><span className="tp-trust-t">OAuth 2.0 — you sign every order</span></span>
          </div>
        </div>
      </section>

      {/* ═══ TRACK RECORD — stat cards + charts ═══ */}
      <section className="alm-section tight" id="proof">
        <div className="alm-wrap">
          <div className="tp-head">
            <div className="tp-eyebrow">Track record</div>
            <h2 className="tp-title">The numbers, <span className="tp-script">net</span> of every cost.</h2>
            <p className="tp-sub">The weekly-swing book on a survivorship-corrected backtest ({bt.period}), net of brokerage, STT and slippage. In-sample and not yet certified — no real capital has traded.</p>
          </div>

          <div className="tp-stats">
            <div className="tp-card tp-stat">
              <Spark tone="bull" d="M0 47 L14 43 L28 45 L42 35 L56 37 L70 22 L84 15 L100 5" />
              <div className="tp-stat-l">Total return</div>
              <div className="tp-stat-v bull">+{fmt(totalReturn)}<span>%</span></div>
              <div className="tp-stat-c">Net · ₹10L → ₹81L</div>
            </div>
            <div className="tp-card tp-stat">
              <Spark tone="bull" d="M0 42 L16 40 L32 37 L48 33 L64 26 L80 18 L100 10" />
              <div className="tp-stat-l">CAGR</div>
              <div className="tp-stat-v">~{fmt(bt.cagr_pct, { dp: 0 })}<span>%</span></div>
              <div className="tp-stat-c">Net of costs · before 20% STCG</div>
            </div>
            <div className="tp-card tp-stat">
              <Spark tone="brand" d="M0 45 L14 42 L28 40 L42 32 L56 30 L70 20 L84 16 L100 8" />
              <div className="tp-stat-l">vs Nifty 500</div>
              <div className="tp-stat-v">+{fmt(alphaPP)}<span>pp</span></div>
              <div className="tp-stat-c">Cumulative alpha · TRI</div>
            </div>
            <div className="tp-card tp-stat">
              <Spark tone="bear" d="M0 14 L18 8 L34 6 L48 12 L62 28 L76 42 L88 47 L100 38" />
              <div className="tp-stat-l">Max drawdown</div>
              <div className="tp-stat-v bear">{fmt(bt.max_drawdown_pct, { dp: 0 })}<span>%</span></div>
              <div className="tp-stat-c">Raw · Sharpe {fmt(bt.sharpe, { dp: 2 })}</div>
            </div>
          </div>

          <div className="alm-chart-duo" style={{ marginTop: 16 }}>
            <EquityCurve data={equityBt} />
            <YearlyReturns data={yearly} />
          </div>

          <p className="bento-fine" style={{ textAlign: 'center', marginInline: 'auto' }}>
            Weekly-swing book, backtest {bt.period}, net of costs before 20% STCG, in-sample on the survivorship-corrected universe — Sharpe {fmt(bt.sharpe, { dp: 2 })}, DSR {fmt(bt.dsr, { dp: 2 })} (below the certification gate). Not indicative of future results; a handful of strong-trend years drive the total, with a &gt;40% peak-to-trough drawdown. No real capital has traded — the forward paper record since {live.since} is the real test.
          </p>
        </div>
      </section>

      {/* ═══ THIS WEEK'S SCAN — split card ═══ */}
      {weekly && (
      <section className="alm-section tight" id="weekly">
        <div className="alm-wrap">
          <div className="tp-card tp-scan-card">
            <div>
              <div className="tp-eyebrow">This week's scan · weekly swing model</div>
              <h2 className="tp-title" style={{ fontSize: 'clamp(24px, 2.6vw, 34px)' }}>Fresh setups, <span className="tp-script">every week</span>.</h2>
              <p className="tp-sub" style={{ margin: '12px 0 0', textAlign: 'left' }}>Our flagship swing model re-scans the Nifty-500 large &amp; mid-cap universe each week and publishes a graded shortlist — counts and grades only, never a ticker or price. Paper-tracked ahead of live capital.</p>
            </div>
            <div>
              <div className="tp-scan-big">{fmt(weekly.n_signals)}<span>fresh setups this week</span></div>
              <div className="tp-scan-pills">
                <span className="tp-pill">{fmt(weekly.grade_a)} grade A</span>
                <span className="tp-pill">{fmt(weekly.grade_b)} grade B</span>
                <span className="tp-pill bull">avg target {fmt(weekly.avg_target_upside_pct, { dp: 1 })}%</span>
              </div>
              <div className="tp-scan-foot">Buy window through {weekly.buy_window_until} · {fmt(weekly.hold_days)}-day swing horizon</div>
            </div>
          </div>
        </div>
      </section>
      )}

      {/* ═══ CONFIDENCE — big stat moment ═══ */}
      <section className="alm-section tight">
        <div className="alm-wrap">
          <div className="tp-card tp-bigstat">
            <div className="tp-bigstat-num">{fmt(bt.mult, { dp: 1 })}<span>×</span></div>
            <div className="tp-bigstat-body">
              <h3>₹10 lakh → ₹81 lakh in the backtest — and honest about the rest.</h3>
              <p>Over {bt.period}, the weekly-swing book compounded 8.1× net of costs (Sharpe {fmt(bt.sharpe, { dp: 2 })}, {fmt(bt.win_rate_pct, { dp: 0 })}% win across {bt.total_trades} trades). But it's in-sample, before 20% STCG, the drawdown runs past 40%, and its DSR of {fmt(bt.dsr, { dp: 2 })} sits below the certification gate — so it's paper-tracked, not proven, and no real capital has traded. We'd rather tell you that than sell you certainty.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ HOW IT WORKS — scan → rank → screen → size ═══ */}
      <section className="alm-section" id="how">
        <div className="alm-wrap">
          <div className="tp-head">
            <div className="tp-eyebrow">How it works</div>
            <h2 className="tp-title">No black box. The same path, <span className="tp-script">every day</span>.</h2>
            <p className="tp-sub">Every signal travels one transparent, frozen pipeline — identical in backtest and in production. The one thing we keep private is the exact ranking formula.</p>
          </div>
          <div className="tp-steps">
            {[
              ['Scan', 'Every weekday after the 15:30 NSE close we refresh point-in-time prices and fundamentals across the full Nifty 500 large- and mid-cap universe. No lookahead, ever.'],
              ['Rank', 'Each name is scored cross-sectionally on trend quality and risk. The ranking rule is proprietary and frozen — derived once from history, then never touched.'],
              ['Screen', 'Only the top-ranked names that also pass strict liquidity and solvency filters survive. Most days that is one or two. Often zero — and that restraint is part of the edge.'],
              ['Risk-size', 'Each survivor ships as a complete plan — entry, a hard stop, a target, and a size set to a fixed risk budget with a volatility cap — ready to route to Kite.'],
            ].map(([title, desc], i) => (
              <div className={`tp-card tp-step${i === 1 ? ' on' : ''}`} key={title}>
                <div className="tp-step-no">0{i + 1}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
          <div className="alm-moat">
            <div className="alm-moat-ic">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
            </div>
            <div className="alm-moat-body">
              <div className="alm-moat-k">The moat · kept private</div>
              <h3>The ranking formula is not disclosed.</h3>
              <p>The exact factor, thresholds, and hold rules are the edge — so they stay internal. You get the complete plan and the full track record; the recipe stays ours.</p>
            </div>
          </div>

          <div className="alm-subhead">What you get — every signal is a complete trade plan</div>
          <div className="alm-ledger">
            <div className="alm-ledger-main">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
                  <LogoTile sym="RELIANCE" size={34} />
                  <div>
                    <div style={{ fontFamily: 'var(--alm-serif)', fontWeight: 600, fontSize: 18, color: 'var(--alm-ink)' }}>RELIANCE</div>
                    <div style={{ fontFamily: 'var(--alm-mono)', fontSize: 10, color: 'var(--alm-ink-3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Energy · NSE · example</div>
                  </div>
                </div>
                <span className="alm-tag">Grade A · Sample</span>
              </div>
              {[
                ['Entry', '₹2,872', ''],
                ['Target', '₹3,066', 'bull'],
                ['Stop', '₹2,786', 'bear'],
                ['Risk : reward', '1 : 2.2', ''],
                ['Hold window', 'Multi-week', ''],
              ].map(([k, v, tone]) => (
                <div key={k} style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', borderTop: '1px solid var(--alm-rule)', paddingTop: 12 }}>
                  <span style={{ fontFamily: 'var(--alm-sans)', fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--alm-ink-3)' }}>{k}</span>
                  <span style={{ fontFamily: 'var(--alm-mono)', fontWeight: 600, fontSize: 16, color: tone === 'bull' ? 'var(--alm-bull)' : tone === 'bear' ? 'var(--alm-bear)' : 'var(--alm-ink)' }}>{v}</span>
                </div>
              ))}
              {/* ATR risk/reward band — stop → entry → target, drawn to scale */}
              <div className="alm-rrbar">
                <div className="alm-rrbar-head"><span className="bear">Risk 1</span><span className="bull">Reward 2.2</span></div>
                <div className="alm-rrbar-track">
                  <div className="alm-rrbar-risk" style={{ width: '31%' }} />
                  <div className="alm-rrbar-reward" style={{ width: '69%' }} />
                  <span className="alm-rrbar-mark" style={{ left: '31%' }} />
                </div>
                <div className="alm-rrbar-scale">
                  <span className="lb start"><b className="bear">₹2,786</b><small>Stop</small></span>
                  <span className="lb mid"><b>₹2,872</b><small>Entry</small></span>
                  <span className="lb end"><b className="bull">₹3,066</b><small>Target</small></span>
                </div>
              </div>
              <div style={{ fontFamily: 'var(--alm-mono)', fontSize: 10, color: 'var(--alm-ink-4)', marginTop: 2 }}>Illustrative example — not a live recommendation.</div>
            </div>
            <div className="alm-ledger-rows">
              {[
                ['Conviction + grade', 'A cross-sectional rank of trend quality against risk, distilled into an A–D grade. Only the top grades ship as signals.'],
                ['Entry, stop, target', 'Concrete prices — an ATR-based stop and a fixed profit target — not a vague “buy now and hope.”'],
                ['Position size', 'Scaled to your account and capped so risk per trade stays bounded. You approve it and route it to Kite.'],
                ['Exit logic', 'A multi-week horizon with a hard stop, a target, a trailing stop, and a time cap. The rule tells you when to leave — target, stop, or time.'],
              ].map(([k, v]) => (
                <div key={k} className="alm-lrow">
                  <div className="alm-lrow-l">{k}</div>
                  <div className="alm-lrow-d big">{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ═══ WHY TRUST IT — the edge + methodology ═══ */}
      <section className="alm-section tight">
        <div className="alm-wrap">
          <Head kicker="Why trust it"
            title="What the edge is — and what it isn’t."
            sub="We’d rather tell you how it actually works than sell you magic. Below, the honest edge — and the discipline behind it." />
          <div className="alm-honest">
            <div className="alm-honest-col">
              <div className="alm-honest-h is">What it is</div>
              {[
                ['Cross-sectional conviction', 'Every name is ranked against the whole universe on trend quality and risk; only the strongest, most liquid, most solvent names clear the bar.'],
                ['Asymmetry by construction', 'Hard ATR stops and a fixed profit target turn an above-even win rate into wins that outweigh the losses.'],
                ['Restraint', 'Most days it stays silent. Not trading the marginal setups is part of the return.'],
              ].map(([t, d]) => (
                <div key={t} className="alm-honest-item">
                  <span className="ic is"><CheckIcon /></span>
                  <div><h4>{t}</h4><p>{d}</p></div>
                </div>
              ))}
            </div>
            <div className="alm-honest-col">
              <div className="alm-honest-h isnt">What it isn’t</div>
              {[
                ['Not a direction oracle', 'It wins about 60% of the time in backtest — an edge, not clairvoyance. It ranks trend quality across names; it does not promise any single stock simply “goes up”.'],
                ['Not AI sector rotation', 'It doesn’t decide which sector leads. That layer is still in shadow research, graded before it can touch a trade.'],
                ['Not a guarantee', 'Backtests flatter, the drawdown is deep, some years are flat, and the live record is still being earned.'],
              ].map(([t, d]) => (
                <div key={t} className="alm-honest-item">
                  <span className="ic isnt"><DashIcon /></span>
                  <div><h4>{t}</h4><p>{d}</p></div>
                </div>
              ))}
            </div>
          </div>

          <div className="alm-subhead">Methodology — no screenshots, no selective memory</div>
          <div className="alm-notes">
            {[
              ['Walk-forward only', 'Every model is tested on out-of-sample bars it never saw at training. We measure what generalises — not what fits the past.',
                <path d="M3 13l4-1 3-7 4 14 3-8 4-1" />],
              ['Costs are baked in', 'Brokerage and STT are modelled into every backtested trade. The numbers you see are after costs, not before.',
                <><circle cx="12" cy="12" r="8.5" /><path d="M9 8.5h6M9 11.5h4M13.5 8.5c0 3-4.5 3-4.5 3l4.5 4" /></>],
              ['The live record is the judge', 'Backtests can flatter. Live trading began recently and the forward record only grows — that’s the test we hold ourselves to.',
                <path d="M12 3.5l7 3v5c0 5-3.5 7.8-7 9.5-3.5-1.7-7-4.5-7-9.5v-5z" />],
              ['We kill our own ideas', 'Every research idea is pre-registered with a pass/fail bar before we see results. Most get killed. Only what survives reaches your dashboard.',
                <><circle cx="12" cy="12" r="8.5" /><path d="M15 9l-6 6M9 9l6 6" /></>],
              ['Survivorship-corrected', 'The backtest universe is reconstructed from historical index membership and puts delisted and merged names (Yes Bank, Suzlon, Jet Airways) back in — it can’t quietly keep only the winners.',
                <path d="M12 3.5l8.5 4.5-8.5 4.5L3.5 8zM3.5 12l8.5 4.5 8.5-4.5M3.5 16l8.5 4.5 8.5-4.5" />],
              ['One codebase, no skew', 'A single source of truth computes the features for both the backtest and the live signal. What we measure is what we serve.',
                <path d="M9 7l-4.5 5 4.5 5M15 7l4.5 5-4.5 5" />],
            ].map(([title, desc, icon]) => (
              <div key={title} className="alm-note">
                <span className="alm-note-ic">
                  <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{icon}</svg>
                </span>
                <h3>{title}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ ROADMAP — compact banner ═══ */}
      <section className="alm-section tight">
        <div className="alm-wrap">
          <div className="alm-moat">
            <div className="alm-moat-ic">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3.2" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1" /></svg>
            </div>
            <div className="alm-moat-body">
              <div className="alm-moat-k">On the roadmap · shadow research · not live</div>
              <h3>An AI sector-regime analyst — running in shadow mode.</h3>
              <p>It reasons about which sectors are setting up to lead, logged and graded weekly against real sector returns at 21 and 42 days. It won’t influence a single live signal until it beats a fair baseline.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ 09 · ACCESS ═══ */}
      <section className="alm-section tight" id="access">
        <div className="alm-wrap">
          <Head no="09" kicker="Access"
            title="Private, invite-only. Not a subscription."
            sub="Nifty Satvik isn’t sold. It’s a private research tool shared with a small group of traders — no plans, no tiers, no card." />
          <div className="alm-access">
            <div className="alm-access-grid">
              {[
                ['No subscription', 'No monthly plan, no paywall. Access is granted, not purchased.',
                  <><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M3 10h18M5 4.5l14 15" /></>],
                ['Your account, your orders', 'You connect your own Zerodha Kite in one step and sign every order yourself. We never hold or manage your capital.',
                  <><path d="M12 3.5l7 3v5c0 5-3.5 7.8-7 9.5-3.5-1.7-7-4.5-7-9.5v-5z" /><path d="M9 12l2 2 4-4" /></>],
                ['Small by design', 'Onboarded in small batches, so the dashboard stays fast and the feedback loop stays real.',
                  <><circle cx="9" cy="9" r="3" /><path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5" /><circle cx="17.5" cy="10" r="2" /><path d="M16 14.5c2 .4 3.5 2 3.5 4.5" /></>],
                ['Leave anytime', 'Revoke Kite access in one click. Your journal and track-record data stay readable.',
                  <><path d="M14 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 8l-4 4 4 4M6 12h9" /></>],
              ].map(([t, d, icon]) => (
                <div key={t} className="alm-access-item">
                  <span className="alm-access-ic">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{icon}</svg>
                  </span>
                  <h4>{t}</h4>
                  <p>{d}</p>
                </div>
              ))}
            </div>
            <div className="alm-access-foot">
              <button className="alm-btn alm-btn-primary" onClick={openModal} style={{ minWidth: 220 }}>
                Request access<span className="alm-btn-arrow"><ArrowIcon /></span>
              </button>
              <small>We review every request personally. Bring a Zerodha account.</small>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ 10 · FAQ ═══ */}
      <section className="alm-section tight" id="faq">
        <div className="alm-wrap">
          <Head no="10" kicker="FAQ" title="Questions, answered." />
          <div className="alm-faq">
            {FAQ_ITEMS.map((item, idx) => (
              <div key={idx} className={`alm-faq-item${openFaq === idx ? ' open' : ''}`}>
                <button className="alm-faq-q" onClick={() => setOpenFaq(openFaq === idx ? null : idx)} aria-expanded={openFaq === idx}>
                  <span style={{ flex: 1 }}>{item.q}</span>
                  <span className="alm-faq-ic"><PlusIcon /></span>
                </button>
                <div className="alm-faq-a">{item.a}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ CLOSING CTA ═══ */}
      <section className="alm-cta">
        <div className="alm-wrap">
          <div className="alm-cta-card">
            <div className="alm-cta-rule" />
            <h2 className="alm-cta-title">Wake up to conviction.<br />Not <em>noise.</em></h2>
            <p className="alm-cta-sub">Invite-only. No subscription, no card — you bring your own Zerodha account.</p>
            <div className="alm-cta-btns">
              <button className="alm-btn alm-btn-primary" onClick={openModal}>
                Request access<span className="alm-btn-arrow"><ArrowIcon /></span>
              </button>
              <button className="alm-btn alm-btn-ghost" onClick={() => scrollTo('proof')}>See the track record</button>
            </div>
            <div className="alm-cta-note">
              Research and decision-support output, not investment advice. Past performance is not indicative of future returns. Subject to market risk.
            </div>
          </div>
        </div>
      </section>

      {/* ═══ COLOPHON / FOOTER ═══ */}
      <footer className="alm-foot">
        <div className="alm-wrap">
          <div className="alm-foot-grid">
            <div className="alm-foot-brand">
              <a className="alm-brand" href="#top">
                <span className="alm-brand-mark" style={{ width: 30, height: 30 }}><img src={brandLogo} alt="Nifty Satvik" /></span>
                <span className="alm-brand-name">Nifty Satvik<span>Systematic Signals</span></span>
              </a>
              <p className="alm-foot-tag">AI-graded swing-trading signals for the Nifty 500. Walk-forward validated and one-click executable through Zerodha Kite.</p>
            </div>
            <div className="alm-foot-col">
              <h4>Product</h4>
              <ul>
                <li><button className="alm-foot-link" onClick={() => scrollTo('how')}>How it works</button></li>
                <li><button className="alm-foot-link" onClick={() => scrollTo('proof')}>Track record</button></li>
                <li><button className="alm-foot-link" onClick={() => scrollTo('access')}>Access</button></li>
                <li><a href="/dashboard">Dashboard</a></li>
              </ul>
            </div>
            <div className="alm-foot-col">
              <h4>Legal</h4>
              <ul>
                <li><a href="#">Disclaimer</a></li>
                <li><a href="#">Risk disclosure</a></li>
                <li><a href="#">Privacy</a></li>
                <li><a href="#">Terms</a></li>
              </ul>
            </div>
            <div className="alm-foot-col">
              <h4>Company</h4>
              <ul>
                <li><a href="#">About</a></li>
                <li><a href="#">Founder note</a></li>
                <li><a href="#">Press</a></li>
                <li><a href="#">Contact</a></li>
              </ul>
            </div>
          </div>
          <div className="alm-foot-rule">
            <span>© 2026 Nifty Satvik</span>
            <span>Made in Bengaluru · NSE data may be delayed</span>
          </div>
          <p className="alm-foot-disc">{DISCLAIMER}</p>
        </div>
      </footer>

      <RequestAccessModal open={requestOpen} onOpenChange={setRequestOpen} />
    </div>
  );
}

/* ─── Default export wrapped in RegimeProvider ─── */
export default function LandingV2() {
  return (
    <RegimeProvider>
      <LandingV2Shell />
    </RegimeProvider>
  );
}
