import { useEffect, useRef, useState } from "react";
import { useSpring, useMotionValue } from "framer-motion";

/**
 * Animated number display — counts between old and new values with spring physics.
 * Flashes green/red briefly when the value changes direction.
 *
 * Usage: <AnimatedValue value={24867.5} format={fmtPrice} />
 */
export function AnimatedValue({
  value,
  format = (v) => v.toFixed(2),
  className = "",
  style = {},
}) {
  const motionVal = useMotionValue(typeof value === "number" ? value : 0);
  const spring = useSpring(motionVal, { stiffness: 80, damping: 20, mass: 0.5 });
  const [display, setDisplay] = useState(() => format(typeof value === "number" ? value : 0));
  const [flash, setFlash] = useState(null); // 'up' | 'down' | null
  const prevRef = useRef(typeof value === "number" ? value : 0);

  useEffect(() => {
    const num = typeof value === "number" ? value : 0;
    const prev = prevRef.current;

    if (num !== prev) {
      // Determine direction for flash
      if (num > prev) setFlash("up");
      else if (num < prev) setFlash("down");

      // Clear flash after 400ms
      const timer = setTimeout(() => setFlash(null), 400);
      prevRef.current = num;
      motionVal.set(num);
      return () => clearTimeout(timer);
    }
  }, [value, motionVal]);

  useEffect(() => {
    const unsub = spring.on("change", (v) => {
      setDisplay(format(v));
    });
    return unsub;
  }, [spring, format]);

  const flashBg = flash === "up"
    ? "rgba(16, 185, 129, 0.15)"
    : flash === "down"
    ? "rgba(239, 68, 68, 0.15)"
    : "transparent";

  return (
    <span
      className={`inline-block tabular-nums transition-colors duration-300 ${className}`}
      style={{
        ...style,
        backgroundColor: flashBg,
        borderRadius: 4,
        padding: flash ? "0 2px" : undefined,
      }}
    >
      {display}
    </span>
  );
}
