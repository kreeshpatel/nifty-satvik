/**
 * useJourney — durable per-user onboarding-journey memory (Stage 6c).
 *
 * The onboarding journey is event-driven: lessons unlock off the user's OWN events (cold start,
 * first recorded buy, first 2R sell, first drawdown) and each is shown once. The "already seen"
 * store is server-side (survives devices/sessions): GET /api/journey + POST /api/journey/{flag}
 * (set-once; re-POST is a cheap no-op, so mark() can be fire-and-forget).
 *
 * Usage: const { seen, mark } = useJourney();  if (!seen('cold_start_acked')) …show… + mark(...)
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchJourneyFlags, setJourneyFlag } from '@/services/api';

export const JOURNEY_KEY = ['user', 'journey'];

export function useJourney(options = {}) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: JOURNEY_KEY,
    queryFn: fetchJourneyFlags,
    select: (data) => data?.flags ?? {},
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    ...options,
  });
  const markMutation = useMutation({
    mutationFn: ({ flag, value }) => setJourneyFlag(flag, value),
    onSuccess: (_res, { flag }) => {
      // Optimistically stamp locally so the lesson never double-fires within the session.
      qc.setQueryData(JOURNEY_KEY, (old) => ({
        flags: { ...(old?.flags ?? {}), [flag]: { set_at: new Date().toISOString(), value: null } },
      }));
    },
  });
  const flags = query.data ?? {};
  return {
    flags,
    isLoading: query.isLoading,
    seen: (flag) => Boolean(flags[flag]),
    mark: (flag, value) => markMutation.mutate({ flag, value }),
  };
}

export default useJourney;
