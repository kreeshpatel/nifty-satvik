/**
 * useKiteMargins + useKiteHoldings — react-query hooks for broker state.
 *
 * Both are gated on `enabled` so that users without Kite don't fire the
 * requests (which would 401 or return empty). The Signals page passes
 * `enabled: kiteConnected` to skip the calls when the KiteContext reports
 * disconnected.
 *
 * Both hooks dedupe across pages — Dashboard + Portfolio + Signals all
 * request holdings; react-query collapses them into a single in-flight
 * request at any given moment.
 */
import { useQuery } from '@tanstack/react-query';
import { kiteMargins, kiteHoldings } from '@/services/api';

export const KITE_MARGINS_KEY = ['kite', 'margins'];
export const KITE_HOLDINGS_KEY = ['kite', 'holdings'];

export function useKiteMargins({ enabled = true } = {}) {
  return useQuery({
    queryKey: KITE_MARGINS_KEY,
    queryFn: kiteMargins,
    enabled,
    // Margins don't move on a per-second basis — bumped from 30s to 3min so
    // route changes don't trigger a refetch storm that can falsely trip the
    // Kite session-expired detector during transient backend hiccups.
    staleTime: 3 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    select: (raw) => {
      // Normalize to { available, used, total } for downstream components.
      // Different Kite accounts expose slightly different shapes; we pick
      // the most permissive cash-available value.
      const eq = raw?.equity || {};
      const available =
        eq?.available?.live_balance ??
        eq?.available?.cash ??
        0;
      const used = eq?.utilised?.debits ?? 0;
      return {
        available: Number(available) || 0,
        used: Number(used) || 0,
        total: (Number(available) || 0) + (Number(used) || 0),
        raw,
      };
    },
  });
}

export function useKiteHoldings({ enabled = true } = {}) {
  return useQuery({
    queryKey: KITE_HOLDINGS_KEY,
    queryFn: kiteHoldings,
    enabled,
    // Holdings only change when an order fills, and the WS bridge already
    // pushes those updates. 30s was over-aggressive — every route change to
    // Dashboard/Portfolio/Funds/OrderPad caused a refetch that could cascade
    // into spurious session-expired events. 3min is plenty.
    staleTime: 3 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    select: (raw) => {
      // Kite sometimes returns an array directly, sometimes { data: [...] }.
      const list = Array.isArray(raw) ? raw : raw?.data ?? [];
      // T+1 normalization. Kite's /portfolio/holdings reports settled qty
      // in `quantity` and just-bought (settling tomorrow) in `t1_quantity`.
      // A fresh buy has quantity=0 and t1_quantity=N — every UI calc that
      // did `qty * ltp` rendered the position as worth ₹0. Same buy gets
      // "missing" by services/nq_positions drift detection too.
      //
      // We override `quantity` to mean the EFFECTIVE held position
      // (settled + T+1) so all consumers — Dashboard, Portfolio, NQ
      // positions math — naturally use the right number. Original values
      // preserved as `settled_quantity` / `t1_quantity` for UI affordances
      // that want to badge "T+1: N" on a row.
      return list.map((h) => {
        const settled = Number(h.quantity) || 0;
        const t1 = Number(h.t1_quantity) || 0;
        return {
          ...h,
          quantity: settled + t1,
          settled_quantity: settled,
          t1_quantity: t1,
        };
      });
    },
  });
}

export default { useKiteMargins, useKiteHoldings };
