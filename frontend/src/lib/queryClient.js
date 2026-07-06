/* ================================================================
   QueryClient — TanStack Query setup for Nifty Satvik.

   Single shared client. Cache policy per endpoint is set at the
   useQuery call-site in hooks/queries/*, not globally here. The
   defaults below are intentionally conservative so that any hook
   that forgets to override them still behaves reasonably.

   Per-endpoint stale/gc times (cron-aligned) are documented in
   ~/.claude/plans/we-need-to-highly-streamed-bengio.md §6.1.
   ================================================================ */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Default: data is fresh for 30s, then revalidates in background on next access.
      // Most hooks override this — overview uses 60s, signals uses 5min, etc.
      staleTime: 30 * 1000,
      // Keep unused data in memory 5min before GC. Longer-lived data (backtests) overrides.
      gcTime: 5 * 60 * 1000,
      // Retry once on network failure — not on 4xx (likely auth or bad input).
      retry: (failureCount, error) => {
        const status = error?.status ?? error?.response?.status;
        if (status >= 400 && status < 500) return false;
        return failureCount < 1;
      },
      // Refetch on window focus, but only when data is stale. Prevents excess network
      // chatter when a user alt-tabs between apps during a trading session.
      refetchOnWindowFocus: true,
      // Keep the previous response visible while a refetch is in flight. Avoids
      // table flicker during polling updates on Signals / Portfolio.
      placeholderData: (prev) => prev,
    },
    mutations: {
      // Mutations (orders, notes, settings) don't retry. Duplicate order placement
      // would be catastrophic — we surface errors directly to the user.
      retry: false,
    },
  },
});

export default queryClient;
