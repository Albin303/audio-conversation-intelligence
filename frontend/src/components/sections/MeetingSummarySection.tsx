'use client';

import { FileText, ListChecks, Loader2 } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { Card } from '@/components/ui/Card';
import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';

export function MeetingSummarySection() {
  const features = useAppStore((s) => s.features);
  const isExtracting = useAppStore((s) => s.isExtracting);
  const summary = features?.conversationSummary;

  return (
    <section id="summary" className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28">
      <Reveal>
        <SectionHeader
          eyebrow="Summary"
          title="Meeting Summary"
          description="Structured overview generated from the conversation transcript."
          align="center"
        />
      </Reveal>

      {isExtracting ? (
        <Reveal delay={0.08}>
          <Card className="flex h-56 flex-col items-center justify-center gap-4" padding="lg">
            <Loader2 className="h-8 w-8 animate-spin text-nexus-accent" />
            <p className="text-sm font-medium text-nexus-fg">Generating summary…</p>
          </Card>
        </Reveal>
      ) : summary ? (
        <div className="space-y-6">
          {summary.provider && (
            <Reveal delay={0.04}>
              <div className="flex justify-center">
                <span className="inline-flex items-center gap-2 rounded-full border border-nexus-border bg-nexus-card px-4 py-1.5 text-xs font-medium text-nexus-muted">
                  <FileText className="h-3.5 w-3.5" />
                  {summary.provider.startsWith('llama') ? 'LLaMA' : 'Local'} summary
                  {typeof summary.confidence === 'number' &&
                    ` · ${Math.round(summary.confidence * 100)}% confidence`}
                </span>
              </div>
            </Reveal>
          )}

          <Reveal delay={0.06}>
            <Card padding="lg">
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
                Overview
              </p>
              <p className="mt-3 text-base leading-relaxed text-nexus-fg">{summary.overview}</p>
            </Card>
          </Reveal>

          <div className="grid gap-4 md:grid-cols-2">
            <Reveal delay={0.08}>
              <Card padding="md" className="h-full">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
                  Customer Need
                </p>
                <p className="mt-2 text-sm leading-relaxed text-nexus-fg">{summary.customerNeed}</p>
              </Card>
            </Reveal>
            <Reveal delay={0.1}>
              <Card padding="md" className="h-full">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
                  Outcome
                </p>
                <p className="mt-2 text-sm leading-relaxed text-nexus-fg">{summary.outcome}</p>
              </Card>
            </Reveal>
          </div>

          <Reveal delay={0.12}>
            <Card padding="lg">
              <div className="mb-4 flex items-center gap-2">
                <ListChecks className="h-4 w-4 text-nexus-accent" />
                <p className="text-sm font-semibold text-nexus-fg">Key Points</p>
              </div>
              <ol className="space-y-3">
                {summary.keyPoints.map((point, index) => (
                  <li
                    key={`${point}-${index}`}
                    className="flex gap-3 rounded-xl border border-nexus-border bg-nexus-bg/50 p-3"
                  >
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-nexus-accent text-[10px] font-bold text-white">
                      {index + 1}
                    </span>
                    <span className="text-sm leading-relaxed text-nexus-fg">{point}</span>
                  </li>
                ))}
              </ol>
            </Card>
          </Reveal>

          <Reveal delay={0.14}>
            <Card padding="md" className="border-nexus-accent/20 bg-nexus-accent/5">
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-accent">
                Next Action
              </p>
              <p className="mt-2 text-sm leading-relaxed text-nexus-fg">{summary.nextAction}</p>
            </Card>
          </Reveal>
        </div>
      ) : (
        <Reveal delay={0.08}>
          <Card
            variant="outline"
            className="flex h-56 flex-col items-center justify-center text-center"
            padding="lg"
          >
            <FileText className="mb-4 h-8 w-8 text-nexus-muted" />
            <p className="text-sm font-medium text-nexus-fg">No summary available</p>
            <p className="mt-1 max-w-sm text-xs text-nexus-muted">
              Run analysis on a transcript to generate a meeting summary.
            </p>
          </Card>
        </Reveal>
      )}
    </section>
  );
}
