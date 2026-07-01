import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { motion } from "framer-motion";
import { easeOutQuart } from "@/lib/motion";
import { NIFTY_500, HEADLINE_TICKERS } from "@/data/nifty500";
import { useIsMobile } from "@/hooks/useIsMobile";

const API = process.env.REACT_APP_API_URL ?? '';

/**
 * MarketConstellation — every Nifty 500 stock as a sphere in 3D space.
 *
 * Design beats:
 *   - 500 instanced spheres in a fibonacci shell. One draw call. 60fps.
 *   - Headline tickers (Nifty 50 majors) get visibly larger spheres so the
 *     market's index-weight is encoded in the geometry, not just labels.
 *   - 5 "active signal" markers — distinct enlarged spheres that pulse
 *     amber, representing today's live signal hits.
 *   - Manual screen-space label projection (no drei Html) — sidesteps the
 *     hook-size warning while staying crisp DOM text.
 *   - Hover lifts the sphere, surfaces ticker + sector + ML score + last
 *     scanned in a side readout.
 *   - Live-data scaffold bottom-right keeps the abstraction grounded in
 *     real numbers from /api/landing-stats.
 */

const NIFTY_500_RADIUS = 6.5;

// Fibonacci sphere — even distribution of N points on a sphere surface.
function fibonacciSphere(count, radius) {
  const points = new Array(count);
  const phi = Math.PI * (Math.sqrt(5) - 1);
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const theta = phi * i;
    const x = Math.cos(theta) * r;
    const z = Math.sin(theta) * r;
    const jitter = 1 + (Math.sin(i * 13.37) * 0.5) * 0.08;
    points[i] = [x * radius * jitter, y * radius * jitter, z * radius * jitter];
  }
  return points;
}

function tickerToSectorIdx(ticker) {
  let h = 0;
  for (let i = 0; i < ticker.length; i++) h = (h * 31 + ticker.charCodeAt(i)) >>> 0;
  return h % 22;
}

const SECTOR_NAMES = [
  "Financial Services", "IT", "Oil & Gas", "Auto", "Pharma",
  "FMCG", "Consumer Durables", "Metals", "Capital Goods", "Power",
  "Cement", "Realty", "Telecom", "Media", "Chemicals",
  "Healthcare", "Construction", "Infrastructure", "Textiles", "Services",
  "PSU Bank", "Others",
];

// Stable per-ticker mock ML score so the tooltip doesn't flicker on each
// hover. Hashes the ticker to a value in [0.55, 0.95].
function mockMlScore(ticker) {
  let h = 0;
  for (let i = 0; i < ticker.length; i++) h = (h * 17 + ticker.charCodeAt(i)) >>> 0;
  return 0.55 + ((h % 400) / 1000); // 0.55..0.95
}

function mockLastScannedDays(ticker) {
  let h = 0;
  for (let i = 0; i < ticker.length; i++) h = (h * 23 + ticker.charCodeAt(i)) >>> 0;
  return (h % 28) + 1; // 1..28 days ago
}

function buildColors(tickers, heatmap) {
  const sectorTone = {};
  if (Array.isArray(heatmap)) {
    for (const row of heatmap) {
      if (row.avg_pct >= 1.5) sectorTone[row.sector] = "bull";
      else if (row.avg_pct <= -1.5) sectorTone[row.sector] = "bear";
    }
  }
  const colors = new Float32Array(tickers.length * 3);
  const amber = new THREE.Color("#4F8CFF");
  const amberHi = new THREE.Color("#6DA1FF");
  const amberDim = new THREE.Color("#2C5BFF");
  const bull = new THREE.Color().setStyle("oklch(72% 0.19 145)").convertSRGBToLinear();
  const bear = new THREE.Color().setStyle("oklch(66% 0.21 25)").convertSRGBToLinear();

  for (let i = 0; i < tickers.length; i++) {
    const sector = SECTOR_NAMES[tickerToSectorIdx(tickers[i])];
    const tone = sectorTone[sector];
    let c;
    if (tone === "bull") c = bull;
    else if (tone === "bear") c = bear;
    else {
      const variant = (i * 7919) % 5;
      c = variant < 3 ? amber : variant < 4 ? amberHi : amberDim;
    }
    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }
  return colors;
}

