import { cn } from '@/lib/utils';

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
};

const variantMap = {
  primary:
    'bg-nexus-accent text-white hover:bg-nexus-accent/90 shadow-soft border border-nexus-accent/20',
  secondary:
    'bg-nexus-card text-nexus-fg border border-nexus-border hover:border-nexus-accent/30 hover:bg-nexus-card/90',
  ghost: 'text-nexus-muted hover:text-nexus-fg hover:bg-nexus-card/60',
};

const sizeMap = {
  sm: 'h-9 px-3 text-sm rounded-lg',
  md: 'h-11 px-5 text-sm rounded-xl',
  lg: 'h-12 px-6 text-base rounded-xl',
};

export function Button({
  className,
  variant = 'primary',
  size = 'md',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium transition-all duration-300',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-nexus-accent/40',
        'disabled:pointer-events-none disabled:opacity-50',
        variantMap[variant],
        sizeMap[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
