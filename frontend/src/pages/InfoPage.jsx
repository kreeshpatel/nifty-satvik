/**
 * InfoPage — the destination page for every footer link (Legal + Company).
 *
 * One component, content keyed by :slug. Reuses the landing's dark blue-glass-navy
 * system ([data-page-ctx="landing"] + tp-* classes) so the pages feel of a piece
 * with the marketing site. Honest, non-committal copy — nothing here is legal advice
 * or a claim we can't stand behind.
 */
import { useParams, Link, Navigate } from 'react-router-dom';
import brandLogo from '@/assets/brand/nifty-satvik-logo.png';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/landing-v2.css';

const PAGES = {
  disclaimer: {
    kicker: 'Legal',
    title: 'Disclaimer',
    body: [
      'Nifty Satvik publishes systematic research and decision-support signals. It is not a SEBI-registered investment adviser or research analyst, and nothing on this site is personalised investment advice.',
      'Every order is placed by you, in your own broker account. We never manage your capital or execute trades on your behalf.',
      'Past performance — including every backtested figure shown here — is not indicative of future returns. The backtests are in-sample, lumpy, and carry deep drawdowns, and no real capital has traded the strategy.',
      DISCLAIMER,
    ],
  },
  'risk-disclosure': {
    kicker: 'Legal',
    title: 'Risk disclosure',
    body: [
      'Trading and investing in equities carries substantial risk, including the total loss of capital. Systematic strategies are no exception.',
      'The weekly-swing book shown on this site is net of costs but before 20% STCG, in-sample on a survivorship-corrected universe, and its Deflated Sharpe Ratio sits below our internal certification gate — it is paper-tracked, not certified, and not proven on live capital.',
      'Backtested drawdowns have exceeded 40% peak-to-trough. Position sizes scale with your equity, and you are responsible for every order you place.',
      'Only deploy risk capital you can afford to lose. If in doubt, consult a SEBI-registered adviser.',
    ],
  },
  privacy: {
    kicker: 'Legal',
    title: 'Privacy',
    body: [
      'We collect only what is needed to run the product: your account details and the trades you choose to record yourself. We never connect to your broker, so we hold no broker credentials, no OAuth token and no access to your account.',
      'Market and stock data is fetched centrally and cached; only your own account data is stored per user.',
      'We do not sell your data. Your recorded trades and track record stay readable to you, and you can ask for them to be exported or deleted at any time.',
    ],
  },
  terms: {
    kicker: 'Legal',
    title: 'Terms',
    body: [
      'Nifty Satvik is private and invite-only — not a paid subscription. Access is granted, not purchased, and can be revoked at any time.',
      'You bring your own broker account and place every order yourself. We provide research and decision-support output only, never discretionary management of your funds.',
      'No outcome is guaranteed. The service is provided as-is, subject to market risk, and may change or pause without notice.',
    ],
  },
  about: {
    kicker: 'Company',
    title: 'About',
    body: [
      'Nifty Satvik is a systematic swing-signal research tool for the Nifty 500. Every weekday it scores the large- and mid-cap universe and surfaces a small, graded shortlist — each idea with an explicit entry, stop and target that you execute in your own broker account.',
      'The discipline is the product: walk-forward validation, pre-registered research, drawdowns shown in full, and a single codebase computing the features for both the backtest and the live signal.',
      'Built in Ahmedabad, India.',
    ],
  },
  'founder-note': {
    kicker: 'Company',
    title: 'Founder note',
    body: [
      'I built Nifty Satvik because I was tired of tip channels with selective memory and no accountability — screenshots of the wins, silence on the rest.',
      'Everything here is measured the way I would want my own money measured: net of costs, in-sample flagged, drawdowns shown in full, and nothing sold as certain that has not earned it. The weekly-swing book is promising, but its Deflated Sharpe sits below our gate — so it is paper-tracked, not proven, and I say so on every card.',
      '— The founder, Ahmedabad',
    ],
  },
  press: {
    kicker: 'Company',
    title: 'Press',
    body: [
      'No press yet — Nifty Satvik is early and invite-only.',
      'For media enquiries, please reach us through the Contact page.',
    ],
  },
  contact: {
    kicker: 'Company',
    title: 'Contact',
    body: [
      'The fastest way to reach us is the “Request access” form on the home page — we review every request personally.',
      'Members receive a direct support channel once onboarded. For anything else, use the same form and mark it as a general enquiry.',
    ],
  },
};

export default function InfoPage() {
  const { slug } = useParams();
  const page = PAGES[slug];
  if (!page) return <Navigate to="/" replace />;   // unknown slug → home (same as the catch-all)

  return (
    <div data-page-ctx="landing">
      <header className="alm-mast">
        <div className="alm-mast-inner">
          <Link className="alm-brand" to="/">
            <span className="alm-brand-mark"><img src={brandLogo} alt="Nifty Satvik" /></span>
            <span className="alm-brand-name">Nifty Satvik<span>Systematic Signals</span></span>
          </Link>
          <Link to="/" className="alm-btn alm-btn-ghost alm-btn-sm">&larr; Back to home</Link>
        </div>
      </header>

      <section className="alm-section">
        <div className="alm-wrap" style={{ maxWidth: 760 }}>
          <div className="tp-eyebrow">{page.kicker}</div>
          <h1 className="tp-title" style={{ margin: '8px 0 0' }}>{page.title}</h1>
          <div className="info-prose">
            {page.body.map((p, i) => <p key={i}>{p}</p>)}
          </div>

          <div className="info-links">
            {Object.entries(PAGES).map(([s, p]) => (
              <Link key={s} to={`/${s}`} className={`info-link${s === slug ? ' on' : ''}`}>{p.title}</Link>
            ))}
          </div>
        </div>
      </section>

      <footer className="alm-foot">
        <div className="alm-wrap">
          <div className="alm-foot-rule">
            <span>© 2026 Nifty Satvik</span>
            <span>Made in Ahmedabad, India</span>
          </div>
          <p className="alm-foot-disc">{DISCLAIMER}</p>
        </div>
      </footer>
    </div>
  );
}
