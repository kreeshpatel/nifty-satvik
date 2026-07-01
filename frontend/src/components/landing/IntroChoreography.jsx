import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { easeOutQuart } from "@/lib/motion";

/**
 * IntroChoreography — first-load cinematic reveal.
 *
 * Storyboard (3.4s total):
 *   0.00s  Pure black + nothing
 *   0.20s  Single amber dot at center fades in
 *   0.45s  Dot expands into a horizontal hairline
 *   0.85s  NIFTYQUANT wordmark types in atop the line (letter-by-letter)
 *   1.55s  "Pre-move detection · since 2024" subtitle fades in below
 *   2.20s  Whole assembly holds for 0.4s
 *   2.60s  Black fades out + assembly scales down + moves up; hero behind
 *          becomes visible
 *   3.40s  Done — overlay unmounts entirely
 *
 * Plays once per browser session via sessionStorage. Skipped entirely
 * for `prefers-reduced-motion`. A small "Skip intro" link top-right
 * fades in at 0.6s for impatient visitors.
 */

const STORAGE_KEY = "nq_intro_seen_v1";

export default function IntroChoreography() {
  const [shouldPlay, setShouldPlay] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let seen = false;
    try {
      seen = sessionStorage.getItem(STORAGE_KEY) === "1";
    } catch {}
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (seen || reduced) {
      setDone(true);
      return;
    }
    setShouldPlay(true);

    // Note: previous version mutated document.body.style.overflow to lock
    // scroll during the intro. That created a leak surface — when the user
    // navigated to /login mid-animation, the React cleanup didn't always
    // run, leaving body locked at overflow:hidden across the entire SPA
    // (including authenticated pages). Real users hit this and lost scroll
    // everywhere until a hard refresh.
    //
    // The intro overlay (IntroOverlay below) is position:fixed inset:0 with
    // a solid backdrop, so it covers the page natively — there's nothing
    // BEHIND it that needs scroll-locking. We just let native scroll go
    // through and rely on the overlay to be the visual bouncer.

    const finishAt = 3400;
    const t = setTimeout(() => {
      setDone(true);
      try { sessionStorage.setItem(STORAGE_KEY, "1"); } catch {}
    }, finishAt);

    return () => {
      clearTimeout(t);
    };
  }, []);

  const handleSkip = () => {
    setDone(true);
    try { sessionStorage.setItem(STORAGE_KEY, "1"); } catch {}
  };

  return (
    <AnimatePresence>
      {shouldPlay && !done && <IntroOverlay onSkip={handleSkip} />}
    </AnimatePresence>
  );
}

const WORDMARK = "NIFTYQUANT";

function IntroOverlay({ onSkip }) {
  return (
    <motion.div
      key="intro"
      initial={{ opacity: 1 }}
      // Full overlay scales+translates as it fades out — gives the
      // effect of the wordmark migrating toward the top nav position.
      exit={{
        opacity: 0,
        transition: { duration: 0.7, ease: easeOutQuart },
      }}
      // Page-level fixed cover. zIndex very high to sit above everything.
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 200,
        background: "var(--surface-0)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {/* Skip link — visible after 600ms */}
      <motion.button
        type="button"
        onClick={onSkip}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.4 }}
        className="font-mono uppercase"
        style={{
          position: "absolute",
          top: 28,
          right: 28,
          background: "transparent",
          border: "none",
          color: "var(--text-3)",
          fontSize: 11,
          letterSpacing: "0.18em",
          cursor: "pointer",
          padding: "8px 10px",
        }}
        whileHover={{ color: "var(--text-1)" }}
      >
        Skip intro
      </motion.button>

      {/* Soft warm radial behind everything */}
      <motion.div
        aria-hidden
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.2, duration: 1.0, ease: easeOutQuart }}
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 1200px 700px at 50% 50%, rgba(79,140,255,0.12), transparent 65%)",
        }}
      />

      {/* The choreographed assembly — exits with scale+translate so it
          looks like the wordmark migrates to nav position. */}
      <motion.div
        initial={{ scale: 1, y: 0 }}
        animate={{ scale: 1, y: 0 }}
        exit={{
          scale: 0.42,
          y: -200,
          transition: { duration: 0.75, ease: easeOutQuart },
        }}
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 14,
        }}
      >
        {/* Center amber dot — first thing the user sees */}
        <DotToLine />

        {/* Wordmark */}
        <Wordmark />

        {/* Subtitle */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.55, duration: 0.5, ease: easeOutQuart }}
          className="font-mono uppercase"
          style={{
            fontSize: 11,
            letterSpacing: "0.22em",
            color: "var(--text-3)",
            marginTop: 4,
          }}
        >
          Pre-move detection · since 2024
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

function DotToLine() {
  return (
    <motion.div
      aria-hidden
      initial={{ width: 4, height: 4, opacity: 0 }}
      animate={{
        width: [4, 4, 220, 220],
        height: [4, 4, 1, 1],
        opacity: [0, 1, 1, 1],
      }}
      transition={{
        delay: 0.2,
        duration: 0.95,
        times: [0, 0.25, 0.7, 1],
        ease: easeOutQuart,
      }}
      style={{
        background: "var(--brand)",
        borderRadius: 999,
      }}
    />
  );
}

function Wordmark() {
  // Letter-by-letter type-in of the wordmark. Each letter scales+lifts in
  // independently with stagger ~45ms.
  const letters = WORDMARK.split("");
  return (
    <div
      className="font-heading"
      style={{
        display: "flex",
        gap: 0,
        fontSize: "clamp(40px, 8vw, 96px)",
        fontWeight: 600,
        color: "var(--text-1)",
        letterSpacing: "-0.04em",
        lineHeight: 1,
      }}
    >
      {letters.map((ch, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, y: 30, scale: 0.92 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{
            delay: 0.85 + i * 0.045,
            duration: 0.42,
            ease: easeOutQuart,
          }}
          style={{ display: "inline-block" }}
        >
          {ch}
        </motion.span>
      ))}
    </div>
  );
}
