/**
 * useNQPositions — react-query hook for the user's NQ-tracked positions.
 *
 * Backing endpoint: GET /api/positions/nq
 *
 * Each entry is a signal the user has actually bought via NQ's Buy/Sell
 * UI, joined with:
 *   - signal context (entry/stop/target/days_since/days_left/status)
 *   - Kite live truth (last_price, kite_qty_for_ticker for drift detection)
 *   - per-(user, signal) state (status_for_user, sell_guidance)
 *
 * Used by PortfolioV2's "Nifty Satvik Positions" section and SignalsV2's
 * "Held — Sell Guidance" tier. Both pages can consume the same query —
 * react-query dedupes the request when the staleTime hasn't elapsed.
 *
 * Cache policy: 30s stale, 5min gcTime. Matches the cadence of
 * useKiteHoldings since this hook joins live Kite data on the backend
 * and a stale price would be visually disorienting (P&L numbers move
 * if you blink).
 *
 * Invalidation triggers (consumers should call queryClient.invalidateQueries):
 *   - useOrderPlacement on order success
 *   - WebSocket order_update fired by ws_manager.broadcast_order_update
 *   - manual refresh from the Portfolio page
 */
import { useQuery } from '@tanstack/react-query';
import { fetchNQPositions } from '@/services/api';

export const NQ_POSITIONS_KEY = ['positions', 'nq'];

export function useNQPositions(options = {}) {
  return useQuery({
    queryKey: NQ_POSITIONS_KEY,
    queryFn: fetchNQPositions,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    select: (raw) => ({
      positions: Array.isArray(raw?.positions) ? raw.positions : [],
      count: raw?.count ?? 0,
      kiteConnected: !!raw?.kite_connected,
      updatedAt: raw?.updated_at,
    }),
    ...options,
  });
}

export default useNQPositions;
