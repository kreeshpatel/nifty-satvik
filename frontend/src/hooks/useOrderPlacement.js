/**
 * useOrderPlacement — the end-to-end trading mutation for NiftyQuant.
 *
 * This hook encapsulates the flow the redesign plan §6.3 specifies:
 *
 *   User clicks PLACE ORDER on OrderPad
 *     → 1. POST /api/kite/orders/:variety  (places the order on Zerodha)
 *     → 2. POST /api/nq-orders             (tracks it in our DB for Accounting/Journal)
 *     → 3. Toast "Order placed: awaiting fill"
 *     → 4. WS order_update handler elsewhere flips status on fill/reject
 *
 * Returns:
 *   {
 *     placeOrder({ payload, signal, side, variety }) → Promise<result>
 *     isPending: boolean
 *     error: Error | null
 *     lastResult: { kite, nq } | null
 *   }
 *
 * The `payload` argument matches Kite's PlaceOrderRequest shape. `signal`
 * is the source signal (used for signal_id linkage). `side` is for toast
 * copy. `variety` defaults to 'regular'; the OrderPad uses LIMIT/MARKET/SL.
 *
 * Error handling:
 *   - Kite rejects (insufficient funds, invalid price) → throws, error toast
 *   - Kite succeeds but /api/nq-orders fails → logs a warning, returns
 *     partial result (kite OK, nq null). The Kite order still went through;
 *     user should see it in Kite web. nq_orders reconciliation can retry.
 *   - Network failure on step 1 → throws, user can retry cleanly.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { placeOrder, createNQOrder } from '@/services/api';
import { KITE_HOLDINGS_KEY, KITE_MARGINS_KEY } from '@/hooks/queries/useKiteState';
import { KITE_ORDERS_KEY } from '@/hooks/queries/useKiteOrders';
import { NQ_STATS_KEY } from '@/hooks/queries/useNQOrders';
import { NQ_POSITIONS_KEY } from '@/hooks/queries/useNQPositions';
import { EXTERNAL_HOLDINGS_KEY } from '@/hooks/queries/useExternalHoldings';

export const NQ_ORDERS_KEY = ['nq-orders'];

function signalIdFrom(signal) {
  if (!signal) return null;
  if (signal.signal_date && signal.ticker) return `${signal.ticker}__${signal.signal_date}`;
  return signal.id ?? null;
}

export function useOrderPlacement() {
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ payload, signal, variety = 'regular' }) => {
      // ── Step 1: place the order on Kite ──────────────
      // We don't strip any fields here — OrderPad composes the payload to
      // match Kite's PlaceOrderRequest exactly. Any extra keys are ignored
      // by Kite.
      const kiteResult = await placeOrder(variety, payload);

      // Kite returns { order_id, status } on success. If we get something
      // shaped like an error ({ detail: "..." } or { error: "..." }), throw
      // so the mutation's onError fires with useful context.
      if (!kiteResult?.order_id) {
        const msg =
          kiteResult?.detail ||
          kiteResult?.error ||
          kiteResult?.message ||
          'Kite order placement failed';
        const err = new Error(msg);
        err.kiteResult = kiteResult;
        throw err;
      }

      // ── Step 2: record in nq_orders (best-effort) ────
      let nqResult = null;
      try {
        nqResult = await createNQOrder({
          kite_order_id: String(kiteResult.order_id),
          signal_id: signalIdFrom(signal),
          ticker: payload.tradingsymbol,
          action: payload.transaction_type,
          qty: payload.quantity,
          placed_price: payload.price ?? payload.trigger_price ?? null,
        });
      } catch (e) {
        // Don't fail the whole mutation if only the tracking row fails —
        // the Kite order is real and primary. Surface a gentle warning.
        // eslint-disable-next-line no-console
        console.warn('[nq_orders] tracking failed (order is still placed on Kite):', e);
      }

      return { kite: kiteResult, nq: nqResult };
    },

    onSuccess: ({ kite }, { payload, signal }) => {
      const side = payload.transaction_type;
      const ticker = payload.tradingsymbol;
      const qty = payload.quantity;
      toast.success(
        `Order sent — awaiting fill`,
        {
          description: `${side} ${qty} ${ticker}${signal?.ticker ? '' : ''} · Kite #${kite.order_id}`,
          duration: 4000,
        }
      );
      // Refetch dependent data. These run in parallel; react-query dedupes.
      qc.invalidateQueries({ queryKey: KITE_HOLDINGS_KEY });
      qc.invalidateQueries({ queryKey: KITE_MARGINS_KEY });
      qc.invalidateQueries({ queryKey: KITE_ORDERS_KEY });
      qc.invalidateQueries({ queryKey: NQ_ORDERS_KEY });
      qc.invalidateQueries({ queryKey: NQ_STATS_KEY });
      // The lifecycle views depend on nq_orders + Kite holdings, so they
      // need to refresh too — otherwise a SELL on a held NQ position
      // would show the wrong qty for ~30s until natural staleness elapses.
      qc.invalidateQueries({ queryKey: NQ_POSITIONS_KEY });
      qc.invalidateQueries({ queryKey: EXTERNAL_HOLDINGS_KEY });
    },

    onError: (error, { payload }) => {
      toast.error(
        `Order failed`,
        {
          description: error?.message || `${payload.transaction_type} ${payload.tradingsymbol} could not be placed.`,
          duration: 6000,
        }
      );
    },
  });

  return {
    placeOrder: (args) => mutation.mutateAsync(args),
    isPending: mutation.isPending,
    error: mutation.error,
    lastResult: mutation.data ?? null,
    reset: mutation.reset,
  };
}

export default useOrderPlacement;
