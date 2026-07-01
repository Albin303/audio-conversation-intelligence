'use client'

import { useEffect, useRef } from 'react'

export function Waveform({ className }: { className?: string }) {
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

    const resize = () => {
      w = canvas.clientWidth
      h = canvas.clientHeight
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    let raf = 0
    let t = 0
    const render = () => {
      t += reduce ? 0 : 0.02
      ctx.clearRect(0, 0, w, h)
      const mid = h / 2
      const lines = 3
      for (let l = 0; l < lines; l++) {
        ctx.beginPath()
        const amp = (h / 3) * (1 - l * 0.28)
        const phase = t + l * 0.8
        for (let x = 0; x <= w; x += 4) {
          const nx = x / w
          const envelope = Math.sin(nx * Math.PI)
          const y =
            mid +
            Math.sin(nx * 18 + phase) *
              amp *
              envelope *
              (0.5 + 0.5 * Math.sin(phase * 1.3 + nx * 6))
          if (x === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        const grad = ctx.createLinearGradient(0, 0, w, 0)
        grad.addColorStop(0, 'rgba(37,99,235,0)')
        grad.addColorStop(0.5, `rgba(34,211,238,${0.7 - l * 0.2})`)
        grad.addColorStop(1, 'rgba(139,92,246,0)')
        ctx.strokeStyle = grad
        ctx.lineWidth = 2 - l * 0.4
        ctx.shadowBlur = 12
        ctx.shadowColor = 'rgba(34,211,238,0.5)'
        ctx.stroke()
        ctx.shadowBlur = 0
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

  return <canvas ref={canvasRef} className={className} />
}
