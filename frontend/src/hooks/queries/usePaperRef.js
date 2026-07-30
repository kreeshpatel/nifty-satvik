/**
 * usePaperRef — react-query hook for the "Paper (ref)" reference book.
 *
 * Backing endpoint: GET /api/portfolio/paper-ref
 *
 * This is the bhanushali weekly-swing PAPER book — the live, flowing modelled record:
 * open positions, closed trades, and the NAV series, read by the backend from the same
 * canonical artifacts the record of record uses (results/paper_portfolio_weekly.json +
 * results/portfolio_history_weekly.csv), with a freshness stamp from the daily monitor.
 *
 * Deliberately NOT usePaperHistory: that reads results/paper_ledger_history.csv, which fed
 * the old momentum paper broker. Its producer was removed with the momentum book and the file
 * is absent from the repo, so it renders an empty series that merely looks live.
 *
 * Admin-only server-side (single-owner simulation artifact); non-admins get available:false.
 *
 * Cache: the book is re-priced once per weekday by the monitor cron, so a 60s stale time is
 * already far tighter than the data changes — matching useNavHistory/usePaperHistory.
 */
import { useQuery } from '@tanstack/react-query';
import { fetchPaperRef } from '@/services/api';

export const PAPER_REF_KEY = ['portfolio', 'paper-ref'];

export function usePaperRef(options = {}) {
  return useQuery({
    queryKey: PAPER_REF_KEY,
    queryFn: fetchPaperRef,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    ...options,
  });
}
