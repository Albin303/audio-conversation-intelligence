'use client';

import { Moon, Sun } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useTheme } from '@/providers/ThemeProvider';

type ThemeToggleProps = {
  className?: string;
  compact?: boolean;
};

export function ThemeToggle({ className, compact = false }: ThemeToggleProps) {
  const { resolved, toggleTheme } = useTheme();
  const isDark = resolved === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={cn(
        'group relative inline-flex items-center justify-center rounded-xl border transition-all duration-300',
        'border-nexus-border bg-nexus-card text-nexus-muted hover:text-nexus-fg',
        'hover:border-nexus-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-nexus-accent/40',
        compact ? 'h-9 w-9' : 'h-10 gap-2 px-3',
        className,
      )}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      <Sun
        className={cn(
          'h-4 w-4 transition-all duration-300',
          isDark ? 'scale-0 rotate-90 opacity-0' : 'scale-100 rotate-0 opacity-100',
          compact && 'absolute',
        )}
      />
      <Moon
        className={cn(
          'h-4 w-4 transition-all duration-300',
          isDark ? 'scale-100 rotate-0 opacity-100' : 'scale-0 -rotate-90 opacity-0',
          compact && 'absolute',
        )}
      />
      {!compact && (
        <span className="text-xs font-medium">{isDark ? 'Dark' : 'Light'}</span>
      )}
    </button>
  );
}
