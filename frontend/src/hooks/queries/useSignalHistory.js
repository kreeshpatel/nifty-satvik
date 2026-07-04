/**
 * useSignalHistory — pulls the full active-signal track record.
 *
 * Backing endpoint: GET /api/signals/history (authenticated FastAPI backend).
 * Reads signals_today.json + signals_history.json + signal_analytics.json
 * server-side (GitHub-first via authenticated token, local fallback) and returns:
 *   { today: [...], history: [...], analytics: {...}, source: 'backend' }
 * Replaced the retired Vercel /fn/signals function when the repo went private
 * (that function read public raw URLs + served the paid signals unauthenticated).
 * Live-price enrichment now comes from the frontend's own price/Kite hooks.
 *
 * Why this is separate from useSignals:
 *   - /api/signals returns today's fresh signals only (whatever the 4:15 PM IST
 *     cron just produced). On weekends + holidays the cron didn't run today, so
 *     it returns an empty array.
 *   - /api/signals/history ALSO returns signals from prior days that are
 *     "still in play" (status ACTIVE / NEAR_TARGET / IN_ZONE) — what a trader
 *     needs to see on Saturday or after a market holiday.
 */
import { useQuery } from '@tanstack/react-query';
import { fetchSignalHistory } from '@/services/api';

export const SIGNAL_HISTORY_KEY = ['signal-history'];

// Placeholder so consumers can read `data.today` / `data.history` immediately
// on mount without null-checking. Real fetch settles in the background.
const HISTORY_PLACEHOLDER = { today: [], history: [], analytics: {}, source: 'placeholder' };

export function useSignalHistory({ model = 'momentum', ...options } = {}) {
  return useQuery({
    queryKey: [...SIGNAL_HISTORY_KEY, model],
    queryFn: () => fetchSignalHistory(model),
    // Bumped to 15 min (was 5 min) so stock detail pages don't re-fetch
    // unnecessarily on every tab switch. Vercel function caches 5 min on
    // edge anyway — most refetches were no-ops.
    staleTime: 15 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: true,
    // `placeholderData` lets ActiveSignalStrip render immediately with an
    // empty history. The real fetch (2-3s on warm backend) finishes in the
    // background and swaps in. Eliminates one of the slow blocking requests
    // from /stock/:symbol mount — pages for stocks WITHOUT an active NQ
    // signal (most of them) now don't wait on this at all.
    placeholderData: HISTORY_PLACEHOLDER,
    ...options,
  });
}

export default useSignalHistory;
