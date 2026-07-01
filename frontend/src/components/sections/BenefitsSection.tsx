export function BenefitsSection() {
  return (
    <section
      id="benefits"
      className="relative w-full bg-black px-4 sm:px-6 md:px-10 py-12 sm:py-20"
    >
      {/* Section Heading */}
      <h2
        className="text-white text-3xl sm:text-4xl md:text-5xl font-light text-center mb-12 sm:mb-24"
        style={{ letterSpacing: '-0.04em' }}
      >
        Key Benefits
      </h2>

      {/* Three-Column Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">

        {/* ── Card 1: Text Card (Left) ── */}
        <div className="relative h-[380px] sm:h-[460px] rounded-2xl bg-neutral-950 overflow-hidden p-6 sm:p-8">
          {/* Blue blob */}
          <div className="absolute top-1/2 -translate-y-1/2 -left-[420px] h-[460px] w-[460px] rounded-full bg-[#1e3a8a] blur-3xl opacity-40" />

          {/* Content */}
          <div className="relative z-10 flex flex-col h-full">
            <h3 className="text-white text-xl sm:text-2xl font-light leading-tight">
              Preemptive Risks<br />
              Scouting and Reactions
            </h3>
            <p className="mt-12 sm:mt-20 text-[13px] sm:text-[14px] leading-relaxed text-white/70 font-light max-w-[280px]">
              Defense platforms constantly observe bandwidth streams, record files, and machine behaviors to uncover unusual patterns or outliers that could signal a defensive failure.
            </p>
          </div>
        </div>

        {/* ── Card 2: Video Card (Center) ── */}
        <div className="relative h-[380px] sm:h-[460px] rounded-2xl bg-neutral-950 overflow-hidden flex flex-col">
          {/* Top video region — 75% height */}
          <div className="relative w-full overflow-hidden" style={{ height: '75%' }}>
            <video
              autoPlay
              loop
              muted
              playsInline
              className="w-full h-full object-cover block"
            >
              <source
                src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260421_072701_f6a01abb-eb30-4559-9d6e-774362defbc3.mp4"
                type="video/mp4"
              />
            </video>
            {/* Bottom fade — blends video into card bg */}
            <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-b from-transparent to-neutral-950" />
          </div>

          {/* Bottom text region */}
          <div className="flex-1 flex items-center justify-start p-6 sm:p-8">
            <h3 className="text-white text-xl sm:text-2xl font-light leading-tight text-left">
              Know-how and Sectoral<br />
              Awareness
            </h3>
          </div>
        </div>

        {/* ── Card 3: Text Card (Right) ── */}
        <div className="relative h-[380px] sm:h-[460px] rounded-2xl bg-neutral-950 overflow-hidden p-6 sm:p-8">
          {/* Purple blob top-right */}
          <div className="absolute -top-28 -right-28 h-56 w-56 rounded-full bg-[#4c1d95] blur-3xl opacity-50" />
          {/* Accent glow bottom-left */}
          <div className="absolute bottom-0 left-0 h-32 w-48 rounded-full bg-[#6d28d9] blur-3xl opacity-20" />

          {/* Content */}
          <div className="relative z-10 flex flex-col h-full">
            <h3 className="text-white text-xl sm:text-2xl font-light leading-tight">
              Predictive Conversion<br />
              Intelligence
            </h3>
            {/* Stat callout */}
            <div className="mt-8 inline-flex items-baseline gap-2">
              <span className="text-4xl font-semibold text-purple-400" style={{ letterSpacing: '-0.03em' }}>94%</span>
              <span className="text-xs text-white/50 uppercase tracking-widest font-light">accuracy</span>
            </div>
            {/* mt-auto pins paragraph to the bottom */}
            <p className="mt-auto text-[13px] sm:text-[14px] leading-relaxed text-white/70 font-light max-w-[320px]">
              XGBoost models analyse sentiment, hesitation signals, and objection patterns in real-time to predict purchase probability before the call even ends.
            </p>
          </div>
        </div>

      </div>
    </section>
  );
}
