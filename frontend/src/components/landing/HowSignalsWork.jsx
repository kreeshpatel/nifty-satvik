import { useEffect, useRef, useState } from "react";
import { motion, useInView, useScroll, useTransform, useMotionValue, useSpring } from "framer-motion";
import { Database, Layers, Brain, Target, ShieldCheck } from "lucide-react";
import SplitText from "@/components/landing/SplitText";
import { Aurora } from "@/components/shared/Aurora";
import { GlowOrb } from "@/components/shared/GlowOrb";

const steps = [
  {
    icon: Database,
    title: "Daily NSE data ingestion",
    description:
      "Every trading day we pull EOD prices and volume for the whole Nifty 500, plus live macro and sector context — the same data the backtest runs on, so what we measure is what we serve.",
  },
  {
    icon: Layers,
    title: "79 model features",
    description:
      "Each stock is enriched into 79 features — momentum and volatility, macro regime, sector strength, and cross-sectional relative-strength ranks. All point-in-time, no lookahead.",
  },
  {
    icon: Brain,
    title: "Two-head LightGBM scoring",
    description:
      "A two-head LightGBM scores every stock daily — one head predicts the size of the move, the other its confidence. The target is a +4% move within a ~14-day swing window.",
  },
  {
    icon: ShieldCheck,
    title: "Quality filter + regime check",
    description:
      "Only signals above quality threshold and aligned with the current market regime (BULL/BEAR/SIDEWAYS) make it to your dashboard.",
  },
  {
    icon: Target,
    title: "Trade plan + risk mgmt",
    description:
      "Each signal ships with a precomputed entry, stop-loss, and target — sized to your portfolio so risk per trade stays bounded.",
  },
];

// Simple media query hook
function useMediaQuery(query) {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e) => setMatches(e.matches);
    mql.addEventListener?.("change", handler);
    return () => mql.removeEventListener?.("change", handler);
  }, [query]);
  return matches;
}

// ============================================================
// Stage visuals
// ============================================================

const TICKERS = [
  ["RELIANCE", "2845.20", "+1.4%", true],
  ["INFY", "1632.55", "+0.8%", true],
  ["HDFCBANK", "1582.10", "-0.3%", false],
  ["TCS", "3920.40", "+2.1%", true],
  ["ICICIBANK", "1245.80", "+0.6%", true],
  ["KOTAKBANK", "1745.30", "-0.5%", false],
  ["LT", "3580.90", "+1.2%", true],
  ["SBIN", "812.45", "+0.9%", true],
  ["AXISBANK", "1108.20", "-0.2%", false],
  ["ITC", "458.30", "+0.4%", true],
  ["BHARTIARTL", "1632.00", "+1.8%", true],
  ["WIPRO", "542.80", "-0.6%", false],
];

const StageDataIngestion = ({ active }) => (
  <div className="w-full rounded-xl border border-white/[0.08] bg-white/[0.02] p-5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]">
    <div className="flex items-center justify-between mb-4">
      <span className="text-[10px] font-mono tracking-wider text-[color:var(--text-3)] uppercase">NSE Universe Feed</span>
      <span className="flex items-center gap-1 text-[10px] font-mono text-[color:var(--bull)]">
        <span className="w-1 h-1 rounded-full bg-[color:var(--bull)] animate-pulse" /> STREAMING
      </span>
    </div>
    <div className="space-y-1.5 max-h-[280px] overflow-hidden">
      {TICKERS.map(([sym, px, chg, up], i) => (
        <motion.div
          key={sym}
          initial={{ opacity: 0, x: -10 }}
          animate={active ? { opacity: 1, x: 0 } : { opacity: 0 }}
          transition={{ duration: 0.3, delay: i * 0.05 }}
          className="flex items-center justify-between text-[11px] font-mono py-1.5 px-2 rounded border border-transparent hover:border-white/[0.04]"
        >
          <span className="text-[color:var(--text-2)]">{sym}</span>
          <div className="flex items-center gap-3 tabular-nums">
            <span className="text-white">{px}</span>
            <motion.span
              animate={active ? { opacity: [0.6, 1, 0.6] } : { opacity: 0 }}
              transition={{ duration: 2, delay: i * 0.1, repeat: Infinity }}
              className={up ? "text-[color:var(--bull)] w-12 text-right" : "text-[color:var(--bear)] w-12 text-right"}
            >
              {chg}
            </motion.span>
          </div>
        </motion.div>
      ))}
    </div>
  </div>
);

