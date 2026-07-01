'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, FileAudio, CheckCircle, Loader2, FileAudio2 } from 'lucide-react';
import { useCallback, useState, useEffect, useRef } from 'react';
import { scrollToSection } from '@/config/navigation';
import { useAppStore } from '@/store/useAppStore';
import { apiService } from '@/services/api';
import { TiltCard } from '@/components/primitives/TiltCard';
import { InlineError } from '@/components/ui/InlineError';
import { Reveal } from '@/components/primitives/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Waveform } from '@/components/animations/Waveform';

function WaveformCanvas() {
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

    const barWidth = 4;
    const gap = 3;
    const speed = 0.0015;

    const render = (time: number) => {
      ctx.clearRect(0, 0, width, height);

      // Create gradient for the waveform bars
      const gradient = ctx.createLinearGradient(0, 0, width, 0);
      gradient.addColorStop(0, '#3b82f6'); // blue
      gradient.addColorStop(0.5, '#60a5fa'); // light blue
      gradient.addColorStop(1, '#4f46e5'); // indigo

      ctx.fillStyle = gradient;

      const numBars = Math.ceil(width / (barWidth + gap));
      const centerY = height / 2;

      for (let i = 0; i < numBars; i++) {
        // Calculate a multi-frequency sine wave height
        const x = i * (barWidth + gap);
        // Base sine wave
        const wave1 = Math.sin(i * 0.05 + time * speed) * 0.4;
        // Secondary harmonics to make it organic
        const wave2 = Math.sin(i * 0.12 - time * speed * 0.7) * 0.25;
        const wave3 = Math.cos(i * 0.03 + time * speed * 1.3) * 0.2;
        
        // Sum and scale the wave
        const combined = wave1 + wave2 + wave3;
        
        // Apply a center-hump envelope (bell curve) so the waves are taller in the center of the screen
        const distFromCenter = Math.abs(i - numBars / 2) / (numBars / 2);
        const envelope = Math.max(0, 1 - distFromCenter * distFromCenter); // parabolic envelope
        
        const barHeight = Math.max(4, (combined * 0.7 + 0.3) * (height * 0.4) * envelope);

        const y = centerY - barHeight / 2;
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(x, y, barWidth, barHeight, 2);
        } else {
          ctx.rect(x, y, barWidth, barHeight);
        }
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 -z-10 h-full w-full opacity-[0.08] dark:opacity-[0.12] pointer-events-none"
    />
  );
}

