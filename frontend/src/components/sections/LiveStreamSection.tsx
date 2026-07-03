'use client';

import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Mic, Square, Loader2, Activity, Radio, RadioTower, CheckCircle, ArrowDown } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { apiService } from '@/services/api';
import { scrollToSection } from '@/config/navigation';

export function LiveStreamSection() {
  const {
    recordingState, setRecordingState,
    liveTranscript, setLiveTranscript,
    socketStatus, setSocketStatus,
    features,
    setTranscription, setExtracting, setFeatures, setPrediction, setError
  } = useAppStore();

  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordedBytes, setRecordedBytes] = useState(0);
  const audioChunksRef = useRef<Blob[]>([]);
  const sourceStreamRef = useRef<MediaStream | null>(null);
  const stopInProgressRef = useRef(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveTranscript]);

  const startCapture = async () => {
    try {
      setError(null);
      setLiveTranscript('');
      setTranscription('');
      setFeatures(null);
      setPrediction(null);
      setRecordedBytes(0);
      audioChunksRef.current = [];
      stopInProgressRef.current = false;

      // Request microphone recording
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false
      });
      sourceStreamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          setRecordedBytes((current) => current + event.data.size);
        }
      };

      recorder.onstop = () => {
        void finalizeRecording();
      };

      recorder.start(1000);
      setMediaRecorder(recorder);
      setRecordingState('recording');
      setSocketStatus('connected');

    } catch (err: any) {
      console.error(err);
      // Handle microphone permission errors gracefully
      const isPermissionDenied = err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError';
      const errMsg = isPermissionDenied
        ? 'Microphone permission is required to record conversations.'
        : (err.message || 'Failed to record audio.');
      setError(errMsg);
      setRecordingState('idle');
      setSocketStatus('disconnected');
      stopCaptureDevices();
    }
  };

  const stopCaptureDevices = () => {
    sourceStreamRef.current?.getTracks().forEach(t => t.stop());
    sourceStreamRef.current = null;
  };

  const stopCapture = () => {
    if (stopInProgressRef.current) return;
    stopInProgressRef.current = true;

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach(t => t.stop());
      stopCaptureDevices();
    } else {
      setRecordingState('idle');
      setSocketStatus('disconnected');
      stopCaptureDevices();
    }
    setMediaRecorder(null);
    setRecordingState('processing');
  };

  const finalizeRecording = async () => {
    const chunks = audioChunksRef.current;
    if (!chunks.length) {
      setError('No audio was recorded. Please ensure your microphone is working and try again.');
      setRecordingState('idle');
      setSocketStatus('disconnected');
      stopInProgressRef.current = false;
      return;
    }

    const recordedAt = new Date().toISOString().replace(/[:.]/g, '-');
    const audioBlob = new Blob(chunks, { type: 'audio/webm' });
    const audioFile = new File([audioBlob], `conversation-recording-${recordedAt}.webm`, { type: 'audio/webm' });

    setSocketStatus('disconnected');
    setRecordingState('analyzing');
    setExtracting(true);
    try {
      const result = await apiService.uploadAudio(audioFile);
      setLiveTranscript(result.transcription);
      setTranscription(result.transcription);
      setFeatures(result.features);
      setPrediction(result.prediction);
      useAppStore.getState().refreshFollowUpAlerts();
      setExtracting(false);
      setRecordingState('completed');
      stopInProgressRef.current = false;
      scrollToSection('processing');
    } catch (err: any) {
      console.error(err);
      setExtracting(false);
      setRecordingState('idle');
      stopInProgressRef.current = false;
      setError(err?.message || 'Failed to process the finalized recording.');
    }
  };

  const capturedSizeMb = (recordedBytes / (1024 * 1024)).toFixed(2);

  return (
    <section id="live-stream" className="py-24 md:py-28 px-8 max-w-5xl mx-auto relative z-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-80px' }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="surface-elevated p-8 md:p-12 relative overflow-hidden"
      >
        {/* Decorative blobs */}
        <div className="absolute -top-20 -right-20 w-72 h-72 bg-ai-blue/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-72 h-72 bg-ai-purple/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-6">
          <div className="flex items-start gap-4">
            <div className="relative w-12 h-12 rounded-2xl bg-gradient-to-br from-ai-blue to-ai-indigo flex items-center justify-center shadow-glow-blue shrink-0">
              <Activity className="w-6 h-6 text-white" strokeWidth={2.4} />
              <div className="absolute inset-0 rounded-2xl ring-1 ring-white/30" />
            </div>
            <div>
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-white mb-1 tracking-tight">
                Record Customer Conversation
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
                Record customer conversations through the microphone, then analyze the finalized recording.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div
              className={`relative inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full border transition-colors ${
                socketStatus === 'connected'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                  : 'bg-gray-500/10 border-gray-500/20 text-gray-500 dark:text-gray-400'
              }`}
            >
              {socketStatus === 'connected' && (
                <span className="absolute inset-0 rounded-full ring-2 ring-emerald-500/30 animate-ping" />
              )}
              {socketStatus === 'connected' ? (
                <RadioTower className="w-3.5 h-3.5 relative" />
              ) : (
                <Radio className="w-3.5 h-3.5 relative" />
              )}
              <span className="relative">{socketStatus === 'connected' ? 'Recording' : 'Recorder idle'}</span>
            </div>

            {recordingState === 'idle' || recordingState === 'completed' ? (
              <button
                onClick={() => {
                  if (recordingState === 'completed') {
                    setLiveTranscript('');
                    setTranscription('');
                  }
                  startCapture();
                }}
                className="group relative inline-flex items-center gap-2 px-6 py-3 text-white rounded-2xl font-semibold transition-all duration-300 ease-expo-out shadow-glow-blue hover:shadow-[0_0_50px_-5px_rgba(10,132,255,0.7)] hover:-translate-y-0.5 overflow-hidden"
                style={{ background: 'linear-gradient(135deg, #0A84FF 0%, #5E5CE6 100%)' }}
              >
                <Mic className="w-4 h-4" />
                {recordingState === 'completed' ? 'Start New Recording' : 'Start Recording'}
                <span className="absolute inset-0 ring-1 ring-inset ring-white/20 rounded-2xl pointer-events-none" />
              </button>
            ) : recordingState === 'recording' ? (
              <button
                onClick={stopCapture}
                className="group inline-flex items-center gap-2 px-6 py-3 text-white rounded-2xl font-semibold transition-all duration-300 ease-expo-out shadow-[0_0_30px_-5px_rgba(239,68,68,0.5)] hover:shadow-[0_0_50px_-5px_rgba(239,68,68,0.7)] hover:-translate-y-0.5"
                style={{ background: 'linear-gradient(135deg, #ef4444 0%, #f43f5e 100%)' }}
              >
                <span className="relative flex items-center justify-center w-2 h-2">
                  <span className="absolute inset-0 rounded-full bg-white animate-ping" />
                  <Square className="w-3 h-3 fill-white relative" />
                </span>
                Stop Recording
              </button>
            ) : (
              <button
                disabled
                className="inline-flex items-center gap-2 px-6 py-3 bg-gray-500/20 text-gray-600 dark:text-gray-300 rounded-2xl font-semibold cursor-not-allowed"
              >
                <Loader2 className="w-4 h-4 animate-spin" />
                {recordingState === 'processing' ? 'Finalizing Audio...' : 'Transcribing & Analyzing...'}
              </button>
            )}
          </div>
        </div>

        {/* Live Transcript Area */}
        <div className="relative rounded-2xl bg-gradient-to-br from-gray-50/80 to-white/40 dark:from-gray-900/60 dark:to-gray-950/40 backdrop-blur border border-gray-200/70 dark:border-white/5 p-6 min-h-[300px] max-h-[400px] overflow-y-auto shadow-inner-highlight">
          {recordingState === 'recording' && (
            <div className="sticky top-0 z-10 flex items-center justify-end mb-3 -mt-1">
              <div className="inline-flex items-center gap-2 bg-red-500 text-white px-3 py-1.5 rounded-full text-[10px] font-bold tracking-widest shadow-[0_0_24px_-4px_rgba(239,68,68,0.6)]">
                <span className="relative flex items-center justify-center w-1.5 h-1.5">
                  <span className="absolute inset-0 rounded-full bg-white animate-ping" />
                  <span className="relative w-1.5 h-1.5 rounded-full bg-white" />
                </span>
                RECORDING
              </div>
            </div>
          )}

          {recordingState === 'completed' ? (
            <div className="h-full min-h-[260px] flex flex-col items-center justify-center gap-5 text-gray-400">
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-emerald-500/20 blur-2xl animate-pulse" />
                <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-emerald-500/10 to-teal-500/10 flex items-center justify-center border border-emerald-500/30">
                  <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.4, ease: 'easeOut' }}
                  >
                    <CheckCircle className="w-10 h-10 text-emerald-500" strokeWidth={1.8} />
                  </motion.div>
                </div>
              </div>
              <div className="text-center max-w-sm">
                <p className="font-semibold text-slate-800 dark:text-white text-lg">Recording Complete & Analyzed!</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  The meeting audio has been successfully transcribed, diarized, and evaluated for business signals.
                </p>
              </div>
              <button
                onClick={() => scrollToSection('input')}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 text-white rounded-xl text-sm font-semibold transition-all duration-200 shadow-md shadow-emerald-500/20 hover:shadow-lg hover:shadow-emerald-500/35 hover:-translate-y-0.5"
              >
                View Transcript & Timeline
                <ArrowDown className="w-4 h-4 animate-bounce" />
              </button>
            </div>
          ) : recordingState === 'recording' ? (
            <div className="h-full min-h-[260px] flex flex-col items-center justify-center gap-4 text-gray-500">
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-ai-blue/20 blur-2xl animate-pulse-glow" />
                <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-ai-blue/20 to-ai-purple/20 flex items-center justify-center border border-ai-blue/30">
                  <Activity className="w-9 h-9 text-ai-blue animate-pulse" strokeWidth={2.2} />
                </div>
              </div>
              {/* Live waveform */}
              <div className="flex items-end gap-1 h-8">
                {Array.from({ length: 24 }).map((_, i) => (
                  <motion.div
                    key={i}
                    animate={{ scaleY: [0.3, 1, 0.3] }}
                    transition={{
                      duration: 0.9,
                      repeat: Infinity,
                      delay: i * 0.05,
                      ease: 'easeInOut',
                    }}
                    className="w-1 rounded-full bg-gradient-to-t from-ai-blue to-ai-purple origin-bottom"
                    style={{ height: '100%' }}
                  />
                ))}
              </div>
              <div className="text-center">
                <p className="font-semibold text-gray-700 dark:text-gray-200">Recording conversation audio locally</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <span className="font-mono font-semibold text-ai-blue">{capturedSizeMb} MB</span> buffered · Transcript appears after you stop recording.
                </p>
              </div>
            </div>
          ) : recordingState === 'processing' || recordingState === 'analyzing' ? (
            <div className="h-full min-h-[260px] flex flex-col items-center justify-center gap-4 text-gray-500">
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-ai-purple/20 blur-2xl animate-pulse" />
                <Loader2 className="relative w-10 h-10 text-ai-purple animate-spin" />
              </div>
              <p className="font-semibold text-gray-700 dark:text-gray-200">
                {recordingState === 'processing' ? 'Finalizing one complete WebM file' : 'Running Whisper and sales intelligence'}
              </p>
              <div className="flex items-center gap-1.5">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                    className="w-1.5 h-1.5 rounded-full bg-ai-purple"
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[260px] flex flex-col items-center justify-center gap-4 text-gray-400">
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-ai-blue/5 blur-2xl" />
                <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-ai-blue/5 to-ai-purple/5 flex items-center justify-center border border-dashed border-ai-blue/30">
                  <Mic className="w-8 h-8 text-ai-blue/50" strokeWidth={1.5} />
                </div>
              </div>
              <div className="text-center max-w-xs">
                <p className="font-semibold text-gray-700 dark:text-gray-200">Ready to record</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Click <span className="font-semibold text-ai-blue">Start Recording</span> to begin capturing audio from your microphone.
                </p>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </section>
  );
}