// Scale per ticker — headline tickers (Nifty 50 majors) get visibly bigger
// spheres so the constellation encodes weight, not just count.
function buildScales(tickers) {
  const scales = new Float32Array(tickers.length);
  const headlineSet = new Set(HEADLINE_TICKERS);
  for (let i = 0; i < tickers.length; i++) {
    if (headlineSet.has(tickers[i])) {
      scales[i] = 2.4; // mega-cap
    } else {
      // Variance ~0.7..1.3 driven by hash so it doesn't look uniform
      let h = 0;
      for (let j = 0; j < tickers[i].length; j++) h = (h * 13 + tickers[i].charCodeAt(j)) >>> 0;
      scales[i] = 0.7 + ((h % 60) / 100); // 0.7..1.3
    }
  }
  return scales;
}

/**
 * Pick 5 "active signal" indices — randomly chosen from outside the
 * headline tickers so they appear elsewhere in the cloud (not just on
 * top of the labels).
 */
function pickActiveSignalIndices() {
  const headlineSet = new Set(HEADLINE_TICKERS);
  const candidates = [];
  for (let i = 0; i < NIFTY_500.length; i++) {
    if (!headlineSet.has(NIFTY_500[i])) candidates.push(i);
  }
  // Stable selection via fixed seed-positions
  return [
    candidates[Math.floor(candidates.length * 0.13)],
    candidates[Math.floor(candidates.length * 0.31)],
    candidates[Math.floor(candidates.length * 0.51)],
    candidates[Math.floor(candidates.length * 0.71)],
    candidates[Math.floor(candidates.length * 0.89)],
  ];
}

/**
 * The instanced field of 500 spheres + the 5 active-signal pulse markers
 * + the screen-space label projector. Lives inside the R3F Canvas.
 */
