import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { motion, useScroll, useTransform, useInView, useMotionValueEvent } from "framer-motion";
import { easeOutQuart } from "@/lib/motion";
import { useIsMobile } from "@/hooks/useIsMobile";

const EquityShaderOverlay = lazy(() =>
  import("@/components/landing/EquityShaderOverlay")
);

const API = process.env.REACT_APP_API_URL ?? '';

/**
 * EquityCurve — pinned, scroll-bound equity curve from the production paper
 * portfolio (portfolio_history.csv, sampled to ~60 points by the backend).
 * The curve's pathLength is bound to scrollYProgress so it draws across the
 * viewport as the user scrolls.
 *
 * Three callouts auto-pin to the FIRST point, the curve's PEAK, and the
 * LATEST point. Their text is computed from the data, never hard-coded —
 * this means the page stays accurate when the strategy revalidator cron
 * publishes a new portfolio_history.csv (every quarter).
 *
 * Pinned region is 220vh:
 *   - first 60vh: intro headline fades in
 *   - middle 100vh: pinned, curve draws bound to scroll
 *   - trailing 60vh: hand-off space before next section
 */

// Fallback used when /api/landing-stats hasn't populated equity_curve yet
// (preview deploys, fresh boot before first cron). Same shape as the API
// payload — list of { date, return_pct }. Kept short so the curve still
// reads cleanly without API.
const FALLBACK_CURVE = [
  { date: "2022-01-03", return_pct: 0 },
  { date: "2022-06-02", return_pct: -7.4 },
  { date: "2023-01-04", return_pct: 12.5 },
  { date: "2023-09-15", return_pct: 28.0 },
  { date: "2024-04-22", return_pct: 54.3 },
  { date: "2024-10-07", return_pct: 81.7 },
  { date: "2025-03-14", return_pct: 65.2 },
  { date: "2025-09-18", return_pct: 52.1 },
  { date: "2026-03-24", return_pct: 43.2 },
];

// SVG canvas — viewBox matches the CSS box. y=320 baseline (~0%), y=20 top.
const VB_W = 1200;
const VB_H = 360;
const PAD_TOP = 30;
const PAD_BOT = 30;
const BASELINE_Y = VB_H - PAD_BOT;
const PLOT_H = VB_H - PAD_TOP - PAD_BOT;

