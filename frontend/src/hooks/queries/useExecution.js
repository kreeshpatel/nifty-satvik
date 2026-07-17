/**
 * useExecution — the per-user durable self-reported execution ledger (Stage 4, ADR 0011).
 *
 * The site instructs; the user executes on their own broker and reports each fill (qty + price)
 * via a popup. These hooks read the durable positions and record buy/sell events. Unlike the
 * ephemeral useHoldings mark, this is the truth-of-record: remaining qty, cost basis, and realized
 * P&L are derived server-side from the append-only events.
 *
 * Backing endpoints: GET /api/execution/positions, GET /api/execution/position/{id},
 * POST /api/execution/{buy,sell,correct}. signal_id = "{TICKER}__{YYYY-MM-DD}".
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  fetchExecutionPositions,
  fetchExecutionPosition,
  recordBuy,
  recordSell,
} from '@/services/api';
import { HOLDINGS_KEY } from './useHoldings';

export const EXECUTION_KEY = ['user', 'execution', 'positions'];
export const executionPositionKey = (signalId) => ['user', 'execution', 'position', signalId];

/** The user's durable positions → array of { signal_id, ticker, remaining_qty, realized_pnl, ... }. */
export function useExecutionPositions(options = {}) {
  return useQuery({
    queryKey: EXECUTION_KEY,
    queryFn: fetchExecutionPositions,
    select: (data) => (Array.isArray(data?.positions) ? data.positions : []),
    staleTime: 30 * 1000,
    gcTime: 10 * 60 * 1000,
    ...options,
  });
}

/** One position + its full event audit trail. Enabled only when a signalId is supplied. */
export function useExecutionPosition(signalId, options = {}) {
  return useQuery({
    queryKey: executionPositionKey(signalId),
    queryFn: () => fetchExecutionPosition(signalId),
    enabled: !!signalId,
    staleTime: 15 * 1000,
    ...options,
  });
}

function useRecordEvent(mutationFn, verb) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (res, vars) => {
      (res?.warnings ?? []).forEach((w) => toast.warning(w));
      const pos = res?.position;
      if (pos) {
        toast.success(
          `${verb} recorded`,
          { description: `${pos.ticker}: ${pos.remaining_qty} left` +
              (pos.realized_pnl ? ` · realized ₹${Math.round(pos.realized_pnl).toLocaleString('en-IN')}` : '') },
        );
      }
      // The ledger changed → refresh positions, this position's trail, and the legacy held-set.
      qc.invalidateQueries({ queryKey: EXECUTION_KEY });
      if (vars?.signal_id) qc.invalidateQueries({ queryKey: executionPositionKey(vars.signal_id) });
      qc.invalidateQueries({ queryKey: HOLDINGS_KEY });
    },
    onError: (err) => toast.error(`Could not record ${verb.toLowerCase()}`, { description: err?.message }),
  });
}

/** Record a self-reported BUY (qty + price). */
export function useRecordBuy() {
  return useRecordEvent(recordBuy, 'Buy');
}

/** Record a partial-aware self-reported SELL (qty + price + tranche). */
export function useRecordSell() {
  return useRecordEvent(recordSell, 'Sell');
}

export default useExecutionPositions;
