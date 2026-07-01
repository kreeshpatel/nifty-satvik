import React from 'react';

const PRESETS = {
  brand:         'var(--stage-light-brand)',
  'brand-strong':'var(--stage-light-brand-strong)',
  bull:          'var(--stage-light-bull)',
  info:          'var(--stage-light-info)',
};

export function StageLight({
  tone = 'brand',
  intensity = 1,
  blendMode = 'screen',
  className,
  style,
}) {
  const bg = PRESETS[tone] || PRESETS.brand;
  return (
    <div
      aria-hidden="true"
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        backgroundImage: bg,
        opacity: intensity,
        mixBlendMode: blendMode,
        ...style,
      }}
    />
  );
}

export default StageLight;
