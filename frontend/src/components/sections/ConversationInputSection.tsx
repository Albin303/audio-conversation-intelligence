'use client';

import { FileText, Wand2, X, MessageSquare, Edit3, User, Headphones } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { scrollToSection } from '@/config/navigation';
import { useAppStore } from '@/store/useAppStore';
import { apiService } from '@/services/api';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { InlineError } from '@/components/ui/InlineError';
import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/lib/utils';

const getSpeakerGradient = (speaker: string) => {
  const s = speaker.toLowerCase();
  if (s === 'customer') return 'from-cyan-500 to-emerald-500';
  if (s === 'agent') return 'from-violet-500 to-indigo-600';
  return 'from-amber-500 to-orange-500';
};

const getSpeakerBgBorder = (speaker: string) => {
  const s = speaker.toLowerCase();
  if (s === 'customer') return 'bg-cyan-500/5 border-cyan-500/20';
  if (s === 'agent') return 'bg-violet-500/5 border-violet-500/20';
  return 'bg-amber-500/5 border-amber-500/20';
};

const getSpeakerTextColor = (speaker: string) => {
  const s = speaker.toLowerCase();
  if (s === 'customer') return 'text-cyan-600 dark:text-cyan-400';
  if (s === 'agent') return 'text-violet-600 dark:text-violet-400';
  return 'text-amber-600 dark:text-amber-400';
};

const getSpeakerRingOffset = (speaker: string, isActive: boolean) => {
  if (!isActive) return '';
  const s = speaker.toLowerCase();
  if (s === 'customer') return 'shadow-[0_0_12px_rgba(6,182,212,0.15)] border-cyan-500/40 bg-cyan-500/10';
  if (s === 'agent') return 'shadow-[0_0_12px_rgba(139,92,246,0.15)] border-violet-500/40 bg-violet-500/10';
  return 'shadow-[0_0_12px_rgba(245,158,11,0.15)] border-amber-500/40 bg-amber-500/10';
};

const getSpeakerAlignment = (speaker: string) => {
  const s = speaker.toLowerCase();
  if (s === 'agent') return 'flex-row-reverse';
  return 'flex-row';
};

