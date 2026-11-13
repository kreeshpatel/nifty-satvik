/**
 * BrandMark — vector redraw of the Nifty Satvik "N" (public/nifty-design logo): the N's
 * right stroke breaks out into an up-right arrow, with three rising candles above it.
 * Crisp at every size, v7 palette: ink N, amber breakout, no network request.
 */
import { useId } from 'react';

export default function BrandMark({ size = 28, title }) {
  const id = useId().replace(/:/g, '');
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true} aria-label={title} focusable="false">
      {title && <title>{title}</title>}
      <defs>
        <linearGradient id={`bm${id}`} x1="4" y1="28" x2="28" y2="4" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#E6E9EE" />
          <stop offset="1" stopColor="#E6E9EE" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="6" fill="#11151A" />
      <rect x=".5" y=".5" width="31" height="31" rx="5.5" fill="none" stroke="#2A313B" strokeOpacity="1" />
      {/* N: left stem, diagonal, short right stem */}
      <path d="M7 25V9.6c0-.9 1.1-1.3 1.7-.7L20 21.4" fill="none" stroke={`url(#bm${id})`} strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M20 25v-7.5" fill="none" stroke={`url(#bm${id})`} strokeWidth="3.4" strokeLinecap="round" />
      {/* breakout arrow */}
      <path d="M20 17.5l5.5-6M21.6 11.2h4.1v4.1" fill="none" stroke="#F0B429" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* rising candles */}
      <g fill="#F0B429">
        <rect x="14.6" y="9" width="1.8" height="4" rx=".5" opacity=".55" /><rect x="15.25" y="7.6" width=".5" height="6.8" rx=".25" opacity=".55" />
        <rect x="18.1" y="6.4" width="1.8" height="4" rx=".5" opacity=".75" /><rect x="18.75" y="5" width=".5" height="6.8" rx=".25" opacity=".75" />
        <rect x="21.6" y="3.8" width="1.8" height="4" rx=".5" /><rect x="22.25" y="2.6" width=".5" height="6.6" rx=".25" />
      </g>
    </svg>
  );
}
