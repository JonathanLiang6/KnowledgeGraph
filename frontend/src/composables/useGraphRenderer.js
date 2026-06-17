// ============================================================
// Canvas 图谱渲染器 — D3 力导向布局 + Canvas 2D
// 节点大小按权重（越核心越大），支持滑块缩放、点击、悬停
// ============================================================
import * as d3 from 'd3'

export function useGraphRenderer(canvasRef, width, height, onNodeClick) {
  let ctx = null
  let canvas = null
  let simulation = null
  let nodes = []
  let links = []
  let transform = d3.zoomIdentity
  let hoveredNode = null
  let selectedNode = null
  let sizeScale = 1.0

  function init(data, scale = 1.0) {
    if (!canvasRef.value) return
    sizeScale = scale
    canvas = canvasRef.value
    const dpr = window.devicePixelRatio || 1
    canvas.width = width.value * dpr
    canvas.height = height.value * dpr
    canvas.style.width = width.value + 'px'
    canvas.style.height = height.value + 'px'
    ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)

    // Zoom
    d3.select(canvas).call(
      d3.zoom()
        .scaleExtent([0.2, 5])
        .on('zoom', (e) => { transform = e.transform; draw() })
    )

    // Click
    d3.select(canvas).on('click', (e) => {
      const rect = canvas.getBoundingClientRect()
      const mx = (e.clientX - rect.left - transform.x) / transform.k
      const my = (e.clientY - rect.top - transform.y) / transform.k
      const hit = hitTest(mx, my)
      if (onNodeClick) onNodeClick(hit)
      selectedNode = hit
      draw()
    })

    // Hover
    d3.select(canvas).on('mousemove', (e) => {
      const rect = canvas.getBoundingClientRect()
      const mx = (e.clientX - rect.left - transform.x) / transform.k
      const my = (e.clientY - rect.top - transform.y) / transform.k
      const prev = hoveredNode
      hoveredNode = hitTest(mx, my)
      if (prev !== hoveredNode) {
        canvas.style.cursor = hoveredNode ? 'pointer' : 'grab'
        draw()
      }
    })

    // Copy data
    nodes = data.nodes.map((n, i) => ({
      ...n,
      x: width.value / 2 + (Math.random() - 0.5) * 200,
      y: height.value / 2 + (Math.random() - 0.5) * 200,
      index: i,
    }))
    links = data.links.map(l => ({
      ...l,
      source: nodes.find(n => n.id === l.source) || l.source,
      target: nodes.find(n => n.id === l.target) || l.target,
    }))

    // Force simulation only
    simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-350))
      .force('center', d3.forceCenter(width.value / 2, height.value / 2))
      .force('collision', d3.forceCollide(28))
      .on('tick', draw)
  }

  function setNodeSizeScale(s) {
    sizeScale = s
    if (simulation) simulation.alpha(0.3).restart()
  }

  // ---------- helpers ----------

  function hitTest(mx, my) {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i]
      const r = nodeRadius(n)
      const dx = mx - n.x
      const dy = my - n.y
      if (dx * dx + dy * dy <= (r + 4) * (r + 4)) return n
    }
    return null
  }

  function nodeRadius(n) {
    // 权重 0.95→~25px，权重 0.5→~13px，默认80%缩放后核心节点≈20px
    const base = Math.max(5, Math.min(26, (n.weight || 0.5) * 27))
    return base * sizeScale
  }

  // ---------- draw ----------

  function draw() {
    if (!ctx || !canvas) return
    const w = width.value
    const h = height.value
    ctx.save()
    ctx.clearRect(0, 0, w, h)
    ctx.translate(transform.x, transform.y)
    ctx.scale(transform.k, transform.k)

    // ---- links ----
    for (const l of links) {
      const sx = l.source?.x
      const sy = l.source?.y
      const tx = l.target?.x
      const ty = l.target?.y
      if (sx == null || tx == null) continue

      const hl = hoveredNode && (l.source === hoveredNode || l.target === hoveredNode)
      const sl = selectedNode && (l.source === selectedNode || l.target === selectedNode)

      ctx.beginPath()
      ctx.moveTo(sx, sy)
      ctx.lineTo(tx, ty)
      ctx.strokeStyle = sl ? '#4F8CF7' : hl ? '#7CABFF' : '#D0D8E8'
      ctx.lineWidth = (hl || sl) ? 2.0 : Math.max(0.6, (l.value || 0.5) * 1.4)
      ctx.stroke()

      // 关系标签（缩放 > 0.4 或高亮时显示）
      if (transform.k > 0.4 && (hl || sl || transform.k > 0.7)) {
        const mx = (sx + tx) / 2
        const my = (sy + ty) / 2
        ctx.fillStyle = hl ? '#4F8CF7' : '#8B95A8'
        const fs = Math.max(10, 11 / transform.k)
        ctx.font = `${fs}px -apple-system, "PingFang SC", sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'bottom'
        ctx.fillText(l.relation || '', mx, my - 4)
      }
    }

    // ---- nodes ----
    for (const n of nodes) {
      const r = nodeRadius(n)
      const isHovered = n === hoveredNode
      const isSelected = n === selectedNode

      // 发光晕
      if (isHovered || isSelected) {
        ctx.beginPath()
        ctx.arc(n.x, n.y, r + 8, 0, Math.PI * 2)
        ctx.fillStyle = isSelected ? 'rgba(79,140,247,0.25)' : 'rgba(79,140,247,0.12)'
        ctx.fill()
      }

      // 圆形节点（纯二维扁平风格）
      ctx.beginPath()
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2)

      // 纯二维扁平圆形
      ctx.fillStyle = n.color || '#4F8CF7'
      ctx.fill()

      // 边框
      ctx.strokeStyle = isSelected ? '#4F8CF7' : isHovered ? '#7CABFF' : 'rgba(255,255,255,0.7)'
      ctx.lineWidth = isSelected ? 2.5 : isHovered ? 2 : 1.2
      ctx.stroke()

      // 标签
      if (isHovered || isSelected || transform.k > 0.45) {
        const fs = isHovered || isSelected ? 13 : Math.max(10, 11 / transform.k)
        ctx.fillStyle = '#1A1A2E'
        ctx.font = `600 ${fs}px -apple-system, "PingFang SC", sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillText(n.name, n.x, n.y + r + 6)
      }
    }

    ctx.restore()
  }

  function stop() {
    if (simulation) simulation.stop()
  }

  function resize(w, h) {
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.width = w + 'px'
    canvas.style.height = h + 'px'
    if (ctx) { ctx.scale(dpr, dpr); draw() }
  }

  return { init, stop, resize, draw, setNodeSizeScale }
}