const FEATURES = [
  ["RSI_14", 0.95],
  ["VOL_RATIO", 0.88],
  ["MOMENTUM_5D", 0.82],
  ["BB_WIDTH", 0.74],
  ["MACD_HIST", 0.68],
  ["SECTOR_REL", 0.61],
  ["BREADTH", 0.55],
  ["VIX_REGIME", 0.48],
  ["RS_RANK", 0.42],
  ["ATR_PCT", 0.36],
];

const StageFeatures = ({ active }) => (
  <div className="w-full rounded-xl border border-white/[0.08] bg-white/[0.02] p-5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]">
    <div className="flex items-center justify-between mb-5">
      <span className="text-[10px] font-mono tracking-wider text-[color:var(--text-3)] uppercase">Feature Importance</span>
      <span className="text-[10px] font-mono text-[color:var(--brand)]">79 FEATURES</span>
    </div>
    <div className="space-y-2.5">
      {FEATURES.map(([name, val], i) => (
        <div key={name} className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-[color:var(--text-3)] w-20 text-right">{name}</span>
          <div className="flex-1 h-2 rounded-full bg-white/[0.04] overflow-hidden">
            <motion.div
              initial={{ scaleX: 0 }}
              animate={active ? { scaleX: val } : { scaleX: 0 }}
              transition={{ duration: 0.8, delay: i * 0.06, ease: [0.65, 0.05, 0, 1] }}
              className="h-full origin-left"
              style={{ background: "var(--brand)" }}
            />
          </div>
          <span className="text-[10px] font-mono text-white w-10 tabular-nums">{val.toFixed(2)}</span>
        </div>
      ))}
    </div>
  </div>
);

const StageMLScoring = ({ active }) => {
  const target = 0.93;
  const motionVal = useMotionValue(0);
  const spring = useSpring(motionVal, { stiffness: 60, damping: 20 });
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const unsub = spring.on("change", (v) => setDisplay(v));
    return unsub;
  }, [spring]);

  useEffect(() => {
    if (active) motionVal.set(target);
    else motionVal.set(0);
  }, [active, motionVal]);

  // Circle params
  const R = 80;
  const C = 2 * Math.PI * R;
  const offset = C - display * C;

  return (
    <div className="w-full rounded-xl border border-white/[0.08] bg-white/[0.02] p-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)] flex flex-col items-center">
      <div className="text-[10px] font-mono tracking-wider text-[color:var(--text-3)] uppercase mb-4">
        ML Confidence Score
      </div>
      <div className="relative">
        <svg width="200" height="200" viewBox="0 0 200 200">
          <defs>
            <linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#4F8CFF" />
              <stop offset="100%" stopColor="#6DA1FF" />
            </linearGradient>
          </defs>
          <circle cx="100" cy="100" r={R} stroke="rgba(255,255,255,0.06)" strokeWidth="10" fill="none" />
          <circle
            cx="100"
            cy="100"
            r={R}
            stroke="url(#scoreGrad)"
            strokeWidth="10"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={C}
            strokeDashoffset={offset}
            transform="rotate(-90 100 100)"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="font-heading font-bold text-5xl text-white tabular-nums">
            {display.toFixed(2)}
          </div>
          <div className="text-[10px] font-mono text-[color:var(--bull)] mt-1">PROBABILITY</div>
        </div>
      </div>
      <div className="mt-4 text-[11px] font-mono text-[color:var(--text-3)] text-center">
        Two-head LightGBM · 79 features<br />
        Only ≥ 0.92 confidence becomes a signal
      </div>
    </div>
  );
};

const CANDIDATES = [
  ["RELIANCE", 0.95, true],
  ["INFY", 0.93, true],
  ["TCS", 0.92, true],
  ["HDFCBANK", 0.62, false, "Below threshold"],
  ["WIPRO", 0.55, false, "Below threshold"],
  ["KOTAKBANK", 0.71, false, "Bear regime mismatch"],
  ["AXISBANK", 0.68, false, "Bear regime mismatch"],
  ["ITC", 0.59, false, "Below threshold"],
];

