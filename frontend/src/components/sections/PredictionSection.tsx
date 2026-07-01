'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, LineChart, ListChecks, Loader2, Zap } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { apiService } from '@/services/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { InlineError } from '@/components/ui/InlineError';
import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/lib/utils';

function DataStreamCanvas() {
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

    const streams: { x: number; y: number; speed: number; length: number; opacity: number }[] = [];
    const points: { x: number; y: number; vy: number; radius: number; opacity: number }[] = [];

    // Initialize vertical data stream lines
    const streamCount = Math.floor(width / 24);
    for (let i = 0; i < streamCount; i++) {
      streams.push({
        x: Math.random() * width,
        y: Math.random() * height,
        speed: Math.random() * 1.5 + 0.5,
        length: Math.random() * 80 + 40,
        opacity: Math.random() * 0.15 + 0.05,
      });
    }

    // Initialize floating data points
    const pointCount = 25;
    for (let i = 0; i < pointCount; i++) {
      points.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vy: -(Math.random() * 0.6 + 0.2),
        radius: Math.random() * 2 + 1,
        opacity: Math.random() * 0.35 + 0.1,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw flowing vertical lines (data streams)
      for (const s of streams) {
        s.y += s.speed;
        if (s.y - s.length > height) {
          s.y = -s.length;
          s.x = Math.random() * width;
        }

        const lineGrad = ctx.createLinearGradient(s.x, s.y - s.length, s.x, s.y);
        lineGrad.addColorStop(0, 'rgba(59, 130, 246, 0)');
        lineGrad.addColorStop(1, `rgba(59, 130, 246, ${s.opacity})`);

        ctx.strokeStyle = lineGrad;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y - s.length);
        ctx.lineTo(s.x, s.y);
        ctx.stroke();
      }

      // Draw floating data points
      for (const p of points) {
        p.y += p.vy;
        if (p.y < 0) {
          p.y = height;
          p.x = Math.random() * width;
        }

        ctx.fillStyle = `rgba(59, 130, 246, ${p.opacity})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();

        if (p.radius > 2) {
          ctx.strokeStyle = `rgba(96, 165, 250, ${p.opacity * 0.5})`;
          ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius * 2.5, 0, Math.PI * 2);
          ctx.stroke();
        }
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

export function PredictionSection() {
  const { isPredicting, prediction, features, setPredicting, error, setError } = useAppStore();

  const handlePredict = async () => {
    if (!features) return;

    setPredicting(true);
    setError(null);
    try {
      const result = await apiService.predictConversion(features);
      useAppStore.getState().setPrediction(result);
      setPredicting(false);
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

  const showError = error?.includes('Prediction failed');
  const probabilityLabel =
    prediction && prediction.probability >= 0.7
      ? 'High conversion likelihood'
      : prediction && prediction.probability >= 0.4
        ? 'Moderate conversion likelihood'
        : 'Low conversion likelihood';

  const riskClass =
    prediction?.risk === 'Low'
      ? 'text-emerald-600 border-emerald-500/25 bg-emerald-500/10'
      : prediction?.risk === 'Medium'
        ? 'text-amber-600 border-amber-500/25 bg-amber-500/10'
        : 'text-red-500 border-red-500/25 bg-red-500/10';

  return (
    <section
      id="prediction"
      className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28"
    >
      <Reveal>
        <SectionHeader
          eyebrow="Analytics"
          title="Conversion Dashboard"
          description="XGBoost probability scoring based on extracted conversation features."
          align="center"
        />
      </Reveal>

      {showError && (
        <Reveal className="mb-6 flex justify-center">
          <InlineError message={error!} onDismiss={() => setError(null)} />
        </Reveal>
      )}

      {isPredicting ? (
        <Reveal delay={0.08}>
          <Card className="flex h-72 flex-col items-center justify-center gap-4" padding="lg">
            <Loader2 className="h-8 w-8 animate-spin text-nexus-accent" />
            <p className="text-sm font-medium text-nexus-fg">Running conversion model…</p>
            <p className="text-xs text-nexus-muted">Scoring extracted features</p>
          </Card>
        </Reveal>
      ) : prediction ? (
        <div className="grid gap-6 lg:grid-cols-12">
          <Reveal delay={0.06} className="lg:col-span-5">
            <Card padding="lg" className="flex h-full flex-col items-center justify-center text-center">
              <div className="relative mb-6 h-48 w-48">
                <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="42"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="5"
                    className="text-nexus-border"
                  />
                  <motion.circle
                    cx="50"
                    cy="50"
                    r="42"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="5"
                    strokeDasharray="263.9"
                    initial={{ strokeDashoffset: 263.9 }}
                    animate={{ strokeDashoffset: 263.9 - 263.9 * prediction.probability }}
                    transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                    strokeLinecap="round"
                    className="text-nexus-accent"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-5xl font-semibold tracking-tight text-nexus-fg">
                    {Math.round(prediction.probability * 100)}
                    <span className="text-xl text-nexus-muted">%</span>
                  </span>
                  <span className="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
                    Probability
                  </span>
                </div>
              </div>
              <h3 className="text-lg font-semibold text-nexus-fg">{probabilityLabel}</h3>
              <span
                className={cn(
                  'mt-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold',
                  riskClass,
                )}
              >
                <Zap className="h-3.5 w-3.5" />
                {prediction.risk} risk
              </span>
            </Card>
          </Reveal>

          <div className="flex flex-col gap-6 lg:col-span-7">
            <Reveal delay={0.1}>
              <Card padding="lg">
                <h4 className="mb-4 text-sm font-semibold text-nexus-fg">Model reasoning</h4>
                <ul className="space-y-2.5">
                  {prediction.insights.map((insight, i) => (
                    <li
                      key={i}
                      className="flex gap-3 rounded-xl border border-nexus-border bg-nexus-bg/50 p-3"
                    >
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-nexus-accent text-[10px] font-bold text-white">
                        {i + 1}
                      </span>
                      <span className="text-sm leading-relaxed text-nexus-fg">{insight}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </Reveal>

            {prediction.nextSteps && prediction.nextSteps.length > 0 && (
              <Reveal delay={0.14}>
                <Card padding="lg">
                  <div className="mb-4 flex items-center gap-2">
                    <ListChecks className="h-4 w-4 text-nexus-secondary" />
                    <h4 className="text-sm font-semibold text-nexus-fg">Recommended actions</h4>
                  </div>
                  <ul className="space-y-2.5">
                    {prediction.nextSteps.map((step, i) => (
                      <li
                        key={i}
                        className="flex gap-3 rounded-xl border border-nexus-border bg-nexus-bg/50 p-3"
                      >
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-nexus-secondary text-[10px] font-bold text-white">
                          {i + 1}
                        </span>
                        <span className="text-sm leading-relaxed text-nexus-fg">{step}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              </Reveal>
            )}
          </div>
        </div>
      ) : (
        <Reveal delay={0.08}>
          {/* Empty state: full-section CSS animated background */}
          <div className="relative min-h-[420px] rounded-3xl overflow-hidden flex items-center justify-center">
            {/* Animated data streams canvas */}
            <div className="absolute inset-0 w-full h-full opacity-[0.25] dark:opacity-[0.12] pointer-events-none -z-10">
              <DataStreamCanvas />
            </div>

            <div className="relative z-10 w-full max-w-md mx-auto px-4">
              <Card
                variant="outline"
                className="flex flex-col items-center justify-center text-center p-10 bg-white/75 backdrop-blur-xl border-slate-200/80 dark:border-slate-700/50 dark:bg-slate-900/70 shadow-2xl"
                padding="lg"
              >
                <LineChart className="mb-4 h-8 w-8 text-blue-600 dark:text-blue-400" />
                <p className="text-xl font-semibold text-slate-900 dark:text-white">Conversion Scoring Model</p>
                <p className="mt-3 max-w-sm text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                  {features
                    ? 'Run the XGBoost classifier model to calculate probability scores and actionable follow-up advice.'
                    : 'Upload an audio file and run feature extraction to unlock predictive conversion scoring.'}
                </p>
                {features && (
                  <Button onClick={handlePredict} className="group mt-6">
                    Run Conversion Model
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </Button>
                )}
              </Card>
            </div>
          </div>
        </Reveal>
      )}
    </section>
  );
}
