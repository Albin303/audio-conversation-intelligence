'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import * as THREE from 'three';

function usePointerParallax(intensity = 0.35) {
  const { camera } = useThree();
  const target = useRef({ x: 0, y: 0 });

  useFrame((state) => {
    const px = state.pointer.x * intensity;
    const py = state.pointer.y * intensity * 0.6;
    target.current.x += (px - target.current.x) * 0.06;
    target.current.y += (py - target.current.y) * 0.06;
    camera.position.x = target.current.x;
    camera.position.y = target.current.y;
    camera.lookAt(0, 0, 0);
  });
}

function IntelligenceCore() {
  const coreRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (coreRef.current) coreRef.current.rotation.y = t * 0.18;
    if (ringRef.current) {
      ringRef.current.rotation.x = Math.PI / 2.4;
      ringRef.current.rotation.z = t * 0.12;
    }
  });

  return (
    <Float speed={1.2} rotationIntensity={0.15} floatIntensity={0.35}>
      <group>
        <mesh ref={coreRef}>
          <icosahedronGeometry args={[1.05, 2]} />
          <meshPhysicalMaterial
            color="#2563EB"
            emissive="#1D4ED8"
            emissiveIntensity={0.15}
            roughness={0.12}
            metalness={0.65}
            transmission={0.55}
            thickness={0.8}
            transparent
            opacity={0.92}
          />
        </mesh>
        <mesh ref={ringRef}>
          <torusGeometry args={[1.55, 0.03, 16, 80]} />
          <meshPhysicalMaterial
            color="#7C3AED"
            roughness={0.2}
            metalness={0.5}
            transmission={0.4}
            transparent
            opacity={0.7}
          />
        </mesh>
      </group>
    </Float>
  );
}

function NeuralParticles() {
  const ref = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const count = 48;
    const pts = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      const radius = 1.8 + Math.random() * 1.4;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      pts[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      pts[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      pts[i * 3 + 2] = radius * Math.cos(phi);
    }
    return pts;
  }, []);

  useFrame((state) => {
    if (!ref.current) return;
    ref.current.rotation.y = state.clock.elapsedTime * 0.04;
    ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.08;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.035}
        color="#60A5FA"
        transparent
        opacity={0.65}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

function WaveformRing() {
  const lineRef = useRef<THREE.LineLoop>(null);
  const positions = useMemo(() => {
    const segments = 64;
    const arr = new Float32Array((segments + 1) * 3);
    for (let i = 0; i <= segments; i += 1) {
      const angle = (i / segments) * Math.PI * 2;
      arr[i * 3] = Math.cos(angle) * 2.1;
      arr[i * 3 + 1] = Math.sin(angle) * 2.1;
      arr[i * 3 + 2] = 0;
    }
    return arr;
  }, []);

  useFrame((state) => {
    if (!lineRef.current) return;
    const pos = lineRef.current.geometry.attributes.position;
    const t = state.clock.elapsedTime;
    for (let i = 0; i < pos.count; i += 1) {
      const angle = (i / pos.count) * Math.PI * 2;
      const wave = Math.sin(angle * 8 + t * 2.2) * 0.08;
      const r = 2.1 + wave;
      pos.setXYZ(i, Math.cos(angle) * r, Math.sin(angle) * r, Math.sin(angle * 4 + t) * 0.06);
    }
    pos.needsUpdate = true;
    lineRef.current.rotation.z = t * 0.05;
  });

  return (
    <lineLoop ref={lineRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial color="#7C3AED" transparent opacity={0.45} />
    </lineLoop>
  );
}

function Scene() {
  usePointerParallax(0.4);

  return (
    <>
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 4, 6]} intensity={0.9} color="#ffffff" />
      <directionalLight position={[-3, -2, 2]} intensity={0.35} color="#7C3AED" />
      <IntelligenceCore />
      <NeuralParticles />
      <WaveformRing />
    </>
  );
}

export function AudioIntelligenceScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 5.2], fov: 42 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
      style={{ background: 'transparent' }}
    >
      <Scene />
    </Canvas>
  );
}
