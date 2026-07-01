import React from 'react';

const TONE_STOPS = {
  brand: [
    'rgba(79, 140, 255, 0.28)',
    'rgba(79, 140, 255, 0.10)',
    'rgba(123, 91, 255, 0.18)',
  ],
  bull: [
    'oklch(72% 0.19 145 / 0.24)',
    'oklch(72% 0.19 145 / 0.08)',
    'oklch(56% 0.16 145 / 0.16)',
  ],
  info: [
    'oklch(78% 0.11 230 / 0.24)',
    'oklch(78% 0.11 230 / 0.08)',
    'oklch(60% 0.14 230 / 0.16)',
  ],
  warn: [
    'oklch(68% 0.18 40 / 0.22)',
    'oklch(68% 0.18 40 / 0.08)',
    'oklch(54% 0.16 40 / 0.14)',
  ],
};

const KEYFRAMES_ID = 'nq-aurora-breathe';

if (typeof document !== 'undefined' && !document.getElementById(KEYFRAMES_ID)) {
  const style = document.createElement('style');
  style.id = KEYFRAMES_ID;
  style.textContent = `
    @keyframes nq-aurora-breathe {
      0%   { transform: translate3d(-4%,  -2%, 0) scale(1.05); opacity: 0.85; }
      50%  { transform: translate3d( 4%,   3%, 0) scale(1.15); opacity: 1;    }
      100% { transform: translate3d(-4%,  -2%, 0) scale(1.05); opacity: 0.85; }
    }
    @keyframes nq-aurora-drift {
      0%   { transform: translate3d( 3%,   2%, 0) scale(1.08); opacity: 0.65; }
      50%  { transform: translate3d(-3%,  -3%, 0) scale(1.18); opacity: 0.9;  }
      100% { transform: translate3d( 3%,   2%, 0) scale(1.08); opacity: 0.65; }
    }
    @media (prefers-reduced-motion: reduce) {
      .nq-aurora-layer { animation: none !important; }
    }
  `;
  document.head.appendChild(style);
}

export function Aurora({
  tone = 'brand',
  intensity = 1,
  className,
  style,
}) {
  const stops = TONE_STOPS[tone] || TONE_STOPS.brand;
  return (
    <div
      aria-hidden="true"
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
        ...style,
      }}
    >
      <div
        className="nq-aurora-layer"
        style={{
          position: 'absolute',
          inset: '-20%',
          background: `radial-gradient(60% 50% at 22% 28%, ${stops[0]} 0%, transparent 60%)`,
          opacity: intensity,
          animation: 'nq-aurora-breathe var(--dur-breathe) var(--ease-bloom) infinite',
          willChange: 'transform, opacity',
          mixBlendMode: 'screen',
        }}
      />
      <div
        className="nq-aurora-layer"
        style={{
          position: 'absolute',
          inset: '-20%',
          background: `radial-gradient(55% 45% at 78% 30%, ${stops[1]} 0%, transparent 65%)`,
          opacity: intensity,
          animation: 'nq-aurora-drift var(--dur-drift) var(--ease-bloom) infinite',
          willChange: 'transform, opacity',
          mixBlendMode: 'screen',
        }}
      />
      <div
        className="nq-aurora-layer"
        style={{
          position: 'absolute',
          inset: '-20%',
          background: `radial-gradient(70% 60% at 50% 90%, ${stops[2]} 0%, transparent 60%)`,
          opacity: intensity * 0.7,
          animation: 'nq-aurora-breathe calc(var(--dur-breathe) * 1.3) var(--ease-bloom) infinite reverse',
          willChange: 'transform, opacity',
          mixBlendMode: 'screen',
        }}
      />
    </div>
  );
}

export default Aurora;
