import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import RegimeStatement from "@/components/landing/RegimeStatement";
import MagneticButton from "@/components/landing/MagneticButton";
import { SignalCard } from "@/components/shared/SignalCard";
import { Aurora } from "@/components/shared/Aurora";
import { GlowOrb } from "@/components/shared/GlowOrb";
import { StageLight } from "@/components/shared/StageLight";
import { NumberTicker } from "@/components/shared/NumberTicker";
import { easeOutQuart } from "@/lib/motion";

const API = process.env.REACT_APP_API_URL ?? '';

/**
 * Sample anonymized signal — used by the SampleSignal section below the
 * hero. The ticker is a placeholder; visitors don't get actionable data,
 * members do. The SignalCard primitive is the same one that renders in
 * the dashboard, so the preview reads as the actual product.
 */
const DEMO_SIGNAL = {
  ticker: "SAMPLE",
  sector: "Capital Goods",
  status: "FRESH",
  grade: "A",
  ml_score: 0.94,
  v7_layers_agreeing: 5,
  entry: 1248.5,
  stop: 1192.3,
  target: 1342.1,
  stop_pct: -4.5,
  target_pct: 7.5,
  rr: 1.67,
  hold_days: 12,
  signal_date: "2026-04-25",
  current_price: 1257.2,
  v7_llm_rationale:
    "Breakout above the 50-day high with above-average volume; sector strength confirms the move.",
};

/**
 * Hero — centered, viewport-dominant headline. The page should command
 * attention the moment it loads: one big editorial statement, one calm
 * subtitle, two CTAs, nothing else. The product preview comes BELOW the
 * hero as its own deliberate beat (see SampleSignal export), not crammed
 * into the right column where it splits the eye.
 *
 * Animation budget: a single fade-up on each row, simultaneously. No
 * word-by-word stagger — at this size the headline must arrive whole.
 */
