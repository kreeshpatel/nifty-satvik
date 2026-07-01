import { useState, useContext, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Loader2, ArrowUpRight } from "lucide-react";
import { motion } from "framer-motion";
import { AuthContext } from "@/context/AuthContext";

const API = process.env.REACT_APP_API_URL ?? '';

/* ── Blue palette (V2 — single brand color, no green) ───────────
   Three intensities for visual hierarchy without breaking the rule
   that green is reserved for BULL-only semantic use. */
const AMBER       = "#4F8CFF";
const AMBER_HI    = "#7BA9FF";
const AMBER_MID   = "#3A6FD9";
const AMBER_DIM   = "#254FA0";

/* ── Network — labeled nodes represent the actual signal pipeline.
     Labels make the graphic mean something instead of being decoration:
     center = the LightGBM MODEL, outer = the 6 input pillars + downstream
     stages. Visitors hovering near each node get a tooltip with what it is. */
const NODE_DEFS = [
  // Center node — the model itself
  { id: 0,  cx: 250, cy: 250, r: 9,   color: AMBER,    glow: true,  label: "MODEL",    blurb: "Two-head LightGBM · 79 features" },

  // Input pillars (named, evenly distributed around the model)
  { id: 1,  cx: 115, cy: 110, r: 5.5, color: AMBER_HI,             label: "FEATURES", blurb: "51 technical indicators" },
  { id: 9,  cx: 325, cy: 145, r: 5,   color: AMBER_HI,             label: "MACRO",    blurb: "8 macro signals (FII, VIX, regime)" },
  { id: 3,  cx: 420, cy: 215, r: 5.5, color: AMBER_HI,             label: "SECTORS",  blurb: "10 sector relative-strength scores" },
  { id: 5,  cx: 250, cy: 430, r: 5,   color: AMBER_HI,             label: "FLOW",     blurb: "Volume + breadth structure" },
  { id: 7,  cx: 70,  cy: 225, r: 5.5, color: AMBER_HI,             label: "GATE",     blurb: "Confidence + return + regime check" },

  // Downstream outputs
  { id: 4,  cx: 395, cy: 380, r: 4.5, color: AMBER_MID,            label: "RISK",     blurb: "Kelly + ATR sizing · sector caps" },
  { id: 11, cx: 165, cy: 330, r: 4.5, color: AMBER_MID,            label: "SIGNAL",   blurb: "Entry · Stop · Target · R:R" },

  // Unlabeled supporting nodes for visual density
  { id: 2,  cx: 370, cy: 85,  r: 3.5, color: AMBER_DIM             },
  { id: 6,  cx: 95,  cy: 355, r: 3.5, color: AMBER_DIM             },
  { id: 8,  cx: 185, cy: 165, r: 3,   color: AMBER_DIM             },
  { id: 10, cx: 340, cy: 300, r: 4,   color: AMBER_DIM             },
  { id: 12, cx: 205, cy: 395, r: 2.5, color: AMBER_DIM             },
  { id: 13, cx: 420, cy: 145, r: 3,   color: AMBER_DIM             },
  { id: 14, cx: 140, cy: 250, r: 2.5, color: AMBER_DIM             },
  { id: 15, cx: 295, cy: 340, r: 3.5, color: AMBER_DIM             },
];

/* Edges — pillars all link to MODEL, then MODEL links to RISK and SIGNAL.
   Supporting nodes weave between for visual structure. */
const EDGES = [
  // Pillars → model
  [0, 1], [0, 3], [0, 5], [0, 7], [0, 9],
  // Model → downstream
  [0, 4], [0, 11],
  // Supporting weave
  [0, 8], [0, 10], [0, 14],
  [1, 2], [1, 8], [2, 9], [2, 13], [3, 13], [3, 10], [3, 4],
  [4, 15], [4, 5], [5, 12], [5, 11], [6, 7], [6, 11],
  [7, 14], [8, 9], [9, 13], [10, 15], [11, 12], [14, 11], [15, 5],
];

/* IDs of the 5 input pillars — used by the auto-pulse heartbeat to pick
   a "stock being scored" entry point. */
const PILLAR_IDS = [1, 3, 5, 7, 9];
const SIGNAL_NODE_ID = 11;
const MODEL_NODE_ID = 0;

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

