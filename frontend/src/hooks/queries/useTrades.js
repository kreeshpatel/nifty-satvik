/**
 * useTrades — infinite-query paginated trade history.
 *
 * Backing endpoint: GET /api/trades?page=1&per_page=50[&ticker=&start=&end=&exit_reason=]
 *   Returns { trades: [...], total, page, pages }
 *
 * Also exports useTradeStats which wraps /api/trades/stats for the Analytics
 * page (aggregate win rate, sector breakdown, 30d accuracy trend). That
 * endpoint is server-cached ~10min so we use a matching 5min staleTime.
 */
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { fetchTrades, fetchTradeStats } from '@/services/api';

export const TRADES_QUERY_KEY = ['trades'];
export const TRADE_STATS_QUERY_KEY = ['trades', 'stats'];

export function useTrades({ perPage = 50, ticker, start, end, exitReason } = {}) {
  const key = [...TRADES_QUERY_KEY, { perPage, ticker, start, end, exitReason }];
  return useInfiniteQuery({
    queryKey: key,
    queryFn: ({ pageParam = 1 }) =>
      fetchTrades({
        page: pageParam,
        per_page: perPage,
        ticker: ticker || undefined,
        start: start || undefined,
        end: end || undefined,
        exit_reason: exitReason || undefined,
      }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (!lastPage) return undefined;
      if (lastPage.page < lastPage.pages) return lastPage.page + 1;
      return undefined;
    },
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

export function useTradeStats(options = {}) {
  return useQuery({
    queryKey: TRADE_STATS_QUERY_KEY,
    queryFn: fetchTradeStats,
    staleTime: 5 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    ...options,
  });
}

/**
 * Helper: flatten an infinite-query result into a single trades array.
 * Works with the shape returned by /api/trades.
 */
export function flattenTrades(infiniteData) {
  if (!infiniteData?.pages) return [];
  return infiniteData.pages.flatMap((p) => p?.trades ?? []);
}

export default useTrades;
