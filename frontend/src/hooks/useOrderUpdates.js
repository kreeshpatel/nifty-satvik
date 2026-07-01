/**
 * useOrderUpdates — subscribe to backend `order_update` WS frames and
 * invalidate every order-shaped TanStack query so the UI reflects fills,
 * rejects, and cancels without waiting for stale-time polling.
 *
 * Backend ws_manager.broadcast_order_update fires on every Kite order_update
 * (PENDING → OPEN → COMPLETE | REJECTED | CANCELLED). The DB row is patched
 * before the WS frame is sent, so a refetch triggered from this hook reads
 * the post-patch state.
 *
 * Mount once at the layout level (ProtectedAppLayout) — useWebSocket uses a
 * module-level singleton socket, so multiple mount sites would clobber it.
 */
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';
import { useWebSocket } from './useWebSocket';
import { KITE_ORDERS_KEY } from './queries/useKiteOrders';
import { KITE_HOLDINGS_KEY, KITE_MARGINS_KEY } from './queries/useKiteState';
import { NQ_ORDERS_KEY } from './useOrderPlacement';
import { NQ_STATS_KEY } from './queries/useNQOrders';

export function useOrderUpdates() {
  const qc = useQueryClient();

  const onOrderUpdate = useCallback(() => {
    qc.invalidateQueries({ queryKey: KITE_ORDERS_KEY });
    qc.invalidateQueries({ queryKey: KITE_HOLDINGS_KEY });
    qc.invalidateQueries({ queryKey: KITE_MARGINS_KEY });
    qc.invalidateQueries({ queryKey: NQ_ORDERS_KEY });
    qc.invalidateQueries({ queryKey: NQ_STATS_KEY });
  }, [qc]);

  const callbacks = useMemo(() => ({ onOrderUpdate }), [onOrderUpdate]);
  useWebSocket(callbacks);
}

export default useOrderUpdates;
