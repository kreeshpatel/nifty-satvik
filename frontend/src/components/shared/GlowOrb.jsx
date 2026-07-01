import React from 'react';

const TONE_COLORS = {
  brand: 'rgba(79, 140, 255, 0.55)',
  bull:  'rgba(63, 221, 138, 0.45)',
  bear:  'rgba(255, 92, 122, 0.40)',
  info:  'rgba(91, 199, 255, 0.45)',
  warn:  'rgba(255, 180, 84, 0.40)',
};

export function GlowOrb({
  tone = 'brand',
  size = 360,
  x = '50%',
  y = '50%',
  blur = 80,
  pulse = false,
  className,
  style,
}) {
  const color = TONE_COLORS[tone] || TONE_COLORS.brand;
  return (
    <div
      aria-hidden="true"
      className={className}
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: size,
        height: size,
        marginLeft: -size / 2,
        marginTop: -size / 2,
        borderRadius: '50%',
        background: `radial-gradient(circle at 50% 50%, ${color} 0%, transparent 65%)`,
        filter: `blur(${blur}px)`,
        opacity: pulse ? 0.8 : 1,
        animation: pulse ? 'nq-orb-pulse 4200ms var(--ease-bloom) infinite' : 'none',
        pointerEvents: 'none',
        mixBlendMode: 'screen',
        willChange: pulse ? 'opacity, transform' : 'auto',
        ...style,
      }}
    />
  );
}

const KEY_ID = 'nq-orb-keyframes';
if (typeof document !== 'undefined' && !document.getElementById(KEY_ID)) {
  const s = document.createElement('style');
  s.id = KEY_ID;
  s.textContent = `
    @keyframes nq-orb-pulse {
      0%, 100% { opacity: 0.6; transform: scale(0.95); }
      50%      { opacity: 1;   transform: scale(1.05); }
    }
    @media (prefers-reduced-motion: reduce) {
      [style*="nq-orb-pulse"] { animation: none !important; }
    }
  `;
  document.head.appendChild(s);
}

export default GlowOrb;