/* ── Interactive Canvas Network ── */
function InteractiveNetwork() {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const stateRef = useRef(null);
  const [hoveredLabel, setHoveredLabel] = useState(null);

  // Initialize physics state once
  if (!stateRef.current) {
    stateRef.current = {
      nodes: NODE_DEFS.map((n) => ({
        ...n,
        homeX: n.cx, homeY: n.cy,
        x: n.cx, y: n.cy,
        vx: 0, vy: 0,
        brightness: 0,
        phase: Math.random() * Math.PI * 2,
      })),
      mouse: { x: -9999, y: -9999, active: false, screenX: 0, screenY: 0 },
      drag: -1,
      pulses: [],
      trail: [],
      // Particles that traverse pipeline edges from pillar → model → signal
      flowParticles: [],
      edgeParticles: EDGES.map((_, i) => ({ t: (i * 0.13) % 1, speed: 0.0025 + (i % 5) * 0.0008 })),
      scale: 1,
      w: 500, h: 500,
      lastHeartbeat: 0,
    };
  }

  const getMousePos = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: -9999, y: -9999, screenX: 0, screenY: 0 };
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * 500,
      y: ((e.clientY - rect.top) / rect.height) * 500,
      screenX: e.clientX - rect.left,
      screenY: e.clientY - rect.top,
    };
  }, []);

  /* Spawn a "scan" — a particle traveling pillar → model. On reaching the
     model, ~60% chance it converts to a "signal" particle that travels
     model → SIGNAL node and emits a bright ring pulse on arrival. This
     auto-fires every ~5s as a heartbeat, giving the constellation a
     constant subtle sense of work happening. */
  const spawnScan = useCallback((startId) => {
    const s = stateRef.current;
    s.flowParticles.push({
      kind: "scan",
      fromId: startId,
      toId: MODEL_NODE_ID,
      t: 0,
      speed: 0.012,
      life: 1,
    });
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext("2d");
    let raf;

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + "px";
      canvas.style.height = rect.height + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      stateRef.current.w = rect.width;
      stateRef.current.h = rect.height;
      stateRef.current.scale = rect.width / 500;
    };

    const ro = new ResizeObserver(resize);
    ro.observe(container);
    resize();

    const tick = (time) => {
      const s = stateRef.current;
      const sc = s.w / 500;
      const t = time * 0.001;
      const W = s.w;
      const H = s.h;

      ctx.clearRect(0, 0, W, H);

      /* Heartbeat — fire a scan from a random pillar every ~5s */
      if (time - s.lastHeartbeat > 5000 + Math.random() * 2000) {
        s.lastHeartbeat = time;
        const startId = PILLAR_IDS[Math.floor(Math.random() * PILLAR_IDS.length)];
        spawnScan(startId);
      }

      /* Physics */
      for (const node of s.nodes) {
        if (s.drag === node.id) {
          node.x += (s.mouse.x - node.x) * 0.3;
          node.y += (s.mouse.y - node.y) * 0.3;
          node.vx = 0;
          node.vy = 0;
        } else {
          const dx = node.homeX - node.x;
          const dy = node.homeY - node.y;
          node.vx += dx * 0.025;
          node.vy += dy * 0.025;

          if (s.mouse.active) {
            const mx = node.x - s.mouse.x;
            const my = node.y - s.mouse.y;
            const md = Math.sqrt(mx * mx + my * my);
            if (md < 120 && md > 1) {
              const force = (120 - md) * 0.008;
              node.vx += (mx / md) * force;
              node.vy += (my / md) * force;
            }
          }

          node.vx += Math.sin(t * 0.7 + node.phase) * 0.02;
          node.vy += Math.cos(t * 0.5 + node.phase * 1.3) * 0.02;
          node.vx *= 0.91;
          node.vy *= 0.91;
          node.x += node.vx;
          node.y += node.vy;
        }

        if (s.mouse.active) {
          const mx = node.x - s.mouse.x;
          const my = node.y - s.mouse.y;
          const md = Math.sqrt(mx * mx + my * my);
          const prox = Math.max(0, 1 - md / 150);
          node.brightness += (prox - node.brightness) * 0.1;
        } else {
          node.brightness *= 0.95;
        }
      }

      /* Pulses */
      for (let i = s.pulses.length - 1; i >= 0; i--) {
        const p = s.pulses[i];
        p.radius += 3;
        p.life -= 0.015;
        if (p.life <= 0) { s.pulses.splice(i, 1); continue; }

        for (const node of s.nodes) {
          const d = Math.sqrt((node.x - p.cx) ** 2 + (node.y - p.cy) ** 2);
          if (Math.abs(d - p.radius) < 15) {
            node.brightness = Math.min(1, node.brightness + 0.3);
          }
        }
      }

      /* Flow particles — pipeline traversal */
      for (let i = s.flowParticles.length - 1; i >= 0; i--) {
        const fp = s.flowParticles[i];
        fp.t += fp.speed;
        if (fp.t >= 1) {
          // Arrived at destination
          const dest = s.nodes.find((n) => n.id === fp.toId);
          if (dest) dest.brightness = Math.min(1, dest.brightness + 0.6);

          if (fp.kind === "scan" && Math.random() < 0.6) {
            // ~60% of scans convert to a SIGNAL hit — second-leg particle
            s.flowParticles.push({
              kind: "signal",
              fromId: MODEL_NODE_ID,
              toId: SIGNAL_NODE_ID,
              t: 0,
              speed: 0.018,
              life: 1,
            });
          } else if (fp.kind === "signal") {
            // Bright ring pulse from SIGNAL node — a "trade fired"
            if (dest) {
              s.pulses.push({ cx: dest.x, cy: dest.y, radius: 0, life: 1 });
            }
          }
          s.flowParticles.splice(i, 1);
        }
      }

      /* Mouse trail */
      if (s.mouse.active) {
        s.trail.push({
          x: s.mouse.x, y: s.mouse.y,
          vx: (Math.random() - 0.5) * 0.5,
          vy: (Math.random() - 0.5) * 0.5,
          life: 1,
        });
      }
      for (let i = s.trail.length - 1; i >= 0; i--) {
        const p = s.trail[i];
        p.x += p.vx;
        p.y += p.vy;
        p.life -= 0.03;
        if (p.life <= 0) s.trail.splice(i, 1);
      }

      /* Draw — orbital rings */
      ctx.save();
      ctx.translate(250 * sc, 250 * sc);
      [90, 150, 210].forEach((r, i) => {
        ctx.save();
        ctx.rotate((-15 + i * 12) * Math.PI / 180);
        ctx.beginPath();
        ctx.ellipse(0, 0, r * sc, r * 0.85 * sc, 0, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(79,140,255,0.05)";
        ctx.lineWidth = 0.6;
        ctx.stroke();
        ctx.restore();
      });
      ctx.restore();

      /* Draw — edges + ambient particles */
      for (let i = 0; i < EDGES.length; i++) {
        const [a, b] = EDGES[i];
        const na = s.nodes.find((n) => n.id === a);
        const nb = s.nodes.find((n) => n.id === b);
        if (!na || !nb) continue;
        const midX = (na.x + nb.x) / 2;
        const midY = (na.y + nb.y) / 2;

        let edgeBright = 0.08;
        if (s.mouse.active) {
          const md = Math.sqrt((midX - s.mouse.x) ** 2 + (midY - s.mouse.y) ** 2);
          edgeBright = 0.08 + Math.max(0, 1 - md / 150) * 0.18;
        }
        edgeBright = Math.min(0.35, edgeBright + (na.brightness + nb.brightness) * 0.1);

        ctx.beginPath();
        ctx.moveTo(na.x * sc, na.y * sc);
        ctx.lineTo(nb.x * sc, nb.y * sc);
        ctx.strokeStyle = `rgba(79,140,255,${edgeBright})`;
        ctx.lineWidth = 0.7;
        ctx.stroke();

        const ep = s.edgeParticles[i];
        ep.t = (ep.t + ep.speed) % 1;
        const px = na.x + (nb.x - na.x) * ep.t;
        const py = na.y + (nb.y - na.y) * ep.t;
        ctx.beginPath();
        ctx.arc(px * sc, py * sc, 1.5 * sc, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(123,169,255,${0.3 + edgeBright})`;
        ctx.fill();
      }

      /* Draw — flow particles (pipeline narrative, larger + brighter) */
      for (const fp of s.flowParticles) {
        const from = s.nodes.find((n) => n.id === fp.fromId);
        const to = s.nodes.find((n) => n.id === fp.toId);
        if (!from || !to) continue;
        const px = from.x + (to.x - from.x) * fp.t;
        const py = from.y + (to.y - from.y) * fp.t;
        const r = fp.kind === "signal" ? 3.5 : 2.5;
        const alpha = fp.kind === "signal" ? 0.95 : 0.7;
        // Glow halo
        const haloR = r * 4 * sc;
        const grad = ctx.createRadialGradient(px * sc, py * sc, 0, px * sc, py * sc, haloR);
        grad.addColorStop(0, `rgba(79,140,255,${alpha * 0.5})`);
        grad.addColorStop(1, "rgba(79,140,255,0)");
        ctx.beginPath();
        ctx.arc(px * sc, py * sc, haloR, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();
        // Core
        ctx.beginPath();
        ctx.arc(px * sc, py * sc, r * sc, 0, Math.PI * 2);
        ctx.fillStyle = fp.kind === "signal" ? "#7BA9FF" : "#4F8CFF";
        ctx.fill();
      }

      /* Draw — pulse rings */
      for (const p of s.pulses) {
        ctx.beginPath();
        ctx.arc(p.cx * sc, p.cy * sc, p.radius * sc, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(79,140,255,${p.life * 0.5})`;
        ctx.lineWidth = 2 * p.life;
        ctx.stroke();
      }

      /* Draw — cursor trail */
      for (const p of s.trail) {
        ctx.beginPath();
        ctx.arc(p.x * sc, p.y * sc, 1.5 * p.life * sc, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(79,140,255,${p.life * 0.4})`;
        ctx.fill();
      }

      /* Draw — nodes */
      for (const node of s.nodes) {
        const nr = node.r * sc;
        const nx = node.x * sc;
        const ny = node.y * sc;
        const extra = node.brightness;

        // Glow halo
        const glowR = nr * (3 + extra * 2);
        const grad = ctx.createRadialGradient(nx, ny, nr * 0.5, nx, ny, glowR);
        const c = hexToRgb(node.color);
        grad.addColorStop(0, `rgba(${c.r},${c.g},${c.b},${0.18 + extra * 0.3})`);
        grad.addColorStop(1, `rgba(${c.r},${c.g},${c.b},0)`);
        ctx.beginPath();
        ctx.arc(nx, ny, glowR, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();

        // Core glow for center MODEL node
        if (node.glow) {
          const coreR = (35 + Math.sin(t * 1.5) * 8 + extra * 15) * sc;
          const coreGrad = ctx.createRadialGradient(nx, ny, 0, nx, ny, coreR);
          coreGrad.addColorStop(0, `rgba(79,140,255,${0.28 + extra * 0.2})`);
          coreGrad.addColorStop(1, "rgba(79,140,255,0)");
          ctx.beginPath();
          ctx.arc(nx, ny, coreR, 0, Math.PI * 2);
          ctx.fillStyle = coreGrad;
          ctx.fill();
        }

        // Node dot
        const dotR = nr * (1 + extra * 0.5);
        ctx.beginPath();
        ctx.arc(nx, ny, dotR, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.globalAlpha = 0.78 + extra * 0.22;
        ctx.fill();
        ctx.globalAlpha = 1;

        // Label
        if (node.label) {
          ctx.font = `${9 * sc}px "DM Sans", ui-sans-serif, sans-serif`;
          ctx.fillStyle = `rgba(79,140,255,${0.55 + extra * 0.4})`;
          ctx.textBaseline = "middle";
          ctx.letterSpacing = "0.12em";
          ctx.fillText(node.label, nx + (node.r + 8) * sc, ny);
        }
      }

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [spawnScan]);

  const onMouseMove = useCallback((e) => {
    const pos = getMousePos(e);
    const s = stateRef.current;
    s.mouse.x = pos.x;
    s.mouse.y = pos.y;
    s.mouse.screenX = pos.screenX;
    s.mouse.screenY = pos.screenY;
    s.mouse.active = true;

    // Check label hover for tooltip
    let found = null;
    for (const node of s.nodes) {
      if (!node.label) continue;
      const d = Math.sqrt((node.x - pos.x) ** 2 + (node.y - pos.y) ** 2);
      if (d < (node.r + 14)) {
        found = { label: node.label, blurb: node.blurb, screenX: pos.screenX, screenY: pos.screenY };
        break;
      }
    }
    setHoveredLabel((prev) => {
      if (!found && !prev) return prev;
      if (!found) return null;
      if (prev && prev.label === found.label) {
        return { ...prev, screenX: found.screenX, screenY: found.screenY };
      }
      return found;
    });
  }, [getMousePos]);

  const onMouseDown = useCallback((e) => {
    const pos = getMousePos(e);
    const s = stateRef.current;

    for (const node of s.nodes) {
      const d = Math.sqrt((node.x - pos.x) ** 2 + (node.y - pos.y) ** 2);
      if (d < node.r + 12) {
        s.drag = node.id;
        // Clicking a pillar fires a manual scan
        if (PILLAR_IDS.includes(node.id)) {
          s.flowParticles.push({
            kind: "scan",
            fromId: node.id,
            toId: MODEL_NODE_ID,
            t: 0,
            speed: 0.012,
            life: 1,
          });
        }
        return;
      }
    }

    // Empty-space click → simple ripple
    s.pulses.push({ cx: pos.x, cy: pos.y, radius: 0, life: 1 });
  }, [getMousePos]);

  const onMouseUp = useCallback(() => {
    stateRef.current.drag = -1;
  }, []);

  const onMouseLeave = useCallback(() => {
    const s = stateRef.current;
    s.mouse.active = false;
    s.drag = -1;
    setHoveredLabel(null);
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full relative" style={{ cursor: "crosshair" }}>
      <canvas
        ref={canvasRef}
        onMouseMove={onMouseMove}
        onMouseDown={onMouseDown}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseLeave}
        className="block w-full h-full"
      />
      {hoveredLabel && (
        <div
          className="pointer-events-none absolute font-mono"
          style={{
            left: hoveredLabel.screenX + 16,
            top: hoveredLabel.screenY + 16,
            background: "var(--surface-2)",
            border: "1px solid var(--edge-2)",
            borderRadius: "var(--r-chip)",
            padding: "8px 11px",
            maxWidth: 240,
            zIndex: 20,
          }}
        >
          <div
            style={{
              fontSize: 10,
              letterSpacing: "0.16em",
              color: "var(--brand)",
              textTransform: "uppercase",
              marginBottom: 3,
            }}
          >
            {hoveredLabel.label}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.4 }}>
            {hoveredLabel.blurb}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Login Page ── */
export default function Login() {
  const { login, loginMfa } = useContext(AuthContext);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  // MFA flow state — set after a successful password step when the user has
  // 2FA enabled. Hides the email/password form and shows a 6-digit code input.
  const [mfaPendingToken, setMfaPendingToken] = useState(null);
  const [mfaCode, setMfaCode] = useState("");

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (loading) return;
    setError("");
    setLoading(true);
    try {
      const result = await login(email, password);
      if (result?.mfaRequired) {
        setMfaPendingToken(result.mfaPendingToken);
      }
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleMfaSubmit = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (loading) return;
    setError("");
    setLoading(true);
    try {
      await loginMfa(mfaPendingToken, mfaCode);
    } catch (err) {
      setError(err.message || "Verification failed");
      setMfaCode("");
    } finally {
      setLoading(false);
    }
  };

  // Real backtest stats — fall back to known-good values if endpoint
  // hasn't loaded yet. Numbers refresh quarterly via the strategy
  // revalidator cron, same as the landing.
  const bt = stats?.backtest;
  const cagr = bt?.cagr_pct ?? 31.1;
  const trades = bt?.total_trades ?? 525;
  const sharpe = bt?.sharpe ?? 2.97;

  return (
    <div
      data-page-ctx="auth"
      className="min-h-screen flex relative overflow-hidden"
      style={{
        background: "var(--surface-0)",
        color: "var(--text-1)",
        // Same contrast pump as Landing — pure-near-white headlines on
        // pure-black for the editorial fintech feel.
        "--text-1": "#F1F5FF",
        "--text-2": "#B8C0DA",
        "--text-3": "#7A82A5",
      }}
    >
      {/* Page-wide ambient gradient — soft warm radial bloom anchored at the
          top, with a secondary glow under the constellation panel.  Two-layer
          radial keeps the form side breathing while the constellation feels
          spotlit. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 1200px 600px at 25% 0%, rgba(79,140,255,0.10), transparent 55%), radial-gradient(ellipse 900px 700px at 25% 70%, rgba(79,140,255,0.06), transparent 60%)",
        }}
      />

      {/* ── Left Panel ── */}
      <div className="hidden lg:flex lg:w-1/2 relative flex-col items-center justify-center">

        <div className="absolute inset-0">
          <InteractiveNetwork />
        </div>

        {/* Bottom branding */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="absolute bottom-8 left-8 right-8 pointer-events-none z-10"
        >
          <div className="flex items-center gap-2.5 mb-3">
            <div
              className="flex items-center justify-center"
              style={{
                width: 28,
                height: 28,
                background: "var(--brand)",
                color: "var(--brand-fg)",
                borderRadius: "var(--r-chip)",
                fontWeight: 700,
                fontSize: 10,
                letterSpacing: "-0.01em",
                fontFamily: "var(--font-heading, inherit)",
              }}
            >
              NQ
            </div>
            <span
              className="font-heading"
              style={{ fontWeight: 600, fontSize: 14, color: "var(--text-1)", letterSpacing: "-0.005em" }}
            >
              NIFTYQUANT
            </span>
          </div>
          <p
            className="font-mono uppercase mb-5"
            style={{ fontSize: 10, letterSpacing: "0.18em", color: "var(--text-3)" }}
          >
            Pre-move detection engine
          </p>
          <div className="flex items-center" style={{ gap: 22 }}>
            <Stat value={`${Number(cagr).toFixed(1)}%`} label="CAGR" />
            <Stat value={Number(trades).toLocaleString("en-IN")} label="trades" />
            <Stat value={Number(sharpe).toFixed(2)} label="Sharpe" />
          </div>
        </motion.div>

        {/* Hover hint */}
        <div
          className="absolute top-8 left-8 font-mono uppercase pointer-events-none z-10"
          style={{ fontSize: 10, letterSpacing: "0.18em", color: "var(--text-4)" }}
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
            style={{ background: "var(--brand)" }}
          />
          Live · hover the labels
        </div>
      </div>

      {/* ── Right Panel ── */}
      <div className="w-full lg:w-1/2 flex flex-col min-h-screen relative">
        <div
          className="hidden lg:block absolute top-0 left-0 bottom-0 w-px"
          style={{ background: "var(--edge-1)" }}
        />

        <div className="flex justify-end p-6">
          <Link
            to="/"
            className="inline-flex items-center gap-2 transition-colors"
            style={{
              fontSize: 13,
              color: "var(--text-2)",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-1)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-2)")}
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Home
          </Link>
        </div>

        <div className="flex-1 flex items-center justify-center px-6 sm:px-12 lg:px-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="w-full max-w-sm"
          >
            <div className="lg:hidden flex items-center gap-2.5 mb-10">
              <div
                className="flex items-center justify-center"
                style={{
                  width: 32,
                  height: 32,
                  background: "var(--brand)",
                  color: "var(--brand-fg)",
                  borderRadius: "var(--r-chip)",
                  fontWeight: 700,
                  fontSize: 12,
                }}
              >
                NQ
              </div>
              <span
                className="font-heading"
                style={{ fontWeight: 600, fontSize: 17, color: "var(--text-1)", letterSpacing: "-0.005em" }}
              >
                NIFTYQUANT
              </span>
            </div>

            <h1
              className="font-heading"
              style={{
                fontWeight: 600,
                color: "var(--text-1)",
                fontSize: "clamp(28px, 3.6vw, 42px)",
                lineHeight: 1.05,
                letterSpacing: "-0.025em",
                margin: 0,
                marginBottom: 8,
              }}
            >
              Welcome back.
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-3)", marginBottom: 36 }}>
              {mfaPendingToken
                ? "Enter the 6-digit code from your authenticator app."
                : "Sign in to your trading dashboard."}
            </p>

            {mfaPendingToken ? (
              <form onSubmit={handleMfaSubmit} className="space-y-5">
                <Field label="Authentication code">
                  <Input
                    id="mfa-code"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    pattern="[0-9]{6}"
                    required
                    autoFocus
                    placeholder="123456"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    className="h-12 tracking-[0.4em] text-center"
                    style={{
                      background: "var(--surface-1)",
                      border: "1px solid var(--edge-1)",
                      color: "var(--text-1)",
                      borderRadius: "var(--r-chip)",
                      fontSize: 18,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  />
                </Field>

                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-2 px-3.5 py-2.5"
                    style={{
                      background: "oklch(66% 0.21 25 / 0.08)",
                      border: "1px solid oklch(66% 0.21 25 / 0.25)",
                      borderRadius: "var(--r-chip)",
                      fontSize: 12,
                      color: "var(--bear)",
                    }}
                  >
                    {error}
                  </motion.div>
                )}

                <button
                  type="submit"
                  disabled={loading || mfaCode.length !== 6}
                  className="w-full h-12 inline-flex items-center justify-center gap-2 disabled:opacity-70 transition-opacity"
                  style={{
                    background: "var(--brand)",
                    color: "var(--brand-fg)",
                    borderRadius: "var(--r-chip)",
                    border: "none",
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Verifying…
                    </>
                  ) : (
                    "Verify and sign in"
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setMfaPendingToken(null);
                    setMfaCode("");
                    setError("");
                  }}
                  className="w-full text-center transition-opacity hover:opacity-80"
                  style={{ fontSize: 12.5, color: "var(--text-3)" }}
                >
                  Use a different account
                </button>
              </form>
            ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <Field label="Email">
                <Input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-12"
                  style={{
                    background: "var(--surface-1)",
                    border: "1px solid var(--edge-1)",
                    color: "var(--text-1)",
                    borderRadius: "var(--r-chip)",
                    fontSize: 14,
                  }}
                />
              </Field>

              <Field label="Password">
                <Input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-12"
                  style={{
                    background: "var(--surface-1)",
                    border: "1px solid var(--edge-1)",
                    color: "var(--text-1)",
                    borderRadius: "var(--r-chip)",
                    fontSize: 14,
                  }}
                />
              </Field>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 px-3.5 py-2.5"
                  style={{
                    background: "oklch(66% 0.21 25 / 0.08)",
                    border: "1px solid oklch(66% 0.21 25 / 0.25)",
                    borderRadius: "var(--r-chip)",
                    fontSize: 12,
                    color: "var(--bear)",
                  }}
                >
                  {error}
                </motion.div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full h-12 inline-flex items-center justify-center gap-2 disabled:opacity-70 transition-opacity"
                style={{
                  background: "var(--brand)",
                  color: "var(--brand-fg)",
                  borderRadius: "var(--r-chip)",
                  border: "none",
                  fontSize: 14,
                  fontWeight: 600,
                  letterSpacing: "-0.005em",
                }}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    Sign in
                    <ArrowUpRight size={14} strokeWidth={2.4} />
                  </>
                )}
              </button>
            </form>
            )}

            {!mfaPendingToken && (
              <>
                <p
                  className="text-center mt-5"
                  style={{ fontSize: 12.5, color: "var(--text-3)" }}
                >
                  <Link
                    to="/forgot-password"
                    className="transition-opacity hover:opacity-80"
                    style={{ color: "var(--text-2)" }}
                  >
                    Forgot your password?
                  </Link>
                </p>

                <p
                  className="text-center mt-3"
                  style={{ fontSize: 13, color: "var(--text-3)" }}
                >
                  Don't have an account?{" "}
                  <Link
                    to="/"
                    className="transition-opacity"
                    style={{ color: "var(--brand)", fontWeight: 600 }}
                  >
                    Request access
                  </Link>
                </p>
              </>
            )}
          </motion.div>
        </div>

        {/* Mobile bottom stats */}
        <div className="lg:hidden flex items-center justify-center pb-8 px-6" style={{ gap: 22 }}>
          <Stat value={`${Number(cagr).toFixed(1)}%`} label="CAGR" />
          <Stat value={Number(trades).toLocaleString("en-IN")} label="trades" />
          <Stat value={Number(sharpe).toFixed(2)} label="Sharpe" />
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label
        className="font-mono uppercase"
        style={{
          fontSize: 10,
          letterSpacing: "0.18em",
          color: "var(--text-3)",
          fontWeight: 500,
        }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

function Stat({ value, label }) {
  return (
    <span style={{ fontSize: 12, color: "var(--text-3)" }}>
      <span
        className="font-mono tabular-nums"
        style={{ color: "var(--brand)", fontWeight: 600, marginRight: 6 }}
      >
        {value}
      </span>
      {label}
    </span>
  );
}
