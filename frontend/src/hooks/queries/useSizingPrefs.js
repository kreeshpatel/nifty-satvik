/**
 * useSizingPrefs / useSizerConfig — the position sizer's risk tier + capital.
 *
 * Tier %s and the single-position cap are POLICY constants owned by the backend
 * (config.py, = the backtest cost model's home) and served static via
 * GET /api/sizer/config. The user's chosen tier + remembered capital are per-user
 * (GET/PUT /api/me/sizing-prefs).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { fetchSizerConfig, fetchSizingPrefs, updateSizingPrefs } from '@/services/api';

export const SIZER_CONFIG_KEY = ['sizer', 'config'];
export const SIZING_PREFS_KEY = ['user', 'sizing-prefs'];

const DEFAULT_CONFIG = { tiers: { medium: 0.02, high: 0.03 }, position_cap_pct: 0.20 };

/** Sizing policy constants (tiers + cap). Cached hard — they rarely change. */
export function useSizerConfig() {
  return useQuery({
    queryKey: SIZER_CONFIG_KEY,
    queryFn: fetchSizerConfig,
    select: (d) => ({
      tiers: d?.tiers ?? DEFAULT_CONFIG.tiers,
      position_cap_pct: d?.position_cap_pct ?? DEFAULT_CONFIG.position_cap_pct,
    }),
    staleTime: 60 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
    placeholderData: DEFAULT_CONFIG,
  });
}

/** The user's saved { risk_tier, default_capital }. */
export function useSizingPrefs() {
  return useQuery({
    queryKey: SIZING_PREFS_KEY,
    queryFn: fetchSizingPrefs,
    select: (d) => ({ risk_tier: d?.risk_tier ?? 'medium', default_capital: d?.default_capital ?? null }),
    staleTime: 5 * 60 * 1000,
  });
}

/** Persist tier and/or capital; optimistically applies immediately. */
export function useUpdateSizingPrefs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prefs) => updateSizingPrefs(prefs),
    onMutate: async (prefs) => {
      await qc.cancelQueries({ queryKey: SIZING_PREFS_KEY });
      const prev = qc.getQueryData(SIZING_PREFS_KEY);
      qc.setQueryData(SIZING_PREFS_KEY, (old) => ({ ...(old || {}), ...prev, ...prefs }));
      return { prev };
    },
    onError: (err, _prefs, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(SIZING_PREFS_KEY, ctx.prev);
      toast.error('Could not save sizing preference', { description: err?.message });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: SIZING_PREFS_KEY }),
  });
}

export default useSizingPrefs;
