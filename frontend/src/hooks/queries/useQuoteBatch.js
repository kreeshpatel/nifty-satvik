/**
 * useQuoteBatch — batch DAILY-CLOSE quotes for watchlists, holdings, signals.
 *
 * Backing endpoint: GET /api/yahoo/quote-batch?symbols=RELIANCE,INFY,...
 *   Returns { RELIANCE: { last_price, previous_close, change, change_pct, as_of }, ... }
 *
 * `last_price` is the last COMPLETED NSE daily close (not live). The server
 * caches it until the next 16:00 IST settle, so this hook fetches once and
 * never polls — polling only kept the Fly machine awake (2026-11-02).
 *
 * Gated on `enabled` so pages that don't need prices don't fire it.
 */
import { useQuery } from '@tanstack/react-query';
import { yahooQuoteBatch } from '@/services/api';

export function useQuoteBatch(symbols, { enabled = true, refetchInterval = false } = {}) {
  const list = (symbols ?? []).filter(Boolean).sort(); // stable cache key
  return useQuery({
    queryKey: ['yahoo', 'quote-batch', list.join(',')],
    queryFn: () => yahooQuoteBatch(list),
    enabled: enabled && list.length > 0,
    staleTime: 60 * 60 * 1000,
    gcTime: 2 * 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchInterval,
    refetchIntervalInBackground: false,
  });
}

export default useQuoteBatch;
