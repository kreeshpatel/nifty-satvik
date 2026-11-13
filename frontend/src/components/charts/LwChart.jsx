/**
 * LwChart — a thin React wrapper over `lightweight-charts` (TradingView's open-source charting
 * library, already a dependency). Real chart component, real crosshair, real price scale — the
 * v7 rule is "no decorative squiggles" (docs/DESIGN_BRIEF_V5.md §10).
 *
 * series: [{ type: 'area' | 'line' | 'histogram' | 'candles' | 'volume', data, color, title? }]
 *   candles: [{ time, open, high, low, close }] · volume: [{ time, value, color }]
 * Colours read from the v7 tokens so the chart follows the theme. `fill` makes the chart take
 * its container's height (min `height`), so a stretched panel has no empty band under the plot.
 */
import { useEffect, useRef } from 'react';
import { createChart, ColorType, CrosshairMode, LineStyle } from 'lightweight-charts';

const css = (name, fallback) => {
  if (typeof window === 'undefined') return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
};

export default function LwChart({ series = [], height = 280, fill = false, label, priceFormat, timeVisible = false, className }) {
  const box = useRef(null);

  useEffect(() => {
    const el = box.current;
    if (!el || !series.length) return undefined;
    const line = css('--line', '#20262E');
    const h = () => (fill ? Math.max(height, el.clientHeight) : height);
    const chart = createChart(el, {
      height: h(),
      width: el.clientWidth,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: css('--ink-3', '#7A8494'),
        fontFamily: css('--mono', 'monospace'), fontSize: 11,
        // The in-plot logo is replaced by the text credit the licence asks for, placed in the
        // page footers ("Charts by TradingView Lightweight Charts™").
        attributionLogo: false },
      grid: { vertLines: { visible: false }, horzLines: { color: line, style: LineStyle.Solid } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
      timeScale: { borderVisible: false, timeVisible, fixLeftEdge: true, fixRightEdge: true, lockVisibleTimeRangeOnResize: true },
      crosshair: { mode: CrosshairMode.Magnet,
        vertLine: { color: css('--ink-4', '#4C5562'), width: 1, style: LineStyle.Dashed, labelBackgroundColor: css('--n3', '#1F252D') },
        horzLine: { color: css('--ink-4', '#4C5562'), width: 1, style: LineStyle.Dashed, labelBackgroundColor: css('--n3', '#1F252D') } },
      handleScroll: false, handleScale: false,
    });
    series.forEach((s) => {
      const common = { priceLineVisible: false, lastValueVisible: s.lastValue !== false, title: s.title || '',
        ...(priceFormat ? { priceFormat } : {}) };
      let ser;
      if (s.type === 'candles') ser = chart.addCandlestickSeries({ ...common, upColor: css('--up', '#20C4A0'), downColor: css('--down', '#FF6B4A'),
        borderVisible: false, wickUpColor: css('--up', '#20C4A0'), wickDownColor: css('--down', '#FF6B4A') });
      else if (s.type === 'volume') {
        // overlay histogram on its own scale in the bottom 20% of the pane
        ser = chart.addHistogramSeries({ priceFormat: { type: 'volume' }, priceScaleId: 'vol', lastValueVisible: false, priceLineVisible: false });
        chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 }, visible: false });
      } else if (s.type === 'histogram') ser = chart.addHistogramSeries({ ...common, color: s.color, base: 0 });
      else if (s.type === 'line') ser = chart.addLineSeries({ ...common, color: s.color, lineWidth: s.width || 2, lineStyle: s.dashed ? LineStyle.Dashed : LineStyle.Solid, crosshairMarkerRadius: 3 });
      else ser = chart.addAreaSeries({ ...common, lineColor: s.color, lineWidth: 2, topColor: s.top || 'rgba(32,196,160,.18)', bottomColor: 'rgba(32,196,160,0)', crosshairMarkerRadius: 3 });
      ser.setData(s.data);
    });
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: h() }));
    ro.observe(el);
    return () => { ro.disconnect(); chart.remove(); };
  }, [series, height, fill, priceFormat, timeVisible]);

  return <div ref={box} className={className} role="img" aria-label={label} style={{ height: fill ? '100%' : height, minHeight: height, width: '100%' }} />;
}
