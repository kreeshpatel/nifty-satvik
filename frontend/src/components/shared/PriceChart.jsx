/**
 * PriceChart — the sole TradingView lightweight-charts entry point in the app.
 *
 * Sole consumer of the `lightweight-charts` package. Other charts (equity
 * curves, donuts, heatmaps) stay on Recharts because lwc is purpose-built for
 * OHLC/financial series. If you need a price chart anywhere, use this — never
 * import lwc directly elsewhere.
 *
 * Caller owns the surrounding chrome (ChartCard for header / period pills /
 * footer). PriceChart is presentation-only: candles in, lwc canvas out.
 */
import React, { useEffect, useMemo, useRef } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
} from 'lightweight-charts';
// Note: CandlestickSeries, AreaSeries, HistogramSeries are v5 named exports
// — not available in v4.2.0. Using addCandlestickSeries() / addAreaSeries() /
// addHistogramSeries() method API (v4) instead.
import { toLwcSeries, inferIntraday } from '@/lib/candles';

// Resolve any CSS-syntax colour string (oklch, hsl, named, hex, rgb...) to a
// form lightweight-charts can parse: '#rrggbb' opaque or 'rgba(r,g,b,a)'
// translucent. lwc ships its own colour parser that predates CSS Color 4
// and throws "Failed to parse color" on `oklch(...)`.
//
// Why we don't just use canvas: we tried earlier (commit 52de3e4). The canvas
// 2D API's fillStyle DOES accept oklch in modern engines, but on some
// browsers (Safari, certain Firefox versions, some Chromiums) it ECHOES the
// oklch string back instead of normalizing to hex/rgba. That echo leaks
// straight into lwc and crashes the chart. So we now do an explicit
// OKLCH→sRGB conversion (Björn Ottosson's matrix) for any oklch() input,
// and only use canvas for non-oklch fallback (named colours, hsl(), etc.).

// ── OKLCH → sRGB ─────────────────────────────────────────────────────────
//
// CSS Color 4 syntax:
//   oklch(L C H)              — L is 0-1 or 0%-100%, C unbounded ≥0, H deg
//   oklch(L C H / A)          — A is 0-1 or 0%-100%
//   oklch(L C H deg)          — explicit deg unit on hue (rare)
//
// Math: OKLCH → OKLab → Linear sRGB → sRGB (gamma-encoded).
// Reference: https://bottosson.github.io/posts/oklab/

function _parseOklch(str) {
  const m = str.match(
    /^oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)(?:deg)?(?:\s*\/\s*([\d.]+)(%?))?\s*\)$/i
  );
  if (!m) return null;
  let L = parseFloat(m[1]);
  if (m[2] === '%') L /= 100;
  const C = parseFloat(m[3]);
  const H = parseFloat(m[4]);
  let alpha = m[5] != null ? parseFloat(m[5]) : 1;
  if (m[6] === '%') alpha /= 100;
  if (Number.isNaN(L) || Number.isNaN(C) || Number.isNaN(H) || Number.isNaN(alpha)) return null;
  return { L, C, H, alpha };
}

function _oklchToRgb({ L, C, H }) {
  // OKLCH → OKLab
  const aLab = C * Math.cos(H * Math.PI / 180);
  const bLab = C * Math.sin(H * Math.PI / 180);
  // OKLab → Linear sRGB (Ottosson matrix)
  const l_ = L + 0.3963377774 * aLab + 0.2158037573 * bLab;
  const m_ = L - 0.1055613458 * aLab - 0.0638541728 * bLab;
  const s_ = L - 0.0894841775 * aLab - 1.2914855480 * bLab;
  const l3 = l_ * l_ * l_;
  const m3 = m_ * m_ * m_;
  const s3 = s_ * s_ * s_;
  let R =  4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3;
  let G = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3;
  let B = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3;
  // Linear → sRGB gamma encoding
  const gamma = (v) =>
    v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055;
  R = Math.max(0, Math.min(1, gamma(R)));
  G = Math.max(0, Math.min(1, gamma(G)));
  B = Math.max(0, Math.min(1, gamma(B)));
  return [Math.round(R * 255), Math.round(G * 255), Math.round(B * 255)];
}

