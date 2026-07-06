import React from 'react';
import { Link } from 'react-router-dom';
import logo from '@/assets/brand/nifty-satvik-logo.png';

/**
 * Nifty Satvik brand lockup — the real logo mark + wordmark.
 * Single source of truth so every header/sidebar renders the brand identically.
 *
 * Props:
 *   size      logo mark px (default 30)
 *   wordSize  wordmark font px (default 16)
 *   showWord  render the "Nifty Satvik" wordmark (default true)
 *   to        route to link to; pass null for a non-link (use onClick)
 *   onClick   click handler (for non-link usage, e.g. sidebar navigate)
 */
export default function BrandLogo({
  size = 30,
  wordSize = 16,
  showWord = true,
  to = '/dashboard',
  onClick,
  className,
}) {
  const gap = size >= 30 ? 10 : 8;
  const inner = (
    <>
      <img
        src={logo}
        alt="Nifty Satvik"
        width={size}
        height={size}
        style={{ width: size, height: size, objectFit: 'contain', display: 'block', flexShrink: 0 }}
      />
      {showWord && (
        <span
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: wordSize,
            letterSpacing: '-0.02em',
            color: 'var(--text-1)',
            whiteSpace: 'nowrap',
          }}
        >
          Nifty <span style={{ color: 'var(--brand)' }}>Satvik</span>
        </span>
      )}
    </>
  );

  const style = { display: 'inline-flex', alignItems: 'center', gap, textDecoration: 'none' };

  if (to) {
    return (
      <Link to={to} onClick={onClick} className={className} style={style}>
        {inner}
      </Link>
    );
  }
  return (
    <div
      className={className}
      onClick={onClick}
      style={{ ...style, cursor: onClick ? 'pointer' : undefined }}
    >
      {inner}
    </div>
  );
}
