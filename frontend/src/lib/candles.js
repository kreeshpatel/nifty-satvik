/**
 * Normalize a candle into { date, open, high, low, value (close), volume }.
 *
 * useStockData / yahooHistorical / kiteHistorical can each emit two shapes:
 *   Kite array:  [timestamp, open, high, low, close, volume]
 *   Yahoo obj:   { date, open, high, low, close, volume }
 *
 * `value` mirrors `close` so legacy area-chart consumers that read `value`
 * keep working.
 */
export function normCandle(c) {
  if (!c) return null;
  if (Array.isArray(c)) {
    return {
      date:   c[0],
      open:   Number(c[1]) || 0,
      high:   Number(c[2]) || 0,
      low:    Number(c[3]) || 0,
      value:  Number(c[4]) || 0,
      volume: Number(c[5]) || 0,
    };
  }
  return {
    date:   c.date || c.timestamp || c[0],
    open:   Number(c.open  ?? c[1]) || 0,
    high:   Number(c.high  ?? c[2]) || 0,
    low:    Number(c.low   ?? c[3]) || 0,
    value:  Number(c.close ?? c.last_price ?? c.value ?? c[4]) || 0,
    volume: Number(c.volume ?? c[5]) || 0,
  };
}

/**
 * Convert a normalized candle's `date` into a lightweight-charts time value.
 * Daily / weekly bars want a 'YYYY-MM-DD' string; intraday wants unix seconds.
 *
 * Inputs we tolerate:
 *   - ISO string: '2026-04-29T09:15:00+05:30'
 *   - Date string: '2026-04-29'
 *   - Unix seconds (number): 1714377900
 *   - Unix millis (number > 1e12): 1714377900000
 *   - Date object
 */
export function toLwcTime(date, intraday) {
  if (date == null) return null;
  let ms;
  if (date instanceof Date) {
    ms = date.getTime();
  } else if (typeof date === 'number') {
    ms = date > 1e12 ? date : date * 1000;
  } else {
    const parsed = Date.parse(date);
    if (Number.isNaN(parsed)) {
      // Already a 'YYYY-MM-DD' that Date.parse couldn't grok? Pass through.
      return intraday ? null : String(date).slice(0, 10);
    }
    ms = parsed;
  }
  if (intraday) return Math.floor(ms / 1000);
  return new Date(ms).toISOString().slice(0, 10);
}

/**
 * Infer whether a candle series is intraday (sub-daily bars) by inspecting
 * timestamps. Looks at the first ~10 consecutive deltas and asks whether the
 * median is under 23 hours. Returns false on too-few-candles fallback.
 *
 * Why infer instead of accepting an `intraday` prop from the caller:
 * useStockData's PERIOD_MAP returns DIFFERENT intervals for the same period
 * label depending on whether Kite or Yahoo answered. e.g. period='1M' is
 * hourly bars via Yahoo but daily bars via Kite. Pinning intraday to a
 * period-name allowlist drops 23 of 24 hourly bars per day on the Yahoo
 * path because non-intraday formatting collapses the time key to 'YYYY-MM-DD'
 * and toLwcSeries de-dupes by it.
 */
export function inferIntraday(candles) {
  if (!Array.isArray(candles) || candles.length < 2) return false;
  const ms = [];
  const stop = Math.min(candles.length - 1, 10);
  for (let i = 1; i <= stop; i += 1) {
    const a = _toMs(candles[i - 1]?.date);
    const b = _toMs(candles[i]?.date);
    if (a != null && b != null && b > a) ms.push(b - a);
  }
  if (ms.length === 0) return false;
  ms.sort((x, y) => x - y);
  const median = ms[Math.floor(ms.length / 2)];
  // 23h threshold catches daily bars even with weekend gaps showing up
  // earlier in the array; weekends are a single 72h delta which won't be
  // the median.
  return median < 23 * 60 * 60 * 1000;
}

function _toMs(date) {
  if (date == null) return null;
  if (date instanceof Date) return date.getTime();
  if (typeof date === 'number') return date > 1e12 ? date : date * 1000;
  const parsed = Date.parse(date);
  return Number.isNaN(parsed) ? null : parsed;
}

/**
 * Convert an array of normalized candles into lightweight-charts series data.
 * Returns { ohlc: [{time,open,high,low,close}], area: [{time,value}], volume: [{time,value,color}] }
 * with rows sorted ascending and de-duplicated by `time` (lwc throws on dupes).
 */
export function toLwcSeries(candles, { intraday = false, bullColor, bearColor } = {}) {
  const ohlc = [];
  const area = [];
  const volume = [];
  const seen = new Set();

  const sorted = candles
    .map((c) => {
      const time = toLwcTime(c.date, intraday);
      if (time == null) return null;
      return { ...c, time };
    })
    .filter(Boolean)
    .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));

  for (const c of sorted) {
    const key = String(c.time);
    if (seen.has(key)) continue;
    seen.add(key);
    ohlc.push({
      time: c.time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.value,
    });
    area.push({ time: c.time, value: c.value });
    if (c.volume > 0) {
      volume.push({
        time: c.time,
        value: c.volume,
        color: c.value >= c.open ? bullColor : bearColor,
      });
    }
  }

  return { ohlc, area, volume };
}
