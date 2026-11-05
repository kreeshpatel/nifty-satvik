/**
 * LandingV3 — the public marketing site, design v5 "Ledger" (docs/DESIGN_BRIEF_V5.md).
 *
 * Content rules (brief §6): every compliance sentence is carried over from LandingV2 verbatim;
 * every figure comes from GET /api/landing-stats (with LandingV2's reviewed fallback when the
 * API is unreachable); product pictures are labelled illustrative. Charts are hand-built SVG so
 * the landing loads no chart library.
 */
import { useEffect, useMemo, useState, useId } from 'react';
import { ArrowRight, ArrowUpRight, Check, Minus, Plus, ShieldCheck, Lock, LineChart,
  Scale, FlaskConical, Layers, Eye, Gauge, CircleSlash, UserCheck, Users, DoorOpen, TrendingUp } from 'lucide-react';
import RequestAccessModal from '@/components/landing/RequestAccessModal';
import BrandMark from '@/components/brand/BrandMark';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/landing-v3.css';

/* Reviewed fallback — identical to LandingV2's STATS_FALLBACK; shown only if the API is down. */
const FALLBACK = {
  backtest: { cagr_pct: 24.7, sharpe: 1.13, win_rate_pct: 59.2, total_trades: 255,
    max_drawdown_pct: -42.4, mult: 8.11, dsr: 0.894, period: '2017–2026' },
  live: { since: '2026-06-30' },
  yearly_returns: [
    { year: '2017', net_pct: 31.8, partial: true }, { year: '2018', net_pct: 11.6 },
    { year: '2019', net_pct: 30.8 }, { year: '2020', net_pct: 11.4 }, { year: '2021', net_pct: 34.5 },
    { year: '2022', net_pct: 34.8 }, { year: '2023', net_pct: 66.5 }, { year: '2024', net_pct: 9.9 },
    { year: '2025', net_pct: -13.0 }, { year: '2026', net_pct: 31.3, partial: true },
  ],
  equity_bt: [
    { t: '2017-01', s: 99.1,  b: 100.0 }, { t: '2018-01', s: 140.6, b: 109.3 },
    { t: '2019-01', s: 152.9, b: 102.8 }, { t: '2020-01', s: 210.4, b: 113.9 },
    { t: '2020-04', s: 174.2, b: 92.9 },  { t: '2021-01', s: 219.2, b: 132.0 },
    { t: '2022-01', s: 297.9, b: 176.1 }, { t: '2023-01', s: 383.6, b: 178.4 },
    { t: '2024-01', s: 666.6, b: 238.7 }, { t: '2024-07', s: 827.2, b: 285.3 },
    { t: '2025-04', s: 604.1, b: 268.5 }, { t: '2026-06', s: 811.5, b: 283.9 },
  ],
};

const MINUS = '−';
const num = (v, dp = 0) => {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  const s = Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp });
  return n < 0 ? `${MINUS}${s}` : s;
};
const signed = (v, dp = 0) => (v == null ? '—' : `${v > 0 ? '+' : ''}${num(v, dp)}`);

const STEPS = [
  ['Scan', 'Every Saturday we refresh point-in-time prices and fundamentals across the full Nifty 500 large- and mid-cap universe and rebuild the book from the weekly close. No lookahead, ever.'],
  ['Rank', 'Each name is scored cross-sectionally on trend quality and risk. The ranking rule is proprietary and frozen — derived once from history, then never touched.'],
  ['Screen', 'Only the top-ranked names that also pass strict liquidity and solvency filters survive. Most days that is one or two. Often zero — and that restraint is part of the edge.'],
  ['Risk-size', 'Each survivor ships as a complete plan — entry, a hard stop, a target, and a size set to a fixed risk budget with a volatility cap — ready for you to place.'],
];

const PLAN_PARTS = [
  ['Conviction + grade', 'A cross-sectional rank of trend quality against risk, distilled into an A–D grade. Only the top grades ship as signals.'],
  ['Entry, stop, target', 'Concrete prices — an ATR-based stop and a fixed profit target — not a vague “buy now and hope.”'],
  ['Position size', 'Scaled to your account and capped so risk per trade stays bounded. You place the order yourself and record the fill you actually got.'],
  ['Exit logic', 'A multi-week horizon with a hard stop, a target, a trailing stop, and a time cap. The rule tells you when to leave — target, stop, or time.'],
];

