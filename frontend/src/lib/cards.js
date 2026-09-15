/**
 * Pure derivations for a weekly card's displayed values.
 *
 * WHY THESE LEFT THE COMPONENT. Each of these was an inline expression inside enrichSignal or a
 * row component, and each was wrong in a way that reads as plausible on screen:
 *
 *   - R-on-a-position divided the user's OWN gain by the MODEL's risk-per-share. A reader who
 *     filled 4% above the model entry saw +0.80R where their real figure was +0.37R.
 *   - "Today" was `new Date().toISOString()`, i.e. UTC. The NSE day is IST, so for the 5h30m
 *     between 00:00 and 05:30 IST every day the app believed it was still yesterday — and that
 *     value decides whether a buy window is open, closing or closed.
 *   - The hold counter ran from the signal date, but the position opens at the FILL, up to three
 *     calendar days later.
 *   - Potential-to-target measured from the middle of the buy band even for cards whose actual
 *     fill price is now known.
 *
 * A number nobody can unit-test is a number nobody checks. These are pure, exported, and pinned
 * in cards.test.js.
 */

const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;

/**
 * Today's date on the NSE calendar, 'YYYY-MM-DD'.
 *
 * NOT `new Date().toISOString()` — that is UTC, which is 5h30m behind IST, so between midnight
 * and 05:30 IST it returns YESTERDAY. This value is compared against `buy_window_until` to decide
 * whether a card is buyable, so being a day behind silently keeps an expired window open.
 * Deliberately not browser-local either: the trading day is Indian wherever the reader is.
 */
export function nseToday(now = Date.now()) {
  return new Date(now + IST_OFFSET_MS).toISOString().slice(0, 10);
}

/** Parse a bare 'YYYY-MM-DD' as a LOCAL calendar date (never UTC midnight). */
export function parseCalendarDate(v) {
  if (!v) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v));
  if (!m) { const d = new Date(v); return Number.isNaN(d.getTime()) ? null : d; }
  return new Date(+m[1], +m[2] - 1, +m[3]);
}

/**
 * R multiple of an OPEN position, measured against the risk actually taken.
 *
 * Risk per share is `fill - stop`, not `entry - stop`. Both the gain and the risk must be
 * measured from the same fill or the ratio means nothing: dividing a reader's own gain by the
 * model's risk flatters every fill above the model entry and punishes every fill below it.
 * Returns null when the fill is at or below the stop — there is no positive risk unit to divide
 * by, and a negative denominator would silently flip the sign.
 */
export function positionR({ ltp, fill, stop }) {
  if (!(ltp > 0) || !(fill > 0) || !(stop > 0)) return null;
  const risk = fill - stop;
  if (!(risk > 0)) return null;
  return (ltp - fill) / risk;
}

/**
 * Percent still to run from here to the target.
 *
 * `from` is the fill when the record knows it (the monitor publishes `filled_price` once the
 * window fills) and the middle of the buy band only while that is still unknown. Before the fill
 * the mid is an estimate; after it, quoting the estimate discards a fact we hold.
 */
export function toTargetPct({ target, filledPrice, buyLow, buyHigh, entry }) {
  const mid = buyLow > 0 && buyHigh > 0 ? (buyLow + buyHigh) / 2 : null;
  const from = filledPrice > 0 ? filledPrice : (mid ?? entry);
  if (!(from > 0) || !(target > 0)) return null;
  return ((target - from) / from) * 100;
}

/**
 * Which week of the hold cap this position is in, counted from the day it OPENED.
 *
 * The card is issued at the Saturday close and filled at the next session's open, so the hold
 * starts up to three calendar days after `signal_date`. Counting from the signal ages every
 * position early and, against a 13-week cap, can retire one on screen a week before the engine
 * would. Prefers the recorded fill date, then the model's bought_date, and only then the signal.
 */
export function holdWeek({ filledOn, boughtDate, signalDate, now = Date.now(), capWeeks = 13 }) {
  const start = parseCalendarDate(filledOn) || parseCalendarDate(boughtDate)
    || parseCalendarDate(signalDate);
  if (!start) return null;
  const days = Math.floor((now - start.getTime()) / 86400000);
  if (days < 0) return null;
  return Math.min(capWeeks, Math.max(1, Math.ceil((days + 1) / 7)));
}

/** Well-formed demerger notes, oldest ex-date first. Shared so both readers agree on what counts. */
function validDemergers(corporateActions) {
  if (!Array.isArray(corporateActions)) return [];
  return corporateActions
    .filter((a) => a && a.kind === 'demerger' && a.retained > 0 && a.retained <= 1)
    .sort((a, b) => String(a.ex_date ?? '').localeCompare(String(b.ex_date ?? '')));
}

