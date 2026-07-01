'use client';

import { useRef, useEffect } from 'react';
import Image from 'next/image';
import { AlertTriangle, ArrowRight, BrainCircuit, Loader2, ShieldCheck, UserRound, Zap } from 'lucide-react';
import { scrollToSection } from '@/config/navigation';
import { useAppStore } from '@/store/useAppStore';
import { apiService } from '@/services/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { InlineError } from '@/components/ui/InlineError';
import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';

function NeuralNetworkCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.offsetWidth);
    let height = (canvas.height = canvas.offsetHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    };

    window.addEventListener('resize', handleResize);

    const particleCount = 45;
    const particles: { x: number; y: number; vx: number; vy: number; radius: number }[] = [];

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.7,
        vy: (Math.random() - 0.5) * 0.7,
        radius: Math.random() * 2 + 1.5,
      });
    }

    const connectionDistance = 110;

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw lines
      ctx.lineWidth = 0.8;
      for (let i = 0; i < particleCount; i++) {
        const p1 = particles[i];
        for (let j = i + 1; j < particleCount; j++) {
          const p2 = particles[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < connectionDistance) {
            const alpha = (1 - dist / connectionDistance) * 0.65;
            ctx.strokeStyle = `rgba(59, 130, 246, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }

      // Draw dots
      for (let i = 0; i < particleCount; i++) {
        const p = particles[i];
        
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > width) p.vx = -p.vx;
        if (p.y < 0 || p.y > height) p.vy = -p.vy;

        ctx.fillStyle = '#3b82f6';
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    animationFrameId = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return <canvas ref={canvasRef} className="w-full h-full" />;
}

export function ExtractionSection() {
  const { isExtracting, features, setPredicting, error, setError } = useAppStore();

  const handlePredict = async () => {
    if (!features) return;

    setPredicting(true);
    setError(null);
    try {
      const prediction = await apiService.predictConversion(features);
      useAppStore.getState().setPrediction(prediction);
      setPredicting(false);
      scrollToSection('prediction');
    } catch (err: unknown) {
      console.error(err);
      setPredicting(false);
      const message =
        err instanceof Error
          ? err.message
          : 'Prediction failed. Check that XGBoost API is running.';
      setError(message);
    }
  };

  const showPredictError = error?.includes('Prediction failed');

  return (
    <section id="extraction" className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28">
      <Reveal>
        <SectionHeader
          eyebrow="Extraction"
          title="Conversation Insights"
          description="Key signals, privacy redactions, and objections detected from the transcript."
          align="center"
        />
      </Reveal>

      {features && (
        <Reveal className="mb-8 flex justify-center" delay={0.04}>
          <span className="inline-flex items-center gap-2 rounded-full border border-nexus-border bg-nexus-card px-4 py-1.5 text-xs font-medium text-nexus-muted">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                features.extractionProvider === 'llama' ? 'bg-nexus-secondary' : 'bg-amber-500'
              }`}
            />
            {features.extractionProvider === 'llama' ? 'LLaMA 3 (Groq)' : 'Local fallback'}
          </span>
        </Reveal>
      )}

      {showPredictError && (
        <Reveal className="mb-6 flex justify-center">
          <InlineError message={error!} onDismiss={() => setError(null)} />
        </Reveal>
      )}

      {isExtracting ? (
        <Reveal delay={0.08}>
          <Card className="flex h-64 flex-col items-center justify-center gap-4" padding="lg">
            <Loader2 className="h-8 w-8 animate-spin text-nexus-secondary" />
            <p className="text-sm font-medium text-nexus-fg">Extracting features…</p>
          </Card>
        </Reveal>
      ) : features ? (
        <div className="space-y-6">
          <Reveal delay={0.06}>
            <Card padding="lg">
              <div className="mb-5 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-nexus-border bg-nexus-bg text-nexus-accent">
                  <BrainCircuit className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-nexus-fg">Extracted Signals</h3>
                  <p className="text-xs text-nexus-muted">Products, topics, and labels from LLaMA</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {features.rawFeatures?.length ? (
                  features.rawFeatures.map((f, i) => (
                    <div
                      key={`${f.label}-${f.name}-${i}`}
                      className="rounded-xl border border-nexus-border bg-nexus-bg/60 px-3.5 py-2"
                    >
                      <span className="block text-[10px] font-semibold uppercase tracking-[0.14em] text-nexus-muted">
                        {f.label}
                      </span>
                      <span className="text-sm font-medium capitalize text-nexus-fg">{f.name}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-nexus-muted">No labeled signals detected.</p>
                )}
              </div>
            </Card>
          </Reveal>

          <Reveal delay={0.1}>
            <Card padding="lg">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-nexus-border bg-nexus-bg text-emerald-600">
                    <ShieldCheck className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-nexus-fg">Privacy Redaction</h3>
                    <p className="text-xs text-nexus-muted">PII scrubbed before cloud inference</p>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-600">
                  {features.privacy?.redactionCount ?? 0} item
                  {(features.privacy?.redactionCount ?? 0) === 1 ? '' : 's'} redacted
                </span>
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <div className="mb-3 flex items-center gap-2">
                    <UserRound className="h-4 w-4 text-nexus-muted" />
                    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-nexus-muted">
                      Detected entities
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {features.privacy?.entities?.length ? (
                      features.privacy.entities.map((entity, index) => (
                        <div
                          key={`${entity.type}-${index}`}
                          className="rounded-lg border border-nexus-border bg-nexus-bg/50 px-3 py-2"
                        >
                          <span className="block text-[10px] font-semibold uppercase tracking-[0.12em] text-nexus-muted">
                            {entity.type.replaceAll('_', ' ')}
                          </span>
                          <span className="text-sm font-medium text-nexus-fg">{entity.value}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-nexus-muted">No sensitive entities detected.</p>
                    )}
                  </div>
                </div>

                <div>
                  <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-nexus-muted">
                    Behavioral signals
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { label: 'Intent', value: features.customerBehaviorSummary?.intentSignals ?? 0 },
                      { label: 'Hesitation', value: features.customerBehaviorSummary?.hesitationScore ?? 0 },
                      { label: 'Urgency', value: features.customerBehaviorSummary?.urgencySignals ?? 0 },
                      { label: 'Words', value: features.customerBehaviorSummary?.wordCount ?? 0 },
                    ].map((metric) => (
                      <div
                        key={metric.label}
                        className="rounded-xl border border-nexus-border bg-nexus-bg/50 p-3"
                      >
                        <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-nexus-muted">
                          {metric.label}
                        </span>
                        <p className="mt-1 text-xl font-semibold text-nexus-fg">{metric.value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </Reveal>

          <Reveal delay={0.14}>
            <Card padding="lg">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 text-red-500">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-nexus-fg">Objections</h3>
                  <p className="text-xs text-nexus-muted">Friction points raised in the conversation</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {features.objections.length > 0 ? (
                  features.objections.map((obj, i) => (
                    <span
                      key={i}
                      className="rounded-xl border border-red-500/20 bg-red-500/10 px-3.5 py-2 text-sm text-red-600 dark:text-red-400"
                    >
                      {obj}
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-nexus-muted">No objections detected.</p>
                )}
              </div>
            </Card>
          </Reveal>

          <Reveal delay={0.18} className="flex justify-center pt-4">
            <Button size="lg" onClick={handlePredict} className="group">
              <Zap className="h-4 w-4" />
              Run Conversion Model
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Button>
          </Reveal>
        </div>
      ) : (
        <Reveal delay={0.08}>
          {/* Empty state: brain as animated 3D background */}
          <div className="relative min-h-[420px] rounded-3xl overflow-hidden flex items-center justify-center">
            {/* Neural Network Canvas with Blur */}
            <div className="absolute inset-0 w-full h-full filter blur-[2px] opacity-[0.10] dark:opacity-[0.15] pointer-events-none -z-10">
              <NeuralNetworkCanvas />
            </div>

            {/* Ghost Image of 3D brain */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none -z-10 opacity-[0.08]">
              <Image
                src="/extraction-3d.png"
                alt="AI Semantic Brain Ghost"
                width={380}
                height={380}
                className="select-none filter drop-shadow(0 0 40px rgba(96,165,250,0.2))"
                priority
              />
            </div>

            <div className="relative z-10 w-full max-w-md mx-auto px-4">
              <Card
                variant="outline"
                className="flex flex-col items-center justify-center text-center p-10 bg-white/75 backdrop-blur-xl border-slate-200/80 dark:border-slate-700/50 dark:bg-slate-900/70 shadow-2xl"
                padding="lg"
              >
                <div className="w-14 h-14 rounded-2xl bg-blue-500/10 dark:bg-blue-500/20 flex items-center justify-center mb-5">
                  <BrainCircuit className="h-7 w-7 text-blue-600 dark:text-blue-400" />
                </div>
                <p className="text-xl font-semibold text-slate-900 dark:text-white">Semantic Feature Extraction</p>
                <p className="mt-3 max-w-sm text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                  Speech Intelligence and Intent Detection processes speech transcripts to identify purchase intent, client objections, PII privacy redactions, and customer behavior metrics.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {['Intent Detection', 'PII Redaction', 'Objection Mining', 'Diarization'].map((tag) => (
                    <span key={tag} className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[11px] font-semibold">
                      {tag}
                    </span>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </Reveal>
      )}
    </section>
  );
}
