/** Reviewed landing copy and fallback data (moved out of LandingV3, 2026-11-05). Compliance
 * wording here is load-bearing: change it only with the owner. Figures come from
 * GET /api/landing-stats; FALLBACK is the reviewed copy shown only when the API is down. */
export const FALLBACK = {
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

export const STEPS = [
  ['Scan', 'Every Saturday we refresh point-in-time prices and fundamentals across the full Nifty 500 large- and mid-cap universe and rebuild the book from the weekly close. No lookahead, ever.'],
  ['Rank', 'Each name is scored cross-sectionally on trend quality and risk. The ranking rule is proprietary and frozen — derived once from history, then never touched.'],
  ['Screen', 'Only the top-ranked names that also pass strict liquidity and solvency filters survive. Most days that is one or two. Often zero — and that restraint is part of the edge.'],
  ['Risk-size', 'Each survivor ships as a complete plan — entry, a hard stop, a target, and a size set to a fixed risk budget with a volatility cap — ready for you to place.'],
];

export const PLAN_PARTS = [
  ['Conviction + grade', 'A cross-sectional rank of trend quality against risk, distilled into an A–D grade. Only the top grades ship as signals.'],
  ['Entry, stop, target', 'Concrete prices — an ATR-based stop and a fixed profit target — not a vague “buy now and hope.”'],
  ['Position size', 'Scaled to your account and capped so risk per trade stays bounded. You place the order yourself and record the fill you actually got.'],
  ['Exit logic', 'A multi-week horizon with a hard stop, a target, a trailing stop, and a time cap. The rule tells you when to leave — target, stop, or time.'],
];

export const IS = [
  ['Cross-sectional conviction', 'Every name is ranked against the whole universe on trend quality and risk; only the strongest, most liquid, most solvent names clear the bar.'],
  ['Asymmetry by construction', 'Hard ATR stops and a fixed profit target turn an above-even win rate into wins that outweigh the losses.'],
  ['Restraint', 'Most days it stays silent. Not trading the marginal setups is part of the return.'],
];

export const ISNT = [
  ['Not a direction oracle', 'It wins about 60% of the time in backtest — an edge, not clairvoyance. It ranks trend quality across names; it does not promise any single stock simply “goes up”.'],
  ['Not AI sector rotation', 'It doesn’t decide which sector leads. That layer is still in shadow research, graded before it can touch a trade.'],
  ['Not a guarantee', 'Backtests flatter, the drawdown is deep, some years are flat, and the live record is still being earned.'],
];

export const FAQ = [
  ['Is Nifty Satvik SEBI-registered?', 'No. Nifty Satvik is not a SEBI-registered investment advisor or research analyst. We publish research and decision-support signals — not personalised investment advice — and we never manage your capital. Every order is placed by you, in your own broker account.'],
  ['Do I need a Zerodha Kite account?', 'No. Nifty Satvik does not connect to your broker and does not place orders. You read the plan here and place every order yourself, in whatever broker you already use, then record what you actually filled so the track record reflects your trades rather than ours.'],
  ['What’s the minimum capital to start?', 'There’s no hard floor, but we recommend ₹2,00,000 minimum. Position sizes scale with your equity, and small accounts have trouble respecting stops on higher-priced names like NESTLEIND or BAJFINANCE.'],
  ['How is this different from a Telegram tip channel?', 'Three differences. (1) Every signal has explicit entry, stop, and target — no “buy at CMP”. (2) Every signal is walk-forward backtested before it ships — no “this stock looks good”. (3) Every trade is logged with timestamps, fills, and P&L — no screenshots, no selective memory.'],
  ['What does it cost?', 'Nothing today. Nifty Satvik is private and invite-only — not a paid subscription. You keep your own broker account; we don’t charge a fee or manage your money. Revoke access anytime — your journal and track-record data stay readable.'],
  ['What happens on a flat or bearish day?', 'The dashboard says so plainly — “No fresh signals today — next scan at 16:15 IST.” The system is designed to underfit; on many weekdays it surfaces zero A-grade signals. Patience is part of the edge.'],
];

export const METHOD = [
  ['Walk-forward only', 'Every model is tested on out-of-sample bars it never saw at training. We measure what generalises — not what fits the past.'],
  ['Costs are baked in', 'Brokerage and STT are modelled into every backtested trade. The numbers you see are after costs, not before.'],
  ['The live record is the judge', 'Backtests can flatter. Live trading began recently and the forward record only grows — that’s the test we hold ourselves to.'],
  ['We kill our own ideas', 'Every research idea is pre-registered with a pass/fail bar before we see results. Most get killed. Only what survives reaches your dashboard.'],
  ['Survivorship-corrected', 'The backtest universe is reconstructed from historical index membership and puts delisted and merged names (Yes Bank, Suzlon, Jet Airways) back in — it can’t quietly keep only the winners.'],
  ['One codebase, no skew', 'A single source of truth computes the features for both the backtest and the live signal. What we measure is what we serve.'],
];

export const ACCESS = [
  ['No subscription', 'No monthly plan, no paywall. Access is granted, not purchased.'],
  ['Your account, your orders', 'We never connect to your broker, place an order, or hold your capital. You trade your own account and tell us what filled.'],
  ['Small by design', 'Onboarded in small batches, so the dashboard stays fast and the feedback loop stays real.'],
  ['Leave anytime', 'Nothing to disconnect, because nothing was connected. Your journal and track-record data stay readable.'],
];
