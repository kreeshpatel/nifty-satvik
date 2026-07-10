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
      // Quantity normalization. Kite's /portfolio/holdings can split a real
      // position's shares across FOUR fields: `quantity` (settled),
      // `t1_quantity` (just-bought, settling tomorrow), `collateral_quantity`
      // (pledged for margin — e.g. via Kite's "Pledge" flow), and
      // `mtf.quantity` (bought on the Margin Trading Facility — those shares
      // sit in a separate `mtf` sub-object, not the top-level `quantity`,
      // because the broker holds them as collateral for the leveraged buy).
      // A position that's fully pledged, freshly bought, or MTF-funded
      // reports quantity=0 even though the holding is real — every UI calc
      // that did `qty * ltp` on the raw `quantity` alone rendered it as
      // worth ₹0 (value, unrealised P&L, allocation — all zeroed), and any
      // capital sitting in an MTF position read as leftover "Cash" instead
      // of an actual holding.
      //
      // We override `quantity` to mean the EFFECTIVE held position (settled
      // + T+1 + collateral + MTF) so all consumers — Dashboard, Portfolio,
      // NQ positions math — naturally use the right number. Original values
      // preserved as `settled_quantity` / `t1_quantity` / `collateral_quantity`
      // / `mtf_quantity` for UI affordances that want to badge "T+1: N" or
      // "Pledged: N" on a row. `product` surfaces 'MTF' instead of Kite's
      // default 'CNC' so the UI can label the position by how it was
      // actually funded rather than implying it's a plain cash buy.
      return list.map((h) => {
        const settled = Number(h.quantity) || 0;
        const t1 = Number(h.t1_quantity) || 0;
        const collateral = Number(h.collateral_quantity) || 0;
        const mtf = Number(h.mtf?.quantity) || 0;
        return {
          ...h,
          quantity: settled + t1 + collateral + mtf,
          settled_quantity: settled,
          t1_quantity: t1,
          collateral_quantity: collateral,
          mtf_quantity: mtf,
          product: mtf > 0 ? 'MTF' : (h.product || 'CNC'),
        };
      });
    },
  });
}

export default { useKiteMargins, useKiteHoldings };
