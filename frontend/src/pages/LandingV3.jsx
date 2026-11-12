/**
 * Public website — design v7.1 "Institutional, dense" (docs/DESIGN_BRIEF_V5.md §10–§11).
 * Every zone has a job (see the §11 table); sections meet through a 1px rule or a tone shift,
 * never empty height. Real data only: index levels (TickerStrip), the backtest series from
 * GET /api/landing-stats (charts + sparklines), and the weekly scan counts when published.
 * Copy is verbatim from lib/landingContent (reviewed).
 */
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Minus, Plus } from 'lucide-react';
import RequestAccessModal from '@/components/landing/RequestAccessModal';
import BrandMark from '@/components/brand/BrandMark';
import LwChart from '@/components/charts/LwChart';
import Spark from '@/components/charts/Spark';
import TickerStrip, { rescoreTimes } from '@/components/shared/TickerStrip';
import { DISCLAIMER } from '@/lib/signalCopy';
import { FALLBACK, STEPS, PLAN_PARTS, IS, ISNT, FAQ, METHOD, ACCESS } from '@/lib/landingContent';
import '@/styles/landing-v7.css';

const MINUS = '−';
const num = (v, dp = 0) => {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  const s = Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp });
  return n < 0 ? `${MINUS}${s}` : s;
};
const signed = (v, dp = 0) => (v == null ? '—' : `${v > 0 ? '+' : ''}${num(v, dp)}`);
const toTime = (t) => { const s = String(t); return s.length === 7 ? `${s}-01` : s.length === 4 ? `${s}-01-01` : s.slice(0, 10); };
const istDate = (d) => d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: 'numeric', month: 'short' });

/* Product-shot rows — labelled "Sample" on screen; no live call is implied. */
const SAMPLE = [
  ['MCX', '2,815.40', '2,426.70', '3,592.80', '+27.6', '2.0R'],
  ['SYRMA', '1,376.70', '1,193.90', '1,742.30', '+26.6', '2.0R'],
  ['LAURUSLABS', '1,543.10', '1,402.60', '1,824.10', '+18.2', '2.0R'],
  ['PTCIL', '9,640.00', '8,125.00', '12,670.00', '+31.4', '2.0R'],
];

function SecHead({ id, eyebrow, title, sub }) {
  return (
    <header className="v7-sh">
      <div><p className="v7-eyebrow">{eyebrow}</p><h2 id={`${id}-h`}>{title}</h2></div>
      {sub && <p className="v7-sh-sub">{sub}</p>}
    </header>
  );
}

function Faq() {
  const [open, setOpen] = useState(null);
  return (
    <div className="v7-faq">
      {FAQ.map(([q, a], i) => {
        const on = open === i;
        return (
          <div key={q} className="v7-faq-item">
            <h3>
              <button type="button" aria-expanded={on} aria-controls={`faq-${i}`} id={`faq-q-${i}`} onClick={() => setOpen(on ? null : i)}>
                <span>{q}</span>{on ? <Minus size={16} aria-hidden /> : <Plus size={16} aria-hidden />}
              </button>
            </h3>
            <div id={`faq-${i}`} role="region" aria-labelledby={`faq-q-${i}`} hidden={!on}><p>{a}</p></div>
          </div>
        );
      })}
    </div>
  );
}

