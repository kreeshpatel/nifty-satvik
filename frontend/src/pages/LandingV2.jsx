/**
 * LandingV2.jsx — NiftyQuant marketing landing page (React port of Landing.html artifact).
 *
 * Ported from: frontend/public/nifty-design/Landing.html
 * Styles:      frontend/src/styles/landing-v2.css (every selector scoped under
 *              [data-page-ctx="landing"] per CLAUDE.md CSS-scoping hard rule).
 *
 * Vanilla JS → React translations:
 *   - FAQ accordion   → useState(openFaq) single-open index
 *   - Sector tabs     → useState(activeSector) + SECTORS data map
 *   - All "Request access" CTAs → RequestAccessModal (real POST /api/access-requests)
 *
 * Compliance: no "guarantee / will / sure-shot" language.
 * Stats are static marketing figures — see NOTE comment below.
 */

import { useState } from 'react';
import { RegimeProvider } from '@/context/RegimeContext';
import RequestAccessModal from '@/components/landing/RequestAccessModal';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/landing-v2.css';

// NOTE: static marketing stats — wire to a public /stats endpoint if one ships.
// Numbers below match the artifact as-is and are not pulled from live data.

/* ─── Sector tab data (mirrors SECTORS in Landing.html vanilla JS) ─── */
const SECTORS = {
  largecap: {
    key: 'largecap',
    label: 'Large-cap · Nifty 100',
    name: 'Nifty 100 · Large-cap universe',
    meta: 'Illustrative — the universe NiftyQuant scans daily',
    pct: '100 names',
    tone: '',
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
    meta: 'Illustrative — the universe NiftyQuant scans daily',
    pct: '150 names',
    tone: '',
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
    meta: 'Illustrative — the universe NiftyQuant scans daily',
    pct: '250 names',
    tone: '',
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
    meta: 'Illustrative — the universe NiftyQuant scans daily',
    pct: 'Bank Nifty',
    tone: '',
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
    q: 'Is NiftyQuant SEBI-registered?',
    a: 'No. NiftyQuant is not a SEBI-registered investment advisor or research analyst. We publish research and decision-support signals — not personalised investment advice — and we never manage your capital. Every order is placed by you, in your own Zerodha Kite account.',
  },
  {
    q: 'Do I need a Zerodha Kite account?',
    a: 'For one-click routing, yes — Kite Connect is the only execution venue we integrate with today. You can still use NiftyQuant without Kite — you\'ll just place orders manually in your own broker.',
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
    a: 'Nothing today. NiftyQuant is private and invite-only — not a paid subscription. You bring your own Zerodha account; we don\'t charge a fee or manage your money. Revoke access anytime — your journal and track-record data stay readable.',
  },
  {
    q: 'What happens on a flat or bearish day?',
    a: 'The dashboard says so plainly — "No fresh signals today — next scan at 16:15 IST." The system is designed to underfit; on average, ~3 of 5 weekdays produce zero A-grade signals. Patience is part of the edge.',
  },
];

/* ─── Tiny logo-tile helper (fallback to monogram) ─── */
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
  const r = Math.round(size * 0.28);
  const tileStyle = { width: size, height: size, borderRadius: r };

  if (!domain || failed) {
    return (
      <span className="lv2-logo-tile mono" style={tileStyle}>
        {sym.slice(0, 2)}
      </span>
    );
  }
  return (
    <span className="lv2-logo-tile" style={tileStyle}>
      <img
        src={`https://icons.duckduckgo.com/ip3/${domain}.ico`}
        alt={sym}
        onError={() => setFailed(true)}
      />
    </span>
  );
}

/* ─── NavIcon SVG ─── */
const ChartIcon = ({ size = 18 }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19V8l5 6 4-9 4 11 3-5v8" />
  </svg>
);

const ArrowIcon = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 17 17 7" /><path d="M7 7h10v10" />
  </svg>
);

const PlayIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="6 4 20 12 6 20 6 4" />
  </svg>
);

const PlusIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
    <path d="M12 5v14M5 12h14" />
  </svg>
);

/* ─── Section Eyebrow ─── */
function SectionEyebrow({ children }) {
  return <div className="lv2-section-eyebrow">{children}</div>;
}

/* ═══════════════════════════════════════════════════════════
   LandingV2Shell — the actual page, wrapped by RegimeProvider
   ═══════════════════════════════════════════════════════════ */
