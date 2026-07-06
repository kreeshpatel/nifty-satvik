import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { easeOutQuart } from "@/lib/motion";
import { Aurora } from "@/components/shared/Aurora";
import { GlowOrb } from "@/components/shared/GlowOrb";

/**
 * Features — editorial capabilities list. The icon-above-heading admin
 * pattern is banned by .impeccable.md, so each feature is a numbered editorial
 * row: index in mono, headline in Geist, supporting body in muted.
 */
const FEATURES = [
  {
    n: "01",
    title: "Pre-move detection",
    body: "A two-head LightGBM scores 441 stocks across 79 features — technical, macro, sectoral. Both confidence and predicted return have to clear the gate before a signal goes live. Trained on 14 years of history (2010–2024) and validated walk-forward, no lookahead.",
  },
  {
    n: "02",
    title: "Native Kite integration",
    body: "One-click sync with your Zerodha Kite account. View holdings, place orders, and track fills inside Nifty Satvik. We hold no positions on your behalf — you sign every order.",
  },
  {
    n: "03",
    title: "Risk-first sizing",
    body: "Every signal carries an ATR-derived stop, an R:R-tuned target, and a volatility-scaled position size. Risk per trade is held near 3.5%, sector exposure capped at 30%, and the book holds at most 30 names. Drawdowns are observable, not surprises.",
  },
  {
    n: "04",
    title: "A decade of validation",
    body: "Every model and parameter change ships only after walk-forward validation across 2010–2024 history — and is then judged on live, out-of-sample trades from a fixed start date. Brokerage and STT are baked in. We don't tell you a strategy works — we show you the trades it would have made.",
  },
];

export default function Features() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      className="relative px-6 lg:px-12 overflow-hidden"
      style={{ paddingTop: 120, paddingBottom: 120 }}
    >
      {/* Section atmosphere — soft amber Aurora + two corner orbs framing
          the editorial 2-col grid. Quieter than Hero/Pricing since this
          section reads as content, not conversion. */}
      <Aurora tone="brand" intensity={0.55} style={{ zIndex: 0 }} />
      <GlowOrb tone="brand" size={520} x="8%"  y="22%" blur={150} style={{ zIndex: 0, opacity: 0.5 }} />
      <GlowOrb tone="info"  size={460} x="92%" y="78%" blur={140} style={{ zIndex: 0, opacity: 0.4 }} />

      <div className="relative" style={{ maxWidth: 1280, marginInline: "auto", zIndex: 1 }} ref={ref}>
        {/* Header */}
        <div className="mb-16 max-w-3xl">
          <div
            className="font-mono uppercase mb-3"
            style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
              style={{ background: "var(--brand)" }}
            />
            04 · What you get
          </div>
          <motion.h2
            initial={{ opacity: 0, y: 14 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.42, ease: easeOutQuart }}
            className="font-heading"
            style={{
              fontWeight: 600,
              color: "var(--text-1)",
              fontSize: "clamp(34px, 5vw, 64px)",
              lineHeight: 1.05,
              letterSpacing: "-0.025em",
              margin: 0,
            }}
          >
            A complete trading desk, not a Telegram channel.
          </motion.h2>
        </div>

        {/* Editorial rows */}
        <div className="grid lg:grid-cols-2" style={{ gap: 32, rowGap: 56 }}>
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.n}
              initial={{ opacity: 0, y: 16 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: i * 0.06, ease: easeOutQuart }}
              style={{
                paddingTop: 24,
                borderTop: "1px solid var(--edge-1)",
              }}
            >
              <div
                className="font-mono mb-4"
                style={{
                  fontSize: 11,
                  letterSpacing: "0.16em",
                  color: "var(--brand)",
                }}
              >
                {f.n}
              </div>
              <h3
                className="font-heading"
                style={{
                  fontWeight: 600,
                  color: "var(--text-1)",
                  fontSize: 26,
                  lineHeight: 1.15,
                  letterSpacing: "-0.015em",
                  marginBottom: 14,
                  marginTop: 0,
                }}
              >
                {f.title}
              </h3>
              <p
                style={{
                  color: "var(--text-2)",
                  fontSize: 15,
                  lineHeight: 1.6,
                  margin: 0,
                  maxWidth: 520,
                }}
              >
                {f.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
