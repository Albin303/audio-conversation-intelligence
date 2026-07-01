'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, ChevronDown } from 'lucide-react';
import Hls from 'hls.js';
import { scrollToSection } from '@/config/navigation';
import { Reveal } from '@/components/primitives/Reveal';
import { MagneticButton } from '@/components/primitives/MagneticButton';
import { useReducedMotion } from '@/hooks/useReducedMotion';

// The silky purple/blue wave video — only lives in the hero
const HLS_SRC = 'https://stream.mux.com/8wrHPCX2dC3msyYU9ObwqNdm00u3ViXvOSHUMRYSEe5Q.m3u8';

const statChips = [
  { label: '99.2%', sub: 'Transcription Accuracy' },
  { label: '< 2s',  sub: 'Avg. Latency' },
  { label: 'Multi-speaker', sub: 'Auto Diarization' },
];

export function HeroSection() {
  const reducedMotion = useReducedMotion();
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (Hls.isSupported()) {
      const hls = new Hls({ startLevel: -1 });
      hls.loadSource(HLS_SRC);
      hls.attachMedia(video);
      return () => hls.destroy();
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = HLS_SRC;
    }
  }, []);

  return (
    <section
      id="hero"
      className="relative flex min-h-[calc(100vh-3.5rem)] items-center justify-center overflow-hidden lg:min-h-screen"
    >
      {/* ── Full-bleed video background ── */}
      <video
        ref={videoRef}
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 h-full w-full object-cover z-0"
      />

      {/* Dark vignette — protects readability on all sides */}
      <div
        className="absolute inset-0 z-[1] pointer-events-none"
        style={{
          background: [
            'linear-gradient(to bottom, rgba(3,7,18,0.65) 0%, rgba(3,7,18,0.25) 40%, rgba(3,7,18,0.50) 75%, rgba(3,7,18,0.90) 100%)',
          ].join(', '),
        }}
      />

      {/* Left/right darkening so side-nav text isn't lost */}
      <div
        className="absolute inset-0 z-[1] pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse at center, transparent 40%, rgba(3,7,18,0.55) 100%)',
        }}
      />

      {/* ── Content ── */}
      <div className="relative z-10 mx-auto flex w-full max-w-5xl flex-col items-center justify-center text-center px-6 py-24 md:px-10 lg:px-12 lg:py-32">

        <Reveal>
          <span className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/[0.07] px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-white/80 backdrop-blur-md">
            Next-Gen Audio Intelligence
          </span>
        </Reveal>

        <Reveal delay={0.06}>
          <h1 className="font-heading text-balance text-4xl font-bold leading-[1.1] tracking-tight text-white sm:text-6xl lg:text-[5rem]">
            Transform Conversations&nbsp;into{' '}
            <span className="bg-gradient-to-r from-violet-300 via-blue-300 to-cyan-300 bg-clip-text text-transparent">
              Predictive Intelligence
            </span>
          </h1>
        </Reveal>

        <Reveal delay={0.12}>
          <p className="mt-8 max-w-xl text-lg leading-relaxed text-white/60 text-pretty">
            Upload your sales calls, extract high-value features, and predict
            conversion outcomes with extreme accuracy using our cutting-edge AI&nbsp;models.
          </p>
        </Reveal>

        <Reveal delay={0.18}>
          <div className="mt-10 flex flex-wrap gap-4 items-center justify-center">
            <MagneticButton onClick={() => scrollToSection('live-stream')}>
              Start Analyzing Now
              <ArrowRight className="h-4 w-4" />
            </MagneticButton>
            <MagneticButton variant="ghost" onClick={() => scrollToSection('prediction')}>
              View Predictions
            </MagneticButton>
          </div>
        </Reveal>

        {/* Stat chips */}
        <Reveal delay={0.24} className="w-full">
          <div className="mt-20 grid grid-cols-1 gap-6 sm:grid-cols-3 w-full max-w-3xl mx-auto">
            {statChips.map((chip) => (
              <div
                key={chip.label}
                className="rounded-2xl border border-white/10 bg-white/[0.06] backdrop-blur-md p-6 flex flex-col items-center justify-center text-center transition-all duration-300 hover:scale-[1.03] hover:border-violet-400/40"
              >
                <span className="text-2xl font-extrabold text-white">{chip.label}</span>
                <span className="text-[10px] text-white/50 uppercase tracking-[0.16em] mt-2 font-bold">{chip.sub}</span>
              </div>
            ))}
          </div>
        </Reveal>
      </div>

      {/* Scroll cue */}
      {!reducedMotion && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.8 }}
          className="absolute bottom-8 left-1/2 z-10 flex -translate-x-1/2 flex-col items-center gap-2"
        >
          <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/40">
            Scroll
          </span>
          <motion.button
            type="button"
            onClick={() => scrollToSection('live-stream')}
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/20 bg-white/10 text-white/50 backdrop-blur-sm transition-colors hover:text-white"
            aria-label="Scroll to live stream"
          >
            <ChevronDown className="h-4 w-4" />
          </motion.button>
        </motion.div>
      )}
    </section>
  );
}
