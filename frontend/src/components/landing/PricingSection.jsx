import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Check } from "lucide-react";
import MagneticButton from "@/components/landing/MagneticButton";
import { easeOutQuart, hoverLiftV2 } from "@/lib/motion";
import { Aurora } from "@/components/shared/Aurora";
import { GlowOrb } from "@/components/shared/GlowOrb";

const PLANS = [
  {
    name: "Trial",
    price: "Free",
    period: "14 days",
    description: "Get started with core features.",
    features: [
      "Live market data feed",
      "Basic signal alerts",
      "Portfolio overview",
      "Community access",
    ],
    cta: "Start free trial",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "₹2,999",
    period: "/ month",
    description: "Full access for active traders.",
    features: [
      "All Trial features",
      "Pre-move signal engine",
      "Advanced P&L analytics",
      "Trade journal with tags",
      "Strategy backtesting",
      "Priority support",
    ],
    cta: "Get Pro access",
    highlighted: true,
  },
  {
    name: "Annual",
    price: "₹24,999",
    period: "/ year",
    description: "Save 30% on the monthly rate.",
    features: [
      "Everything in Pro",
      "Custom strategy builder",
      "API access",
      "1-on-1 onboarding call",
      "Early feature access",
      "Dedicated support",
    ],
    cta: "Go Annual",
    highlighted: false,
  },
];

function PricingCard({ plan, index, onRequestAccess, inView }) {
  const isPro = plan.highlighted;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.45, delay: index * 0.08, ease: easeOutQuart }}
      whileHover="hover"
      style={{
        position: "relative",
        background: "var(--surface-1)",
        border: `1px solid ${isPro ? "var(--brand-edge)" : "var(--edge-1)"}`,
        borderRadius: "var(--r-card)",
        padding: 28,
        boxShadow: isPro
          ? "0 0 0 1px var(--brand-soft), var(--shadow-glow-md), var(--bloom-brand)"
          : "var(--shadow-sm), var(--bloom-brand)",
        overflow: "hidden",
      }}
    >
      <motion.div variants={hoverLiftV2} initial="rest" />
      {isPro && (
        <div
          className="font-mono uppercase"
          style={{
            position: "absolute",
            top: -10,
            left: 24,
            paddingInline: 10,
            paddingBlock: 3,
            background: "var(--brand)",
            color: "var(--brand-fg)",
            borderRadius: "var(--r-chip)",
            fontSize: 10,
            letterSpacing: "0.16em",
            fontWeight: 600,
          }}
        >
          Most picked
        </div>
      )}

      <div className="mb-7">
        <h3
          className="font-heading"
          style={{
            fontWeight: 600,
            color: "var(--text-1)",
            fontSize: 18,
            letterSpacing: "-0.005em",
            margin: 0,
            marginBottom: 6,
          }}
        >
          {plan.name}
        </h3>
        <p style={{ color: "var(--text-3)", fontSize: 13, margin: 0 }}>{plan.description}</p>
      </div>

      <div className="mb-7" style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <span
          className="font-heading"
          style={{
            fontWeight: 600,
            fontSize: 42,
            letterSpacing: "-0.03em",
            color: "var(--text-1)",
            fontVariantNumeric: "tabular-nums",
            lineHeight: 1,
          }}
        >
          {plan.price}
        </span>
        <span style={{ color: "var(--text-3)", fontSize: 13 }}>{plan.period}</span>
      </div>

      <ul style={{ margin: 0, padding: 0, listStyle: "none", marginBottom: 28 }}>
        {plan.features.map((feature) => (
          <li
            key={feature}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 13.5,
              color: "var(--text-2)",
              marginBottom: 10,
            }}
          >
            <Check size={14} strokeWidth={2.4} style={{ color: "var(--bull)", flexShrink: 0 }} />
            {feature}
          </li>
        ))}
      </ul>

      {isPro ? (
        <MagneticButton strength={0.2} className="block w-full">
          <button
            type="button"
            onClick={onRequestAccess}
            style={{
              width: "100%",
              height: 44,
              background: "var(--brand)",
              color: "var(--brand-fg)",
              borderRadius: "var(--r-chip)",
              border: "none",
              fontSize: 13.5,
              fontWeight: 600,
              cursor: "pointer",
              letterSpacing: "-0.005em",
            }}
          >
            {plan.cta}
          </button>
        </MagneticButton>
      ) : (
        <button
          type="button"
          onClick={onRequestAccess}
          style={{
            width: "100%",
            height: 44,
            background: "transparent",
            color: "var(--text-1)",
            borderRadius: "var(--r-chip)",
            border: "1px solid var(--edge-2)",
            fontSize: 13.5,
            fontWeight: 500,
            cursor: "pointer",
            letterSpacing: "-0.005em",
          }}
        >
          {plan.cta}
        </button>
      )}
    </motion.div>
  );
}

export default function PricingSection({ onRequestAccess }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      className="relative px-6 lg:px-12 overflow-hidden"
      style={{ paddingTop: 120, paddingBottom: 120 }}
    >
      {/* Section atmospheric backdrop — Aurora wash + a strong amber orb
          centered behind the Pro tier so the highlighted plan reads as
          back-lit. Two smaller orbs at the edges add stage depth. */}
      <Aurora tone="brand" intensity={0.85} style={{ zIndex: 0 }} />
      <GlowOrb tone="brand" size={780} x="50%" y="48%" blur={170} pulse style={{ zIndex: 0, opacity: 0.7 }} />
      <GlowOrb tone="info"  size={420} x="12%" y="72%" blur={120} style={{ zIndex: 0, opacity: 0.45 }} />
      <GlowOrb tone="bull"  size={420} x="88%" y="68%" blur={120} style={{ zIndex: 0, opacity: 0.35 }} />

      <div className="relative" style={{ maxWidth: 1280, marginInline: "auto", zIndex: 1 }} ref={ref}>
        <div className="mb-14 max-w-3xl">
          <div
            className="font-mono uppercase mb-3"
            style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
              style={{ background: "var(--brand)" }}
            />
            06 · Pricing
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
            One price. No tiers of edge.
          </motion.h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3" style={{ gap: 18, maxWidth: 1100 }}>
          {PLANS.map((plan, i) => (
            <PricingCard
              key={plan.name}
              plan={plan}
              index={i}
              onRequestAccess={onRequestAccess}
              inView={inView}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
