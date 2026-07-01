'use client'

import { useEffect, useRef } from 'react'

export function CursorGlow() {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (window.matchMedia('(pointer: coarse)').matches) return

    let raf = 0
    let curX = window.innerWidth / 2
    let curY = window.innerHeight / 2
    let tX = curX
    let tY = curY

    const onMove = (e: MouseEvent) => {
      tX = e.clientX
      tY = e.clientY
    }

    const loop = () => {
      curX += (tX - curX) * 0.12
      curY += (tY - curY) * 0.12
      el.style.transform = `translate3d(${curX - 250}px, ${curY - 250}px, 0)`
      raf = requestAnimationFrame(loop)
    }

    window.addEventListener('mousemove', onMove)
    raf = requestAnimationFrame(loop)
    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-[60] hidden md:block"
    >
      <div
        ref={ref}
        className="h-[500px] w-[500px] rounded-full opacity-50 blur-[80px] will-change-transform"
        style={{
          background: 'var(--cursor-glow)',
        }}
      />
    </div>
  )
}