export default function Hero({ onRequestAccess }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/api/landing-stats`)
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled) setStats(d);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const bt = stats?.backtest;
  const cagr = bt?.cagr_pct ?? 31.1;
  const totalTrades = bt?.total_trades ?? 525;
  const periodStartYear = (() => {
    const period = bt?.period;
    if (typeof period === "string") {
      const m = period.match(/(\d{4})/);
      if (m) return m[1];
    }
    return "2020";
  })();

  return (
    <section
      className="relative px-6 lg:px-12 w-full flex flex-col items-center justify-center text-center overflow-hidden"
      style={{
        minHeight: "calc(100dvh - 100px)",
        paddingTop: "clamp(56px, 8vh, 110px)",
        paddingBottom: "clamp(48px, 6vh, 80px)",
        // Section stretches to viewport width; inner content elements
        // own their own max-widths (RegimeStatement: 14ch, body: 640px,
        // etc.) so the layout reads as edge-to-edge at any zoom level.
      }}
    >
      {/* Hero atmospheric stack — layered so depth reads as a real stage.
          1. Aurora: slow-breathing warm wash, the base atmosphere
          2. StageLight (top-left): the bright cone, like a key light
          3. StageLight (top-right): cooler-temp soft fill for depth
          4. GlowOrb behind headline: the main hero light source
          5. GlowOrb top edge: rim light that picks out the cursor grid

          All aria-hidden, zero pointer-events, mixBlendMode: screen so
          they stay translucent over the pure-black canvas. */}
      <Aurora tone="brand" intensity={1.1} style={{ zIndex: 0 }} />
      <StageLight tone="brand-strong" intensity={1.05} style={{ zIndex: 0 }} />
      <StageLight
        tone="info"
        intensity={0.55}
        style={{
          zIndex: 0,
          backgroundImage:
            'radial-gradient(70% 55% at 88% 14%, oklch(78% 0.11 230 / 0.18) 0%, oklch(78% 0.11 230 / 0.06) 28%, transparent 70%)',
        }}
      />
      <GlowOrb
        tone="brand"
        size={1100}
        x="50%"
        y="42%"
        blur={180}
        pulse
        style={{ zIndex: 0 }}
      />
      <GlowOrb
        tone="brand"
        size={420}
        x="18%"
        y="20%"
        blur={90}
        style={{ zIndex: 0, opacity: 0.7 }}
      />
      <GlowOrb
        tone="info"
        size={360}
        x="84%"
        y="28%"
        blur={100}
        style={{ zIndex: 0, opacity: 0.55 }}
      />
      {/* Bottom vignette — pulls focus to the headline by darkening the
          edge where the SampleSignal section begins. */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 220,
          background:
            'linear-gradient(to bottom, transparent 0%, oklch(0% 0 0 / 0.65) 80%, var(--surface-0) 100%)',
          zIndex: 0,
          pointerEvents: 'none',
        }}
      />

      {/* Content z-stack — everything below sits inside this relative
          wrapper so it paints above the absolute atmospheric layers. */}
      <div
        className="relative w-full flex flex-col items-center text-center"
        style={{ zIndex: 1 }}
      >

      {/* Eyebrow */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.05 }}
        className="font-mono uppercase mb-9"
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
        NiftyQuant · Pre-move detection for Indian equity
      </motion.div>

      {/* The headline — viewport-dominant. RegimeStatement renders the
          single editorial sentence at clamp(72px, 12vw, 200px). */}
      <RegimeStatement regime={2} />

      {/* Backtest metric strip — calm, mono, single line. NumberTicker
          counts the headline numbers up on first paint for a small but
          tangible "this is live" feel. */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.42, delay: 0.35, ease: easeOutQuart }}
        className="mt-10 font-mono"
        style={{ fontSize: 14, color: "var(--text-3)" }}
      >
        <NumberTicker
          value={Number(cagr)}
          decimals={1}
          suffix="%"
          duration={1300}
          style={{ color: "var(--text-1)", fontWeight: 600 }}
        />{" "}
        CAGR{" "}
        <span style={{ color: "var(--text-4)" }}>·</span>{" "}
        <NumberTicker
          value={Number(totalTrades)}
          decimals={0}
          duration={1500}
          formatter={(n) => Math.round(n).toLocaleString("en-IN")}
          style={{ color: "var(--text-1)", fontWeight: 600 }}
        />{" "}
        closed trades{" "}
        <span style={{ color: "var(--text-4)" }}>·</span>{" "}
        <span style={{ color: "var(--text-1)", fontWeight: 600 }}>
          since {periodStartYear}
        </span>
      </motion.div>

      {/* Body — single line, centered */}
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.42, delay: 0.45, ease: easeOutQuart }}
        className="mt-7"
        style={{
          color: "var(--text-2)",
          fontSize: 18,
          maxWidth: 640,
          lineHeight: 1.55,
          margin: "28px auto 0",
        }}
      >
        Every weekday at 4:15 PM IST, our LightGBM ensemble scores 441 stocks
        and surfaces only the few that earned a place.
      </motion.p>

      {/* CTAs */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.42, delay: 0.55, ease: easeOutQuart }}
        className="mt-12 flex items-center justify-center gap-6 flex-wrap"
      >
        <MagneticButton onClick={onRequestAccess}>
          <span
            className="inline-flex items-center justify-center gap-2 h-12 px-7 text-sm"
            style={{
              background: "var(--brand)",
              color: "var(--brand-fg)",
              borderRadius: "var(--r-chip)",
              fontWeight: 600,
              letterSpacing: "-0.005em",
            }}
          >
            Request access
            <ArrowUpRight size={15} strokeWidth={2.4} />
          </span>
        </MagneticButton>
        <Link
          to="/login"
          className="text-sm transition-opacity"
          style={{
            color: "var(--text-2)",
            textDecorationLine: "underline",
            textDecorationColor: "var(--edge-2)",
            textUnderlineOffset: 6,
            textDecorationThickness: 1,
          }}
        >
          Sign in
        </Link>
      </motion.div>
      </div>
    </section>
  );
}

/**
 * SampleSignal — the SignalCard demo, presented as its own deliberate
 * beat below the hero. Centered, calm, with a small caption above and a
 * disclosure below. Members see live tickers; visitors see the structure.
 */
export function SampleSignal() {
  return (
    <section
      className="relative px-6 lg:px-12 overflow-hidden"
      style={{ paddingTop: 24, paddingBottom: 96 }}
    >
      {/* Soft atmospheric halo behind the demo card so it feels intentional
          (a hero artifact) rather than floating in a void. Tone matches
          the FRESH info pulse on the card itself. */}
      <GlowOrb
        tone="info"
        size={680}
        x="50%"
        y="55%"
        blur={140}
        style={{ zIndex: 0, opacity: 0.45 }}
      />
      <div
        className="relative"
        style={{ maxWidth: 480, marginInline: "auto", zIndex: 1 }}
      >
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: easeOutQuart }}
        >
          <div
            className="font-mono uppercase mb-3 flex items-center gap-2 justify-center"
            style={{
              fontSize: 10,
              letterSpacing: "0.16em",
              color: "var(--text-3)",
            }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: "var(--info)" }}
            />
            Live preview · sample signal
          </div>
          <SignalCard signal={DEMO_SIGNAL} />
          <div
            className="font-mono mt-3 text-center"
            style={{
              fontSize: 10,
              color: "var(--text-4)",
              letterSpacing: "0.05em",
            }}
          >
            Members see live tickers · this preview is anonymized
          </div>
        </motion.div>
      </div>
    </section>
  );
}
