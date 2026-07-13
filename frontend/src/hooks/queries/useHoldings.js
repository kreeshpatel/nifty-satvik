/**
 * useHoldings — the per-user EPHEMERAL "I bought this" marks on the Signals page.
 *
 * The user manually marks a recommendation bought; the mark lives only while the
 * trade is open and is erased server-side once the model completes it. This hook
 * exposes the still-open holdings (and a convenience Set of held signal_ids) plus
 * optimistic mark/unmark mutations.
 *
 * Backing endpoints: GET/POST /api/holdings, DELETE /api/holdings/{signal_id}.
 * signal_id = "{TICKER}__{YYYY-MM-DD}" (the shared canonical key).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { fetchHoldings, markBought, unmarkBought } from '@/services/api';

export const HOLDINGS_KEY = ['user', 'holdings'];

/** The user's open holdings → array of { signal_id, ticker, entry, stop, qty, ... }. */
export function useHoldings(options = {}) {
  return useQuery({
    queryKey: HOLDINGS_KEY,
    queryFn: fetchHoldings,
    select: (data) => (Array.isArray(data?.holdings) ? data.holdings : []),
    staleTime: 30 * 1000,
    gcTime: 10 * 60 * 1000,
    ...options,
  });
}

/** Mark a signal bought. Optimistically inserts the row, rolling back on error. */
export function useMarkBought() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => markBought(payload),
    onMutate: async (payload) => {
      await qc.cancelQueries({ queryKey: HOLDINGS_KEY });
      const prev = qc.getQueryData(HOLDINGS_KEY);
      qc.setQueryData(HOLDINGS_KEY, (old) => {
        const list = old?.holdings ?? [];
        if (list.some((h) => h.signal_id === payload.signal_id)) {
          return { holdings: list.map((h) => (h.signal_id === payload.signal_id ? { ...h, ...payload } : h)) };
        }
        return { holdings: [{ ...payload }, ...list] };
      });
      return { prev };
    },
    onError: (err, _payload, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(HOLDINGS_KEY, ctx.prev);
      toast.error('Could not mark bought', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: HOLDINGS_KEY }),
  });
}

/** Unmark a signal (sold early / fat-finger). Optimistically removes it. */
export function useUnmarkBought() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (signalId) => unmarkBought(signalId),
    onMutate: async (signalId) => {
      await qc.cancelQueries({ queryKey: HOLDINGS_KEY });
      const prev = qc.getQueryData(HOLDINGS_KEY);
      qc.setQueryData(HOLDINGS_KEY, (old) => ({
        holdings: (old?.holdings ?? []).filter((h) => h.signal_id !== signalId),
      }));
      return { prev };
    },
    onError: (err, _signalId, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(HOLDINGS_KEY, ctx.prev);
      toast.error('Could not unmark', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: HOLDINGS_KEY }),
  });
}

export default useHoldings;
