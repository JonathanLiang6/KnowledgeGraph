/**
 * useTopologyRenderer.js - v3.2 拓扑导航 D3 力导向图渲染
 *
 * 纯 Canvas 渲染，事件通过回调外传给 Vue 组件处理。
 * 根节点固定中央，分支节点（无 kb_id）金色，KB 节点绿色。
 */
import * as d3 from 'd3'

export function useTopologyRenderer(hostRef, opts = {}) {
  const { onNodeClick, onNodeDblClick, onNodeRightClick, onCanvasClick, onCanvasRightClick } = opts

  let canvas, ctx, transform = d3.zoomIdentity
  let sim = null, simNodes = [], simLinks = []
  let nodes = [], links = []
  let rafId = null
  let clickTimer = null  // 区分单击/双击

  function init() {
    const host = hostRef.value
    if (!host) return
    host.innerHTML = ''
    const dpr = window.devicePixelRatio || 1
    canvas = document.createElement('canvas')
    canvas.width = host.clientWidth * dpr
    canvas.height = host.clientHeight * dpr
    canvas.style.width = '100%'
    canvas.style.height = '100%'
    host.appendChild(canvas)
    ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)

    const zoom = d3.zoom().scaleExtent([0.25, 3]).on('zoom', e => { transform = e.transform; schedule() })
    d3.select(canvas).call(zoom)

    // 所有事件在 canvas 上处理
    d3.select(canvas)
      .on('click', e => {
        const p = screenToWorld(e)
        const n = hitTest(p.x, p.y)
        if (n) {
          // 延迟判断单击/双击
          if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; onNodeDblClick?.(n) }
          else { clickTimer = setTimeout(() => { clickTimer = null; onNodeClick?.(n) }, 280) }
        } else {
          onCanvasClick?.()
        }
      })
      .on('contextmenu', e => {
        e.preventDefault()
        const p = screenToWorld(e)
        const n = hitTest(p.x, p.y)
        if (n) onNodeRightClick?.(n, e.clientX, e.clientY)
        else onCanvasRightClick?.(e.clientX, e.clientY)
      })

    schedule()
  }

  function screenToWorld(e) {
    const r = canvas.getBoundingClientRect()
    return { x: (e.clientX - r.left - transform.x) / transform.k, y: (e.clientY - r.top - transform.y) / transform.k }
  }

  function hitTest(wx, wy) {
    // 反向遍历（后渲染的在上面）
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i]; if (n.x == null || n.y == null) continue
      const r = n.is_root ? 44 : (!n.kb_id ? 34 : 28)
      if ((wx - n.x) ** 2 + (wy - n.y) ** 2 < r * r) return n
    }
    return null
  }

  function updateData(_nodes, _links) {
    nodes = _nodes.map(n => ({ ...n }))
    links = _links.map(l => ({ ...l }))

    const host = hostRef.value
    const cw = host?.clientWidth || 800, ch = host?.clientHeight || 600
    const cx = cw / 2, cy = ch / 2

    if (sim) sim.stop()
    simNodes = nodes.map((n, i) => {
      const sn = { ...n, x: n.position_x || cx + (Math.random() - 0.5) * 150, y: n.position_y || cy + (Math.random() - 0.5) * 150 }
      if (n.is_root) { sn.fx = cx; sn.fy = cy }
      return sn
    })
    simLinks = links.map(l => ({
      source: simNodes.find(s => s.id === l.source_id),
      target: simNodes.find(s => s.id === l.target_id),
    })).filter(l => l.source && l.target)

    sim = d3.forceSimulation(simNodes)
      .force('link', d3.forceLink(simLinks).distance(160).strength(0.3))
      .force('charge', d3.forceManyBody().strength(-350))
      .force('center', d3.forceCenter(cx, cy))
      .force('collide', d3.forceCollide(48))
      .alphaDecay(0.015)
      .on('tick', () => {
        simNodes.forEach((s, i) => { if (i < nodes.length) { nodes[i].x = s.x; nodes[i].y = s.y } })
        schedule()
      })
      .on('end', () => schedule())

    schedule()
  }

  function schedule() {
    if (!rafId) rafId = requestAnimationFrame(() => { rafId = null; draw() })
  }

  function draw() {
    if (!ctx || !canvas) return
    const host = hostRef.value
    const cw = host?.clientWidth || 800, ch = host?.clientHeight || 600
    const dpr = window.devicePixelRatio || 1

    ctx.save(); ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, cw, ch)
    ctx.translate(transform.x, transform.y); ctx.scale(transform.k, transform.k)

    // 边
    ctx.strokeStyle = 'rgba(255,255,255,0.07)'; ctx.lineWidth = 1.2
    links.forEach(l => {
      const s = nodes.find(n => n.id === l.source_id), t = nodes.find(n => n.id === l.target_id)
      if (!s || !t || s.x == null || t.x == null) return
      ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke()
    })

    // 节点
    nodes.forEach(n => {
      const x = n.x || 0, y = n.y || 0
      const isBranch = !n.kb_id && !n.is_root
      const r = n.is_root ? 42 : isBranch ? 32 : 26

      // 光晕
      const g = ctx.createRadialGradient(x, y, r * 0.4, x, y, r * 1.6)
      g.addColorStop(0, n.is_root ? 'rgba(45,140,78,0.4)' : isBranch ? 'rgba(230,162,60,0.3)' : 'rgba(13,148,136,0.25)')
      g.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r * 1.6, 0, Math.PI * 2); ctx.fill()

      // 节点圆
      ctx.fillStyle = n.is_root ? '#1A5E30' : isBranch ? 'rgba(180,100,20,0.85)' : 'rgba(20,55,35,0.88)'
      ctx.strokeStyle = n.is_root ? 'rgba(45,140,78,0.8)' : isBranch ? 'rgba(230,162,60,0.6)' : 'rgba(13,148,136,0.5)'
      ctx.lineWidth = n.is_root ? 2.5 : 1.5
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke()

      // Emoji
      const fs = n.is_root ? 22 : isBranch ? 18 : 15
      ctx.font = `${fs}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillStyle = '#fff'; ctx.fillText(n.icon || '📁', x, y - 1)

      // 名称
      const name = (n.name || '').length > 8 ? (n.name || '').slice(0, 8) + '..' : (n.name || '')
      ctx.font = `${n.is_root ? 13 : 11}px "PingFang SC","Microsoft YaHei",sans-serif`
      ctx.textAlign = 'center'; ctx.textBaseline = 'top'
      ctx.fillStyle = n.is_root ? '#fff' : isBranch ? 'rgba(255,210,130,0.9)' : 'rgba(255,255,255,0.85)'
      ctx.fillText(name, x, y + r + 4)

      // 小标签
      if (n.is_root) {
        ctx.font = '9px sans-serif'; ctx.fillStyle = 'rgba(255,255,255,0.4)'; ctx.fillText('ROOT', x, y + r + 19)
      } else if (isBranch) {
        ctx.font = '9px sans-serif'; ctx.fillStyle = 'rgba(255,200,120,0.4)'; ctx.fillText('分支', x, y + r + 16)
      }
    })
    ctx.restore()
  }

  function resize() {
    if (!canvas || !hostRef.value) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = hostRef.value.clientWidth * dpr
    canvas.height = hostRef.value.clientHeight * dpr
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    schedule()
  }

  function destroy() { if (sim) { sim.stop(); sim = null }; nodes = []; links = []; if (rafId) cancelAnimationFrame(rafId); if (clickTimer) clearTimeout(clickTimer) }

  return { init, updateData, resize, destroy }
}
