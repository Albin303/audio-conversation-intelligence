'use client';

import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Card } from '@/components/ui/Card';

const METRICS = [
  {
    label: 'Word Error Rate',
    value: '27.3%',
    note: 'Whisper transcription benchmark',
  },
  {
    label: 'Diarization Error Rate',
    value: '0.0%',
    note: 'Speaker segmentation accuracy',
  },
  {
    label: 'Role Classification',
    value: '100%',
    note: 'Agent vs customer labeling',
  },
  {
    label: 'Lead Scoring Accuracy',
    value: '66.7%',
    note: 'XGBoost conversion model',
  },
  {
    label: 'Sentiment Label Accuracy',
    value: '100%',
    note: 'Dominant sentiment classification',
  },
];

const RUNTIME = [
  { label: 'Benchmark runtime', value: '9.7s' },
  { label: 'Peak memory', value: '536 MB' },
  { label: 'Source', value: 'sprint5_benchmark_report.json' },
];

export function PerformanceSection() {
  return (
    <section id="performance" className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28">
      <Reveal>
        <SectionHeader
          eyebrow="Benchmarks"
          title="Performance"
          description="Measured pipeline metrics from the project benchmark suite — not marketing estimates."
          align="center"
        />
      </Reveal>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {METRICS.map((metric, index) => (
          <Reveal key={metric.label} delay={0.04 * index}>
            <Card padding="md" className="h-full">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-nexus-muted">
                {metric.label}
              </p>
              <p className="mt-2 text-3xl font-semibold tracking-tight text-nexus-fg">{metric.value}</p>
              <p className="mt-2 text-xs leading-relaxed text-nexus-muted">{metric.note}</p>
            </Card>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.2} className="mt-6">
        <Card padding="lg">
          <h3 className="mb-4 text-sm font-semibold text-nexus-fg">Benchmark execution</h3>
          <dl className="grid gap-4 sm:grid-cols-3">
            {RUNTIME.map((item) => (
              <div key={item.label} className="rounded-xl border border-nexus-border bg-nexus-bg/50 p-4">
                <dt className="text-[10px] font-semibold uppercase tracking-[0.14em] text-nexus-muted">
                  {item.label}
                </dt>
                <dd className="mt-1 text-sm font-medium text-nexus-fg">{item.value}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </Reveal>
    </section>
  );
}