const IS = [
  ['Cross-sectional conviction', 'Every name is ranked against the whole universe on trend quality and risk; only the strongest, most liquid, most solvent names clear the bar.'],
  ['Asymmetry by construction', 'Hard ATR stops and a fixed profit target turn an above-even win rate into wins that outweigh the losses.'],
  ['Restraint', 'Most days it stays silent. Not trading the marginal setups is part of the return.'],
];
const ISNT = [
  ['Not a direction oracle', 'It wins about 60% of the time in backtest — an edge, not clairvoyance. It ranks trend quality across names; it does not promise any single stock simply “goes up”.'],
  ['Not AI sector rotation', 'It doesn’t decide which sector leads. That layer is still in shadow research, graded before it can touch a trade.'],
  ['Not a guarantee', 'Backtests flatter, the drawdown is deep, some years are flat, and the live record is still being earned.'],
];

const METHOD = [
  [FlaskConical, 'Walk-forward only', 'Every model is tested on out-of-sample bars it never saw at training. We measure what generalises — not what fits the past.'],
  [Scale, 'Costs are baked in', 'Brokerage and STT are modelled into every backtested trade. The numbers you see are after costs, not before.'],
  [Eye, 'The live record is the judge', 'Backtests can flatter. Live trading began recently and the forward record only grows — that’s the test we hold ourselves to.'],
  [CircleSlash, 'We kill our own ideas', 'Every research idea is pre-registered with a pass/fail bar before we see results. Most get killed. Only what survives reaches your dashboard.'],
  [Layers, 'Survivorship-corrected', 'The backtest universe is reconstructed from historical index membership and puts delisted and merged names (Yes Bank, Suzlon, Jet Airways) back in — it can’t quietly keep only the winners.'],
  [Gauge, 'One codebase, no skew', 'A single source of truth computes the features for both the backtest and the live signal. What we measure is what we serve.'],
];

const ACCESS = [
  [UserCheck, 'No subscription', 'No monthly plan, no paywall. Access is granted, not purchased.'],
  [Lock, 'Your account, your orders', 'We never connect to your broker, place an order, or hold your capital. You trade your own account and tell us what filled.'],
  [Users, 'Small by design', 'Onboarded in small batches, so the dashboard stays fast and the feedback loop stays real.'],
  [DoorOpen, 'Leave anytime', 'Nothing to disconnect, because nothing was connected. Your journal and track-record data stay readable.'],
];

const FAQ = [
  ['Is Nifty Satvik SEBI-registered?', 'No. Nifty Satvik is not a SEBI-registered investment advisor or research analyst. We publish research and decision-support signals — not personalised investment advice — and we never manage your capital. Every order is placed by you, in your own broker account.'],
  ['Do I need a Zerodha Kite account?', 'No. Nifty Satvik does not connect to your broker and does not place orders. You read the plan here and place every order yourself, in whatever broker you already use, then record what you actually filled so the track record reflects your trades rather than ours.'],
  ['What’s the minimum capital to start?', 'There’s no hard floor, but we recommend ₹2,00,000 minimum. Position sizes scale with your equity, and small accounts have trouble respecting stops on higher-priced names like NESTLEIND or BAJFINANCE.'],
  ['How is this different from a Telegram tip channel?', 'Three differences. (1) Every signal has explicit entry, stop, and target — no “buy at CMP”. (2) Every signal is walk-forward backtested before it ships — no “this stock looks good”. (3) Every trade is logged with timestamps, fills, and P&L — no screenshots, no selective memory.'],
  ['What does it cost?', 'Nothing today. Nifty Satvik is private and invite-only — not a paid subscription. You keep your own broker account; we don’t charge a fee or manage your money. Revoke access anytime — your journal and track-record data stay readable.'],
  ['What happens on a flat or bearish day?', 'The dashboard says so plainly — “No fresh signals today — next scan at 16:15 IST.” The system is designed to underfit; on many weekdays it surfaces zero A-grade signals. Patience is part of the edge.'],
];

/* ── Charts (SVG, no library) ─────────────────────────────────────────── */

