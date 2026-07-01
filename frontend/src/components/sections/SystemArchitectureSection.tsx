'use client';

import { ArrowRight } from 'lucide-react';
import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Card } from '@/components/ui/Card';

const LAYERS = [
  {
    title: 'Next.js Dashboard',
    description: 'Single-page workflow UI with section-based navigation and live pipeline state.',
  },
  {
    title: 'FastAPI Service Layer',
    description: 'Versioned `/api/v1` routes with legacy compatibility, middleware, and service boundaries.',
  },
  {
    title: 'Repository Layer',
    description: 'SQLite persistence for conversations, processing jobs, and follow-up alerts.',
  },
  {
    title: 'Worker Boundary',
    description: 'Audio and ML workers process queued jobs independently from the API process.',
  },
];

const FLOW = [
  'Client uploads audio',
  'File stored in uploads/audio',
  'Job written to SQLite',
  'Worker transcribes & diarizes',
  'Features extracted via LLaMA',
  'Prediction scored via XGBoost',
  'Results polled by frontend',
];

export function SystemArchitectureSection() {
  return (
    <section id="architecture" className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28">
      <Reveal>
        <SectionHeader
          eyebrow="System Design"
          title="System Architecture"
          description="Modular monolith with clear separation between API, persistence, and background workers."
          align="center"
        />
      </Reveal>

      <div className="grid gap-8 lg:grid-cols-2">
        <Reveal delay={0.06}>
          <Card padding="lg">
            <h3 className="mb-5 text-sm font-semibold text-nexus-fg">Architecture layers</h3>
            <ol className="space-y-3">
              {LAYERS.map((layer, index) => (
                <li
                  key={layer.title}
                  className="rounded-xl border border-nexus-border bg-nexus-bg/50 p-4"
                >
                  <div className="mb-1 flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-nexus-accent text-[10px] font-bold text-white">
                      {index + 1}
                    </span>
                    <span className="text-sm font-semibold text-nexus-fg">{layer.title}</span>
                  </div>
                  <p className="pl-8 text-xs leading-relaxed text-nexus-muted">{layer.description}</p>
                </li>
              ))}
            </ol>
          </Card>
        </Reveal>

        <Reveal delay={0.1}>
          <Card padding="lg" className="h-full">
            <h3 className="mb-5 text-sm font-semibold text-nexus-fg">Audio processing flow</h3>
            <ol className="space-y-2">
              {FLOW.map((step, index) => (
                <li key={step} className="flex items-center gap-3 text-sm text-nexus-fg">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-nexus-border bg-nexus-card text-[10px] font-semibold text-nexus-muted">
                    {index + 1}
                  </span>
                  <span>{step}</span>
                  {index < FLOW.length - 1 && (
                    <ArrowRight className="ml-auto hidden h-3.5 w-3.5 text-nexus-border sm:block" />
                  )}
                </li>
              ))}
            </ol>

            <div className="mt-8 rounded-xl border border-nexus-border bg-nexus-bg/50 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
                Persistent storage
              </p>
              <ul className="mt-3 space-y-1.5 font-mono text-xs text-nexus-fg">
                <li>uploads/audio/</li>
                <li>uploads/reports/</li>
                <li>database/nexus_ai.db</li>
                <li>logs/nexus_ai.log</li>
              </ul>
            </div>
          </Card>
        </Reveal>
      </div>
    </section>
  );
}
