/**
 * useIndexSparklines — intraday sparklines for NIFTY 50 / BANK NIFTY / VIX / etc.
 *
 * Backing endpoint: GET /api/yahoo/index-sparklines (public, no auth)
 *   Returns {
 *     NIFTY:     { last: number, changePct: number, series: [{ t, v }] },
 *     BANKNIFTY: { ... },
 *     INDIAVIX:  { ... },
 *     USDINR:    { ... },
 *     ...
 *   }
 *
 * Cache: 60s stale, only refetch while page is visible. During market hours
 * this gives a lively-enough dashboard; off-hours the request settles and
 * the cache takes over.
 */
import { useQuery } from '@tanstack/react-query';
import { yahooIndexSparklines } from '@/services/api';

export const INDEX_SPARKLINES_KEY = ['yahoo', 'index-sparklines'];

export function useIndexSparklines(options = {}) {
  return useQuery({
    queryKey: INDEX_SPARKLINES_KEY,
    queryFn: yahooIndexSparklines,
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchIntervalInBackground: false,
    ...options,
  });
}

export default useIndexSparklines;
