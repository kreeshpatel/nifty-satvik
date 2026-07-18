// frontend/src/lib/signalCopy.js
// Compliance: research / decision-support framing only — never "guarantee", "will", "sure".

export const SECTIONS = {
  SELL:    { title: 'Sell now',           sub: 'The model has exited these — sell on the next market open.' },
  BUY:     { title: 'Buy today',          sub: "New high-conviction ideas from today's scan." },
  CLOSING: { title: 'Buy window closing', sub: 'Still actionable, but the entry window is about to close.' },
  HOLD:    { title: 'Holding',            sub: "Open positions — no action needed, we're tracking them." },
  WATCH:   { title: 'Brewing',            sub: 'On the radar but not actionable yet — watching for a trigger.' },
  CLOSED:  { title: 'Closed & missed',    sub: 'Resolved, or past their entry window.' },
};

export const CONVICTION = {
  HIGH: { label: 'High conviction',      tone: 'brand'   },
  MED:  { label: 'Moderate conviction',  tone: 'neutral' },
  LOW:  { label: 'Low — watchlist only', tone: 'muted'   },
};

export const TIER = {
  signal:    { label: 'SIGNAL',    sub: 'Actionable today' },
  watchlist: { label: 'WATCHLIST', sub: 'Monitoring only'  },
};

const fmtShort = (d) => !d ? '' :
  new Date(d).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }).toUpperCase();
const daysLeft = (until, now = new Date()) =>
  !until ? null : Math.max(0, Math.ceil((new Date(until) - now) / 86400000));

export function actionChip(sig = {}, now = new Date()) {
  const a = sig.actionability, status = (sig.status || '').toUpperCase();
  if (status === 'HIT_TARGET') return { text: 'TARGET HIT · SELL ON NEXT OPEN', tone: 'bull' };
  if (status === 'HIT_STOP')   return { text: 'STOP HIT · SELL ON NEXT OPEN',   tone: 'bear' };
  if (status === 'EXPIRED' || a === 'EXIT_REQUIRED')
    return { text: 'EXIT · SELL ON NEXT OPEN', tone: 'warn' };
  if (a === 'BUY_OPEN' || (!a && sig.tier === 'signal')) {
    const left = daysLeft(sig.buy_window_until, now);
    return {
      text: left != null ? `BUY BY ${fmtShort(sig.buy_window_until)} · ${left} DAY${left === 1 ? '' : 'S'} LEFT`
                         : 'BUY — WINDOW OPEN',
      tone: 'brand',
    };
  }
  if (a === 'BUY_CLOSED') return { text: 'WINDOW CLOSED', tone: 'muted' };
  return { text: 'WATCHING', tone: 'muted' };
}

export function holdingChip(sig = {}) {
  if (!sig.signal_date || !sig.hold_days) return 'HOLDING';
  const d = Math.max(1, Math.round((Date.now() - new Date(sig.signal_date)) / 86400000));
  return `HOLDING · DAY ${Math.min(d, sig.hold_days)} OF ${sig.hold_days}`;
}

export const STATES = {
  empty:        'No new signals today. The scanner runs at 4:15 PM IST on trading days.',
  loading:      'Scanning the market…',
  error:        "Couldn't load signals. Pull to refresh, or try again shortly.",
  windowClosed: 'Entry window has closed — we no longer recommend buying this here.',
  noWatchlist:  'Nothing brewing right now.',
  // Stage 6: between scans, doing nothing IS the strategy — suppress the urge to fiddle.
  idle:         'Nothing to buy right now — and that’s the strategy working. The next scan is Saturday; between scans, sitting on your hands is what the backtest assumes you do.',
};