export function ConversationInputSection() {
  const { transcription, setTranscription, setExtracting, isExtracting, error, setError, features } =
    useAppStore();
  const [localText, setLocalText] = useState('');
  const [viewMode, setViewMode] = useState<'edit' | 'speaker'>('edit');
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);

  useEffect(() => {
    if (transcription) {
      setLocalText(transcription);
    }
  }, [transcription]);

  // Auto-switch to speaker view when diarized data arrives and set initial active segment
  useEffect(() => {
    if (features?.diarizedTranscript?.length) {
      setViewMode('speaker');
      setActiveSegmentIndex(features.diarizedTranscript.length - 1);
    }
  }, [features?.diarizedTranscript]);

  const timelineSegments = useMemo(() => {
    if (!features?.diarizedTranscript) return [];
    const turns = features.diarizedTranscript;
    const wordCounts = turns.map(t => t.text.split(/\s+/).filter(w => w.length > 0).length);
    const totalWords = wordCounts.reduce((a, b) => a + b, 0) || 1;
    
    return turns.map((turn, index) => ({
      speaker: turn.speaker,
      widthPercent: (wordCounts[index] / totalWords) * 100,
      text: turn.text,
      index,
    }));
  }, [features?.diarizedTranscript]);

  const wordCount = useMemo(
    () => localText.split(/\s+/).filter((w) => w.length > 0).length,
    [localText],
  );
  const charCount = localText.length;
  const approxReadTime = Math.max(1, Math.round(wordCount / 200));

  const handleAnalyze = useCallback(async () => {
    if (!localText.trim()) return;

    setError(null);
    setTranscription(localText);
    setExtracting(true);

    try {
      const isTextUnchanged = localText.trim() === transcription.trim();
      const response = await apiService.extractFeatures(
        localText,
        isTextUnchanged ? (features?.diarizedTranscript ?? undefined) : undefined
      );
      setTranscription(response.transcription);
      useAppStore.getState().setFeatures(response.features);
      useAppStore.getState().setPrediction(null);
      useAppStore.getState().refreshFollowUpAlerts();
      setExtracting(false);
      scrollToSection('speakers');
    } catch (err: unknown) {
      console.error(err);
      setExtracting(false);
      const message =
        err instanceof Error
          ? err.message
          : 'Backend feature extraction failed. Check LLaMA 3 connection.';
      setError(message);
    }
  }, [localText, setTranscription, setExtracting, setError]);

  const handleClear = () => {
    setLocalText('');
    setTranscription('');
    setViewMode('edit');
  };

  const showError = error && error.toLowerCase().includes('feature extraction');
  const hasDiarized = (features?.diarizedTranscript?.length ?? 0) > 0;

  return (
    <section
      id="input"
      className="relative mx-auto flex min-h-[70vh] max-w-5xl flex-col justify-center px-6 py-20 md:px-10 md:py-28"
    >
      <Reveal>
        <SectionHeader
          eyebrow="Transcription"
          title="Speech Recognition"
          description="Review and edit the transcript produced by Whisper, or paste text to re-run analysis."
        />
      </Reveal>

      {showError && (
        <Reveal className="mb-6">
          <InlineError message={error} onDismiss={() => setError(null)} />
        </Reveal>
      )}

      <Reveal delay={0.08}>
        <Card padding="none" className="overflow-hidden">
          {/* Mini Waveform Visualization */}
          <div className="flex items-center justify-center gap-0.5 h-6 bg-slate-50/40 dark:bg-slate-950/20 border-b border-nexus-border/50 px-5 overflow-hidden select-none pointer-events-none">
            {Array.from({ length: 75 }).map((_, i) => {
              const centerDist = Math.abs(i - 37) / 37;
              const envelope = Math.max(0.2, 1 - centerDist * centerDist);
              const height = (Math.sin(i * 0.15) * 6 + 10) * envelope;
              return (
                <div
                  key={i}
                  className="w-1 rounded-full bg-gradient-to-t from-blue-600 to-indigo-500 origin-center animate-wave-bar"
                  style={{
                    height: `${height}px`,
                    animationDelay: `${i * 0.02}s`,
                    animationDuration: `${0.7 + (i % 5) * 0.15}s`,
                  }}
                />
              );
            })}
          </div>

          {/* Header */}
          <div className="flex items-center justify-between border-b border-nexus-border px-5 py-4">
            <div className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
              <FileText className="h-3.5 w-3.5" />
              Transcript
            </div>

            <div className="flex items-center gap-2">
              {/* Speaker / Edit toggle — only shown when diarized data is available */}
              {hasDiarized && (
                <div className="flex items-center rounded-lg border border-nexus-border overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setViewMode('speaker')}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold transition-colors',
                      viewMode === 'speaker'
                        ? 'bg-nexus-accent/10 text-nexus-accent'
                        : 'text-nexus-muted hover:text-nexus-fg',
                    )}
                  >
                    <MessageSquare className="h-3 w-3" />
                    Speakers
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('edit')}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold transition-colors border-l border-nexus-border',
                      viewMode === 'edit'
                        ? 'bg-nexus-accent/10 text-nexus-accent'
                        : 'text-nexus-muted hover:text-nexus-fg',
                    )}
                  >
                    <Edit3 className="h-3 w-3" />
                    Edit
                  </button>
                </div>
              )}

              {localText && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-nexus-muted transition-colors hover:text-red-500"
                >
                  <X className="h-3 w-3" />
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Body */}
          <AnimatePresence mode="wait">
            {viewMode === 'speaker' && hasDiarized ? (
              <motion.div
                key="speaker"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="px-5 py-5 space-y-4 max-h-[480px] overflow-y-auto"
              >
                {/* Speaker Timeline Strip */}
                {timelineSegments.length > 0 && (
                  <div className="mb-6 p-4 rounded-xl border border-nexus-border bg-nexus-bg/50 backdrop-blur-md">
                    <div className="flex items-center justify-between text-xs text-nexus-muted mb-2">
                      <span className="font-semibold uppercase tracking-wider">Conversation Timeline</span>
                      <span className="font-mono">
                        Active: {activeSegmentIndex !== null ? timelineSegments[activeSegmentIndex]?.speaker : 'None'}
                      </span>
                    </div>
                    
                    <div className="flex h-6 w-full rounded-md overflow-hidden bg-slate-200/50 dark:bg-slate-800/50 p-0.5 gap-0.5 border border-nexus-border/50">
                      {timelineSegments.map((seg, idx) => {
                        const isActive = activeSegmentIndex === idx;
                        const showLabel = seg.widthPercent > 12;
                        return (
                          <div
                            key={idx}
                            className={cn(
                              "h-full rounded-sm transition-all duration-300 relative cursor-pointer flex items-center justify-center overflow-hidden text-[9px] font-bold text-white uppercase tracking-wider select-none bg-gradient-to-r",
                              getSpeakerGradient(seg.speaker),
                              isActive ? "ring-2 ring-nexus-accent ring-offset-1 dark:ring-offset-slate-900 z-10 scale-y-105" : ""
                            )}
                            style={{ width: `${seg.widthPercent}%` }}
                            onClick={() => {
                              setActiveSegmentIndex(idx);
                              const bubbleEl = document.getElementById(`bubble-${idx}`);
                              if (bubbleEl) {
                                bubbleEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                              }
                            }}
                          >
                            {showLabel && (
                              <span className="truncate px-1 opacity-90">
                                {seg.speaker}
                              </span>
                            )}
                            
                            {isActive && (
                              <span className="absolute inset-0 rounded-sm bg-white/20 animate-pulse pointer-events-none" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                    
                    <div className="flex gap-4 items-center mt-2 px-1 text-[10px] font-semibold text-nexus-muted uppercase tracking-widest flex-wrap">
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600" />
                        <span>Agent</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-gradient-to-br from-cyan-500 to-emerald-500" />
                        <span>Customer</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-gradient-to-br from-amber-500 to-orange-500" />
                        <span>Guest</span>
                      </div>
                    </div>
                  </div>
                )}

                {features!.diarizedTranscript!.map((turn, index) => {
                  const isAgent = turn.speaker.toLowerCase() === 'agent';
                  return (
                    <motion.div
                      key={`${turn.speaker}-${index}`}
                      id={`bubble-${index}`}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35, delay: Math.min(index * 0.04, 0.4) }}
                      className={`flex gap-3 ${getSpeakerAlignment(turn.speaker)}`}
                    >
                      {/* Avatar */}
                      <div
                        className={cn(
                          'shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-white shadow-sm relative transition-all duration-300 bg-gradient-to-br',
                          getSpeakerGradient(turn.speaker),
                          activeSegmentIndex === index && 'ring-2 ring-nexus-accent ring-offset-2 dark:ring-offset-slate-900 scale-105'
                        )}
                        title={turn.speaker}
                        onClick={() => setActiveSegmentIndex(index)}
                      >
                        {activeSegmentIndex === index && (
                          <span className="absolute -inset-1 rounded-full ring-2 ring-nexus-accent/50 animate-ping pointer-events-none" />
                        )}
                        {isAgent ? (
                          <Headphones className="h-4 w-4" />
                        ) : (
                          <User className="h-4 w-4" />
                        )}
                      </div>
 
                      {/* Bubble */}
                      <div
                        className={cn(
                          'relative max-w-[78%] rounded-2xl border px-4 py-3 transition-all duration-300 cursor-pointer',
                          getSpeakerBgBorder(turn.speaker),
                          activeSegmentIndex === index && getSpeakerRingOffset(turn.speaker, true)
                        )}
                        onClick={() => setActiveSegmentIndex(index)}
                      >
                        {/* Speaker label */}
                        <div
                          className={cn(
                            'text-[10px] font-bold uppercase tracking-[0.18em] mb-1.5 flex items-center gap-1.5',
                            getSpeakerTextColor(turn.speaker)
                          )}
                        >
                          <span className={cn('h-1.5 w-1.5 rounded-full bg-current')} />
                          {turn.speaker}
                        </div>
                        <p className="text-sm text-nexus-fg leading-relaxed">{turn.text}</p>
                      </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            ) : (
              <motion.textarea
                key="edit"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                value={localText}
                onChange={(e) => setLocalText(e.target.value)}
                placeholder="Upload audio to populate the transcript, or paste conversation text here…"
                className="min-h-[280px] w-full resize-none border-0 bg-transparent px-5 py-4 text-base leading-relaxed text-nexus-fg placeholder:text-nexus-muted focus:outline-none focus:ring-0 md:text-lg"
              />
            )}
          </AnimatePresence>

          {/* Footer */}
          <div className="flex flex-col gap-4 border-t border-nexus-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-2">
              <span className="rounded-full border border-nexus-border bg-nexus-bg px-3 py-1 font-mono text-[11px] font-medium text-nexus-muted">
                {wordCount.toLocaleString()} words
              </span>
              <span className="rounded-full border border-nexus-border bg-nexus-bg px-3 py-1 font-mono text-[11px] font-medium text-nexus-muted">
                {charCount.toLocaleString()} chars
              </span>
              <span className="rounded-full border border-nexus-accent/20 bg-nexus-accent/10 px-3 py-1 text-[11px] font-medium text-nexus-accent">
                ~{approxReadTime} min read
              </span>
              {hasDiarized && (
                <span className="rounded-full border border-violet-500/20 bg-violet-500/10 px-3 py-1 text-[11px] font-medium text-violet-600 dark:text-violet-400">
                  {features!.diarizedTranscript!.length} speaker turns
                </span>
              )}
            </div>

            <Button
              onClick={handleAnalyze}
              disabled={!localText.trim() || isExtracting}
              className="shrink-0"
            >
              <Wand2 className="h-4 w-4" />
              {isExtracting ? 'Analyzing…' : 'Run Analysis'}
            </Button>
          </div>
        </Card>
      </Reveal>
    </section>
  );
}
