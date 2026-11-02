/**
 * useKiteQuote — live full quote for a single instrument.
 *
 * Backing endpoint: GET /api/kite/quote?instruments=NSE:RELIANCE
 * Returns Kite's full quote shape:
 *   {
 *     "NSE:RELIANCE": {
 *       last_price, ohlc: { open, high, low, close },
 *       volume, average_price, oi, oi_day_high, oi_day_low,
 *       depth: {
 *         buy:  [{ price, quantity, orders }, ...top 5],
 *         sell: [{ price, quantity, orders }, ...top 5]
 *       },
 *       net_change, last_quantity, last_trade_time, change_pct, ...
 *     }
 *   }
 *
 * Uses owner's Kite session (paid Market Data) on the backend, so it works
 * for every user regardless of whether they've connected their personal Kite.
 *
 * One snapshot per mount — NO polling (2026-11-02). Live quotes were removed
 * to let the Fly machine suspend; depth is a point-in-time snapshot only.
 */
import { useQuery } from '@tanstack/react-query';
import { kiteQuote } from '@/services/api';

/**
 * @param symbol — short ticker like 'RELIANCE'. Will be prefixed with NSE:
 * @param exchange — defaults to 'NSE'. Pass 'BSE' for Sensex names.
 * @param refetchInterval — defaults to false (no polling).
 */
export function useKiteQuote(symbol, { exchange = 'NSE', refetchInterval = false, enabled = true } = {}) {
  const instrument = symbol ? `${exchange}:${String(symbol).toUpperCase()}` : null;
  return useQuery({
    queryKey: ['kite', 'quote', instrument],
    queryFn: () => kiteQuote([instrument]),
    enabled: enabled && !!instrument,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    gcTime: 5 * 60 * 1000,
    refetchInterval,
    refetchIntervalInBackground: false,
    select: (raw) => {
      // Backend proxies Kite's response shape: keyed by `<exchange>:<symbol>`.
      if (!raw || typeof raw !== 'object') return null;
      // Kite wraps in { data: {...} } sometimes; normalise.
      const inner = raw.data ?? raw;
      const row = inner?.[instrument];
      return row || null;
    },
  });
}

export default useKiteQuote;
