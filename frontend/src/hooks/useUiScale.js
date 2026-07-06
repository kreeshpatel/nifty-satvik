import { useCallback, useEffect, useState } from 'react';

/**
 * useUiScale — a "zoom that doesn't reflow" control.
 *
 * Applies CSS `zoom` to the document root, which scales the whole UI uniformly
 * WITHOUT changing the effective viewport width the responsive breakpoints see
 * — so the layout stays put (unlike browser Ctrl +/− which reflows). Persisted
 * to localStorage. `zoom` is supported in Chromium + Safari + Firefox ≥126.
 */
const KEY = 'nq_ui_scale';
const STEPS = [0.8, 0.9, 1, 1.1, 1.25];

function readScale() {
  try {
    const v = parseFloat(localStorage.getItem(KEY));
    return STEPS.includes(v) ? v : 1;
  } catch { return 1; }
}

export function applyUiScale(v) {
  if (typeof document !== 'undefined') {
    document.documentElement.style.zoom = String(v || 1);
  }
}

// Apply the saved scale as early as possible so there's no flash at 100%.
applyUiScale(readScale());

export function useUiScale() {
  const [scale, setScale] = useState(readScale);

  useEffect(() => {
    applyUiScale(scale);
    try { localStorage.setItem(KEY, String(scale)); } catch {}
  }, [scale]);

  const dec = useCallback(() => setScale((s) => STEPS[Math.max(0, STEPS.indexOf(s) - 1)]), []);
  const inc = useCallback(() => setScale((s) => STEPS[Math.min(STEPS.length - 1, STEPS.indexOf(s) + 1)]), []);
  const reset = useCallback(() => setScale(1), []);

  return {
    scale,
    pct: Math.round(scale * 100),
    canDec: scale > STEPS[0],
    canInc: scale < STEPS[STEPS.length - 1],
    dec, inc, reset,
  };
}

export default useUiScale;
