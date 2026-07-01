'use client'

import { useEffect, useRef } from 'react'

type V3 = { x: number; y: number; z: number }

function latLngToVec(lat: number, lng: number, r: number): V3 {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lng + 180) * (Math.PI / 180)
  return {
    x: -r * Math.sin(phi) * Math.cos(theta),
    y: r * Math.cos(phi),
    z: r * Math.sin(phi) * Math.sin(theta),
  }
}

// Abstract node positions (lat/lng) representing data centers
const nodes = [
  [37, -122], [40, -74], [51, 0], [48, 2], [52, 13], [35, 139],
  [1, 103], [-33, 151], [19, 72], [-23, -46], [25, 55], [55, 37],
  [22, 114], [-1, 36], [60, 24], [-26, 28],
]
const arcs = [
  [0, 1], [1, 2], [2, 3], [3, 4], [4, 11], [5, 6], [6, 7],
  [0, 5], [1, 9], [8, 10], [12, 5], [13, 8], [2, 14], [11, 4], [15, 6],
]

export function Globe({ className }: { className?: string }) {
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
    let cx = 0
    let cy = 0
    let R = 0

    const resize = () => {
      w = canvas.clientWidth
      h = canvas.clientHeight
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      cx = w / 2
      cy = h / 2
      R = Math.min(w, h) * 0.38
    }

    const rotate = (v: V3, a: number): V3 => ({
      x: v.x * Math.cos(a) - v.z * Math.sin(a),
      y: v.y,
      z: v.x * Math.sin(a) + v.z * Math.cos(a),
    })

    let raf = 0
    let t = 0
    const render = () => {
      t += reduce ? 0 : 0.0035
      ctx.clearRect(0, 0, w, h)

      // glow
      const g = ctx.createRadialGradient(cx, cy, R * 0.2, cx, cy, R * 1.5)
      g.addColorStop(0, 'rgba(37,99,235,0.18)')
      g.addColorStop(1, 'rgba(3,7,18,0)')
      ctx.fillStyle = g
      ctx.beginPath()
      ctx.arc(cx, cy, R * 1.5, 0, Math.PI * 2)
      ctx.fill()

      // latitude / longitude grid
      ctx.strokeStyle = 'rgba(96,165,250,0.12)'
      ctx.lineWidth = 0.6
      for (let lat = -60; lat <= 60; lat += 30) {
        ctx.beginPath()
        for (let lng = -180; lng <= 180; lng += 6) {
          const v = rotate(latLngToVec(lat, lng, R), t)
          const sx = cx + v.x
          const sy = cy + v.y
          if (v.z < 0 && Math.abs(v.x) > R * 0.98) continue
          if (lng === -180) ctx.moveTo(sx, sy)
          else ctx.lineTo(sx, sy)
        }
        ctx.stroke()
      }
      for (let lng = -180; lng < 180; lng += 30) {
        ctx.beginPath()
        for (let lat = -90; lat <= 90; lat += 6) {
          const v = rotate(latLngToVec(lat, lng, R), t)
          const sx = cx + v.x
          const sy = cy + v.y
          if (lat === -90) ctx.moveTo(sx, sy)
          else ctx.lineTo(sx, sy)
        }
        ctx.stroke()
      }

      // project nodes
      const proj = nodes.map(([la, ln]) => {
        const v = rotate(latLngToVec(la, ln, R), t)
        return { x: cx + v.x, y: cy + v.y, z: v.z }
      })

      // arcs with traveling pulse
      arcs.forEach(([a, b], idx) => {
        const pa = proj[a]
        const pb = proj[b]
        if (!pa || !pb) return
        const front = (pa.z + pb.z) / 2 > -R * 0.3
        const mx = (pa.x + pb.x) / 2
        const my = (pa.y + pb.y) / 2 - 40
        ctx.beginPath()
        ctx.moveTo(pa.x, pa.y)
        ctx.quadraticCurveTo(mx, my, pb.x, pb.y)
        ctx.strokeStyle = front
          ? 'rgba(34,211,238,0.5)'
          : 'rgba(34,211,238,0.12)'
        ctx.lineWidth = front ? 1.2 : 0.6
        ctx.stroke()

        // pulse
        const p = (t * 3 + idx * 0.3) % 1
        const px = (1 - p) * (1 - p) * pa.x + 2 * (1 - p) * p * mx + p * p * pb.x
        const py = (1 - p) * (1 - p) * pa.y + 2 * (1 - p) * p * my + p * p * pb.y
        ctx.beginPath()
        ctx.arc(px, py, front ? 2.4 : 1.2, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(34,211,238,${front ? 0.9 : 0.3})`
        ctx.fill()
      })

      // nodes
      proj.forEach((p) => {
        const front = p.z > -R * 0.2
        ctx.beginPath()
        ctx.arc(p.x, p.y, front ? 3 : 1.5, 0, Math.PI * 2)
        ctx.fillStyle = front ? 'rgba(96,165,250,1)' : 'rgba(96,165,250,0.3)'
        if (front) {
          ctx.shadowBlur = 12
          ctx.shadowColor = 'rgba(34,211,238,0.9)'
        }
        ctx.fill()
        ctx.shadowBlur = 0
      })

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
