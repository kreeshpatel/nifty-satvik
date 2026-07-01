/**
 * usePaperPositions — paper-portfolio positions fallback for Kite-off users.
 *
 * Backing endpoint: GET /api/positions
 *   Returns [{ ticker, entry_date, entry_price, shares, position_size, atr_stop,
 *              ml_score, current_price, current_value, unrealised_pnl,
 *              unrealised_pnl_pct, hold_days, sector, regime_at_entry, stop_distance_pct }]
 *
 * Used by the Portfolio page when `!kite?.connected` — surfaces what the
 * backend's paper-trading engine thinks the user's positions are. Not
 * billed as "live trading" anywhere in the UI; a banner on the page tells
 * the user to connect Kite for real holdings.
 *
 * Cache: 30s stale — paper portfolio snapshot updates whenever the user's
 * session or the cron runs. 30s is a good compromise between freshness
 * and chatter.
 */
import { useQuery } from '@tanstack/react-query';
import { fetchPositions } from '@/services/api';

export const POSITIONS_QUERY_KEY = ['positions'];

export function usePaperPositions(options = {}) {
  return useQuery({
    queryKey: POSITIONS_QUERY_KEY,
    queryFn: fetchPositions,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    select: (raw) => (Array.isArray(raw) ? raw : raw?.data ?? []),
    ...options,
  });
}

export default usePaperPositions;