function GrowthChart({ data }) {
  const gid = useId().replace(/:/g, '');
  const [hover, setHover] = useState(null);
  const W = 640, H = 300, P = { l: 8, r: 8, t: 16, b: 28 };
  const pts = data.filter((d) => d && d.s != null);
  if (pts.length < 2) return <div className="l3-chart-empty">Chart unavailable</div>;
  const max = Math.max(...pts.map((d) => Math.max(d.s, d.b ?? 0))) * 1.06;
  const min = Math.min(...pts.map((d) => Math.min(d.s, d.b ?? d.s))) * 0.94;
  const x = (i) => P.l + (i / (pts.length - 1)) * (W - P.l - P.r);
  const y = (v) => P.t + (1 - (v - min) / (max - min)) * (H - P.t - P.b);
  const line = (k) => pts.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(d[k]).toFixed(1)}`).join('');
  const area = `${line('s')}L${x(pts.length - 1)},${H - P.b}L${x(0)},${H - P.b}Z`;
  const years = pts.map((d, i) => [String(d.t).slice(0, 4), i]).filter(([yr], i, a) => i === 0 || yr !== a[i - 1][0]);
  const h = hover != null ? pts[hover] : pts[pts.length - 1];
  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const i = Math.round(((e.clientX - r.left) / r.width) * (pts.length - 1));
    setHover(Math.max(0, Math.min(pts.length - 1, i)));
  };
  return (
    <figure className="l3-growth">
      <div className="l3-growth-read" aria-live="polite">
        <span className="l3-growth-date">{String(h.t)}</span>
        <span><i className="l3-key l3-key-s" />Strategy <b data-num>₹{num(h.s, 1)}</b></span>
        {h.b != null && <span><i className="l3-key l3-key-b" />Nifty 500 <b data-num>₹{num(h.b, 1)}</b></span>}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" preserveAspectRatio="none"
        aria-label={`Growth of ₹100: strategy ₹${num(pts[pts.length - 1].s, 0)} versus Nifty 500 ₹${num(pts[pts.length - 1].b, 0)} (backtest, in-sample)`}
        onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id={`g${gid}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="var(--l-up)" stopOpacity=".22" />
            <stop offset="1" stopColor="var(--l-up)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={P.l} x2={W - P.r} y1={P.t + f * (H - P.t - P.b)} y2={P.t + f * (H - P.t - P.b)} className="l3-grid" />
        ))}
        <path d={area} fill={`url(#g${gid})`} />
        {pts[0].b != null && <path d={line('b')} className="l3-line-b" />}
        <path d={line('s')} className="l3-line-s" />
        {hover != null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={P.t} y2={H - P.b} className="l3-cross" />
            <circle cx={x(hover)} cy={y(pts[hover].s)} r="4" className="l3-dot" />
          </g>
        )}
        {years.filter((_, i) => i % 2 === 0).map(([yr, i]) => (
          <text key={yr} x={x(i)} y={H - 8} className="l3-axis">{yr}</text>
        ))}
      </svg>
    </figure>
  );
}

function YearBars({ data }) {
  const max = Math.max(...data.map((d) => Math.abs(d.net_pct)), 1);
  return (
    <ol className="l3-years" aria-label="Calendar-year net returns, backtest">
      {data.map((d) => {
        const up = d.net_pct >= 0;
        return (
          <li key={d.year} className={up ? 'up' : 'down'}>
            <span className="l3-years-v" data-num>{up ? '▲' : '▼'} {signed(d.net_pct, 1)}%</span>
            <span className="l3-years-track">
              <span className="l3-years-bar" style={{ height: `${(Math.abs(d.net_pct) / max) * 100}%` }} />
            </span>
            <span className="l3-years-y">{d.year}{d.partial ? '*' : ''}</span>
          </li>
        );
      })}
    </ol>
  );
}


