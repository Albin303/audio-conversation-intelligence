'use client';

import { cn } from '@/lib/utils';

type InlineErrorProps = {
  message: string;
  onDismiss?: () => void;
  className?: string;
};

export function InlineError({ message, onDismiss, className }: InlineErrorProps) {
  return (
    <div
      role="alert"
      className={cn(
        'inline-flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-400',
        className,
      )}
    >
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="ml-1 font-medium underline underline-offset-2 hover:text-red-500"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}