function LandingV2Shell() {
  const [requestOpen, setRequestOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(null);      // single-open FAQ index
  const [activeSector, setActiveSector] = useState('largecap');

  const openModal = () => setRequestOpen(true);

  const sector = SECTORS[activeSector];

  function scrollTo(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }

  return (
    <div data-page-ctx="landing">

      {/* ─── NAV ─── */}
      <nav className="lv2-nav">
        <a className="lv2-nav-brand" href="#top">
          <div className="lv2-nav-mark">
            <ChartIcon size={18} />
          </div>
          <span className="lv2-nav-text">NiftyQuant</span>
        </a>
        <div className="lv2-nav-links">
          <button className="lv2-nav-link" onClick={() => scrollTo('how')}>How it works</button>
          <button className="lv2-nav-link" onClick={() => scrollTo('proof')}>Track record</button>
          <button className="lv2-nav-link" onClick={() => scrollTo('access')}>Access</button>
          <button className="lv2-nav-link" onClick={() => scrollTo('faq')}>FAQ</button>
        </div>
        <div className="lv2-nav-cta">
          <a href="/login" className="lv2-btn lv2-btn-ghost" style={{ height: 36, fontSize: 13 }}>
            Sign in
          </a>
          <button className="lv2-btn lv2-btn-primary" onClick={openModal} style={{ height: 36, fontSize: 13 }}>
            Request access
            <span className="lv2-btn-arrow"><ArrowIcon /></span>
          </button>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section className="lv2-hero" id="top">
        <div className="lv2-hero-grid" />
        <div className="lv2-hero-glow" />
        <div className="lv2-wrap">
          <div className="lv2-hero-pill">
            <span className="lv2-badge">NEW</span>
            <span>Walk-forward validated · 14 years of NSE history · 441 stocks scanned daily</span>
          </div>

          <h1 className="lv2-hero-title">
            Trade only when the<br />
            market says <em>yes</em>.
          </h1>

          <p className="lv2-hero-sub">
            NiftyQuant scores all 441 stocks in the Nifty 500 every weekday at 16:15 IST.
            You wake up to the day's A-grade signals — often one, sometimes none — each with an explicit
            entry, stop, and target, and a one-click route to Zerodha Kite.
          </p>

          <div className="lv2-hero-cta">
            <button className="lv2-btn lv2-btn-primary" onClick={openModal}>
              See today's signals
              <span className="lv2-btn-arrow"><ArrowIcon /></span>
            </button>
            <button className="lv2-btn lv2-btn-ghost" onClick={() => scrollTo('how')}>
              <PlayIcon />
              Watch the 90-second tour
            </button>
          </div>

          <div className="lv2-hero-trust">
            <span>Walk-forward validated on 14 years of NSE data</span>
            <span className="lv2-sep" />
            <span>One-click Zerodha Kite routing · you sign every order</span>
          </div>

          {/* Stat band */}
          <div className="lv2-hero-stats">
            <div className="lv2-hero-stat">
              <div className="lv2-hero-stat-v">441</div>
              <div className="lv2-hero-stat-l">Stocks scored daily</div>
            </div>
            <div className="lv2-hero-stat">
              <div className="lv2-hero-stat-v">0.95</div>
              <div className="lv2-hero-stat-l">Mean Sharpe · walk-forward</div>
            </div>
            <div className="lv2-hero-stat">
              <div className="lv2-hero-stat-v">53<span>%</span></div>
              <div className="lv2-hero-stat-l">Win rate · out-of-sample</div>
            </div>
            <div className="lv2-hero-stat">
              <div className="lv2-hero-stat-v">0.92</div>
              <div className="lv2-hero-stat-l">Confidence gate to ship</div>
            </div>
          </div>
          <p style={{ fontSize: 11, color: 'var(--lv2-text-3)', marginTop: 14, maxWidth: 600 }}>
            10-fold walk-forward, out-of-sample, survivorship-corrected (2017–2026). Backtest, not live — returns varied widely year to year and were negative in 3 of the last 8.
          </p>
        </div>

        {/* Product bezel */}
        <div className="lv2-hero-product">
          <div className="lv2-hero-product-bezel">
            <div className="lv2-hero-product-bar">
              <span className="lv2-dot" /><span className="lv2-dot" /><span className="lv2-dot" />
              <span className="lv2-url">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2C20 17.5 12 22 12 22Z" /></svg>
                app.niftyquant.in / dashboard
              </span>
            </div>
            <div className="lv2-hero-product-img">
              <div className="lv2-mini-dash">
                {/* Top bar */}
                <div className="lv2-mini-dash-bar">
                  <div className="lv2-mini-dash-brand">
                    <div className="lv2-m"><ChartIcon size={13} /></div>
                    NiftyQuant
                  </div>
                  <div className="lv2-mini-dash-tabs">
                    {['Dashboard', 'Signals', 'Portfolio', 'Backtest'].map((t, i) => (
                      <span key={t} className={`lv2-mini-dash-tab${i === 0 ? ' on' : ''}`}>{t}</span>
                    ))}
                  </div>
                </div>
                {/* Sidebar */}
                <div className="lv2-mini-dash-side">
                  <div className="lv2-sec">Today</div>
                  <div className="lv2-item on"><span className="lv2-d" />Fresh signals · 3</div>
                  <div className="lv2-item"><span className="lv2-d" />Open positions · 7</div>
                  <div className="lv2-item"><span className="lv2-d" />Equity curve</div>
                  <div className="lv2-sec">Research</div>
                  <div className="lv2-item"><span className="lv2-d" />Backtest</div>
                  <div className="lv2-item"><span className="lv2-d" />Track record</div>
                  <div className="lv2-item"><span className="lv2-d" />Journal</div>
                </div>
                {/* Main */}
                <div className="lv2-mini-dash-main">
                  <div className="lv2-mini-dash-regime">
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--lv2-bull)', boxShadow: '0 0 8px var(--lv2-bull)', flexShrink: 0 }} />
                    The market is <em>Bullish</em> · NIFTY +0.68% · Breadth 75
                  </div>
                  <div className="lv2-mini-cards">
                    <div className="lv2-mini-card fresh">
                      <div className="lv2-mini-card-eyebrow">FRESH · GRADE A</div>
                      <div className="lv2-mini-card-head">
                        <LogoTile sym="RELIANCE" size={22} />
                        <div className="lv2-mini-card-name">RELIANCE</div>
                      </div>
                      <div className="lv2-mini-card-vals">
                        <span className="lv2-mini-card-price">₹2,948.20</span>
                        <span className="lv2-mini-card-pct bull">+2.18%</span>
                      </div>
                    </div>
                    <div className="lv2-mini-card fresh">
                      <div className="lv2-mini-card-eyebrow">FRESH · GRADE A−</div>
                      <div className="lv2-mini-card-head">
                        <LogoTile sym="TCS" size={22} />
                        <div className="lv2-mini-card-name">TCS</div>
                      </div>
                      <div className="lv2-mini-card-vals">
                        <span className="lv2-mini-card-price">₹4,128.50</span>
                        <span className="lv2-mini-card-pct bull">+1.62%</span>
                      </div>
                    </div>
                  </div>
                  <div className="lv2-mini-chart">
                    <svg viewBox="0 0 320 90" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="lv2-mc-fill" x1="0" x2="0" y1="0" y2="1">
                          <stop offset="0%" stopColor="#4F8CFF" stopOpacity="0.42" />
                          <stop offset="100%" stopColor="#4F8CFF" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                      <path d="M0 70 L20 64 L40 66 L60 58 L80 52 L100 56 L120 44 L140 48 L160 38 L180 30 L200 36 L220 24 L240 18 L260 22 L280 14 L300 10 L320 6 L320 90 L0 90 Z" fill="url(#lv2-mc-fill)" />
                      <path d="M0 70 L20 64 L40 66 L60 58 L80 52 L100 56 L120 44 L140 48 L160 38 L180 30 L200 36 L220 24 L240 18 L260 22 L280 14 L300 10 L320 6"
                        fill="none" stroke="#4F8CFF" strokeWidth="2" strokeLinecap="round"
                        style={{ filter: 'drop-shadow(0 2px 6px rgba(79,140,255,0.45))' }} />
                      <circle cx="320" cy="6" r="3.2" fill="#fff" />
                      <circle cx="320" cy="6" r="8" fill="#fff" opacity="0.20" />
                    </svg>
                  </div>
                </div>
                {/* Right column */}
                <div className="lv2-mini-dash-right">
                  <div className="lv2-sec">Sector breadth</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                    {[['Banking', '72%', 'var(--lv2-bull)'], ['IT', '58%', 'var(--lv2-bull)'], ['Auto', '41%', 'var(--lv2-warn)'], ['Pharma', '64%', 'var(--lv2-bull)'], ['Energy', '36%', 'var(--lv2-bear)']].map(([label, val, color]) => (
                      <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{label}</span>
                        <span style={{ color, fontFamily: 'var(--lv2-font-mono)' }}>{val}</span>
                      </div>
                    ))}
                  </div>
                  <div className="lv2-mini-bal">
                    <div className="lv2-l">EQUITY · LTD</div>
                    <div className="lv2-v">₹52.43L</div>
                    <div className="lv2-l" style={{ marginTop: 4 }}>+8.4% MTD</div>
                    <button className="lv2-mini-bal-btn">Open trade desk</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── TRUST STRIP ─── */}
      <section className="lv2-trust">
        <div className="lv2-wrap">
          <div className="lv2-trust-label">DATA · EXECUTION · SECURITY</div>
          <div className="lv2-trust-row">
            <div className="lv2-trust-logo">
              <span className="lv2-trust-mono" style={{ color: '#F1F5FF' }}>NSE</span>
              <span className="lv2-trust-meta">EOD bars + intraday quotes</span>
            </div>
            <span className="lv2-trust-div" />
            <div className="lv2-trust-logo lv2-trust-kite">
              <span className="lv2-trust-kite-mark">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 4v16h16" /><path d="M4 16l5-5 4 4 7-7" />
                </svg>
              </span>
              <span className="lv2-trust-kite-text">
                Zerodha&nbsp;<span style={{ color: 'var(--lv2-text-3)', fontWeight: 400 }}>Kite Connect</span>
              </span>
            </div>
            <span className="lv2-trust-div" />
            <div className="lv2-trust-logo">
              <span className="lv2-trust-mono" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                OAuth 2.0
              </span>
              <span className="lv2-trust-meta">No password storage</span>
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS — sector tabs ─── */}
      <section className="lv2-section" id="how">
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>HOW IT WORKS</SectionEyebrow>
            <h2 className="lv2-section-title">Built for the way Indian swings actually trade.</h2>
            <p className="lv2-section-sub">
              A two-head LightGBM scores every Nifty 500 stock against 79 features —
              momentum, volatility, macro regime, sector strength, and cross-sectional relative strength. Only stocks that earn a place ship as signals.
            </p>
          </div>

          {/* Sector tabs (React state replaces vanilla classList) */}
          <div className="lv2-sectors-wrap">
            <div className="lv2-sectors-tabs">
              {SECTOR_KEYS.map((key) => (
                <button
                  key={key}
                  className={`lv2-sector-tab${activeSector === key ? ' on' : ''}`}
                  onClick={() => setActiveSector(key)}
                >
                  {SECTORS[key].label}
                </button>
              ))}
            </div>
          </div>

          <div className="lv2-sector-panel">
            <div className="lv2-sector-chart">
              <div className="lv2-sector-chart-head">
                <div>
                  <div className="lv2-sector-chart-h">{sector.name}</div>
                  <div className="lv2-sector-chart-meta">{sector.meta}</div>
                </div>
                <span className={`lv2-sector-chart-pct ${sector.tone}`}>{sector.pct}</span>
              </div>
              <svg className="lv2-sector-chart-svg" viewBox="0 0 600 280" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="lv2-sc-fill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#4F8CFF" stopOpacity="0.32" />
                    <stop offset="100%" stopColor="#4F8CFF" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <line x1="0" x2="600" y1="70"  y2="70"  stroke="rgba(255,255,255,0.05)" />
                <line x1="0" x2="600" y1="140" y2="140" stroke="rgba(255,255,255,0.05)" />
                <line x1="0" x2="600" y1="210" y2="210" stroke="rgba(255,255,255,0.05)" />
                {/* benchmark dashed */}
                <path d="M0 230 L60 224 L120 220 L180 214 L240 208 L300 202 L360 198 L420 192 L480 188 L540 184 L600 180"
                  fill="none" stroke="#7A82A5" strokeWidth="1.6" strokeDasharray="5 5" opacity="0.7" />
                <path d={sector.fillPath} fill="url(#lv2-sc-fill)" />
                <path d={sector.linePath}
                  fill="none" stroke="#4F8CFF" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"
                  style={{ filter: 'drop-shadow(0 4px 12px rgba(79,140,255,0.5))' }} />
                <circle cx={sector.endCx} cy={sector.endCy} r="5" fill="#4F8CFF" />
                <circle cx={sector.endCx} cy={sector.endCy} r="10" fill="#4F8CFF" opacity="0.20" />
                <text x="8" y="265" fontFamily="var(--lv2-font-mono)" fontSize="9" fill="#7A82A5">Illustrative — not a live curve</text>
              </svg>
            </div>

            <div className="lv2-sector-side">
              {sector.rows.map((row) => (
                <div key={row.sym} className="lv2-s-item">
                  <div className="lv2-item-l">
                    <LogoTile sym={row.sym} size={30} />
                    <div>
                      <div className="lv2-sym">{row.sym} <span className="lv2-name">· {row.name}</span></div>
                    </div>
                  </div>
                  <div>
                    <span className="lv2-price">{row.price}</span>
                    {' '}<span className={`lv2-chg ${row.tone}`}> {row.chg}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── PIPELINE (5 steps) ─── */}
      <section className="lv2-section" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>UNDER THE HOOD</SectionEyebrow>
            <h2 className="lv2-section-title">No black box. Five steps, every day.</h2>
            <p className="lv2-section-sub">
              Every signal travels the same path — and every step runs identically in
              backtest and in production. What we measure is what we serve.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 14 }}>
            {[
              ['Daily scan', 'Every weekday at 16:15 IST we pull EOD bars for all 441 tradeable Nifty 500 names, plus live macro and sector context.'],
              ['79 features', 'Each stock becomes 79 point-in-time features — momentum, volatility, macro regime, sector strength, relative-strength ranks. No lookahead.'],
              ['Two-head LightGBM', 'One head predicts the size of the move, the other its confidence. Trained on 14 years (2010–2024) and validated walk-forward.'],
              ['Confidence gate', 'Only names clearing a 0.92 confidence floor and the return bar survive. Most days that’s one or two. Often zero.'],
              ['Risk-sized plan', 'Each survivor ships with an ATR stop, an R:R-tuned target, and a volatility-scaled size — ready to route to Kite.'],
            ].map(([title, desc], i) => (
              <div
                key={title}
                style={{
                  background: 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%)',
                  border: '1px solid var(--lv2-edge-1)',
                  borderRadius: 16,
                  padding: 22,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                }}
              >
                <div style={{ fontFamily: 'var(--lv2-font-mono)', fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--lv2-brand-hi)', fontWeight: 600 }}>
                  {`0${i + 1}`}
                </div>
                <h3 style={{ fontFamily: 'var(--lv2-font-display)', fontSize: 17, fontWeight: 600, letterSpacing: '-0.018em', margin: 0, color: 'var(--lv2-text-1)' }}>
                  {title}
                </h3>
                <p style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--lv2-text-2)', margin: 0 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CAPABILITIES / FEATURES ─── */}
      <section className="lv2-section" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>CAPABILITIES</SectionEyebrow>
            <h2 className="lv2-section-title">Conviction, proof, execution.</h2>
            <p className="lv2-section-sub">Three things in that order. Everything else is noise.</p>
          </div>

          <div className="lv2-features">
            {/* 01 — CONVICTION */}
            <div className="lv2-feature">
              <div className="lv2-num">01 · CONVICTION</div>
              <h3>Only signals that earned their place.</h3>
              <p>The 4:15 PM IST scan grades every stock A through D. We surface A and A−. Most days that's one or two ideas. Often zero — and that's a feature.</p>
              <div className="lv2-feature-visual">
                <svg viewBox="0 0 320 140" width="100%" height="100%" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="lv2-ft1" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#5BC7FF" stopOpacity="0.5" />
                      <stop offset="100%" stopColor="#5BC7FF" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <g transform="translate(20, 18)">
                    <rect width="280" height="22" rx="6" fill="rgba(91,199,255,0.18)" stroke="rgba(91,199,255,0.4)" />
                    <text x="12" y="15" fontFamily="DM Sans" fontSize="10" fontWeight="600" fill="#5BC7FF">A · RELIANCE · +2.18%</text>
                  </g>
                  <g transform="translate(20, 46)">
                    <rect width="280" height="22" rx="6" fill="rgba(91,199,255,0.14)" stroke="rgba(91,199,255,0.3)" />
                    <text x="12" y="15" fontFamily="DM Sans" fontSize="10" fontWeight="600" fill="#B8C0DA">A− · TCS · +1.62%</text>
                  </g>
                  <g transform="translate(20, 74)" opacity="0.4">
                    <rect width="280" height="14" rx="4" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.08)" />
                    <text x="12" y="11" fontFamily="DM Sans" fontSize="9" fill="#7A82A5">B+ · BAJFINANCE · score below threshold</text>
                  </g>
                  <g transform="translate(20, 94)" opacity="0.25">
                    <rect width="280" height="14" rx="4" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.08)" />
                    <text x="12" y="11" fontFamily="DM Sans" fontSize="9" fill="#7A82A5">B · HINDUNILVR · score below threshold</text>
                  </g>
                  <g transform="translate(20, 114)" opacity="0.12">
                    <rect width="280" height="14" rx="4" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.08)" />
                    <text x="12" y="11" fontFamily="DM Sans" fontSize="9" fill="#7A82A5">436 more stocks · scored, not surfaced</text>
                  </g>
                </svg>
              </div>
            </div>

            {/* 02 — PROOF */}
            <div className="lv2-feature">
              <div className="lv2-num">02 · PROOF</div>
              <h3>Walk-forward backtested. Not curve-fit.</h3>
              <p>Every signal is validated on out-of-sample bars the model never saw at training time. Track record updates daily, with every trade open or closed.</p>
              <div className="lv2-feature-visual">
                <svg viewBox="0 0 320 140" width="100%" height="100%" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="lv2-ft2" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#3FDD8A" stopOpacity="0.40" />
                      <stop offset="100%" stopColor="#3FDD8A" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <line x1="0" x2="320" y1="50" y2="50" stroke="rgba(255,255,255,0.05)" />
                  <line x1="0" x2="320" y1="90" y2="90" stroke="rgba(255,255,255,0.05)" />
                  <path d="M0 110 L40 100 L80 105 L120 88 L160 82 L200 65 L240 58 L280 40 L320 28 L320 140 L0 140 Z" fill="url(#lv2-ft2)" />
                  <path d="M0 110 L40 100 L80 105 L120 88 L160 82 L200 65 L240 58 L280 40 L320 28"
                    fill="none" stroke="#3FDD8A" strokeWidth="2"
                    style={{ filter: 'drop-shadow(0 2px 6px rgba(63,221,138,0.5))' }} />
                  <path d="M0 120 L40 116 L80 114 L120 108 L160 104 L200 98 L240 94 L280 90 L320 86"
                    fill="none" stroke="#7A82A5" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.6" />
                  <circle cx="320" cy="28" r="3.5" fill="#3FDD8A" />
                  <text x="6" y="14" fontFamily="DM Sans" fontSize="9" fontWeight="600" fill="#3FDD8A">Strategy (backtest)</text>
                  <text x="6" y="28" fontFamily="DM Sans" fontSize="9" fill="#7A82A5">Benchmark</text>
                </svg>
              </div>
            </div>

            {/* 03 — EXECUTION */}
            <div className="lv2-feature">
              <div className="lv2-num">03 · EXECUTION</div>
              <h3>One click to Zerodha Kite.</h3>
              <p>Sized to your account, routed to Kite, recorded in your journal. No second tab. No copy-paste. The signal is the order is the trade log.</p>
              <div className="lv2-feature-visual" style={{ display: 'grid', placeItems: 'center' }}>
                <svg viewBox="0 0 220 100" width="220" height="100">
                  <g transform="translate(8, 14)">
                    <rect width="96" height="72" rx="10" fill="rgba(79,140,255,0.10)" stroke="rgba(79,140,255,0.36)" />
                    <text x="10" y="18" fontFamily="DM Sans" fontSize="9" fontWeight="600" fill="#5BC7FF">FRESH</text>
                    <text x="10" y="34" fontFamily="DM Sans" fontSize="13" fontWeight="600" fill="#F1F5FF">RELIANCE</text>
                    <text x="10" y="50" fontFamily="DM Sans" fontSize="11" fontWeight="500" fill="#F1F5FF" style={{ fontVariantNumeric: 'tabular-nums' }}>₹2,948</text>
                    <rect x="10" y="56" width="68" height="14" rx="7" fill="#4F8CFF" />
                    <text x="44" y="66" fontFamily="DM Sans" fontSize="9" fontWeight="600" fill="#fff" textAnchor="middle">BUY × 25</text>
                  </g>
                  <g transform="translate(110, 46)">
                    <path d="M0 4 H22 M16 0 L24 4 L16 8" fill="none" stroke="#4F8CFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </g>
                  <g transform="translate(140, 14)">
                    <rect width="72" height="72" rx="10" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.18)" />
                    <circle cx="36" cy="22" r="11" fill="#ff6b35" />
                    <path d="M30 18 L34 22 L42 14" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                    <text x="36" y="46" fontFamily="DM Sans" fontSize="9" fontWeight="600" fill="#F1F5FF" textAnchor="middle">Kite</text>
                    <text x="36" y="58" fontFamily="DM Sans" fontSize="8" fill="#7A82A5" textAnchor="middle">Filled</text>
                    <text x="36" y="68" fontFamily="DM Sans" fontSize="8" fill="#3FDD8A" textAnchor="middle" style={{ fontVariantNumeric: 'tabular-nums' }}>14s</text>
                  </g>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── ANATOMY OF A SIGNAL ─── */}
      <section className="lv2-section" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>WHAT YOU GET</SectionEyebrow>
            <h2 className="lv2-section-title">Every signal is a complete trade plan.</h2>
            <p className="lv2-section-sub">
              No “buy at CMP.” Each signal arrives with everything you need to act — and to
              manage the downside — precomputed.
            </p>
          </div>
          <div className="lv2-proof">
            {/* Sample signal card */}
            <div className="lv2-proof-chart" style={{ height: 'auto', display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <LogoTile sym="RELIANCE" size={34} />
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--lv2-text-1)', fontSize: 16 }}>RELIANCE</div>
                    <div style={{ fontSize: 11, color: 'var(--lv2-text-3)', fontFamily: 'var(--lv2-font-mono)' }}>Energy · NSE · example</div>
                  </div>
                </div>
                <span style={{ fontFamily: 'var(--lv2-font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--lv2-info)', border: '1px solid var(--lv2-info-edge)', background: 'var(--lv2-info-soft)', borderRadius: 6, padding: '4px 8px' }}>
                  GRADE A · CONF 0.94
                </span>
              </div>
              {[
                ['Entry', '₹2,872', ''],
                ['Target', '₹3,066', 'bull'],
                ['Stop', '₹2,786', 'bear'],
                ['Risk : reward', '1 : 2.2', ''],
                ['Hold window', '~14 days', ''],
              ].map(([k, v, tone]) => (
                <div key={k} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--lv2-edge-1)', paddingTop: 10 }}>
                  <span style={{ fontSize: 13, color: 'var(--lv2-text-3)' }}>{k}</span>
                  <span style={{ fontFamily: 'var(--lv2-font-mono)', fontWeight: 600, fontSize: 14, color: tone === 'bull' ? 'var(--lv2-bull)' : tone === 'bear' ? 'var(--lv2-bear)' : 'var(--lv2-text-1)' }}>{v}</span>
                </div>
              ))}
              <div style={{ fontSize: 11, color: 'var(--lv2-text-4)', marginTop: 4 }}>Illustrative example — not a live recommendation.</div>
            </div>
            {/* Field explanations */}
            <div className="lv2-proof-stats">
              {[
                ['Confidence + grade', 'A calibrated probability that the move clears the bar, distilled into an A–D grade. Only A and A− ship as signals.'],
                ['Entry, stop, target', 'Concrete prices — an ATR-based stop and an R:R-tuned target — not a vague “buy now and hope.”'],
                ['Position size', 'Scaled to your account and capped so risk per trade stays bounded. You approve it and route it to Kite.'],
                ['Exit logic', 'A swing horizon of about two weeks. The model tells you when to leave — target hit, stop hit, or time.'],
              ].map(([k, v]) => (
                <div key={k} className="lv2-stat">
                  <div className="lv2-stat-l">{k}</div>
                  <div className="lv2-stat-d" style={{ marginTop: 6, fontSize: 13, color: 'var(--lv2-text-2)' }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── TRACK RECORD ─── */}
      <section className="lv2-section" id="proof" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>TRACK RECORD · 10-FOLD WALK-FORWARD</SectionEyebrow>
            <h2 className="lv2-section-title">Tested out-of-sample. The good years and the bad.</h2>
            <p className="lv2-section-sub">A survivorship-corrected, walk-forward backtest of the core 14-day model (2017–2026), with brokerage and STT modelled in. Returns concentrate in trending years and were negative in three of the last eight. Live trading began recently — the forward record is still accumulating. Backtest figures, not live results.</p>
          </div>

          <div className="lv2-proof">
            <div className="lv2-proof-chart" style={{ height: 'auto', minHeight: 320 }}>
              <div style={{ fontSize: 11, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--lv2-text-3)', fontWeight: 600, marginBottom: 12 }}>
                Walk-forward return by year (CAGR)
              </div>
              <svg viewBox="0 0 600 300" width="100%" height="100%" style={{ maxHeight: 270 }}>
                {(() => {
                  const data = [['2017', 31.6], ['2018', -6.0], ['2019', -15.3], ['2020', 103.7], ['2021', 106.0], ['2022', 5.0], ['2023', 9.7], ['2024', -7.6], ['2025', -6.4], ['2026', 14.5]];
                  const maxV = 110, minV = -22, plotTop = 30, plotBot = 248;
                  const scale = (plotBot - plotTop) / (maxV - minV);
                  const zeroY = plotBot - (0 - minV) * scale;
                  const slot = 600 / data.length;
                  const bw = 30;
                  return (
                    <g>
                      <line x1="0" x2="600" y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
                      {data.map(([yr, v], i) => {
                        const x = i * slot + (slot - bw) / 2;
                        const h = Math.max(2, Math.abs(v) * scale);
                        const y = v >= 0 ? zeroY - h : zeroY;
                        const color = v >= 0 ? '#3FDD8A' : '#FF5C7A';
                        return (
                          <g key={yr}>
                            <rect x={x} y={y} width={bw} height={h} rx="3" fill={color} opacity="0.88" />
                            <text x={x + bw / 2} y={v >= 0 ? y - 5 : y + h + 12} fontFamily="var(--lv2-font-mono)" fontSize="9" fill={color} textAnchor="middle">{`${v > 0 ? '+' : ''}${v}%`}</text>
                            <text x={x + bw / 2} y="288" fontFamily="var(--lv2-font-mono)" fontSize="9" fill="#7A82A5" textAnchor="middle">{`'${yr.slice(2)}`}</text>
                          </g>
                        );
                      })}
                    </g>
                  );
                })()}
              </svg>
            </div>

            <div className="lv2-proof-stats">
              <div className="lv2-stat">
                <div className="lv2-stat-l">MEAN SHARPE</div>
                <div className="lv2-stat-v">0.95</div>
                <div className="lv2-stat-d">10-fold walk-forward, out-of-sample · median 0.85</div>
              </div>
              <div className="lv2-stat">
                <div className="lv2-stat-l">WIN RATE</div>
                <div className="lv2-stat-v">53<span className="lv2-stat-unit">%</span></div>
                <div className="lv2-stat-d">Mean across folds · range 40–69%</div>
              </div>
              <div className="lv2-stat">
                <div className="lv2-stat-l">PROFITABLE YEARS</div>
                <div className="lv2-stat-v">5<span className="lv2-stat-unit"> / 8</span></div>
                <div className="lv2-stat-d">2019–2026 · negative in 2019, 2024, 2025</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── THE EDGE, HONESTLY ─── */}
      <section className="lv2-section" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>THE EDGE, HONESTLY</SectionEyebrow>
            <h2 className="lv2-section-title">What the edge is — and what it isn’t.</h2>
            <p className="lv2-section-sub">We’d rather tell you how it actually works than sell you magic.</p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 18, maxWidth: 980, margin: '0 auto' }}>
            {[
              {
                kind: 'is',
                label: 'WHAT IT IS',
                items: [
                  ['Calibrated conviction', 'The model rates how likely a stock is to make a sizable move; only the highest-confidence names clear the 0.92 gate.'],
                  ['Asymmetry by construction', 'ATR stops and R:R-tuned targets turn a roughly even win rate into wins that are bigger than the losses.'],
                  ['Restraint', 'Most days it stays silent. Not trading the marginal setups is part of the return.'],
                ],
              },
              {
                kind: 'isnt',
                label: 'WHAT IT ISN’T',
                items: [
                  ['Not a direction oracle', 'The win rate sits around 50%. The model ranks how much a stock may move — not whether it’s simply “going up”.'],
                  ['Not AI sector rotation', 'It doesn’t decide which sector leads. That layer is still in shadow research, graded before it can touch a trade.'],
                  ['Not a guarantee', 'Backtests flatter, some years are negative, and the live record is still being earned.'],
                ],
              },
            ].map((col) => {
              const accent = col.kind === 'is' ? 'var(--lv2-bull)' : 'var(--lv2-text-3)';
              return (
                <div key={col.kind} style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%)', border: '1px solid var(--lv2-edge-1)', borderRadius: 18, padding: 26 }}>
                  <div style={{ fontFamily: 'var(--lv2-font-mono)', fontSize: 11, letterSpacing: '0.16em', fontWeight: 600, color: accent, marginBottom: 16 }}>{col.label}</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {col.items.map(([t, d]) => (
                      <div key={t} style={{ display: 'flex', gap: 11 }}>
                        <span style={{ color: accent, flexShrink: 0, marginTop: 2, lineHeight: 0 }}>
                          {col.kind === 'is'
                            ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
                            : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M5 12h14" /></svg>}
                        </span>
                        <div>
                          <div style={{ color: 'var(--lv2-text-1)', fontWeight: 600, fontSize: 14.5, marginBottom: 3 }}>{t}</div>
                          <div style={{ color: 'var(--lv2-text-2)', fontSize: 13, lineHeight: 1.5 }}>{d}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── HOW WE STAY HONEST ─── */}
      <section className="lv2-section" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>METHODOLOGY</SectionEyebrow>
            <h2 className="lv2-section-title">How we keep ourselves honest.</h2>
            <p className="lv2-section-sub">No screenshots, no selective memory. For a tool that touches real money, the discipline is the product.</p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 14 }}>
            {[
              ['Walk-forward only', 'Every model is tested on out-of-sample bars it never saw at training. We measure what generalises — not what fits the past.'],
              ['Costs are baked in', 'Brokerage and STT are modelled into every backtested trade. The numbers you see are after costs, not before.'],
              ['The live record is the judge', 'Backtests can flatter. Live trading began recently and the forward record only grows — that’s the test we hold ourselves to.'],
              ['We kill our own ideas', 'Every research idea is pre-registered with a pass/fail bar before we see results. Most get killed. Only what survives reaches your dashboard.'],
              ['Survivorship-corrected', 'The backtest universe is reconstructed from historical index membership and puts delisted and merged names (Yes Bank, Suzlon, Jet Airways) back in — it can’t quietly keep only the winners.'],
              ['One codebase, no skew', 'A single source of truth computes the features for both the backtest and the live signal. What we measure is what we serve.'],
            ].map(([title, desc]) => (
              <div
                key={title}
                style={{
                  background: 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%)',
                  border: '1px solid var(--lv2-edge-1)',
                  borderRadius: 16,
                  padding: 22,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <h3 style={{ fontFamily: 'var(--lv2-font-display)', fontSize: 16, fontWeight: 600, letterSpacing: '-0.018em', margin: 0, color: 'var(--lv2-text-1)' }}>{title}</h3>
                <p style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--lv2-text-2)', margin: 0 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── WHAT'S NEXT — AI SECTOR-REGIME ─── */}
      <section className="lv2-section" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>ON THE ROADMAP</SectionEyebrow>
            <h2 className="lv2-section-title">What we’re building next.</h2>
            <p className="lv2-section-sub">The model picks names and times them. The next layer reasons about sectors.</p>
          </div>
          <div className="lv2-proof">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--lv2-text-2)', margin: 0, maxWidth: '52ch' }}>
                We’re training an AI sector-regime analyst — a model that reasons about which sectors are
                setting up to lead, and why. Because a language model can’t be honestly backtested on history
                it has already seen, it runs in <strong style={{ color: 'var(--lv2-text-1)' }}>shadow mode</strong>:
                its calls are logged and graded against what the market actually does over the following weeks.
                It won’t influence a single live signal until it beats a fair baseline.
              </p>
              <span style={{ alignSelf: 'flex-start', fontFamily: 'var(--lv2-font-mono)', fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--lv2-warn)', border: '1px solid rgba(255,180,84,0.4)', background: 'rgba(255,180,84,0.12)', borderRadius: 6, padding: '5px 10px' }}>
                STATUS · SHADOW RESEARCH · NOT LIVE
              </span>
            </div>
            <div className="lv2-proof-stats">
              {[
                ['Shadow mode', 'Logged weekly, never wired to a live signal.'],
                ['Graded forward', 'Scored against real sector returns at 21 and 42 days.'],
                ['Ships only if it earns it', 'Promoted to live sizing only after it beats a fair baseline.'],
              ].map(([k, v]) => (
                <div key={k} className="lv2-stat">
                  <div className="lv2-stat-l">{k}</div>
                  <div className="lv2-stat-d" style={{ marginTop: 6, fontSize: 13, color: 'var(--lv2-text-2)' }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── PRIVATE ACCESS ─── */}
      <section className="lv2-section" id="access" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>ACCESS</SectionEyebrow>
            <h2 className="lv2-section-title">Private, invite-only. Not a subscription.</h2>
            <p className="lv2-section-sub">NiftyQuant isn’t sold. It’s a private research tool shared with a small group of traders — no plans, no tiers, no card.</p>
          </div>

          <div style={{ maxWidth: 760, margin: '0 auto', background: 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%)', border: '1px solid var(--lv2-edge-1)', borderRadius: 20, padding: 32 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 20, marginBottom: 30 }}>
              {[
                ['No subscription', 'No monthly plan, no paywall. Access is granted, not purchased.'],
                ['Your account, your orders', 'You connect your own Zerodha Kite in one step and sign every order yourself. We never hold or manage your capital.'],
                ['Small by design', 'Onboarded in small batches, so the dashboard stays fast and the feedback loop stays real.'],
                ['Leave anytime', 'Revoke Kite access in one click. Your journal and track-record data stay readable.'],
              ].map(([t, d]) => (
                <div key={t} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9, color: 'var(--lv2-text-1)', fontWeight: 600, fontSize: 15 }}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#3FDD8A" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M20 6 9 17l-5-5" /></svg>
                    {t}
                  </div>
                  <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--lv2-text-2)', paddingLeft: 24 }}>{d}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, textAlign: 'center' }}>
              <button className="lv2-btn lv2-btn-primary" onClick={openModal} style={{ minWidth: 220 }}>
                Request access
                <span className="lv2-btn-arrow"><ArrowIcon /></span>
              </button>
              <span style={{ fontSize: 12, color: 'var(--lv2-text-3)' }}>We review every request personally. Bring a Zerodha account.</span>
            </div>
          </div>
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section className="lv2-section" id="faq" style={{ paddingTop: 0 }}>
        <div className="lv2-wrap">
          <div className="lv2-section-head">
            <SectionEyebrow>FAQ</SectionEyebrow>
            <h2 className="lv2-section-title">Questions, answered.</h2>
          </div>

          <div className="lv2-faq">
            {FAQ_ITEMS.map((item, idx) => (
              <div key={idx} className={`lv2-faq-item${openFaq === idx ? ' open' : ''}`}>
                <button
                  className="lv2-faq-q"
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  aria-expanded={openFaq === idx}
                >
                  <span>{item.q}</span>
                  <span className="lv2-faq-ic">
                    <PlusIcon />
                  </span>
                </button>
                <div className="lv2-faq-a">{item.a}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="lv2-cta">
        <div className="lv2-wrap">
          <div className="lv2-cta-card">
            <h2 className="lv2-cta-title">Wake up to conviction.<br />Not noise.</h2>
            <p className="lv2-cta-sub">Invite-only. No subscription, no card — you bring your own Zerodha account.</p>
            <div className="lv2-cta-buttons">
              <button className="lv2-btn lv2-btn-primary" onClick={openModal}>
                Request access
                <span className="lv2-btn-arrow"><ArrowIcon /></span>
              </button>
              <button className="lv2-btn lv2-btn-ghost" onClick={() => scrollTo('proof')}>
                See the track record
              </button>
            </div>
            <div className="lv2-cta-note">
              Research and decision-support output, not investment advice. Past performance is not indicative of future returns. Subject to market risk.
            </div>
          </div>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer className="lv2-footer">
        <div className="lv2-wrap">
          <div className="lv2-footer-grid">
            <div className="lv2-footer-brand">
              <div className="lv2-footer-brand-row">
                <div className="lv2-nav-mark" style={{ width: 28, height: 28, borderRadius: 7 }}>
                  <ChartIcon size={15} />
                </div>
                <span className="lv2-nav-text">NiftyQuant</span>
              </div>
              <p className="lv2-footer-tag">
                AI-graded swing-trading signals for the Nifty 500. Walk-forward validated and one-click executable through Zerodha Kite.
              </p>
            </div>

            <div className="lv2-footer-col">
              <h4>Product</h4>
              <ul>
                <li><button className="lv2-footer-col-link" onClick={() => scrollTo('how')} style={{ background: 'none', border: 0, cursor: 'pointer', padding: 0, fontSize: 'inherit', fontFamily: 'inherit', color: 'inherit' }}>How it works</button></li>
                <li><button className="lv2-footer-col-link" onClick={() => scrollTo('proof')} style={{ background: 'none', border: 0, cursor: 'pointer', padding: 0, fontSize: 'inherit', fontFamily: 'inherit', color: 'inherit' }}>Track record</button></li>
                <li><button className="lv2-footer-col-link" onClick={() => scrollTo('access')} style={{ background: 'none', border: 0, cursor: 'pointer', padding: 0, fontSize: 'inherit', fontFamily: 'inherit', color: 'inherit' }}>Access</button></li>
                <li><a href="/dashboard">Dashboard</a></li>
              </ul>
            </div>

            <div className="lv2-footer-col">
              <h4>Legal</h4>
              <ul>
                <li><a href="#">Disclaimer</a></li>
                <li><a href="#">Risk disclosure</a></li>
                <li><a href="#">Privacy</a></li>
                <li><a href="#">Terms</a></li>
              </ul>
            </div>

            <div className="lv2-footer-col">
              <h4>Company</h4>
              <ul>
                <li><a href="#">About</a></li>
                <li><a href="#">Founder note</a></li>
                <li><a href="#">Press</a></li>
                <li><a href="#">Contact</a></li>
              </ul>
            </div>
          </div>

          <div className="lv2-footer-foot">
            <span>© 2026 NiftyQuant</span>
            <span>Made in Bengaluru · NSE data may be delayed</span>
          </div>
          <p className="lv2-footer-disclaimer">{DISCLAIMER}</p>
        </div>
      </footer>

      {/* ─── Request access modal (real POST /api/access-requests) ─── */}
      <RequestAccessModal open={requestOpen} onOpenChange={setRequestOpen} />
    </div>
  );
}

/* ─── Default export wrapped in RegimeProvider (matches current Landing.jsx pattern) ─── */
export default function LandingV2() {
  return (
    <RegimeProvider>
      <LandingV2Shell />
    </RegimeProvider>
  );
}