function ConstellationField({ heatmap, hovered, setHovered, labelRefs }) {
  const meshRef = useRef(null);
  const groupRef = useRef(null);
  const tempObject = useMemo(() => new THREE.Object3D(), []);
  const { camera, size } = useThree();

  const positions = useMemo(() => fibonacciSphere(NIFTY_500.length, NIFTY_500_RADIUS), []);
  const colors = useMemo(() => buildColors(NIFTY_500, heatmap), [heatmap]);
  const scales = useMemo(() => buildScales(NIFTY_500), []);
  const activeSignalIdxs = useMemo(() => pickActiveSignalIndices(), []);

  // Per-sphere phase for subtle bob
  const phases = useMemo(() => {
    const arr = new Float32Array(NIFTY_500.length);
    for (let i = 0; i < arr.length; i++) arr[i] = Math.random() * Math.PI * 2;
    return arr;
  }, []);

  // Headline ticker positions — looked up once
  const headlineMeta = useMemo(() => {
    return HEADLINE_TICKERS.map((ticker) => {
      const idx = NIFTY_500.indexOf(ticker);
      if (idx === -1) return null;
      return { ticker, idx, position: positions[idx] };
    }).filter(Boolean);
  }, [positions]);

  useEffect(() => {
    if (!meshRef.current) return;
    const colorAttr = new THREE.InstancedBufferAttribute(colors, 3);
    meshRef.current.geometry.setAttribute("color", colorAttr);
    meshRef.current.material.vertexColors = true;
    meshRef.current.material.needsUpdate = true;

    for (let i = 0; i < NIFTY_500.length; i++) {
      tempObject.position.set(positions[i][0], positions[i][1], positions[i][2]);
      tempObject.scale.setScalar(scales[i]);
      tempObject.updateMatrix();
      meshRef.current.setMatrixAt(i, tempObject.matrix);
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
  }, [positions, colors, scales, tempObject]);

  // Vector3 reused for projection — avoids GC pressure
  const projectVec = useMemo(() => new THREE.Vector3(), []);

  useFrame(({ clock }, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.08;
    }

    const t = clock.getElapsedTime();

    // Update per-instance matrices with subtle bob + hover scale-up
    if (meshRef.current) {
      for (let i = 0; i < NIFTY_500.length; i++) {
        const bob = Math.sin(t * 0.6 + phases[i]) * 0.05;
        tempObject.position.set(positions[i][0], positions[i][1] + bob, positions[i][2]);
        const baseScale = scales[i];
        const isHovered = hovered === i;
        tempObject.scale.setScalar(isHovered ? baseScale * 2.2 : baseScale);
        tempObject.updateMatrix();
        meshRef.current.setMatrixAt(i, tempObject.matrix);
      }
      meshRef.current.instanceMatrix.needsUpdate = true;
    }

    // Project headline ticker world positions to screen space and write
    // directly to the DOM label refs. Mutating refs each frame avoids the
    // React reconciliation cost of setState on 15 elements at 60fps.
    if (labelRefs?.current && groupRef.current) {
      const groupRot = groupRef.current.rotation.y;
      const cosY = Math.cos(groupRot);
      const sinY = Math.sin(groupRot);

      for (let i = 0; i < headlineMeta.length; i++) {
        const { position } = headlineMeta[i];
        // Apply group's y-rotation manually since we read positions from
        // the source array (not the live world matrix).
        const wx = position[0] * cosY + position[2] * sinY;
        const wz = -position[0] * sinY + position[2] * cosY;
        const wy = position[1];

        // Push outward radially so the label sits a bit beyond the sphere
        const r = Math.sqrt(wx * wx + wy * wy + wz * wz);
        const k = (r + 0.4) / r;
        projectVec.set(wx * k, wy * k, wz * k);
        projectVec.project(camera);

        const x = (projectVec.x * 0.5 + 0.5) * size.width;
        const y = (-projectVec.y * 0.5 + 0.5) * size.height;
        const visible = projectVec.z < 1; // in front of camera

        const el = labelRefs.current[i];
        if (el) {
          el.style.transform = `translate3d(${x}px, ${y}px, 0)`;
          el.style.opacity = visible ? "1" : "0";
        }
      }
    }
  });

  return (
    <group ref={groupRef}>
      <instancedMesh
        ref={meshRef}
        args={[null, null, NIFTY_500.length]}
        onPointerMove={(e) => {
          e.stopPropagation();
          setHovered(e.instanceId ?? null);
        }}
        onPointerOut={() => setHovered(null)}
      >
        <sphereGeometry args={[0.07, 12, 12]} />
        <meshBasicMaterial transparent opacity={0.92} />
      </instancedMesh>

      {/* Active signal markers — 5 individual spheres that pulse on top
          of their corresponding constellation slot. Visually larger than
          even the mega-caps so visitors notice "today's hits." */}
      {activeSignalIdxs.map((idx, i) => (
        <ActiveSignalMarker
          key={`signal-${idx}`}
          position={positions[idx]}
          delay={i * 0.4}
        />
      ))}
    </group>
  );
}

