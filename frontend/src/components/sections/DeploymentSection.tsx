'use client';

import { Reveal } from '@/components/ui/Reveal';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Card } from '@/components/ui/Card';

const SERVICES = [
  {
    name: 'api',
    port: '8000',
    image: 'Dockerfile.api',
    role: 'REST API, job queue, health checks',
  },
  {
    name: 'frontend',
    port: '3000',
    image: 'Dockerfile.frontend',
    role: 'Next.js standalone production build',
  },
  {
    name: 'audio-worker',
    port: '—',
    image: 'Dockerfile.audio',
    role: 'Transcription & diarization (workers profile)',
  },
  {
    name: 'ml-worker',
    port: '—',
    image: 'Dockerfile.ml',
    role: 'Feature extraction & prediction (workers profile)',
  },
];

const VOLUMES = [
  { name: 'nexus_uploads', mount: '/app/uploads' },
  { name: 'nexus_database', mount: '/app/database' },
  { name: 'nexus_logs', mount: '/app/logs' },
];

export function DeploymentSection() {
  return (
    <section id="deployment" className="relative mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-28">
      <Reveal>
        <SectionHeader
          eyebrow="Infrastructure"
          title="Deployment"
          description="Containerized services orchestrated via docker-compose.v2.yml with persistent volumes."
          align="center"
        />
      </Reveal>

      <div className="grid gap-6 lg:grid-cols-3">
        <Reveal delay={0.06} className="lg:col-span-2">
          <Card padding="lg">
            <h3 className="mb-5 text-sm font-semibold text-nexus-fg">Services</h3>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead>
                  <tr className="border-b border-nexus-border text-[10px] font-semibold uppercase tracking-[0.14em] text-nexus-muted">
                    <th className="pb-3 pr-4">Service</th>
                    <th className="pb-3 pr-4">Port</th>
                    <th className="pb-3 pr-4">Image</th>
                    <th className="pb-3">Role</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-nexus-border/70">
                  {SERVICES.map((service) => (
                    <tr key={service.name}>
                      <td className="py-3 pr-4 font-mono text-xs text-nexus-accent">{service.name}</td>
                      <td className="py-3 pr-4 font-mono text-xs text-nexus-fg">{service.port}</td>
                      <td className="py-3 pr-4 font-mono text-xs text-nexus-muted">{service.image}</td>
                      <td className="py-3 text-xs text-nexus-muted">{service.role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </Reveal>

        <Reveal delay={0.1}>
          <Card padding="lg" className="h-full">
            <h3 className="mb-5 text-sm font-semibold text-nexus-fg">Volumes</h3>
            <ul className="space-y-3">
              {VOLUMES.map((volume) => (
                <li
                  key={volume.name}
                  className="rounded-xl border border-nexus-border bg-nexus-bg/50 p-3"
                >
                  <p className="font-mono text-xs font-medium text-nexus-accent">{volume.name}</p>
                  <p className="mt-1 font-mono text-[11px] text-nexus-muted">{volume.mount}</p>
                </li>
              ))}
            </ul>
          </Card>
        </Reveal>
      </div>

      <Reveal delay={0.14} className="mt-6">
        <Card padding="md" variant="outline">
          <p className="font-mono text-xs text-nexus-muted">
            docker compose -f docker-compose.v2.yml --profile workers up
          </p>
        </Card>
      </Reveal>
    </section>
  );
}
