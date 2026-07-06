/**
 * useUserWatchlist — the per-user saved-stocks lists behind the left rail.
 *
 * Each user has two independent lists (list 1 = seeded core, list 2 = blank).
 * Every hook takes a `listNo` (default 1) and is cached under a per-list key so
 * the two tabs never clobber each other.
 *
 * Backing endpoints: GET/POST /api/watchlist?list=N,
 * DELETE /api/watchlist/{ticker}?list=N, PATCH /api/watchlist/reorder.
 * Returns membership only; live prices come from useQuoteBatch (shared feed).
 *
 * NOT to be confused with useWatchlist (the model's signal-tier watchlist).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { getWatchlist, addToWatchlist, removeFromWatchlist, reorderWatchlist } from '@/services/api';

export const userWatchlistKey = (listNo = 1) => ['user', 'watchlist', listNo];
// Back-compat alias for any code that referenced the flat key.
export const USER_WATCHLIST_KEY = ['user', 'watchlist'];

export function useUserWatchlist(listNo = 1, options = {}) {
  return useQuery({
    queryKey: userWatchlistKey(listNo),
    queryFn: () => getWatchlist(listNo),
    select: (data) => (Array.isArray(data?.watchlist) ? data.watchlist : []),
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    ...options,
  });
}

/** Optimistically add `ticker` to `listNo`, rolling back on error. */
export function useAddToWatchlist(listNo = 1) {
  const qc = useQueryClient();
  const key = userWatchlistKey(listNo);
  return useMutation({
    mutationFn: (ticker) => addToWatchlist(ticker, listNo),
    onMutate: async (ticker) => {
      const sym = String(ticker || '').toUpperCase();
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData(key);
      qc.setQueryData(key, (old) => {
        const list = old?.watchlist ?? [];
        return list.includes(sym) ? old : { watchlist: [...list, sym] };
      });
      return { prev };
    },
    onError: (err, ticker, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(key, ctx.prev);
      toast.error('Could not add to watchlist', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  });
}

/** Optimistically remove `ticker` from `listNo`, rolling back on error. */
export function useRemoveFromWatchlist(listNo = 1) {
  const qc = useQueryClient();
  const key = userWatchlistKey(listNo);
  return useMutation({
    mutationFn: (ticker) => removeFromWatchlist(ticker, listNo),
    onMutate: async (ticker) => {
      const sym = String(ticker || '').toUpperCase();
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData(key);
      qc.setQueryData(key, (old) => {
        const list = old?.watchlist ?? [];
        return { watchlist: list.filter((t) => t !== sym) };
      });
      return { prev };
    },
    onError: (err, ticker, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(key, ctx.prev);
      toast.error('Could not remove from watchlist', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  });
}

/** Persist a new order for `listNo`; optimistically applies it immediately. */
export function useReorderWatchlist(listNo = 1) {
  const qc = useQueryClient();
  const key = userWatchlistKey(listNo);
  return useMutation({
    mutationFn: (order) => reorderWatchlist(order, listNo),
    onMutate: async (order) => {
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData(key);
      qc.setQueryData(key, { watchlist: order });
      return { prev };
    },
    onError: (err, order, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(key, ctx.prev);
      toast.error('Could not reorder watchlist', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  });
}

export default useUserWatchlist;
