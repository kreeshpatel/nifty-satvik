/**
 * PortfolioV3 — Production Portfolio page.
 *
 * Converted from frontend/public/nifty-design/portfolio2.jsx (Babel-in-browser artifact).
 * Pattern follows DashboardV3 / SignalsV3: ES imports, real hooks, graceful fallbacks,
 * compliance strings, CSS scoped under .pv3- prefix.
 *
 * Sections:
 *   StateStrip  — regime badge + LIVE/PAPER mode + RISK status (computable cells only)
 *   EquityHero  — total value + 4-KPI stack + equity curve (useOverview + useNavHistory)
 *   PerfRibbon  — Sharpe, max drawdown, win rate, avg win/loss (useOverview().metrics)
 *   RiskRibbon  — drawdown headroom + win-rate headroom (computed from real data)
 *                 // TODO: kill-system state endpoint (partial — 2 of 5 cells computable)
 *   MonthlyPnl  — monthly realised return % bucketed from useTrades()
 *                 // TODO: monthly P&L endpoint or position-size on trades
 *   HoldingsTable — useKiteHoldings (connected) OR usePaperPositions (else)
 *   AllocCard   — stacked bar + ranked list by sector (Kite or paper)
 *   ClosedCard  — useTrades() first 5 entries
 *
 * Compliance: no "guarantee", "will", "sure", "sure-shot" in client-facing strings.
 * DISCLAIMER footer sourced from @/lib/signalCopy.
 */

import React, { useState, useContext, useMemo } from 'react';
import { KiteContext } from '@/App';
import { useOverview } from '@/hooks/queries/useOverview';
import { useNavHistory } from '@/hooks/queries/useNavHistory';
import { usePaperHistory } from '@/hooks/queries/usePaperHistory';
import { useKiteHoldings, useKiteMargins } from '@/hooks/queries/useKiteState';
import { usePaperPositions } from '@/hooks/queries/usePaperPositions';
import { useTrades, flattenTrades } from '@/hooks/queries/useTrades';
import { useSignals } from '@/hooks/queries/useSignals';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/portfolio-v3.css';

// ─────────────────────────────────────────────────────────────────────
// Formatters
// ─────────────────────────────────────────────────────────────────────
const fmtINR = (n) =>
  n == null ? '—' : '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtNum = (n) =>
  n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (n) =>
  n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
const fmtPct1 = (n) =>
  n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%';
const fmtLakh = (n) => {
  if (n == null) return '—';
  const sign = n < 0 ? '−' : '';
  const a = Math.abs(n);
  if (a >= 1e7) return sign + '₹' + (a / 1e7).toFixed(2) + 'Cr';
  if (a >= 1e5) return sign + '₹' + (a / 1e5).toFixed(2) + 'L';
  return sign + '₹' + Math.round(a).toLocaleString('en-IN');
};
const fmtSignedINR = (n) =>
  n == null ? '—' : (n >= 0 ? '+' : '−') + '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN');

// ─────────────────────────────────────────────────────────────────────
// Company logo with graceful fallback: brand favicon → monogram
// ─────────────────────────────────────────────────────────────────────
const TICKER_DOMAINS = {
  RELIANCE: 'ril.com', TCS: 'tcs.com', BAJFINANCE: 'bajajfinserv.in',
  INFY: 'infosys.com', HDFCBANK: 'hdfcbank.com', ICICIBANK: 'icicibank.com',
  BHARTIARTL: 'airtel.in', LT: 'larsentoubro.com', MARUTI: 'marutisuzuki.com',
  KOTAKBANK: 'kotak.com', ADANIENT: 'adanienterprises.com', SBIN: 'sbi.co.in',
  AXISBANK: 'axisbank.com', TATAPOWER: 'tatapower.com', POLYCAB: 'polycab.com',
  VOLTAS: 'voltas.com', CUMMINSIND: 'cummins.com', TITAN: 'titancompany.com',
  SUNPHARMA: 'sunpharma.com', DIVISLAB: 'divislabs.com', PERSISTENT: 'persistent.com',
  WIPRO: 'wipro.com', HINDUNILVR: 'hul.co.in', BHARTIARTL: 'airtel.in',
};

