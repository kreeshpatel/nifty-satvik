/**
 * useKiteOrders — today's Kite order book.
 *
 * Backing endpoint: GET /api/kite/orders
 *   Returns [{ order_id, tradingsymbol, transaction_type, quantity, filled_quantity,
 *              price, status, order_type, product, ... }]
 *
 * Cache: 30s stale. The Orders table on Portfolio is live-patched via
 * WS order_update events (see useLiveTicks), so polling is only a fallback
 * for users without WS connectivity.
 *
 * Gated on `enabled: kiteConnected` to skip the request when Kite is off —
 * otherwise we'd burn polls returning 401 every 30s.
 */
import { useQuery } from '@tanstack/react-query';
import { kiteOrders } from '@/services/api';

export const KITE_ORDERS_KEY = ['kite', 'orders'];

export function useKiteOrders({ enabled = true } = {}) {
  return useQuery({
    queryKey: KITE_ORDERS_KEY,
    queryFn: kiteOrders,
    enabled,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    select: (raw) => {
      const list = Array.isArray(raw) ? raw : raw?.data ?? [];
      // Backend returns today's orders unsorted. Render newest first so the
      // most-recently-placed order (the one the user just submitted via
      // OrderPad) appears at the top.
      return [...list].sort((a, b) => {
        const at = a.order_timestamp || a.exchange_timestamp || '';
        const bt = b.order_timestamp || b.exchange_timestamp || '';
        return bt.localeCompare(at);
      });
    },
  });
}

export default useKiteOrders;
