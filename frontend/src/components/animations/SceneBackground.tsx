'use client'

import { useEffect, useRef } from 'react'

function Starfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let dpr = Math.min(window.devicePixelRatio || 1, 2)
    let w = 0
    let h = 0
    type Star = {
      x: number
      y: number
      z: number
      r: number
      tw: number
    }
    let stars: Star[] = []

    const resize = () => {
      w = canvas.clientWidth
      h = canvas.clientHeight
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const count = Math.min(220, Math.floor((w * h) / 9000))
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        z: Math.random(),
        r: Math.random() * 1.4 + 0.2,
        tw: Math.random() * Math.PI * 2,
      }))
    }

    let raf = 0
    let t = 0
    const render = () => {
      t += 0.012
      ctx.clearRect(0, 0, w, h)
      for (const s of stars) {
        const twinkle = 0.5 + 0.5 * Math.sin(t + s.tw)
        const alpha = (0.25 + s.z * 0.6) * twinkle
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r * (0.6 + s.z), 0, Math.PI * 2)
        const hue = s.z > 0.7 ? '34,211,238' : '147,197,253'
        ctx.fillStyle = `rgba(${hue},${alpha})`
        ctx.fill()
        s.y += (0.05 + s.z * 0.12) * (reduce ? 0 : 1)
        if (s.y > h) s.y = 0
      }
      raf = requestAnimationFrame(render)
    }

    resize()
    window.addEventListener('resize', resize)
    raf = requestAnimationFrame(render)
    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
  )
}

export function SceneBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-background"
    >
      {/* aurora blobs */}
      <div
        className="absolute -left-[10%] top-[-20%] h-[60vh] w-[60vw] rounded-full blur-[120px]"
        style={{
          background:
            'radial-gradient(circle, rgba(37,99,235,0.35), transparent 60%)',
          animation: 'aurora-drift 22s ease-in-out infinite',
        }}
      />
      <div
        className="absolute right-[-10%] top-[10%] h-[55vh] w-[55vw] rounded-full blur-[130px]"
        style={{
          background:
            'radial-gradient(circle, rgba(139,92,246,0.28), transparent 60%)',
          animation: 'aurora-drift 28s ease-in-out infinite reverse',
        }}
      />
      <div
        className="absolute bottom-[-20%] left-[20%] h-[55vh] w-[55vw] rounded-full blur-[140px]"
        style={{
          background:
            'radial-gradient(circle, rgba(34,211,238,0.22), transparent 60%)',
          animation: 'aurora-drift 32s ease-in-out infinite',
        }}
      />
      <Starfield />
      {/* vignette */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(120% 80% at 50% 0%, transparent 40%, rgba(3,7,18,0.7) 100%)',
        }}
      />
      {/* grain */}
      <div className="grain absolute inset-0 opacity-[0.04] mix-blend-screen" />
    </div>
  )
}
