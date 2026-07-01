import React, { Suspense, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

function ParticleSwarm({ count = 220, tone = 'brand' }) {
  const ref = useRef();

  const { positions, colors } = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const baseColor = new THREE.Color();
    if (tone === 'bull') baseColor.setRGB(0.40, 0.94, 0.50);
    else if (tone === 'info') baseColor.setRGB(0.40, 0.70, 1.00);
    else baseColor.setRGB(1.00, 0.72, 0.20);

    for (let i = 0; i < count; i++) {
      pos[i * 3 + 0] = (Math.random() - 0.5) * 14;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 8;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 6 - 2;
      const j = 0.5 + Math.random() * 0.6;
      col[i * 3 + 0] = baseColor.r * j;
      col[i * 3 + 1] = baseColor.g * j;
      col[i * 3 + 2] = baseColor.b * j;
    }
    return { positions: pos, colors: col };
  }, [count, tone]);

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.getElapsedTime();
    ref.current.rotation.y = t * 0.02;
    ref.current.rotation.x = Math.sin(t * 0.05) * 0.05;
    const posAttr = ref.current.geometry.attributes.position;
    for (let i = 0; i < count; i++) {
      const ix = i * 3 + 1;
      posAttr.array[ix] += Math.sin(t * 0.4 + i) * 0.0008;
    }
    posAttr.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={colors.length / 3}
          array={colors}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.04}
        sizeAttenuation
        vertexColors
        transparent
        opacity={0.85}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

function FloatingShard({ position, scale, rotationSpeed, tone = 'brand' }) {
  const ref = useRef();
  const color = useMemo(() => {
    if (tone === 'bull') return new THREE.Color(0.40, 0.94, 0.50);
    if (tone === 'info') return new THREE.Color(0.40, 0.70, 1.00);
    return new THREE.Color(1.00, 0.72, 0.20);
  }, [tone]);

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.getElapsedTime();
    ref.current.rotation.x = t * rotationSpeed * 0.5;
    ref.current.rotation.y = t * rotationSpeed;
    ref.current.position.y = position[1] + Math.sin(t * 0.6 + position[0]) * 0.3;
  });

  return (
    <mesh ref={ref} position={position} scale={scale}>
      <icosahedronGeometry args={[1, 0]} />
      <meshStandardMaterial
        color={color}
        metalness={0.85}
        roughness={0.15}
        emissive={color}
        emissiveIntensity={0.25}
        transparent
        opacity={0.85}
      />
    </mesh>
  );
}

function Scene({ tone, density }) {
  const shards = useMemo(
    () => [
      { position: [-3.2,  1.4, -1], scale: 0.6,  rot: 0.10 },
      { position: [ 3.5, -0.8, -2], scale: 0.45, rot: 0.14 },
      { position: [ 1.5,  2.0, -3], scale: 0.55, rot: 0.08 },
      { position: [-2.0, -1.6, -2], scale: 0.40, rot: 0.18 },
      { position: [ 0.0,  1.0, -4], scale: 0.70, rot: 0.06 },
      { position: [ 2.4,  1.8, -1], scale: 0.35, rot: 0.20 },
      { position: [-3.8, -0.4, -3], scale: 0.50, rot: 0.12 },
    ],
    [],
  );
  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[-5, 5, 5]} intensity={1.4} color="#ffce7a" />
      <pointLight position={[5, -3, 3]} intensity={0.6} color="#ff9a3c" />
      <ParticleSwarm count={density} tone={tone} />
      {shards.map((s, i) => (
        <FloatingShard
          key={i}
          position={s.position}
          scale={s.scale}
          rotationSpeed={s.rot}
          tone={tone}
        />
      ))}
    </>
  );
}

export function ParticleField({
  tone = 'brand',
  density = 220,
  className,
  style,
}) {
  return (
    <div
      aria-hidden="true"
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        ...style,
      }}
    >
      <Suspense fallback={null}>
        <Canvas
          dpr={[1, 1.5]}
          gl={{ antialias: true, alpha: true, powerPreference: 'low-power' }}
          camera={{ position: [0, 0, 6], fov: 55 }}
          frameloop="always"
          style={{ pointerEvents: 'none' }}
        >
          <Scene tone={tone} density={density} />
        </Canvas>
      </Suspense>
    </div>
  );
}

export default ParticleField;