export function UploadSection() {
  const [isDragging, setIsDragging] = useState(false);
  const {
    isUploading,
    uploadProgress,
    audioFile,
    setUploading,
    setUploadProgress,
    setAudioFile,
    setTranscription,
    setExtracting,
    error,
    setError,
  } = useAppStore();

  const handleFile = useCallback(
    async (file: File) => {
      if (!file || !file.type.startsWith('audio/')) {
        alert('Please upload an audio file');
        return;
      }

      setError(null);
      setAudioFile(file);
      setUploading(true);
      setUploadProgress(0);

      const interval = setInterval(() => {
        const current = useAppStore.getState().uploadProgress;
        if (current >= 95) {
          clearInterval(interval);
          setUploadProgress(95);
        } else {
          setUploadProgress(current + 5);
        }
      }, 100);

      try {
        const response = await apiService.uploadAudio(file);
        clearInterval(interval);
        setUploadProgress(100);
        setUploading(false);
        setTranscription(response.transcription);
        setExtracting(true);
        useAppStore.getState().setFeatures(response.features);
        useAppStore.getState().setPrediction(null);
        useAppStore.getState().refreshFollowUpAlerts();
        setExtracting(false);
        setTimeout(() => {
          scrollToSection('processing');
        }, 800);
      } catch (err: unknown) {
        clearInterval(interval);
        setUploading(false);
        console.error(err);
        const message =
          err instanceof Error
            ? err.message
            : 'Backend transcription failed. Please ensure the API is running.';
        setError(message);
        setTimeout(() => {
          scrollToSection('processing');
        }, 800);
      }
    },
    [
      setAudioFile,
      setUploading,
      setUploadProgress,
      setTranscription,
      setExtracting,
      setError,
    ],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const files = e.dataTransfer.files;
      if (files?.length) {
        handleFile(files[0]);
      }
    },
    [handleFile],
  );

  return (
    <section
      id="upload"
      className="relative mx-auto flex min-h-[75vh] max-w-4xl flex-col justify-center px-6 py-24 md:px-10 lg:py-32"
    >
      <WaveformCanvas />
      <Reveal>
        <SectionHeader
          eyebrow="Input"
          title="Upload Audio"
          description="Import your audio files to kick off transcription, diarization, and semantic extraction."
          align="center"
          className="mb-14"
        />
      </Reveal>

      {error && !error.includes('feature extraction') && !error.includes('Prediction failed') && (
        <Reveal className="mb-8 flex justify-center">
          <InlineError message={error} onDismiss={() => setError(null)} />
        </Reveal>
      )}

      <div className="w-full">
        <AnimatePresence mode="wait">
          {!audioFile ? (
            <motion.div
              key="dropzone"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.45 }}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              className={`relative transition-transform duration-300 ${
                isDragging ? 'scale-[1.015]' : ''
              }`}
            >
              <TiltCard
                className={`flex h-[360px] flex-col items-center justify-center overflow-hidden border-dashed p-10 text-center transition-colors duration-300 ${
                  isDragging
                    ? 'border-blue-500 bg-blue-50/10 dark:border-blue-400 dark:bg-blue-950/10'
                    : 'hover:border-blue-500/50'
                }`}
              >
                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50/80 text-blue-600 shadow-md dark:border-slate-800 dark:bg-slate-950/80 dark:text-blue-400">
                  <UploadCloud className="h-7 w-7" strokeWidth={1.8} />
                </div>

                <h3 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
                  {isDragging ? 'Release to upload' : 'Drag and drop audio file'}
                </h3>
                <p className="mt-3 max-w-xs text-sm text-slate-500 dark:text-slate-400">
                  Supports MP3, WAV, or M4A. Mono or Stereo files.
                </p>

                <label className="mt-8 mx-auto cursor-pointer inline-flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white transition-all shadow-md shadow-blue-500/10 hover:shadow-blue-500/20">
                  Browse files
                  <input
                    type="file"
                    accept="audio/*"
                    className="sr-only"
                    onChange={(e) => e.target.files && handleFile(e.target.files[0])}
                  />
                </label>
              </TiltCard>
            </motion.div>
          ) : (
            <motion.div
              key="details"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.45 }}
            >
              <div className="relative rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-100/80 dark:border-slate-800 dark:bg-slate-900/90 dark:shadow-none">
                <div className="absolute inset-x-0 top-0 h-1.5 overflow-hidden rounded-t-3xl bg-slate-100 dark:bg-slate-800">
                  <motion.div
                    initial={false}
                    animate={{ width: `${uploadProgress}%` }}
                    transition={{ duration: 0.4, ease: 'easeOut' }}
                    className="h-full bg-blue-600 dark:bg-blue-500"
                  />
                </div>

                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-blue-600 dark:border-slate-800 dark:bg-slate-950 dark:text-blue-400">
                      <FileAudio className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h4 className="truncate font-semibold text-slate-900 dark:text-white">{audioFile.name}</h4>
                      <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                        {(audioFile.size / (1024 * 1024)).toFixed(2)} MB · {audioFile.type || 'audio/*'}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {isUploading ? (
                      <span className="flex items-center gap-2 text-xs font-semibold text-blue-600 dark:text-blue-400">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Transcribing
                      </span>
                    ) : (
                      <span className="flex items-center gap-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        <CheckCircle className="h-4 w-4" />
                        Done
                      </span>
                    )}
                  </div>
                </div>

                {/* Connected Sound Waveform representation */}
                <div className="my-8 rounded-2xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-800/80 dark:bg-slate-950/40">
                  <Waveform className="h-20 w-full" />
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400 dark:text-slate-500">Status</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {isUploading ? `Uploading file & running models (${uploadProgress}%)` : 'Processing successful'}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
