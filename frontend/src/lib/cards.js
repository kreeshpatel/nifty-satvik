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