/**
 * The demerger audit notes on a held card, each with the entry the position had BEFORE it.
 *
 * B′ (PR #98) multiplies a held position's entry/stop/target by the retained ratio on the ex-date
 * and credits the spun-off value as cash. The card then prints only the re-based levels, so HEG
 * reads entry 242.95 against a broker fill near 653 with nothing on screen explaining the gap.
 * `entry / retained` undoes the re-base; with more than one event, each note's pre-event entry
 * divides out that event AND every later one, because the scaling compounds.
 *
 * Absent key, a non-array, or a malformed note → no notes. Nothing else on the card depends on it.
 */
export function demergerNotes(corporateActions, entry) {
  const events = validDemergers(corporateActions);
  return events.map((a, i) => {
    const scale = events.slice(i).reduce((acc, e) => acc * e.retained, 1);
    return {
      exDate: a.ex_date ?? null,
      retainedPct: a.retained * 100,
      spinPerShare: typeof a.spin_value_per_share === 'number' ? a.spin_value_per_share : null,
      // The factor this event and every later one applied. On the first note it is the whole
      // re-base, which is what a caller holding an UN-rebased price (a broker fill) multiplies by.
      scale,
      originalEntry: entry > 0 ? entry / scale : null,
    };
  });
}

/**
 * The reader's average buy price on a demerged holding, re-based the way B′ re-bases the model's.
 *
 * The ledger's `avg_buy_price` is what the reader paid for a share that has since been split in two.
 * Priced against today's post-ex quote it reports the spun-off value as a loss: HEG read about −65%
 * (653.00 against ~225) while the model, re-based, read about −8%. A buy made BEFORE an ex-date
 * carries `retained` of its cost into the parent share and the rest into the spun-off shares, which
 * sit at the reader's broker and not in this ledger. So each pre-ex buy is scaled by the retained
 * ratio of every ex-date it predates, and a post-ex buy is left alone. The result prices the parent
 * shares only, which is also the basis the card's re-based stop and target are on.
 *
 * WHEN a buy happened is the hard part: the capture modal sends no `executed_at`, so an event's
 * date is when it was RECORDED, which is on or after the fill. Hence:
 *   - recorded before an ex-date → the fill was pre-ex. Certain.
 *   - recorded on/after it → decided by price. The ex-date moves the quote from `prior_close` to
 *     `prior_close × retained`, and a fill above the geometric midpoint of the two is a pre-ex fill
 *     recorded late. `basis: 'events+price'` says that evidence was used.
 *   - no event trail yet (still loading, or the request failed) → every buy is assumed pre-ex,
 *     which is the normal case for a position held into its demerger. `basis: 'assumed'`.
 *
 * Returns { avg, rawAvg, basis }; basis is 'none' when there is no demerger to apply.
 */
export function ledgerCostBasis({ avgBuy, events, corporateActions }) {
  const rawAvg = avgBuy > 0 ? Number(avgBuy) : null;
  const dem = validDemergers(corporateActions);
  if (dem.length === 0 || rawAvg == null) return { avg: rawAvg, rawAvg, basis: 'none' };
  const scaleFrom = (phase) => dem.slice(phase).reduce((acc, d) => acc * d.retained, 1);

  const buys = Array.isArray(events)
    ? events.filter((e) => e && !e.superseded && String(e.side).toUpperCase() === 'BUY'
                      && Number(e.qty) > 0 && Number(e.price) > 0)
    : [];
  if (buys.length === 0) return { avg: rawAvg * scaleFrom(0), rawAvg, basis: 'assumed' };

  let qty = 0, cost = 0, byPrice = false;
  for (const e of buys) {
    const q = Number(e.qty), px = Number(e.price);
    const day = String(e.executed_at || e.created_at || '').slice(0, 10);
    // How many ex-dates the RECORD falls on or after; with no date at all, price decides every one.
    let phase = day ? dem.filter((d) => String(d.ex_date ?? '') <= day).length : dem.length;
    while (phase > 0) {
      const d = dem[phase - 1];
      if (!(d.prior_close > 0 && px > d.prior_close * Math.sqrt(d.retained))) break;
      phase -= 1;
      byPrice = true;
    }
    qty += q;
    cost += q * px * scaleFrom(phase);
  }
  return { avg: cost / qty, rawAvg, basis: byPrice ? 'events+price' : 'events' };
}
