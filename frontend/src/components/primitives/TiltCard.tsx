'use client'

import { cn } from '@/lib/utils'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { type ReactNode, useRef } from 'react'

export function TiltCard({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const mx = useMotionValue(0.5)
  const my = useMotionValue(0.5)
  const rx = useSpring(useTransform(my, [0, 1], [9, -9]), { stiffness: 200, damping: 18 })
  const ry = useSpring(useTransform(mx, [0, 1], [-9, 9]), { stiffness: 200, damping: 18 })
  const gx = useTransform(mx, [0, 1], ['0%', '100%'])
  const gy = useTransform(my, [0, 1], ['0%', '100%'])

  const onMove = (e: React.MouseEvent) => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    mx.set((e.clientX - r.left) / r.width)
    my.set((e.clientY - r.top) / r.height)
  }
  const reset = () => {
    mx.set(0.5)
    my.set(0.5)
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={reset}
      style={{ rotateX: rx, rotateY: ry, transformStyle: 'preserve-3d' }}
      className={cn(
        'group relative overflow-hidden rounded-3xl glass p-7 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/5 dark:hover:shadow-[0_30px_80px_-30px_rgba(34,211,238,0.25)] border border-slate-200/60 dark:border-white/5',
        className,
      )}
    >
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: useTransform(
            [gx, gy],
            ([x, y]) =>
              `radial-gradient(220px circle at ${x} ${y}, var(--tilt-glow), transparent 70%)`,
          ),
        }}
      />
      <div style={{ transform: 'translateZ(40px)' }} className="relative flex flex-col items-center w-full">
        {children}
      </div>
    </motion.div>
  )
}