function tickerBg(sym) {
  let h = 0;
  for (const ch of (sym || '')) h = (h + ch.charCodeAt(0) * 13) % 360;
  return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`;
}

function Logo({ sym, size = 30, radius = 8 }) {
  const domain = TICKER_DOMAINS[(sym || '').toUpperCase()];
  const sources = domain
    ? [`https://icons.duckduckgo.com/ip3/${domain}.ico`, `https://www.google.com/s2/favicons?domain=${domain}&sz=128`]
    : [];
  const [idx, setIdx] = useState(0);
  React.useEffect(() => { setIdx(0); }, [sym]);
  if (idx >= sources.length) {
    return (
      <div
        className="pv3-logo-tile pv3-logo-mono"
        style={{ width: size, height: size, borderRadius: radius, background: tickerBg(sym), fontSize: Math.round(size * 0.34) }}
      >
        {(sym || '??').slice(0, 2)}
      </div>
    );
  }
  return (
    <div className="pv3-logo-tile" style={{ width: size, height: size, borderRadius: radius }}>
      <img src={sources[idx]} alt={sym} onError={() => setIdx((i) => i + 1)} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Icons
// ─────────────────────────────────────────────────────────────────────
const Icon = {
  Arrow:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>,
  Plug:    (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22v-5"/><path d="M9 7V2"/><path d="M15 7V2"/><path d="M6 13V8a6 6 0 0 1 12 0v5a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2z"/></svg>,
  Alert:   (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>,
  Shield:  (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
};

// ─────────────────────────────────────────────────────────────────────
// Skeleton
// ─────────────────────────────────────────────────────────────────────
function Skel({ w = '100%', h = 14, radius = 6 }) {
  return <div className="pv3-skel" style={{ width: w, height: h, borderRadius: radius }} />;
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 1 — StateStrip
// Driven by: KiteContext.connected, useSignals().regime
// ─────────────────────────────────────────────────────────────────────
function StateStrip({ kiteConnected, regime, drawdownPct }) {
  const status = (regime?.status || '').toLowerCase();
  const isBull = status.includes('bull');
  const isBear = status.includes('bear');
  const regimeLabel = isBull ? 'Bullish' : isBear ? 'Bearish' : 'Choppy';
  const regimeCls = isBull ? 'num-bull' : isBear ? 'num-bear' : 'num-warn';

  // Computable risk status from drawdown_pct
  // Kill threshold: 15% drawdown (documented in CLAUDE.md). We can compute % to kill.
  const DRAWDOWN_KILL = 15;
  const ddPct = drawdownPct != null ? Math.abs(Number(drawdownPct)) : null;
  const riskOk = ddPct == null || ddPct < DRAWDOWN_KILL * 0.6;
  const riskSoft = ddPct != null && ddPct >= DRAWDOWN_KILL * 0.6 && ddPct < DRAWDOWN_KILL;
  const riskWord = riskSoft ? 'SOFT WARNING' : ddPct != null && ddPct >= DRAWDOWN_KILL ? 'HARD KILL' : 'ALL CLEAR';
  const riskCls = riskSoft ? 'kw-soft' : (ddPct != null && ddPct >= DRAWDOWN_KILL) ? 'kw-hard' : 'kw-ok';

  return (
    <div className="pv3-regime-strip">
      <div className="pv3-regime-left">
        <span className={`pv3-live-dot ${!kiteConnected ? 'pv3-dot-info' : ''}`} />
        <span className="pv3-regime-eyebrow">
          {kiteConnected ? 'LIVE' : 'PAPER'}
        </span>
        <span className="pv3-regime-statement">
          Portfolio is{' '}
          <em className={kiteConnected ? 'num-bull' : 'num-info'}>
            {kiteConnected ? 'Live' : 'Paper'}
          </em>
          <span className="pv3-sep">·</span>
          <span>
            Market is <em className={regimeCls}>{regimeLabel}</em>
          </span>
          {regime?.vix != null && (
            <>
              <span className="pv3-sep">·</span>
              <span className="pv3-t-num-small">VIX {Number(regime.vix).toFixed(1)}</span>
            </>
          )}
        </span>
      </div>
      <div className="pv3-regime-right">
        <span className="pv3-strength-label">RISK</span>
        <span className={`pv3-kw ${riskCls}`}>{riskWord}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 2 — Equity curve SVG
// Data from useNavHistory or useOverview().equity_curve
// Benchmark line hidden if no benchmark data (never fabricated)
// ─────────────────────────────────────────────────────────────────────
const PERIODS = ['1M', '3M', '6M', '1Y', 'All'];
const PERIOD_DAYS = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365, 'All': null };

function EquityChartSvg({ history, totalValue, startValue }) {
  const [period, setPeriod] = useState('All');
  const [hiIdx, setHiIdx] = useState(null);
  const svgRef = React.useRef(null);

  const data = useMemo(() => {
    if (!history || history.length === 0) return [];
    const days = PERIOD_DAYS[period];
    const sliced = days ? history.slice(-days) : history;
    return sliced.map((p) => ({ date: p.date, value: Number(p.value) || 0 }));
  }, [history, period]);

  // X axis labels — must be computed before any early return (rules-of-hooks)
  const xLabels = useMemo(() => {
    if (!data || data.length <= 1) return [];
    const maxLabels = 5;
    const step2 = Math.max(1, Math.floor(data.length / maxLabels));
    const labels = [];
    const seen = new Set();
    for (let i = 0; i < data.length; i += step2) {
      const label = data[i].date?.slice(0, 7) || '';
      // Dedupe repeated YYYY-MM — a short/dense series otherwise prints the
      // same month 2-3× (the "2026-05 2026-05 2026-05" axis bug).
      if (!label || seen.has(label)) continue;
      seen.add(label);
      labels.push({ i, label });
    }
    return labels;
  }, [data]);

  if (!data.length) {
    return (
      <div className="pv3-eq-wrap">
        <div className="pv3-eq-empty">
          No equity history yet — data accumulates daily after the first portfolio scan.
        </div>
        <div className="pv3-eq-period-strip">
          {PERIODS.map((p) => (
            <button key={p} className={`pv3-seg-btn ${period === p ? 'active' : ''}`} onClick={() => setPeriod(p)}>{p}</button>
          ))}
        </div>
      </div>
    );
  }

  const W = 640, H = 250, padL = 4, padR = 56, padT = 16, padB = 22;
  const N = data.length;
  const vals = data.map((d) => d.value);
  const dMin = Math.min(...vals);
  const dMax = Math.max(...vals);
  const range = dMax - dMin || 1; // eslint-disable-line no-unused-vars

  // Smart Y-tick step
  const rawStep = (dMax - dMin) / 3.2;
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep || 1)));
  const nrm = rawStep / mag;
  const step = (nrm < 1.5 ? 1 : nrm < 3 ? 2 : nrm < 7 ? 5 : 10) * mag;
  const yMin = Math.floor(dMin / step) * step;
  const yMax = Math.ceil(dMax / step) * step;
  const yRange = (yMax - yMin) || 1;
  const ticks = [];
  for (let v = yMin; v <= yMax + 1e-6; v += step) ticks.push(v);

  const xOf = (i) => padL + (i * (W - padL - padR)) / Math.max(N - 1, 1);
  const yOf = (v) => padT + (H - padT - padB) * (1 - (v - yMin) / yRange);
  const linePath = data.map((d, i) => `${i === 0 ? 'M' : 'L'}${xOf(i).toFixed(1)},${yOf(d.value).toFixed(1)}`).join(' ');
  const areaPath = `${linePath} L${xOf(N - 1)},${H - padB} L${xOf(0)},${H - padB} Z`;
  const peakVal = Math.max(...vals);

  const onMove = (e) => {
    if (!svgRef.current) return;
    const r = svgRef.current.getBoundingClientRect();
    const i = Math.max(0, Math.min(N - 1, Math.round(((e.clientX - r.left) / r.width) * (N - 1))));
    setHiIdx(i);
  };
  const hp = hiIdx != null && data[hiIdx]
    ? { i: hiIdx, v: data[hiIdx].value, date: data[hiIdx].date, r: startValue ? ((data[hiIdx].value - startValue) / startValue) * 100 : null }
    : null;

  return (
    <div className="pv3-eq-wrap" onMouseLeave={() => setHiIdx(null)}>
      <div className="pv3-eq-r-head">
        <span className="pv3-t-footnote">
          Equity curve · since inception
          {startValue && totalValue ? ` · ${fmtPct1(((totalValue - startValue) / startValue) * 100)} total` : ''}
        </span>
        <div className="pv3-eq-seg">
          {PERIODS.map((p) => (
            <button key={p} className={`pv3-seg-btn ${period === p ? 'active' : ''}`} onClick={() => setPeriod(p)}>{p}</button>
          ))}
        </div>
      </div>
      {hp && (
        <div className="pv3-eq-tip" style={{ left: `${(xOf(hp.i) / W) * 100}%` }}>
          <b>{fmtLakh(hp.v)}</b>
          {hp.r != null && <span className={hp.r >= 0 ? 'num-bull' : 'num-bear'}>{fmtPct1(hp.r)}</span>}
          {hp.date && <span style={{ fontSize: 9, opacity: 0.7 }}>{hp.date}</span>}
        </div>
      )}
      <svg
        ref={svgRef}
        className="pv3-eq-svg"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        onMouseMove={onMove}
      >
        <defs>
          <linearGradient id="pv3EqFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--brand-hi, #4F8CFF)" stopOpacity="0.24" />
            <stop offset="100%" stopColor="var(--brand-hi, #4F8CFF)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((tv, i) => (
          <g key={i}>
            <line className="pv3-eq-grid" x1={padL} y1={yOf(tv)} x2={W - padR} y2={yOf(tv)} />
            <text className="pv3-eq-ax" x={W - padR + 6} y={yOf(tv) + 3}>
              {fmtLakh(tv).replace('.00', '')}
            </text>
          </g>
        ))}
        {/* Peak line */}
        <line className="pv3-eq-peak" x1={padL} y1={yOf(peakVal)} x2={W - padR} y2={yOf(peakVal)} />
        <text className="pv3-eq-peak-l" x={padL + 3} y={yOf(peakVal) - 4}>PEAK {fmtLakh(peakVal)}</text>
        {/* Equity fill + line */}
        <path d={areaPath} fill="url(#pv3EqFill)" />
        <path className="pv3-eq-line" d={linePath} />
        {/* Crosshair */}
        {hp && <line className="pv3-eq-cross" x1={xOf(hp.i)} y1={padT} x2={xOf(hp.i)} y2={H - padB} />}
        <circle
          cx={xOf(hp ? hp.i : N - 1)}
          cy={yOf(hp ? hp.v : vals[N - 1])}
          r="4"
          fill="var(--brand-hi, #4F8CFF)"
          stroke="#0a0e22"
          strokeWidth="1.5"
        />
      </svg>
      {xLabels.length > 0 && (
        <div className="pv3-eq-xax">
          {xLabels.map(({ i, label }) => (
            <span key={i}>{label}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 2 — EquityHero (fused: big number + 4 KPIs + curve)
// Big number: useOverview().portfolio.total_value
// Today's P&L: computed from holdings day_change×qty (Kite) or sum unrealised (paper)
// Cash: margins.available (Kite) or portfolio.cash (paper)
// Deployed %: invested/total_value
// Curve: useNavHistory or useOverview().equity_curve fallback
// ─────────────────────────────────────────────────────────────────────
function EquityHero({ portfolio, metrics, navHistory, paperHistory, isPaper, margins, holdings, paperPositions, isLoading }) {
  const [rper, setRper] = useState('MTD');
  const isLive = !isPaper;

  // Total equity (mode-appropriate value synthesized by the parent)
  const totalValue = portfolio?.total_value ?? null;

  // Today's P&L — computed from real data, never fabricated
  const todayPnL = useMemo(() => {
    if (isLive) {
      const list = holdings ?? [];
      const daySum = list.reduce((s, h) => s + (Number(h.day_change) || 0) * (Number(h.quantity) || 0), 0);
      if (daySum !== 0) return daySum;
      // All-zero → unrealised as fallback
      return list.reduce((s, h) => s + ((Number(h.last_price) || 0) - (Number(h.average_price) || 0)) * (Number(h.quantity) || 0), 0);
    }
    return (paperPositions ?? []).reduce((s, p) => s + (Number(p.unrealised_pnl) || 0), 0);
  }, [isLive, holdings, paperPositions]);

  const todayPnLPct = totalValue && totalValue > 0 ? (todayPnL / totalValue) * 100 : null;

  // Cash
  const cash = isLive
    ? (margins?.available ?? portfolio?.cash ?? null)
    : (portfolio?.cash ?? null);

  // Deployed %
  const invested = isLive
    ? (holdings ?? []).reduce((s, h) => s + (Number(h.last_price) || 0) * (Number(h.quantity) || 0), 0)
    : (portfolio?.invested ?? null);
  const deployedPct = totalValue && totalValue > 0 && invested != null ? (invested / totalValue) * 100 : null;

  // Equity history — MODE-GATED. Each view has its own series; mixing them
  // was the "paper chart shows the live account + nonsense % since inception"
  // bug. Paper → the ₹10L paper-broker ledger (paper-history); Live → the
  // real Kite NAV (nav-history). Never fall through from one to the other:
  // an empty paper series must render the honest empty state, NOT the live
  // account's NAV.
  const history = useMemo(() => {
    const rows = isPaper
      ? (paperHistory?.history ?? [])
      : (navHistory?.history ?? []);
    return Array.isArray(rows) ? rows : [];
  }, [isPaper, paperHistory, navHistory]);

  // Start value for the "since inception" %. Now guaranteed same-source as
  // `history` (and as `totalValue`, which the parent synthesizes per mode),
  // so the % no longer divides a paper total by a live starting NAV. For Paper,
  // prefer the server-provided baseline (₹10L INITIAL_CAPITAL) so this %
  // shares one denominator with the KPI total-return (F7) instead of using
  // history[0].value, which can drift to a non-baseline row after a deploy gap.
  const startValue = isPaper
    ? (paperHistory?.baseline ?? (history.length > 0 ? history[0].value : null))
    : (history.length > 0 ? history[0].value : null);

  // Realized P&L tabs — no MTD/YTD breakdown available from API
  // Showing total_return_pct as proxy, labelled honestly
  const totalReturnPct = portfolio?.total_return_pct ?? null;

  const upCount = isLive
    ? (holdings ?? []).filter((h) => (Number(h.day_change) || 0) > 0).length
    : (paperPositions ?? []).filter((p) => (Number(p.unrealised_pnl) || 0) > 0).length;
  const posCount = isLive ? (holdings ?? []).length : (paperPositions ?? []).length;

  return (
    <div className="pv3-card pv3-eq-hero">
      {/* Left: big number + 4 KPIs */}
      <div className="pv3-eqh-l">
        <div className="pv3-t-ui-micro">TOTAL EQUITY · MARK-TO-MARKET</div>
        {isLoading ? (
          <Skel w="60%" h={50} radius={8} />
        ) : (
          <div className="pv3-eqh-eq">{fmtLakh(totalValue)}</div>
        )}
        <div className="pv3-eqh-delta">
          {todayPnL !== 0 && todayPnL != null && (
            <span className={`pv3-tag ${todayPnL >= 0 ? 'pv3-tag-bull' : 'pv3-tag-bear'}`}>
              {fmtSignedINR(todayPnL)}
              {todayPnLPct != null && ` · ${fmtPct1(todayPnLPct)}`}
            </span>
          )}
          {totalReturnPct != null && (
            <span>
              Total <b className={totalReturnPct >= 0 ? 'num-bull' : 'num-bear'}>{fmtPct1(totalReturnPct)}</b>
            </span>
          )}
        </div>

        <div className="pv3-eqh-kpis">
          {/* KPI: Today's P&L */}
          <div className="pv3-eqh-kpi">
            <span className="pv3-ek-l">Today's P&amp;L</span>
            <span className={`pv3-ek-v ${todayPnL == null ? '' : todayPnL >= 0 ? 'num-bull' : 'num-bear'}`}>
              {isLoading ? '—' : fmtSignedINR(todayPnL)}
            </span>
            <span className="pv3-ek-s">
              {posCount > 0 ? `${upCount}/${posCount} up` : '—'}
            </span>
          </div>

          {/* KPI: Return % (total, labelled honestly — no MTD breakdown in API) */}
          <div className="pv3-eqh-kpi">
            <span className="pv3-ek-l">
              Total return
            </span>
            <span className={`pv3-ek-v ${totalReturnPct == null ? '' : totalReturnPct >= 0 ? 'num-bull' : 'num-bear'}`}>
              {isLoading ? '—' : fmtPct(totalReturnPct)}
            </span>
            <span className="pv3-ek-s">
              {metrics?.total_trades != null ? `${metrics.total_trades} trades` : '—'}
            </span>
          </div>

          {/* KPI: Deployed % */}
          <div className="pv3-eqh-kpi">
            <span className="pv3-ek-l">Deployed</span>
            <span className="pv3-ek-v">
              {isLoading || deployedPct == null ? '—' : `${deployedPct.toFixed(0)}%`}
            </span>
            <span className="pv3-ek-s">{invested != null ? fmtLakh(invested) : '—'}</span>
          </div>

          {/* KPI: Cash */}
          <div className="pv3-eqh-kpi">
            <span className="pv3-ek-l">Cash</span>
            <span className="pv3-ek-v">{isLoading ? '—' : fmtLakh(cash)}</span>
            <span className="pv3-ek-s">deployable</span>
          </div>
        </div>
      </div>

      {/* Right: equity curve */}
      <div className="pv3-eqh-r">
        {isLoading ? (
          <Skel w="100%" h={230} radius={8} />
        ) : (
          <EquityChartSvg
            history={history}
            totalValue={totalValue}
            startValue={startValue}
          />
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 3 — PerfRibbon
// Source: useOverview().metrics + portfolio.drawdown_pct
// All values from real hooks; source-tagged honestly (backtest vs live)
// ─────────────────────────────────────────────────────────────────────
function PerfRibbon({ metrics, portfolio, isLoading }) {
  const sharpe   = metrics?.sharpe_ratio   ?? null;
  const drawdown = portfolio?.drawdown_pct ?? null;
  const winRate  = metrics?.win_rate       ?? null;
  const avgWin   = metrics?.avg_win        ?? null;
  const avgLoss  = metrics?.avg_loss       ?? null;
  const totalTrades = metrics?.total_trades ?? null;

  const cells = [
    {
      label: 'Sharpe ratio',
      value: sharpe != null ? Number(sharpe).toFixed(2) : '—',
      src: 'paper',
    },
    {
      label: 'Max drawdown',
      value: drawdown != null ? fmtPct1(-Math.abs(drawdown)) : '—',
      src: 'paper',
    },
    {
      label: 'Win rate',
      value: winRate != null ? `${Number(winRate).toFixed(1)}%` : '—',
      src: 'paper',
    },
    {
      label: 'Avg win / loss',
      value: avgWin != null && avgLoss != null
        ? `${Number(avgWin).toFixed(1)}% / ${Number(avgLoss).toFixed(1)}%`
        : '—',
      src: 'paper',
    },
    {
      label: 'Track record',
      value: totalTrades != null ? `${totalTrades} trades` : '—',
      src: null,
    },
  ];

  const SRC_TAG = { live: 'LIVE', backtest: 'BACKTEST', paper: 'PAPER' };
  const SRC_CLS = { live: 'pv3-src-live', backtest: 'pv3-src-backtest', paper: 'pv3-src-paper' };

  return (
    <div className="pv3-perf-ribbon">
      {cells.map((c) => (
        <div key={c.label} className="pv3-prc">
          <span className="pv3-prc-l">{c.label}</span>
          <span className="pv3-prc-v">{isLoading ? '—' : c.value}</span>
          {c.src && (
            <span className={`pv3-prc-src ${SRC_CLS[c.src] || ''}`}>
              {SRC_TAG[c.src]}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 4 — RiskRibbon (kill guardrails, partial)
// Only 2 cells computable from available hooks:
//   1. Drawdown headroom (portfolio.drawdown_pct vs 15% kill)
//   2. Win-rate headroom (metrics.win_rate vs 45% kill)
// Other 3 cells (consecutive losses, single-day loss, days-without-signal)
// require backend kill-state endpoint — shown as "—" with honest label.
// TODO: kill-system state endpoint
// ─────────────────────────────────────────────────────────────────────
const KILL_DD_THRESHOLD  = 15; // % drawdown kill
const KILL_WR_THRESHOLD  = 45; // % rolling win-rate kill

function riskCell(value, fill, status) {
  return { value, fill: Math.min(1, Math.max(0, fill)), status };
}

function RiskRibbon({ portfolio, metrics, isLoading }) {
  const drawdownPct = portfolio?.drawdown_pct ?? null;
  const winRate     = metrics?.win_rate       ?? null;

  const ddAbs  = drawdownPct != null ? Math.abs(Number(drawdownPct)) : null;
  const ddFill = ddAbs != null ? ddAbs / KILL_DD_THRESHOLD : null;
  const ddStatus = ddFill == null ? 'unknown'
    : ddFill >= 1 ? 'hard'
    : ddFill >= 0.75 ? 'soft'
    : 'ok';
  const ddValue = ddAbs != null ? `−${ddAbs.toFixed(1)}%` : '—';

  const wrFill = winRate != null
    ? Math.max(0, (KILL_WR_THRESHOLD - Number(winRate)) / KILL_WR_THRESHOLD)
    : null;
  const wrStatus = wrFill == null ? 'unknown'
    : wrFill >= 0.9 ? 'hard'
    : wrFill >= 0.6 ? 'soft'
    : 'ok';
  const wrValue = winRate != null ? `${Number(winRate).toFixed(0)}%` : '—';

  const cells = [
    { name: 'Drawdown',       ...riskCell(ddValue, ddFill ?? 0, ddStatus) },
    { name: 'Rolling-20 WR',  ...riskCell(wrValue, wrFill ?? 0, wrStatus) },
    // These three require the kill-system state endpoint — not available in frontend hooks
    { name: 'Consec. losses', ...riskCell('—', 0, 'unknown') },
    { name: 'Single-day loss', ...riskCell('—', 0, 'unknown') },
    { name: 'Days w/o signal', ...riskCell('—', 0, 'unknown') },
  ];

  const worst = cells.reduce((w, c) => {
    if (c.status === 'hard') return 'hard';
    if (c.status === 'soft' && w !== 'hard') return 'soft';
    return w;
  }, 'ok');

  const overallWord = worst === 'hard' ? 'HARD KILL' : worst === 'soft' ? 'SOFT WARNING' : 'ALL CLEAR';
  const overallCls  = worst === 'hard' ? 'kw-hard' : worst === 'soft' ? 'kw-soft' : 'kw-ok';

  return (
    <div className="pv3-card pv3-risk-card">
      <div className="pv3-card-head">
        <div>
          <div className="pv3-t-ui-headline">
            Risk guardrails
            <span className="pv3-partial-note"> (partial — live kill-state endpoint pending)</span>
          </div>
          {/* TODO: kill-system state endpoint */}
          <div className="pv3-t-ui-footnote">
            2 of 5 limits computed · 3 need backend kill-state API
          </div>
        </div>
        <span className={`pv3-kw ${overallCls}`}>{overallWord}</span>
      </div>
      <div className="pv3-risk-cells">
        {cells.map((k) => (
          <div key={k.name} className={`pv3-rc pv3-rc-${k.status} ${k.status === 'soft' || k.status === 'hard' ? 'pv3-rc-pulse' : ''}`}>
            <div className="pv3-rc-name">{k.name}</div>
            <div className="pv3-rc-val">
              {isLoading ? '—' : k.value}
            </div>
            <div className="pv3-rc-bar">
              <span style={{ width: k.status === 'unknown' ? '0%' : Math.round(k.fill * 100) + '%' }} />
            </div>
            <div className="pv3-rc-pct">
              {k.status === 'unknown'
                ? 'not tracked yet'
                : `${Math.round(k.fill * 100)}% to kill`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 5 — MonthlyPnl
// Client-side: bucket useTrades() by exit_date month, sum return_pct
// Axis label: "monthly realised return %" (honest — qty not in trade shape)
// TODO: monthly P&L endpoint or position-size on trades
// ─────────────────────────────────────────────────────────────────────
function MonthlyPnl({ trades, isLoading }) {
  const data = useMemo(() => {
    if (!trades || trades.length === 0) return [];
    const byMonth = new Map();
    for (const t of trades) {
      const dateStr = t.exit_date || t.entry_date || '';
      if (!dateStr) continue;
      const month = dateStr.slice(0, 7); // YYYY-MM
      const existing = byMonth.get(month) || { month, sumRetPct: 0, count: 0 };
      existing.sumRetPct += Number(t.return_pct) || 0;
      existing.count += 1;
      byMonth.set(month, existing);
    }
    return Array.from(byMonth.values())
      .sort((a, b) => a.month.localeCompare(b.month))
      .slice(-12) // last 12 months
      .map((m) => ({
        label: new Date(m.month + '-01').toLocaleString('en-IN', { month: 'short' }),
        value: m.sumRetPct, // sum of return_pct
      }));
  }, [trades]);

  const posMonths = data.filter((d) => d.value >= 0).length;
  const maxAbs = data.length > 0 ? Math.max(...data.map((d) => Math.abs(d.value))) || 1 : 1;

  return (
    <div className="pv3-card">
      <div className="pv3-card-head">
        <div>
          <div className="pv3-t-ui-headline">Monthly realised return</div>
          {/* TODO: monthly P&L endpoint or position-size on trades */}
          <div className="pv3-t-ui-footnote">
            {isLoading
              ? 'Loading…'
              : data.length > 0
                ? `model track record · sum of return %/mo · ${posMonths}/${data.length} +ve`
                : 'No closed trades — chart populates after first signal closes'}
          </div>
        </div>
      </div>
      {!isLoading && data.length === 0 ? (
        <div className="pv3-monthly-empty">
          No closed trade data yet. Return % by month appears here as signals close.
        </div>
      ) : (
        <div className="pv3-mp-chart">
          <div className="pv3-mp-baseline" />
          {isLoading
            ? Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="pv3-mp-col">
                  <div className="pv3-mp-bar-wrap">
                    <span className="pv3-mp-bar b-up pv3-skel" style={{ bottom: '50%', height: '20%' }} />
                  </div>
                  <div className="pv3-mp-m" />
                </div>
              ))
            : data.map((d) => {
                const h = (Math.abs(d.value) / maxAbs) * 48;
                const up = d.value >= 0;
                return (
                  <div
                    key={d.label}
                    className="pv3-mp-col"
                    title={`${d.label} · ${d.value >= 0 ? '+' : ''}${d.value.toFixed(2)}%`}
                  >
                    <div className="pv3-mp-bar-wrap">
                      <span
                        className={`pv3-mp-bar ${up ? 'b-up' : 'b-dn'}`}
                        style={up ? { bottom: '50%', height: h + '%' } : { top: '50%', height: h + '%' }}
                      />
                    </div>
                    <div className="pv3-mp-m">{d.label}</div>
                  </div>
                );
              })}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 6 — HoldingsTable
// Kite connected: useKiteHoldings()
// Kite off: usePaperPositions()
// P&L column: value on ONE line, % stacked below-right (pcol/pf-pnl-v/pf-pnl-p)
// Alloc column: mini bar + % stacked (acol/al-mini/al-n)
// Status: sell-target / sell-stop / hold derived from hold_days vs target proximity
// ─────────────────────────────────────────────────────────────────────

// Status chip map — derived from row data since status isn't a Kite field
function deriveHoldingStatus(row) {
  if (row._status) return row._status;
  // Paper positions may have a status indicator from the signal
  return 'hold';
}

// Derive the Holdings "Status" chip for a paper position from the LIVE model
// state. The backend joins each position to signals_history and attaches
// `signal_status` (the cron's track_signals re-evaluates every held signal
// daily), so the chip is no longer a static "HOLD" — it shows when the model
// has flagged an exit (the broker then sells the next session). Falls back to
// a price-vs-target/stop proximity check for positions written before the
// status field existed.
function derivePaperStatus(h) {
  const st = String(h.signal_status || '').toUpperCase();
  if (st === 'HIT_STOP') return 'sell-stop';
  if (st === 'HIT_TARGET' || st === 'NEAR_TARGET') return 'sell-target';
  if (st === 'EXPIRED') return 'sell-time';
  if (st === 'ACTIVE') return 'hold';
  // No status yet → approximate from price vs the model's target / stop.
  const ltp = Number(h.current_price) || 0;
  const tgt = Number(h.target) || 0;
  const stp = Number(h.atr_stop ?? h.stop) || 0;
  if (tgt > 0 && ltp >= tgt) return 'sell-target';
  if (stp > 0 && ltp <= stp) return 'sell-stop';
  return 'hold';
}

const HOLDING_STATUS_LABELS = {
  'hold':        ['HOLD',        'pv3-sp-hold'],
  'sell-target': ['SELL · TGT',  'pv3-sp-tgt'],
  'sell-stop':   ['SELL · STP',  'pv3-sp-stp'],
  'sell-time':   ['EXIT · TIME', 'pv3-sp-hold'],
};

function HoldingsTable({ holdings, isPaper, totalEquity, isLoading }) {
  const [activeTab, setActiveTab] = useState('all');

  const rows = useMemo(() => {
    if (!holdings || holdings.length === 0) return [];

    if (isPaper) {
      return holdings.map((h, i) => {
        const qty = Number(h.shares) || 0;
        const avg = Number(h.entry_price) || 0;
        const ltp = Number(h.current_price) || 0;
        const value = Number(h.current_value) || qty * ltp;
        const pnl = h.unrealised_pnl != null ? Number(h.unrealised_pnl) : (value - qty * avg);
        // Use the ledger's cost-basis return so the % AGREES with the ₹ figure
        // (both fee-inclusive). Recomputing (ltp-avg)/avg gave a price-only %
        // that contradicted the fee-inclusive ₹ — e.g. the "−₹45 / +0.00%" row.
        const pnlPct = h.unrealised_pnl_pct != null
          ? Number(h.unrealised_pnl_pct)
          : (avg > 0 ? ((ltp - avg) / avg) * 100 : 0);
        return {
          id: `paper-${h.ticker || i}`,
          sym: h.ticker || '—',
          sector: h.sector || 'Other',
          qty,
          avg,
          ltp,
          value,
          day: null,
          pnl,
          pnlPct,
          _status: derivePaperStatus(h),
        };
      });
    }

    // Kite holdings shape
    return holdings.map((h, i) => {
      const qty = Number(h.quantity) || 0;
      const avg = Number(h.average_price) || 0;
      const ltp = Number(h.last_price) || 0;
      const value = ltp * qty;
      const pnl = (ltp - avg) * qty;
      const pnlPct = avg > 0 ? ((ltp - avg) / avg) * 100 : 0;
      const dayChg = h.day_change != null ? (Number(h.day_change) / ltp) * 100 : (h.day_change_percentage ?? null);
      return {
        id: h.tradingsymbol || `kite-${i}`,
        sym: h.tradingsymbol || '—',
        sector: h.sector || 'Other',
        qty,
        avg,
        ltp,
        value,
        day: dayChg,
        pnl,
        pnlPct,
        _status: 'hold',
      };
    });
  }, [holdings, isPaper]);

  const totalValue = totalEquity || rows.reduce((s, r) => s + r.value, 0);

  const filtered = useMemo(() => {
    if (activeTab === 'winners') return rows.filter((r) => r.pnl >= 0);
    if (activeTab === 'to-exit') return rows.filter((r) => r._status !== 'hold');
    return rows;
  }, [rows, activeTab]);

  return (
    <div className="pv3-stocks-table">
      <div className="pv3-stocks-table-head">
        <div>
          <div className="pv3-t-ui-headline">Holdings</div>
          <div className="pv3-t-ui-footnote">
            {isLoading
              ? 'Loading…'
              : rows.length > 0
                ? `${rows.length} open · ${isPaper ? 'paper portfolio' : 'synced with Kite'}`
                : isPaper
                  ? 'No paper positions yet'
                  : 'Connect Kite to see live holdings'}
          </div>
        </div>
        <div className="pv3-stocks-table-tabs">
          {['all', 'winners', 'to-exit'].map((t) => (
            <button key={t} className={`pv3-ttab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
              {t === 'to-exit' ? 'To exit' : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="pv3-htbl">
        {/* Headers */}
        <div className="pv3-th">Company</div>
        <div className="pv3-th pv3-th-r">Qty</div>
        <div className="pv3-th pv3-th-r">Avg</div>
        <div className="pv3-th pv3-th-r">LTP</div>
        <div className="pv3-th pv3-th-r">Value</div>
        <div className="pv3-th pv3-th-r">Day</div>
        <div className="pv3-th pv3-th-r">Unreal. P&amp;L</div>
        <div className="pv3-th pv3-th-r">Alloc</div>
        <div className="pv3-th pv3-th-r">Status</div>

        {isLoading ? (
          <div style={{ gridColumn: '1 / -1', padding: '24px 18px' }}>
            <Skel w="40%" h={14} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="pv3-holdings-empty" style={{ gridColumn: '1 / -1' }}>
            {rows.length === 0
              ? (isPaper ? 'No paper positions yet.' : 'Connect Kite to see your holdings here.')
              : `No ${activeTab === 'to-exit' ? 'exit candidates' : activeTab} right now.`}
          </div>
        ) : (
          filtered.map((r) => {
            const alloc = totalValue > 0 ? (r.value / totalValue) * 100 : 0;
            const sp = HOLDING_STATUS_LABELS[r._status] || HOLDING_STATUS_LABELS['hold'];
            return (
              <React.Fragment key={r.id}>
                <div className="pv3-td pv3-td-name">
                  <Logo sym={r.sym} size={32} radius={8} />
                  <div>
                    <div className="pv3-td-name-sym">{r.sym}</div>
                    <div className="pv3-td-name-full">{r.sector}</div>
                  </div>
                </div>
                <div className="pv3-td pv3-td-r tabular-nums">{Math.round(r.qty)}</div>
                <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--text-3)' }}>
                  {fmtNum(r.avg)}
                </div>
                <div className="pv3-td pv3-td-r tabular-nums">{fmtNum(r.ltp)}</div>
                <div className="pv3-td pv3-td-r tabular-nums">{fmtLakh(r.value)}</div>
                <div
                  className="pv3-td pv3-td-r tabular-nums"
                  style={{ color: r.day == null ? 'var(--text-4)' : r.day >= 0 ? 'var(--bull)' : 'var(--bear)' }}
                >
                  {r.day != null ? fmtPct(r.day) : '—'}
                </div>
                {/* P&L: value on one line, % stacked below-right */}
                <div className="pv3-td pv3-td-r tabular-nums" style={{ color: r.pnl >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
                  <div className="pv3-pcol">
                    <span className="pv3-pnl-v">{fmtSignedINR(r.pnl)}</span>
                    <span className="pv3-pnl-p">{fmtPct(r.pnlPct)}</span>
                  </div>
                </div>
                {/* Alloc: mini bar + % stacked cleanly */}
                <div className="pv3-td pv3-td-r">
                  <div className="pv3-acol">
                    <span className="pv3-al-mini">
                      <span style={{ width: Math.min(100, alloc * 2.6) + '%' }} />
                    </span>
                    <span className="pv3-al-n tabular-nums">{alloc.toFixed(1)}%</span>
                  </div>
                </div>
                <div className="pv3-td pv3-td-r">
                  <span className={`pv3-spill ${sp[1]}`}>{sp[0]}</span>
                </div>
              </React.Fragment>
            );
          })
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 7 — AllocCard
// Groups holdings by sector, adds Cash slice
// Colors: sector palette mapped from canonical sectors
// ─────────────────────────────────────────────────────────────────────
const SECTOR_HEX = {
  'Capital Goods': '#5BC7FF',
  'Financials': '#4F8CFF',
  'Finance': '#4F8CFF',
  'Pharma': '#3FDD8A',
  'Healthcare': '#3FDD8A',
  'Auto': '#FFB454',
  'Automobile': '#FFB454',
  'IT': '#A78BFA',
  'Technology': '#A78BFA',
  'Energy': '#FF7F50',
  'Metal': '#94A3B8',
  'FMCG': '#F9A8D4',
  'Consumer': '#FCD34D',
  'Cement': '#78716C',
  'Realty': '#FB923C',
  'Other': '#5A6488',
  'Cash': '#5A6488',
};

function sectorColor(name) {
  return SECTOR_HEX[name] || '#5A6488';
}

function AllocCard({ holdings, cash, totalEquity, isPaper, isLoading }) {
  const rows = useMemo(() => {
    if (!holdings || holdings.length === 0) return [];

    const by = {};
    for (const h of holdings) {
      const sector = h.sector || 'Other';
      const value = isPaper
        ? (Number(h.current_value) || (Number(h.shares) || 0) * (Number(h.current_price) || 0))
        : (Number(h.last_price) || 0) * (Number(h.quantity) || 0);
      by[sector] = (by[sector] || 0) + value;
    }

    const totalInvested = Object.values(by).reduce((s, v) => s + v, 0);
    const equity = totalEquity || (totalInvested + (cash || 0));

    const result = Object.entries(by).map(([name, v]) => ({
      name,
      v,
      pct: equity > 0 ? (v / equity) * 100 : 0,
    }));

    if (cash != null && cash > 0) {
      result.push({ name: 'Cash', v: cash, pct: equity > 0 ? (cash / equity) * 100 : 0 });
    }

    return result.sort((a, b) => b.v - a.v);
  }, [holdings, cash, totalEquity, isPaper]);

  const equityLabel = totalEquity != null ? fmtLakh(totalEquity) : '—';
  const posCount = holdings?.length ?? 0;

  return (
    <div className="pv3-card">
      <div className="pv3-card-head">
        <div>
          <div className="pv3-t-ui-headline">Allocation</div>
          <div className="pv3-t-ui-footnote">% of equity · {posCount} position{posCount !== 1 ? 's' : ''}</div>
        </div>
        <span className="pv3-t-num-small pv3-dim">{equityLabel}</span>
      </div>

      {isLoading ? (
        <Skel w="100%" h={16} radius={8} />
      ) : rows.length === 0 ? (
        <div className="pv3-alloc-empty">
          {isPaper ? 'No paper positions yet.' : 'Connect Kite to see allocation.'}
        </div>
      ) : (
        <>
          <div className="pv3-alloc-stack">
            {rows.map((r) => (
              <span
                key={r.name}
                style={{ width: r.pct + '%', background: sectorColor(r.name) }}
                title={`${r.name} ${r.pct.toFixed(1)}%`}
              />
            ))}
          </div>
          <div className="pv3-alloc-list">
            {rows.map((r) => (
              <div key={r.name} className="pv3-al-row">
                <span className="pv3-al-dot" style={{ background: sectorColor(r.name) }} />
                <span className="pv3-al-name">{r.name}</span>
                <span className="pv3-al-pct pv3-t-num-small">{r.pct.toFixed(1)}%</span>
                <span className="pv3-al-val pv3-t-num-small pv3-dim">{fmtLakh(r.v)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SECTION 8 — ClosedCard
// Source: useTrades() first 5 entries, exit_reason → reason styling
// P&L: return_pct from real trade data (qty not in shape — labelled as %)
// ─────────────────────────────────────────────────────────────────────
const RSN_MAP = {
  target:     ['TGT',  'won'],
  hit_target: ['TGT',  'won'],
  HIT_TARGET: ['TGT',  'won'],
  stop:       ['STP',  'lost'],
  hit_stop:   ['STP',  'lost'],
  HIT_STOP:   ['STP',  'lost'],
  time:       ['TIME', 'neu'],
  expired:    ['TIME', 'neu'],
  EXPIRED:    ['TIME', 'neu'],
};

function ClosedCard({ trades, isLoading }) {
  const recent = useMemo(() => (trades ?? []).slice(0, 5), [trades]);

  const totalRetPct = recent.reduce((s, t) => s + (Number(t.return_pct) || 0), 0);

  return (
    <div className="pv3-card">
      <div className="pv3-card-head">
        <div>
          <div className="pv3-t-ui-headline">Recently closed</div>
          <div className="pv3-t-ui-footnote">model track record · last {recent.length} trades</div>
        </div>
        {recent.length > 0 && (
          <span className={`pv3-t-num-small ${totalRetPct >= 0 ? 'num-bull' : 'num-bear'}`}>
            {fmtPct(totalRetPct)} combined
          </span>
        )}
      </div>

      {isLoading ? (
        Array.from({ length: 3 }).map((_, i) => <Skel key={i} w="100%" h={32} radius={6} />)
      ) : recent.length === 0 ? (
        <div className="pv3-closed-empty">No closed trades yet.</div>
      ) : (
        <div className="pv3-closed-list">
          {recent.map((t, i) => {
            const reason = t.exit_reason || '';
            const r = RSN_MAP[reason] || RSN_MAP[reason.toLowerCase()] || ['—', 'neu'];
            const retPct = Number(t.return_pct) ?? null;
            return (
              <div key={`${t.ticker}-${t.exit_date}-${i}`} className="pv3-cl-row">
                <Logo sym={t.ticker} size={26} radius={6} />
                <span className="pv3-cl-sym">{t.ticker}</span>
                <span className={`pv3-cl-rsn ${r[1]}`}>{r[0]}</span>
                <span className="pv3-cl-held pv3-t-num-small pv3-dim">
                  {t.hold_days != null ? `${Math.round(t.hold_days)}d` : '—'}
                </span>
                <span className={`pv3-cl-pnl pv3-t-num-small ${retPct == null ? '' : retPct >= 0 ? 'num-bull' : 'num-bear'}`}>
                  {retPct != null ? fmtPct(retPct) : '—'}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────────
export default function PortfolioV3() {
  const kite = useContext(KiteContext);
  const kiteConnected = !!kite?.connected;

  // Two views only: Paper (the model's paper portfolio) and Live (real Kite
  // account). The selector defaults to Live when Kite is connected, else
  // Paper — and follows the connection until the user picks explicitly.
  const [modeOverride, setModeOverride] = useState(null);
  const mode = modeOverride ?? (kiteConnected ? 'live' : 'paper');
  const isPaper = mode === 'paper';

  const overviewQuery   = useOverview();
  const navHistoryQuery = useNavHistory();          // live Kite NAV (Live view)
  const paperHistoryQuery = usePaperHistory();      // ₹10L paper-broker ledger (Paper view)
  const holdingsQuery   = useKiteHoldings({ enabled: kiteConnected });
  const marginsQuery    = useKiteMargins({ enabled: kiteConnected });
  const paperQuery      = usePaperPositions(); // always on — Paper view works regardless of Kite
  const tradesQuery     = useTrades({ perPage: 50 });
  const signalsQuery    = useSignals();

  // Stable references so the view useMemo below doesn't recompute every render.
  const paperPortfolio = useMemo(() => overviewQuery.data?.portfolio ?? {}, [overviewQuery.data]);
  const metrics    = useMemo(() => overviewQuery.data?.metrics ?? {}, [overviewQuery.data]);
  const regime     = signalsQuery.data?.regime ?? {};
  const navHistory = navHistoryQuery.data ?? null;
  const paperHistory = paperHistoryQuery.data ?? null;

  const kiteHoldings = useMemo(() => holdingsQuery.data ?? [], [holdingsQuery.data]);
  const paperPos     = useMemo(() => paperQuery.data ?? [], [paperQuery.data]);
  const margins      = marginsQuery.data ?? null;

  // Synthesize a single view-model so every section reads uniform fields,
  // whichever mode is active. Live figures are computed from REAL Kite data
  // (never the paper ₹10L); paper figures come from the overview hook.
  const view = useMemo(() => {
    if (isPaper) {
      return {
        holdings: paperPos,
        portfolio: paperPortfolio,
        cash: paperPortfolio?.cash ?? null,
        totalEquity: paperPortfolio?.total_value ?? null,
      };
    }
    const mktValue = kiteHoldings.reduce((s, h) => s + (Number(h.last_price) || 0) * (Number(h.quantity) || 0), 0);
    const cost     = kiteHoldings.reduce((s, h) => s + (Number(h.average_price) || 0) * (Number(h.quantity) || 0), 0);
    const liveCash = margins?.available ?? null;
    const total    = liveCash != null ? mktValue + liveCash : (mktValue || null);
    const livePortfolio = {
      total_value: total,
      cash: liveCash,
      invested: mktValue || null,
      total_return_pct: cost > 0 ? ((mktValue - cost) / cost) * 100 : null,
      drawdown_pct: null,          // not computable without a live NAV peak
      n_positions: kiteHoldings.length || null,
    };
    return { holdings: kiteHoldings, portfolio: livePortfolio, cash: liveCash, totalEquity: total };
  }, [isPaper, paperPos, paperPortfolio, kiteHoldings, margins]);

  const activeHoldings = view.holdings;
  const cash           = view.cash;
  const totalEquity    = view.totalEquity;

  // Trades (flatten infinite query)
  const trades = useMemo(() => flattenTrades(tradesQuery.data), [tradesQuery.data]);

  const isOverviewLoading = overviewQuery.isLoading;
  const isHoldingsLoading = isPaper ? paperQuery.isLoading : holdingsQuery.isLoading;
  const liveDisconnected = !isPaper && !kiteConnected;

  return (
    <div className="pv3-page density-regular">

      {/* StateStrip */}
      <StateStrip
        kiteConnected={!isPaper}
        regime={regime}
        drawdownPct={view.portfolio?.drawdown_pct}
      />

      {/* Page title + Paper/Live selector */}
      <section className="pv3-row pv3-head-row">
        <div className="pv3-row-head">
          <div>
            <div className="pv3-t-ui-micro">PORTFOLIO · MONITORING</div>
            <h2 className="pv3-row-title">Portfolio</h2>
            <div className="pv3-t-ui-footnote">
              {isPaper
                ? 'Paper portfolio · model-traded, no real capital'
                : kiteConnected
                  ? 'Live mark-to-market · Kite connected'
                  : 'Live view · connect Kite to populate'}
            </div>
          </div>
          <div className="pv3-mode-toggle" role="tablist" aria-label="Portfolio view">
            <button
              role="tab"
              aria-selected={isPaper}
              className={`pv3-mode-btn ${isPaper ? 'active' : ''}`}
              onClick={() => setModeOverride('paper')}
            >
              Paper
            </button>
            <button
              role="tab"
              aria-selected={!isPaper}
              className={`pv3-mode-btn ${!isPaper ? 'active' : ''}`}
              onClick={() => setModeOverride('live')}
            >
              Live
            </button>
          </div>
        </div>
      </section>

      {/* Live-but-disconnected prompt */}
      {liveDisconnected && (
        <section className="pv3-row">
          <div className="pv3-connect-banner">
            <span>Connect your Zerodha Kite account to see live holdings, cash and P&amp;L.</span>
            <button className="pv3-connect-btn" onClick={kite?.connect}>
              <Icon.Plug width="13" height="13" />
              Connect Kite
            </button>
          </div>
        </section>
      )}

      {/* EquityHero */}
      <section className="pv3-row">
        <EquityHero
          portfolio={view.portfolio}
          metrics={metrics}
          navHistory={navHistory}
          paperHistory={paperHistory}
          isPaper={isPaper}
          margins={margins}
          holdings={view.holdings}
          paperPositions={isPaper ? paperPos : []}
          isLoading={isOverviewLoading}
        />
      </section>

      {/* PerfRibbon — model track record (mode-agnostic) */}
      <section className="pv3-row">
        <PerfRibbon
          metrics={metrics}
          portfolio={view.portfolio}
          isLoading={isOverviewLoading}
        />
      </section>

      {/* RiskRibbon */}
      <section className="pv3-row">
        <RiskRibbon
          portfolio={view.portfolio}
          metrics={metrics}
          isLoading={isOverviewLoading}
        />
      </section>

      {/* MonthlyPnl */}
      <section className="pv3-row">
        <MonthlyPnl
          trades={trades}
          isLoading={tradesQuery.isLoading}
        />
      </section>

      {/* Holdings + Right rail (AllocCard + ClosedCard) */}
      <section className="pv3-row pv3-row-data">
        <HoldingsTable
          holdings={activeHoldings}
          isPaper={isPaper}
          totalEquity={totalEquity}
          isLoading={isHoldingsLoading}
        />
        <aside className="pv3-right-rail">
          <AllocCard
            holdings={activeHoldings}
            cash={cash}
            totalEquity={totalEquity}
            isPaper={isPaper}
            isLoading={isHoldingsLoading}
          />
          <ClosedCard
            trades={trades}
            isLoading={tradesQuery.isLoading && trades.length === 0}
          />
        </aside>
      </section>

      {/* Footer */}
      <footer className="pv3-foot">
        <div className="pv3-disclaimer">{DISCLAIMER}</div>
        <div className="pv3-foot-meta">
          SEBI Research Analyst · Model-generated signals · Research output only · v2026.06
        </div>
      </footer>
    </div>
  );
}