function formatDate(iso) {
  if (!iso) return "—";
  const [y, m] = iso.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${months[parseInt(m, 10) - 1] || "?"} ${y}`;
}

function buildCurvePath(points) {
  if (!points.length) return { d: "", coords: [] };
  // Determine y-scale from the data's actual return range, padded a bit.
  const returns = points.map((p) => p.return_pct);
  const min = Math.min(...returns);
  const max = Math.max(...returns);
  const lo = Math.min(0, min - 4);
  const hi = max + 4;
  const range = hi - lo || 1;

  const coords = points.map((p, i) => {
    const x = (i / (points.length - 1)) * VB_W;
    const y = PAD_TOP + ((hi - p.return_pct) / range) * PLOT_H;
    return { x, y, ...p };
  });

  let d = `M ${coords[0].x.toFixed(2)} ${coords[0].y.toFixed(2)}`;
  for (let i = 1; i < coords.length; i++) {
    const px = coords[i - 1].x;
    const py = coords[i - 1].y;
    const cx = coords[i].x;
    const cy = coords[i].y;
    const midX = (px + cx) / 2;
    d += ` Q ${midX.toFixed(2)} ${py.toFixed(2)} ${cx.toFixed(2)} ${cy.toFixed(2)}`;
  }
  return { d, coords, lo, hi };
}

export default function EquityCurve() {
  // Mobile gets a static, no-scroll-jack layout: curve draws once on
  // view-enter, callouts stack below the chart, no 220vh sticky region.
  // Desktop keeps the scrollytelling rig.
  const isMobile = useIsMobile();
  if (isMobile) return <MobileEquityCurve />;
  return <DesktopEquityCurve />;
}

function DesktopEquityCurve() {
  const containerRef = useRef(null);
  const stickyRef = useRef(null);
  const inView = useInView(stickyRef, { once: true, margin: "-30%" });

  const [points, setPoints] = useState(FALLBACK_CURVE);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/api/landing-stats`)
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        const ec = d?.equity_curve;
        if (Array.isArray(ec) && ec.length >= 6) setPoints(ec);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const { d, coords } = useMemo(() => buildCurvePath(points), [points]);

  // Three callouts: start, peak, end.
  const callouts = useMemo(() => {
    if (!coords?.length) return [];
    const startIdx = 0;
    let peakIdx = 0;
    for (let i = 1; i < coords.length; i++) {
      if (coords[i].return_pct > coords[peakIdx].return_pct) peakIdx = i;
    }
    const endIdx = coords.length - 1;

    const peak = coords[peakIdx];
    const end = coords[endIdx];

    const callouts = [
      {
        coord: coords[startIdx],
        label: formatDate(coords[startIdx].date),
        body: "Paper portfolio go-live · ₹10L baseline",
      },
    ];
    if (peakIdx !== startIdx && peakIdx !== endIdx) {
      callouts.push({
        coord: peak,
        label: formatDate(peak.date),
        body: `Peak +${peak.return_pct.toFixed(1)}% return`,
      });
    }
    callouts.push({
      coord: end,
      label: formatDate(end.date),
      body: `Today · ${end.return_pct >= 0 ? "+" : ""}${end.return_pct.toFixed(1)}% cumulative`,
    });
    return callouts;
  }, [coords]);

  const finalReturn = coords.length ? coords[coords.length - 1].return_pct : 0;

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  });
  const pathLength = useTransform(scrollYProgress, [0.18, 0.74], [0, 1]);
  const finalOpacity = useTransform(scrollYProgress, [0.6, 0.78], [0, 1]);
  const finalY = useTransform(scrollYProgress, [0.6, 0.78], [10, 0]);

  // ── Shader overlay refs — mutated each scroll tick (no React re-renders) ──
  // Shader space is normalized 0..1 (origin top-left of the canvas, like UV).
  const progressRef = useRef(0);
  const penPosRef = useRef({ x: 0, y: 0.5 });
  const anchorsRef = useRef([
    { x: 0, y: 0.5 },
    { x: 0, y: 0.5 },
    { x: 0, y: 0.5 },
  ]);
  const anchorActiveRef = useRef([0, 0, 0]);
  const aspectRef = useRef(VB_W / VB_H);

  // Recompute anchor positions in shader UV space whenever the curve changes
  useEffect(() => {
    if (!callouts.length) return;
    callouts.slice(0, 3).forEach((c, i) => {
      anchorsRef.current[i] = {
        x: c.coord.x / VB_W,
        // Flip Y because shader UV's origin is bottom-left in WebGL
        y: 1 - c.coord.y / VB_H,
      };
    });
  }, [callouts]);

  // Subscribe to pathLength and update pen position + anchor activations.
  // Reading coords in this callback so it stays in sync with curve data.
  useMotionValueEvent(pathLength, "change", (latest) => {
    progressRef.current = latest;

    if (coords.length >= 2) {
      // Find the curve segment that latest progress lands in
      const t = Math.max(0, Math.min(1, latest));
      const seg = t * (coords.length - 1);
      const i = Math.floor(seg);
      const frac = seg - i;
      const a = coords[i];
      const b = coords[Math.min(i + 1, coords.length - 1)];
      const px = a.x + (b.x - a.x) * frac;
      const py = a.y + (b.y - a.y) * frac;
      penPosRef.current = {
        x: px / VB_W,
        y: 1 - py / VB_H,
      };
    }

    // Activate anchors whose threshold has been passed
    callouts.slice(0, 3).forEach((c, i) => {
      const threshold = c.coord.x / VB_W;
      anchorActiveRef.current[i] = latest >= threshold ? 1 : 0;
    });
  });

  return (
    <section
      ref={containerRef}
      className="relative"
      style={{ height: "220vh" }}
    >
      <div
        ref={stickyRef}
        className="sticky top-0 flex flex-col justify-center"
        style={{ minHeight: "100vh", paddingInline: "clamp(24px, 5vw, 80px)" }}
      >
        <div style={{ maxWidth: 1280, marginInline: "auto", width: "100%" }}>
          <div className="mb-8 flex items-end justify-between flex-wrap gap-6">
            <div>
              <div
                className="font-mono uppercase mb-3"
                style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
                  style={{ background: "var(--brand)" }}
                />
                03 · The curve
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
                Four years of paper portfolio. Scroll to draw the curve.
              </motion.h2>
            </div>
            <motion.div
              style={{
                background: "var(--surface-1)",
                border: "1px solid var(--edge-1)",
                borderRadius: "var(--r-card)",
                padding: "12px 18px",
                minWidth: 200,
              }}
            >
              <div
                className="font-mono uppercase mb-1"
                style={{ fontSize: 10, letterSpacing: "0.16em", color: "var(--text-3)" }}
              >
                Cumulative return
              </div>
              <motion.div
                style={{
                  opacity: finalOpacity,
                  y: finalY,
                  fontVariantNumeric: "tabular-nums",
                  fontSize: 36,
                  fontWeight: 600,
                  letterSpacing: "-0.025em",
                  color: finalReturn >= 0 ? "var(--bull)" : "var(--bear)",
                  fontFamily: "var(--font-heading, inherit)",
                  lineHeight: 1,
                }}
              >
                {finalReturn >= 0 ? "+" : ""}
                {finalReturn.toFixed(1)}%
              </motion.div>
            </motion.div>
          </div>

          <div
            style={{
              background: "var(--surface-1)",
              border: "1px solid var(--edge-1)",
              borderRadius: "var(--r-card)",
              padding: 24,
              position: "relative",
            }}
          >
            <div style={{ position: "relative" }}>
              <svg
                viewBox={`0 0 ${VB_W} ${VB_H}`}
                preserveAspectRatio="none"
                width="100%"
                style={{ display: "block", height: "clamp(220px, 42vw, 360px)" }}
              >
                <defs>
                  <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4F8CFF" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#4F8CFF" stopOpacity={0} />
                  </linearGradient>
                </defs>

                {/* Hairline grid */}
                {[0.25, 0.5, 0.75].map((p) => (
                  <line
                    key={p}
                    x1={0}
                    x2={VB_W}
                    y1={PAD_TOP + p * PLOT_H}
                    y2={PAD_TOP + p * PLOT_H}
                    stroke="var(--edge-1)"
                    strokeWidth={1}
                  />
                ))}
                <line
                  x1={0}
                  x2={VB_W}
                  y1={BASELINE_Y}
                  y2={BASELINE_Y}
                  stroke="var(--edge-2)"
                  strokeWidth={1}
                  strokeDasharray="3 4"
                />

                {/* Area fill — revealed by scaleX bound to scroll */}
                <motion.g
                  style={{ scaleX: pathLength, transformOrigin: "left center" }}
                >
                  <path
                    d={`${d} L ${VB_W} ${BASELINE_Y} L 0 ${BASELINE_Y} Z`}
                    fill="url(#equityFill)"
                  />
                </motion.g>

                {/* The curve itself */}
                <motion.path
                  d={d}
                  fill="none"
                  stroke="#4F8CFF"
                  strokeWidth={2.4}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ pathLength }}
                />

                {/* Callout dots */}
                {callouts.map((c, i) => (
                  <CalloutDot key={i} coord={c.coord} pathLength={pathLength} />
                ))}
              </svg>

              {/* WebGL shader overlay — bright pen glow at the current scroll
                  position + expanding ripple rings at each callout anchor. The
                  shader uses additive blending so it adds to the SVG below
                  rather than covering it. */}
              <Suspense fallback={null}>
                <EquityShaderOverlay
                  progressRef={progressRef}
                  penPosRef={penPosRef}
                  anchorsRef={anchorsRef}
                  anchorActiveRef={anchorActiveRef}
                  aspectRef={aspectRef}
                />
              </Suspense>

              {/* Callout text overlays — absolutely positioned by data x */}
              <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
                {callouts.map((c, i) => (
                  <CalloutCard
                    key={i}
                    coord={c.coord}
                    label={c.label}
                    body={c.body}
                    pathLength={pathLength}
                    align={i === 0 ? "left" : i === callouts.length - 1 ? "right" : "center"}
                  />
                ))}
              </div>
            </div>

            <div
              className="font-mono mt-4 flex items-center justify-between"
              style={{ fontSize: 10.5, color: "var(--text-4)", letterSpacing: "0.05em" }}
            >
              <span>{formatDate(coords[0]?.date)}</span>
              <span>{formatDate(coords[coords.length - 1]?.date)}</span>
            </div>
          </div>

          <p
            style={{
              fontSize: 11,
              color: "var(--text-4)",
              textAlign: "center",
              marginTop: 24,
              lineHeight: 1.5,
            }}
          >
            Equity curve from the production paper portfolio · sampled from the
            daily history file · past performance does not guarantee future returns.
          </p>
        </div>
      </div>
    </section>
  );
}

