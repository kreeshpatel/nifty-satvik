/**
 * useQuoteBatch — batch live quotes for TickerTape + HoldingsRow presence.
 *
 * Backing endpoint: GET /api/yahoo/quote-batch?symbols=RELIANCE,INFY,...
 *   Returns { RELIANCE: { last_price, change, change_pct }, ... }
 *
 * Public endpoint (no auth). Server caches 30s per symbol, so polling at
 * 60s here is the right rhythm — half the server cache window, never hits
 * Yahoo directly from the user's machine.
 *
 * Gated on `enabled` so TickerTape on landing can use this while also not
 * firing while the user is on a page that doesn't need ticker data.
 */
import { useQuery } from '@tanstack/react-query';
import { yahooQuoteBatch } from '@/services/api';

export function useQuoteBatch(symbols, { enabled = true, refetchInterval = 60 * 1000 } = {}) {
  const list = (symbols ?? []).filter(Boolean).sort(); // stable cache key
  return useQuery({
    queryKey: ['yahoo', 'quote-batch', list.join(',')],
    queryFn: () => yahooQuoteBatch(list),
    enabled: enabled && list.length > 0,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchInterval,
    refetchIntervalInBackground: false,
  });
}

export default useQuoteBatch;
