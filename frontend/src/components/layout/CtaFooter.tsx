'use client';

import { ArrowUpRight } from 'lucide-react';

export function CtaFooter() {
  return (
    <section
      className="relative py-32 px-6 md:px-16 lg:px-24 text-center overflow-hidden w-full"
      style={{
        background:
          'linear-gradient(to bottom, #030712 0%, #070d1f 50%, #030712 100%)',
      }}
    >
      {/* Subtle radial glow — no video */}
      <div
        className="absolute inset-0 pointer-events-none z-0"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% 60%, rgba(109,40,217,0.12) 0%, transparent 70%)',
        }}
      />

      {/* Top fade from whatever section is above */}
      <div
        className="absolute top-0 left-0 right-0 z-[1] pointer-events-none"
        style={{ height: 120, background: 'linear-gradient(to bottom, #030712, transparent)' }}
      />
      {/* Bottom fade */}
      <div
        className="absolute bottom-0 left-0 right-0 z-[1] pointer-events-none"
        style={{ height: 80, background: 'linear-gradient(to top, #030712, transparent)' }}
      />

      {/* Content */}
      <div className="relative z-10">
        <h2 className="text-5xl md:text-6xl lg:text-7xl font-heading italic text-white tracking-tight leading-[1.0] max-w-3xl mx-auto mb-4">
          Ready to transform your conversations?
        </h2>
        <p className="text-white/50 font-body font-light text-sm md:text-base max-w-xl mx-auto mb-8">
          Start analyzing sales calls with AI&#8209;powered diarization, sentiment analysis, and predictive scoring — in minutes.
        </p>
        <div className="flex items-center justify-center gap-6">
          <button className="liquid-glass-strong rounded-full px-6 py-3 text-sm font-medium text-white flex items-center gap-2 hover:bg-white/10 transition-all font-body">
            Get Started
            <ArrowUpRight className="h-5 w-5" />
          </button>
          <button className="bg-white text-black rounded-full px-6 py-3 text-sm font-medium flex items-center gap-2 hover:bg-white/90 transition-colors font-body">
            View Demo
            <ArrowUpRight className="h-4 w-4" />
          </button>
        </div>

        {/* Footer bar */}
        <div className="mt-32 pt-8 border-t border-white/10 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-white/30 font-body font-light text-xs">
            &copy; 2026 Speech Intelligence and Intent Detection. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            {['Privacy', 'Terms', 'Contact'].map((link) => (
              <a
                key={link}
                href="#"
                className="text-white/30 hover:text-white/60 font-body font-light text-xs transition-colors"
              >
                {link}
              </a>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
