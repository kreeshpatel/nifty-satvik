import { motion, useScroll, useSpring } from "framer-motion";

/**
 * Thin amber scroll-progress bar pinned to the top of the viewport.
 * Single brand color — no regime gradient (the regime is now hero copy).
 */
export default function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 110,
    damping: 30,
    restDelta: 0.001,
  });

  return (
    <motion.div
      className="scroll-progress-bar"
      style={{
        scaleX,
        width: "100%",
        background: "var(--brand)",
      }}
    />
  );
}
