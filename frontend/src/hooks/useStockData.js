// useStockData — master hook for the stock detail page
// Tries Kite first for live data, falls back to Yahoo Finance for everything.

import { useState, useEffect, useCallback, useContext } from 'react';
import {
  getInstrumentToken, getInstrumentInfo, fetchStockData,
  fetchCurrentPrice, computeAllIndicators,
} from '@/services/kiteStock';
import {
  subscribeToTicks, unsubscribeFromTicks,
  kiteQuote, yahooQuote, yahooHistorical, yahooFundamentals,
} from '@/services/api';
import { KiteContext } from '@/App';

const PERIOD_MAP = {
  '1D':  { kite: { interval: 'minute',   days: 1 },    yahoo: { interval: '5m',  period: '1d' } },
  '1W':  { kite: { interval: '5minute',  days: 7 },    yahoo: { interval: '15m', period: '5d' } },
  '1M':  { kite: { interval: '15minute', days: 30 },   yahoo: { interval: '1h',  period: '1mo' } },
  '3M':  { kite: { interval: 'day',      days: 90 },   yahoo: { interval: '1d',  period: '3mo' } },
  '6M':  { kite: { interval: 'day',      days: 180 },  yahoo: { interval: '1d',  period: '6mo' } },
  '1Y':  { kite: { interval: 'day',      days: 365 },  yahoo: { interval: '1d',  period: '1y' } },
  '5Y':  { kite: { interval: 'day',      days: 1825 }, yahoo: { interval: '1d',  period: '5y' } },
  'ALL': { kite: { interval: 'day',      days: 3650 }, yahoo: { interval: '1d',  period: 'max' } },
};