// ── Stage 6 — the discipline harness copy (PRODUCT_SYNTHESIS §1). Forward-honest; never a promise. ──
export const DISCIPLINE = {
  title: 'DISCIPLINE · YOUR BOOK vs THE MODEL’S',
  explain: 'In research, cherry-picking names from the ranked book regressed toward a ~0.74 Sharpe null — '
    + 'barely better than random picks. Taking the whole book with the planned exits measured ~1.03. This gauge '
    + 'is where your recorded behaviour sits on that span. An estimate from your own ledger, not a promised return.',
  legLabels: {
    coverage: 'Took the buys', fidelity: 'Inside entry band', timing: 'On time',
    exit_adherence: 'Exited on plan', hold_through: 'Held through', concentration: 'Spread evenly',
  },
  skipFriction: (rank, ticker) =>
    `Skipping #${rank} ${ticker} is where cherry-picking regresses toward the 0.74 null — the ranked book only works taken whole.`,
  fatTail: 'Cutting a winner early doesn’t shave a little return — it removes the rare 10–40R monster that '
    + 'carries the whole book. In the research record, the winner-cut was the single most expensive user behaviour.',
  patternExitReframe: (r) =>
    `You’re booking a ${r != null ? `+${r.toFixed(1)}R ` : ''}winner on schedule. The down-week from the high IS the exhaustion signal — this exit always feels like selling the bottom, and it isn’t.`,
  coInstruct: 'Place both resting orders on your broker NOW, while you’re here: the partial-profit '
    + 'limit and the stop-loss. The plan’s edge is execution-sensitive — a resting order fires without you watching.',
};

// Stage 6c — cold-start onboarding (shown once; forward-honest expectations).
export const COLD_START = {
  title: 'Before your first trade — what normal looks like',
  points: [
    'This is a weekly-swing book: ~5 names, held weeks to months, decided once a week at the Saturday scan. Most days there is nothing to do — that’s by design, not neglect.',
    'Roughly 4 in 10 positions hit their stop. A losing streak and a double-digit drawdown (−11% has been normal in research) are expected parts of the path, not a sign it broke.',
    'The record says the return comes from a few big winners carried to plan. The costly mistakes are skipping ranked names and cutting winners early — the app will nudge you when either is about to happen.',
    'You execute on your own broker and report fills here. The model’s paper book is a reference, never a promise of your return.',
  ],
  ack: 'I understand — lumpy is normal',
};

// Stage 6c — just-in-time lessons, keyed by journey flag. Unlocked by the user's OWN events.
export const LESSONS = {
  lesson_first_buy: {
    title: 'First buy recorded',
    body: 'Two resting orders make the plan real: the partial-profit limit and the stop-loss. Place both on your broker now — they execute the plan while you’re not watching.',
  },
  lesson_first_2r: {
    title: 'First +2R partial — this is the machine working',
    body: 'You just booked the planned 40% at 2R. The rest of the position is now playing for the fat tail — let the runner run; the 44-week SMA decides its exit, not a feeling.',
  },
  lesson_first_drawdown: {
    title: 'Your first drawdown — this is the normal part',
    body: 'Every path through the research record includes stretches like this (−11% was typical). The measured mistake is de-risking mid-drawdown; the plan’s stops already cap each name’s downside.',
  },
};

export const TOOLTIPS = {
  conviction: 'How strongly the model favours this setup — its own confidence, not a probability of profit.',
  buyWindow:  'Buy any time in this 2–3 day window. Entry prices are indicative, not a hard limit.',
  rr:         'Reward-to-risk: expected upside to target vs downside to the stop.',
  stop:       'The price at which we cut losses to protect your capital.',
  hold:       'Typical holding period. The exit rules can sell sooner or extend it.',
};

export const EXPECTATION =
  'In research backtests on stocks the model never trained on, roughly 2 in 3 signals reached ' +
  'target and about 1 in 3 hit the stop. Buying within the recommended window preserved most of ' +
  'that edge. These are research figures, not a promise of future results.';

export const DISCLAIMER =
  'Research and decision-support output, not investment advice. Model and backtested results are ' +
  'not indicative of future returns. All trading carries risk of loss; you are responsible for ' +
  'your own decisions.';

/**
 * Build the segments for the dot-separated anchor row.
 *
 * Returns an array of segment descriptors so the caller can colour each
 * segment independently in JSX:
 *   { text: string, color?: string }   — color is a CSS custom-property string
 *
 * Example output:
 *   Entry ₹180–182 · Target ₹209 (+16%) · Stop ₹161 (−11%) · R:R 1.5 · ~15d
 *
 * All prices passed in as numbers. Percentages are derived from entry midpoint
 * when the pct fields are absent. Missing fields are omitted cleanly.
 *
 * @param {object} sig - raw signal object
 * @param {function} fmtPrice - price formatter (₹ prefix, 2dp)
 * @param {function} fmtPct   - percent formatter (+/- sign, 2dp)
 */
