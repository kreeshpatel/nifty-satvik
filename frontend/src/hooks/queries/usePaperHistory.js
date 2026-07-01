/**
 * usePaperHistory — react-query hook for the paper-broker equity curve.
 *
 * Backing endpoint: GET /api/portfolio/paper-history
 *
 * Rows are the realistic capital-constrained ₹10L paper-broker ledger
 * (results/paper_ledger_history.csv), written once per trading day by the
 * scanner cron's paper-broker step (src/trading/paper_broker.py). This is
 * deliberately separate from useNavHistory (live Kite NAV) — the Paper view
 * of the Portfolio Equity Curve must read THIS so it plots the bot's actual
 * ₹10L equity instead of silently showing the live account's NAV.
 *
 * Series is empty until the paper bot starts running (NIFTYQUANT_PAPER_BROKER
 * env var). The chart degrades to an honest "data accumulates daily" empty
 * state in that case.
 *
 * Cache: 60s stale, 5min gc — matches useNavHistory (snapshots are 1/day,
 * so a tighter stale time would just churn the cache).
 */
import { useQuery } from '@tanstack/react-query';
import { fetchPaperHistory } from '@/services/api';

export const PAPER_HISTORY_KEY = ['portfolio', 'paper-history'];

export function usePaperHistory({ days = 365, ...options } = {}) {
  return useQuery({
    queryKey: [...PAPER_HISTORY_KEY, days],
    queryFn: () => fetchPaperHistory(days),
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    select: (raw) => ({
      history: Array.isArray(raw?.history) ? raw.history : [],
      count: raw?.count ?? 0,
      firstDate: raw?.first_date ?? null,
      lastDate: raw?.last_date ?? null,
      // ₹10L cost basis (INITIAL_CAPITAL) so the "since inception %" anchors to
      // the same denominator /overview uses, not the first surviving ledger row.
      baseline: raw?.baseline ?? null,
    }),
    ...options,
  });
}

export default usePaperHistory;