function CalloutDot({ coord, pathLength }) {
  const threshold = coord.x / VB_W;
  const opacity = useTransform(pathLength, (v) => (v >= threshold ? 1 : 0));
  const scale = useTransform(pathLength, (v) => (v >= threshold ? 1 : 0.4));
  return (
    <motion.circle
      cx={coord.x}
      cy={coord.y}
      r={5}
      fill="#4F8CFF"
      stroke="var(--surface-1)"
      strokeWidth={2.5}
      style={{ opacity, scale, transformOrigin: `${coord.x}px ${coord.y}px` }}
    />
  );
}

function CalloutCard({ coord, label, body, pathLength, align }) {
  const threshold = coord.x / VB_W + 0.02;
  const opacity = useTransform(pathLength, (v) => (v >= threshold ? 1 : 0));
  const y = useTransform(pathLength, (v) => (v >= threshold ? 0 : 6));
  const leftPct = (coord.x / VB_W) * 100;
  const verticalLift = -((BASELINE_Y - coord.y) / VB_H) * 360 - 96;

  let xTransform = "translateX(-50%)";
  if (align === "left") xTransform = "translateX(0)";
  if (align === "right") xTransform = "translateX(-100%)";

  return (
    <motion.div
      style={{
        position: "absolute",
        left: `${leftPct}%`,
        top: verticalLift,
        transform: xTransform,
        opacity,
        y,
        background: "var(--surface-2)",
        border: "1px solid var(--edge-2)",
        borderRadius: "var(--r-chip)",
        padding: "8px 12px",
        minWidth: "min(200px, 80vw)",
        maxWidth: "min(240px, 88vw)",
      }}
    >
      <div
        className="font-mono uppercase"
        style={{ fontSize: 10, letterSpacing: "0.12em", color: "var(--brand)" }}
      >
        {label}
      </div>
      <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 4, lineHeight: 1.4 }}>
        {body}
      </div>
    </motion.div>
  );
}

