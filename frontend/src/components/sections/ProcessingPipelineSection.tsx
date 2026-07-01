'use client';

import { motion } from 'framer-motion';
import {
  BrainCircuit,
  CheckCircle2,
  Circle,
  Loader2,
  Mic,
  UploadCloud,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card } from '@/components/ui/Card';
import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/lib/utils';

type StepStatus = 'pending' | 'active' | 'complete' | 'error';

type PipelineStep = {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

const PIPELINE_STEPS: PipelineStep[] = [
  {
    id: 'upload',
    label: 'Upload',
    description: 'Audio file sent to the API',
    icon: UploadCloud,
  },
  {
    id: 'transcribe',
    label: 'Transcription',
    description: 'Whisper converts speech to text',
    icon: Mic,
  },
  {
    id: 'extract',
    label: 'Feature Extraction',
    description: 'LLaMA analyzes transcript signals',
    icon: BrainCircuit,
  },
  {
    id: 'ready',
    label: 'Pipeline Complete',
    description: 'Transcript and insights ready',
    icon: CheckCircle2,
  },
];

function resolveStepStatuses(state: {
  audioFile: File | null;
  isUploading: boolean;
  uploadProgress: number;
  isExtracting: boolean;
  transcription: string;
  features: unknown;
  error: string | null;
  recordingState: string;
}): Record<string, StepStatus> {
  const {
    audioFile,
    isUploading,
    uploadProgress,
    isExtracting,
    transcription,
    features,
    error,
    recordingState,
  } = state;

  const statuses: Record<string, StepStatus> = {
    upload: 'pending',
    transcribe: 'pending',
    extract: 'pending',
    ready: 'pending',
  };

  if (error && audioFile) {
    if (isUploading || uploadProgress < 100) statuses.upload = 'error';
    else if (!transcription) statuses.transcribe = 'error';
    else statuses.extract = 'error';
    return statuses;
  }

  const liveActive =
    recordingState === 'recording' ||
    recordingState === 'processing' ||
    recordingState === 'analyzing';

  if (!audioFile && !liveActive && !transcription) {
    return statuses;
  }

  if (isUploading) {
    statuses.upload = uploadProgress < 60 ? 'active' : 'complete';
    statuses.transcribe = uploadProgress >= 60 ? 'active' : 'pending';
    return statuses;
  }

  if (isExtracting || recordingState === 'analyzing') {
    statuses.upload = 'complete';
    statuses.transcribe = 'complete';
    statuses.extract = 'active';
    return statuses;
  }

  if (recordingState === 'recording' || recordingState === 'processing') {
    statuses.upload = 'active';
    statuses.transcribe = recordingState === 'processing' ? 'active' : 'pending';
    return statuses;
  }

  if (transcription && features) {
    statuses.upload = 'complete';
    statuses.transcribe = 'complete';
    statuses.extract = 'complete';
    statuses.ready = 'complete';
    return statuses;
  }

  if (transcription) {
    statuses.upload = 'complete';
    statuses.transcribe = 'complete';
    return statuses;
  }

  if (audioFile) {
    statuses.upload = 'complete';
    statuses.transcribe = 'active';
  }

  return statuses;
}

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === 'active') {
    return <Loader2 className="h-4 w-4 animate-spin text-nexus-accent" />;
  }
  if (status === 'complete') {
    return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  }
  if (status === 'error') {
    return <Circle className="h-4 w-4 text-red-500" />;
  }
  return <Circle className="h-4 w-4 text-nexus-border" />;
}

