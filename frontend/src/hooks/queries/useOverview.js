/**
 * useOverview — portfolio summary + equity curve + aggregate metrics.
 *
 * Backing endpoint: GET /api/overview
 *   Returns {
 *     portfolio: { total_value, cash, invested, total_return_pct, drawdown_pct, peak_value, n_positions },
 *     equity_curve: [{ date, value, regime }],
 *     metrics: { total_trades, win_rate, profit_factor, avg_win, avg_loss, avg_hold_days, sharpe_ratio }
 *   }
 *
 * This hook is hit from Dashboard + Portfolio + TrackRecord. react-query's
 * automatic deduplication means a single request serves all three — the
 * primary reason we adopted TanStack Query in Phase 0.
 *
 * Cache: 60s stale (per plan §6.1). Refetch on window focus — a returning
 * user sees fresh P&L the moment they tab back in.
 */
import { useQuery } from '@tanstack/react-query';
import { fetchOverview } from '@/services/api';

export const OVERVIEW_QUERY_KEY = ['overview'];

export function useOverview(options = {}) {
  return useQuery({
    queryKey: OVERVIEW_QUERY_KEY,
    queryFn: fetchOverview,
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: true,
    ...options,
  });
}

export default useOverview;
