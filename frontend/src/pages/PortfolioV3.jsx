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
 *
 * Compliance: no "guarantee", "will", "sure", "sure-shot" in client-facing strings.
 * DISCLAIMER footer sourced from @/lib/signalCopy.
 */

import React, { useState, useMemo } from 'react';
import { useOverview } from '@/hooks/queries/useOverview';
import { useNavHistory } from '@/hooks/queries/useNavHistory';
import { usePaperHistory } from '@/hooks/queries/usePaperHistory';
import { usePaperPositions } from '@/hooks/queries/usePaperPositions';
import { useExecutionPositions, useReconciliation } from '@/hooks/queries/useExecution';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import { useTrades, flattenTrades } from '@/hooks/queries/useTrades';
import { useSignals } from '@/hooks/queries/useSignals';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/portfolio-v3.css';

// A self-reported ledger position (Stage 4) joined to an owner quote, mapped to the same shape the
// page's "your holdings" sections read. Cost basis + realized P&L are the ledger's truth; the current
// price is the owner's live quote. No cash / total-NAV is fabricated (ADR 0011 — we don't hold the
// user's broker balance), so value = Σ(remaining × quote) only.
function ledgerHoldingToRow(pos, quotes) {
  const q = quotes?.[(pos.ticker || '').toUpperCase()] || null;
  const avg = Number(pos.avg_buy_price) || 0;
  const ltp = q?.last_price != null ? Number(q.last_price) : avg;   // fall back to cost if no quote yet
  return {
    tradingsymbol: pos.ticker,
    sector: pos.sector || 'Other',
    quantity: Number(pos.remaining_qty) || 0,
    average_price: avg,
    last_price: ltp,
    day_change_percentage: q?.change_pct ?? null,
    product: 'SELF',
  };
}

