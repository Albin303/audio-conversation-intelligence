'use client';

import dynamic from 'next/dynamic';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const AudioIntelligenceScene = dynamic(
  () =>
    import('@/components/three/AudioIntelligenceScene').then(
      (mod) => mod.AudioIntelligenceScene,
    ),
  {
    ssr: false,
    loading: () => <VisualizationFallback />,
  },
);

function VisualizationFallback() {
  return (
    <div className="relative flex h-full w-full items-center justify-center" aria-hidden>
      <div className="absolute h-48 w-48 rounded-full bg-nexus-accent/10 blur-3xl" />
      <div className="relative flex h-40 w-40 items-center justify-center rounded-full border border-nexus-border/80 bg-nexus-card/50 backdrop-blur-xl">
        <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-nexus-accent/20 to-nexus-secondary/20" />
      </div>
      <div className="absolute inset-0 flex items-center justify-center gap-1">
        {Array.from({ length: 24 }).map((_, i) => (
          <span
            key={i}
            className="w-0.5 rounded-full bg-nexus-accent/40"
            style={{
              height: `${12 + Math.sin(i * 0.8) * 10}px`,
              animation: `wave-bar 1.4s ease-in-out ${i * 0.05}s infinite`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function HeroVisualization() {
  const reducedMotion = useReducedMotion();

  return (
    <div
      className="relative mx-auto aspect-square w-full max-w-md lg:max-w-none lg:h-[min(520px,70vh)]"
      aria-hidden
    >
      <div className="absolute inset-0 rounded-[2rem] border border-nexus-border/60 bg-nexus-card/30 backdrop-blur-sm" />
      <div className="absolute inset-4 rounded-[1.5rem] border border-nexus-border/40" />
      <div className="relative h-full w-full overflow-hidden rounded-[2rem]">
        {reducedMotion ? <VisualizationFallback /> : <AudioIntelligenceScene />}
      </div>
    </div>
  );
}
