import { useEffect, useRef, useState, useCallback } from "react";
import { isMarketHours } from "./useMarketHours";

/**
 * Polling hook that respects tab visibility and (optionally) market hours.
 *
 * @param {() => Promise<any>} fetcher - async function returning data
 * @param {number} intervalMs - poll interval
 * @param {object} opts
 * @param {boolean} opts.enabled - pause polling when false (default true)
 * @param {boolean} opts.pauseWhenHidden - pause when document is hidden (default true)
 * @param {boolean} opts.marketHoursOnly - only poll during Nifty market hours (default false)
 * @param {Array<any>} opts.deps - when these change, refetch immediately and restart interval
 *
 * @returns { data, error, loading, lastUpdated, isPolling, refetch }
 */
export default function usePolling(fetcher, intervalMs, opts = {}) {
  const {
    enabled = true,
    pauseWhenHidden = true,
    marketHoursOnly = false,
    deps = [],
  } = opts;

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [tick, setTick] = useState(0); // triggers re-evaluation when visibility or market-hours change

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const doFetch = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Re-evaluate polling on visibility change
  useEffect(() => {
    if (!pauseWhenHidden) return;
    const handler = () => setTick((t) => t + 1);
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, [pauseWhenHidden]);

  // Re-evaluate every 60s when marketHoursOnly so we catch market open/close transitions
  useEffect(() => {
    if (!marketHoursOnly) return;
    const id = setInterval(() => setTick((t) => t + 1), 60_000);
    return () => clearInterval(id);
  }, [marketHoursOnly]);

  // Core polling loop
  useEffect(() => {
    if (!enabled) return;
    const visible = !pauseWhenHidden || document.visibilityState === "visible";
    if (!visible) return;

    if (marketHoursOnly && !isMarketHours()) {
      // Do one initial fetch for last-known data, but don't loop.
      if (!data) doFetch();
      return;
    }

    doFetch();
    const id = setInterval(doFetch, intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, marketHoursOnly, pauseWhenHidden, tick, ...deps]);

  const isPolling = enabled
    && (!pauseWhenHidden || (typeof document !== "undefined" && document.visibilityState === "visible"))
    && (!marketHoursOnly || isMarketHours());

  return { data, error, loading, lastUpdated, isPolling, refetch: doFetch };
}
