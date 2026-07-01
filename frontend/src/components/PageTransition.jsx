import { motion } from "framer-motion";

/**
 * Wraps a page to give it a fade-in + slight scale on mount,
 * and fade-out + slight scale-down on unmount.
 */
export default function PageTransition({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.35, ease: [0.65, 0.05, 0, 1] }}
    >
      {children}
    </motion.div>
  );
}
