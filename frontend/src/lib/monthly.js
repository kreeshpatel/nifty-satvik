/**
 * Monthly performance, from a source that actually means something.
 *
 * WHAT WAS WRONG. The Portfolio chart bucketed closed trades by exit month and **summed their
 * return percentages**. Five trades at +10% rendered a +50% bar. That is not a return: each
 * position is a fraction of the book (the sizer risks ~2% per trade), so the portfolio moved a
 * small multiple of that, and the figure scales with how MANY trades a month happened to close.
 * A busy month dwarfs a quiet one of identical quality, and no two bars are comparable.
 *
 * Percentages of different denominators do not add. That is the whole defect.
 *
 * TWO HONEST SOURCES, preferred in this order:
 *
 *   1. THE EQUITY CURVE — month-end value against the previous month-end. This is the actual
 *      monthly return, needs no position sizes, and the page already fetches it. It is the right
 *      answer for a chart titled "monthly return".
 *
 *   2. SUM OF R — when no curve is available. R is a normalised risk unit: the book sizes every
 *      position to the same risk, so R adds across trades in a way percentages do not, and the
 *      whole programme already reasons in it. It is NOT a percentage and is labelled "R" so it
 *      cannot be read as one.
 *
 * The old TODO asked for "a monthly P&L endpoint or position-size on trades". Neither is needed;
 * the data was already on the page.
 */

/** A finite, usable number — or null.
 *
 * `Number(null)` is 0 and `Number('')` is 0, both of which pass `Number.isFinite`. A null equity
 * point was therefore stored as zero and rendered a −100% month; a null `r_multiple` counted as a
 * flat trade. Absent is not zero, and this is the guard that says so. Caught by its own test.
 */
function num(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Month key 'YYYY-MM' from a bare date string, or null. */
function monthOf(dateStr) {
  const m = /^(\d{4})-(\d{2})/.exec(String(dateStr || ''));
  return m ? `${m[1]}-${m[2]}` : null;
}

const SHORT_MONTH = (key) => {
  const [y, m] = key.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleString('en-IN', { month: 'short' });
};

/**
 * Monthly % return from an equity curve `[{date, value}]`.
 *
 * Uses each month's LAST point against the previous month's last point, so a month is measured
 * close-to-close rather than from whatever day the series happens to start on. The first month
 * has no predecessor and is therefore omitted — inventing a baseline for it would manufacture a
 * return out of the series' start date.
 */
export function monthlyReturnsFromCurve(history = [], { limit = 12 } = {}) {
  const lastOfMonth = new Map();
  for (const p of history) {
    const key = monthOf(p?.date);
    const value = num(p?.value);
    // A NAV of zero or less is not a data point, it is a broken one — and dividing by it below
    // would emit a −100% month out of a gap in the series.
    if (!key || value === null || value <= 0) continue;
    lastOfMonth.set(key, value);          // insertion order follows the series; later wins
  }
  const keys = [...lastOfMonth.keys()].sort();
  const out = [];
  for (let i = 1; i < keys.length; i += 1) {
    const prev = lastOfMonth.get(keys[i - 1]);
    const cur = lastOfMonth.get(keys[i]);
    if (!(prev > 0)) continue;
    out.push({ key: keys[i], label: SHORT_MONTH(keys[i]), value: ((cur / prev) - 1) * 100 });
  }
  return out.slice(-limit);
}

/**
 * Monthly sum of R from closed trades, bucketed by exit month.
 *
 * Summing R is legitimate where summing percent is not: every position is sized to the same unit
 * of risk, so one trade at +2R and one at −1R genuinely leaves the month +1R. Trades without an
 * `r_multiple` are skipped rather than counted as zero — a missing measurement is not a flat one.
 */
export function monthlyRFromTrades(trades = [], { limit = 12 } = {}) {
  const byMonth = new Map();
  for (const t of trades) {
    const key = monthOf(t?.exit_date || t?.close_date || t?.entry_date);
    const r = num(t?.r_multiple);
    if (!key || r === null) continue;
    const cur = byMonth.get(key) || { key, value: 0, count: 0 };
    cur.value += r;
    cur.count += 1;
    byMonth.set(key, cur);
  }
  return [...byMonth.values()]
    .sort((a, b) => a.key.localeCompare(b.key))
    .slice(-limit)
    .map((m) => ({ ...m, label: SHORT_MONTH(m.key) }));
}

/**
 * The series to chart, plus what it IS — so the caption can never claim more than the number does.
 * `unit` is 'pct' or 'R'; callers must render it, not assume percent.
 */
export function monthlySeries({ history = [], trades = [], limit = 12 } = {}) {
  const curve = monthlyReturnsFromCurve(history, { limit });
  if (curve.length) {
    return { data: curve, unit: 'pct', source: 'equity curve, month-end to month-end' };
  }
  const r = monthlyRFromTrades(trades, { limit });
  if (r.length) {
    return { data: r, unit: 'R', source: 'sum of R on closed trades — not a percentage' };
  }
  return { data: [], unit: 'pct', source: null };
}
