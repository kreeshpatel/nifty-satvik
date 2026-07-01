/**
 * useBacktestLive + useBacktestHistorical — track record data hooks.
 *
 * Backing endpoints:
 *   GET /api/backtest/live       — live record since Jan 2026
 *   GET /api/backtest/historical — full 2020-2025 backtest
 *
 * Both return a single consolidated blob of:
 *   {
 *     as_of, start_date,
 *     stats: { days_live, total_signals, win_rate, avg_return_pct, hit_target, hit_stop, expired, ... },
 *     equity_curve: [{ date, month, strategy, strategy_pct }],
 *     monthly_returns: { '2026': [2.5, 3.1, -0.8, ...] },
 *     exit_reasons:    [{ reason, value, count, color }],
 *     recent_closed:   [{ id, date, symbol, side, entry, exit, pnl, pnlPct, exitReason, holdDays }],
 *     active:          [{ ticker, sector, entry, target, stop, current_price, pnl_pct, ... }],
 *   }
 *
 * Cache:
 *   - live:       10 min stale (regenerated as new signals close)
 *   - historical: 1 day stale (regenerated monthly by cron)
 */
import { useQuery } from '@tanstack/react-query';
import { fetchBacktestLive, fetchBacktestHistorical } from '@/services/api';

export const BACKTEST_LIVE_KEY = ['backtest', 'live'];
export const BACKTEST_HISTORICAL_KEY = ['backtest', 'historical'];

export function useBacktestLive(options = {}) {
  return useQuery({
    queryKey: BACKTEST_LIVE_KEY,
    queryFn: fetchBacktestLive,
    staleTime: 10 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    ...options,
  });
}

export function useBacktestHistorical(options = {}) {
  return useQuery({
    queryKey: BACKTEST_HISTORICAL_KEY,
    queryFn: fetchBacktestHistorical,
    staleTime: 24 * 60 * 60 * 1000,
    gcTime: 7 * 24 * 60 * 60 * 1000,
    ...options,
  });
}

export default useBacktestLive;
