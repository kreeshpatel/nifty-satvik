/**
 * Publish schedule — when the backend's data actually changes (docs/DESIGN_BRIEF_V5.md §12).
 * Source of truth: .github/workflows cron lines (all IST; IST has no DST, IST = UTC+5:30).
 *   weekdays 16:15 IST  bhanushali monitor (daily re-price)
 *   weekdays 16:30 IST  post-close scan
 *   Saturday 18:00 IST  weekly recompute
 * Queries use this to refetch just after a publish instead of polling all day — polling kept
 * the scale-to-zero Fly machine awake (cost).
 */
const IST_MS = 330 * 60 * 1000;

// [dayOfWeek (0=Sun, IST), hour, minute] — IST
const SLOTS = [
  ...[1, 2, 3, 4, 5].flatMap((d) => [[d, 16, 15], [d, 16, 30]]),
  [6, 18, 0],
];

/** The next publish time after `now`, as a Date. */
export function nextPublish(now = new Date()) {
  const ist = new Date(now.getTime() + IST_MS);            // shifted clock: read with getUTC*
  let best = null;
  for (let add = 0; add <= 7; add += 1) {
    const day = new Date(Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate() + add));
    for (const [dow, h, m] of SLOTS) {
      if (day.getUTCDay() !== dow) continue;
      const t = Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate(), h, m) - IST_MS;
      if (t > now.getTime() && (best == null || t < best)) best = t;
    }
    if (best != null) break;
  }
  return new Date(best);
}

/** NSE cash session, Mon–Fri 09:15–15:30 IST (exchange holidays not modelled). */
export function isMarketOpen(now = new Date()) {
  const ist = new Date(now.getTime() + IST_MS);
  const dow = ist.getUTCDay();
  const mins = ist.getUTCHours() * 60 + ist.getUTCMinutes();
  return dow >= 1 && dow <= 5 && mins >= 9 * 60 + 15 && mins <= 15 * 60 + 30;
}

/**
 * refetchInterval for publish-driven data: wake ~2 min after the next publish (jobs take a
 * moment to land), never sooner than 1 min, never later than 6 h (a safety net).
 */
export function untilNextPublish(now = new Date()) {
  const ms = nextPublish(now).getTime() - now.getTime() + 2 * 60 * 1000;
  return Math.min(Math.max(ms, 60 * 1000), 6 * 60 * 60 * 1000);
}

export const fmtIST = (d, opts = {}) => new Date(d).toLocaleString('en-IN', {
  timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false, ...opts,
});