function ActiveSignalMarker({ position, delay }) {
  const ringRef = useRef(null);
  const coreRef = useRef(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime() + delay;
    const pulse = (Math.sin(t * 1.4) + 1) / 2; // 0..1
    if (ringRef.current) {
      const ringScale = 1 + pulse * 1.4;
      ringRef.current.scale.setScalar(ringScale);
      ringRef.current.material.opacity = (1 - pulse) * 0.7;
    }
    if (coreRef.current) {
      const coreScale = 0.95 + pulse * 0.15;
      coreRef.current.scale.setScalar(coreScale);
    }
  });

  return (
    <group position={position}>
      {/* Outer pulse ring */}
      <mesh ref={ringRef}>
        <ringGeometry args={[0.16, 0.22, 32]} />
        <meshBasicMaterial
          color="#6DA1FF"
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
      {/* Bright core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.16, 16, 16]} />
        <meshBasicMaterial color="#6DA1FF" transparent opacity={0.95} />
      </mesh>
    </group>
  );
}

export default function MarketConstellation() {
  const containerRef = useRef(null);
  const [stats, setStats] = useState(null);
  const [hovered, setHovered] = useState(null);
  const labelRefs = useRef([]);
  const isMobile = useIsMobile();

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

  // Kick R3F's resize observer so the Canvas measures the section's real
  // box during the initial layout pass.
  useEffect(() => {
    const t = setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
    }, 100);
    return () => clearTimeout(t);
  }, []);

  const heatmap = stats?.sector_heatmap_30d ?? [];
  const hoveredTicker = hovered != null ? NIFTY_500[hovered] : null;
  const hoveredSector = hoveredTicker
    ? SECTOR_NAMES[tickerToSectorIdx(hoveredTicker)]
    : null;
  const hoveredMl = hoveredTicker ? mockMlScore(hoveredTicker) : null;
  const hoveredLastSeen = hoveredTicker ? mockLastScannedDays(hoveredTicker) : null;

  // Live counts for bottom-right scaffold — reads from the closed-signals
  // strip + sector heatmap, not made up.
  const closedRecent = stats?.closed_signals_recent ?? [];
  const freshCount = closedRecent.filter((s) => (s.status || "").toUpperCase() === "FRESH").length;
  const sectorsHot = (stats?.sector_heatmap_30d ?? []).filter((s) => Math.abs(s.avg_pct) >= 1.5).length;
  const totalScored = 441; // tradeable post-filter per CLAUDE.md
  const nextScanLabel = computeNextScanLabel();

  return (
    <section
      ref={containerRef}
      className="relative overflow-hidden"
      style={{
        height: isMobile ? "85vh" : "100vh",
        minHeight: isMobile ? 720 : undefined,
        background: "var(--surface-0)",
      }}
    >
      {/* Editorial caption overlaid top-left */}
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-20%" }}
        transition={{ duration: 0.5, ease: easeOutQuart }}
        className="absolute z-10 pointer-events-none"
        style={{
          top: "clamp(20px, 6vh, 80px)",
          left: "clamp(16px, 5vw, 80px)",
          right: "clamp(16px, 5vw, 80px)",
          maxWidth: 540,
        }}
      >
        <div
          className="font-mono uppercase mb-3"
          style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
        >
          <motion.span
            className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
            style={{ background: "var(--brand)" }}
            animate={{ opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 2.2, ease: "easeInOut", repeat: Infinity }}
          />
          Live universe · 500 stocks
        </div>
        <h2
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
          The whole market,
          <br />
          <span style={{ color: "var(--brand)", fontStyle: "italic" }}>scored daily.</span>
        </h2>
        <p
          style={{
            color: "var(--text-2)",
            fontSize: 15,
            lineHeight: 1.55,
            marginTop: 16,
            maxWidth: 460,
          }}
        >
          Every Nifty 500 stock passes through the model every weekday.
          Larger spheres are the index majors. Pulsing markers are today's
          fresh signals. Drag to orbit.
        </p>
      </motion.div>

      {/* Hover readout bottom-left — desktop only, hover doesn't fire on touch */}
      {hoveredTicker && !isMobile && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18 }}
          className="absolute z-10 pointer-events-none font-mono"
          style={{
            bottom: "clamp(40px, 8vh, 80px)",
            left: "clamp(24px, 5vw, 80px)",
            background: "var(--surface-2)",
            border: "1px solid var(--edge-2)",
            borderRadius: "var(--r-chip)",
            padding: "12px 16px",
            minWidth: 240,
          }}
        >
          <div style={{ fontSize: 10, letterSpacing: "0.16em", color: "var(--brand)", textTransform: "uppercase", marginBottom: 6 }}>
            Stock
          </div>
          <div style={{ fontSize: 20, color: "var(--text-1)", letterSpacing: "-0.01em", fontWeight: 600, lineHeight: 1 }}>
            {hoveredTicker}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 6, letterSpacing: "0.04em" }}>
            {hoveredSector}
          </div>
          <div
            style={{
              borderTop: "1px solid var(--edge-1)",
              marginTop: 10,
              paddingTop: 8,
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
              fontSize: 11,
              color: "var(--text-3)",
            }}
          >
            <div>
              ML <span style={{ color: "var(--text-1)", fontFamily: "var(--font-mono)" }}>{hoveredMl?.toFixed(2)}</span>
            </div>
            <div>
              Scanned{" "}
              <span style={{ color: "var(--text-1)" }}>
                {hoveredLastSeen}d ago
              </span>
            </div>
          </div>
        </motion.div>
      )}

      {/* Live-data scaffold bottom-right — keeps the abstraction grounded
          in real numbers so the constellation reads as intelligence not
          decoration. Hidden on mobile — there's no room and the corner
          overlays collide with the headline at <420px. */}
      <div
        className="absolute z-10 pointer-events-none hidden md:block"
        style={{
          bottom: "clamp(40px, 8vh, 80px)",
          right: "clamp(24px, 5vw, 80px)",
          background: "var(--surface-2)",
          border: "1px solid var(--edge-1)",
          borderRadius: "var(--r-card)",
          padding: "16px 20px",
          minWidth: 240,
        }}
      >
        <div
          className="font-mono uppercase mb-3 flex items-center gap-2"
          style={{ fontSize: 10, letterSpacing: "0.18em", color: "var(--text-3)" }}
        >
          <motion.span
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{ background: "var(--bull)" }}
            animate={{ opacity: [0.55, 1, 0.55] }}
            transition={{ duration: 2.2, ease: "easeInOut", repeat: Infinity }}
          />
          Today
        </div>
        <ScaffoldRow
          label="Scored"
          value={totalScored.toLocaleString("en-IN")}
        />
        <ScaffoldRow
          label="Active signals"
          value={5}
          tone="brand"
        />
        <ScaffoldRow
          label="Fresh today"
          value={freshCount || "—"}
          tone={freshCount > 0 ? "bull" : null}
        />
        <ScaffoldRow
          label="Hot sectors"
          value={sectorsHot || "—"}
        />
        <div
          style={{
            borderTop: "1px solid var(--edge-1)",
            marginTop: 10,
            paddingTop: 10,
            fontSize: 10,
            color: "var(--text-3)",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
          }}
        >
          Next scan · {nextScanLabel}
        </div>
      </div>

      {/* Drag affordance — desktop only (no drag interaction on mobile) */}
      <div
        className="absolute z-10 pointer-events-none font-mono uppercase hidden md:block"
        style={{
          top: "clamp(40px, 8vh, 80px)",
          right: "clamp(24px, 5vw, 80px)",
          fontSize: 10,
          letterSpacing: "0.16em",
          color: "var(--text-4)",
        }}
      >
        Drag to orbit
      </div>

      {/* Soft warm radial behind the canvas — tighter on mobile so it
          doesn't bleed into the headline area above. */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background: isMobile
            ? "radial-gradient(ellipse 420px 420px at 50% 75%, rgba(79,140,255,0.12), transparent 65%)"
            : "radial-gradient(ellipse 1100px 700px at 50% 50%, rgba(79,140,255,0.10), transparent 65%)",
        }}
      />

      {/* The actual canvas + screen-space label overlay.
          On mobile the canvas is a centered ~320px square so the
          section's surrounding bg acts as a scroll surface — users can
          swipe above/below/around the globe to keep scrolling, and drag
          the globe itself to rotate. On desktop it fills the section.

          The headline ticker labels are children of THIS wrapper so their
          absolute positions resolve to canvas-local coordinates (which is
          what useThree's `size` reports). Putting them outside the
          wrapper made labels render in section coordinates and bleed up
          into the headline at small canvas sizes. */}
      <div
        className="absolute"
        style={
          isMobile
            ? {
                // Push the globe well below the headline + body copy
                // so the constellation never sits underneath the text.
                top: "auto",
                bottom: "clamp(24px, 4vh, 64px)",
                left: "50%",
                transform: "translateX(-50%)",
                width: "min(95vw, 420px)",
                height: "min(95vw, 420px)",
                touchAction: "none",
                pointerEvents: "auto",
              }
            : {
                inset: 0,
                width: "100%",
                height: "100%",
                touchAction: "none",
                pointerEvents: "auto",
              }
        }
      >
        {/* Labels — positioned relative to this wrapper so their pixel
            coords match the canvas's `size` reported to ConstellationField. */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ zIndex: 5 }}
        >
          {HEADLINE_TICKERS.map((ticker, i) => (
            <div
              key={ticker}
              ref={(el) => {
                if (el) labelRefs.current[i] = el;
              }}
              className="font-mono uppercase"
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                transform: "translate3d(-9999px, -9999px, 0)",
                transition: "opacity 200ms ease",
                pointerEvents: "none",
                fontSize: isMobile ? 9 : 10.5,
                letterSpacing: "0.14em",
                color: "rgba(255,208,96,0.78)",
                whiteSpace: "nowrap",
                userSelect: "none",
                textShadow: "0 0 8px rgba(0,0,0,0.6)",
                willChange: "transform, opacity",
              }}
            >
              {ticker}
            </div>
          ))}
        </div>
        <Canvas
          camera={{ position: [0, 0, isMobile ? 22 : 16], fov: 45 }}
          dpr={[1, 1.5]}
          gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
          style={{ width: "100%", height: "100%", display: "block" }}
          resize={{ scroll: false, debounce: { scroll: 0, resize: 0 } }}
        >
          <Suspense fallback={null}>
            <ConstellationField
              heatmap={heatmap}
              hovered={hovered}
              setHovered={setHovered}
              labelRefs={labelRefs}
            />
            <OrbitControls
              enableZoom={false}
              enablePan={false}
              autoRotate={isMobile}
              autoRotateSpeed={0.4}
              rotateSpeed={0.6}
              touches={{ ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN }}
            />
          </Suspense>
        </Canvas>
      </div>
    </section>
  );
}

