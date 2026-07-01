'use client'

import { cn } from '@/lib/utils'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { type ReactNode, useRef } from 'react'

type Props = {
  children: ReactNode
  className?: string
  variant?: 'primary' | 'ghost'
  href?: string
  onClick?: () => void
}

export function MagneticButton({
  children,
  className,
  variant = 'primary',
  href,
  onClick,
}: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const sx = useSpring(x, { stiffness: 200, damping: 15 })
  const sy = useSpring(y, { stiffness: 200, damping: 15 })
  const tx = useTransform(sx, (v) => v * 0.35)
  const ty = useTransform(sy, (v) => v * 0.35)

  const handleMove = (e: React.MouseEvent) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    x.set(e.clientX - rect.left - rect.width / 2)
    y.set(e.clientY - rect.top - rect.height / 2)
  }

  const reset = () => {
    x.set(0)
    y.set(0)
  }

   const base =
     'relative inline-flex items-center justify-center gap-2 rounded-full px-7 py-3.5 text-sm font-medium tracking-wide transition-all duration-300 will-change-transform select-none'
   const styles =
     variant === 'primary'
       ? 'text-primary-foreground'
       : 'text-slate-800 hover:text-slate-900 border border-slate-200/80 bg-slate-50/50 hover:bg-slate-100/80 hover:border-slate-300 dark:text-foreground/80 dark:hover:text-foreground dark:border-white/10 dark:bg-white/[0.03] dark:hover:bg-white/[0.06]'
 
   const Inner = (
     <motion.div
       ref={ref}
       onMouseMove={handleMove}
       onMouseLeave={reset}
       onClick={onClick}
       style={{ x: tx, y: ty }}
       whileTap={{ scale: 0.94 }}
       className={cn(base, styles, className)}
     >
       {variant === 'primary' && (
         <span
           aria-hidden
           className="absolute inset-0 rounded-full bg-primary shadow-lg shadow-blue-500/20 dark:shadow-[0_0_32px_rgba(37,99,235,0.4)]"
         />
       )}
       {variant === 'primary' && (
         <span
           aria-hidden
           className="absolute inset-0 rounded-full opacity-0 transition-opacity duration-300 hover:opacity-100 bg-gradient-to-r from-blue-600 to-indigo-600 shadow-xl shadow-blue-500/25 dark:shadow-[0_0_48px_rgba(34,211,238,0.45)]"
         />
       )}
       <span className="relative z-10 flex items-center gap-2">{children}</span>
     </motion.div>
   )

  if (href) {
    return (
      <a href={href} className="inline-flex">
        {Inner}
      </a>
    )
  }
  return Inner
}
