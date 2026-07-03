'use client';

import { motion } from 'framer-motion';
import { Volume2, Cpu, Brain, LineChart, ShieldCheck, ArrowRight } from 'lucide-react';
import { Reveal } from '@/components/primitives/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { useState } from 'react';

const steps = [
  {
    icon: Volume2,
    title: 'Audio',
    subtitle: 'Raw Input',
    description: 'Record raw meetings, phone conversations, voice files, or streams with clean, loss-less recording pipes.',
    accent: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Cpu,
    title: 'AI Processing',
    subtitle: 'Recognition',
    description: 'Convert speech to high-accuracy text transcripts instantly with low-latency Whisper and Nemotron neural systems.',
    accent: 'from-cyan-500 to-blue-600',
  },
  {
    icon: Brain,
    title: 'Understanding',
    subtitle: 'Speaker Identification',
    description: 'Identify distinct voiceprints, map who spoke when, and cluster conversation points based on speaker behavior.',
    accent: 'from-blue-600 to-indigo-500',
  },
  {
    icon: LineChart,
    title: 'Insights',
    subtitle: 'Analysis',
    description: 'Surface aspect-based sentiment, calculate engagement metrics, and isolate key follow-up action items.',
    accent: 'from-indigo-500 to-purple-500',
  },
  {
    icon: ShieldCheck,
    title: 'Actions',
    subtitle: 'Automation',
    description: 'Deliver summaries directly into corporate dashboards, trigger alerts, and sync follow-up pipelines.',
    accent: 'from-purple-500 to-pink-500',
  },
];

export function ProductStoryBlock() {
  const [activeStep, setActiveStep] = useState<number | null>(null);

  return (
    <section id="story" className="relative mx-auto max-w-7xl px-6 py-24 md:px-10 lg:px-12 lg:py-32">
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <div className="absolute left-1/4 top-1/2 h-72 w-72 rounded-full bg-blue-500/5 blur-3xl" />
        <div className="absolute right-1/4 bottom-0 h-72 w-72 rounded-full bg-indigo-500/5 blur-3xl" />
      </div>

      <Reveal>
        <SectionHeader
          eyebrow="Workflow"
          title="How Voice Intelligence Works"
          description="Speech Intelligence and Intent Detection processes the entire lifecycle of enterprise voice, turning spoken words into structured action items."
          align="center"
          className="mb-16"
        />
      </Reveal>

      {/* Horizontal Flow Diagram */}
      <div className="relative grid gap-6 md:grid-cols-5">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const isActive = activeStep === index;
          
          return (
            <Reveal key={step.title} delay={index * 0.08} className="relative h-full">
              {/* Connector line for large screens */}
              {index < steps.length - 1 && (
                <div className="absolute top-12 left-[calc(100%-12px)] z-0 hidden w-full items-center md:flex" aria-hidden>
                  <div className="h-0.5 w-full bg-slate-200/80 dark:bg-slate-800/80" />
                  <ArrowRight className="h-4 w-4 -translate-x-3 text-slate-300 dark:text-slate-700" />
                </div>
              )}

              <div
                onMouseEnter={() => setActiveStep(index)}
                onMouseLeave={() => setActiveStep(null)}
                className={`relative z-10 flex h-full flex-col rounded-3xl border p-7 transition-all duration-500 ${
                  isActive 
                    ? 'border-blue-500/30 bg-white shadow-xl shadow-blue-500/5 dark:bg-slate-900/90 dark:border-blue-500/20' 
                    : 'border-slate-200/60 bg-white/70 backdrop-blur-md hover:border-slate-300/80 dark:border-slate-800/80 dark:bg-slate-900/40 dark:hover:border-slate-700/80'
                }`}
              >
                <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-r ${step.accent} text-white shadow-md transition-transform duration-500 ${isActive ? 'scale-110 rotate-3' : ''}`}>
                  <Icon className="h-5 w-5" />
                </div>

                <div className="mt-6 flex-grow">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Step 0{index + 1} · {step.subtitle}
                  </span>
                  <h3 className="mt-2 text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                    {step.title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                    {step.description}
                  </p>
                </div>
              </div>
            </Reveal>
          );
        })}
      </div>

      {/* Summary Highlight Box */}
      <Reveal delay={0.4} className="mt-16">
        <div className="rounded-3xl border border-slate-200/60 bg-slate-50/50 p-8 text-center backdrop-blur-md dark:border-slate-800/80 dark:bg-slate-900/30">
          <p className="mx-auto max-w-3xl text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
            Speech Intelligence and Intent Detection ensures compliance, high fidelity, and actionability at scale. By embedding the 
            <span className="mx-1 text-blue-600 font-semibold dark:text-blue-400">Audio Intelligence Engine</span> 
            directly into your workflows, raw conversations immediately drive business value.
          </p>
        </div>
      </Reveal>
    </section>
  );
}