export function ProcessingPipelineSection() {
  const audioFile = useAppStore((s) => s.audioFile);
  const isUploading = useAppStore((s) => s.isUploading);
  const uploadProgress = useAppStore((s) => s.uploadProgress);
  const isExtracting = useAppStore((s) => s.isExtracting);
  const transcription = useAppStore((s) => s.transcription);
  const features = useAppStore((s) => s.features);
  const error = useAppStore((s) => s.error);
  const recordingState = useAppStore((s) => s.recordingState);

  const stepStatuses = useMemo(
    () =>
      resolveStepStatuses({
        audioFile,
        isUploading,
        uploadProgress,
        isExtracting,
        transcription,
        features,
        error,
        recordingState,
      }),
    [audioFile, isUploading, uploadProgress, isExtracting, transcription, features, error, recordingState],
  );

  const activeIndex = PIPELINE_STEPS.findIndex((step) => stepStatuses[step.id] === 'active');
  const progress =
    activeIndex >= 0
      ? ((activeIndex + 0.5) / PIPELINE_STEPS.length) * 100
      : stepStatuses.ready === 'complete'
        ? 100
        : 0;

  const statusLabel = useMemo(() => {
    if (error && audioFile) return 'Pipeline encountered an error';
    if (stepStatuses.ready === 'complete') return 'All stages complete';
    if (isExtracting || recordingState === 'analyzing') return 'Extracting features…';
    if (isUploading) return 'Uploading and transcribing…';
    if (recordingState === 'recording') return 'Capturing live audio…';
    if (recordingState === 'processing') return 'Processing captured audio…';
    if (!audioFile && !transcription) return 'Waiting for audio input';
    return 'Pipeline idle';
  }, [audioFile, error, isExtracting, isUploading, recordingState, stepStatuses.ready, transcription]);

  return (
    <section id="processing" className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28">
      <Reveal>
        <SectionHeader
          eyebrow="Pipeline"
          title="Audio Processing"
          description="Track each stage as your recording moves from upload through transcription and feature extraction."
          align="center"
        />
      </Reveal>

      <Reveal delay={0.08}>
        <Card className="overflow-hidden" padding="lg">
          <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-nexus-fg">{statusLabel}</p>
              <p className="mt-1 text-xs text-nexus-muted">
                {audioFile
                  ? `${audioFile.name} · ${(audioFile.size / (1024 * 1024)).toFixed(2)} MB`
                  : recordingState !== 'idle'
                    ? 'Live capture session'
                    : 'No active job'}
              </p>
            </div>
            {(isUploading || isExtracting || recordingState !== 'idle') && (
              <span className="inline-flex items-center gap-2 rounded-full border border-nexus-accent/20 bg-nexus-accent/10 px-3 py-1 text-xs font-medium text-nexus-accent">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-nexus-accent" />
                In progress
              </span>
            )}
          </div>

          <div className="relative mb-10 hidden h-1 overflow-hidden rounded-full bg-nexus-border/60 sm:block">
            <motion.div
              className="h-full rounded-full bg-nexus-accent"
              initial={false}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>

          <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PIPELINE_STEPS.map((step, index) => {
              const status = stepStatuses[step.id];
              const Icon = step.icon;

              return (
                <li key={step.id}>
                  <div
                    className={cn(
                      'relative h-full rounded-2xl border p-5 transition-colors duration-300',
                      status === 'active' && 'border-nexus-accent/40 bg-nexus-accent/5',
                      status === 'complete' && 'border-emerald-500/25 bg-emerald-500/5',
                      status === 'error' && 'border-red-500/25 bg-red-500/5',
                      status === 'pending' && 'border-nexus-border bg-nexus-card/40',
                    )}
                  >
                    <div className="mb-4 flex items-center justify-between">
                      <div
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-xl border',
                          status === 'active'
                            ? 'border-nexus-accent/30 bg-nexus-accent/10 text-nexus-accent'
                            : status === 'complete'
                              ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600'
                              : 'border-nexus-border bg-nexus-bg text-nexus-muted',
                        )}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <StatusIcon status={status} />
                    </div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
                      Step {index + 1}
                    </p>
                    <h3 className="mt-1 text-sm font-semibold text-nexus-fg">{step.label}</h3>
                    <p className="mt-2 text-xs leading-relaxed text-nexus-muted">{step.description}</p>
                  </div>
                </li>
              );
            })}
          </ol>

          {transcription && (
            <div className="mt-8 rounded-2xl border border-nexus-border bg-nexus-bg/50 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
                Latest output
              </p>
              <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-nexus-fg">
                {transcription}
              </p>
            </div>
          )}
        </Card>
      </Reveal>
    </section>
  );
}
