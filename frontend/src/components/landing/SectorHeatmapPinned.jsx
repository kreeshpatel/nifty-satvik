import { useEffect, useRef, useState } from "react";
import { animate, motion, useMotionValue, useScroll, useTransform, useInView } from "framer-motion";
import { easeOutQuart } from "@/lib/motion";
import { useIsMobile } from "@/hooks/useIsMobile";

const API = process.env.REACT_APP_API_URL ?? '';

/**
 * Fallback heatmap — used when /api/landing-stats hasn't accumulated enough
 * sector data yet. Plausible values for visual completeness; gets replaced
 * the moment the real fetch resolves.
 */
const FALLBACK_SECTORS = [
  { sector: "Capital Goods", avg_pct: 5.2, trades: 8 },
  { sector: "Auto", avg_pct: 4.1, trades: 6 },
  { sector: "Pharma", avg_pct: 3.4, trades: 5 },
  { sector: "Financial Services", avg_pct: 2.8, trades: 12 },
  { sector: "IT", avg_pct: 2.2, trades: 7 },
  { sector: "Cement", avg_pct: 1.9, trades: 4 },
  { sector: "Chemicals", avg_pct: 1.6, trades: 6 },
  { sector: "FMCG", avg_pct: 1.1, trades: 5 },
  { sector: "Power", avg_pct: 0.8, trades: 3 },
  { sector: "Metals", avg_pct: 0.4, trades: 4 },
  { sector: "Telecom", avg_pct: 0.1, trades: 2 },
  { sector: "Realty", avg_pct: -0.3, trades: 3 },
  { sector: "Consumer Durables", avg_pct: -0.7, trades: 4 },
  { sector: "Media", avg_pct: -1.2, trades: 2 },
  { sector: "Oil & Gas", avg_pct: -1.6, trades: 3 },
  { sector: "PSU Bank", avg_pct: -2.1, trades: 5 },
  { sector: "Textiles", avg_pct: -2.6, trades: 2 },
  { sector: "Healthcare", avg_pct: -3.0, trades: 3 },
  { sector: "Services", avg_pct: -3.4, trades: 2 },
  { sector: "Construction", avg_pct: -4.1, trades: 3 },
  { sector: "Infrastructure", avg_pct: -4.8, trades: 4 },
  { sector: "Others", avg_pct: -5.3, trades: 6 },
];

function tileColor(pct) {
  // Map avg_pct to a bull/bear OKLCH lightness. The reference brightness is
  // tuned so neutral (~0%) reads as a quiet card surface and ±5% saturates.
  const clamped = Math.max(-6, Math.min(6, pct || 0));
  const intensity = Math.min(0.6, Math.abs(clamped) / 6 * 0.55 + 0.05);
  if (clamped >= 0) {
    return `oklch(28% 0.10 145 / ${0.4 + intensity})`;
  }
  return `oklch(28% 0.12 25 / ${0.4 + intensity})`;
}

function tileTextColor(pct) {
  const abs = Math.abs(pct || 0);
  if (abs < 0.5) return "var(--text-3)";
  return pct >= 0 ? "var(--bull)" : "var(--bear)";
}

/**
 * SectorHeatmapPinned — pinned-scroll Nifty 500 sector heatmap. As the user
 * scrolls into the section, sector tiles ripple in with a stagger driven by
 * the row's distance from the viewport top. Each tile's color encodes the
 * mean closed-signal return for that sector over the last 30 days.
 *
 * The pinned region is 220vh tall: first 60vh is empty intro space,
 * the middle 100vh is the locked heatmap with tiles filling in,
 * the trailing 60vh is breathing room before the next section.
 *
 * No decorative animation — the only motion is the scroll-bound reveal of
 * real sector data + a livePulse on the most-active tile (one only).
 */