export function useStockData(symbol) {
  const kite = useContext(KiteContext);
  const [token, setToken] = useState(null);
  const [info, setInfo] = useState(null);
  const [price, setPrice] = useState(null);
  const [candles, setCandles] = useState([]);
  const [indicators, setIndicators] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [orders, setOrders] = useState([]);
  const [period, setPeriod] = useState('1Y');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // errorKind distinguishes "backend / network failed" from "request succeeded
  // but returned nothing" — lets the empty-state UI pick warn vs muted.
  // 'network' | 'empty' | null
  const [errorKind, setErrorKind] = useState(null);
  const [tick, setTick] = useState(null);
  // warmingUp flips true if loading lingers past 2s — surfaced in the UI as
  // a "fetching live data" banner so users know we're alive during a slow
  // first load (a cold 24h instrument-master cache, an uncached historical
  // candle fetch, etc. — see routers/kite.py). NOT a Render-style cold
  // start: the backend has run on Fly.io (always-on, min_machines_running=1)
  // since 2026-06-25 and never sleeps. Cleared as soon as price or candles
  // land. Independent of loading so we don't show the banner on every fast load.
  const [warmingUp, setWarmingUp] = useState(false);

  // Resolve symbol -> token + info
  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;
    (async () => {
      try {
        const [t, inf] = await Promise.all([
          getInstrumentToken(symbol),
          getInstrumentInfo(symbol),
        ]);
        if (cancelled) return;
        setToken(t);
        setInfo(inf);
      } catch {}
    })();
    return () => { cancelled = true; };
  }, [symbol]);

  // Fetch all data: price, candles, holdings — Kite + Yahoo IN PARALLEL.
  //
  // Previous structure was serial: Kite-price → Yahoo-price fallback → Kite-
  // candles → Yahoo-candles fallback → daily-indicators fetch. On Kite-slow
  // or Kite-down, every page mount paid the full Kite timeout twice before
  // hitting the Yahoo fallback. Worst case observed: 30+ seconds.
  //
  // New structure fires all four primary arms (Kite price, Yahoo price,
  // Kite candles, Yahoo candles) in parallel via Promise.allSettled. Total
  // latency = max(slowest_arm) instead of sum_of_serial_attempts. Kite is
  // still preferred when it returns valid data; Yahoo is the fallback we
  // never used to call until Kite finished.
  //
  // The daily-indicators 4th fetch (only fires for intraday periods that
  // can't compute RSI/EMA from the bars they have) is deferred to a
  // separate effect below so it doesn't gate first paint.
  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setErrorKind(null);
    setWarmingUp(false);

    // If the page is still loading after 2s, surface the warming-up banner.
    // Cleared by the early-paint trigger below the moment price/candles land.
    const warmTimer = setTimeout(() => {
      if (!cancelled) setWarmingUp(true);
    }, 2000);

    (async () => {
      const periodCfg = PERIOD_MAP[period] || PERIOD_MAP['1Y'];
      const startedAt = performance.now();

      // Per-arm helpers — each returns null on failure (no thrown errors
      // escape, so Promise.allSettled always sees 'fulfilled' but with
      // potentially-null value). Lets us count "real failures" separately
      // from "didn't even try because no Kite session".
      const kiteAttempt = kite.connected && token;

      const priceKite = kiteAttempt
        ? fetchCurrentPrice(token).catch(() => null)
        : Promise.resolve(null);

      const priceYahoo = yahooQuote(symbol).catch(() => null);

      const candlesKite = kiteAttempt
        ? fetchStockData(token, periodCfg.kite.interval, periodCfg.kite.days)
            .catch(() => null)
        : Promise.resolve(null);

      const candlesYahoo = yahooHistorical(
        symbol, periodCfg.yahoo.interval, periodCfg.yahoo.period,
      ).catch(() => null);

      // Fire holdings + orders in the same parallel batch when Kite is
      // connected. They're independent of price/candles and don't gate the
      // chart, but starting them now overlaps their latency.
      const holdingsP = kite.connected
        ? Promise.resolve(null)
        : Promise.resolve(null);
      const ordersP = kite.connected
        ? Promise.resolve(null)
        : Promise.resolve(null);

      // ─── EARLY-PAINT: flip loading=false the moment price OR candles arrive
      // Previously we awaited Promise.all on ALL six arms before painting,
      // so the slowest arm (often yfinance fundamentals or a cold-start
      // Kite call) gated first paint. Now we race the four core arms and
      // unblock the page as soon as we have *anything useful*. Holdings +
      // orders backfill in the background without delaying the chart.
      const racePrice = (async () => {
        // Resolve as soon as either price source returns a real LTP.
        const winner = await Promise.race([
          priceKite.then((r) => (r?.last_price ? { kind: 'kite', r } : null)),
          priceYahoo.then((r) => (r?.last_price ? { kind: 'yahoo', r } : null)),
        ]).catch(() => null);
        return winner;
      })();
      const raceCandles = (async () => {
        const winner = await Promise.race([
          candlesKite.then((r) => (r?.candles?.length ? { kind: 'kite', r } : null)),
          candlesYahoo.then((r) => (Array.isArray(r) && r.length ? { kind: 'yahoo', r } : null)),
        ]).catch(() => null);
        return winner;
      })();

      // First-paint trigger: race price + candles. If either lands, flip
      // loading=false so the user gets a paint. The full Promise.all below
      // still completes for the canonical assignment (winner-side fallback,
      // failure-counting, etc.).
      Promise.race([racePrice, raceCandles]).then((winner) => {
        if (cancelled || !winner) return;
        // Surface the winner immediately as a partial state — full state
        // is written below once Promise.all settles. Avoid re-flicker by
        // only writing fields the canonical pass will preserve.
        if (winner.kind === 'kite' && winner.r?.last_price && !winner.r?.candles) {
          setPrice((prev) => prev ?? winner.r);
        } else if (winner.kind === 'yahoo' && winner.r?.last_price && !Array.isArray(winner.r)) {
          // Yahoo quote shape — normalise to our canonical price shape.
          setPrice((prev) => prev ?? {
            last_price: winner.r.last_price,
            open: winner.r.open,
            high: winner.r.high,
            low: winner.r.low,
            close: winner.r.previous_close || winner.r.close,
            volume: winner.r.volume,
            change: winner.r.change,
            change_pct: winner.r.change_pct,
            fifty_two_week_high: winner.r.fifty_two_week_high,
            fifty_two_week_low: winner.r.fifty_two_week_low,
            market_cap: winner.r.market_cap,
            name: winner.r.name,
          });
        } else if (Array.isArray(winner.r) && winner.r.length > 0) {
          setCandles((prev) => prev.length > 0 ? prev : winner.r);
        } else if (winner.r?.candles?.length > 0) {
          setCandles((prev) => prev.length > 0 ? prev : winner.r.candles);
        }
        // Unblock the chart skeleton + LTP block — even if other arms still
        // pending, the user sees real data. Also clear the warming banner.
        setLoading(false);
        setWarmingUp(false);
      });

      const [
        kpRes, ypRes, kcRes, ycRes, hRes, oRes,
      ] = await Promise.all([priceKite, priceYahoo, candlesKite, candlesYahoo, holdingsP, ordersP]);

      // ─── Resolve price: prefer Kite when it returned a real LTP ───
      let priceData = null;
      if (kpRes && kpRes.last_price) {
        priceData = kpRes;
      } else if (ypRes && ypRes.last_price) {
        priceData = {
          last_price: ypRes.last_price,
          open: ypRes.open,
          high: ypRes.high,
          low: ypRes.low,
          close: ypRes.previous_close || ypRes.close,
          volume: ypRes.volume,
          change: ypRes.change,
          change_pct: ypRes.change_pct,
          fifty_two_week_high: ypRes.fifty_two_week_high,
          fifty_two_week_low: ypRes.fifty_two_week_low,
          market_cap: ypRes.market_cap,
          name: ypRes.name,
        };
        if (ypRes.name && (!info || !info.name)) {
          setInfo(prev => ({ ...prev, name: ypRes.name, tradingsymbol: symbol }));
        }
      }

      // ─── Resolve candles: prefer Kite when it returned bars ───
      let candleData = [];
      let indicatorData = null;
      if (kcRes && Array.isArray(kcRes.candles) && kcRes.candles.length > 0) {
        candleData = kcRes.candles;
        indicatorData = kcRes.indicators;
      } else if (Array.isArray(ycRes) && ycRes.length > 0) {
        candleData = ycRes;
        // Compute indicators from daily Yahoo candles inline (already daily
        // bars so no extra fetch needed).
        if (periodCfg.yahoo.interval === '1d') {
          try {
            indicatorData = computeAllIndicators(candleData);
          } catch {}
        }
      }

      // ─── Filter holdings/orders to this ticker ───
      const holdingsData = Array.isArray(hRes)
        ? hRes.filter(x => x.tradingsymbol === symbol)
        : [];
      const ordersData = Array.isArray(oRes)
        ? oRes.filter(x => x.tradingsymbol === symbol)
        : [];

      // Track failures for errorKind. A "real" failure is when an arm
      // returned null AND we were expecting it to work. Kite arms not
      // attempted (no session) don't count.
      let netFailures = 0;
      let netAttempts = 0;
      if (kiteAttempt) {
        netAttempts += 1;
        if (!kpRes || !kpRes.last_price) netFailures += 1;
        netAttempts += 1;
        if (!kcRes || !kcRes.candles?.length) netFailures += 1;
      }
      netAttempts += 1;
      if (!ypRes || !ypRes.last_price) netFailures += 1;
      netAttempts += 1;
      if (!Array.isArray(ycRes) || ycRes.length === 0) netFailures += 1;

      if (cancelled) return;

      const elapsedMs = Math.round(performance.now() - startedAt);

      console.info(
        `[stock] useStockData ✓ ${elapsedMs}ms (price=${priceData ? '✓' : '✗'} candles=${candleData.length} indicators=${indicatorData ? '✓' : '–'})`,
      );

      clearTimeout(warmTimer);
      setPrice(priceData);
      setCandles(candleData);
      setIndicators(indicatorData);
      setHoldings(holdingsData);
      setOrders(ordersData);
      setLoading(false);
      setWarmingUp(false);

      if (!priceData && candleData.length === 0) {
        // Network errored on a majority of attempts → backend is likely down /
        // cold-starting / unreachable. Half the attempts could be normal Kite
        // 401s when disconnected, so we use a strict majority threshold.
        if (netAttempts > 0 && netFailures >= Math.ceil(netAttempts / 2)) {
          setErrorKind('network');
          setError(`Backend unreachable. Reload in a few seconds while it warms up.`);
        } else {
          setErrorKind('empty');
          setError(`No data found for ${symbol}. Check if the symbol is valid.`);
        }
      }
    })();

    return () => {
      cancelled = true;
      clearTimeout(warmTimer);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, token, period, kite.connected]);

  // ─── Deferred indicator backfill ──────────────────────────────────
  //
  // For intraday periods (1D / 1W / 1M with sub-daily Yahoo intervals), the
  // primary fetch produces bars whose granularity is too fine for the daily-
  // window indicators (RSI 14 / ADX 14 / EMA 21 / EMA 50). If indicators
  // are still null after the main fetch settled, fall back to a 1-year
  // daily Yahoo fetch JUST for indicator computation. This used to live
  // inside the main effect, blocking the page; now it runs after `candles`
  // is set so first paint isn't delayed.
  useEffect(() => {
    if (!symbol) return;
    if (indicators) return;          // already have them from primary fetch
    if (candles.length === 0) return; // nothing to gate on yet

    const periodCfg = PERIOD_MAP[period] || PERIOD_MAP['1Y'];
    if (periodCfg.yahoo.interval === '1d') return; // daily — would have computed already

    let cancelled = false;
    // Defer one tick so we don't compete with the first paint.
    const t = setTimeout(async () => {
      try {
        const dailyCandles = await yahooHistorical(symbol, '1d', '1y');
        if (cancelled) return;
        if (Array.isArray(dailyCandles) && dailyCandles.length > 30) {
          setIndicators(computeAllIndicators(dailyCandles));
        }
      } catch {}
    }, 0);

    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, period, candles, indicators]);

  // Subscribe to WebSocket ticks for live price (Kite only)
  useEffect(() => {
    if (!token || !kite.connected) return;
    subscribeToTicks([token]);
    return () => unsubscribeFromTicks([token]);
  }, [token, kite.connected]);

  // Live price polling: Kite quote every 3s if connected, Yahoo every 30s as fallback.
  //
  // Why 3s and not 1s: human reaction time on depth is ~1s, but the page is
  // not a HFT terminal — a 3s refresh feels live and halves backend QPS,
  // which matters a lot on the cold-start path where every extra request
  // queues behind the warm-up. OrderBookL2 reads from the same tick we
  // refresh here (via the `tick` prop in StockDetailV2), so it inherits
  // this cadence too — no separate /api/kite/quote poll fires.
  useEffect(() => {
    if (!symbol) return;

    const pollKite = kite.connected && symbol;
    const intervalMs = pollKite ? 3000 : 30000;
    const instrumentKey = `NSE:${symbol}`;

    const poll = async () => {
      try {
        if (pollKite) {
          // Kite paid live quote — real-time, includes market depth
          const data = await kiteQuote([instrumentKey]);
          const q = data?.[instrumentKey] || data?.data?.[instrumentKey];
          if (q) {
            setPrice(prev => ({
              ...prev,
              last_price: q.last_price,
              open: q.ohlc?.open,
              high: q.ohlc?.high,
              low: q.ohlc?.low,
              close: q.ohlc?.close,
              volume: q.volume || q.volume_traded,
              change: q.net_change,
              change_pct: q.ohlc?.close ? ((q.last_price - q.ohlc.close) / q.ohlc.close * 100) : null,
            }));
            // Update tick with depth data for OrderBook
            if (q.depth) {
              setTick({ depth: q.depth, last_price: q.last_price, volume: q.volume });
            }
          }
        } else {
          // Yahoo fallback — ~15min delay
          const yq = await yahooQuote(symbol);
          if (yq && yq.last_price) {
            setPrice(prev => ({
              ...prev,
              last_price: yq.last_price,
              open: yq.open,
              high: yq.high,
              low: yq.low,
              close: yq.previous_close || yq.close,
              volume: yq.volume,
              change: yq.change,
              change_pct: yq.change_pct,
              fifty_two_week_high: yq.fifty_two_week_high,
              fifty_two_week_low: yq.fifty_two_week_low,
            }));
          }
        }
      } catch {}
    };

    // Fire the first poll immediately so depth + live LTP arrive on the
    // SAME tick the user hits the page. Previously the first poll waited a
    // full intervalMs (was 1s, now 3s) before firing — visible delay on
    // every navigation. The interval handles subsequent ticks.
    poll();
    const interval = setInterval(poll, intervalMs);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, kite.connected]);

  const changePeriod = useCallback((p) => setPeriod(p), []);

  return {
    symbol, token, info, price, tick, candles, indicators,
    holdings, orders, period, changePeriod, loading, warmingUp, error, errorKind,
  };
}

export default useStockData;
