'use client';

import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Card } from '@/components/ui/Card';

const STACK = [
  {
    category: 'Frontend',
    items: [
      { name: 'Next.js 14', role: 'App Router dashboard' },
      { name: 'React 18 + TypeScript', role: 'Typed UI components' },
      { name: 'Tailwind CSS', role: 'Design system & layout' },
      { name: 'Zustand', role: 'Pipeline state management' },
      { name: 'Framer Motion + Lenis', role: 'Motion & smooth scroll' },
      { name: 'React Three Fiber', role: 'Hero visualization' },
    ],
  },
  {
    category: 'API & Services',
    items: [
      { name: 'FastAPI', role: 'REST API & job polling' },
      { name: 'Uvicorn', role: 'ASGI server' },
      { name: 'SQLite', role: 'Jobs, conversations, alerts' },
      { name: 'Structured logging', role: 'Request ID + JSON logs' },
    ],
  },
  {
    category: 'Audio & ML Pipeline',
    items: [
      { name: 'Whisper', role: 'Speech-to-text transcription' },
      { name: 'Pyannote', role: 'Speaker diarization' },
      { name: 'LLaMA 3 (Groq)', role: 'Feature extraction & summaries' },
      { name: 'XGBoost', role: 'Conversion probability scoring' },
      { name: 'spaCy + VADER', role: 'NLP fallback & sentiment' },
    ],
  },
  {
    category: 'Infrastructure',
    items: [
      { name: 'Docker Compose', role: 'Multi-service orchestration' },
      { name: 'Split Dockerfiles', role: 'API, audio, ML, frontend images' },
      { name: 'Persistent volumes', role: 'Uploads, database, logs' },
      { name: 'Background workers', role: 'Queued audio & ML processing' },
    ],
  },
];

export function TechnologyStackSection() {
  return (
    <section id="technology" className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28">
      <Reveal>
        <SectionHeader
          eyebrow="Engineering"
          title="Technology Stack"
          description="Production components used across the frontend, API, ML pipeline, and deployment layer."
          align="center"
        />
      </Reveal>

      <div className="grid gap-5 md:grid-cols-2">
        {STACK.map((group, groupIndex) => (
          <Reveal key={group.category} delay={0.05 * groupIndex}>
            <Card padding="lg" className="h-full">
              <h3 className="mb-5 text-sm font-semibold text-nexus-fg">{group.category}</h3>
              <ul className="space-y-3">
                {group.items.map((item) => (
                  <li
                    key={item.name}
                    className="flex items-start justify-between gap-4 border-b border-nexus-border/60 pb-3 last:border-0 last:pb-0"
                  >
                    <span className="text-sm font-medium text-nexus-fg">{item.name}</span>
                    <span className="text-right text-xs text-nexus-muted">{item.role}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
