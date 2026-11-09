/**
 * Public website — design v7 "Institutional" (docs/DESIGN_BRIEF_V5.md §10).
 * Asymmetric layout; the hero is a product shot built from real components (LwChart on the
 * backtest series from GET /api/landing-stats); 1px rules instead of cards; no gradients, no
 * shadows, no illustrations. All copy comes from lib/landingContent (reviewed; verbatim).
 */
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Minus, Plus } from 'lucide-react';
import RequestAccessModal from '@/components/landing/RequestAccessModal';
import BrandMark from '@/components/brand/BrandMark';
import LwChart from '@/components/charts/LwChart';
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

/* Sample rows for the product shot — labelled "Sample" on screen; no live call is implied. */
const SAMPLE = [
  ['MCX', '2,815.40', '2,426.70', '3,592.80', '+27.6'],
  ['SYRMA', '1,376.70', '1,193.90', '1,742.30', '+26.6'],
  ['LAURUSLABS', '1,543.10', '1,402.60', '1,824.10', '+18.2'],
];

function Section({ id, eyebrow, title, sub, children, wide }) {
  return (
    <section id={id} className={`v7-sec${wide ? ' v7-sec-wide' : ''}`} aria-labelledby={`${id}-h`}>
      <div className="v7-wrap v7-sec-grid">
        <header className="v7-sec-head">
          <p className="v7-eyebrow">{eyebrow}</p>
          <h2 id={`${id}-h`}>{title}</h2>
          {sub && <p className="v7-sec-sub">{sub}</p>}
        </header>
        <div className="v7-sec-body">{children}</div>
      </div>
    </section>
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
  const eq = useMemo(() => stats.equity_bt || [], [stats.equity_bt]);
  const last = eq[eq.length - 1];
  const alpha = last && last.b != null ? Math.round(last.s - last.b) : null;
  const go = (id) => { setMenu(false); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const open = () => { setMenu(false); setAsk(true); };

  const growth = useMemo(() => {
    const s = eq.filter((d) => d && d.s != null).map((d) => ({ time: toTime(d.t), value: Number(d.s) }));
    const b = eq.filter((d) => d && d.b != null).map((d) => ({ time: toTime(d.t), value: Number(d.b) }));
    const out = [{ type: 'area', data: s, color: '#20C4A0', title: 'Strategy' }];
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
      </header>

      <main id="main">
        {/* HERO — copy left, product shot right */}
        <section className="v7-hero" id="top">
          <div className="v7-wrap v7-hero-grid">
            <div className="v7-hero-copy">
              <p className="v7-eyebrow"><span className="v7-dot" aria-hidden />Invite-only · Nifty 500 research</p>
              <h1>Systematic swing research for the Nifty&nbsp;500.</h1>
              <p className="v7-lede">
                Nifty Satvik re-scores the Nifty 500 every Saturday evening, and re&#8209;prices what you already hold after
                each weekday close. You get A&#8209;grade signals with an explicit entry, stop and target — and you place the
                orders yourself.
              </p>
              <div className="v7-cta">
                <button type="button" className="pf-btn" onClick={open}>Request access <ArrowRight size={16} aria-hidden /></button>
                <button type="button" className="pf-btn-2" onClick={() => go('how')}>How it works</button>
              </div>
              <dl className="v7-facts">
                <div><dt>Universe</dt><dd>Nifty 500</dd></div>
                <div><dt>Re-score</dt><dd>Sat 18:00 IST</dd></div>
                <div><dt>Execution</dt><dd>Your broker</dd></div>
              </dl>
            </div>

            <figure className="v7-shot" aria-label="Product preview">
              <div className="v7-shot-bar">
                <span className="v7-shot-tab on">Track record</span><span className="v7-shot-tab">This week</span><span className="v7-shot-tab">Research</span>
                <span className="v7-shot-meta">Backtest {bt.period} · in-sample</span>
              </div>
              <div className="v7-shot-body">
                <div className="v7-shot-head">
                  <div>
                    <p className="v7-k">Growth of ₹100</p>
                    <p className="v7-shot-big" data-num>₹{last ? num(last.s, 0) : '—'} <span className="v7-up">▲ {signed(last ? last.s - 100 : null)}%</span></p>
                  </div>
                  <ul className="v7-legend" aria-hidden>
                    <li><i className="v7-key-s" />Strategy</li><li><i className="v7-key-b" />Nifty 500</li>
                  </ul>
                </div>
                <LwChart series={growth} height={220} label={`Growth of ₹100, ${bt.period}: strategy ₹${last ? num(last.s) : '—'} vs Nifty 500 ₹${last ? num(last.b) : '—'} (backtest, in-sample)`} />
                <table className="v7-mini" aria-label="Sample research calls">
                  <caption>This week's calls <span>Sample</span></caption>
                  <thead><tr><th scope="col">Symbol</th><th scope="col">Entry</th><th scope="col">Stop</th><th scope="col">Target</th><th scope="col">Upside</th></tr></thead>
                  <tbody>{SAMPLE.map(([s, e, st, t, u]) => (
                    <tr key={s}><th scope="row">{s}</th><td>{e}</td><td className="v7-down">{st}</td><td className="v7-up">{t}</td><td className="v7-up">▲ {u}%</td></tr>
                  ))}</tbody>
                </table>
              </div>
            </figure>
          </div>
        </section>

        {/* KEY FIGURES */}
        <section className="v7-figs" aria-label="Backtest summary">
          <div className="v7-wrap">
            <dl className="v7-figs-row">
              <div><dt>CAGR, net</dt><dd data-num>~{num(bt.cagr_pct)}%</dd></div>
              <div><dt>vs Nifty 500</dt><dd data-num className="v7-up">{alpha != null ? `${signed(alpha)} pts` : '—'}</dd></div>
              <div><dt>Win rate</dt><dd data-num>{num(bt.win_rate_pct)}%</dd></div>
              <div><dt>Trades</dt><dd data-num>{num(bt.total_trades)}</dd></div>
              <div><dt>Max drawdown</dt><dd data-num className="v7-down">{num(bt.max_drawdown_pct)}%</dd></div>
            </dl>
            <p className="v7-fine">Weekly-swing book, survivorship-corrected backtest {bt.period}, net of brokerage, STT and slippage, before 20% STCG. Sharpe {num(bt.sharpe, 2)}, DSR {num(bt.dsr, 2)} — below the certification gate. In-sample; no real capital has traded.</p>
          </div>
        </section>

        <Section id="how" eyebrow="How it works" title="No black box. The same path, every week."
          sub="Every signal travels one transparent, frozen pipeline — identical in backtest and in production. The one thing we keep private is the exact ranking formula.">
          <ol className="v7-steps">
            {STEPS.map(([t, d], i) => (
              <li key={t}><span className="v7-step-n" data-num>{String(i + 1).padStart(2, '0')}</span><h3>{t}</h3><p>{d}</p></li>
            ))}
          </ol>
          <p className="v7-note"><b>The ranking formula is not disclosed.</b> The exact factor, thresholds, and hold rules are the edge — so they stay internal. You get the complete plan and the full track record; the recipe stays ours.</p>
        </Section>

        <Section id="plan" eyebrow="What you get" title="Every signal is a complete trade plan.">
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
            <dl className="v7-defs">{PLAN_PARTS.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
          </div>
        </Section>

        <Section id="record" eyebrow="Track record" title="The numbers, net of every cost."
          sub={`The weekly-swing book on a survivorship-corrected backtest (${bt.period}), net of brokerage, STT and slippage. In-sample and not yet certified — no real capital has traded.`}>
          <div className="v7-charts">
            <figure className="v7-panel">
              <figcaption>Growth of ₹100 <span>Strategy vs Nifty 500</span></figcaption>
              <LwChart series={growth} height={260} label="Growth of ₹100, strategy versus Nifty 500, backtest" />
            </figure>
            <figure className="v7-panel">
              <figcaption>Calendar-year returns <span>Net · first and last years partial</span></figcaption>
              <LwChart series={yearly} height={260} priceFormat={pctFormat} label="Calendar-year net returns, backtest" />
            </figure>
          </div>
          <p className="v7-fine">Weekly-swing book, backtest {bt.period}, net of costs before 20% STCG, in-sample on the survivorship-corrected universe — Sharpe {num(bt.sharpe, 2)}, DSR {num(bt.dsr, 2)} (below the certification gate). Not indicative of future results; a handful of strong-trend years drive the total, with a &gt;40% peak-to-trough drawdown. No real capital has traded — the forward paper record since {stats.live.since} is the real test.</p>
        </Section>

        <Section id="edge" eyebrow="Why trust it" title="What the edge is — and what it isn’t.">
          <div className="v7-two">
            <div><h3 className="v7-col-h v7-up">What it is</h3><dl className="v7-defs">{IS.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl></div>
            <div><h3 className="v7-col-h v7-down">What it isn’t</h3><dl className="v7-defs">{ISNT.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl></div>
          </div>
        </Section>

        <Section id="method" eyebrow="Methodology" title="No screenshots. No selective memory.">
          <dl className="v7-grid3">{METHOD.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl>
          <p className="v7-note"><b>On the roadmap · shadow research · not live.</b> An AI sector-regime analyst — running in shadow mode. It reasons about which sectors are setting up to lead, logged and graded weekly against real sector returns at 21 and 42 days. It won’t influence a single live signal until it beats a fair baseline.</p>
        </Section>

        <Section id="access" eyebrow="Access" title="Private, invite-only. Not a subscription."
          sub="Nifty Satvik isn’t sold. It’s a private research tool shared with a small group of traders — no plans, no tiers, no card.">
          <dl className="v7-grid2">{ACCESS.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl>
        </Section>

        <Section id="faq" eyebrow="FAQ" title="Questions, answered."><Faq /></Section>

        <section className="v7-final" aria-labelledby="final-h">
          <div className="v7-wrap v7-final-in">
            <div>
              <h2 id="final-h">Wake up to conviction. Not noise.</h2>
              <p>Invite-only. No subscription, no card — you keep your own broker account.</p>
            </div>
            <div className="v7-cta">
              <button type="button" className="pf-btn" onClick={open}>Request access <ArrowRight size={16} aria-hidden /></button>
              <button type="button" className="pf-btn-2" onClick={() => go('record')}>See the track record</button>
            </div>
          </div>
          <p className="v7-wrap v7-fine">Research and decision-support output, not investment advice. Past performance is not indicative of future returns. Subject to market risk.</p>
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
