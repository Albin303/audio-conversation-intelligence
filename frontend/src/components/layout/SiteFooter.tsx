'use client';

import { scrollToSection, TARGET_NAV_ITEMS } from '@/config/navigation';

const FOOTER_LINKS = TARGET_NAV_ITEMS.filter((item) =>
  ['technology', 'architecture', 'deployment', 'performance'].includes(item.id),
);

export function SiteFooter() {
  return (
    <footer
      id="footer"
      className="relative mt-12 w-full overflow-hidden border-t border-nexus-border bg-nexus-card/40 backdrop-blur-xl"
    >
      <div className="mx-auto max-w-6xl px-6 py-14 md:px-10">
        <div className="grid gap-10 md:grid-cols-[1.2fr_1fr]">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-nexus-accent text-sm font-bold text-white">
                S
              </div>
              <div>
                <p className="font-semibold tracking-tight text-nexus-fg">Speech Intelligence and Intent Detection</p>
                <p className="text-xs text-nexus-muted">Enterprise Audio Intelligence</p>
              </div>
            </div>
            <p className="mt-5 max-w-md text-sm leading-relaxed text-nexus-muted">
              A full-stack audio intelligence platform — from upload and transcription through
              speaker identification, analytics, and follow-up workflows.
            </p>
          </div>

          <div>
            <p className="mb-4 text-[10px] font-semibold uppercase tracking-[0.16em] text-nexus-muted">
              Engineering
            </p>
            <ul className="grid grid-cols-2 gap-2">
              {FOOTER_LINKS.map((link) => (
                <li key={link.id}>
                  <button
                    type="button"
                    onClick={() => scrollToSection(link.id)}
                    className="text-sm text-nexus-muted transition-colors hover:text-nexus-fg"
                  >
                    {link.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-2 border-t border-nexus-border pt-6 text-xs text-nexus-muted sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Speech Intelligence and Intent Detection. Portfolio project.</p>
          <p className="font-mono">FastAPI · Next.js · Whisper · LLaMA · XGBoost</p>
        </div>
      </div>
    </footer>
  );
}
