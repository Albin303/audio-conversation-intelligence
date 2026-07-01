'use client'

import { motion, type Variants } from 'framer-motion'
import type { ReactNode } from 'react'

const directions = {
  up: { y: 40, x: 0 },
  down: { y: -40, x: 0 },
  left: { x: 40, y: 0 },
  right: { x: -40, y: 0 },
  none: { x: 0, y: 0 },
}

export function Reveal({
  children,
  className,
  delay = 0,
  direction = 'up',
  blur = true,
  once = true,
}: {
  children: ReactNode
  className?: string
  delay?: number
  direction?: keyof typeof directions
  blur?: boolean
  once?: boolean
}) {
  const offset = directions[direction]
  const variants: Variants = {
    hidden: {
      opacity: 0,
      ...offset,
      filter: blur ? 'blur(12px)' : 'blur(0px)',
    },
    visible: {
      opacity: 1,
      x: 0,
      y: 0,
      filter: 'blur(0px)',
      transition: {
        duration: 0.9,
        delay,
        ease: [0.22, 1, 0.36, 1],
      },
    },
  }

  return (
    <motion.div
      className={className}
      variants={variants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once, amount: 0.25 }}
    >
      {children}
    </motion.div>
  )
}
