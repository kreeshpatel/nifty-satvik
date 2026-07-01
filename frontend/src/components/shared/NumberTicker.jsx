import React, { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

function easeOutExpo(t) {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

export function NumberTicker({
  value,
  duration = 1100,
  decimals = 0,
  prefix = '',
  suffix = '',
  formatter,
  className,
  style,
}) {
  const ref = useRef(null);
  const [display, setDisplay] = useState(0);
  const [hasEntered, setHasEntered] = useState(false);
  const reduced = useReducedMotion();
  const startedRef = useRef(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (reduced) {
      setDisplay(value);
      setHasEntered(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !startedRef.current) {
            startedRef.current = true;
            setHasEntered(true);
            io.unobserve(node);
          }
        });
      },
      { threshold: 0.4 },
    );
    io.observe(node);
    return () => io.disconnect();
  }, [reduced, value]);

  useEffect(() => {
    if (!hasEntered) return;
    if (reduced) {
      setDisplay(value);
      return;
    }
    const start = performance.now();
    const from = 0;
    const to = Number(value) || 0;
    let raf = 0;
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      setDisplay(from + (to - from) * easeOutExpo(t));
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [hasEntered, value, duration, reduced]);

  const formatted = formatter
    ? formatter(display)
    : display.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });

  return (
    <span ref={ref} className={className} style={{ fontVariantNumeric: 'tabular-nums', ...style }}>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
}

export default NumberTicker;
