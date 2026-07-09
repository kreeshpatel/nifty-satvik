/**
 * useSignals — react-query hook for the live signals feed.
 *
 * Backing endpoint: GET /api/signals
 *   Returns { signals, regime, portfolio, model, cron_health, sizing_capital, ... }
 *
 * Cache policy (from the redesign plan §6.1):
 *   staleTime: 5 minutes       — signals only regenerate when the 4:15 PM IST cron runs
 *   gcTime:    30 minutes
 *   refetch:   on mount + on window focus + every 5 minutes while page is visible
 *
 * We do NOT align polling to cron wall-clock times here (that was in an earlier
 * plan draft). A simple 5-min interval is deterministic, easy to reason about,
 * and the response is already server-cached cheaply.
 *
 * Shape returned to callers:
 *   { data, isLoading, isFetching, error, refetch }
 *
 * Consumer components read:
 *   data.signals        — array of active signals for today
 *   data.regime         — { status, strength, vix, breadth }
 *   data.model          — { version, trained_at, n_features }
 *   data.cron_health    — { status, expected_today, last_run_today }
 *   data.portfolio      — paper portfolio snapshot
 *   data.sizing_capital — capital used by cron for position sizing
 */
import { useQuery } from '@tanstack/react-query';
import { fetchSignals } from '@/services/api';

export const SIGNALS_QUERY_KEY = ['signals'];

// `model`: 'bhanushali' (weekly-swing, the systematic live book — default) or
// 'momentum' (baseline_v1, suspended). Part of the query key so each model
// caches separately. 'weekly' still resolves to bhanushali on the backend.
export function useSignals({ model = 'bhanushali', ...options } = {}) {
  return useQuery({
    queryKey: [...SIGNALS_QUERY_KEY, model],
    queryFn: () => fetchSignals(model),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    refetchIntervalInBackground: false,  // don't burn requests while tab is hidden
    ...options,
  });
}

export default useSignals;
