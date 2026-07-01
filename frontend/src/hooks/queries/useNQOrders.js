/**
 * useNQOrders — list of NiftyQuant-executed orders for the current user.
 *
 * Backing endpoint: GET /api/nq-orders[?year=&month=&ticker=&status=]
 *   Returns { orders: [...], count }
 *
 * Used by both Journal (filter status=COMPLETE) and Accounting (filter by
 * year/month). Cache is short — 60s — because the WS order_update path
 * patches rows in the DB, and we want fresh state on tab focus.
 *
 * useNQOrderStats — aggregate stats per period (FY/YTD/30d/all).
 * Backing endpoint: GET /api/nq-orders/stats?period=fy
 *   Returns { period, realised_pnl, unrealised_pnl, total_brokerage,
 *             total_stt, net_pnl, stcg_pnl, ltcg_pnl, trades_matched,
 *             open_positions }
 *
 * useUpdateNQOrderNotes — mutation to persist Journal rationale.
 *   PATCH /api/nq-orders/:id/notes  { notes }
 *
 * After a successful update we invalidate the orders list so any open
 * Journal entry card sees the new note.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { listNQOrders, fetchNQOrderStats, updateNQOrderNotes } from '@/services/api';

export const NQ_ORDERS_KEY = ['nq-orders'];
export const NQ_STATS_KEY = ['nq-orders', 'stats'];

export function useNQOrders(params = {}, options = {}) {
  const key = [...NQ_ORDERS_KEY, params];
  return useQuery({
    queryKey: key,
    queryFn: () => listNQOrders(params),
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    select: (raw) => raw?.orders ?? [],
    ...options,
  });
}

export function useNQOrderStats(period = 'fy', options = {}) {
  return useQuery({
    queryKey: [...NQ_STATS_KEY, period],
    queryFn: () => fetchNQOrderStats(period),
    staleTime: 5 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    ...options,
  });
}

export function useUpdateNQOrderNotes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }) => updateNQOrderNotes(id, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: NQ_ORDERS_KEY });
    },
  });
}

export default useNQOrders;
