import { useRef } from "react";
import { motion, useInView } from "framer-motion";

/**
 * Word-by-word scroll-triggered reveal with clip-path mask animation.
 *
 * Each word starts hidden behind a mask, then slides up + fades in
 * one after the other when the element enters the viewport.
 *
 * Props:
 * - text: string to split into words
 * - className: classes for the wrapping element
 * - delay: starting delay in seconds (default 0)
 * - stagger: delay between words (default 0.06)
 * - as: HTML element to render (default 'h2')
 */
export default function SplitText({
  text = "",
  className = "",
  delay = 0,
  stagger = 0.06,
  as = "h2",
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-15%" });
  const words = text.split(" ");

  const Component = motion[as] || motion.h2;

  return (
    <Component
      ref={ref}
      className={className}
      style={{ display: "inline-block" }}
    >
      {words.map((word, i) => (
        <span
          key={i}
          style={{
            display: "inline-block",
            overflow: "hidden",
            paddingBottom: "0.1em",
            paddingRight: "0.25em",
            verticalAlign: "top",
          }}
        >
          <motion.span
            style={{ display: "inline-block" }}
            initial={{ y: "110%", opacity: 0 }}
            animate={isInView ? { y: "0%", opacity: 1 } : {}}
            transition={{
              duration: 0.7,
              delay: delay + i * stagger,
              ease: [0.65, 0.05, 0, 1],
            }}
          >
            {word}
          </motion.span>
        </span>
      ))}
    </Component>
  );
}