/* Step illustrations — schematic only (no data is implied). Deterministic, so SSR/screenshot-stable. */
const rnd = (i) => { const x = Math.sin(i * 12.9898) * 43758.5453; return x - Math.floor(x); };
function StepArt({ i }) {
  const W = 220, H = 96;
  if (i === 0) { // Scan: the whole universe, every name a dot
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="l3-art" aria-hidden>
        {Array.from({ length: 84 }).map((_, k) => (
          <circle key={k} cx={10 + (k % 14) * 15.4} cy={12 + Math.floor(k / 14) * 14.4} r="2.6"
            className={rnd(k) > 0.86 ? 'a-hi' : 'a-lo'} />
        ))}
      </svg>
    );
  }
  if (i === 1) { // Rank: the same names, sorted by score; the top tail lights up
    const vals = Array.from({ length: 28 }).map((_, k) => 0.12 + 0.86 * Math.pow(1 - k / 28, 1.6) + rnd(k) * 0.05);
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="l3-art" aria-hidden>
        {vals.map((v, k) => (
          <rect key={k} x={6 + k * 7.6} y={H - 8 - v * 74} width="5" height={v * 74} rx="1.5" className={k < 5 ? 'a-hi' : 'a-lo'} />
        ))}
        <line x1="4" x2={W - 4} y1={H - 7.5} y2={H - 7.5} className="a-axis" />
      </svg>
    );
  }
  if (i === 2) { // Screen: a liquidity/solvency gate only a couple pass
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="l3-art" aria-hidden>
        {Array.from({ length: 5 }).map((_, k) => (
          <circle key={k} cx="22" cy={16 + k * 16} r="3" className="a-hi" />
        ))}
        <rect x="96" y="6" width="3" height="84" rx="1.5" className="a-gate" />
        {[16, 32, 48, 64, 80].map((y, k) => (
          <path key={y} d={k === 1 || k === 3 ? `M28 ${y} C70 ${y} 80 48 100 48 L196 ${y === 32 ? 38 : 58}` : `M28 ${y} L88 ${y}`}
            className={k === 1 || k === 3 ? 'a-pass' : 'a-stop'} />
        ))}
        <circle cx="200" cy="38" r="4" className="a-up" /><circle cx="200" cy="58" r="4" className="a-up" />
      </svg>
    );
  }
  return ( // Risk-size: stop · entry · target, drawn to scale
    <svg viewBox={`0 0 ${W} ${H}`} className="l3-art" aria-hidden>
      <rect x="10" y="44" width="62" height="6" rx="3" className="a-down" />
      <rect x="74" y="44" width="136" height="6" rx="3" className="a-upbar" />
      <rect x="71.5" y="36" width="2.5" height="22" rx="1.2" className="a-ink" />
      <text x="10" y="74" className="a-t">stop</text><text x="73" y="74" className="a-t" textAnchor="middle">entry</text>
      <text x="210" y="74" className="a-t" textAnchor="end">target</text>
      <text x="40" y="30" className="a-t a-tdown" textAnchor="middle">1R</text><text x="142" y="30" className="a-t a-tup" textAnchor="middle">2R</text>
    </svg>
  );
}


/* Hero product shot — a CSS-built phone running a sample Nifty Satvik screen. Sample content
   only (labelled on screen); no live figures are implied. */
function PhoneMock() {
  const rows = [['MCX', 'A', '+27.6%'], ['SYRMA', 'A', '+26.6%'], ['LAURUSLABS', 'A', '+18.2%']];
  return (
    <div className="pf-phone-wrap" aria-hidden>
      <div className="pf-phone">
        <div className="pf-notch" />
        <div className="pf-screen">
          <div className="pf-s-top"><BrandMark size={20} /><span>Command center</span><i className="pf-s-av" /></div>
          <div className="pf-s-hero">
            <span className="pf-s-lbl">Market regime</span>
            <span className="pf-s-big">Bullish</span>
            <span className="pf-s-pill">▲ Breadth +41</span>
            <svg viewBox="0 0 220 60" className="pf-s-spark"><defs><linearGradient id="pfsg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#fff" stopOpacity=".45" /><stop offset="1" stopColor="#fff" stopOpacity="0" /></linearGradient></defs>
              <path d="M0 48 L20 44 L40 46 L60 36 L80 38 L100 28 L120 31 L140 20 L160 24 L180 12 L200 15 L220 6 L220 60 L0 60Z" fill="url(#pfsg)" />
              <path d="M0 48 L20 44 L40 46 L60 36 L80 38 L100 28 L120 31 L140 20 L160 24 L180 12 L200 15 L220 6" fill="none" stroke="#fff" strokeWidth="2" strokeLinejoin="round" /></svg>
          </div>
          <div className="pf-s-sec"><span>Fresh buys</span><b>3</b></div>
          {rows.map(([t, g, u]) => (
            <div key={t} className="pf-s-row"><span className="pf-s-tile">{t.slice(0, 2)}</span><span className="pf-s-t">{t}<small>Grade {g}</small></span><span className="pf-s-u">▲ {u}</span></div>
          ))}
          <div className="pf-s-cta">View trade plan</div>
          <p className="pf-s-note">Sample screen</p>
        </div>
      </div>
      <div className="pf-float pf-fl-a pf-card pf-ring">
        <span className="pf-ic up"><TrendingUp size={18} /></span>
        <div><p className="pf-fl-l">Target reached</p><p className="pf-fl-v">Trim 40% · +2R</p></div>
      </div>
      <div className="pf-float pf-fl-b pf-card pf-ring">
        <span className="pf-ic"><ShieldCheck size={18} /></span>
        <div><p className="pf-fl-l">Every call ships with</p><p className="pf-fl-v">Entry · Stop · Target</p></div>
      </div>
    </div>
  );
}

