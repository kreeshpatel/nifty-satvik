import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { easeOutQuart } from "@/lib/motion";
import { GlowOrb } from "@/components/shared/GlowOrb";

/**
 * Founder moment — single signed paragraph. No fake "team" page, no bio
 * decorations. The avatar is initials in a brand-tinted square that doesn't
 * try to look like a person; it tries to look like a signature.
 */
export default function FounderSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      className="relative px-6 lg:px-12 overflow-hidden"
      style={{ paddingTop: 120, paddingBottom: 120 }}
    >
      {/* Single soft brand orb back-lighting the signed paragraph so the
          founder moment reads as personal warmth, not flat copy. */}
      <GlowOrb tone="brand" size={580} x="50%" y="50%" blur={160} style={{ zIndex: 0, opacity: 0.35 }} />

      <div className="relative" style={{ maxWidth: 760, marginInline: "auto", zIndex: 1 }} ref={ref}>
        <div
          className="font-mono uppercase mb-6"
          style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
            style={{ background: "var(--brand)" }}
          />
          07 · About
        </div>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.45, ease: easeOutQuart }}
          className="font-heading"
          style={{
            fontWeight: 500,
            color: "var(--text-1)",
            fontSize: "clamp(22px, 2.4vw, 30px)",
            lineHeight: 1.45,
            letterSpacing: "-0.012em",
            marginBottom: 36,
          }}
        >
          I built NiftyQuant because I wanted the tools institutions use, on the
          stocks I actually trade. Every signal you see, I take myself with my
          own capital. No paid promotions, no affiliate kickbacks, no Telegram
          channels. Just the model, the trades, and the receipts.
        </motion.div>

        <div className="flex items-center gap-4">
          <div
            className="font-heading flex items-center justify-center"
            style={{
              width: 44,
              height: 44,
              background: "var(--brand)",
              color: "var(--brand-fg)",
              borderRadius: "var(--r-chip)",
              fontWeight: 600,
              fontSize: 15,
              letterSpacing: "-0.01em",
            }}
          >
            KP
          </div>
          <div>
            <div
              className="font-heading"
              style={{
                fontWeight: 600,
                color: "var(--text-1)",
                fontSize: 14,
                letterSpacing: "-0.005em",
              }}
            >
              Kreesh Patel
            </div>
            <div
              className="font-mono uppercase mt-0.5"
              style={{ fontSize: 10, letterSpacing: "0.16em", color: "var(--text-3)" }}
            >
              Founder · Quant developer
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