// Outstanding reconciliation items (Stage 4b): what the model plan expects of the user's held names
// that their ledger doesn't yet reflect. Severity mirrors the P cadence (high/action/warn/info).
function ActionItemsStrip({ items }) {
  if (!items || items.length === 0) return null;
  const sevCls = { high: 'num-bear', action: 'num-bull', warn: 'num-warn', info: 'num-info' };
  return (
    <div className="pv3-actions-strip">
      <div className="pv3-actions-head">
        <span className="pv3-t-ui-micro">OUTSTANDING · MODEL vs YOUR LEDGER</span>
        <span className="pv3-t-ui-footnote">{items.length} to reconcile · record the fill to clear it</span>
      </div>
      <ul className="pv3-actions-list">
        {items.slice(0, 6).map((it, i) => (
          <li key={`${it.signal_id}-${it.type}-${i}`} className="pv3-action-item">
            <span className={`pv3-action-dot ${sevCls[it.severity] || 'num-info'}`} />
            <span className="pv3-action-sym">{it.ticker}</span>
            <span className="pv3-action-msg">{it.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// A CLOSED ledger position mapped to the closed-trades table shape (realized figures from the ledger).
function ledgerClosedToTrade(pos) {
  const avg = Number(pos.avg_buy_price) || 0;
  const pnl = Number(pos.realized_pnl) || 0;
  const qty = Number(pos.total_sold_qty) || Number(pos.total_bought_qty) || 0;
  const exit = avg > 0 && qty > 0 ? avg + pnl / qty : avg;          // implied avg exit from realized P&L
  const day = pos.last_event_at ? String(pos.last_event_at).slice(0, 10) : null;
  return {
    ticker: pos.ticker, qty, entry_price: avg, exit_price: Number(exit.toFixed(2)),
    return_pct: pos.realized_pnl_pct ?? null, net_pnl: pnl,
    entry_date: null, exit_date: day, hold_days: null, exit_reason: 'self-reported',
  };
}

// ─────────────────────────────────────────────────────────────────────
// Formatters
// ─────────────────────────────────────────────────────────────────────
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
  WIPRO: 'wipro.com', HINDUNILVR: 'hul.co.in',
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
        {/* kiteConnected is repurposed as "is the user's own book" (true) vs the model paper ref (false). */}
        <span className={`pv3-live-dot ${!kiteConnected ? 'pv3-dot-info' : ''}`} />
        <span className="pv3-regime-eyebrow">
          {kiteConnected ? 'YOURS' : 'PAPER'}
        </span>
        <span className="pv3-regime-statement">
          Showing{' '}
          <em className={kiteConnected ? 'num-bull' : 'num-info'}>
            {kiteConnected ? 'your holdings' : "the model's paper book"}
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
        product: h.product || 'CNC',
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
                ? `${rows.length} open · ${isPaper ? 'model paper book' : 'your self-reported holdings'}`
                : isPaper
                  ? 'No paper positions yet'
                  : 'No holdings recorded yet'}
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
              ? (isPaper ? 'No paper positions yet.' : 'No holdings yet — record a buy from the Research page.')
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
                    <div className="pv3-td-name-full">{r.sector}{r.product === 'MTF' ? ' · MTF' : ''}</div>
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

    // Allocation is computed on INVESTED CAPITAL (cost basis: qty x avg
    // price), not current market value — so a position doubling in price
    // doesn't visually inflate "how much of my capital did I put here",
    // and this bar reflects the actual sizing decision, not price drift.
    const by = {};
    for (const h of holdings) {
      const sector = h.sector || 'Other';
      const invested = isPaper
        ? (Number(h.shares) || 0) * (Number(h.entry_price) || 0)
        : (Number(h.quantity) || 0) * (Number(h.average_price) || 0);
      by[sector] = (by[sector] || 0) + invested;
    }

    const totalInvested = Object.values(by).reduce((s, v) => s + v, 0);
    const totalCapital = totalInvested + (cash || 0);

    const result = Object.entries(by).map(([name, v]) => ({
      name,
      v,
      pct: totalCapital > 0 ? (v / totalCapital) * 100 : 0,
    }));

    if (cash != null && cash > 0) {
      result.push({ name: 'Cash', v: cash, pct: totalCapital > 0 ? (cash / totalCapital) * 100 : 0 });
    }

    return result.sort((a, b) => b.v - a.v);
  }, [holdings, cash, isPaper]);

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
          {isPaper ? 'No paper positions yet.' : 'No holdings to allocate yet.'}
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
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────
// Paper sub-tabs — Positions / Closed Trades / Activity (+ P&L strips)
// ─────────────────────────────────────────────────────────────────────
// exit_reason → [chip label, tone]. Consumed by reasonChip below.
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

function reasonChip(reason) {
  const k = String(reason || '');
  if (RSN_MAP[k]) return RSN_MAP[k];
  if (RSN_MAP[k.toLowerCase()]) return RSN_MAP[k.toLowerCase()];
  if (k.toLowerCase().includes('trail')) return ['TRAIL', 'won'];
  return ['—', 'neu'];
}

function PnlStat({ label, value, sub, tone }) {
  return (
    <div className="pv3-pstat">
      <div className="pv3-pstat-l">{label}</div>
      <div className={`pv3-pstat-v ${tone || ''}`}>{value}</div>
      {sub != null && <div className="pv3-pstat-s">{sub}</div>}
    </div>
  );
}

function UnrealizedStrip({ holdings, isPaper }) {
  const s = useMemo(() => {
    const rows = (holdings || []).map((h) => ({
      sym: h.ticker || h.tradingsymbol || '—',
      pnl: isPaper
        ? Number(h.unrealised_pnl) || 0
        : ((Number(h.last_price) || 0) - (Number(h.average_price) || 0)) * (Number(h.quantity) || 0),
    }));
    const total = rows.reduce((a, r) => a + r.pnl, 0);
    const invested = (holdings || []).reduce(
      (a, h) => a + (Number(h.current_value ?? (Number(h.last_price) || 0) * (Number(h.quantity) || 0)) || 0), 0);
    const winners = rows.filter((r) => r.pnl > 0).length;
    const best = rows.length ? rows.reduce((a, b) => (b.pnl > a.pnl ? b : a)) : null;
    const worst = rows.length ? rows.reduce((a, b) => (b.pnl < a.pnl ? b : a)) : null;
    return { total, invested, n: rows.length, winners, best, worst };
  }, [holdings, isPaper]);
  return (
    <div className="pv3-pnl-strip">
      <PnlStat label="Unrealised P&L" value={fmtSignedINR(s.total)} tone={s.total >= 0 ? 'num-bull' : 'num-bear'}
               sub={s.invested > 0 ? fmtPct((s.total / s.invested) * 100) + ' on cost' : null} />
      <PnlStat label="Open positions" value={s.n} sub={`${s.winners} in profit`} />
      <PnlStat label="Best" value={s.best ? s.best.sym : '—'} tone="num-bull" sub={s.best ? fmtSignedINR(s.best.pnl) : null} />
      <PnlStat label="Worst" value={s.worst ? s.worst.sym : '—'} tone="num-bear" sub={s.worst ? fmtSignedINR(s.worst.pnl) : null} />
    </div>
  );
}

function RealizedStrip({ trades }) {
  const s = useMemo(() => {
    const t = trades || [];
    const pnls = t.map((x) => Number(x.net_pnl) || 0);
    const rets = t.map((x) => Number(x.return_pct) || 0);
    const wins = rets.filter((r) => r > 0);
    const losses = rets.filter((r) => r <= 0);
    const gw = pnls.filter((p) => p > 0).reduce((a, b) => a + b, 0);
    const gl = Math.abs(pnls.filter((p) => p < 0).reduce((a, b) => a + b, 0));
    return {
      n: t.length,
      total: pnls.reduce((a, b) => a + b, 0),
      winRate: t.length ? (wins.length / t.length) * 100 : null,
      avgWin: wins.length ? wins.reduce((a, b) => a + b, 0) / wins.length : null,
      avgLoss: losses.length ? losses.reduce((a, b) => a + b, 0) / losses.length : null,
      pf: gl > 0 ? gw / gl : null,
    };
  }, [trades]);
  return (
    <div className="pv3-pnl-strip">
      <PnlStat label="Realised P&L" value={fmtSignedINR(s.total)} tone={s.total >= 0 ? 'num-bull' : 'num-bear'} sub={`${s.n} closed`} />
      <PnlStat label="Win rate" value={s.winRate != null ? s.winRate.toFixed(0) + '%' : '—'}
               sub={s.n ? `${Math.round((s.winRate / 100) * s.n)}/${s.n}` : null} />
      <PnlStat label="Avg win / loss"
               value={s.avgWin != null || s.avgLoss != null
                 ? `${s.avgWin != null ? fmtPct(s.avgWin) : '—'} / ${s.avgLoss != null ? fmtPct(s.avgLoss) : '—'}` : '—'} />
      <PnlStat label="Profit factor" value={s.pf != null ? s.pf.toFixed(2) : '—'}
               tone={s.pf != null ? (s.pf >= 1 ? 'num-bull' : 'num-bear') : ''} />
    </div>
  );
}

function PositionsTable({ holdings, isLoading }) {
  const rows = useMemo(() => (holdings || []).map((h, i) => {
    const qty = Number(h.shares) || 0;
    const entry = Number(h.entry_price) || 0;
    const ltp = Number(h.current_price) || 0;
    const value = Number(h.current_value) || qty * ltp;
    const pnl = h.unrealised_pnl != null ? Number(h.unrealised_pnl) : value - qty * entry;
    const pnlPct = h.unrealised_pnl_pct != null ? Number(h.unrealised_pnl_pct) : (entry > 0 ? ((ltp - entry) / entry) * 100 : 0);
    const stop = Number(h.atr_stop) || 0;
    const target = Number(h.target) || 0;
    const rr = (entry > 0 && entry !== stop && target > 0) ? (target - entry) / (entry - stop) : null;
    return { id: h.ticker || i, sym: h.ticker || '—', sector: h.sector || 'Other', qty, entry, ltp, value, pnl, pnlPct, stop, target, rr, days: h.hold_days };
  }), [holdings]);
  return (
    <div className="pv3-stocks-table">
      <div className="pv3-stocks-table-head">
        <div>
          <div className="pv3-t-ui-headline">Open positions</div>
          <div className="pv3-t-ui-footnote">{isLoading ? 'Loading…' : `${rows.length} held · entry / stop / target / R:R`}</div>
        </div>
      </div>
      <div className="pv3-ptbl">
        <div className="pv3-th">Company</div>
        <div className="pv3-th pv3-th-r">Qty</div>
        <div className="pv3-th pv3-th-r">Entry</div>
        <div className="pv3-th pv3-th-r">LTP</div>
        <div className="pv3-th pv3-th-r">Value</div>
        <div className="pv3-th pv3-th-r">Unreal P&L</div>
        <div className="pv3-th pv3-th-r">Days</div>
        <div className="pv3-th pv3-th-r">Stop</div>
        <div className="pv3-th pv3-th-r">Target</div>
        <div className="pv3-th pv3-th-r">R:R</div>
        {isLoading ? (
          <div className="pv3-td" style={{ gridColumn: '1 / -1' }}><Skel w="100%" h={40} /></div>
        ) : rows.length === 0 ? (
          <div className="pv3-closed-empty" style={{ gridColumn: '1 / -1' }}>No open positions.</div>
        ) : rows.map((r) => (
          <React.Fragment key={r.id}>
            <div className="pv3-td pv3-td-name">
              <Logo sym={r.sym} size={32} radius={8} />
              <div>
                <div className="pv3-td-name-sym">{r.sym}</div>
                <div className="pv3-td-name-full">{r.sector}</div>
              </div>
            </div>
            <div className="pv3-td pv3-td-r tabular-nums">{Math.round(r.qty)}</div>
            <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--text-3)' }}>{fmtNum(r.entry)}</div>
            <div className="pv3-td pv3-td-r tabular-nums">{fmtNum(r.ltp)}</div>
            <div className="pv3-td pv3-td-r tabular-nums">{fmtLakh(r.value)}</div>
            <div className="pv3-td pv3-td-r tabular-nums" style={{ color: r.pnl >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
              <div className="pv3-pcol"><span className="pv3-pnl-v">{fmtSignedINR(r.pnl)}</span><span className="pv3-pnl-p">{fmtPct(r.pnlPct)}</span></div>
            </div>
            <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--text-3)' }}>{r.days != null ? `${r.days}d` : '—'}</div>
            <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--bear)' }}>{r.stop ? fmtNum(r.stop) : '—'}</div>
            <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--bull)' }}>{r.target ? fmtNum(r.target) : '—'}</div>
            <div className="pv3-td pv3-td-r tabular-nums">{r.rr != null ? r.rr.toFixed(2) : '—'}</div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function ClosedTradesTable({ trades, isLoading }) {
  const rows = useMemo(() => [...(trades || [])].sort((a, b) => String(b.exit_date || '').localeCompare(String(a.exit_date || ''))), [trades]);
  return (
    <div className="pv3-stocks-table">
      <div className="pv3-stocks-table-head">
        <div>
          <div className="pv3-t-ui-headline">Closed trades</div>
          <div className="pv3-t-ui-footnote">{isLoading ? 'Loading…' : `${rows.length} round-trip${rows.length === 1 ? '' : 's'}`}</div>
        </div>
      </div>
      <div className="pv3-ctbl">
        <div className="pv3-th">Company</div>
        <div className="pv3-th pv3-th-r">In</div>
        <div className="pv3-th pv3-th-r">Out</div>
        <div className="pv3-th pv3-th-r">Held</div>
        <div className="pv3-th pv3-th-r">Entry</div>
        <div className="pv3-th pv3-th-r">Exit</div>
        <div className="pv3-th pv3-th-c">Reason</div>
        <div className="pv3-th pv3-th-r">Realised</div>
        <div className="pv3-th pv3-th-r">Return</div>
        {isLoading ? (
          <div className="pv3-td" style={{ gridColumn: '1 / -1' }}><Skel w="100%" h={40} /></div>
        ) : rows.length === 0 ? (
          <div className="pv3-closed-empty" style={{ gridColumn: '1 / -1' }}>No closed trades yet — round-trips appear here as positions exit.</div>
        ) : rows.map((t, i) => {
          const [lbl, tone] = reasonChip(t.exit_reason);
          const ret = Number(t.return_pct);
          const pnl = Number(t.net_pnl);
          return (
            <React.Fragment key={`${t.ticker}-${t.exit_date}-${i}`}>
              <div className="pv3-td pv3-td-name"><Logo sym={t.ticker} size={32} radius={8} /><div className="pv3-td-name-sym">{t.ticker}</div></div>
              <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--text-3)' }}>{String(t.entry_date || '').slice(0, 10)}</div>
              <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--text-3)' }}>{String(t.exit_date || '').slice(0, 10)}</div>
              <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--text-3)' }}>{t.hold_days != null ? `${Math.round(t.hold_days)}d` : '—'}</div>
              <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--text-3)' }}>{fmtNum(t.entry_price)}</div>
              <div className="pv3-td pv3-td-r tabular-nums">{fmtNum(t.exit_price)}</div>
              <div className="pv3-td pv3-td-c"><span className={`pv3-cl-rsn ${tone}`}>{lbl}</span></div>
              <div className="pv3-td pv3-td-r tabular-nums" style={{ color: pnl >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtSignedINR(pnl)}</div>
              <div className="pv3-td pv3-td-r tabular-nums" style={{ color: ret >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtPct(ret)}</div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

function ActivityPanel({ holdings, trades, isLoading }) {
  const events = useMemo(() => {
    const ev = [];
    (holdings || []).forEach((h) => ev.push({ date: h.entry_date, side: 'BUY', ticker: h.ticker, qty: Number(h.shares) || null, price: Number(h.entry_price) || null, note: 'opened' }));
    (trades || []).forEach((t) => {
      ev.push({ date: t.entry_date, side: 'BUY', ticker: t.ticker, qty: Number(t.qty) || null, price: Number(t.entry_price) || null, note: 'entry' });
      ev.push({ date: t.exit_date, side: 'SELL', ticker: t.ticker, qty: Number(t.qty) || null, price: Number(t.exit_price) || null, note: t.exit_reason, pnl: Number(t.net_pnl) });
    });
    return ev.filter((e) => e.date).sort((a, b) => String(b.date).localeCompare(String(a.date)));
  }, [holdings, trades]);
  return (
    <div className="pv3-stocks-table">
      <div className="pv3-stocks-table-head">
        <div>
          <div className="pv3-t-ui-headline">Activity</div>
          <div className="pv3-t-ui-footnote">{isLoading ? 'Loading…' : `${events.length} fill${events.length === 1 ? '' : 's'} · buys fill at next open, sells at exit`}</div>
        </div>
      </div>
      <div className="pv3-act-list">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skel key={i} w="100%" h={36} />)
        ) : events.length === 0 ? (
          <div className="pv3-closed-empty">No activity yet.</div>
        ) : events.map((e, i) => (
          <div key={i} className="pv3-act-row">
            <span className={`pv3-act-side ${e.side === 'BUY' ? 'buy' : 'sell'}`}>{e.side}</span>
            <Logo sym={e.ticker} size={24} radius={6} />
            <span className="pv3-act-sym">{e.ticker}</span>
            <span className="pv3-act-qty tabular-nums" style={{ color: 'var(--text-3)' }}>{e.qty != null ? `${e.qty} sh` : ''}{e.price != null ? ` @ ${fmtNum(e.price)}` : ''}</span>
            <span className="pv3-act-note" style={{ color: 'var(--text-3)' }}>{e.note}</span>
            <span className="pv3-act-date tabular-nums" style={{ color: 'var(--text-3)' }}>{String(e.date).slice(0, 10)}</span>
            {e.pnl != null
              ? <span className="pv3-act-pnl tabular-nums" style={{ color: e.pnl >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtSignedINR(e.pnl)}</span>
              : <span />}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PortfolioV3() {
  // Two views: YOURS (the user's own self-reported holdings, from the Stage-4 execution ledger) and
  // PAPER (the model's ₹10L paper book, a labeled REFERENCE — not the user's return). Defaults to
  // Yours. No Kite (ADR 0011): the user executes on their own broker and reports fills.
  const [mode, setMode] = useState('yours');
  const [ptab, setPtab] = useState('overview');   // sub-tab: overview | positions | closed | activity
  const isPaper = mode === 'paper';

  const overviewQuery   = useOverview();
  const navHistoryQuery = useNavHistory();          // model NAV (only surfaced in the Paper reference view)
  const paperHistoryQuery = usePaperHistory();      // ₹10L paper-broker ledger (Paper reference view)
  const paperQuery      = usePaperPositions();      // the model's paper positions (Paper reference view)
  const execQuery       = useExecutionPositions();  // the user's OWN durable positions (Yours view)
  const reconQuery      = useReconciliation({ enabled: !isPaper });  // outstanding model-vs-ledger items
  const tradesQuery     = useTrades({ perPage: 50 });
  const signalsQuery    = useSignals();

  // Stable references so the view useMemo below doesn't recompute every render.
  const paperPortfolio = useMemo(() => overviewQuery.data?.portfolio ?? {}, [overviewQuery.data]);
  const metrics    = useMemo(() => overviewQuery.data?.metrics ?? {}, [overviewQuery.data]);
  const regime     = signalsQuery.data?.regime ?? {};
  const navHistory = navHistoryQuery.data ?? null;
  const paperHistory = paperHistoryQuery.data ?? null;

  const paperPos    = useMemo(() => paperQuery.data ?? [], [paperQuery.data]);
  const execPos     = useMemo(() => execQuery.data ?? [], [execQuery.data]);
  const openExec    = useMemo(() => execPos.filter((p) => (Number(p.remaining_qty) || 0) > 0), [execPos]);
  const closedExec  = useMemo(() => execPos.filter((p) => (Number(p.remaining_qty) || 0) <= 0
                                                          && (Number(p.total_bought_qty) || 0) > 0), [execPos]);

  // Live quotes for the user's held names (owner market-data), joined for current price / unrealized.
  const heldTickers = useMemo(
    () => [...new Set(openExec.map((p) => (p.ticker || '').toUpperCase()).filter(Boolean))], [openExec]);
  const quotesQuery = useQuoteBatch(heldTickers, { enabled: !isPaper && heldTickers.length > 0 });
  const quotes = quotesQuery.data ?? null;

  const yoursHoldings = useMemo(() => openExec.map((p) => ledgerHoldingToRow(p, quotes)), [openExec, quotes]);

  // Synthesize a single view-model so every section reads uniform fields, whichever mode is active.
  const view = useMemo(() => {
    if (isPaper) {
      return {
        holdings: paperPos,
        portfolio: paperPortfolio,
        cash: paperPortfolio?.cash ?? null,
        totalEquity: paperPortfolio?.total_value ?? null,
      };
    }
    // YOURS: value + unrealized computed from the ledger (cost basis) × owner quotes. No cash / NAV
    // is invented — we don't hold the user's broker balance (ADR 0011), so totalEquity = market value.
    const mktValue = yoursHoldings.reduce((s, h) => s + (Number(h.last_price) || 0) * (Number(h.quantity) || 0), 0);
    const cost     = yoursHoldings.reduce((s, h) => s + (Number(h.average_price) || 0) * (Number(h.quantity) || 0), 0);
    const realized = closedExec.reduce((s, p) => s + (Number(p.realized_pnl) || 0), 0);
    const yoursPortfolio = {
      total_value: mktValue || null,
      cash: null,                                   // not tracked — self-report has no broker cash
      invested: cost || null,
      total_return_pct: cost > 0 ? ((mktValue - cost) / cost) * 100 : null,
      realized_pnl: realized,
      drawdown_pct: null,
      n_positions: yoursHoldings.length || null,
    };
    return { holdings: yoursHoldings, portfolio: yoursPortfolio, cash: null, totalEquity: mktValue || null };
  }, [isPaper, paperPos, paperPortfolio, yoursHoldings, closedExec]);

  const activeHoldings = view.holdings;
  const cash           = view.cash;
  const totalEquity    = view.totalEquity;

  // Closed trades: the model's paper round-trips in the Paper view; the user's own realized ledger
  // round-trips in the Yours view.
  const modelTrades = useMemo(() => flattenTrades(tradesQuery.data), [tradesQuery.data]);
  const yoursTrades = useMemo(() => closedExec.map(ledgerClosedToTrade), [closedExec]);
  const trades = isPaper ? modelTrades : yoursTrades;

  const isOverviewLoading = isPaper ? overviewQuery.isLoading : execQuery.isLoading;
  const isHoldingsLoading = isPaper ? paperQuery.isLoading : execQuery.isLoading;
  const closedLoading     = isPaper ? tradesQuery.isLoading : execQuery.isLoading;

  return (
    <div className="pv3-page density-regular">

      {/* StateStrip */}
      <StateStrip
        kiteConnected={!isPaper}
        regime={regime}
        drawdownPct={view.portfolio?.drawdown_pct}
      />

      {/* Page title + Yours/Paper selector */}
      <section className="pv3-row pv3-head-row">
        <div className="pv3-row-head">
          <div>
            <div className="pv3-t-ui-micro">PORTFOLIO · MONITORING</div>
            <h2 className="pv3-row-title">Portfolio</h2>
            <div className="pv3-t-ui-footnote">
              {isPaper
                ? "The model's paper book · a labeled reference, not your return"
                : 'Your holdings · from what you reported, priced live · no broker link'}
            </div>
          </div>
          <div className="pv3-mode-toggle" role="tablist" aria-label="Portfolio view">
            <button
              role="tab"
              aria-selected={!isPaper}
              className={`pv3-mode-btn ${!isPaper ? 'active' : ''}`}
              onClick={() => setMode('yours')}
            >
              Yours
            </button>
            <button
              role="tab"
              aria-selected={isPaper}
              className={`pv3-mode-btn ${isPaper ? 'active' : ''}`}
              onClick={() => setMode('paper')}
            >
              Paper (ref)
            </button>
          </div>
        </div>
      </section>

      {/* Sub-tab bar — Portfolio sections */}
      <section className="pv3-row">
        <nav className="pv3-subtabs" role="tablist" aria-label="Portfolio sections">
          {[['overview', 'Overview'], ['positions', 'Positions'], ['closed', 'Closed Trades'], ['activity', 'Activity']].map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={ptab === id}
              className={`pv3-subtab ${ptab === id ? 'active' : ''}`}
              onClick={() => setPtab(id)}
            >
              {label}
            </button>
          ))}
        </nav>
      </section>

      {/* Empty-ledger prompt — the user hasn't recorded any buys yet */}
      {!isPaper && !isHoldingsLoading && activeHoldings.length === 0 && closedExec.length === 0 && (
        <section className="pv3-row">
          <div className="pv3-connect-banner">
            <span>No holdings yet. When you buy a call on your broker, record it from the Research
              page — your positions and realized P&amp;L will show up here.</span>
          </div>
        </section>
      )}

      {/* OVERVIEW — NAV + equity curve + performance + risk + allocation */}
      {ptab === 'overview' && (
        <>
          {!isPaper && (reconQuery.data?.items?.length ?? 0) > 0 && (
            <section className="pv3-row"><ActionItemsStrip items={reconQuery.data.items} /></section>
          )}
          <section className="pv3-row">
            <EquityHero
              portfolio={view.portfolio}
              metrics={metrics}
              navHistory={navHistory}
              paperHistory={paperHistory}
              isPaper={isPaper}
              margins={null}
              holdings={view.holdings}
              paperPositions={isPaper ? paperPos : []}
              isLoading={isOverviewLoading}
            />
          </section>
          <section className="pv3-row">
            <PerfRibbon metrics={metrics} portfolio={view.portfolio} isLoading={isOverviewLoading} />
          </section>
          <section className="pv3-row">
            <RiskRibbon portfolio={view.portfolio} metrics={metrics} isLoading={isOverviewLoading} />
          </section>
          <section className="pv3-row">
            <AllocCard holdings={activeHoldings} cash={cash} totalEquity={totalEquity} isPaper={isPaper} isLoading={isHoldingsLoading} />
          </section>
        </>
      )}

      {/* POSITIONS — aggregate unrealised P&L + per-position detail (stop/target/R:R) */}
      {ptab === 'positions' && (
        <>
          <section className="pv3-row"><UnrealizedStrip holdings={activeHoldings} isPaper={isPaper} /></section>
          <section className="pv3-row">
            {isPaper
              ? <PositionsTable holdings={paperPos} isLoading={isHoldingsLoading} />
              : <HoldingsTable holdings={activeHoldings} isPaper={isPaper} totalEquity={totalEquity} isLoading={isHoldingsLoading} />}
          </section>
        </>
      )}

      {/* CLOSED TRADES — realised P&L + full round-trip table + monthly returns */}
      {ptab === 'closed' && (
        <>
          <section className="pv3-row"><RealizedStrip trades={trades} /></section>
          <section className="pv3-row"><ClosedTradesTable trades={trades} isLoading={closedLoading} /></section>
          <section className="pv3-row"><MonthlyPnl trades={trades} isLoading={closedLoading} /></section>
        </>
      )}

      {/* ACTIVITY — chronological fills (buys at next open, sells at exit) */}
      {ptab === 'activity' && (
        <section className="pv3-row">
          <ActivityPanel
            holdings={isPaper ? paperPos : []}
            trades={trades}
            isLoading={closedLoading || (isPaper && paperQuery.isLoading)}
          />
        </section>
      )}

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
