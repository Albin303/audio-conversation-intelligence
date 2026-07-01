import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  icon?: LucideIcon;
  align?: 'left' | 'center';
  className?: string;
};

export function SectionHeader({
  eyebrow,
  title,
  description,
  icon: Icon,
  align = 'left',
  className,
}: SectionHeaderProps) {
  const centered = align === 'center';

  return (
    <header
      className={cn(
        'mb-12 md:mb-16',
        centered && 'text-center mx-auto max-w-3xl',
        className,
      )}
    >
      {eyebrow && (
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-nexus-muted">
          {eyebrow}
        </p>
      )}
      <div className={cn('flex gap-4', centered ? 'flex-col items-center' : 'items-start')}>
        {Icon && (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-nexus-border bg-nexus-card text-nexus-accent shadow-soft">
            <Icon className="h-5 w-5" strokeWidth={2.2} />
          </div>
        )}
        <div className={centered ? 'space-y-3' : 'space-y-2'}>
          <h2 className="text-3xl font-semibold tracking-tight text-nexus-fg md:text-4xl text-balance">
            {title}
          </h2>
          {description && (
            <p className="max-w-2xl text-base leading-relaxed text-nexus-muted text-pretty">
              {description}
            </p>
          )}
        </div>
      </div>
    </header>
  );
}
