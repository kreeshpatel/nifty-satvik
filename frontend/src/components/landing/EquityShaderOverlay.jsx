import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * EquityShaderOverlay — a WebGL canvas that sits on top of the SVG equity
 * curve and adds shader-based glow effects:
 *
 *   1. A bright amber glow at the current "pen tip" — the position along
 *      the curve corresponding to the scroll progress
 *   2. Expanding ripple rings at each callout anchor (start / peak /
 *      latest), continuously pulsing once the pen has passed them
 *
 * The SVG curve below stays as the crisp data line; this overlay adds
 * the cinematic atmosphere that the brief asked for. Tied to the same
 * scroll progress as the SVG via a shared MotionValue.
 *
 * Uniforms are mutated on each frame via refs (no React state) to keep
 * the 60fps target.
 */

const VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy * 2.0, 0.0, 1.0);
  }
`;

const FRAGMENT = /* glsl */ `
  precision highp float;

  uniform float uTime;
  uniform float uProgress;
  uniform vec2 uPenPos;
  uniform vec2 uAnchors[3];
  uniform float uAnchorActive[3];
  uniform float uAspect;

  varying vec2 vUv;

  // Aspect-correct distance — keeps glow circular when canvas is wide
  float aspectDist(vec2 a, vec2 b) {
    vec2 d = a - b;
    d.x *= uAspect;
    return length(d);
  }

  void main() {
    vec3 col = vec3(0.0);
    float alpha = 0.0;

    // ── Pen glow — bright soft halo at the current scroll position ──
    if (uProgress > 0.001) {
      float penDist = aspectDist(vUv, uPenPos);

      // Inner core — small bright dot
      float core = exp(-penDist * 80.0) * 0.95;
      // Outer halo — larger soft glow
      float halo = exp(-penDist * 14.0) * 0.55;
      // Ambient bloom — very wide, subtle
      float bloom = exp(-penDist * 5.0) * 0.18;

      float intensity = core + halo + bloom;
      // Ramp in on first 4% of progress so it doesn't pop
      intensity *= smoothstep(0.0, 0.04, uProgress);

      col += vec3(1.0, 0.72, 0.06) * intensity;
      alpha = max(alpha, intensity);
    }

    // ── Anchor ripples — expanding rings at each active callout ──
    for (int i = 0; i < 3; i++) {
      float aActive = uAnchorActive[i];
      if (aActive <= 0.0) continue;

      float d = aspectDist(vUv, uAnchors[i]);
      float speed = 0.18;
      float maxR = 0.18;
      // Ripple cycles every (maxR / speed * 2) seconds; offset per anchor
      float phase = mod(uTime * 0.5 + float(i) * 0.37, 1.0);
      float ringR = phase * maxR;
      float ringWidth = 0.008;
      float ring = exp(-pow((d - ringR) / ringWidth, 2.0));
      // Ring fades as it expands
      float ringFade = 1.0 - phase;

      // Static core dot at the anchor itself
      float anchorCore = exp(-d * 90.0) * 0.85;

      float anchorIntensity = (ring * ringFade * 0.45 + anchorCore) * aActive;
      col += vec3(1.0, 0.85, 0.3) * anchorIntensity;
      alpha = max(alpha, anchorIntensity);
    }

    gl_FragColor = vec4(col, alpha);
  }
`;

function ShaderQuad({ progressRef, penPosRef, anchorsRef, anchorActiveRef, aspectRef }) {
  const materialRef = useRef(null);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uProgress: { value: 0 },
      uPenPos: { value: new THREE.Vector2(0.5, 0.5) },
      uAnchors: { value: [new THREE.Vector2(), new THREE.Vector2(), new THREE.Vector2()] },
      uAnchorActive: { value: [0, 0, 0] },
      uAspect: { value: 1 },
    }),
    []
  );

  useFrame((state) => {
    if (!materialRef.current) return;
    const u = materialRef.current.uniforms;
    u.uTime.value = state.clock.getElapsedTime();
    u.uProgress.value = progressRef.current;
    u.uPenPos.value.set(penPosRef.current.x, penPosRef.current.y);
    u.uAnchors.value[0].set(anchorsRef.current[0].x, anchorsRef.current[0].y);
    u.uAnchors.value[1].set(anchorsRef.current[1].x, anchorsRef.current[1].y);
    u.uAnchors.value[2].set(anchorsRef.current[2].x, anchorsRef.current[2].y);
    u.uAnchorActive.value[0] = anchorActiveRef.current[0];
    u.uAnchorActive.value[1] = anchorActiveRef.current[1];
    u.uAnchorActive.value[2] = anchorActiveRef.current[2];
    u.uAspect.value = aspectRef.current;
  });

  return (
    <mesh>
      <planeGeometry args={[1, 1]} />
      <shaderMaterial
        ref={materialRef}
        uniforms={uniforms}
        vertexShader={VERTEX}
        fragmentShader={FRAGMENT}
        transparent
        depthWrite={false}
        depthTest={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

/**
 * Public component. Renders an absolutely-positioned WebGL canvas inside
 * its parent. Caller passes the live values via refs (mutated outside
 * React to avoid re-renders at 60fps).
 *
 * Caller is responsible for sizing the parent and ensuring it has
 * `position: relative` so the absolute fill works.
 */
export default function EquityShaderOverlay({
  progressRef,
  penPosRef,
  anchorsRef,
  anchorActiveRef,
  aspectRef,
}) {
  const containerRef = useRef(null);

  // Kick R3F's resize observer so the Canvas measures the parent's real box
  useEffect(() => {
    const t = setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
    }, 100);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      ref={containerRef}
      className="pointer-events-none absolute inset-0"
      style={{
        width: "100%",
        height: "100%",
        // Additive blending in the shader handles the glow combination
      }}
    >
      <Canvas
        camera={{ position: [0, 0, 1], fov: 50 }}
        dpr={[1, 1.5]}
        gl={{
          antialias: false, // shader is soft, no jagged edges
          alpha: true,
          premultipliedAlpha: false,
          powerPreference: "high-performance",
        }}
        style={{ width: "100%", height: "100%", display: "block" }}
        resize={{ scroll: false, debounce: { scroll: 0, resize: 0 } }}
      >
        <ShaderQuad
          progressRef={progressRef}
          penPosRef={penPosRef}
          anchorsRef={anchorsRef}
          anchorActiveRef={anchorActiveRef}
          aspectRef={aspectRef}
        />
      </Canvas>
    </div>
  );
}
