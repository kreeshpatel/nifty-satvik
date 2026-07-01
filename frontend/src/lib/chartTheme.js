/**
 * Chart theme tokens — single source of truth for all recharts usage.
 * Mirrors the design-token layer in index.css: blue accent, semantic
 * green/red, muted grid, dark glass tooltip.
 *
 * Usage:
 *   import { CHART_COLORS, CHART_GRID, CHART_AXIS_TICK, ChartDefs, tooltipStyle, chartTooltipContent } from '@/lib/chartTheme';
 */

// Brand & semantic colors
export const CHART_COLORS = {
  blue: '#4F8CFF',
  blueLight: '#6DA1FF',
  blueDeep: '#2C5BFF',
  blueGlow: 'rgba(79, 140, 255, 0.40)',
  green: '#3FDD8A',
  red: '#FF5C7A',
  amber: '#FFB454',
  violet: '#7B5BFF',
  cyan: '#5BC7FF',
  // Diverse categorical palette — use for pie/donut slices or multi-series
  categorical: ['#4F8CFF', '#6DA1FF', '#3FDD8A', '#FFB454', '#7B5BFF', '#5BC7FF', '#FF5C7A', '#2C5BFF'],
};

// Grid + axis treatment
export const CHART_GRID = {
  stroke: 'rgba(255, 255, 255, 0.05)',
  strokeDasharray: '3 3',
};

export const CHART_AXIS_TICK = {
  fontSize: 10,
  fill: '#6B7280',
  fontFamily: 'var(--font-mono)',
};

export const CHART_AXIS_LINE = { stroke: 'rgba(255, 255, 255, 0.06)' };

// Tooltip container style — matches surface-2 recipe
export const tooltipStyle = {
  background: 'rgba(15, 23, 42, 0.92)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  borderRadius: 10,
  padding: '8px 12px',
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.45)',
  color: '#E5E7EB',
};

export const tooltipLabelStyle = { fontSize: 11, color: '#9CA3AF', marginBottom: 2, fontWeight: 500 };
export const tooltipValueStyle = { fontSize: 13, color: '#E5E7EB', fontVariantNumeric: 'tabular-nums', fontWeight: 600 };

// SVG filter ids for drop-shadow glow on line charts
export const GLOW_FILTER_ID = 'chart-glow-blue';

// Gradient ids (use these in Area fill="url(#...)")
export const GRADIENT_ID_BLUE = 'chart-grad-blue';
export const GRADIENT_ID_GREEN = 'chart-grad-green';
export const GRADIENT_ID_RED = 'chart-grad-red';
export const GRADIENT_ID_BLUE_BAR = 'chart-grad-blue-bar';

/**
 * Shared <defs> block — drop into any recharts chart:
 *   <AreaChart>
 *     <ChartDefs />
 *     <Area fill="url(#chart-grad-blue)" filter={`url(#${GLOW_FILTER_ID})`} ... />
 *   </AreaChart>
 *
 * Exposes:
 *  - linear area gradients (blue, green, red)
 *  - vertical bar gradient (blue -> blue-deep)
 *  - blue drop-shadow glow filter for line strokes
 */
export const ChartDefs = () => (
  <defs>
    <linearGradient id={GRADIENT_ID_BLUE} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={CHART_COLORS.blue} stopOpacity={0.28} />
      <stop offset="95%" stopColor={CHART_COLORS.blue} stopOpacity={0.01} />
    </linearGradient>
    <linearGradient id={GRADIENT_ID_GREEN} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={CHART_COLORS.green} stopOpacity={0.22} />
      <stop offset="95%" stopColor={CHART_COLORS.green} stopOpacity={0.01} />
    </linearGradient>
    <linearGradient id={GRADIENT_ID_RED} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={CHART_COLORS.red} stopOpacity={0.22} />
      <stop offset="95%" stopColor={CHART_COLORS.red} stopOpacity={0.01} />
    </linearGradient>
    <linearGradient id={GRADIENT_ID_BLUE_BAR} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={CHART_COLORS.blueLight} stopOpacity={1} />
      <stop offset="100%" stopColor={CHART_COLORS.blueDeep} stopOpacity={1} />
    </linearGradient>
    <filter id={GLOW_FILTER_ID} x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feFlood floodColor={CHART_COLORS.blue} floodOpacity="0.45" />
      <feComposite in2="blur" operator="in" />
      <feMerge>
        <feMergeNode />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
);

/**
 * Bar shape helpers — use as the `shape` prop on <Bar> to render
 * rounded-top bars with the design-system blue gradient.
 */
export const ROUNDED_BAR_RADIUS = [6, 6, 0, 0];