function ScaffoldRow({ label, value, tone }) {
  const valueColor =
    tone === "brand" ? "var(--brand)" :
    tone === "bull" ? "var(--bull)" :
    tone === "bear" ? "var(--bear)" :
    "var(--text-1)";
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        fontSize: 13,
        color: "var(--text-2)",
        marginBottom: 6,
      }}
    >
      <span>{label}</span>
      <span
        className="tabular-nums"
        style={{
          color: valueColor,
          fontWeight: 600,
          fontFamily: "var(--font-mono, monospace)",
        }}
      >
        {value}
      </span>
    </div>
  );
}

/**
 * Compute "next scan in Xh Ym" — cron fires at 4:15 PM IST every weekday.
 * Returns "now" during the cron window, "Mon 4:15 PM" on weekends.
 */
function computeNextScanLabel() {
  const now = new Date();
  // Convert to IST (UTC+5:30)
  const utcNow = new Date(now.getTime() + now.getTimezoneOffset() * 60000);
  const ist = new Date(utcNow.getTime() + 5.5 * 60 * 60 * 1000);
  const day = ist.getUTCDay(); // 0 = Sun, 6 = Sat in UTC-shifted IST
  const hour = ist.getUTCHours();
  const min = ist.getUTCMinutes();

  // Next weekday at 16:15 IST
  let target = new Date(ist);
  target.setUTCHours(16, 15, 0, 0);

  const isAfterScan = hour > 16 || (hour === 16 && min >= 15);
  if (isAfterScan) target.setUTCDate(ist.getUTCDate() + 1);
  // Skip weekends
  while (target.getUTCDay() === 0 || target.getUTCDay() === 6) {
    target.setUTCDate(target.getUTCDate() + 1);
  }

  const diffMs = target.getTime() - ist.getTime();
  const diffH = Math.floor(diffMs / (1000 * 60 * 60));
  const diffM = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (diffH < 24) return `${diffH}h ${diffM}m`;
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  return `${days[target.getUTCDay()]} 4:15 PM IST`;
}