const StageQualityFilter = ({ active }) => (
  <div className="w-full rounded-xl border border-white/[0.08] bg-white/[0.02] p-5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]">
    <div className="flex items-center justify-between mb-4">
      <span className="text-[10px] font-mono tracking-wider text-[color:var(--text-3)] uppercase">Quality Filter</span>
      <span className="text-[10px] font-mono text-[color:var(--bull)]">3 / 8 PASSED</span>
    </div>
    <div className="space-y-1.5">
      {CANDIDATES.map(([sym, score, passed, reason], i) => (
        <motion.div
          key={sym}
          initial={{ opacity: 0, x: -10 }}
          animate={active ? { opacity: 1, x: 0 } : { opacity: 0 }}
          transition={{ duration: 0.4, delay: i * 0.08 }}
          className={`flex items-center justify-between text-[11px] font-mono py-2 px-3 rounded border ${
            passed
              ? "border-[color:var(--bull)]/[0.3] bg-[color:var(--bull)]/[0.06]"
              : "border-[color:var(--edge-1)] bg-[color:var(--surface-2)]"
          }`}
        >
          <span className={passed ? "text-white" : "text-[color:var(--text-3)] line-through"}>{sym}</span>
          <div className="flex items-center gap-3">
            <span className={passed ? "text-[color:var(--bull)] tabular-nums" : "text-[color:var(--text-3)] tabular-nums"}>
              {score.toFixed(2)}
            </span>
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={active ? { opacity: 1, scale: 1 } : { opacity: 0 }}
              transition={{ duration: 0.3, delay: i * 0.08 + 0.3 }}
              className={`text-[9px] px-2 py-0.5 rounded ${
                passed
                  ? "bg-[color:var(--bull)]/[0.15] text-[color:var(--bull)]"
                  : "bg-[color:var(--bear)]/[0.12] text-[color:var(--bear)]"
              }`}
            >
              {passed ? "PASSED" : reason}
            </motion.span>
          </div>
        </motion.div>
      ))}
    </div>
  </div>
);

