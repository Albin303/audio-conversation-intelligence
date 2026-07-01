'use client'

import { useEffect, useRef } from 'react'

export function AudioIntelligenceEngine({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouse = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let dpr = Math.min(window.devicePixelRatio || 1, 2)
    let w = 0
    let h = 0
    let cx = 0
    let cy = 0
    let maxRadius = 0

    const resize = () => {
      w = canvas.clientWidth
      h = canvas.clientHeight
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      cx = w / 2
      cy = h / 2
      maxRadius = Math.min(w, h) * 0.38
    }

    let raf = 0
    let t = 0

    const render = () => {
      t += reduce ? 0 : 0.008
      ctx.clearRect(0, 0, w, h)

      // Interpolate mouse coordinates smoothly
      mouse.current.x += (mouse.current.targetX - mouse.current.x) * 0.08
      mouse.current.y += (mouse.current.targetY - mouse.current.y) * 0.08

      const mouseStrength = Math.sqrt(mouse.current.x * mouse.current.x + mouse.current.y * mouse.current.y)
      const mouseAngle = Math.atan2(mouse.current.y, mouse.current.x)

      // Get theme colors from DOM computed variables
      const isDark = document.documentElement.classList.contains('dark')
      const accentColor = isDark ? 'rgba(34, 211, 238, 0.45)' : 'rgba(37, 99, 235, 0.35)'
      const primaryColor = isDark ? 'rgba(37, 99, 235, 0.3)' : 'rgba(79, 70, 229, 0.2)'
      const secondaryColor = isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(96, 165, 250, 0.1)'
      const coreColor = isDark ? 'rgba(34, 211, 238, 0.7)' : 'rgba(37, 99, 235, 0.65)'

      // Draw central sound energy glow core
      const corePulse = 1 + Math.sin(t * 4) * 0.08
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxRadius * 0.25 * corePulse)
      coreGrad.addColorStop(0, coreColor.replace('0.7', '0.2').replace('0.65', '0.2'))
      coreGrad.addColorStop(0.5, primaryColor.replace('0.3', '0.08').replace('0.2', '0.05'))
      coreGrad.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = coreGrad
      ctx.beginPath()
      ctx.arc(cx, cy, maxRadius * 0.5 * corePulse, 0, Math.PI * 2)
      ctx.fill()

      // Render concentric waveform rings
      const numRings = 5
      const wavePoints: { x: number; y: number; id: number }[][] = []

      for (let r = 0; r < numRings; r++) {
        const baseRadius = maxRadius * (0.35 + (r / numRings) * 0.6)
        const pointsCount = 90 + r * 15
        const currentRingPoints: { x: number; y: number; id: number }[] = []

        ctx.beginPath()
        
        // Custom animation parameters per ring layer
        const speedMultiplier = 1.5 - r * 0.18
        const waveFrequency = 4 + r * 2
        const waveAmplitude = maxRadius * (0.015 + (1 / (r + 1)) * 0.065)

        for (let i = 0; i < pointsCount; i++) {
          const angle = (i / pointsCount) * Math.PI * 2
          
          // Neural waveform calculations combining multiple sine ripples
          let ripple = Math.sin(angle * waveFrequency + t * speedMultiplier) * waveAmplitude
          ripple += Math.cos(angle * (waveFrequency - 2) - t * 0.5) * (waveAmplitude * 0.4)

          // React directly to cursor position
          const angleDiff = Math.abs(angle - mouseAngle)
          const focus = Math.max(0, 1 - angleDiff / Math.PI)
          ripple += Math.sin(t * 6) * waveAmplitude * 0.65 * focus * mouseStrength

          const radius = baseRadius + ripple
          const px = cx + Math.cos(angle) * radius
          const py = cy + Math.sin(angle) * radius

          currentRingPoints.push({ x: px, y: py, id: i })

          if (i === 0) {
            ctx.moveTo(px, py)
          } else {
            ctx.lineTo(px, py)
          }
        }

        ctx.closePath()

        // Set wave line styling
        const grad = ctx.createLinearGradient(cx - maxRadius, cy, cx + maxRadius, cy)
        grad.addColorStop(0, primaryColor)
        grad.addColorStop(0.5, accentColor)
        grad.addColorStop(1, secondaryColor)

        ctx.strokeStyle = grad
        ctx.lineWidth = 1.4 - r * 0.18
        ctx.stroke()

        wavePoints.push(currentRingPoints)
      }

      // Draw faint, neural interconnection strings (data streams) between adjacent waveforms
      ctx.lineWidth = 0.5
      ctx.strokeStyle = isDark ? 'rgba(34, 211, 238, 0.06)' : 'rgba(37, 99, 235, 0.04)'
      
      for (let r = 0; r < numRings - 1; r++) {
        const ringA = wavePoints[r]
        const ringB = wavePoints[r + 1]
        if (!ringA || !ringB) continue

        // Connect nodes inside the frequency band dynamically
        for (let i = 0; i < ringA.length; i += 6) {
          const ptA = ringA[i]
          const targetIndex = Math.floor((i / ringA.length) * ringB.length)
          const ptB = ringB[targetIndex]
          
          if (ptA && ptB) {
            ctx.beginPath()
            ctx.moveTo(ptA.x, ptA.y)
            ctx.lineTo(ptB.x, ptB.y)
            ctx.stroke()
          }
        }
      }

      // Render glowing nodes (data frequencies) along the main outer ring
      const outerRing = wavePoints[numRings - 1]
      if (outerRing) {
        ctx.fillStyle = isDark ? 'rgba(34, 211, 238, 0.8)' : 'rgba(37, 99, 235, 0.7)'
        for (let i = 0; i < outerRing.length; i += 18) {
          const node = outerRing[i]
          if (node) {
            const pulseSize = 2.5 + Math.sin(t * 5 + node.id) * 1.2
            ctx.beginPath()
            ctx.arc(node.x, node.y, pulseSize, 0, Math.PI * 2)
            ctx.fill()
          }
        }
      }

      raf = requestAnimationFrame(render)
    }

    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      const mx = e.clientX - rect.left - rect.width / 2
      const my = e.clientY - rect.top - rect.height / 2
      mouse.current.targetX = mx / (rect.width / 2)
      mouse.current.targetY = my / (rect.height / 2)
    }

    const onLeave = () => {
      mouse.current.targetX = 0
      mouse.current.targetY = 0
    }

    resize()
    window.addEventListener('resize', resize)
    window.addEventListener('mousemove', onMove)
    canvas.addEventListener('mouseleave', onLeave)
    
    raf = requestAnimationFrame(render)

    return () => {
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMove)
      canvas.removeEventListener('mouseleave', onLeave)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* Dynamic sound core */}
      <canvas ref={canvasRef} className="h-full w-full max-w-full max-h-full" />
    </div>
  )
}
