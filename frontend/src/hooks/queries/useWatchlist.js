/**
 * useWatchlist — react-query hook for borderline signal candidates.
 *
 * Backing endpoint: GET /api/signals/watchlist
 *
 * Reads from `results/signals_watchlist.json` on the backend (or GitHub
 * raw fallback). These are signals the model surfaced today with
 * confidence in the 0.75-0.92 band — promising but below the entry gate.
 * They're not buyable, just monitored.
 *
 * Cache policy mirrors useSignals: 5min staleTime, 30min gcTime,
 * 5min refetch interval. The watchlist file is regenerated once per
 * day by the 4:15 PM IST cron, so there's no value in tighter cadence.
 *
 * Each signal arrives with actionability='WATCHLIST' stamped by the
 * backend so the SignalsV2 tier rendering can treat it uniformly with
 * the other actionability values without confidence-range checks
 * client-side.
 */
import { useQuery } from '@tanstack/react-query';
import { fetchWatchlist } from '@/services/api';

export const WATCHLIST_QUERY_KEY = ['signals', 'watchlist'];

export function useWatchlist({ model = 'bhanushali', ...options } = {}) {
  return useQuery({
    queryKey: [...WATCHLIST_QUERY_KEY, model],
    queryFn: () => fetchWatchlist(model),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    refetchIntervalInBackground: false,
    select: (raw) => ({
      signals: Array.isArray(raw?.signals) ? raw.signals : [],
      count: raw?.count ?? 0,
      generatedAt: raw?.generated_at,
    }),
    ...options,
  });
}

export default useWatchlist;