export function buildAnchorRow(sig = {}, fmtPrice, fmtPct) {
  const { entry, entry_high, max_entry, stop, target, stop_pct, target_pct, rr, hold_days } = sig;

  const entryMid = typeof entry === 'number' ? entry : null;
  // Entry-range high = the buy-limit ceiling (max_entry) — the highest fill that
  // keeps reward:risk above the floor. Legacy signals used entry_high; max_entry
  // is the canonical field. Renders as a range only when it sits above entry.
  const entryHigh =
    typeof max_entry === 'number' ? max_entry
    : typeof entry_high === 'number' ? entry_high
    : null;

  // Resolve pct from field if present, else derive from entry midpoint.
  const resolvedTargetPct =
    typeof target_pct === 'number'
      ? target_pct
      : entryMid && typeof target === 'number' && entryMid > 0
        ? ((target - entryMid) / entryMid) * 100
        : null;
  const resolvedStopPct =
    typeof stop_pct === 'number'
      ? stop_pct
      : entryMid && typeof stop === 'number' && entryMid > 0
        ? ((stop - entryMid) / entryMid) * 100
        : null;

  const segments = [];

  // Entry — may be a range (entry–entry_high) or a single price.
  if (entryMid != null) {
    const entryStr =
      entryHigh != null && entryHigh !== entryMid
        ? `Entry ${fmtPrice(entryMid)}–${fmtPrice(entryHigh)}`
        : `Entry ${fmtPrice(entryMid)}`;
    segments.push({ text: entryStr, color: 'var(--text-2)' });
  }

  // Target — bull colour.
  if (typeof target === 'number') {
    const pctStr = resolvedTargetPct != null ? ` (${fmtPct(resolvedTargetPct)})` : '';
    segments.push({ text: `Target ${fmtPrice(target)}${pctStr}`, color: 'var(--bull)' });
  }

  // Stop — bear colour.
  if (typeof stop === 'number') {
    const pctStr = resolvedStopPct != null ? ` (${fmtPct(resolvedStopPct)})` : '';
    segments.push({ text: `Stop ${fmtPrice(stop)}${pctStr}`, color: 'var(--bear)' });
  }

  // R:R — neutral.
  if (rr != null) {
    segments.push({ text: `R:R ${Number(rr).toFixed(1)}`, color: 'var(--text-2)' });
  }

  // Hold — neutral.
  if (typeof hold_days === 'number') {
    segments.push({ text: `~${hold_days}d`, color: 'var(--text-3)' });
  }

  return segments;
}

/**
 * Buy-plan for the card face — the buy-limit ceiling + the T+1 execution rule made
 * PROMINENT. The cron fires at 4:15 PM after the close, so you act at the NEXT open;
 * `max_entry` is the highest fill that keeps reward:risk above the floor, so chasing a
 * gap-up above it collapses the trade. If today's price already ran past the limit, the
 * plan flips to a "don't chase" warning.
 *
 * Returns { state, tone, head, sub } or null when there's no entry reference.
 *   state: 'ok' | 'past'   tone: 'brand' | 'warn'   head: the price line   sub: the rule
 */
export function buyPlan(sig = {}, fmtPrice = (v) => `₹${v}`) {
  const { entry, max_entry, current_price } = sig;
  const limit = typeof max_entry === 'number' ? max_entry : null;
  if (limit != null && typeof current_price === 'number' && current_price > limit) {
    return {
      state: 'past', tone: 'warn',
      head: `Above limit ${fmtPrice(limit)}`,
      sub: 'ran past the buy-limit — wait for a pullback, don’t chase',
    };
  }
  if (limit != null) {
    return {
      state: 'ok', tone: 'brand',
      head: `Buy ≤ ${fmtPrice(limit)}`,
      sub: 'at next open · don’t chase above',
    };
  }
  if (typeof entry === 'number') {
    return { state: 'ok', tone: 'brand', head: `Buy near ${fmtPrice(entry)}`, sub: 'at next open' };
  }
  return null;
}
