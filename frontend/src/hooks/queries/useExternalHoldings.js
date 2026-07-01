/**
 * useExternalHoldings — Kite holdings minus NQ-attributed qty.
 *
 * Backing endpoint: GET /api/positions/external
 *
 * The strict-overlap rule (decided with the user during planning): if
 * Kite shows 150 of a ticker and NQ recorded 100, this hook returns the
 * remaining 50 as "external". It will never duplicate qty across the NQ
 * and external sections of the Portfolio.
 *
 * Returns: { holdings: [...], count, kiteConnected, updatedAt }
 * Each holding row carries the standard Kite shape (tradingsymbol,
 * average_price, last_price, etc.) PLUS an `nq_attributed_qty` field
 * for the UI tooltip ("100 of 150 are NQ-tracked → 50 shown here").
 */
import { useQuery } from '@tanstack/react-query';
import { fetchExternalHoldings } from '@/services/api';

export const EXTERNAL_HOLDINGS_KEY = ['positions', 'external'];

export function useExternalHoldings(options = {}) {
  return useQuery({
    queryKey: EXTERNAL_HOLDINGS_KEY,
    queryFn: fetchExternalHoldings,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    select: (raw) => ({
      holdings: Array.isArray(raw?.holdings) ? raw.holdings : [],
      count: raw?.count ?? 0,
      kiteConnected: !!raw?.kite_connected,
      updatedAt: raw?.updated_at,
    }),
    ...options,
  });
}

export default useExternalHoldings;