// ====================================================================
// MobileEquityCurve — no scroll-jack, no shader, no absolute callouts.
// The curve draws once on view-enter and the callouts stack below the
// chart as a simple list. Cumulative-return sits inside the chart card
// so it reads as a label on the curve, not a competing headline.
// ====================================================================
function MobileEquityCurve() {
  const sectionRef = useRef(null);
  const inView = useInView(sectionRef, { once: true, margin: "-15%" });
  const [points, setPoints] = useState(FALLBACK_CURVE);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/api/landing-stats`)
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        const ec = d?.equity_curve;
        if (Array.isArray(ec) && ec.length >= 6) setPoints(ec);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const { d, coords } = useMemo(() => buildCurvePath(points), [points]);

  const callouts = useMemo(() => {
    if (!coords?.length) return [];
    let peakIdx = 0;
    for (let i = 1; i < coords.length; i++) {
      if (coords[i].return_pct > coords[peakIdx].return_pct) peakIdx = i;
    }
    const endIdx = coords.length - 1;
    const result = [
      {
        coord: coords[0],
        label: formatDate(coords[0].date),
        body: "Paper portfolio go-live · ₹10L baseline",
      },
    ];
    if (peakIdx !== 0 && peakIdx !== endIdx) {
      result.push({
        coord: coords[peakIdx],
        label: formatDate(coords[peakIdx].date),
        body: `Peak +${coords[peakIdx].return_pct.toFixed(1)}% return`,
      });
    }
    result.push({
      coord: coords[endIdx],
      label: formatDate(coords[endIdx].date),
      body: `Today · ${coords[endIdx].return_pct >= 0 ? "+" : ""}${coords[endIdx].return_pct.toFixed(1)}% cumulative`,
    });
    return result;
  }, [coords]);

  const finalReturn = coords.length ? coords[coords.length - 1].return_pct : 0;

  return (
    <section
      ref={sectionRef}
      className="relative"
      style={{ paddingBlock: "clamp(56px, 10vh, 96px)", paddingInline: 24 }}
    >
      <div style={{ maxWidth: 720, marginInline: "auto", width: "100%" }}>
        {/* Eyebrow */}
        <div
          className="font-mono uppercase mb-3"
          style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
            style={{ background: "var(--brand)" }}
          />
          03 · The curve
        </div>

        {/* Headline */}
        <motion.h2
          initial={{ opacity: 0, y: 14 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.42, ease: easeOutQuart }}
          className="font-heading"
          style={{
            fontWeight: 600,
            color: "var(--text-1)",
            fontSize: "clamp(28px, 7vw, 40px)",
            lineHeight: 1.08,
            letterSpacing: "-0.025em",
            margin: "0 0 24px",
          }}
        >
          Four years of paper portfolio.
        </motion.h2>

        {/* Chart card with embedded cumulative-return label */}
        <div
          style={{
            background: "var(--surface-1)",
            border: "1px solid var(--edge-1)",
            borderRadius: "var(--r-card)",
            padding: 16,
            position: "relative",
          }}
        >
          {/* Cumulative return — sits inside the card so it reads as a
              label on the chart, not a competing heading. */}
          <div
            className="flex items-baseline justify-between"
            style={{ marginBottom: 12 }}
          >
            <div
              className="font-mono uppercase"
              style={{ fontSize: 10, letterSpacing: "0.16em", color: "var(--text-3)" }}
            >
              Cumulative return
            </div>
            <motion.div
              initial={{ opacity: 0 }}
              animate={inView ? { opacity: 1 } : {}}
              transition={{ duration: 0.4, delay: 1.0 }}
              className="tabular-nums"
              style={{
                fontVariantNumeric: "tabular-nums",
                fontSize: 24,
                fontWeight: 600,
                letterSpacing: "-0.02em",
                color: finalReturn >= 0 ? "var(--bull)" : "var(--bear)",
                lineHeight: 1,
              }}
            >
              {finalReturn >= 0 ? "+" : ""}
              {finalReturn.toFixed(1)}%
            </motion.div>
          </div>

          <svg
            viewBox={`0 0 ${VB_W} ${VB_H}`}
            preserveAspectRatio="none"
            width="100%"
            style={{ display: "block", height: "clamp(180px, 48vw, 240px)" }}
          >
            <defs>
              <linearGradient id="equityFillMobile" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4F8CFF" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#4F8CFF" stopOpacity={0} />
              </linearGradient>
            </defs>

            {[0.25, 0.5, 0.75].map((p) => (
              <line
                key={p}
                x1={0}
                x2={VB_W}
                y1={PAD_TOP + p * PLOT_H}
                y2={PAD_TOP + p * PLOT_H}
                stroke="var(--edge-1)"
                strokeWidth={1}
              />
            ))}
            <line
              x1={0}
              x2={VB_W}
              y1={BASELINE_Y}
              y2={BASELINE_Y}
              stroke="var(--edge-2)"
              strokeWidth={1}
              strokeDasharray="3 4"
            />

            {/* Area fill draws with the curve */}
            <motion.path
              d={`${d} L ${VB_W} ${BASELINE_Y} L 0 ${BASELINE_Y} Z`}
              fill="url(#equityFillMobile)"
              initial={{ opacity: 0 }}
              animate={inView ? { opacity: 1 } : { opacity: 0 }}
              transition={{ duration: 0.6, delay: 0.6 }}
            />

            {/* The curve — single 1.2s draw on view-enter */}
            <motion.path
              d={d}
              fill="none"
              stroke="#4F8CFF"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={inView ? { pathLength: 1 } : { pathLength: 0 }}
              transition={{ duration: 1.2, ease: easeOutQuart, delay: 0.2 }}
            />

            {/* Static callout dots */}
            {callouts.map((c, i) => (
              <motion.circle
                key={i}
                cx={c.coord.x}
                cy={c.coord.y}
                r={6}
                fill="#4F8CFF"
                stroke="var(--surface-1)"
                strokeWidth={3}
                initial={{ opacity: 0, scale: 0.4 }}
                animate={inView ? { opacity: 1, scale: 1 } : {}}
                transition={{ duration: 0.3, delay: 1.0 + i * 0.15 }}
                style={{ transformOrigin: `${c.coord.x}px ${c.coord.y}px` }}
              />
            ))}
          </svg>

          <div
            className="font-mono mt-3 flex items-center justify-between"
            style={{ fontSize: 11, color: "var(--text-4)", letterSpacing: "0.05em" }}
          >
            <span>{formatDate(coords[0]?.date)}</span>
            <span>{formatDate(coords[coords.length - 1]?.date)}</span>
          </div>
        </div>

        {/* Callout list — stacked, no overlap, no scroll math */}
        <div
          className="grid"
          style={{ gap: 10, marginTop: 16 }}
        >
          {callouts.map((c, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.4, delay: 1.4 + i * 0.1 }}
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--edge-2)",
                borderRadius: "var(--r-chip)",
                padding: "10px 14px",
              }}
            >
              <div
                className="font-mono uppercase"
                style={{ fontSize: 10, letterSpacing: "0.12em", color: "var(--brand)" }}
              >
                {c.label}
              </div>
              <div
                style={{
                  fontSize: 13,
                  color: "var(--text-2)",
                  marginTop: 4,
                  lineHeight: 1.45,
                }}
              >
                {c.body}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Disclosure */}
        <p
          style={{
            fontSize: 11,
            color: "var(--text-4)",
            textAlign: "center",
            marginTop: 24,
            lineHeight: 1.5,
          }}
        >
          Equity curve from the production paper portfolio · sampled from the
          daily history file · past performance does not guarantee future
          returns.
        </p>
      </div>
    </section>
  );
}