/* ── Pieces ───────────────────────────────────────────────────────────── */

function Section({ id, eyebrow, title, sub, children, className = '' }) {
  return (
    <section id={id} className={`l3-section ${className}`} aria-labelledby={id ? `${id}-h` : undefined}>
      <div className="l3-wrap">
        {(eyebrow || title) && (
          <header className="l3-head">
            {eyebrow && <p className="l3-eyebrow">{eyebrow}</p>}
            {title && <h2 id={id ? `${id}-h` : undefined} className="l3-h2">{title}</h2>}
            {sub && <p className="l3-sub">{sub}</p>}
          </header>
        )}
        {children}
      </div>
    </section>
  );
}

function PlanCard() {
  return (
    <div className="l3-plan" aria-label="Illustrative trade plan">
      <div className="l3-plan-top">
        <span className="l3-mono-tile" aria-hidden>RE</span>
        <div>
          <div className="l3-plan-sym">RELIANCE</div>
          <div className="l3-plan-meta">Energy · NSE</div>
        </div>
        <span className="l3-chip l3-chip-up">Grade A</span>
      </div>
      <dl className="l3-plan-rows">
        <div><dt>Entry</dt><dd data-num>₹2,872</dd></div>
        <div><dt>Target</dt><dd data-num className="up">₹3,066</dd></div>
        <div><dt>Stop</dt><dd data-num className="down">₹2,786</dd></div>
        <div><dt>Risk : reward</dt><dd data-num>1 : 2.2</dd></div>
        <div><dt>Hold window</dt><dd>Multi-week</dd></div>
      </dl>
      <div className="l3-rr" aria-hidden>
        <span className="l3-rr-risk" style={{ width: '31%' }} />
        <span className="l3-rr-reward" style={{ width: '69%' }} />
        <span className="l3-rr-mark" style={{ left: '31%' }} />
      </div>
      <div className="l3-rr-legend" aria-hidden>
        <span data-num>₹2,786<small>Stop</small></span>
        <span data-num style={{ left: '31%' }}>₹2,872<small>Entry</small></span>
        <span data-num>₹3,066<small>Target</small></span>
      </div>
      <p className="l3-plan-note">Illustrative example — not a live recommendation.</p>
    </div>
  );
}

