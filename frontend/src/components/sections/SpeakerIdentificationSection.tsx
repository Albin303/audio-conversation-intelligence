'use client';

import { Loader2, MessagesSquare, UserRound, Volume2 } from 'lucide-react';
import { useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card } from '@/components/ui/Card';
import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/lib/utils';

function formatTimestamp(seconds?: number | null) {
  if (seconds == null || Number.isNaN(seconds)) return null;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function SpeakerIdentificationSection() {
  const features = useAppStore((s) => s.features);
  const isExtracting = useAppStore((s) => s.isExtracting);

  const turns = useMemo(() => features?.diarizedTranscript ?? [], [features?.diarizedTranscript]);
  const speakerCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const turn of turns) {
      counts[turn.speaker] = (counts[turn.speaker] ?? 0) + 1;
    }
    return counts;
  }, [turns]);

  const uniqueSpeakers = Object.keys(speakerCounts);

  return (
    <section
      id="speakers"
      className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28"
    >
      <Reveal>
        <SectionHeader
          eyebrow="Diarization"
          title="Speaker Identification"
          description="Conversation turns attributed to each speaker after transcription."
          align="center"
        />
      </Reveal>

      {isExtracting ? (
        <Reveal delay={0.08}>
          <Card className="flex h-64 flex-col items-center justify-center gap-4" padding="lg">
            <Loader2 className="h-8 w-8 animate-spin text-nexus-accent" />
            <p className="text-sm font-medium text-nexus-fg">Identifying speakers…</p>
          </Card>
        </Reveal>
      ) : turns.length > 0 ? (
        <div className="space-y-6">
          <Reveal delay={0.06}>
            <div className="flex flex-wrap items-center justify-center gap-3">
              {uniqueSpeakers.map((speaker) => {
                const isCustomer = speaker === 'Customer';
                return (
                  <div
                    key={speaker}
                    className={cn(
                      'inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium',
                      isCustomer
                        ? 'border-nexus-accent/25 bg-nexus-accent/10 text-nexus-accent'
                        : 'border-nexus-secondary/25 bg-nexus-secondary/10 text-nexus-secondary',
                    )}
                  >
                    <UserRound className="h-3.5 w-3.5" />
                    {speaker}
                    <span className="text-xs opacity-70">· {speakerCounts[speaker]} turns</span>
                  </div>
                );
              })}
              {features?.audioQuality && (
                <div className="inline-flex items-center gap-2 rounded-full border border-nexus-border bg-nexus-card px-4 py-2 text-sm text-nexus-muted">
                  <Volume2 className="h-3.5 w-3.5" />
                  Audio {features.audioQuality.label}
                  {typeof features.audioQuality.confidence === 'number' &&
                    ` · ${Math.round(features.audioQuality.confidence * 100)}%`}
                </div>
              )}
            </div>
          </Reveal>

          <div className="grid gap-3 md:grid-cols-2">
            {turns.map((turn, index) => {
              const isCustomer = turn.speaker === 'Customer';
              const timestamp =
                formatTimestamp(turn.start) ??
                (turn.end != null ? formatTimestamp(turn.end) : null);

              return (
                <Reveal key={`${turn.speaker}-${index}`} delay={0.04 * Math.min(index, 8)}>
                  <Card
                    padding="md"
                    className={cn(
                      'h-full transition-colors',
                      isCustomer
                        ? 'border-nexus-accent/20 bg-nexus-accent/[0.03]'
                        : 'border-nexus-secondary/20 bg-nexus-secondary/[0.03]',
                    )}
                  >
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div
                          className={cn(
                            'flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white',
                            isCustomer ? 'bg-nexus-accent' : 'bg-nexus-secondary',
                          )}
                        >
                          {isCustomer ? 'C' : 'A'}
                        </div>
                        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-nexus-fg">
                          {turn.speaker}
                        </span>
                      </div>
                      {timestamp && (
                        <span className="font-mono text-[10px] text-nexus-muted">{timestamp}</span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-nexus-fg">{turn.text}</p>
                  </Card>
                </Reveal>
              );
            })}
          </div>
        </div>
      ) : (
        <Reveal delay={0.08}>
          <Card
            variant="outline"
            className="flex h-64 flex-col items-center justify-center text-center"
            padding="lg"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-nexus-border bg-nexus-bg text-nexus-muted">
              <MessagesSquare className="h-5 w-5" />
            </div>
            <p className="text-sm font-medium text-nexus-fg">No speaker turns yet</p>
            <p className="mt-1 max-w-sm text-xs text-nexus-muted">
              Upload audio or run feature extraction to see diarized conversation turns here.
            </p>
          </Card>
        </Reveal>
      )}
    </section>
  );
}