const StageTradePlan = ({ active }) => {
  // Simple mini chart with horizontal lines
  return (
    <div className="w-full rounded-xl border border-white/[0.08] bg-white/[0.02] p-5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-[10px] font-mono tracking-wider text-[color:var(--text-3)] uppercase">RELIANCE · BUY</div>
          <div className="font-heading font-bold text-2xl text-white mt-1 tabular-nums">₹2,845.20</div>
        </div>
        <div className="text-right">
          <div className="text-[9px] font-mono text-[color:var(--text-3)]">RR</div>
          <div className="text-sm font-mono text-[color:var(--bull)]">2.8 : 1</div>
        </div>
      </div>
      <div className="relative h-44 rounded-lg bg-white/[0.01] border border-white/[0.04] overflow-hidden">
        <svg viewBox="0 0 300 180" className="w-full h-full">
          {/* Target line */}
          <motion.line
            x1="0" x2="300" y1="35" y2="35"
            stroke="#72C766" strokeWidth="1.2" strokeDasharray="4 3"
            initial={{ pathLength: 0 }}
            animate={active ? { pathLength: 1 } : { pathLength: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          />
          {/* Entry line */}
          <motion.line
            x1="0" x2="300" y1="95" y2="95"
            stroke="#4F8CFF" strokeWidth="1.2" strokeDasharray="4 3"
            initial={{ pathLength: 0 }}
            animate={active ? { pathLength: 1 } : { pathLength: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          />
          {/* Stop line */}
          <motion.line
            x1="0" x2="300" y1="140" y2="140"
            stroke="oklch(66% 0.21 25)" strokeWidth="1.2" strokeDasharray="4 3"
            initial={{ pathLength: 0 }}
            animate={active ? { pathLength: 1 } : { pathLength: 0 }}
            transition={{ duration: 0.8, delay: 0.7 }}
          />
          {/* Candle path mock */}
          <motion.path
            d="M 20 110 L 50 100 L 80 105 L 110 95 L 140 90 L 170 85 L 200 75 L 230 65 L 260 50 L 285 40"
            stroke="url(#tradeGrad)"
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={active ? { pathLength: 1 } : { pathLength: 0 }}
            transition={{ duration: 1.2, delay: 0.9 }}
          />
          <defs>
            <linearGradient id="tradeGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#4F8CFF" />
              <stop offset="100%" stopColor="#72C766" />
            </linearGradient>
          </defs>
          {/* Labels */}
          <text x="295" y="32" fontSize="9" fill="#72C766" textAnchor="end" fontFamily="monospace">TARGET ₹2,965</text>
          <text x="295" y="92" fontSize="9" fill="#4F8CFF" textAnchor="end" fontFamily="monospace">ENTRY ₹2,845</text>
          <text x="295" y="137" fontSize="9" fill="oklch(66% 0.21 25)" textAnchor="end" fontFamily="monospace">STOP ₹2,802</text>
        </svg>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-[10px] font-mono">
        <div className="text-center p-2 rounded bg-white/[0.02]">
          <div className="text-[color:var(--text-3)]">Risk</div>
          <div className="text-[color:var(--bear)] mt-0.5">1.5%</div>
        </div>
        <div className="text-center p-2 rounded bg-white/[0.02]">
          <div className="text-[color:var(--text-3)]">Reward</div>
          <div className="text-[color:var(--bull)] mt-0.5">4.2%</div>
        </div>
        <div className="text-center p-2 rounded bg-white/[0.02]">
          <div className="text-[color:var(--text-3)]">Size</div>
          <div className="text-white mt-0.5">35 sh</div>
        </div>
      </div>
    </div>
  );
};

const STAGE_VISUALS = [StageDataIngestion, StageFeatures, StageMLScoring, StageQualityFilter, StageTradePlan];

// ============================================================
// Stage shell — used by both desktop horizontal and mobile fallback
// ============================================================

function Stage({ step, index, active }) {
  const Visual = STAGE_VISUALS[index];
  return (
    <div className="w-screen h-screen flex-shrink-0 flex items-center px-8 lg:px-24">
      <div className="w-full grid lg:grid-cols-[1fr_1.2fr] gap-16 items-center">
        {/* Left: editorial text */}
        <div>
          <div className="flex items-center gap-4 mb-10">
            <span
              className="font-mono"
              style={{
                fontSize: 13,
                letterSpacing: "0.18em",
                color: "var(--brand)",
                fontWeight: 600,
              }}
            >
              {String(index + 1).padStart(2, "0")} / 05
            </span>
            <div
              className="h-px w-16"
              style={{ background: "var(--edge-2)" }}
            />
          </div>
          <h3
            className="font-heading mb-6"
            style={{
              fontWeight: 600,
              color: "var(--text-1)",
              fontSize: "clamp(36px, 4.5vw, 60px)",
              lineHeight: 1.05,
              letterSpacing: "-0.025em",
              margin: 0,
              marginBottom: 22,
            }}
          >
            {step.title}
          </h3>
          <p
            style={{
              fontSize: 17,
              lineHeight: 1.6,
              color: "var(--text-2)",
              maxWidth: 520,
              margin: 0,
            }}
          >
            {step.description}
          </p>
        </div>
        {/* Right: visual — fills available space */}
        <div className="flex justify-center lg:justify-end">
          <div className="w-full max-w-xl">
            <Visual active={active} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Mobile / reduced-motion fallback — vertical card list
// ============================================================

function MobileFallback() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section className="relative py-24 md:py-32">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[400px] h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />

      <div className="absolute top-16 left-8 lg:left-16 section-number opacity-100 hidden md:block">
        03
      </div>

      <div className="max-w-5xl mx-auto px-6 lg:px-8 relative">
        <div ref={ref} className="text-center mb-16">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.4 }}
            className="inline-block font-mono text-xs tracking-[0.2em] text-[color:var(--brand)] uppercase mb-4"
          >
            Under the hood
          </motion.span>
          <SplitText
            text="How every signal is generated"
            className="font-heading font-bold text-3xl sm:text-4xl md:text-5xl tracking-tight text-white mb-3 block"
            delay={0.1}
          />
          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="text-sm text-[color:var(--text-2)] max-w-xl mx-auto mt-4"
          >
            No black box. No tipster guesses. Every signal goes through the same
            5-stage pipeline — fully transparent, fully testable.
          </motion.p>
        </div>

        <div className="space-y-3">
          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="flex items-start gap-5 p-5 rounded-xl border border-white/[0.06] bg-white/[0.02]"
              >
                <div className="flex-shrink-0">
                  <span
                    className="font-mono"
                    style={{
                      fontSize: 11,
                      letterSpacing: "0.16em",
                      color: "var(--brand)",
                      fontWeight: 600,
                    }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <div className="flex-1 pt-1">
                  <h3
                    className="font-heading"
                    style={{
                      fontWeight: 600,
                      color: "var(--text-1)",
                      fontSize: 18,
                      letterSpacing: "-0.01em",
                      margin: 0,
                      marginBottom: 6,
                    }}
                  >
                    {step.title}
                  </h3>
                  <p style={{ color: "var(--text-2)", fontSize: 14, lineHeight: 1.55, margin: 0 }}>
                    {step.description}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ============================================================
// Desktop pinned horizontal scroll
// ============================================================

function DesktopHorizontal() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });

  // Move container from 0 to -80% (4 stages × 20% = 80% leftover for last stage)
  const x = useTransform(scrollYProgress, [0, 1], ["0%", "-80%"]);

  // Active stage index — 0-4
  const [activeStage, setActiveStage] = useState(0);
  useEffect(() => {
    const unsub = scrollYProgress.on("change", (v) => {
      // Map progress 0..1 to stage 0..4
      const idx = Math.min(steps.length - 1, Math.floor(v * steps.length));
      setActiveStage(idx);
    });
    return unsub;
  }, [scrollYProgress]);

  return (
    <section ref={ref} className="relative" style={{ height: `${steps.length * 100}vh` }}>
      <div className="sticky top-0 h-screen overflow-hidden flex items-center" style={{ background: "var(--surface-0)" }}>
        {/* Atmospheric stage — Aurora wash + soft amber orb anchored at
            the center horizon so the scroll-pinned stage feels lit, not
            empty. Sits under all step content (zIndex 0). */}
        <Aurora tone="brand" intensity={0.55} style={{ zIndex: 0 }} />
        <GlowOrb tone="brand" size={760} x="50%" y="55%" blur={170} pulse style={{ zIndex: 0, opacity: 0.55 }} />
        <GlowOrb tone="info"  size={400} x="12%" y="30%" blur={120} style={{ zIndex: 0, opacity: 0.4 }} />

        {/* Top divider */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[400px] h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />

        {/* Big editorial section number */}
        <div className="absolute top-16 right-8 lg:right-16 section-number opacity-100 hidden md:block z-10 pointer-events-none">
          03
        </div>

        {/* Section label top-left */}
        <div className="absolute top-12 left-8 lg:left-24 z-10 pointer-events-none">
          <div
            className="font-mono uppercase"
            style={{
              fontSize: 11,
              letterSpacing: "0.18em",
              color: "var(--text-3)",
            }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
              style={{ background: "var(--brand)" }}
            />
            05 · Under the hood
          </div>
          <h2
            className="font-heading mt-2"
            style={{
              fontWeight: 600,
              color: "var(--text-1)",
              fontSize: 22,
              letterSpacing: "-0.015em",
              margin: 0,
              marginTop: 8,
            }}
          >
            How every signal is generated
          </h2>
        </div>

        {/* Horizontal track */}
        <motion.div
          style={{ x, width: `${steps.length * 100}vw` }}
          className="flex h-full items-center"
        >
          {steps.map((step, i) => (
            <Stage key={i} step={step} index={i} active={activeStage === i} />
          ))}
        </motion.div>

        {/* Progress dots — bottom center */}
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 flex items-center gap-3 z-10">
          {steps.map((_, i) => (
            <div
              key={i}
              className="h-2 rounded-full transition-all duration-500"
              style={{
                width: i === activeStage ? 48 : 8,
                background:
                  i === activeStage
                    ? "var(--brand)"
                    : i < activeStage
                      ? "var(--bull)"
                      : "var(--edge-2)",
                opacity: i < activeStage ? 0.6 : 1,
              }}
            />
          ))}
          <span className="ml-4 text-sm font-mono tracking-wider text-[color:var(--text-3)]">
            {String(activeStage + 1).padStart(2, "0")} / 05
          </span>
        </div>
      </div>
    </section>
  );
}

export default function HowSignalsWork() {
  // Always render the static stacked-card variant. The DesktopHorizontal
  // version was a scroll-pinned horizontal slide deck that read as
  // "sliding slides" — confusing UX on a marketing page. The mobile
  // fallback is the same content in a clean vertical list, which works
  // on every viewport.
  return <MobileFallback />;
}