function _rgbToHex(r, g, b) {
  const h = (n) => n.toString(16).padStart(2, '0');
  return `#${h(r)}${h(g)}${h(b)}`;
}

// Cached canvas for non-oklch inputs (named colours, hsl(), etc.).
let _resolverCtx = null;
function _ctx() {
  if (_resolverCtx) return _resolverCtx;
  const cv = document.createElement('canvas');
  cv.width = 1;
  cv.height = 1;
  _resolverCtx = cv.getContext('2d');
  return _resolverCtx;
}

function resolveColor(cssColor, fallback) {
  const input = (cssColor || '').trim();
  if (!input) return fallback;

  // 1. oklch() — explicit math conversion. Never depends on canvas behaviour.
  if (/^oklch\s*\(/i.test(input)) {
    const parsed = _parseOklch(input);
    if (!parsed) return fallback;
    const [r, g, b] = _oklchToRgb(parsed);
    if (parsed.alpha >= 1) return _rgbToHex(r, g, b);
    return `rgba(${r},${g},${b},${Number(parsed.alpha.toFixed(3))})`;
  }

  // 2. Already in a lwc-friendly form — pass through.
  if (input.startsWith('#') || /^rgba?\(/i.test(input)) {
    return input;
  }

  // 3. Named colours, hsl(), etc. — canvas converter as last resort.
  try {
    const ctx = _ctx();
    if (!ctx) return fallback;
    ctx.fillStyle = '#000000';
    ctx.fillStyle = input;
    const resolved = ctx.fillStyle;
    // Canvas refused to parse → sentinel stayed.
    if (
      resolved === '#000000' &&
      input.toLowerCase() !== '#000000' &&
      input.toLowerCase() !== 'black'
    ) {
      return fallback;
    }
    // Canvas accepted but echoed an unparseable form (oklch / hwb / lab) —
    // shouldn't happen given step 1 above, but guard anyway.
    if (/^(oklch|oklab|hwb|lab|lch)\(/i.test(resolved)) {
      return fallback;
    }
    return resolved;
  } catch {
    return fallback;
  }
}

// Read CSS-var design tokens once per chart mount and resolve oklch/etc to
// canvas-friendly hex/rgba. Tokens are stable for the chart's lifetime; if
// the theme ever becomes user-switchable we'd need to recreate on theme change.
function readTokens() {
  const cs = getComputedStyle(document.documentElement);
  const get = (k, fallback) =>
    resolveColor((cs.getPropertyValue(k) || '').trim(), fallback);
  return {
    bull:    get('--bull',     '#3FDD8A'),
    bear:    get('--bear',     '#FF5C7A'),
    brand:   get('--brand',    '#4F8CFF'),
    surface: get('--surface-1','rgba(255,255,255,0.04)'),
    text1:   get('--text-1',   '#FAFAFA'),
    text3:   get('--text-3',   'rgba(255,255,255,0.55)'),
    edge1:   get('--edge-1',   'rgba(255,255,255,0.05)'),
    edge2:   get('--edge-2',   'rgba(255,255,255,0.10)'),
    edge3:   get('--edge-3',   'rgba(255,255,255,0.18)'),
    // fontMono is a font stack, not a colour — read raw.
    fontMono: ((cs.getPropertyValue('--font-mono') || '').trim() || 'ui-monospace, monospace'),
  };
}

// Turn a #hex or rgba(...) colour (already canvas-resolved by readTokens) into
// the same colour with a forced alpha. lwc area-series wants a translucent
// topColor that fades to transparent.
function withAlpha(color, alpha) {
  const c = (color || '').trim();
  if (!c) return `rgba(255,255,255,${alpha})`;

  if (c.startsWith('#')) {
    const hex = c.slice(1);
    const full = hex.length === 3
      ? hex.split('').map((ch) => ch + ch).join('')
      : hex.padEnd(6, '0').slice(0, 6);
    const r = parseInt(full.slice(0, 2), 16);
    const g = parseInt(full.slice(2, 4), 16);
    const b = parseInt(full.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  // rgb()/rgba() — slot the alpha in
  const m = c.match(/rgba?\(([^)]+)\)/i);
  if (m) {
    const parts = m[1].split(',').map((p) => p.trim());
    return `rgba(${parts[0]},${parts[1]},${parts[2]},${alpha})`;
  }

  // Last-resort: send through the canvas resolver to coerce, then drop alpha
  // back in. Handles named colours, hsl(), etc.
  const resolved = resolveColor(c, `rgba(255,255,255,${alpha})`);
  if (resolved.startsWith('#') || /^rgba?\(/i.test(resolved)) {
    return withAlpha(resolved, alpha);
  }
  return c;
}

export function PriceChart({
  candles = [],
  height = 400,
  chartType = 'candle',     // 'candle' | 'area'
  showVolume = true,
  signal = null,            // { entry, stop, target } or null
  ltp = null,
  tone = 'muted',           // colours area mode + LTP line
  intraday,                 // unset → auto-detect from candle timestamps via inferIntraday
  ariaLabel = 'Price chart', // overridable for screen readers (canvas itself is opaque to AT)
}) {
  // Auto-detect intraday if the caller didn't pass it explicitly. Keeps
  // both Yahoo (sometimes hourly for '1M') and Kite (daily for '1M') paths
  // correct without making the caller know which data source answered.
  const intradayResolved = useMemo(
    () => (typeof intraday === 'boolean' ? intraday : inferIntraday(candles)),
    [intraday, candles],
  );
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const priceSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const priceLinesRef = useRef({ entry: null, stop: null, target: null, ltp: null });
  const tokensRef = useRef(null);

  // Chart lifecycle — create once, destroy on unmount. chartType + intraday
  // changes recreate the inner series via the data effect below; we don't
  // need to recreate the whole chart for those.
  //
  // `autoSize: true` makes lwc own the ResizeObserver internally — it tracks
  // the container's clientWidth/Height and redraws on change. This is more
  // robust than our previous manual observer, which had a 0-width-at-mount
  // race when the container was inside a tab/drawer that hadn't laid out
  // yet (lwc would create a 0-width canvas that needed a later resize event
  // to recover).
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;

    const tokens = readTokens();
    tokensRef.current = tokens;

    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: tokens.surface },
        textColor: tokens.text3,
        fontFamily: tokens.fontMono,
        fontSize: 10,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: tokens.edge1 },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: tokens.edge3, width: 1, style: LineStyle.Dotted, labelBackgroundColor: tokens.surface },
        horzLine: { color: tokens.edge2, width: 1, style: LineStyle.Dotted, labelBackgroundColor: tokens.surface },
      },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.08, bottom: showVolume ? 0.28 : 0.08 } },
      timeScale: { borderVisible: false, timeVisible: intradayResolved, secondsVisible: false },
      handleScroll: true,
      handleScale: true,
    });
    chartRef.current = chart;

    return () => {
      try { chart.remove(); } catch { /* already disposed */ }
      chartRef.current = null;
      priceSeriesRef.current = null;
      volumeSeriesRef.current = null;
      priceLinesRef.current = { entry: null, stop: null, target: null, ltp: null };
    };
    // The chart is created once; intraday/showVolume changes flow through
    // the dedicated effects below without recreating the chart.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // showVolume drives the price-scale bottom margin so the volume pane
  // has room. Container height is controlled by the wrapper div's CSS via
  // the `height` prop (autoSize watches the container).
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.applyOptions({
      rightPriceScale: { scaleMargins: { top: 0.08, bottom: showVolume ? 0.28 : 0.08 } },
    });
  }, [showVolume]);

  // intraday changes the time-axis label format (HH:MM vs date). Apply
  // without recreating the chart so user period switches don't flicker.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.applyOptions({
      timeScale: { timeVisible: intradayResolved, secondsVisible: false },
    });
  }, [intradayResolved]);

  // Memoize lwc-shaped series so we don't recompute on every render. The
  // OHLC + area arrays are tiny (≤ ~3650 points worst case for ALL period),
  // but candle arrays change identity often during loading flicker.
  const tokens = tokensRef.current; // null on very first render — guarded below
  const series = useMemo(
    () =>
      toLwcSeries(candles, {
        intraday: intradayResolved,
        bullColor: withAlpha(tokens?.bull || '#22C55E', 0.55),
        bearColor: withAlpha(tokens?.bear || '#EF4444', 0.55),
      }),
    [candles, intradayResolved, tokens?.bull, tokens?.bear],
  );

  // Series creation + data binding — fires on chartType/intraday/data change.
  // On chartType flip we tear down the price series and rebuild; volume
  // series persists across flips.
  useEffect(() => {
    const chart = chartRef.current;
    const t = tokensRef.current;
    if (!chart || !t) return;

    // (Re)build the price series whenever chartType changes.
    if (priceSeriesRef.current) {
      try { chart.removeSeries(priceSeriesRef.current); } catch { /* noop */ }
      priceSeriesRef.current = null;
      priceLinesRef.current = { entry: null, stop: null, target: null, ltp: null };
    }

    if (chartType === 'area') {
      const toneColor =
        tone === 'bull' ? t.bull :
        tone === 'bear' ? t.bear : t.brand;
      priceSeriesRef.current = chart.addAreaSeries({
        lineColor: toneColor,
        topColor: withAlpha(toneColor, 0.32),
        bottomColor: withAlpha(toneColor, 0),
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
      });
      priceSeriesRef.current.setData(series.area);
    } else {
      priceSeriesRef.current = chart.addCandlestickSeries({
        upColor:       t.bull,
        downColor:     t.bear,
        wickUpColor:   t.bull,
        wickDownColor: t.bear,
        borderVisible: false,
        priceLineVisible: false,
        lastValueVisible: true,
      });
      priceSeriesRef.current.setData(series.ohlc);
    }

    // Volume series — created once, then kept in sync via setData.
    if (showVolume) {
      if (!volumeSeriesRef.current) {
        volumeSeriesRef.current = chart.addHistogramSeries({
          priceFormat: { type: 'volume' },
          priceScaleId: '',
          lastValueVisible: false,
          priceLineVisible: false,
        });
        volumeSeriesRef.current.priceScale().applyOptions({
          scaleMargins: { top: 0.78, bottom: 0 },
        });
      }
      volumeSeriesRef.current.setData(series.volume);
    } else if (volumeSeriesRef.current) {
      try { chart.removeSeries(volumeSeriesRef.current); } catch { /* noop */ }
      volumeSeriesRef.current = null;
    }

    // Fit content on first data load so the user sees the whole range
    // without manual zoom. Once the user pans/zooms, we don't refit
    // (lwc only refits on explicit calls).
    if (series.ohlc.length > 0) {
      try { chart.timeScale().fitContent(); } catch { /* noop */ }
    }
  }, [chartType, series, tone, showVolume]);

  // Price line overlays — entry / stop / target / LTP. Diff against refs
  // so we only recreate the lines that actually changed.
  useEffect(() => {
    const ps = priceSeriesRef.current;
    const t = tokensRef.current;
    if (!ps || !t) return;

    const desired = {
      entry: signal && Number.isFinite(Number(signal.entry))
        ? { price: Number(signal.entry), color: t.text3, title: 'Entry' }
        : null,
      stop: signal && Number.isFinite(Number(signal.stop))
        ? { price: Number(signal.stop), color: t.bear, title: 'Stop' }
        : null,
      target: signal && Number.isFinite(Number(signal.target))
        ? { price: Number(signal.target), color: t.bull, title: 'Target' }
        : null,
      ltp: Number.isFinite(Number(ltp))
        ? { price: Number(ltp), color: t.brand, title: 'LTP' }
        : null,
    };

    Object.keys(desired).forEach((key) => {
      const next = desired[key];
      const existing = priceLinesRef.current[key];
      if (existing) {
        try { ps.removePriceLine(existing); } catch { /* noop */ }
        priceLinesRef.current[key] = null;
      }
      if (next) {
        priceLinesRef.current[key] = ps.createPriceLine({
          price: next.price,
          color: next.color,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: next.title,
        });
      }
    });
  }, [signal, ltp]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      style={{ width: '100%', height, position: 'relative' }}
    />
  );
}

export default PriceChart;
