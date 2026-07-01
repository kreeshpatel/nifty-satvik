import { useEffect, useState } from "react";
import { motion, useMotionValue, useMotionTemplate, useSpring } from "framer-motion";

/**
 * CursorGrid — fixed-position page background dot grid.
 *
 * Default: a calm, static muted dot grid that adds page texture without
 * drawing the eye. Per the editorial direction, the page should let the
 * big editorial type and scroll-bound moments do the talking — the
 * background is texture, not animation.
 *
 * `reactive` opts into the cursor-reactive amber halo (used on Login
 * where it's the central animated element). Auto-disabled on touch /
 * prefers-reduced-motion.
 */
export default function CursorGrid({ enabled = false, reactive = false, radius = 220 }) {
  const mouseX = useMotionValue(-9999);
  const mouseY = useMotionValue(-9999);
  const smoothX = useSpring(mouseX, { stiffness: 280, damping: 32, mass: 0.4 });
  const smoothY = useSpring(mouseY, { stiffness: 280, damping: 32, mass: 0.4 });
  const [active, setActive] = useState(false);

  useEffect(() => {
    if (!enabled || !reactive) return;
    const coarse = window.matchMedia("(pointer: coarse)").matches;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (coarse || reduced) return;

    setActive(true);

    const onMove = (e) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };
    const onLeave = () => {
      mouseX.set(-9999);
      mouseY.set(-9999);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerleave", onLeave, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
    };
  }, [enabled, reactive, mouseX, mouseY]);

  const mask = useMotionTemplate`radial-gradient(circle ${radius}px at ${smoothX}px ${smoothY}px, #000 0%, rgba(0,0,0,0.6) 40%, transparent 100%)`;

  // Static base — always rendered. Muted dots, no animation.
  const base = (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10"
      style={{
        backgroundImage:
          "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.035) 1px, transparent 0)",
        backgroundSize: "28px 28px",
      }}
    />
  );

  if (!enabled || !reactive || !active) return base;

  return (
    <>
      {base}
      {/* Blue dot grid, only visible inside the cursor mask */}
      <motion.div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(79,140,255,0.55) 1.4px, transparent 0)",
          backgroundSize: "28px 28px",
          maskImage: mask,
          WebkitMaskImage: mask,
        }}
      />
    </>
  );
}
