import React, { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

export function RevealOnScroll({
  children,
  delay = 0,
  y = 24,
  duration = 0.72,
  once = true,
  threshold = 0.15,
  as: As = 'div',
  className,
  style,
}) {
  const ref = useRef(null);
  const [shown, setShown] = useState(false);
  const reduced = useReducedMotion();

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (reduced) {
      setShown(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setShown(true);
            if (once) io.unobserve(node);
          } else if (!once) {
            setShown(false);
          }
        });
      },
      { threshold, rootMargin: '0px 0px -10% 0px' },
    );
    io.observe(node);
    return () => io.disconnect();
  }, [once, threshold, reduced]);

  const MotionAs = motion[As] || motion.div;

  return (
    <MotionAs
      ref={ref}
      className={className}
      style={style}
      initial={reduced ? false : { opacity: 0, y }}
      animate={shown ? { opacity: 1, y: 0 } : { opacity: 0, y }}
      transition={{
        duration,
        delay,
        ease: [0.16, 1, 0.3, 1],
      }}
    >
      {children}
    </MotionAs>
  );
}

export default RevealOnScroll;
