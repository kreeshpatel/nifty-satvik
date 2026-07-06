/**
 * useUserWatchlist — the per-user saved-stocks list behind the left rail.
 *
 * Backing endpoints: GET/POST /api/watchlist, DELETE /api/watchlist/{ticker}.
 * Returns membership only; live prices come from useQuoteBatch (shared feed).
 *
 * NOT to be confused with useWatchlist (the model's signal-tier watchlist).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { getWatchlist, addToWatchlist, removeFromWatchlist, reorderWatchlist } from '@/services/api';

export const USER_WATCHLIST_KEY = ['user', 'watchlist'];

export function useUserWatchlist(options = {}) {
  return useQuery({
    queryKey: USER_WATCHLIST_KEY,
    queryFn: getWatchlist,
    select: (data) => (Array.isArray(data?.watchlist) ? data.watchlist : []),
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    ...options,
  });
}

/** Optimistically add `ticker`, rolling back on error. */
export function useAddToWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ticker) => addToWatchlist(ticker),
    onMutate: async (ticker) => {
      const sym = String(ticker || '').toUpperCase();
      await qc.cancelQueries({ queryKey: USER_WATCHLIST_KEY });
      const prev = qc.getQueryData(USER_WATCHLIST_KEY);
      qc.setQueryData(USER_WATCHLIST_KEY, (old) => {
        const list = old?.watchlist ?? [];
        return list.includes(sym) ? old : { watchlist: [...list, sym] };
      });
      return { prev };
    },
    onError: (err, ticker, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(USER_WATCHLIST_KEY, ctx.prev);
      toast.error('Could not add to watchlist', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: USER_WATCHLIST_KEY }),
  });
}

/** Optimistically remove `ticker`, rolling back on error. */
export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ticker) => removeFromWatchlist(ticker),
    onMutate: async (ticker) => {
      const sym = String(ticker || '').toUpperCase();
      await qc.cancelQueries({ queryKey: USER_WATCHLIST_KEY });
      const prev = qc.getQueryData(USER_WATCHLIST_KEY);
      qc.setQueryData(USER_WATCHLIST_KEY, (old) => {
        const list = old?.watchlist ?? [];
        return { watchlist: list.filter((t) => t !== sym) };
      });
      return { prev };
    },
    onError: (err, ticker, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(USER_WATCHLIST_KEY, ctx.prev);
      toast.error('Could not remove from watchlist', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: USER_WATCHLIST_KEY }),
  });
}

/** Persist a new order; optimistically applies it immediately. */
export function useReorderWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (order) => reorderWatchlist(order),
    onMutate: async (order) => {
      await qc.cancelQueries({ queryKey: USER_WATCHLIST_KEY });
      const prev = qc.getQueryData(USER_WATCHLIST_KEY);
      qc.setQueryData(USER_WATCHLIST_KEY, { watchlist: order });
      return { prev };
    },
    onError: (err, order, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(USER_WATCHLIST_KEY, ctx.prev);
      toast.error('Could not reorder watchlist', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: USER_WATCHLIST_KEY }),
  });
}

export default useUserWatchlist;
