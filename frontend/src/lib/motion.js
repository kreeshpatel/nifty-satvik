// Shared framer-motion variants + easings for Nifty Satvik.
// Every page imports from here; inline variant definitions in feature components
// should migrate here over time.
//
// Token naming follows the liquid-glass system in src/styles/liquid-glass.css:
//   easeOut         = matches --spring-280 bezier
//   easeOutSofter   = matches --spring-350 bezier (barely-there overshoot)

export const easeOut = [0.2, 0.8, 0.2, 1];
export const easeOutSofter = [0.175, 0.885, 0.32, 1.05];

const DEFAULT_DELAY_STEP = 0.06;

export const fadeInUp = {
  hidden: { opacity: 0, y: 14 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: typeof i === 'number' ? i * DEFAULT_DELAY_STEP : 0,
      duration: 0.42,
      ease: easeOut,
    },
  }),
};

export const fadeIn = {
  hidden: { opacity: 0 },
  visible: (i = 0) => ({
    opacity: 1,
    transition: {
      delay: typeof i === 'number' ? i * DEFAULT_DELAY_STEP : 0,
      duration: 0.32,
      ease: easeOut,
    },
  }),
};

export const staggerContainer = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.04,
    },
  },
};

// Spring transitions — matched to liquid-glass curves, used on hover + tab indicators
export const springSlide = {
  type: 'spring',
  stiffness: 280,
  damping: 28,
  mass: 0.9,
};

export const springTight = {
  type: 'spring',
  stiffness: 420,
  damping: 32,
};

export const hoverLift = {
  rest: { y: 0, transition: springSlide },
  hover: { y: -2, transition: springTight },
};

// SVG path draw-in — used by equity curve, sector bars, etc.
export const drawIn = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: (i = 0) => ({
    pathLength: 1,
    opacity: 1,
    transition: {
      delay: typeof i === 'number' ? i * DEFAULT_DELAY_STEP : 0,
      duration: 1.1,
      ease: easeOut,
    },
  }),
};

// Bar growth — horizontal bar sweep from left, used by sector allocation
export const barGrow = {
  hidden: { scaleX: 0, transformOrigin: 'left center' },
  visible: (i = 0) => ({
    scaleX: 1,
    transformOrigin: 'left center',
    transition: {
      delay: 0.1 + (typeof i === 'number' ? i * 0.04 : 0),
      duration: 0.6,
      ease: easeOut,
    },
  }),
};

// ================================================================
// v2 — RETAIL-PRO CANONICAL SET (locked 2026-04-24)
//
// Six variants, every new component imports from this section. The
// legacy exports above (fadeInUp, fadeIn, staggerContainer, hoverLift,
// drawIn, barGrow) remain in place for existing components until they
// migrate in later plan phases — do NOT add new usages of them.
//
// Rationale for the six-variant cap is in ~/.claude/plans/we-need-to-
// highly-streamed-bengio.md §4 and /.impeccable.md.
// ================================================================

export const easeOutQuart = [0.25, 1, 0.5, 1];
export const easeOutCubic = [0.33, 1, 0.68, 1];
export const easePanel    = [0.32, 0.72, 0, 1];

// 1. PAGE ENTRY — route mount, first paint. Stagger caps at 6 so long
//    lists don't feel laggy; anything past 6 snaps to visible instantly.
export const pageEnter = {
  hidden: { opacity: 0, y: 8 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: typeof i === 'number' ? Math.min(i, 5) * 0.06 : 0,
      duration: 0.32,
      ease: easeOutQuart,
    },
  }),
};

export const pageEnterStagger = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06, delayChildren: 0 },
  },
};

// 2. HOVER LIFT — interactive card surface. y -2 is small enough to
//    feel alive without drawing the eye during scanning. The shadow
//    transition is handled via CSS var --shadow-sm -> --shadow-md on
//    the component; this variant only moves the y axis.
export const hoverLiftV2 = {
  rest:  { y: 0,  transition: { duration: 0.18, ease: easeOutCubic } },
  hover: { y: -2, transition: { duration: 0.18, ease: easeOutCubic } },
};

// 3. PRESS — button / chip. Scale 0.97 is the Apple HIG default for
//    tap feedback; anything smaller feels ignored, anything bigger
//    feels toy-like.
export const press = {
  rest:  { scale: 1 },
  press: { scale: 0.97, transition: { duration: 0.1, ease: 'easeOut' } },
};

// 4. NUMBER TICK — flash on value change from WS. Kept under reduced-
//    motion because disappearance/reappearance opacity is a primary
//    comprehension signal for updated values.
export const numberTick = {
  initial: { opacity: 0.4 },
  animate: { opacity: 1, transition: { duration: 0.14, ease: easeOutQuart } },
};

// 5. PANEL SLIDE — drawer open/close. The easePanel curve is iOS
//    share-sheet / Linear drawer shape: fast start, gentle settle,
//    no overshoot.
export const panelSlide = {
  closed: { x: '100%', transition: { duration: 0.28, ease: easePanel } },
  open:   { x: 0,      transition: { duration: 0.28, ease: easePanel } },
};

// 6. LIVE PULSE — the ONLY sustained animation permitted. Used on the
//    6px WS-connected indicator dot in the header footer. Every other
//    "pulsing" / "breathing" effect in the codebase gets removed.
export const livePulse = {
  animate: {
    opacity: [0.6, 1, 0.6],
    transition: { duration: 2.2, ease: 'easeInOut', repeat: Infinity },
  },
};
