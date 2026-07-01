import { motion } from "framer-motion";
import { ArrowRight, Play } from "lucide-react";
import DashboardMockup from "./DashboardMockup";

/**
 * HeroV3 — fxreplay-inspired hero. Centered single column.
 *
 * Order:
 *   - badge pill
 *   - giant headline (accent on the second half)
 *   - one-line sub
 *   - primary + ghost CTA row
 *   - 441 / 0.92 / 4:15 PM proof stats
 *   - DashboardMockup (flat, no rotation, no perspective)
 *
 * No SplitText, no per-word stagger, nothing slides. Each block fades
 * up with a small delay offset (~100ms) via framer-motion.
 */

const fade = (delay = 0) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] },
});

export default function HeroV3({ onRequestAccess }) {
  return (
    <section
      className="relative overflow-hidden"
      style={{
        background: "var(--surface-0)",
        paddingTop: "clamp(80px, 12vh, 140px)",
        paddingBottom: "clamp(48px, 8vh, 96px)",
      }}
    >
      {/* Radial brand glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0"
        style={{
          height: "120vh",
          background:
            "radial-gradient(ellipse 1600px 900px at 50% -12%, rgba(79, 140, 255, 0.18), rgba(79, 140, 255, 0.04) 38%, transparent 64%)",
        }}
      />
      {/* SVG hairlines fanning down from the top */}
      <svg
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 mx-auto"
        width="100%"
        height="520"
        viewBox="0 0 1440 520"
        preserveAspectRatio="none"
        style={{ opacity: 0.18, mixBlendMode: "screen" }}
      >
        {[...Array(11)].map((_, i) => (
          <line
            key={i}
            x1={720}
            y1={-20}
            x2={120 + i * 120}
            y2={540}
            stroke="url(#hero-line-grad)"
            strokeWidth="1"
          />
        ))}
        <defs>
          <linearGradient id="hero-line-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4F8CFF" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#4F8CFF" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>

      <div
        className="relative mx-auto"
        style={{
          maxWidth: 1200,
          padding: "0 clamp(20px, 4vw, 56px)",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr)",
            gap: "clamp(48px, 8vh, 88px)",
            textAlign: "center",
            alignItems: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <motion.div {...fade(0)} className="hero-v3-badge">
              <span className="dot" />
              <span>Built for Nifty 500 · Live since 2024</span>
            </motion.div>

            <motion.h1
              {...fade(0.1)}
              className="hero-v3-headline font-heading"
            >
              Quant signals for the{" "}
              <span className="hero-v3-accent">Nifty 500.</span>
            </motion.h1>

            <motion.p {...fade(0.22)} className="hero-v3-sub">
              An AI model scores 441 Indian stocks every weekday. The few that
              clear a 0.92 confidence floor become signals at 4:15 PM IST. Most
              days that's one stock. Some days it's none. Either way, the model
              decides &mdash; not us.
            </motion.p>

            <motion.div {...fade(0.34)} className="hero-v3-cta-row">
              <button
                type="button"
                className="hero-v3-btn hero-v3-btn-primary"
                onClick={onRequestAccess}
              >
                Request access
                <ArrowRight size={16} />
              </button>
              <button
                type="button"
                className="hero-v3-btn hero-v3-btn-ghost"
                onClick={() => {
                  const el = document.querySelector("#how-signals-work");
                  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                <Play size={14} fill="currentColor" />
                See how it works
              </button>
            </motion.div>

            <motion.div {...fade(0.46)} className="hero-v3-proof">
              <ProofStat value="441" label="stocks scanned" />
              <ProofDivider />
              <ProofStat value="0.92" label="confidence floor" />
              <ProofDivider />
              <ProofStat value="4:15 PM" label="IST daily" />
            </motion.div>
          </div>

          {/* Flat dashboard mockup directly below the copy. No rotation. */}
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.95, delay: 0.55, ease: [0.22, 1, 0.36, 1] }}
            className="hero-v3-screenshot"
          >
            <DashboardMockup />
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function ProofStat({ value, label }) {
  return (
    <div className="hero-v3-proof-stat">
      <div className="hero-v3-proof-value">{value}</div>
      <div className="hero-v3-proof-label">{label}</div>
    </div>
  );
}

function ProofDivider() {
  return (
    <span
      aria-hidden
      style={{
        width: 1,
        height: 32,
        background: "var(--edge-1)",
        margin: "0 clamp(16px, 3vw, 32px)",
      }}
    />
  );
}
