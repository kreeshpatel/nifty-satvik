/**
 * useExecution — the per-user durable self-reported execution ledger (Stage 4, ADR 0011).
 *
 * The site instructs; the user executes on their own broker and reports each fill (qty + price)
 * via a popup. These hooks read the durable positions and record buy/sell events. Unlike the
 * ephemeral bought-mark this replaced (removed 2026-08-27), this is the truth-of-record:
 * remaining qty, cost basis, and realized
 * P&L are derived server-side from the append-only events.
 *
 * Backing endpoints: GET /api/execution/positions, GET /api/execution/position/{id},
 * POST /api/execution/{buy,sell,correct}. signal_id = "{TICKER}__{YYYY-MM-DD}".
 */
import { useMemo } from 'react';
import { useQuery, useQueries, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  fetchExecutionPositions,
  fetchExecutionPosition,
  fetchReconciliation,
  fetchDiscipline,
  recordBuy,
  recordSell,
} from '@/services/api';
import { ledgerCostBasis } from '@/lib/cards';

export const EXECUTION_KEY = ['user', 'execution', 'positions'];
export const RECONCILIATION_KEY = ['user', 'execution', 'reconciliation'];
export const DISCIPLINE_KEY = ['user', 'execution', 'discipline'];
export const executionPositionKey = (signalId) => ['user', 'execution', 'position', signalId];

/** The six-leg discipline gauge priced on the Sharpe null segment [0.67 … 1.03] (Stage 6). */
export function useDiscipline(options = {}) {
  return useQuery({
    queryKey: DISCIPLINE_KEY,
    queryFn: fetchDiscipline,
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    ...options,
  });
}

/** The user's OPEN reconciliation action items (model plan − their ledger). */
export function useReconciliation(options = {}) {
  return useQuery({
    queryKey: RECONCILIATION_KEY,
    queryFn: fetchReconciliation,
    select: (data) => ({
      asOf: data?.as_of ?? null,
      nOpen: data?.n_open ?? 0,
      items: Array.isArray(data?.action_items) ? data.action_items : [],
    }),
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    ...options,
  });
}

/**
 * The nav-badge counts: how many lines /this-week is holding for you right now.
 *
 * Shares RECONCILIATION_KEY with useReconciliation, so the badge costs no extra request — it is
 * the same cached payload read through a different select. It exists because a daily alarm that
 * only speaks on the page you have to remember to open is not an alarm: the missed-exit item is
 * derived every weekday, and until it was counted in the chrome the user could go a week without
 * learning the model had sold a name they still hold.
 *
 * `missed` is kept SEPARATE from `exitsDue` rather than summed into one number, because they carry
 * different urgency — an exit that is still due is on-plan, one already missed is not — and the
 * badge colours on that distinction.
 */
export function useOutstandingActions(options = {}) {
  return useQuery({
    queryKey: RECONCILIATION_KEY,
    queryFn: fetchReconciliation,
    select: (data) => {
      const items = Array.isArray(data?.action_items) ? data.action_items : [];
      const missed = items.filter((i) => i.type === 'MISSED_EXIT').length;
      const exitsDue = items.filter((i) => i.type === 'SELL_DUE' || i.type === 'STALE_HOLD').length;
      return { missed, exitsDue, total: missed + exitsDue };
    },
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    ...options,
  });
}

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

// Module-level so its identity is stable across renders; combine results are structurally shared.
const trailEvents = (results) => results.map((r) => (Array.isArray(r.data?.events) ? r.data.events : null));

/**
 * The event trails of several positions → Map(signal_id → events | null while loading).
 *
 * Shares executionPositionKey with useExecutionPosition, so a recorded fill invalidates it too.
 * Callers pass only the handful of positions a demerger touched (see ledgerCostBasis in lib/cards),
 * and must memoise `signalIds`.
 */
export function useExecutionTrails(signalIds) {
  const events = useQueries({
    queries: signalIds.map((sid) => ({
      queryKey: executionPositionKey(sid),
      queryFn: () => fetchExecutionPosition(sid),
      staleTime: 15 * 1000,
    })),
    combine: trailEvents,
  });
  return useMemo(() => new Map(signalIds.map((sid, i) => [sid, events[i]])), [signalIds, events]);
}

/**
 * The cost basis of every given ledger position → Map(signal_id → ledgerCostBasis result).
 *
 * ONE implementation for Research, Portfolio and Dashboard, because all three price the reader's
 * P&L off `avg_buy_price` and a demerged holding must read the same on each. Joins the demerger
 * notes from the signals feed (the ledger does not carry them) and fetches event trails only for
 * the positions a demerger touched. `positions` and `signals` must be memoised.
 */
// The ledger re-bases a demerged holding server-side now (position_state + corporate_actions), so a
// position that carries `cost_basis` is already answered and needs no event trail. The local
// computation stays as the fallback for a frontend deployed ahead of that backend; it can go once
// the API has shipped.
const fromLedger = (p) => (typeof p?.cost_basis === 'string' ? {
  avg: Number(p.avg_buy_price) || null,
  rawAvg: Number(p.raw_avg_buy_price ?? p.avg_buy_price) || null,
  basis: p.cost_basis,
} : null);

export function useLedgerCostBases(positions, signals) {
  const caBySignal = useMemo(() => {
    const m = new Map();
    for (const s of signals ?? []) {
      if (!Array.isArray(s?.corporate_actions) || s.corporate_actions.length === 0) continue;
      const t = String(s.ticker || '').toUpperCase();
      if (t) m.set(s.signal_id || `${t}__${s.signal_date}`, s.corporate_actions);
    }
    return m;
  }, [signals]);
  const sids = useMemo(
    () => (positions ?? []).filter((p) => !fromLedger(p) && caBySignal.has(p.signal_id)).map((p) => p.signal_id),
    [positions, caBySignal]);
  const trails = useExecutionTrails(sids);
  return useMemo(() => new Map((positions ?? []).map((p) => [p.signal_id, fromLedger(p) ?? ledgerCostBasis({
    avgBuy: p.avg_buy_price, events: trails.get(p.signal_id), corporateActions: caBySignal.get(p.signal_id),
  })])), [positions, trails, caBySignal]);
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
      // The ledger changed → refresh positions, this position's trail, outstanding actions
      // and the discipline gauge. Held-ness is DERIVED from positions now, so there is no second
      // store to invalidate alongside them.
      qc.invalidateQueries({ queryKey: EXECUTION_KEY });
      if (vars?.signal_id) qc.invalidateQueries({ queryKey: executionPositionKey(vars.signal_id) });
      qc.invalidateQueries({ queryKey: RECONCILIATION_KEY });
      qc.invalidateQueries({ queryKey: DISCIPLINE_KEY });
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