function Faq() {
  const [open, setOpen] = useState(null);
  return (
    <div className="l3-faq">
      {FAQ.map(([q, a], i) => {
        const isOpen = open === i;
        return (
          <div key={q} className={`l3-faq-item${isOpen ? ' open' : ''}`}>
            <h3>
              <button type="button" aria-expanded={isOpen} aria-controls={`faq-${i}`} id={`faq-q-${i}`}
                onClick={() => setOpen(isOpen ? null : i)}>
                <span>{q}</span>
                <span className="l3-faq-ic" aria-hidden>{isOpen ? <Minus size={16} /> : <Plus size={16} />}</span>
              </button>
            </h3>
            <div id={`faq-${i}`} role="region" aria-labelledby={`faq-q-${i}`} className="l3-faq-a" hidden={!isOpen}>
              <p>{a}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────────────────── */

export default function LandingV3() {
  const [stats, setStats] = useState(FALLBACK);
  const [requestOpen, setRequestOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [menu, setMenu] = useState(false);
  const [pastHero, setPastHero] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch('/api/landing-stats')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!alive || !d) return;
        setStats({
          backtest: { ...FALLBACK.backtest, ...(d.backtest || {}) },
          live: { ...FALLBACK.live, ...(d.live || {}) },
          weekly_swing: d.weekly_swing || null,
          yearly_returns: Array.isArray(d.yearly_returns) && d.yearly_returns.length ? d.yearly_returns : FALLBACK.yearly_returns,
          equity_bt: Array.isArray(d.equity_bt) && d.equity_bt.length ? d.equity_bt : FALLBACK.equity_bt,
        });
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    const on = () => { setScrolled(window.scrollY > 8); setPastHero(window.scrollY > 520); };
    on(); window.addEventListener('scroll', on, { passive: true });
    document.title = 'Nifty Satvik — systematic swing research for the Nifty 500';
    return () => window.removeEventListener('scroll', on);
  }, []);

  const bt = stats.backtest;
  const live = stats.live;
  const weekly = stats.weekly_swing;
  const eq = stats.equity_bt || [];
  const last = eq[eq.length - 1];
  const totalReturn = last ? Math.round(last.s - 100) : null;
  const alpha = last && last.b != null ? Math.round(last.s - last.b) : null;
  const go = (id) => { setMenu(false); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const ask = () => { setMenu(false); setRequestOpen(true); };

  const NAV = useMemo(() => [['how', 'How it works'], ['record', 'Track record'], ['method', 'Methodology'], ['faq', 'FAQ']], []);

  return (
    <div className="l3" data-page-ctx="landing-v3">
      <a href="#main" className="skip-link">Skip to main content</a>

      <header className={`l3-nav${scrolled ? ' scrolled' : ''}`}>
        <div className="l3-wrap l3-nav-in">
          <a className="l3-brand" href="#top" aria-label="Nifty Satvik home">
            <BrandMark size={28} />
            <span>Nifty Satvik</span>
          </a>
          <nav aria-label="Primary" className="l3-nav-links">
            {NAV.map(([id, label]) => <button key={id} type="button" onClick={() => go(id)}>{label}</button>)}
          </nav>
          <div className="l3-nav-cta">
            <a className="l3-btn l3-btn-quiet" href="/login">Sign in</a>
            <button type="button" className="l3-btn l3-btn-primary" onClick={ask}>Request access</button>
            <button type="button" className="l3-burger" aria-label="Menu" aria-expanded={menu} onClick={() => setMenu(!menu)}>
              <span /><span />
            </button>
          </div>
        </div>
        {menu && (
          <nav aria-label="Mobile" className="l3-sheet">
            {NAV.map(([id, label]) => <button key={id} type="button" onClick={() => go(id)}>{label}</button>)}
            <a href="/login">Sign in</a>
          </nav>
        )}
      </header>

      <main id="main">
        {/* HERO */}
        <section className="l3-hero" id="top">
          <div className="l3-wrap l3-hero-grid">
            <div className="l3-hero-copy">
              <p className="l3-pill"><span className="l3-dot-live" aria-hidden />Invite-only · Nifty 500 research</p>
              <h1 className="l3-h1">Trade the plan.<br /><span className="pf-grad-text">Not the noise.</span></h1>
              <p className="l3-lede">
                Nifty Satvik re-scores the Nifty 500 every Saturday evening, and re‑prices what you
                already hold after each weekday close. You get A‑grade signals with an explicit entry,
                stop and target — and you place the orders yourself.
              </p>
              <div className="l3-cta-row">
                <button type="button" className="pf-btn" onClick={ask}>
                  Request access <ArrowRight size={16} aria-hidden />
                </button>
                <button type="button" className="pf-btn-2" onClick={() => go('how')}>How it works</button>
              </div>
              <ul className="l3-assure">
                <li><ShieldCheck size={15} aria-hidden />You place every order yourself</li>
                <li><Lock size={15} aria-hidden />No broker connection</li>
                <li><LineChart size={15} aria-hidden />Every trade on the record</li>
              </ul>
            </div>

            <PhoneMock />
          </div>
        </section>

        {/* STATS STRIP */}
        <section className="l3-strip" aria-label="Backtest summary">
          <div className="l3-wrap l3-strip-grid">
            <div><p className="l3-label">CAGR</p><p className="l3-stat" data-num>~{num(bt.cagr_pct)}%</p><p className="l3-cap">Net of costs, before STCG</p></div>
            <div><p className="l3-label">vs Nifty 500</p><p className="l3-stat up" data-num>{alpha != null ? `${signed(alpha)} pts` : '—'}</p><p className="l3-cap">Cumulative, growth of ₹100</p></div>
            <div><p className="l3-label">Win rate</p><p className="l3-stat" data-num>{num(bt.win_rate_pct)}%</p><p className="l3-cap">Across {num(bt.total_trades)} trades</p></div>
            <div><p className="l3-label">Max drawdown</p><p className="l3-stat down" data-num>{num(bt.max_drawdown_pct)}%</p><p className="l3-cap">Sharpe {num(bt.sharpe, 2)} · DSR {num(bt.dsr, 2)}</p></div>
          </div>
        </section>

        {weekly && (
          <Section id="weekly" eyebrow="This week’s scan · weekly swing model" className="l3-tight">
            <div className="l3-weekly">
              <div>
                <h2 className="l3-h3">Fresh setups, every week.</h2>
                <p className="l3-sub l3-left">Our flagship swing model re-scans the Nifty-500 large &amp; mid-cap universe each week and publishes a graded shortlist — counts and grades only, never a ticker or price. Paper-tracked ahead of live capital.</p>
              </div>
              <div className="l3-weekly-n">
                <p className="l3-big" data-num>{num(weekly.n_signals)}</p>
                <p className="l3-cap">fresh setups this week · {num(weekly.grade_a)} grade A · {num(weekly.grade_b)} grade B · avg target {num(weekly.avg_target_upside_pct, 1)}%</p>
                <p className="l3-cap">Buy window through {weekly.buy_window_until} · {num(weekly.hold_days)}-day swing horizon</p>
              </div>
            </div>
          </Section>
        )}

        {/* HOW */}
        <Section id="how" eyebrow="How it works" title="No black box. The same path, every week."
          sub="Every signal travels one transparent, frozen pipeline — identical in backtest and in production. The one thing we keep private is the exact ranking formula.">
          <ol className="l3-steps">
            {STEPS.map(([t, d], i) => (
              <li key={t}>
                <StepArt i={i} />
                <span className="l3-step-n" data-num>{String(i + 1).padStart(2, '0')}</span>
                <h3>{t}</h3>
                <p>{d}</p>
              </li>
            ))}
          </ol>
          <div className="l3-moat">
            <Lock size={18} aria-hidden />
            <div>
              <h3>The ranking formula is not disclosed.</h3>
              <p>The exact factor, thresholds, and hold rules are the edge — so they stay internal. You get the complete plan and the full track record; the recipe stays ours.</p>
            </div>
          </div>
        </Section>

        {/* PLAN */}
        <Section id="plan" eyebrow="What you get" title="Every signal is a complete trade plan.">
          <div className="l3-split">
            <PlanCard />
            <dl className="l3-parts">
              {PLAN_PARTS.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
            </dl>
          </div>
        </Section>

        {/* RECORD */}
        <Section id="record" eyebrow="Track record" title="The numbers, net of every cost."
          sub={`The weekly-swing book on a survivorship-corrected backtest (${bt.period}), net of brokerage, STT and slippage. In-sample and not yet certified — no real capital has traded.`}>
            <div className="l3-hero-card l3-growth-card">
              <div className="l3-hero-card-head">
                <div>
                  <p className="l3-label">Growth of ₹100 · backtest {bt.period}</p>
                  <p className="l3-big" data-num>
                    {bt.mult != null ? `${num(bt.mult, 1)}×` : '—'}
                    {totalReturn != null && <span className="l3-delta up">▲ {signed(totalReturn)}%</span>}
                  </p>
                </div>
                <span className="l3-chip">In-sample · not certified</span>
              </div>
              {eq.length > 1 ? <GrowthChart data={eq} /> : <div className="l3-chart-skel" aria-hidden />}
              <p className="l3-fine">Net of brokerage, STT and slippage, before 20% STCG. Survivorship-corrected universe. Not indicative of future results; no real capital has traded.</p>
            </div>
          <div className="l3-panel">
            <div className="l3-panel-head">
              <h3>Calendar-year returns</h3>
              <span className="l3-cap">Net, backtest · * partial year</span>
            </div>
            <YearBars data={stats.yearly_returns} />
          </div>
          <p className="l3-fine l3-center">
            Weekly-swing book, backtest {bt.period}, net of costs before 20% STCG, in-sample on the survivorship-corrected universe — Sharpe {num(bt.sharpe, 2)}, DSR {num(bt.dsr, 2)} (below the certification gate). Not indicative of future results; a handful of strong-trend years drive the total, with a &gt;40% peak-to-trough drawdown. No real capital has traded — the forward paper record since {live.since} is the real test.
          </p>
        </Section>

        {/* TRUST */}
        <Section id="edge" eyebrow="Why trust it" title="What the edge is — and what it isn’t."
          sub="We’d rather tell you how it actually works than sell you magic.">
          <div className="l3-isnt">
            <div className="l3-panel">
              <p className="l3-label up">What it is</p>
              <ul>{IS.map(([t, d]) => <li key={t}><Check size={16} className="up" aria-hidden /><div><h3>{t}</h3><p>{d}</p></div></li>)}</ul>
            </div>
            <div className="l3-panel">
              <p className="l3-label down">What it isn’t</p>
              <ul>{ISNT.map(([t, d]) => <li key={t}><Minus size={16} className="down" aria-hidden /><div><h3>{t}</h3><p>{d}</p></div></li>)}</ul>
            </div>
          </div>
        </Section>

        <Section id="method" eyebrow="Methodology" title="No screenshots. No selective memory.">
          <ul className="l3-grid3">
            {METHOD.map(([Icon, t, d]) => (
              <li key={t} className="l3-feature pf-card"><span className="pf-ic"><Icon size={19} aria-hidden /></span><h3>{t}</h3><p>{d}</p></li>
            ))}
          </ul>
          <div className="l3-roadmap">
            <span className="l3-chip">On the roadmap · shadow research · not live</span>
            <p><b>An AI sector-regime analyst — running in shadow mode.</b> It reasons about which sectors are setting up to lead, logged and graded weekly against real sector returns at 21 and 42 days. It won’t influence a single live signal until it beats a fair baseline.</p>
          </div>
        </Section>

        <Section id="access" eyebrow="Access" title="Private, invite-only. Not a subscription."
          sub="Nifty Satvik isn’t sold. It’s a private research tool shared with a small group of traders — no plans, no tiers, no card.">
          <ul className="l3-grid4">
            {ACCESS.map(([Icon, t, d]) => (
              <li key={t} className="l3-feature pf-card"><span className="pf-ic"><Icon size={19} aria-hidden /></span><h3>{t}</h3><p>{d}</p></li>
            ))}
          </ul>
        </Section>

        <Section id="faq" eyebrow="FAQ" title="Questions, answered.">
          <Faq />
        </Section>

        <section className="l3-final" aria-labelledby="final-h">
          <div className="l3-wrap l3-final-in">
            <h2 id="final-h" className="l3-h2">Wake up to conviction.<br />Not noise.</h2>
            <p className="l3-sub">Invite-only. No subscription, no card — you keep your own broker account.</p>
            <div className="l3-cta-row l3-center-row">
              <button type="button" className="pf-btn" onClick={ask}>Request access <ArrowRight size={16} aria-hidden /></button>
              <button type="button" className="pf-btn-2" onClick={() => go('record')}>See the track record</button>
            </div>
            <p className="l3-fine">Research and decision-support output, not investment advice. Past performance is not indicative of future returns. Subject to market risk.</p>
          </div>
        </section>
      </main>

      <footer className="l3-foot">
        <div className="l3-wrap">
          <div className="l3-foot-grid">
            <div className="l3-foot-brand">
              <a className="l3-brand" href="#top"><BrandMark size={26} /><span>Nifty Satvik</span></a>
              <p>Systematic swing research for the Nifty 500. Walk-forward validated; you place every order in your own broker.</p>
            </div>
            <nav aria-label="Product"><h4>Product</h4><ul>
              <li><button type="button" onClick={() => go('how')}>How it works</button></li>
              <li><button type="button" onClick={() => go('record')}>Track record</button></li>
              <li><button type="button" onClick={() => go('access')}>Access</button></li>
              <li><a href="/dashboard">Dashboard <ArrowUpRight size={13} aria-hidden /></a></li>
            </ul></nav>
            <nav aria-label="Legal"><h4>Legal</h4><ul>
              <li><a href="/disclaimer">Disclaimer</a></li><li><a href="/risk-disclosure">Risk disclosure</a></li>
              <li><a href="/privacy">Privacy</a></li><li><a href="/terms">Terms</a></li>
            </ul></nav>
            <nav aria-label="Company"><h4>Company</h4><ul>
              <li><a href="/about">About</a></li><li><a href="/founder-note">Founder note</a></li>
              <li><a href="/press">Press</a></li><li><a href="/contact">Contact</a></li>
            </ul></nav>
          </div>
          <div className="l3-foot-base">
            <span>© {new Date().getFullYear()} Nifty Satvik</span>
            <span>Made in Ahmedabad, India</span>
          </div>
          <p className="l3-fine l3-left">{DISCLAIMER}</p>
        </div>
      </footer>

      {/* Mobile: primary action pinned in the thumb zone once the hero CTA scrolls away. */}
      <div className={`l3-mcta${pastHero ? ' show' : ''}`} aria-hidden={!pastHero}>
        <a className="l3-btn l3-btn-ghost" href="/login" tabIndex={pastHero ? 0 : -1}>Sign in</a>
        <button type="button" className="l3-btn l3-btn-primary" onClick={ask} tabIndex={pastHero ? 0 : -1}>Request access</button>
      </div>

      <RequestAccessModal open={requestOpen} onOpenChange={setRequestOpen} />
    </div>
  );
}
