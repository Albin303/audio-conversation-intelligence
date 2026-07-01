import { cn } from '@/lib/utils';

type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  variant?: 'glass' | 'solid' | 'outline';
  padding?: 'none' | 'sm' | 'md' | 'lg';
};

const paddingMap = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

const variantMap = {
  glass: 'glass-panel',
  solid: 'bg-nexus-panel border border-nexus-border shadow-soft',
  outline: 'border border-nexus-border bg-transparent',
};

export function Card({
  className,
  variant = 'glass',
  padding = 'md',
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn('rounded-2xl', variantMap[variant], paddingMap[padding], className)}
      {...props}
    >
      {children}
    </div>
  );
}
