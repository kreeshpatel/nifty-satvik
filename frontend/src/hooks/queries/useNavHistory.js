/**
 * useNavHistory — react-query hook for the user's daily NAV series.
 *
 * Backing endpoint: GET /api/portfolio/nav-history
 *
 * Rows are auto-written by /api/positions/nq (dashboard loads). No
 * backfill exists — series starts whenever the snapshot service
 * shipped + the user first opened the dashboard with Kite connected.
 *
 * The chart degrades gracefully on partial data — PortfolioV2 +
 * DashboardV2 both check `count` and render a "less than a week of
 * history yet" hint when the series is too short for a meaningful
 * curve.
 *
 * Cache: 60s stale, 5min gc. NAV doesn't move per-second on the
 * server (snapshots are throttled to 1/day per user), so a tighter
 * stale time would just churn the cache.
 */
import { useQuery } from '@tanstack/react-query';
import { fetchNavHistory } from '@/services/api';

export const NAV_HISTORY_KEY = ['portfolio', 'nav-history'];

export function useNavHistory({ days = 365, ...options } = {}) {
  return useQuery({
    queryKey: [...NAV_HISTORY_KEY, days],
    queryFn: () => fetchNavHistory(days),
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    select: (raw) => ({
      history: Array.isArray(raw?.history) ? raw.history : [],
      count: raw?.count ?? 0,
      firstDate: raw?.first_date ?? null,
      lastDate: raw?.last_date ?? null,
    }),
    ...options,
  });
}

export default useNavHistory;