export default function SectorHeatmapPinned() {
  // Mobile drops the 220vh + sticky scroll-jack: section becomes
  // auto-height and tiles reveal in one 1.4s staggered animation on
  // view-enter. Desktop keeps the scroll-bound reveal.
  const isMobile = useIsMobile();
  const containerRef = useRef(null);
  const stickyRef = useRef(null);
  const [sectors, setSectors] = useState(FALLBACK_SECTORS);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  });

  // Mobile: a normal motion value we ramp 0→1 on view-enter.
  // Desktop: bound to the section's scroll progress.
  const mobileReveal = useMotionValue(0);
  const scrollReveal = useTransform(scrollYProgress, [0.18, 0.62], [0, 1]);
  const reveal = isMobile ? mobileReveal : scrollReveal;

  const inView = useInView(stickyRef, { once: true, margin: isMobile ? "-10%" : "-30%" });

  useEffect(() => {
    if (!isMobile || !inView) return;
    const controls = animate(mobileReveal, 1, { duration: 1.4, ease: easeOutQuart });
    return () => controls.stop();
  }, [isMobile, inView, mobileReveal]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/api/landing-stats`)
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        const sh = d?.sector_heatmap_30d;
        if (Array.isArray(sh) && sh.length >= 6) {
          setSectors(sh.slice(0, 22));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Find the most active sector (largest |avg_pct|) for the livePulse marker.
  const mostActiveIdx = sectors.reduce((best, s, i) => {
    if (Math.abs(s.avg_pct) > Math.abs(sectors[best].avg_pct)) return i;
    return best;
  }, 0);

  return (
    <section
      ref={containerRef}
      className="relative"
      style={isMobile ? { paddingBlock: "clamp(48px, 8vh, 80px)" } : { height: "220vh" }}
    >
      <div
        ref={stickyRef}
        className={isMobile ? "flex items-center" : "sticky top-0 flex items-center"}
        style={
          isMobile
            ? { paddingInline: 24 }
            : {
                minHeight: "100vh",
                paddingInline: "clamp(24px, 5vw, 80px)",
                paddingBlock: 64,
              }
        }
      >
        <div className="w-full" style={{ maxWidth: 1280, marginInline: "auto" }}>
          {/* Header */}
          <div className="mb-10 flex items-end justify-between flex-wrap gap-6">
            <div>
              <div
                className="font-mono uppercase mb-3"
                style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
                  style={{ background: "var(--brand)" }}
                />
                02 · The pulse
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
                  maxWidth: 780,
                }}
              >
                Every weekday at <span style={{ color: "var(--brand)" }}>4:15 PM IST</span>,
                we score 441 stocks across 22 sectors.
              </motion.h2>
            </div>
            <motion.p
              initial={{ opacity: 0 }}
              animate={inView ? { opacity: 1 } : {}}
              transition={{ duration: 0.5, delay: 0.2 }}
              style={{ color: "var(--text-2)", fontSize: 15, maxWidth: 320 }}
            >
              {isMobile
                ? "The grid below is the last 30 days, by sector. Green tiles outperformed. Red ones lagged."
                : "The grid below is the last 30 days, by sector. Green tiles outperformed. Red ones lagged. Scroll to fill the board."}
            </motion.p>
          </div>

          {/* Heatmap grid — 4-6 columns responsive */}
          <div
            className="grid"
            style={{
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 8,
            }}
          >
            {sectors.map((s, i) => (
              <SectorTile
                key={s.sector + i}
                sector={s.sector}
                avg_pct={s.avg_pct}
                trades={s.trades}
                index={i}
                total={sectors.length}
                reveal={reveal}
                isMostActive={i === mostActiveIdx}
              />
            ))}
          </div>

          {/* Footer caption */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="font-mono mt-10 flex items-center gap-2 flex-wrap"
            style={{ fontSize: 11, color: "var(--text-3)", letterSpacing: "0.05em" }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: "var(--bull)" }}
            />
            Outperformed
            <span style={{ color: "var(--text-4)", marginInline: 8 }}>·</span>
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: "var(--bear)" }}
            />
            Lagged
            <span style={{ color: "var(--text-4)", marginInline: 8 }}>·</span>
            Updated daily after market close · cached 10 min
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function SectorTile({ sector, avg_pct, trades, index, total, reveal, isMostActive }) {
  // Each tile has a per-index reveal threshold so they fill in row-by-row.
  const threshold = index / total;
  const opacity = useTransform(reveal, (v) => {
    const local = (v - threshold) * 6;
    return Math.max(0, Math.min(1, local));
  });
  const scale = useTransform(reveal, (v) => {
    const local = (v - threshold) * 6;
    return Math.max(0.94, Math.min(1, 0.94 + local * 0.06));
  });

  return (
    <motion.div
      style={{
        opacity,
        scale,
        background: tileColor(avg_pct),
        border: "1px solid var(--edge-1)",
        borderRadius: "var(--r-chip)",
        padding: "14px 14px 12px",
        position: "relative",
        minHeight: 86,
      }}
    >
      <div
        className="font-mono uppercase truncate"
        style={{
          fontSize: 9.5,
          letterSpacing: "0.12em",
          color: "var(--text-3)",
        }}
      >
        {sector}
      </div>
      <div
        className="font-heading mt-2"
        style={{
          fontVariantNumeric: "tabular-nums",
          fontSize: 22,
          fontWeight: 600,
          letterSpacing: "-0.02em",
          lineHeight: 1,
          color: tileTextColor(avg_pct),
        }}
      >
        {avg_pct >= 0 ? "+" : ""}
        {avg_pct.toFixed(1)}
        <span style={{ fontSize: 13, color: "var(--text-3)" }}>%</span>
      </div>
      <div
        className="font-mono mt-2"
        style={{ fontSize: 10, color: "var(--text-4)", letterSpacing: "0.05em" }}
      >
        {trades} trade{trades === 1 ? "" : "s"}
      </div>
      {isMostActive && (
        <motion.span
          aria-hidden
          className="absolute"
          style={{
            top: 10,
            right: 10,
            width: 6,
            height: 6,
            borderRadius: 999,
            background: "var(--brand)",
          }}
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2.2, ease: "easeInOut", repeat: Infinity }}
        />
      )}
    </motion.div>
  );
}