export default function LandingV3() {
  const [stats, setStats] = useState(FALLBACK);
  const [ask, setAsk] = useState(false);
  const [menu, setMenu] = useState(false);
  const [pastHero, setPastHero] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch('/api/landing-stats').then((r) => (r.ok ? r.json() : null)).then((d) => {
      if (!alive || !d) return;
      setStats({
        backtest: { ...FALLBACK.backtest, ...(d.backtest || {}) },
        live: { ...FALLBACK.live, ...(d.live || {}) },
        weekly_swing: d.weekly_swing || null,
        yearly_returns: Array.isArray(d.yearly_returns) && d.yearly_returns.length ? d.yearly_returns : FALLBACK.yearly_returns,
        equity_bt: Array.isArray(d.equity_bt) && d.equity_bt.length ? d.equity_bt : FALLBACK.equity_bt,
      });
    }).catch(() => {});
    document.title = 'Nifty Satvik — systematic swing research for the Nifty 500';
    const on = () => setPastHero(window.scrollY > 560);
    window.addEventListener('scroll', on, { passive: true });
    return () => { alive = false; window.removeEventListener('scroll', on); };
  }, []);

  const bt = stats.backtest;
  const live = stats.live;
  const weekly = stats.weekly_swing;
  const eq = useMemo(() => (stats.equity_bt || []).filter((d) => d && d.s != null), [stats.equity_bt]);
  const last = eq[eq.length - 1];
  const alpha = last && last.b != null ? Math.round(last.s - last.b) : null;
  const sVals = useMemo(() => eq.map((d) => Number(d.s)), [eq]);
  const bVals = useMemo(() => eq.filter((d) => d.b != null).map((d) => Number(d.b)), [eq]);
  const rel = useMemo(() => eq.filter((d) => d.b != null).map((d) => Number(d.s) - Number(d.b)), [eq]);
  const dd = useMemo(() => { let pk = -Infinity; return sVals.map((v) => { pk = Math.max(pk, v); return (v / pk - 1) * 100; }); }, [sVals]);
  const yr = useMemo(() => (stats.yearly_returns || []).map((y) => Number(y.net_pct)), [stats.yearly_returns]);
  const posYears = yr.filter((v) => v > 0).length;
  const { last: rescored } = rescoreTimes(new Date());

  const go = (id) => { setMenu(false); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const open = () => { setMenu(false); setAsk(true); };

  const growth = useMemo(() => {
    const out = [{ type: 'area', data: eq.map((d) => ({ time: toTime(d.t), value: Number(d.s) })), color: '#20C4A0', title: 'Strategy' }];
    const b = eq.filter((d) => d.b != null).map((d) => ({ time: toTime(d.t), value: Number(d.b) }));
    if (b.length) out.push({ type: 'line', data: b, color: '#7A8494', width: 1, dashed: true, title: 'Nifty 500' });
    return out;
  }, [eq]);
  const yearly = useMemo(() => [{
    type: 'histogram', lastValue: false,
    data: (stats.yearly_returns || []).map((y) => ({ time: `${y.year}-07-01`, value: Number(y.net_pct), color: Number(y.net_pct) >= 0 ? '#20C4A0' : '#FF6B4A' })),
  }], [stats.yearly_returns]);
  const pctFormat = useMemo(() => ({ type: 'custom', formatter: (v) => `${v.toFixed(0)}%`, minMove: 1 }), []);

  const NAV = [['how', 'How it works'], ['record', 'Track record'], ['method', 'Methodology'], ['faq', 'FAQ']];

  return (
    <div className="v7">
      <a href="#main" className="skip-link">Skip to main content</a>
      <header className="v7-nav">
        <div className="v7-wrap v7-nav-in">
          <a className="v7-brand" href="#top" aria-label="Nifty Satvik home"><BrandMark size={24} /><span>Nifty Satvik</span></a>
          <nav aria-label="Primary" className="v7-nav-links">
            {NAV.map(([id, l]) => <button key={id} type="button" onClick={() => go(id)}>{l}</button>)}
          </nav>
          <div className="v7-nav-cta">
            <a href="/login" className="v7-link">Sign in</a>
            <button type="button" className="pf-btn v7-btn-sm" onClick={open}>Request access</button>
            <button type="button" className="v7-burger" aria-label="Menu" aria-expanded={menu} onClick={() => setMenu(!menu)}><span /><span /></button>
          </div>
        </div>
        {menu && (
          <nav aria-label="Mobile" className="v7-sheet">
            {NAV.map(([id, l]) => <button key={id} type="button" onClick={() => go(id)}>{l}</button>)}
            <a href="/login">Sign in</a>
          </nav>
        )}
        <TickerStrip />
      </header>

      <main id="main">
        {/* HERO — two columns of equal weight; the panel stretches to the copy column */}
        <section className="v7-hero" id="top">
          <div className="v7-wrap v7-hero-grid">
            <div className="v7-hero-copy">
              <p className="v7-status"><span className="v7-dot" aria-hidden />Book re-scored {istDate(rescored)}, 18:00 IST · research only</p>
              <h1>Systematic swing research for the Nifty&nbsp;500.</h1>
              <p className="v7-lede">
                Nifty Satvik re-scores the Nifty 500 every Saturday evening, and re&#8209;prices what you already hold after
                each weekday close. You get A&#8209;grade signals with an explicit entry, stop and target — and you place the
                orders yourself.
              </p>

              {weekly ? (
                <dl className="v7-kpis" aria-label="This week's scan">
                  <div><dt>Fresh setups</dt><dd data-num>{num(weekly.n_signals)}</dd></div>
                  <div><dt>Grade A · B</dt><dd data-num>{num(weekly.grade_a)}<small> · {num(weekly.grade_b)}</small></dd></div>
                  <div><dt>Avg target</dt><dd data-num className="v7-up">{signed(weekly.avg_target_upside_pct, 1)}%</dd></div>
                  <div><dt>Horizon</dt><dd data-num>{num(weekly.hold_days)}<small>d</small></dd></div>
                </dl>
              ) : (
                <dl className="v7-kpis" aria-label="Backtest at a glance">
                  <div><dt>Growth ×</dt><dd data-num>{num(bt.mult, 1)}<small>×</small></dd></div>
                  <div><dt>Win rate</dt><dd data-num>{num(bt.win_rate_pct)}<small>%</small></dd></div>
                  <div><dt>Up years</dt><dd data-num>{posYears}<small>/{yr.length}</small></dd></div>
                  <div><dt>Trades</dt><dd data-num>{num(bt.total_trades)}</dd></div>
                </dl>
              )}

              <div className="v7-cta">
                <button type="button" className="pf-btn" onClick={open}>Request access <ArrowRight size={16} aria-hidden /></button>
                <button type="button" className="pf-btn-2" onClick={() => go('how')}>How it works</button>
                <a href="/login" className="v7-link v7-cta-signin">Already invited? Sign in</a>
              </div>

              <table className="v7-yr" aria-label="Calendar-year net returns, backtest">
                <caption>Calendar-year net returns <span>backtest · * partial</span></caption>
                <tbody>{[0, 1].map((row) => (
                  <tr key={row}>{(stats.yearly_returns || []).slice(row * 5, row * 5 + 5).map((y) => (
                    <td key={y.year}><span>{y.year}{y.partial ? '*' : ''}</span><b className={Number(y.net_pct) >= 0 ? 'v7-up' : 'v7-down'}>{signed(Number(y.net_pct), 1)}%</b></td>
                  ))}</tr>
                ))}</tbody>
              </table>

              <dl className="v7-facts">
                <div><dt>Universe</dt><dd>Nifty 500, large &amp; mid cap</dd></div>
                <div><dt>Cadence</dt><dd>Weekly re-score · daily re-price</dd></div>
                <div><dt>Every call</dt><dd>Entry · stop · target · size</dd></div>
                <div><dt>Execution</dt><dd>Your broker — we never place orders</dd></div>
              </dl>
            </div>

            <figure className="v7-shot" aria-label="Product preview">
              <div className="v7-shot-bar">
                <span className="v7-shot-tab on">Track record</span><span className="v7-shot-tab">This week</span><span className="v7-shot-tab">Research</span>
                <span className="v7-shot-meta">Backtest {bt.period} · in-sample</span>
              </div>
              <div className="v7-shot-head">
                <div>
                  <p className="v7-k">Growth of ₹100 · strategy</p>
                  <p className="v7-shot-big" data-num>₹{last ? num(last.s, 0) : '—'} <span className="v7-up">▲ {signed(last ? last.s - 100 : null)}%</span></p>
                </div>
                <div>
                  <p className="v7-k">Nifty 500</p>
                  <p className="v7-shot-mid" data-num>₹{last && last.b != null ? num(last.b, 0) : '—'}</p>
                </div>
                <div>
                  <p className="v7-k">Excess</p>
                  <p className="v7-shot-mid v7-up" data-num>{alpha != null ? `${signed(alpha)} pts` : '—'}</p>
                </div>
                <ul className="v7-legend" aria-hidden><li><i className="v7-key-s" />Strategy</li><li><i className="v7-key-b" />Nifty 500</li></ul>
              </div>
              <div className="v7-shot-chart">
                <LwChart series={growth} height={220} fill label={`Growth of ₹100, ${bt.period}: strategy ₹${last ? num(last.s) : '—'} vs Nifty 500 ₹${last ? num(last.b) : '—'} (backtest, in-sample)`} />
              </div>
              <table className="v7-mini" aria-label="Sample research calls">
                <caption>Research calls <span>Sample</span></caption>
                <thead><tr><th scope="col">Symbol</th><th scope="col">Entry</th><th scope="col">Stop</th><th scope="col">Target</th><th scope="col">Upside</th><th scope="col">R:R</th></tr></thead>
                <tbody>{SAMPLE.map(([s, e, st, t, u, rr]) => (
                  <tr key={s}><th scope="row">{s}</th><td>{e}</td><td className="v7-down">{st}</td><td className="v7-up">{t}</td><td className="v7-up">▲ {u}%</td><td>{rr}</td></tr>
                ))}</tbody>
              </table>
              <figcaption className="v7-shot-foot">
                <span>Source: survivorship-corrected backtest, net of costs, before STCG</span>
                <span>Not certified · DSR {num(bt.dsr, 2)}</span>
              </figcaption>
            </figure>
          </div>
        </section>

        {/* KEY FIGURES — abut the hero; every figure carries a real series */}
        <section className="v7-figs" aria-label="Backtest summary">
          <div className="v7-wrap">
            <dl className="v7-figs-row">
              <div><dt>CAGR, net</dt><dd data-num>~{num(bt.cagr_pct)}%</dd><Spark data={sVals} width={96} height={24} label="Strategy equity curve" /></div>
              <div><dt>vs Nifty 500</dt><dd data-num className="v7-up">{alpha != null ? `${signed(alpha)} pts` : '—'}</dd><Spark data={rel} width={96} height={24} label="Strategy minus benchmark" /></div>
              <div><dt>Nifty 500, same period</dt><dd data-num>₹{last && last.b != null ? num(last.b) : '—'}</dd><Spark data={bVals} width={96} height={24} tone="flat" label="Benchmark growth of ₹100" /></div>
              <div><dt>Calendar years</dt><dd data-num>{posYears}<small> up · {yr.length - posYears} down</small></dd><Spark data={yr} width={96} height={24} bars label="Calendar-year returns" /></div>
              <div><dt>Max drawdown</dt><dd data-num className="v7-down">{num(bt.max_drawdown_pct)}%</dd><Spark data={dd} width={96} height={24} tone="down" label="Drawdown from peak" /></div>
            </dl>
          </div>
        </section>

        <div className="v7-reg" role="note">
          <div className="v7-wrap v7-reg-in">
            <span>Not SEBI-registered</span><span>Research only</span><span>You place every order</span>
            <span>In-sample, not certified</span><span>Paper record since <b data-num>{live.since}</b></span>
          </div>
        </div>

        <section id="how" className="v7-sec v7-tone" aria-labelledby="how-h">
          <div className="v7-wrap">
            <SecHead id="how" eyebrow="How it works" title="No black box. The same path, every week."
              sub="Every signal travels one transparent, frozen pipeline — identical in backtest and in production. The one thing we keep private is the exact ranking formula." />
            <ol className="v7-steps">
              {STEPS.map(([t, d], i) => (
                <li key={t}><span className="v7-step-n" data-num>{String(i + 1).padStart(2, '0')}</span><h3>{t}</h3><p>{d}</p></li>
              ))}
            </ol>
            <p className="v7-row-note"><b>The ranking formula is not disclosed.</b> The exact factor, thresholds, and hold rules are the edge — so they stay internal. You get the complete plan and the full track record; the recipe stays ours.</p>
          </div>
        </section>

        <section id="plan" className="v7-sec" aria-labelledby="plan-h">
          <div className="v7-wrap">
            <SecHead id="plan" eyebrow="What you get" title="Every signal is a complete trade plan." />
            <div className="v7-plan">
              <table className="v7-ticket" aria-label="Illustrative trade plan">
                <caption><span>RELIANCE</span> Energy · NSE <em>Grade A</em></caption>
                <tbody>
                  <tr><th scope="row">Entry</th><td data-num>₹2,872</td></tr>
                  <tr><th scope="row">Stop</th><td data-num className="v7-down">₹2,786</td></tr>
                  <tr><th scope="row">Target</th><td data-num className="v7-up">₹3,066</td></tr>
                  <tr><th scope="row">Risk : reward</th><td data-num>1 : 2.2</td></tr>
                  <tr><th scope="row">Hold window</th><td>Multi-week</td></tr>
                </tbody>
                <tfoot><tr><td colSpan="2">Illustrative example — not a live recommendation.</td></tr></tfoot>
              </table>
              <dl className="v7-grid2 v7-grid-tight">{PLAN_PARTS.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
            </div>
          </div>
        </section>

        <section id="record" className="v7-sec v7-tone" aria-labelledby="record-h">
          <div className="v7-wrap">
            <SecHead id="record" eyebrow="Track record" title="The numbers, net of every cost."
              sub={`The weekly-swing book on a survivorship-corrected backtest (${bt.period}), net of brokerage, STT and slippage. In-sample and not yet certified — no real capital has traded.`} />
            <div className="v7-charts">
              <figure className="v7-panel">
                <figcaption>Growth of ₹100 <span>Strategy vs Nifty 500</span></figcaption>
                <LwChart series={growth} height={240} label="Growth of ₹100, strategy versus Nifty 500, backtest" />
              </figure>
              <figure className="v7-panel">
                <figcaption>Calendar-year returns <span>Net · first and last years partial</span></figcaption>
                <LwChart series={yearly} height={240} priceFormat={pctFormat} label="Calendar-year net returns, backtest" />
              </figure>
              <table className="v7-years" aria-label="Calendar-year net returns">
                <thead><tr><th scope="col">Year</th>{(stats.yearly_returns || []).map((y) => <th scope="col" key={y.year}>{y.year}{y.partial ? '*' : ''}</th>)}</tr></thead>
                <tbody><tr><th scope="row">Net</th>{(stats.yearly_returns || []).map((y) => (
                  <td key={y.year} className={Number(y.net_pct) >= 0 ? 'v7-up' : 'v7-down'}>{signed(Number(y.net_pct), 1)}%</td>
                ))}</tr></tbody>
              </table>
            </div>
            <p className="v7-fine">Weekly-swing book, backtest {bt.period}, net of costs before 20% STCG, in-sample on the survivorship-corrected universe — Sharpe {num(bt.sharpe, 2)}, DSR {num(bt.dsr, 2)} (below the certification gate). Not indicative of future results; a handful of strong-trend years drive the total, with a &gt;40% peak-to-trough drawdown. No real capital has traded — the forward paper record since {live.since} is the real test. * partial year.</p>
          </div>
        </section>

        <section id="edge" className="v7-sec" aria-labelledby="edge-h">
          <div className="v7-wrap">
            <SecHead id="edge" eyebrow="Why trust it" title="What the edge is — and what it isn’t." sub="We’d rather tell you how it actually works than sell you magic." />
            <div className="v7-two">
              <div><h3 className="v7-col-h v7-up">What it is</h3><dl className="v7-defs">{IS.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl></div>
              <div><h3 className="v7-col-h v7-down">What it isn’t</h3><dl className="v7-defs">{ISNT.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl></div>
            </div>
          </div>
        </section>

        <section id="method" className="v7-sec v7-tone" aria-labelledby="method-h">
          <div className="v7-wrap">
            <SecHead id="method" eyebrow="Methodology" title="No screenshots. No selective memory." />
            <dl className="v7-grid3">{METHOD.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl>
            <p className="v7-row-note"><b>On the roadmap · shadow research · not live.</b> An AI sector-regime analyst — running in shadow mode. It reasons about which sectors are setting up to lead, logged and graded weekly against real sector returns at 21 and 42 days. It won’t influence a single live signal until it beats a fair baseline.</p>
          </div>
        </section>

        <section id="access" className="v7-sec" aria-labelledby="access-h">
          <div className="v7-wrap v7-access">
            <div>
              <SecHead id="access" eyebrow="Access" title="Private, invite-only. Not a subscription."
                sub="Nifty Satvik isn’t sold. It’s a private research tool shared with a small group of traders — no plans, no tiers, no card." />
              <dl className="v7-grid2 v7-grid-tight">{ACCESS.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl>
            </div>
            <div id="faq">
              <header className="v7-sh v7-sh-solo"><div><p className="v7-eyebrow">FAQ</p><h2>Questions, answered.</h2></div></header>
              <Faq />
            </div>
          </div>
        </section>

        <section className="v7-final" aria-labelledby="final-h">
          <div className="v7-wrap v7-final-in">
            <h2 id="final-h">Wake up to conviction. Not noise.</h2>
            <p>Invite-only. No subscription, no card — you keep your own broker account.</p>
            <div className="v7-cta">
              <button type="button" className="pf-btn" onClick={open}>Request access <ArrowRight size={16} aria-hidden /></button>
              <button type="button" className="pf-btn-2" onClick={() => go('record')}>See the track record</button>
            </div>
          </div>
        </section>
      </main>

      <footer className="v7-foot">
        <div className="v7-wrap">
          <div className="v7-foot-grid">
            <div>
              <a className="v7-brand" href="#top"><BrandMark size={20} /><span>Nifty Satvik</span></a>
              <p>Systematic swing research for the Nifty 500. Walk-forward validated; you place every order in your own broker.</p>
            </div>
            <nav aria-label="Product"><h4>Product</h4><ul>
              <li><button type="button" onClick={() => go('how')}>How it works</button></li>
              <li><button type="button" onClick={() => go('record')}>Track record</button></li>
              <li><button type="button" onClick={() => go('access')}>Access</button></li>
              <li><a href="/dashboard">Dashboard</a></li>
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
          <div className="v7-foot-base"><span>© {new Date().getFullYear()} Nifty Satvik · Made in Ahmedabad, India</span><span>Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">TradingView Lightweight Charts™</a></span></div>
          <p className="v7-fine">{DISCLAIMER}</p>
        </div>
      </footer>

      <div className={`v7-mcta${pastHero ? ' show' : ''}`} aria-hidden={!pastHero}>
        <a className="pf-btn-2" href="/login" tabIndex={pastHero ? 0 : -1}>Sign in</a>
        <button type="button" className="pf-btn" onClick={open} tabIndex={pastHero ? 0 : -1}>Request access</button>
      </div>
      <RequestAccessModal open={ask} onOpenChange={setAsk} />
    </div>
  );
}
