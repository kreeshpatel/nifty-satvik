import { motion } from "framer-motion";
import { easeOutQuart } from "@/lib/motion";

const REGIME_LABELS = { 0: "BEAR", 1: "CHOPPY", 2: "BULL" };
const REGIME_COLORS = {
  0: "var(--bear)",
  1: "var(--warn)",
  2: "var(--bull)",
};

/**
 * RegimeStatement — viewport-dominant editorial sentence:
 *   "The market is BULL."
 *
 * Sized to fill the hero centerline at clamp(72px, 12vw, 200px) so the
 * page commands attention the moment it loads. The label word ("BULL"
 * etc.) is amber italic — the rest near-white. Animation is a single
 * fade-up on the whole sentence; word-by-word stagger fights the size.
 */
export default function RegimeStatement({ regime = 2 }) {
  const label = REGIME_LABELS[regime] ?? "BULL";
  const color = REGIME_COLORS[regime] ?? "var(--brand)";

  return (
    <motion.h1
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, delay: 0.15, ease: easeOutQuart }}
      className="font-heading"
      style={{
        fontWeight: 600,
        color: "var(--text-1)",
        // Lower the floor on small viewports — at 72px the headline
        // overflows symmetric layout on phones <380px and the eye reads
        // it as left-leaning. clamp(48px..) keeps it bold but contained.
        fontSize: "clamp(48px, 12vw, 200px)",
        lineHeight: 0.92,
        letterSpacing: "-0.03em",
        margin: "0 auto",
        maxWidth: "min(100%, 14ch)",
        textAlign: "center",
      }}
    >
      The market is{" "}
      <span style={{ color, fontStyle: "italic" }}>{label}</span>
      <span style={{ color: "var(--text-1)" }}>.</span>
    </motion.h1>
  );
}
